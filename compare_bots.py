# compare_bots.py

from botRL.bot_variants import (
    create_bot_standard,
    create_bot_aggressive,
    create_bot_probabilistic,
    create_bot_history,
    create_bot_full_custom
)
from cli.partita import PartitaCLI
from bot.bot_predatore import BotPredatore


def train_and_evaluate(create_fn, name, episodes=5000):
    print(f"\n{'='*60}")
    print(f"  TRAINING: {name}")
    print(f"{'='*60}")

    trainer = create_fn()
    trainer.train(n_episodes=episodes, eval_every=500, log_every=50)

    # Valutazione finale
    from botRL.bot_rl import BotRL
    bot = BotRL(trainer.network, device='cpu', deterministic=True)

    wins = 0
    n_games = 200
    for i in range(n_games):
        partita = PartitaCLI(bot, BotPredatore(), a_idx=i%2, verbose=False)
        ris = partita.gioca(seed=i)
        if ris["vincitore"] is not None:
            vincitore = bot.nome() if (i%2==0 and ris["vincitore"]==0) or (i%2==1 and ris["vincitore"]==1) else "Predatore"
            if vincitore == bot.nome():
                wins += 1

    winrate = wins / n_games
    print(f"\n{name}: WR vs Predatore = {winrate:.1%}")
    return winrate


def main():
    bots = [
        ("Standard", create_bot_standard),
        ("Aggressive", create_bot_aggressive),
        ("Probabilistic", create_bot_probabilistic),
        ("History", create_bot_history),
        ("Full Custom", create_bot_full_custom),
    ]

    results = {}
    for name, create_fn in bots:
        wr = train_and_evaluate(create_fn, name, episodes=5000)
        results[name] = wr

    print(f"\n{'='*60}")
    print("  CLASSIFICA FINALE")
    print(f"{'='*60}")
    for name, wr in sorted(results.items(), key=lambda x: x[1], reverse=True):
        print(f"  {name:20s}: {wr:.1%}")


if __name__ == "__main__":
    main()