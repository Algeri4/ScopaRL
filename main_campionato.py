#!/usr/bin/env python3
# main_campionato.py
# Campionato round‑robin: tutti i bot si sfidano tra loro.
# Classifica globale con rating Elo batch e matrice di confidenza Beta‑Binomiale.
# =============================================================================
# METODO STATISTICO UTILIZZATO
# =============================================================================
#
# Il programma utilizza due strumenti statistici distinti.
#
# -----------------------------------------------------------------------------
# 1) Confronto diretto fra due bot (Posterior Beta-Binomiale)
# -----------------------------------------------------------------------------
#
# Ogni partita decisiva viene modellata come una prova di Bernoulli:
#
#     vittoria A -> successo
#     vittoria B -> fallimento
#
# Assumendo una prior uniforme
#
#         p ~ Beta(1,1)
#
# dopo aver osservato:
#
#         v_a vittorie
#         v_b sconfitte
#
# si ottiene la distribuzione a posteriori
#
#         Beta(v_a+1, v_b+1)
#
# dalla quale viene calcolata
#
#         P(p > 0.5 | dati)
#
# ovvero la probabilità che il vero win-rate del bot A sia superiore al 50%.
#
# Questa misura viene utilizzata esclusivamente negli scontri diretti tra due
# bot e rappresenta la confidenza statistica che uno sia realmente migliore
# dell'altro.
#
#
# -----------------------------------------------------------------------------
# 2) Classifica generale (rating Elo batch)
# -----------------------------------------------------------------------------
#
# Una probabilità di superiorità è definita solo tra una coppia di bot e non
# può essere mediata o utilizzata direttamente per costruire una classifica
# globale.
#
# Per questo motivo il ranking del campionato utilizza il sistema Elo.
#
# Ogni bot possiede un rating iniziale (1500 punti).
#
# Dopo ogni scontro (costituito da N partite) il rating viene aggiornato una
# sola volta utilizzando il punteggio medio osservato:
#
#         S = (vittorie + 0.5 * pareggi) / partite_totali
#
# confrontato con il punteggio atteso derivante dalla formula Elo:
#
#         E = 1 / (1 + 10^((R_avversario - R_bot)/400))
#
# Il nuovo rating è quindi
#
#         R' = R + K (S - E)
#
# dove K controlla la velocità di aggiornamento.
#
# Aggiornare l'Elo una sola volta per ogni scontro ("batch Elo") è preferibile
# rispetto ad aggiornarlo partita per partita, poiché ogni confronto è composto
# da molte partite giocate nelle stesse condizioni sperimentali (seed
# controllati e alternanza del primo giocatore).
#
#
# -----------------------------------------------------------------------------
# Riassunto
# -----------------------------------------------------------------------------
#
# • Posterior Beta-Binomiale
#       → misura quanto è probabile che A sia migliore di B.
#
# • Elo batch
#       → produce una classifica globale coerente di tutti i bot.
#
# I due strumenti rispondono a domande differenti e vengono utilizzati in modo
# complementare.
#
# =============================================================================

# ═══════════════════════════════════════════════════════════════════
# PARAMETRI CONFIGURABILI (hardcoded - usati come default)
# ═══════════════════════════════════════════════════════════════════
N_PARTITE_DEFAULT = 100
ALTERNA_INIZIO = True
VERBOSE = False
STAMPA_CLASSIFICA = True
STAMPA_DETTAGLI = True

K_ELO = 24                 # velocità di aggiornamento Elo (consigliato 24-32)
ELO_INIZIALE = 1500.0      # rating di partenza
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


# =============================================================================
# 1) CONFIDENZA BETA-BINOMIALE (posterior)
# =============================================================================
def confidenza_migliore(v_a: int, v_b: int):
    """
    Restituisce la probabilità (approssimata) che il bot A sia migliore di B,
    usando il modello Beta‑Binomiale.

    La distribuzione a posteriori è Beta(v_a+1, v_b+1).
    Calcoliamo P(p > 0.5) approssimando la Beta con una Normale
    (valida per un numero di partite >= qualche decina).

    Ritorna: (conf_a, conf_b, livello, migliore)
      conf_a      : probabilità % che A sia superiore
      conf_b      : probabilità % che B sia superiore
      livello     : stringa descrittiva
      migliore    : "A" o "B" o None in caso di perfetta parità
    """

    n = v_a + v_b
    if n == 0:
        return 50.0, 50.0, "nessuna", None

    # casi limite
    if v_a == 0 and v_b > 0:
        return 0.1, 99.9, "molto forte", "B"
    if v_b == 0 and v_a > 0:
        return 99.9, 0.1, "molto forte", "A"

    # parametri della Beta
    alpha = v_a + 1
    beta = v_b + 1
    media = alpha / (alpha + beta)
    var = (alpha * beta) / ((alpha + beta)**2 * (alpha + beta + 1))
    sigma = math.sqrt(var)

    # probabilità P(p > 0.5) usando l'approssimazione normale
    z = (0.5 - media) / sigma
    conf_a = (1 - NormalDist().cdf(z)) * 100
    conf_b = 100 - conf_a

    conf_a = max(0.1, min(99.9, conf_a))
    conf_b = max(0.1, min(99.9, conf_b))

    # determinazione del migliore
    if conf_a > conf_b:
        migliore = "A"
    elif conf_b > conf_a:
        migliore = "B"
    else:
        migliore = None

    # livello di confidenza
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


# =============================================================================
# 2) SISTEMA ELO BATCH
# =============================================================================
def aggiorna_elo(ra: float, rb: float, sa: float, k: float = K_ELO) -> tuple:
    """
    Calcola i nuovi rating Elo dopo uno scontro tra A e B.

    ra, rb   : rating attuali
    sa       : punteggio osservato di A (compreso tra 0 e 1)
               es. 0.855 se A vince 85 partite su 100 con 1 pareggio
    k        : fattore K

    Ritorna (nuovo_ra, nuovo_rb)
    """
    # punteggio atteso
    ea = 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))
    eb = 1.0 - ea

    # aggiornamento
    nuovo_ra = ra + k * (sa - ea)
    nuovo_rb = rb + k * ((1.0 - sa) - eb)

    return nuovo_ra, nuovo_rb


# =============================================================================
# 3) INTERFACCIA UTENTE
# =============================================================================
def stampa_bot_disponibili(bot_disponibili: dict, selezionati: set):
    print(f"\n{'─' * 50}")
    print("Bot disponibili (X = selezionato):")
    print(f"{'─' * 50}")
    for i, nome in enumerate(sorted(bot_disponibili.keys()), 1):
        marker = "[X]" if nome in selezionati else "[ ]"
        print(f"  {marker} [{i}] {nome}")
    print(f"{'─' * 50}")
    print(f"Selezionati: {len(selezionati)} bot")


def chiedi_selezione_bot(bot_disponibili: dict) -> list:
    nomi = sorted(bot_disponibili.keys())
    selezionati = set(nomi)

    while True:
        stampa_bot_disponibili(bot_disponibili, selezionati)
        print("\nComandi:")
        print("  'all'    - seleziona tutti")
        print("  'none'   - deseleziona tutti")
        print("  'toggle N' - cambia stato del bot N")
        print("  'done'   - conferma selezione")

        cmd = input("\nComando: ").strip().lower()

        if cmd == "done":
            if len(selezionati) < 2:
                print("Errore: servono almeno 2 bot!")
                continue
            return sorted(selezionati)

        elif cmd == "all":
            selezionati = set(nomi)

        elif cmd == "none":
            selezionati = set()

        elif cmd.startswith("toggle"):
            try:
                idx = int(cmd.split()[1]) - 1
                if 0 <= idx < len(nomi):
                    nome = nomi[idx]
                    if nome in selezionati:
                        selezionati.remove(nome)
                    else:
                        selezionati.add(nome)
            except (IndexError, ValueError):
                print("Uso: toggle N")

        else:
            print("Comando non riconosciuto")


def chiedi_numero_partite() -> int:
    while True:
        val = input(f"\nPartite per ogni scontro [{N_PARTITE_DEFAULT}]: ").strip()
        if val == "":
            return N_PARTITE_DEFAULT
        try:
            n = int(val)
            if n >= 10:
                return n
            print("Servono almeno 10 partite per significatività statistica")
        except ValueError:
            pass
        print("Inserisci un numero valido")


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


# =============================================================================
# 4) MAIN DEL CAMPIONATO
# =============================================================================
def main():
    bot_disponibili = scopri_bot()
    if not bot_disponibili:
        print("Errore: nessun bot trovato!")
        return

    print(f"\n{'=' * 60}")
    print("  CAMPIONATO SCOPA BERGAMASCA")
    print(f"{'=' * 60}")

    nomi_bot = chiedi_selezione_bot(bot_disponibili)
    n_partite = chiedi_numero_partite()
    seme_inizio = chiedi_seme()

    n_bot = len(nomi_bot)
    n_scontri = n_bot * (n_bot - 1) // 2
    totale_partite = n_scontri * n_partite

    print(f"\n{'=' * 60}")
    print(f"Bot partecipanti ({n_bot}):")
    for nome in nomi_bot:
        print(f"  • {nome}")
    print(f"\nPartite per scontro: {n_partite}")
    print(f"Totale scontri: {n_scontri}")
    print(f"Totale partite: {totale_partite}")
    print(f"Seed: {seme_inizio}")
    print(f"{'=' * 60}\n")

    # Inizializzazione statistiche grezze + rating Elo
    classifica = {
        nome: {
            "v": 0, "s": 0, "p": 0,        # vittorie, sconfitte, pareggi
            "pf": 0, "ps": 0,               # punti fatti, subiti
            "sc": 0,                        # scope fatte
            "elo": ELO_INIZIALE             # rating iniziale
        }
        for nome in nomi_bot
    }

    h2h = {}

    scontro_num = 0
    for i, nome_a in enumerate(nomi_bot):
        for j, nome_b in enumerate(nomi_bot):
            if i >= j:
                continue

            scontro_num += 1

            mod_a, cls_a, ckpt_a = bot_disponibili[nome_a]
            mod_b, cls_b, ckpt_b = bot_disponibili[nome_b]
            bot_a = crea_bot(mod_a, cls_a, ckpt_a)
            bot_b = crea_bot(mod_b, cls_b, ckpt_b)

            print(f"[{scontro_num}/{n_scontri}] {nome_a} vs {nome_b} ... ", end="", flush=True)

            v_a = v_b = p = 0
            pf_a = pf_b = sc_a = sc_b = 0

            for n in range(n_partite):
                a_inizia = (n % 2 == 0) if ALTERNA_INIZIO else True
                partita = PartitaCLI(
                    bot_a, bot_b,
                    a_idx=0 if a_inizia else 1,
                    verbose=VERBOSE
                )
                offset = scontro_num * 10000 + n
                ris = partita.gioca(seed=seme_inizio + offset)

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

            print(f"{v_a}-{v_b}-{p}")

            # -- aggiornamento Elo batch -----------------------------------
            sa = (v_a + 0.5 * p) / n_partite   # punteggio normalizzato di A
            ra = classifica[nome_a]["elo"]
            rb = classifica[nome_b]["elo"]
            classifica[nome_a]["elo"], classifica[nome_b]["elo"] = aggiorna_elo(ra, rb, sa)
            # ----------------------------------------------------------------

            # -- confidenza Beta‑Binomiale per questo scontro ---------------
            conf_a, conf_b, livello, migliore = confidenza_migliore(v_a, v_b)
            h2h[(nome_a, nome_b)] = {
                "v_a": v_a, "v_b": v_b, "p": p,
                "conf_a": conf_a, "conf_b": conf_b, "livello": livello,
                "migliore": migliore
            }
            # ----------------------------------------------------------------

            # Accumulo statistiche tradizionali
            classifica[nome_a]["v"] += v_a
            classifica[nome_a]["s"] += v_b
            classifica[nome_a]["p"] += p
            classifica[nome_a]["pf"] += pf_a
            classifica[nome_a]["ps"] += pf_b
            classifica[nome_a]["sc"] += sc_a

            classifica[nome_b]["v"] += v_b
            classifica[nome_b]["s"] += v_a
            classifica[nome_b]["p"] += p
            classifica[nome_b]["pf"] += pf_b
            classifica[nome_b]["ps"] += pf_a
            classifica[nome_b]["sc"] += sc_b

    # =========================================================================
    # CLASSIFICA FINALE ORDINATA PER ELO
    # =========================================================================
    if STAMPA_CLASSIFICA:
        print(f"\n{'=' * 70}")
        print("  CLASSIFICA FINALE (rating Elo batch)")
        print(f"{'=' * 70}")

        ordinati = sorted(
            classifica.items(),
            key=lambda x: x[1]["elo"],
            reverse=True
        )

        print(f"{'Pos':<4} {'Bot':<18} {'Elo':>8} {'V':>4} {'S':>4} {'P':>4} {'%V':>6} {'Diff':>6} {'Scope':>6}")
        print("-" * 70)
        for pos, (nome, stat) in enumerate(ordinati, 1):
            total = stat["v"] + stat["s"] + stat["p"]
            perc = (stat["v"] / total * 100) if total > 0 else 0
            diff = stat["pf"] - stat["ps"]
            print(
                f"{pos:<4} {nome:<18} {stat['elo']:>8.1f} {stat['v']:>4} {stat['s']:>4} {stat['p']:>4} {perc:>6.1f} {diff:>6} {stat['sc']:>6}"
            )

    # =========================================================================
    # MATRICE SCONTRI DIRETTI (confidenza Beta‑Binomiale)
    # =========================================================================
    if STAMPA_DETTAGLI:
        print(f"\n{'=' * 70}")
        print("  MATRICE SCONTRI DIRETTI (probabilità Beta‑Binomiale)")
        print(f"{'=' * 70}")

        print(f"{'':<18}", end="")
        for nome in nomi_bot:
            print(f" {nome[:8]:>8}", end="")
        print()

        for nome_a in nomi_bot:
            print(f"{nome_a:<18}", end="")
            for nome_b in nomi_bot:
                if nome_a == nome_b:
                    print(f" {'---':>8}", end="")
                else:
                    # Prendi i dati dello scontro (in qualunque ordine siano memorizzati)
                    if (nome_a, nome_b) in h2h:
                        dati = h2h[(nome_a, nome_b)]
                        conf = dati["conf_a"]  # A è nome_a, B è nome_b
                    else:
                        dati = h2h[(nome_b, nome_a)]
                        conf = dati["conf_b"]  # A è nome_b, B è nome_a (invertiti)
                    print(f" {conf:>7.1f}%", end="")
            print()

        print(f"\n{'=' * 70}")
        print("  DETTAGLIO SCONTRI (confidenza Beta‑Binomiale)")
        print(f"{'=' * 70}")

        for (nome_a, nome_b), dati in sorted(h2h.items()):
            v_a, v_b, p = dati["v_a"], dati["v_b"], dati["p"]
            conf_a, conf_b, livello, migliore = (
                dati["conf_a"], dati["conf_b"], dati["livello"], dati["migliore"]
            )
            n_dec = v_a + v_b

            print(f"\n{nome_a} vs {nome_b}: {v_a}-{v_b}-{p}")
            print(f"  Win rate {nome_a}: {v_a / n_dec * 100:.1f}% ({n_dec} decisive)")

            if migliore == "A":
                print(f"  → {nome_a} migliore con {conf_a:.1f}% confidenza ({livello})")
            elif migliore == "B":
                print(f"  → {nome_b} migliore con {conf_b:.1f}% confidenza ({livello})")
            else:
                print(f"  → Nessun bot significativamente migliore")

    print(f"\n{'=' * 70}")
    print("Campionato terminato!")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()