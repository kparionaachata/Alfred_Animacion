"""Plumas que se desprenden de los pollos al aletear y picotear sobre Alfred (objetos/vanilla/feather, escala 0.2).
Fisica de pluma (inercia-accion-reaccion): sale de la punta del ala con la velocidad del aleteo (afuera y arriba),
el aire la frena enseguida (arrastre fuerte), cae a velocidad terminal baja balanceandose y girando, y al tocar el
suelo o la espalda de Alfred se queda quieta y plana."""
import bpy, math, random
from mathutils import Vector, Euler
sc = bpy.context.scene
logs = bpy.app.driver_namespace["_pollos_alfred_logs"]
base = bpy.data.objects["pluma_base"]; col = bpy.data.collections["plumas_pollos"]
base.hide_viewport = base.hide_render = True
for o in [o for o in col.objects if o.name.startswith("pluma_") and o != base]: bpy.data.objects.remove(o)
rnd = random.Random(11)
G = 9.81 / 24 ** 2
FIN = sc.frame_end
dg = bpy.context.evaluated_depsgraph_get()
excl = set()
for c in ("pollo_relleno", "pollos_alfred", "plumas_pollos", "insectos_alfred", "cerdo_relleno"):
    if c in bpy.data.collections: excl |= {o.name for o in bpy.data.collections[c].all_objects}
suelo_cache = {}
def suelo(x, y, f):
    """altura de apoyo: espalda de Alfred (tirado desde ~798) o el bloque de abajo"""
    if f >= 888 and -19.78 <= x <= -19.02 and -6.35 <= y <= -4.55: return 11.69
    k = (math.floor(x), math.floor(y))
    if k not in suelo_cache:
        o = Vector((k[0] + 0.5, k[1] + 0.5, 30)); z = 11.0
        for _ in range(8):
            h = sc.ray_cast(dg, o, Vector((0, 0, -1)))
            if not h[0]: break
            if h[4].name in excl or h[2].z < 0.5 or h[4].name.startswith("Mesh_"): o = h[1] - Vector((0, 0, 0.001)); continue
            z = round(h[1].z); break
        suelo_cache[k] = z
    return suelo_cache[k] + 0.004

# momentos de desprendimiento
salidas = []   # (frame, pollo)
ALETEOS = bpy.app.driver_namespace["_pollos_aleteos"]
for n, vs in ALETEOS.items():
    for a, b in vs:
        for _ in range(6): salidas.append((rnd.choice((8, 24, 40, 56)) + a + rnd.randint(-1, 2), n))   # en las bajadas de ala
for n, L in logs.items():
    for slot, tipo, a, b in L:
        if a < 870: continue          # solo sobre Alfred (desde que se tiran, ~877)
        if tipo == "picotear" and rnd.random() < 0.35:
            salidas.append((rnd.randint(a + 6, b - 4), n))
        elif tipo == "saltar":
            salidas.append((b, n))            # al caer sobre Alfred
salidas.sort()
plumas = []
for i, (f0, n) in enumerate(salidas):
    if f0 >= FIN - 2: continue
    sc.frame_set(f0)
    arm = bpy.data.objects["Armature_" + n]; pb = arm.pose.bones
    lado = rnd.choice("RL")
    ala = arm.matrix_world @ pb["Elbow_%s_chicken_1" % lado].tail
    pecho = arm.matrix_world @ pb["Chest_M_chicken_1"].head
    fuera = (ala - pecho); fuera.z = 0
    fuera = fuera.normalized() if fuera.length > 1e-4 else Vector((1, 0, 0))
    p = ala + Vector((rnd.uniform(-0.05, 0.05), rnd.uniform(-0.05, 0.05), rnd.uniform(0, 0.08)))
    v = fuera * rnd.uniform(0.07, 0.11) + Vector((rnd.uniform(-0.02, 0.02), rnd.uniform(-0.02, 0.02), rnd.uniform(0.05, 0.08)))
    o = bpy.data.objects.new("pluma_%02d" % i, base.data); col.objects.link(o)
    for m in base.modifiers:
        mm = o.modifiers.new(m.name, m.type)
        for attr in ("thickness", "offset", "use_even_offset"):
            if hasattr(m, attr): setattr(mm, attr, getattr(m, attr))
    o.scale = (0.2, 0.2, 0.2); o.rotation_mode = "XYZ"
    rz = rnd.uniform(0, 6.28); wz = rnd.uniform(-0.18, 0.18)
    ax, ay = rnd.uniform(0.4, 0.9), rnd.uniform(0.4, 0.9); fr = rnd.uniform(0.18, 0.3); ph = rnd.uniform(0, 6.28)
    # oculta antes de salir
    o.hide_viewport = o.hide_render = True
    o.keyframe_insert("hide_viewport", frame=f0 - 1); o.keyframe_insert("hide_render", frame=f0 - 1)
    o.hide_viewport = o.hide_render = False
    o.keyframe_insert("hide_viewport", frame=f0); o.keyframe_insert("hide_render", frame=f0)
    quieta = None; rx = ry = 0.0
    for f in range(f0, FIN + 1):
        if quieta is None:
            t = f - f0
            v.z -= G * 0.6                        # peso de la pluma
            v *= 0.92 if t < 10 else 0.85         # sale disparada del ala ~10 f y luego el aire la frena
            v.z = max(v.z, -0.012)                # velocidad terminal ~0.3 m/s
            bal = Vector((math.cos(t * fr + ph), math.sin(t * fr * 0.8 + ph), 0)) * 0.006 * min(1.0, t / 6)
            p = p + v + bal
            wz *= 0.985; rz += wz + 0.03 * math.sin(t * fr + ph)
            rx = ax * math.sin(t * fr + ph); ry = ay * math.sin(t * fr * 0.8 + ph + 1.3)
            zs = suelo(p.x, p.y, f)
            if p.z <= zs:
                p.z = zs; quieta = f; rx0, ry0 = rx, ry
        else:
            k = min(1.0, (f - quieta) / 4.0)       # se asienta plana en 4 frames
            rx, ry = rx0 * (1 - k), ry0 * (1 - k)
        o.location = p; o.rotation_euler = (rx, ry, rz)
        o.keyframe_insert("location", frame=f); o.keyframe_insert("rotation_euler", frame=f)
        if quieta is not None and f >= quieta + 4: break
    ad = o.animation_data
    for fc in ad.action.layers[0].strips[0].channelbags[0].fcurves:
        for kp in fc.keyframe_points: kp.interpolation = "CONSTANT" if fc.data_path.startswith("hide") else "LINEAR"
    plumas.append((o.name, n, f0, quieta, [round(c, 2) for c in p]))
result = {"plumas": len(plumas), "detalle": plumas[:8]}
