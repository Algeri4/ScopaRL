# scopa/mazzo.py
import random
from .carta import Carta
from .costanti import SEMI


class Mazzo:
    def __init__(self):
        self.carte = [Carta(s, v) for s in SEMI for v in range(1, 11)]
        random.shuffle(self.carte)

    def pesca(self, n=1):
        """
        Pesca n carte dal tallone.
        Se n=1 (default), ritorna UNA carta.
        Se n>1, ritorna una LISTA di carte.
        """
        if n == 1:
            return self.carte.pop()
        else:
            pescate = []
            for _ in range(n):
                pescate.append(self.carte.pop())
            return pescate

    def rimanenti(self):
        return len(self.carte)

    def rigenera(self):
        """Ricrea il mazzo da 40 carte e mischia."""
        self.carte = [Carta(s, v) for s in SEMI for v in range(1, 11)]
        random.shuffle(self.carte)