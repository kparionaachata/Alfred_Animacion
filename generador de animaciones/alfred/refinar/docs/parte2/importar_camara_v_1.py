"""Se ejecuta DENTRO de Blender (exec). Inserta los keyframes de la camara cinematografica continua (camara_parte2.json, generado por compose_camara_parte2.py): ubicacion de `Camara_Cinematica`
(su TRACK_TO ya apunta a `Cam_Foco`), ubicacion de `Cam_Foco` (punto de mira entre Alfred y Jerry) y focal. Antes ajusta con raycast cada muestra: si el terreno, un arbol o un bloque tapa la
vista entre la camara y el punto de mira (o la camara queda dentro de algo) sube la elevacion y, si no basta, acerca la camara. NO renderiza.
Idempotente: borra los keyframes anteriores de esos objetos antes de insertar.
"""
import bpy, json, math, os
from mathutils import Vector

BASE = r"C:\Users\user\Desktop\Alfred_Animacion"
J = json.load(open(os.path.join(BASE, r"generador de animaciones\alfred\refinar\docs\parte2\camara_parte2.json"), encoding="utf-8"))
sc = bpy.context.scene; cam = bpy.data.objects["Camara_Cinematica"]; foco = bpy.data.objects["Cam_Foco"]
PERSONAJES = {"Object", "a", "jerry", "Dog_001_rig"} | {f"zombie_{n}" for n in range(1, 6)} | {f"zombie_{n}_Armature" for n in range(1, 6)} | {f"armature_face_zombie_{n}" for n in range(1, 6)}


def es_personaje(o):
    while o is not None:
        if o.name in PERSONAJES or o.name.startswith(("ojo_", "antorcha", "torch", "smoke")): return True
        o = o.parent
    return False


sc.frame_set(J["N"])                                                       # estado final: todos los bloques del refugio visibles (obstaculos conservadores)
dg = bpy.context.evaluated_depsgraph_get()


BLOQ = json.load(open(os.path.join(BASE, "generador de animaciones", "alfred", "refinar", "docs", "parte2", "refugio_bloques.json"), encoding="utf-8"))["bloques"]
APARECE = {f"refugio_bloque_{i:02d}": b["frame"] for i, b in enumerate(BLOQ)}


def libre(origen, destino, f=None):
    """distancia hasta el primer obstaculo que no sea un personaje (None si el camino esta libre)."""
    d = destino - origen; L = d.length; d.normalize(); o = origen.copy(); recorrido = 0.0
    for _ in range(12):
        ok, loc, nor, idx, obj, mat = sc.ray_cast(dg, o, d, distance=L - recorrido)
        if not ok: return None
        ignora = es_personaje(obj) or obj.name.startswith("Suzanne") or "Water" in obj.name            # el agua no tapa la vista: los personajes nadan justo bajo su superficie
        ignora = ignora or (obj.name in APARECE and f is not None and f < APARECE[obj.name])           # un bloque del refugio aun no existe antes de su frame de aparicion
        if not ignora: return recorrido + (loc - o).length
        recorrido += (loc - o).length + 0.05; o = loc + d * 0.05
    return None


def suelo(x, y, zmax=80.0):
    ok, loc, nor, idx, obj, mat = sc.ray_cast(dg, Vector((x, y, zmax)), Vector((0, 0, -1)), distance=zmax + 20)
    return loc.z if ok else None


ajustes = 0; res = []
for m in J["muestras"]:
    t = Vector(m["mira"]); c = Vector(m["cam"]); d0 = (c - t).length; v = c - t
    az = math.atan2(v.y, v.x); el = math.asin(v.z / d0) if d0 > 1e-6 else 0.0; d = d0; hecho = False
    for intento in range(5):
        c = t + Vector((d * math.cos(el) * math.cos(az), d * math.cos(el) * math.sin(az), d * math.sin(el)))
        h = libre(t, c, m["f"]); g = suelo(c.x, c.y); abajo = g is not None and c.z < g + 0.8
        if h is None and not abajo: break
        hecho = True
        if intento < 3: el = min(math.radians(75), el + math.radians(9))        # sube la camara
        else: d = max(2.5, (h if h is not None else d) - 0.6)                  # y si sigue tapado, la acerca
    ajustes += 1 if hecho else 0; res.append((m["f"], c, t, m["focal"]))
# suavizado ligero de la trayectoria ajustada (sin saltos entre muestras vecinas)
W = 2
cams = [r[1] for r in res]
sm = [sum((cams[j] for j in range(max(0, i - W), min(len(cams), i + W + 1))), Vector()) / (min(len(cams), i + W + 1) - max(0, i - W)) for i in range(len(cams))]
# borrar animacion previa de estos objetos y de los datos de la camara
for ob in (cam, foco, cam.data):
    if ob.animation_data and ob.animation_data.action: ob.animation_data.action = None
for (f, c0, t, focal), c in zip(res, sm):
    cam.location = c; cam.keyframe_insert("location", frame=f)
    foco.location = t; foco.keyframe_insert("location", frame=f)
    cam.data.lens = focal; cam.data.keyframe_insert("lens", frame=f)
# interpolacion suave (Bezier con manejadores auto-limitados)
from bpy_extras import anim_utils
for ob in (cam, foco, cam.data):
    ad = ob.animation_data; act = ad.action
    cb = anim_utils.action_get_channelbag_for_slot(act, ad.action_slot)
    for fc in cb.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = "BEZIER"; kp.handle_left_type = "AUTO_CLAMPED"; kp.handle_right_type = "AUTO_CLAMPED"
sc.camera = cam; sc.frame_set(1)
print(f"camara: {len(res)} muestras con keyframes de ubicacion/mira/focal; {ajustes} ajustadas por obstaculos; frames {res[0][0]}-{res[-1][0]}")
