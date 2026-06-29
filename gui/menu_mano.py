# gui/menu_mano.py
# Menu di fine smazzata con dettaglio punteggi

import tkinter as tk


def mostra_menu(root, frame_parent, partita_finita, dati, bot_nome, ft_titolo, ft_normale, ft_grande, ft_piccolo,
                on_continua, on_riparti, on_esci, on_abbandona):
    """
    Mostra il menu fine smazzata/partita.
    Ritorna il frame creato (per poterlo distruggere dopo).
    """
    frame_menu = tk.Frame(root, bg="#0d3b10", padx=30, pady=30,
                          highlightbackground="#f1c40f", highlightthickness=3)
    frame_menu.place(relx=0.5, rely=0.5, anchor="center", width=600, height=560)

    titolo = "PARTITA FINITA" if partita_finita else "FINE SMAZZATA"
    tk.Label(frame_menu, text=titolo, font=ft_grande,
             bg="#0d3b10", fg="#f1c40f").pack(pady=10)

    if dati is None:
        tk.Label(frame_menu, text="Dati smazzata non disponibili",
                 font=ft_normale, bg="#0d3b10", fg="red").pack()
        _crea_pulsanti(frame_menu, partita_finita, None, ft_titolo, ft_normale, ft_grande,
                       on_continua, on_riparti, on_esci, on_abbandona)
        return frame_menu

    prese_0 = dati["prese_0"]
    prese_1 = dati["prese_1"]
    scope_0 = dati["scope_0"]
    scope_1 = dati["scope_1"]
    punti_mano = dati["punti_mano"]
    punti_totali = dati["punti_totali"]
    dettagli = dati["dettagli"]

    carte_0 = len(prese_0)
    carte_1 = len(prese_1)
    denari_0 = sum(1 for c in prese_0 if c.seme.lower() == "denari")
    denari_1 = sum(1 for c in prese_1 if c.seme.lower() == "denari")
    settebello_0 = any(c.seme.lower() == "denari" and c.valore == 7 for c in prese_0)
    settebello_1 = any(c.seme.lower() == "denari" and c.valore == 7 for c in prese_1)
    prim_0 = dettagli["p0"]["primiera_valore"]
    prim_1 = dettagli["p1"]["primiera_valore"]

    tk.Label(frame_menu, text="DETTAGLIO PUNTI SMAZZATA:",
             font=ft_titolo, bg="#0d3b10", fg="#ffeb3b").pack(pady=(10, 5))

    frame_dettagli = tk.Frame(frame_menu, bg="#0d3b10")
    frame_dettagli.pack(pady=5)

    tk.Label(frame_dettagli, text=f"{'':15s} {'TU':10s} {bot_nome:15s}",
             font=ft_titolo, bg="#0d3b10", fg="white").grid(row=0, column=0, columnspan=3, pady=5)

    righe = [
        ("Carte:", carte_0, carte_1),
        ("Denari:", denari_0, denari_1),
        ("Settebello:", "SÌ" if settebello_0 else "NO", "SÌ" if settebello_1 else "NO"),
        ("Primiera:", prim_0, prim_1),
        ("Scope:", scope_0, scope_1),
        ("Punti mano:", punti_mano[0], punti_mano[1]),
    ]

    for i, (label, v0, v1) in enumerate(righe, start=1):
        tk.Label(frame_dettagli, text=f"{label:15s} {v0:10s} {v1:15s}",
                 font=ft_normale, bg="#0d3b10", fg="white").grid(
                     row=i, column=0, columnspan=3, sticky="w")

    tk.Label(frame_dettagli, text=f"{'─' * 42}",
             font=ft_normale, bg="#0d3b10", fg="#f1c40f").grid(
                 row=len(righe)+1, column=0, columnspan=3, pady=5)

    tk.Label(frame_dettagli,
             text=f"{'TOTALE:':15s} {punti_totali[0]:10d} {punti_totali[1]:15d}",
             font=ft_grande, bg="#0d3b10", fg="#4caf50").grid(
                 row=len(righe)+2, column=0, columnspan=3, sticky="w")

    _crea_pulsanti(frame_menu, partita_finita, punti_totali, ft_titolo, ft_normale, ft_grande,
                   on_continua, on_riparti, on_esci, on_abbandona)

    return frame_menu


def _crea_pulsanti(frame_menu, partita_finita, punti_totali, ft_titolo, ft_normale, ft_grande,
                   on_continua, on_riparti, on_esci, on_abbandona):
    frame_btn = tk.Frame(frame_menu, bg="#0d3b10")
    frame_btn.pack(pady=20)

    if partita_finita:
        if punti_totali:
            vincitore = 0 if punti_totali[0] > punti_totali[1] else 1
            vinc_nome = "TU" if vincitore == 0 else "Avversario"
            tk.Label(frame_menu, text=f"VINCE: {vinc_nome}!",
                     font=ft_grande, bg="#0d3b10", fg="#ffeb3b").pack(pady=5)

        tk.Button(frame_btn, text="RIPARTI", font=ft_titolo,
                  bg="#388e3c", fg="white", width=12, command=on_riparti).pack(side=tk.LEFT, padx=10)
        tk.Button(frame_btn, text="ESCI", font=ft_titolo,
                  bg="#d32f2f", fg="white", width=12, command=on_esci).pack(side=tk.LEFT, padx=10)
    else:
        tk.Button(frame_btn, text="CONTINUA", font=ft_titolo,
                  bg="#388e3c", fg="white", width=12, command=on_continua).pack(side=tk.LEFT, padx=10)
        tk.Button(frame_btn, text="ABBANDONA", font=ft_titolo,
                  bg="#d32f2f", fg="white", width=12, command=on_abbandona).pack(side=tk.LEFT, padx=10)