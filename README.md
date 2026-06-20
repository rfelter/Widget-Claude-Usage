# ⬡ Claude Usage Widget — Windows

Widget flottante always-on-top che mostra in tempo reale:

- **Sessione 5h** — % usata + countdown al reset
- **Settimana** — % usata + countdown al reset  
- **Sonnet** — solo se incluso nel tuo piano (Max/Team)

Stessi dati di `Impostazioni → Utilizzo` in Claude Desktop.

---

## Installazione e Configurazione

### Passo 1 — Python
Se non ce l'hai già, scaricalo da **https://python.org** (versione 3.10+).  
⚠ Durante l'installazione, spunta **"Add Python to PATH"**.

### Passo 2 — Recuperare la `sessionKey` da Claude.ai
Non è necessario installare Node.js o utilizzare il terminale per autenticarsi. Puoi recuperare la chiave direttamente dal browser:
1. Apri il browser (Chrome, Edge, Firefox, ecc.) e vai su [claude.ai](https://claude.ai) (assicurati di aver effettuato l'accesso).
2. Premi **F12** sulla tastiera (o fai clic destro -> *Ispeziona*) per aprire gli Strumenti per sviluppatori.
3. Vai alla scheda **Applicazione** (o **Application** / **Storage** / **Archiviazione** a seconda del browser).
4. Nel menu laterale, espandi la voce **Cookie** e seleziona `https://claude.ai`.
5. Cerca la riga con nome **`sessionKey`** e copia il suo valore (è una stringa che inizia con `sk-ant-sid01-...`).

*Nota alternativa (opzionale): Se hai già installato la CLI Claude Code tramite Node.js, il widget rileverà automaticamente il tuo token OAuth presente in `~/.claude/.credentials.json`.*

### Passo 3 — Avvia e configura il widget
1. Fai doppio clic su **`avvia_widget.bat`** (oppure avvialo da terminale con `python claude_usage.py`).
2. Se è il primo avvio, si aprirà automaticamente la finestra delle impostazioni. Altrimenti, puoi aprirla cliccando sull'icona dell'ingranaggio **⚙** in alto a destra nel widget.
3. Incolla il valore della `sessionKey` copiato al Passo 2 nel campo dedicato.
4. Clicca su **Salva e aggiorna**.

---

## Come si usa

| Azione | Effetto |
|--------|---------|
| **Trascina** il widget | Lo sposti dove vuoi sullo schermo |
| **Tasto destro** | Menu contestuale: Aggiorna / Impostazioni / Chiudi |
| **⚙** (in alto a destra) | Apre la finestra delle impostazioni / inserimento chiave |

Il widget si aggiorna automaticamente ogni 5 minuti.

---

## Posizionamento consigliato

Trascina il widget nell'angolo in basso a sinistra della finestra di Claude Desktop, sotto la lista delle conversazioni — si integra perfettamente nell'interfaccia.

---

## Colori delle barre

| Colore | Significato |
|--------|-------------|
| 🟢 Verde | Meno del 65% di utilizzo |
| 🟡 Giallo | Tra il 65% e l'85% di utilizzo |
| 🔴 Rosso | Oltre l'85% di utilizzo |

---

## Sessione o Chiave Scaduta?

La `sessionKey` può scadere se effettui il logout dal browser o dopo un certo periodo di inattività. Se il widget mostra un pallino rosso o un errore:
1. Accedi a [claude.ai](https://claude.ai) nel tuo browser.
2. Copia la nuova `sessionKey` tramite F12.
3. Apri le impostazioni del widget (click destro -> *Impostazioni* oppure icona **⚙**), incolla la nuova chiave e clicca su **Salva e aggiorna**.

---

## Privacy

- Il widget comunica **solo** con i server ufficiali di Anthropic (`api.anthropic.com` e `claude.ai`).
- Le credenziali e la `sessionKey` sono salvate localmente sul tuo PC nel file di configurazione `~/.claude_usage_widget.json` (nella cartella del tuo profilo utente) e non vengono mai condivise o inviate altrove.
- Nessuna telemetria, nessun sistema di tracciamento.

---

## Avvio automatico con Windows

Per fare in modo che il widget si avvii da solo all'accensione del PC:
1. Premi **Win + R** sulla tastiera, digita `shell:startup` e premi Invio.
2. Crea e incolla nella cartella che si apre un collegamento al file `avvia_widget.bat`.
