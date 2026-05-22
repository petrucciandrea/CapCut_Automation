import os
import json
import sys
import uuid
import subprocess

PROGETTO_DIR = "/app/capcut_output/tavernetta_progetto_reale"
JSON_INPUT_AI = os.path.join(PROGETTO_DIR, "istruzioni_montaggio_capcut.json")
VIDEO_ORIGINALE_NOME = "IMG_7663.MOV"

def carica_json(percorso):
    if not os.path.exists(percorso):
        print(f"❌ [ERRORE] File missing: {percorso}")
        sys.exit(1)
    with open(percorso, "r", encoding="utf-8") as f:
        return json.load(f)

def genera_id_capcut():
    return str(uuid.uuid4()).upper()

def ottieni_metadati_video():
    """Usa ffprobe per estrarre dimensioni e durata reale del file video sorgente"""
    video_path = os.path.join("/app/footage", VIDEO_ORIGINALE_NOME)
    comando = [
        "ffprobe", "-v", "error", 
        "-select_streams", "v:0", 
        "-show_entries", "stream=width,height,duration", 
        "-of", "json", video_path
    ]
    try:
        risultato = subprocess.run(comando, capture_output=True, text=True, check=True)
        info = json.loads(risultato.stdout)
        stream = info["streams"][0]
        width = stream["width"]
        height = stream["height"]
        durata_sec = float(stream.get("duration", 0))
        return width, height, int(durata_sec * 1000000) # Convertito in microsecondi
    except Exception as e:
        print(f"⚠️ Errore lettura ffprobe ({e}). Uso fallback verticale standard.")
        return 1080, 1920, 100000000

def genera_progetto_nativo_zero_click():
    print("\n" + "="*50)
    print("🚀 GENERATORE PROGETTI CAPCUT NATIVO (ZERO-CLICK)")
    print("="*50)
    
    dati_ai = carica_json(JSON_INPUT_AI)
    tagli = dati_ai["tagli_video"]
    
    # 1. Analisi dinamica del video per evitare forzature di formato
    width, height, durata_totale_video_us = ottieni_metadati_video()
    ratio_string = "9:16" if width < height else "16:9"
    if width == height: ratio_string = "1:1"
    
    print(f"📊 Rilevato formato video: {width}x{height} ({ratio_string})")

    # 2. Generazione ID strutturali incrociati (Essenziali per CapCut)
    video_material_id = genera_id_capcut()
    local_material_id = genera_id_capcut()
    project_id = genera_id_capcut()
    
    percorso_video_mac = f"/Users/andreapetrucci/Documents/progetti_miei/CapCut_Automation/data/{VIDEO_ORIGINALE_NOME}"

    # 3. Costruzione del Database dei Materiali (Bypassa l'importazione manuale)
    materiale_video_strutturato = {
        "id": video_material_id,
        "type": "video",
        "local_material_id": local_material_id,
        "path": percorso_video_mac,
        "duration": durata_totale_video_us,
        "width": width,
        "height": height,
        "video_frame_rate": 24.0,
        "has_audio": True,
        "extra_info": ""
    }

    # 4. Generazione dei segmenti della Timeline
    traccia_video = {
        "id": genera_id_capcut(),
        "type": "video",
        "segments": []
    }
    
    timeline_cursor_us = 0

    for taglio in tagli:
        start_us = taglio["start_ms"] * 1000
        end_us = taglio["end_ms"] * 1000
        durata_us = end_us - start_us
        
        segmento = {
            "id": genera_id_capcut(),
            "material_id": video_material_id,
            "source_timerange": {"start": start_us, "duration": durata_us},
            "target_timerange": {"start": timeline_cursor_us, "duration": durata_us},
            "track_id": traccia_video["id"],
            "render_index": 0,
            "volume": 1.0
        }
        traccia_video["segments"].append(segmento)
        timeline_cursor_us += durata_us

    # 5. Compilazione del File di Progetto Schema-Compliant
    progetto_struttura_completa = {
        "id": project_id,
        "version": 360000,
        "new_version": "169.0.0",
        "name": f"Montaggio_AI_{VIDEO_ORIGINALE_NOME.split('.')[0]}",
        "duration": timeline_cursor_us,
        "fps": 24.0,
        "is_drop_frame_timecode": False,
        "color_space": -1,
        "config": {
            "video_mute": False,
            "subtitle_sync": True,
            "maintrack_adsorb": True,
            "material_save_mode": 0
        },
        "canvas_config": {
            "ratio": ratio_string,
            "width": width,
            "height": height,
            "background": None
        },
        "tracks": [traccia_video],
        "materials": {
            "videos": [materiale_video_strutturato],
            "flowers": [], "tail_leaders": [], "audios": [], "images": [], "texts": [],
            "effects": [], "stickers": [], "canvases": [], "transitions": [], "audio_effects": [],
            "audio_fades": [], "beats": [], "material_animations": [], "placeholders": [],
            "placeholder_infos": [], "speeds": [], "common_mask": [], "chromas": [],
            "text_templates": [], "realtime_denoises": [], "audio_pannings": [],
            "audio_pitch_shifts": [], "video_trackings": [], "hsl": [], "drafts": [],
            "color_curves": [], "hsl_curves": [], "primary_color_wheels": [],
            "log_color_wheels": [], "video_effects": [], "audio_balances": [],
            "handwrites": [], "manual_deformations": [], "manual_beautys": [],
            "plugin_effects": [], "sound_channel_mappings": [], "green_screens": [],
            "shapes": [], "material_colors": [], "digital_humans": [],
            "digital_human_model_dressing": [], "smart_crops": [], "ai_translates": [],
            "audio_track_indexes": [], "loudnesses": [], "vocal_beautifys": [],
            "vocal_separations": [], "smart_relights": [], "time_marks": [],
            "multi_language_refs": [], "video_shadows": [], "video_strokes": [], "video_radius": []
        },
        "keyframes": {"videos": [], "audios": [], "texts": [], "stickers": [], "filters": [], "adjusts": [], "handwrites": [], "effects": []},
        "platform": {"os": "mac", "app_id": 359289, "app_source": "cc"},
        "cover": {
            "snapshot_time": dati_ai["timestamp_frame_copertina_ms"] * 1000,
            "title": dati_ai["titolo_copertina_alto"]
        },
        "draft_type": "video"
    }

    # Salvataggio del file finale autonomo
    file_output_iniettato = os.path.join(PROGETTO_DIR, "draft_info_INIETTATO.json")
    with open(file_output_iniettato, "w", encoding="utf-8") as f:
        json.dump(progetto_struttura_completa, f, indent=4, ensure_ascii=False)
        
    print("\n✅ [PROGETTO AUTONOMO GENERATO]")
    print(f"📄 File pronto da inserire a freddo: {file_output_iniettato}")
    print(f"⏱️ Durata finale Reel: {timeline_cursor_us / 1000000:.2f} secondi.")
    print("="*50)

if __name__ == "__main__":
    genera_progetto_nativo_zero_click()