import random
from typing import Tuple, Optional, List, Dict, Any
from scopa.carta import Carta
from scopa.motore import MotoreScopa
from .base import BotAgent


class BotIntelligente2(BotAgent):
    """
    Bot euristico basato su uno SCORING esplicito per ogni azione possibile,
    guardando due mosse avanti (la mia mossa, poi la possibile reazione
    dell'avversario con ogni carta a lui sconosciuta).

    Logica:
    1) Se posso fare scopa, la faccio sempre (tra piu' scope, scelgo quella
       che porta il guadagno maggiore, es. settebello).

    2) Altrimenti, per ogni azione legale (presa o balla) calcolo il banco
       che resterebbe dopo la mia mossa (B1). Per OGNI carta sconosciuta
       (che l'avversario potrebbe avere in mano) controllo cosa potrebbe
       fare su B1:
         - se con quella carta l'avversario potrebbe fare SCOPA         -> -10000
         - se potrebbe prendere il settebello senza lasciarmi la
           possibilita' di rifarmi subito con una scopa                -> -8000
         - se potrebbe prendere un 7 (non settebello) senza lasciarmi
           la possibilita' di scopa                                    -> -5000
         - se potrebbe prendere un 6 senza lasciarmi la possibilita'
           di scopa                                                    -> -3000
         - se potrebbe prendere un Oro (denari) senza lasciarmi la
           possibilita' di scopa                                       -> -2000
         - se potrebbe prendere qualunque altra carta senza lasciarmi
           la possibilita' di scopa                                    -> -1000
         - se con quella carta NON puo' prendere nulla                 -> 0

       "Senza lasciarmi la possibilita' di fare scopa" viene verificato
       DAVVERO: si calcola il banco B2 che resterebbe dopo la presa
       ipotetica dell'avversario e si controlla se una qualunque carta
       della mia mano (dopo aver giocato la carta di questo turno) mi
       permetterebbe di fare scopa su B2. Se si', quella particolare
       minaccia non genera penalita' (il rischio e' "coperto" dalla
       controscopa). Questo e' lo sguardo "due mosse dopo".

       Le penalita' di tutte le carte sconosciute si sommano: questo, oltre
       a penalizzare le mosse davvero pericolose, pesa automaticamente
       anche la PROBABILITA' (piu' carte sconosciute abilitano una minaccia,
       piu' la mossa viene penalizzata) senza bisogno di un calcolo
       probabilistico separato.

    3) Al rischio calcolato sottraggo il guadagno immediato delle carte che
       prendo in questa mossa (0 se e' una balla):
         settebello = 6000, ogni 7 = 2500, ogni 6 = 500,
         ogni Oro (denari) = 300, ogni altra carta = 100

    4) Scelgo l'azione con punteggio (guadagno - rischio) piu' alto.
       In caso di pareggio: prima minimizzo il numero di carte sconosciute
       che darebbero scopa all'avversario (probabilita' di scopa), poi il
       rischio totale, poi preferisco il guadagno maggiore.
    """

    def __init__(self, nome: str = "Intelligente2"):
        self._nome = nome

    def nome(self) -> str:
        return self._nome

    # ------------------------------------------------------------------
    # SCELTA MOSSA
    # ------------------------------------------------------------------

    def scegli_mossa(self, observation: dict) -> Tuple[Carta, Optional[List[Carta]]]:
        azioni = observation["azioni_legali"]
        banco = observation["banco"]
        mano = observation.get("mano", [])
        sconosciute = observation.get("sconosciute", [])

        if not azioni:
            raise ValueError("Nessuna azione legale!")

        # 1) SCOPA: se posso farla, la faccio sempre.
        scope = [a for a in azioni if a[1] is not None and len(a[1]) == len(banco)]
        if scope:
            migliore = max(scope, key=lambda a: self._guadagno(a[1] + [a[0]]))
            return migliore

        # 2) Valutazione completa di tutte le azioni non-scopa
        candidati: List[Dict[str, Any]] = []
        for azione in azioni:
            carta, prese = azione
            carte_totali = (prese + [carta]) if prese is not None else []
            guadagno = self._guadagno(carte_totali)

            # Banco che resta dopo la MIA mossa (B1)
            if prese is not None:
                banco_dopo = [c for c in banco if not any(self._carta_uguale(c, p) for p in prese)]
            else:
                banco_dopo = banco + [carta]

            # La mia mano dopo aver giocato "carta" in questo turno
            mano_dopo = [c for c in mano if not self._carta_uguale(c, carta)]

            rischio_totale, n_carte_scopa = self._valuta_rischio(banco_dopo, sconosciute, mano_dopo)

            punteggio = guadagno - rischio_totale

            candidati.append({
                "azione": azione,
                "punteggio": punteggio,
                "n_carte_scopa": n_carte_scopa,
                "rischio_totale": rischio_totale,
                "guadagno": guadagno,
            })

        # Ordina: punteggio decrescente, poi meno carte che darebbero scopa
        # all'avversario (= minor probabilita' di scopa), poi meno rischio
        # totale, poi guadagno maggiore. Se resta un pareggio perfetto,
        # random.choice tra i pari-merito evita bias deterministici.
        candidati.sort(key=lambda x: (
            -x["punteggio"],
            x["n_carte_scopa"],
            x["rischio_totale"],
            -x["guadagno"],
        ))

        miglior_punteggio = candidati[0]["punteggio"]
        migliori = [c for c in candidati if (
            c["punteggio"] == miglior_punteggio
            and c["n_carte_scopa"] == candidati[0]["n_carte_scopa"]
            and c["rischio_totale"] == candidati[0]["rischio_totale"]
            and c["guadagno"] == candidati[0]["guadagno"]
        )]

        return random.choice(migliori)["azione"]

    # ------------------------------------------------------------------
    # VALUTAZIONE RISCHIO (2 mosse avanti)
    # ------------------------------------------------------------------

    def _valuta_rischio(self, banco_b1: List[Carta], sconosciute: List[Carta],
                         mano_dopo: List[Carta]) -> Tuple[int, int]:
        """
        Ritorna (rischio_totale, numero_carte_che_darebbero_scopa) valutando,
        per ogni carta sconosciuta, la peggior reazione possibile
        dell'avversario su banco_b1.
        """
        if not banco_b1:
            return 0, 0

        rischio_totale = 0
        n_carte_scopa = 0

        for carta_sco in sconosciute:
            penalita, e_scopa = self._penalita_per_carta_sconosciuta(banco_b1, carta_sco, mano_dopo)
            rischio_totale += penalita
            if e_scopa:
                n_carte_scopa += 1

        return rischio_totale, n_carte_scopa

    def _penalita_per_carta_sconosciuta(self, banco_b1: List[Carta], carta_sco: Carta,
                                         mano_dopo: List[Carta]) -> Tuple[int, bool]:
        """
        Calcola la peggior penalita' che l'avversario potrebbe infliggerci
        giocando "carta_sco" su banco_b1, considerando TUTTE le prese
        legali possibili con quella carta (si prende il caso peggiore).
        """
        prese_possibili = MotoreScopa.trova_tutte_prese_legali(banco_b1, carta_sco)
        if not prese_possibili:
            return 0, False

        peggior_penalita = 0
        scopa_possibile = False

        for presa in prese_possibili:
            # Scopa per l'avversario: penalita' massima, non mitigabile.
            if len(presa) == len(banco_b1):
                peggior_penalita = max(peggior_penalita, 10000)
                scopa_possibile = True
                continue

            # Banco che resterebbe dopo la presa ipotetica dell'avversario (B2)
            banco_b2 = [c for c in banco_b1 if not any(self._carta_uguale(c, p) for p in presa)]

            # Se dopo quella presa io potrei rifarmi subito con una scopa,
            # questa minaccia specifica non genera penalita'.
            if self._posso_fare_scopa(banco_b2, mano_dopo):
                continue

            carte_prese_avversario = presa + [carta_sco]

            if any(c.is_settebello() for c in carte_prese_avversario):
                peggior_penalita = max(peggior_penalita, 8000)
            elif any(c.valore == 7 for c in carte_prese_avversario):
                peggior_penalita = max(peggior_penalita, 5000)
            elif any(c.valore == 6 for c in carte_prese_avversario):
                peggior_penalita = max(peggior_penalita, 3000)
            elif any(c.seme.lower() == "denari" for c in carte_prese_avversario):
                peggior_penalita = max(peggior_penalita, 2000)
            else:
                peggior_penalita = max(peggior_penalita, 1000)

        return peggior_penalita, scopa_possibile

    def _posso_fare_scopa(self, banco: List[Carta], mano: List[Carta]) -> bool:
        """True se con una qualunque carta della mia mano posso svuotare 'banco'."""
        if not banco:
            return False
        for c in mano:
            for presa in MotoreScopa.trova_tutte_prese_legali(banco, c):
                if len(presa) == len(banco):
                    return True
        return False

    # ------------------------------------------------------------------
    # GUADAGNO IMMEDIATO
    # ------------------------------------------------------------------

    def _guadagno(self, carte: List[Carta]) -> int:
        punteggio = 0
        for c in carte:
            if c.is_settebello():
                punteggio += 6000
            elif c.valore == 7:
                punteggio += 2500
            elif c.valore == 6:
                punteggio += 500
            elif c.seme.lower() == "denari":
                punteggio += 300
            else:
                punteggio += 100
        return punteggio

    # ------------------------------------------------------------------
    # HELPER
    # ------------------------------------------------------------------

    def _carta_uguale(self, c1: Carta, c2: Carta) -> bool:
        return c1.seme == c2.seme and c1.valore == c2.valore