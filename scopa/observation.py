# scopa/observation.py
from .carta import Carta
from .costanti import SEMI


class ObservationBuilder:
    """
    Costruisce lo stato di gioco per il bot.
    L'observation contiene SEMPRE tutta l'informazione grezza disponibile:
    ogni encoder è libero di usarne solo una parte, ma l'env non decide
    per nessuno cosa è "utile" o no.
    """

    @staticmethod
    def build(env, giocatore_idx: int):
        """
        Crea il dizionario osservazione.
        'env' è l'istanza di ScopaEnvironment.
        """
        g = env.giocatore_0 if giocatore_idx == 0 else env.giocatore_1
        avv = env.giocatore_1 if giocatore_idx == 0 else env.giocatore_0

        # Carte note (visibili a tutti)
        note = set(env.tavolo.banco)
        note.update(g.mano)
        note.update(g.prese)
        note.update(avv.prese)

        tutte = {Carta(s, v) for s in SEMI for v in range(1, 11)}
        sconosciute = tutte - note

        return {
            "giocatore_idx": giocatore_idx,
            "mano": list(g.mano),
            "banco": list(env.tavolo.banco),
            "prese_mie": list(g.prese),
            "prese_avversario": list(avv.prese),
            "scope_mie": g.scope,
            "scope_avversario": avv.scope,
            "mano_corrente": env.mano_corrente,
            "carte_mazzo": env.mazzo.rimanenti(),
            "turno": env.turno,
            "punteggi": list(env.punteggi),
            "sconosciute": list(sconosciute),
            "carte_mazzo": env.mazzo.rimanenti(),
            "n_carte_avversario": len(avv.mano),
            "turno": env.turno,
            "azioni_legali": env.get_legal_actions(giocatore_idx),
            "partita_finita": env.partita_finita,
            # NUOVO: storico completo delle mosse di questa smazzata.
            # Ogni elemento: {"turno": idx, "carta": Carta, "prese": [Carta,...], "scopa": bool}
            # Esposto qui (invece che tenuto stateful dentro un encoder) così che
            # qualsiasi ObservationEncoder possa costruirci sopra una feature di
            # memoria/storia rimanendo una funzione pura di observation -> vettore.
            "storico": list(env.storico),
        }

    @staticmethod
    def to_vector(obs: dict) -> list:
        """
        Encoding "storico" mantenuto per retrocompatibilità con codice
        esistente che lo chiama direttamente. Per il training nuovo, usare
        botRL.observation_encoder.StandardEncoder (fa la stessa cosa, ma
        è iniettabile e scambiabile con altri encoder).
        """
        def one_hot(carte, size=40):
            v = [0.0] * size
            for c in carte:
                idx = SEMI.index(c.seme) * 10 + (c.valore - 1)
                v[idx] = 1.0
            return v

        v = []
        v.extend(one_hot(obs["mano"]))
        v.extend(one_hot(obs["banco"]))
        v.extend(one_hot(obs["prese_mie"]))
        v.extend(one_hot(obs["prese_avversario"]))
        v.extend(one_hot(obs["sconosciute"]))
        v.extend([
            obs["scope_mie"] / 10.0,
            obs["scope_avversario"] / 10.0,
            obs["mano_corrente"] / 2.0,
            obs["carte_mazzo"] / 40.0,
            obs["n_carte_avversario"] / 9.0,
            obs["turno"],
            obs["punteggi"][0] / 21.0,
            obs["punteggi"][1] / 21.0,
            len(obs["azioni_legali"]) / 50.0,
            1.0 if obs["partita_finita"] else 0.0,
        ])
        return v