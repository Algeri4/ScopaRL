#!/usr/bin/env python3
# main_scontro.py
# Scontro CLI tra due bot scelti dall'utente.
# =============================================================================
# METODO STATISTICO UTILIZZATO
# =============================================================================
#
# Questo programma confronta due bot facendo disputare un elevato numero di
# partite indipendenti di Scopa Bergamasca.
#
# Ogni partita decisiva (i pareggi vengono esclusi dall'analisi statistica)
# viene modellata come una prova di Bernoulli:
#
#     - vittoria del bot A -> successo
#     - vittoria del bot B -> fallimento
#
# Indichiamo con p la probabilità reale che il bot A vinca contro il bot B.
#
# Prima di osservare alcuna partita si assume una prior uniforme:
#
#         p ~ Beta(1,1)
#
# che rappresenta l'assenza di conoscenze pregresse.
#
# Dopo aver osservato:
#
#         v_a vittorie di A
#         v_b vittorie di B
#
# la distribuzione a posteriori diventa:
#
#         p | dati ~ Beta(v_a+1, v_b+1)
#
# Da tale distribuzione viene calcolata
#
#         P(p > 0.5 | dati)
#
# cioè la probabilità che il vero win-rate del bot A sia superiore al 50%.
#
# Questa probabilità rappresenta la confidenza che A sia realmente più forte
# di B, tenendo conto sia del numero di vittorie sia del numero totale di
# partite disputate.
#
# Ad esempio:
#
#     6-4   -> bassa confidenza
#     60-40 -> buona confidenza
#     600-400 -> confidenza molto elevata
#
# In questo modo vengono evitati i limiti dei classici test di significatività
# (p-value), ottenendo invece una probabilità direttamente interpretabile.
#
# =============================================================================
# ═══════════════════════════════════════════════════════════════════
# PARAMETRI CONFIGURABILI (hardcoded)
# ═══════════════════════════════════════════════════════════════════
N_PARTITE_DEFAULT = 100
ALTERNA_INIZIO = True
# ═══════════════════════════════════════════════════════════════════

import sys
import os
import math
import random
import time
from statistics import NormalDist
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli.partita import PartitaCLI
from gui.menu_bot import scopri_bot, crea_bot


def confidenza_migliore(v_a: int, v_b: int):
    """
    ----------------------------------------------------------------------
    Confidenza tramite modello Beta-Binomiale
    ----------------------------------------------------------------------

    Ogni partita decisiva (pareggi esclusi) viene vista come una prova di
    Bernoulli:

        vittoria A -> successo
        vittoria B -> fallimento

    Sia p la probabilità reale che A vinca contro B.

    Prima di osservare le partite assumiamo una prior non informativa:

        p ~ Beta(1,1)

    Dopo aver osservato:

        v_a vittorie di A
        v_b vittorie di B

    la distribuzione a posteriori diventa

        p | dati ~ Beta(v_a+1, v_b+1)

    La quantità di interesse è

        P(p > 0.5 | dati)

    cioè la probabilità che il vero win-rate di A sia superiore al 50%.

    Tale probabilità rappresenta la nostra confidenza che A sia realmente
    migliore di B.

    Per evitare dipendenze esterne (SciPy), la distribuzione Beta viene
    approssimata con una Normale avente stessa media e varianza.

    L'approssimazione è molto accurata quando il numero di partite è almeno
    qualche decina, come nei benchmark tra bot.
    ----------------------------------------------------------------------
    """

    n = v_a + v_b

    if n == 0:
        return 50.0, 50.0, "nessuna", None

    alpha = v_a + 1
    beta = v_b + 1

    # media della Beta
    media = alpha / (alpha + beta)

    # varianza della Beta
    var = (alpha * beta) / (
        (alpha + beta) ** 2 * (alpha + beta + 1)
    )

    sigma = math.sqrt(var)

    # probabilità P(p > 0.5)
    z = (0.5 - media) / sigma
    conf_a = (1 - NormalDist().cdf(z)) * 100
    conf_b = 100 - conf_a

    conf_a = max(0.1, min(99.9, conf_a))
    conf_b = max(0.1, min(99.9, conf_b))

    migliore = "A" if conf_a > conf_b else "B"

    vincitore = max(conf_a, conf_b)

    if vincitore >= 99:
        livello = "molto forte"
    elif vincitore >= 95:
        livello = "forte"
    elif vincitore >= 90:
        livello = "moderata"
    elif vincitore >= 75:
        livello = "debole"
    else:
        livello = "nessuna"

    return conf_a, conf_b, livello, migliore

def stampa_bot(numerati: dict):
    print(f"\n{'─' * 40}")
    print("Bot disponibili:")
    print(f"{'─' * 40}")
    for num, nome in numerati.items():
        print(f"  [{num}] {nome}")
    print(f"{'─' * 40}")


def chiedi_scelta(prompt: str, numerati: dict) -> str:
    while True:
        try:
            scelta = input(f"\n{prompt}: ").strip()
            idx = int(scelta)
            if idx in numerati:
                return numerati[idx]
        except ValueError:
            pass
        print("Scelta non valida, riprova.")


def chiedi_numero(prompt: str, default: int) -> int:
    while True:
        val = input(f"{prompt} [{default}]: ").strip()
        if val == "":
            return default
        try:
            n = int(val)
            if n > 0:
                return n
        except ValueError:
            pass
        print("Inserisci un numero valido.")


def chiedi_seme() -> int:
    print(f"\n{'─' * 40}")
    print("Opzioni seed (per riproducibilità):")
    print("  [invio]  - seed casuale (diverso ogni volta)")
    print("  N        - seed specifico (es. 42, 123, ...)")
    print(f"{'─' * 40}")

    val = input("Seed: ").strip()
    if val == "":
        seme = int(time.time() * 1000) % 1000000 + random.randint(0, 999999)
        print(f"Seed casuale generato: {seme}")
        return seme

    try:
        seme = int(val)
        print(f"Seed fisso: {seme}")
        return seme
    except ValueError:
        print("Input non valido, uso seed casuale")
        seme = int(time.time() * 1000) % 1000000
        print(f"Seed casuale generato: {seme}")
        return seme


def main():
    bot_disponibili = scopri_bot()
    nomi = sorted(bot_disponibili.keys())

    if len(nomi) < 2:
        print("Errore: servono almeno 2 bot!")
        return

    numerati = {i + 1: nome for i, nome in enumerate(nomi)}

    print(f"\n{'=' * 50}")
    print("  SCONTRO BOT - CLI")
    print(f"{'=' * 50}")

    stampa_bot(numerati)
    nome_a = chiedi_scelta("Scegli il PRIMO bot", numerati)

    stampa_bot(numerati)
    nome_b = chiedi_scelta("Scegli il SECONDO bot", numerati)

    n_partite = chiedi_numero("Quante partite?", N_PARTITE_DEFAULT)
    seme_inizio = chiedi_seme()

    print(f"\n{'=' * 50}")
    print(f"  {nome_a}  vs  {nome_b}")
    print(f"  {n_partite} partite")
    print(f"  Seed: {seme_inizio}")
    print(f"{'=' * 50}\n")

    mod_a, cls_a, ckpt_a = bot_disponibili[nome_a]
    mod_b, cls_b, ckpt_b = bot_disponibili[nome_b]
    bot_a = crea_bot(mod_a, cls_a, ckpt_a)
    bot_b = crea_bot(mod_b, cls_b, ckpt_b)

    v_a = v_b = p = 0
    pf_a = pf_b = sc_a = sc_b = 0

    for n in range(n_partite):
        a_inizia = (n % 2 == 0) if ALTERNA_INIZIO else True
        partita = PartitaCLI(bot_a, bot_b, a_idx=0 if a_inizia else 1, verbose=False)
        ris = partita.gioca(seed=seme_inizio + n)

        p0, p1 = ris["punteggi"]
        s0, s1 = ris["scope"]

        if a_inizia:
            pa, pb, sa, sb = p0, p1, s0, s1
        else:
            pa, pb, sa, sb = p1, p0, s1, s0

        pf_a += pa
        pf_b += pb
        sc_a += sa
        sc_b += sb

        if ris["vincitore"] is None:
            p += 1
        elif (a_inizia and ris["vincitore"] == 0) or (not a_inizia and ris["vincitore"] == 1):
            v_a += 1
        else:
            v_b += 1

        if (n + 1) % 10 == 0 or n == n_partite - 1:
            print(f"  Progresso: {n + 1}/{n_partite}", end="\r", flush=True)

    print()

    conf_a, conf_b, livello, migliore = confidenza_migliore(v_a, v_b)
    n_decisive = v_a + v_b

    print(f"\n{'=' * 50}")
    print("  RISULTATI")
    print(f"{'=' * 50}")
    print(f"{nome_a:<20} {v_a:>4} V  |  {v_b:>4} S  |  {p:>4} P")
    print(f"{nome_b:<20} {v_b:>4} V  |  {v_a:>4} S  |  {p:>4} P")
    print(f"{'─' * 50}")
    total = v_a + v_b + p
    print(f"Percentuale vittorie {nome_a}: {v_a / total * 100:.1f}%")
    print(f"Percentuale vittorie {nome_b}: {v_b / total * 100:.1f}%")
    print(f"Percentuale pareggi:       {p / total * 100:.1f}%")
    print(f"{'─' * 50}")
    print(f"Media punti {nome_a}: {pf_a / n_partite:.2f}")
    print(f"Media punti {nome_b}: {pf_b / n_partite:.2f}")
    print(f"Media scope {nome_a}: {sc_a / n_partite:.2f}")
    print(f"Media scope {nome_b}: {sc_b / n_partite:.2f}")
    print(f"{'=' * 50}")

    print(f"\n{'=' * 50}")
    print("  ANALISI STATISTICA")
    print(f"{'=' * 50}")
    print(f"Partite decisive: {n_decisive} (escluse {p} pareggi)")
    print(f"Win rate {nome_a}: {v_a / n_decisive * 100:.1f}% su {n_decisive} partite")

    # ═══ CORRETTO: stampa il nome del bot migliore, non sempre A ═══
    if migliore == "A":
        print(f"\n🏆 Confidenza che {nome_a} sia migliore di {nome_b}:")
        print(f"   {conf_a:.1f}% ({livello})")
    elif migliore == "B":
        print(f"\n🏆 Confidenza che {nome_b} sia migliore di {nome_a}:")
        print(f"   {conf_b:.1f}% ({livello})")
    else:
        print(f"\n🤝 Pareggio perfetto: nessun bot dimostrabilmente migliore")
        print(f"   Confidenza: 50.0%")

    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    main()