# -*- coding: utf-8 -*-
"""RING DE LUCHA (base_ranas_1.blend): ESPECTADORES alrededor de la valla.
- Ribbits (estructura_lista/ribbits/ribbit_N.blend) rellenan los huecos entre los guardianes, pegados a la valla y mirando al centro.
- Cerdo, vaca y oveja (mas altos): de pie en DOS PATAS (el cuerpo gira hacia arriba sobre las patas traseras, que quedan en el suelo),
  una pata delantera APOYADA en la barra de arriba de la valla y la otra AGITANDOSE en el aire para animar a su luchador.
  Las patas se apuntan en el mundo (FK); en la oveja se apaga el IK de las patas delanteras.
Repetible: reanexa solo lo que falte y rehace poses y animacion."""
import bpy, math, random
from mathutils import Vector, Matrix, Euler, Quaternion

E = r"C:\Users\user\Desktop\Alfred_Animacion\estructura_lista"
Z = 9.0; CENTRO = Vector((-37.5, -12.0, Z))
VALLA = dict(x0=-40.5, x1=-34.5, y0=-14.5, y1=-9.5, z_barra=9.95)     # ejes de los postes y altura de la barra de arriba
COL = "espectadores_ring"
sc = bpy.context.scene; vl = bpy.context.view_layer


def coleccion():
    c = bpy.data.collections.get(COL)
    if c is None: c = bpy.data.collections.new(COL); sc.collection.children.link(c)
    return c


def anexar(ruta, raiz, nombre_nuevo):
    """anexa el .blend (todos sus objetos) y renombra la raiz; devuelve la raiz"""
    if bpy.data.objects.get(nombre_nuevo): return bpy.data.objects[nombre_nuevo]
    with bpy.data.libraries.load(ruta, link=False) as (src, dst): dst.objects = list(src.objects)
    c = coleccion(); r = None
    for o in dst.objects:
        if o is None: continue
        c.objects.link(o)
        if o.name.split(".")[0] == raiz and o.parent is None: r = o
    sobra = [o for o in dst.objects if o and o.parent is None and o is not r and o.type != 'EMPTY' and not o.children]
    for o in [o for o in dst.objects if o and o.parent is None and o is not r]:          # p. ej. el calamar que viene en cow.blend
        for x in [o] + list(o.children_recursive): bpy.data.objects.remove(x)
    r.name = nombre_nuevo
    return r


def mirar_centro(x, y, desvio=0.0):
    d = CENTRO.xy - Vector((x, y)); return math.atan2(-d.x, d.y) + desvio      # los modelos miran a +Y


def puntos(o):
    dg = bpy.context.evaluated_depsgraph_get(); ps = []
    for c in [o] + list(o.children_recursive):
        if c.type == 'MESH':
            e = c.evaluated_get(dg); m = e.to_mesh(); ps += [c.matrix_world @ v.co for v in m.vertices]; e.to_mesh_clear()
    return ps


def apoyar_en_suelo(r):
    vl.update(); ps = puntos(r); r.location.z += Z - min(p.z for p in ps); vl.update()


def apuntar(arm, hueso, punta, objetivo_w):
    """gira `hueso` (FK) para que el vector cabeza->`punta()` apunte a objetivo_w; devuelve el valor de rotacion local"""
    pb = arm.pose.bones[hueso]; vl.update()
    a = arm.matrix_world @ pb.head; b = punta()
    q = (b - a).normalized().rotation_difference((objetivo_w - a).normalized())
    R = Matrix.Translation(a) @ q.to_matrix().to_4x4() @ Matrix.Translation(-a)
    nuevo = arm.matrix_world.inverted() @ R @ arm.matrix_world @ pb.matrix
    m = arm.convert_space(pose_bone=pb, matrix=nuevo, from_space='POSE', to_space='LOCAL')
    if pb.rotation_mode == 'QUATERNION': pb.rotation_quaternion = m.to_quaternion()
    else: pb.rotation_euler = m.to_euler(pb.rotation_mode, pb.rotation_euler)
    vl.update()


# ------------------------------------------------------------------ guion de espectadores
RIBBITS = [("ribbit_1", -39.2, -8.85), ("ribbit_4", -34.25, -15.15),            # ribbit_2 y ribbit_3 se cambiaron por una vaca y un cerdo
           ("ribbit_5", -33.85, -12.17), ("ribbit_6", -33.86, -14.25), ("ribbit_7", -41.15, -13.7)]
# (archivo, raiz, nombre, lado, posicion a lo largo de la valla, hueso hombro apoyado, punta apoyada, hombro que anima, punta que anima, luchador)
ANIMALES = [
    ("cerdo_1.blend", "cerdo_1", "cerdo_ring", "S", -37.45, ("Leg:FR_cerdo_1", "Leg:FR:Bend_cerdo_1"), ("Leg:FL_cerdo_1", "Leg:FL:Bend_cerdo_1"), "alfred"),
    ("cow.blend", "cow", "vaca_ring", "N", -36.65, ("Leg:U:F:L", "Leg:L:F:L"), ("Leg:U:F:R", "Leg:L:F:R"), "guard_ribbit_1", "fijo"),
    # (la oveja del lado oeste se cambio por un POLLO en un slab: pollo_espectador)
    ("cow.blend", "cow", "vaca2_ring", "E", -11.95, ("Leg:U:F:R", "Leg:L:F:R"), ("Leg:U:F:L", "Leg:L:F:L"), "alfred"),
    ("cerdo_1.blend", "cerdo_1", "cerdo2_ring", "N", -40.0, ("Leg:FL_cerdo_1", "Leg:FL:Bend_cerdo_1"), ("Leg:FR_cerdo_1", "Leg:FR:Bend_cerdo_1"), "guard_ribbit_1"),
]
def arma_de(r): return next(c for c in r.children_recursive if c.type == 'ARMATURE' and c.pose and len(c.pose.bones) > 3 and "extras" not in c.name)
INCLINACION = math.radians(58)                                # cuanto se levantan sobre las patas traseras
FIN = 745; CADA = 2; PERIODO = 14                             # agitar la pata: un vaiven cada 14 frames


def lado_geom(lado, pos, D):
    """(pivote xy, yaw, punto de la valla) para un animal en el lado N/S/E/O a `pos` a lo largo de la valla y D de separacion"""
    if lado == "S": return Vector((pos, VALLA["y0"] - D)), 0.0, lambda x, y: Vector((x, VALLA["y0"], VALLA["z_barra"]))
    if lado == "N": return Vector((pos, VALLA["y1"] + D)), math.pi, lambda x, y: Vector((x, VALLA["y1"], VALLA["z_barra"]))
    if lado == "O": return Vector((VALLA["x0"] - D, pos)), -math.pi / 2, lambda x, y: Vector((VALLA["x0"], y, VALLA["z_barra"]))
    return Vector((VALLA["x1"] + D, pos)), math.pi / 2, lambda x, y: Vector((VALLA["x1"], y, VALLA["z_barra"]))


def pivote_trasero(r):
    """pies traseros en el espacio de la raiz (centro de los vertices mas bajos de la mitad trasera)"""
    r.matrix_world = Matrix(); vl.update(); ps = puntos(r)
    zmin = min(p.z for p in ps); ymed = sum(p.y for p in ps) / len(ps)
    pie = [p for p in ps if p.z < zmin + 0.06 and p.y < ymed]
    return Vector((0.0, sum(p.y for p in pie) / len(pie), zmin))


def puntos_sin(o, huesos):
    """vertices deformados del objeto y sus hijos, quitando los que pesan mas en los huesos `huesos` (o las mallas de esas patas)"""
    dg = bpy.context.evaluated_depsgraph_get(); ps = []
    for c in [o] + list(o.children_recursive):
        if c.type != 'MESH': continue
        nombres = {g.index: g.name for g in c.vertex_groups}
        e = c.evaluated_get(dg); m = e.to_mesh()
        for v, vo in zip(m.vertices, c.data.vertices):
            gs = sorted(vo.groups, key=lambda x: -x.weight)
            if gs and nombres.get(gs[0].group) in huesos: continue
            if not gs and c.parent_type == 'BONE' and c.parent_bone in huesos: continue
            ps.append(c.matrix_world @ v.co)
        e.to_mesh_clear()
    return ps


def kd_valla():
    from mathutils.kdtree import KDTree
    ps = puntos(bpy.data.objects["valla_ring_lucha"]); kd = KDTree(len(ps))
    for i, v in enumerate(ps): kd.insert(v, i)
    kd.balance(); return kd


def construir():
    rng = random.Random(21); hechos = {}
    # ---- ribbits
    for n, x, y in RIBBITS:
        r = anexar(E + "/ribbits/" + n + ".blend", n, n + "_ring")
        r.location = (x + rng.uniform(-0.06, 0.06), y + rng.uniform(-0.05, 0.05), Z); r.rotation_euler = (0, 0, mirar_centro(x, y, math.radians(rng.uniform(-15, 15))))
        apoyar_en_suelo(r); hechos[r.name] = tuple(round(v, 2) for v in r.location)
    # ---- animales en dos patas
    kd = kd_valla()
    for archivo, raiz, nombre, lado, pos, apoyo, anima, luchador, *_x in ANIMALES:
        r = anexar(E + "/" + archivo, raiz, nombre); arm = arma_de(r); P = arm.pose.bones
        if arm.animation_data: arm.animation_data_clear()
        for pb in P:
            pb.location = (0, 0, 0); pb.scale = (1, 1, 1)
            if pb.rotation_mode == 'QUATERNION': pb.rotation_quaternion = (1, 0, 0, 0)
            else: pb.rotation_euler = (0, 0, 0)
            for c in pb.constraints:
                if c.type == 'IK' and "front" in pb.name: c.influence = 0.0       # oveja: patas delanteras a mano (FK)
        piv = pivote_trasero(r)
        delanteras = {apoyo[0], apoyo[1], anima[0], anima[1]}
        cuerpo = [o for o in r.children_recursive if o.type == 'MESH']

        def colocar(D):
            p_xy, yaw, _f = lado_geom(lado, pos, D)
            r.matrix_world = Matrix.Translation(Vector((p_xy.x, p_xy.y, Z))) @ Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Rotation(INCLINACION, 4, 'X') @ Matrix.Translation(-piv)
            vl.update()
        D = 0.3
        for D in [0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:      # lo mas cerca de la valla sin tocarla (patas delanteras aparte)
            colocar(D); ps = [p for p in puntos(r) if p.z < VALLA["z_barra"] - 0.15]
            if min(kd.find(p)[2] for p in ps) > 0.04: break
        apoyar_en_suelo(r)
        _p, _y, fvalla = lado_geom(lado, pos, D)
        hom = arm.matrix_world @ P[apoyo[0]].head
        apuntar(arm, apoyo[0], lambda: arm.matrix_world @ P[apoyo[1]].tail, fvalla(hom.x, hom.y))
        # pata que anima: se agita arriba, hacia su luchador
        L = bpy.data.objects[luchador].matrix_world.translation; homa = arm.matrix_world @ P[anima[0]].head
        hacia = (L - homa); hacia.z = 0; hacia.normalize()
        pb = P[anima[0]]; claves = []
        for f in range(1, FIN + 1, CADA):
            t = 2 * math.pi * (f + rng.random() * 0) / PERIODO
            obj = homa + Vector((0, 0, 0.45 + 0.12 * math.sin(t))) + hacia * (0.22 + 0.1 * math.sin(t + 1.3)) + Vector((0, 0, 0)).cross(hacia)
            apuntar(arm, anima[0], lambda: arm.matrix_world @ P[anima[1]].tail, obj)
            claves.append((f, pb.rotation_quaternion.copy() if pb.rotation_mode == 'QUATERNION' else pb.rotation_euler.copy()))
        arm.animation_data_create(); act = bpy.data.actions.new(nombre + "_anima"); arm.animation_data.action = act
        ruta = 'pose.bones["%s"].%s' % (anima[0], "rotation_quaternion" if pb.rotation_mode == 'QUATERNION' else "rotation_euler")
        for i in range(len(claves[0][1])):
            fc = act.fcurve_ensure_for_datablock(arm, ruta, index=i); fc.keyframe_points.add(len(claves))
            fc.keyframe_points.foreach_set("co", [c for f, v in claves for c in (f, v[i])]); fc.update()
        sc.frame_set(1)
        punta = arm.matrix_world @ P[apoyo[1]].tail
        hechos[nombre] = dict(lado=lado, separacion=D, pata_en_barra=[round(c, 2) for c in punta], error_barra=round((punta - fvalla(hom.x, hom.y)).length, 3), anima_a=luchador)
    hechos.update(animales_v2())                                               # postura buena: columna curvada, patas traseras verticales, cabeza al ring
    return hechos


# ------------------------------------------------------------------ ribbits subidos a un SLAB, apoyados en la valla y animando
SLAB = "C:/Users/user/Desktop/Alfred_Animacion/bloques_dinamicos/slab_de_tablones_de_roble.blend"
# (raiz, armadura, brazo apoyado, brazo que anima, luchador, lado de la valla)
SUBIDOS = [("guard_ribbit_3", "main_guard_ribbit_3", "N", "alfred"), ("guard_ribbit_12", "main_guard_ribbit_12", "E", "guard_ribbit_1"),
           ("guard_ribbit_15", "main_guard_ribbit_15", "O", "alfred"), ("ribbit_1_ring", None, "N", "guard_ribbit_1"),
           ("ribbit_5_ring", None, "E", "alfred"), ("ribbit_7_ring", None, "O", "guard_ribbit_1")]


def slab_en(x, y, nombre):
    o = bpy.data.objects.get(nombre)
    if o is None:
        base = bpy.data.objects.get("slab_ring_base")
        if base is None:
            with bpy.data.libraries.load(SLAB, link=False) as (src, dst): dst.meshes = [n for n in src.meshes]
            me = dst.meshes[0]; me.name = "slab_tablones_roble_ring"
        me = bpy.data.meshes["slab_tablones_roble_ring"]
        o = bpy.data.objects.new(nombre, me); coleccion().objects.link(o)
    vs = [v.co for v in o.data.vertices]
    off = Vector(((min(v.x for v in vs) + max(v.x for v in vs)) / 2, (min(v.y for v in vs) + max(v.y for v in vs)) / 2, min(v.z for v in vs)))
    o.location = Vector((math.floor(x) + 0.5, math.floor(y) + 0.5, Z)) - off      # ocupa la mitad de abajo del bloque donde esta
    vl.update(); return o


def pies(r):
    ps = [p for p in puntos(r)]; zmin = min(p.z for p in ps); return [p for p in ps if p.z < zmin + 0.05]


def slab_bajo_pies(r, lado):
    """el slab justo bajo los pies (pegado a la valla sin tocar los postes: 12.5 cm) y, si un pie asoma, el frog retrocede hasta pisarlo entero"""
    s = bpy.data.objects["slab_" + r.name]; o = {"N": Vector((0, 1, 0)), "S": Vector((0, -1, 0)), "E": Vector((1, 0, 0)), "O": Vector((-1, 0, 0))}[lado]
    linea = {"N": VALLA["y1"], "S": -VALLA["y0"], "E": VALLA["x1"], "O": -VALLA["x0"]}[lado]
    pc = sum(pies(r), Vector()) / len(pies(r)); d = pc.dot(o) - linea
    vs = [v.co for v in s.data.vertices]
    off = Vector(((min(v.x for v in vs) + max(v.x for v in vs)) / 2, (min(v.y for v in vs) + max(v.y for v in vs)) / 2, min(v.z for v in vs)))
    lat = pc - o * pc.dot(o); centro = lat + o * (linea + max(d, 0.135 + 0.5))
    s.location = Vector((centro.x, centro.y, Z)) - off; vl.update()
    borde = min((s.matrix_world @ v.co).dot(o) for v in s.data.vertices)
    falta = max(0.0, borde + 0.01 - min(p.dot(o) for p in pies(r)))
    if falta: r.location += o * falta; vl.update()
    return falta


def subir_y_apoyar():
    rng = random.Random(5); kd = kd_valla(); hechos = {}
    for raiz, armn, lado, luchador in SUBIDOS:
        r = bpy.data.objects[raiz]
        arm = bpy.data.objects[armn] if armn else arma_de(r); P = arm.pose.bones
        sufijo = raiz.replace("guard_ribbit", "guard_ribbit") if armn else raiz.replace("_ring", "")
        brazo_ap = next(b.name for b in P if b.name.startswith("right_arm")); brazo_an = next(b.name for b in P if b.name.startswith("left_arm"))
        if arm.animation_data and arm.animation_data.action and arm.animation_data.action.name.endswith("_anima"):
            bpy.data.actions.remove(arm.animation_data.action)
        for b in (brazo_ap, brazo_an): P[b].rotation_mode = 'QUATERNION'; P[b].rotation_quaternion = (1, 0, 0, 0)
        slab_en(r.location.x, r.location.y, "slab_" + raiz)
        r.location.z = Z + 0.5; vl.update()
        # hacia la valla hasta quedar pegado (sin contar los brazos)
        d = {"N": Vector((0, -1, 0)), "S": Vector((0, 1, 0)), "E": Vector((-1, 0, 0)), "O": Vector((1, 0, 0))}[lado]
        for _ in range(12):
            ps = puntos(r)
            if min(kd.find(p)[2] for p in ps) < 0.06: break
            r.location += d * 0.03; vl.update()
        slab_bajo_pies(r, lado)                                                 # el slab bajo los pies (no en la celda de antes)
        # brazo derecho sobre la barra de arriba, brazo izquierdo agitandose hacia su luchador
        hom = arm.matrix_world @ P[brazo_ap].head
        valla = {"N": Vector((hom.x, VALLA["y1"], VALLA["z_barra"] + 0.03)), "S": Vector((hom.x, VALLA["y0"], VALLA["z_barra"] + 0.03)),
                 "E": Vector((VALLA["x1"], hom.y, VALLA["z_barra"] + 0.03)), "O": Vector((VALLA["x0"], hom.y, VALLA["z_barra"] + 0.03))}[lado]
        apuntar(arm, brazo_ap, lambda: arm.matrix_world @ P[brazo_ap].tail, valla)
        L = bpy.data.objects[luchador].matrix_world.translation; homa = arm.matrix_world @ P[brazo_an].head
        hacia = (L - homa); hacia.z = 0; hacia.normalize(); claves = []; fase = rng.uniform(0, 6.28); per = rng.choice((10, 12, 14))
        for f in range(1, FIN + 1, CADA):
            t = 2 * math.pi * f / per + fase
            obj = homa + Vector((0, 0, 0.42 + 0.12 * math.sin(t))) + hacia * (0.18 + 0.08 * math.sin(t + 1.1))
            apuntar(arm, brazo_an, lambda: arm.matrix_world @ P[brazo_an].tail, obj)
            claves.append((f, P[brazo_an].rotation_quaternion.copy()))
        arm.animation_data_create(); act = bpy.data.actions.new(raiz + "_anima"); arm.animation_data.action = act
        ruta = 'pose.bones["%s"].rotation_quaternion' % brazo_an
        for i in range(4):
            fc = act.fcurve_ensure_for_datablock(arm, ruta, index=i); fc.keyframe_points.add(len(claves))
            fc.keyframe_points.foreach_set("co", [c for f, v in claves for c in (f, v[i])]); fc.update()
        sc.frame_set(1)
        mano = arm.matrix_world @ P[brazo_ap].tail
        hechos[raiz] = dict(slab=[round(v, 2) for v in bpy.data.objects["slab_" + raiz].location], mano_en_barra=[round(c, 2) for c in mano],
                            error=round((mano - valla).length, 3), anima_a=luchador)
    return hechos


# ------------------------------------------------------------------ ANIMALES v2: columna curvada, patas traseras verticales y cabeza al ring
# (v1 giraba el animal entero como una tabla: cuerpo recto, cabeza al cielo y patas traseras inclinadas)
ESQ = {   # partes del rig de cada especie: (hueso que dobla la parte delantera, [(muslo trasero, punta)], cabeza, punta de la cabeza)
    "cerdo": ("Body:Bend_cerdo_1", [("Leg:BL_cerdo_1", "Leg:BL:Bend_cerdo_1"), ("Leg:BR_cerdo_1", "Leg:BR:Bend_cerdo_1")], "Head_cerdo_1", ("Eye-L_cerdo_1", "Eye-R_cerdo_1")),
    "vaca": ("Chest", [("Leg:U:B:L", "Leg:L:B:L"), ("Leg:U:B:R", "Leg:L:B:R")], "Head", ("Eye:Left", "Eye:Right")),
    "oveja": ("front_torso_1", [("rear_left_leg_upper_1", "rear_left_hoof_1"), ("rear_right_leg_upper_1", "rear_right_hoof_1")], "head_1", None),
}
INCL_CUERPO = math.radians(40); INCL_PECHO = math.radians(25)


def especie(nombre): return "cerdo" if "cerdo" in nombre else ("vaca" if "vaca" in nombre else "oveja")


def rotar_mundo(arm, hueso, eje_w, ang):
    pb = arm.pose.bones[hueso]; vl.update(); a = arm.matrix_world @ pb.head
    R = Matrix.Translation(a) @ Quaternion(eje_w.normalized(), ang).to_matrix().to_4x4() @ Matrix.Translation(-a)
    nuevo = arm.matrix_world.inverted() @ R @ arm.matrix_world @ pb.matrix
    m = arm.convert_space(pose_bone=pb, matrix=nuevo, from_space='POSE', to_space='LOCAL')
    if pb.rotation_mode == 'QUATERNION': pb.rotation_quaternion = m.to_quaternion()
    else: pb.rotation_euler = m.to_euler(pb.rotation_mode, pb.rotation_euler)
    vl.update()


def orientar_cabeza(r, arm, cabeza, objetivo):
    """gira la cabeza para que su CARA (el +Y del animal en reposo) mire a `objetivo` y la deja derecha (su arriba lo mas cerca de +Z)"""
    pb = arm.pose.bones[cabeza]; Rr = pb.bone.matrix_local.to_3x3().inverted()
    A = arm.matrix_world.to_3x3().inverted() @ r.matrix_world.to_3x3()        # ejes de la raiz en el espacio de la armadura
    f_loc = (Rr @ (A @ Vector((0, 1, 0)))).normalized(); u_loc = (Rr @ (A @ Vector((0, 0, 1)))).normalized()
    def ejes():
        M = (arm.matrix_world @ pb.matrix).to_3x3(); return (M @ f_loc).normalized(), (M @ u_loc).normalized()
    f, u = ejes(); h = arm.matrix_world @ pb.head; d = (objetivo - h).normalized()
    q = f.rotation_difference(d)
    if q.angle > 1e-5: rotar_mundo(arm, cabeza, q.axis, q.angle)
    f, u = ejes(); arriba = Vector((0, 0, 1)) - f * f.z
    if arriba.length > 1e-4:
        arriba.normalize(); ang = math.atan2(f.dot(u.cross(arriba)), u.dot(arriba))
        rotar_mundo(arm, cabeza, f, ang)
    f, u = ejes(); return math.degrees(f.angle(d)), math.degrees(u.angle(Vector((0, 0, 1))))


def animales_v2():
    rng = random.Random(21); kd = kd_valla(); hechos = {}
    for archivo, raiz, nombre, lado, pos, apoyo, anima, luchador, *extra in ANIMALES:
        r = bpy.data.objects[nombre]; arm = arma_de(r); P = arm.pose.bones; esp = especie(nombre)
        dobla, traseras, cabeza, ojos = ESQ[esp]
        if arm.animation_data:
            if arm.animation_data.action and arm.animation_data.action.users <= 1: bpy.data.actions.remove(arm.animation_data.action)
            arm.animation_data_clear()
        for pb in P:
            pb.location = (0, 0, 0); pb.scale = (1, 1, 1)
            if pb.rotation_mode == 'QUATERNION': pb.rotation_quaternion = (1, 0, 0, 0)
            else: pb.rotation_euler = (0, 0, 0)
            for c in pb.constraints:
                if c.type in ('IK', 'COPY_ROTATION', 'STRETCH_TO', 'DAMPED_TRACK'): c.influence = 0.0     # las patas/cabeza se ponen a mano
        # 1) orientacion: mira al ring y se inclina 40 grados; 2) el pecho se dobla 25 mas (columna curvada)
        _p, yaw, fvalla = lado_geom(lado, pos, 0.5)
        ROT = Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Rotation(INCL_CUERPO, 4, 'X')
        r.matrix_world = Matrix.Translation(Vector((_p.x, _p.y, Z))) @ ROT; vl.update()     # ya en su sitio (la cabeza apunta al ring desde ahi)
        lat = (r.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized()
        rotar_mundo(arm, dobla, lat, INCL_PECHO)
        # 3) patas traseras verticales (un poco adelantadas: equilibrio)
        fwd = Vector((-math.sin(yaw), math.cos(yaw), 0))
        for muslo, punta in traseras:
            a = arm.matrix_world @ P[muslo].head
            apuntar(arm, muslo, lambda m=muslo, t=punta: arm.matrix_world @ P[t].tail, a + fwd * 0.08 - Vector((0, 0, 1)))
        # 4) cabeza mirando al centro del ring
        if ojos: pt = lambda: (arm.matrix_world @ P[ojos[0]].head + arm.matrix_world @ P[ojos[1]].head) / 2
        else: pt = lambda: arm.matrix_world @ P[cabeza].tail
        hc = arm.matrix_world @ P[cabeza].head
        orientar_cabeza(r, arm, cabeza, Vector((CENTRO.x, CENTRO.y, hc.z - 0.05)))      # mira al ring casi a su altura, sin ladearse
        delanteras = set()
        for h in (apoyo[0], anima[0]):
            delanteras.add(h); delanteras.update(c.name for c in P[h].children_recursive)
        # 5) colocar: pies traseros en el pasto, lo mas cerca de la valla sin tocarla (patas delanteras aparte)
        base_M = ROT
        for D in [x / 20 for x in range(-16, 25)]:                                # de -0.8 a 1.2 m: lo mas cerca posible
            p_xy, _yaw, _f = lado_geom(lado, pos, D)
            r.matrix_world = Matrix.Translation(Vector((p_xy.x, p_xy.y, 0))) @ base_M; vl.update()
            apoyar_en_suelo(r)
            ps = [q for q in puntos_sin(r, delanteras) if q.z < VALLA["z_barra"] + 0.06]       # todo el cuerpo hasta la barra, sin las patas delanteras
            fuera = {"N": lambda q: q.y > VALLA["y1"] + 0.13, "S": lambda q: q.y < VALLA["y0"] - 0.13,
                     "E": lambda q: q.x > VALLA["x1"] + 0.13, "O": lambda q: q.x < VALLA["x0"] - 0.13}[lado]
            if all(fuera(q) for q in ps) and min(kd.find(q)[2] for q in ps) > 0.04: break    # lo de abajo, del lado de fuera
        # 6) patas delanteras en V (la cara queda libre en medio): la apoyada toca la barra hacia SU lado; la otra se agita arriba y hacia
        #    afuera, un poco hacia su luchador
        hom = arm.matrix_world @ P[apoyo[0]].head; homa = arm.matrix_world @ P[anima[0]].head
        medio = (hom + homa) / 2
        fuera_ap = (hom - medio); fuera_ap.z = 0; fuera_ap.normalize()
        fuera_an = (homa - medio); fuera_an.z = 0; fuera_an.normalize()
        mira_h = (CENTRO - arm.matrix_world @ P[cabeza].head); mira_h.z = 0          # la cabeza mira al centro del ring
        if "fijo" not in extra and mira_h.dot(fuera_an) > mira_h.dot(fuera_ap):                         # si gira la cabeza hacia la pata que anima, se cambian:
            apoyo, anima = anima, apoyo                                          # se agita la del otro lado y la cara queda libre
            hom, homa = homa, hom; fuera_ap, fuera_an = fuera_an, fuera_ap
        barra = fvalla(hom.x, hom.y) + fuera_ap * 0.22
        adentro = (barra - hom); adentro.z = 0; adentro.normalize()
        ik2(arm, apoyo[0], apoyo[1], barra, -adentro + Vector((0, 0, -0.6)))       # codo hacia abajo y atras: la pezuna sobre la barra
        L = bpy.data.objects[luchador].matrix_world.translation
        hacia = (L - homa); hacia.z = 0; hacia.normalize(); pb = P[anima[0]]; claves = []
        fase = rng.uniform(0, 6.28)
        cab = P[cabeza]; mueve_cabeza = (esp == "oveja"); claves_cab = []
        base_cab = cab.rotation_quaternion.copy() if cab.rotation_mode == 'QUATERNION' else cab.rotation_euler.copy()
        for f in range(1, FIN + 1, CADA):
            t = 2 * math.pi * f / PERIODO + fase
            obj = homa + Vector((0, 0, 0.36 + 0.10 * math.sin(t))) + fuera_an * (0.22 + 0.08 * math.sin(t + 1.3)) + hacia * 0.08
            fwd_h = Vector((-math.sin(yaw), math.cos(yaw), 0))
            ik2(arm, anima[0], anima[1], obj, -fwd_h + Vector((0, 0, -0.7)))               # codo hacia abajo y atras
            pl = P[HIJO_PATA[anima[0]]]
            claves.append((f, pb.rotation_quaternion.copy() if pb.rotation_mode == 'QUATERNION' else pb.rotation_euler.copy(),
                           pl.rotation_quaternion.copy() if pl.rotation_mode == 'QUATERNION' else pl.rotation_euler.copy()))
            if mueve_cabeza:                                                   # la oveja mueve la cabeza: asiente y gira (anima)
                if cab.rotation_mode == 'QUATERNION': cab.rotation_quaternion = base_cab
                else: cab.rotation_euler = base_cab
                hcab = arm.matrix_world @ cab.head
                rotar_mundo(arm, cabeza, lat, math.radians(10) * math.sin(2 * math.pi * f / 18 + fase))
                rotar_mundo(arm, cabeza, Vector((0, 0, 1)), math.radians(14) * math.sin(2 * math.pi * f / 31 + fase * 0.5))
                claves_cab.append((f, cab.rotation_quaternion.copy() if cab.rotation_mode == 'QUATERNION' else cab.rotation_euler.copy()))
        arm.animation_data_create(); act = bpy.data.actions.new(nombre + "_anima"); arm.animation_data.action = act
        claves_p = [(f, v) for f, v, _l in claves]; claves_l = [(f, l) for f, _v, l in claves]
        for hb, cl in ((anima[0], claves_p), (HIJO_PATA[anima[0]], claves_l), (cabeza, claves_cab)):
            if not cl: continue
            pbh = P[hb]; ruta = 'pose.bones["%s"].%s' % (hb, "rotation_quaternion" if pbh.rotation_mode == 'QUATERNION' else "rotation_euler")
            for i in range(len(cl[0][1])):
                fc = act.fcurve_ensure_for_datablock(arm, ruta, index=i); fc.keyframe_points.add(len(cl))
                fc.keyframe_points.foreach_set("co", [c for f, v in cl for c in (f, v[i])]); fc.update()
        sc.frame_set(1)
        # informe
        pbc = P[cabeza]; A_ = arm.matrix_world.to_3x3().inverted() @ r.matrix_world.to_3x3()
        f_l = (pbc.bone.matrix_local.to_3x3().inverted() @ (A_ @ Vector((0, 1, 0)))).normalized()
        hc = arm.matrix_world @ pbc.head; mira = (arm.matrix_world @ pbc.matrix).to_3x3() @ f_l; objc = Vector((CENTRO.x, CENTRO.y, hc.z - 0.05)) - hc
        ps = puntos(r); zmin = min(q.z for q in ps)
        piesz = [round(arm.matrix_world.translation.z, 2)]
        punta = arm.matrix_world @ P[apoyo[1]].tail
        hechos[nombre] = dict(cabeza_al_ring=round(math.degrees(mira.angle(objc)), 1), suelo=round(zmin, 3), separacion=D,
                              pata_en_barra=[round(c, 2) for c in punta], error_barra=round((punta - barra).length, 3), pata_traseras=[round(math.degrees((arm.matrix_world @ P[t].tail - arm.matrix_world @ P[m].head).angle(Vector((0, 0, -1)))), 1) for m, t in traseras])
    return hechos



HIJO_PATA = {"Leg:FR_cerdo_1": "Leg:FR:Bend_cerdo_1", "Leg:FL_cerdo_1": "Leg:FL:Bend_cerdo_1", "Leg:U:F:R": "Leg:L:F:R", "Leg:U:F:L": "Leg:L:F:L",
             "front_right_leg_upper_1": "front_right_leg_knee_1", "front_left_leg_upper_1": "front_left_leg_knee_1"}


def ik2(arm, muslo, punta_hueso, T, polo):
    """pata de 2 tramos: el muslo lleva la rodilla a su sitio y la pierna lleva la punta (`punta_hueso`.tail) justo a T"""
    P = arm.pose.bones; pierna = HIJO_PATA[muslo]; W = arm.matrix_world; vl.update()
    S = W @ P[muslo].head; K = W @ P[pierna].head; F = W @ P[punta_hueso].tail
    a = (K - S).length; b = (F - K).length; d = max(abs(a - b) + 1e-3, min(a + b - 1e-3, (T - S).length)); n = (T - S).normalized()
    ca = (a * a + d * d - b * b) / (2 * a * d); sa = math.sqrt(max(0.0, 1 - ca * ca))
    pp = polo - n * polo.dot(n); pp = pp.normalized() if pp.length > 1e-6 else n.orthogonal().normalized()
    E = S + n * a * ca + pp * a * sa
    apuntar(arm, muslo, lambda: arm.matrix_world @ P[pierna].head, E)
    apuntar(arm, pierna, lambda: arm.matrix_world @ P[punta_hueso].tail, T)
    vl.update(); return ((arm.matrix_world @ P[punta_hueso].tail) - T).length



# ------------------------------------------------------------------ REDISTRIBUCION: animales separados y ribbits en slabs entre ellos
# (nombre, archivo del ribbit si hay que anexarlo, lado, posicion a lo largo de la valla, con slab, luchador al que anima)
FROGS = [
    # norte: cerdo2 (-40.0) y vaca (-36.65)
    ("guard_ribbit_3", None, "N", -38.85, True, "alfred"), ("ribbit_1_ring", "ribbit_1", "N", -38.0, True, "guard_ribbit_1"),
    ("guard_ribbit_13", None, "N", -35.3, True, "alfred"), ("guard_ribbit_4", None, "N", -34.45, False, None),
    # sur: cerdo (-37.45)
    ("guard_ribbit_2", None, "S", -40.35, False, None), ("ribbit_2_ring", "ribbit_2", "S", -39.5, True, "alfred"),
    ("guard_ribbit_5", None, "S", -38.65, True, "guard_ribbit_1"), ("ribbit_3_ring", "ribbit_3", "S", -36.25, True, "alfred"),
    ("guard_ribbit_11", None, "S", -35.4, False, None), ("ribbit_4_ring", "ribbit_4", "S", -34.55, False, None),
    # este: vaca2 (-11.95)
    ("ribbit_6_ring", "ribbit_6", "E", -14.2, False, None), ("guard_ribbit_12", None, "E", -13.35, True, "guard_ribbit_1"),
    ("ribbit_5_ring", "ribbit_5", "E", -10.55, True, "alfred"), ("ribbit_8_ring", "ribbit_8", "E", -9.7, True, "guard_ribbit_1"),
    # oeste: oveja (-12.0)
    ("ribbit_7_ring", "ribbit_7", "O", -13.4, True, "guard_ribbit_1"), ("guard_ribbit_15", None, "O", -10.6, True, "alfred"),
    ("ribbit_4b_ring", "ribbit_4", "O", -9.75, True, "alfred"),
]
SEP_FROG = 0.6                                                  # distancia de la valla al centro del frog (antes de pegarse)


def punto_lado(lado, pos, sep):
    if lado == "N": return Vector((pos, VALLA["y1"] + sep, Z))
    if lado == "S": return Vector((pos, VALLA["y0"] - sep, Z))
    if lado == "E": return Vector((VALLA["x1"] + sep, pos, Z))
    return Vector((VALLA["x0"] - sep, pos, Z))


def frog_espectador(nombre, archivo, lado, pos, con_slab, luchador, rng, kd):
    r = bpy.data.objects.get(nombre)
    if r is None: r = anexar(E + "/ribbits/" + archivo + ".blend", archivo, nombre)
    arm = arma_de(r); P = arm.pose.bones
    sl = bpy.data.objects.get("slab_" + nombre)
    if sl and not con_slab: bpy.data.objects.remove(sl); sl = None
    pt = punto_lado(lado, pos, SEP_FROG)
    r.location = (pt.x + rng.uniform(-0.04, 0.04), pt.y + rng.uniform(-0.04, 0.04), Z)
    r.rotation_euler = (0, 0, mirar_centro(pt.x, pt.y, math.radians(rng.uniform(-12, 12)))); vl.update()
    if not con_slab:
        apoyar_en_suelo(r); return dict(slab=False)
    brazo_ap = next(b.name for b in P if b.name.startswith("right_arm")); brazo_an = next(b.name for b in P if b.name.startswith("left_arm"))
    if arm.animation_data and arm.animation_data.action and arm.animation_data.action.name.split(".")[0].endswith("_anima"):
        a = arm.animation_data.action; arm.animation_data.action = None
        if a.users == 0: bpy.data.actions.remove(a)
    for b in (brazo_ap, brazo_an): P[b].rotation_mode = 'QUATERNION'; P[b].rotation_quaternion = (1, 0, 0, 0)
    slab_en(r.location.x, r.location.y, "slab_" + nombre)
    r.location.z = Z + 0.5; vl.update()
    d = {"N": Vector((0, -1, 0)), "S": Vector((0, 1, 0)), "E": Vector((-1, 0, 0)), "O": Vector((1, 0, 0))}[lado]
    for _ in range(14):
        if min(kd.find(q)[2] for q in puntos(r)) < 0.06: break
        r.location += d * 0.03; vl.update()
    slab_bajo_pies(r, lado)
    o_ = {"N": Vector((0, 1, 0)), "S": Vector((0, -1, 0)), "E": Vector((1, 0, 0)), "O": Vector((-1, 0, 0))}[lado]
    if (arm.matrix_world @ P[brazo_an].head).dot(o_) < (arm.matrix_world @ P[brazo_ap].head).dot(o_):
        brazo_ap, brazo_an = brazo_an, brazo_ap                                  # se apoya el brazo que queda mas cerca de la valla
    hom = arm.matrix_world @ P[brazo_ap].head
    valla = {"N": Vector((hom.x, VALLA["y1"], VALLA["z_barra"] + 0.03)), "S": Vector((hom.x, VALLA["y0"], VALLA["z_barra"] + 0.03)),
             "E": Vector((VALLA["x1"], hom.y, VALLA["z_barra"] + 0.03)), "O": Vector((VALLA["x0"], hom.y, VALLA["z_barra"] + 0.03))}[lado]
    apuntar(arm, brazo_ap, lambda: arm.matrix_world @ P[brazo_ap].tail, valla)
    L = bpy.data.objects[luchador].matrix_world.translation; homa = arm.matrix_world @ P[brazo_an].head
    hacia = (L - homa); hacia.z = 0; hacia.normalize(); claves = []; fase = rng.uniform(0, 6.28); per = rng.choice((10, 12, 14))
    for f in range(1, FIN + 1, CADA):
        t = 2 * math.pi * f / per + fase
        apuntar(arm, brazo_an, lambda: arm.matrix_world @ P[brazo_an].tail, homa + Vector((0, 0, 0.42 + 0.12 * math.sin(t))) + hacia * (0.18 + 0.08 * math.sin(t + 1.1)))
        claves.append((f, P[brazo_an].rotation_quaternion.copy()))
    arm.animation_data_create(); act = bpy.data.actions.new(nombre + "_anima"); arm.animation_data.action = act
    for i in range(4):
        fc = act.fcurve_ensure_for_datablock(arm, 'pose.bones["%s"].rotation_quaternion' % brazo_an, index=i); fc.keyframe_points.add(len(claves))
        fc.keyframe_points.foreach_set("co", [c for f, v in claves for c in (f, v[i])]); fc.update()
    sc.frame_set(1); mano = arm.matrix_world @ P[brazo_ap].tail
    return dict(slab=True, mano_barra=round((mano - valla).length, 3), anima_a=luchador)


def redistribuir():
    rng = random.Random(8); kd = kd_valla(); hechos = {}
    hechos["animales"] = animales_v2()
    for nombre, archivo, lado, pos, con_slab, luchador in FROGS:
        hechos[nombre] = frog_espectador(nombre, archivo, lado, pos, con_slab, luchador, rng, kd)
    return hechos



def juntar_slabs():
    """slabs vecinos que se solapan: se ponen uno junto al otro (se tocan sin solaparse) a cada lado del punto medio"""
    sl = [o for o in bpy.data.objects if o.name.startswith("slab_") and o.type == 'MESH']
    def caja(o):
        vs = [o.matrix_world @ v.co for v in o.data.vertices]; return [min(v.x for v in vs), max(v.x for v in vs), min(v.y for v in vs), max(v.y for v in vs)]
    hecho = []
    for i, A in enumerate(sl):
        for B in sl[i + 1:]:
            a, b = caja(A), caja(B); ox = min(a[1], b[1]) - max(a[0], b[0]); oy = min(a[3], b[3]) - max(a[2], b[2])
            if ox > 0.002 and oy > 0.002:
                k = 0 if ox < oy else 1; ca = (a[2 * k] + a[2 * k + 1]) / 2; cb = (b[2 * k] + b[2 * k + 1]) / 2; mid = (ca + cb) / 2; sg = 1 if ca < cb else -1
                A.location[k] += (mid - 0.5 * sg) - ca; B.location[k] += (mid + 0.5 * sg) - cb; vl.update(); hecho.append((A.name, B.name))
    return hecho



# ------------------------------------------------------------------ POLLO en un slab (donde estaba la oveja): mira al ring y aletea animando
POLLO = ("chicken_1", "pollo_ring", "O", -12.0, "alfred")


def quitar_oveja():
    o = bpy.data.objects.get("oveja_ring")
    if o is None: return False
    for x in [o] + list(o.children_recursive):
        ad = getattr(x, "animation_data", None)
        if ad and ad.action and ad.action.users <= 1: a = ad.action; ad.action = None; bpy.data.actions.remove(a)
        d = x.data; bpy.data.objects.remove(x)
        if d is not None and d.users == 0:
            if isinstance(d, bpy.types.Mesh): bpy.data.meshes.remove(d)
            elif isinstance(d, bpy.types.Armature): bpy.data.armatures.remove(d)
    return True


def eje_que_sube(arm, hueso, punta, eje_candidatos):
    """(indice, signo) del eje local de `hueso` que mas SUBE `punta()`"""
    pb = arm.pose.bones[hueso]; base = pb.rotation_euler.copy(); vl.update(); z0 = punta().z; mejor = None
    for i in range(3):
        e = base.copy(); e[i] += 0.3; pb.rotation_euler = e; vl.update(); dz = punta().z - z0
        if mejor is None or abs(dz) > abs(mejor[1]): mejor = (i, dz)
    pb.rotation_euler = base; vl.update()
    return mejor[0], (1.0 if mejor[1] > 0 else -1.0)


def pollo_espectador():
    rng = random.Random(13); kd = kd_valla()
    quitar_oveja()
    archivo, nombre, lado, pos, luchador = POLLO
    r = anexar(E + "/" + archivo + ".blend", archivo, nombre); arm = arma_de(r); P = arm.pose.bones
    if arm.animation_data: arm.animation_data.action = None                       # su animacion propia (de otra escena) no se usa
    for pb in P: pb.rotation_mode = 'XYZ'; pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
    pt = punto_lado(lado, pos, SEP_FROG)
    r.location = (pt.x, pt.y, Z); r.rotation_euler = (0, 0, mirar_centro(pt.x, pt.y)); vl.update()
    slab_en(r.location.x, r.location.y, "slab_" + nombre); r.location.z = Z + 0.5; vl.update()
    d = {"N": Vector((0, -1, 0)), "S": Vector((0, 1, 0)), "E": Vector((-1, 0, 0)), "O": Vector((1, 0, 0))}[lado]
    for _ in range(16):
        if min(kd.find(q)[2] for q in puntos(r)) < 0.06: break
        r.location += d * 0.03; vl.update()
    slab_bajo_pies(r, lado)
    # aletea: las dos alas suben y bajan (rapido), la cabeza asiente
    alas = []
    for lado_a in ("R", "L"):
        h = "Shoulder_%s_chicken_1" % lado_a; t = "Elbow_%s_end_chicken_1" % lado_a
        alas.append((h, eje_que_sube(arm, h, lambda t=t: arm.matrix_world @ P[t].tail, None)))
    cab = "Head_M_chicken_1"; cuello = "Neck_M_chicken_1"
    ic, sc_ = eje_que_sube(arm, cab, lambda: arm.matrix_world @ P["Jaw_top_chicken_1"].tail, None)
    claves = {h: [] for h, _e in alas}; claves[cab] = []
    fase = rng.uniform(0, 6.28)
    for f in range(1, FIN + 1, CADA):
        # rafagas de aleteo (aletea 1.5 s, descansa un poco) y asentir con la cabeza
        rafaga = 0.5 + 0.5 * math.sin(2 * math.pi * f / 60 + fase)
        a = math.radians(85) * (0.25 + 0.75 * rafaga) * (0.5 + 0.5 * math.sin(2 * math.pi * f / 6))
        for h, (i, sg) in alas:
            e = Euler((0, 0, 0)); e[i] = sg * a; claves[h].append((f, e))
        e = Euler((0, 0, 0)); e[ic] = -sc_ * math.radians(12) * math.sin(2 * math.pi * f / 14 + fase); claves[cab].append((f, e))
    arm.animation_data_create(); act = bpy.data.actions.new(nombre + "_anima"); arm.animation_data.action = act
    for h, cl in claves.items():
        for i in range(3):
            fc = act.fcurve_ensure_for_datablock(arm, 'pose.bones["%s"].rotation_euler' % h, index=i); fc.keyframe_points.add(len(cl))
            fc.keyframe_points.foreach_set("co", [c for f, v in cl for c in (f, v[i])]); fc.update()
    sc.frame_set(1); vl.update()
    ps = puntos(r); pz = min(q.z for q in pies(r))
    return dict(posicion=[round(v, 2) for v in r.location], pies_z=round(pz, 3), alto=round(max(q.z for q in ps), 2),
                a_valla=round(min(kd.find(q)[2] for q in ps), 3), alas=[(h, e) for h, e in alas], anima_a=luchador)
