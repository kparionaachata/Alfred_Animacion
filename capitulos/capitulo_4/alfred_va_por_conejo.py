# -*- coding: utf-8 -*-
"""alfred_se_levanta_en_la_mañana_2: desde F0 Alfred se acerca lentamente al conejo por Desktop/alfred_recorrido_conejo.json.
Tramo 1 (caminar sigiloso): pies actuales -> P1 -> P2 (frente al bloque de 1 m).
Convenciones del rig (caminar_alfred_y_jerry.py): rz del empty `alfred` = rumbo - 92 grados; UpLeg X+ = muslo adelante;
rodilla X negativa = flexion; UpArm X+ = brazo atras."""
import bpy, json, math
from mathutils import Vector, Matrix, Euler

F0 = 580; V = 0.022; ZANCADA = 1.2
RUTA = r"C:\Users\user\Desktop\alfred_recorrido_conejo.json"
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
sc = bpy.context.scene
AA = bpy.data.objects["Armature"]; EA = AA.parent
KP = [Vector((k["coordinates"]["x"], k["coordinates"]["y"], k["coordinates"]["z"])) for k in json.load(open(RUTA, encoding="utf-8"))["key_points"]]


def bags(ob): return [cb for l in ob.animation_data.action.layers for s in l.strips for cb in s.channelbags]


def limpiar_despues(f0):
    for ob in (AA, EA):
        for cb in bags(ob):
            for fc in cb.fcurves:
                if "Mirar_" in fc.data_path: continue
                for k in [k for k in fc.keyframe_points if k.co.x > f0][::-1]: fc.keyframe_points.remove(k)
                fc.update()


def pies(f):
    sc.frame_set(f); pr = AA.matrix_world @ AA.pose.bones["Rightknee_alfred"].tail; pl = AA.matrix_world @ AA.pose.bones["Leftknee_alfred"].tail
    return Vector(((pr.x + pl.x) / 2, (pr.y + pl.y) / 2, 0))


def desenrollar(prev, x):
    while x - prev > math.pi: x -= 2 * math.pi
    while x - prev < -math.pi: x += 2 * math.pi
    return x


def caminar(f_ini, puntos, v=V, base=None):
    """camina de los pies actuales por `puntos` (xy). Devuelve frame final."""
    P_ini = pies(f_ini); loc0 = Vector(EA.location); rz0 = EA.rotation_euler.z; d0 = Vector((loc0.x - P_ini.x, loc0.y - P_ini.y, 0))
    base = base or {pb.name: Euler(tuple(pb.rotation_euler), 'XYZ') for pb in AA.pose.bones}
    hips0 = Vector(AA.pose.bones["Hips_alfred"].location)
    pts = [P_ini] + [Vector((p.x, p.y, 0)) for p in puntos]
    seg = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]; L = sum(seg)
    def en(s):
        for i, sl in enumerate(seg):
            if s <= sl or i == len(seg) - 1: return pts[i].lerp(pts[i + 1], min(1, s / sl)), (pts[i + 1] - pts[i])
            s -= sl
    s = 0.0; t = 0; phi = 0.0; rz_prev = rz0; f = f_ini; pasos = []
    while L - s > 0.004 and t < 2000:
        vv = v * min(1.0, (t + 1) / 8.0, max(0.08, (L - s) / (v * 8.0))); s = min(L, s + vv); t += 1; f = f_ini + t
        pos, d = en(s); th = math.atan2(d.y, d.x)
        rz_t = desenrollar(rz_prev, th - math.radians(92.0)); rz = rz_prev + (rz_t - rz_prev) * 0.25; rz_prev = rz
        EA.location = Vector((pos.x, pos.y, 0)) + (Matrix.Rotation(rz - rz0, 3, 'Z') @ d0) + Vector((0, 0, loc0.z)); EA.rotation_euler = (0, 0, rz)
        EA.keyframe_insert("location", frame=f); EA.keyframe_insert("rotation_euler", frame=f)
        env = min(1.0, vv / v); fase_prev = phi; phi += 2 * math.pi * vv / ZANCADA; sn = math.sin(phi); cs = math.cos(phi)
        for b, sg in (("RightUpLeg_alfred", +1), ("LeftUpLeg_alfred", -1)):
            e = Euler(tuple(base[b])); e.x += sg * math.radians(22) * sn * env; AA.pose.bones[b].rotation_euler = e; AA.pose.bones[b].keyframe_insert("rotation_euler", frame=f)
        for b, sg in (("Rightknee_alfred", +1), ("Leftknee_alfred", -1)):
            e = Euler(tuple(base[b])); e.x += -(math.radians(8) + math.radians(34) * max(0.0, sg * cs) ** 1.3) * env; AA.pose.bones[b].rotation_euler = e; AA.pose.bones[b].keyframe_insert("rotation_euler", frame=f)
        pbH = AA.pose.bones["Hips_alfred"]; pbH.location = hips0 + Vector((0, -0.02 * env * (1 - math.cos(2 * phi)) / 2, 0)); pbH.keyframe_insert("location", frame=f)
        if int(phi / math.pi - 0.5) != int(fase_prev / math.pi - 0.5) and phi > 0.5 * math.pi: pasos.append(f)
    return f, pasos


def kb(b, f, x=None, y=None, z=None, base=None):
    """clave de rotacion euler (grados absolutos) del hueso b; ejes None = valor base"""
    pb = AA.pose.bones[b]; e = Euler(tuple(base[b])) if base else Euler(tuple(pb.rotation_euler))
    for i, v in enumerate((x, y, z)):
        if v is not None: e[i] = math.radians(v)
    pb.rotation_euler = e; pb.keyframe_insert("rotation_euler", frame=f)


def kroot(f, loc, rx, rz):
    EA.location = loc; EA.rotation_euler = (math.radians(rx), 0, math.radians(rz))
    EA.keyframe_insert("location", frame=f); EA.keyframe_insert("rotation_euler", frame=f)


def trepar_arrastrar_saltar(C):
    """C = frame en que llega frente al bloque. Devuelve dict de frames clave."""
    sc.frame_set(C); base = {pb.name: Euler(tuple(pb.rotation_euler)) for pb in AA.pose.bones}
    L0 = Vector(EA.location); z0 = L0.z; zt = z0 + 1.0
    P3, P4, P5, P6 = KP[2], KP[3], KP[4], KP[5]
    ofs = Vector((0.369, 0.0885, 0))                                                # empty respecto a los pies (de pie, rz=0)
    def at(p, dz=0.0): return Vector((p.x, p.y, 0)) + ofs + Vector((0, 0, zt + dz))
    rz_up = -2.0; rz_j = math.degrees(math.atan2(P6.y - P5.y, P6.x - P5.x)) - 92.0
    edge = Vector((L0.x, KP[1].y + 0.55, 0))                                        # borde del bloque (y = -18.0)
    # ---------------- trepar ----------------
    kroot(C, L0, 0, rz_up)
    kroot(C + 6, L0 + Vector((0, 0.10, -0.12)), -10, rz_up)                       # se agacha y toma impulso
    kroot(C + 12, Vector((L0.x, KP[1].y + 0.20, z0 + 0.55)), -25, rz_up)            # salta y apoya manos arriba
    kroot(C + 20, Vector((L0.x, KP[1].y + 0.45, z0 + 0.95)), -55, rz_up)            # se impulsa con los brazos, pecho sobre el bloque
    kroot(C + 28, Vector((L0.x, KP[1].y + 0.75, zt + 0.12)), -84, rz_up)            # queda tendido boca abajo
    for b in ("RightUpArm_alfred", "LeftUpArm_alfred"):
        kb(b, C, base=base); kb(b, C + 6, x=-40, base=base); kb(b, C + 12, x=-70, base=base); kb(b, C + 20, x=20, base=base); kb(b, C + 28, x=-80, base=base)
    for b in ("Rightelbow_alfred", "Leftelbow_alfred"):
        kb(b, C, base=base); kb(b, C + 6, x=20, base=base); kb(b, C + 12, x=10, base=base); kb(b, C + 20, x=60, base=base); kb(b, C + 28, x=30, base=base)
    for b, d in (("RightUpLeg_alfred", 0), ("LeftUpLeg_alfred", 1)):
        kb(b, C, base=base); kb(b, C + 6, x=35, base=base); kb(b, C + 12, x=10 + 20 * d, base=base); kb(b, C + 20, x=50 * (1 - d) + 5, base=base); kb(b, C + 28, x=0, y=0, z=0, base=base)
    for b in ("Rightknee_alfred", "Leftknee_alfred"):
        kb(b, C, base=base); kb(b, C + 6, x=-60, base=base); kb(b, C + 12, x=-20, base=base); kb(b, C + 20, x=-70, base=base); kb(b, C + 28, x=-10, base=base)
    for b in ("Spine1_alfred", "Spine2_alfred"):
        kb(b, C, base=base); kb(b, C + 6, x=15, base=base); kb(b, C + 20, x=20, base=base); kb(b, C + 28, x=0, y=0, z=0, base=base)
    for b in ("Hips_alfred", "Spine_alfred"):
        kb(b, C, base=base); kb(b, C + 28, x=base[b].x * 57.2958 * 0 + 0, y=0, z=0, base=base) if b == "Spine_alfred" else (kb(b, C, base=base), kb(b, C + 28, base=base))
    kb("Neck_alfred", C, base=base); kb("Neck_alfred", C + 28, x=-35, base=base)
    # ---------------- arrastrarse P3 -> P5 ----------------
    A0 = C + 28; A1 = A0 + 60; n = 4
    for i in range(0, 61, 3):
        f = A0 + i; t = i / 60.0; tt = ss(t)
        y = (KP[1].y + 0.75) + (P5.y - (KP[1].y + 0.75)) * (t + 0.03 * math.sin(2 * math.pi * n * t))
        kroot(f, Vector((L0.x + (P5.x - L0.x) * 0 , y, zt + 0.12 + 0.02 * abs(math.sin(math.pi * n * t)))), -84, rz_up)
        ph = 2 * math.pi * n * t
        kb("RightUpArm_alfred", f, x=-80 - 30 * math.sin(ph), base=base); kb("LeftUpArm_alfred", f, x=-80 + 30 * math.sin(ph), base=base)
        kb("Rightelbow_alfred", f, x=30 + 30 * max(0, math.cos(ph)), base=base); kb("Leftelbow_alfred", f, x=30 + 30 * max(0, -math.cos(ph)), base=base)
        kb("RightUpLeg_alfred", f, x=-15 * math.sin(ph), y=0, z=0, base=base); kb("LeftUpLeg_alfred", f, x=15 * math.sin(ph), y=0, z=0, base=base)
        kb("Rightknee_alfred", f, x=-10 - 40 * max(0, -math.sin(ph)), base=base); kb("Leftknee_alfred", f, x=-10 - 40 * max(0, math.sin(ph)), base=base)
        kb("Spine1_alfred", f, x=0, y=6 * math.sin(ph), z=0, base=base)
    # ---------------- saltar P5 -> P6 ----------------
    J0 = A1; pS = Vector((L0.x, P5.y, 0)); pE = Vector((P6.x, P6.y, 0)) + ofs * 0.0
    kroot(J0 + 6, Vector((pS.x, pS.y - 0.1, zt + 0.10)), -60, rz_up)                # se encoge (agazapado)
    kroot(J0 + 10, Vector((pS.x, pS.y - 0.15, zt + 0.05)), -55, rz_j)               # gira hacia el conejo
    for i in range(0, 13):
        t = i / 12.0; p = pS.lerp(pE, t)
        kroot(J0 + 10 + i, Vector((p.x, p.y, zt + 0.10 + 0.7 * 4 * t * (1 - t))), -55 - 30 * t, rz_j)
    kroot(J0 + 25, Vector((pE.x, pE.y, zt + 0.12)), -86, rz_j)
    kb("RightUpArm_alfred", J0 + 6, x=10, base=base); kb("LeftUpArm_alfred", J0 + 6, x=10, base=base)
    kb("RightUpArm_alfred", J0 + 14, x=-110, base=base); kb("LeftUpArm_alfred", J0 + 14, x=-110, base=base)
    kb("RightUpArm_alfred", J0 + 25, x=-95, base=base); kb("LeftUpArm_alfred", J0 + 25, x=-95, base=base)
    for b in ("Rightelbow_alfred", "Leftelbow_alfred"):
        kb(b, J0 + 6, x=80, base=base); kb(b, J0 + 14, x=5, base=base); kb(b, J0 + 25, x=25, base=base)
    for b in ("RightUpLeg_alfred", "LeftUpLeg_alfred"):
        kb(b, J0 + 6, x=70, y=0, z=0, base=base); kb(b, J0 + 14, x=-10, y=0, z=0, base=base); kb(b, J0 + 25, x=0, y=0, z=0, base=base)
    for b in ("Rightknee_alfred", "Leftknee_alfred"):
        kb(b, J0 + 6, x=-90, base=base); kb(b, J0 + 14, x=-5, base=base); kb(b, J0 + 25, x=-15, base=base)
    kb("Neck_alfred", J0 + 6, x=-40, base=base); kb("Neck_alfred", J0 + 25, x=-30, base=base)
    return {"trepa": (C, A0), "arrastra": (A0, A1), "salto": (J0, J0 + 25)}
