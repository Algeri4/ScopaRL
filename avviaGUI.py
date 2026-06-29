#!/usr/bin/env python3
# avvia.py
# Entry point per avviare il gioco dalla root del progetto

import sys
import os

# Assicura che la cartella corrente sia nel path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main import main

if __name__ == "__main__":
    main()