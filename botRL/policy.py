"""
botRL/policy.py
Wrapper della policy che gestisce:
  - Conversione observation -> input NN (delegata a un ObservationEncoder)
  - Scelta delle prese (deterministica o con euristica)
  - Interfaccia con il motore della Scopa

IMPORTANTE: la policy NON usa più ObservationBuilder.to_vector direttamente.
Usa sempre l'ObservationEncoder che le viene iniettato nel costruttore, sia
in training che in inferenza (partite vere). Questo garantisce che la rete
riceva sempre lo stesso tipo di input con cui è stata allenata, qualsiasi
encoder sia stato scelto.
"""

import torch
import random
from typing import Tuple, Optional, List
from scopa.carta import Carta
from scopa.motore import MotoreScopa
from .rete import ScopaNetwork, carta_to_idx, idx_to_carta, build_action_mask
from .observation_encoder import ObservationEncoder, StandardEncoder


class ScopaPolicy:
    """
    Policy che wrappa la rete neurale.

    Logica:
      1. L'encoder trasforma observation -> vettore
      2. La rete outputta logits per le 40 carte
      3. Mascheriamo solo le carte in mano
      4. Campioniamo la carta da giocare
      5. Il motore calcola le prese legali per quella carta
      6. Se multiple prese, usiamo euristica greedy per scegliere
    """

    def __init__(self, network: ScopaNetwork,
                 encoder: ObservationEncoder = None,
                 device='cpu',
                 deterministic: bool = False,
                 temperature: float = 1.0):
        """
        Args:
            network: istanza di ScopaNetwork
            encoder: ObservationEncoder da usare per convertire observation -> vettore.
                     Se None, usa StandardEncoder (comportamento di prima).
            device: 'cpu' o 'cuda'
            deterministic: se True, prende sempre l'azione migliore (no sampling)
            temperature: >1 = più esplorazione, <1 = più exploitation
        """
        self.network = network.to(device)
        self.device = device
        self.deterministic = deterministic
        self.temperature = temperature
        self.motore = MotoreScopa()

        self.encoder = encoder or StandardEncoder()

        # Fail fast: se rete ed encoder non sono compatibili è un errore di
        # configurazione, meglio scoprirlo subito che a runtime con NaN strani.
        if self.network.input_dim != self.encoder.input_dim:
            raise ValueError(
                f"Rete e encoder incompatibili: network.input_dim={self.network.input_dim} "
                f"!= encoder.input_dim={self.encoder.input_dim} "
                f"(encoder={type(self.encoder).__name__})"
            )

    def select_action(self, observation: dict,
                       return_tensors: bool = False) -> Tuple:
        """
        Seleziona un'azione dato lo stato di gioco.

        Args:
            observation: dict da ObservationBuilder
            return_tensors: se True, ritorna anche log_prob e value (per training)

        Returns:
            action: (Carta, Optional[List[Carta]]) - mossa da giocare
            (opzionale) log_prob, value per training
        """
        obs_vector = torch.tensor(
            self.encoder.encode(observation),
            dtype=torch.float32,
            device=self.device
        )

        mano = observation["mano"]
        action_mask = build_action_mask(mano, device=self.device)

        with torch.no_grad() if not self.network.training else torch.enable_grad():
            policy_logits, value = self.network(obs_vector)

            masked_logits = policy_logits.clone()
            if masked_logits.dim() == 2:
                masked_logits = masked_logits.squeeze(0)
            masked_logits[~action_mask] = -1e9
            if masked_logits.dim() == 1:
                masked_logits = masked_logits.unsqueeze(0)
            masked_logits = masked_logits / self.temperature
            probs = torch.softmax(masked_logits, dim=-1)

            if self.deterministic:
                action_idx = torch.argmax(probs, dim=-1)
            else:
                dist = torch.distributions.Categorical(probs)
                action_idx = dist.sample()

        seme, valore = idx_to_carta(action_idx.item())
        carta_scelta = Carta(seme, valore)

        if carta_scelta not in mano:
            # Fallback: non dovrebbe succedere con masking corretto
            print("QEUSTO NON SAREBBE MAI DOBUTO ESSER PRINTATO")
            carta_scelta = random.choice(mano)
            action_idx = torch.tensor(carta_to_idx(carta_scelta), device=self.device)

        banco = observation["banco"]
        prese_legali = self.motore.trova_tutte_prese_legali(banco, carta_scelta)

        if not prese_legali:
            prese = None
        elif len(prese_legali) == 1:
            prese = prese_legali[0]
        else:
            prese = self._scegli_migliore_preso(banco, prese_legali)

        action = (carta_scelta, prese)

        if return_tensors:
            log_prob = torch.distributions.Categorical(probs).log_prob(action_idx)
            return action, action_idx, log_prob, value.squeeze(-1)

        return action

    def _scegli_migliore_preso(self, banco, prese_legali: List[List[Carta]]) -> List[Carta]:
        """
        Euristica per scegliere tra multiple prese possibili.
        Priorità:
          1. Scopa (prende tutto il banco)
          2. Prende Settebello
          3. Prende 7
          4. Prende Denari
          5. Più carte prese
        """
        migliore = None
        miglior_punteggio = -float('inf')

        for prese in prese_legali:
            punteggio = 0

            if len(prese) == len(banco):
                punteggio += 10000

            for c in prese:
                if c.is_settebello():
                    punteggio += 500
                elif c.valore == 7:
                    punteggio += 200
                elif c.seme == "denari":
                    punteggio += 80
                elif c.valore == 10:
                    punteggio += 30

            punteggio += len(prese) * 10

            if punteggio > miglior_punteggio:
                miglior_punteggio = punteggio
                migliore = prese

        return migliore

    def evaluate_actions(self, obs_vectors: torch.Tensor,
                          actions: torch.Tensor,
                          action_masks: torch.Tensor) -> Tuple:
        """
        Valuta azioni per l'update PPO.

        Args:
            obs_vectors: (batch, input_dim)
            actions: (batch,) indici delle carte giocate
            action_masks: (batch, 40) maschere

        Returns:
            log_probs, values, entropy
        """
        policy_logits, values = self.network(obs_vectors)

        masked_logits = policy_logits.clone()
        masked_logits[~action_masks] = -1e9

        probs = torch.softmax(masked_logits, dim=-1)
        dist = torch.distributions.Categorical(probs)

        log_probs = dist.log_prob(actions)
        entropy = dist.entropy()

        return log_probs, values.squeeze(-1), entropy