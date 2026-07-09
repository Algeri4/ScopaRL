# bot/Intelligente6.py
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
from scopa.costanti import SEMI
from .base import BotAgent


class BotQWEN(BotAgent):
    """
    BotQWEN (Intelligente6) - L'evoluzione definitiva.

    FILOSOFIA: "Controllo Deterministico + Inferenza Statistica".
    Non ci affidiamo solo alle probabilità (che possono ingannare),
    ma cerchiamo la CERTEZZA MATEMATICA (Banco Morto).
    Usiamo le probabilità e l'inferenza solo per scegliere la migliore
    tra le opzioni sicure, o per minimizzare il danno quando siamo costretti a rischiare.

    PILASTRI STRATEGICI:
    1. BANCO MORTO ASSOLUTO: Se la somma del banco > 10, o se le carte
       per quella somma sono finite, il banco è "morto". Bonus enorme.
    2. INFERENZA PULITA: Se l'avversario balla, sappiamo che NON ha i valori
       delle carte sul banco. Questo non altera il conteggio del mazzo,
       ma azzera le probabilità locali per quei valori.
    3. PRIMIERA ATTIVA: Non guardiamo solo i 7. Se ci manca un seme,
       prendere una carta di quel seme vale oro.
    4. NESSUNA "ATTESA FORZATA": Nella Scopa, passare l'iniziativa è un errore.
       Giochiamo sempre per il controllo immediato del tavolo.
    """

    def __init__(self, nome: str = "BotQWEN"):
        self._nome = nome

        # --- STATO E MEMORIA ---
        self._smazzata_corrente: Optional[int] = None
        self._conteggio_uscite: Dict[int, int] = defaultdict(int)  # Carte viste globalmente
        self._valori_esclusi_avv: Set[int] = set()  # Valori che l'avversario SICURAMENTE non ha
        self._mosse_avv_processate: int = 0

    def nome(self) -> str:
        return self._nome

    # ======================================================================
    # GESTIONE MEMORIA E INFERENZA
    # ======================================================================
    def _aggiorna_stato(self, obs: dict):
        """Aggiorna il conteggio carte e l'inferenza ad ogni turno."""
        mano = obs.get("mano_corrente", 1)

        # Reset a ogni nuova smazzata
        if mano != self._smazzata_corrente:
            self._smazzata_corrente = mano
            self._conteggio_uscite = defaultdict(int)
            self._valori_esclusi_avv = set()
            self._mosse_avv_processate = 0

        # 1. Aggiorna conteggio globale (carte viste sul tavolo, prese, mano)
        for chiave in ("mano", "banco", "prese_mie", "prese_avversario"):
            for c in obs.get(chiave, []):
                self._conteggio_uscite[c.valore] += 1

        # 2. Inferenza dalle mosse avversario
        storico = obs.get("storico", [])
        giocatore_idx = obs.get("giocatore_idx", 0)
        avversario_idx = 1 - giocatore_idx

        mosse_avv = [m for m in storico if m.get("turno") == avversario_idx]

        # Analizza solo le mosse nuove
        for mossa in mosse_avv[self._mosse_avv_processate:]:
            self._inferisci_da_mossa(mossa)
        self._mosse_avv_processate = len(mosse_avv)

    def _inferisci_da_mossa(self, mossa: dict):
        """
        INFERENZA: Se l'avversario balla, non aveva carte dei valori
        presenti sul banco in quel momento (altrimenti la regola
        dell'obbligo di presa singola lo avrebbe costretto a prendere).
        """
        prese = mossa.get("prese", [])
        banco_prima = mossa.get("banco_prima", [])

        if not prese:  # L'avversario ha BALLATO
            for carta in banco_prima:
                # L'avversario NON ha questo valore.
                # Lo aggiungiamo al set delle esclusioni.
                self._valori_esclusi_avv.add(carta.valore)

    # ======================================================================
    # CALCOLO PROBABILITÀ "INTELLIGENTE" (con inferenza)
    # ======================================================================
    def _prob_avv_ha_valore(self, obs: dict, valore: int) -> float:
        """
        Probabilità che l'avversario abbia almeno 1 carta di un dato valore.
        Se l'inferenza ci dice che SICURAMENTE non ce l'ha, ritorna 0.0.
        """
        if valore in self._valori_esclusi_avv:
            return 0.0

        note, n_mano_avv, carte_mazzo = calcola_parametri(obs)
        n_sconosciute = carte_mazzo + n_mano_avv
        if n_sconosciute <= 0:
            return 0.0

        rimanenti = 4 - self._conteggio_uscite.get(valore, 0)
        if rimanenti <= 0:
            return 0.0

        return probabilita_almeno_una(rimanenti, n_sconosciute, n_mano_avv)

    # ======================================================================
    # VALUTAZIONE DEL BANCO (Il cuore strategico)
    # ======================================================================
    def _is_banco_morto(self, banco: List[Carta]) -> bool:
        """
        Un banco è "MORTO" se l'avversario non può matematicamente scoparlo.
        Questo accade se:
        1. La somma delle carte > 10 (nessuna carta può raggiungere quella somma).
        2. La somma <= 10, ma tutte le 4 carte di quel valore sono già uscite.
        """
        if not banco:
            return True

        somma = sum(c.valore for c in banco)
        if somma > 10:
            return True  # Regola d'oro della Scopa!

        # Se la somma è <= 10, controlla se le carte per quella somma sono finite
        rimanenti_per_somma = 4 - self._conteggio_uscite.get(somma, 0)
        return rimanenti_per_somma <= 0

    def _calcola_rischio_banco(self, banco: List[Carta], obs: dict) -> float:
        """
        Calcola il "danno atteso" se l'avversario gioca sul banco attuale.
        Usato come spareggio o per valutare le opzioni rischiose.
        """
        if not banco:
            return 0.0

        danno_totale = 0.0
        for valore in range(1, 11):
            prob = self._prob_avv_ha_valore(obs, valore)
            if prob <= 0:
                continue

            carta_fittizia = Carta("denari", valore)
            prese = MotoreScopa.trova_tutte_prese_legali(banco, carta_fittizia)
            if not prese:
                continue

            # L'avversario sceglie la presa che fa più male a noi
            max_danno = 0.0
            for p in prese:
                danno = len(p) * 10  # Carte perse
                if len(p) == len(banco):
                    danno += 500  # SCOPA (danno enorme)
                for c in p:
                    if c.is_settebello():
                        danno += 200
                    elif c.valore == 7:
                        danno += 50
                    elif c.seme == "denari":
                        danno += 30
                max_danno = max(max_danno, danno)

            danno_totale += prob * max_danno

        return danno_totale

    # ======================================================================
    # VALUTAZIONE PRIMIERA
    # ======================================================================
    def _valuta_guadagno_primiera(self, carte_prese: List[Carta], obs: dict) -> float:
        """
        Calcola quanto queste carte migliorano la nostra Primiera.
        Bonus enorme se completiamo un seme mancante.
        """
        prese_mie = obs.get("prese_mie", [])

        # Migliori carte attuali per seme
        migliori_attuali = {}
        for c in prese_mie:
            vp = c.valore_primiera()
            if c.seme not in migliori_attuali or vp > migliori_attuali[c.seme]:
                migliori_attuali[c.seme] = vp

        # Simula aggiunta
        migliori_simulati = dict(migliori_attuali)
        for c in carte_prese:
            vp = c.valore_primiera()
            if c.seme not in migliori_simulati or vp > migliori_simulati[c.seme]:
                migliori_simulati[c.seme] = vp

        bonus = 0.0
        semi_attuali = set(migliori_attuali.keys())
        semi_simulati = set(migliori_simulati.keys())

        # Completamento seme mancante (Bonus MASSICCIO)
        semi_mancanti = set(SEMI) - semi_attuali
        for seme in semi_mancanti:
            if seme in semi_simulati:
                bonus += 400.0

                # Miglioramento seme esistente
        for seme in SEMI:
            if seme in migliori_simulati and seme in migliori_attuali:
                if migliori_simulati[seme] > migliori_attuali[seme]:
                    bonus += (migliori_simulati[seme] - migliori_attuali[seme]) * 8.0

        return bonus

    # ======================================================================
    # SCELTA DELLA MOSSA (Il cervello)
    # ======================================================================
    def scegli_mossa(self, observation: dict) -> Tuple[Carta, Optional[List[Carta]]]:
        self._aggiorna_stato(observation)

        azioni = observation["azioni_legali"]
        banco = observation["banco"]

        if not azioni:
            raise ValueError("Nessuna azione legale!")

        # 1. SCOPA: Priorità assoluta
        scope = [a for a in azioni if a[1] is not None and len(a[1]) == len(banco)]
        if scope:
            return scope[0]

        # 2. SETTEBELLO: Priorità assoluta
        settebello = [
            a for a in azioni
            if a[1] is not None and any(c.is_settebello() for c in a[1] + [a[0]])
        ]
        if settebello:
            return settebello[0]

        # Separa prese e balla
        azioni_prese = [a for a in azioni if a[1] is not None]
        azioni_balla = [a for a in azioni if a[1] is None]

        candidati = []

        # ==================================================================
        # VALUTAZIONE PRESE
        # ==================================================================
        for carta, prese in azioni_prese:
            score = 0.0
            carte_totali = prese + [carta]
            banco_dopo = [c for c in banco if c not in prese]

            # A. Valore intrinseco delle carte prese
            for c in carte_totali:
                if c.valore == 7 and not c.is_settebello():
                    score += 150.0
                elif c.seme == "denari":
                    score += 60.0
                elif c.valore == 10:
                    score += 20.0
            score += len(carte_totali) * 15.0

            # B. Primiera Attiva
            score += self._valuta_guadagno_primiera(carte_totali, observation)

            # C. Controllo del Banco (Il vero differenziale)
            if not banco_dopo:
                score += 1000.0  # È una scopa, già gestita, ma comunque ottimo
            elif self._is_banco_morto(banco_dopo):
                score += 800.0  # Banco Morto! Sicurezza matematica.
            else:
                # Se il banco non è morto, calcola il rischio e penalizza
                rischio = self._calcola_rischio_banco(banco_dopo, observation)
                score -= rischio * 0.8  # Penalità proporzionale al danno atteso

                # Bonus se lasciamo una somma che l'avversario SICURAMENTE non ha (Inferenza)
                somma_banco = sum(c.valore for c in banco_dopo)
                if somma_banco in self._valori_esclusi_avv:
                    score += 300.0

                    # D. Valore della carta giocata (preferisci carte alte per non lasciarle in giro)
            score += carta.valore * 2.0

            candidati.append((score, (carta, prese)))

        # ==================================================================
        # VALUTAZIONE BALLA (Se non ci sono prese, o se le prese sono troppo rischiose)
        # ==================================================================
        for carta in [a[0] for a in azioni_balla]:
            score = -100.0  # Penalità base per il ballare (perdita di iniziativa)
            banco_dopo = banco + [carta]

            # A. Controllo del Banco
            if self._is_banco_morto(banco_dopo):
                score += 800.0  # Banco Morto anche in balla!
            else:
                rischio = self._calcola_rischio_banco(banco_dopo, observation)
                score -= rischio * 1.2  # Penalità più alta per la balla

                # Inferenza: se lasciamo una somma che l'avversario non ha
                somma_banco = sum(c.valore for c in banco_dopo)
                if somma_banco in self._valori_esclusi_avv:
                    score += 300.0

            # B. Sicurezza intrinseca della carta
            # Se l'avversario non ha il valore di questa carta, è una balla più sicura
            if carta.valore in self._valori_esclusi_avv:
                score += 150.0

            # C. Carte alte sono migliori da ballare (più difficili da sommare)
            if carta.valore >= 8:
                score += (carta.valore - 7) * 20.0

            # D. Non ballare mai Denari o 7 se puoi evitarlo
            if carta.seme == "denari": score -= 100.0
            if carta.valore == 7: score -= 150.0

            candidati.append((score, (carta, None)))

        # ==================================================================
        # SELEZIONE FINALE
        # ==================================================================
        if not candidati:
            return random.choice(azioni)

        # Ordina per punteggio decrescente
        candidati.sort(key=lambda x: x[0], reverse=True)

        # Se il migliore è una presa, prendila (a meno che il rischio non sia assurdo,
        # ma il nostro scoring già bilancia).
        # Se il migliore è una balla con Banco Morto, falla.

        return candidati[0][1]