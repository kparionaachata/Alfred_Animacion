"""Parte 3 - CAMARA PROFESIONAL dentro del refugio (pedido de Kebyn: "mueve la camara de forma profesional para que ponga enfasis en las expresiones de los personajes").
Se ejecuta DENTRO de Blender (exec) sobre base_parte_3.blend, por fases (cada una cabe en una llamada del MCP):
    FASE = "elegir"   -> por cada plano prueba varios angulos y distancias (rayos: camara dentro de la sala, sin tocar mallas, linea de vision limpia hasta la cara) y guarda `camara_plan.json`
    FASE = "hornear"  -> construye el movimiento (mezcla suave de planos, filtro gaussiano, lente y apertura), pone keyframes en `Camara_Conversacion` / `Foco_Conversacion` y activa la profundidad de campo
    FASE = "validar"  -> revisa fotograma a fotograma (dentro de la sala, sin atravesar mallas, cara visible) y mide la velocidad de giro de la camara
Datos: `camara_muestras.json` = posicion de la cara (centro de las mallas de los ojos), cabeza y morro de Alfred y Jerry en cada frame, y los tramos de HABLA de cada voz (RMS del audio por frame).
Lenguaje de camara: sin cortes (la sala es de 2 x 2 m): un solo movimiento continuo; planos mas cerrados (lente 40-55 mm, 0.9-1.15 m) sobre quien HABLA, que entran unos frames antes de que hable y se quedan unos despues,
empuje lento (dolly-in) dentro de cada plano; planos de conjunto (12-24 mm) en las acciones; la camara se coloca de 3/4 respecto a la cara; el objetivo (Foco) sigue el centro de la cara; la profundidad de campo
(apertura f/3.2 en primeros planos, f/11 en general) desenfoca el fondo.
"""
import bpy, json, math, os
import numpy as np
from mathutils import Vector

FASE = globals().get("FASE", "hornear")
DIR = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\parte3"
sc = bpy.context.scene; cam = bpy.data.objects["Camara_Conversacion"]; foco = bpy.data.objects["Foco_Conversacion"]
N = 480; T = 20; FR = np.arange(1, N + 1)
cache = json.load(open(os.path.join(DIR, "camara_muestras.json"))); M = cache["muestras"]
# tramos: (inicio, fin, tipo). Hablan: Alfred f58-89, f212-256, f371-402; Jerry f115-157, f298-348 (de `cache["voz"]`).
PLANOS = [(1, 42, "wide"), (42, 104, "alfred"), (104, 162, "jerry"), (162, 200, "dos"), (200, 260, "alfred"), (260, 290, "jerry_med"), (290, 356, "jerry"), (356, 412, "alfred"), (412, 480, "wide_end")]
CORTE_GRADOS = 38.0                                                                  # si el giro de la vista entre dos planos pasa de esto, se CORTA (en una pausa del dialogo) en vez de girar rapido; el primer y el ultimo plano se mueven (empuje y retroceso)
CORTES = globals().get("CORTES", True)
P_W = np.array([-96.6, -108.17, 15.85]); T_W = np.array([-96.01, -108.98, 14.51])
AZ = {"alfred": [-30, 30, -15, 15, -45, 45, -60, 60, 75, 90, -75, -90], "jerry": [60, -60, 90, -90, 30, -30, 110, -110], "alfred_obj": [-30, -15, 15, 30, -45, 45, -60, 60, 0], "jerry_med": [0, -20, 20, -40, 40], "dos": [0, -20, 20, -40]}
DS = [1.0, 0.85, 0.7, 0.55]


def serie(k):
    fs = np.array(sorted(int(f) for f in M if k in M[f])); v = np.array([M[str(f)][k] for f in fs])
    return np.stack([np.interp(FR, fs, v[:, i]) for i in range(3)], axis=1)


def gauss(a, sigma):
    r = int(3 * sigma); k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2); k /= k.sum()
    p = np.pad(a, ((r, r), (0, 0)), mode="edge")
    return np.stack([np.convolve(p[:, i], k, mode="valid") for i in range(a.shape[1])], axis=1)


def unit_xy(v):
    h = v.copy(); h[:, 2] = 0; n = np.linalg.norm(h, axis=1, keepdims=True); n[n < 1e-6] = 1.0
    return h / n


def rz(v, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.stack([v[:, 0] * c - v[:, 1] * s, v[:, 0] * s + v[:, 1] * c, v[:, 2]], axis=1)


aC, aH, jC, jH, jN = (serie(k) for k in ("aC", "aH", "jC", "jH", "jN"))
FA = unit_xy(gauss(aC - aH, 6)); FJ = unit_xy(gauss(jN - jH, 6)); aCs = gauss(aC, 5); jCs = gauss(jC, 5)          # la camara no sigue cada tic de la cara (un operador real filtra)


def estacion(tipo, ini, fin, az=0.0, ds=1.0):
    """(posicion[N,3], objetivo[N,3], lente[N]) del plano `tipo` para TODOS los frames (se mezcla solo donde pesa)."""
    elev = 0.0
    if ds >= 10: ds -= 10.0; elev = 0.40                                                                 # ds codificado: >= 10 = la misma distancia pero 0.40 m mas alta (mira a la cara desde arriba, por encima de las herramientas que vuelan)
    p = np.clip((FR - ini) / float(max(1, fin - ini)), 0, 1)[:, None]; pe = p * p * (3 - 2 * p); z = np.array([0, 0, 1.0])
    cte = lambda F: np.tile(unit_xy(F[ini - 1:fin].mean(axis=0, keepdims=True))[0], (N, 1))                  # direccion de la cara PROMEDIO del plano: la camara sigue a la cara pero no orbita con cada giro de cabeza
    FAc, FJc = cte(FA), cte(FJ)
    if tipo in ("wide", "wide_end"):
        pos = P_W + np.array([0.12, -0.06, -0.10]) * (pe if tipo == "wide" else (1 - pe)); tgt = np.tile(T_W, (N, 1)); lens = 12.0 + 1.0 * (pe[:, 0] if tipo == "wide" else (1 - pe[:, 0]))
    elif tipo == "alfred":
        tgt = aCs + FAc * 0.06 + z * 0.04; d = (1.15 - 0.25 * pe) * ds; pos = aCs + rz(FAc, az) * d + z * (0.10 + elev); lens = d[:, 0] * (21.0 + 5.0 * pe[:, 0])                          # cabeza de Alfred (0.5 m) ~60 % de la altura del cuadro
    elif tipo == "jerry":
        tgt = jCs; d = (1.0 - 0.2 * pe) * ds; pos = jCs + rz(FJc, az) * d + z * 0.03; lens = d[:, 0] * (33.0 + 7.0 * pe[:, 0])                          # cabeza de Jerry (0.3 m) ~60 % de la altura
    elif tipo == "alfred_obj":
        tgt = aCs + np.array([-0.22, 0.0, -0.06]); d = 1.2 * ds; pos = tgt + rz(FAc, az) * d + z * 0.18; lens = d * (19.0 + 1.0 * pe[:, 0])                  # Alfred (cara) con el brazo y la herramienta en el cuadro
    elif tipo == "jerry_med":
        tgt = (jH + jCs) / 2 + np.array([0.22, 0.06, -0.08]); dv = np.array([-0.35, 0.9, 0.5]); dv = dv / np.linalg.norm(dv); pos = tgt + rz(np.tile(dv, (N, 1)), az) * 1.25 * ds; lens = 1.25 * ds * (18.0 + 1.0 * pe[:, 0])
    else:  # dos
        tgt = (aCs + jCs) / 2 + np.array([0, 0, -0.05]); dv = np.array([-0.55, 0.65, 0.45]); dv = dv / np.linalg.norm(dv); pos = tgt + rz(np.tile(dv, (N, 1)), az) * 1.25 * ds; lens = np.full(N, 1.25 * ds * 16.0)
    return pos, tgt, lens


def ray_ok(dg, pos, tgt):
    if not (-96.86 < pos.x < -95.12 and -109.86 < pos.y < -108.12 and 14.3 < pos.z < 15.92): return False
    for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        if sc.ray_cast(dg, pos, Vector(d), distance=0.12)[0]: return False
    v = tgt - pos; dist = v.length; vn = v.normalized(); der = vn.cross(Vector((0, 0, 1))); der = der.normalized() if der.length > 1e-6 else Vector((1, 0, 0)); arr = der.cross(vn)
    for off in (Vector(), der * 0.12, -der * 0.12, arr * 0.12, -arr * 0.12):                  # el centro y 4 puntos alrededor de la cara: nada (herramientas voladoras, brazos, Jerry) pasa entre la camara y el plano
        d2 = (tgt + off) - pos; ok, loc, _n, _i, ob, _m = sc.ray_cast(dg, pos, d2.normalized(), distance=max(0.05, d2.length - 0.1))
        if ok and (loc - tgt).length >= 0.32: return False
    return True


if FASE == "elegir":
    cur = sc.frame_current; muestras = list(range(1, N + 1, 3)); elegido = {}
    ests = {}
    for i, (ini, fin, tipo) in enumerate(PLANOS):
        for az in (AZ.get(tipo) or [0]):
            for ds in ([1.0] if tipo in ("wide", "wide_end") else (DS[:3] + ([10.0 + x for x in DS[:3]] if i == 4 else []) if tipo == "alfred" else (DS[:3] if tipo == "jerry" else (DS[:2] if tipo == "alfred_obj" else DS)))): ests[(i, az, ds)] = estacion(tipo, ini, fin, az, ds)
    score = {k: [0, 0] for k in ests}
    try:
        for f in muestras:
            sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
            for (i, az, ds), (pos, tgt, lens) in ests.items():
                ini, fin, tipo = PLANOS[i]
                if not (ini - 4 <= f <= fin + 4): continue
                score[(i, az, ds)][1] += 1
                if ray_ok(dg, Vector(pos[f - 1]), Vector(tgt[f - 1])): score[(i, az, ds)][0] += 1
    finally:
        sc.frame_set(cur)
    def vista(k, f):
        pos, tgt, _l = ests[k]; v = tgt[f - 1] - pos[f - 1]; return v / np.linalg.norm(v), pos[f - 1]
    cands = []                                                                                       # por plano: [(clave, fraccion valida)]
    for i in range(len(PLANOS)):
        cands.append([(k, v[0] / v[1]) for k, v in score.items() if k[0] == i and v[1] > 0 and v[0] / v[1] >= 0.8])
        if not cands[-1]: cands[-1] = [(max((k for k in score if k[0] == i), key=lambda k: score[k][0] / max(1, score[k][1])), 0.0)]

    def paso(ka, kb, f):                                                                              # coste de pasar del plano a al b en el frame f: giro de la vista + desplazamiento
        va, pa = vista(ka, f); vb, pb = vista(kb, f)
        return math.degrees(math.acos(max(-1, min(1, float(va @ vb))))) + 40.0 * float(np.linalg.norm(pa - pb))
    coste = [{k: (200.0 * (1 - fr)) for k, fr in cands[0]}]; atras = [{}]
    for i in range(1, len(PLANOS)):
        fb = PLANOS[i][0]; ci = {}; ai = {}
        for kb, frb in cands[i]:
            mejor = min(coste[i - 1].items(), key=lambda kv: kv[1] + paso(kv[0], kb, fb)); ci[kb] = mejor[1] + paso(mejor[0], kb, fb) + 400.0 * (1 - frb) + 150.0 * (1.0 - (kb[2] % 10)) + (10.0 if kb[2] >= 10 else 0.0); ai[kb] = mejor[0]                    # prefiere distancias mayores (no pegarse tanto a la cara)
        coste.append(ci); atras.append(ai)
    k = min(coste[-1], key=coste[-1].get); camino = [k]
    for i in range(len(PLANOS) - 1, 0, -1): k = atras[i][k]; camino.append(k)
    camino.reverse(); Ts = []
    for i, k in enumerate(camino):
        ini, fin, tipo = PLANOS[i]; elegido[i] = {"az": k[1], "ds": k[2], "validos": score[k][0], "de": score[k][1]}
        if i > 0:
            fb = PLANOS[i][0]; va, _p = vista(camino[i - 1], fb); vb, _q = vista(k, fb); ang = math.degrees(math.acos(max(-1, min(1, float(va @ vb)))))
            Ts.append(int(min(56, max(24, math.ceil(ang / 1.2))))); elegido[i]["giro_entrada"] = round(ang, 1); elegido[i]["corte"] = bool(CORTES and ang > CORTE_GRADOS and 1 < i < len(PLANOS) - 1)
        print(PLANOS[i], elegido[i])
    json.dump({"planos": PLANOS, "elegido": elegido, "T": Ts}, open(os.path.join(DIR, "camara_plan.json"), "w"))

if FASE in ("hornear", "validar"):
    plan = json.load(open(os.path.join(DIR, "camara_plan.json"))); el = plan["elegido"]
    W = np.zeros((len(PLANOS), N)); ss = lambda u: np.clip(u, 0, 1) ** 2 * (3 - 2 * np.clip(u, 0, 1)); Ts = plan.get("T") or [T] * (len(PLANOS) - 1)
    cortes = [i for i in range(1, len(PLANOS)) if el[str(i)].get("corte")]; Tc = [1.0 if (i + 1) in cortes else float(Ts[i]) for i in range(len(PLANOS) - 1)]       # Tc[i] = duracion del paso del plano i al i+1 (1 = corte seco)
    for i, (ini, fin, tipo) in enumerate(PLANOS):
        a = (np.ones(N) if i == 0 else ((FR >= ini).astype(float) if Tc[i - 1] <= 1.0 else ss((FR - (ini - Tc[i - 1] / 2.0)) / Tc[i - 1])))                      # corte seco = escalon en el frame de entrada
        b = (np.ones(N) if i == len(PLANOS) - 1 else ((FR < fin).astype(float) if Tc[i] <= 1.0 else 1 - ss((FR - (fin - Tc[i] / 2.0)) / Tc[i]))); W[i] = a * b
    W /= W.sum(axis=0, keepdims=True)
    pos = np.zeros((N, 3)); tgt = np.zeros((N, 3)); lens = np.zeros(N)
    for i, (ini, fin, tipo) in enumerate(PLANOS):
        e = el[str(i)]; ps, ts, ls = estacion(tipo, ini, fin, e["az"], e["ds"]); pos += W[i][:, None] * ps; tgt += W[i][:, None] * ts; lens += W[i] * ls
    cf = [PLANOS[i][0] for i in cortes]; lim = [0] + [c - 1 for c in cf] + [N]                                  # secciones entre cortes: el filtro no cruza un corte
    for a_, b_ in zip(lim[:-1], lim[1:]):
        pos[a_:b_] = gauss(pos[a_:b_], 3.0); tgt[a_:b_] = gauss(tgt[a_:b_], 3.0); lens[a_:b_] = gauss(lens[a_:b_, None], 3.0)[:, 0]
    d = tgt - pos; d /= np.linalg.norm(d, axis=1, keepdims=True); ang = np.degrees(np.arccos(np.clip((d[1:] * d[:-1]).sum(axis=1), -1, 1))); ang[[c - 2 for c in cf]] = 0.0
    print("cortes en f%s; giro max %.2f grados/frame (f%d), medio %.3f; desplazamiento max %.3f m/frame (sin contar cortes)" % (cf, ang.max(), int(ang.argmax()) + 2, ang.mean(), np.linalg.norm(np.diff(pos, axis=0), axis=1)[[i for i in range(N - 1) if i + 2 not in cf]].max()))
    if FASE == "hornear":
        for ob in (cam, foco): ob.animation_data_clear()
        cam.data.animation_data_clear()
        fst = np.interp(lens, [12, 20, 30, 45], [11.0, 7.0, 4.5, 3.2])
        cam.data.dof.use_dof = True; cam.data.dof.focus_object = foco; cam.data.dof.aperture_blades = 0
        for f in range(1, N + 1):
            cam.location = pos[f - 1]; foco.location = tgt[f - 1]; cam.data.lens = float(lens[f - 1]); cam.data.dof.aperture_fstop = float(fst[f - 1])
            cam.keyframe_insert("location", frame=f); foco.keyframe_insert("location", frame=f); cam.data.keyframe_insert("lens", frame=f); cam.data.keyframe_insert("dof.aperture_fstop", frame=f)
        for ob in (cam, foco, cam.data):
            ad = ob.animation_data
            if ad and ad.action:
                acc = ad.action
                fcs = acc.fcurves if hasattr(acc, "fcurves") else [c for l in acc.layers for s_ in l.strips for b_ in s_.channelbags for c in b_.fcurves]
                for c in fcs:
                    for k in c.keyframe_points: k.interpolation = 'LINEAR'
        sc.camera = cam; sc.frame_set(1)
        print("camara horneada: f1-%d" % N)
    else:
        cur = sc.frame_current; malos = []
        try:
            for f in range(1, N + 1, 3):
                sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
                if not ray_ok(dg, cam.matrix_world.translation.copy(), foco.matrix_world.translation.copy()): malos.append(f)
        finally:
            sc.frame_set(cur)
        print("frames con problema (camara dentro de una malla, fuera de la sala o cara tapada):", malos)
