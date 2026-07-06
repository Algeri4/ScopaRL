# gui/menu_bot.py
# Menu di selezione bot dinamico - con supporto BotRL

import tkinter as tk
from tkinter import font, messagebox
import os
import sys
import importlib
import inspect
from .costanti_gui import BASE_DIR, BOT_DIR


def scopri_bot():
    """Scansiona la cartella bot/ e botRL/ e trova tutte le classi bot disponibili."""
    bot_disponibili = {}

    # ═══ Bot classici in bot/ ═══
    if os.path.exists(BOT_DIR):
        sys.path.insert(0, BASE_DIR)
        for filename in sorted(os.listdir(BOT_DIR)):
            if not filename.endswith(".py") or filename.startswith("__"):
                continue
            modulo_nome = f"bot.{filename[:-3]}"
            try:
                mod = importlib.import_module(modulo_nome)
                for nome, obj in inspect.getmembers(mod, inspect.isclass):
                    if nome == "BotAgent":
                        continue
                    if hasattr(obj, "scegli_mossa") and hasattr(obj, "nome"):
                        try:
                            istanza = obj()
                            nome_bot = istanza.nome()
                            bot_disponibili[nome_bot] = (modulo_nome, nome, None)
                        except Exception:
                            bot_disponibili[nome] = (modulo_nome, nome, None)
            except Exception as e:
                print(f"[WARN] Impossibile caricare {modulo_nome}: {e}")
        sys.path.pop(0)

    # ═══ BotRL in botRL/ ═══
    botrl_path = os.path.join(BASE_DIR, "botRL")
    if os.path.exists(botrl_path):
        checkpoint_dir = os.path.join(botrl_path, "checkpoints")
        if os.path.exists(checkpoint_dir):
            ckpts = [f for f in os.listdir(checkpoint_dir) if f.endswith('.pt')]
            ckpts.sort()

            for ckpt in ckpts:
                nome_ckpt = ckpt.replace('.pt', '')
                nome_display = f"BotRL ({nome_ckpt})"
                bot_disponibili[nome_display] = ("botRL.bot_rl", "BotRL", ckpt)

    return bot_disponibili


def crea_bot(modulo_nome, classe_nome, checkpoint=None, device='cpu'):
    """Istanzia un bot dato modulo e classe."""
    sys.path.insert(0, BASE_DIR)
    try:
        mod = importlib.import_module(modulo_nome)
        cls = getattr(mod, classe_nome)

        # ═══ SPECIALE: BotRL richiede checkpoint ═══
        if classe_nome == "BotRL":
            if checkpoint is None:
                raise ValueError("BotRL richiede un checkpoint!")

            checkpoint_path = os.path.join(BASE_DIR, "botRL", "checkpoints", checkpoint)
            if not os.path.exists(checkpoint_path):
                checkpoint_path = checkpoint

            return cls.from_checkpoint(checkpoint_path, device=device)

        return cls()
    finally:
        sys.path.pop(0)


class MenuSelezioneBot:
    BG_MAIN = "#0f2818"
    BG_CARD = "#163d22"
    BG_CARD_HOVER = "#1e5230"
    BG_CARD_SELECTED = "#2a6b3c"
    ACCENT_GOLD = "#f1c40f"
    TEXT_WHITE = "#ffffff"
    TEXT_GRAY = "#b0b0b0"
    BTN_GREEN = "#27ae60"
    BTN_GREEN_HOVER = "#2ecc71"
    BTN_RED = "#c0392b"
    BTN_RED_HOVER = "#e74c3c"
    BTN_RL = "#8e44ad"
    BTN_RL_HOVER = "#9b59b6"

    def __init__(self, root, callback_selezione):
        self.root = root
        self.root.title("Scopa Bergamasca - Seleziona Bot")
        self.root.configure(bg=self.BG_MAIN)
        self.root.geometry("520x700")
        self.root.resizable(False, False)
        self.callback = callback_selezione

        self.bot_disponibili = scopri_bot()

        self.ft_titolo = font.Font(family="Helvetica", size=22, weight="bold")
        self.ft_sottotitolo = font.Font(family="Helvetica", size=13)
        self.ft_bot = font.Font(family="Helvetica", size=12, weight="bold")
        self.ft_desc = font.Font(family="Helvetica", size=10)
        self.ft_contatore = font.Font(family="Helvetica", size=11)
        self.ft_btn = font.Font(family="Helvetica", size=14, weight="bold")
        self.ft_ckpt = font.Font(family="Helvetica", size=9)

        self._crea_widgets()

    def _crea_widgets(self):
        # Header
        header = tk.Frame(self.root, bg=self.BG_MAIN, height=100)
        header.pack(fill=tk.X, pady=(25, 5))
        header.pack_propagate(False)

        tk.Label(header, text="♠  SCOPA BERGAMASCA  ♦",
                 font=self.ft_titolo, bg=self.BG_MAIN,
                 fg=self.ACCENT_GOLD).pack(pady=(10, 0))

        tk.Label(header, text="Seleziona il tuo avversario",
                 font=self.ft_sottotitolo, bg=self.BG_MAIN,
                 fg=self.TEXT_GRAY).pack(pady=(5, 0))

        # Separatore RL
        tk.Frame(self.root, bg=self.ACCENT_GOLD, height=2).pack(fill=tk.X, padx=35, pady=10)

        # Sezione BotRL
        self._crea_sezione_rl()

        # Separatore
        tk.Frame(self.root, bg=self.ACCENT_GOLD, height=2).pack(fill=tk.X, padx=35, pady=10)

        # Sezione bot classici
        self._crea_sezione_classici()

        # Pulsanti
        frame_btn = tk.Frame(self.root, bg=self.BG_MAIN)
        frame_btn.pack(pady=(10, 25))

        self.btn_esci = tk.Label(frame_btn, text="  ESCI  ",
                                 font=self.ft_btn, bg=self.BTN_RED,
                                 fg=self.TEXT_WHITE, cursor="hand2",
                                 padx=30, pady=10)
        self.btn_esci.pack(side=tk.LEFT, padx=12)
        self.btn_esci.bind("<Button-1>", lambda e: self.root.destroy())
        self.btn_esci.bind("<Enter>", lambda e: self.btn_esci.config(bg=self.BTN_RL_HOVER))
        self.btn_esci.bind("<Leave>", lambda e: self.btn_esci.config(bg=self.BTN_RED))

    def _crea_sezione_rl(self):
        """Crea la sezione per selezionare BotRL."""
        frame_rl = tk.Frame(self.root, bg=self.BG_MAIN)
        frame_rl.pack(fill=tk.X, padx=35, pady=(5, 5))

        tk.Label(frame_rl, text="🤖 BOT RL (Reinforcement Learning)",
                 font=self.ft_bot, bg=self.BG_MAIN,
                 fg=self.ACCENT_GOLD).pack(anchor="w")

        # Filtra solo i BotRL
        bot_rl = {k: v for k, v in self.bot_disponibili.items() if k.startswith("BotRL")}

        if not bot_rl:
            tk.Label(frame_rl, text="Nessun checkpoint trovato.\nAllenare prima con: python train.py",
                     font=self.ft_desc, bg=self.BG_MAIN, fg="#e74c3c",
                     justify="center").pack(pady=10)
            return

        # Radio buttons per checkpoint
        self.ckpt_selezionato = tk.StringVar(value=list(bot_rl.keys())[0])

        for nome_display, (modulo, classe, ckpt) in bot_rl.items():
            rb = tk.Radiobutton(frame_rl, text=nome_display,
                                variable=self.ckpt_selezionato,
                                value=nome_display, bg=self.BG_MAIN,
                                fg=self.TEXT_WHITE,
                                selectcolor=self.BG_CARD_SELECTED,
                                font=self.ft_ckpt, anchor="w")
            rb.pack(fill=tk.X, padx=20, pady=2)

        # Pulsante gioca RL
        self.btn_gioca_rl = tk.Label(frame_rl, text="  GIOCA CON BotRL  ",
                                     font=self.ft_btn, bg=self.BTN_RL,
                                     fg=self.TEXT_WHITE, cursor="hand2",
                                     padx=20, pady=8)
        self.btn_gioca_rl.pack(pady=(10, 5))
        self.btn_gioca_rl.bind("<Button-1>", lambda e: self._conferma_rl())
        self.btn_gioca_rl.bind("<Enter>", lambda e: self.btn_gioca_rl.config(bg=self.BTN_RL_HOVER))
        self.btn_gioca_rl.bind("<Leave>", lambda e: self.btn_gioca_rl.config(bg=self.BTN_RL))

    def _crea_sezione_classici(self):
        """Crea la sezione per i bot classici."""
        tk.Label(self.root, text="🎴 BOT CLASSICI",
                 font=self.ft_bot, bg=self.BG_MAIN,
                 fg=self.ACCENT_GOLD).pack(anchor="w", padx=35)

        # Filtra bot classici
        bot_classici = {k: v for k, v in self.bot_disponibili.items() if not k.startswith("BotRL")}

        frame_container = tk.Frame(self.root, bg=self.BG_MAIN)
        frame_container.pack(pady=10, padx=35, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(frame_container, bg=self.BG_MAIN,
                                highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(frame_container, orient=tk.VERTICAL,
                                 command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=self.BG_MAIN)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw", width=440)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.bot_selezionato = tk.StringVar()
        self.card_widgets = {}

        if not bot_classici:
            tk.Label(self.scroll_frame, text="Nessun bot trovato in bot/",
                     font=self.ft_sottotitolo, bg=self.BG_MAIN, fg="#e74c3c").pack(pady=40)
        else:
            self.bot_selezionato.set(list(bot_classici.keys())[0])
            for idx, (nome_bot, data) in enumerate(bot_classici.items()):
                self._crea_card_bot(idx, nome_bot)

        # Contatore
        n_bot = len(bot_classici)
        tk.Label(self.root,
                 text=f"{n_bot} bot classici disponibili",
                 font=self.ft_contatore, bg=self.BG_MAIN,
                 fg=self.TEXT_GRAY).pack(pady=(0, 5))

        # Pulsante gioca classico
        frame_btn = tk.Frame(self.root, bg=self.BG_MAIN)
        frame_btn.pack(pady=5)

        self.btn_gioca = tk.Label(frame_btn, text="  GIOCA  ",
                                  font=self.ft_btn, bg=self.BTN_GREEN,
                                  fg=self.TEXT_WHITE, cursor="hand2",
                                  padx=30, pady=10)
        self.btn_gioca.pack(side=tk.LEFT, padx=12)
        self.btn_gioca.bind("<Button-1>", lambda e: self._conferma())
        self.btn_gioca.bind("<Enter>", lambda e: self.btn_gioca.config(bg=self.BTN_GREEN_HOVER))
        self.btn_gioca.bind("<Leave>", lambda e: self.btn_gioca.config(bg=self.BTN_GREEN))

        self._evidenzia_selezione()

    def _crea_card_bot(self, idx, nome_bot):
        """Crea una card cliccabile per ogni bot."""
        card = tk.Frame(self.scroll_frame, bg=self.BG_CARD,
                        padx=15, pady=12, cursor="hand2")
        card.pack(fill=tk.X, pady=4)
        card.bind("<Button-1>", lambda e, n=nome_bot: self._seleziona(n))
        card.bind("<Enter>", lambda e, c=card, n=nome_bot: self._on_hover(c, n))
        card.bind("<Leave>", lambda e, c=card, n=nome_bot: self._on_leave(c, n))

        indicatore = tk.Canvas(card, width=20, height=20, bg=self.BG_CARD,
                               highlightthickness=0)
        indicatore.pack(side=tk.LEFT, padx=(0, 12))
        self._disegna_indicatore(indicatore, selezionato=False)

        testo_frame = tk.Frame(card, bg=self.BG_CARD)
        testo_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        lbl_nome = tk.Label(testo_frame, text=nome_bot,
                            font=self.ft_bot, bg=self.BG_CARD,
                            fg=self.TEXT_WHITE, anchor="w")
        lbl_nome.pack(fill=tk.X)
        lbl_nome.bind("<Button-1>", lambda e, n=nome_bot: self._seleziona(n))

        difficolta = self._stima_difficolta(nome_bot)
        lbl_diff = tk.Label(testo_frame, text=difficolta,
                            font=self.ft_desc, bg=self.BG_CARD,
                            fg=self.TEXT_GRAY, anchor="w")
        lbl_diff.pack(fill=tk.X)
        lbl_diff.bind("<Button-1>", lambda e, n=nome_bot: self._seleziona(n))

        self.card_widgets[nome_bot] = {
            "card": card,
            "indicatore": indicatore,
            "nome": lbl_nome,
            "diff": lbl_diff
        }

    def _disegna_indicatore(self, canvas, selezionato):
        canvas.delete("all")
        if selezionato:
            canvas.create_oval(2, 2, 18, 18, fill=self.ACCENT_GOLD, outline="")
            canvas.create_oval(6, 6, 14, 14, fill=self.BG_CARD_SELECTED, outline="")
        else:
            canvas.create_oval(2, 2, 18, 18, fill="", outline=self.TEXT_GRAY, width=2)

    def _stima_difficolta(self, nome_bot):
        nome = nome_bot.lower()
        if "casuale" in nome:
            return "🎲 Facile  ·  Mosse casuali"
        elif "greedy" in nome:
            return "🧠 Medio  ·  Euristica base"
        elif "predatore" in nome:
            return "🧠 Medio  ·  Euristica aggressiva"
        elif "intelligente1" in nome:
            return "🧠 Difficile  ·  Sicurezza anti-scopa"
        elif "intelligente2" in nome:
            return "🧠 Difficile  ·  Memoria + banchi morti"
        elif "rl" in nome or "ppo" in nome or "reinforce" in nome:
            return "🤖 Impossibile  ·  Reinforcement Learning"
        else:
            return "🧠 Medio  ·  Bot generico"

    def _seleziona(self, nome_bot):
        self.bot_selezionato.set(nome_bot)
        self._evidenzia_selezione()

    def _evidenzia_selezione(self):
        for nome, widgets in self.card_widgets.items():
            sel = (nome == self.bot_selezionato.get())
            bg = self.BG_CARD_SELECTED if sel else self.BG_CARD
            widgets["card"].config(bg=bg)
            widgets["nome"].config(bg=bg)
            widgets["diff"].config(bg=bg)
            widgets["indicatore"].config(bg=bg)
            self._disegna_indicatore(widgets["indicatore"], sel)

    def _on_hover(self, card, nome_bot):
        if nome_bot != self.bot_selezionato.get():
            card.config(bg=self.BG_CARD_HOVER)
            widgets = self.card_widgets[nome_bot]
            widgets["nome"].config(bg=self.BG_CARD_HOVER)
            widgets["diff"].config(bg=self.BG_CARD_HOVER)
            widgets["indicatore"].config(bg=self.BG_CARD_HOVER)

    def _on_leave(self, card, nome_bot):
        sel = (nome_bot == self.bot_selezionato.get())
        bg = self.BG_CARD_SELECTED if sel else self.BG_CARD
        card.config(bg=bg)
        widgets = self.card_widgets[nome_bot]
        widgets["nome"].config(bg=bg)
        widgets["diff"].config(bg=bg)
        widgets["indicatore"].config(bg=bg)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _conferma_rl(self):
        """Conferma selezione BotRL."""
        nome_ckpt = self.ckpt_selezionato.get()
        if not nome_ckpt:
            messagebox.showerror("Errore", "Seleziona un checkpoint BotRL!")
            return

        modulo, classe, ckpt = self.bot_disponibili[nome_ckpt]
        try:
            bot = crea_bot(modulo, classe, checkpoint=ckpt, device='cpu')
            self.root.destroy()
            self.callback(bot)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile caricare BotRL:\n{str(e)}")

    def _conferma(self):
        """Conferma selezione bot classico."""
        nome_bot = self.bot_selezionato.get()
        if not nome_bot:
            return
        modulo, classe, ckpt = self.bot_disponibili[nome_bot]
        bot = crea_bot(modulo, classe, checkpoint=ckpt)
        self.root.destroy()
        self.callback(bot)