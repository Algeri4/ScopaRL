# gui/costanti_gui.py
# Costanti e configurazione della GUI

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets", "carte")
BOT_DIR = os.path.join(BASE_DIR, "bot")

CARTA_L = 90
CARTA_H = 140
SPAZIO_CARTE = 100

NOMI_FILE = {
    1: "01_asso", 2: "02", 3: "03", 4: "04", 5: "05",
    6: "06", 7: "07", 8: "08_fante", 9: "09_cavallo", 10: "10_re"
}

SEMI_DIR = {
    "Denari": "denari", "denari": "denari",
    "Coppe": "coppe", "coppe": "coppe",
    "Spade": "spade", "spade": "spade",
    "Bastoni": "bastoni", "bastoni": "bastoni"
}

W = 1200
H = 900
CX = W // 2

Y_AVV_MANO = 130
Y_BANCO = 360
Y_GIOC_MANO = 640

X_MAZZETTO = 100
Y_MAZZETTO_AVV = 120
Y_MAZZETTO_GIOC = 640

SLOT_MANO = 9
SLOT_BANCO = 10