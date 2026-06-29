# scopa/ambiente.py
import random
from typing import Tuple, Optional

from .carta import Carta
from .costanti import SEMI
from .mazzo import Mazzo
from .tavolo import Tavolo
from .giocatore import Giocatore
from .motore import MotoreScopa
from .punteggio import ContatorePunti
from .observation import ObservationBuilder


class ScopaEnvironment:
    def __init__(self, nome_p0="Bot", nome_p1="Avversario"):
        self.mazzo = Mazzo()
        self.tavolo = Tavolo()
        self.motore = MotoreScopa()

        self.giocatore_0 = Giocatore(nome_p0, "bot")
        self.giocatore_1 = Giocatore(nome_p1, "bot")

        self.mazziere = 1
        self.turno = 0
        self.mano_corrente = 1
        self.giocate_totali = 0
        self.partita_finita = False
        self.punteggi = [0, 0]
        self.ultimo_prese = None
        self.storico = []

        # Dati dell'ultima smazzata conclusa (per GUI / log)
        self.ultima_smazzata = None

    # ------------------------------------------------------------------
    # GIOCO
    # ------------------------------------------------------------------
    def reset(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

        self.giocatore_0.reset()
        self.giocatore_1.reset()
        self.tavolo.reset()
        self.mazzo.rigenera()

        self.mazziere = 1
        self.turno = 1 - self.mazziere
        self.mano_corrente = 1
        self.giocate_totali = 0
        self.partita_finita = False
        self.punteggi = [0, 0]
        self.ultimo_prese = None
        self.storico = []
        self.ultima_smazzata = None

        self._distribuisci_mano()
        return self._get_observation(0)

    def _distribuisci_mano(self):
        while True:
            self.giocatore_0.ricevi_carte(self.mazzo.pesca(9))
            self.giocatore_1.ricevi_carte(self.mazzo.pesca(9))
            self.tavolo.aggiungi(self.mazzo.pesca(4))

            if self.motore.controlla_banco_iniziale(self.tavolo.banco):
                self.giocatore_0.mano = []
                self.giocatore_1.mano = []
                self.tavolo.reset()
                self.mazzo.rigenera()
                print("[SISTEMA] Ridistribuzione per 3+ Re nel banco")
            else:
                break

    def step(self, action: Tuple[Carta, Optional[list]], giocatore_idx: int):
        if self.partita_finita:
            raise ValueError("Partita finita")
        if giocatore_idx != self.turno:
            raise ValueError("Non è il tuo turno")

        g = self._giocatore(giocatore_idx)
        carta, prese = action

        # Validazione
        if carta not in g.mano:
            raise ValueError("Carta non in mano")
        if action not in self.get_legal_actions(giocatore_idx):
            raise ValueError("Azione illegale")

        # Esecuzione
        banco_prima = list(self.tavolo.banco)
        g.gioca_carta(carta)

        reward = 0.0
        info = {"scopa": False, "balla": False}

        if prese:
            self.tavolo.rimuovi(prese)
            prese_totali = prese + [carta]
            is_scopa = self.motore.is_scopa(banco_prima, prese)
            ultima = (self.mano_corrente == 2 and len(g.mano) == 0 and self.mazzo.rimanenti() == 0)

            if is_scopa and not ultima:
                g.aggiungi_prese(prese_totali, scopa=True)
                reward += 1.0
                info["scopa"] = True
            else:
                g.aggiungi_prese(prese_totali, scopa=False)

            # Reward shaping
            for c in prese_totali:
                if c.is_settebello(): reward += 0.5
                elif c.valore == 7: reward += 0.3
                elif c.seme == "Denari": reward += 0.1

            self.ultimo_prese = giocatore_idx
        else:
            self.tavolo.aggiungi([carta])
            reward -= 0.05
            info["balla"] = True

        # Log
        self.storico.append({
            "turno": giocatore_idx,
            "carta": carta,
            "prese": prese or [],
            "scopa": info["scopa"]
        })

        self.giocate_totali += 1
        self.turno = 1 - self.turno
        self._controlla_fine()

        return self._get_observation(giocatore_idx), reward, self.partita_finita, info

    def _controlla_fine(self):
        if self.mano_corrente == 1 and self.giocate_totali >= 18:
            if self.mazzo.rimanenti() > 0:
                self.mano_corrente = 2
                self.giocatore_0.ricevi_carte(self.mazzo.pesca(9))
                self.giocatore_1.ricevi_carte(self.mazzo.pesca(9))
            else:
                self._fine_smazzata()

        elif self.mano_corrente == 2 and self.giocate_totali >= 36:
            self._fine_smazzata()

    def _fine_smazzata(self):
        # Carte rimaste al banco -> ultimo giocatore che ha preso
        if self.tavolo.banco and self.ultimo_prese is not None:
            self._giocatore(self.ultimo_prese).prese.extend(self.tavolo.banco)
            self.tavolo.reset()

        # Conteggio punti
        pt0, pt1, dettagli = ContatorePunti.calcola(
            self.giocatore_0.prese, self.giocatore_0.scope,
            self.giocatore_1.prese, self.giocatore_1.scope
        )

        self.punteggi[0] += pt0
        self.punteggi[1] += pt1

        # SALVA dati della smazzata PRIMA del reset
        self.ultima_smazzata = {
            "prese_0": list(self.giocatore_0.prese),
            "prese_1": list(self.giocatore_1.prese),
            "scope_0": self.giocatore_0.scope,
            "scope_1": self.giocatore_1.scope,
            "punti_mano": [pt0, pt1],
            "punti_totali": list(self.punteggi),
            "dettagli": dettagli,
            "ultimo_prese": self.ultimo_prese,
        }

        print(f"\n[SMAZZATA] {self.giocatore_0.nome} +{pt0}, {self.giocatore_1.nome} +{pt1}")
        print(f"  Totale: {self.punteggi}")
        print(f"  Primiera: {dettagli['primiera']}")

        if max(self.punteggi) >= 11:
            self.partita_finita = True
            v = 0 if self.punteggi[0] > self.punteggi[1] else 1
            print(f"\n[VITTORIA] {self._giocatore(v).nome} vince!")
            return

        self._prepara_nuova_smazzata()

    def _prepara_nuova_smazzata(self):
        self.mazzo.rigenera()
        self.giocatore_0.prese = []
        self.giocatore_0.scope = 0
        self.giocatore_1.prese = []
        self.giocatore_1.scope = 0
        self.tavolo.reset()

        self.mazziere = 1 - self.mazziere
        self.turno = 1 - self.mazziere
        self.mano_corrente = 1
        self.giocate_totali = 0
        self.ultimo_prese = None
        self.storico = []

        self._distribuisci_mano()
        print(f"\n[NUOVA SMAZZATA] Mazziere: {self._giocatore(self.mazziere).nome}")

    # ------------------------------------------------------------------
    # RL INTERFACE
    # ------------------------------------------------------------------
    def get_legal_actions(self, giocatore_idx: int):
        g = self._giocatore(giocatore_idx)
        azioni = []
        for carta in g.mano:
            prese = self.motore.trova_tutte_prese_legali(self.tavolo.banco, carta)
            if not prese:
                azioni.append((carta, None))
            else:
                for p in prese:
                    azioni.append((carta, p))
        return azioni

    def _get_observation(self, giocatore_idx: int):
        return ObservationBuilder.build(self, giocatore_idx)

    def stato_to_vector(self, obs: dict) -> list:
        return ObservationBuilder.to_vector(obs)

    # ------------------------------------------------------------------
    # UTILITY
    # ------------------------------------------------------------------
    def _giocatore(self, idx: int):
        return self.giocatore_0 if idx == 0 else self.giocatore_1