# scopa/giocatore.py
from .carta import Carta


class Giocatore:
    """
    Rappresenta un giocatore (umano o bot).
    """

    def __init__(self, nome, tipo="umano"):
        self.nome = nome
        self.tipo = tipo          # "umano" o "bot"
        self.mano = []            # carte in mano
        self.prese = []           # carte prese durante la mano
        self.scope = 0            # contatore scope

    def reset(self):
        """Azzera tutto per una nuova partita."""
        self.mano = []
        self.prese = []
        self.scope = 0

    def ricevi_carte(self, carte):
        """Il mazziere dà carte al giocatore."""
        self.mano.extend(carte)
        # Ordina per seme e valore (comodo per leggere)
        self.mano.sort(key=lambda c: (c.seme, c.valore))

    def gioca_carta(self, carta):
        """
        Toglie una carta dalla mano e la restituisce.
        Lancia errore se la carta non c'è.
        """
        if carta not in self.mano:
            raise ValueError(f"{self.nome} non ha in mano {carta}!")
        self.mano.remove(carta)
        return carta

    def aggiungi_prese(self, carte, scopa=False):
        """Mette carte nelle prese e aumenta scope se necessario."""
        self.prese.extend(carte)
        if scopa:
            self.scope += 1

    def __str__(self):
        return f"{self.nome} ({self.tipo})"