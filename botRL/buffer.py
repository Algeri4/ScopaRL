"""
botRL/buffer.py
Buffer PPO
"""

import torch
from typing import List, Tuple


class RolloutBuffer:
    def __init__(self, device='cpu'):
        self.device = device
        self.clear()

    def clear(self):
        self.obs_vectors = []
        self.actions = []
        self.action_masks = []
        self.log_probs = []
        self.rewards = []
        self.values = []
        self.dones = []

    def add(self, obs_vector, action, action_mask, log_prob, reward, value, done):
        self.obs_vectors.append(obs_vector)
        self.actions.append(action)
        self.action_masks.append(action_mask)
        self.log_probs.append(log_prob)
        self.rewards.append(reward)
        self.values.append(value)
        self.dones.append(done)

    def get_batch(self) -> Tuple:
        obs = torch.stack(self.obs_vectors)
        actions = torch.stack(self.actions)
        masks = torch.stack(self.action_masks)
        log_probs = torch.stack(self.log_probs)
        rewards = torch.tensor(self.rewards, dtype=torch.float32, device=self.device)
        values = torch.stack(self.values)
        dones = torch.tensor(self.dones, dtype=torch.float32, device=self.device)

        return obs, actions, masks, log_probs, rewards, values, dones

    def compute_advantages(self, rewards, values, dones, gamma=0.99, gae_lambda=0.95):
        T = len(rewards)
        advantages = torch.zeros(T, device=self.device)
        last_gae = 0

        # Assicura values 1D
        values = values.view(-1)

        for t in reversed(range(T)):
            if t == T - 1:
                next_value = 0
            else:
                next_value = values[t + 1]

            if dones[t]:
                next_value = 0

            delta = rewards[t] + gamma * next_value - values[t]
            advantages[t] = last_gae = delta + gamma * gae_lambda * (1 - dones[t]) * last_gae

        returns = advantages + values

        # Normalizza advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # Assicura shape 1D
        advantages = advantages.view(-1)
        returns = returns.view(-1)

        return advantages, returns

    def __len__(self):
        return len(self.rewards)