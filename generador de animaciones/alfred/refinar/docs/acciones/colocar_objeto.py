# -*- coding: utf-8 -*-
"""EJECUTOR GENERICO de la accion `colocar_objeto` (esquema `alfred_accion_v1`): un personaje saca un objeto de su espalda con una mano y lo coloca en un sitio del mundo, inclinandose si hace falta.
Todo lo que cambia entre una escena y otra esta en el JSON de la accion (ver `colocar_objeto_exterior/accion.json` y su LEEME): que objeto, que mano, de donde sale, donde se coloca, como se inclina el cuerpo,
cuando ocurre cada cosa y que suena. Este script no tiene numeros de escena.
USO (dentro de Blender, con la escena abierta):
    ns = {"__name__": "accion", "ACCION_JSON": r"...\\accion.json"}; exec(open(r"...\\colocar_objeto.py", encoding="utf-8").read(), ns)
Necesita el add-on Alfred Animation Studio (fuente en refinar/alfred_animation_studio) y `docs/parte3/ik_brazos.py`. Repetible: reescribe las claves del rango de la accion. No guarda el .blend."""
import importlib.util
import json
import math
import os

import bpy
from mathutils import Euler, Quaternion, Vector

REFINAR = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"; ADDON = os.path.join(REFINAR, "alfred_animation_studio"); RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(REFINAR)))
exec(open(os.path.join(REFINAR, "docs", "parte3", "ik_brazos.py"), encoding="utf-8").read(), globals())          # fk, mundo, cabeza_cola, resolver, AA (armature con Hips_alfred), OO (su root)


def _cargar(n):
    sp = importlib.util.spec_from_file_location(n, os.path.join(ADDON, n + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


cu = _cargar("claves_util"); om = _cargar("objetos_mundo"); gv = _cargar("guion_v2"); ss = om.ss
A = json.load(open(ACCION_JSON, encoding="utf-8")); P = A["parametros"]; TT = dict(A["tiempos"]); LADO = P["lado"]; SG = -1.0 if LADO == "Left" else 1.0
UP, EL = LADO + "UpArm_alfred", LADO + "elbow_alfred"


def t_(x):
    """tiempo = numero, nombre de un tiempo de la accion, o 'nombre+N' / 'nombre-N'."""
    if isinstance(x, (int, float)): return int(x)
    s = x.replace(" ", ""); base = s; off = 0
    for sg in ("+", "-"):
        if sg in s[1:]: base, o = s.rsplit(sg, 1); off = int(o) * (1 if sg == "+" else -1); break
    return TT[base] + off


sc = bpy.context.scene; F0 = TT["inicio"]; FIN = TT["fin"]; sc.frame_set(F0); bpy.context.view_layer.update()
ROT0 = {b.name: tuple(b.rotation_euler) for b in AA.pose.bones}; LOC0 = {b.name: tuple(b.location) for b in AA.pose.bones}; ROOT0 = (tuple(OO.location), OO.rotation_euler[2])
CU = P["cuerpo"]; DYAW, LEAN, ROOT2 = float(CU["giro_deg"]), float(CU["inclinacion_deg"]), tuple(CU["root_xy"])
DEST = P["destino"]; SUELO = Vector(DEST["loc"])


def pose_M(root, dyaw, lean, z=None):
    rot = {k: list(v) for k, v in ROT0.items()}
    for b, w in (("Spine_alfred", .32), ("Spine1_alfred", .34), ("Spine2_alfred", .34)): rot[b][0] += math.radians(lean * w)
    return fk(rot, LOC0), mundo((root[0], root[1], ROOT0[0][2] if z is None else z), ROOT0[1] + math.radians(dyaw))


# --- brazo: reposo (el de F0) -> espalda -> alcance -> reposo
q_rest = Euler(ROT0[UP], 'XYZ').to_quaternion(); x_rest = ROT0[EL][0]; UP_LOC0 = LOC0[UP]; EL_ROT0 = ROT0[EL]
M0, Mw0 = pose_M(ROOT0[0][:2], 0, 0); back_w = Mw0 @ M0["Spine1_alfred"].translation; off = P["origen"]["offset_mundo"]
BACK = Vector((back_w.x + off[0], back_w.y + off[1] * SG, back_w.z + off[2]))
q_back, qe_back, e_back, _ = resolver(LADO, M0["Spine2_alfred"], Mw0, BACK, codo_hint=BACK + Vector((-0.05, -0.2 * SG, -0.2)), inicio=(q_rest, x_rest), iters=5000, semilla=3)
EL_BACK = (2 * math.atan2(qe_back.x, qe_back.w), 0.0, 0.0)
AL = P["brazo"]["alcance"]
if AL["modo"] == "pose":                                                       # pose tomada a mano en Blender (valores de la barra de huesos)
    UP_LOC1 = tuple(AL["hombro"]["loc"]); q_reach = Euler([math.radians(a) for a in AL["hombro"]["rot_deg"]], 'XYZ').to_quaternion(); EL_ROT1 = tuple(math.radians(a) for a in AL["codo"]["rot_deg"]); e_reach = 0.0
else:                                                                          # "ik": la muneca llega a `muneca_sobre_destino` por encima del destino
    M2, Mw2 = pose_M(ROOT2, DYAW, LEAN); tgt = SUELO + Vector(AL.get("muneca_sobre_destino", [0, 0, 0.25]))
    q_reach, qe_r, e_reach, _ = resolver(LADO, M2["Spine2_alfred"], Mw2, tgt, inicio=(q_back, EL_BACK[0]), iters=6000, semilla=2); UP_LOC1 = UP_LOC0; EL_ROT1 = (2 * math.atan2(qe_r.x, qe_r.w), 0.0, 0.0)
print("error muneca: espalda %.3f m, alcance %.3f m (modo %s)" % (e_back, e_reach, AL["modo"]))


def mezcla(a, b, u):
    return a.slerp(b if a.dot(b) >= 0 else -b, u)


def lerp3(a, b, u):
    return tuple(a[i] + (b[i] - a[i]) * u for i in range(3))


Te, Ta, Tq, Tv = t_("espalda"), t_("alcance"), t_("quieto"), t_("vuelve")


def estado(k):
    """-> (inclinacion, giro, avance del root 0..1, q hombro, ubicacion hombro, euler codo)"""
    if k <= Te: u = ss((k - F0) / (Te - F0)); return 0.0, 0.0, 0.0, mezcla(q_rest, q_back, u), UP_LOC0, lerp3(EL_ROT0, EL_BACK, u)
    if k <= Ta: u = ss((k - Te) / (Ta - Te)); return LEAN * u, DYAW * u, u, mezcla(q_back, q_reach, u), lerp3(UP_LOC0, UP_LOC1, u), lerp3(EL_BACK, EL_ROT1, u)
    if k <= Tq: return LEAN, DYAW, 1.0, q_reach, UP_LOC1, EL_ROT1
    if k <= Tv: u = ss((k - Tq) / (Tv - Tq)); return LEAN * (1 - u), DYAW * (1 - u), 1 - u, mezcla(q_reach, q_rest, u), lerp3(UP_LOC1, UP_LOC0, u), lerp3(EL_ROT1, EL_ROT0, u)
    return 0.0, 0.0, 0.0, q_rest, UP_LOC0, EL_ROT0


# --- rango de la escena y tira base del NLA
sc.frame_end = max(sc.frame_end, FIN)
for t in (AA.animation_data.nla_tracks if AA.animation_data else []):                      # sin animacion previa (p. ej. base_parte_5) no hay pistas que extender
    for s in t.strips:
        if t.name.startswith("Base") and s.frame_end < FIN: s.frame_end_ui = FIN
# --- claves del cuerpo
wa = cu.escritor_de(AA, 'pose.bones["Spine_alfred"].rotation_euler', 0, F0 + 1); wo = cu.escritor_de(OO, "location", 0, F0 + 1); prev = Euler(ROT0[UP], 'XYZ')
for k in range(F0, FIN + 1):                                                  # desde F0: la clave de partida queda escrita (con los valores de reposo)
    lean, dyaw, ur, q, upl, elr = estado(k)
    for b, w in (("Spine_alfred", .32), ("Spine1_alfred", .34), ("Spine2_alfred", .34)): wa.poner('pose.bones["%s"].rotation_euler' % b, 0, k, ROT0[b][0] + math.radians(lean * w))
    e = q.to_euler('XYZ', prev); prev = e
    for i in range(3):
        wa.poner('pose.bones["%s"].rotation_euler' % UP, i, k, e[i]); wa.poner('pose.bones["%s"].location' % UP, i, k, upl[i]); wa.poner('pose.bones["%s"].rotation_euler' % EL, i, k, elr[i])
    for i in range(2): wo.poner("location", i, k, ROOT0[0][i] + (ROOT2[i] - ROOT0[0][i]) * ur)
    wo.poner("location", 2, k, ROOT0[0][2]); wo.poner("rotation_euler", 2, k, ROOT0[1] + math.radians(dyaw))
for b_ in ("Spine_alfred", "Spine1_alfred", "Spine2_alfred"): wa.limpiar('pose.bones["%s"].rotation_euler' % b_, 0, FIN + 1)             # si antes duraba mas, se quitan las claves que sobran despues del fin
for i in range(3):
    for ruta_ in ('pose.bones["%s"].rotation_euler' % UP, 'pose.bones["%s"].location' % UP, 'pose.bones["%s"].rotation_euler' % EL): wa.limpiar(ruta_, i, FIN + 1)
    wo.limpiar("location", i, FIN + 1)
wo.limpiar("rotation_euler", 2, FIN + 1)
wa.cerrar(); wo.cerrar()
for ob in (AA, OO):
    if ob.animation_data: ob.animation_data.use_nla = False; ob.animation_data.use_nla = True
    ob.update_tag()
sc.frame_set(Ta); bpy.context.view_layer.update()
mano = AA.matrix_world @ AA.pose.bones[EL].tail; print("muneca en f%d: %s" % (Ta, [round(c, 3) for c in mano]))

# --- el objeto: copia de otro (con su jerarquia: malla, llama, humo, luz) o importado de un .blend
OB = P["objeto"]; nombre = OB["nombre"]
if bpy.data.objects.get(nombre) is None:
    col = bpy.data.collections.get(nombre) or bpy.data.collections.new(nombre)
    if col.name not in sc.collection.children: sc.collection.children.link(col)
    if OB.get("copia_jerarquia_de"):
        raiz = bpy.data.objects[OB["copia_jerarquia_de"]]; objs = [raiz] + list(raiz.children_recursive); mp = {}
        for x in objs:
            c = x.copy()
            if x.type == 'LIGHT': c.data = x.data.copy()
            if c.animation_data: c.animation_data_clear()
            if x.type == 'LIGHT' and c.data.animation_data: c.data.animation_data_clear()
            c.name = nombre if x is raiz else x.name + "_" + nombre; mp[x] = c; col.objects.link(c)
        for x in objs:
            if x.parent: mp[x].parent = mp[x.parent]; mp[x].matrix_parent_inverse = x.matrix_parent_inverse.copy()
    else:
        ruta = os.path.join(RAIZ, OB["blend"]); n0 = OB.get("fuente_objeto", nombre)
        with bpy.data.libraries.load(ruta, link=False) as (src, dst): dst.objects = [n0]
        o = dst.objects[0]; o.name = nombre; col.objects.link(o); o.parent = None
    bpy.data.objects[nombre].rotation_mode = 'QUATERNION'
agarre = om.agarre_desde_mundo(P["armature"], EL, Ta, list(SUELO), DEST.get("rot_deg", [0, 0, 0]))
escala = float(OB.get("escala", 1.0)); Ts = t_("suelta")
cfg = {"id": "obj_" + nombre, "nombre": nombre, "armature": P["armature"], "hueso": EL, "escala_mano": escala, "inicial": {"loc": [BACK.x, BACK.y, BACK.z], "escala": 0.001, "visible": True},
       "agarres": {"mano": {"matriz": agarre, "origen": "su sitio final en el destino, relativo a la mano en f%d" % Ta}},
       "eventos": [{"tipo": "en_mano", "t": Te, "agarre": "mano", "pop": {"dur": int(OB.get("pop_frames", 3)), "escala": escala}},
                   {"tipo": "asienta", "t": Ts, "dur": int(OB.get("asienta_frames", 3)), "vivo": True, "en": {"loc": list(SUELO), "rot": DEST.get("rot_deg", [0, 0, 0]), "escala": float(OB.get("escala_destino", escala))}}]}
mundo_ = []
if OB.get("luz"): mundo_.append({"id": "luz_" + nombre, "accion": "luz", "t": 1, "objeto": nombre, "energia": float(OB["luz"]["energia"]) if "energia" in OB["luz"] else bpy.data.objects[OB["luz"]["energia_de"]].data.energy,
                                 "claves": [[1, 0.0], [Te, 0.0], [Te + int(OB["luz"].get("encendido_frames", 3)), 1.0], [FIN, 1.0]]})
g = gv.migrar({"version": "2.0", "meta": {"frame_fin": FIN}, "anclas": {}, "objetos": [cfg], "mundo": mundo_})
res = om.calcular(bpy.context, g, frames=[1, 2] + list(range(max(1, F0 - 2), FIN + 1))); om.aplicar(bpy.context, res); om.aplicar_mundo_luces(bpy.context, g)
# --- sonidos (tiras en el VSE, con el id de la accion para poder quitarlas)
ed = sc.sequence_editor or sc.sequence_editor_create(); sonp = os.path.join(RAIZ, "sonidos", "sounds"); pref = A["id"] + ":"
for s_ in [x for x in ed.strips_all if str(x.get("guion_id", "")).startswith(pref)]: ed.strips.remove(s_)
for m in A.get("sonidos", []):
    fr = t_(m["t"]); st = ed.strips.new_sound("SND_%s_%d" % (m["etiqueta"], fr), os.path.normpath(os.path.join(sonp, m["archivo"])), int(m.get("canal", 22)), fr); st.volume = float(m.get("volumen", 1.0)); st.pan = float(m.get("pan", 0.0))
    st["mcsnd"] = m.get("grupo", "objetos"); st["mcsnd_ev"] = m["etiqueta"]; st["guion_id"] = pref + m["etiqueta"]
ob = bpy.data.objects[nombre]; sc.frame_set(FIN); bpy.context.view_layer.update()
print("%s en f%d: %s (destino %s)" % (nombre, FIN, [round(c, 3) for c in ob.matrix_world.translation], list(SUELO)))
sc.frame_set(F0)
