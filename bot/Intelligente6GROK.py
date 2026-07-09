# bot/grok_scopa.py
import random
from typing import Tuple, Optional, List
from scopa.carta import Carta
from bot.base import BotAgent
from scopa.probabilita import calcola_tutte_proabilita


class BotGROK(BotAgent):
    def __init__(self, nome: str = "BotGROK"):
        self._nome = nome

    def nome(self) -> str:
        return self._nome

    def _valore_carta(self, c: Carta) -> int:
        if c.is_settebello():
            return 1000
        if c.valore == 7:
            return 400
        if c.seme == "denari":
            return 150
        if c.valore == 10:  # Re
            return 80
        if c.valore >= 8:
            return 60
        return c.valore * 10

    def _valuta_presa(self, observation: dict, carta: Carta, prese: List[Carta]) -> float:
        banco = observation["banco"]
        carte_prese = prese + [carta]

        score = 0.0

        # SCOPA = priorità assoluta
        if len(prese) == len(banco):
            score += 10000

        # Valore diretto delle carte prese
        for c in carte_prese:
            score += self._valore_carta(c)

        # Bonus numero carte
        score += len(carte_prese) * 25

        # Penalità se lascio banco pericoloso per l'avversario
        banco_dopo = [c for c in banco if c not in prese]
        if banco_dopo:
            # Probabilità che avversario possa prendere qualcosa di buono
            probs = calcola_tutte_proabilita(observation)
            rischio = 0
            for c in banco_dopo:
                p = probs.get(c.valore, {}).get("probs", [0])[0]  # P(avversario ha almeno una)
                rischio += p * c.valore
            score -= rischio * 15

        return score

    def scegli_mossa(self, observation: dict) -> Tuple[Carta, Optional[List[Carta]]]:
        azioni = observation["azioni_legali"]
        if not azioni:
            raise ValueError("Nessuna azione legale!")

        azioni_prese = [a for a in azioni if a[1] is not None]
        azioni_balla = [a for a in azioni if a[1] is None]

        # Se posso prendere, valuto tutte le prese
        if azioni_prese:
            migliori = []
            for carta, prese in azioni_prese:
                val = self._valuta_presa(observation, carta, prese)
                migliori.append((val, (carta, prese)))

            migliori.sort(key=lambda x: x[0], reverse=True)
            return migliori[0][1]

        # === FASE BALLA ===
        # Preferisco ballare carte alte/difficili da prendere
        if azioni_balla:
            # Ordina per valore decrescente, ma con bonus se è denari o 7
            def balla_score(a):
                c = a[0]
                s = self._valore_carta(c) * 2
                # Bonus se lascio carta che avversario probabilmente NON ha
                probs = calcola_tutte_proabilita(observation)
                p_avv = probs.get(c.valore, {}).get("probs", [1.0])[0]
                s += (1 - p_avv) * 300
                return s

            azioni_balla.sort(key=balla_score, reverse=True)
            return azioni_balla[0]

        return azioni[0]  # fallback