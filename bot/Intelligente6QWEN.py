# bot/Campione.py
import random
from typing import Tuple, Optional, List, Dict
from scopa.carta import Carta
from scopa.motore import MotoreScopa
from scopa.costanti import SEMI
from .base import BotAgent


class BotQWEN(BotAgent):
    """
    BotCampione: Vincitore del Campionato Scopa Bergamasca.
    Filosofia: Memoria assoluta, creazione di "Banchi Morti",
    caccia spietata a Settebello e Primiera. Zero inferenze psicologiche.
    """

    def __init__(self, nome: str = "BotQWEN"):
        self._nome = nome
        self.carte_uscite: Dict[int, int] = {v: 0 for v in range(1, 11)}
        self._smazzata_corrente: Optional[int] = None

    def nome(self) -> str:
        return self._nome

    # ------------------------------------------------------------------
    # MEMORIA ASSOLUTA (Card Counting)
    # ------------------------------------------------------------------
    def _aggiorna_memoria(self, obs: dict):
        mano = obs.get("mano_corrente", 1)
        if mano != self._smazzata_corrente:
            self._smazzata_corrente = mano
            self.carte_uscite = {v: 0 for v in range(1, 11)}

        # Conta TUTTE le carte visibili (mano, banco, prese di entrambi)
        note = []
        for k in ("mano", "banco", "prese_mie", "prese_avversario"):
            note.extend(obs.get(k, []))

        for c in note:
            self.carte_uscite[c.valore] += 1

    def _rimanenti(self, valore: int) -> int:
        """Quante carte di questo valore sono ancora 'sconosciute' (mazzo + mano avv)."""
        return max(0, 4 - self.carte_uscite.get(valore, 0))

    # ------------------------------------------------------------------
    # LOGICA DEL "BANCO MORTO" (Il segreto della vittoria)
    # ------------------------------------------------------------------
    def _has_subset_sum(self, banco: List[Carta], target: int) -> bool:
        """Verifica se esiste una combinazione di carte sul banco che somma a 'target'."""
        n = len(banco)
        # Ottimizzazione: se la somma totale è minore di target, impossibile
        if sum(c.valore for c in banco) < target:
            return False

        # bitmask per controllare tutti i sottoinsiemi (max 2^10 = 1024, istantaneo)
        for i in range(1, 1 << n):
            current_sum = 0
            for j in range(n):
                if (i & (1 << j)):
                    current_sum += banco[j].valore
            if current_sum == target:
                return True
        return False

    def _is_banco_morto(self, banco: List[Carta]) -> bool:
        """
        Un banco è MORTO se l'avversario non può fisicamente mangiare nulla.
        Cioè: per ogni valore V ancora in circolazione (rimanenti > 0),
        NON esiste nessuna combinazione sul banco che sommi a V.
        """
        if not banco:
            return True

        for v in range(1, 11):
            if self._rimanenti(v) > 0:
                # Se esiste almeno un valore in circolazione che può essere
                # combinato con le carte sul banco, il banco è VIVO.
                if self._has_subset_sum(banco, v):
                    return False
        return True

    def _calcola_rischio_banco(self, banco: List[Carta]) -> float:
        """
        Se il banco è vivo, calcola quanto è pericoloso.
        Penalità basata sul valore delle carte che l'avversario potrebbe mangiare.
        """
        if not banco or self._is_banco_morto(banco):
            return 0.0

        rischio = 0.0
        for v in range(1, 11):
            if self._rimanenti(v) > 0 and self._has_subset_sum(banco, v):
                # L'avversario potrebbe avere 'v' e mangiare.
                # Quanto fa male? Dipende da cosa c'è sul banco.
                # Cerchiamo la combinazione massima che potrebbe fare.
                # Euristica rapida: se c'è un 7 o 6 sul banco, è pericolosissimo.
                for c in banco:
                    if c.valore == 7:
                        rischio += 500.0
                    elif c.valore == 6:
                        rischio += 200.0
                    elif c.seme.lower() == "denari":
                        rischio += 100.0

                # Rischio Scopa: se la somma di TUTTO il banco è 'v', è SCOPA!
                if sum(c.valore for c in banco) == v:
                    rischio += 100000.0  # PENALITÀ ASSOLUTA

        return rischio

    # ------------------------------------------------------------------
    # VALUTAZIONE AZIONI
    # ------------------------------------------------------------------
    def _valuta_presa(self, carta: Carta, prese: List[Carta], banco: List[Carta], obs: dict) -> float:
        """Calcola il punteggio di una mossa di presa."""
        score = 0.0
        carte_totali = prese + [carta]
        banco_residuo = [c for c in banco if c not in prese]

        # 1. SCOOPA (Vittoria istantanea)
        if len(prese) == len(banco):
            score += 100000.0

        # 2. RISORSE FONDAMENTALI (Primiera e Settebello)
        for c in carte_totali:
            if c.is_settebello():
                score += 15000.0
            elif c.valore == 7:
                score += 3000.0
            elif c.valore == 6:
                score += 800.0
            elif c.seme.lower() == "denari":
                score += 300.0

        # 3. QuantitÃ  (Carte)
        score += len(carte_totali) * 50.0

        # 4. DIFESA (Rischio sul banco residuo)
        if banco_residuo:
            rischio = self._calcola_rischio_banco(banco_residuo)
            score -= rischio

        return score

    def _valuta_balla(self, carta: Carta, banco: List[Carta]) -> float:
        """Calcola il punteggio di una mossa di 'balla' (lasciare la carta sul banco)."""
        score = 0.0
        nuovo_banco = banco + [carta]

        # 1. Creazione di un BANCO MORTO (Bonus Enorme)
        if self._is_banco_morto(nuovo_banco):
            score += 20000.0
        else:
            # 2. Penalità per rischio lasciato
            rischio = self._calcola_rischio_banco(nuovo_banco)
            score -= rischio

        # 3. Penalità per aver lasciato sul tavolo carte preziose
        if carta.valore == 7:
            score -= 5000.0
        elif carta.valore == 6:
            score -= 1500.0
        elif carta.seme.lower() == "denari":
            score -= 500.0

        # 4. Bonus per carte alte (diffili da sommare per l'avversario)
        if carta.valore >= 8:
            score += 100.0

        return score

    # ------------------------------------------------------------------
    # SCELTA FINALE
    # ------------------------------------------------------------------
    def scegli_mossa(self, observation: dict) -> Tuple[Carta, Optional[List[Carta]]]:
        self._aggiorna_memoria(observation)
        azioni = observation["azioni_legali"]
        banco = observation["banco"]

        if not azioni:
            raise ValueError("Nessuna azione legale!")

        azioni_prese = [a for a in azioni if a[1] is not None]
        azioni_balla = [a for a in azioni if a[1] is None]

        # ======================================================================
        # FASE 1: VALUTAZIONE PRESE
        # ======================================================================
        if azioni_prese:
            migliori_prese = []
            max_score = -float('inf')

            for carta, prese in azioni_prese:
                score = self._valuta_presa(carta, prese, banco, observation)
                if score > max_score:
                    max_score = score
                    migliori_prese = [(carta, prese)]
                elif score == max_score:
                    migliori_prese.append((carta, prese))

            # Se la miglior presa è sicura (o comunque la migliore in assoluto), falla
            # Regola d'oro: se puoi fare Scopa, falla sempre.
            if max_score >= 100000.0:
                return migliori_prese[0]

            # Se la miglior presa non lascia Scope all'avversario, ed è un buon bottino, falla
            if max_score > 0:
                return migliori_prese[0]

        # ======================================================================
        # FASE 2: VALUTAZIONE BALLA (Difesa)
        # ======================================================================
        if azioni_balla:
            migliori_balla = []
            max_score = -float('inf')

            for carta, _ in azioni_balla:
                score = self._valuta_balla(carta, banco)
                if score > max_score:
                    max_score = score
                    migliori_balla = [(carta, None)]
                elif score == max_score:
                    migliori_balla.append((carta, None))

            # Se troviamo un Banco Morto, o la miglior balla è accettabile
            if max_score > -10000.0:  # Soglia di tolleranza
                return migliori_balla[0]

        # ======================================================================
        # FASE 3: DISPERAZIONE (Fallback)
        # ======================================================================
        # Se siamo costretti a lasciare una Scopa o una carta pessima,
        # scegliamo il male minore tra tutte le azioni disponibili.
        tutte_le_azioni = []
        for carta, prese in azioni:
            if prese is not None:
                score = self._valuta_presa(carta, prese, banco, observation)
            else:
                score = self._valuta_balla(carta, banco)
            tutte_le_azioni.append((score, (carta, prese)))

        tutte_le_azioni.sort(key=lambda x: x[0], reverse=True)
        return tutte_le_azioni[0][1]