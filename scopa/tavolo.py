# scopa/tavolo.py
from .carta import Carta


class Tavolo:
    """
    Il banco: le carte scoperte al centro del tavolo.
    """

    def __init__(self):
        self.banco = []  # lista di Carta

    def reset(self):
        """Pulisce il tavolo."""
        self.banco = []

    def aggiungi(self, carte):
        """Mette carte sul banco."""
        self.banco.extend(carte)

    def rimuovi(self, carte):
        """Toglie carte dal banco (quando un giocatore le prende)."""
        for c in carte:
            if c in self.banco:
                self.banco.remove(c)

    def __str__(self):
        if not self.banco:
            return "Banco: VUOTO"
        return "Banco: " + ", ".join(str(c) for c in self.banco)