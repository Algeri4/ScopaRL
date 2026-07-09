import random


class BotGEMINI:
    """
    Bot per Scopa Bergamasca progettato da Gemini.
    Strategia:
    1. Massimizza i punti (Settebello, Scope, Primiera, Denari).
    2. Difesa ferrea contro le Scope dell'avversario.
    3. Gestione intelligente degli scarti.
    """

    def nome(self):
        return "BotGemini"

    def scegli_mossa(self, observation):
        azioni = observation["azioni_legali"]
        banco = observation["banco"]
        mano = observation["mano"]
        sconosciute = observation["sconosciute"]

        # FIX ERROR: Verifica se a[1] è None prima di calcolarne la lunghezza
        azioni_prese = [a for a in azioni if a[1] is not None and len(a[1]) > 0]
        azioni_balla = [a for a in azioni if a[1] is None or len(a[1]) == 0]

        # 1. VALUTAZIONE PRESE
        if azioni_prese:
            migliore_presa = None
            miglior_punteggio_presa = -9999

            for azione in azioni_prese:
                carta_giocata, carte_prese = azione
                punteggio = self._valuta_presa(carta_giocata, carte_prese, banco)

                # Malus se la presa lascia un banco facilmente attaccabile (somma <= 10)
                carte_rimanenti_banco = [c for c in banco if c not in carte_prese]
                if not self._is_scopa(banco, carte_prese) and len(carte_rimanenti_banco) > 0:
                    somma_rimanente = sum(c.valore for c in carte_rimanenti_banco)
                    if somma_rimanente <= 10:
                        # Controlla se l'avversario ha ancora carte di quel valore
                        se_possibile = any(c.valore == somma_rimanente for c in sconosciute)
                        if se_possibile:
                            punteggio -= 250  # Rischio scopa alto

                if punteggio > miglior_punteggio_presa:
                    miglior_punteggio_presa = punteggio
                    migliore_presa = azione

            return migliore_presa

        # 2. VALUTAZIONE BALLE (nessuna presa possibile)
        migliore_balla = None
        miglior_punteggio_balla = -9999

        for azione in azioni_balla:
            carta_giocata = azione[0]
            banco_futuro = banco + [carta_giocata]

            punteggio = self._valuta_balla(carta_giocata, banco_futuro, sconosciute)

            if punteggio > miglior_punteggio_balla:
                miglior_punteggio_balla = punteggio
                migliore_balla = azione

        return migliore_balla if migliore_balla else random.choice(azioni)

    def _valuta_presa(self, carta_giocata, carte_prese, banco):
        punteggio = 0

        # Scopa!
        if self._is_scopa(banco, carte_prese):
            punteggio += 1500

        for c in carte_prese:
            # Settebello
            if c.valore == 7 and c.seme.lower() == "denari":
                punteggio += 500
            # Altri 7 (Primiera)
            elif c.valore == 7:
                punteggio += 200
            # Denari
            if c.seme.lower() == "denari":
                punteggio += 80
            # Primiera: 6 (valore alto per primiera)
            if c.valore == 6:
                punteggio += 50
            # Valore numerico (le carte figurate e alte aggiungono peso per la quantità)
            punteggio += c.valore

        return punteggio

    def _valuta_balla(self, carta, banco_futuro, sconosciute):
        punteggio = 0
        somma_banco = sum(c.valore for c in banco_futuro)

        # MALUS: non buttare carte di valore se possibile
        if carta.valore == 7 and carta.seme.lower() == "denari":
            punteggio -= 2000  # Mai regalare il Settebello
        elif carta.valore == 7:
            punteggio -= 800
        elif carta.seme.lower() == "denari":
            punteggio -= 300

        # Rischio Scopa Diretto: l'avversario ha una singola carta uguale alla somma del banco?
        if somma_banco <= 10:
            possibili_scope = [c for c in sconosciute if c.valore == somma_banco]
            if possibili_scope:
                punteggio -= 600 * len(possibili_scope)
            else:
                punteggio += 500

        # Preferisci calare carte basse (es. 1, 2) se non fanno fare scopa facilmente
        punteggio -= (carta.valore * 10)

        return punteggio

    def _is_scopa(self, banco_prima, carte_prese):
        return len(banco_prima) > 0 and len(banco_prima) == len(carte_prese)