# -*- coding: utf-8 -*-
"""Parte 11: la PALOMA (estructura_lista/paloma_1.blend) entra volando justo cuando Alfred levanta su pan, lo muerde con el pico, tiran
de un lado al otro y al final ELLA se lo queda y se va volando sobre el mar (Alfred, sentado, la sigue con la mirada).
La trayectoria del pan (forcejeo y huida) la decide alfred_saca_flechas_parte11.py (tramo PAN, `p11_tiempos` pan_*): aqui la paloma
pone el PICO en el pan frame a frame. Llega desde el mar (descendiendo), aletea rapido mientras tira (cuerpo hacia atras, cabeza tirando),
y huye con el pan en el pico. Rig: pigeon_1 (EMPTY) -> body_paloma_1 (7 huesos, cuaterniones) -> Mesh_0_paloma_1. Mira a +Y; las alas
aletean en su eje Z local (izquierda +, derecha -). Repetible: rehace su propia animacion."""
import bpy, math
from mathutils import Vector, Quaternion, Matrix, Euler

BLEND = r"C:\Users\user\Desktop\Alfred_Animacion\estructura_lista\paloma_1.blend"
COL = "paloma_1_p11"; ROOT = "pigeon_1"; ARM = "body_paloma_1"
ESCALA = 0.7                                  # paloma de Minecraft junto a Alfred
VUELO_LLEGADA = 40                            # frames que tarda en llegar
DESDE = Vector((7.0, -4.0, 4.5))              # de donde viene, relativo al pan (sobre el mar, alto)
ALETEO = 3.5                                  # frames por aleteo (MAS aleteos, pedido del usuario)


def _sstep(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


def preparar():
    sc = bpy.context.scene; col = bpy.data.collections.get(COL)
    if col is None:
        col = bpy.data.collections.new(COL); sc.collection.children.link(col)
        with bpy.data.libraries.load(BLEND, link=False) as (src, dst): dst.objects = list(src.objects)
        for o in dst.objects:
            if o: col.objects.link(o)
    return bpy.data.objects[ROOT], bpy.data.objects[ARM]


def construir():
    sc = bpy.context.scene; T = sc["p11_tiempos"]; root, arm = preparar(); P = arm.pose.bones
    for idb in [root] + list(root.children_recursive):                # sin animacion y VISIBLE para medir (oculta no se evalua)
        ad = idb.animation_data
        if ad and ad.action:
            a = ad.action; ad.action = None
            if a.users == 0: bpy.data.actions.remove(a)
        idb.hide_viewport = False; idb.hide_render = False
    root.location = (0, 0, 0); root.rotation_euler = (0, 0, 0); root.scale = (ESCALA,) * 3
    for b in P: b.rotation_mode = 'QUATERNION'; b.rotation_quaternion = (1, 0, 0, 0)
    bpy.context.view_layer.update()
    m = next(o for o in arm.children if o.type == 'MESH')
    pts = [m.matrix_world @ v.co for v in m.data.vertices]; ymax = max(p.y for p in pts)
    pico = sum((p for p in pts if p.y > ymax - 0.04), Vector()) / len([p for p in pts if p.y > ymax - 0.04])   # punta del pico (espacio de la raiz)
    pico /= ESCALA

    # pan: posicion por frame (sus curvas)
    pan = bpy.data.objects["pan_alfred"]; fcs = {(fc.data_path, fc.array_index): fc for l in pan.animation_data.action.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves}
    pan_en = lambda f: Vector([fcs[("location", i)].evaluate(f) for i in range(3)])
    LL, GA = int(T["pan_llega"]), int(T["pan_gana"]); TI = int(T["pan_tiron"]); FIN = sc.frame_end
    F_IN = LL - VUELO_LLEGADA
    alf = bpy.data.objects["alfred"].matrix_world.translation
    hacia_alfred = (Vector((alf.x, alf.y, 0)) - Vector((pan_en(LL).x, pan_en(LL).y, 0))).normalized()

    loc, rot, huesos = [], [], {b.name: [] for b in P}; yaw_prev = None; vis = []
    for f in range(1, FIN + 1):
        vis.append(f >= F_IN)
        q = {b.name: Quaternion() for b in P}
        if f < LL:                                                   # vuela hacia el pan (curva que baja y frena)
            u = _sstep(max(0.0, (f - F_IN) / float(VUELO_LLEGADA))); B = pan_en(LL) - hacia_alfred * 0.22
            A = B + DESDE; C = A.lerp(B, 0.6) + Vector((0, 0, 1.2))
            pos = (1 - u) ** 2 * A + 2 * (1 - u) * u * C + u * u * B   # Bezier cuadratica
            dir_ = (B - A) if u < 0.98 else hacia_alfred
            yaw = math.atan2(-dir_.x, dir_.y); pitch = 0.25 * (1 - u) - 0.35 * _sstep((u - 0.7) / 0.3)   # al llegar se frena (se echa atras)
            pico_w = pos; ala = 1.1
        elif f < GA:                                                 # forcejeo: el pico agarra el pan, se echa atras y tira
            k = f - LL; pico_w = pan_en(f) - hacia_alfred * 0.16      # muerde el extremo del pan de su lado
            yaw = math.atan2(-hacia_alfred.x, hacia_alfred.y); pitch = -0.45 - 0.15 * math.sin(2 * math.pi * k / TI)
            ala = 1.6                                                 # aletea fuerte mientras tira
            q["head_paloma_1"] = Quaternion(Vector((1, 0, 0)), 0.25 * math.sin(2 * math.pi * k / TI + 0.6))
        else:                                                        # se lo lleva: vuela con el pan en el pico
            k = f - GA; wp = _sstep(k / 10.0)                          # el pico pasa del extremo del pan a sujetarlo por el centro, sin saltos
            pico_w = pan_en(f) - hacia_alfred * 0.16 * (1 - wp) + Vector((0, 0, 0.04)) * wp
            d = pan_en(f + 1) - pan_en(f); d = d if d.length > 1e-4 else Vector((1, 0, 0))
            y_tira = math.atan2(-hacia_alfred.x, hacia_alfred.y); y_vuela = math.atan2(-d.x, d.y)
            w = _sstep((k - 8) / 14.0)                                 # primero se echa atras con el pan (sigue mirando a Alfred) y luego se da la vuelta
            yaw = y_tira + ((y_vuela - y_tira + math.pi) % (2 * math.pi) - math.pi) * w; pitch = -0.45 * (1 - w) + 0.15 * w; ala = 1.2
        # aleteo (alas) y patas recogidas al volar
        fase = 2 * math.pi * f / ALETEO
        a_ = ala * (0.5 + 0.5 * math.sin(fase))
        q["left_wing_paloma_1"] = Quaternion(Vector((0, 0, 1)), a_); q["rwing_paloma_1"] = Quaternion(Vector((0, 0, 1)), -a_)
        for l in ("left_leg_paloma_1", "rleg_paloma_1"): q[l] = Quaternion(Vector((1, 0, 0)), 0.9)
        if yaw_prev is not None: yaw = yaw_prev + ((yaw - yaw_prev + math.pi) % (2 * math.pi) - math.pi)
        yaw_prev = yaw
        R = Euler((pitch, 0.06 * math.sin(fase), yaw)).to_matrix()
        # sube y baja un poco con cada aleteo; la raiz se pone para que el PICO quede donde toca
        pos_root = pico_w - R @ (pico * ESCALA) + Vector((0, 0, 0.025 * math.sin(fase + 1.2)))
        loc.append(pos_root); rot.append((pitch, 0.06 * math.sin(fase), yaw))
        for n, qq in q.items(): huesos[n].append(qq)

    def curva(a, idb, ruta, i, vals, interp=1):
        fc = a.fcurve_ensure_for_datablock(idb, ruta, index=i); kp = fc.keyframe_points; kp.add(len(vals))
        kp.foreach_set("co", [c for k, v in enumerate(vals) for c in (k + 1, float(v))]); kp.foreach_set("interpolation", [interp] * len(vals)); fc.update()
    for idb, nombre in ((root, "p11_paloma_root"), (arm, "p11_paloma_huesos")):
        viejo = bpy.data.actions.get(nombre)
        if viejo: bpy.data.actions.remove(viejo)
        idb.animation_data_create(); idb.animation_data.action = bpy.data.actions.new(nombre)
    a = root.animation_data.action
    for i in range(3): curva(a, root, "location", i, [v[i] for v in loc])
    for i in range(3): curva(a, root, "rotation_euler", i, [v[i] for v in rot])
    curva(a, root, "hide_viewport", 0, [not v for v in vis], 0); curva(a, root, "hide_render", 0, [not v for v in vis], 0)
    for o in [x for x in root.children_recursive if x.type == 'MESH']:   # el empty no oculta a sus hijos: se ocultan tambien
        viejo = bpy.data.actions.get("p11_paloma_vis_" + o.name)
        if viejo: bpy.data.actions.remove(viejo)
        o.animation_data_create(); ao = bpy.data.actions.new("p11_paloma_vis_" + o.name); o.animation_data.action = ao
        curva(ao, o, "hide_viewport", 0, [not v for v in vis], 0); curva(ao, o, "hide_render", 0, [not v for v in vis], 0)
    a = arm.animation_data.action
    curva(a, arm, "hide_viewport", 0, [not v for v in vis], 0); curva(a, arm, "hide_render", 0, [not v for v in vis], 0)
    for n, L in huesos.items():
        for i in range(4): curva(a, arm, 'pose.bones["%s"].rotation_quaternion' % n, i, [qq[i] for qq in L])
    sc["p11_paloma"] = {"entra": F_IN, "llega": LL, "gana": GA}
    print("PALOMA: entra", F_IN, "agarra el pan", LL, "se lo lleva", GA)
    return F_IN


if __name__ in ("__main__", "x"):
    construir()
