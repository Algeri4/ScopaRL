"""
botRL/self_play_trainer.py
Trainer avanzato con curriculum learning e self-play.

Strategia:
  1. Fase 1: Allenamento contro BotCasuale (impara le basi)
  2. Fase 2: Allenamento contro BotGreedy (impara a prendere carte)
  3. Fase 3: Allenamento contro BotPredatore (impara strategie avanzate)
  4. Fase 4: Self-play (gioca contro versioni precedenti di sé stesso)

Il self-play è fondamentale per superare il livello del bot più forte:
  - Salva checkpoint ogni N episodi
  - L'avversario è una versione precedente del bot (con probabilità decay)
  - Questo crea un "adversarial training" che spinge il bot a migliorare
"""

import os
import random
import copy
import torch
from typing import Optional
from collections import deque

from scopa.ambiente import ScopaEnvironment
from scopa.observation import ObservationBuilder
from bot.casuale import BotCasuale
from bot.greedy import BotGreedy
from bot.bot_predatore import BotPredatore
from .rete import ScopaNetwork, build_action_mask
from .policy import ScopaPolicy
from .buffer import RolloutBuffer
from .trainer import PPOTrainer


class SelfPlayTrainer(PPOTrainer):
    """
    Estende PPOTrainer con curriculum learning e self-play.
    """

    def __init__(self, network: ScopaNetwork,
                 curriculum_phases: list = None,
                 self_play_start: int = 3000,
                 opponent_pool_size: int = 5,
                 **kwargs):
        """
        Args:
            network: rete neurale
            curriculum_phases: lista di (episodi, opponent_name) per curriculum
            self_play_start: episodio da cui iniziare self-play
            opponent_pool_size: quanti checkpoint vecchi tenere nel pool
            **kwargs: altri argomenti per PPOTrainer
        """
        # Inizializza con opponent casuale (verrà cambiato durante training)
        super().__init__(network, opponent=BotCasuale(), **kwargs)

        self.curriculum_phases = curriculum_phases or [
            (1000, "casuale"),
            (2000, "greedy"),
            (3000, "predatore"),
        ]
        self.self_play_start = self_play_start
        self.opponent_pool_size = opponent_pool_size

        # Pool di opponent per self-play
        self.opponent_pool = []  # Lista di (network_state_dict, winrate)
        self.current_phase = 0
        self.episodes_in_phase = 0

        # Metriche
        self.self_play_ratio = 0.0  # Percentuale di partite in self-play

    def get_curriculum_opponent(self, episode: int):
        """Determina l'avversario in base alla fase del curriculum."""
        cumulative = 0
        for max_ep, opponent_name in self.curriculum_phases:
            cumulative += max_ep
            if episode <= cumulative:
                if opponent_name == "casuale":
                    return BotCasuale()
                elif opponent_name == "greedy":
                    return BotGreedy()
                elif opponent_name == "predatore":
                    return BotPredatore()
        return None  # Self-play

    def get_self_play_opponent(self):
        """Seleziona un opponent dal pool per self-play."""
        if not self.opponent_pool:
            return BotPredatore()  # Fallback

        # Scegli un opponent dal pool (preferibilmente più recenti)
        weights = [i + 1 for i in range(len(self.opponent_pool))]
        idx = random.choices(range(len(self.opponent_pool)), weights=weights)[0]

        state_dict, _ = self.opponent_pool[idx]

        # Crea rete e carica pesi
        opponent_net = ScopaNetwork(input_dim=209, hidden_dim=512).to(self.device)
        opponent_net.load_state_dict(state_dict)
        opponent_net.eval()

        # Crea bot
        from .bot_rl import BotRL
        return BotRL(opponent_net, nome=f"BotRL_Past_{idx}", device=self.device, deterministic=True)

    def add_to_opponent_pool(self, winrate: float):
        """Aggiunge il modello corrente al pool di self-play."""
        state_dict = copy.deepcopy(self.network.state_dict())
        self.opponent_pool.append((state_dict, winrate))

        # Mantieni solo gli ultimi N
        if len(self.opponent_pool) > self.opponent_pool_size:
            self.opponent_pool.pop(0)

        print(f"🎯 Aggiunto al pool self-play (size: {len(self.opponent_pool)})")

    def train(self, n_episodes: int = 10000,
              eval_every: int = 100,
              n_eval_games: int = 50,
              save_every: int = 500,
              self_play_freq: int = 3):  # Ogni N eval, aggiungi al pool
        """
        Loop principale con curriculum e self-play.
        """
        env = ScopaEnvironment("RL_Bot", "Opponent")

        for episode in range(1, n_episodes + 1):
            # --- Curriculum Learning ---
            curriculum_opponent = self.get_curriculum_opponent(episode)

            if curriculum_opponent is not None:
                # Fase curriculum: gioca contro bot fissi
                self.opponent = curriculum_opponent
                is_self_play = False
            else:
                # Fase self-play: mix tra bot fissi e sé stesso
                if random.random() < 0.7:  # 70% self-play
                    self.opponent = self.get_self_play_opponent()
                    is_self_play = True
                else:
                    self.opponent = BotPredatore()
                    is_self_play = False

            # Raccogli rollout
            buffer = self.collect_rollout(env, agent_idx=0)

            # Update
            metrics = self.update_policy(buffer)

            # Log
            total_reward = sum(buffer.rewards)
            self.episode_rewards.append(total_reward)
            self.episode_lengths.append(len(buffer))

            if episode % 10 == 0:
                avg_reward = sum(self.episode_rewards) / len(self.episode_rewards)
                avg_length = sum(self.episode_lengths) / len(self.episode_lengths)
                mode = "SELF-PLAY" if is_self_play else self.opponent.nome()
                print(f"Episode {episode:5d} | Mode: {mode:12s} | Reward: {total_reward:7.2f} | "
                      f"Avg: {avg_reward:7.2f} | Len: {avg_length:3.0f}")

            # Evaluation e salvataggio
            if episode % eval_every == 0:
                # Valuta contro BotPredatore (benchmark fisso)
                self.opponent = BotPredatore()
                winrate = self.evaluate(n_games=n_eval_games)

                print(f"\n{'=' * 60}")
                print(f"EVALUATION Episode {episode}")
                print(f"Winrate vs Predatore: {winrate:.1%}")
                print(f"{'=' * 60}\n")

                # Salva best model
                if winrate > self.best_winrate:
                    self.best_winrate = winrate
                    self.save_checkpoint("best_model.pt", episode, winrate)
                    print(f"💾 Nuovo best model! Winrate: {winrate:.1%}")

                # Aggiungi al pool self-play ogni N eval
                if episode >= self.self_play_start and episode % (eval_every * self_play_freq) == 0:
                    self.add_to_opponent_pool(winrate)

            # Checkpoint periodico
            if episode % save_every == 0:
                self.save_checkpoint(f"checkpoint_{episode}.pt", episode)

        print("\n✅ Training completato!")
        print(f"🏆 Best winrate vs Predatore: {self.best_winrate:.1%}")