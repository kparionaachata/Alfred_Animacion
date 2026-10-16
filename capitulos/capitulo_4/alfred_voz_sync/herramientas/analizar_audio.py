r"""Herramienta de analisis de voz para Alfred Voz Sync (usa la app `estudio_audio_expresion` SIN modificarla).

Para un audio (mp3/wav...) hace lo mismo que la app: normaliza con FFmpeg, mide la prosodia (librosa), transcribe con Whisper Base local (RTX 3050) -con el tiempo de cada palabra- y combina
palabras + tono + los ejemplos que el usuario aprobo (`estudio_audio_expresion/aprendizaje/aprobaciones.jsonl`, solo se LEE) para estimar la emocion. Ademas construye la geometria de los ojos de
Alfred (mezcla de las expresiones aprobadas de `estudio_animacion/catalogo_ojos/alfred`, como el generador procedural de la app). Escribe junto al audio:
  <audio>.emocion.json : texto, emocion (NEUTRO, ENOJO, ALEGRIA, TRISTEZA, SUENO, MIEDO, SORPRESA, DUDA), intensidad, confianza, puntajes, palabras [{t0, t1, w}] -> lo lee Alfred Voz Sync.
  <audio>.cara.json    : (solo si la emocion no es neutral) parametros y coordenadas de los ojos de Alfred -> Alfred Voz Sync crea la animacion facial como capa aditiva.
Uso (con el Python del entorno de la app, que tiene librosa/torch/transformers):
  ..\..\..\..\voz_a_voz\Applio\env\Scripts\python.exe analizar_audio.py "C:\...\audios\alfred\fdfdfdfff.mp3" [--emocion duda] [--texto "..."]
`--emocion` / `--texto` fuerzan la emocion o corrigen la transcripcion (como la correccion manual de la app).
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ESTUDIO = Path(r"C:\Users\user\Desktop\Alfred_Animacion\estudio_audio_expresion")
CATALOGO = Path(r"C:\Users\user\Desktop\Alfred_Animacion\estudio_animacion\catalogo_ojos\alfred")
FFMPEG = Path(r"C:\ffmpeg\bin\ffmpeg.exe")
MAPA = {"alegria": "ALEGRIA", "tristeza": "TRISTEZA", "enojo": "ENOJO", "sorpresa": "SORPRESA", "cansancio": "SUENO", "duda": "DUDA", "neutral": "NEUTRO", "miedo": "MIEDO"}
INVERSO = {v: k for k, v in MAPA.items()}
FASES = [(0.00, 0.00), (0.12, 0.00), (0.28, 0.70), (0.42, 1.08), (0.57, 0.92), (0.72, 1.02), (0.86, 0.48), (1.00, 0.00)]      # mismas fases que generador_procedural.py


def palabras_whisper(wav, motor):
    """[(t0, t1, palabra)] con Whisper Base local; si el modelo no da tiempos por palabra, reparte cada segmento entre sus palabras."""
    pipe = motor._load_pipeline()
    r = pipe(str(wav), generate_kwargs={"language": "spanish", "task": "transcribe"}, return_timestamps="word")
    out = []
    for c in r.get("chunks") or []:
        t = c.get("timestamp") or (None, None)
        if t[0] is None: continue
        t1 = t[1] if t[1] is not None else t[0] + 0.3
        w = (c.get("text") or "").strip()
        if w: out.append((float(t[0]), float(t1), w))
    return (r.get("text") or "").strip(), out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("audio"); ap.add_argument("--emocion", default=""); ap.add_argument("--texto", default=""); ap.add_argument("--sin-cara", action="store_true")
    a = ap.parse_args(); audio = Path(a.audio)
    if not audio.is_file(): sys.exit(f"No existe {audio}")
    sys.path.insert(0, str(ESTUDIO))
    import analizador_emocion as ae
    import generador_procedural as gp
    import transcribir_audio as ta
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        r = subprocess.run([str(FFMPEG), "-hide_banner", "-loglevel", "error", "-y", "-i", str(audio), "-vn", "-ac", "1", "-ar", "22050", "-c:a", "pcm_s16le", str(wav)])
        if r.returncode or not wav.exists(): sys.exit("FFmpeg no pudo leer el audio")
        feats = ae.extract_features(wav)
        texto, palabras = palabras_whisper(wav, ta)
    if a.texto: texto = a.texto; palabras = [] if a.texto != texto else palabras
    pred = ae.classify_multimodal(feats, texto, ESTUDIO / "aprendizaje" / "aprobaciones.jsonl")
    emo = a.emocion.lower() if a.emocion else pred["emotion"]
    if emo.upper() in MAPA.values(): emo = INVERSO[emo.upper()]
    conf = 1.0 if a.emocion else float(pred["confidence"])
    intensidad = round(min(1.3, 0.6 + 0.7 * conf), 3)
    meta = {"fuente": "estudio_audio_expresion (Whisper base + prosodia + ejemplos aprobados) via Alfred Voz Sync/herramientas/analizar_audio.py", "texto": texto, "emocion": MAPA.get(emo, "NEUTRO"),
            "intensidad": intensidad, "confianza": round(conf, 3), "forzada": bool(a.emocion), "puntajes": {MAPA.get(k, k): round(v, 3) for k, v in pred["scores"].items()},
            "puntajes_acusticos": {MAPA.get(k, k): round(v, 3) for k, v in pred["acoustic_scores"].items()}, "puntajes_palabras": {MAPA.get(k, k): round(v, 3) for k, v in pred["semantic_scores"].items()},
            "peso_ejemplos_aprobados": round(pred["example_memory_weight"], 3), "ejemplos_mas_parecidos": pred["closest_approved_examples"],
            "duracion_s": round(feats["duration"], 3), "rasgos": {k: round(v, 3) for k, v in feats["normalized"].items()},
            "palabras": [{"t0": round(t0, 3), "t1": round(t1, 3), "w": w} for t0, t1, w in palabras]}
    base = audio.with_suffix("")
    ruta_emo = Path(str(base) + ".emocion.json"); ruta_emo.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"emocion: {meta['emocion']} (confianza {conf:.2f}, intensidad {intensidad}) | texto: {texto!r} | {len(palabras)} palabras con tiempo | {ruta_emo}")
    es_jerry = "jerry" in [p_.lower() for p_ in audio.parts]                          # para Jerry la cara viene del animacion_jerry.py de la app (importar_script_jerry.py), no de la geometria de Alfred
    if emo != "neutral" and not a.sin_cara and not es_jerry:
        coords, comps = gp._blend(CATALOGO, emo, feats)
        n = feats["normalized"]; confi = conf
        intensity = min(1.0, 0.42 + n["energia"] * 0.24 + n["dinamica"] * 0.18 + confi * 0.22)
        par = {"shape_value": 0.040 + 0.035 * intensity, "scale_x": 1.06 + 0.18 * intensity, "scale_z": 1.08 + 0.25 * intensity, "vertical": 0.0006 + 0.0022 * n["variacion_tono"],
               "rotation": 0.018 + 0.055 * n["variacion_tono"], "lateral": 0.00025 + 0.0010 * n["dinamica"]}
        cara = {"emocion": MAPA.get(emo, "NEUTRO"), "componentes": comps, "intensidad": round(intensity, 3), "parametros": par, "fases": FASES, "duracion_s": round(feats["duration"], 3), "coordenadas": coords}
        ruta_cara = Path(str(base) + ".cara.json"); ruta_cara.write_text(json.dumps(cara, ensure_ascii=False), encoding="utf-8")
        print(f"cara: {[(c['expression'], round(c['weight'], 2)) for c in comps]} intensidad {intensity:.2f} | {ruta_cara}")
    elif (a.sin_cara or emo == "neutral") and not es_jerry:
        for suf in (".cara.json",):
            p = Path(str(base) + suf)
            if p.exists(): p.unlink()


if __name__ == "__main__":
    main()
