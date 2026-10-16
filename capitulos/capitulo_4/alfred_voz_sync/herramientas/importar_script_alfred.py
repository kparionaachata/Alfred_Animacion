r"""Convierte el `animacion_alfred.py` que genera la app estudio_audio_expresion (voz de Alfred) en datos para Alfred Voz Sync, SIN ejecutarlo (se lee con `ast`; el script de la app es destructivo: borra la
animacion de los ojos y cambia el rango de la escena). Usa EXACTAMENTE la geometria (`COORDINATES`), los parametros y las fases del script, y su parpadeo (`BLINK_CENTERS`).
Escribe junto al audio:
  <audio>.cara.json    : {"tipo": "alfred", emocion, parametros, fases, coordenadas, parpadeos [[frame, 1.0]], duracion_s = END_FRAME / 24, habla = {curva, vertical, scale_x, scale_z, attack_rotation} (oscilacion del habla de las mallas de los ojos)}
  <audio>.emocion.json : texto (el de la app), emocion, intensidad (si ya existe -p. ej. creado por analizar_audio.py- se conservan las palabras con su tiempo)
Uso:  python importar_script_alfred.py "C:\...\audios\alfred\x.mp3" "C:\...\Downloads\animacion_alfred.py"
"""
import ast
import json
import sys
from pathlib import Path

MAPA = {"alegria": "ALEGRIA", "tristeza": "TRISTEZA", "enojo": "ENOJO", "sorpresa": "SORPRESA", "cansancio": "SUENO", "duda": "DUDA", "curiosidad": "DUDA", "neutral": "NEUTRO", "miedo": "MIEDO", "disgusto": "ENOJO", "asco": "ENOJO"}
NOMBRES = ("GENERATED_EMOTION", "TRANSCRIPT", "COORDINATES", "END_FRAME", "SHAPE_VALUE", "SCALE_X", "SCALE_Z", "VERTICAL", "ROTATION", "LATERAL", "BLINK_CENTERS", "phase_data")
OPCIONALES = ("SPEECH_CURVE", "SPEECH_VERTICAL", "SPEECH_SCALE_X", "SPEECH_SCALE_Z", "ATTACK_ROTATION")           # oscilacion del habla de los OJOS (pulso vertical, squash / stretch, giro de ataque)


def main():
    if len(sys.argv) < 3: sys.exit(__doc__)
    audio = Path(sys.argv[1]); script = Path(sys.argv[2]); raw = script.read_bytes()
    try: src = raw.decode("utf-8")
    except UnicodeDecodeError: src = raw.decode("cp1252", errors="replace")                         # los scripts de la app pueden venir en ANSI (ñ, acentos)
    tree = ast.parse(src); d = {}
    for nodo in tree.body:
        if isinstance(nodo, ast.Assign) and len(nodo.targets) == 1 and isinstance(nodo.targets[0], ast.Name) and nodo.targets[0].id in NOMBRES + OPCIONALES: d[nodo.targets[0].id] = ast.literal_eval(nodo.value)
    falta = [n for n in NOMBRES if n not in d]
    if falta: sys.exit(f"Faltan constantes en el script: {falta}")
    end = int(d["END_FRAME"]); emo = MAPA.get(str(d["GENERATED_EMOTION"]).lower(), "NEUTRO")
    par = {"shape_value": d["SHAPE_VALUE"], "scale_x": d["SCALE_X"], "scale_z": d["SCALE_Z"], "vertical": d["VERTICAL"], "rotation": d["ROTATION"], "lateral": d["LATERAL"]}
    base = audio.with_suffix(""); ruta_e = Path(str(base) + ".emocion.json")
    try: meta = json.loads(ruta_e.read_text(encoding="utf-8"))
    except Exception: meta = {}
    inten = float(meta.get("intensidad", 1.0)) if meta else 1.0
    cara = {"tipo": "alfred", "fuente": script.name, "emocion": emo, "componentes": [{"expression": "procedural (app)", "weight": 1.0}], "intensidad": round(min(1.0, inten), 3), "parametros": par,
            "fases": [list(q) for q in d["phase_data"]], "duracion_s": round(end / 24.0, 4), "coordenadas": d["COORDINATES"], "parpadeos": [[int(c), 1.0] for c in d["BLINK_CENTERS"]]}
    if all(k in d for k in OPCIONALES):
        cara["habla"] = {"curva": [[int(f), float(v)] for f, v in d["SPEECH_CURVE"]], "vertical": d["SPEECH_VERTICAL"], "scale_x": d["SPEECH_SCALE_X"], "scale_z": d["SPEECH_SCALE_Z"], "attack_rotation": d["ATTACK_ROTATION"]}
    Path(str(base) + ".cara.json").write_text(json.dumps(cara, ensure_ascii=False), encoding="utf-8")
    texto = str(d["TRANSCRIPT"]).replace("sue�o", "sueño"); pal = meta.get("palabras") or []
    nuevas = texto.replace(",", " ").split()
    if pal and len(nuevas) == len(pal):                                                       # el texto de la app corrige a Whisper; los tiempos de cada palabra se conservan
        for p_, w_ in zip(pal, nuevas): p_["w"] = w_
    meta.update({"fuente": f"{script.name} de la app de expresion facial (voz de Alfred)", "texto": texto, "emocion": emo, "intensidad": cara["intensidad"], "duracion_s": cara["duracion_s"], "palabras": pal, "forzada": True})
    ruta_e.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Alfred: emocion {emo} | texto {texto!r} | {end} frames | parpadeo en {d['BLINK_CENTERS']} | {len(d['COORDINATES'])} ojos | palabras {len(pal)} | {base}.cara.json / .emocion.json")


if __name__ == "__main__":
    main()
