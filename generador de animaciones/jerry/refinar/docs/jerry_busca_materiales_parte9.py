# -*- coding: utf-8 -*-
"""Parte 9: mientras a Alfred le pasa todo (pan, flechas, caida), Jerry sigue de pie en (-131.5, -71.32, 10) mirando la cueva (rz 90, hacia -x) BUSCANDO MATERIALES:
recorre la cueva con la cabeza de lado a lado y de arriba a abajo (`spine_2` Z = su lado, + a su derecha; X + = mira abajo), con pausas como si encontrara algo,
acompanado por `spine_1` (x0.35) y filtros organicos (respiracion `spine_1`, orejas, cola). Accion `p9_jerry_armature`, f1-FIN. Base del primer uso en `scene["jerry_p9_base"]` (repetible)."""
import bpy, math, random
from mathutils import Euler

FIN = 700
sc = bpy.context.scene; A = bpy.data.objects["Dog_001_rig"]
CAN = ("spine_1", "spine_2", "ear.L", "ear.R", "tail_2")
PATA = {"front_shoulder.R": (40.0, 30.0, -30.0), "front_thigh.R": (0.0, 0.0, 0.0), "front_shin.R": (20.0, 0.0, 0.0), "front_foot.R": (10.0, 0.0, 0.0)}   # PUNO a MEDIA altura (pie z 10.41: mitad entre de pie 10.14 y el anterior 10.68), 0.30 a su derecha y lejos del hocico (0.30)
PATA_L = {"front_shoulder.L": (100.0, 30.0, 30.0), "front_thigh.L": (0.0, 0.0, 0.0), "front_shin.L": (90.0, 0.0, 0.0), "front_foot.L": (20.0, 0.0, 0.0)}  # pata izquierda al sombrero (pie 0.13 sobre su centro)
if "jerry_p9_base_pataL" not in sc: sc["jerry_p9_base_pataL"] = {n: list(A.pose.bones[n].rotation_euler) for n in PATA_L}
BASEL = {n: list(sc["jerry_p9_base_pataL"][n]) for n in PATA_L}
T_SUBE = 416; T_AGARRA = 426; T_SUELO = 438; T_PUNO = 444                                # se quita el sombrero (f416-438) y lo deja en el suelo ANTES de levantar el puno
if "jerry_p9_base" not in sc: sc["jerry_p9_base"] = {n: list(A.pose.bones[n].rotation_euler) for n in CAN}
if "jerry_p9_base_pata" not in sc: sc["jerry_p9_base_pata"] = {n: list(A.pose.bones[n].rotation_euler) for n in PATA}
BASEP = {n: list(sc["jerry_p9_base_pata"][n]) for n in PATA}
# f410 una flecha se clava en la piedra a su DERECHA: reacciona rapido (respingo, orejas atras) y MIRA HACIA ABAJO (a Alfred / el esqueleto); levanta el puno y dice
# "Que cosa? ..." (voz desde VOZ = 414, habla hasta ~f503); baja la pata y vuelve a buscar materiales
H = 410; VOZ = 414; FIN_VOZ = 505
BASE = {n: list(sc["jerry_p9_base"][n]) for n in CAN}
old = bpy.data.actions.get("p9_jerry_armature")
if old: bpy.data.actions.remove(old)
A.animation_data_create(); A.animation_data.action = None
# (frame, Z lado, X abajo) relativos a la base: mira de lado a lado, se asoma abajo, se detiene a inspeccionar
RUTA = [(1, 0, 0), (20, 0, 0), (45, 0.45, 0.05), (75, 0.45, 0.05), (95, 0.35, 0.30), (130, 0.35, 0.30), (150, 0, 0.10), (175, -0.45, 0.05), (210, -0.45, 0.05),
        (230, -0.35, 0.32), (265, -0.35, 0.32), (285, -0.10, 0.0), (310, 0.20, -0.10), (345, 0.20, -0.10), (365, 0.50, 0.15), (400, 0.50, 0.15), (420, 0.15, 0.35),
        (455, 0.15, 0.35), (475, -0.30, 0.10), (510, -0.30, 0.10), (530, -0.50, 0.25), (565, -0.50, 0.25), (590, 0, 0.05), (625, 0.30, 0.20), (660, 0.30, 0.20), (700, 0, 0.05)]
ss = lambda t: t * t * (3 - 2 * t)
def mirada(f):
    for (f0, z0, x0), (f1, z1, x1) in zip(RUTA, RUTA[1:]):
        if f0 <= f <= f1: t = ss((f - f0) / (f1 - f0)); return z0 + (z1 - z0) * t, x0 + (x1 - x0) * t
    return RUTA[-1][1], RUTA[-1][2]
rng = random.Random(42); fn = [rng.uniform(0, 6.28) for _ in range(6)]
def reac(f):
    """peso de la reaccion (cabeza abajo) y de la pata arriba"""
    if f < H: return 0.0, 0.0, 0.0
    w = ss(min(1.0, (f - H) / 4.0)) if f < FIN_VOZ + 8 else 1.0 - ss(min(1.0, (f - FIN_VOZ - 8) / 14.0))
    pw = 0.0 if f < T_PUNO else (ss(min(1.0, (f - T_PUNO) / 7.0)) if f < FIN_VOZ else 1.0 - ss(min(1.0, (f - FIN_VOZ) / 10.0)))
    pl = 0.0 if f < T_SUBE or f > T_SUELO else (ss((f - T_SUBE) / (T_AGARRA - 1 - T_SUBE)) if f < T_AGARRA - 1 else (1.0 if f <= T_AGARRA + 2 else 1.0 - ss((f - T_AGARRA - 2) / (T_SUELO - T_AGARRA - 2))))
    return w, pw, pl
for f in range(1, FIN + 1):
    z, x = mirada(f); w, pw, pl = reac(f)
    for n, dg in PATA_L.items():
        b = A.pose.bones[n]; b.rotation_euler = Euler([BASEL[n][i] + math.radians(dg[i]) * pl for i in range(3)], 'XYZ'); b.keyframe_insert("rotation_euler", frame=f, group=n)
    respingo = 0.12 * math.exp(-(f - H) / 3.0) if f >= H else 0.0
    z = z * (1 - w) + 0.15 * w; x = x * (1 - w) + 0.55 * w + respingo
    for n, dg in PATA.items():
        b = A.pose.bones[n]; sac = math.radians(7) * math.sin((f - VOZ) * 0.9) * pw if n == "front_shoulder.R" else 0.0      # sacude el puno mientras habla
        b.rotation_euler = Euler([BASEP[n][i] + math.radians(dg[i]) * pw + (sac if i == 0 else 0) for i in range(3)], 'XYZ'); b.keyframe_insert("rotation_euler", frame=f, group=n)
    nz = 0.03 * math.sin(f * 0.11 + fn[0]) + 0.015 * math.sin(f * 0.27 + fn[1]); nx = 0.025 * math.sin(f * 0.09 + fn[2])     # micro-movimiento: no queda congelado
    resp = 0.05 * math.sin(f * 2 * math.pi * 0.01 * 4)                                         # respiracion
    v = {"spine_2": (BASE["spine_2"][0] + x + nx, BASE["spine_2"][1], BASE["spine_2"][2] + z + nz),
         "spine_1": (BASE["spine_1"][0] + 0.35 * x + resp * 0.3, BASE["spine_1"][1], BASE["spine_1"][2] + 0.35 * z + resp * 0.2),
         "ear.L": (BASE["ear.L"][0] - 0.35 * w, BASE["ear.L"][1], BASE["ear.L"][2] + 0.12 * math.sin(f * 0.06)),
         "ear.R": (BASE["ear.R"][0] - 0.35 * w, BASE["ear.R"][1], BASE["ear.R"][2] + 0.12 * math.sin(f * 0.06 + 1.57)),
         "tail_2": (BASE["tail_2"][0], BASE["tail_2"][1], BASE["tail_2"][2] + 0.183 * math.sin(f * 0.12))}
    for n, e in v.items():
        b = A.pose.bones[n]; b.rotation_euler = Euler(e, 'XYZ'); b.keyframe_insert("rotation_euler", frame=f, group=n)
LIMPIO = {"jaw_bot": ((0, 0, 0), (0, 0, 0), (1, 1, 1)), "jaw_top": ((0, 0, 0), (0, 0, 0), (1, 1, 1)), "scull": ((0, 0, 0), (0, 0, 0), (1, 1, 1)), "scull_1": ((0, 0, 0), (0, 0, 0), (1, 1, 1)),
          "sejas_1_jerry": ((0, 0, 0), (0.006569, 0.000489, -0.000191), (1, 1, 1)), "sejas_2_jerry": ((0, 0, 0), (0.013395, -0.000836, 0.003522), (1, 1, 1))}
for n, (r_, l_, s_) in LIMPIO.items():                                                      # cara en REPOSO (la mandibula quedaba abierta: valores sueltos de voces anteriores); la voz se suma despues sobre esto
    b = A.pose.bones[n]; b.rotation_mode = 'XYZ'; b.rotation_euler = r_; b.location = l_; b.scale = s_
    for dp in ("rotation_euler", "location", "scale"): b.keyframe_insert(dp, frame=1, group=n)
A.animation_data.action.name = "p9_jerry_armature"
# ---------- el SOMBRERO: el original (con piel) se oculta en T_AGARRA; una copia rigida `sombrero_jerry_libre` sigue a la pata y queda derecha en el suelo ----------
from mathutils import Matrix, Vector
SOM = bpy.data.objects["sombrero_jerry"]; LIB = bpy.data.objects["sombrero_jerry_libre"]; SPOT = Vector((-131.85, -71.76))   # suelo (z 10) junto a su pata izquierda, delante
def BW(n): return A.matrix_world @ A.pose.bones[n].matrix
sc.frame_set(1); R1 = BW("sombrero").to_quaternion()
sc.frame_set(T_AGARRA); dg_ = bpy.context.evaluated_depsgraph_get(); ev = SOM.evaluated_get(dg_)
me_n = bpy.data.meshes.new_from_object(ev); me_n.transform(SOM.matrix_world); old_me = LIB.data; LIB.data = me_n
for m_ in SOM.data.materials:
    if m_ and m_.name not in [x.name for x in me_n.materials if x]: pass
if old_me.users == 0: bpy.data.meshes.remove(old_me)
me_n.name = "sombrero_jerry_libre"; LIB.animation_data_clear(); LIB.parent = None; LIB.rotation_mode = 'QUATERNION'; LIB.matrix_world = Matrix.Identity(4)
P0 = BW("front_foot.L"); RG = BW("sombrero").to_quaternion()
cen = sum((v.co for v in me_n.vertices), Vector()) / len(me_n.vertices)
Rfin = (R1 @ RG.inverted()).to_matrix().to_4x4()                                              # deshace la inclinacion de la cabeza: queda derecho
zmin = min((Rfin @ (v.co - cen)).z for v in me_n.vertices)
MFIN = Matrix.Translation(Vector((SPOT.x, SPOT.y, 10.0 - zmin))) @ Rfin @ Matrix.Translation(-cen)
for f in range(T_AGARRA, T_SUELO + 5):
    sc.frame_set(f); Mf = BW("front_foot.L") @ P0.inverted(); t = ss(min(1.0, (f - T_AGARRA) / (T_SUELO - T_AGARRA)))
    qa = Mf.to_quaternion(); qb = MFIN.to_quaternion(); ca = Mf @ cen; cb = MFIN @ cen             # se interpola el CENTRO del sombrero (no la traslacion de la matriz)
    c_ = ca.lerp(cb, t); q_ = qa.slerp(qb, t); M_ = Matrix.Translation(c_) @ q_.to_matrix().to_4x4() @ Matrix.Translation(-cen)
    LIB.matrix_world = M_
    for dp in ("location", "rotation_quaternion", "scale"): LIB.keyframe_insert(dp, frame=f)
for o_, vis in ((SOM, (0, 1)), (LIB, (1, 0))):                                              # (hide antes, hide desde T_AGARRA)
    o_.animation_data_create()
    for dp in ("hide_viewport", "hide_render"):
        if o_.animation_data.action:
            for fc in [c for c in o_.animation_data.action.fcurves if c.data_path == dp] if hasattr(o_.animation_data.action, "fcurves") else []: o_.animation_data.action.fcurves.remove(fc)
        setattr(o_, dp, bool(vis[0])); o_.keyframe_insert(dp, frame=1); o_.keyframe_insert(dp, frame=T_AGARRA - 1)
        setattr(o_, dp, bool(vis[1])); o_.keyframe_insert(dp, frame=T_AGARRA)
print("JERRY BUSCA MATERIALES: f1-%d, %d puntos de mirada" % (FIN, len(RUTA)))
