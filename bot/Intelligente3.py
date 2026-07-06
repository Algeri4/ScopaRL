import random
from typing import Tuple, Optional, List
from scopa.carta import Carta
from scopa.motore import MotoreScopa
from scopa.probabilita import (
    probabilita_almeno_una,
    probabilita_cumulative,
    calcola_parametri,
    conta_carte_per_valore,
)
from .base import BotAgent


class BotIntelligente3(BotAgent):
    """
    Bot euristico avanzato con calcolo probabilistico del rischio.
    Sfrutta scopa.probabilita per decisioni informate.
    """

    def __init__(self, nome: str = "Intelligente3"):
        self._nome = nome

    def nome(self) -> str:
        return self._nome

    # ------------------------------------------------------------------
    # RISCHIO BANCO (usa la libreria condivisa)
    # ------------------------------------------------------------------

    def _calcola_rischio_banco(self, banco: List[Carta], note: List[Carta],
                                 n_mano_avversario: int, carte_mazzo: int) -> float:
        """
        Calcola il rischio di lasciare il banco così com'è.
        Usa probabilita_almeno_una dalla libreria condivisa.
        """
        if not banco:
            return 0.0

        n_sconosciute = carte_mazzo + n_mano_avversario
        carte_passate = conta_carte_per_valore(note)

        rischio_totale = 0.0

        for valore in range(1, 11):
            rimanenti = 4 - carte_passate.get(valore, 0)
            if rimanenti <= 0:
                continue

            prob_ha_carta = probabilita_almeno_una(rimanenti, n_sconosciute, n_mano_avversario)
            if prob_ha_carta <= 0:
                continue

            carta_fittizia = Carta("denari", valore)
            prese = MotoreScopa.trova_tutte_prese_legali(banco, carta_fittizia)

            if prese:
                max_prese = max(len(p) for p in prese)
                rischio_scopa = 1.0 if max_prese == len(banco) else 0.0
                danno = (max_prese / max(len(banco), 1)) * 0.5 + rischio_scopa * 2.0
                rischio_totale += prob_ha_carta * danno

        return min(rischio_totale, 1.0)

    # ------------------------------------------------------------------
    # SCELTA MOSSA
    # ------------------------------------------------------------------

    def scegli_mossa(self, observation: dict) -> Tuple[Carta, Optional[List[Carta]]]:
        azioni = observation["azioni_legali"]
        banco = observation["banco"]

        # Usa la libreria condivisa per parametri
        note, n_mano_avversario, carte_mazzo = calcola_parametri(observation)
        n_sconosciute = carte_mazzo + n_mano_avversario
        carte_passate = conta_carte_per_valore(note)

        if not azioni:
            raise ValueError("Nessuna azione legale!")

        # 1) SCOPA
        scope = [a for a in azioni if a[1] is not None and len(a[1]) == len(banco)]
        if scope:
            return scope[0]

        # 2) SETTEBELLO
        settebello = [
            a for a in azioni
            if a[1] is not None and any(c.is_settebello() for c in a[1] + [a[0]])
        ]
        if settebello:
            return settebello[0]

        azioni_prese = [a for a in azioni if a[1] is not None]
        azioni_balla = [a for a in azioni if a[1] is None]

        # ==============================================================
        # 3) PRESE: valuta rischio del banco residuo con probabilità
        # ==============================================================
        candidati_prese = []
        for azione in azioni_prese:
            carta, prese = azione
            banco_dopo = [c for c in banco if c not in prese]
            if not banco_dopo:
                continue

            # Rischio scopa usando probabilità cumulative
            rischio_scopa = 0.0
            for valore in range(1, 11):
                rim = 4 - carte_passate.get(valore, 0)
                if rim <= 0:
                    continue
                prob = probabilita_almeno_una(rim, n_sconosciute, n_mano_avversario)
                if prob > 0:
                    carta_fittizia = Carta("denari", valore)
                    prese_poss = MotoreScopa.trova_tutte_prese_legali(banco_dopo, carta_fittizia)
                    if any(len(p) == len(banco_dopo) for p in prese_poss):
                        rischio_scopa = max(rischio_scopa, prob)

            rischio_generale = self._calcola_rischio_banco(banco_dopo, note, n_mano_avversario, carte_mazzo)

            punteggio = 0
            carte_totali = prese + [carta]

            for c in carte_totali:
                if c.is_settebello():
                    punteggio += 500
                elif c.valore == 7:
                    punteggio += 200
                elif c.seme.lower() == "denari":
                    punteggio += 80
                elif c.valore == 10:
                    punteggio += 30

            punteggio += len(carte_totali) * 10
            punteggio += carta.valore * 2

            # Penalità basata su probabilità reale
            if rischio_scopa > 0.5:
                punteggio -= 300
            elif rischio_generale > 0.7:
                punteggio -= 150
            elif rischio_generale < 0.2:
                punteggio += 100

            candidati_prese.append((punteggio, azione, rischio_scopa))

        if candidati_prese:
            sicure = [c for c in candidati_prese if c[2] < 0.3]
            if sicure:
                sicure.sort(key=lambda x: x[0], reverse=True)
                return sicure[0][1]
            candidati_prese.sort(key=lambda x: x[0], reverse=True)
            return candidati_prese[0][1]

        # ==============================================================
        # 4) BALLA: minimizza rischio probabilistico
        # ==============================================================
        candidati_balla = []
        for azione in azioni_balla:
            carta = azione[0]
            banco_dopo = banco + [carta]

            rischio_scopa = 0.0
            for valore in range(1, 11):
                rim = 4 - carte_passate.get(valore, 0)
                if rim <= 0:
                    continue
                prob = probabilita_almeno_una(rim, n_sconosciute, n_mano_avversario)
                if prob > 0:
                    carta_fittizia = Carta("denari", valore)
                    prese_poss = MotoreScopa.trova_tutte_prese_legali(banco_dopo, carta_fittizia)
                    if any(len(p) == len(banco_dopo) for p in prese_poss):
                        rischio_scopa = max(rischio_scopa, prob)

            rischio_generale = self._calcola_rischio_banco(banco_dopo, note, n_mano_avversario, carte_mazzo)

            punteggio = carta.valore * 2

            if carta.seme.lower() == "denari":
                punteggio -= 50
            if carta.valore == 7:
                punteggio -= 80

            if rischio_scopa > 0:
                punteggio -= rischio_scopa * 500
            if rischio_generale > 0.5:
                punteggio -= rischio_generale * 200

            # Bonus banco morto (somma = valore finito)
            somma_banco = sum(c.valore for c in banco_dopo)
            rim_somma = 4 - carte_passate.get(somma_banco, 0)
            if rim_somma <= 0 and len(banco_dopo) > 1:
                punteggio += 300

            candidati_balla.append((punteggio, azione, rischio_scopa))

        if candidati_balla:
            senza_scopa = [c for c in candidati_balla if c[2] == 0]
            if senza_scopa:
                senza_scopa.sort(key=lambda x: x[0], reverse=True)
                return senza_scopa[0][1]
            candidati_balla.sort(key=lambda x: (x[2], -x[0]))
            return candidati_balla[0][1]

        return random.choice(azioni)