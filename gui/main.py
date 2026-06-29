# gui/main.py
# Entry point del gioco

import tkinter as tk
import argparse
from .menu_bot import scopri_bot, crea_bot, MenuSelezioneBot
from .scopa_gui import ScopaGUI


def avvia_gui(bot=None):
    """Avvia il gioco. Se bot è None, mostra il menu di selezione."""
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


def main():
    parser = argparse.ArgumentParser(description="Scopa Bergamasca GUI")
    parser.add_argument("--bot", type=str, default=None,
                        help="Nome del bot da usare (es. 'BotGreedy', 'BotPredatore')")
    args = parser.parse_args()

    if args.bot:
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


if __name__ == "__main__":
    main()