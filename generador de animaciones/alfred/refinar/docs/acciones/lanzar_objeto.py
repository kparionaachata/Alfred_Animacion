# -*- coding: utf-8 -*-
"""EJECUTOR GENERICO de la accion `lanzar_objeto` (esquema `alfred_accion_v1`): un personaje saca un objeto de su espalda con una mano, arma el brazo, lo lanza contra un PUNTO del mundo (la cara de un zombie...), el objeto rebota y cae en otro punto.
Cuerpo, cuello y brazos se calculan con la IK de `docs/parte3/ik_brazos.py` a partir de poses CLAVE definidas en el JSON de la accion (`pasos`: tiempo, giro del cuerpo, inclinacion, avance, posicion relativa de la mano y del codo respecto al cuerpo).
La mirada se mantiene fija en el punto de mira (el cuello compensa giro e inclinacion). El brazo izquierdo vuelve de donde estaba (p. ej. en V) a su reposo.
USO (dentro de Blender): ns = {"__name__": "accion", "ACCION_JSON": r"...\\accion.json"}; exec(open(r"...\\lanzar_objeto.py", encoding="utf-8").read(), ns)   -> deja en ns["OBJ_CFG"] la configuracion del objeto (guion v2) para exportar.
Repetible (la clave de partida del frame `inicio` conserva la pose de ese frame; quita las claves que sobren despues del `fin`). No guarda el .blend."""
import importlib.util
import json
import math
import os

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

REFINAR = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"; ADDON = os.path.join(REFINAR, "alfred_animation_studio"); RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(REFINAR)))
exec(open(os.path.join(REFINAR, "docs", "parte3", "ik_brazos.py"), encoding="utf-8").read(), globals())          # fk, mundo, resolver, AA, OO


def _cargar(n):
    sp = importlib.util.spec_from_file_location(n, os.path.join(ADDON, n + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


cu = _cargar("claves_util"); om = _cargar("objetos_mundo"); gv = _cargar("guion_v2"); ss = om.ss
A = json.load(open(ACCION_JSON, encoding="utf-8")); P = A["parametros"]; TT = dict(A["tiempos"]); LADO = P["lado"]; OTRO = "Left" if LADO == "Right" else "Right"; SG = -1.0 if LADO == "Left" else 1.0
UP, EL, UPO, ELO = LADO + "UpArm_alfred", LADO + "elbow_alfred", OTRO + "UpArm_alfred", OTRO + "elbow_alfred"; SP = (("Spine_alfred", .32), ("Spine1_alfred", .34), ("Spine2_alfred", .34))


def t_(x):
    if isinstance(x, (int, float)): return int(x)
    s = x.replace(" ", ""); base = s; off = 0
    for sg in ("+", "-"):
        if sg in s[1:]: base, o = s.rsplit(sg, 1); off = int(o) * (1 if sg == "+" else -1); break
    return TT[base] + off


sc = bpy.context.scene; F0 = TT["inicio"]; FIN = TT["fin"]
sc.frame_set(int(P["reposo_frame"])); bpy.context.view_layer.update(); ID_ROT = {b.name: tuple(b.rotation_euler) for b in AA.pose.bones}; ID_LOC = {b.name: tuple(b.location) for b in AA.pose.bones}
sc.frame_set(F0); bpy.context.view_layer.update()
ROT0 = {b.name: tuple(b.rotation_euler) for b in AA.pose.bones}; LOC0 = {b.name: tuple(b.location) for b in AA.pose.bones}; ROOT0 = (tuple(OO.location), OO.rotation_euler[2])
FR = P["frente"]; NK = float(FR.get("cuello_x_por_grado_de_mirada", 0.84)); YAW0 = float(FR["mira_a_grados"]) + math.degrees(ROOT0[1]) - float(FR["rz_deg"])                  # hacia donde mira el cuerpo en F0
LEAN0 = math.degrees(sum(ROT0[b][0] - ID_ROT[b][0] for b, w in SP)); NECK0 = ROT0["Neck_alfred"]; MIRA = Vector(P["mira_a"]["loc"])
D0 = Vector((math.cos(math.radians(YAW0)), math.sin(math.radians(YAW0)), 0))                                                                       # direccion de avance (hacia el objetivo)
PASOS = [dict(p, t=t_(p["t"])) for p in P["pasos"]]; KEYS = [dict(t=F0, dyaw=0.0, lean=LEAN0, adv=0.0)] + [dict(t=p["t"], **p["cuerpo"]) for p in PASOS]; TE = t_(P["origen"]["t"]); TR = t_(P["lanzamiento"]["t"])


def rel(root_xy, yaw_deg, r, z0=None):
    c, s = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg)); return Vector((root_xy[0] + c * r[0] - s * r[1], root_xy[1] + s * r[0] + c * r[1], (ROOT0[0][2] if z0 is None else z0) + r[2]))


def cuerpo_en(t):
    """-> (giro respecto a F0 en grados, inclinacion, avance) interpolado entre las claves"""
    for a, b in zip(KEYS, KEYS[1:]):
        if t <= b["t"]:
            u = (t - a["t"]) / float(b["t"] - a["t"]); u = u if b.get("lineal") else ss(u)
            return tuple(a[k] + (b[k] - a[k]) * u for k in ("dyaw", "lean", "adv"))
    k = KEYS[-1]; return k["dyaw"], k["lean"], k["adv"]


def root_xy(adv): return (ROOT0[0][0] + D0.x * adv, ROOT0[0][1] + D0.y * adv)


def pose_M(dyaw, lean, adv):
    rot = {k: list(v) for k, v in ID_ROT.items()}
    for b, w in SP: rot[b][0] += math.radians(lean * w)
    xy = root_xy(adv); return fk(rot, LOC0), mundo((xy[0], xy[1], ROOT0[0][2]), ROOT0[1] + math.radians(dyaw))


# --- poses clave del brazo (se resuelven en orden, cada una a partir de la anterior)
q_ini = Euler(ROT0[UP], 'XYZ').to_quaternion(); x_ini = ROT0[EL][0]; ARM = [dict(t=F0, q=q_ini, x=x_ini, el=ROT0[EL])]; q_prev, x_prev = q_ini, x_ini
OFF = P["origen"]["offset_espalda"]
for p in PASOS:
    dy, ln, ad = p["cuerpo"]["dyaw"], p["cuerpo"]["lean"], p["cuerpo"]["adv"]
    if p.get("reposo"): ARM.append(dict(t=p["t"], q=Euler(ID_ROT[UP], 'XYZ').to_quaternion(), x=ID_ROT[EL][0], el=ID_ROT[EL])); continue
    M, Mw = pose_M(dy, ln, ad); xy = root_xy(ad); yaw = YAW0 + dy
    if p.get("espalda"): sp1 = Mw @ M["Spine1_alfred"].translation; tgt = rel((sp1.x, sp1.y), yaw, (0, 0, 0), sp1.z) if False else (sp1 + Vector((math.cos(math.radians(yaw)) * OFF[0] - math.sin(math.radians(yaw)) * OFF[1] * SG, math.sin(math.radians(yaw)) * OFF[0] + math.cos(math.radians(yaw)) * OFF[1] * SG, OFF[2])))
    else: tgt = rel(xy, yaw, p["mano_rel"])
    dh = p["codo_delta"]; hint = tgt + (rel((0, 0), yaw, dh, 0.0) - Vector((0, 0, 0)))
    q, qe, err, codo = resolver(LADO, M["Spine2_alfred"], Mw, tgt, codo_hint=hint, inicio=(q_prev, x_prev), iters=int(p.get("iters", 6000)), semilla=int(p.get("semilla", 3)))
    x = 2 * math.atan2(qe.x, qe.w); ARM.append(dict(t=p["t"], q=q, x=x, el=(x, 0.0, 0.0))); q_prev, x_prev = q, x; p["_tgt"] = tgt; print("paso %-10s f%d: error muneca %.3f m, mano %s" % (p["nombre"], p["t"], err, [round(c, 3) for c in tgt]))
if True:
    q_i2 = Euler(ROT0[UPO], 'XYZ').to_quaternion(); q_i3 = Euler(ID_ROT[UPO], 'XYZ').to_quaternion(); TL = t_(P["brazo_otro"]["reposo_en"])


def brazo_en(t):
    for a, b in zip(ARM, ARM[1:]):
        if t <= b["t"]:
            u = (t - a["t"]) / float(b["t"] - a["t"]); u = u if b["t"] - a["t"] <= 6 else ss(u); qa, qb = a["q"], b["q"]; q = qa.slerp(qb if qa.dot(qb) >= 0 else -qb, u)
            return q, tuple(a["el"][i] + (b["el"][i] - a["el"][i]) * u for i in range(3))
    return ARM[-1]["q"], ARM[-1]["el"]


def otro_en(t):
    u = ss(max(0.0, min(1.0, (t - F0) / float(TL - F0)))); qb = q_i3 if q_i2.dot(q_i3) >= 0 else -q_i3
    return q_i2.slerp(qb, u), tuple(ROT0[ELO][i] + (ID_ROT[ELO][i] - ROT0[ELO][i]) * u for i in range(3))


# --- claves del cuerpo
sc.frame_end = max(sc.frame_end, FIN)
for t in (AA.animation_data.nla_tracks if AA.animation_data else []):
    for s in t.strips:
        if t.name.startswith("Base") and s.frame_end < FIN: s.frame_end_ui = FIN
wa = cu.escritor_de(AA, 'pose.bones["Spine_alfred"].rotation_euler', 0, F0 + 1); wo = cu.escritor_de(OO, "location", 0, F0 + 1); prev = Euler(ROT0[UP], 'XYZ'); prevo = Euler(ROT0[UPO], 'XYZ')
for k in range(F0, FIN + 1):
    dyaw, lean, adv = cuerpo_en(k); xy = root_xy(adv)
    for b, w in SP: wa.poner('pose.bones["%s"].rotation_euler' % b, 0, k, ID_ROT[b][0] + math.radians(lean * w))
    wa.poner('pose.bones["Neck_alfred"].rotation_euler', 0, k, NECK0[0] - math.radians((lean - LEAN0) / NK)); wa.poner('pose.bones["Neck_alfred"].rotation_euler', 1, k, NECK0[1] - math.radians(dyaw))        # la mirada se queda en el punto
    q, elr = brazo_en(k); e = q.to_euler('XYZ', prev); prev = e; qo, elo = otro_en(k); eo = qo.to_euler('XYZ', prevo); prevo = eo
    for i in range(3):
        wa.poner('pose.bones["%s"].rotation_euler' % UP, i, k, e[i]); wa.poner('pose.bones["%s"].location' % UP, i, k, LOC0[UP][i]); wa.poner('pose.bones["%s"].rotation_euler' % EL, i, k, elr[i])
        wa.poner('pose.bones["%s"].rotation_euler' % UPO, i, k, eo[i]); wa.poner('pose.bones["%s"].rotation_euler' % ELO, i, k, elo[i])
    wo.poner("location", 0, k, xy[0]); wo.poner("location", 1, k, xy[1]); wo.poner("location", 2, k, ROOT0[0][2]); wo.poner("rotation_euler", 2, k, ROOT0[1] + math.radians(dyaw))
for b_, w_ in SP: wa.limpiar('pose.bones["%s"].rotation_euler' % b_, 0, FIN + 1)
for i in range(2): wa.limpiar('pose.bones["Neck_alfred"].rotation_euler', i, FIN + 1)
for i in range(3):
    for n_ in (UP, EL, UPO, ELO): wa.limpiar('pose.bones["%s"].rotation_euler' % n_, i, FIN + 1)
    wa.limpiar('pose.bones["%s"].location' % UP, i, FIN + 1); wo.limpiar("location", i, FIN + 1)
wo.limpiar("rotation_euler", 2, FIN + 1); wa.cerrar(); wo.cerrar()
for ob in (AA, OO):
    if ob.animation_data: ob.animation_data.use_nla = False; ob.animation_data.use_nla = True
    ob.update_tag()
# --- el objeto
OB = P["objeto"]; nombre = OB["nombre"]; esc = float(OB.get("escala", 1.0))
if bpy.data.objects.get(nombre) is None:
    col = bpy.data.collections.get(nombre) or bpy.data.collections.new(nombre)
    if col.name not in sc.collection.children: sc.collection.children.link(col)
    ruta = os.path.join(RAIZ, OB["blend"]); n0 = OB.get("fuente_objeto", nombre)
    with bpy.data.libraries.load(ruta, link=False) as (src, dst): dst.objects = [n0]
    o = dst.objects[0]; o.name = nombre; col.objects.link(o); o.parent = None; o.rotation_mode = 'QUATERNION'
BACK = next(p["_tgt"] for p in PASOS if p.get("espalda")); LZ = P["lanzamiento"]; V1 = int(LZ["vuelo"]); RBS = P["rebote"] if isinstance(P["rebote"], list) else [P["rebote"]]
EVT = [{"tipo": "en_mano", "t": TE, "agarre": "mano", "pop": {"dur": int(OB.get("pop_frames", 3)), "escala": esc}},
       {"tipo": "lanza", "t": TR, "vuelo": V1, "a": {"centro": LZ["golpea_en"], "quat": LZ.get("quat", [1, 0, 0, 0]), "escala": esc}, "giro": {"eje": LZ["giro"]["eje"], "de": LZ["giro"]["de"], "a": 0.0, "curva": "suave"}, "nota": "vuelo hasta la cara del zombie (golpea)"}]
t_r = TR + V1
for k_, RB in enumerate(RBS):                                                                       # rebotes seguidos: cada uno parte donde acabo el anterior
    e_ = {"tipo": "rebota", "t": t_r, "vuelo": int(RB["vuelo"]), "a": {"centro": RB["cae_en"], "quat": RB.get("quat", [1, 0, 0, 0]), "escala": esc}, "giro": {"eje": RB["giro"]["eje"], "de": RB["giro"]["de"], "a": 0.0}, "nota": RB.get("nota", "rebote %d" % (k_ + 1))}
    if RB.get("arco"): e_["arco"] = RB["arco"]
    EVT.append(e_); t_r += int(RB["vuelo"])
OBJ_CFG = {"id": "obj_" + nombre, "nombre": nombre, "armature": P["armature"], "hueso": EL, "escala_mano": esc, "inicial": {"loc": [BACK.x, BACK.y, BACK.z], "escala": 0.001, "visible": True},
           "agarres": {"mano": {"matriz": OB["agarre_mano"], "origen": "agarre de la mano derecha tomado de stick_1 (valores de Kebyn en f625)"}}, "eventos": EVT}
V2 = t_r - (TR + V1)
g = gv.migrar({"version": "2.0", "meta": {"frame_fin": FIN}, "anclas": {}, "objetos": [OBJ_CFG], "mundo": []})
res = om.calcular(bpy.context, g, frames=[1, 2] + list(range(max(1, F0 - 2), FIN + 1))); om.aplicar(bpy.context, res)
ob = bpy.data.objects[nombre]; sc.frame_set(TR + V1); bpy.context.view_layer.update(); p1 = [round(c, 3) for c in ob.matrix_world.translation]; sc.frame_set(FIN); bpy.context.view_layer.update()
print("%s: f%d-f%d | sale de la espalda f%d, lanza f%d, golpea f%d en %s (objetivo %s), cae en %s (%d rebote(s))" % (A["id"], F0, FIN, TE, TR, TR + V1, p1, list(LZ["golpea_en"]), [round(c, 3) for c in ob.matrix_world.translation], len(RBS)))
sc.frame_set(F0)
