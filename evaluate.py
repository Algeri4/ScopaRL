#!/usr/bin/env python3
"""
evaluate.py
Script per valutare il bot RL contro i bot manuali.

Usage:
    python evaluate.py --model botRL/checkpoints/best_model.pt --opponent predatore --games 200
    python evaluate.py --model botRL/checkpoints/best_model.pt --tournament
"""

import argparse
import torch
from cli.partita_cli import PartitaCLI
from bot.bot_casuale import BotCasuale
from bot.bot_greedy import BotGreedy
from bot.predatore import BotPredatore
from botRL.bot_rl import BotRL
from botRL.rete import ScopaNetwork


def valuta_bot(bot, avversario, n_games=100):
    """Valuta un bot contro un avversario."""
    vittorie = 0
    pareggi = 0
    scope_totali = 0
    punti_totali = 0

    for i in range(n_games):
        a_inizia = (i % 2 == 0)
        if a_inizia:
            partita = PartitaCLI(bot, avversario, a_idx=0, verbose=False)
        else:
            partita = PartitaCLI(avversario, bot, a_idx=1, verbose=False)

        ris = partita.gioca(seed=i)

        # Determina vincitore
        vincitore_nome = None
        if ris["vincitore"] is not None:
            vincitore_nome = bot.nome() if (a_inizia and ris["vincitore"] == 0) or (
                        not a_inizia and ris["vincitore"] == 1) else avversario.nome()

        if vincitore_nome == bot.nome():
            vittorie += 1
        elif ris["vincitore"] is None:
            pareggi += 1

        # Punti e scope (mappati correttamente)
        if a_inizia:
            scope_totali += ris["scope"][0]
            punti_totali += ris["punteggi"][0]
        else:
            scope_totali += ris["scope"][1]
            punti_totali += ris["punteggi"][1]

    return {
        "vittorie": vittorie,
        "pareggi": pareggi,
        "sconfitte": n_games - vittorie - pareggi,
        "winrate": vittorie / n_games,
        "scope_media": scope_totali / n_games,
        "punti_media": punti_totali / n_games,
    }


def torneo(bot, n_games=100):
    """Torneo contro tutti i bot."""
    avversari = {
        "Casuale": BotCasuale(),
        "Greedy": BotGreedy(),
        "Predatore": BotPredatore(),
    }

    print(f"\n{'=' * 60}")
    print(f"  🏆 TORNEO: {bot.nome()}")
    print(f"{'=' * 60}")

    for nome, avversario in avversari.items():
        print(f"\n📊 vs {nome} ({n_games} partite)...")
        ris = valuta_bot(bot, avversario, n_games)
        print(f"   Winrate: {ris['winrate']:.1%} ({ris['vittorie']}/{n_games})")
        print(f"   Pareggi: {ris['pareggi']} | Sconfitte: {ris['sconfitte']}")
        print(f"   Scope/media: {ris['scope_media']:.2f} | Punti/media: {ris['punti_media']:.2f}")

    print(f"\n{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(description="Valuta il bot RL")
    parser.add_argument("--model", type=str, required=True, help="Path al checkpoint")
    parser.add_argument("--opponent", type=str, default="predatore",
                        choices=["casuale", "greedy", "predatore", "all"],
                        help="Avversario o 'all' per torneo")
    parser.add_argument("--games", type=int, default=100, help="Numero partite")
    parser.add_argument("--device", type=str, default="cpu", choices=["cpu", "cuda"])
    parser.add_argument("--deterministic", action="store_true", help="Modalità greedy")

    args = parser.parse_args()

    # Carica bot RL
    print(f"📂 Caricamento modello: {args.model}")
    bot = BotRL.from_checkpoint(
        args.model,
        nome="BotRL",
        device=args.device,
        deterministic=args.deterministic
    )
    print(f"✅ Bot caricato: {bot.nome()}")
    print(f"   Deterministic: {args.deterministic}")

    if args.opponent == "all":
        torneo(bot, n_games=args.games)
    else:
        avversari = {
            "casuale": BotCasuale(),
            "greedy": BotGreedy(),
            "predatore": BotPredatore(),
        }
        avversario = avversari[args.opponent]

        print(f"\n📊 Valutazione vs {avversario.nome()} ({args.games} partite)...")
        ris = valuta_bot(bot, avversario, args.games)

        print(f"\n{'=' * 60}")
        print(f"  RISULTATI")
        print(f"{'=' * 60}")
        print(f"  Bot: {bot.nome()}")
        print(f"  Avversario: {avversario.nome()}")
        print(f"  Partite: {args.games}")
        print(f"  Vittorie: {ris['vittorie']} ({ris['winrate']:.1%})")
        print(f"  Pareggi: {ris['pareggi']}")
        print(f"  Sconfitte: {ris['sconfitte']}")
        print(f"  Scope/media: {ris['scope_media']:.2f}")
        print(f"  Punti/media: {ris['punti_media']:.2f}")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    main()