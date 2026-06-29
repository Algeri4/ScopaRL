# gui/caricatore.py
# Caricamento e caching delle immagini delle carte

import os
from PIL import Image, ImageTk
from scopa.carta import Carta
from .costanti_gui import CARTA_L, CARTA_H, ASSETS_DIR, NOMI_FILE, SEMI_DIR


class CaricatoreCarte:
    def __init__(self):
        self.cache = {}
        self.cache_img = {}
        self.retro = None
        self._carica_retro()

    def _carica_retro(self):
        img = Image.new("RGB", (CARTA_L, CARTA_H), "#1a5276")
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        for i in range(0, CARTA_L, 10):
            draw.line([(i, 0), (i, CARTA_H)], fill="#154360", width=1)
        for i in range(0, CARTA_H, 10):
            draw.line([(0, i), (CARTA_L, i)], fill="#154360", width=1)
        draw.rectangle([3, 3, CARTA_L - 3, CARTA_H - 3], outline="#f1c40f", width=2)
        self.retro = ImageTk.PhotoImage(img)

    def get(self, carta: Carta) -> ImageTk.PhotoImage:
        chiave = (carta.seme, carta.valore)
        if chiave in self.cache:
            return self.cache[chiave]

        seme_dir = SEMI_DIR.get(carta.seme, carta.seme.lower())
        nome = NOMI_FILE[carta.valore]
        percorso = os.path.join(ASSETS_DIR, seme_dir, f"{nome}.png")

        if os.path.exists(percorso):
            img = Image.open(percorso)
            img = img.resize((CARTA_L, CARTA_H), Image.Resampling.LANCZOS)
        else:
            img = Image.new("RGB", (CARTA_L, CARTA_H), "white")
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            draw.rectangle([2, 2, CARTA_L - 2, CARTA_H - 2], outline="black", width=2)
            draw.text((10, 10), f"{carta.valore}", fill="black")
            draw.text((10, 60), carta.seme[:3], fill="black")

        self.cache_img[chiave] = img
        photo = ImageTk.PhotoImage(img)
        self.cache[chiave] = photo
        return photo

    def get_ruotata(self, carta: Carta, angolo=90) -> ImageTk.PhotoImage:
        chiave = (carta.seme, carta.valore, angolo)
        if chiave in self.cache:
            return self.cache[chiave]

        chiave_orig = (carta.seme, carta.valore)
        if chiave_orig not in self.cache_img:
            self.get(carta)

        img_orig = self.cache_img[chiave_orig]
        img_ruotata = img_orig.rotate(angolo, expand=True, resample=Image.Resampling.BICUBIC)
        photo = ImageTk.PhotoImage(img_ruotata)
        self.cache[chiave] = photo
        return photo