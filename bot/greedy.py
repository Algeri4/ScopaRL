import random
from typing import Tuple, Optional, List
from scopa.carta import Carta
from .base import BotAgent


class BotGreedy(BotAgent):
    """
    Bot euristico con priorità:
    1) Scopa (se può svuotare il banco)
    2) Prende Settebello
    3) Prende un 7 (utile per Primiera)
    4) Prende Denari
    5) Carta balla con valore più alto (per non lasciare carte basse facili)
    """

    def __init__(self, nome: str = "BotGreedy"):
        self._nome = nome

    def nome(self) -> str:
        return self._nome

    def scegli_mossa(self, observation: dict) -> Tuple[Carta, Optional[List[Carta]]]:
        azioni = observation["azioni_legali"]
        banco = observation["banco"]

        if not azioni:
            raise ValueError("Nessuna azione legale!")

        candidati = []

        for azione in azioni:
            carta, prese = azione
            punteggio = 0

            if prese is None:
                # Carta balla: penalizziamo leggermente, ma preferiamo carte alte
                # (più difficili da prendere per l'avversario)
                punteggio = carta.valore * 0.5
                candidati.append((punteggio, azione))
                continue

            # --- È una presa: valutiamo ---
            carte_totali = prese + [carta]

            # 1) Scopa? Se prese copre tutto il banco attuale
            if len(prese) == len(banco):
                punteggio += 1000  # MASSIMA priorità

            # 2) Carte prese
            for c in carte_totali:
                if c.is_settebello():
                    punteggio += 100
                elif c.valore == 7:
                    punteggio += 50
                elif c.seme == "Denari":
                    punteggio += 20
                elif c.valore == 10:  # Re
                    punteggio += 5

            candidati.append((punteggio, azione))

        # Ordina per punteggio decrescente
        candidati.sort(key=lambda x: x[0], reverse=True)
        return candidati[0][1]
