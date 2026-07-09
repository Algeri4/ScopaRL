# bot/bot_sintesi.py
import random
from typing import Tuple, Optional, List, Dict, Set
from collections import defaultdict
from scopa.carta import Carta
from scopa.motore import MotoreScopa
from scopa.probabilita import (
    probabilita_almeno_una,
    calcola_parametri,
    conta_carte_per_valore,
)
from .base import BotAgent


class BotKIMI(BotAgent):
    """
    Bot che sintetizza il meglio di Intelligente1/2/3 senza l'over-engineering
    di Intelligente4/5.

    Principi:
    1. SEMPLICE: solo feature che migliorano statisticamente
    2. ROBUSTO: niente inferenze speculative, niente simulazioni 1-step
    3. BILANCIATO: rischio calcolato ma non paralizzante
    4. AGGRESSIVO: quando sicuro, prende; quando rischioso, balla intelligente
    """

    def __init__(self, nome: str = "BotKIMI"):
        self._nome = nome
        # Memoria come Intelligente2 (funziona!)
        self._carte_viste: Set[Tuple[str, int]] = set()
        self._smazzata_corrente: Optional[int] = None
        # Conteggio esatto per valore (da Intelligente5, ma usato con cautela)
        self._conteggio_uscite: Dict[int, int] = defaultdict(int)

    def nome(self) -> str:
        return self._nome

    # ------------------------------------------------------------------
    # MEMORIA (esatta come Intelligente2 — funziona!)
    # ------------------------------------------------------------------

    def _aggiorna_memoria(self, obs: dict):
        mano = obs.get("mano_corrente", 1)
        if mano != self._smazzata_corrente:
            self._smazzata_corrente = mano
            self._carte_viste = set()
            self._conteggio_uscite = defaultdict(int)

        for chiave in ("mano", "banco", "prese_mie", "prese_avversario"):
            for c in obs.get(chiave, []):
                key = (c.seme, c.valore)
                if key not in self._carte_viste:
                    self._carte_viste.add(key)
                    self._conteggio_uscite[c.valore] += 1

    def _carta_uguale(self, c1: Carta, c2: Carta) -> bool:
        return c1.seme == c2.seme and c1.valore == c2.valore

    def _calcola_carte_rimanenti(self, valore: int) -> int:
        return 4 - self._conteggio_uscite.get(valore, 0)

    # ------------------------------------------------------------------
    # SICUREZZA (come Intelligente1 — funziona!)
    # ------------------------------------------------------------------

    def _avversario_puo_fare_scopa(self, banco: List[Carta], sconosciute: List[Carta]) -> bool:
        """True se una carta sconosciuta permette all'avversario di prendere TUTTO il banco."""
        if not banco:
            return False
        for carta in sconosciute:
            prese = MotoreScopa.trova_tutte_prese_legali(banco, carta)
            for p in prese:
                if len(p) == len(banco):
                    return True
        return False

    def _banco_morto(self, banco: List[Carta], sconosciute: List[Carta]) -> bool:
        """Il banco è 'morto' quando l'avversario non può più scopare."""
        if not banco:
            return True
        if self._avversario_puo_fare_scopa(banco, sconosciute):
            return False
        # Banco morto classico: somma = valore finito
        somma = sum(c.valore for c in banco)
        valori_sconosciuti = set(c.valore for c in sconosciute)
        return somma not in valori_sconosciuti

    # ------------------------------------------------------------------
    # RISCHIO PROBABILISTICO (semplificato da Intelligente3, NON continuo)
    # ------------------------------------------------------------------

    def _rischio_scopa(self, banco_dopo: List[Carta], observation: dict) -> float:
        """
        Calcola P(avversario fa scopa sul banco_dopo).
        Semplificato: SOLO per decidere se una presa è "sicura" o no.
        """
        if not banco_dopo or len(banco_dopo) < 2:
            return 0.0

        note, n_mano_avversario, carte_mazzo = calcola_parametri(observation)
        n_sconosciute = carte_mazzo + n_mano_avversario
        carte_passate = conta_carte_per_valore(note)

        rischio = 0.0
        for valore in range(1, 11):
            rimanenti = self._calcola_carte_rimanenti(valore)
            if rimanenti <= 0:
                continue
            prob = probabilita_almeno_una(rimanenti, n_sconosciute, n_mano_avversario)
            if prob > 0:
                carta_fittizia = Carta("denari", valore)
                prese = MotoreScopa.trova_tutte_prese_legali(banco_dopo, carta_fittizia)
                if any(len(p) == len(banco_dopo) for p in prese):
                    rischio = max(rischio, prob)

        return rischio

    # ------------------------------------------------------------------
    # VALUTAZIONE CARTE (classica, funzionale)
    # ------------------------------------------------------------------

    def _valore_carte(self, carte: List[Carta]) -> int:
        """Punteggio euristico di un gruppo di carte."""
        punteggio = 0
        for c in carte:
            if c.is_settebello():
                punteggio += 500
            elif c.valore == 7:
                punteggio += 200
            elif c.seme.lower() == "denari":
                punteggio += 80
            elif c.valore == 10:
                punteggio += 30
        punteggio += len(carte) * 10
        return punteggio

    def _valuta_primiera(self, carte_prese: List[Carta], observation: dict) -> float:
        """
        Quanto queste carte migliorano la primiera?
        SEMPLIFICATO: bonus solo per completare semi mancanti.
        """
        prese_mie = observation.get("prese_mie", [])

        # Semi già coperti
        semi_coperti = set()
        for c in prese_mie:
            semi_coperti.add(c.seme)

        # Semi che copriremmo con queste carte
        nuovi_semi = set(c.seme for c in carte_prese) - semi_coperti

        bonus = 0.0
        # Completare un seme mancante è CRITICO per primiera
        for seme in nuovi_semi:
            if seme not in semi_coperti:
                bonus += 300  # Da Intelligente5, ma solo questo

        # Migliorare seme esistente
        for c in carte_prese:
            if c.seme in semi_coperti:
                # Trova migliore attuale per questo seme
                attuale = max(
                    (cc.valore_primiera() for cc in prese_mie if cc.seme == c.seme),
                    default=0
                )
                if c.valore_primiera() > attuale:
                    bonus += (c.valore_primiera() - attuale) * 5

        return bonus

    # ------------------------------------------------------------------
    # SCELTA MOSSA PRINCIPALE
    # ------------------------------------------------------------------

    def scegli_mossa(self, observation: dict) -> Tuple[Carta, Optional[List[Carta]]]:
        self._aggiorna_memoria(observation)

        azioni = observation["azioni_legali"]
        banco = observation["banco"]
        sconosciute = observation.get("sconosciute", [])

        if not azioni:
            raise ValueError("Nessuna azione legale!")

        # 1) SCOVA: sempre
        scope = [a for a in azioni if a[1] is not None and len(a[1]) == len(banco)]
        if scope:
            # Scegli scopa con carte più preziose
            return max(scope, key=lambda a: self._valore_carte(a[1] + [a[0]]))

        # 2) SETTEBELLO: sempre
        settebello = [
            a for a in azioni
            if a[1] is not None and any(c.is_settebello() for c in a[1] + [a[0]])
        ]
        if settebello:
            return settebello[0]

        azioni_prese = [a for a in azioni if a[1] is not None]
        azioni_balla = [a for a in azioni if a[1] is None]

        # ==============================================================
        # 3) PRESE: sicurezza + valore, NON rischio continuo
        # ==============================================================
        prese_sicure = []
        prese_rischio = []

        for azione in azioni_prese:
            carta, prese = azione
            banco_dopo = [c for c in banco if not any(self._carta_uguale(c, p) for p in prese)]

            # Calcola rischio scopa
            rischio = self._rischio_scopa(banco_dopo, observation)

            punteggio = self._valore_carte(prese + [carta])
            punteggio += self._valuta_primiera(prese + [carta], observation)

            # Bonus banco morto (molto importante!)
            if self._banco_morto(banco_dopo, sconosciute):
                punteggio += 400

            if rischio < 0.3:
                prese_sicure.append((punteggio, azione, rischio))
            else:
                # Penalità SOGlia, non continua
                punteggio -= 200 if rischio > 0.5 else 100
                prese_rischio.append((punteggio, azione, rischio))

        # Scegli tra prese sicure se ce ne sono
        if prese_sicure:
            prese_sicure.sort(key=lambda x: x[0], reverse=True)
            return prese_sicure[0][1]

        # Se solo prese rischiose, scegli la meno peggio
        if prese_rischio:
            prese_rischio.sort(key=lambda x: (x[2], -x[0]))  # Min rischio, max valore
            return prese_rischio[0][1]

        # ==============================================================
        # 4) BALLA: intelligente ma semplice
        # ==============================================================
        candidati_balla = []

        for azione in azioni_balla:
            carta = azione[0]
            banco_dopo = banco + [carta]

            # Rischio che avversario prenda
            rischio = self._rischio_scopa(banco_dopo, observation)

            punteggio = carta.valore * 2  # Carte alte più sicure

            # Penalità carte importanti
            if carta.seme.lower() == "denari":
                punteggio -= 50
            if carta.valore == 7:
                punteggio -= 80

            # Penalità rischio con SOGLIE
            if rischio > 0.5:
                punteggio -= 300
            elif rischio > 0.2:
                punteggio -= 100

            # Bonus banco morto
            if self._banco_morto(banco_dopo, sconosciute):
                punteggio += 300

            # Se siamo SICURI che avversario non ha il valore → balla ottima
            if self._calcola_carte_rimanenti(carta.valore) == 0:
                punteggio += 200  # Non può prendere con stesso valore

            candidati_balla.append((punteggio, azione, rischio))

        if candidati_balla:
            # Prima: cerca balla senza rischio scopa
            sicure = [c for c in candidati_balla if c[2] == 0]
            if sicure:
                sicure.sort(key=lambda x: x[0], reverse=True)
                return sicure[0][1]

            # Altrimenti: minimo rischio possibile
            candidati_balla.sort(key=lambda x: (x[2], -x[0]))
            return candidati_balla[0][1]

        # Disperazione
        return random.choice(azioni)