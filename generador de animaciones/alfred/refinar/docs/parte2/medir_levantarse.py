"""Se ejecuta DENTRO de Blender (exec). Mide, para cada zombie, la subida organica (zombie_levantarse_parte2.py) y escribe `levantarse_correccion.json` para `compose_zombies_parte2.py`:
  rel[i] = altura del punto mas bajo de la malla evaluada respecto al origen del vacio del zombie (solo depende de la pose); `compose_zombies_parte2.py` fija con ella la altura de la raiz: zs = suelo + rel[fin] - rel[i] (de pie rel[fin] = apoyo normal; tendido o sentado el cuerpo toca el suelo sin atravesarlo y sube al empujar con los brazos),
  dx, dy[i] = desplazamiento horizontal (mundo) de la raiz para que los tobillos queden PLANTADOS (la media de los dos tobillos no se mueve respecto al primer frame de la subida).
No cambia la escena de forma permanente: coloca el vacio y los huesos del zombie segun el artefacto `parte2_zombie_N_sigue` frame a frame (hay que volver a hacer frame_set despues), no inserta keyframes.
Flujo de dos pasadas: 1) borrar `levantarse_correccion.json`, python compose_zombies_parte2.py; 2) exec de este script en Blender (escribe el json); 3) python compose_zombies_parte2.py otra vez.
`medir()` solo mide y devuelve el residuo cuando ya hay correcciones aplicadas (comprobacion).
"""
import bpy, json, math, os
import numpy as np
from mathutils import Vector

BASE = r"C:\Users\user\Desktop\Alfred_Animacion"
HERE = os.path.join(BASE, "generador de animaciones", "alfred", "refinar", "docs", "parte2")
RISE = {1: 30, 2: 34, 3: 26, 5: 28, 4: 36}                                       # FALLV[n]["rise"]
RISE_EXTRA = 14


def cargar(n):
    return json.load(open(os.path.join(BASE, "generador de animaciones", f"zombie_{n}", "refinar", "animaciones_ia", f"parte2_zombie_{n}_sigue", f"parte2_zombie_{n}_sigue.animacion.json"), encoding="utf-8"))


def val(c, i):
    return c[i] if isinstance(c, list) else c


def poner(n, D, k):
    emp = bpy.data.objects[f"zombie_{n}"]; L = D["root"]["canales"]["location"]; R = D["root"]["canales"]["rotation_euler"]
    emp.location = (val(L[0], k), val(L[1], k), val(L[2], k)); emp.rotation_euler = (val(R[0], k), val(R[1], k), val(R[2], k))
    arm = bpy.data.objects[f"zombie_{n}_Armature"]
    for b, pr in D["armature"]["bones"].items():
        pb = arm.pose.bones.get(b)
        if pb: pb.rotation_euler = (val(pr["rotation_euler"][0], k), val(pr["rotation_euler"][1], k), val(pr["rotation_euler"][2], k))
    return emp, arm


def medir_frame(n, D, k):
    emp, arm = poner(n, D, k); bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); zmin = 1e9
    for o in bpy.data.objects:
        if o.type != 'MESH' or not o.name.endswith(f"_zombie_{n}") or o.parent is None: continue
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        try:
            co = np.empty(len(me.vertices) * 3, dtype=np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
            mw = np.array(ev.matrix_world); zw = co @ mw[2, :3] + mw[2, 3]; zmin = min(zmin, float(zw.min()))
        finally: ev.to_mesh_clear()
    mwa = arm.matrix_world; ta = [mwa @ arm.pose.bones[f"{s}_zombie_{n}"].tail for s in ("Rightknee", "Leftknee")]
    return zmin - emp.location.z, (ta[0].x + ta[1].x) / 2, (ta[0].y + ta[1].y) / 2


def rango(n, kh_golpe_frame, libre_frame):
    rise_f = RISE[n] + RISE_EXTRA; k_end = libre_frame - 1; k0 = k_end - rise_f; return k0, k_end


def medir(escribir=True):
    ev = json.load(open(os.path.join(HERE, "empujes_zombies.json"), encoding="utf-8"))["eventos"]; out = {}; informe = []
    for n in range(1, 6):
        e = ev[str(n)]; D = cargar(n); k0, k_end = rango(n, e["frame_golpe"], e["frame_libre"]); filas = []
        for k in range(k0, k_end + 1): filas.append(medir_frame(n, D, k))
        z0, x0, y0 = filas[0]
        rel = [round(f[0], 5) for f in filas]; dz = [round(filas[-1][0] - f[0], 5) for f in filas]; dx = [round(x0 - f[1], 5) for f in filas]; dy = [round(y0 - f[2], 5) for f in filas]
        out[str(n)] = {"k0": k0, "rel": rel, "dx": dx, "dy": dy}
        informe.append((n, f"k0={k0} ({len(dz)} f): altura relativa al estar de pie: min/max {min(dz):.3f}/{max(dz):.3f}, desplazamiento final {math.hypot(dx[-1], dy[-1]):.2f} m, max {max(math.hypot(a, b) for a, b in zip(dx, dy)):.2f} m"))
    if escribir:
        json.dump(out, open(os.path.join(HERE, "levantarse_correccion.json"), "w"), separators=(",", ":"))
    return informe
