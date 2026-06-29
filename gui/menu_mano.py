# gui/menu_mano.py
# Menu di fine smazzata con dettaglio punteggi - grafica migliorata

import tkinter as tk


def mostra_menu(root, frame_parent, partita_finita, dati, bot_nome, ft_titolo, ft_normale, ft_grande, ft_piccolo,
                on_continua, on_riparti, on_esci, on_abbandona):
    """
    Mostra il menu fine smazzata/partita.
    Ritorna il frame creato.
    """
    # Overlay scuro sopra il canvas
    overlay = tk.Frame(root, bg="#000000")
    overlay.place(x=0, y=0, width=root.winfo_width(), height=root.winfo_height())
    overlay.lower()

    # Frame principale del menu (più largo per ospitare nomi lunghi)
    frame_menu = tk.Frame(root, bg="#0d3b10", padx=0, pady=0,
                          highlightbackground="#f1c40f", highlightthickness=3)
    frame_menu.place(relx=0.5, rely=0.5, anchor="center", width=640, height=600)
    frame_menu.lift()

    titolo = "PARTITA FINITA" if partita_finita else "FINE SMAZZATA"
    tk.Label(frame_menu, text=titolo, font=ft_grande,
             bg="#0d3b10", fg="#f1c40f").pack(pady=(15, 10))

    if dati is None:
        tk.Label(frame_menu, text="Dati smazzata non disponibili",
                 font=ft_normale, bg="#0d3b10", fg="red").pack(pady=20)
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

    # Tronca nome bot se troppo lungo
    bot_nome_corto = bot_nome[:12] if len(bot_nome) > 12 else bot_nome

    # --- TABELLA STILIZZATA ---
    frame_tabella = tk.Frame(frame_menu, bg="#1b5e20", padx=15, pady=15,
                             highlightbackground="#f1c40f", highlightthickness=2)
    frame_tabella.pack(pady=10, padx=25, fill=tk.X)

    # Configura colonne con pesi
    frame_tabella.columnconfigure(0, weight=3)
    frame_tabella.columnconfigure(1, weight=2)
    frame_tabella.columnconfigure(2, weight=2)

    # Header
    _cella(frame_tabella, 0, 0, "CATEGORIA", ft_titolo, "#154360", "#f1c40f", "w")
    _cella(frame_tabella, 0, 1, "TU", ft_titolo, "#154360", "#f1c40f", "center")
    _cella(frame_tabella, 0, 2, bot_nome_corto.upper(), ft_titolo, "#154360", "#f1c40f", "center")

    # Dati
    righe = [
        ("Carte", carte_0, carte_1),
        ("Denari", denari_0, denari_1),
        ("Settebello", "SÌ" if settebello_0 else "NO", "SÌ" if settebello_1 else "NO"),
        ("Primiera", prim_0, prim_1),
        ("Scope", scope_0, scope_1),
        ("Punti mano", punti_mano[0], punti_mano[1]),
    ]

    for i, (label, v0, v1) in enumerate(righe, start=1):
        bg_col = "#1b5e20" if i % 2 == 1 else "#144a18"
        _cella(frame_tabella, i, 0, label, ft_normale, bg_col, "white", "w")
        _cella(frame_tabella, i, 1, str(v0), ft_normale, bg_col,
               "#ffeb3b" if v0 > v1 else "white", "center")
        _cella(frame_tabella, i, 2, str(v1), ft_normale, bg_col,
               "#ffeb3b" if v1 > v0 else "white", "center")

    # Riga totale
    n = len(righe) + 1
    _cella(frame_tabella, n, 0, "TOTALE", ft_grande, "#0d3b10", "#f1c40f", "w")
    _cella(frame_tabella, n, 1, str(punti_totali[0]), ft_grande, "#0d3b10", "#4caf50", "center")
    _cella(frame_tabella, n, 2, str(punti_totali[1]), ft_grande, "#0d3b10", "#4caf50", "center")

    # --- PULSANTI ---
    _crea_pulsanti(frame_menu, partita_finita, punti_totali, ft_titolo, ft_normale, ft_grande,
                   on_continua, on_riparti, on_esci, on_abbandona)

    return frame_menu


def _cella(parent, r, c, testo, font, bg, fg, anchor):
    """Crea una cella della tabella."""
    sticky = {"w": "w", "center": "nsew", "e": "e"}.get(anchor, "nsew")
    lbl = tk.Label(parent, text=testo, font=font, bg=bg, fg=fg, anchor=anchor)
    lbl.grid(row=r, column=c, padx=5, pady=3, sticky=sticky)
    return lbl


def _crea_pulsanti(frame_menu, partita_finita, punti_totali, ft_titolo, ft_normale, ft_grande,
                   on_continua, on_riparti, on_esci, on_abbandona):
    frame_btn = tk.Frame(frame_menu, bg="#0d3b10")
    frame_btn.pack(pady=20)

    if partita_finita:
        if punti_totali:
            vincitore = 0 if punti_totali[0] > punti_totali[1] else 1
            vinc_nome = "TU" if vincitore == 0 else "Avversario"
            tk.Label(frame_menu, text=f"VINCE: {vinc_nome}!",
                     font=ft_grande, bg="#0d3b10", fg="#ffeb3b").pack(pady=(0, 5))

        tk.Button(frame_btn, text="RIPARTI", font=ft_titolo,
                  bg="#388e3c", fg="white", width=12, height=1,
                  command=on_riparti).pack(side=tk.LEFT, padx=10)
        tk.Button(frame_btn, text="ESCI", font=ft_titolo,
                  bg="#d32f2f", fg="white", width=12, height=1,
                  command=on_esci).pack(side=tk.LEFT, padx=10)
    else:
        tk.Button(frame_btn, text="CONTINUA", font=ft_titolo,
                  bg="#388e3c", fg="white", width=12, height=1,
                  command=on_continua).pack(side=tk.LEFT, padx=10)
        tk.Button(frame_btn, text="ABBANDONA", font=ft_titolo,
                  bg="#d32f2f", fg="white", width=12, height=1,
                  command=on_abbandona).pack(side=tk.LEFT, padx=10)