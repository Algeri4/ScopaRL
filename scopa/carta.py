from .costanti import SEMI, NOMI_CARTE, PRIMIERA_VALORI, SETTEBELLO

class Carta:
    def __init__(self, seme, valore):
        assert seme in SEMI
        assert valore in [1,2,3,4,5,6,7,8,9,10]
        self.seme = seme
        self.valore = valore

    def __str__(self):
        return f"{NOMI_CARTE[self.valore]} di {self.seme}"

    def __eq__(self, other):
        return isinstance(other, Carta) and self.seme == other.seme and self.valore == other.valore

    def __hash__(self):
        return hash((self.seme, self.valore))

    def valore_primiera(self):
        return PRIMIERA_VALORI[self.valore]

    def is_settebello(self):
        return (self.seme, self.valore) == SETTEBELLO