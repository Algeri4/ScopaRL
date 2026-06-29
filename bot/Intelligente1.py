import random
from typing import Tuple, Optional, List
from scopa.carta import Carta
from scopa.motore import MotoreScopa
from .base import BotAgent


class BotIntelligente1(BotAgent):
    """
    Bot euristico avanzato:
    1) Scopa (svuota il banco)
    2) Settebello
    3) Prende senza lasciare scopa all'avversario: priorità 7 > Denari > resto
    4) Balla sicura possibile: evita Denari e 7, a caso tra il resto
    """

    def __init__(self, nome: str = "Intelligente1"):
        self._nome = nome

    def nome(self) -> str:
        return self._nome

    def scegli_mossa(self, observation: dict) -> Tuple[Carta, Optional[List[Carta]]]:
        azioni = observation["azioni_legali"]
        banco = observation["banco"]
        sconosciute = observation.get("sconosciute", [])

        if not azioni:
            raise ValueError("Nessuna azione legale!")

        # 1) SCOPA: svuota completamente il banco
        scope = [a for a in azioni if a[1] is not None and len(a[1]) == len(banco)]
        if scope:
            return scope[0]

        # 2) SETTEBELLO: prende il 7 di denari (priorità assoluta dopo la scopa)
        settebello = [
            a for a in azioni
            if a[1] is not None and any(c.is_settebello() for c in a[1] + [a[0]])
        ]
        if settebello:
            return settebello[0]

        # Separazione
        azioni_prese = [a for a in azioni if a[1] is not None]
        azioni_balla = [a for a in azioni if a[1] is None]

        # 3) PRESE SICURE: non lasciano scopa all'avversario
        prese_sicure = []
        for azione in azioni_prese:
            carta, prese = azione
            # Calcola banco dopo la presa (carte non prese)
            banco_dopo = [c for c in banco if not any(self._carta_uguale(c, p) for p in prese)]
            if not banco_dopo:
                continue  # Scopa già gestita sopra

            if not self._avversario_puo_fare_scopa(banco_dopo, sconosciute):
                prese_sicure.append(azione)

        if prese_sicure:
            # Priorità: 7 > Denari > numero carte > valore
            candidati = []
            for azione in prese_sicure:
                carta, prese = azione
                carte_totali = prese + [carta]
                punteggio = 0

                # 7 (Primiera)
                for c in carte_totali:
                    if c.valore == 7:
                        punteggio += 300

                # Denari
                for c in carte_totali:
                    if c.seme.lower() == "denari":
                        punteggio += 100

                # Più carte prese = meglio
                punteggio += len(carte_totali) * 10

                # Valore alto
                for c in carte_totali:
                    punteggio += c.valore

                candidati.append((punteggio, azione))

            candidati.sort(key=lambda x: x[0], reverse=True)
            return candidati[0][1]

        # 4) BALLA: cerca di NON dare scopa all'avversario
        balla_sicure = []
        for azione in azioni_balla:
            carta = azione[0]
            banco_dopo = banco + [carta]
            if not self._avversario_puo_fare_scopa(banco_dopo, sconosciute):
                balla_sicure.append(azione)

        # Preferisci: non denari, non 7
        balla_preferite = [
            a for a in balla_sicure
            if a[0].seme.lower() != "denari" and a[0].valore != 7
        ]
        if balla_preferite:
            return random.choice(balla_preferite)

        # Se non c'è preferita sicura, qualsiasi sicura va bene
        if balla_sicure:
            return random.choice(balla_sicure)

        # Se anche la balla rischia, prova a ballare comunque evitando denari/7
        balla_meno_pericolosa = [
            a for a in azioni_balla
            if a[0].seme.lower() != "denari" and a[0].valore != 7
        ]
        if balla_meno_pericolosa:
            return random.choice(balla_meno_pericolosa)

        # Disperazione: balla a caso
        if azioni_balla:
            return random.choice(azioni_balla)

        # Se proprio non c'è scelta, prendi a caso (anche se rischioso)
        if azioni_prese:
            return random.choice(azioni_prese)

        return random.choice(azioni)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _carta_uguale(self, c1: Carta, c2: Carta) -> bool:
        return c1.seme == c2.seme and c1.valore == c2.valore

    def _avversario_puo_fare_scopa(self, banco: List[Carta], sconosciute: List[Carta]) -> bool:
        """
        True se esiste almeno una carta sconosciuta che, giocata sul banco,
        permetterebbe all'avversario di prendere TUTTE le carte sul banco.
        """
        if not banco:
            return False

        for carta in sconosciute:
            prese = MotoreScopa.trova_tutte_prese_legali(banco, carta)
            for p in prese:
                if len(p) == len(banco):
                    return True
        return False