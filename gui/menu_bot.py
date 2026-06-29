# gui/menu_bot.py
# Menu di selezione bot dinamico

import tkinter as tk
from tkinter import font
import os
import sys
import importlib
import inspect
from .costanti_gui import BASE_DIR, BOT_DIR


def scopri_bot():
    """Scansiona la cartella bot/ e trova tutte le classi bot disponibili."""
    bot_disponibili = {}
    if not os.path.exists(BOT_DIR):
        return bot_disponibili

    sys.path.insert(0, BASE_DIR)
    for filename in sorted(os.listdir(BOT_DIR)):
        if not filename.endswith(".py") or filename.startswith("__"):
            continue
        modulo_nome = f"bot.{filename[:-3]}"
        try:
            mod = importlib.import_module(modulo_nome)
            for nome, obj in inspect.getmembers(mod, inspect.isclass):
                if hasattr(obj, "scegli_mossa") and hasattr(obj, "nome"):
                    try:
                        istanza = obj()
                        nome_bot = istanza.nome()
                        bot_disponibili[nome_bot] = (modulo_nome, nome)
                    except Exception:
                        bot_disponibili[nome] = (modulo_nome, nome)
        except Exception as e:
            print(f"[WARN] Impossibile caricare {modulo_nome}: {e}")
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
        tk.Label(self.root, text="SCOPA BERGAMASCA",
                 font=self.ft_titolo, bg="#1b5e20", fg="#f1c40f").pack(pady=20)
        tk.Label(self.root, text="Seleziona il tuo avversario:",
                 font=self.ft_normale, bg="#1b5e20", fg="white").pack(pady=10)

        frame_lista = tk.Frame(self.root, bg="#0d3b10", padx=20, pady=20,
                               highlightbackground="#f1c40f", highlightthickness=2)
        frame_lista.pack(pady=10, padx=30, fill=tk.BOTH, expand=True)

        if not self.bot_disponibili:
            tk.Label(frame_lista, text="Nessun bot trovato in bot/",
                     font=self.ft_normale, bg="#0d3b10", fg="red").pack(pady=20)
            return

        self.bot_selezionato = tk.StringVar(value=list(self.bot_disponibili.keys())[0])

        for nome_bot, (modulo, classe) in self.bot_disponibili.items():
            rb = tk.Radiobutton(
                frame_lista, text=nome_bot, variable=self.bot_selezionato,
                value=nome_bot, font=self.ft_normale,
                bg="#0d3b10", fg="white", selectcolor="#1b5e20",
                activebackground="#0d3b10", activeforeground="#ffeb3b"
            )
            rb.pack(anchor=tk.W, pady=5)

        tk.Label(self.root, text=f"{len(self.bot_disponibili)} bot trovati",
                 font=self.ft_piccolo, bg="#1b5e20", fg="#aaaaaa").pack(pady=5)

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