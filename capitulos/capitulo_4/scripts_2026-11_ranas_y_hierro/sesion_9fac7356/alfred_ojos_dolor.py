"""Expresion de dolor en los ojos de Alfred (la referencia del usuario): forma 'Dolor' en ojo_derecho/izquierdo_alfred.
Cada ojo: borde superior bajo por fuera que sube en curva hasta la esquina INTERIOR (cejas de dolor), y borde inferior
con una joroba hacia arriba en el centro. Se anima mientras rueda/se sacude con los insectos y mientras lo picotean los
pollos (f686-fin), con un apreton extra en cada picotazo (frame exacto, perfil de inercia) y sin tapar los parpadeos."""
import bpy, math
sc = bpy.context.scene
OJOS = ("ojo_derecho_alfred", "ojo_izquierdo_alfred")
A, RAMPA = 686, 6
FIN = sc.frame_end
ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
sc.frame_set(100)
pos = {n: bpy.data.objects[n].matrix_world.translation.copy() for n in OJOS}
medio = (pos[OJOS[0]] + pos[OJOS[1]]) / 2
TOP_FUERA, CURVA, JOROBA = 0.70, 3.0, 0.09
res = {}
for n in OJOS:
    o = bpy.data.objects[n]; sk = o.data.shape_keys; kb = sk.key_blocks
    M = o.matrix_world.to_3x3()
    vert = max(range(3), key=lambda i: abs(M.col[i].normalized().z))
    resto = [i for i in range(3) if i != vert]
    base = [v.co.copy() for v in kb["Basis"].data]
    ext = {i: (min(c[i] for c in base), max(c[i] for c in base)) for i in range(3)}
    hor = max(resto, key=lambda i: ext[i][1] - ext[i][0])               # el eje mas ancho del plano = horizontal
    sg_v = 1 if M.col[vert].z > 0 else -1
    sg_in = 1 if (M.col[hor].normalized()).dot(medio - pos[n]) > 0 else -1   # +hor apunta hacia dentro?
    k = kb.get("Dolor") or o.shape_key_add(name="Dolor", from_mix=False)
    k.relative_key = kb["Basis"]; k.slider_min, k.slider_max = 0.0, 1.0
    (x0, x1), (z0, z1) = ext[hor], ext[vert]
    for i, c in enumerate(base):
        u = (c[hor] - x0) / (x1 - x0); u = u if sg_in > 0 else 1 - u     # 0 = borde de fuera, 1 = borde interior
        v = (c[vert] - z0) / (z1 - z0); v = v if sg_v > 0 else 1 - v     # 0 = abajo, 1 = arriba
        top = TOP_FUERA + (1 - TOP_FUERA) * u ** CURVA
        bot = JOROBA * math.sin(math.pi * u)
        nv = bot + v * (top - bot)
        nv = nv if sg_v > 0 else 1 - nv
        p = c.copy(); p[vert] = z0 + nv * (z1 - z0); k.data[i].co = p
    res[n] = {"vertical": vert, "horizontal": hor, "interior_es_+": sg_in > 0}

# --- animacion: dolor desde que rueda con los insectos hasta el final, apreton en cada picotazo ---
logs = bpy.app.driver_namespace.get("_pollos_alfred_logs", {})
picos = []
if logs:
    for n_, L in logs.items():
        arm = bpy.data.objects["Armature_" + n_]; hb = arm.pose.bones["Head_M_chicken_1"]; sobre = False
        for slot, tipo, a, b in L:
            if tipo == "saltar": sobre = True; picos.append(b); continue
            if sobre and tipo == "picotear":
                zs = []
                for f in range(a, b + 1): sc.frame_set(f); zs.append((arm.matrix_world @ hb.tail).z)
                picos += [a + i for i in range(1, len(zs) - 1) if zs[i] <= zs[i - 1] and zs[i] < zs[i + 1] and zs[i] < max(zs) - 0.05]
picos = sorted(p for p in picos if p <= FIN)
PERFIL = [(0, 0.45), (2, 1.0), (5, -0.18), (8, 0.06), (11, 0.0)]
for n in OJOS:
    o = bpy.data.objects[n]; k = o.data.shape_keys.key_blocks["Dolor"]
    vals = {}
    for f in range(A - 1, FIN + 1):
        vals[f] = 0.82 * ss((f - A) / RAMPA)                              # dolor base
    for p in picos:                                                       # se aprieta en el frame del picotazo
        for off, w in PERFIL:
            if p + off <= FIN: vals[p + off] = min(1.0, vals.get(p + off, 0.82) + 0.18 * w)
    for f in sorted(vals):
        k.value = vals[f]; k.keyframe_insert("value", frame=f)
    k.value = 0.0
    sk = o.data.shape_keys
    for c in sk.animation_data.action.layers[0].strips[0].channelbag(sk.animation_data.action_slot).fcurves:
        if c.data_path == 'key_blocks["Dolor"].value':
            for kp in c.keyframe_points: kp.interpolation = "LINEAR"
res["picotazos"] = len(picos)
result = res
