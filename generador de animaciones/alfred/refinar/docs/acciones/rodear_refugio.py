# -*- coding: utf-8 -*-
"""ZOMBIE QUE CAMINA ALREDEDOR DEL REFUGIO, SIN BLENDER (segundos): portable individual con la marcha del personaje (ciclo IA `parte2_<p>_sigue`) recorriendo un anillo alrededor del refugio, sentido antihorario, desde su posicion actual.
  python rodear_refugio.py zombie_2 --desde 1 --fin 240 --inicio=-98.62,-111.5,13 --rz-inicio=217 [--fase 13] [--velocidad 0.79]
El anillo es el rectangulo del refugio (x -98..-94, y -111..-107) ampliado --holgura (1.3 m) para no atravesar los bloques. El rumbo sigue la trayectoria (rz = rumbo - 90). Los primeros 30 frames se une desde la posicion inicial al anillo.
Estructura de huesos: de `zombie_1/refinar/poses/pose213.json` renombrada. Organico apagado. Visibles desde el inicio. Escribe `configuracion_portable_<p>_rodea_refugio_f<a>_<b>.json` + una pose por frame."""
import argparse
import hashlib
import json
import math
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
import caminar_a_pose as cp
import pose_estatica as pe

REFUGIO = (-98.0, -94.0, -111.0, -107.0)                                                   # xmin, xmax, ymin, ymax (bloques refugio_bloque_*)


def anillo(h):
    x0, x1, y0, y1 = REFUGIO[0] - h, REFUGIO[1] + h, REFUGIO[2] - h, REFUGIO[3] + h; pts = [(x1, y0), (x1, y1), (x0, y1), (x0, y0)]; seg = []; tot = 0.0       # esquina SE -> NE -> NO -> SO (antihorario)
    for i in range(4):
        a, b = pts[i], pts[(i + 1) % 4]; L = math.hypot(b[0] - a[0], b[1] - a[1]); seg.append((a, b, L)); tot += L
    def pos(s):
        s %= tot
        for a, b, L in seg:
            if s <= L: t = s / L; return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            s -= L
    return pos, tot


def plantilla(personaje):
    """estructura de huesos del personaje: pose de zombie_1 (`pose213.json`) con los nombres cambiados a este personaje (los `parado.json` de los demas zombies son copias con nombres de zombie_1)."""
    t = open(os.path.join(pe.BASE, "zombie_1", "refinar", "poses", "pose213.json"), encoding="utf-8").read().replace("zombie_1", personaje)
    d = json.loads(t); d["poses"][0].pop("root", None); d["poses"][0]["root"] = {"location": {"x": 0.0, "y": 0.0, "z": 0.0}, "rotation_euler_deg": {"x": 0.0, "y": 0.0, "z": 0.0}, "scale": {"x": 1.0, "y": 1.0, "z": 1.0}}
    for b in d["poses"][0]["bones"].values():
        for k in ("location", "rotation_euler_rad", "rotation_euler_deg"): b["local_space"][k] = {"x": 0.0, "y": 0.0, "z": 0.0}
    r = os.path.join(os.environ.get("TEMP", "."), "plantilla_%s.json" % personaje); json.dump(d, open(r, "w", encoding="utf-8"), indent=1); return r


def crear(personaje, desde, fin, inicio, rz_ini, fase=0, v=0.79, holgura=1.3):
    nombre = personaje + "_rodea_refugio"; pose_base = plantilla(personaje)
    ruta, n = pe.crear(personaje, pose_base, desde, fin - desde + 1, nombre, aparicion=False); C = json.load(open(ruta, encoding="utf-8")); carp = C["poses_dir"]
    pos, tot = anillo(holgura); s0 = min((i * tot / 4000.0 for i in range(4000)), key=lambda s: math.hypot(pos(s)[0] - inicio[0], pos(s)[1] - inicio[1])); p0 = pos(s0); off = (inicio[0] - p0[0], inicio[1] - p0[1])
    pose, per = cp.ciclo(personaje, 1.0); vf = v / 24.0; z = inicio[2]
    def xy(t):
        a = pos(s0 + vf * t); k = 1 - cp._smooth(t / 30.0); return a[0] + off[0] * k, a[1] + off[1] * k
    man = []; aps = {}
    for fr in range(desde, fin + 1):
        t = fr - desde; x, y = xy(t); xx, yy = xy(t + 6); rz_camina = math.degrees(math.atan2(yy - y, xx - x)) - 90.0
        d = (rz_camina - rz_ini + 180) % 360 - 180; rz = rz_ini + d * cp._smooth(t / 20.0)
        fp = json.load(open(os.path.join(carp, "%s_f%d.json" % (nombre, fr)), encoding="utf-8")); c = fp["poses"][0]; walk = pose(t + fase)
        for hn, hb in c["bones"].items():
            if hn not in walk: continue
            l, e = walk[hn]; ls = hb["local_space"]
            ls["location"] = dict(zip("xyz", [round(q, 6) for q in l])); ls["rotation_euler_rad"] = dict(zip("xyz", [round(q, 6) for q in e])); ls["rotation_euler_deg"] = dict(zip("xyz", [round(math.degrees(q), 4) for q in e]))
            hb["raw_rotation_euler_deg"] = dict(ls["rotation_euler_deg"]); hb["raw_location"] = dict(ls["location"]); hb["rotation_mode"] = "XYZ"
        c["root"] = {"location": {"x": round(x, 6), "y": round(y, 6), "z": z}, "rotation_euler_deg": {"x": 0.0, "y": 0.0, "z": round(rz, 4)}, "scale": {"x": 1.0, "y": 1.0, "z": 1.0}}
        p = os.path.join(carp, "%s_f%d.json" % (nombre, fr)); json.dump(fp, open(p, "w", encoding="utf-8", newline="\n"), indent=2, ensure_ascii=False)
        man.append({"frame": fr, "archivo": os.path.basename(p), "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest()}); aps[fr] = (x, y, z, rz)
    def fix(ap): k = int(ap["pose_name"].rsplit("_f", 1)[1]); x, y, zz, rz = aps[k]; ap.update({"pos_x": x, "pos_y": y, "pos_z": zz, "rot_x": 0.0, "rot_y": 0.0, "rot_z": rz})
    for ap in C["action_poses"]: fix(ap)
    for ap in C[personaje + "_segs"][0]["action_poses"]: fix(ap)
    C["portable"]["pose_manifest"] = man; C["paso1_path"]["root_rot_z"] = rz_ini; C["paso1_path"]["path_points"][0]["coords"] = [inicio[0], inicio[1], z]
    C["description"] = "%s camina alrededor del refugio (anillo con holgura %.1f m, antihorario, %.2f m/s) desde (%.3f, %.3f) durante f%d-f%d." % (personaje, holgura, v, inicio[0], inicio[1], desde, fin)
    C["export_desc"] = C["description"]; C["meta"]["titulo"] = C["description"]; C["meta"]["notas"] = "Marcha del ciclo IA parte2_%s_sigue (fase %d). Anillo alrededor de x %s y %s del refugio. Visible desde f%d." % (personaje, fase, REFUGIO[:2], REFUGIO[2:], desde)
    C["anclas"] = {"inicio": desde, "fin": fin}
    C["mundo"] = [{"id": "visible_" + personaje, "accion": "mostrar", "objetos": [o for o in pe.objetos_del_personaje(personaje) if o != personaje and not o.endswith("_Armature")], "t": "inicio", "nota": "visible desde el inicio"}]
    json.dump(C, open(ruta, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
    return ruta, n


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0]); a.add_argument("personaje"); a.add_argument("--desde", type=int, default=1); a.add_argument("--fin", type=int, default=240); a.add_argument("--inicio", type=cp._xyz, required=True)
    a.add_argument("--rz-inicio", type=float, required=True); a.add_argument("--fase", type=float, default=0.0); a.add_argument("--velocidad", type=float, default=0.79); a.add_argument("--holgura", type=float, default=1.3)
    p = a.parse_args(); r, n = crear(p.personaje, p.desde, p.fin, p.inicio, p.rz_inicio, p.fase, p.velocidad, p.holgura); print("guion escrito (%d frames): %s" % (n, r))
