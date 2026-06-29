import itertools
from .carta import Carta
from .costanti import SEMI, PRIMIERA_VALORI  # ← importa da qui

class MotoreScopa:
    """
    Giudice delle regole. Nessuno stato, solo calcoli.
    """

    # --- REGOLE DI PRESA ---

    @staticmethod
    def trova_prese_singole(banco, carta_giocata):
        """
        Ritorna liste di carte dello STESSO VALORE sul banco.
        Esempio: gioco 5, banco ha [5, 3, 2] → ritorna [[5]]
        """
        risultato = []
        for c in banco:
            if c.valore == carta_giocata.valore:
                risultato.append([c])
        return risultato

    @staticmethod
    def trova_prese_multiple(banco, carta_giocata):
        """
        Ritorna combinazioni di 2+ carte sul banco la cui somma è uguale
        al valore della carta giocata.
        Esempio: gioco 9, banco ha [5, 4, 3] → ritorna [[5,4], [5,3,1]...]
        """
        if len(banco) < 2:
            return []

        target = carta_giocata.valore
        risultato = []

        # Prova combinazioni da 2 carte fino a tutte le carte sul banco
        for quante in range(2, len(banco) + 1):
            for combo in itertools.combinations(banco, quante):
                somma = sum(c.valore for c in combo)
                if somma == target:
                    risultato.append(list(combo))

        return risultato

    @staticmethod
    def trova_tutte_prese_legali(banco, carta_giocata):
        """
        REGOLA FONDAMENTALE:
        - Se esiste una presa singola, DEVI farla (è obbligatoria)
        - Altrimenti ritorna tutte le prese multiple possibili
        - Se non c'è nulla, ritorna lista vuota (carta "balla")
        """
        singole = MotoreScopa.trova_prese_singole(banco, carta_giocata)

        if singole:
            return singole  # Obbligo di prendere la carta uguale

        multiple = MotoreScopa.trova_prese_multiple(banco, carta_giocata)
        return multiple

    @staticmethod
    def is_scopa(banco_prima, carte_prese):
        """
        Scopa = prendi TUTTE le carte sul banco.
        banco_prima: lista carte prima della giocata
        carte_prese: lista carte prese (compresa quella giocata? No, solo banco)
        """
        if not banco_prima:
            return False
        return len(banco_prima) == len(carte_prese)

    # --- REGOLE DI PUNTEGGIO ---

    @staticmethod
    def calcola_primiera(prese):
        """
        Calcola il punteggio Primiera.
        Per ogni seme, prende la carta con valore Primiera più alto.
        Se manca un seme, ritorna 0 (non valida).
        """
        migliori = {}  # seme → valore primiera più alto

        for carta in prese:
            vp = PRIMIERA_VALORI[carta.valore]
            seme = carta.seme

            if seme not in migliori or vp > migliori[seme]:
                migliori[seme] = vp

        # Devi avere almeno un seme per tipo
        if len(migliori) < 4:
            return 0

        return sum(migliori.values())

    @staticmethod
    def confronta_primiera(prese_a, prese_b):
        """
        Confronta due primiere.
        Ritorna: (valore_a, valore_b, chi_vince)
        chi_vince: 0 = A, 1 = B, None = parità o entrambi invalidi
        """
        p_a = MotoreScopa.calcola_primiera(prese_a)
        p_b = MotoreScopa.calcola_primiera(prese_b)

        if p_a == 0 and p_b == 0:
            return p_a, p_b, None
        if p_a == 0:
            return p_a, p_b, 1
        if p_b == 0:
            return p_a, p_b, 0

        if p_a > p_b:
            return p_a, p_b, 0
        elif p_b > p_a:
            return p_a, p_b, 1
        else:
            return p_a, p_b, None

    @staticmethod
    def controlla_banco_iniziale(banco):
        """
        Regola Bergamasca: se nel banco iniziale ci sono 3 o 4 Re (valore 10),
        la mano è invalida e si deve ridistribuire.
        """
        re_count = sum(1 for c in banco if c.valore == 10)
        return re_count >= 3