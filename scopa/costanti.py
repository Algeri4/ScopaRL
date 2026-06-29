# scopa/costanti.py
# Sorgente unica della verità per tutte le costanti del gioco

# Semi
SEMI = ["bastoni", "spade", "coppe", "denari"]

# Valori nominali (1=Asso, 8=Fante, 9=Cavallo, 10=Re)
VALORI = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# Nomi leggibili
NOMI_CARTE = {
    1: "Asso", 2: "2", 3: "3", 4: "4", 5: "5",
    6: "6", 7: "7", 8: "Fante", 9: "Cavallo", 10: "Re"
}

# Valori Primiera
PRIMIERA_VALORI = {
    7: 21, 6: 18, 1: 16, 5: 15, 4: 14, 3: 13, 2: 12,
    8: 10, 9: 10, 10: 10
}

# Carta speciale
SETTEBELLO = ("denari", 7)