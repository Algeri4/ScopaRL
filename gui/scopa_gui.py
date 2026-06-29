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
        start_x = CX - ((