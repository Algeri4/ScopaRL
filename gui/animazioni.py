# gui/animazioni.py
# Tutte le animazioni del gioco

import tkinter as tk
from .costanti_gui import Y_BANCO, CX, X_MAZZETTO, Y_MAZZETTO_AVV, Y_MAZZETTO_GIOC


class GestoreAnimazioni:
    def __init__(self, canvas, root, caricatore):
        self.canvas = canvas
        self.root = root
        self.caricatore = caricatore

    def vola(self, carta, x_from, y_from, x_to, y_to, durata_ms=600, callback=None):
        photo = self.caricatore.get(carta)
        id_img = self.canvas.create_image(x_from, y_from, image=photo, tags="animazione")

        steps = 30
        dx = (x_to - x_from) / steps
        dy = (y_to - y_from) / steps
        delay = durata_ms // steps

        def step(i):
            if i >= steps:
                if callback:
                    callback()
                return
            self.canvas.move(id_img, dx, dy)
            self.root.after(delay, lambda: step(i + 1))

        step(0)
        return id_img

    def lampeggia(self, carte, calcola_posizione, durata_ms=1000, callback=None):
        if not carte:
            if callback:
                callback()
            return

        ids_lampeggio = []
        for carta in carte:
            x, y = calcola_posizione(carta)
            rid = self.canvas.create_rectangle(x - 55, y - 80, x + 55, y + 80,
                                               outline="#ffeb3b", width=8, fill="",
                                               tags="lampeggio")
            ids_lampeggio.append(rid)

        flash_count = [0]

        def flash():
            if flash_count[0] >= 6:
                for rid in ids_lampeggio:
                    self.canvas.delete(rid)
                if callback:
                    callback()
                return
            for rid in ids_lampeggio:
                current = self.canvas.itemcget(rid, "outline")
                new_color = "#ffeb3b" if current == "#1b5e20" else "#1b5e20"
                self.canvas.itemconfig(rid, outline=new_color)
            flash_count[0] += 1
            self.root.after(durata_ms // 6, flash)

        flash()

    def vola_gruppo(self, carte_gruppo, posizioni, x_mazzetto, y_mazzetto, callback=None):
        self.canvas.delete("lampeggio")

        ids_gruppo = []
        for i, c in enumerate(carte_gruppo):
            photo = self.caricatore.get(c)
            x_orig, y_orig = posizioni[(c.seme, c.valore)]
            x_dest = x_mazzetto + (i % 3) * 2
            y_dest = y_mazzetto + (i % 3) * 2
            id_img = self.canvas.create_image(x_orig, y_orig, image=photo, tags="animazione")
            ids_gruppo.append((id_img, x_orig, y_orig, x_dest, y_dest))

        steps = 25
        delay = 800 // steps

        def step(i):
            if i >= steps:
                self.canvas.delete("animazione")
                if callback:
                    callback()
                return
            for id_img, x_orig, y_orig, x_dest, y_dest in ids_gruppo:
                dx = (x_dest - x_orig) / steps
                dy = (y_dest - y_orig) / steps
                self.canvas.move(id_img, dx, dy)
            self.root.after(delay, lambda: step(i + 1))

        step(0)

    def effetto_scopa(self, x, y, ft_scopa, callback=None):
        self.canvas.create_rectangle(
            x - 230, y - 70, x + 230, y + 70,
            fill="#b71c1c", outline="#ffeb3b", width=6,
            tags="effetto_scopa"
        )
        txt = self.canvas.create_text(
            x, y, text="SCOPA!", font=ft_scopa,
            fill="#ffeb3b", tags="effetto_scopa"
        )

        count = [0]

        def pulse():
            if count[0] >= 5:
                self.canvas.delete("effetto_scopa")
                if callback:
                    callback()
                return
            color = "#ffffff" if count[0] % 2 == 0 else "#ffeb3b"
            self.canvas.itemconfig(txt, fill=color)
            count[0] += 1
            self.root.after(250, pulse)

        pulse()