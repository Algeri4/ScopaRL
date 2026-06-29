# scopa/punteggio.py
from .motore import MotoreScopa


class ContatorePunti:
    """
    Arbitro del punteggio. Non sa nulla dello stato di gioco,
    solo prende due mazzetti di carte e conta.
    """

    @staticmethod
    def calcola(prese_0, scope_0, prese_1, scope_1):
        """
        Ritorna: (punti_0, punti_1, dettaglio_dict)
        """
        p0 = {"scope": scope_0, "carte": 0, "denari": 0, "settebello": 0, "primiera": 0}
        p1 = {"scope": scope_1, "carte": 0, "denari": 0, "settebello": 0, "primiera": 0}

        # --- Carte totali ---
        p0["carte"] = len(prese_0)
        p1["carte"] = len(prese_1)

        # --- Denari ---
        p0["denari"] = sum(1 for c in prese_0 if c.seme == "denari")
        p1["denari"] = sum(1 for c in prese_1 if c.seme == "denari")

        # --- Settebello ---
        p0["settebello"] = 1 if any(c.is_settebello() for c in prese_0) else 0
        p1["settebello"] = 1 if any(c.is_settebello() for c in prese_1) else 0

        # --- Primiera ---
        prim_a, prim_b, vinc_prim = MotoreScopa.confronta_primiera(prese_0, prese_1)
        p0["primiera_valore"] = prim_a
        p1["primiera_valore"] = prim_b

        # --- Assegnazione punti ---
        punti = [0, 0]

        # Scope
        punti[0] += scope_0
        punti[1] += scope_1

        # Carte
        if p0["carte"] > p1["carte"]:
            punti[0] += 1
        elif p1["carte"] > p0["carte"]:
            punti[1] += 1

        # Denari
        if p0["denari"] > p1["denari"]:
            punti[0] += 1
        elif p1["denari"] > p0["denari"]:
            punti[1] += 1

        # Settebello
        punti[0] += p0["settebello"]
        punti[1] += p1["settebello"]

        # Primiera
        if vinc_prim == 0:
            punti[0] += 1
        elif vinc_prim == 1:
            punti[1] += 1

        return punti[0], punti[1], {"p0": p0, "p1": p1, "primiera": (prim_a, prim_b, vinc_prim)}