# cli/partita_cli.py
from scopa.ambiente import ScopaEnvironment
from scopa.carta import Carta
from bot.base import BotAgent


class PartitaCLI:
    """
    Gestisce una partita in modalità terminale: Umano vs Bot, Bot vs Bot, o Umano vs Umano.
    Ottimizzata per training RL e tornei batch.
    """

    def __init__(self, giocatore_a, giocatore_b, a_idx: int = 0, verbose: bool = True):
        """
        giocatore_a, giocatore_b: istanze BotAgent o stringhe "umano"
        a_idx: chi è il giocatore_0 (0=a, 1=b)
        verbose: stampa a schermo (False per training veloce)
        """
        self.giocatore_a = giocatore_a
        self.giocatore_b = giocatore_b
        self.a_idx = a_idx
        self.verbose = verbose

        nomi = [self._nome(giocatore_a), self._nome(giocatore_b)]
        if a_idx == 1:
            nomi = [nomi[1], nomi[0]]

        self.env = ScopaEnvironment(nomi[0], nomi[1])
        self.storico_mosse = []

    def _nome(self, g):
        return g.nome() if isinstance(g, BotAgent) else g

    def _is_umano(self, g):
        return isinstance(g, str) and g.lower() == "umano"

    def _agente(self, idx: int):
        """Ritorna l'agente corrispondente all'indice di turno."""
        if idx == 0:
            return self.giocatore_a if self.a_idx == 0 else self.giocatore_b
        else:
            return self.giocatore_b if self.a_idx == 0 else self.giocatore_a

    # ------------------------------------------------------------------
    # GIOCO
    # ------------------------------------------------------------------
    def gioca(self, seed: int = None) -> dict:
        """
        Esegue una partita completa.
        Ritorna: {
            "vincitore": 0|1|None (pareggio),
            "punteggi": [p0, p1],
            "scope": [s0, s1],
            "turni": N,
            "storico": [...]
        }
        """
        self.env.reset(seed=seed)
        self.storico_mosse = []

        if self.verbose:
            self._stampa_header()

        turno = 0
        while not self.env.partita_finita:
            idx = self.env.turno
            obs = self.env._get_observation(idx)
            agente = self._agente(idx)

            if self.verbose:
                self._stampa_stato(obs, turno, idx)

            if self._is_umano(agente):
                azione = self._chiedi_mossa_umano(obs)
            else:
                azione = agente.scegli_mossa(obs)
                if self.verbose:
                    self._stampa_mossa_bot(idx, azione)

            obs, reward, done, info = self.env.step(azione, idx)
            self.storico_mosse.append({
                "turno": turno,
                "giocatore": idx,
                "azione": azione,
                "reward": reward,
                "scopa": info.get("scopa", False)
            })

            if self.verbose and info.get("scopa"):
                nome = self.env._giocatore(idx).nome
                print(f"    *** 🧹 SCOOPA di {nome}! ***")

            turno += 1

        risultato = self._compila_risultato(turno)
        if self.verbose:
            self._stampa_finale(risultato)
        return risultato

    # ------------------------------------------------------------------
    # TORNEO BATCH
    # ------------------------------------------------------------------
    @staticmethod
    def torneo(bot_a, bot_b, n_partite: int = 100, seme_inizio: int = 0) -> dict:
        """
        Esegue n partite tra due bot, alternando chi inizia.
        Ritorna statistiche aggregate.
        """
        vittorie_a = 0
        vittorie_b = 0
        pareggi = 0
        punti_a = 0
        punti_b = 0
        scope_a = 0
        scope_b = 0

        for i in range(n_partite):
            a_inizia = (i % 2 == 0)
            partita = PartitaCLI(bot_a, bot_b, a_idx=0 if a_inizia else 1, verbose=False)
            ris = partita.gioca(seed=seme_inizio + i)

            # Mappa vincitore (0/1) ai nomi reali
            vincitore_nome = None
            if ris["vincitore"] is not None:
                # Chi è il vincitore in termini di bot?
                vincitore_reale = bot_a.nome() if (a_inizia and ris["vincitore"] == 0) or (not a_inizia and ris["vincitore"] == 1) else bot_b.nome()
                if vincitore_reale == bot_a.nome():
                    vittorie_a += 1
                else:
                    vittorie_b += 1
            else:
                pareggi += 1

            # Punti e scope (sempre mappati al bot corretto)
            p0, p1 = ris["punteggi"]
            if a_inizia:
                punti_a += p0
                punti_b += p1
                scope_a += ris["scope"][0]
                scope_b += ris["scope"][1]
            else:
                punti_a += p1
                punti_b += p0
                scope_a += ris["scope"][1]
                scope_b += ris["scope"][0]

        return {
            "bot_a": bot_a.nome(),
            "bot_b": bot_b.nome(),
            "partite": n_partite,
            "vittorie_a": vittorie_a,
            "vittorie_b": vittorie_b,
            "pareggi": pareggi,
            "media_punti_a": punti_a / n_partite,
            "media_punti_b": punti_b / n_partite,
            "media_scope_a": scope_a / n_partite,
            "media_scope_b": scope_b / n_partite,
        }

    # ------------------------------------------------------------------
    # STAMPA
    # ------------------------------------------------------------------
    def _stampa_header(self):
        nomi = [self.env.giocatore_0.nome, self.env.giocatore_1.nome]
        print(f"\n{'='*60}")
        print(f"  SCOPA BERGAMASCA")
        print(f"  {nomi[0]} vs {nomi[1]}")
        print(f"{'='*60}")

    def _stampa_stato(self, obs: dict, turno: int, idx: int):
        g = self.env._giocatore(idx)
        print(f"\n{'─'*60}")
        print(f"TURNO {turno:3d} | SMAZZATA {len(self.env.storico)//36 + 1} | MANO {self.env.mano_corrente}/2")
        print(f"Tocca a: {g.nome}")
        print(f"{'─'*60}")
        print(f"BANCO ({len(obs['banco'])}): {', '.join(str(c) for c in obs['banco']) or 'VUOTO'}")
        print(f"MAZZO: {obs['carte_mazzo']} carte rimanenti")
        print(f"SCOPE: {self.env.giocatore_0.nome}={self.env.giocatore_0.scope} | {self.env.giocatore_1.nome}={self.env.giocatore_1.scope}")
        print(f"PUNTI TOTALI: {self.env.punteggi[0]} | {self.env.punteggi[1]}")

        # Mostra mano umana se presente
        for i in [0, 1]:
            agente = self._agente(i)
            if self._is_umano(agente):
                obs_u = self.env._get_observation(i)
                print(f"\nMANO {self.env._giocatore(i).nome}:")
                for j, c in enumerate(obs_u["mano"]):
                    print(f"  [{j}] {c}")
        print(f"{'─'*60}")

    def _stampa_mossa_bot(self, idx: int, azione: tuple):
        carta, prese = azione
        nome = self.env._giocatore(idx).nome
        if prese is None:
            print(f"\n>>> {nome} gioca: {carta} → BALLA")
        else:
            scopa = " 🧹 SCOOPA!" if len(prese) == len(self.env.tavolo.banco) + len(prese) else ""
            prese_str = ", ".join(str(c) for c in prese)
            print(f"\n>>> {nome} gioca: {carta} → prende {prese_str}{scopa}")

    def _stampa_finale(self, ris: dict):
        print(f"\n{'='*60}")
        print("PARTITA FINITA")
        print(f"{'='*60}")
        p0, p1 = ris["punteggi"]
        print(f"{self.env.giocatore_0.nome}: {p0} punti")
        print(f"{self.env.giocatore_1.nome}: {p1} punti")
        if ris["vincitore"] == 0:
            print(f"\n🏆 VINCE {self.env.giocatore_0.nome}!")
        elif ris["vincitore"] == 1:
            print(f"\n🏆 VINCE {self.env.giocatore_1.nome}!")
        else:
            print("\n🤝 PAREGGIO!")
        print(f"{'='*60}")

    # ------------------------------------------------------------------
    # COMPILAZIONE RISULTATO
    # ------------------------------------------------------------------
    def _compila_risultato(self, turni: int) -> dict:
        p0, p1 = self.env.punteggi
        vincitore = 0 if p0 > p1 else (1 if p1 > p0 else None)
        return {
            "vincitore": vincitore,
            "punteggi": [p0, p1],
            "scope": [self.env.giocatore_0.scope, self.env.giocatore_1.scope],
            "turni": turni,
            "storico": self.storico_mosse,
        }

    # ------------------------------------------------------------------
    # INPUT UMANO
    # ------------------------------------------------------------------
    def _chiedi_mossa_umano(self, obs: dict) -> tuple:
        azioni = obs["azioni_legali"]

        print(f"\nAzioni disponibili:")
        for idx, (carta, prese) in enumerate(azioni):
            if prese is None:
                print(f"  {idx:2d}: {carta} → BALLA")
            else:
                prese_str = ", ".join(str(c) for c in prese)
                banco = obs["banco"]
                scopa = " 🧹 SCOOPA!" if len(prese) == len(banco) else ""
                print(f"  {idx:2d}: {carta} → prende {prese_str}{scopa}")

        while True:
            try:
                scelta = input(f"\nScegli (0-{len(azioni)-1}): ").strip()
                i = int(scelta)
                if 0 <= i < len(azioni):
                    return azioni[i]
            except ValueError:
                pass
            print("Scelta non valida, riprova.")