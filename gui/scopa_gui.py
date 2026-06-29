# gui/scopa_gui.py
# Classe principale ScopaGUI - coordina tutti i moduli

import tkinter as tk
from tkinter import messagebox, font

from scopa.ambiente import ScopaEnvironment
from scopa.carta import Carta

from .costanti_gui import (
    W, H, CX, Y_AVV_MANO, Y_BANCO, Y_GIOC_MANO,
    X_MAZZETTO, Y_MAZZETTO_AVV, Y_MAZZETTO_GIOC,
    SPAZIO_CARTE, SLOT_MANO, SLOT_BANCO
)
from .caricatore import CaricatoreCarte
from .animazioni import GestoreAnimazioni
from .disegno import Disegnatore
from .menu_mano import mostra_menu


class ScopaGUI:
    def __init__(self, root: tk.Tk, bot_agent):
        self.root = root
        self.root.title("Scopa Bergamasca")
        self.root.configure(bg="#1b5e20")
        self.root.geometry(f"{W}x{H}")
        self.root.resizable(False, False)

        self.caricatore = CaricatoreCarte()
        self.bot = bot_agent
        self.env = ScopaEnvironment("Tu", bot_agent.nome())
        self.animatore = None
        self.disegnatore = None

        # Stato interazione
        self.carta_selezionata = None
        self.prese_selezionate = []
        self.attesa_input = False
        self.animazione_in_corso = False
        self.modo_selezione = False
        self.mostra_carte_bot = False

        # Slot fissi
        self.mano_giocatore_slots = [None] * SLOT_MANO
        self.mano_avversario_slots = [None] * SLOT_MANO
        self.banco_slots = [None] * SLOT_BANCO

        # Tracking scope cards
        self.scope_cartes_giocatore = []
        self.scope_cartes_bot = []

        # Flag pausa tra mani
        self.attesa_continua = False
        self.frame_menu = None

        # Buffer carte residue fine smazzata
        self.carte_residue_smazzata = []

        # Font
        self.ft_titolo = font.Font(family="Helvetica", size=14, weight="bold")
        self.ft_normale = font.Font(family="Helvetica", size=11)
        self.ft_piccolo = font.Font(family="Helvetica", size=10)
        self.ft_grande = font.Font(family="Helvetica", size=18, weight="bold")
        self.ft_scopa = font.Font(family="Helvetica", size=48, weight="bold")

        self._crea_widgets()
        self._inizia_partita()

    # ─────────────────────────────────────────────────────────────────────────
    # WIDGETS
    # ─────────────────────────────────────────────────────────────────────────

    def _crea_widgets(self):
        self.canvas = tk.Canvas(self.root, width=W, height=H, bg="#1b5e20",
                                highlightthickness=0)
        self.canvas.pack()

        self.animatore = GestoreAnimazioni(self.canvas, self.root, self.caricatore)
        self.disegnatore = Disegnatore(self.canvas, self.caricatore)

        # Info bar
        self.frame_info = tk.Frame(self.root, bg="#0d3b10", padx=10, pady=5)
        self.frame_info.place(x=0, y=0, width=W, height=40)

        self.lbl_info = tk.Label(
            self.frame_info, text="", font=self.ft_titolo,
            bg="#0d3b10", fg="white"
        )
        self.lbl_info.pack(side=tk.LEFT)

        self.btn_spia = tk.Button(
            self.frame_info, text="SPIA BOT", font=self.ft_piccolo,
            bg="#546e7a", fg="white", width=10,
            command=self._toggle_spia_bot
        )
        self.btn_spia.pack(side=tk.RIGHT)

        # Pulsanti
        self.frame_pulsanti = tk.Frame(self.root, bg="#0d3b10", pady=8)
        self.frame_pulsanti.place(x=0, y=H - 50, width=W, height=50)

        self.btn_gioca = tk.Button(
            self.frame_pulsanti, text="GIOCA", font=self.ft_titolo,
            bg="#ff6f00", fg="white", width=10, state=tk.DISABLED,
            command=self._conferma_mossa
        )
        self.btn_gioca.pack(side=tk.LEFT, padx=30)

        self.btn_annulla = tk.Button(
            self.frame_pulsanti, text="ANNULLA", font=self.ft_normale,
            bg="#546e7a", fg="white", width=8, state=tk.DISABLED,
            command=self._annulla_selezione
        )
        self.btn_annulla.pack(side=tk.LEFT, padx=10)

        self.btn_reset = tk.Button(
            self.frame_pulsanti, text="NUOVA PARTITA", font=self.ft_normale,
            bg="#388e3c", fg="white", command=self._inizia_partita
        )
        self.btn_reset.pack(side=tk.RIGHT, padx=30)

        self.btn_cambia_bot = tk.Button(
            self.frame_pulsanti, text="CAMBIA BOT", font=self.ft_normale,
            bg="#5e35b1", fg="white", command=self._cambia_bot
        )
        self.btn_cambia_bot.pack(side=tk.RIGHT, padx=10)

    def _toggle_spia_bot(self):
        self.mostra_carte_bot = not self.mostra_carte_bot
        if self.mostra_carte_bot:
            self.btn_spia.config(bg="#ff6f00", text="NASCONDI BOT")
        else:
            self.btn_spia.config(bg="#546e7a", text="SPIA BOT")
        self._ricostruisci_schermo()

    def _cambia_bot(self):
        from .main import avvia_gui
        self.root.destroy()
        avvia_gui()

    # ─────────────────────────────────────────────────────────────────────────
    # COORDINATE SLOT
    # ─────────────────────────────────────────────────────────────────────────

    def _calcola_x_mano(self, slot_idx, y_base):
        start_x = CX - ((SLOT_MANO - 1) * SPAZIO_CARTE) // 2 + 120
        return start_x + slot_idx * SPAZIO_CARTE

    def _calcola_x_banco(self, slot_idx):
        start_x = CX - ((SLOT_BANCO - 1) * SPAZIO_CARTE) // 2
        return start_x + slot_idx * SPAZIO_CARTE

    # ─────────────────────────────────────────────────────────────────────────
    # GESTIONE SLOT
    # ─────────────────────────────────────────────────────────────────────────

    def _trova_slot_libero_mano(self, slots):
        for i, c in enumerate(slots):
            if c is None:
                return i
        return None

    def _trova_slot_libero_banco(self):
        for i, c in enumerate(self.banco_slots):
            if c is None:
                return i
        return None

    def _carta_uguale(self, c1, c2):
        if c1 is None or c2 is None:
            return False
        return c1.seme == c2.seme and c1.valore == c2.valore

    def _trova_slot_carta_mano_giocatore(self, carta):
        for i, c in enumerate(self.mano_giocatore_slots):
            if self._carta_uguale(c, carta):
                return i
        return None

    def _trova_slot_carta_mano_avversario(self, carta):
        for i, c in enumerate(self.mano_avversario_slots):
            if self._carta_uguale(c, carta):
                return i
        return None

    def _trova_slot_carta_banco(self, carta):
        for i, c in enumerate(self.banco_slots):
            if self._carta_uguale(c, carta):
                return i
        return None

    def _sincronizza_mano_slots(self, giocatore_idx):
        g = self.env.giocatore_0 if giocatore_idx == 0 else self.env.giocatore_1
        mano = g.mano
        slots = self.mano_giocatore_slots if giocatore_idx == 0 else self.mano_avversario_slots

        for i in range(SLOT_MANO):
            if slots[i] is not None and slots[i] not in mano:
                slots[i] = None

        for carta in mano:
            if carta not in slots:
                slot = self._trova_slot_libero_mano(slots)
                if slot is not None:
                    slots[slot] = carta

    def _sincronizza_banco_slots(self):
        banco = self.env.tavolo.banco
        for i in range(SLOT_BANCO):
            if self.banco_slots[i] is not None and self.banco_slots[i] not in banco:
                self.banco_slots[i] = None
        for carta in banco:
            if carta not in self.banco_slots:
                slot = self._trova_slot_libero_banco()
                if slot is not None:
                    self.banco_slots[slot] = carta

    # ─────────────────────────────────────────────────────────────────────────
    # DISEGNO
    # ─────────────────────────────────────────────────────────────────────────

    def _ricostruisci_schermo(self):
        self.canvas.delete("sel")
        self.canvas.delete("lampeggio")
        self.canvas.delete("animazione")
        self.canvas.delete("effetto_scopa")
        self.disegnatore.clear()

        # Mazzetti
        self.disegnatore.mazzetto(X_MAZZETTO, Y_MAZZETTO_AVV,
                                  self.env.giocatore_1, self.scope_cartes_bot)
        self.disegnatore.mazzetto(X_MAZZETTO, Y_MAZZETTO_GIOC,
                                  self.env.giocatore_0, self.scope_cartes_giocatore)

        # Mano avversario
        if not self.attesa_continua:
            self.disegnatore.mano_avversario(
                self.mano_avversario_slots, self.mostra_carte_bot, Y_AVV_MANO, self._calcola_x_mano
            )

        # Banco
        self.disegnatore.banco(
            self.banco_slots, self.prese_selezionate, self._calcola_x_banco,
            self._carta_uguale, self.animazione_in_corso, self._clicca_banco
        )

        # Mano giocatore
        if not self.attesa_continua:
            self.disegnatore.mano_giocatore(
                self.mano_giocatore_slots, self.carta_selezionata, self._calcola_x_mano,
                self._carta_uguale, self.animazione_in_corso, self._clicca_mano
            )

    # ─────────────────────────────────────────────────────────────────────────
    # ANIMAZIONI MOSSA
    # ─────────────────────────────────────────────────────────────────────────

    def _animazione_giocatore_gioca(self, carta, prese, callback=None):
        idx = self._trova_slot_carta_mano_giocatore(carta)
        if idx is None:
            if callback:
                callback()
            return

        x_from = self._calcola_x_mano(idx, Y_GIOC_MANO)
        y_from = Y_GIOC_MANO
        self.mano_giocatore_slots[idx] = None
        self._ricostruisci_schermo()

        slot = self._trova_slot_libero_banco()
        if slot is None:
            slot = SLOT_BANCO - 1
        x_to = self._calcola_x_banco(slot)
        y_to = Y_BANCO

        self.animatore.vola(carta, x_from, y_from, x_to, y_to, 500,
                            lambda: self._fase2_giocatore(carta, prese, slot, callback))

    def _fase2_giocatore(self, carta, prese, slot, callback):
        if not prese:
            self.banco_slots[slot] = carta
            self._ricostruisci_schermo()
            if callback:
                callback()
            return

        self.banco_slots[slot] = carta
        self._ricostruisci_schermo()

        def posizione_banco(carta_obj):
            slot_c = self._trova_slot_carta_banco(carta_obj)
            if slot_c is not None:
                return (self._calcola_x_banco(slot_c), Y_BANCO)
            return (CX, Y_BANCO)

        carte_da_lampeggiare = list(prese) + [carta]
        self.animatore.lampeggia(carte_da_lampeggiare, posizione_banco, 1000,
                                 lambda: self._fase3_vola_mazzetto(carta, prese, slot,
                                                                   X_MAZZETTO, Y_MAZZETTO_GIOC, callback))

    def _fase3_vola_mazzetto(self, carta, prese, slot, x_mazzetto, y_mazzetto, callback):
        carte_gruppo = [carta] + list(prese)
        posizioni = {}
        for c in carte_gruppo:
            slot_c = self._trova_slot_carta_banco(c)
            if slot_c is not None:
                posizioni[(c.seme, c.valore)] = (self._calcola_x_banco(slot_c), Y_BANCO)
            else:
                posizioni[(c.seme, c.valore)] = (CX, Y_BANCO)

        for c in prese:
            s = self._trova_slot_carta_banco(c)
            if s is not None:
                self.banco_slots[s] = None
        self.banco_slots[slot] = None
        self._ricostruisci_schermo()

        self.animatore.vola_gruppo(carte_gruppo, posizioni, x_mazzetto, y_mazzetto, callback)

    def _animazione_bot_gioca(self, carta, prese, callback=None):
        idx = self._trova_slot_carta_mano_avversario(carta)
        if idx is not None:
            x_from = self._calcola_x_mano(idx, Y_AVV_MANO)
            y_from = Y_AVV_MANO
            self.mano_avversario_slots[idx] = None
        else:
            x_from = CX
            y_from = Y_AVV_MANO

        self._ricostruisci_schermo()

        slot = self._trova_slot_libero_banco()
        if slot is None:
            slot = SLOT_BANCO - 1
        x_to = self._calcola_x_banco(slot)
        y_to = Y_BANCO

        self.animatore.vola(carta, x_from, y_from, x_to, y_to, 600,
                            lambda: self._fase2_bot(carta, prese, slot, callback))

    def _fase2_bot(self, carta, prese, slot, callback):
        if not prese:
            self.banco_slots[slot] = carta
            self._ricostruisci_schermo()
            self.root.after(400, callback)
            return

        self.banco_slots[slot] = carta
        self._ricostruisci_schermo()

        def posizione_banco(carta_obj):
            slot_c = self._trova_slot_carta_banco(carta_obj)
            if slot_c is not None:
                return (self._calcola_x_banco(slot_c), Y_BANCO)
            return (CX, Y_BANCO)

        carte_da_lampeggiare = list(prese) + [carta]
        self.animatore.lampeggia(carte_da_lampeggiare, posizione_banco, 1000,
                                 lambda: self._fase3_bot_mazzetto(carta, prese, slot, callback))

    def _fase3_bot_mazzetto(self, carta, prese, slot, callback):
        carte_gruppo = [carta] + list(prese)
        posizioni = {}
        for c in carte_gruppo:
            slot_c = self._trova_slot_carta_banco(c)
            if slot_c is not None:
                posizioni[(c.seme, c.valore)] = (self._calcola_x_banco(slot_c), Y_BANCO)
            else:
                posizioni[(c.seme, c.valore)] = (CX, Y_BANCO)

        for c in prese:
            s = self._trova_slot_carta_banco(c)
            if s is not None:
                self.banco_slots[s] = None
        self.banco_slots[slot] = None
        self._ricostruisci_schermo()

        self.animatore.vola_gruppo(carte_gruppo, posizioni, X_MAZZETTO, Y_MAZZETTO_AVV, callback)

    def _animazione_fine_mano(self, carte_residue, callback):
        """
        Anima le carte residue della smazzata appena conclusa.
        NON legge da env.tavolo (è già pronto con la nuova mano).
        """
        if not carte_residue:
            if callback:
                callback()
            return

        # Cattura le posizioni attuali sul canvas
        posizioni_attuali = {}
        for carta in carte_residue:
            slot_idx = self._trova_slot_carta_banco(carta)
            if slot_idx is not None:
                posizioni_attuali[(carta.seme, carta.valore)] = (
                    self._calcola_x_banco(slot_idx), Y_BANCO
                )
            else:
                posizioni_attuali[(carta.seme, carta.valore)] = (CX, Y_BANCO)

        giocatore_idx = getattr(self, 'ultima_presaindice', 0)
        x_mazzetto = X_MAZZETTO
        y_mazzetto = Y_MAZZETTO_GIOC if giocatore_idx == 0 else Y_MAZZETTO_AVV

        # Svuota SOLO i slot della GUI, MAI il tavolo dell'ambiente
        for i in range(SLOT_BANCO):
            self.banco_slots[i] = None
        self._ricostruisci_schermo()

        # Crea le immagini di animazione alle posizioni ORIGINALI
        ids_gruppo = []
        for i, c in enumerate(carte_residue):
            photo = self.caricatore.get(c)
            x_orig, y_orig = posizioni_attuali[(c.seme, c.valore)]
            x_dest = x_mazzetto + (i % 3) * 2
            y_dest = y_mazzetto + (i % 3) * 2
            id_img = self.canvas.create_image(x_orig, y_orig, image=photo, tags="animazione")
            ids_gruppo.append((id_img, x_orig, y_orig, x_dest, y_dest))

        steps = 25
        delay = 800 // steps

        def step(i):
            if i >= steps:
                self.canvas.delete("animazione")
                self._ricostruisci_schermo()
                if callback:
                    callback()
                return
            for id_img, x_orig, y_orig, x_dest, y_dest in ids_gruppo:
                dx = (x_dest - x_orig) / steps
                dy = (y_dest - y_orig) / steps
                self.canvas.move(id_img, dx, dy)
            self.root.after(delay, lambda: step(i + 1))

        step(0)

    # ─────────────────────────────────────────────────────────────────────────
    # EFFETTO SCOPA
    # ─────────────────────────────────────────────────────────────────────────

    def _mostra_effetto_scopa(self, giocatore_idx, callback):
        self.animatore.effetto_scopa(CX, H // 2 - 50, self.ft_scopa, callback)

    # ─────────────────────────────────────────────────────────────────────────
    # LOGICA DI GIOCO
    # ─────────────────────────────────────────────────────────────────────────

    def _inizia_partita(self):
        self.env.reset(seed=None)
        self.carta_selezionata = None
        self.prese_selezionate = []
        self.attesa_input = False
        self.animazione_in_corso = False
        self.modo_selezione = False
        self.mostra_carte_bot = False
        self.mano_giocatore_slots = [None] * SLOT_MANO
        self.mano_avversario_slots = [None] * SLOT_MANO
        self.banco_slots = [None] * SLOT_BANCO
        self.scope_cartes_giocatore = []
        self.scope_cartes_bot = []
        self.ultima_presaindice = 0
        self.attesa_continua = False
        self.carte_residue_smazzata = []
        if self.frame_menu:
            self.frame_menu.destroy()
            self.frame_menu = None

        self.btn_spia.config(bg="#546e7a", text="SPIA BOT")

        self._sincronizza_mano_slots(0)
        self._sincronizza_mano_slots(1)
        self._sincronizza_banco_slots()
        self._ricostruisci_schermo()
        self._aggiorna_info()

        if self.env.turno != 0:
            self.root.after(800, self._turno_bot)

    def _aggiorna_info(self):
        g0, g1 = self.env.giocatore_0, self.env.giocatore_1
        bot = g1 if g1.tipo == "bot" else g0

        n_smazzata = 1
        if self.env.punteggi[0] > 0 or self.env.punteggi[1] > 0:
            n_smazzata = max(1, (self.env.punteggi[0] + self.env.punteggi[1]) // 3 + 1)

        info = (
            f"Smazzata {n_smazzata}  |  "
            f"Mano {self.env.mano_corrente}/2  |  "
            f"Turno: {'TU' if self.env.turno == 0 else bot.nome}  |  "
            f"Mazzo: {self.env.mazzo.rimanenti()}  |  "
            f"Punti: Tu={self.env.punteggi[0]}  {bot.nome}={self.env.punteggi[1]}"
        )
        self.lbl_info.config(text=info)

        if self.modo_selezione:
            self.btn_gioca.config(text="GIOCA", state=tk.NORMAL)
            self.btn_annulla.config(state=tk.NORMAL)
        else:
            self.btn_gioca.config(text="GIOCA", state=tk.DISABLED)
            self.btn_annulla.config(state=tk.DISABLED)

    # ─────────────────────────────────────────────────────────────────────────
    # INTERAZIONE UTENTE
    # ─────────────────────────────────────────────────────────────────────────

    def _clicca_mano(self, carta: Carta):
        if self.attesa_input or self.animazione_in_corso or self.env.turno != 0:
            return

        if self.modo_selezione and not self._carta_uguale(self.carta_selezionata, carta):
            self._annulla_selezione()

        self.carta_selezionata = carta

        azioni = self.env.get_legal_actions(0)
        azioni_carta = [a for a in azioni if self._carta_uguale(a[0], carta)]

        if not azioni_carta:
            self.carta_selezionata = None
            return

        solo_balla = all(a[1] is None for a in azioni_carta)
        if solo_balla:
            self._esegui_mossa_animata((carta, None), 0)
            return

        prese_possibili = [a for a in azioni_carta if a[1] is not None]
        if len(prese_possibili) == 1:
            self._esegui_mossa_animata((carta, prese_possibili[0][1]), 0)
            return

        self.modo_selezione = True
        self.prese_selezionate = []
        self._ricostruisci_schermo()
        self._aggiorna_info()

    def _clicca_banco(self, carta: Carta):
        if not self.modo_selezione:
            return
        if self.carta_selezionata is None:
            return

        idx_trovato = None
        for i, c in enumerate(self.prese_selezionate):
            if self._carta_uguale(c, carta):
                idx_trovato = i
                break

        if idx_trovato is not None:
            self.prese_selezionate.pop(idx_trovato)
        else:
            self.prese_selezionate.append(carta)

        azioni = self.env.get_legal_actions(0)
        azioni_carta = [a for a in azioni if self._carta_uguale(a[0], self.carta_selezionata)]

        combinazione_valida = None
        for a in azioni_carta:
            if a[1] is not None:
                azione_prese = set((c.seme, c.valore) for c in a[1])
                selezionate_set = set((c.seme, c.valore) for c in self.prese_selezionate)
                if azione_prese == selezionate_set:
                    combinazione_valida = a[1]
                    break

        if combinazione_valida:
            self.prese_selezionate = list(combinazione_valida)
            self._conferma_mossa()
            return
        else:
            self.btn_gioca.config(text="GIOCA", state=tk.DISABLED)

        self._ricostruisci_schermo()
        self._aggiorna_info()

    def _conferma_mossa(self):
        if not self.modo_selezione or self.carta_selezionata is None:
            return
        if not self.prese_selezionate:
            self._annulla_selezione()
            return

        azione = (self.carta_selezionata, self.prese_selezionate)
        self.carta_selezionata = None
        self.prese_selezionate = []
        self.modo_selezione = False
        self._esegui_mossa_animata(azione, 0)

    def _annulla_selezione(self):
        self.carta_selezionata = None
        self.prese_selezionate = []
        self.modo_selezione = False
        self._ricostruisci_schermo()
        self._aggiorna_info()

    # ─────────────────────────────────────────────────────────────────────────
    # ESECUZIONE MOSSA
    # ─────────────────────────────────────────────────────────────────────────

    def _esegui_mossa_animata(self, azione, giocatore_idx):
        carta, prese = azione
        self.animazione_in_corso = True
        self.attesa_input = True

        self.ultima_mossa_carta = carta
        self.ultima_mossa_prese = prese
        self.ultima_mossa_giocatore = giocatore_idx

        if giocatore_idx == 0:
            self._animazione_giocatore_gioca(carta, prese,
                                             lambda: self._completa_mossa(azione, giocatore_idx))
        else:
            self._animazione_bot_gioca(carta, prese,
                                       lambda: self._completa_mossa(azione, giocatore_idx))

    def _completa_mossa(self, azione, giocatore_idx):
        carta, prese = azione
        banco_prima = list(self.env.tavolo.banco)

        # --- Determina se questa mossa chiuderà la smazzata ---
        sara_fine_smazzata = False
        if self.env.mano_corrente == 2 and self.env.giocate_totali == 35:
            sara_fine_smazzata = True
        elif (self.env.mano_corrente == 1 and self.env.giocate_totali == 17
              and self.env.mazzo.rimanenti() == 0):
            sara_fine_smazzata = True

        # --- Calcola il banco finale (carte residue) prima che vengano resettate ---
        if sara_fine_smazzata:
            if prese:
                self.carte_residue_smazzata = [
                    c for c in banco_prima
                    if not any(self._carta_uguale(c, p) for p in prese)
                ]
            else:
                self.carte_residue_smazzata = banco_prima + [carta]
        else:
            self.carte_residue_smazzata = []

        try:
            obs, reward, done, info = self.env.step(azione, giocatore_idx)
        except ValueError as e:
            messagebox.showerror("Errore", str(e))
            self.animazione_in_corso = False
            self.attesa_input = False
            self._annulla_selezione()
            return

        if self.ultima_mossa_prese is not None and len(self.ultima_mossa_prese) > 0:
            self.ultima_presaindice = giocatore_idx

        if info.get("scopa"):
            if self.ultima_mossa_giocatore == 0:
                self.scope_cartes_giocatore.append(self.ultima_mossa_carta)
            else:
                self.scope_cartes_bot.append(self.ultima_mossa_carta)

            self._mostra_effetto_scopa(giocatore_idx,
                                       lambda: self._finisci_mossa(azione, giocatore_idx, info))
        else:
            self._finisci_mossa(azione, giocatore_idx, info)

    def _finisci_mossa(self, azione, giocatore_idx, info):
        partita_finita = self.env.partita_finita

        smazzata_finita = (self.env.giocate_totali == 0 and len(self.env.storico) == 0
                           and not self.attesa_continua)

        if smazzata_finita or partita_finita:
            # NON sincronizzare mani o banco: l'ambiente è già nella nuova smazzata!
            self.attesa_continua = True
            self._ricostruisci_schermo()
            self.root.after(300, lambda: self._animazione_fine_mano(
                self.carte_residue_smazzata,
                lambda: self._mostra_menu_mano(partita_finita)))
            return

        self._sincronizza_mano_slots(0)
        self._sincronizza_mano_slots(1)
        self._sincronizza_banco_slots()

        self.carta_selezionata = None
        self.prese_selezionate = []
        self.modo_selezione = False
        self.animazione_in_corso = False
        self.attesa_input = False

        self._ricostruisci_schermo()
        self._aggiorna_info()

        if self.env.turno != 0:
            self.root.after(600, self._turno_bot)

    def _turno_bot(self):
        if self.animazione_in_corso:
            return
        self.attesa_input = True
        self.animazione_in_corso = True
        obs = self.env._get_observation(self.env.turno)
        azione = self.bot.scegli_mossa(obs)
        self._esegui_mossa_animata(azione, self.env.turno)

    # ─────────────────────────────────────────────────────────────────────────
    # MENU FINE SMAZZATA
    # ─────────────────────────────────────────────────────────────────────────

    def _mostra_menu_mano(self, partita_finita=False):
        bot = self.env.giocatore_1 if self.env.giocatore_1.tipo == "bot" else self.env.giocatore_0

        def on_continua():
            self.frame_menu.destroy()
            self.frame_menu = None
            self.attesa_continua = False
            self.scope_cartes_giocatore = []
            self.scope_cartes_bot = []
            self._sincronizza_mano_slots(0)
            self._sincronizza_mano_slots(1)
            self._sincronizza_banco_slots()
            self._ricostruisci_schermo()
            self._aggiorna_info()
            if self.env.turno != 0:
                self.root.after(600, self._turno_bot)

        def on_riparti():
            self.frame_menu.destroy()
            self.frame_menu = None
            self._inizia_partita()

        def on_esci():
            self.root.destroy()

        def on_abbandona():
            self.frame_menu.destroy()
            self.frame_menu = None
            self._mostra_menu_mano(partita_finita=True)

        self.frame_menu = mostra_menu(
            self.root, self.frame_menu, partita_finita,
            self.env.ultima_smazzata, bot.nome,
            self.ft_titolo, self.ft_normale, self.ft_grande, self.ft_piccolo,
            on_continua, on_riparti, on_esci, on_abbandona
        )