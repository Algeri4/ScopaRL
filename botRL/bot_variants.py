# botRL/bot_variants.py
"""
Esempi di combinazioni encoder + reward engine per confrontare varianti
di PPO. Ogni funzione crea un trainer pronto, con rete correttamente
dimensionata per l'encoder scelto (l'assert dentro PPOTrainer se ne
occupa in automatico).
"""

from botRL.rete import ScopaNetwork
from botRL.trainer import PPOTrainer
from botRL.reward_engine import (
    DefaultRewardEngine,
    AggressiveRewardEngine,
    PrimieraRewardEngine,
)
from botRL.observation_encoder import (
    StandardEncoder,
    ProbabilisticEncoder,
    HistoryEncoder,
    PreseEncoder,
)


def _crea_trainer(encoder, reward, opponent=None, hidden_dim=512, **kwargs):
    network = ScopaNetwork(input_dim=encoder.input_dim, hidden_dim=hidden_dim)
    return PPOTrainer(
        network=network,
        reward_engine=reward,
        observation_encoder=encoder,
        opponent=opponent,
        **kwargs
    )


def create_bot_standard(opponent=None):
    """Bot con configurazione standard (baseline)."""
    return _crea_trainer(StandardEncoder(), DefaultRewardEngine(), opponent)


def create_bot_aggressive(opponent=None):
    """Bot che premia scope e penalizza il ballare più del default."""
    return _crea_trainer(StandardEncoder(), AggressiveRewardEngine(), opponent)


def create_bot_probabilistic(opponent=None):
    """Bot che usa probabilità delle carte avversario invece di sconosciute one-hot."""
    return _crea_trainer(ProbabilisticEncoder(), DefaultRewardEngine(), opponent)


def create_bot_history(opponent=None, history_length=5):
    """Bot con memoria delle ultime N mosse giocate."""
    return _crea_trainer(HistoryEncoder(history_length=history_length),
                          DefaultRewardEngine(), opponent)


def create_bot_prese(opponent=None):
    """Bot che si concentra sull'elenco delle prese fatte (mie/avversario)."""
    return _crea_trainer(PreseEncoder(), DefaultRewardEngine(), opponent)


def create_bot_full_custom(opponent=None):
    """Combinazione: reward aggressive + input probabilistico."""
    return _crea_trainer(ProbabilisticEncoder(), AggressiveRewardEngine(), opponent)


def create_bot_primiera(opponent=None):
    """Bot che punta a massimizzare il valore primiera delle prese."""
    return _crea_trainer(StandardEncoder(), PrimieraRewardEngine(), opponent)


# Registro comodo per script di confronto (vedi compare_bots.py)
VARIANTI_DISPONIBILI = {
    "Standard": create_bot_standard,
    "Aggressive": create_bot_aggressive,
    "Probabilistic": create_bot_probabilistic,
    "History": create_bot_history,
    "Prese": create_bot_prese,
    "FullCustom": create_bot_full_custom,
    "Primiera": create_bot_primiera,
}