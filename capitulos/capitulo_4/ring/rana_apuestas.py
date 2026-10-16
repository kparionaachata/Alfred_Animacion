# -*- coding: utf-8 -*-
"""base_ranas_3: RANA DE LAS APUESTAS (ribbit nuevo, modelo ribbit_7).
Lleva un PAPEL en la mano derecha (objetos/vanilla/paper) y un LAPIZ en la izquierda (modelado aqui: cuerpo hexagonal
amarillo, punta de madera con grafito, virola metalica y goma rosa). Camina por detras del publico del lado sur anotando
apuestas (se para frente a algunos espectadores y escribe). En F_JERRY llega por detras de Jerry y le pregunta; Jerry
(jerry_ranas3.py, APUESTA) baja de la valla, se gira, le dice "todo", saca 5 PEPITAS DE HIERRO (objetos/vanilla/iron_nugget)
"del bolsillo" y se las da: quedan sobre el papel, la rana anota la apuesta y se las guarda. Despues sigue anotando.
Uso (exec en Blender): construir()   (despues de regenerar a Jerry con jerry_ranas3.py)
"""
import bpy, bmesh, math
from mathutils import Vector, Euler, Matrix

DIR = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/"
BASE = "C:/Users/user/Desktop/Alfred_Animacion/"
bpy.app.driver_namespace["pelea_variante"] = "ranas3"
L = {"__name__": "luch"}
exec(open(DIR + "luchadores_rodean.py", encoding="utf-8").read(), L)
apuntar, rotar_mundo, ss, desenrollar = L["apuntar"], L["rotar_mundo"], L["ss"], L["desenrollar"]
UP = L["UP"]
JN = {"__name__": "j3"}
exec(compile(open(DIR + "jerry_ranas3.py", encoding="utf8").read(), "jerry_ranas3.py", "exec"), JN)
sc = bpy.context.scene; vl = bpy.context.view_layer
D = math.radians
SUELO = 9.0
SUF = "_ribbit_7"
NOMBRE = "rana_apuestas"
F_JERRY = JN["APUESTA"][0]                         # 270
RECIBE = 314                                        # las pepitas pasan de la pata de Jerry al papel
GUARDA = 338                                        # se las guarda
# (frame, punto, accion): "anda" hasta ese punto / "anota" quieto escribiendo mirando a `mira`
PLAN = [(1, (-33.3, -16.25)),
        (40, (-34.59, -16.05)), (82, (-34.59, -16.05)),          # anota la apuesta de ribbit_4_ring
        (118, (-35.38, -16.20)), (160, (-35.38, -16.20)),        # anota la de guard_ribbit_11
        (262, tuple(JN["RANA_APUESTAS"])), (346, tuple(JN["RANA_APUESTAS"])),   # Jerry
        (392, (-38.65, -16.10)), (432, (-38.65, -16.10)),        # guard_ribbit_5
        (468, (-39.60, -16.10)), (508, (-39.60, -16.10)),        # ribbit_2_ring
        (560, (-41.4, -16.35)), (10 ** 6, (-41.4, -16.35))]
MIRA = {(40, 82): "ribbit_4_ring", (118, 160): "guard_ribbit_11", (262, 346): "jerry", (392, 432): "guard_ribbit_5", (468, 508): "ribbit_2_ring"}


def ramp(f, a, b): return ss((f - a) / float(max(1e-6, b - a)))


def ventana(f, a, b, c, d): return ramp(f, a, b) * (1 - ramp(f, c, d))


def fcs(o):
    return [fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


def pos_raiz(nombre, f):
    o = bpy.data.objects[nombre]; v = list(o.location)
    if o.animation_data and o.animation_data.action:
        for fc in fcs(o):
            if fc.data_path == "location": v[fc.array_index] = fc.evaluate(f)
    return Vector(v)


def anexar(archivo, nombres, col):
    with bpy.data.libraries.load(BASE + archivo, link=False) as (src, dst): dst.objects = [n for n in nombres if n in src.objects]
    out = [o for o in dst.objects if o]
    for o in out: col.objects.link(o)
    return out


def material(nombre, color, rough=0.6, metal=0.0):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    m.use_nodes = True; b = m.node_tree.nodes.get("Principled BSDF")
    if b:
        b.inputs["Base Color"].default_value = (*color, 1.0); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    m.diffuse_color = (*color, 1.0)
    return m


def crear_lapiz(col):
    """lapiz de 12 cm a lo largo de +Z: cuerpo hexagonal amarillo, virola, goma rosa, punta de madera y grafito"""
    if "lapiz_apuestas" in bpy.data.objects: return bpy.data.objects["lapiz_apuestas"]
    me = bpy.data.meshes.new("lapiz_apuestas"); bm = bmesh.new()
    mats = [material("lapiz_amarillo", (0.95, 0.72, 0.05)), material("lapiz_madera", (0.86, 0.66, 0.42)),
            material("lapiz_grafito", (0.12, 0.12, 0.13), 0.4), material("lapiz_virola", (0.75, 0.75, 0.78), 0.3, 1.0),
            material("lapiz_goma", (0.95, 0.52, 0.62))]
    r = 0.0045

    def anillo(z, rad, n=6):
        return [bm.verts.new((rad * math.cos(2 * math.pi * k / n + math.pi / 6), rad * math.sin(2 * math.pi * k / n + math.pi / 6), z)) for k in range(n)]

    def tubo(a, b, mi):
        for k in range(6):
            f = bm.faces.new((a[k], a[(k + 1) % 6], b[(k + 1) % 6], b[k])); f.material_index = mi
    goma0, goma1 = anillo(0.0, r * 0.95), anillo(0.008, r * 0.95)
    vir0, vir1 = anillo(0.008, r * 1.05), anillo(0.016, r * 1.05)
    cue0, cue1 = anillo(0.016, r), anillo(0.10, r)
    f = bm.faces.new(list(reversed(goma0))); f.material_index = 4
    tubo(goma0, goma1, 4); tubo(vir0, vir1, 3); tubo(cue0, cue1, 0)
    punta_m = anillo(0.114, r * 0.3)
    tubo(cue1, punta_m, 1)
    tip = bm.verts.new((0, 0, 0.12))
    for k in range(6):
        f = bm.faces.new((punta_m[k], punta_m[(k + 1) % 6], tip)); f.material_index = 2
    bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    o = bpy.data.objects.new("lapiz_apuestas", me); col.objects.link(o)
    return o


def preparar():
    col = bpy.data.collections.get("rana_apuestas_col")
    if col is None: col = bpy.data.collections.new("rana_apuestas_col"); sc.collection.children.link(col)
    if NOMBRE not in bpy.data.objects:
        nuevos = anexar("estructura_lista/ribbits/ribbit_7.blend", ["ribbit_7", "ribbit.001_ribbit_7", "Mesh_0_ribbit_7"], col)
        raiz = next(o for o in nuevos if o.parent is None); raiz.name = NOMBRE
        for o in nuevos:
            if o.type == 'ARMATURE': o.name = NOMBRE + "_arm"
            if o.animation_data: o.animation_data.action = None
    if "papel_apuestas" not in bpy.data.objects:
        o = anexar("objetos/vanilla/paper/paper.blend", ["paper"], col)[0]; o.name = "papel_apuestas"
    lapiz = crear_lapiz(col)
    for k in range(5):
        n = "pepita_apuesta_%d" % (k + 1)
        if n not in bpy.data.objects:
            o = anexar("objetos/vanilla/iron_nugget/iron_nugget.blend", ["iron_nugget"], col)[0]; o.name = n
    return bpy.data.objects[NOMBRE], bpy.data.objects[NOMBRE + "_arm"], bpy.data.objects["papel_apuestas"], lapiz, [bpy.data.objects["pepita_apuesta_%d" % (k + 1)] for k in range(5)]


def escala_a(o, lado):
    """escala uniforme para que la mayor dimension del objeto mida `lado`"""
    o.scale = (1, 1, 1); vl.update(); dm = max(o.dimensions)
    if dm > 1e-6: s = lado / dm; o.scale = (s, s, s)


def en_plan(f):
    for (f0, a), (f1, b) in zip(PLAN[:-1], PLAN[1:]):
        if f0 <= f <= f1:
            a, b = Vector(a), Vector(b)
            if (a - b).length < 1e-4: return a, False
            return a.lerp(b, ss((f - f0) / float(f1 - f0))), True
    return Vector(PLAN[-1][1]), False


def mirando(f):
    for (a, b), quien in MIRA.items():
        if a <= f <= b: return quien
    return None


def construir():
    FIN = sc.frame_end
    raiz, arm, papel, lapiz, pepitas = preparar()
    P = arm.pose.bones; W = lambda: arm.matrix_world
    B = {k: k + SUF for k in ("body", "left_arm", "right_arm", "right_leg", "left_leg")}
    for b in B.values(): P[b].rotation_mode = 'XYZ'
    escala_a(papel, 0.20); escala_a(lapiz, 0.13)
    for o in pepitas: escala_a(o, 0.06)
    jr, ja = bpy.data.objects["jerry"], bpy.data.objects["Dog_001_rig"]
    ocultos = [o.name for r in (raiz, jr) for o in [r] + list(r.children_recursive) if o.hide_viewport]
    for n in ocultos: bpy.data.objects[n].hide_viewport = False
    # ---- papel y lapiz en las manos (hijos de los huesos de los brazos, en la punta)
    raiz.animation_data_clear(); arm.animation_data_clear()
    raiz.location = (PLAN[0][1][0], PLAN[0][1][1], SUELO); raiz.rotation_euler = (0, 0, 0)
    for b in B.values(): P[b].rotation_euler = (0, 0, 0)
    vl.update()
    for obj, b, rot in ((papel, B["right_arm"], Euler((D(70), 0, 0))), (lapiz, B["left_arm"], Euler((D(-30), 0, D(20))))):
        obj.parent = None; obj.animation_data_clear()
        mano = W() @ P[b].tail
        M = Matrix.LocRotScale(mano, rot.to_quaternion(), obj.scale.copy())
        obj.parent = arm; obj.parent_type = 'BONE'; obj.parent_bone = b
        vl.update(); obj.matrix_world = M
    # ---- recorrido de la rana
    out = {"loc": [], "rot": [], "h": {b: [] for b in B.values()}}; papel_w = {}; lapiz_w = {}
    ys = []
    for f in range(1, FIN + 1):
        p, anda = en_plan(f); quien = mirando(f)
        if quien:
            q = pos_raiz(quien, f) if quien != "jerry" else pos_raiz("jerry", f)
            d = Vector((q.x - p.x, q.y - p.y, 0))
        elif anda:
            p2, _ = en_plan(min(FIN, f + 3)); d = Vector((p2.x - p.x, p2.y - p.y, 0))
        else:
            d = Vector((0, 1, 0))
        ys.append(math.atan2(-d.x, d.y) if d.length > 1e-3 else (ys[-1] if ys else 0.0))
    ys = desenrollar(ys); hs = list(ys)
    for i in range(1, len(hs)): hs[i] = hs[i - 1] + (ys[i] - hs[i - 1]) * 0.3
    for i, f in enumerate(range(1, FIN + 1)):
        p, anda = en_plan(f); quien = mirando(f)
        salto = 0.05 * abs(math.sin(math.pi * f / 8.0)) if anda else 0.0
        raiz.location = (p.x, p.y, SUELO + salto); raiz.rotation_euler = (0, 0, hs[i])
        for b in B.values(): P[b].rotation_euler = (0, 0, 0)
        vl.update()
        R3 = raiz.matrix_world.to_3x3(); fw = (R3 @ Vector((0, 1, 0))).normalized(); rt = (R3 @ Vector((1, 0, 0))).normalized(); up = (R3 @ Vector((0, 0, 1))).normalized()
        anota = quien is not None and not anda
        rotar_mundo(arm, B["body"], rt, D(-8 if anota else -4) + D(2) * math.sin(f * 0.3))
        if anda: rotar_mundo(arm, B["body"], UP, D(6 * math.sin(2 * math.pi * f / 16.0)))
        # brazo derecho: sostiene el papel delante del pecho (lo acerca a Jerry al recibir)
        hom_r = W() @ P[B["right_arm"]].head
        Tr = hom_r + fw * 0.16 + up * 0.02 - rt * 0.05
        if quien == "jerry":
            Tr = Tr.lerp(hom_r + fw * 0.24 + up * 0.06, ventana(f, 304, 310, RECIBE + 2, RECIBE + 8))
        apuntar(arm, B["right_arm"], lambda: W() @ P[B["right_arm"]].tail, Tr)
        vl.update()
        hoja = W() @ P[B["right_arm"]].tail
        # brazo izquierdo: lapiz; al anotar escribe en el papel (zigzag); al preguntar a Jerry lo senala con el lapiz
        hom_l = W() @ P[B["left_arm"]].head
        Tl = hom_l + fw * 0.12 - up * 0.02 + rt * 0.03
        if anota:
            escribe = hoja + up * 0.03 + rt * (0.02 * math.sin(f * 1.6)) + fw * (0.01 * math.sin(f * 0.8))
            w = 1.0
            if quien == "jerry":                                                 # pregunta (senala) -> espera -> anota tras recibir
                senala = hom_l + fw * 0.22 + up * 0.10
                w = ramp(f, RECIBE + 2, RECIBE + 6)
                Tl = Tl.lerp(senala, ventana(f, F_JERRY, F_JERRY + 4, F_JERRY + 14, F_JERRY + 18))
            Tl = Tl.lerp(escribe, w)
        apuntar(arm, B["left_arm"], lambda: W() @ P[B["left_arm"]].tail, Tl)
        for s, lado in (("right_leg", 1), ("left_leg", -1)):
            b = B[s]; hip = W() @ P[b].head
            pie = (-up * 0.85 - fw * 0.3 + rt * lado * 0.2) if salto > 0.015 else (-up + rt * lado * 0.12)
            apuntar(arm, b, lambda b=b: W() @ P[b].tail, hip - pie.normalized() * 0.14)
        vl.update()
        if salto <= 0.015:                                                     # pisa el suelo
            dg = bpy.context.evaluated_depsgraph_get(); z = 1e9
            for x in raiz.children_recursive:
                if x.type == 'MESH' and x not in (papel, lapiz):
                    e = x.evaluated_get(dg); M = x.matrix_world; z = min(z, min((M @ v.co).z for v in e.data.vertices))
            raiz.location.z += SUELO - z; vl.update()
        papel_w[f] = papel.matrix_world.copy()
        out["loc"].append((f, tuple(raiz.location))); out["rot"].append((f, tuple(raiz.rotation_euler)))
        for b in B.values(): out["h"][b].append((f, tuple(P[b].rotation_euler)))

    def claves(obj, canales, nombre, const=()):
        obj.animation_data_create(); old = bpy.data.actions.get(nombre)
        if old: bpy.data.actions.remove(old)
        act = bpy.data.actions.new(nombre); obj.animation_data.action = act
        for path, cl in canales.items():
            for i_ in range(len(cl[0][1])):
                fc = act.fcurve_ensure_for_datablock(obj, path, index=i_); fc.keyframe_points.add(len(cl))
                fc.keyframe_points.foreach_set("co", [x for f_, v_ in cl for x in (f_, v_[i_])])
                for k in fc.keyframe_points: k.interpolation = 'CONSTANT' if path in const else 'LINEAR'
                fc.update()
    claves(raiz, {"location": out["loc"], "rotation_euler": out["rot"]}, NOMBRE + "_raiz")
    claves(arm, {'pose.bones["%s"].rotation_euler' % b: v for b, v in out["h"].items()}, NOMBRE + "_anima")
    # ---- pepitas: aparecen en la pata de Jerry ("del bolsillo"), pasan al papel y la rana se las guarda
    a0, a1 = JN["APUESTA_BOLSILLO"][0] + 4, GUARDA
    toe = {}
    for f in range(a0, RECIBE + 1):
        sc.frame_set(f)
        for x in [jr] + list(jr.children_recursive): x.hide_viewport = False
        vl.update(); toe[f] = ja.matrix_world @ ja.pose.bones["front_toe.R"].tail
    for k, o in enumerate(pepitas):
        o.parent = None; o.animation_data_clear(); o.rotation_mode = 'XYZ'
        off = Vector((0.025 * math.cos(2 * math.pi * k / 5), 0.025 * math.sin(2 * math.pi * k / 5), 0.012 * (k % 2)))
        locs, rots = [], []
        for f in range(a0 - 1, a1 + 2):
            if f <= RECIBE - 2: p = toe.get(max(a0, min(RECIBE, f)), toe[a0]) + off + Vector((0, 0, 0.02))
            elif f <= RECIBE + 2:                                               # caen sobre el papel
                u = (f - (RECIBE - 2)) / 4.0; dest = papel_w[f].translation + off * 1.2 + Vector((0, 0, 0.015))
                p = toe[RECIBE] + off + Vector((0, 0, 0.02)); p = p.lerp(dest, ss(u)); p.z += 0.03 * math.sin(math.pi * u)
            else: p = papel_w[min(f, FIN)].translation + off * 1.2 + Vector((0, 0, 0.015))
            locs.append((f, tuple(p))); rots.append((f, (0.0, 0.0, 0.6 * k + 0.05 * f)))
        vis = [(1, (1.0,)), (a0, (0.0,)), (a1 + 1, (1.0,))]
        claves(o, {"location": locs, "rotation_euler": rots, "hide_viewport": vis, "hide_render": vis}, o.name + "_acc", const=("hide_viewport", "hide_render"))
    for n in ocultos: bpy.data.objects[n].hide_viewport = True
    sc.frame_set(sc.frame_current)
    return {"rana": NOMBRE, "pepitas": len(pepitas), "recibe": RECIBE, "jerry_apuesta": JN["APUESTA"]}
