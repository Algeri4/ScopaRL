# gui/__init__.py
# Package GUI Scopa Bergamasca
"""
REGOLAMENTO DELLA SCOPA BERGAMASCA
Versione 2 Giocatori – 4 Carte in Banco – Due Mani da 9 Carte
1. INTRODUZIONE E MATERIALE
Cosa serve per giocare:

    Un mazzo di 40 carte italiane (Napoletane): i semi sono Denari ♦, Coppe ♥, Spade ♠, Bastoni ♣
    Le carte per seme sono: Asso (1), 2, 3, 4, 5, 6, 7, Fante (8), Cavallo (9), Re (10)
    2 giocatori
    Un foglio per segnare i punti

Obiettivo del gioco:
Accumulare punti catturando carte dal tavolo e realizzando "scope". Vince chi per primo raggiunge 11 punti totali (o il punteggio concordato prima di iniziare).
2. PREPARAZIONE DELLA PARTITA
2.1 Chi è il mazziere
Il mazziere della prima mano viene scelto per sorteggio, per comune accordo, o estraendo carte: chi pesca la carta più alta (o il Re di Denari) diventa mazziere.
Il mazziere cambia ad ogni mano, passando in senso orario (o semplicemente si alternano i due giocatori).
2.2 Taglio del mazzo
Prima di distribuire, il mazziere fa "tagliare" il mazzo all'avversario (il giocatore alla sua destra), che divide il mazzo in due parti e il mazziere ricompone.
2.3 Distribuzione delle carte (VARIANTE BERGAMASCA)
Ecco la distribuzione specifica di questa versione:

    Il mazziere distribuisce 9 carte coperte al primo giocatore (una alla volta)
    Poi distribuisce 9 carte coperte al secondo giocatore (una alla volta)
    Infine, mette 4 carte scoperte al centro del tavolo (il "banco")

Totale carte distribuite: 9 + 9 + 4 = 22 carte.
Rimangono nel tallone: 40 - 22 = 18 carte.

    ⚠️ Regola speciale del banco: Se tra le 4 carte iniziali sul banco ci sono 3 o 4 Re, la mano è considerata invalida (nessuno potrebbe fare scopa). Si rimescolano tutte le carte e si ridistribuisce.

3. SVOLGIMENTO DEL GIOCO
3.1 Ordine di gioco
Inizia a giocare il giocatore alla destra del mazziere (l'avversario), poi si alternano. Il turno passa da un giocatore all'altro.
3.2 La giocata
A turno, ogni giocatore deve calare una carta dalla propria mano sul tavolo. Ci sono tre possibilità:
A) PRESA SINGOLA (stesso valore)
Se sul banco c'è una carta dello stesso valore di quella giocata, il giocatore la prende.
Esempio: Giochi un 5 e sul banco c'è un 5 → prendi quel 5.
B) PRESA MULTIPLA (somma)
Se sul banco ci sono due o più carte la cui somma dei valori è uguale alla carta giocata, il giocatore le prende tutte.
Esempio: Giochi un 7 e sul banco ci sono un 3 e un 4 → prendi 3+4.
C) NESSUNA PRESA (carta "balla")
Se nessuna carta sul banco corrisponde per valore o somma, la carta giocata rimane sul banco scoperta, a disposizione del prossimo giocatore.
4. REGOLE IMPORTANTI SULLE PRESE
4.1 Priorità della presa singola
Se esistono sia una presa singola che una presa multipla possibili con la stessa carta, è OBBLIGATORIO fare la presa singola (prendere la carta dello stesso valore).
Esempio: Sul banco ci sono un 5, un 2 e un 3. Tu giochi un 5. Devi prendere il 5, NON puoi prendere 2+3.
4.2 Scelta tra prese multiple
Se esistono più combinazioni possibili di somma (e nessuna presa singola), il giocatore può scegliere quale combinazione prendere.
Esempio: Sul banco ci sono Asso(1), 3, 4, 5. Tu giochi un Cavallo(9). Puoi scegliere tra:

    5 + 4 = 9
    5 + 3 + 1 = 9
    Scegli tu quale combinazione prendere.

4.3 La SCOPA
Quando un giocatore, con una singola giocata, riesce a prendere TUTTE le carte presenti sul banco (lasciandolo completamente vuoto), ha realizzato una SCOPA!
Valore: Ogni scopa vale 1 punto aggiuntivo.
Come segnarla: La carta usata per fare scopa viene messa di traverso nel mazzetto delle proprie prese, in modo da ricordare a fine mano quante scope si sono fatte.

    ⚠️ ATTENZIONE: Se la scopa viene fatta con l'ultima carta giocata nell'ultima mano, NON vale punto! È considerata una presa normale.

5. RINNOVO DELLE CARTE
Nella Scopa classica si ridistribuiscono 3 carte alla volta.
Nella versione Bergamasca con 9+9 carte, la distribuzione iniziale è diversa:

    All'inizio ogni giocatore ha 9 carte in mano
    Il banco ha 4 carte
    Giocate tutte le 9 carte (9 turni a testa), finisce la prima mano
    A quel punto, il mazziere distribuisce le carte rimanenti dal tallone: 9 carte al primo giocatore e 9 al secondo (o le restanti 18 divise equamente)
    Si gioca la seconda mano con le nuove carte
    Quando finiscono tutte le carte del mazzo, la partita termina

In sintesi: Si giocano 2 mani complete da 9 carte ciascuna (18 giocate a testa), con 4 carte fisse in banco all'inizio.
6. FINE DELLA MANO E CARTE RIMANENTI
Quando tutte le carte sono state giocate:

    Se sul banco rimangono ancora delle carte, vanno al giocatore che ha fatto l'ultima presa (non conta come scopa)
    Si procede al conteggio dei punti

7. CONTEGGIO DEI PUNTI (FONDAMENTALE!)
Alla fine di ogni mano (smazzata), si contano i punti. Sono in palio fino a 5 punti per mano:
Table
Punto	Descrizione	Condizione di vittoria
1. SCOPE	Ogni scopa realizzata	1 punto per ogni scopa
2. CARTE (o "Lunga")	Chi ha preso più carte in totale	Più di 20 carte (su 40). In caso di parità 20-20, nessuno prende il punto
3. DENARI (o "Ori")	Chi ha preso più carte di Denari	Più di 5 denari (su 10). In caso di parità 5-5, nessuno prende il punto
4. SETTEBELLO	Chi ha preso il 7 di Denari	1 punto fisso (nessuna parità possibile)
5. PRIMIERA	Chi ha la primiera più alta	Vedi spiegazione dettagliata sotto. In caso di parità, nessuno prende il punto
8. LA PRIMIERA – GUIDA DETTAGLIATA PER PRINCIPIANTI
La Primiera è il punto più complesso della Scopa. Leggi attentamente!
8.1 Cos'è la Primiera?
La Primiera è un punteggio speciale che si calcola solo alla fine della mano, usando le carte che hai catturato durante il gioco.
8.2 Requisito fondamentale
Per poter calcolare la Primiera, devi aver preso almeno una carta per ogni seme (almeno un Denaro, una Coppa, una Spada e un Bastone).
Se ti manca anche solo un seme, non puoi fare Primiera e il punto va automaticamente all'avversario (se lui ha tutti e 4 i semi).
8.3 Come si calcola
Dalle carte che hai preso, prendi la carta con il valore di Primiera più alto per ogni seme (una per seme, quindi 4 carte totali).
Somma i loro "punti-Primiera" secondo questa tabella:
Table
Carta	Valore Primiera
7	21 punti
6	18 punti
Asso	16 punti
5	15 punti
4	14 punti
3	13 punti
2	12 punti
Fante, Cavallo, Re	10 punti
8.4 Esempi pratici di calcolo
Esempio 1 – Vince il Giocatore A:

    Giocatore A ha preso: 7♦, 6♥, 7♠, Asso♣
    → Primiera: 21 + 18 + 21 + 16 = 76 punti
    Giocatore B ha preso: 5♦, 4♥, 6♠, 3♣
    → Primiera: 15 + 14 + 18 + 13 = 60 punti

Vince la Primiera il Giocatore A (76 > 60). A prende 1 punto.
Esempio 2 – Pareggio perfetto:

    Giocatore A ha: 7♦, 7♥, 6♠, 6♣
    → 21 + 21 + 18 + 18 = 78 punti
    Giocatore B ha: 7♠, 7♣, 6♦, 6♥
    → 21 + 21 + 18 + 18 = 78 punti

Pareggio! Nessuno prende il punto della Primiera.
Esempio 3 – Attenzione allo stesso seme!

    Giocatore A ha preso: 7♦, 6♦, 7♠, Asso♣
    → Per i Denari prendi solo il 7 (21 punti), il 6♦ non conta perché è dello stesso seme!
    → Primiera: 21 (7♦) + 21 (7♠) + 16 (Asso♣) + ?
    → Manca la quarta carta di un seme diverso! Se il giocatore non ha una carta di Coppe, la Primiera è nulla.

Esempio 4 – Tre 7 non bastano!

    Giocatore A ha: 7♦, 7♥, 7♠, 2♣
    → 21 + 21 + 21 + 12 = 75 punti
    Giocatore B ha: 7♣, 6♦, 6♥, 6♠
    → 21 + 18 + 18 + 18 = 75 punti

Pareggio! Anche se A ha tre 7, il punteggio totale è uguale. Nessuno prende il punto.
Esempio 5 – Il "Settanta" (Primiera massima)
Se un giocatore riesce a prendere tutti e quattro i 7 (7♦, 7♥, 7♠, 7♣), ha la Primiera massima possibile:
→ 21 + 21 + 21 + 21 = 84 punti
Questa combinazione si chiama "Settanta" e in alcune varianti vale un punto aggiuntivo (oltre al punto della Primiera). Nella versione standard conta come Primiera normale, ma è imbattibile!
8.5 Strategia per la Primiera

    I 7 sono le carte più importanti (valgono 21 punti)
    I 6 sono secondi (18 punti)
    Gli Assi sono terzi (16 punti)
    Cerca di prendere almeno una carta per ogni seme, altrimenti perdi automaticamente il punto
    Ricorda: le figure (Fante, Cavallo, Re) valgono tutte solo 10 punti nella Primiera, anche se nel gioco valgono 8, 9 e 10!

9. FINE DELLA PARTITA E VITTORIA

    I punti ottenuti in ogni mano si sommano progressivamente
    Vince chi per primo raggiunge 11 punti (o il punteggio concordato: 11, 16 o 21)
    Se entrambi i giocatori raggiungono 11+ punti nella stessa mano, si continua a giocare mani aggiuntive finché uno non supera l'altro
    Se la partita finisce in parità, si gioca un'altra mano di spareggio

"""