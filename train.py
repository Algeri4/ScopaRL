#!/usr/bin/env python3
"""
train.py
Script principale per allenare il bot RL della Scopa Bergamasca.
"""

import argparse
import torch

from bot.bot_predatore import BotPredatore
from botRL.rete import ScopaNetwork
from botRL.trainer import PPOTrainer


def main():
    parser = argparse.ArgumentParser(description="Allena il bot RL per Scopa Bergamasca")
    parser.add_argument("--episodes", type=int, default=20000, help="Numero di episodi")
    parser.add_argument("--opponent", type=str, default="predatore",
                        choices=["casuale", "greedy", "predatore"],
                        help="Bot avversario per training (ignorato, usa curriculum)")
    parser.add_argument("--device", type=str, default="cpu", choices=["cpu", "cuda"])
    parser.add_argument("--lr", type=float, default=3e-4, help="Learning rate")
    parser.add_argument("--resume", type=str, default=None,
                        help="Path checkpoint da cui riprendere")
    parser.add_argument("--eval-every", type=int, default=500,
                        help="Valuta ogni N episodi")
    parser.add_argument("--save-every", type=int, default=2000,
                        help="Salva checkpoint ogni N episodi")
    parser.add_argument("--log-every", type=int, default=100,
                        help="Stampa progresso ogni N episodi")

    args = parser.parse_args()

    print("=" * 60)
    print("  SCOPA BERGAMASCA - RL TRAINER")
    print("=" * 60)
    print(f"Episodes: {args.episodes} | Device: {args.device} | LR: {args.lr}")
    print("=" * 60)

    network = ScopaNetwork(input_dim=209, hidden_dim=512)
    print(f"Rete: {sum(p.numel() for p in network.parameters()):,} parametri\n")

    trainer = PPOTrainer(
        network=network,
        opponent=BotPredatore(),
        lr=args.lr,
        device=args.device,
    )

    start_episode = 0
    if args.resume:
        start_episode = trainer.load_checkpoint(args.resume)
        print(f"Ripreso da episodio {start_episode}")

    try:
        trainer.train(
            n_episodes=args.episodes,
            eval_every=args.eval_every,
            save_every=args.save_every,
            log_every=args.log_every,
        )
    except KeyboardInterrupt:
        print("\nTraining interrotto")
        trainer.save_checkpoint("interrupted.pt", start_episode + args.episodes)

    trainer.save_checkpoint("final_model.pt", args.episodes)
    print(f"\nTraining completato! Best WR vs Predatore: {trainer.best_winrate:.1%}")


if __name__ == "__main__":
    main()