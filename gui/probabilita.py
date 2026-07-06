# gui/probabilita.py
# Tabella probabilità carte avversario (vista dal bot)
# Usa scopa.probabilita per i calcoli

import tkinter as tk
from typing import List
from scopa.carta import Carta
from scopa.probabilita import calcola_tutte_proabilita, calcola_parametri


class TabellaProbabilita:
    """
    Tabella 10 righe x 6 colonne che mostra, dal punto di vista del bot,
    la probabilità che il giocatore umano abbia ALMENO 1, 2, 3 o 4 carte
    di ciascun valore (1-10).
    """

    # Colori
    BG_HEADER = "#154360"
    BG_RIGA_DISPARI = "#1b5e20"
    BG_RIGA_PARI = "#144a18"
    FG_HEADER = "#f1c40f"
    FG_NORMALE = "#ffffff"
    FG_ZERO = "#888888"

    def __init__(self, canvas, x, y, larghezza, altezza_riga, altezza_header):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.larghezza = larghezza
        self.altezza_riga = altezza_riga
        self.altezza_header = altezza_header

        self.larghezze_col = [28, 45, 55, 55, 55, 55]
        self.font_header = ("Helvetica", 8, "bold")
        self.font_dato = ("Courier", 9)
        self.font_valore = ("Helvetica", 10, "bold")

        self.widget_ids = []

    def _clear(self):
        for wid in self.widget_ids:
            self.canvas.delete(wid)
        self.widget_ids = []

    def _crea_rettangolo(self, x1, y1, x2, y2, fill, outline="#f1c40f", width=1):
        rid = self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill,
                                         outline=outline, width=width, tags="tabella_prob")
        self.widget_ids.append(rid)
        return rid

    def _crea_testo(self, x, y, testo, font, fill, anchor="center"):
        tid = self.canvas.create_text(x, y, text=testo, font=font,
                                      fill=fill, anchor=anchor, tags="tabella_prob")
        self.widget_ids.append(tid)
        return tid

    def disegna(self, note: List[Carta], mano_umano: List[Carta], carte_mazzo: int):
        self._clear()

        # Costruisci observation fittizia per riusare la logica condivisa
        n_mano_umano = len(mano_umano)
        n_sconosciute = carte_mazzo + n_mano_umano

        # Calcola carte passate per valore
        from scopa.probabilita import conta_carte_per_valore
        carte_passate = conta_carte_per_valore(note)

        # Header
        y_curr = self.y
        self._crea_rettangolo(self.x, y_curr,
                              self.x + self.larghezza, y_curr + self.altezza_header,
                              self.BG_HEADER, width=2)
        headers = ["V", "Pass", "P(≥1)", "P(≥2)", "P(≥3)", "P(≥4)"]
        x_col = self.x
        for i, h in enumerate(headers):
            cx = x_col + self.larghezze_col[i] // 2
            self._crea_testo(cx, y_curr + self.altezza_header // 2,
                             h, self.font_header, self.FG_HEADER)
            x_col += self.larghezze_col[i]

        # Righe valori 1-10
        from scopa.probabilita import probabilita_cumulative
        for valore in range(1, 11):
            y_curr += self.altezza_header if valore == 1 else self.altezza_riga
            bg = self.BG_RIGA_DISPARI if valore % 2 == 1 else self.BG_RIGA_PARI

            self._crea_rettangolo(self.x, y_curr,
                                  self.x + self.larghezza, y_curr + self.altezza_riga,
                                  bg, width=1)

            passate = carte_passate.get(valore, 0)
            rimanenti = 4 - passate

            if rimanenti <= 0 or n_sconosciute <= 0 or n_mano_umano <= 0:
                probs = [0.0, 0.0, 0.0, 0.0]
            else:
                probs = probabilita_cumulative(rimanenti, n_sconosciute, n_mano_umano)

            x_col = self.x
            celle = [str(valore), str(passate)] + [self._fmt_prob(p) for p in probs]

            for i, testo in enumerate(celle):
                cx = x_col + self.larghezze_col[i] // 2
                fg = self.FG_NORMALE if i < 2 or probs[i - 2] > 0 else self.FG_ZERO
                font = self.font_valore if i == 0 else self.font_dato
                self._crea_testo(cx, y_curr + self.altezza_riga // 2,
                                 testo, font, fg)
                x_col += self.larghezze_col[i]

        # Bordo esterno
        tot_h = self.altezza_header + 10 * self.altezza_riga
        self._crea_rettangolo(self.x, self.y,
                              self.x + self.larghezza, self.y + tot_h,
                              "", outline=self.FG_HEADER, width=2)

    def _fmt_prob(self, p: float) -> str:
        if p <= 0:
            return "0%"
        if p >= 0.999:
            return "100%"
        return f"{p:.1%}"