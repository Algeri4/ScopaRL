from scopa.ambiente import ScopaEnvironment
from scopa.carta import Carta
from bot.base import BotAgent


class PartitaCLI:
    """Gestisce una partita in modalità terminale: Umano vs Bot."""

    def __init__(self, nome_umano: str, bot: BotAgent, umano_idx: int = 0):
        """
        umano_idx: 0 = giocatore_0, 1 = giocatore_1.
        Di default l'umano è il giocatore 0 (inizia per secondo se mazziere è 1).
        """
        self.nome_umano = nome_umano
        self.bot = bot
        self.umano_idx = umano_idx

        # Crea ambiente: il nome del bot è sempre giocatore_1 in questo setup
        # Se umano_idx=0, bot è giocatore_1. Se umano_idx=1, bot è giocatore_0.
        nomi = [nome_umano, bot.nome()] if umano_idx == 0 else [bot.nome(), nome_umano]
        self.env = ScopaEnvironment(nomi[0], nomi[1])

    def gioca(self, seed: int = None):
        """Loop principale di gioco."""
        self.env.reset(seed=seed)
        print(f"\n{'='*60}")
        print(f"  SCOPA BERGAMASCA")
        print(f"  {self.nome_umano} vs {self.bot.nome()}")
        print(f"{'='*60}")

        turno = 0
        while not self.env.partita_finita:
            idx = self.env.turno
            obs = self.env._get_observation(idx)
            nome = self.env.giocatore_0.nome if idx == 0 else self.env.giocatore_1.nome

            self._stampa_stato(obs, turno, nome)

            if idx == self.umano_idx:
                azione = self._chiedi_mossa_umano(obs)
            else:
                azione = self.bot.scegli_mossa(obs)
                carta, prese = azione
                prese_str = f"prende {len(prese)} carte" if prese else "BALLA"
                print(f"\n>>> {nome} gioca: {carta} → {prese_str}")

            obs, reward, done, info = self.env.step(azione, idx)

            if info["scopa"]:
                print(f"    *** 🧹 SCOOPA di {nome}! ***")

            turno += 1

        self._stampa_finale()

    # ------------------------------------------------------------------
    # STAMPA
    # ------------------------------------------------------------------
    def _stampa_stato(self, obs: dict, turno: int, nome_attivo: str):
        g0, g1 = self.env.giocatore_0, self.env.giocatore_1
        print(f"\n{'─'*60}")
        print(f"TURNO {turno:3d} | SMAZZATA {len(self.env.storico)//36 + 1} | MANO {self.env.mano_corrente}/2")
        print(f"Tocca a: {nome_attivo}")
        print(f"{'─'*60}")
        print(f"BANCO ({len(obs['banco'])}): {', '.join(str(c) for c in obs['banco']) or 'VUOTO'}")
        print(f"MAZZO: {obs['carte_mazzo']} carte rimanenti")
        print(f"SCOPE: {g0.nome}={g0.scope} | {g1.nome}={g1.scope}")
        print(f"PUNTI TOTALI: {g0.nome}={self.env.punteggi[0]} | {g1.nome}={self.env.punteggi[1]}")

        # Mostra sempre la mano dell'umano, anche se non è il suo turno
        umano_obs = obs if obs["giocatore_idx"] == self.umano_idx else self.env._get_observation(self.umano_idx)
        print(f"\nLE TUE CARTE ({self.nome_umano}):")
        for i, c in enumerate(umano_obs["mano"]):
            print(f"  [{i}] {c}")
        print(f"{'─'*60}")

    def _stampa_finale(self):
        g0, g1 = self.env.giocatore_0, self.env.giocatore_1
        print(f"\n{'='*60}")
        print("PARTITA FINITA")
        print(f"{'='*60}")
        print(f"{g0.nome}: {self.env.punteggi[0]} punti")
        print(f"{g1.nome}: {self.env.punteggi[1]} punti")
        if self.env.punteggi[0] > self.env.punteggi[1]:
            print(f"\n🏆 VINCE {g0.nome}!")
        elif self.env.punteggi[1] > self.env.punteggi[0]:
            print(f"\n🏆 VINCE {g1.nome}!")
        else:
            print("\n🤝 PAREGGIO!")
        print(f"{'='*60}")

    # ------------------------------------------------------------------
    # INPUT UMANO
    # ------------------------------------------------------------------
    def _chiedi_mossa_umano(self, obs: dict):
        azioni = obs["azioni_legali"]

        print(f"\nAzioni disponibili:")
        for idx, (carta, prese) in enumerate(azioni):
            if prese is None:
                print(f"  {idx:2d}: {carta} → BALLA (carta sul banco)")
            else:
                prese_str = ", ".join(str(c) for c in prese)
                # Indica se è scopa
                banco = obs["banco"]
                scopa_flag = " 🧹 SCOOPA!" if len(prese) == len(banco) else ""
                print(f"  {idx:2d}: {carta} → prendi {prese_str}{scopa_flag}")

        while True:
            try:
                scelta = input(f"\nScegli azione (0-{len(azioni)-1}): ").strip()
                i = int(scelta)
                if 0 <= i < len(azioni):
                    return azioni[i]
            except ValueError:
                pass
            print("Scelta non valida.")
