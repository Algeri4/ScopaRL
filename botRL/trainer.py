"""
botRL/trainer.py
Trainer PPO per il bot Scopa.

Gestisce:
  - Self-play o training contro bot fissi
  - Raccolta rollouts
  - Update PPO (multiple epochs sui dati raccolti)
  - Salvataggio checkpoint (con reward_engine/encoder usati)
  - Logging

RewardEngine e ObservationEncoder sono iniettabili: questo trainer resta
lo stesso file per qualsiasi combinazione di reward/input che si vuole
sperimentare. Cambia solo cosa gli passi nel costruttore.

NOTA SUL REWARD: ScopaEnvironment.step() è neutrale (restituisce sempre
reward=0.0, vedi scopa/ambiente.py). Tutto il reward numerico usato per
il training nasce da self.reward_engine, mai dall'ambiente.
"""

import os
import random
import torch
import torch.nn as nn
import torch.optim as optim
from typing import Optional, List
from collections import deque

from scopa.ambiente import ScopaEnvironment
from bot.bot_predatore import BotPredatore
from .rete import ScopaNetwork, build_action_mask, carta_to_idx
from .policy import ScopaPolicy
from .buffer import RolloutBuffer
from .reward_engine import RewardEngine, DefaultRewardEngine
from .observation_encoder import ObservationEncoder, StandardEncoder


class PPOTrainer:
    """
    Trainer PPO per Scopa Bergamasca.

    Hyperparametri tipici:
      - lr: 3e-4
      - gamma: 0.99
      - gae_lambda: 0.95
      - clip_epsilon: 0.2
      - entropy_coef: 0.01
      - value_coef: 0.5
      - max_grad_norm: 0.5
      - update_epochs: 4
      - batch_size: 64
    """

    def __init__(self,
                 network: ScopaNetwork,
                 reward_engine: RewardEngine = None,
                 observation_encoder: ObservationEncoder = None,
                 opponent=None,  # BotAgent o None per self-play
                 lr: float = 3e-4,
                 gamma: float = 0.99,
                 gae_lambda: float = 0.95,
                 clip_epsilon: float = 0.2,
                 entropy_coef: float = 0.01,
                 value_coef: float = 0.5,
                 max_grad_norm: float = 0.5,
                 update_epochs: int = 4,
                 batch_size: int = 64,
                 device: str = 'cpu',
                 checkpoint_dir: str = 'botRL/checkpoints'):

        self.device = device
        self.network = network.to(device)
        self.opponent = opponent

        self.reward_engine = reward_engine or DefaultRewardEngine()
        self.observation_encoder = observation_encoder or StandardEncoder()

        # La rete deve essere dimensionata per l'encoder scelto.
        if self.network.input_dim != self.observation_encoder.input_dim:
            raise ValueError(
                f"Rete input_dim={self.network.input_dim} != "
                f"Encoder input_dim={self.observation_encoder.input_dim} "
                f"(encoder={type(self.observation_encoder).__name__})"
            )

        # Policy del nostro agente: riceve lo STESSO encoder del trainer,
        # così training e inferenza (BotRL) sono sempre coerenti.
        self.policy = ScopaPolicy(
            network,
            encoder=self.observation_encoder,
            device=device,
            deterministic=False
        )

        self.optimizer = optim.Adam(network.parameters(), lr=lr)

        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.entropy_coef = entropy_coef
        self.value_coef = value_coef
        self.max_grad_norm = max_grad_norm
        self.update_epochs = update_epochs
        self.batch_size = batch_size

        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)

        self.episode_rewards = deque(maxlen=100)
        self.episode_lengths = deque(maxlen=100)
        self.win_history = deque(maxlen=100)
        self.best_winrate = 0.0

    def collect_rollout(self, env: ScopaEnvironment,
                         agent_idx: int = 0,
                         max_steps: int = 1000) -> RolloutBuffer:
        """
        Gioca un episodio e raccoglie la traiettoria.
        """
        buffer = RolloutBuffer(device=self.device)
        env.reset()

        step_count = 0
        last_own_observation = None  # per il reward terminale

        while not env.partita_finita and step_count < max_steps:
            current_idx = env.turno
            obs = env._get_observation(current_idx)

            if current_idx == agent_idx:
                obs_vector = torch.tensor(
                    self.observation_encoder.encode(obs),
                    dtype=torch.float32,
                    device=self.device
                )

                action_mask = build_action_mask(obs["mano"], device=self.device)

                action, action_idx, log_prob, value = self.policy.select_action(
                    obs, return_tensors=True
                )
                value = value.view(-1)

                # `_` perché env.step() restituisce sempre reward=0.0
                # (l'ambiente è neutrale sul reward, vedi scopa/ambiente.py):
                # il numero vero lo calcola self.reward_engine sotto.
                next_obs, _, done, info = env.step(action, current_idx)
                last_own_observation = next_obs

                shaped_reward = self.reward_engine.compute_step_reward(
                    info=info,
                    observation=obs,
                    action=action,
                    next_observation=next_obs,
                    done=done
                )

                buffer.add(
                    obs_vector=obs_vector,
                    action=action_idx.detach(),
                    action_mask=action_mask,
                    log_prob=log_prob.detach(),
                    reward=shaped_reward,
                    value=value.detach(),
                    done=done
                )
            else:
                if self.opponent is not None:
                    azione = self.opponent.scegli_mossa(obs)
                else:
                    azione = self.policy.select_action(obs)

                next_obs, _, done, info = env.step(azione, current_idx)

            step_count += 1

        # Reward terminale: aggiunto all'ultimo step raccolto per il nostro agente
        if env.partita_finita and last_own_observation is not None and len(buffer) > 0:
            final_reward = self.reward_engine.compute_terminal_reward(last_own_observation)
            buffer.rewards[-1] += final_reward

        return buffer

    def update_policy(self, buffer: RolloutBuffer):
        """Esegue l'update PPO sui dati raccolti."""
        if len(buffer) == 0:
            return {}

        obs, actions, masks, old_log_probs, rewards, values, dones = buffer.get_batch()
        values = values.view(-1)

        advantages, returns = buffer.compute_advantages(
            rewards, values, dones,
            gamma=self.gamma,
            gae_lambda=self.gae_lambda
        )
        returns = returns.view(-1)

        dataset_size = len(buffer)
        indices = list(range(dataset_size))

        total_policy_loss = 0
        total_value_loss = 0
        total_entropy = 0
        n_updates = 0

        for epoch in range(self.update_epochs):
            random.shuffle(indices)

            for start in range(0, dataset_size, self.batch_size):
                end = min(start + self.batch_size, dataset_size)
                batch_idx = indices[start:end]

                batch_obs = obs[batch_idx]
                batch_actions = actions[batch_idx]
                batch_masks = masks[batch_idx]
                batch_old_log_probs = old_log_probs[batch_idx]
                batch_advantages = advantages[batch_idx]
                batch_returns = returns[batch_idx]

                new_log_probs, new_values, entropy = self.policy.evaluate_actions(
                    batch_obs, batch_actions, batch_masks
                )

                new_values = new_values.view(-1)
                batch_returns = batch_returns.view(-1)
                batch_advantages = batch_advantages.view(-1)
                batch_old_log_probs = batch_old_log_probs.view(-1)
                new_log_probs = new_log_probs.view(-1)

                ratio = torch.exp(new_log_probs - batch_old_log_probs)

                surr1 = ratio * batch_advantages
                surr2 = torch.clamp(
                    ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon
                ) * batch_advantages

                policy_loss = -torch.min(surr1, surr2).mean()
                value_loss = nn.functional.mse_loss(new_values, batch_returns)
                entropy_loss = -entropy.mean()

                loss = (
                    policy_loss
                    + self.value_coef * value_loss
                    + self.entropy_coef * entropy_loss
                )

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.network.parameters(), self.max_grad_norm)
                self.optimizer.step()

                total_policy_loss += policy_loss.item()
                total_value_loss += value_loss.item()
                total_entropy += entropy.mean().item()
                n_updates += 1

        return {
            'policy_loss': total_policy_loss / n_updates,
            'value_loss': total_value_loss / n_updates,
            'entropy': total_entropy / n_updates,
        }

    def train(self, n_episodes: int = 10000,
              eval_every: int = 100,
              n_eval_games: int = 50,
              save_every: int = 500,
              log_every: int = 100):
        """Loop principale di training."""
        env = ScopaEnvironment("RL_Bot", "Opponent")

        for episode in range(1, n_episodes + 1):
            buffer = self.collect_rollout(env, agent_idx=0)
            metrics = self.update_policy(buffer)

            total_reward = sum(buffer.rewards)
            self.episode_rewards.append(total_reward)
            self.episode_lengths.append(len(buffer))

            if episode % log_every == 0:
                avg_reward = sum(self.episode_rewards) / len(self.episode_rewards)
                avg_length = sum(self.episode_lengths) / len(self.episode_lengths)
                print(f"Ep {episode:5d} | Reward: {total_reward:7.2f} | "
                      f"Avg: {avg_reward:7.2f} | Len: {avg_length:3.0f} | "
                      f"Policy: {metrics.get('policy_loss', 0):.4f} | "
                      f"Value: {metrics.get('value_loss', 0):.4f}")

            if episode % eval_every == 0:
                winrate = self.evaluate(n_games=n_eval_games)
                print(f"\n{'=' * 60}")
                print(f"EVALUATION Episode {episode}")
                print(f"Winrate vs Opponent: {winrate:.1%}")
                print(f"{'=' * 60}\n")

                if winrate > self.best_winrate:
                    self.best_winrate = winrate
                    self.save_checkpoint("best_model.pt", episode, winrate)
                    print(f"💾 Nuovo best model salvato! Winrate: {winrate:.1%}")

            if episode % save_every == 0:
                self.save_checkpoint(f"checkpoint_{episode}.pt", episode)

        print("\n✅ Training completato!")

    def evaluate(self, n_games: int = 100) -> float:
        """Valuta il bot contro l'avversario. Ritorna winrate (0-1)."""
        from cli.partita import PartitaCLI
        from .bot_rl import BotRL

        # Fallback se opponent non è settato (es. fase self-play senza bot fisso)
        opponent = self.opponent or BotPredatore()

        bot_rl = BotRL(
            self.network,
            observation_encoder=self.observation_encoder,
            device=self.device,
            deterministic=True
        )

        wins = 0
        draws = 0

        for i in range(n_games):
            a_inizia = (i % 2 == 0)

            if a_inizia:
                partita = PartitaCLI(bot_rl, opponent, a_idx=0, verbose=False)
            else:
                partita = PartitaCLI(opponent, bot_rl, a_idx=1, verbose=False)

            ris = partita.gioca(seed=i)

            if ris["vincitore"] is not None:
                vincitore_nome = bot_rl.nome() if (a_inizia and ris["vincitore"] == 0) or (
                        not a_inizia and ris["vincitore"] == 1) else opponent.nome()
                if vincitore_nome == bot_rl.nome():
                    wins += 1
            else:
                draws += 1

        winrate = wins / n_games
        return winrate

    def save_checkpoint(self, filename: str, episode: int, winrate: float = 0.0):
        """
        Salva checkpoint, includendo la CONFIGURAZIONE usata (encoder,
        reward engine, dimensioni rete) così che from_checkpoint possa
        ricostruire esattamente lo stesso setup senza doverlo indovinare.
        """
        path = os.path.join(self.checkpoint_dir, filename)
        torch.save({
            'episode': episode,
            'network_state_dict': self.network.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'winrate': winrate,
            'best_winrate': self.best_winrate,
            # --- metadati per ricostruzione corretta ---
            'network_input_dim': self.network.input_dim,
            'network_hidden_dim': self.network.hidden_dim,
            'encoder_class': type(self.observation_encoder).__name__,
            'reward_engine_class': type(self.reward_engine).__name__,
        }, path)
        print(f"💾 Checkpoint salvato: {path}")

    def load_checkpoint(self, filename: str):
        """Carica checkpoint (assume stessa rete/encoder già istanziati)."""
        path = os.path.join(self.checkpoint_dir, filename)
        checkpoint = torch.load(path, map_location=self.device)
        self.network.load_state_dict(checkpoint['network_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.best_winrate = checkpoint.get('best_winrate', 0.0)
        print(f"📂 Checkpoint caricato: {path} (episodio {checkpoint['episode']})")
        return checkpoint['episode']