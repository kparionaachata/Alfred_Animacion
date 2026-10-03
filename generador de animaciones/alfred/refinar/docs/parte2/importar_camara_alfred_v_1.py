"""Se ejecuta DENTRO de Blender (exec). SEGUNDA RUTA enfocada en Alfred: crea `Camara_Alfred` + `Cam_Foco_Alfred` (sin tocar `Camara_Cinematica`) e inserta los keyframes de la camara cinematografica continua (camara_alfred_parte2.json, generado por compose_camara_parte2.py): ubicacion de `Camara_Cinematica`
(su TRACK_TO ya apunta a `Cam_Foco`), ubicacion de `Cam_Foco` (punto de mira entre Alfred y Jerry) y focal. Antes ajusta con raycast cada muestra: si el terreno, un arbol o un bloque tapa la
vista entre la camara y el punto de mira (o la camara queda dentro de algo) sube la elevacion y, si no basta, acerca la camara. NO renderiza.
Idempotente: borra los keyframes anteriores de esos objetos antes de insertar.
"""
import bpy, json, math, os
from mathutils import Vector

BASE = r"C:\Users\user\Desktop\Alfred_Animacion"
J = json.load(open(os.path.join(BASE, r"generador de animaciones\alfred\refinar\docs\parte2\camara_alfred_parte2.json"), encoding="utf-8"))
sc = bpy.context.scene
cam = bpy.data.objects.get("Camara_Alfred"); foco = bpy.data.objects.get("Cam_Foco_Alfred")
if foco is None:
    foco = bpy.data.objects.new("Cam_Foco_Alfred", None); foco.empty_display_type = "PLAIN_AXES"; sc.collection.objects.link(foco)
if cam is None:
    cd = bpy.data.cameras.new("Camara_Alfred"); cd.sensor_width = bpy.data.objects["Camara_Cinematica"].data.sensor_width if "Camara_Cinematica" in bpy.data.objects else 36.0
    cd.clip_end = 2000.0; cam = bpy.data.objects.new("Camara_Alfred", cd); sc.collection.objects.link(cam)
    tt = cam.constraints.new("TRACK_TO"); tt.target = foco; tt.track_axis = "TRACK_NEGATIVE_Z"; tt.up_axis = "UP_Y"
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
        ignora = ignora or (obj.name in APARECE and f is not None and f < APARECE[obj.name])
        ignora = ignora or (obj.name in APARECE and f is not None and f >= 2000)                                  # desde f2000 el sujeto ES el refugio sellado: sus bloques no tapan la vista           # un bloque del refugio aun no existe antes de su frame de aparicion
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
    az0, el0 = az, el; mejor = None; hecho = False
    for dael in (0, 9, 18, 27, 36):                                                            # 1) sube la camara; 2) la gira alrededor de los personajes (+-12 ... +-72 grados); se queda con la primera libre
        for daz in (0, 12, -12, 24, -24, 36, -36, 48, -48, 60, -60, 72, -72):
            a_ = az0 + math.radians(daz); e_ = min(math.radians(78), el0 + math.radians(dael))
            c = t + Vector((d * math.cos(e_) * math.cos(a_), d * math.cos(e_) * math.sin(a_), d * math.sin(e_)))
            h = libre(t, c, m["f"]); g = suelo(c.x, c.y); abajo = g is not None and c.z < g + 0.8
            libre_d = d if h is None else h
            if mejor is None or (not abajo and libre_d > mejor[0]) : mejor = (libre_d, c.copy(), a_, e_)
            if h is None and not abajo: mejor = (d, c.copy(), a_, e_); break
        else: continue
        break
    c = mejor[1]; hecho = (mejor[2] != az0 or mejor[3] != el0)
    if mejor[0] < d - 0.3:                                                                      # 3) si todo sigue tapado, la acerca hasta antes del obstaculo
        dd = max(2.5, mejor[0] - 0.6); c = t + Vector((dd * math.cos(mejor[3]) * math.cos(mejor[2]), dd * math.cos(mejor[3]) * math.sin(mejor[2]), dd * math.sin(mejor[3]))); hecho = True
    # la camara NUNCA queda dentro del refugio ni pegada a su techo: si cae dentro del volumen (+margen) se saca al lado mas cercano, y si queda a menos de 1.5 m por encima se sube
    X0, X1, Y0, Y1, Z0, Z1 = -99.0, -93.0, -112.0, -106.0, 13.5, 17.0
    if X0 < c.x < X1 and Y0 < c.y < Y1 and Z0 < c.z < Z1 + 1.5:
        if c.z > Z1 - 0.5: c.z = Z1 + 1.8
        else:
            lados = [(c.x - X0, (X0 - 1.2, c.y)), (X1 - c.x, (X1 + 1.2, c.y)), (c.y - Y0, (c.x, Y0 - 1.2)), (Y1 - c.y, (c.x, Y1 + 1.2))]; _, (c.x, c.y) = min(lados, key=lambda z: z[0])
        hecho = True
    elif X0 < c.x < X1 and Y0 < c.y < Y1 and Z1 + 1.5 <= c.z < Z1 + 1.8: c.z = Z1 + 1.8
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
