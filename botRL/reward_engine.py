# botRL/reward_engine.py
"""
Interfaccia per il calcolo del reward.

IMPORTANTE: il RewardEngine non riceve mai l'oggetto `env` grezzo.
Riceve solo `observation` / `next_observation` (i dict prodotti da
ObservationBuilder), che contengono già tutto il necessario, incluso
"punteggi" e "giocatore_idx". Questo evita che il reward finisca per
dipendere da dettagli interni di ScopaEnvironment, e rende ogni
RewardEngine testabile in isolamento (basta costruire un dict finto).
"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional, List
from scopa.carta import Carta
from scopa.motore import MotoreScopa


class RewardEngine(ABC):
    """Interfaccia per il calcolo del reward. Ogni bot può implementare il proprio."""

    @abstractmethod
    def compute_step_reward(self,
                             info: dict,
                             observation: dict,
                             action: Tuple[Carta, Optional[List[Carta]]],
                             next_observation: dict,
                             done: bool) -> float:
        """
        Calcola il reward per UN singolo step (mossa).

        NB: non riceve un "base_reward" dall'ambiente perché
        ScopaEnvironment.step() è neutrale sul reward per costruzione
        (restituisce sempre 0.0) — vedi nota in scopa/ambiente.py.
        Tutto il reward numerico nasce qui, non nell'ambiente.
        """
        pass

    @abstractmethod
    def compute_terminal_reward(self, final_observation: dict) -> float:
        """
        Calcola il reward terminale quando la partita finisce.
        `final_observation` è l'observation ottenuta dopo l'ultimo step,
        per l'agente stesso (contiene "giocatore_idx" e "punteggi" globali).
        """
        pass


# ----------------------------------------------------------------------
# Utility condivisa: punteggio proprio vs avversario da una observation
# ----------------------------------------------------------------------
def _mio_vs_avversario(observation: dict) -> Tuple[int, int]:
    idx = observation["giocatore_idx"]
    p0, p1 = observation["punteggi"]
    return (p0, p1) if idx == 0 else (p1, p0)


class DefaultRewardEngine(RewardEngine):
    """Reward engine di default (bilanciato)."""

    def compute_step_reward(self, info, observation, action, next_observation, done):
        reward = 0.0
        carta, prese = action

        if info.get("scopa", False):
            reward += 5.0

        if prese:
            carte_totali = prese + [carta]
            for c in carte_totali:
                if c.is_settebello():
                    reward += 3.0
                elif c.valore == 7:
                    reward += 1.0
                elif c.seme == "denari":
                    reward += 0.5
            reward += len(carte_totali) * 0.1
        else:
            reward -= 0.1
            for c in observation["mano"]:
                if c != carta and MotoreScopa.trova_tutte_prese_legali(observation["banco"], c):
                    reward -= 0.5
                    break

            for c in observation["banco"]:
                if c.is_settebello():
                    reward -= 2.0
                elif c.valore == 7:
                    reward -= 0.5

        return reward

    def compute_terminal_reward(self, final_observation):
        mio, avv = _mio_vs_avversario(final_observation)
        diff = mio - avv
        if mio > avv:
            return 10.0 + diff * 0.5
        elif mio < avv:
            return -10.0 + diff * 0.5
        return 0.0


class AggressiveRewardEngine(RewardEngine):
    """Premia di più le scope, penalizza di più il ballare."""

    def compute_step_reward(self, info, observation, action, next_observation, done):
        reward = 0.0
        carta, prese = action

        if info.get("scopa", False):
            reward += 10.0

        if prese:
            carte_totali = prese + [carta]
            for c in carte_totali:
                if c.is_settebello():
                    reward += 5.0
                elif c.valore == 7:
                    reward += 2.0
                elif c.seme == "denari":
                    reward += 1.0
        else:
            reward -= 1.0

        return reward

    def compute_terminal_reward(self, final_observation):
        mio, avv = _mio_vs_avversario(final_observation)
        if mio > avv:
            return 10.0
        elif mio < avv:
            return -10.0
        return 0.0


class PrimieraRewardEngine(RewardEngine):
    """Premia la raccolta di carte con alto valore primiera."""

    def compute_step_reward(self, info, observation, action, next_observation, done):
        reward = 0.0
        carta, prese = action

        if prese:
            carte_totali = prese + [carta]
            for c in carte_totali:
                reward += c.valore_primiera() * 0.1
        else:
            for c in observation["banco"]:
                if c.valore_primiera() > 15:
                    reward -= 0.3

        return reward

    def compute_terminal_reward(self, final_observation):
        mio, avv = _mio_vs_avversario(final_observation)
        if mio > avv:
            return 10.0
        elif mio < avv:
            return -10.0
        return 0.0


# Registro per (de)serializzazione nei checkpoint
REWARD_ENGINE_REGISTRY = {
    "DefaultRewardEngine": DefaultRewardEngine,
    "AggressiveRewardEngine": AggressiveRewardEngine,
    "PrimieraRewardEngine": PrimieraRewardEngine,
}


def crea_reward_engine(nome: str) -> RewardEngine:
    if nome not in REWARD_ENGINE_REGISTRY:
        raise ValueError(f"RewardEngine sconosciuto: {nome}. "
                          f"Disponibili: {list(REWARD_ENGINE_REGISTRY.keys())}")
    return REWARD_ENGINE_REGISTRY[nome]()