# bot/Intelligente7.py
import random
from typing import Tuple, Optional, List, Set
from collections import defaultdict
from scopa.carta import Carta
from scopa.motore import MotoreScopa
from scopa.probabilita import (
    probabilita_almeno_una,
    calcola_parametri,
    conta_carte_per_valore,
)
from .base import BotAgent


class BotDEEPSEEK(BotAgent):
    """
    Bot avanzato per Scopa Bergamasca.
    Strategia:
      1. Scopa e Settebello hanno priorità assoluta.
      2. Valuta le prese in base a: 7 > Denari > numero carte > Primiera.
      3. Quando balla, sceglie la carta che rende il banco "morto"
         (senza possibilità di scopa) e che non aiuta l'avversario.
      4. Usa la memoria delle carte già uscite per decisioni più accurate.
    """

    def __init__(self, nome: str = "BotDEEPSEEK"):
        self._nome = nome
        self._carte_viste: Set[Tuple[str, int]] = set()
        self._smazzata_corrente: Optional[int] = None

    def nome(self) -> str:
        return self._nome

    # ------------------------------------------------------------------
    # MEMORIA
    # ------------------------------------------------------------------

    def _aggiorna_memoria(self, obs: dict):
        mano = obs.get("mano_corrente", 1)
        if mano != self._smazzata_corrente:
            self._smazzata_corrente = mano
            self._carte_viste = set()

        for chiave in ("mano", "banco", "prese_mie", "prese_avversario"):
            for c in obs.get(chiave, []):
                self._carte_viste.add((c.seme, c.valore))

    def _carta_uguale(self, c1: Carta, c2: Carta) -> bool:
        return c1.seme == c2.seme and c1.valore == c2.valore

    # ------------------------------------------------------------------
    # UTILITY
    # ------------------------------------------------------------------

    def _peso_carta(self, carta: Carta) -> int:
        """
        Peso per valutare le carte prese:
        - Settebello: 1000
        - 7 (non settebello): 500
        - Denari: 200
        - Altre: valore * 10 (così le carte alte valgono di più)
        """
        if carta.is_settebello():
            return 1000
        if carta.valore == 7:
            return 500
        if carta.seme.lower() == "denari":
            return 200
        return carta.valore * 10

    def _valore_primiera(self, prese: List[Carta]) -> int:
        """Calcola il punteggio Primiera delle carte prese (0 se manca un seme)."""
        from scopa.costanti import SEMI, PRIMIERA_VALORI
        migliori = {}
        for c in prese:
            vp = PRIMIERA_VALORI[c.valore]
            if c.seme not in migliori or vp > migliori[c.seme]:
                migliori[c.seme] = vp
        if len(migliori) < 4:
            return 0
        return sum(migliori.values())

    def _prob_avversario_ha_valore(self, observation: dict, valore: int) -> float:
        """Probabilità che l'avversario abbia almeno una carta di questo valore."""
        note, n_mano_avversario, carte_mazzo = calcola_parametri(observation)
        n_sconosciute = carte_mazzo + n_mano_avversario
        carte_passate = conta_carte_per_valore(note)
        rimanenti = 4 - carte_passate.get(valore, 0)
        if rimanenti <= 0:
            return 0.0
        return probabilita_almeno_una(rimanenti, n_sconosciute, n_mano_avversario)

    def _rischio_scopa(self, banco: List[Carta], observation: dict) -> float:
        """
        Stima la probabilità che l'avversario possa fare scopa sul banco attuale.
        Considera solo le carte che l'avversario potrebbe avere (sconosciute).
        """
        if not banco:
            return 0.0
        sconosciute = observation.get("sconosciute", [])
        max_prob = 0.0
        for carta in sconosciute:
            prese = MotoreScopa.trova_tutte_prese_legali(banco, carta)
            for p in prese:
                if len(p) == len(banco):
                    prob = self._prob_avversario_ha_valore(observation, carta.valore)
                    max_prob = max(max_prob, prob)
        return max_prob

    # ------------------------------------------------------------------
    # SCELTA MOSSA
    # ------------------------------------------------------------------

    def scegli_mossa(self, observation: dict) -> Tuple[Carta, Optional[List[Carta]]]:
        self._aggiorna_memoria(observation)

        azioni = observation["azioni_legali"]
        banco = observation["banco"]

        if not azioni:
            raise ValueError("Nessuna azione legale!")

        # 1) SCOPA (priorità assoluta)
        scope = [a for a in azioni if a[1] is not None and len(a[1]) == len(banco)]
        if scope:
            return scope[0]

        # 2) SETTEBELLO (priorità assoluta)
        settebello = [
            a for a in azioni
            if a[1] is not None and any(c.is_settebello() for c in a[1] + [a[0]])
        ]
        if settebello:
            return settebello[0]

        azioni_prese = [a for a in azioni if a[1] is not None]
        azioni_balla = [a for a in azioni if a[1] is None]

        # ==============================================================
        # 3) PRESE
        # ==============================================================
        if azioni_prese:
            candidati = []
            for azione in azioni_prese:
                carta, prese = azione
                banco_dopo = [c for c in banco if not any(self._carta_uguale(c, p) for p in prese)]
                carte_totali = prese + [carta]

                punteggio = 0

                # --- Peso intrinseco delle carte prese ---
                for c in carte_totali:
                    punteggio += self._peso_carta(c)

                # --- Bonus per numero di carte prese ---
                punteggio += len(carte_totali) * 5

                # --- Bonus per migliorare la Primiera ---
                prese_mie_attuali = observation.get("prese_mie", [])
                primiera_attuale = self._valore_primiera(prese_mie_attuali)
                primiera_futura = self._valore_primiera(prese_mie_attuali + carte_totali)
                if primiera_futura > primiera_attuale:
                    punteggio += (primiera_futura - primiera_attuale) * 2

                # --- Penalità per rischio scopa sul banco residuo ---
                rischio = self._rischio_scopa(banco_dopo, observation)
                if rischio > 0.6:
                    punteggio -= 200
                elif rischio > 0.3:
                    punteggio -= 80

                # --- Bonus se il banco residuo è "morto" ---
                # (nessuna possibilità di scopa e somma non più presente)
                if banco_dopo and self._rischio_scopa(banco_dopo, observation) == 0:
                    somma = sum(c.valore for c in banco_dopo)
                    valori_esistenti = set()
                    for c in observation.get("sconosciute", []):
                        valori_esistenti.add(c.valore)
                    if somma not in valori_esistenti:
                        punteggio += 150

                candidati.append((punteggio, azione))

            candidati.sort(key=lambda x: x[0], reverse=True)
            return candidati[0][1]

        # ==============================================================
        # 4) BALLA
        # ==============================================================
        if azioni_balla:
            candidati = []
            for azione in azioni_balla:
                carta = azione[0]
                banco_dopo = banco + [carta]

                punteggio = 0

                # --- Penalità per carte preziose (Denari e 7) ---
                if carta.seme.lower() == "denari":
                    punteggio -= 100
                if carta.valore == 7:
                    punteggio -= 150
                # Preferiamo carte alte (più difficili da prendere)
                punteggio += carta.valore * 2

                # --- Rischio scopa dopo la balla ---
                rischio = self._rischio_scopa(banco_dopo, observation)
                if rischio > 0.5:
                    punteggio -= 300
                elif rischio > 0.2:
                    punteggio -= 100

                # --- Bonus: rendere il banco "morto" ---
                if banco_dopo and self._rischio_scopa(banco_dopo, observation) == 0:
                    somma = sum(c.valore for c in banco_dopo)
                    valori_esistenti = set()
                    for c in observation.get("sconosciute", []):
                        valori_esistenti.add(c.valore)
                    if somma not in valori_esistenti:
                        punteggio += 200

                # --- Evitare di dare carte che l'avversario può prendere subito ---
                prob_avv_ha_stesso = self._prob_avversario_ha_valore(observation, carta.valore)
                if prob_avv_ha_stesso > 0.5:
                    punteggio -= 100 * prob_avv_ha_stesso

                candidati.append((punteggio, azione))

            candidati.sort(key=lambda x: x[0], reverse=True)
            return candidati[0][1]

        # Fallback (non dovrebbe mai succedere)
        return random.choice(azioni)