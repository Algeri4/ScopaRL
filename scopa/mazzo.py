# scopa/mazzo.py
import random
from .carta import Carta
from .costanti import SEMI


class Mazzo:
    """
    NB: usa un'istanza PRIVATA di random.Random, non il modulo `random`
    globale. Così seedare una partita (es. per valutazione riproducibile)
    non altera il flusso di casualità di nessun'altra partita/episodio in
    corso altrove nel processo. Prima, ScopaEnvironment.reset(seed=...)
    chiamava random.seed(seed) sul modulo globale: questo significava che
    ogni valutazione (che usa sempre gli stessi seed 0..49) resettava lo
    stato pseudo-casuale globale allo stesso identico punto ogni volta,
    facendo sì che gli episodi di training subito dopo ogni valutazione
    rigiocassero le stesse identiche mani.
    """

    def __init__(self, rng: random.Random = None):
        self._rng = rng or random.Random()
        self.carte = [Carta(s, v) for s in SEMI for v in range(1, 11)]
        self._rng.shuffle(self.carte)

    def pesca(self, n=1):
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
        """Ricrea il mazzo da 40 carte e mischia (con l'RNG privato)."""
        self.carte = [Carta(s, v) for s in SEMI for v in range(1, 11)]
        self._rng.shuffle(self.carte)