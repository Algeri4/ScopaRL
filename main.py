#!/usr/bin/env python3
"""
Punto di ingresso per giocare a Scopa Bergamasca da terminale.
"""

from bot.casuale import BotCasuale
from bot.greedy import BotGreedy
from cli.partita import PartitaCLI


def menu():
    print("="*60)
    print("SCOPA BERGAMASCA - CLI")
    print("="*60)
    print("1) Tu vs Bot Casuale")
    print("2) Tu vs Bot Greedy (euristico)")
    print("3) Bot Casuale vs Bot Greedy (guarda una partita)")
    print("4) Esci")
    print("="*60)
    return input("Scelta: ").strip()


def main():
    while True:
        scelta = menu()

        if scelta == "1":
            nome = input("Il tuo nome: ").strip() or "Tu"
            bot = BotCasuale()
            partita = PartitaCLI(nome, bot)
            partita.gioca(seed=42)

        elif scelta == "2":
            nome = input("Il tuo nome: ").strip() or "Tu"
            bot = BotGreedy()
            partita = PartitaCLI(nome, bot)
            partita.gioca(seed=42)

        elif scelta == "3":
            print("\n[Modalità spettatore: BotCasuale vs BotGreedy]")
            # In questo caso usiamo entrambi bot, ma PartitaCLI è pensata per umano.
            # Per ora saltiamo o creiamo una versione semplificata.
            print("Non ancora implementato in questa versione.")

        elif scelta == "4":
            print("Ciao!")
            break
        else:
            print("Scelta non valida.\n")


if __name__ == "__main__":
    main()
