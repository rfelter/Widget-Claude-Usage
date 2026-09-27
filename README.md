# ⬡ Claude Usage Widget — Windows

> Documentazione relativa alla **versione 1.6** del widget.

Widget flottante always-on-top che mostra in tempo reale:

- **Contesto** — solo se in uso claude code (aggiornato ogni minuto): token usati sulla finestra del modello in uso (1M per la generazione corrente, 200K per Haiku 4.5 e la famiglia 3.x)
- **Sessione 5h** — % usata + countdown al reset (aggiornato ogni 5 minuti)
- **Settimana** — % usata + countdown al reset  (aggiornato ogni 5 minuti)
- **Sonnet** — quota settimanale dedicata a Sonnet (solo se il piano la prevede)
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
5. Cerca la riga con nome **`sessionKey`** e copia il suo valore (è una stringa che inizia con `sk-ant-sid...`).

   > Il prefisso è cambiato nel tempo: le chiavi erano `sk-ant-sid01-...`, oggi sono `sk-ant-sid02-...`.
   > Conta il nome del cookie (`sessionKey`), non il numero nel prefisso.

> **Nota sul Metodo B (OAuth).** Il widget cerca un token OAuth in `~/.claude/.credentials.json`,
> il file che la CLI Claude Code usava per le credenziali. **Sulle installazioni aggiornate di
> Claude Code quel file non viene più mantenuto**, quindi il rilevamento automatico in genere non
> scatta: la via affidabile è la `sessionKey` del Passo 2. Se vuoi comunque un secondo canale,
> `claude setup-token` genera un token a vita lunga da incollare a mano nel campo OAuth.

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
| **!** rosso (in alto) | Compare quando esiste una versione più recente: clic per aprire la pagina dei rilasci |

Il widget si aggiorna automaticamente con tempistiche diverse a seconda della barra.

### Modalità compatta

Cliccando l'icona **⧉** il widget si riduce a una barra verticale stretta che mostra
**solo le percentuali**, colorate secondo le stesse soglie (verde/giallo/rosso). Le voci
restano nello stesso ordine verticale della vista completa, così sono riconoscibili anche
senza etichetta; passando il mouse su una percentuale compare un **tooltip** con la
descrizione (Contesto / Sessione 5h / Settimana / Sonnet / Crediti). Il bordo destro resta ancorato,
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

### Colori della riga sotto la barra

La riga piccola sotto ogni barra (`Reset tra…`, token usati, crediti) resta in
**grigio neutro finché l'utilizzo è sotto il 65%**: sotto quella soglia non c'è
niente da segnalare. Superata la soglia si accende, con due logiche diverse:

| Riga | Da 65% in su |
|------|--------------|
| **Reset tra…** (Sessione, Settimana, Sonnet) | 🟡 finché c'è da resistere · 🟢 quando il reset è vicino: entro **1 ora** per la Sessione 5h, entro **24 ore** per Settimana e Sonnet |
| **Contesto** e **Crediti** | stesso colore della barra (🟡 → 🔴) |

Il **rosso non compare mai sul countdown di reset**: è riservato al consumo
(barra e percentuale). Il tempo che manca al reset non è di per sé una cattiva
notizia — una finestra appena azzerata è lo stato più sano possibile ed è anche
il più lontano dal reset — quindi colorarlo di rosso darebbe due segnali opposti
sulla stessa riga.

---

## Sessione o Chiave Scaduta?

La `sessionKey` può scadere se effettui il logout dal browser o dopo un certo periodo di inattività. Se il widget mostra un pallino rosso o un errore:
1. Accedi a [claude.ai](https://claude.ai) nel tuo browser.
2. Copia la nuova `sessionKey` tramite F12.
3. Apri le impostazioni del widget (click destro -> *Impostazioni* oppure icona **⚙**), incolla la nuova chiave e clicca su **Salva e aggiorna**.

> ⚠ **Non incollare la `sessionKey` anche nel campo OAuth.** Sono due credenziali
> diverse: il campo OAuth vuole un token `sk-ant-oat01-...`. Se ci finisce la
> sessionKey, il widget tenta a ogni aggiornamento una chiamata destinata a
> fallire prima di ripiegare sul metodo corretto — e impedisce il rilevamento
> automatico del token di Claude Code. Lascialo vuoto se non usi il metodo B.
> Per rimuoverne una già salvata basta **svuotare il campo e salvare** (dalla v1.5:
> nelle versioni precedenti un campo lasciato vuoto veniva ignorato e il valore
> vecchio restava nel file di configurazione).

> **Più organizzazioni sullo stesso account?** Dalla v1.5 il widget sceglie da sé
> quella con abbonamento chat (Pro/Max/Team): le organizzazioni di solo API non
> espongono i dati di utilizzo e venivano scelte per errore se comparivano per
> prime nella risposta.

---

## Avviso di nuova versione

Quando esiste una release più recente di quella installata, nell'angolo in alto del widget
compare un **`!` rosso**: un clic apre la pagina dei rilasci su GitHub. L'avviso compare anche
nella barra compatta, e il passaggio del mouse mostra quale versione è disponibile.

Come funziona, in concreto:

- il controllo avviene **una volta al giorno**, in background, leggendo il numero dell'ultima
  release pubblicata su GitHub. L'esito viene memorizzato, quindi riavviare il widget non
  ripete la chiamata;
- se la rete non c'è o GitHub non risponde, **non accade nulla**: nessun errore a schermo,
  nessuna riga di log, nessun effetto sulle barre dell'utilizzo. Si riprova al prossimo avvio;
- si disattiva togliendo la spunta a **«Avvisami se esce una nuova versione»** nelle
  impostazioni. Disattivandolo il widget scorda anche l'ultimo esito, quindi il `!` sparisce.

> ⚠ **L'avviso funziona solo dalla versione 1.6 in poi.** Chi usa una versione precedente non
> può riceverlo: quel codice non contiene il controllo. Per essere avvisato senza aggiornare,
> l'alternativa è **Watch → Custom → Releases** sulla pagina del repository, che manda una
> notifica a ogni rilascio.

---

## Privacy

- Il widget comunica con i server ufficiali di Anthropic (`api.anthropic.com` e `claude.ai`) per i dati di utilizzo, e — **se il controllo aggiornamenti è attivo** — con `api.github.com` una volta al giorno per leggere il numero dell'ultima versione pubblicata. Nessun altro destinatario.
- Nella chiamata a GitHub **non viene inviata nessuna credenziale**: è una richiesta pubblica e anonima, in cui GitHub vede solo il tuo indirizzo IP e la stringa `claude-usage-widget/<versione>`. Si disattiva dalla casella nelle impostazioni.
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
