# botRL/observation_encoder.py
"""
Interfaccia per convertire observation dict -> vettore per la NN.

Tutti gli encoder sono FUNZIONI PURE: stessa observation in input,
stesso vettore in output, nessuno stato interno mutabile. Questo è
importante perché lo stesso encoder deve poter essere usato sia durante
il training (rollout sequenziali) sia durante partite/valutazioni in
parallelo, senza che una partita "sporchi" lo stato di un'altra.

Per questo anche HistoryEncoder non tiene un buffer interno: legge la
storia direttamente da observation["storico"], che l'ambiente espone
già (vedi scopa/observation.py).
"""

from abc import ABC, abstractmethod
from typing import List
from scopa.costanti import SEMI


def _one_hot(carte, size=40) -> List[float]:
    v = [0.0] * size
    for c in carte:
        idx = SEMI.index(c.seme) * 10 + (c.valore - 1)
        v[idx] = 1.0
    return v


def _features_scalari(observation: dict) -> List[float]:
    return [
        observation["scope_mie"] / 10.0,
        observation["scope_avversario"] / 10.0,
        observation["mano_corrente"] / 2.0,
        observation["carte_mazzo"] / 40.0,
        observation["turno"],
        observation["punteggi"][0] / 21.0,
        observation["punteggi"][1] / 21.0,
        len(observation["azioni_legali"]) / 50.0,
        1.0 if observation["partita_finita"] else 0.0,
    ]


class ObservationEncoder(ABC):
    """Interfaccia per convertire observation dict in vettore per la NN."""

    @abstractmethod
    def encode(self, observation: dict) -> List[float]:
        """Converte observation in lista di float. Deve essere una funzione pura."""
        pass

    @property
    @abstractmethod
    def input_dim(self) -> int:
        """Dimensione del vettore di output."""
        pass


class StandardEncoder(ObservationEncoder):
    """Encoding standard: one-hot carte (mano/banco/prese mie/prese avv/sconosciute) + scalari."""

    @property
    def input_dim(self) -> int:
        return 209  # 40*5 one-hot + 9 scalari

    def encode(self, observation: dict) -> List[float]:
        v = []
        v.extend(_one_hot(observation["mano"]))
        v.extend(_one_hot(observation["banco"]))
        v.extend(_one_hot(observation["prese_mie"]))
        v.extend(_one_hot(observation["prese_avversario"]))
        v.extend(_one_hot(observation["sconosciute"]))
        v.extend(_features_scalari(observation))
        return v


class ProbabilisticEncoder(ObservationEncoder):
    """
    Al posto delle carte "sconosciute" in one-hot, usa la probabilità
    ipergeometrica che l'avversario abbia >=1,2,3,4 carte di ogni valore.
    """

    @property
    def input_dim(self) -> int:
        return 40 * 4 + 40 + 9  # mano+banco+prese_mie+prese_avv one-hot (40*4) + prob (40) + 9 scalari

    def encode(self, observation: dict) -> List[float]:
        from scopa.probabilita import calcola_tutte_proabilita

        probs = calcola_tutte_proabilita(observation)
        prob_vector = []
        for valore in range(1, 11):
            p = probs.get(valore, {})
            cum = p.get("probs", [0.0, 0.0, 0.0, 0.0])
            prob_vector.extend(cum)  # 4 valori per ciascuna delle 10 carte = 40

        v = []
        v.extend(_one_hot(observation["mano"]))
        v.extend(_one_hot(observation["banco"]))
        v.extend(_one_hot(observation["prese_mie"]))
        v.extend(_one_hot(observation["prese_avversario"]))
        v.extend(prob_vector)
        v.extend(_features_scalari(observation))
        return v


class HistoryEncoder(ObservationEncoder):
    """
    Encoding che include le ultime N carte giocate (one-hot ciascuna),
    ricavate da observation["storico"]. Nessuno stato interno: la storia
    arriva dall'observation, quindi l'encoder resta una funzione pura.
    """

    def __init__(self, history_length: int = 5):
        self.history_length = history_length

    @property
    def input_dim(self) -> int:
        return 209 + 40 * self.history_length

    def encode(self, observation: dict) -> List[float]:
        v = []
        v.extend(_one_hot(observation["mano"]))
        v.extend(_one_hot(observation["banco"]))
        v.extend(_one_hot(observation["prese_mie"]))
        v.extend(_one_hot(observation["prese_avversario"]))
        v.extend(_one_hot(observation["sconosciute"]))

        storico = observation.get("storico", [])
        ultime = storico[-self.history_length:] if storico else []
        carte_ultime = [mossa["carta"] for mossa in ultime]

        for i in range(self.history_length):
            if i < len(carte_ultime):
                v.extend(_one_hot([carte_ultime[i]]))
            else:
                v.extend([0.0] * 40)

        v.extend(_features_scalari(observation))
        return v


class PreseEncoder(ObservationEncoder):
    """
    Esempio richiesto: invece delle carte "sconosciute" usa esplicitamente
    l'elenco delle prese fatte da entrambi (che sono già in observation,
    quindi non serve nessuna modifica all'ambiente).
    Qui semplicemente enfatizziamo prese_mie/prese_avversario con encoding
    ripetuto, a scopo dimostrativo di quanto sia facile aggiungere varianti.
    """

    @property
    def input_dim(self) -> int:
        return 40 * 4 + 9  # mano, banco, prese_mie, prese_avversario + scalari

    def encode(self, observation: dict) -> List[float]:
        v = []
        v.extend(_one_hot(observation["mano"]))
        v.extend(_one_hot(observation["banco"]))
        v.extend(_one_hot(observation["prese_mie"]))
        v.extend(_one_hot(observation["prese_avversario"]))
        v.extend(_features_scalari(observation))
        return v


# Registro per (de)serializzazione nei checkpoint: permette a BotRL.from_checkpoint
# di ricostruire l'encoder corretto senza che il chiamante debba saperlo a priori.
ENCODER_REGISTRY = {
    "StandardEncoder": StandardEncoder,
    "ProbabilisticEncoder": ProbabilisticEncoder,
    "HistoryEncoder": HistoryEncoder,
    "PreseEncoder": PreseEncoder,
}


def crea_encoder(nome: str, **kwargs) -> ObservationEncoder:
    if nome not in ENCODER_REGISTRY:
        raise ValueError(f"ObservationEncoder sconosciuto: {nome}. "
                          f"Disponibili: {list(ENCODER_REGISTRY.keys())}")
    return ENCODER_REGISTRY[nome](**kwargs)