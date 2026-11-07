# Discord Music Bot

Bot Discord in Python con i comandi slash `/play`, `/skip`, `/pause`, `/resume` e `/stop`.

## Requisiti

- Python 3.11 o 3.12 consigliato
- FFmpeg installato e disponibile nel PATH
- Applicazione e bot creati nel [Discord Developer Portal](https://discord.com/developers/applications)

## Installazione su Windows

Apri PowerShell nella cartella del progetto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Apri `.env` e inserisci il token del bot:

```env
DISCORD_TOKEN=IL_TUO_TOKEN
```

Non condividere mai il token e non caricare `.env` su GitHub.

## Installare FFmpeg

Installa FFmpeg per Windows e aggiungi la cartella `bin` al PATH di Windows. Chiudi e riapri PowerShell, poi verifica:

```powershell
ffmpeg -version
```

## Configurare Discord

Nel Developer Portal:

1. Crea una nuova Application e apri la sezione **Bot**.
2. Crea il bot e copia il token. Se necessario, rigeneralo.
3. In **Installation** (o OAuth2 URL Generator), seleziona gli scope `bot` e `applications.commands`.
4. Concedi i permessi **View Channels**, **Send Messages**, **Connect** e **Speak**.
5. Apri il link generato e aggiungi il bot al tuo server.

Non serve attivare Message Content Intent: il bot usa comandi slash.

## Avvio

Dalla cartella del progetto, con l'ambiente virtuale attivo:

```powershell
python bot.py
```

Quando appare il messaggio di connessione, prova `/play` in un canale testuale del server. Devi essere già collegato a un canale vocale.

## Comandi

- `/play query` — link YouTube o titolo da cercare
- `/skip` — salta il brano corrente
- `/pause` — mette in pausa
- `/resume` — riprende
- `/stop` — svuota la coda e disconnette il bot

La coda è separata per server. Se resta inattivo per 3 minuti, il bot si disconnette automaticamente.

## Note

Il PC o server che esegue `bot.py` deve rimanere acceso e connesso a Internet. Chiudere PowerShell o arrestare il processo spegne il bot. L'estrazione da YouTube può smettere di funzionare se YouTube cambia il proprio sistema: in quel caso aggiorna yt-dlp con `pip install -U yt-dlp`.

Usa il bot solo con contenuti che hai il diritto di riprodurre e nel rispetto dei termini delle piattaforme coinvolte.
