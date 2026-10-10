# -*- coding: utf-8 -*-
"""FIJAR UNA POSE (de un archivo de pose) COMO POSE FINAL DE UN PORTABLE, SIN BLENDER (segundos): desde `--hasta` el personaje tiene EXACTAMENTE los valores del archivo (huesos y root: posicion y rotacion Z);
entre `--desde` y `--hasta` se mezcla (suave) desde la pose que habia. Los angulos del archivo pueden venir con vueltas (p. ej. 396 grados): en la mezcla se usa el equivalente mas cercano a la pose anterior.
  python fijar_pose_final.py <configuracion_portable.json> <pose.json> --desde 414 --hasta 422
Actualiza las poses por frame, el manifiesto (sha256) y action_poses (posicion / rotacion Z del root). Repetible, pero hay que volver a correrlo si se vuelve a exportar el portable."""
import argparse
import hashlib
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from caminar_a_pose import _smooth as ss


def main(cfg_f, pose_f, desde, hasta):
    C = json.load(open(cfg_f, encoding="utf-8")); D = C["portable"]["poses_directory"]; man = {m["frame"]: m for m in C["portable"]["pose_manifest"]}; T = json.load(open(pose_f, encoding="utf-8"))["poses"][0]; fin = max(man); n = 0; aps = {}
    for f in range(desde, fin + 1):
        ruta = os.path.join(D, man[f]["archivo"]); fp = json.load(open(ruta, encoding="utf-8")); c = fp["poses"][0]; w = ss((f - desde) / float(hasta - desde)) if f < hasta else 1.0
        for hn, hb in c["bones"].items():
            if hn not in T["bones"]: continue
            t = T["bones"][hn]["local_space"]; g = hb["local_space"]
            if w >= 1.0:
                hb["local_space"] = json.loads(json.dumps(t)); hb["raw_rotation_euler_deg"] = dict(t["rotation_euler_deg"]); hb["raw_location"] = dict(t["location"]); hb["raw_scale"] = dict(t["scale"])
            else:
                for k in "xyz":
                    r0 = g["rotation_euler_rad"][k]; r1 = t["rotation_euler_rad"][k]; r1 = r1 - 2 * math.pi * round((r1 - r0) / (2 * math.pi)); r = r0 + (r1 - r0) * w
                    g["rotation_euler_rad"][k] = round(r, 6); g["rotation_euler_deg"][k] = round(math.degrees(r), 4)
                    g["location"][k] = round(g["location"][k] + (t["location"][k] - g["location"][k]) * w, 6); g["scale"][k] = round(g["scale"][k] + (t["scale"][k] - g["scale"][k]) * w, 6)
                hb["raw_rotation_euler_deg"] = dict(g["rotation_euler_deg"]); hb["raw_location"] = dict(g["location"]); hb["raw_scale"] = dict(g["scale"])
        r0 = c["root"]; tr = T["root"]
        if w >= 1.0: c["root"] = json.loads(json.dumps(tr))
        else:
            for k in "xyz": r0["location"][k] = round(r0["location"][k] + (tr["location"][k] - r0["location"][k]) * w, 6)
            r0["rotation_euler_deg"]["z"] = round(r0["rotation_euler_deg"]["z"] + (tr["rotation_euler_deg"]["z"] - r0["rotation_euler_deg"]["z"]) * w, 4)
        json.dump(fp, open(ruta, "w", encoding="utf-8", newline="\n"), indent=2, ensure_ascii=False); man[f]["sha256"] = hashlib.sha256(open(ruta, "rb").read()).hexdigest()
        r = c["root"]; aps[f] = (r["location"]["x"], r["location"]["y"], r["location"]["z"], r["rotation_euler_deg"]["z"]); n += 1
    def fix(ap):
        k = int(ap["pose_name"].rsplit("_f", 1)[1])
        if k in aps: x, y, z, rz = aps[k]; ap.update({"pos_x": x, "pos_y": y, "pos_z": z, "rot_z": rz})
    for ap in C["action_poses"]: fix(ap)
    for clave in [k for k in C if k.endswith("_segs")]:
        for ap in C[clave][0]["action_poses"]: fix(ap)
    C["portable"]["pose_manifest"] = [man[k] for k in sorted(man)]; C.setdefault("meta", {})["pose_final"] = {"archivo": os.path.basename(pose_f), "desde": desde, "hasta": hasta}
    json.dump(C, open(cfg_f, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2); print("POSE FINAL: %d frames (f%d-f%d): pose de %s desde f%d; root (%.6f, %.6f, %.1f) rz %.4f" % (n, desde, fin, os.path.basename(pose_f), hasta, *aps[fin]))


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0]); a.add_argument("config"); a.add_argument("pose"); a.add_argument("--desde", type=int, required=True); a.add_argument("--hasta", type=int, required=True); p = a.parse_args(); main(p.config, p.pose, p.desde, p.hasta)
