# -*- coding: utf-8 -*-
"""MOVER LA CAMARA DE UN PUNTO A OTRO, en segundos y SIN tocar Blender ni volver a exportar poses: se edita solo la seccion `camara` del guion portable (el JSON).
Sirve para cualquier guion portable / guion 2.0 (`configuraciones/guiones/*.json`): la camara no forma parte de las poses.

  python mover_camara.py <guion.json> --inicio=X,Y,Z [--destino=X,Y,Z --desde 88 --duracion 24] [--f0 61 --f1 112] [--interp smooth|linear] [--foco=X,Y,Z] [--objeto Camera.001]
      (sin --destino la camara queda FIJA en `inicio` todo el guion)
      inicio   donde esta la camara al empezar el guion (se mantiene fija hasta `desde`)
      destino  donde queda despues del movimiento
      desde    frame en que empieza a moverse (p. ej. cuando Alfred termina de asomarse)
      duracion frames que tarda en llegar (0 = CORTE: salta al destino en `desde`)
      f0 / f1  rango del guion (por omision: `portable.frame_range`)
  Ejemplo:  python mover_camara.py ../../configuraciones/guiones/configuracion_portable_alfred_se_inclina_para_mirar_afuera_f61_112.json --inicio=-91.623,-107.82,14.847 --destino=-95.995,-109.89,15.027 --desde 88 --duracion 24

IMPORTANTE: las coordenadas con signo negativo se escriben con `=` (--inicio=-91.6,-107.8,14.8) para que no se confundan con una opcion.
Tambien se usa como modulo (`mover_camara.mover(ruta_json, inicio, destino, desde, duracion, ...)`). Para ver el resultado en Blender: boton "Camara" del estudio (`alfst.cam_aplicar`) o `aplicar_en_blender()` (dentro de Blender, con el guion ya cargado en la escena).
Las entradas de camara que ya tenga el guion para ese objeto se REEMPLAZAN (las de otros objetos, p. ej. el foco, se conservan)."""
import argparse
import json
import os


def _xyz(s):
    v = [float(x) for x in s.split(",")]
    if len(v) != 3: raise ValueError("se esperan 3 valores X,Y,Z: %r" % s)
    return v


def mover(ruta, inicio, destino=None, desde=None, duracion=24, f0=None, f1=None, interp="smooth", objeto="Camera.001", foco=None):
    """edita `camara` de `ruta`: `objeto` fijo en `inicio` de f0 a `desde` y luego hacia `destino` (en `duracion` frames; 0 = corte). Devuelve las entradas escritas."""
    with open(ruta, encoding="utf-8") as fh: d = json.load(fh)
    if destino is None or desde is None: desde = None                                                     # sin destino: la camara queda FIJA en `inicio` todo el guion
    rango = (d.get("portable") or {}).get("frame_range") or [d.get("meta", {}).get("frame_ini", 1), d.get("meta", {}).get("frame_fin", desde)]
    f0 = int(rango[0] if f0 is None else f0); f1 = int(rango[1] if f1 is None else f1); duracion = int(duracion); desde = f1 if desde is None else int(desde)
    if not f0 <= desde <= f1: raise ValueError("`desde` (%d) debe estar dentro del rango del guion (%d-%d)" % (desde, f0, f1))
    r = lambda v: [round(float(x), 6) for x in v]
    cam = [e for e in (d.get("camara") or []) if e.get("objeto") != objeto or e.get("canal") not in (None, "location")]       # se quita solo la posicion de ese objeto (lente, f/, foco y otras camaras se conservan)
    cam = [e for e in cam if not (e.get("objeto") == objeto and e.get("tipo") == "movimiento")]
    fija = destino is None
    nuevas = [{"tipo": "claves", "objeto": objeto, "canal": "location", "interp": "LINEAR", "claves": [[f0] + r(inicio), [desde] + r(inicio)], "id": "cam_loc_f%d_f%d" % (f0, desde)}]
    if fija: pass
    elif duracion <= 0: nuevas[0]["claves"].append([desde + 1] + r(destino)); nuevas[0]["interp"] = "CONSTANT"; nuevas[0]["nota"] = "corte: la camara salta al destino en f%d" % (desde + 1)
    else: nuevas.append({"tipo": "movimiento", "objeto": objeto, "desde": desde, "hasta": desde + duracion, "destino": r(destino), "interp": interp, "id": "cam_mueve_f%d_f%d" % (desde, desde + duracion), "nota": "la camara pasa a estas coordenadas"})
    if foco is not None: nuevas.append({"tipo": "claves", "objeto": "Foco_Conversacion", "canal": "location", "interp": "LINEAR", "claves": [[f0] + r(foco), [f1] + r(foco)], "id": "cam_foco_f%d_f%d" % (f0, f1)})
    d["camara"] = nuevas + cam
    with open(ruta, "w", encoding="utf-8", newline="\n") as fh: json.dump(d, fh, ensure_ascii=False, indent=2)
    return nuevas


def aplicar_en_blender():
    """dentro de Blender: aplica la seccion `camara` del guion que esta en la escena (el mismo boton del estudio)."""
    import bpy
    return bpy.ops.alfst.cam_aplicar()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0]); ap.add_argument("guion"); ap.add_argument("--inicio", type=_xyz, required=True); ap.add_argument("--destino", type=_xyz)
    ap.add_argument("--desde", type=int); ap.add_argument("--duracion", type=int, default=24); ap.add_argument("--f0", type=int); ap.add_argument("--f1", type=int); ap.add_argument("--interp", default="smooth"); ap.add_argument("--foco", type=_xyz); ap.add_argument("--objeto", default="Camera.001")
    a = ap.parse_args(); out = mover(a.guion, a.inicio, a.destino, a.desde, a.duracion, a.f0, a.f1, a.interp, a.objeto, a.foco)
    if a.destino is None: print("camara de %s: FIJA en %s todo el guion" % (os.path.basename(a.guion), a.inicio)); raise SystemExit
    print("camara de %s: fija en %s hasta f%d y %s" % (os.path.basename(a.guion), a.inicio, a.desde, ("pasa a %s en %d frames (f%d-%d)" % (a.destino, a.duracion, a.desde, a.desde + a.duracion)) if a.duracion > 0 else "salta a %s (corte)" % a.destino))
