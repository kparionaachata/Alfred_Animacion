# -*- coding: utf-8 -*-
"""
motor_cerdo_1.py -- Cerdo_1 Animation Studio: MOTOR DE MOVIMIENTO del guion 2.0 (fase 4 del plan `docs/PLAN_PARTE3_AL_FLUJO.md`).

Python PURO (sin bpy): las partes que tocan Blender (`hornear`, `verificar_en_blender`) importan bpy al usarse. Reproduce, tramo a tramo, lo que hace `parte3/sentarse_en_refugio.py` para Cerdo_1, pero leyendo sus
parametros de la seccion `movimiento` del guion (en vez de constantes del script) y comparandolo con la REFERENCIA NUMERICA (`datos_guion/base_referencia_cerdo_1.json`, fase 0).

Estrategia ("estrangulacion"): el motor genera la animacion completa. Cada frame sale de UN tramo ya migrado (calculado por el motor desde el guion) o, mientras su tramo no se migra, de la referencia congelada;
despues se aplica el MISMO suavizado de curvas que el generador (`cerdo_1_final`: todo menos los brazos) y los ajustes de suelo. Asi el guion se llena tramo a tramo y la animacion nunca queda a medias.

SECCION `movimiento` del guion
  {referencia_numerica: ruta,            fuente de los frames aun no migrados
   yaw_base_deg: -720,                   giro acumulado de la parte 2 (el yaw del root se escribe como yaw_base + yaw)
   organico: {...nombres del estudio...},  breathing_amplitude, breathing_speed, breathing_phase, head_sway_amplitude/_speed/_seed, micro_scale_amplitude, secondary_motion_lag/_damping, smooth_passes, smooth_factor
   tramos: [{id, nombre, tipo, inicio, fin, estado, usa, params}]}       `usa` = tomar los params de otro tramo; los params con prefijo `t_` son tiempos (frames o anclas)
TIPOS DE TRAMO
  sentado_cansado   aproximacion + sentarse con la referencia `sentado_cansado_cerdo_1` + reposo (respira, ruido, mira la antorcha, se duerme): S01 (f1-52) y S02 (f53-189)
"""
import copy
import json
import math
import os

try:
    from . import guion_v2 as gv
except Exception:                                                                      # fuera del paquete (pruebas / exec por ruta)
    import importlib.util as _ilu
    _sp = _ilu.spec_from_file_location("guion_v2", os.path.join(os.path.dirname(os.path.abspath(__file__)), "guion_v2.py")); gv = _ilu.module_from_spec(_sp); _sp.loader.exec_module(gv)

D = math.radians
RAIZ = os.environ.get("CERDO_1_RAIZ", r"C:\Users\user\Desktop\Alfred_Animacion")
BRAZOS = lambda b: "UpArm" in b or "elbow" in b
_CACHE = {}


def ss(u):
    u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)


def wp_eval(wps, k):
    """waypoints [(frame, tuple)] -> valor con smoothstep entre ellos."""
    if k <= wps[0][0]: return wps[0][1]
    if k >= wps[-1][0]: return wps[-1][1]
    i = next(q for q in range(1, len(wps)) if wps[q][0] >= k); f0, f1 = wps[i - 1][0], wps[i][0]; u = ss((k - f0) / float(f1 - f0))
    return tuple(a + (b - a) * u for a, b in zip(wps[i - 1][1], wps[i][1]))


def breathe(k, a0, per, ph=0.0):
    return a0 * math.sin(2 * math.pi * k / per + ph)


def noise(k, seed, a):
    return a * (0.55 * math.sin(k * 0.071 + seed) + 0.3 * math.sin(k * 0.137 + seed * 2.3) + 0.15 * math.sin(k * 0.293 + seed * 3.7))


def org_noise(f, freq, seed, dim=0):
    v = math.sin(f * freq * 1.3 + seed * 7.3 + dim * 3.7) + math.sin(f * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5 + math.sin(f * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25
    return v / 1.75


def _abs(ruta):
    return ruta if os.path.isabs(ruta) else os.path.join(RAIZ, "generador de animaciones", "cerdo_1", "refinar", ruta)


def _json(ruta):
    if ruta not in _CACHE:
        with open(_abs(ruta), encoding="utf-8") as f: _CACHE[ruta] = json.load(f)
    return _CACHE[ruta]


# ------------------------------------------------------------------------------------------------------------------------------------------- parametros
def organico_de(mov):
    """nombres del estudio -> los que usa el motor (los mismos valores que `ORG` del generador)."""
    o = (mov or {}).get("organico") or {}
    return dict(br_amp=o["breathing_amplitude"], br_speed=o["breathing_speed"], br_phase=o["breathing_phase"], hs_amp=o["head_sway_amplitude"], hs_speed=o["head_sway_speed"], hs_seed=o["head_sway_seed"],
                micro_amp=o["micro_scale_amplitude"], sec_lag=o["secondary_motion_lag"], sec_damp=o["secondary_motion_damping"], sm_passes=int(o["smooth_passes"]), sm_factor=o["smooth_factor"])


def tramos_de(d):
    """tramos del guion DESPLEGADO (frames absolutos), con `usa` resuelto: [{id, tipo, inicio, fin, params (con t_* resueltos)}]."""
    mov = d.get("movimiento") or {}; tr = {t["id"]: t for t in mov.get("tramos") or []}; out = []
    for t in mov.get("tramos") or []:
        p = copy.deepcopy((tr[t["usa"]] if t.get("usa") else t).get("params") or {})
        out.append({"id": t["id"], "tipo": t["tipo"], "inicio": int(t["inicio"]), "fin": int(t["fin"]), "params": p, "estado": t.get("estado", "sin aprobar")})
    return sorted(out, key=lambda t: t["inicio"])


# ------------------------------------------------------------------------------------------------------------------------------------------- tipo `sentado_cansado` (S01 + S02)
def _ref_rot(R, b, t):
    n = R["frames"]; t = min(max(t, 0.0), n - 1.0); i = int(t); j = min(i + 1, n - 1); u = t - i; a = R["rot"][b][i]; c = R["rot"][b][j]
    return [a[q] + (c[q] - a[q]) * u for q in range(3)]


def _ref_loc(arr, t, n):
    t = min(max(t, 0.0), n - 1.0); i = int(t); j = min(i + 1, n - 1); u = t - i
    return [arr[i][q] + (arr[j][q] - arr[i][q]) * u for q in range(3)]


def organico(k, rot, org):
    a = org["br_amp"]; ph = k * org["br_speed"] * 2 * math.pi + org["br_phase"]
    for b in ("Body:Bend_cerdo_1", "Body:Bend_cerdo_1"): rot[b][0] += a * math.sin(ph); rot[b][2] += a * 0.4 * math.sin(ph + 1.2)
    for ax in range(3):
        d = org["hs_amp"] * org_noise(k, org["hs_speed"], org["hs_seed"], ax)
        for b in ("Head_cerdo_1", "Head_cerdo_1"):
            if b in rot: rot[b][ax] += d


def micro_scale(k, org):
    return 1.0 + org["micro_amp"] * math.sin(k * org["br_speed"] * 2 * math.pi + org["br_phase"])


def raw_sentado_cansado(k, p, org, t_fin, ctx=None, con_organico=True):
    """rotaciones (rad) y ubicaciones del frame k, antes del suavizado. `p` = params del tramo (ver `construir_movimiento_s01_s02.py`)."""
    R = _json(p["referencia_sentado"]); ref0 = int(p["t_ref0"]); slow = p["slow"]; n = R["frames"]; refend = int(ref0 + (n - 1) * slow); rot = {}; loc = {}
    stand = {b: (0.0, 0.0, 0.0) for b in R["rot"]}; stand["Leg:FR_cerdo_1"] = stand["Leg:FL_cerdo_1"] = (0.0, 0.0, 0.0)
    wf = ss((k - 1) / float(ref0 - 1))                                           # la pose de pie se acerca a la primera pose de la referencia con UNA curva lenta durante f1-29
    for b in R["rot"]:
        if k < ref0: r0 = stand[b]; r1 = _ref_rot(R, b, 0); rot[b] = [r0[j] + (r1[j] - r0[j]) * wf for j in range(3)]
        else: rot[b] = _ref_rot(R, b, (k - ref0) / slow)
    for b, arr in R["loc"].items():
        l1 = _ref_loc(arr, (k - ref0) / slow, n); loc[b] = [l1[j] * wf for j in range(3)] if k < ref0 else l1
    rot["Head_cerdo_1"][0] *= p["cuello_x_factor"]                                # mira al frente (la referencia baja la cabeza 16 grados: aqui ~5)
    if k < ref0:                                                                 # f1-29: gira y da pasitos de acomodo con contrapeso; llega quieto
        a = p["aproximacion"]; T = a["dur"]; v = min(max((k - a["t_inicio"]) / T, 0.0), 1.0); W = math.sin(math.pi * v) ** 2; ph = (k - a["t_inicio"]) * 2 * math.pi / a["ciclo"]; sw = W * math.sin(ph)
        rot["Leg:BR_cerdo_1"][0] += D(a["piernas"] * sw); rot["Leg:BL_cerdo_1"][0] -= D(a["piernas"] * sw)
        rot["Leg:BR:Bend_cerdo_1"][0] += D(-a["rodillas"] * W * 0.5 * (1 + math.sin(ph + 1.0))); rot["Leg:BL:Bend_cerdo_1"][0] += D(-a["rodillas"] * W * 0.5 * (1 - math.sin(ph + 1.0)))
        rot["Leg:FR_cerdo_1"][0] += D(-a["brazos"] * sw); rot["Leg:FL_cerdo_1"][0] += D(a["brazos"] * sw)
        rot["Body:Bend_cerdo_1"][2] += D(-a["spine_z"] * sw); rot["Body:Bend_cerdo_1"][2] += D(a["spine2_z"] * sw); rot["Body_cerdo_1"][2] += D(a["hips_z"] * sw)
        rot["Head_cerdo_1"][1] += D(a["cuello_y"] * math.sin(math.pi * min(max((k - 1) / a["cuello_y_dur"], 0.0), 1.0)) ** 2)
        for b_, sd_, a_ in a["ruido"]: rot[b_][0] += D(noise(k, sd_, a_) * (1 - ss((k - a["ruido_fade"][0]) / a["ruido_fade"][1])))
    if k > refend:                                                               # reposo: la pose final de la referencia + filtros organicos
        r = p["reposo"]; t = k - refend; alive = ss(t / r["alive_dur"])
        for b, sd, a in r["ruido"]: rot[b][0] += D(alive * noise(k, sd, a)); rot[b][2] += D(alive * noise(k, sd + 9, r["ruido_z"]))
        rot["Head_cerdo_1"][0] += D(alive * noise(k, *r["cuello_x"])); rot["Head_cerdo_1"][2] += D(alive * noise(k, *r["cuello_z"]))
        (b1, a1, p1, f1), (b2, a2, p2, f2), (b3, a3, p3, f3) = r["respira"]
        rot[b1][0] += D(alive * breathe(k, a1, p1)); rot[b2][0] += D(alive * breathe(k, a2, p2, f2)); rot[b3][0] += D(alive * breathe(k, a3, p3, f3))
        t0 = int(p["t_mira"]); mira = wp_eval([(t0 + dt, (v,)) for dt, v in r["mira"]] + [(t_fin, (0.0,))], k)[0]
        rot["Head_cerdo_1"][1] += D(mira); rot["Head_cerdo_1"][0] += D(-r["mira_x"] * ss((k - t0 - r["mira_x_ini"]) / 12.0) * (1 - ss((k - t0 - r["mira_x_fin"]) / 12.0)))
        cae = wp_eval([(t0 + dt, (v,)) for dt, v in r["cae"]] + [(t_fin, (r["cae"][-1][1],))], k)[0]
        rot["Head_cerdo_1"][0] += D(cae); rot["Head_cerdo_1"][2] += D(cae * r["cae_z"])
        sig = math.exp(-((k - t0 - r["suspiro_dt"]) / r["suspiro_ancho"]) ** 2); rot["Body:Bend_cerdo_1"][0] += D(-r["suspiro_amp"] * sig)
        rot["Leg:FL_cerdo_1"][0] += D(alive * noise(k, *r["brazo_i"])); rot["Leg:FL:Bend_cerdo_1"][0] += D(alive * noise(k, *r["codo_i"]))
    if con_organico: organico(k, rot, org)
    return rot, loc


def root_sentado(k, p, ctx=None):
    """root (x, y, z, yaw grados) de la aproximacion: UN movimiento (giro +90 y desplazamiento con la misma curva suave). Solo vale mientras no actuan los demas terminos del root (k < 502)."""
    a = p["root"]; u = ss((k - a["t_inicio"]) / a["dur"])
    yaw = a["yaw"] * u + a["rebase"] * math.sin(math.pi * min(max((k - a["rebase_ini"]) / a["rebase_dur"], 0.0), 1.0)) ** 2
    return [a["x0"] + a["dx"] * u, a["y0"] + a["dy"] * u, a["z"], yaw]


# ------------------------------------------------------------------------------------------------------------------------------------------- tipo `cuerpo` (S03-S14): port de `cerdo_1_at` / `throw_layer` / `arm_table` / `root_at` del generador. Usa mathutils.
def _mu():
    from mathutils import Euler, Matrix, Quaternion
    return Euler, Matrix, Quaternion


def _E(*d):
    Euler, _, _ = _mu(); return Euler([D(x) for x in d], 'XYZ').to_matrix()


def _qpow(q0, q1, u):
    """q0 -> q1 por el camino mas corto, con u fuera de [0, 1] permitido (Elastic In-Out sobrepasa)."""
    _, _, Quaternion = _mu(); d = q0.inverted() @ q1
    if d.w < 0: d = -d
    ax, an = d.to_axis_angle()
    return q0 @ Quaternion(ax, an * u) if an > 1e-9 else q0.copy()


def ela(u):
    """Elastic In-Out (misma formula que el add-on y la parte 2)."""
    if u <= 0.0: return 0.0
    if u >= 1.0: return 1.0
    c5 = 2 * math.pi / 4.5
    if u < 0.5: return -(2 ** (20 * u - 10) * math.sin((20 * u - 11.125) * c5)) / 2
    return (2 ** (-20 * u + 10) * math.sin((20 * u - 11.125) * c5)) / 2 + 1


def _wpl(rows):
    return [(int(r[0]), tuple(r[1])) for r in rows]


def _pares(rows):
    return [(int(r[0]), r[1]) for r in rows]


def _goal(lado, delta, e):
    """(cuaternion hombro, cuaternion codo) del agarre: gesto del estudio (+ espejo en X para el izquierdo) compuesto con el ajuste `delta` (X, Y, Z del hombro y X del codo, grados)."""
    _, Matrix, _ = _mu(); ru, re = _E(*e["u"]), _E(*e["e"])
    if lado == "Left": sx = Matrix.Diagonal((-1, 1, 1)); ru, re = sx @ ru @ sx, sx @ re @ sx
    return (ru @ _E(delta[0], delta[1], delta[2])).to_quaternion(), (re @ _E(delta[3], 0, 0)).to_quaternion()


def kn_w(k, p):
    r = p["rodillas"]; return ss((k - r["t_ini"]) / float(r["t_fin"] - r["t_ini"]))


def stand_w(k, p):
    d = p["de_pie"]; return ss((k - d["t_ini"]) / float(d["dur"]))


def lean_w(k, p):
    return ss((k - p["t_lean_sube"]) / float(p["t_lean_tope"] - p["t_lean_sube"])) * (1 - ss((k - p["t_lean_baja"]) / float(p["lean_baja_dur"])))


def nuca_capa(k, rot, p):
    """tronco y cabeza al apoyarse en el muro con las manos en la nuca (los brazos van en `_arm_state`)."""
    n = p["nuca"]; t0 = n["t_ini"]; dd = n["dur"]
    if k < t0 - 2: return
    w = ss((k - t0) / float(dd)); x = max(0.0, k - (t0 + dd)); aco = math.exp(-x / 11.0) * math.sin(2 * math.pi * x / 15.0) * ss((k - t0 - dd + 2) / 2.0)
    rot["Body:Bend_cerdo_1"][0] += D(-3.0 * w + 3.0 * aco); rot["Body:Bend_cerdo_1"][0] += D(-1.5 * w + 1.5 * aco); rot["Body:Bend_cerdo_1"][0] += D(-1.0 * w)
    rot["Head_cerdo_1"][0] += D(-14.0 * ss((k - t0 - 6) / 22.0) + 2.5 * aco)
    rot["Head_cerdo_1"][1] += D(20.0 * ss((k - t0 - 4) / 14.0) * (1 - ss((k - t0 - 74) / 16.0)))


def kn_capa(k, rot, loc, p):
    """sentado -> de rodillas -> de pie: mezcla todos los huesos que no son los brazos hacia la pose de rodillas y suma la inclinacion / la mirada de cada momento."""
    r = p["rodillas"]
    if k < r["t_ini"] - 1: return
    w = kn_w(k, p)
    for b in rot:
        if "UpArm" in b or "elbow" in b: continue
        t = (0.0, 0.0, 0.0)
        if b.endswith("UpLeg_cerdo_1"): t = (D(r["pierna"][0]), 0.0, 0.0)
        elif b.endswith("knee_cerdo_1"): t = (D(r["pierna"][1]), 0.0, 0.0)
        rot[b] = [rot[b][j] * (1 - w) + t[j] * w for j in range(3)]
    sw = stand_w(k, p)
    if sw > 0:
        for b in rot:
            if "UpArm" in b or "elbow" in b: continue
            rot[b] = [v * (1 - sw) for v in rot[b]]
    h = loc.get("Body_cerdo_1", [0.0, 0.0, 0.0]); loc["Body_cerdo_1"] = [h[0] * (1 - w), (h[1] * (1 - w) + r["hips_y"] * w) * (1 - sw), h[2] * (1 - w)]
    ln = wp_eval(_wpl(r["tt_inclina"]), k)[0]
    for b, wg in p["barrido"]["reparto"]: rot[b][0] += D(ln * wg)
    rot["Head_cerdo_1"][0] += D(-0.15 * ln + wp_eval(_wpl(r["tt_cuello"]), k)[0]); rot["Head_cerdo_1"][1] += D(wp_eval(_wpl(r["tt_mirada"]), k)[0])


def giro_capa(k, rot, p):
    """animacion de giro (+90 grados sobre si mismo): la cabeza se adelanta, dos pasitos con contrapeso y torsion de tronco."""
    g = p["giro"]; rot0, rd = g["t_ini1"], g["dur1"]
    v = (k - rot0) / float(rd)
    if v <= 0.0 or v >= 1.0:
        v = (k - g["t_ini2"]) / float(g["dur2"])
        if v <= 0.0 or v >= 1.0: return
        k = k - (g["t_ini2"] - rot0)
    W = math.sin(math.pi * v) ** 2; ph = (k - rot0) * 2 * math.pi / 8.0; sw = W * math.sin(ph)
    rot["Leg:BR_cerdo_1"][0] += D(10 * sw); rot["Leg:BL_cerdo_1"][0] -= D(10 * sw)
    rot["Leg:BR:Bend_cerdo_1"][0] += D(-14 * W * 0.5 * (1 + math.sin(ph + 1.0))); rot["Leg:BL:Bend_cerdo_1"][0] += D(-14 * W * 0.5 * (1 - math.sin(ph + 1.0)))
    rot["Body:Bend_cerdo_1"][2] += D(-3 * sw); rot["Body:Bend_cerdo_1"][2] += D(2 * sw); rot["Body_cerdo_1"][2] += D(2.2 * sw)
    rot["Head_cerdo_1"][1] += D(28 * math.sin(math.pi * min(max(v * 1.3, 0.0), 1.0)) ** 2)


def _base_sin_lanzar(k, p, org, N, base):
    """`cerdo_1_at(k, throw=False)`: referencia / reposo + nuca + rodillas / de pie + filtros organicos + giro."""
    rot, loc = raw_sentado_cansado(k, base, org, N, None, False)
    nuca_capa(k, rot, p); kn_capa(k, rot, loc, p); organico(k, rot, org); giro_capa(k, rot, p)
    return rot, loc


def clr_pose(k, p):
    """(cuat. hombro, cuat. codo) de la mano izquierda durante los manotazos del barrido; None fuera de ese tramo."""
    _, _, Quaternion = _mu(); b = p["barrido"]; keys = _pares(b["tt_claves"])
    if k < keys[0][0] or k >= keys[-1][0]: return None
    Q = {n: [Quaternion(q) for q in v] for n, v in b["q"].items()}; Q["N"] = [Quaternion(q) for q in p["nuca"]["q"]["Left"]]; Q["SIT"] = [Quaternion(q) for q in p["sit"]["q"]["Left"]]
    Q["S"] = [_qpow(Q["R"][i], Q["S"][i], b["sw"]) for i in (0, 1)]                  # el manotazo no llega al final de la pose S (solo `sw` de camino): la mano no se mete en el pelaje de Jerry
    for (f0, a), (f1, c) in zip(keys[:-1], keys[1:]):
        if f0 <= k < f1:
            x = (k - f0) / float(f1 - f0); u = (0.3 * ela(x) + 0.7 * ss(x)) if (a, c) == ("R", "S") else ss(x)
            return _qpow(Q[a][0], Q[c][0], u), _qpow(Q[a][1], Q[c][1], u)


def _eu_key(lado, p, cache):
    """Euler XYZ (rad) del hombro y X del codo de cada pose de brazo (tabla `poses`; SIT sale de `sit.q` en la rama de menor torsion Z)."""
    if lado in cache: return cache[lado]
    _, _, Quaternion = _mu(); si = 0 if lado == "Left" else 2; out = {}; sq = p["sit"]["q"][lado]; e = Quaternion(sq[0]).to_euler('XYZ'); c = (e.x, e.y, e.z); c2 = (e.x + math.pi, math.pi - e.y, e.z + math.pi)
    cc = [[((a_ + math.pi) % (2 * math.pi)) - math.pi for a_ in q] for q in (c, c2)]; cc = min(cc, key=lambda q: 3 * abs(q[2]) + 0.1 * abs(q[0]))
    qe = Quaternion(sq[1]); xe = 2 * math.atan2(qe.x, qe.w); out["SIT"] = (cc, (xe, 0.0, 0.0))
    for nm, v in p["brazos"]["poses"].items():
        ev_ = v[si + 1]; out[nm] = ([math.radians(a_) for a_ in v[si]], tuple(math.radians(a_) for a_ in (ev_ if isinstance(ev_, (list, tuple)) else (ev_, 0.0, 0.0))))
    if lado == "Right":                                                                  # el brazo derecho tambien rota en +Y: la MISMA postura escrita como (X + 180, 180 - Y, Z + 180); BACK ya viene escrita asi
        out = {nm: (e_[0] if nm == "BACK" else [e_[0][0] + math.pi, math.pi - e_[0][1], e_[0][2] + math.pi], e_[1]) for nm, e_ in out.items()}
    cache[lado] = out; return out


def tab_eul(lado, k, lru, p, cache):
    """([rx, ry, rz] del hombro, [rx, ry, rz] del codo, ubicacion): angulos Euler entre las poses de la tabla de brazos, canal por canal (Elastic al 30 % en la espalda y el tiron al frente)."""
    b = p["brazos"]; EU = _eu_key(lado, p, cache); e = p["estudio"]; locg = (e["loc"][0] * (-1 if lado == "Left" else 1), e["loc"][1], e["loc"][2]); tbk = _pares(b["tt_tbk"])
    wl = ss((k - tbk[0][0]) / 10.0); lc = tuple(l * (1 - wl) + g * wl for l, g in zip(lru, locg))
    keys = _pares(b["tt_pre_r" if lado == "Right" else "tt_pre_l"]) + tbk[2:-1] + _pares(b["tt_x_right" if lado == "Right" else "tt_x_left"])
    for (f0, a), (f1, c) in zip(keys[:-1], keys[1:]):
        if f0 <= k < f1:
            x = (k - f0) / float(f1 - f0); u = (0.3 * ela(x) + 0.7 * ss(x)) if (a, c) in (("REST", "BACK"), ("BACK", "HI"), ("TOP", "BACK"), ("BACK", "HOLD"), ("SW0", "SW1")) else ss(x)
            A_, B_ = EU[a], EU[c]; return [A_[0][q] + (B_[0][q] - A_[0][q]) * u for q in range(3)], [A_[1][q] + (B_[1][q] - A_[1][q]) * u for q in range(3)], lc
    E_ = EU[keys[-1][1]]; return list(E_[0]), list(E_[1]), lc


def _arm_state(lado, k, qru, qre, lru, p):
    """(cuat. hombro, cuat. codo, ubicacion del hombro) del brazo `lado` mientras NO usa la tabla de poses (lanzar herramientas, nuca, sentado, barrido); None si no participa. Mismo orden de prioridades que el generador."""
    _, _, Quaternion = _mu(); e = p["estudio"]; t = p["tiempos"]; locg = (e["loc"][0] * (-1 if lado == "Left" else 1), e["loc"][1], e["loc"][2]); sit = p["sit"]; nuca = p["nuca"]
    if lado == "Right" and sit["t_ini"] <= k < _pares(p["brazos"]["tt_tbk"])[0][0]:
        u = ss((k - sit["t_ini"]) / float(sit["t_fin"] - sit["t_ini"])); a_, b_ = (Quaternion(q) for q in nuca["q"]["Right"]); c_, d_ = (Quaternion(q) for q in sit["q"]["Right"]); return _qpow(a_, c_, u), _qpow(b_, d_, u), tuple(lru)
    if lado == "Left" and k >= _pares(p["barrido"]["tt_claves"])[0][0]:
        c_ = clr_pose(k, p)
        if c_ is not None: return c_[0], c_[1], tuple(lru)
    if k >= nuca["t_ini"]:
        gu, ge = (Quaternion(q) for q in nuca["q"][lado]); u = ss((k - nuca["t_ini"]) / float(nuca["dur"])); return qru.slerp(gu, u), qre.slerp(ge, u), tuple(lru)
    for ag in p["agarres"]:
        if ag["lado"] != lado: continue
        gf = int(ag["t_toma"]); kr = gf + t["sostiene"] + t["lanza"]; gu, ge = _goal(lado, ag["delta"], e); ru_, re_ = (Quaternion(q) for q in p["suelta"][lado])
        if gf - t["alcanza"] <= k < gf: u = ss((k - gf + t["alcanza"]) / float(t["alcanza"])); w = u; return qru.slerp(gu, u), qre.slerp(ge, u), tuple(l * (1 - w) + g * w for l, g in zip(lru, locg))
        if gf <= k < gf + t["sostiene"]: return gu, ge, locg
        if gf + t["sostiene"] <= k < kr:
            x_ = (k - gf - t["sostiene"]) / float(t["lanza"]); u = 0.3 * ela(x_) + 0.7 * ss(x_); w = 1 - ss(x_)
            return _qpow(gu, ru_, u), _qpow(ge, re_, u), tuple(l * (1 - w) + g * w for l, g in zip(lru, locg))
        if kr <= k < kr + t["vuelve"]: u = ss((k - kr) / float(t["vuelve"])); return ru_.slerp(qru, u), re_.slerp(qre, u), tuple(lru)
    return None


def prep_cuerpo(p, org, N, fin, por_id, d=None):
    """tabla de los dos brazos para TODOS los frames desde el primer lanzamiento: Euler compatibles frame a frame (tabla de poses o cuaterniones), movimiento secundario de los codos y claves exactas, como `arm_table()`."""
    Euler, _, _ = _mu(); base = por_id[p["base_de"]]; t = p["tiempos"]; kst = min(int(a["t_toma"]) for a in p["agarres"]) - t["alcanza"]; tab = {}; prev = {}; cache = {}
    tbk0 = _pares(p["brazos"]["tt_tbk"])[0][0]
    r0, _l = _base_sin_lanzar(kst - 1, p, org, N, base)
    for lado in ("Right", "Left"): prev[lado + "UpArm_cerdo_1"] = Euler(r0[lado + "UpArm_cerdo_1"], 'XYZ'); prev[lado + "elbow_cerdo_1"] = Euler(r0[lado + "elbow_cerdo_1"], 'XYZ')
    for k in range(kst, N + 1):
        rot, loc = _base_sin_lanzar(k, p, org, N, base)
        for lado in ("Right", "Left"):
            ua, el = lado + "UpArm_cerdo_1", lado + "elbow_cerdo_1"; lru = tuple(loc.get(ua, (0.0, 0.0, 0.0)))
            if k >= tbk0:                                                                # tabla de poses: los Euler se escriben tal cual (sin pasar por cuaterniones)
                e_, x_, l_ = tab_eul(lado, k, lru, p, cache); prev[ua], prev[el] = Euler(e_, 'XYZ'), Euler(x_, 'XYZ'); tab[(lado, k)] = [list(e_), list(x_), list(l_)]; continue
            qru, qre = Euler(rot[ua], 'XYZ').to_quaternion(), Euler(rot[el], 'XYZ').to_quaternion(); st = _arm_state(lado, k, qru, qre, lru, p) or (qru, qre, lru)
            eu = st[0].to_euler('XYZ', prev[ua]); ee = st[1].to_euler('XYZ', prev[el]); prev[ua], prev[el] = eu, ee; tab[(lado, k)] = [list(eu), list(ee), list(st[2])]
    pin = set()                                                                          # frames con el codo EXACTO (pose BACK de Kebyn, impactos del hacha): sin movimiento secundario
    b = p["brazos"]
    for lst in (b["tt_tbk"], b["tt_pre_r"], b["tt_pre_l"], b["tt_x_right"], b["tt_x_left"]):
        for (f0, a_), (f1, b_) in zip(_pares(lst)[:-1], _pares(lst)[1:]):
            if a_ == "BACK" and b_ == "BACK": pin |= set(range(f0, f1 + 1))
    for e in (d or {}).get("exactos") or []:
        if e.get("ventana", 0) > 0 and any("elbow" in h for h in e.get("huesos", {})): pin |= {f + dd for f in e["frames"] for dd in (0, 1)}
    lag = int(round(org["sec_lag"])); dmp = org["sec_damp"]; ks = list(range(kst, N + 1))
    for lado in ("Right", "Left"):
        for ax in range(3):
            vals = [tab[(lado, kk)][1][ax] for kk in ks]
            for i, kk in enumerate(ks):
                if kk in pin: continue
                dl = vals[max(0, i - lag)] * (1 - dmp) + vals[i] * dmp; tab[(lado, kk)][1][ax] = vals[i] * 0.7 + dl * 0.3
    return {"tab": tab, "kst": kst, "base": base}


def raw_cuerpo(k, p, org, t_fin, ctx):
    rot, loc = _base_sin_lanzar(k, p, org, t_fin, ctx["base"])
    w = lean_w(k, p)
    if w > 0:
        for b, a in p["lean"]: rot[b][0] += D(a * w)
    bar = p["barrido"]; lc = wp_eval(_wpl(bar["tt_inclinacion"]), k)[0]
    if lc > 0:                                                                           # se inclina sobre la cadera para llegar a la pila del suelo
        for b, wg in bar["reparto"]: rot[b][0] += D(bar["inclinacion"] * wg * lc)
        rot["Head_cerdo_1"][0] += D(-0.15 * bar["inclinacion"] * lc)
    for lado in ("Right", "Left"):
        t = ctx["tab"].get((lado, k))
        if t is None: continue
        ua, el = lado + "UpArm_cerdo_1", lado + "elbow_cerdo_1"; rot[ua], rot[el] = list(t[0]), list(t[1])
        if ua in loc: loc[ua] = list(t[2])
    return rot, loc


def root_cuerpo(k, p, ctx):
    """root (x, y, z, yaw): aproximacion + rodillas + antorcha + de pie + giros + caida al pozo + avance y retroceso del corte."""
    a = p["root"]; r = p["rodillas"]; base = ctx["base"]["root"]; u = ss((k - base["t_inicio"]) / base["dur"])
    yaw = base["yaw"] * u + base["rebase"] * math.sin(math.pi * min(max((k - base["rebase_ini"]) / base["rebase_dur"], 0.0), 1.0)) ** 2
    x = base["x0"] + base["dx"] * u
    if k >= r["t_ini"]: w = kn_w(k, p); x = x * (1 - w) + r["x"] * w
    an = a["antorcha"]; x += an["dx"] * (ss((k - an["t_ini"]) / an["dur"]) - ss((k - an["t_fin"]) / an["dur"]))
    sc = a["scoot"]; x += sc["dx"] * ss((k - sc["t_ini"]) / float(sc["dur"]))
    sw = stand_w(k, p); y = base["y0"] + base["dy"] * u; dp = p["de_pie"]; x = x * (1 - sw) + dp["x"] * sw; y = y * (1 - sw) + dp["y"] * sw
    co = a["corte"]; x += co["avance"] * ss((k - co["t_avance"]) / co["avance_dur"]) + co["retroceso"] * ss((k - co["t_retroceso"]) / co["retroceso_dur"])
    g = p["giro"]; yaw += 90.0 * ss((k - g["t_ini1"]) / float(g["dur1"])) + 90.0 * ss((k - g["t_ini2"]) / float(g["dur2"]))
    po = a["pozo"]
    return [x, y, base["z"] - po["baja"] * ss((k - po["t_ini"]) / float(po["dur"])), yaw]


TIPOS = {"sentado_cansado": (raw_sentado_cansado, root_sentado, None), "cuerpo": (raw_cuerpo, root_cuerpo, prep_cuerpo)}


# ------------------------------------------------------------------------------------------------------------------------------------------- pipeline
def cargar_referencia(ruta):
    return _json(ruta)


def suavizar(raw_rot, raw_loc, org, N):
    """el suavizado de curvas del generador (`cerdo_1_final`): sm_passes pasadas del filtro [0.25, 0.5, 0.25] mezclado a sm_factor sobre TODOS los huesos menos los brazos (rotaciones y ubicaciones)."""
    fin_rot = {b: [list(v) for v in vs] for b, vs in raw_rot.items()}; fin_loc = {b: [list(v) for v in vs] for b, vs in raw_loc.items()}
    for src, dst in ((raw_rot, fin_rot), (raw_loc, fin_loc)):
        for b in src:
            if BRAZOS(b): continue
            for ax in range(3):
                vals = [src[b][i][ax] for i in range(N)]
                for _ in range(org["sm_passes"]):
                    out = vals[:]
                    for i in range(1, N - 1): out[i] = vals[i] * (1 - org["sm_factor"]) + (vals[i - 1] * 0.25 + vals[i] * 0.5 + vals[i + 1] * 0.25) * org["sm_factor"]
                    vals = out
                for i in range(N): dst[b][i][ax] = vals[i]
    return fin_rot, fin_loc


def aplicar_exactos(fin_rot, exactos, N):
    """seccion `exactos` del guion: en esos frames los huesos (menos los brazos, que ya vienen exactos de su tabla) valen EXACTAMENTE lo que dio el usuario, por encima del suavizado; antes y despues se mezcla en
    `ventana` frames (como el generador: sube en [f-v, f], se mantiene f..f+1, baja en [f+1, f+1+v])."""
    for e in exactos or []:
        v = float(e.get("ventana", 0)); hs = {b: t for b, t in (e.get("huesos") or {}).items() if not BRAZOS(b)}
        if not hs or v <= 0: continue
        for k in range(1, N + 1):
            w = max(ss((k - h + v) / v) * (1 - ss((k - h - 1) / v)) for h in e["frames"])
            if w > 0:
                for b, t in hs.items(): fin_rot[b][k - 1] = [fin_rot[b][k - 1][q] * (1 - w) + D(t[q]) * w for q in range(3)]


def generar(guion, referencia=None, tramos=None):
    """-> {"N", "raw": {rot, loc}, "final": {rot, loc}, "root": [[x,y,z,yaw]...], "micro": [...], "ajuste_hips": [...], "tramos": [...], "migrados": {frame: id}}.
    Los frames de los tramos migrados salen del motor; los demas, de la referencia congelada (si el guion la tiene). Con TODOS los frames cubiertos por tramos la referencia ya no hace falta."""
    d = gv.desplegar(gv.migrar(guion)); mov = d.get("movimiento") or {}; org = organico_de(mov); N = int((d.get("meta") or {}).get("frame_fin") or 0)
    ref = referencia or (cargar_referencia(mov["referencia_numerica"]) if mov.get("referencia_numerica") else None); N = int(ref["N"]) if ref else N
    trs = [t for t in tramos_de(d) if tramos is None or t["id"] in tramos]; por_id = {t["id"]: t["params"] for t in tramos_de(d)}
    if ref:
        raw_r = {b: [list(v) for v in vs] for b, vs in ref["raw"]["rot"].items()}; raw_l = {b: [list(v) for v in vs] for b, vs in ref["raw"]["loc"].items()}; root = [list(v) for v in ref["root"]]
    else: raw_r, raw_l, root = {}, {}, [None] * N
    migrados = {}; cache = {}
    for t in trs:
        raw_fn, root_fn, prep_fn = TIPOS[t["tipo"]]; clave = (t["tipo"], json.dumps(t["params"], sort_keys=True))
        if prep_fn and clave not in cache: cache[clave] = prep_fn(t["params"], org, N, min(N, t["fin"]), por_id, d)
        ctx = cache.get(clave)
        for k in range(max(1, t["inicio"]), min(N, t["fin"]) + 1):
            r, l = raw_fn(k, t["params"], org, N, ctx)
            for b, v in r.items(): raw_r.setdefault(b, [None] * N)[k - 1] = v
            for b, v in l.items(): raw_l.setdefault(b, [None] * N)[k - 1] = v
            root[k - 1] = root_fn(k, t["params"], ctx); migrados[k] = t["id"]
    if not ref:
        falta = [k for k in range(1, N + 1) if k not in migrados]
        if falta: raise ValueError("sin referencia numerica, los tramos tienen que cubrir todos los frames; faltan %d (f%d...)" % (len(falta), falta[0]))
    fin_r, fin_l = suavizar(raw_r, raw_l, org, N); aplicar_exactos(fin_r, d.get("exactos"), N)
    ajuste = mov.get("ajuste_hips") or (ref["ajuste_hips"] if ref else [[0.0, 0.0, 0.0]] * N)
    return {"N": N, "raw": {"rot": raw_r, "loc": raw_l}, "final": {"rot": fin_r, "loc": fin_l}, "root": root, "micro": [micro_scale(k, org) for k in range(1, N + 1)], "ajuste_hips": ajuste, "tramos": trs,
            "migrados": migrados, "yaw_base_deg": mov.get("yaw_base_deg", 0.0)}


def _dang(d):
    return abs((d + math.pi) % (2 * math.pi) - math.pi)


def comparar(res, ref, rango=None):
    """diferencia maxima motor - referencia por capa: rotaciones (grados), ubicaciones (m), root (m / grados), micro. `rango` = (f0, f1) o None = todo. -> dict"""
    N = res["N"]; f0, f1 = rango or (1, N); out = {"raw_rot_deg": 0.0, "final_rot_deg": 0.0, "final_loc_m": 0.0, "root_m": 0.0, "root_yaw_deg": 0.0, "micro": 0.0, "peor": {}}

    def upd(clave, v, k, b=None):
        if v > out[clave]: out[clave] = v; out["peor"][clave] = (k, b)
    for b in res["final"]["rot"]:
        for k in range(f0, f1 + 1):
            i = k - 1
            upd("raw_rot_deg", max(_dang(res["raw"]["rot"][b][i][q] - ref["raw"]["rot"][b][i][q]) for q in range(3)) * 180 / math.pi, k, b)       # angulos equivalentes (+-360) cuentan como iguales
            upd("final_rot_deg", max(_dang(res["final"]["rot"][b][i][q] - ref["final"]["rot"][b][i][q]) for q in range(3)) * 180 / math.pi, k, b)
    for b in res["final"]["loc"]:
        for k in range(f0, f1 + 1): upd("final_loc_m", max(abs(res["final"]["loc"][b][k - 1][q] - ref["final"]["loc"][b][k - 1][q]) for q in range(3)), k, b)
    for k in range(f0, f1 + 1):
        a, c = res["root"][k - 1], ref["root"][k - 1]; upd("root_m", max(abs(a[q] - c[q]) for q in range(3)), k); upd("root_yaw_deg", abs(a[3] - c[3]), k); upd("micro", abs(res["micro"][k - 1] - ref["micro"][k - 1]), k)
    return out


# ------------------------------------------------------------------------------------------------------------------------------------------- Blender
def _rig():
    import bpy
    A = next(o for o in bpy.data.objects if o.type == "ARMATURE" and "Body_cerdo_1" in o.pose.bones); return A, A.parent


try:
    from .claves_util import escritor_de as _escritor_de, fcurves as _cu_fcurves
except Exception:                                                                       # fuera del paquete
    import importlib.util as _ilu2
    _sp2 = _ilu2.spec_from_file_location("claves_util", os.path.join(os.path.dirname(os.path.abspath(__file__)), "claves_util.py")); _cu = _ilu2.module_from_spec(_sp2); _sp2.loader.exec_module(_cu)
    _escritor_de, _cu_fcurves = _cu.escritor_de, _cu.fcurves


def hornear(context, res, frames):
    """escribe en el rig de Cerdo_1 (claves por frame, en la accion donde ya estan las del generador) lo que dice el motor para `frames`: rotaciones, ubicaciones (Hips con el ajuste de suelo), root y escala de Spine1.
    No toca ningun otro frame. -> numero de frames."""
    import math as _m
    A, O = _rig(); frames = list(frames); TH = _m.radians(res.get("yaw_base_deg", 0.0)); f0 = frames[0]
    wa = _escritor_de(A, 'pose.bones["Body_cerdo_1"].rotation_euler', 0, f0); wo = _escritor_de(O, "location", 0, f0)
    for k in frames:
        i = k - 1
        for b, vs in res["final"]["rot"].items():
            for q in range(3): wa.poner('pose.bones["%s"].rotation_euler' % b, q, k, vs[i][q])
        for b, vs in res["final"]["loc"].items():
            v = list(vs[i])
            if b == "Body_cerdo_1": v = [v[q] + res["ajuste_hips"][i][q] for q in range(3)]
            for q in range(3): wa.poner('pose.bones["%s"].location' % b, q, k, v[q])
        for q, v in enumerate((1.0, 1.0, res["micro"][i])): wa.poner('pose.bones["Body:Bend_cerdo_1"].scale', q, k, v)
        x, y, z, yaw = res["root"][i]
        for q, v in enumerate((x, y, z)): wo.poner("location", q, k, v)
        wo.poner("rotation_euler", 2, k, TH + _m.radians(yaw))
    wa.cerrar(); wo.cerrar()
    for ob in (A, O):                                                                       # el NLA a veces no evalua las claves que se tocaron por la API de fcurves hasta reconstruir las relaciones de animacion (igual que Voz Sync)
        if ob.animation_data: ob.animation_data.use_nla = False; ob.animation_data.use_nla = True
        ob.update_tag()
    context.scene.frame_set(context.scene.frame_current); context.view_layer.update()
    return len(frames)


def auditar_accion(context, res, tol_deg=0.05, tol_m=1e-4):
    """revisa las CLAVES de la accion de Cerdo_1 y de su root contra lo que dice el motor: -> {"rot": {(hueso, eje): [frames]}, "loc": {...}, "root": {...}, "claves": n}. Detecta claves corruptas aunque no se vean en los frames muestreados."""
    import math as _m
    A, O = _rig(); out = {"rot": {}, "loc": {}, "root": {}, "claves": 0}; TH = _m.radians(res.get("yaw_base_deg", 0.0))

    def curvas(ob, ruta0):
        ad = ob.animation_data
        act = ad.action if ad and ad.action else next((t.strips[0].action for t in ad.nla_tracks if t.name.startswith("Base") and t.strips), None)
        return {(f.data_path, f.array_index): f for f in _cu_fcurves(act)} if act else {}
    for (ruta, idx), fc in curvas(A, None).items():
        if ".rotation_euler" in ruta or ".location" in ruta:
            b = ruta.split('"')[1]; rot = ruta.endswith("rotation_euler"); tabla = res["final"]["rot" if rot else "loc"].get(b)
            if tabla is None: continue
            for p in fc.keyframe_points:
                k = int(round(p.co[0]))
                if not 1 <= k <= res["N"]: continue
                esp = tabla[k - 1][idx] + (res["ajuste_hips"][k - 1][idx] if (b == "Body_cerdo_1" and not rot) else 0.0); d = abs(p.co[1] - esp); out["claves"] += 1
                if rot: d = abs((d + _m.pi) % (2 * _m.pi) - _m.pi) * 180 / _m.pi
                if d > (tol_deg if rot else tol_m): out["rot" if rot else "loc"].setdefault((b, idx), []).append(k)
    for (ruta, idx), fc in curvas(O, None).items():
        if ruta in ("location", "rotation_euler"):
            for p in fc.keyframe_points:
                k = int(round(p.co[0]))
                if not 1 <= k <= res["N"]: continue
                x = res["root"][k - 1]; esp = x[idx] if ruta == "location" else (TH + _m.radians(x[3]) if idx == 2 else None)
                if esp is not None and abs(p.co[1] - esp) > 1e-4: out["root"].setdefault((ruta, idx), []).append(k)
    return out


def verificar_en_blender(context, res, frames):
    """compara lo que EVALUA Blender (sin voces) con lo que dice el motor: diferencia maxima de rotaciones (grados), ubicaciones (m) y root (m / grados) en `frames`."""
    import math as _m
    A, O = _rig(); PA = A.pose.bones; sc = context.scene; f0 = sc.frame_current
    trs = [t for t in A.animation_data.nla_tracks if t.name.startswith("VozSync")]
    for t in trs: t.mute = True
    out = {"rot_deg": 0.0, "loc_m": 0.0, "root_m": 0.0, "root_yaw_deg": 0.0, "n": 0}
    try:
        for k in frames:
            sc.frame_set(k); context.view_layer.update(); i = k - 1; out["n"] += 1
            for b, vs in res["final"]["rot"].items(): out["rot_deg"] = max(out["rot_deg"], max(abs(PA[b].rotation_euler[q] - vs[i][q]) for q in range(3)) * 180 / _m.pi)
            for b, vs in res["final"]["loc"].items():
                v = [vs[i][q] + (res["ajuste_hips"][i][q] if b == "Body_cerdo_1" else 0.0) for q in range(3)]; out["loc_m"] = max(out["loc_m"], max(abs(PA[b].location[q] - v[q]) for q in range(3)))
            x, y, z, yaw = res["root"][i]; out["root_m"] = max(out["root_m"], abs(O.location.x - x), abs(O.location.y - y), abs(O.location.z - z))
            out["root_yaw_deg"] = max(out["root_yaw_deg"], abs(((_m.degrees(O.rotation_euler.z) - res.get("yaw_base_deg", 0.0) - yaw) + 180) % 360 - 180))
    finally:
        for t in trs: t.mute = False
        sc.frame_set(f0)
    return {k: (round(v, 6) if isinstance(v, float) else v) for k, v in out.items()}
