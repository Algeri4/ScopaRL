import random
from typing import Tuple, Optional, List, Dict
from scopa.carta import Carta
from scopa.costanti import SEMI
from scopa.motore import MotoreScopa
from scopa.probabilita import (
    probabilita_almeno_una,
    calcola_parametri,
    conta_carte_per_valore,
)
from .base import BotAgent


class BotCLAUDE(BotAgent):
    """
    Bot euristico "campione" per il campionato ScopaRL.

    FILOSOFIA (dopo aver analizzato Intelligente1..5):
    - Intelligente1/2 vincono perché usano un VINCOLO RIGIDO di sicurezza:
      non lasciare mai una scopa certa all'avversario se esiste un'alternativa
      che la evita con certezza (calcolata sulle carte davvero sconosciute,
      non su un contatore fatto in casa che si può corrompere).
    - Intelligente3/4/5 hanno sostituito quel vincolo con una somma di bonus/
      penalità pesati "a sentimento", finendo per scegliere mosse rischiose
      quando un'alternativa sicura al 100% esisteva (in più, Intelligente4/5
      avevano un bug concreto: il controllo sul rischio nella scelta della
      presa era dead code, ritornava sempre la stessa opzione).

    STRATEGIA:
      1) Scopa sempre, se disponibile (tra più scope, la migliore per valore).
      2) Settebello sempre, se disponibile e non c'è scopa.
      3) Tra le prese "sicure" (nessuna carta sconosciuta permette scopa
         all'avversario dopo), scegli quella che massimizza un punteggio
         basato su: 7 (primiera), completamento di un seme mancante in
         primiera, denari, numero di carte, creazione di un banco morto.
      4) Se NESSUNA presa è sicura, sei comunque obbligato a prendere
         (è un'azione legale che l'ambiente offre solo se esiste una presa
         valida quando la carta ha presa singola obbligatoria, o se scegli
         di prendere invece di ballare quando entrambe le opzioni esistono):
         scegli la presa che minimizza il rischio REALE (calcolato con la
         probabilità ipergeometrica corretta di scopa.probabilita) pesato
         contro il valore guadagnato.
      5) Se non puoi prendere (balla): tra le "balle sicure" preferisci
         quelle che creano un banco morto, evitando di scartare denari/7/
         settebello. Se nessuna balla è sicura, minimizza il rischio atteso
         usando la probabilità corretta.

    Nota tecnica importante: uso SEMPRE observation["sconosciute"], che è
    calcolato dal motore di gioco (ObservationBuilder) come insieme esatto
    delle carte non ancora viste da questo giocatore. Non reinvento un
    contatore di carte "uscite": è esattamente lì che Intelligente5 aveva
    introdotto un bug di inferenza (segnare come "sparito per sempre" un
    valore solo perché l'avversario non lo aveva in quel momento).
    """

    def __init__(self, nome: str = "BotCLAUDE"):
        self._nome = nome

    def nome(self) -> str:
        return self._nome

    # ------------------------------------------------------------------
    # HELPER: sicurezza (stesso principio, provato, di Intelligente1/2)
    # ------------------------------------------------------------------

    @staticmethod
    def _carta_uguale(c1: Carta, c2: Carta) -> bool:
        return c1.seme == c2.seme and c1.valore == c2.valore

    @staticmethod
    def _avversario_puo_fare_scopa(banco: List[Carta], sconosciute: List[Carta]) -> bool:
        """True se esiste ALMENO UNA carta sconosciuta che, giocata su questo
        banco, permetterebbe all'avversario di prendere tutto (scopa certa
        possibile, non solo probabile)."""
        if not banco:
            return False
        for carta in sconosciute:
            prese = MotoreScopa.trova_tutte_prese_legali(banco, carta)
            for p in prese:
                if len(p) == len(banco):
                    return True
        return False

    @staticmethod
    def _valori_finiti(sconosciute: List[Carta]) -> set:
        """Valori che non compaiono più tra le carte sconosciute: se la somma
        del banco è uno di questi, il banco è 'morto' per la scopa."""
        presenti = set(c.valore for c in sconosciute)
        return set(range(1, 11)) - presenti

    def _banco_morto(self, banco: List[Carta], sconosciute: List[Carta]) -> bool:
        if not banco:
            return True
        if self._avversario_puo_fare_scopa(banco, sconosciute):
            return False
        somma = sum(c.valore for c in banco)
        return somma in self._valori_finiti(sconosciute)

    # ------------------------------------------------------------------
    # HELPER: primiera dinamica (bonus vero, non un +300 fisso per "7")
    # ------------------------------------------------------------------

    @staticmethod
    def _bonus_primiera(prese_mie: List[Carta], carte_nuove: List[Carta]) -> float:
        migliori = {}
        for c in prese_mie:
            vp = c.valore_primiera()
            if c.seme not in migliori or vp > migliori[c.seme]:
                migliori[c.seme] = vp

        completa_prima = len(migliori) == 4
        prima = sum(migliori.values()) if completa_prima else 0

        migliori2 = dict(migliori)
        for c in carte_nuove:
            vp = c.valore_primiera()
            if c.seme not in migliori2 or vp > migliori2[c.seme]:
                migliori2[c.seme] = vp

        completa_dopo = len(migliori2) == 4
        dopo = sum(migliori2.values()) if completa_dopo else 0

        bonus = 0.0
        # Completare un seme mancante nella primiera è enorme: senza tutti
        # e 4 i semi la primiera vale 0 punti, quindi è un requisito binario.
        if not completa_prima and completa_dopo:
            bonus += 600.0
        elif completa_prima and completa_dopo:
            bonus += (dopo - prima) * 4.0
        return bonus

    # ------------------------------------------------------------------
    # HELPER: rischio probabilistico corretto (solo come tie-break, MAI
    # per scavalcare un'opzione sicura al 100% quando esiste)
    # ------------------------------------------------------------------

    @staticmethod
    def _rischio_scopa_atteso(banco: List[Carta], observation: dict) -> float:
        """Probabilità attesa (0..1) che l'avversario possa fare scopa su
        questo banco, usando la vera distribuzione ipergeometrica."""
        if not banco:
            return 0.0
        note, n_mano_avv, carte_mazzo = calcola_parametri(observation)
        n_sconosciute = carte_mazzo + n_mano_avv
        carte_passate = conta_carte_per_valore(note)

        rischio = 0.0
        for valore in range(1, 11):
            rimanenti = 4 - carte_passate.get(valore, 0)
            if rimanenti <= 0:
                continue
            prob = probabilita_almeno_una(rimanenti, n_sconosciute, n_mano_avv)
            if prob <= 0:
                continue
            carta_fittizia = Carta("denari", valore)
            prese = MotoreScopa.trova_tutte_prese_legali(banco, carta_fittizia)
            if any(len(p) == len(banco) for p in prese):
                rischio = max(rischio, prob)
        return rischio

    # ------------------------------------------------------------------
    # VALUTAZIONE DI UNA PRESA (per ordinare le opzioni sicure)
    # ------------------------------------------------------------------

    def _punteggio_presa(self, carta: Carta, prese: List[Carta],
                          banco_dopo: List[Carta], sconosciute: List[Carta],
                          prese_mie: List[Carta]) -> float:
        carte_totali = prese + [carta]
        punteggio = 0.0

        for c in carte_totali:
            if c.valore == 7:
                punteggio += 220.0
            if c.seme.lower() == "denari":
                punteggio += 90.0

        punteggio += self._bonus_primiera(prese_mie, carte_totali)
        punteggio += len(carte_totali) * 12.0
        punteggio += carta.valore * 1.5

        if self._banco_morto(banco_dopo, sconosciute):
            punteggio += 400.0

        return punteggio

    # ------------------------------------------------------------------
    # SCELTA MOSSA
    # ------------------------------------------------------------------

    def scegli_mossa(self, observation: dict) -> Tuple[Carta, Optional[List[Carta]]]:
        azioni = observation["azioni_legali"]
        banco = observation["banco"]
        sconosciute = observation.get("sconosciute", [])
        prese_mie = observation.get("prese_mie", [])

        if not azioni:
            raise ValueError("Nessuna azione legale!")

        # 1) SCOPA: sempre, se disponibile. Tra più scope, la migliore.
        scope = [a for a in azioni if a[1] is not None and len(a[1]) == len(banco)]
        if scope:
            def valore_scopa(azione):
                carta, prese = azione
                v = 0.0
                for c in prese + [carta]:
                    if c.is_settebello():
                        v += 1000.0
                    elif c.valore == 7:
                        v += 50.0
                    elif c.seme.lower() == "denari":
                        v += 20.0
                return v
            scope.sort(key=valore_scopa, reverse=True)
            return scope[0]

        # 2) SETTEBELLO: priorità assoluta dopo la scopa.
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
            candidati_sicuri = []
            candidati_rischiosi = []

            for azione in azioni_prese:
                carta, prese = azione
                banco_dopo = [c for c in banco
                              if not any(self._carta_uguale(c, p) for p in prese)]

                if not self._avversario_puo_fare_scopa(banco_dopo, sconosciute):
                    punteggio = self._punteggio_presa(carta, prese, banco_dopo,
                                                       sconosciute, prese_mie)
                    candidati_sicuri.append((punteggio, azione))
                else:
                    rischio = self._rischio_scopa_atteso(banco_dopo, observation)
                    punteggio = self._punteggio_presa(carta, prese, banco_dopo,
                                                       sconosciute, prese_mie)
                    # Penalità reale, proporzionale al rischio calcolato
                    # correttamente (non un contatore corrotto). Usata SOLO
                    # per ordinare tra opzioni che restano comunque rischiose.
                    punteggio_netto = punteggio - rischio * 600.0
                    candidati_rischiosi.append((punteggio_netto, rischio, azione))

            # Vincolo rigido: se esiste ALMENO UNA presa sicura, si usa
            # esclusivamente quella (mai scavalcata da bonus su opzioni
            # rischiose: qui sta l'errore di Intelligente3/4/5).
            if candidati_sicuri:
                candidati_sicuri.sort(key=lambda x: x[0], reverse=True)
                return candidati_sicuri[0][1]

            # Nessuna presa è sicura: minimizza rischio reale, poi punteggio.
            candidati_rischiosi.sort(key=lambda x: (x[1], -x[0]))
            return candidati_rischiosi[0][2]

        # ==============================================================
        # 4) BALLA
        # ==============================================================
        candidati_sicuri = []
        candidati_rischiosi = []

        for azione in azioni_balla:
            carta = azione[0]
            banco_dopo = banco + [carta]

            if not self._avversario_puo_fare_scopa(banco_dopo, sconosciute):
                punteggio = carta.valore * 1.5
                if carta.seme.lower() == "denari":
                    punteggio -= 60.0
                if carta.valore == 7:
                    punteggio -= 90.0
                if self._banco_morto(banco_dopo, sconosciute):
                    punteggio += 350.0
                candidati_sicuri.append((punteggio, azione))
            else:
                rischio = self._rischio_scopa_atteso(banco_dopo, observation)
                punteggio = carta.valore * 1.5
                if carta.seme.lower() == "denari":
                    punteggio -= 60.0
                if carta.valore == 7:
                    punteggio -= 90.0
                punteggio -= rischio * 600.0
                candidati_rischiosi.append((punteggio, rischio, azione))

        if candidati_sicuri:
            candidati_sicuri.sort(key=lambda x: x[0], reverse=True)
            return candidati_sicuri[0][1]

        if candidati_rischiosi:
            candidati_rischiosi.sort(key=lambda x: (x[1], -x[0]))
            return candidati_rischiosi[0][2]

        # Non dovrebbe mai arrivare qui.
        return random.choice(azioni)