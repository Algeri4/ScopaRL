"""
botRL/pretrain/imitation.py

Pre-training supervisionato (behavioral cloning) della policy head di
ScopaNetwork, imitando un bot euristico deterministico (Predatore,
Intelligente1/2/3...). Serve come warm-start prima del training PPO:
la policy parte già sapendo giocare in modo sensato, invece che da pesi
casuali, così il training RL può concentrarsi su rifinire la strategia
invece di scoprire le basi da un reward scarso e rumoroso.

Per lanciare: basta aprire questo file in PyCharm e premere Run/tasto
verde. Per cambiare bot o numero di smazzate, modifica le costanti nella
sezione CONFIG qui sotto.
"""

import os

import torch
import torch.nn.functional as F

from scopa.ambiente import ScopaEnvironment
from bot.predatore import BotPredatore
from bot.Intelligente1 import BotIntelligente1
from bot.Intelligente2 import BotIntelligente2
from bot.Intelligente3 import BotIntelligente3
from botRL.rete import ScopaNetwork, build_action_mask, carta_to_idx
from botRL.observation_encoder import StandardEncoder

# ============================================================
# CONFIG — modifica qui, poi premi Run
# ============================================================
BOT_NAME = "intelligente3"     # "predatore" | "intelligente1" | "intelligente2" | "intelligente3"
N_HANDS = 8000
HIDDEN_DIM = 128
LOG_EVERY = 200
DEVICE = "cpu"
# ============================================================

BOT_REGISTRY = {
    "predatore": BotPredatore,
    "intelligente1": BotIntelligente1,
    "intelligente2": BotIntelligente2,
    "intelligente3": BotIntelligente3,
}

CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "checkpoints")


def run_imitation(bot_name: str, n_hands: int, hidden_dim: int,
                   log_every: int, device: str) -> ScopaNetwork:
    if bot_name not in BOT_REGISTRY:
        raise ValueError(f"Bot sconosciuto: {bot_name}. Scegli tra {list(BOT_REGISTRY)}")

    encoder = StandardEncoder()
    network = ScopaNetwork(input_dim=encoder.input_dim, hidden_dim=hidden_dim).to(device)
    optimizer = torch.optim.Adam(network.parameters(), lr=3e-4)

    bot_a = BOT_REGISTRY[bot_name]()
    bot_b = BOT_REGISTRY[bot_name]()
    env = ScopaEnvironment("A", "B")

    print("=" * 60)
    print(f"PRE-TRAINING (imitation learning) contro: {bot_name}")
    print(f"Encoder: {type(encoder).__name__} | input_dim: {encoder.input_dim}")
    print(f"Rete: {sum(p.numel() for p in network.parameters()):,} parametri")
    print("=" * 60)

    running_loss, running_correct, running_total = 0.0, 0, 0

    for hand in range(1, n_hands + 1):
        env.reset()

        while not env.partita_finita:
            idx = env.turno
            obs = env._get_observation(idx)

            bot = bot_a if idx == 0 else bot_b
            carta_target, prese_target = bot.scegli_mossa(obs)
            target_idx = torch.tensor([carta_to_idx(carta_target)], device=device)

            obs_vector = torch.tensor(
                encoder.encode(obs), dtype=torch.float32, device=device
            ).unsqueeze(0)
            action_mask = build_action_mask(obs["mano"], device=device).unsqueeze(0)

            policy_logits, _ = network(obs_vector)
            masked_logits = policy_logits.clone()
            masked_logits[~action_mask] = -1e9

            loss = F.cross_entropy(masked_logits, target_idx)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            running_correct += int(masked_logits.argmax(dim=-1).item() == target_idx.item())
            running_total += 1

            env.step((carta_target, prese_target), idx)

        if hand % log_every == 0:
            avg_loss = running_loss / running_total
            accuracy = 100.0 * running_correct / running_total
            print(f"Smazzata {hand:5d} | Loss: {avg_loss:.4f} | Accuratezza: {accuracy:5.1f}%")
            running_loss, running_correct, running_total = 0.0, 0, 0

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    save_path = os.path.join(CHECKPOINT_DIR, f"pretrained_{bot_name}.pt")
    torch.save({
        "state_dict": network.state_dict(),
        "input_dim": encoder.input_dim,
        "hidden_dim": hidden_dim,
        "encoder_class": type(encoder).__name__,
        "imitated_bot": bot_name,
        "n_hands": n_hands,
    }, save_path)
    print(f"\n💾 Pesi pre-allenati salvati in: {save_path}")

    return network


if __name__ == "__main__":
    run_imitation(
        bot_name=BOT_NAME,
        n_hands=N_HANDS,
        hidden_dim=HIDDEN_DIM,
        log_every=LOG_EVERY,
        device=DEVICE,
    )