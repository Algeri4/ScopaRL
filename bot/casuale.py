import random
from typing import Tuple, Optional, List
from scopa.carta import Carta
from .base import BotAgent


class BotCasuale(BotAgent):
    """Gioca mosse a caso tra quelle legali."""

    def __init__(self, nome: str = "BotCasuale"):
        self._nome = nome

    def nome(self) -> str:
        return self._nome

    def scegli_mossa(self, observation: dict) -> Tuple[Carta, Optional[List[Carta]]]:
        azioni = observation["azioni_legali"]
        if not azioni:
            raise ValueError("Nessuna azione legale!")
        return random.choice(azioni)
