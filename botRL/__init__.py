"""
botRL - Bot per Scopa Bergamasca con Reinforcement Learning (PPO)

Package contenente:
  - rete.py: Architettura della rete neurale
  - policy.py: Policy con action masking
  - buffer.py: Rollout buffer per PPO
  - trainer.py: Loop di training
  - bot_rl.py: BotAgent wrapper

Usage rapido:
    from botRL.trainer import PPOTrainer
    from botRL.rete import ScopaNetwork
    from bot.bot_predatore import BotPredatore

    network = ScopaNetwork()
    trainer = PPOTrainer(network, opponent=BotPredatore())
    trainer.train(n_episodes=10000)
"""