#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI Scopa Bergamasca - Tkinter Canvas con animazioni reali
- Menu selezione bot dinamico (scansiona cartella bot/)
- Carte volano: mano -> banco (slot fisso) -> mazzetto
- Evidenziazione visibile della carta lanciata + prese
- Banco a 10 slot fissi, mano a 9 slot fissi
- Carte scopa in basso al mazzetto (ruotate 90°)
- Effetto visivo SCOPA! al centro schermo
- Fine mano: tutte le carte volano al mazzetto, poi menu, poi nuove carte su CONTINUA
- Pulsante SPIA BOT per mostrare/nascondere carte avversario
"""

import tkinter as tk
from tkinter import messagebox, font
from PIL import Image, ImageTk
import os
import sys
import importlib
import inspect

from scopa.ambiente import ScopaEnvironment
from scopa.carta import Carta

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAZIONE
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets", "carte")
BOT_DIR = os.path.join(BASE_DIR, "bot")

CARTA_L = 90
CARTA_H = 140
SPAZIO_CARTE = 100

NOMI_FILE = {
    1: "01_asso", 2: "02", 3: "03", 4: "04", 5: "05",
    6: "06", 7: "07", 8: "08_fante", 9: "09_cavallo", 10: "10_re"
}

SEMI_DIR = {
    "Denari": "denari", "denari": "denari",
    "Coppe": "coppe", "coppe": "coppe",
    "Spade": "spade", "spade": "spade",
    "Bastoni": "bastoni", "bastoni": "bastoni"
}


# ─────────────────────────────────────────────────────────────────────────────
# CARICAMENTO IMMAGINI
# ─────────────────────────────────────────────────────────────────────────────

class CaricatoreCarte:
    def __init__(self):
        self.cache = {}
        self.cache_img = {}
        self.retro = None
        self._carica_retro()

    def _carica_retro(self):
        img = Image.new("RGB", (CARTA_L, CARTA_H), "#1a5276")
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        for i in range(0, CARTA_L, 10):
            draw.line([(i, 0), (i, CARTA_H)], fill="#154360", width=1)
        for i in range(0, CARTA_H, 10):
            draw.line([(0, i), (CARTA_L, i)], fill="#154360", width=1)
        draw.rectangle([3, 3, CARTA_L - 3, CARTA_H - 3], outline="#f1c40f", width=2)
        self.retro = ImageTk.PhotoImage(img)

    def get(self, carta: Carta) -> ImageTk.PhotoImage:
        chiave = (carta.seme, carta.valore)
        if chiave in self.cache:
            return self.cache[chiave]

        seme_dir = SEMI_DIR.get(carta.seme, carta.seme.lower())
        nome = NOMI_FILE[carta.valore]
        percorso = os.path.join(ASSETS_DIR, seme_dir, f"{nome}.png")

        if os.path.exists(percorso):
            img = Image.open(percorso)
            img = img.resize((CARTA_L, CARTA_H), Image.Resampling.LANCZOS)
        else:
            img = Image.new("RGB", (CARTA_L, CARTA_H), "white")
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            draw.rectangle([2, 2, CARTA_L - 2, CARTA_H - 2], outline="black", width=2)
            draw.text((10, 10), f"{carta.valore}", fill="black")
            draw.text((10, 60), carta.seme[:3], fill="black")

        self.cache_img[chiave] = img
        photo = ImageTk.PhotoImage(img)
        self.cache[chiave] = photo
        return photo

    def get_ruotata(self, carta: Carta, angolo=90) -> ImageTk.PhotoImage:
        chiave = (carta.seme, carta.valore, angolo)
        if chiave in self.cache:
            return self.cache[chiave]

        chiave_orig = (carta.seme, carta.valore)
        if chiave_orig not in self.cache_img:
            self.get(carta)

        img_orig = self.cache_img[chiave_orig]
        img_ruotata = img_orig.rotate(angolo, expand=True, resample=Image.Resampling.BICUBIC)
        photo = ImageTk.PhotoImage(img_ruotata)
        self.cache[chiave] = photo
        return photo


# ─────────────────────────────────────────────────────────────────────────────
# DISCOVERY BOT DINAMICO
# ─────────────────────────────────────────────────────────────────────────────

def scopri_bot():
    """
    Scansiona la cartella bot/ e trova tutte le classi bot disponibili.
    Ritorna: dict {nome_visualizzato: (nome_modulo, nome_classe)}
    """
    bot_disponibili = {}

    if not os.path.exists(BOT_DIR):
        return bot_disponibili

    sys.path.insert(0, BASE_DIR)

    for filename in sorted(os.listdir(BOT_DIR)):
        if not filename.endswith(".py"):
            continue
        if filename.startswith("__"):
            continue

        modulo_nome = f"bot.{filename[:-3]}"
        try:
            mod = importlib.import_module(modulo_nome)
            for nome, obj in inspect.getmembers(mod, inspect.isclass):
                # Cerca classi che hanno i metodi tipici di un bot
                if hasattr(obj, "scegli_mossa") and hasattr(obj, "nome"):
                    # Istanzia per ottenere il nome
                    try:
                        istanza = obj()
                        nome_bot = istanza.nome()
                        bot_disponibili[nome_bot] = (modulo_nome, nome)
                    except Exception:
                        # Se non riesce a instanziare, usa il nome della classe
                        bot_disponibili[nome] = (modulo_nome, nome)
        except Exception as e:
            print(f"[WARN] Impossibile caricare {modulo_nome}: {e}")
            continue

    sys.path.pop(0)
    return bot_disponibili


def crea_bot(modulo_nome, classe_nome):
    """Istanzia un bot dato modulo e classe."""
    sys.path.insert(0, BASE_DIR)
    try:
        mod = importlib.import_module(modulo_nome)
        cls = getattr(mod, classe_nome)
        return cls()
    finally:
        sys.path.pop(0)


# ─────────────────────────────────────────────────────────────────────────────
# MENU SELEZIONE BOT
# ─────────────────────────────────────────────────────────────────────────────

class MenuSelezioneBot:
    def __init__(self, root, callback_selezione):
        self.root = root
        self.root.title("Scopa Bergamasca - Seleziona Bot")
        self.root.configure(bg="#1b5e20")
        self.root.geometry("500x500")
        self.root.resizable(False, False)
        self.callback = callback_selezione

        self.bot_disponibili = scopri_bot()

        self.ft_titolo = font.Font(family="Helvetica", size=16, weight="bold")
        self.ft_normale = font.Font(family="Helvetica", size=12)
        self.ft_piccolo = font.Font(family="Helvetica", size=10)

        self._crea_widgets()

    def _crea_widgets(self):
        # Titolo
        tk.Label(self.root, text="🃏 SCOPA BERGAMASCA",
                 font=self.ft_titolo, bg="#1b5e20", fg="#f1c40f").pack(pady=20)

        tk.Label(self.root, text="Seleziona il tuo avversario:",
                 font=self.ft_normale, bg="#1b5e20", fg="white").pack(pady=10)

        # Frame lista bot
        frame_lista = tk.Frame(self.root, bg="#0d3b10", padx=20, pady=20,
                               highlightbackground="#f1c40f", highlightthickness=2)
        frame_lista.pack(pady=10, padx=30, fill=tk.BOTH, expand=True)

        if not self.bot_disponibili:
            tk.Label(frame_lista, text="Nessun bot trovato in bot/",
                     font=self.ft_normale, bg="#0d3b10", fg="red").pack(pady=20)
            return

        self.bot_selezionato = tk.StringVar(value=list(self.bot_disponibili.keys())[0])

        for i, (nome_bot, (modulo, classe)) in enumerate(self.bot_disponibili.items()):
            rb = tk.Radiobutton(
                frame_lista, text=nome_bot, variable=self.bot_selezionato,
                value=nome_bot, font=self.ft_normale,
                bg="#0d3b10", fg="white", selectcolor="#1b5e20",
                activebackground="#0d3b10", activeforeground="#ffeb3b"
            )
            rb.pack(anchor=tk.W, pady=5)

        # Info
        tk.Label(self.root,
                 text=f"{len(self.bot_disponibili)} bot trovati",
                 font=self.ft_piccolo, bg="#1b5e20", fg="#aaaaaa").pack(pady=5)

        # Pulsanti
        frame_btn = tk.Frame(self.root, bg="#1b5e20")
        frame_btn.pack(pady=20)

        tk.Button(frame_btn, text="GIOCA", font=self.ft_titolo,
                  bg="#388e3c", fg="white", width=12,
                  command=self._conferma).pack(side=tk.LEFT, padx=10)

        tk.Button(frame_btn, text="ESCI", font=self.ft_normale,
                  bg="#d32f2f", fg="white", width=10,
                  command=self.root.destroy).pack(side=tk.LEFT, padx=10)

    def _conferma(self):
        nome_bot = self.bot_selezionato.get()
        modulo, classe = self.bot_disponibili[nome_bot]
        bot = crea_bot(modulo, classe)
        self.root.destroy()
        self.callback(bot)


# ─────────────────────────────────────────────────────────────────────────────
# GUI CON CANVAS E ANIMAZIONI
# ─────────────────────────────────────────────────────────────────────────────

class ScopaGUI:
    def __init__(self, root: tk.Tk, bot_agent):
        self.root = root
        self.root.title("Scopa Bergamasca")
        self.root.configure(bg="#1b5e20")
        self.root.geometry("1200x900")
        self.root.resizable(False, False)

        self.caricatore = CaricatoreCarte()
        self.bot = bot_agent
        self.env = ScopaEnvironment("Tu", bot_agent.nome())

        # Stato interazione
        self.carta_selezionata = None
        self.prese_selezionate = []
        self.attesa_input = False
        self.animazione_in_corso = False
        self.modo_selezione = False
        self.mostra_carte_bot = False

        # Slot fissi
        self.SLOT_MANO = 9
        self.SLOT_BANCO = 10
        self.mano_giocatore_slots = [None] * self.SLOT_MANO
        self.mano_avversario_slots = [None] * self.SLOT_MANO
        self.banco_slots = [None] * self.SLOT_BANCO

        # Tracking scope cards
        self.scope_cartes_giocatore = []
        self.scope_cartes_bot = []

        # Flag pausa tra mani
        self.attesa_continua = False

        # Font
        self.ft_titolo = font.Font(family="Helvetica", size=14, weight="bold")
        self.ft_normale = font.Font(family="Helvetica", size=11)
        self.ft_piccolo = font.Font(family="Helvetica", size=10)
        self.ft_grande = font.Font(family="Helvetica", size=18, weight="bold")
        self.ft_scopa = font.Font(family="Helvetica", size=48, weight="bold")

        # Dimensioni
        self.W = 1200
        self.H = 900
        self.CX = self.W // 2

        # Posizioni Y
        self.Y_AVV_MANO = 130
        self.Y_BANCO = 360
        self.Y_GIOC_MANO = 640

        # Posizioni mazzetti (sinistra)
        self.X_MAZZETTO = 100
        self.Y_MAZZETTO_AVV = 120
        self.Y_MAZZETTO_GIOC = 640

        self._crea_widgets()
        self._inizia_partita()

    def _crea_widgets(self):
        self.canvas = tk.Canvas(self.root, width=self.W, height=self.H, bg="#1b5e20",
                                highlightthickness=0)
        self.canvas.pack()

        # Info bar
        self.frame_info = tk.Frame(self.root, bg="#0d3b10", padx=10, pady=5)
        self.frame_info.place(x=0, y=0, width=self.W, height=40)

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
        self.frame_pulsanti.place(x=0, y=self.H - 50, width=self.W, height=50)

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

        # Pulsante cambia bot
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
        """Torna al menu di selezione bot."""
        self.root.destroy()
        avvia_gui()

    # ─────────────────────────────────────────────────────────────────────────
    # SLOT FISSI
    # ─────────────────────────────────────────────────────────────────────────

    def _calcola_x_mano(self, slot_idx, y_base):
        start_x = self.CX - ((self.SLOT_MANO - 1) * SPAZIO_CARTE) // 2 + 120
        return start_x + slot_idx * SPAZIO_CARTE

    def _calcola_x_banco(self, slot_idx):
        start_x = self.CX - ((self.SLOT_BANCO - 1) * SPAZIO_CARTE) // 2
        return start_x + slot_idx * SPAZIO_CARTE

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

        for i in range(self.SLOT_MANO):
            if slots[i] is not None and slots[i] not in mano:
                slots[i] = None

        for carta in mano:
            if carta not in slots:
                slot = self._trova_slot_libero_mano(slots)
                if slot is not None:
                    slots[slot] = carta

    def _sincronizza_banco_slots(self):
        banco = self.env.tavolo.banco
        for i in range(self.SLOT_BANCO):
            if self.banco_slots[i] is not None and self.banco_slots[i] not in banco:
                self.banco_slots[i] = None
        for carta in banco:
            if carta not in self.banco_slots:
                slot = self._trova_slot_libero_banco()
                if slot is not None:
                    self.banco_slots[slot] = carta

    # ─────────────────────────────────────────────────────────────────────────
    # DISEGNO SCENE
    # ─────────────────────────────────────────────────────────────────────────

    def _clear_canvas(self):
        self.canvas.delete("all")

    def _disegna_statico(self):
        self._disegna_mazzetto(self.X_MAZZETTO, self.Y_MAZZETTO_AVV, 1)
        self._disegna_mazzetto(self.X_MAZZETTO, self.Y_MAZZETTO_GIOC, 0)

    def _disegna_mazzetto(self, x, y, giocatore_idx):
        g = self.env.giocatore_0 if giocatore_idx == 0 else self.env.giocatore_1
        scope_cartes = self.scope_cartes_giocatore if giocatore_idx == 0 else self.scope_cartes_bot

        n_prese = len(g.prese)
        if n_prese > 0:
            for i in range(min(3, n_prese)):
                offset = i * 2
                self.canvas.create_image(x + offset, y + offset,
                                         image=self.caricatore.retro, tags="static")

        if scope_cartes:
            n_scope = len(scope_cartes)
            spazio_scope = max(15, 35 - n_scope * 4)
            y_scope = y + 75
            start_x_scope = x - ((n_scope - 1) * spazio_scope) // 2
            for i, carta in enumerate(scope_cartes):
                x_scope = start_x_scope + i * spazio_scope
                photo_ruotata = self.caricatore.get_ruotata(carta, 90)
                self.canvas.create_image(x_scope, y_scope, image=photo_ruotata, tags="static")

    def _disegna_mano_avversario(self):
        if self.attesa_continua:
            return
        for i in range(self.SLOT_MANO):
            carta = self.mano_avversario_slots[i]
            if carta is None:
                continue
            x = self._calcola_x_mano(i, self.Y_AVV_MANO)
            y = self.Y_AVV_MANO
            photo = self.caricatore.get(carta) if self.mostra_carte_bot else self.caricatore.retro
            self.canvas.create_image(x, y, image=photo, tags=("mano_avv", f"avv_{i}"))

    def _disegna_banco(self):
        for slot_idx, carta in enumerate(self.banco_slots):
            if carta is None:
                continue
            x = self._calcola_x_banco(slot_idx)
            y = self.Y_BANCO
            photo = self.caricatore.get(carta)

            if not self.animazione_in_corso:
                selezionata = any(self._carta_uguale(carta, ps) for ps in self.prese_selezionate)
                if selezionata:
                    self.canvas.create_rectangle(x - 50, y - 75, x + 50, y + 75,
                                                 outline="#ffeb3b", width=5, fill="",
                                                 tags=("sel", f"sel_{slot_idx}"))

            id_img = self.canvas.create_image(x, y, image=photo, tags=("banco", f"banco_{slot_idx}"))
            self.canvas.tag_bind(id_img, "<Button-1>", lambda e, c=carta: self._clicca_banco(c))

    def _disegna_mano_giocatore(self):
        if self.attesa_continua:
            return
        for i in range(self.SLOT_MANO):
            carta = self.mano_giocatore_slots[i]
            if carta is None:
                continue
            x = self._calcola_x_mano(i, self.Y_GIOC_MANO)
            y = self.Y_GIOC_MANO
            photo = self.caricatore.get(carta)

            if not self.animazione_in_corso:
                selezionata = self._carta_uguale(self.carta_selezionata, carta)
                if selezionata:
                    self.canvas.create_rectangle(x - 50, y - 75, x + 50, y + 75,
                                                 outline="#ffeb3b", width=5, fill="",
                                                 tags=("sel", f"sel_mano_{i}"))

            id_img = self.canvas.create_image(x, y, image=photo, tags=("mano", f"mano_{i}"))
            self.canvas.tag_bind(id_img, "<Button-1>", lambda e, c=carta: self._clicca_mano(c))

    # ─────────────────────────────────────────────────────────────────────────
    # ANIMAZIONI
    # ────────────────────────────────────────────────────────────────────────

    def _animazione_vola(self, carta, x_from, y_from, x_to, y_to, durata_ms=600, callback=None):
        photo = self.caricatore.get(carta)
        id_img = self.canvas.create_image(x_from, y_from, image=photo, tags="animazione")

        steps = 30
        dx = (x_to - x_from) / steps
        dy = (y_to - y_from) / steps
        delay = durata_ms // steps

        def step(i):
            if i >= steps:
                if callback:
                    callback()
                return
            self.canvas.move(id_img, dx, dy)
            self.root.after(delay, lambda: step(i + 1))

        step(0)
        return id_img

    def _lampeggia_carte(self, carte, durata_ms=1000, callback=None):
        if not carte:
            if callback:
                callback()
            return

        ids_lampeggio = []
        for carta in carte:
            slot = self._trova_slot_carta_banco(carta)
            if slot is not None:
                x = self._calcola_x_banco(slot)
                y = self.Y_BANCO
            else:
                x, y = self.CX, self.Y_BANCO

            rid = self.canvas.create_rectangle(x - 55, y - 80, x + 55, y + 80,
                                               outline="#ffeb3b", width=8, fill="",
                                               tags="lampeggio")
            ids_lampeggio.append(rid)

        flash_count = [0]

        def flash():
            if flash_count[0] >= 6:
                for rid in ids_lampeggio:
                    self.canvas.delete(rid)
                if callback:
                    callback()
                return
            for rid in ids_lampeggio:
                current = self.canvas.itemcget(rid, "outline")
                new_color = "#ffeb3b" if current == "#1b5e20" else "#1b5e20"
                self.canvas.itemconfig(rid, outline=new_color)
            flash_count[0] += 1
            self.root.after(durata_ms // 6, flash)

        flash()

    def _animazione_giocatore_gioca(self, carta, prese, callback=None):
        idx = self._trova_slot_carta_mano_giocatore(carta)
        if idx is None:
            if callback:
                callback()
            return

        x_from = self._calcola_x_mano(idx, self.Y_GIOC_MANO)
        y_from = self.Y_GIOC_MANO
        self.mano_giocatore_slots[idx] = None
        self._ricostruisci_schermo()

        slot = self._trova_slot_libero_banco()
        if slot is None:
            slot = self.SLOT_BANCO - 1
        x_to = self._calcola_x_banco(slot)
        y_to = self.Y_BANCO

        self._animazione_vola(carta, x_from, y_from, x_to, y_to, 500,
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

        carte_da_lampeggiare = list(prese) + [carta]
        self._lampeggia_carte(carte_da_lampeggiare, 1000,
                              lambda: self._fase3_vola_mazzetto(carta, prese, slot,
                                                                self.X_MAZZETTO,
                                                                self.Y_MAZZETTO_GIOC, callback))

    def _fase3_vola_mazzetto(self, carta, prese, slot, x_mazzetto, y_mazzetto, callback):
        self.canvas.delete("lampeggio")

        carte_gruppo = [carta] + list(prese)
        posizioni = {}
        for c in carte_gruppo:
            slot_c = self._trova_slot_carta_banco(c)
            if slot_c is not None:
                posizioni[(c.seme, c.valore)] = (self._calcola_x_banco(slot_c), self.Y_BANCO)
            else:
                posizioni[(c.seme, c.valore)] = (self.CX, self.Y_BANCO)

        for c in prese:
            s = self._trova_slot_carta_banco(c)
            if s is not None:
                self.banco_slots[s] = None
        self.banco_slots[slot] = None
        self._ricostruisci_schermo()

        ids_gruppo = []
        for i, c in enumerate(carte_gruppo):
            photo = self.caricatore.get(c)
            x_orig, y_orig = posizioni[(c.seme, c.valore)]
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

    def _animazione_bot_gioca(self, carta, prese, callback=None):
        idx = self._trova_slot_carta_mano_avversario(carta)
        if idx is not None:
            x_from = self._calcola_x_mano(idx, self.Y_AVV_MANO)
            y_from = self.Y_AVV_MANO
            self.mano_avversario_slots[idx] = None
        else:
            x_from = self.CX
            y_from = self.Y_AVV_MANO

        self._ricostruisci_schermo()

        slot = self._trova_slot_libero_banco()
        if slot is None:
            slot = self.SLOT_BANCO - 1
        x_to = self._calcola_x_banco(slot)
        y_to = self.Y_BANCO

        self._animazione_vola(carta, x_from, y_from, x_to, y_to, 600,
                              lambda: self._fase2_bot(carta, prese, slot, callback))

    def _fase2_bot(self, carta, prese, slot, callback):
        if not prese:
            self.banco_slots[slot] = carta
            self._ricostruisci_schermo()
            self.root.after(400, callback)
            return

        self.banco_slots[slot] = carta
        self._ricostruisci_schermo()

        carte_da_lampeggiare = list(prese) + [carta]
        self._lampeggia_carte(carte_da_lampeggiare, 1000,
                              lambda: self._fase3_bot_mazzetto(carta, prese, slot, callback))

    def _fase3_bot_mazzetto(self, carta, prese, slot, callback):
        self.canvas.delete("lampeggio")

        carte_gruppo = [carta] + list(prese)
        posizioni = {}
        for c in carte_gruppo:
            slot_c = self._trova_slot_carta_banco(c)
            if slot_c is not None:
                posizioni[(c.seme, c.valore)] = (self._calcola_x_banco(slot_c), self.Y_BANCO)
            else:
                posizioni[(c.seme, c.valore)] = (self.CX, self.Y_BANCO)

        for c in prese:
            s = self._trova_slot_carta_banco(c)
            if s is not None:
                self.banco_slots[s] = None
        self.banco_slots[slot] = None
        self._ricostruisci_schermo()

        ids_gruppo = []
        for i, c in enumerate(carte_gruppo):
            photo = self.caricatore.get(c)
            x_orig, y_orig = posizioni[(c.seme, c.valore)]
            x_dest = self.X_MAZZETTO + (i % 3) * 2
            y_dest = self.Y_MAZZETTO_AVV + (i % 3) * 2
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

    def _animazione_fine_mano(self, callback):
        carte_residue = [c for c in self.banco_slots if c is not None]
        if not carte_residue:
            if callback:
                callback()
            return

        giocatore_idx = getattr(self, 'ultima_presaindice', 0)
        x_mazzetto = self.X_MAZZETTO
        y_mazzetto = self.Y_MAZZETTO_GIOC if giocatore_idx == 0 else self.Y_MAZZETTO_AVV

        posizioni = {}
        for c in carte_residue:
            slot_c = self._trova_slot_carta_banco(c)
            if slot_c is not None:
                posizioni[(c.seme, c.valore)] = (self._calcola_x_banco(slot_c), self.Y_BANCO)
            else:
                posizioni[(c.seme, c.valore)] = (self.CX, self.Y_BANCO)

        for i in range(self.SLOT_BANCO):
            self.banco_slots[i] = None
        self._ricostruisci_schermo()

        ids_gruppo = []
        for i, c in enumerate(carte_residue):
            photo = self.caricatore.get(c)
            x_orig, y_orig = posizioni[(c.seme, c.valore)]
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

    def _ricostruisci_schermo(self):
        self.canvas.delete("sel")
        self.canvas.delete("lampeggio")
        self.canvas.delete("animazione")
        self.canvas.delete("effetto_scopa")
        self._clear_canvas()
        self._disegna_statico()
        self._disegna_mano_avversario()
        self._disegna_banco()
        self._disegna_mano_giocatore()

    # ─────────────────────────────────────────────────────────────────────────
    # EFFETTO SCOPA
    # ─────────────────────────────────────────────────────────────────────────

    def _mostra_effetto_scopa(self, giocatore_idx, callback):
        x = self.CX
        y = self.H // 2 - 50

        self.canvas.create_rectangle(
            x - 230, y - 70, x + 230, y + 70,
            fill="#b71c1c", outline="#ffeb3b", width=6,
            tags="effetto_scopa"
        )
        txt = self.canvas.create_text(
            x, y, text="SCOPA!", font=self.ft_scopa,
            fill="#ffeb3b", tags="effetto_scopa"
        )

        count = [0]

        def pulse():
            if count[0] >= 5:
                self.canvas.delete("effetto_scopa")
                if callback:
                    callback()
                return
            color = "#ffffff" if count[0] % 2 == 0 else "#ffeb3b"
            self.canvas.itemconfig(txt, fill=color)
            count[0] += 1
            self.root.after(250, pulse)

        pulse()

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
        self.mano_giocatore_slots = [None] * self.SLOT_MANO
        self.mano_avversario_slots = [None] * self.SLOT_MANO
        self.banco_slots = [None] * self.SLOT_BANCO
        self.scope_cartes_giocatore = []
        self.scope_cartes_bot = []
        self.ultima_presaindice = 0
        self.attesa_continua = False

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
    # ESECUZIONE MOSSA CON ANIMAZIONE
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
            self._sincronizza_banco_slots()
            self.attesa_continua = True
            self._ricostruisci_schermo()
            self.root.after(300, lambda: self._animazione_fine_mano(
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
        self.frame_menu = tk.Frame(self.root, bg="#0d3b10", padx=30, pady=30,
                                   highlightbackground="#f1c40f", highlightthickness=3)
        self.frame_menu.place(relx=0.5, rely=0.5, anchor="center", width=600, height=560)

        g0, g1 = self.env.giocatore_0, self.env.giocatore_1
        bot = g1 if g1.tipo == "bot" else g0

        if partita_finita:
            titolo = "PARTITA FINITA"
        else:
            titolo = "FINE SMAZZATA"

        tk.Label(self.frame_menu, text=titolo, font=self.ft_grande,
                 bg="#0d3b10", fg="#f1c40f").pack(pady=10)

        # ── Recupera dati dalla smazzata appena conclusa ──
        dati = self.env.ultima_smazzata
        if dati is None:
            tk.Label(self.frame_menu, text="Dati smazzata non disponibili",
                     font=self.ft_normale, bg="#0d3b10", fg="red").pack()
            self._crea_pulsanti_menu(partita_finita)
            return

        prese_0 = dati["prese_0"]
        prese_1 = dati["prese_1"]
        scope_0 = dati["scope_0"]
        scope_1 = dati["scope_1"]
        punti_mano = dati["punti_mano"]
        punti_totali = dati["punti_totali"]
        dettagli = dati["dettagli"]

        # Calcola statistiche (confronto case-insensitive per i semi)
        carte_0 = len(prese_0)
        carte_1 = len(prese_1)
        denari_0 = sum(1 for c in prese_0 if c.seme.lower() == "denari")
        denari_1 = sum(1 for c in prese_1 if c.seme.lower() == "denari")
        settebello_0 = any(c.seme.lower() == "denari" and c.valore == 7 for c in prese_0)
        settebello_1 = any(c.seme.lower() == "denari" and c.valore == 7 for c in prese_1)
        prim_0 = dettagli["p0"]["primiera_valore"]
        prim_1 = dettagli["p1"]["primiera_valore"]

        tk.Label(self.frame_menu, text="DETTAGLIO PUNTI SMAZZATA:",
                 font=self.ft_titolo, bg="#0d3b10", fg="#ffeb3b").pack(pady=(10, 5))

        frame_dettagli = tk.Frame(self.frame_menu, bg="#0d3b10")
        frame_dettagli.pack(pady=5)

        tk.Label(frame_dettagli, text=f"{'':15s} {'TU':10s} {bot.nome:15s}",
                 font=self.ft_titolo, bg="#0d3b10", fg="white").grid(
                     row=0, column=0, columnspan=3, pady=5)

        tk.Label(frame_dettagli, text=f"{'Carte:':15s} {carte_0:10d} {carte_1:15d}",
                 font=self.ft_normale, bg="#0d3b10", fg="white").grid(
                     row=1, column=0, columnspan=3, sticky="w")

        tk.Label(frame_dettagli, text=f"{'Denari:':15s} {denari_0:10d} {denari_1:15d}",
                 font=self.ft_normale, bg="#0d3b10", fg="white").grid(
                     row=2, column=0, columnspan=3, sticky="w")

        tk.Label(frame_dettagli,
                 text=f"{'Settebello:':15s} {'SÌ' if settebello_0 else 'NO':10s} "
                      f"{'SÌ' if settebello_1 else 'NO':15s}",
                 font=self.ft_normale, bg="#0d3b10", fg="white").grid(
                     row=3, column=0, columnspan=3, sticky="w")

        tk.Label(frame_dettagli, text=f"{'Primiera:':15s} {prim_0:10d} {prim_1:15d}",
                 font=self.ft_normale, bg="#0d3b10", fg="white").grid(
                     row=4, column=0, columnspan=3, sticky="w")

        tk.Label(frame_dettagli, text=f"{'Scope:':15s} {scope_0:10d} {scope_1:15d}",
                 font=self.ft_normale, bg="#0d3b10", fg="white").grid(
                     row=5, column=0, columnspan=3, sticky="w")

        tk.Label(frame_dettagli, text=f"{'Punti mano:':15s} {punti_mano[0]:10d} {punti_mano[1]:15d}",
                 font=self.ft_normale, bg="#0d3b10", fg="white").grid(
                     row=6, column=0, columnspan=3, sticky="w")

        tk.Label(frame_dettagli, text=f"{'─' * 42}",
                 font=self.ft_normale, bg="#0d3b10", fg="#f1c40f").grid(
                     row=7, column=0, columnspan=3, pady=5)

        tk.Label(frame_dettagli,
                 text=f"{'TOTALE:':15s} {punti_totali[0]:10d} {punti_totali[1]:15d}",
                 font=self.ft_grande, bg="#0d3b10", fg="#4caf50").grid(
                     row=8, column=0, columnspan=3, sticky="w")

        self._crea_pulsanti_menu(partita_finita, punti_totali)

    def _crea_pulsanti_menu(self, partita_finita, punti_totali=None):
        frame_btn = tk.Frame(self.frame_menu, bg="#0d3b10")
        frame_btn.pack(pady=20)

        if partita_finita:
            if punti_totali:
                vincitore = 0 if punti_totali[0] > punti_totali[1] else 1
                vinc_nome = "TU" if vincitore == 0 else self.env.giocatore_1.nome
                tk.Label(self.frame_menu,
                         text=f"VINCE: {vinc_nome}!",
                         font=self.ft_grande, bg="#0d3b10", fg="#ffeb3b").pack(pady=5)

            tk.Button(frame_btn, text="RIPARTI", font=self.ft_titolo,
                      bg="#388e3c", fg="white", width=12, command=self._riparti).pack(side=tk.LEFT, padx=10)
            tk.Button(frame_btn, text="ESCI", font=self.ft_titolo,
                      bg="#d32f2f", fg="white", width=12, command=self._esci).pack(side=tk.LEFT, padx=10)
        else:
            tk.Button(frame_btn, text="CONTINUA", font=self.ft_titolo,
                      bg="#388e3c", fg="white", width=12, command=self._continua).pack(side=tk.LEFT, padx=10)
            tk.Button(frame_btn, text="ABBANDONA", font=self.ft_titolo,
                      bg="#d32f2f", fg="white", width=12, command=self._abbandona).pack(side=tk.LEFT, padx=10)

    def _continua(self):
        self.frame_menu.destroy()
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

    def _riparti(self):
        self.frame_menu.destroy()
        self._inizia_partita()

    def _esci(self):
        self.root.destroy()

    def _abbandona(self):
        self.frame_menu.destroy()
        self._mostra_menu_mano(partita_finita=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def avvia_gui(bot=None):
    """
    Avvia il gioco. Se bot è None, mostra il menu di selezione.
    """
    if bot is None:
        root = tk.Tk()

        def on_bot_selezionato(bot_scelto):
            root_game = tk.Tk()
            ScopaGUI(root_game, bot_scelto)
            root_game.mainloop()

        MenuSelezioneBot(root, on_bot_selezionato)
        root.mainloop()
    else:
        root = tk.Tk()
        ScopaGUI(root, bot)
        root.mainloop()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scopa Bergamasca GUI")
    parser.add_argument("--bot", type=str, default=None,
                        help="Nome del bot da usare (es. 'BotCasuale', 'BotGreedy')")
    args = parser.parse_args()

    if args.bot:
        # Cerca il bot tra quelli disponibili
        bot_disponibili = scopri_bot()
        bot_trovato = None
        for nome, (modulo, classe) in bot_disponibili.items():
            if nome == args.bot or classe == args.bot:
                bot_trovato = crea_bot(modulo, classe)
                break
        if bot_trovato:
            avvia_gui(bot_trovato)
        else:
            print(f"Bot '{args.bot}' non trovato. Bot disponibili: {list(bot_disponibili.keys())}")
            avvia_gui()
    else:
        avvia_gui()
