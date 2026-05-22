import os
import sys
import json
import subprocess
import time
import google.generativeai as genai
from pydantic import BaseModel, Field
from typing import List

# =====================================================================
# 🛠️ CONFIGURAZIONE PERCORSI E AMBIENTE
# =====================================================================
CLIENTI_FILE_PATH = os.path.join(os.path.dirname(__file__), "clients.json")
FOOTAGE_DIR = "/app/footage"
OUTPUT_DIR = "/app/capcut_output"

# Inizializzazione delle API Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# =====================================================================
# 📐 SCHEMI PYDANTIC
# =====================================================================
class TaglioVideo(BaseModel):
    start_ms: int = Field(description="Timestamp iniziale del blocco utile (in millisecondi)")
    end_ms: int = Field(description="Timestamp finale del blocco utile (in millisecondi)")
    tipo_scena: str = Field(description="Tipologia di scena: 'hook', 'body', 'call_to_action'")
    testo_sottotitolo: str = Field(description="L'ESATTA trascrizione letterale, parola per parola, senza alcuna modifica o riscrittura, del parlato in questo blocco")

class AutomazioneVideoSchema(BaseModel):
    tagli_video: List[TaglioVideo] = Field(description="Lista sequenziale ordinata cronologicamente dei tagli per la timeline, escludendo errori e silenzi")
    timestamp_frame_copertina_ms: int = Field(description="Il millisecondo esatto ideale da cui estrarre il frame per la copertina")
    titolo_copertina_alto: str = Field(description="Titolo sintetico (max 4-5 parole) in MAIUSCOLO per la parte alta della copertina")
    stile_musica_consigliato: str = Field(description="Indicazione sul tipo di traccia audio di sottofondo (es. 'pop_trend', 'jazz_lofi')")

# =====================================================================
# 🎛️ ESTRAZIONE AUDIO TRAMITE FFMPEG
# =====================================================================
def estrai_audio_da_video(video_filename: str) -> str:
    """Estrae la traccia audio dal video e la salva nella cartella /tmp interna del container"""
    video_path = os.path.join(FOOTAGE_DIR, video_filename)
    
    # Spostiamo il file temporaneo in /tmp (zona sicura di Linux, libera da vincoli del Mac)
    audio_path = "/tmp/temp_audio.mp3"
    
    # Rimuove il vecchio file audio temporaneo se esiste
    if os.path.exists(audio_path):
        os.remove(audio_path)
        
    print(f"\n🎵 [FFmpeg] Estrazione traccia audio da {video_filename} in corso...")
    
    # Comando FFmpeg con filtri di compatibilità universale (-ar e -ac)
    comando = [
        "ffmpeg", "-i", video_path,
        "-vn",                      # Disattiva lo stream video
        "-acodec", "libmp3lame",    # Forza il codec MP3 standard
        "-ar", "44100",             # Forza il campionamento standard a 44.1kHz
        "-ac", "2",                 # Forza l'audio in Stereo (2 canali) per evitare crash su microfoni mono/multi-traccia
        "-q:a", "4",                # Qualità ottimale e file leggero
        audio_path,
        "-y"                        # Sovrascrivi senza chiedere
    ]
    
    try:
        # Eseguiamo catturando i log di errore reali per il debug se qualcosa va storto
        risultato = subprocess.run(comando, capture_output=True, text=True, check=True)
        print("✅ [FFmpeg] Traccia audio estratta con successo in /tmp!")
        return audio_path
    except subprocess.CalledProcessError as e:
        print(f"❌ [FFmpeg ERRORE] Errore di esecuzione.")
        print(f"Log dettagliato di FFmpeg:\n{e.stderr}")
        sys.exit(1)

# =====================================================================
# 🧠 CORE PIPELINE MULTIMODALE GEMINI
# =====================================================================
def elabora_video_con_audio_reale(cliente: dict, audio_path: str) -> dict:
    """Carica l'audio reale su Gemini e richiede l'analisi dei tagli strutturata."""
    
    # 1. Caricamento del file audio sui server temporanei di Google tramite File API
    print("📤 [API] Caricamento del file audio sui server di Google Cloud per l'analisi neurale...")
    audio_file_uploaded = genai.upload_file(path=audio_path)
    
    # Aspetta che il file sia elaborato (stato ACTIVE)
    while audio_file_uploaded.state.name == "PROCESSING":
        print("⏳ Attendendo l'indicizzazione dell'audio sui server Google...")
        time.sleep(2)
        audio_file_uploaded = genai.get_file(audio_file_uploaded.name)
        
    if audio_file_uploaded.state.name == "FAILED":
        print("❌ [ERRORE] Elaborazione del file audio fallita sui server Google.")
        return {}
        
    print("✅ [API] File audio pronto ed indicizzato.")

    # 2. Definizione del System Prompt Blindato
    system_instruction_text = f"""
    Sei un assistente esperto montatore video cinematografico e analista audio per social media.
    Ti viene fornito in input un file audio reale estratto da una ripresa video del cliente "{cliente['nome']}".
    Il tuo compito è ascoltare l'audio, mappare tutti i timestamp temporali (in millisecondi) del parlato ed emettere lo schema JSON per il montaggio.
    
    Linee guida fondamentali per il testo:
    - Ascolta accuratamente le parole pronunciate: il campo 'testo_sottotitolo' deve contenere l'ESATTA trascrizione letterale (parola per parola, 100% fedele) del parlato originale.
    - NON riassumere, NON eliminare le ripetizioni se decidi di includere quella clip, copia il testo parlato esattamente come viene pronunciato.
    
    Strategia di taglio (Timeline):
    1. Isola i millisecondi di inizio ('start_ms') e fine ('end_ms') di ogni frase parlata.
    2. Taglia fuori i silenzi morti, i rumori di fondo, i sospiri e i blocchi in cui chi parla fa errori evidenti o si ferma dicendo "rifaccio", "aspetta", "prova microfono".
    3. Organizza i tagli utili in senso logico (Hook -> Body -> Call to Action).
    4. Sulla base del settore del brand ({cliente['settore']}), individua il millisecondo esatto per la copertina e genera un titolo in MAIUSCOLO d'impatto.
    """
    
    # 3. Inizializzazione del modello di ultima generazione
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        system_instruction=system_instruction_text
    )
    
    # 4. Prompt utente che collega l'oggetto del file audio caricato
    prompt_utente = [
        audio_file_uploaded,
        "\nAnalizza questo file audio reale. Genera la timeline dei tagli video in formato JSON rispettando lo schema Pydantic fornito."
    ]
    
    print(f"\n🧠 [AI] Gemini sta ascoltando l'audio reale per il brand {cliente['nome']}...")
    
    try:
        response = model.generate_content(
            prompt_utente,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=AutomazioneVideoSchema,
                temperature=0.0 # Determinismo matematico assoluto
            )
        )
        
        # Pulizia: eliminiamo il file dai server Google dopo l'uso
        genai.delete_file(audio_file_uploaded.name)
        
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ [ERRORE API] Impossibile completare la richiesta o decodificare il JSON: {e}")
        return {}

# =====================================================================
# 📦 FUNZIONI DI SERVIZIO STANDARD
# =====================================================================
def carica_database_clienti():
    if not os.path.exists(CLIENTI_FILE_PATH):
        print(f"❌ [ERRORE] File {CLIENTI_FILE_PATH} mancante.")
        sys.exit(1)
    with open(CLIENTI_FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def scansiona_video_disponibili():
    estensioni_valide = ('.mp4', '.mov', '.m4v')
    if not os.path.exists(FOOTAGE_DIR):
        return []
    return [f for f in os.listdir(FOOTAGE_DIR) if f.lower().endswith(estensioni_valide) and not f.startswith("temp_")]

def seleziona_cliente(clienti):
    while True:
        print("\n" + "="*50)
        print("   AGENZIA AI (CONTENT OPS) - SELEZIONE CLIENTE")
        print("="*50)
        for c in clienti:
            print(f" [{c['id']}] {c['nome']} ({c['settore']})")
        print(" [0] Esci dal programma")
        print("="*50)
        scelta = input("Seleziona il numero del cliente: ").strip()
        if scelta == "0": sys.exit(0)
        cliente_selezionato = next((c for c in clienti if c["id"] == scelta), None)
        if cliente_selezionato: return cliente_selezionato
        print("❌ Scelta non valida.")

def seleziona_video(video_list):
    while True:
        print("\n" + "="*50)
        print("   SELEZIONE FILE VIDEO REALE (RAW FOOTAGE)")
        print("="*50)
        for i, video in enumerate(video_list, start=1):
            print(f" [{i}] {video}")
        print(" [0] Esci")
        print("="*50)
        scelta = input("Seleziona il numero del video da elaborare: ").strip()
        if scelta == "0": sys.exit(0)
        try:
            indice = int(scelta) - 1
            if 0 <= indice < len(video_list): return video_list[indice]
        except ValueError: pass
        print("❌ Selezione non valida.")

# =====================================================================
# 🚀 CORE EXECUTION
# =====================================================================
def main():
    print("==================================================")
    print("⚡ AVVIO PIPELINE AUDIO REALE: MULTIMODAL AI ⚡")
    print("==================================================")
    
    database_clienti = carica_database_clienti()
    cliente = seleziona_cliente(database_clienti)
    
    video_disponibili = scansiona_video_disponibili()
    if not video_disponibili:
        print(f"\n⚠️ Sposta il tuo video reale (es. IMG_7663.MOV) nella cartella 'data/' del tuo Mac e riavvia.")
        sys.exit(0)
        
    video_scelto = seleziona_video(video_disponibili)
    
    print(f"\n🎬 File in elaborazione: {video_scelto}")
    
    # 1. Chiamiamo FFmpeg per estrarre l'audio reale
    percorso_audio_estratto = estrai_audio_da_video(video_scelto)
    
    # 2. Passiamo l'audio reale a Gemini per ascolto e generazione timeline
    risultato_automazione = elabora_video_con_audio_reale(cliente, percorso_audio_estratto)
    
    # Pulizia locale del file audio temporaneo per non sprecare spazio sul Mac
    if os.path.exists(percorso_audio_estratto):
        os.remove(percorso_audio_estratto)
        
    if not risultato_automazione:
        print("❌ Pipeline fallita.")
        sys.exit(1)
        
    # 3. Scrittura del file JSON finale
    folder_progetto_nome = f"{cliente['nome'].lower().replace(' ', '_')}_progetto_reale"
    percorso_salvataggio_host = os.path.join(OUTPUT_DIR, folder_progetto_nome)
    os.makedirs(percorso_salvataggio_host, exist_ok=True)
    
    file_metadati_finale = os.path.join(percorso_salvataggio_host, "istruzioni_montaggio_capcut.json")
    with open(file_metadati_finale, "w", encoding="utf-8") as f:
        json.dump(risultato_automazione, f, indent=4, ensure_ascii=False)
        
    print("\n" + "="*50)
    print("🎉 PIPELINE COMPLETATA SU AUDIO REALE!")
    print("="*50)
    print(f"📍 Cliente: {cliente['nome']}")
    print(f"📁 JSON reale generato: {file_metadati_finale}")
    print(f"🎬 Numero clip identificate ed estratte: {len(risultato_automazione.get('tagli_video', []))}")
    print(f"📸 Frame copertina: {risultato_automazione.get('timestamp_frame_copertina_ms')} ms")
    print("="*50)

if __name__ == "__main__":
    main()