# -*- coding: utf-8 -*-
"""Parte 11: mientras la paloma le roba el pan a Alfred y lo lanza al mar, JERRY (junto a la fogata) NO lo mira: solo se ocupa de su
comida (la mira, la huele y la mueve). (Version anterior: miraba a Alfred; el usuario lo cambio.)
Guion (de `p11_tiempos` pan_*):
  - cuando entra la paloma, gira el cuerpo y la cabeza hacia Alfred y mira el forcejeo;
  - vuelve a la fogata y empuja su pescado con el hocico dos veces (el pescado se mueve un poco en cada empujon);
  - cuando la paloma gana y Alfred sale volando al mar, levanta la cabeza y lo mira caer;
  - vuelve a acomodar el pescado y se queda mirando su comida.
Se SUMA a la accion de jerry_nada_pescado_parte11.py (y a la de voz_jerry_anda_ve) guardando lo sumado: al repetir se deshace y se rehace.
Los ejes de la cabeza se MIDEN (que eje de scull lleva el hocico hacia un lado / hacia abajo)."""
import bpy, math
from mathutils import Vector, Matrix

MARCA = "jerry_observa_acomoda"; PEZ = "pescado_fogata_jerry"


def _sstep(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


def _env(f, a, b, ent, sal): return _sstep((f - a) / float(ent)) * (1 - _sstep((f - b) / float(sal)))


def _curvas(idb):
    a = idb.animation_data.action
    return {(fc.data_path, fc.array_index): fc for l in a.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves}


def _mover(fc, f, d):
    k = fc.keyframe_points[f - 1]
    if int(round(k.co.x)) != f: raise RuntimeError("clave inesperada %s %d" % (fc.data_path, f))
    k.co.y += d; k.handle_left.y += d; k.handle_right.y += d


def _deshacer(idb):
    a = idb.animation_data.action; dd = a.get(MARCA + "_deltas")
    if dd:
        cv = _curvas(idb)
        for clave, v in dd.to_dict().items():
            ruta, idx = clave.rsplit("|", 1)
            for j, x in enumerate(v["vals"]): _mover(cv[(ruta, int(idx))], v["ini"] + j, -x)
        for fc in cv.values(): fc.update()
        del a[MARCA + "_deltas"]


def construir():
    sc = bpy.context.scene; T = sc["p11_tiempos"]
    arm = bpy.data.objects["Dog_001_rig"]; root = bpy.data.objects["jerry_sin_armadura"]; P = arm.pose.bones
    for idb in (arm, root): _deshacer(idb)
    E, LL, GA, CAE = int(T["pan_entra"]), int(T["pan_llega"]), int(T["pan_gana"]), int(T["pan_cae"])
    FIN = sc.frame_end

    # ejes medidos de la cabeza: hocico (punta de jaw_top) hacia la izquierda de Jerry y hacia abajo
    sc.frame_set(E); bpy.context.view_layer.update()
    hocico = lambda: arm.matrix_world @ P["jaw_top"].tail
    adelante = (hocico() - arm.matrix_world @ P["scull"].head); adelante.z = 0; adelante.normalize()
    izq = Vector((0, 0, 1)).cross(adelante)

    def eje(hueso, direccion):
        mejor = None; base = P[hueso].rotation_euler.copy()
        for i in range(3):
            p0 = hocico(); e = base.copy(); e[i] += 0.2; P[hueso].rotation_euler = e; bpy.context.view_layer.update()
            d = (hocico() - p0).dot(direccion); P[hueso].rotation_euler = base; bpy.context.view_layer.update()
            if mejor is None or abs(d) > abs(mejor[1]): mejor = (i, d)
        return mejor[0], (1.0 if mejor[1] > 0 else -1.0)
    GIRO_CAB = eje("scull", izq); BAJA_CAB = eje("scull", Vector((0, 0, -1))); BAJA_CUELLO = eje("spine_1", Vector((0, 0, -1)))
    sc.frame_set(1)

    # hacia donde esta Alfred visto desde Jerry (yaw del root); el cuerpo gira parte y la cabeza el resto
    fyaw = _curvas(root)[("rotation_euler", 2)]
    alf = bpy.data.objects["alfred"].matrix_world.translation; jp = root.matrix_world.translation
    sc.frame_set(E); jp = root.matrix_world.translation.copy(); sc.frame_set(1)
    d = Vector((alf.x - jp.x, alf.y - jp.y)); yaw_alf = math.atan2(-d.x, d.y)
    yaw_fog = fyaw.evaluate(E)
    giro_total = (yaw_alf - yaw_fog + math.pi) % (2 * math.pi) - math.pi
    G_CUERPO = giro_total * 0.55; G_CABEZA = abs(giro_total) * 0.45     # la cabeza gira hacia el mismo lado (medido: izq = +)
    lado = 1.0 if giro_total > 0 else -1.0

    # tramos: NO mira a Alfred (pedido del usuario): solo se ocupa de su comida -> la MIRA, la HUELE y la MUEVE
    OLER = [E + 8, LL + 22, GA + 6, CAE + 36]        # rafagas de olfateo (12 frames: hocico arriba-abajo rapido)
    EMP = [LL + 4, LL + 46]                          # empujones al pescado (hocico)
    EMP2 = [GA + 28, CAE + 54]                       # lo vuelve a acomodar
    PATAS = [(E + 26, "R"), (LL + 30, "L"), (GA + 12, "R"), (CAE + 40, "L")]   # tambien lo mueve con las PATAS delanteras (alterna)
    rango = list(range(E, FIN + 1))
    cv_a = _curvas(arm); dr = {"rotation_euler|2": []}; da = {}

    def suma(ruta, i, f, v):
        da.setdefault("%s|%d" % (ruta, i), [0.0] * len(rango))[f - rango[0]] += v

    for f in rango:
        dr["rotation_euler|2"].append(0.0)                                                     # el cuerpo no gira
        sb = 'pose.bones["%s"].rotation_euler'
        # la MIRA: la cabeza recorre el pescado despacio de un lado al otro y se acerca/aleja un poco
        i, s = GIRO_CAB; suma(sb % "scull", i, f, s * 0.12 * math.sin(f / 21.0))
        i, s = BAJA_CAB; suma(sb % "scull", i, f, s * 0.05 * math.sin(f / 33.0 + 1.0))
        # la HUELE: rafagas cortas, el hocico sube y baja rapido y la nariz (jaw_top) tiembla
        olf = 0.0
        for o0 in OLER: olf = max(olf, _env(f, o0, o0 + 12, 3, 4))
        i, s = BAJA_CAB; suma(sb % "scull", i, f, s * (0.10 * olf + 0.05 * olf * math.sin(f * 2.1)))
        suma(sb % "jaw_top", 0, f, -0.06 * olf * abs(math.sin(f * 2.4)))
        # la MUEVE: empujones con el hocico
        emp = 0.0
        for e0 in EMP + EMP2:
            x = f - e0
            if -6 <= x <= 10: emp = max(emp, _sstep((x + 6) / 6.0) if x < 0 else (1 - _sstep(x / 10.0)))
        i, s = BAJA_CAB; suma(sb % "scull", i, f, s * 0.35 * emp)
        i, s = BAJA_CUELLO; suma(sb % "spine_1", i, f, s * 0.25 * emp)
        for b in ("tail_1", "tail_2"):                                                          # contento con su comida: mueve la cola
            suma(sb % b, 1, f, 0.18 * math.sin(f / 3.5) * max(emp, olf, 0.35))
    # patas: en cada toque la pata delantera se estira hasta el pescado (calculado en el mundo), lo arrastra un poco hacia si y vuelve
    pez0 = bpy.data.objects.get(PEZ)
    for pico, l in PATAS:
        hombro, punta = "front_shoulder." + l, "front_toe." + l
        sc.frame_set(pico); bpy.context.view_layer.update()
        a = arm.matrix_world @ P[hombro].head; b = arm.matrix_world @ P[punta].tail
        obj = pez0.matrix_world.translation + Vector((0, 0, 0.04)) if pez0 else b
        q = (b - a).normalized().rotation_difference((obj - a).normalized())
        R = Matrix.Translation(a) @ q.to_matrix().to_4x4() @ Matrix.Translation(-a)
        nuevo = arm.matrix_world.inverted() @ R @ arm.matrix_world @ P[hombro].matrix
        e_cur = P[hombro].rotation_euler.copy(); e_new = arm.convert_space(pose_bone=P[hombro], matrix=nuevo, from_space='POSE', to_space='LOCAL').to_euler('XYZ', e_cur)
        dlt = [e_new[i] - e_cur[i] for i in range(3)]
        largo = (b - a).length; alcance = (obj - a).length                                   # si no llega, estira un poco la "mano"
        for f in range(pico - 8, pico + 14):
            if f < rango[0] or f > rango[-1]: continue
            x = f - pico
            w = _sstep((x + 8) / 8.0) if x < 0 else (1.0 if x < 4 else 1 - _sstep((x - 4) / 10.0))
            arrastre = 0.18 * _sstep((x - 0) / 4.0) * (1 - _sstep((x - 4) / 10.0)) if x >= 0 else 0.0   # tira el pescado hacia si
            for i in range(3): suma('pose.bones["%s"].rotation_euler' % hombro, i, f, dlt[i] * w)
            suma('pose.bones["%s"].rotation_euler' % ("front_shin." + l), 0, f, -arrastre)
            i_, s_ = BAJA_CAB; suma('pose.bones["scull"].rotation_euler', i_, f, s_ * 0.15 * w)        # mira lo que hace con la pata
    sc.frame_set(1)
    for clave, vals in da.items():
        r, i = clave.rsplit("|", 1); fc = cv_a.get((r, int(i)))
        if fc is None: continue
        for j, v in enumerate(vals): _mover(fc, rango[j], v)
    cv_r = _curvas(root)
    for j, v in enumerate(dr["rotation_euler|2"]): _mover(cv_r[("rotation_euler", 2)], rango[j], v)
    for fc in list(cv_a.values()) + list(cv_r.values()): fc.update()
    arm.animation_data.action[MARCA + "_deltas"] = {k: {"ini": rango[0], "vals": v} for k, v in da.items() if ("pose" in k)}
    root.animation_data.action[MARCA + "_deltas"] = {k: {"ini": rango[0], "vals": v} for k, v in dr.items()}

    # el pescado se mueve un poco con cada empujon (gira y se corre unos cm)
    pez = bpy.data.objects.get(PEZ)
    if pez and pez.animation_data and pez.animation_data.action:
        cvp = _curvas(pez)
        for (ruta, i), fc in cvp.items():
            if ruta in ("location", "rotation_euler"):
                for k in reversed(range(len(fc.keyframe_points))):
                    if fc.keyframe_points[k].co.x >= E: fc.keyframe_points.remove(fc.keyframe_points[k], fast=True)
                fc.update()
        sc.frame_set(E - 1); loc0 = pez.location.copy(); rot0 = pez.rotation_euler.copy()
        acum_l = Vector(); acum_r = 0.0
        for n, e0 in enumerate(sorted(EMP + EMP2 + [pk for pk, _l in PATAS])):
            pez.location = loc0 + acum_l; pez.rotation_euler = rot0.copy(); pez.rotation_euler.z += acum_r
            pez.keyframe_insert("location", frame=e0 - 1); pez.keyframe_insert("rotation_euler", frame=e0 - 1)
            acum_l += Vector((0.025 * (-1) ** n, 0.02, 0.0)); acum_r += math.radians(9 * (-1) ** (n + 1))
            pez.location = loc0 + acum_l; pez.rotation_euler = rot0.copy(); pez.rotation_euler.z += acum_r
            pez.keyframe_insert("location", frame=e0 + 4); pez.keyframe_insert("rotation_euler", frame=e0 + 4)
        sc.frame_set(1)
    sc["p11_jerry_observa"] = {"olfatea": OLER, "empujones": EMP + EMP2, "patas": [pk for pk, _l in PATAS]}
    print("JERRY observa y acomoda:", dict(sc["p11_jerry_observa"]))


if __name__ in ("__main__", "x"):
    construir()
