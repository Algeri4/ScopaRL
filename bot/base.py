from abc import ABC, abstractmethod
from typing import Tuple, Optional, List
from scopa.carta import Carta


class BotAgent(ABC):
    """
    Interfaccia base per ogni giocatore artificiale.
    Tutti i bot (casuale, greedy, RL) devono implementare questi due metodi.
    """

    @abstractmethod
    def nome(self) -> str:
        """Ritorna il nome del bot (per la CLI)."""
        pass

    @abstractmethod
    def scegli_mossa(self, observation: dict) -> Tuple[Carta, Optional[List[Carta]]]:
        """
        Ritorna un'azione legale: (Carta_da_giocare, [carte_da_prendere] oppure None).
        observation è il dizionario che ritorna env._get_observation().
        """
        pass
