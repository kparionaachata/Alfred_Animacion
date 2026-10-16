r"""Convierte el `animacion_jerry.py` que genera la app de expresion facial (voz de Jerry) en datos para Alfred Voz Sync, SIN ejecutarlo (se lee con `ast`, asi no borra ni pisa nada en Blender).
El script de la app es DESTRUCTIVO (borra la animacion de los ojos, keyframea los huesos con valores absolutos en f1..END y cambia el rango de la escena); Alfred Voz Sync reproduce exactamente
la misma animacion (mandibula, hocico, cabeza, cejas, ojos, pupilas, parpadeo) como capas ADITIVAS desde el frame en que empieza el audio.
Escribe junto al audio:
  <audio>.cara.json    : {"tipo": "jerry", constantes del script (COMPONENTS, AMPLITUDE, PUPIL_SHIFT, EYE_SCALE, SPEECH_CURVE, BROW_*, phase_data, intensidades...), "parpadeos": [[frame, valor], ...]}
  <audio>.emocion.json : texto, emocion (DUDA, ENOJO...), intensidad (si ya existe se conserva el contexto que tenga, p. ej. palabras)
Uso:  python importar_script_jerry.py "C:\...\audios\jerry\dsdsdsdaa.wav" "C:\...\Downloads\animacion_jerry.py"
"""
import ast
import json
import sys
from pathlib import Path

MAPA = {"alegria": "ALEGRIA", "tristeza": "TRISTEZA", "enojo": "ENOJO", "sorpresa": "SORPRESA", "cansancio": "SUENO", "duda": "DUDA", "neutral": "NEUTRO", "miedo": "MIEDO"}
NOMBRES = ("GENERATED_EMOTION", "TRANSCRIPT", "COMPONENTS", "END_FRAME", "AMPLITUDE", "PUPIL_SHIFT", "EYE_SCALE", "SPEECH_CURVE", "BLINK_COUNT", "BROW_BASE", "BROW_POSE", "BROW_POSE_STRENGTH")


def curva_parpadeo(offset, dur):
    """misma curva 40/20/40 de `_blink_curve_value` de jerry_animation_studio/eye_system.py."""
    t = max(0.0, min(1.0, (offset - 1) / max(dur - 1, 1)))
    if t <= 0.40:
        p = t / 0.40; return p * p * (3.0 - 2.0 * p)
    if t <= 0.60: return 1.0
    p = (t - 0.60) / 0.40; return 1.0 - (p * p * (3.0 - 2.0 * p))


def parpadeos(inicio, fin, cuantos, dur):
    """misma distribucion que `_build_blink_map`: [(frame, valor)] de los parpadeos repartidos uniformemente en [inicio, fin]."""
    dur = max(dur, 6); total = fin - inicio + 1; cuantos = max(1, cuantos); slot = total / cuantos; mapa = {}
    for i in range(cuantos):
        bs = int(inicio + slot * i + slot / 2 - dur / 2); bs = max(inicio, min(bs, fin - dur + 1))
        for off in range(1, dur + 1):
            f = bs + off - 1
            if f > fin: break
            mapa[f] = max(mapa.get(f, 0.0), curva_parpadeo(off, dur))
    return sorted(mapa.items())


def main():
    if len(sys.argv) < 3: sys.exit(__doc__)
    audio = Path(sys.argv[1]); script = Path(sys.argv[2]); tree = ast.parse(script.read_text(encoding="utf-8")); datos = {}
    for nodo in tree.body:
        if isinstance(nodo, ast.Assign) and len(nodo.targets) == 1 and isinstance(nodo.targets[0], ast.Name):
            n = nodo.targets[0].id
            if n in NOMBRES or n == "phase_data": datos[n] = ast.literal_eval(nodo.value)
        elif isinstance(nodo, ast.ClassDef) and nodo.name == "Settings":
            datos["Settings"] = {t.targets[0].id: ast.literal_eval(t.value) for t in nodo.body if isinstance(t, ast.Assign) and isinstance(t.targets[0], ast.Name)}
    falta = [n for n in NOMBRES + ("phase_data", "Settings") if n not in datos]
    if falta: sys.exit(f"Faltan constantes en el script: {falta}")
    end = int(datos["END_FRAME"]); datos["tipo"] = "jerry"; datos["fuente"] = str(script.name)
    datos["parpadeos"] = [[f, round(v, 5)] for f, v in parpadeos(1, end, int(datos["BLINK_COUNT"]), 9)]
    base = audio.with_suffix("")
    Path(str(base) + ".cara.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    ruta_e = Path(str(base) + ".emocion.json")
    try: meta = json.loads(ruta_e.read_text(encoding="utf-8"))
    except Exception: meta = {}
    emo = MAPA.get(str(datos["GENERATED_EMOTION"]).lower(), "NEUTRO")
    meta.update({"fuente": "animacion_jerry.py de la app de expresion facial (voz de Jerry)", "texto": datos["TRANSCRIPT"], "emocion": emo, "intensidad": round(min(1.3, 0.6 + 0.7 * float(datos["AMPLITUDE"])), 3), "duracion_s": round(end / 24.0, 3)})
    ruta_e.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    habla = [f for f, v in datos["SPEECH_CURVE"] if v > 0.05]
    print(f"Jerry: emocion {emo} | texto {datos['TRANSCRIPT']!r} | {end} frames | habla f{min(habla)}-f{max(habla)} ({len(habla)} f) | {len(datos['parpadeos'])} frames de parpadeo | {base}.cara.json / .emocion.json")


if __name__ == "__main__":
    main()
