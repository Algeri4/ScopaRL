"""
botRL/bot_rl.py
BotAgent che wrappa la rete neurale allenata con RL.
Implementa l'interfaccia BotAgent per compatibilità con PartitaCLI.
"""

import torch
from typing import Tuple, Optional, List
from scopa.carta import Carta
from bot.base import BotAgent
from .rete import ScopaNetwork, build_action_mask
from .policy import ScopaPolicy
from .observation_encoder import ObservationEncoder, StandardEncoder, crea_encoder


class BotRL(BotAgent):
    """
    Bot che usa una rete neurale allenata con PPO.

    Usage:
        network = ScopaNetwork()
        bot = BotRL(network, deterministic=True)

    Oppure, per caricare un checkpoint (ricostruisce automaticamente
    l'encoder e le dimensioni della rete usati durante il training):
        bot = BotRL.from_checkpoint("botRL/checkpoints/best_model.pt")
    """

    def __init__(self, network: ScopaNetwork,
                 observation_encoder: ObservationEncoder = None,
                 nome: str = "BotRL",
                 device: str = 'cpu',
                 deterministic: bool = True,
                 temperature: float = 1.0):
        """
        Args:
            network: rete neurale allenata
            observation_encoder: encoder usato per costruire l'input della rete.
                Deve essere lo STESSO usato in training, altrimenti la rete
                riceve un vettore diverso da quello per cui è stata allenata.
                Se None, usa StandardEncoder (comportamento di default).
            nome: nome del bot
            device: 'cpu' o 'cuda'
            deterministic: True = greedy, False = sampling
            temperature: temperatura per sampling (>1 = più esplorazione)
        """
        self._nome = nome
        self.device = device
        self.policy = ScopaPolicy(
            network,
            encoder=observation_encoder or StandardEncoder(),
            device=device,
            deterministic=deterministic,
            temperature=temperature
        )

    def nome(self) -> str:
        return self._nome

    def scegli_mossa(self, observation: dict) -> Tuple[Carta, Optional[List[Carta]]]:
        """
        Seleziona mossa dato lo stato.

        Args:
            observation: dict da ObservationBuilder

        Returns:
            (Carta, [prese] | None)
        """
        action = self.policy.select_action(observation)
        return action

    @classmethod
    def from_checkpoint(cls, checkpoint_path: str,
                         nome: str = "BotRL",
                         device: str = 'cpu',
                         deterministic: bool = True):
        """
        Crea un BotRL da un checkpoint salvato.

        Ricostruisce automaticamente:
          - le dimensioni della rete (network_input_dim / network_hidden_dim)
          - l'ObservationEncoder usato in training (encoder_class)
        leggendoli dai metadati salvati da PPOTrainer.save_checkpoint.

        Per checkpoint "vecchi" (salvati prima di questa modifica, senza
        questi metadati) fa fallback su ScopaNetwork(input_dim=209,
        hidden_dim=512) + StandardEncoder, cioè il comportamento originale.

        Args:
            checkpoint_path: path al file .pt
            nome: nome del bot
            device: 'cpu' o 'cuda'
            deterministic: modalità greedy o sampling

        Returns:
            BotRL istanziato
        """
        checkpoint = torch.load(checkpoint_path, map_location=device)

        input_dim = checkpoint.get('network_input_dim', 209)
        hidden_dim = checkpoint.get('network_hidden_dim', 512)
        encoder_class_name = checkpoint.get('encoder_class', 'StandardEncoder')

        try:
            encoder = crea_encoder(encoder_class_name)
        except ValueError:
            print(f"[WARN] Encoder '{encoder_class_name}' non trovato nel registro, "
                  f"uso StandardEncoder come fallback.")
            encoder = StandardEncoder()

        network = ScopaNetwork(input_dim=input_dim, hidden_dim=hidden_dim)
        network.load_state_dict(checkpoint['network_state_dict'])
        network.to(device)
        network.eval()

        return cls(network, observation_encoder=encoder, nome=nome,
                    device=device, deterministic=deterministic)