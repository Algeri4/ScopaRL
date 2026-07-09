"""
botRL/trainer.py

PPOTrainer: training loop principale per ScopaNetwork via PPO.

Un "episodio" = UNA SINGOLA SMAZZATA (non l'intera partita a 11 punti).
Più smazzate vengono accumulate in un unico buffer prima di ogni update
PPO (episodes_per_update), per avere gradienti meno rumorosi.

Supporta il caricamento di pesi pre-allenati via imitation learning
(vedi botRL/pretrain/imitation.py) come warm-start della policy, invece
di partire da inizializzazione casuale.
"""

import os

import torch
import torch.nn.functional as F

from scopa.ambiente import ScopaEnvironment
from bot.predatore import BotPredatore
from bot.casuale import BotCasuale
from .rete import ScopaNetwork, build_action_mask, carta_to_idx
from .policy import Policy
from .buffer import RolloutBuffer
from .observation_encoder import StandardEncoder
from .reward_engine import DefaultRewardEngine


class PPOTrainer:
    def __init__(self,
                 network: ScopaNetwork,
                 opponent=None,
                 observation_encoder=None,
                 reward_engine=None,
                 lr: float = 3e-4,
                 gamma: float = 0.99,
                 gae_lambda: float = 0.95,
                 clip_epsilon: float = 0.2,
                 value_coef: float = 0.1,
                 entropy_coef: float = 0.01,
                 update_epochs: int = 4,
                 batch_size: int = 64,
                 device: str = "cpu",
                 checkpoint_dir: str = "botRL/checkpoints"):
        self.network = network.to(device)
        self.opponent = opponent
        self.observation_encoder = observation_encoder or StandardEncoder()
        self.reward_engine = reward_engine or DefaultRewardEngine()

        self.optimizer = torch.optim.Adam(self.network.parameters(), lr=lr)
        self.policy = Policy(self.network, self.observation_encoder,
                              motore=None, device=device)

        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.value_coef = value_coef
        self.entropy_coef = entropy_coef
        self.update_epochs = update_epochs
        self.batch_size = batch_size
        self.device = device
        self.checkpoint_dir = checkpoint_dir

        self.episode_rewards = []
        self.episode_lengths = []
        self.best_winrate = 0.0

        os.makedirs(checkpoint_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Warm-start da pesi pre-allenati (imitation learning)
    # ------------------------------------------------------------------
    def load_pretrained_weights(self, path: str):
        """
        Carica pesi salvati da botRL/pretrain/imitation.py come punto di
        partenza della policy, invece di init casuale. Il value head viene
        caricato anche lui (i pesi ci sono, anche se non allenati in modo
        mirato durante l'imitation learning) e verrà rifinito rapidamente
        dal training PPO stesso.

        Solleva un errore chiaro se input_dim/hidden_dim non combaciano,
        invece di un cryptico shape-mismatch da load_state_dict.
        """
        checkpoint = torch.load(path, map_location=self.device)

        ckpt_input_dim = checkpoint.get("input_dim")
        ckpt_hidden_dim = checkpoint.get("hidden_dim")

        if ckpt_input_dim != self.network.input_dim or ckpt_hidden_dim != self.network.hidden_dim:
            raise ValueError(
                f"Checkpoint pre-allenato incompatibile con questa rete:\n"
                f"  checkpoint: input_dim={ckpt_input_dim}, hidden_dim={ckpt_hidden_dim}\n"
                f"  rete attuale: input_dim={self.network.input_dim}, hidden_dim={self.network.hidden_dim}\n"
                f"Assicurati che l'encoder e hidden_dim usati in imitation.py "
                f"combacino con quelli di PPOTrainer."
            )

        self.network.load_state_dict(checkpoint["state_dict"])
        print(f"✅ Pesi pre-allenati caricati da: {path}")
        print(f"   (imitava: {checkpoint.get('imitated_bot', '?')}, "
              f"{checkpoint.get('n_hands', '?')} smazzate di training)")

    # ------------------------------------------------------------------
    # Raccolta di UNA singola smazzata
    # ------------------------------------------------------------------
    def collect_rollout(self, env: ScopaEnvironment,
                         agent_idx: int = 0,
                         max_steps: int = 1000) -> RolloutBuffer:
        """
        Gioca UNA SINGOLA SMAZZATA (non l'intera partita a 11) e raccoglie
        la traiettoria. L'episodio finisce quando env segnala
        info["fine_smazzata"], non quando env.partita_finita.
        """
        buffer = RolloutBuffer(device=self.device)
        env.reset()

        step_count = 0
        hand_done = False

        while not hand_done and step_count < max_steps:
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

                next_obs, _, done, info = env.step(action, current_idx)
                hand_done = info.get("fine_smazzata", False) or done

                shaped_reward = self.reward_engine.compute_step_reward(
                    info=info,
                    observation=obs,
                    action=action,
                    next_observation=next_obs,
                    done=hand_done
                )

                buffer.add(
                    obs_vector=obs_vector,
                    action=action_idx.detach(),
                    action_mask=action_mask,
                    log_prob=log_prob.detach(),
                    reward=shaped_reward,
                    value=value.detach(),
                    done=hand_done
                )
            else:
                if self.opponent is not None:
                    azione = self.opponent.scegli_mossa(obs)
                else:
                    azione = self.policy.select_action(obs)

                next_obs, _, done, info = env.step(azione, current_idx)
                hand_done = info.get("fine_smazzata", False) or done

            step_count += 1

        if hand_done and len(buffer) > 0:
            # Observation fresca a fine mano (indipendentemente da chi ha
            # giocato l'ultima mossa): env è già completamente aggiornato,
            # punteggi inclusi.
            final_observation = env._get_observation(agent_idx)
            final_reward = self.reward_engine.compute_terminal_reward(final_observation)
            buffer.rewards[-1] += final_reward

        return buffer

    # ------------------------------------------------------------------
    # Update PPO su un buffer (eventualmente concatenazione di più mani)
    # ------------------------------------------------------------------
    def update_policy(self, buffer: RolloutBuffer) -> dict:
        obs, actions, masks, old_log_probs, rewards, values, dones = buffer.get_batch()
        values = values.view(-1)
        actions = actions.view(-1)

        advantages, returns = buffer.compute_advantages(
            rewards, values, dones, gamma=self.gamma, gae_lambda=self.gae_lambda
        )
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        n_samples = obs.shape[0]
        total_policy_loss = 0.0
        total_value_loss = 0.0
        n_updates = 0

        for _ in range(self.update_epochs):
            perm = torch.randperm(n_samples)
            for start in range(0, n_samples, self.batch_size):
                batch_idx = perm[start:start + self.batch_size]

                batch_obs = obs[batch_idx]
                batch_actions = actions[batch_idx]
                batch_masks = masks[batch_idx]
                batch_old_log_probs = old_log_probs[batch_idx].view(-1)
                batch_advantages = advantages[batch_idx]
                batch_returns = returns[batch_idx]

                new_log_probs, new_values, entropy = self.policy.evaluate_actions(
                    batch_obs, batch_actions, batch_masks
                )
                new_log_probs = new_log_probs.view(-1)
                new_values = new_values.view(-1)

                ratio = torch.exp(new_log_probs - batch_old_log_probs)
                surr1 = ratio * batch_advantages
                surr2 = torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * batch_advantages
                policy_loss = -torch.min(surr1, surr2).mean()

                value_loss = F.mse_loss(new_values, batch_returns)
                entropy_loss = -entropy.mean()

                loss = policy_loss + self.value_coef * value_loss + self.entropy_coef * entropy_loss

                self.optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.network.parameters(), max_norm=0.5)
                self.optimizer.step()

                total_policy_loss += policy_loss.item()
                total_value_loss += value_loss.item()
                n_updates += 1

        return {
            "policy_loss": total_policy_loss / max(n_updates, 1),
            "value_loss": total_value_loss / max(n_updates, 1),
        }

    # ------------------------------------------------------------------
    # Valutazione: winrate su n_games contro un opponent (di default,
    # quello di training; passandolo esplicito puoi valutare vs un bot
    # diverso, es. BotCasuale, come diagnostica indipendente).
    # ------------------------------------------------------------------
    def evaluate(self, n_games: int = 100, opponent=None) -> float:
        from cli.partita import PartitaCLI

        opponent = opponent or self.opponent or BotPredatore()

        old_deterministic = self.policy.deterministic
        self.policy.deterministic = True

        vittorie = 0
        for i in range(n_games):
            agent_idx = i % 2  # alterna chi gioca per primo
            bot_rl = self.policy
            giocatori = [bot_rl, opponent] if agent_idx == 0 else [opponent, bot_rl]

            partita = PartitaCLI(giocatori[0], giocatori[1])
            risultato = partita.gioca_silenziosa()

            if risultato["vincitore"] == agent_idx:
                vittorie += 1

        self.policy.deterministic = old_deterministic
        return vittorie / n_games

    # ------------------------------------------------------------------
    # Checkpoint
    # ------------------------------------------------------------------
    def save_checkpoint(self, filename: str, episode: int, winrate: float = None):
        path = os.path.join(self.checkpoint_dir, filename)
        torch.save({
            "network_state_dict": self.network.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "episode": episode,
            "winrate": winrate,
            "network_input_dim": self.network.input_dim,
            "network_hidden_dim": self.network.hidden_dim,
            "encoder_class": type(self.observation_encoder).__name__,
        }, path)
        print(f"💾 Checkpoint salvato: {path}")

    # ------------------------------------------------------------------
    # Loop principale di training
    # ------------------------------------------------------------------
    def train(self, n_episodes: int = 10000,
              eval_every: int = 500,
              n_eval_games: int = 50,
              save_every: int = 2000,
              log_every: int = 100,
              episodes_per_update: int = 100):
        env = ScopaEnvironment("RL_Bot", "Opponent")

        episode = 0
        while episode < n_episodes:
            combined_buffer = RolloutBuffer(device=self.device)

            for _ in range(episodes_per_update):
                if episode >= n_episodes:
                    break

                ep_buffer = self.collect_rollout(env, agent_idx=0)

                combined_buffer.obs_vectors.extend(ep_buffer.obs_vectors)
                combined_buffer.actions.extend(ep_buffer.actions)
                combined_buffer.action_masks.extend(ep_buffer.action_masks)
                combined_buffer.log_probs.extend(ep_buffer.log_probs)
                combined_buffer.rewards.extend(ep_buffer.rewards)
                combined_buffer.values.extend(ep_buffer.values)
                combined_buffer.dones.extend(ep_buffer.dones)

                episode += 1
                total_reward = sum(ep_buffer.rewards)
                self.episode_rewards.append(total_reward)
                self.episode_lengths.append(len(ep_buffer))

                if episode % log_every == 0:
                    avg_reward = sum(self.episode_rewards[-log_every:]) / min(log_every, len(self.episode_rewards))
                    avg_length = sum(self.episode_lengths[-log_every:]) / min(log_every, len(self.episode_lengths))
                    print(f"Ep {episode:5d} | Reward: {total_reward:7.2f} | "
                          f"Avg: {avg_reward:7.2f} | Len: {avg_length:3.0f}")

                if episode % eval_every == 0:
                    winrate = self.evaluate(n_games=n_eval_games)
                    winrate_casuale = self.evaluate(n_games=n_eval_games, opponent=BotCasuale())

                    print(f"\n{'=' * 60}")
                    print(f"EVALUATION Episode {episode}")
                    print(f"Winrate vs Opponent (training): {winrate:.1%}")
                    print(f"Winrate vs Casuale (diagnostica): {winrate_casuale:.1%}")
                    print(f"{'=' * 60}\n")

                    if winrate > self.best_winrate:
                        self.best_winrate = winrate
                        self.save_checkpoint("best_model.pt", episode, winrate)
                        print(f"💾 Nuovo best model salvato! Winrate: {winrate:.1%}")

                if episode % save_every == 0:
                    self.save_checkpoint(f"checkpoint_{episode}.pt", episode)

            metrics = self.update_policy(combined_buffer)
            print(f"  → Update PPO su {len(combined_buffer)} campioni | "
                  f"Policy: {metrics['policy_loss']:.4f} | Value: {metrics['value_loss']:.4f}")

        print("\n✅ Training completato!")
        self.save_checkpoint("final_model.pt", episode)