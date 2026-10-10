# -*- coding: utf-8 -*-
"""CAMINAR HASTA UNA POSE, SIN BLENDER (segundos): el personaje camina en linea recta desde su posicion inicial y llega, en el frame exacto, a la posicion/rotacion/pose de un archivo de pose.
  python caminar_a_pose.py zombie_1 <pose.json> --desde 1 --llega 193 --fin 240 --inicio=-93.604,-111.711 --rz-inicio=-56.2 [--nombre zombie_1_camina_al_refugio] [--estiramiento 1.25]
    ciclo de marcha: se toma de la animacion IA del personaje (`animaciones_ia/parte2_<p>_sigue/*.animacion.json`, estilo ZOMBIE_ASIM); --estiramiento >1 lo hace mas lento.
    el personaje esta visible desde --desde (no hay aparicion). Rumbo: rz = rumbo - 90 (convencion del ciclo IA). Los ultimos --mezcla frames se mezclan del ciclo a la pose exacta.
Escribe un portable individual (pose por frame + configuracion), organico TODO apagado."""
import argparse
import glob
import hashlib
import json
import math
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
import pose_estatica as pe


def _smooth(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


def _lerp(a, b, t): return a + (b - a) * t


def _xyz(s): return [float(v) for v in s.split(",")]


def ciclo(personaje, estir):
    """(funcion frame_de_ciclo -> {hueso: (loc[3], rot[3] rad)}, periodo) a partir de la animacion IA de marcha."""
    f = glob.glob(os.path.join(pe.BASE, personaje, "refinar", "animaciones_ia", "parte2_%s_sigue" % personaje, "*.animacion.json"))[0]
    d = json.load(open(f, encoding="utf-8")); bones = d["armature"]["bones"]; f0 = d["frame_inicio"]
    # picos de la pierna derecha (X) entre 200 y 500 -> periodo
    k = [n for n in bones if n.startswith("RightUpLeg")][0]; seg = bones[k]["rotation_euler"][0]
    pk = [i for i in range(200, 500) if seg[i] > seg[i - 1] and seg[i] >= seg[i + 1] and seg[i] > 0.2]
    pk = [q for j, q in enumerate(pk) if j == 0 or q - pk[j - 1] > 20]                         # elimina picos duplicados de una meseta
    a, b = pk[1], pk[2]; per = b - a                                                      # un ciclo completo
    def pose(t):                                                                              # t = fase en frames de ciclo (0..per)
        x = a + (t % per); i = int(math.floor(x)); w = x - i; out = {}
        for n, v in bones.items():
            r = [_lerp(v["rotation_euler"][c][i], v["rotation_euler"][c][i + 1], w) for c in range(3)]
            l = [(_lerp(v["location"][c][i], v["location"][c][i + 1], w) if isinstance(v["location"][c], list) else v["location"][c]) for c in range(3)]; out[n] = (l, r)
        return out
    # cierre del ciclo: mezcla suave los ultimos 6 frames hacia la fase 0 para que no haya salto
    return pose, per * estir


def crear(personaje, pose_file, desde, llega, fin, inicio, rz_ini, nombre, estir=1.25, mezcla=20, desvio=0.55):
    destino = json.load(open(pose_file, encoding="utf-8"))["poses"][0]; r = destino["root"]; fin_xyz = (r["location"]["x"], r["location"]["y"], r["location"]["z"]); rz_fin = r["rotation_euler_deg"]["z"]
    ruta, n = pe.crear(personaje, pose_file, desde, fin - desde + 1, nombre, aparicion=False)                  # estructura (config + poses) con la pose fija; luego se reescribe por frame
    C = json.load(open(ruta, encoding="utf-8")); pose, per = ciclo(personaje, estir); per_real = per / estir
    dx, dy = fin_xyz[0] - inicio[0], fin_xyz[1] - inicio[1]; rumbo = math.degrees(math.atan2(dy, dx)); rz_camina = rumbo - 90.0; dist = math.hypot(dx, dy); dur = llega - desde
    carp = C["poses_dir"]; man = []; aps = {}
    def trayecto(s):                                                                                          # recta inicio->destino con un desvio lateral (+X) para no atravesar la pared del refugio
        b = _smooth(s / 0.25) * (1 - _smooth((s - 0.75) / 0.25)); return inicio[0] + dx * s + desvio * b, inicio[1] + dy * s
    for fr in range(desde, fin + 1):
        u = min(1.0, (fr - desde) / dur); s = u * (1.2 - 0.2 * u)                                              # avance con ligero frenado final
        x, y = trayecto(s); z = inicio[2] if len(inicio) > 2 else fin_xyz[2]
        s2 = min(1.0, s + 0.01); xx, yy = trayecto(s2); rz_camina = math.degrees(math.atan2(yy - y, xx - x)) - 90.0 if s < 0.99 else rz_camina
        rz = _lerp(rz_ini, rz_camina, _smooth((fr - desde) / 20.0)); rz = _lerp(rz, rz_fin, _smooth((fr - (llega - mezcla)) / float(mezcla)))
        if fr >= llega: x, y, z, rz = fin_xyz[0], fin_xyz[1], fin_xyz[2], rz_fin
        w = _smooth((fr - (llega - mezcla)) / float(mezcla)) if fr < llega else 1.0
        fp = json.load(open(os.path.join(carp, "%s_f%d.json" % (nombre, fr)), encoding="utf-8")); c = fp["poses"][0]
        walk = pose((fr - desde) / estir) if w < 1.0 else None
        for hn, hb in c["bones"].items():
            ls = hb["local_space"]; dd = destino["bones"][hn]["local_space"]
            if walk is not None and hn in walk:
                l, e = walk[hn]
                loc = [_lerp(l[i], dd["location"][k], w) for i, k in enumerate("xyz")]; rot = [_lerp(e[i], dd["rotation_euler_rad"][k], w) for i, k in enumerate("xyz")]
                ls["location"] = dict(zip("xyz", [round(v, 6) for v in loc])); ls["rotation_euler_rad"] = dict(zip("xyz", [round(v, 6) for v in rot])); ls["rotation_euler_deg"] = dict(zip("xyz", [round(math.degrees(v), 4) for v in rot]))
                hb["raw_rotation_euler_deg"] = dict(ls["rotation_euler_deg"]); hb["raw_location"] = dict(ls["location"]); hb["rotation_mode"] = "XYZ"
        c["root"] = {"location": {"x": round(x, 6), "y": round(y, 6), "z": round(z, 6)}, "rotation_euler_deg": {"x": 0.0, "y": 0.0, "z": round(rz, 4)}, "scale": {"x": 1.0, "y": 1.0, "z": 1.0}}
        p = os.path.join(carp, "%s_f%d.json" % (nombre, fr)); json.dump(fp, open(p, "w", encoding="utf-8", newline="\n"), indent=2, ensure_ascii=False)
        man.append({"frame": fr, "archivo": os.path.basename(p), "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest()}); aps[fr] = (x, y, z, rz)
    def fix(ap):
        k = int(ap["pose_name"].rsplit("_f", 1)[1]); x, y, z, rz = aps[k]; ap.update({"pos_x": x, "pos_y": y, "pos_z": z, "rot_x": 0.0, "rot_y": 0.0, "rot_z": rz})
    for ap in C["action_poses"]: fix(ap)
    for ap in C[personaje + "_segs"][0]["action_poses"]: fix(ap)
    C["portable"]["pose_manifest"] = man
    x0, y0 = aps[desde][0], aps[desde][1]
    C["paso1_path"]["root_rot_z"] = rz_ini; C["paso1_path"]["path_points"][0]["coords"] = [inicio[0], inicio[1], aps[desde][2]]
    C["description"] = "%s camina en linea recta desde (%.3f, %.3f) hacia el refugio (%.2f m, rumbo %.1f grados) y llega en f%d exacto a la posicion/pose de %s; se queda ahi hasta f%d." % (personaje, inicio[0], inicio[1], dist, rumbo, llega, os.path.basename(pose_file), fin)
    C["export_desc"] = C["description"]; C["meta"]["titulo"] = C["description"]; C["meta"]["notas"] = "Marcha tomada del ciclo IA (parte2_%s_sigue), estiramiento x%.2f (periodo %.0f frames); ultimos %d frames mezclados a la pose exacta. Visible desde f%d (sin aparicion)." % (personaje, estir, per, mezcla, desde)
    C["anclas"] = {"inicio": desde, "llega": llega, "fin": fin}; C["mundo"] = [{"id": "visible_" + personaje, "accion": "mostrar", "objetos": [o for o in pe.objetos_del_personaje(personaje) if o != personaje and not o.endswith("_Armature")], "t": "inicio", "nota": "visible desde el inicio"}]
    json.dump(C, open(ruta, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
    return ruta, n, dist, rumbo


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0]); a.add_argument("personaje"); a.add_argument("pose"); a.add_argument("--desde", type=int, default=1); a.add_argument("--llega", type=int, required=True); a.add_argument("--fin", type=int, required=True)
    a.add_argument("--inicio", type=_xyz, required=True); a.add_argument("--rz-inicio", type=float, required=True); a.add_argument("--nombre"); a.add_argument("--estiramiento", type=float, default=1.25); a.add_argument("--mezcla", type=int, default=20); a.add_argument("--desvio", type=float, default=0.55)
    p = a.parse_args(); r, n, d, rb = crear(p.personaje, p.pose, p.desde, p.llega, p.fin, p.inicio, p.rz_inicio, p.nombre or p.personaje + "_camina_al_refugio", p.estiramiento, p.mezcla, p.desvio)
    print("guion escrito (%d frames, %.2f m, rumbo %.1f): %s" % (n, d, rb, r))
