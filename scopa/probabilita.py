# scopa/probabilita.py
# Calcolo probabilità ipergeometrico per la Scopa Bergamasca

from math import comb
from typing import List, Dict
from scopa.carta import Carta


def conta_carte_per_valore(carte: List[Carta]) -> Dict[int, int]:
    """Ritorna un dict {valore: count} per le carte date."""
    result = {}
    for c in carte:
        result[c.valore] = result.get(c.valore, 0) + 1
    return result


def probabilita_puntuale(rimanenti_valore: int, n_sconosciute: int,
                         n_mano_avversario: int, k: int) -> float:
    """
    P(X = k) con distribuzione ipergeometrica.
    X = numero di carte di questo valore nella mano dell'avversario.
    """
    if k < 0 or k > rimanenti_valore or k > n_mano_avversario:
        return 0.0
    if n_sconosciute <= 0 or n_mano_avversario <= 0 or rimanenti_valore <= 0:
        return 0.0

    num1 = comb(rimanenti_valore, k)
    num2 = comb(n_sconosciute - rimanenti_valore, n_mano_avversario - k)
    den = comb(n_sconosciute, n_mano_avversario)

    if den == 0:
        return 0.0
    return (num1 * num2) / den


def probabilita_cumulative(rimanenti_valore: int, n_sconosciute: int,
                           n_mano_avversario: int) -> List[float]:
    """
    Ritorna [P(X≥1), P(X≥2), P(X≥3), P(X≥4)].
    """
    if n_sconosciute <= 0 or n_mano_avversario <= 0 or rimanenti_valore <= 0:
        return [0.0, 0.0, 0.0, 0.0]

    max_k = min(rimanenti_valore, n_mano_avversario)
    if max_k < 1:
        return [0.0, 0.0, 0.0, 0.0]

    # Calcola probabilità puntuali P(X = i)
    probs_puntuali = {}
    for i in range(0, max_k + 1):
        probs_puntuali[i] = probabilita_puntuale(rimanenti_valore, n_sconosciute, n_mano_avversario, i)

    # Calcola cumulative P(X ≥ k)
    cumulative = []
    for k in range(1, 5):
        if k > max_k:
            cumulative.append(0.0)
        else:
            prob = sum(probs_puntuali[i] for i in range(k, max_k + 1))
            cumulative.append(min(prob, 1.0))

    return cumulative


def probabilita_almeno_una(rimanenti_valore: int, n_sconosciute: int,
                           n_mano_avversario: int) -> float:
    """P(X ≥ 1): probabilità che l'avversario abbia ALMENO una carta di quel valore."""
    probs = probabilita_cumulative(rimanenti_valore, n_sconosciute, n_mano_avversario)
    return probs[0] if probs else 0.0


def calcola_note_da_observation(observation: dict) -> List[Carta]:
    """
    Estrae tutte le carte note da un'observation del bot.
    """
    note = []
    for chiave in ("mano", "banco", "prese_mie", "prese_avversario"):
        note.extend(observation.get(chiave, []))
    return note


def calcola_parametri(observation: dict) -> tuple:
    """
    Dall'observation di un bot, calcola:
    - carte_note: lista di Carta note
    - n_mano_avversario: quante carte ha l'avversario in mano
    - carte_mazzo: carte rimaste nel mazzo

    Ritorna: (carte_note, n_mano_avversario, carte_mazzo)
    """
    note = calcola_note_da_observation(observation)
    carte_mazzo = observation.get("carte_mazzo", 0)

    # L'avversario ha lo stesso numero di carte che abbiamo noi
    # (o quasi, a seconda del turno)
    n_mano_avversario = len(observation.get("mano", []))
    if n_mano_avversario == 0:
        n_mano_avversario = 1  # fallback

    return note, n_mano_avversario, carte_mazzo


def calcola_tutte_proabilita(observation: dict) -> Dict[int, dict]:
    """
    Calcola per ogni valore (1-10) le probabilità cumulative.
    Ritorna: {valore: {"passate": N, "rimanenti": M, "probs": [P≥1, P≥2, P≥3, P≥4]}}
    """
    note, n_mano_avversario, carte_mazzo = calcola_parametri(observation)

    carte_passate = conta_carte_per_valore(note)
    n_sconosciute = carte_mazzo + n_mano_avversario

    result = {}
    for valore in range(1, 11):
        passate = carte_passate.get(valore, 0)
        rimanenti = 4 - passate

        if rimanenti <= 0 or n_sconosciute <= 0 or n_mano_avversario <= 0:
            probs = [0.0, 0.0, 0.0, 0.0]
        else:
            probs = probabilita_cumulative(rimanenti, n_sconosciute, n_mano_avversario)

        result[valore] = {
            "passate": passate,
            "rimanenti": rimanenti,
            "probs": probs
        }

    return result