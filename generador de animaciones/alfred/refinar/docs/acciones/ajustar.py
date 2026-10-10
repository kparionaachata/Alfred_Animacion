# -*- coding: utf-8 -*-
"""AJUSTAR VALORES SIN BLENDER (segundos): edita los guiones portables de la secuencia de una parte editando solo su JSON. Una orden = un comando.
  python ajustar.py organico breathing_amplitude=0.02 breathing_speed=0.01 head_sway_amplitude=0.03        filtros organicos de TODOS los guiones de la secuencia (o --solo parte del nombre)
  python ajustar.py camara --inicio=-91.6,-107.8,14.8 --destino=-95.9,-109.8,15.0 --desde 88 --duracion 24 --solo se_inclina     (= mover_camara.py)
  python ajustar.py ver                                                                                     lista la secuencia y sus filtros organicos
La secuencia (orden y archivos) esta en `secuencia_parte5.json`. Para verlo en Blender: `aplicar_secuencia.py` (una sola ejecucion dentro de Blender).
Los valores organicos validos son los campos de AlfredOrganicFilters (breathing_enabled/amplitude/speed/phase, head_sway_*, weight_shift_*, root_noise_*, secondary_motion_*, smooth_*, micro_scale_*, shoulder_noise_*)."""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__)); REF = os.path.dirname(os.path.dirname(AQUI)); SEC = os.path.join(AQUI, "secuencia_parte5.json")


def secuencia():
    with open(SEC, encoding="utf-8") as f: s = json.load(f)
    return [os.path.join(REF, "configuraciones", "guiones", x) for x in s["guiones"]]


def _val(t):
    for c in (int, float):
        try: return c(t)
        except ValueError: pass
    return {"true": True, "false": False}.get(t.lower(), t)


def organico(pares, solo=None):
    cambios = dict(p.split("=", 1) for p in pares); n = 0
    for f in secuencia():
        if solo and solo not in os.path.basename(f): continue
        d = json.load(open(f, encoding="utf-8")); o = d["alfred_segs"][0]["organic"]
        for k, v in cambios.items():
            if k not in o: print("  aviso: %r no es un campo organico de %s" % (k, os.path.basename(f)[:50]))
            o[k] = _val(v)
        json.dump(d, open(f, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2); n += 1
    print("organico actualizado en %d guion(es): %s" % (n, ", ".join("%s=%s" % (k, _val(v)) for k, v in cambios.items())))


def ver():
    for f in secuencia():
        d = json.load(open(f, encoding="utf-8")); o = d["alfred_segs"][0]["organic"]; r = d["portable"]["frame_range"]
        print("f%d-%d %-62s respiracion %s/%s cabeza %s" % (r[0], r[1], os.path.basename(f)[28:-5], o.get("breathing_amplitude"), o.get("breathing_speed"), o.get("head_sway_amplitude")))


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "ver": ver()
    elif a[0] == "organico":
        solo = None
        if "--solo" in a: i = a.index("--solo"); solo = a[i + 1]; a = a[:i] + a[i + 2:]
        organico(a[1:], solo)
    elif a[0] == "camara":
        sys.argv = ["mover_camara.py"] + a[1:]; solo = None
        if "--solo" in sys.argv:
            i = sys.argv.index("--solo"); solo = sys.argv[i + 1]; sys.argv = sys.argv[:i] + sys.argv[i + 2:]
        sys.path.insert(0, AQUI); import mover_camara as mc
        import argparse
        ap = argparse.ArgumentParser(); ap.add_argument("--inicio", type=mc._xyz, required=True); ap.add_argument("--destino", type=mc._xyz); ap.add_argument("--desde", type=int); ap.add_argument("--duracion", type=int, default=24)
        p = ap.parse_args(sys.argv[1:]); n = 0
        for f in secuencia():
            if solo and solo not in os.path.basename(f): continue
            mc.mover(f, p.inicio, p.destino, p.desde, p.duracion); n += 1
        print("camara actualizada en %d guion(es)" % n)
    else: print(__doc__)
