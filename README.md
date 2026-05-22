# Spiegazione Strategica del Workflow Attuale

L'architettura attuale dell'agente è stata ingegnerizzata per massimizzare l'affidabilità e la precisione del taglio, separando nettamente i compiti tra l'Intelligenza Artificiale e l'applicazione host (CapCut):

1. **Il Cervello (Gemini + FFmpeg):** Isola la traccia audio reale, esegue una mappatura temporale multimodale e produce un file di istruzioni matematiche (`istruzioni_montaggio_capcut.json`). Questo file contiene la verità semantica del video (testo esatto, posizionamento delle pause ed errori).
2. **Il Braccio (Python Compiler):** Traduce i millisecondi estratti dall'AI in microsecondi compatibili con lo standard di CapCut Desktop per Mac, strutturando una timeline logica stabile.
3. **La Finitura (CapCut Host):** Delegando la gestione della traccia testo e la formattazione dei sottotitoli nativi alle funzioni interne di CapCut (*Auto Captions*), eliminiamo i rischi di crash dell'applicazione dovuti ai rigidi controlli di convalida dei metadati proprietari del software.

---

# 🎬 README.md (CapCut Automation Agent)

Pipeline intelligente basata su Docker e Gemini Multimodale per l'analisi dei video, l'estrazione chirurgica del parlato, la rimozione automatica dei tempi morti (silenzi/errori) e la generazione della struttura di montaggio.

## 📂 Struttura del Progetto

```text
CapCut_Automation/
├── docker-compose.yaml
├── Dockerfile
├── requirements.txt
├── README.md                  <-- Questo file
├── data/
│   └── [Video Master].MOV     <-- Inserisci qui i video da elaborare (es. IMG_7663.MOV)
├── output_drafts/
│   └── [nome_cliente]/        <-- Cartella generata automaticamente dall'AI
│       ├── istruzioni_montaggio_capcut.json
│       └── draft_info_INIETTATO.json
└── src/
    ├── main.py                <-- Core pipeline (FFmpeg + Gemini Audio Analysis)
    └── applica_montaggio.py   <-- Iniettore/Compilatore logico della timeline

```

---

## 🚀 Flusso di Lavoro Attuale

### 1. Preparazione

Inserisci il file video originale (es. `IMG_7663.MOV`) all'interno della cartella `data/` sul tuo Mac.

### 2. Fase Analisi (Ascolto AI e Taglio Silenzi)

Esegui l'agente per avviare l'estrazione della traccia audio tramite FFmpeg e l'analisi multimodale di Gemini. L'AI taglierà chirurgicamente i silenzi, gli errori e organizzerà il flusso in blocchi (*Hook, Body, CTA*).

```bash
docker compose run --rm capcut_agent

```

* **Cosa succede:** Al termine dell'elaborazione, l'AI creerà una cartella dentro `output_drafts/` contenente il file `istruzioni_montaggio_capcut.json` con la trascrizione e i timestamp esatti al millisecondo.

### 3. Compilazione della Timeline Logica

Per tradurre le istruzioni dell'AI in una struttura leggibile e calcolare le metriche di montaggio sul video reale, esegui il compilatore Python:

```bash
docker compose run --rm capcut_agent python src/applica_montaggio.py

```

* **Cosa succede:** Viene generato il file `draft_info_INIETTATO.json` pronto per l'ispezione della timeline.

---

## 🛠️ Comandi Utili per la Manutenzione e il Debug

Se modifichi la struttura del container o i pacchetti Linux, usa questo comando per forzare Docker a ricostruire l'ambiente ignorando la cache di macOS:

```bash
docker compose build --no-cache

```

Per verificare in tempo reale i file visti dal container all'interno della sandbox Linux:

```bash
docker compose run --rm capcut_agent ls -l /app/src

```

---

## 📝 Note Tecniche Importanti

* **Isolamento di Scrittura:** FFmpeg esegue l'estrazione della traccia MP3 direttamente nella cartella protetta `/tmp` interna di Linux per aggirare i blocchi dei permessi di scrittura di macOS.
* **Parametri Audio Universali:** L'audio viene convertito forzatamente a `44100Hz`, `Stereo (2 canali)` e codec `libmp3lame` per garantire la massima compatibilità di lettura frequenze con i modelli AI.