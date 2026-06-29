# gui/disegno.py
# Rendering del tavolo, mani, mazzetti

import tkinter as tk
from .costanti_gui import (
    Y_AVV_MANO, Y_BANCO, Y_GIOC_MANO, X_MAZZETTO, Y_MAZZETTO_AVV, Y_MAZZETTO_GIOC,
    SPAZIO_CARTE, SLOT_MANO, SLOT_BANCO, CX
)


class Disegnatore:
    def __init__(self, canvas, caricatore):
        self.canvas = canvas
        self.caricatore = caricatore

    def clear(self):
        self.canvas.delete("all")

    def mazzetto(self, x, y, giocatore, scope_cartes):
        n_prese = len(giocatore.prese)
        if n_prese > 0:
            for i in range(min(3, n_prese)):
                offset = i * 2
                self.canvas.create_image(x + offset, y + offset,
                                         image=self.caricatore.retro, tags="static")

        if scope_cartes:
            n_scope = len(scope_cartes)
            spazio_scope = max(15, 35 - n_scope * 4)
            y_scope = y + 75
            start_x_scope = x - ((n_scope - 1) * spazio_scope) // 2
            for i, carta in enumerate(scope_cartes):
                x_scope = start_x_scope + i * spazio_scope
                photo_ruotata = self.caricatore.get_ruotata(carta, 90)
                self.canvas.create_image(x_scope, y_scope, image=photo_ruotata, tags="static")

    def mano_avversario(self, slots, mostra_carte, y_base, calcola_x):
        for i in range(SLOT_MANO):
            carta = slots[i]
            if carta is None:
                continue
            x = calcola_x(i, y_base)
            photo = self.caricatore.get(carta) if mostra_carte else self.caricatore.retro
            self.canvas.create_image(x, y_base, image=photo, tags=("mano_avv", f"avv_{i}"))

    def banco(self, slots, prese_selezionate, calcola_x_banco, carta_uguale, animazione_in_corso, on_click):
        for slot_idx, carta in enumerate(slots):
            if carta is None:
                continue
            x = calcola_x_banco(slot_idx)
            y = Y_BANCO
            photo = self.caricatore.get(carta)

            if not animazione_in_corso:
                selezionata = any(carta_uguale(carta, ps) for ps in prese_selezionate)
                if selezionata:
                    self.canvas.create_rectangle(x - 50, y - 75, x + 50, y + 75,
                                                 outline="#ffeb3b", width=5, fill="",
                                                 tags=("sel", f"sel_{slot_idx}"))

            id_img = self.canvas.create_image(x, y, image=photo, tags=("banco", f"banco_{slot_idx}"))
            self.canvas.tag_bind(id_img, "<Button-1>", lambda e, c=carta: on_click(c))

    def mano_giocatore(self, slots, carta_selezionata, calcola_x_mano, carta_uguale, animazione_in_corso, on_click):
        for i in range(SLOT_MANO):
            carta = slots[i]
            if carta is None:
                continue
            x = calcola_x_mano(i, Y_GIOC_MANO)
            y = Y_GIOC_MANO
            photo = self.caricatore.get(carta)

            if not animazione_in_corso:
                selezionata = carta_uguale(carta_selezionata, carta)
                if selezionata:
                    self.canvas.create_rectangle(x - 50, y - 75, x + 50, y + 75,
                                                 outline="#ffeb3b", width=5, fill="",
                                                 tags=("sel", f"sel_mano_{i}"))

            id_img = self.canvas.create_image(x, y, image=photo, tags=("mano", f"mano_{i}"))
            self.canvas.tag_bind(id_img, "<Button-1>", lambda e, c=carta: on_click(c))

    def selezione(self, x, y, tag):
        self.canvas.create_rectangle(x - 50, y - 75, x + 50, y + 75,
                                     outline="#ffeb3b", width=5, fill="",
                                     tags=("sel", tag))