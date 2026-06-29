import random
from typing import Tuple, Optional, List
from scopa.carta import Carta
from .base import BotAgent


class BotPredatore(BotAgent):
    """
    Bot euristico che NON balla mai se può prendere.
    Priorità tra le prese:
    1) Scopa (svuota il banco)
    2) Settebello
    3) 7 (Primiera)
    4) Denari
    5) Carte di valore alto (più difficili da prendere per l'avversario)
    6) Numero di carte prese (più è meglio)

    Se NON può prendere, balla la carta più alta possibile.
    """

    def __init__(self, nome: str = "BotPredatore"):
        self._nome = nome

    def nome(self) -> str:
        return self._nome

    def scegli_mossa(self, observation: dict) -> Tuple[Carta, Optional[List[Carta]]]:
        azioni = observation["azioni_legali"]
        banco = observation["banco"]

        if not azioni:
            raise ValueError("Nessuna azione legale!")

        # Separa prese e balla
        azioni_prese = [a for a in azioni if a[1] is not None]
        azioni_balla = [a for a in azioni if a[1] is None]

        # REGOLA FERMA: se c'è almeno una presa, NON balla mai
        if azioni_prese:
            candidati = []
            for azione in azioni_prese:
                carta, prese = azione
                punteggio = 0
                carte_totali = prese + [carta]

                # 1) Scopa? Svuota tutto il banco
                if len(prese) == len(banco):
                    punteggio += 10000  # PRIORITÀ ASSOLUTA

                # 2) Settebello
                for c in carte_totali:
                    if c.is_settebello():
                        punteggio += 500

                # 3) 7 (Primiera) — anche se non settebello
                for c in carte_totali:
                    if c.valore == 7 and not c.is_settebello():
                        punteggio += 200

                # 4) Denari
                for c in carte_totali:
                    if c.seme.lower() == "denari":
                        punteggio += 80

                # 5) Re (valore 10) — utili per il conteggio carte
                for c in carte_totali:
                    if c.valore == 10:
                        punteggio += 30

                # 6) Numero di carte prese (più carte = meglio)
                punteggio += len(carte_totali) * 10

                # 7) Valore della carta giocata (preferisci carte alte)
                punteggio += carta.valore * 2

                candidati.append((punteggio, azione))

            candidati.sort(key=lambda x: x[0], reverse=True)
            return candidati[0][1]

        # Se NON può prendere, balla la carta più alta
        # (più difficile da prendere per l'avversario)
        if azioni_balla:
            azioni_balla.sort(key=lambda a: a[0].valore, reverse=True)
            return azioni_balla[0]

        # Fallback (non dovrebbe mai arrivare qui)
        return azioni[0]
