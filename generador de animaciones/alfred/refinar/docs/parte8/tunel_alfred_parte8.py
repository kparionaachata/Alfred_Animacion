# -*- coding: utf-8 -*-
"""Parte 8: Alfred cava un tunel irregular desde (-104.5, -69.5, 9.0) hacia el oeste hasta una cueva natural (plan en `tunel_plan.json`: 13 columnas x -108..-120, 64 celdas).
Reutiliza las animaciones existentes de las poses portables (por frame):
  - palada: `poses/pala_pozo_f843_983` (saca la pala de la espalda f855-879, ciclo de palada f893-906 (14 f, impacto en f893/f907), guarda la pala f945-959);
  - picar = la animacion de usar el hacha (`poses/golpea_rompe_madera_f1016_1063`, ciclo f1026-1037 (12 f, impacto f1026)) con el PICO (`wooden_pickaxe`) en lugar del hacha.
Herramienta segun el bloque: tierra/pasto -> pala; piedra -> pico. Cada palada/golpe rompe hasta 2 celdas de la columna en el frame del impacto; despues Alfred avanza 1 bloque.
Salidas: acciones de `alfred` (raiz) y `armature` (huesos), Child Of `Mano`/`Espalda` de `stone_shovel` y `wooden_pickaxe`, y `docs/parte8/tunel_eventos.json` (frame -> celdas) para `tunel_geometria_parte8.py`.
Se ejecuta DENTRO de Blender con exec (escena `base_parte_8.blend`). Repetible (rehace las acciones de Alfred y de las herramientas)."""
import bpy, json, math
from mathutils import Matrix, Vector

R = "C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/"
sc = bpy.context.scene; vl = bpy.context.view_layer
ROOT = bpy.data.objects["alfred"]; ARM = bpy.data.objects["armature"]
PLAN = json.load(open(R + "docs/parte8/tunel_plan.json", encoding="utf-8"))
COLS = PLAN["cols"]; CELLS = {int(k): [tuple(c) for c in v] for k, v in PLAN["cells"].items()}; TIPO = PLAN["tipo"]
START = (-104.5, -69.5); Z0 = 9.0
CY = {x: (-70 if x >= -109 else (-69 if x >= -112 else -68)) for x in COLS}   # fila central de cada columna
ss = lambda t: 0.0 if t <= 0 else (1.0 if t >= 1 else t * t * (3 - 2 * t))

# ---------------- poses ----------------
def cargar(carpeta, pref, a, b):
    out = {}
    for f in range(a, b + 1):
        p = json.load(open(R + "poses/%s/%s%d.json" % (carpeta, pref, f), encoding="utf-8"))["poses"][0]
        out[f] = {n: tuple(v["local_space"]["rotation_euler_deg"][k] for k in "xyz") + tuple(v["local_space"]["location"][k] for k in "xyz") + tuple(v["local_space"]["scale"][k] for k in "xyz") for n, v in p["bones"].items()}
    return out
PA = cargar("pala_pozo_f843_983", "pala_pozo_f", 843, 983)
HA = cargar("golpea_rompe_madera_f1016_1063", "golpea_rompe_madera_f", 1016, 1063)
BONES = list(PA[843].keys())
def mezcla(p, q, t): return {n: tuple(a + (b - a) * t for a, b in zip(p[n], q[n])) for n in p}
REPOSO = PA[843]; LISTO = PA[879]                                              # de pie con los brazos colgando / con la pala hacia abajo
def pala_ciclo(c): return PA[893 + (c % 14)]
def pico_ciclo(c): return HA[1026 + (c % 12)]

# ---------------- agarres ----------------
def M4(v): return Matrix([v[0:4], v[4:8], v[8:12], v[12:16]])
CFG_P = json.load(open(R + "configuraciones/guiones/configuracion_portable_pala_pozo_f843_983.json", encoding="utf-8"))["objetos"][0]
CFG_H = json.load(open(R + "configuraciones/guiones/configuracion_portable_golpea_rompe_madera_f1016_1063.json", encoding="utf-8"))["objetos"][0]
RAB = json.load(open(R + "docs/acciones/rel_espalda_alfred_blend.json", encoding="utf-8"))["herramientas"]
def conescala(m, s):
    l, q, _ = m.decompose(); return Matrix.Translation(l) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((s, s, s, 1))
ESC_MANO = float(globals().get("ESC_MANO", 0.7))
GRIP_PALA = conescala(M4(CFG_P["agarres"]["cavar"]["matriz"]), ESC_MANO)
ALTO = M4(CFG_H["agarres"]["alto"]["matriz"]); IMPACTO = M4(CFG_H["agarres"]["impacto"]["matriz"])
def grip_pico(relx):                                                            # mezcla alto <-> impacto segun el codo derecho (igual que el hacha)
    t = max(0.0, min(1.0, (relx - (-43.0)) / (30.0 - (-43.0))))
    la, qa, _ = ALTO.decompose(); li, qi, _ = IMPACTO.decompose()
    return Matrix.Translation(la.lerp(li, t)) @ qa.slerp(qi, t).to_matrix().to_4x4() @ Matrix.Diagonal((ESC_MANO, ESC_MANO, ESC_MANO, 1))
def grip_de(herr, pose): return GRIP_PALA if herr == "pala" else grip_pico(pose["Rightelbow_alfred"][0])
def mixM(A, B, t):
    la, qa, sa = A.decompose(); lb, qb, sb = B.decompose()
    return Matrix.Translation(la.lerp(lb, t)) @ qa.slerp(qb, t).to_matrix().to_4x4() @ Matrix.Diagonal(tuple(sa.lerp(sb, t)) + (1,))

# ---------------- linea de tiempo ----------------
TL = {}; EVENTOS = []; ACC = []
cur = [1]; ult = {"pose": REPOSO, "x": START[0], "y": START[1], "rz": 90.0}
def rz_hacia(x, y, tx, ty): return math.degrees(math.atan2(-(tx - x), (ty - y)))
def poner(pose, x, y, rz, z=None):
    TL[cur[0]] = dict(pose=pose, x=x, y=y, rz=rz, z=(ult.get('z', Z0) if z is None else z)); ult.update(pose=pose, x=x, y=y, rz=rz, z=TL[cur[0]]['z']); cur[0] += 1
def piernas(base, fase, amp):
    p = dict(base); a = 24.0 * amp; s = math.sin(fase); c = math.cos(fase)
    def sumar(n, dx):
        v = list(p[n]); v[0] += dx; p[n] = tuple(v)
    sumar("RightUpLeg_alfred", a * s); sumar("LeftUpLeg_alfred", -a * s)
    sumar("Rightknee_alfred", -max(0.0, -c) * 28 * amp); sumar("Leftknee_alfred", -max(0.0, c) * 28 * amp)
    return p
def caminar(x1, y1, tx, ty, nf, pose_base, ciclo=12.0):
    x0, y0, rz0 = ult["x"], ult["y"], ult["rz"]; rz1 = rz_hacia(x1, y1, tx, ty); p0 = ult["pose"]
    for i in range(nf):
        u = (i + 1) / nf; amp = min(1.0, (i + 1) / 3.0, (nf - i) / 3.0 + 0.15)
        base = mezcla(p0, pose_base, ss(min(1.0, (i + 1) / 4.0)))
        poner(piernas(base, i / ciclo * 2 * math.pi, amp), x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, rz0 + (rz1 - rz0) * ss(min(1.0, u * 1.5)))
def secuencia(seq, x, y, rz, mezcla_in=3):
    p0 = ult["pose"]
    for i, p in enumerate(seq):
        poner(mezcla(p0, p, ss((i + 1) / (mezcla_in + 1))) if i < mezcla_in else p, x, y, rz)
def quedarse(n, pose, x, y, rz): secuencia([pose] * n, x, y, rz, mezcla_in=min(4, n))

def pos_columna(x): return x + 1.55, CY[x] + 0.5                              # donde se para Alfred para cavar la columna x (casilla [x, x+1])
def grupos(x):
    cs = sorted(CELLS[x], key=lambda c: (TIPO["%d,%d,%d" % (x, c[0], c[1])] == "piedra", c[1], abs(c[0] - CY[x])))
    out = []; g = []
    tp = lambda c: TIPO["%d,%d,%d" % (x, c[0], c[1])]
    for c in cs:
        if g and (len(g) >= 2 or tp(g[0]) != tp(c)): out.append(g); g = []
        g.append(c)
    if g: out.append(g)
    return [("pico" if tp(g[0]) == "piedra" else "pala", [(x, y, z) for (y, z) in g]) for g in out]

def tomar(herr, x, y, rz):                                                      # clip de la pala f855-879: la mano va a la espalda (f857-864), agarra (f865-868) y la trae al frente
    t0 = cur[0]; secuencia([PA[f] for f in range(855, 880)], x, y, rz, mezcla_in=4); ACC.append((t0 + (866 - 855), herr, "toma"))
def guardar(herr, x, y, rz):                                                    # clip de la pala f945-959: el brazo va a la espalda y la suelta (f956); luego vuelve a reposo
    t0 = cur[0]; secuencia([PA[f] for f in range(945, 960)], x, y, rz, mezcla_in=3); ACC.append((t0 + (956 - 945), herr, "guarda"))
    secuencia([mezcla(PA[959], REPOSO, ss((i + 1) / 10.0)) for i in range(10)], x, y, rz, mezcla_in=0)

def construir():
    TL.clear(); EVENTOS.clear(); ACC.clear(); cur[0] = 1; ult.update(pose=REPOSO, x=START[0], y=START[1], rz=90.0)
    quedarse(12, REPOSO, START[0], START[1], 90.0)
    x0, y0 = pos_columna(COLS[0]); caminar(x0, y0, x0 - 5, y0, 22, REPOSO); quedarse(4, REPOSO, x0, y0, ult["rz"])
    herr = None; ultimo = None
    for k, x in enumerate(COLS):
        xr, yr = pos_columna(x); rzc = rz_hacia(xr, yr, x + 0.5, CY[x] + 0.5)
        if k > 0:
            caminar(xr, yr, x + 0.5, CY[x] + 0.5, 9, LISTO if herr == "pala" else (HA[1022] if herr == "pico" else REPOSO)); ultimo = None
        for (th, celdas) in grupos(x):
            if herr != th:
                if herr is not None: guardar(herr, xr, yr, rzc)
                tomar(th, xr, yr, rzc); herr = th; ultimo = None
                if th == "pico": secuencia([mezcla(LISTO, HA[1022], ss((i + 1) / 7.0)) for i in range(7)], xr, yr, rzc, mezcla_in=0)
            n, imp = (14, 6) if herr == "pala" else (12, 4)
            ciclo = pala_ciclo if herr == "pala" else pico_ciclo
            t_ini = cur[0]; secuencia([ciclo(8 + i) for i in range(n)], xr, yr, rzc, mezcla_in=(0 if ultimo == (herr, x) else 5)); ultimo = (herr, x)
            EVENTOS.append((t_ini + imp, celdas))
    xr, yr = pos_columna(COLS[-1]); guardar(herr, xr, yr, ult["rz"]); quedarse(24, REPOSO, xr, yr, ult["rz"])
    return cur[0] - 1

# ---------------- acciones rapidas (slotted) ----------------
def accion(obj, nombre, canales, grupos=None):
    """canales: {(data_path, indice): [(frame, valor), ...]}; crea una accion nueva con claves LINEALES y la asigna."""
    if obj.animation_data is None: obj.animation_data_create()
    ant = obj.animation_data.action
    obj.animation_data.action = None
    if ant is not None and ant.users == 0: bpy.data.actions.remove(ant)
    a = bpy.data.actions.new(nombre); slot = a.slots.new(id_type='OBJECT', name=obj.name); layer = a.layers.new("Capa"); strip = layer.strips.new(type='KEYFRAME'); cb = strip.channelbag(slot, ensure=True)
    for (dp, i), pts in canales.items():
        g = (grupos or {}).get(dp)
        fc = cb.fcurves.new(dp, index=i, group_name=g) if g else cb.fcurves.new(dp, index=i)
        fc.keyframe_points.add(len(pts)); fc.keyframe_points.foreach_set("co", [v for p in pts for v in p])
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
        fc.update()
    obj.animation_data.action = a; obj.animation_data.action_slot = slot
    return a

def matrices_en(t):                                                              # (mano derecha, Spine1) en mundo con la pose del frame t (sin claves en el armature)
    d = TL[t]; ROOT.location = (d["x"], d["y"], d.get("z", Z0)); ROOT.rotation_euler = (0, 0, math.radians(d["rz"]))
    for n, v in d["pose"].items():
        pb = ARM.pose.bones[n]; pb.rotation_mode = 'XYZ'; pb.rotation_euler = tuple(math.radians(a) for a in v[0:3]); pb.location = v[3:6]; pb.scale = v[6:9]
    vl.update()
    return (ARM.matrix_world @ ARM.pose.bones["Rightelbow_alfred"].matrix).copy(), (ARM.matrix_world @ ARM.pose.bones["Spine1_alfred"].matrix).copy()

def aplicar(etapa2=False):
    fin = construir()
    if etapa2: fin = construir2()
    return _aplicar_tl(fin)

def _aplicar_tl(fin):
    # --- herramientas: constraints y matrices de transicion (se calculan ANTES de poner claves) ---
    sh = bpy.data.objects["stone_shovel"]; pk = bpy.data.objects["wooden_pickaxe"]
    REL_PALA = sh.matrix_basis.copy()                                           # el sitio actual de la pala en la espalda (Child Of `Espalda`, inverse identidad)
    for o in (sh, pk):
        if o.animation_data and o.animation_data.action: o.animation_data.action = None
        o.rotation_mode = 'QUATERNION'
        for c in list(o.constraints): o.constraints.remove(c)
        for nom, hueso in (("Espalda", "Spine1_alfred"), ("Mano", "Rightelbow_alfred")):
            c = o.constraints.new('CHILD_OF'); c.name = nom; c.target = ARM; c.subtarget = hueso; c.inverse_matrix = Matrix.Identity(4); c.influence = 1.0 if nom == "Espalda" else 0.0
    REL = {"pala": REL_PALA, "pico": M4(RAB["wooden_pickaxe"]["matriz"])}
    OBJ = {"pala": sh, "pico": pk}
    M_ = {}
    for (tacc, herr, tipo) in ACC:
        for t in range(tacc - 4, tacc + 5):
            if t in TL and t not in M_: M_[t] = matrices_en(t)
    B = {"pala": {1: REL["pala"]}, "pico": {1: REL["pico"]}}
    for (tacc, herr, tipo) in ACC:
        if tipo == "toma":
            hand, sp1 = M_[tacc]; B0 = hand.inverted() @ (sp1 @ REL[herr])
            B[herr][tacc - 1] = REL[herr]; B[herr][tacc] = B0
            for i in range(1, 5): B[herr][tacc + i] = mixM(B0, grip_de(herr, TL[tacc + i]["pose"]), i / 4.0)
        else:
            for i in range(4, -1, -1):                                          # los 4 frames anteriores: del agarre a la pose de la espalda vista desde la mano
                t = tacc - i; hand, sp1 = M_[t]; Bb = hand.inverted() @ (sp1 @ REL[herr])
                B[herr][t] = mixM(grip_de(herr, TL[t]["pose"]), Bb, (4 - i) / 4.0)
            B[herr][tacc + 1] = REL[herr]
    # --- claves de Alfred ---
    can = {}; ts = sorted(TL)
    for ax in range(3):
        can[("location", ax)] = [(t, (TL[t]["x"], TL[t]["y"], TL[t].get("z", Z0))[ax]) for t in ts]
    can[("rotation_euler", 2)] = [(t, math.radians(TL[t]["rz"])) for t in ts]
    a_root = accion(ROOT, "tunel_alfred_root", can)
    can = {}
    for n in BONES:
        for j, (dp, ax) in enumerate([("rotation_euler", 0), ("rotation_euler", 1), ("rotation_euler", 2), ("location", 0), ("location", 1), ("location", 2), ("scale", 0), ("scale", 1), ("scale", 2)]):
            can[('pose.bones["%s"].%s' % (n, dp), ax)] = [(t, (math.radians(TL[t]["pose"][n][j]) if dp == "rotation_euler" else TL[t]["pose"][n][j])) for t in ts]
    for pb in ARM.pose.bones: pb.rotation_mode = 'XYZ'
    a_arm = accion(ARM, "tunel_alfred_armature", can, grupos={k[0]: k[0].split('"')[1] for k in can})
    # --- claves de las herramientas ---
    for herr, o in OBJ.items():
        cambios = sorted((tacc, tipo) for (tacc, h, tipo) in ACC if h == herr)
        for i in range(0, len(cambios) - 1, 2):                                 # en la mano entre la toma y la guarda: una clave por frame
            for t in range(cambios[i][0] + 5, cambios[i + 1][0] - 4): B[herr].setdefault(t, grip_de(herr, TL[t]["pose"]))
        tf = sorted(B[herr]); can = {}
        for ax in range(3): can[("location", ax)] = [(t, B[herr][t].to_translation()[ax]) for t in tf]; can[("scale", ax)] = [(t, B[herr][t].to_scale()[ax]) for t in tf]
        for ax in range(4): can[("rotation_quaternion", ax)] = [(t, B[herr][t].to_quaternion()[ax]) for t in tf]
        inf_e = [(1, 1.0)]; inf_m = [(1, 0.0)]
        for (tacc, h, tipo) in sorted(ACC):
            if h != herr: continue
            if tipo == "toma": inf_e += [(tacc - 1, 1.0), (tacc, 0.0)]; inf_m += [(tacc - 1, 0.0), (tacc, 1.0)]
            else: inf_e += [(tacc, 0.0), (tacc + 1, 1.0)]; inf_m += [(tacc, 1.0), (tacc + 1, 0.0)]
        can[('constraints["Espalda"].influence', 0)] = sorted(set(inf_e)); can[('constraints["Mano"].influence', 0)] = sorted(set(inf_m))
        accion(o, "tunel_%s" % herr, can)
        for fc in o.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
            if "influence" in fc.data_path:
                for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
    json.dump({"eventos": [{"frame": f, "celdas": [list(c) for c in cs]} for f, cs in EVENTOS], "acciones": [{"frame": f, "herramienta": h, "tipo": t} for f, h, t in sorted(ACC)], "fin": fin}, open(R + "docs/parte8/tunel_eventos.json", "w"))
    sc.frame_set(1)
    return {"fin": fin, "golpes": len(EVENTOS), "acc": sorted(ACC)}


# =====================================================================================================
# ETAPA 2 (2026-10-10): Alfred sigue por la cueva y cava/pica hasta la coordenada (-128.5, -67.5, 9.0) = cara inferior del bloque de piedra (-129, -68, 9),
# techo de una galeria diagonal que baja hacia el oeste. Ruta (`tunel2_ruta.json`, Dijkstra sobre la rejilla de la cueva: pasos con suelo solido, 3 de alto, cavar cuesta 1 por celda):
# por el borde norte de la galeria (suelo mas alto, y -66/-67) hasta (-130, -68, 9), con ~21 celdas por cavar; al final rompe el bloque de la coordenada mirando al este.
# Se llama `construir2()` DESPUES de `construir()` (continua la misma linea de tiempo y la lista de rupturas).
def es_piedra_celda(c):
    so = bpy.data.objects["Stone"]; mw = so.matrix_world; p = Vector((c[0] + .5, c[1] + .5, c[2] + .5))
    return sum(1 for v in so.data.vertices if (mw @ v.co - p).length < 0.9) >= 3
def construir2():
    """RECTO por y = -67.5 (fila de celdas y -68) desde el final del tunel (x -120) hasta la coordenada (-129.5, -67.5, 8.0): sin curvas. Alfred camina por la cueva (el piso baja en diagonal, la raiz baja de z 9 a 8 en linea recta)
    y cava/pica solo las celdas SOLIDAS del corredor (z 8-10) que encuentra; al final rompe el bloque de la coordenada (-130, -68, 8) y entra en el hasta quedar en (-129.5, -67.5, 8.0)."""
    G = json.load(open(R + "docs/parte8/tunel2_rejilla.json", encoding="utf-8"))
    sol = lambda c: G.get("%d,%d,%d" % c, 1)
    YC = -68; XA = -120; XB = -130                                                  # celdas: de (-120) a la celda de la coordenada (-130)
    zraiz = lambda x: 9.0 - (XA - x) / float(XA - XB) * 1.0                          # z de la raiz en el centro de la celda x (9.0 -> 8.0 en linea recta)
    cx = lambda x: (x + 0.5, YC + 0.5, zraiz(x + 0.5 if False else x))
    herr = None; ultimo = None
    xr0, yr0 = ult["x"], ult["y"]
    q = XA; xa, ya, za = cx(q)
    caminar(xa, ya, xa - 1, ya, 10, REPOSO); TL[cur[0] - 1]["z"] = za
    def a_pie(qa, qb, nf=10, pose=REPOSO):
        xa_, ya_, za_ = cx(qa); xb_, yb_, zb_ = cx(qb); rz0 = ult["rz"]; p0_ = ult["pose"]
        for i in range(nf):
            u = (i + 1) / nf; amp = min(1.0, (i + 1) / 3.0, (nf - i) / 3.0 + 0.15); base = mezcla(p0_, pose, ss(min(1.0, (i + 1) / 4.0)))
            poner(piernas(base, i / 12.0 * 2 * math.pi, amp), xa_ + (xb_ - xa_) * u, ya_, 90.0, z=za_ + (zb_ - za_) * u)
    for xq in range(XA, XB, -1):
        xn = xq - 1; xa_, ya_, za_ = cx(xq)
        nuevos = [(xn, YC, z) for z in (8, 9, 10) if sol((xn, YC, z))]
        if nuevos:
            th = "pico" if any(es_piedra_celda(c) for c in nuevos) else (herr or "pala")
            for i in range(0, len(nuevos), 2):
                grp = nuevos[i:i + 2]
                if herr != th:
                    if herr is not None: guardar(herr, xa_, ya_, 90.0)
                    tomar(th, xa_, ya_, 90.0); herr = th; ultimo = None
                    if th == "pico": secuencia([mezcla(LISTO, HA[1022], ss((j + 1) / 7.0)) for j in range(7)], xa_, ya_, 90.0, mezcla_in=0)
                n, imp = (14, 6) if herr == "pala" else (12, 4); ciclo = pala_ciclo if herr == "pala" else pico_ciclo
                t_ini = cur[0]; secuencia([ciclo(8 + j) for j in range(n)], xa_, ya_, 90.0, mezcla_in=(0 if ultimo == (herr, xq) else 5)); ultimo = (herr, xq)
                EVENTOS.append((t_ini + imp, grp))
        a_pie(xq, xn, pose=(LISTO if herr == "pala" else (HA[1022] if herr == "pico" else REPOSO))); ultimo = None
    xa_, ya_, za_ = cx(XB)
    if herr is not None: guardar(herr, xa_, ya_, 90.0)
    quedarse(24, REPOSO, xa_, ya_, 90.0)
    return cur[0] - 1

