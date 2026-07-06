"""
botRL/rete.py
Architettura della rete neurale per il bot RL della Scopa Bergamasca.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple


class ScopaNetwork(nn.Module):
    """
    Rete neurale per la Scopa Bergamasca.

    Architettura:
      - Input: input_dim elementi (dipende dall'ObservationEncoder usato)
      - Shared backbone: input_dim -> hidden_dim -> hidden_dim//2
      - Policy head: hidden_dim//2 -> 40 (logits per ogni carta)
      - Value head: hidden_dim//2 -> 1 (stima V(s))
    """

    def __init__(self, input_dim: int = 209, hidden_dim: int = 512):
        super().__init__()

        # NB: salviamo esplicitamente le dimensioni come attributi. Servono
        # per validare a runtime che la rete sia compatibile con l'encoder
        # scelto (assert network.input_dim == encoder.input_dim) e per
        # poterle salvare/ricaricare correttamente nei checkpoint.
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim

        # Shared backbone
        self.backbone = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.LayerNorm(hidden_dim // 2),
        )

        # Policy head: output per ogni carta (40 carte totali)
        self.policy_head = nn.Sequential(
            nn.Linear(hidden_dim // 2, 256),
            nn.ReLU(),
            nn.Linear(256, 40)  # 4 semi × 10 valori = 40 carte
        )

        # Value head: stima del valore dello stato
        self.value_head = nn.Sequential(
            nn.Linear(hidden_dim // 2, 256),
            nn.ReLU(),
            nn.Linear(256, 1)
        )

        self._init_weights()

    def _init_weights(self):
        """Inizializzazione Xavier per stabilità."""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, obs_vector: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass.

        Args:
            obs_vector: tensor shape (batch, input_dim) o (input_dim,)

        Returns:
            policy_logits: (batch, 40) o (40,)
            value: (batch, 1) o (1,)
        """
        if obs_vector.dim() == 1:
            obs_vector = obs_vector.unsqueeze(0)

        features = self.backbone(obs_vector)
        policy_logits = self.policy_head(features)
        value = self.value_head(features)

        return policy_logits, value

    def get_action_and_value(self, obs_vector: torch.Tensor,
                              action_mask: torch.Tensor,
                              action: torch.Tensor = None) -> Tuple:
        """
        Ottiene azione, log_prob, entropy e value.

        Args:
            obs_vector: stato
            action_mask: tensor bool (40,) True per carte in mano
            action: azione già scelta (per training), None per inference

        Returns:
            action: indice della carta scelta (0-39)
            log_prob: log probabilità dell'azione
            entropy: entropia della distribuzione
            value: stima V(s)
        """
        policy_logits, value = self.forward(obs_vector)

        masked_logits = policy_logits.clone()
        masked_logits[~action_mask] = -1e9

        probs = F.softmax(masked_logits, dim=-1)
        dist = torch.distributions.Categorical(probs)

        if action is None:
            action = dist.sample()

        log_prob = dist.log_prob(action)
        entropy = dist.entropy()

        return action, log_prob, entropy, value.squeeze(-1)


def carta_to_idx(carta) -> int:
    """
    Converte una Carta in indice 0-39.
    Ordine: per seme (bastoni, spade, coppe, denari), per valore (1-10).
    """
    semi = ["bastoni", "spade", "coppe", "denari"]
    seme_idx = semi.index(carta.seme)
    return seme_idx * 10 + (carta.valore - 1)


def idx_to_carta(idx: int):
    """Converte indice 0-39 in (seme, valore)."""
    semi = ["bastoni", "spade", "coppe", "denari"]
    seme_idx = idx // 10
    valore = (idx % 10) + 1
    return semi[seme_idx], valore


def build_action_mask(mano, device='cpu') -> torch.Tensor:
    """
    Crea maschera delle azioni legali.
    True per le carte che sono in mano.

    Args:
        mano: lista di Carta
        device: 'cpu' o 'cuda'

    Returns:
        mask: tensor bool (40,)
    """
    mask = torch.zeros(40, dtype=torch.bool, device=device)
    for carta in mano:
        mask[carta_to_idx(carta)] = True
    return mask