import random
from typing import Tuple, Optional, List
from scopa.carta import Carta
from scopa.motore import MotoreScopa
from .base import BotAgent


class BotIntelligente2(BotAgent):
    """
    Bot euristico con memoria delle carte passate:
    1) Scopa
    2) Settebello
    3) Prende senza dare scopa; preferisce lasciare un banco 'morto'
       (somma totale = valore finito, quindi l'avversario non può più scopare)
    4) Balla sicura; cerca di CREARE un banco morto, evitando Denari e 7
    """

    def __init__(self, nome: str = "Intelligente2"):
        self._nome = nome
        # Memoria persistente delle carte già viste in questa smazzata
        self._carte_viste = set()
        self._smazzata_corrente = None

    def nome(self) -> str:
        return self._nome

    # ------------------------------------------------------------------
    # MEMORIA
    # ------------------------------------------------------------------

    def _aggiorna_memoria(self, obs: dict):
        """Traccia tutte le carte note fino a questo turno."""
        mano = obs.get("mano_corrente", 1)

        # Se cambia smazzata, azzera la memoria
        if mano != self._smazzata_corrente:
            self._smazzata_corrente = mano
            self._carte_viste = set()

        for chiave in ("mano", "banco", "prese_mie", "prese_avversario"):
            for c in obs.get(chiave, []):
                self._carte_viste.add((c.seme, c.valore))

    def _sconosciute_effettive(self, obs: dict) -> List[Carta]:
        """
        Ritorna le carte che l'avversario POTREBBE avere in mano.
        Usa l'observation (già filtrata) ma la rafforza con la memoria interna.
        """
        # L'observation ha già fatto il calcolo corretto
        return obs.get("sconosciute", [])

    def _valori_finiti(self, sconosciute: List[Carta]) -> set:
        """Valori che NON esistono più tra le carte sconosciute."""
        tutti = set(range(1, 11))
        presenti = set(c.valore for c in sconosciute)
        return tutti - presenti

    # ------------------------------------------------------------------
    # LOGICA DI SICUREZZA
    # ------------------------------------------------------------------

    def _carta_uguale(self, c1: Carta, c2: Carta) -> bool:
        return c1.seme == c2.seme and c1.valore == c2.valore

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

    def _somma_banco(self, banco: List[Carta]) -> int:
        return sum(c.valore for c in banco)

    def _banco_morto(self, banco: List[Carta], sconosciute: List[Carta]) -> bool:
        """
        Il banco è 'morto' quando:
        - L'avversario non può fare scopa (già controllato)
        - E la somma totale del banco è un valore FINITO
          (nessuna carta sconosciuta ha quel valore, quindi impossibile da scopare)
        """
        if not banco:
            return True
        if self._avversario_puo_fare_scopa(banco, sconosciute):
            return False
        somma = self._somma_banco(banco)
        return somma in self._valori_finiti(sconosciute)

    # ------------------------------------------------------------------
    # SCELTA MOSSA
    # ------------------------------------------------------------------

    def scegli_mossa(self, observation: dict) -> Tuple[Carta, Optional[List[Carta]]]:
        self._aggiorna_memoria(observation)

        azioni = observation["azioni_legali"]
        banco = observation["banco"]
        sconosciute = self._sconosciute_effettive(observation)

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
        # 3) PRESE SICURE (non danno scopa)
        # ==============================================================
        prese_sicure = []
        for azione in azioni_prese:
            carta, prese = azione
            banco_dopo = [c for c in banco if not any(self._carta_uguale(c, p) for p in prese)]
            if not self._avversario_puo_fare_scopa(banco_dopo, sconosciute):
                prese_sicure.append(azione)

        if prese_sicure:
            candidati = []
            for azione in prese_sicure:
                carta, prese = azione
                carte_totali = prese + [carta]
                banco_dopo = [c for c in banco if not any(self._carta_uguale(c, p) for p in prese)]
                punteggio = 0

                # Banco morto = somma finita, l'avversario non può più scopare → bonus massimo
                if self._banco_morto(banco_dopo, sconosciute):
                    punteggio += 1000

                # 7 (Primiera)
                for c in carte_totali:
                    if c.valore == 7:
                        punteggio += 300

                # Denari
                for c in carte_totali:
                    if c.seme.lower() == "denari":
                        punteggio += 100

                # Più carte prese
                punteggio += len(carte_totali) * 10

                # Valore alto
                for c in carte_totali:
                    punteggio += c.valore

                candidati.append((punteggio, azione))

            candidati.sort(key=lambda x: x[0], reverse=True)
            return candidati[0][1]

        # ==============================================================
        # 4) BALLA SICURA — cerca di CREARE un banco morto
        # ==============================================================
        balla_sicure = []
        for azione in azioni_balla:
            carta = azione[0]
            banco_dopo = banco + [carta]
            if not self._avversario_puo_fare_scopa(banco_dopo, sconosciute):
                balla_sicure.append(azione)

        # Tra le sicure, preferisci quelle che rendono il banco MORTO
        # (somma totale = valore finito, quindi l'avversario non può scopare)
        balla_morto = []
        for azione in balla_sicure:
            carta = azione[0]
            banco_dopo = banco + [carta]
            if self._banco_morto(banco_dopo, sconosciute):
                balla_morto.append(azione)

        # Preferite: non Denari, non 7, e che creino banco morto
        preferite_morto = [
            a for a in balla_morto
            if a[0].seme.lower() != "denari" and a[0].valore != 7
        ]
        if preferite_morto:
            return random.choice(preferite_morto)

        if balla_morto:
            return random.choice(balla_morto)

        # Poi tra tutte le sicure, preferisci non Denari e non 7
        preferite_sicure = [
            a for a in balla_sicure
            if a[0].seme.lower() != "denari" and a[0].valore != 7
        ]
        if preferite_sicure:
            return random.choice(preferite_sicure)

        if balla_sicure:
            return random.choice(balla_sicure)

        # Se anche la balla rischia, prova a ballare comunque evitando denari/7
        balla_meno_pericolosa = [
            a for a in azioni_balla
            if a[0].seme.lower() != "denari" and a[0].valore != 7
        ]
        if balla_meno_pericolosa:
            return random.choice(balla_meno_pericolosa)

        if azioni_balla:
            return random.choice(azioni_balla)

        # Disperazione: prendi a caso
        if azioni_prese:
            return random.choice(azioni_prese)
        return random.choice(azioni)