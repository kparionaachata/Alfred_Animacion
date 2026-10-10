# -*- coding: utf-8 -*-
"""ZOMBIE QUE SE RETIRA TRAS RECIBIR UN GOLPE Y SIGUE CAMINANDO ALREDEDOR DEL REFUGIO, SIN BLENDER (segundos): modifica las poses por frame de un portable desde el frame del golpe.
  python zombie_retirada_golpe.py zombie_1 <configuracion_portable.json> --golpe 256 [--fin 340] [--camina-desde 262]
- f golpe .. golpe+8: el brazo que araña vuelve a la pose base (la de `pose213`); el tronco se echa hacia atras (Spine1/Spine2, sacudida que decae en 12 frames).
- desde `camina-desde`: mezcla (12 frames) de esa pose a la marcha del personaje (ciclo IA `parte2_<p>_sigue`) y retrocede hacia el anillo del refugio (el de `rodear_refugio.py`, antihorario, 0.79 m/s): se une al anillo en 30 frames y gira hasta su rumbo.
Repetible sobre el portable ya generado por `caminar_a_pose.py` + `zombie_arana_brazo.py` (reescribe los frames >= golpe). Actualiza root, huesos, manifiesto y action_poses."""
import argparse
import hashlib
import json
import math
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
import caminar_a_pose as cp
import rodear_refugio as rr


def ss(x): return cp._smooth(x)


def ang(a, b, u):
    d = (b - a + 180.0) % 360.0 - 180.0; return a + d * u


def main(pers, cfg_f, golpe, fin, camina, base_pose, v=0.79, holgura=1.3, sentido=1):
    C = json.load(open(cfg_f, encoding="utf-8")); D = C["portable"]["poses_directory"]; man = {m["frame"]: m for m in C["portable"]["pose_manifest"]}; nombre = [m["archivo"] for m in man.values()][0].rsplit("_f", 1)[0]
    base = json.load(open(base_pose, encoding="utf-8"))["poses"][0]; pose, per = cp.ciclo(pers, 1.0); pos, tot = rr.anillo(holgura)
    cargar = lambda f: json.load(open(os.path.join(D, man[f]["archivo"]), encoding="utf-8"))
    P0 = (base["root"]["location"]["x"], base["root"]["location"]["y"], base["root"]["location"]["z"]); RZ0 = base["root"]["rotation_euler_deg"]["z"]
    s0 = min((i * tot / 4000.0 for i in range(4000)), key=lambda s: math.hypot(pos(s)[0] - P0[0], pos(s)[1] - P0[1])); p0 = pos(s0); off = (P0[0] - p0[0], P0[1] - p0[1]); vf = v / 24.0
    brazo = [n for n in base["bones"] if "UpArm" in n or "elbow" in n and n.startswith("Right")]; arm_golpe = {n: dict(cargar(golpe)["poses"][0]["bones"][n]["local_space"]["rotation_euler_rad"]) for n in brazo if n.startswith("Right")}
    dist = 0.0; aps = {}
    def xy(t, d): a = pos(s0 + sentido * d); k = 1 - ss(t / 30.0); return a[0] + off[0] * k, a[1] + off[1] * k
    for f in range(golpe + 1, fin + 1):
        fp = cargar(f); c = fp["poses"][0]; r = f - golpe; t = f - camina
        rec = ss(r / 3.0) * (1 - ss((r - 3) / 12.0)); wa = ss(r / 8.0); w = ss(t / 12.0) if t > 0 else 0.0
        walk = pose(max(t, 0)) if t > 0 else None
        for hn, hb in c["bones"].items():
            ls = hb["local_space"]; b0 = base["bones"][hn]["local_space"]; eu = {k: b0["rotation_euler_rad"][k] for k in "xyz"}; lo = {k: b0["location"][k] for k in "xyz"}
            if hn in arm_golpe: eu = {k: arm_golpe[hn][k] + (eu[k] - arm_golpe[hn][k]) * wa for k in "xyz"}              # el brazo suelta el arañazo
            if hn.startswith("Spine1_"): eu["x"] -= math.radians(10.0) * rec
            elif hn.startswith("Spine2_"): eu["x"] -= math.radians(14.0) * rec
            elif hn.startswith("Hips_"): eu["x"] -= math.radians(6.0) * rec
            if walk is not None and hn in walk:
                l, e = walk[hn]; eu = {k: eu[k] + (e[i] - eu[k]) * w for i, k in enumerate("xyz")}; lo = {k: lo[k] + (l[i] - lo[k]) * w for i, k in enumerate("xyz")}
            ls["rotation_euler_rad"] = {k: round(eu[k], 6) for k in "xyz"}; ls["rotation_euler_deg"] = {k: round(math.degrees(eu[k]), 4) for k in "xyz"}; ls["location"] = {k: round(lo[k], 6) for k in "xyz"}
            hb["raw_rotation_euler_deg"] = dict(ls["rotation_euler_deg"]); hb["raw_location"] = dict(ls["location"]); hb["rotation_mode"] = "XYZ"
        if t > 0:
            dist += vf * ss(t / 12.0); x, y = xy(t, dist); xx, yy = xy(t + 6, dist + vf * 6); rz = ang(RZ0, math.degrees(math.atan2(yy - y, xx - x)) - 90.0, ss(t / 20.0))
        else: x, y, rz = P0[0], P0[1], RZ0
        c["root"] = {"location": {"x": round(x, 6), "y": round(y, 6), "z": P0[2]}, "rotation_euler_deg": {"x": 0.0, "y": 0.0, "z": round(rz, 4)}, "scale": {"x": 1.0, "y": 1.0, "z": 1.0}}
        ruta = os.path.join(D, man[f]["archivo"]); json.dump(fp, open(ruta, "w", encoding="utf-8", newline="\n"), indent=2, ensure_ascii=False); man[f]["sha256"] = hashlib.sha256(open(ruta, "rb").read()).hexdigest(); aps[f] = (x, y, P0[2], rz)
    def fix(ap):
        k = int(ap["pose_name"].rsplit("_f", 1)[1])
        if k in aps: x, y, z, rz = aps[k]; ap.update({"pos_x": x, "pos_y": y, "pos_z": z, "rot_x": 0.0, "rot_y": 0.0, "rot_z": rz})
    for ap in C["action_poses"]: fix(ap)
    for ap in C[pers + "_segs"][0]["action_poses"]: fix(ap)
    C["portable"]["pose_manifest"] = [man[k] for k in sorted(man)]; C["anclas"]["golpe"] = golpe; C["anclas"]["camina_desde"] = camina; C["anclas"]["fin"] = fin
    C["description"] = C["description"].rstrip() + " Al recibir el stick en f%d se echa hacia atras, se retira y desde f%d camina alrededor del refugio (anillo %s, %.2f m/s) hasta f%d." % (golpe, camina, "antihorario" if sentido > 0 else "horario", v, fin)
    C["export_desc"] = C["description"]; C["meta"]["titulo"] = C["description"]; C["meta"]["frame_fin"] = fin
    json.dump(C, open(cfg_f, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2); print("RETIRADA: %s f%d-f%d | golpe f%d, camina desde f%d, ultimo punto (%.2f, %.2f)" % (pers, golpe + 1, fin, golpe, camina, aps[fin][0], aps[fin][1]))


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0]); a.add_argument("personaje"); a.add_argument("config"); a.add_argument("--golpe", type=int, required=True); a.add_argument("--fin", type=int, default=340); a.add_argument("--camina-desde", type=int, default=None); a.add_argument("--horario", action="store_true", help="recorre el anillo en sentido horario (por omision antihorario)")
    a.add_argument("--pose", default=os.path.join(rr.pe.BASE, "zombie_1", "refinar", "poses", "pose213.json")); p = a.parse_args(); main(p.personaje, p.config, p.golpe, p.fin, p.camina_desde or p.golpe + 6, p.pose, sentido=-1 if p.horario else 1)
