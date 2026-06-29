# tools/taglia_carte.py
from PIL import Image
import os

# Configurazione
INPUT_FILE = "../assets/Carte_bergamasche.jpg"  # metti qui il percorso del tuo file
OUTPUT_DIR = "../assets/carte"

# Ordine dei semi nelle 4 righe (dall'alto al basso)
SEMI = ["bastoni", "spade", "coppe", "denari"]

# Ordine dei valori nelle 10 colonne (da sinistra a destra)
VALORI = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# Nomi file
NOMI_FILE = {
    1: "01_asso", 2: "02", 3: "03", 4: "04", 5: "05",
    6: "06", 7: "07", 8: "08_fante", 9: "09_cavallo", 10: "10_re"
}


def taglia_carte():
    img = Image.open(INPUT_FILE)
    larghezza, altezza = img.size

    # Calcola dimensioni singola carta
    # La griglia è 4 righe × 10 colonne
    carte_per_riga = 10
    carte_per_colonna = 4

    carta_w = larghezza // carte_per_riga
    carta_h = altezza // carte_per_colonna

    print(f"Immagine: {larghezza}x{altezza}")
    print(f"Singola carta: {carta_w}x{carta_h}")
    print(f"Taglio in corso...")

    # Crea cartelle
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for seme in SEMI:
        os.makedirs(os.path.join(OUTPUT_DIR, seme), exist_ok=True)

    # Taglia e salva
    for riga, seme in enumerate(SEMI):          # 0=bastoni, 1=spade, 2=coppe, 3=denari
        for colonna, valore in enumerate(VALORI):  # 0=asso, 1=2, ..., 9=re

            # Coordinate di ritaglio
            left = colonna * carta_w
            upper = riga * carta_h
            right = left + carta_w
            lower = upper + carta_h

            # Ritaglia
            carta = img.crop((left, upper, right, lower))

            # Salva
            nome = NOMI_FILE[valore]
            percorso = os.path.join(OUTPUT_DIR, seme, f"{nome}.png")
            carta.save(percorso, "PNG")

            print(f"  {seme}/{nome}.png  ({valore})")

    print(f"\nFatto! 40 carte salvate in {OUTPUT_DIR}/")


if __name__ == "__main__":
    taglia_carte()