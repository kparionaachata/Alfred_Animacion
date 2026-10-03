"""Se ejecuta DENTRO de Blender (exec). SEGUNDA RUTA de camara enfocada en las expresiones de Alfred: crea `Camara_Alfred` + `Cam_Foco_Alfred` (sin tocar `Camara_Cinematica`/`Camera.001`)
e inserta keyframes de ubicacion, mira y focal a partir de `camara_alfred_parte2.json` (compose_camara_alfred_parte2.py). NO renderiza. Idempotente.
Diferencias con importar_camara.py: (1) para cada muestra reune hasta K posiciones candidatas LIBRES (la linea de vista a la cabeza de Alfred y a 3 puntos laterales/altos no la tapa
ningun arbol/hoja/bloque, y no hay nada a menos de 0.6 m de la camara) y elige la secuencia de candidatas con Viterbi, penalizando saltos entre muestras vecinas (no gira de golpe);
(2) despues limita la velocidad de giro de la mirada (LIM grados por frame) suavizando localmente camara y punto de mira.
Como el raycast es lento, se ejecuta por etapas (cada llamada procesa ~70 s):
    exec(compile(open(RUTA, encoding="utf-8").read(), RUTA, "exec")); print(paso())      # repetir hasta que diga "listo para finalizar"
    print(finalizar())                                                                    # Viterbi + limite de giro + keyframes
"""
import bpy, json, math, os, time
from mathutils import Vector

BASE = r"C:\Users\user\Desktop\Alfred_Animacion"
K = 30                                                                     # candidatas libres por muestra
LIM = 0.45                                                                 # grados por frame maximos de giro de la mirada (solo se informa; el Viterbi ya lo penaliza)
ITER_MAX = 0                                                               # pasadas de suavizado posterior (0 = no mover las camaras elegidas, que ya son validas)
ST = bpy.app.driver_namespace.setdefault("camalf", {})
sc = bpy.context.scene
PERSONAJES = {"Object", "a", "jerry", "Dog_001_rig"} | {f"zombie_{n}" for n in range(1, 6)} | {f"zombie_{n}_Armature" for n in range(1, 6)} | {f"armature_face_zombie_{n}" for n in range(1, 6)}
X0, X1, Y0, Y1, Z0, Z1 = -99.0, -93.0, -112.0, -106.0, 13.5, 17.0           # volumen del refugio
DIRS = [Vector(v) for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]


def es_personaje(o):
    while o is not None:
        if o.name in PERSONAJES or o.name.startswith(("ojo_", "antorcha", "torch", "smoke", "Cam_Foco", "Camara_")): return True
        o = o.parent
    return False


def ignora(obj, f):
    if es_personaje(obj) or obj.name.startswith("Suzanne") or "Water" in obj.name: return True                  # el agua no tapa la vista
    ap = ST["APARECE"]
    if obj.name in ap and f is not None and (f < ap[obj.name] or f >= 2000): return True                         # bloque aun inexistente / desde f2000 el sujeto ES el refugio
    return False


def libre(dg, origen, destino, f):
    """True si la linea origen-destino no la tapa nada (se atraviesan agua, personajes y bloques aun inexistentes)."""
    d = destino - origen; L = d.length; d.normalize(); o = origen.copy(); rec = 0.0
    for _ in range(12):
        ok, loc, nor, idx, obj, mat = sc.ray_cast(dg, o, d, distance=L - rec)
        if not ok: return True
        if not ignora(obj, f): return False
        rec += (loc - o).length + 0.05; o = loc + d * 0.05
    return True


def suelo(dg, x, y, zmax=80.0):
    ok, loc, nor, idx, obj, mat = sc.ray_cast(dg, Vector((x, y, zmax)), Vector((0, 0, -1)), distance=zmax + 20)
    return loc.z if ok else None


def valida(dg, c, t, f):
    """posicion de camara c valida para el punto de mira t en el frame f."""
    if X0 - 0.6 < c.x < X1 + 0.6 and Y0 - 0.6 < c.y < Y1 + 0.6 and Z0 < c.z < Z1 + 1.5 and 1494 <= f < 2000: return False         # dentro o pegada al refugio (solo existe desde el primer bloque, f1494)
    g = suelo(dg, c.x, c.y)
    if g is not None and c.z < g + 0.8: return False                                                                    # bajo/pegada al suelo
    h = (c - t); lado = Vector((-h.y, h.x, 0.0))
    lado = lado.normalized() * 0.35 if lado.length > 1e-6 else Vector((0.35, 0, 0))
    for p in (t, t + Vector((0, 0, 0.35)), t + lado, t - lado):
        if not libre(dg, p, c, f): return False
    for d in DIRS:                                                                                                       # nada a menos de 0.6 m de la camara (hojas/troncos pegados)
        ok, loc, nor, idx, obj, mat = sc.ray_cast(dg, c, d, distance=0.6)
        if ok and not ignora(obj, f): return False
    return True


def bloqueos(dg, c, t, f):
    """numero de comprobaciones que falla la posicion c (0 = valida); sirve para elegir la menos mala cuando no hay ninguna libre."""
    n = 0
    if X0 - 0.6 < c.x < X1 + 0.6 and Y0 - 0.6 < c.y < Y1 + 0.6 and Z0 < c.z < Z1 + 1.5 and 1494 <= f < 2000: n += 3
    g = suelo(dg, c.x, c.y)
    if g is not None and c.z < g + 0.8: n += 3
    h = (c - t); lado = Vector((-h.y, h.x, 0.0)); lado = lado.normalized() * 0.35 if lado.length > 1e-6 else Vector((0.35, 0, 0))
    for p in (t, t + Vector((0, 0, 0.35)), t + lado, t - lado):
        if not libre(dg, p, c, f): n += 1
    for d in DIRS:
        ok, loc, nor, idx, obj, mat = sc.ray_cast(dg, c, d, distance=0.6)
        if ok and not ignora(obj, f): n += 1
    return n


def preparar():
    J = json.load(open(os.path.join(BASE, r"generador de animaciones\alfred\refinar\docs\parte2\camara_alfred_parte2.json"), encoding="utf-8"))
    BLOQ = json.load(open(os.path.join(BASE, "generador de animaciones", "alfred", "refinar", "docs", "parte2", "refugio_bloques.json"), encoding="utf-8"))["bloques"]
    ST.clear(); ST.update(J=J, APARECE={f"refugio_bloque_{i:02d}": b["frame"] for i, b in enumerate(BLOQ)}, i=0, cands=[], n_libres=0, n_sin=0)
    sc.frame_set(J["N"])                                                       # estado final: todos los bloques del refugio visibles (obstaculos conservadores)


def paso(budget=70.0):
    if "J" not in ST: preparar()
    J = ST["J"]; ms = J["muestras"]; t0 = time.time()
    if sc.frame_current != J["N"]: sc.frame_set(J["N"])
    dg = bpy.context.evaluated_depsgraph_get()
    while ST["i"] < len(ms) and time.time() - t0 < budget:
        m = ms[ST["i"]]; f = m["f"]; t = Vector(m["mira"]); c0 = Vector(m["cam"]); v = c0 - t; d0 = v.length
        az0 = math.atan2(v.y, v.x); el0 = math.asin(v.z / d0) if d0 > 1e-6 else 0.0
        grid = []
        for dael in (0, 8, 16, 24, 32):
            for daz in (0, 10, -10, 20, -20, 30, -30, 40, -40, 50, -50, 60, -60):
                for ds in (1.0, 0.8, 0.65):
                    grid.append((abs(daz) / 10.0 + dael / 8.0 + (1 - ds) * 8.0, daz, dael, ds))
        grid.sort(); libres = []
        for dev, daz, dael, ds in grid:
            a_ = az0 + math.radians(daz); e_ = min(math.radians(78), el0 + math.radians(dael)); d = max(1.8, d0 * ds)
            c = t + Vector((d * math.cos(e_) * math.cos(a_), d * math.cos(e_) * math.sin(a_), d * math.sin(e_)))
            if valida(dg, c, t, f):
                libres.append((dev, c))
                if len(libres) >= K: break
        if not libres:                                                         # sin ninguna libre: las K "menos malas" (coste = desviacion + 6 x comprobaciones falladas), para que la camara siga una trayectoria continua
            ST["n_sin"] += 1; pun = []
            for dev, daz, dael, ds in grid:
                a_ = az0 + math.radians(daz); e_ = min(math.radians(78), el0 + math.radians(dael)); d = max(1.8, d0 * ds)
                c = t + Vector((d * math.cos(e_) * math.cos(a_), d * math.cos(e_) * math.sin(a_), d * math.sin(e_))); pun.append((dev + 6.0 * bloqueos(dg, c, t, f), c))
            pun.sort(key=lambda z: z[0]); libres = [(100.0 + p0, c) for p0, c in pun[:K]]
        ST["cands"].append((c0.copy(), libres, t.copy(), f)); ST["i"] += 1
    return f"procesadas {ST['i']}/{len(ms)} muestras ({ST['n_sin']} sin posicion libre)" + (" - listo para finalizar" if ST["i"] >= len(ms) else " - repetir paso()")


def ang(t, c):
    """azimut y elevacion (grados) de la camara c respecto al punto de mira t."""
    v = c - t; return (math.degrees(math.atan2(v.y, v.x)), math.degrees(math.atan2(v.z, math.hypot(v.x, v.y))))


def finalizar():
    from bpy_extras import anim_utils
    J = ST["J"]; ms = J["muestras"]; cands = ST["cands"]; n = len(ms)
    assert len(cands) == n, "faltan muestras: llama a paso() hasta terminar"
    # Viterbi: coste de nodo = desviacion respecto a la nominal; coste de transicion = cambio del ajuste entre muestras vecinas (evita saltos de la camara)
    best = [[dev for dev, c in cands[0][1]]]; back = []
    for i in range(1, n):
        c0p = cands[i - 1][0]; cur = []; bk = []
        for dev, c in cands[i][1]:
            adj = c - cands[i][0]; opts = []; ang_c = ang(cands[i][2], c)
            for j, (dp, cp) in enumerate(cands[i - 1][1]):
                da = max(abs((ang_c[0] - ang(cands[i - 1][2], cp)[0] + 180) % 360 - 180), abs(ang_c[1] - ang(cands[i - 1][2], cp)[1]))                       # cambio de azimut/elevacion (grados) entre muestras vecinas
                opts.append((best[i - 1][j] + 4.0 * ((adj - (cp - c0p)).length ** 2) + 0.2 * da + 4.0 * max(0.0, da - 1.8 * (cands[i][3] - cands[i - 1][3]) / 4.0) ** 2, j))
            s, j = min(opts); cur.append(s + dev); bk.append(j)
        best.append(cur); back.append(bk)
    j = min(range(len(best[-1])), key=lambda q: best[-1][q]); sel = [0] * n
    for i in range(n - 1, -1, -1):
        sel[i] = j
        if i > 0: j = back[i - 1][j]
    C = [cands[i][1][sel[i]][1].copy() for i in range(n)]; T = [Vector(m["mira"]) for m in ms]; F = [m["focal"] for m in ms]; fr = [m["f"] for m in ms]

    def tasas():
        r = []
        for i in range(n - 1):
            a = (T[i] - C[i]).normalized(); b = (T[i + 1] - C[i + 1]).normalized(); r.append(math.degrees(a.angle(b)) / (fr[i + 1] - fr[i]))
        return r
    r0 = tasas(); it = 0
    while it < ITER_MAX:                                                            # limite de giro: suaviza localmente camara y punto de mira donde la mirada gira mas de LIM grados/frame
        r = tasas(); mal = [i for i, x in enumerate(r) if x > LIM]
        if not mal: break
        idx = sorted({q for i in mal for q in (i - 1, i, i + 1, i + 2) if 0 < q < n - 1})
        C2 = list(C); T2 = list(T)
        for q in idx:
            C2[q] = 0.25 * C[q - 1] + 0.5 * C[q] + 0.25 * C[q + 1]; T2[q] = 0.25 * T[q - 1] + 0.5 * T[q] + 0.25 * T[q + 1]
        C, T = C2, T2; it += 1
    r1 = tasas()
    # comprobacion final de visibilidad (tras suavizar)
    if sc.frame_current != J["N"]: sc.frame_set(J["N"])
    dg = bpy.context.evaluated_depsgraph_get(); tapadas = [fr[i] for i in range(n) if bloqueos(dg, C[i], T[i], fr[i]) > 0]
    # objetos y keyframes
    foco = bpy.data.objects.get("Cam_Foco_Alfred"); cam = bpy.data.objects.get("Camara_Alfred")
    if foco is None:
        foco = bpy.data.objects.new("Cam_Foco_Alfred", None); foco.empty_display_type = "PLAIN_AXES"; sc.collection.objects.link(foco)
    if cam is None:
        cd = bpy.data.cameras.new("Camara_Alfred"); cd.clip_end = 2000.0; cam = bpy.data.objects.new("Camara_Alfred", cd); sc.collection.objects.link(cam)
        tt = cam.constraints.new("TRACK_TO"); tt.target = foco; tt.track_axis = "TRACK_NEGATIVE_Z"; tt.up_axis = "UP_Y"
    for ob in (cam, foco, cam.data):
        if ob.animation_data and ob.animation_data.action: ob.animation_data.action = None
    for i in range(n):
        cam.location = C[i]; cam.keyframe_insert("location", frame=fr[i]); foco.location = T[i]; foco.keyframe_insert("location", frame=fr[i]); cam.data.lens = F[i]; cam.data.keyframe_insert("lens", frame=fr[i])
    for ob in (cam, foco, cam.data):
        ad = ob.animation_data; cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
        for fc in cb.fcurves:
            for kp in fc.keyframe_points: kp.interpolation = "BEZIER"; kp.handle_left_type = "AUTO_CLAMPED"; kp.handle_right_type = "AUTO_CLAMPED"
    sc.camera = cam; sc.frame_set(1)
    return (f"camara Alfred: {n} muestras; giro max de la mirada {max(r0):.2f} -> {max(r1):.2f} grados/frame ({it} pasadas de suavizado, limite {LIM}); "
            f"{sum(1 for x in r1 if x > LIM)} tramos aun sobre el limite; {len(tapadas)} muestras con vista aun tapada/pegada a algo: {tapadas[:40]}")


if "J" not in ST: preparar()
