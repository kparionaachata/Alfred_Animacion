"""ZOMBIES RONDANDO EL REFUGIO (pedido de Kebyn): mientras Alfred se asoma a mirar (f1094 en adelante) los 5 zombies que estan alrededor del refugio CONTINUAN CAMINANDO alrededor de el, en sentido antihorario visto desde arriba
(el lado este sube hacia el norte), asi que los del lado este -zombie_4 y zombie_5, a 1.6 m de la camara nueva (-91.623, -107.82, 14.847)- pasan por delante de ella.
Se ejecuta en Blender DESPUES de `sentarse_en_refugio.py` (no toca a Alfred / Jerry / la camara; los zombies no se regeneran con el script principal). Se puede ejecutar varias veces: la pose y la posicion de reposo se guardan la
primera vez en propiedades del objeto (`pose_estatica`, `pos_inicial`, `yaw_inicial`).
  - Camino: rectangulo redondeado (radio 0.9 m) que pasa por los 5 zombies tal como estan puestos: x -98.8..-93.2, y -111.86..-106.2. Cada uno arranca desde su sitio en f1094 (aceleracion de 10 f), gira hasta mirar hacia donde camina,
    y sigue hasta el final. Velocidad ~1.0 m/s (0.92-1.06 segun el zombie); paso de 1.5 m (el ciclo de las piernas va atado a la distancia recorrida: sin patinar).
  - Marcha de zombie (huesos de la rig: pierna X + = adelante, rodilla X - = flexion, brazo derecho Z -90 = al frente, el izquierdo +90): brazos al frente y un poco elevados, torso inclinado ~8 grados, piernas +-24 grados con rodilla
    flexionada al balancear, giro de cadera y contragiro de hombros, cabeza ladeada. La pose de reposo de cada zombie se mezcla con la marcha (f1090-1100).
  - Suelo: z de la hierba (`a.001`) en cada punto (hay un escalon de 1 m hacia abajo en la esquina suroeste que recorre zombie_2); zombie_5 estaba flotando 0.52 m: baja al suelo al arrancar."""
import bpy
import json
import math
from mathutils import Vector

sc = bpy.context.scene
F0, N = 1094, sc.frame_end
XW, XE, YS, YN, RAD = -98.8, -93.2, -111.86, -106.2, 0.9
STRIDE, A_LEG, V = 1.5, 24.0, {1: 0.96, 2: 1.0, 3: 0.92, 4: 1.06, 5: 1.0}
PH0 = {1: 0.0, 2: 2.1, 3: 4.0, 4: 1.0, 5: 3.1}
D = math.radians
ss = lambda t: (lambda u: u * u * (3 - 2 * u))(min(max(t, 0.0), 1.0))


def ring():
    pts = []; st = 0.05

    def line(a, b):
        L = (b - a).length; n = max(1, int(L / st))
        for i in range(n): pts.append(a.lerp(b, i / n))

    def arc(c, a0, a1):
        n = max(2, int(RAD * abs(a1 - a0) / st))
        for i in range(n): t = a0 + (a1 - a0) * i / n; pts.append(c + Vector((RAD * math.cos(t), RAD * math.sin(t))))
    r = RAD
    line(Vector((XW + r, YS)), Vector((XE - r, YS))); arc(Vector((XE - r, YS + r)), -math.pi / 2, 0)
    line(Vector((XE, YS + r)), Vector((XE, YN - r))); arc(Vector((XE - r, YN - r)), 0, math.pi / 2)
    line(Vector((XE - r, YN)), Vector((XW + r, YN))); arc(Vector((XW + r, YN - r)), math.pi / 2, math.pi)
    line(Vector((XW, YN - r)), Vector((XW, YS + r))); arc(Vector((XW + r, YS + r)), math.pi, 1.5 * math.pi)
    return pts


RING = ring(); NP = len(RING); STEP = 0.05
dg = bpy.context.evaluated_depsgraph_get()


def ground(x, y):
    o = Vector((x, y, 40.0)); d = Vector((0, 0, -1))
    for _ in range(12):
        ok, loc, nor, idx, ob, mat = sc.ray_cast(dg, o, d)
        if not ok: return 14.0
        if ob.name == "a.001": return loc.z
        o = loc + d * 0.01
    return 14.0


def at(s):
    s = s % (NP * STEP); i = s / STEP; i0 = int(i) % NP; i1 = (i0 + 1) % NP; p = RING[i0].lerp(RING[i1], i - int(i)); t = (RING[i1] - RING[i0]).normalized(); return p, t


for n in range(1, 6):
    R = bpy.data.objects["zombie_%d" % n]; A = bpy.data.objects["zombie_%d_Armature" % n]; P = A.pose.bones; sfx = "_zombie_%d" % n
    if "pose_estatica" not in A:
        A["pose_estatica"] = json.dumps({b.name: [list(b.rotation_euler), list(b.location)] for b in P}); R["pos_inicial"] = list(R.location); R["yaw_inicial"] = R.rotation_euler.z
    ST = json.loads(A["pose_estatica"]); p0 = Vector(R["pos_inicial"]); yaw0 = R["yaw_inicial"]; z0 = p0.z
    for ob in (R, A):
        if ob.animation_data and ob.animation_data.action: ob.animation_data.action = None
    for b in P: b.rotation_euler, b.location = ST[b.name]
    R.location = p0; R.rotation_euler = (0, 0, yaw0)
    s0 = min(range(NP), key=lambda i: (RING[i] - Vector((p0.x, p0.y))).length) * STEP
    ks = list(range(F0 - 4, N + 1)); dist = {}; d = 0.0
    for k in ks:
        dist[k] = d; d += V[n] / 24.0 * ss((k - F0) / 10.0)
    yp = {}; prev = None                                                                             # rumbo del camino, continuo
    for k in ks:
        _, t = at(s0 + dist[k]); y = math.atan2(-t.x, t.y)
        if prev is None: y += 2 * math.pi * round((yaw0 - y) / (2 * math.pi))
        else: y += 2 * math.pi * round((prev - y) / (2 * math.pi))
        yp[k] = prev = y
    zg = {}
    for k in ks: p, _ = at(s0 + dist[k]); zg[k] = ground(p.x, p.y)
    zs = {k: sum(zg[q] for q in range(max(ks[0], k - 3), min(ks[-1], k + 3) + 1)) / (min(ks[-1], k + 3) - max(ks[0], k - 3) + 1) for k in ks}
    for k in [1] + list(range(F0 - 4, N + 1)):
        if k == 1 or k == F0 - 4:
            for b in P: b.rotation_euler, b.location = ST[b.name]
            R.location = p0; R.rotation_euler = (0, 0, yaw0)
        else:
            wg = ss((k - F0 + 4) / 10.0); w_turn = ss((k - F0 + 2) / 12.0); ph = 2 * math.pi * dist[k] / STRIDE + PH0[n]; sn, cs = math.sin(ph), math.cos(ph)
            p, _ = at(s0 + dist[k]); pos = Vector((p0.x, p0.y)).lerp(p, ss((k - F0 + 3) / 4.0)) if k < F0 + 2 else p
            R.location = (pos.x, pos.y, z0 + (zs[k] - z0) * ss((k - F0 + 2) / 8.0)); R.rotation_euler = (0, 0, yaw0 * (1 - w_turn) + yp[k] * w_turn)
            G = {"RightUpLeg": (A_LEG * sn, 0, 0), "LeftUpLeg": (-A_LEG * sn, 0, 0), "Rightknee": (-4 - 38 * max(0.0, cs), 0, 0), "Leftknee": (-4 - 38 * max(0.0, -cs), 0, 0),
                 "RightUpArm": (-22 + 3 * cs, 0, -86 + 4 * sn), "LeftUpArm": (-22 - 3 * cs, 0, 86 - 4 * sn), "Rightelbow": (-6, 0, 0), "Leftelbow": (-6, 0, 0),
                 "Hips": (0, 0, 4 * sn), "Spine": (3 + 1.0 * math.sin(2 * ph), 0, -3 * sn), "Spine1": (3, 0, -2 * sn), "Spine2": (2, 0, -1 * sn), "Neck": (-6, 0, 3 * math.sin(ph + 1.0))}
            for b in P:
                nm = b.name.replace(sfx, ""); e0, l0 = ST[b.name]
                if nm in G: g = [D(a) for a in G[nm]]; b.rotation_euler = [e0[j] * (1 - wg) + g[j] * wg for j in range(3)]
                else: b.rotation_euler = e0
                if nm == "Hips": b.location = (l0[0], l0[1] + 0.02 * wg * math.cos(2 * ph), l0[2])
        R.keyframe_insert("location", frame=k); R.keyframe_insert("rotation_euler", frame=k)
        for b in P:
            b.keyframe_insert("rotation_euler", frame=k)
            if b.name.startswith("Hips"): b.keyframe_insert("location", frame=k)
    print("zombie_%d: s0=%.2f m, recorrido %.2f m, z final %.2f, pos final %s" % (n, s0, dist[N], R.location.z, [round(c, 2) for c in R.location]))
sc.frame_set(1)
