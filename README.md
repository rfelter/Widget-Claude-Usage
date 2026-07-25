# ⬡ Claude Usage Widget — Windows

> Documentazione relativa alla **versione 1.3** del widget.

Widget flottante always-on-top che mostra in tempo reale:

- **Contesto** — solo se in uso claude code (aggiornato ogni minuto)
- **Sessione 5h** — % usata + countdown al reset (aggiornato ogni 5 minuti)
- **Settimana** — % usata + countdown al reset  (aggiornato ogni 5 minuti)
- **Crediti** — crediti di utilizzo extra: % usata + valore usato/tetto in valuta (solo se attivi sul piano)

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
| **⧉** (in alto a destra) | Riduce il widget alla **barra compatta** |
| **⛶** (nella barra compatta) | Riespande il widget alla vista completa |

Il widget si aggiorna automaticamente con tempistiche diverse a seconda della barra.

### Modalità compatta

Cliccando l'icona **⧉** il widget si riduce a una barra verticale stretta che mostra
**solo le percentuali**, colorate secondo le stesse soglie (verde/giallo/rosso). Le voci
restano nello stesso ordine verticale della vista completa, così sono riconoscibili anche
senza etichetta; passando il mouse su una percentuale compare un **tooltip** con la
descrizione (Contesto / Sessione 5h / Settimana / Sonnet). Il bordo destro resta ancorato,
quindi il widget non si sposta orizzontalmente durante la riduzione.

L'icona **⛶** nella barra compatta riporta alla vista completa. Lo **stato scelto
(compatto o esteso) viene ricordato** e ripristinato al successivo avvio.

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
- ⚠ **I token sono salvati in chiaro** in quel file, protetto solo dai permessi del tuo profilo utente Windows: non sincronizzarlo su cloud o backup condivisi e non condividerlo. La `sessionKey` equivale alla tua sessione claude.ai completa.
- Eventuali errori vengono registrati in `~/.claude_usage_widget.log` (solo messaggi tecnici, mai token).
- Nessuna telemetria, nessun sistema di tracciamento.

---

## Avvio senza finestra e avvio automatico con Windows

Il file `.bat` apre per sua natura una finestra di console (visibile per un istante) —
è un limite del formato, non un bug. Per un avvio a **zero finestre**:

1. Tasto destro su **`crea_collegamento_silenzioso.ps1`** → **Esegui con PowerShell**
   (una tantum). Genera nella stessa cartella il file
   **"Avvia Widget (silenzioso).lnk"**, puntato direttamente a `pythonw.exe`.
2. Usa quel collegamento per l'avvio quotidiano (doppio clic, o copialo sul Desktop).
3. Per l'avvio automatico all'accensione: premi **Win + R**, digita `shell:startup`,
   premi Invio, e copia lì lo stesso collegamento.

> **Perché uno script generatore e non un `.vbs` pronto?** L'associazione file `.vbs`
> non è affidabile su tutte le installazioni Windows (Microsoft sta deprecando
> VBScript; su alcuni PC il doppio clic su `.vbs` non apre nulla). Un collegamento
> `.lnk` puntato a `pythonw.exe` evita del tutto il problema — Explorer lo esegue
> nativamente. Lo script genera il collegamento con il percorso Python corretto per
> **il tuo PC**, quindi va eseguito una volta su ogni macchina in cui installi il widget.
>
> Il `.bat` resta comunque utile per il primo avvio: mostra messaggi diagnostici
> (es. Python non installato).
