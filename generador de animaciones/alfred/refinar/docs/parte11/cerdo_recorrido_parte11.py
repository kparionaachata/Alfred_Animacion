# -*- coding: utf-8 -*-
"""Parte 11 (base_parte_11.blend): RECORRIDO DEL CERDO (cerdo_1) desde el frame 1, con el estudio del cerdo (cerdo_1_animation_studio).
- Recorrido: automatizacion/entradas/base_parte_11/recorrido_cerdo_1.json (el que hizo el usuario, 20 puntos sobre bloques de 1 m3).
  Caminar / saltar subir / saltar bajar se detectan solos por la altura de los puntos.
- PAUSAS (como el cerdo de Minecraft quieto): el cuerpo no se mueve y la cabeza MIRA ALREDEDOR hacia puntos al azar
  (izquierda/derecha, arriba/abajo). Ver PAUSAS abajo (punto -> frames).
- GRUNIDOS ("oink", entity.pig.ambient, sonidos de Minecraft): 5 en total, uno en cada pausa y uno al caminar. Solo sonido: no mueve la boca.
Repetible: rehace la animacion del cerdo y sus propias tiras (SND_p11_cerdo_*). No toca a Alfred, a Jerry, la camara ni los ojos."""
import bpy, sys, json, random, importlib, importlib.util

sc = bpy.context.scene
G = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones"
REC = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\automatizacion\entradas\base_parte_11\recorrido_cerdo_1.json"
BLEND = r"C:\Users\user\Desktop\Alfred_Animacion\estructura_lista\cerdo_1.blend"
PAUSAS = {3: 120, 8: 144, 15: 120, 20: 192}            # punto (1 = el primero) -> frames quieto mirando alrededor. (El estudio no admite pausa justo antes ni justo despues de un salto: el punto 1 baja de un bloque)
F_INICIO = 1
rng = random.Random(11)

# ---------------- estudio del cerdo ----------------
if G + r"\cerdo_1\refinar" not in sys.path: sys.path.insert(0, G + r"\cerdo_1\refinar")
est = sys.modules.get("cerdo_1_animation_studio")
if est is None or not hasattr(sc, "cerdo_1_path"):
    import cerdo_1_animation_studio as est
    try: est.register()
    except Exception: est.unregister(); est.register()
pc = sc.cerdo_1_path
pc.recording_active = False
pc.path_points.clear()
for i, kp in enumerate(json.load(open(REC, encoding="utf-8"))["key_points"], start=1):
    p = pc.path_points.add(); c = kp["coordinates"]; p.coords = (c["x"], c["y"], c["z"])
    p.texture = kp.get("texture", ""); p.face_index = str(kp.get("face_index", ""))
    if i in PAUSAS: p.tipo_segmento = "PARADA"; p.parada_frames_punto = PAUSAS[i]
pc.blend_filepath = BLEND
pc.frame_inicio = F_INICIO
pc.root_rot_x, pc.root_rot_y, pc.root_rot_z = 0.0, 0.0, 0.0       # al empezar mira hacia donde va (+Y)
f0, f1 = sc.frame_start, sc.frame_end
r = bpy.ops.cerdo_1pr.preview_path()
print("CERDO recorrido:", r)

# ---------------- tramos generados ----------------
root = bpy.data.objects["cerdo_1"]
tramos = sorted(((int(s.frame_start), int(s.frame_end), s.action.name) for t in root.animation_data.nla_tracks for s in t.strips), key=lambda x: x[0])
fin = max(b for a, b, n in tramos)
sc.frame_start, sc.frame_end = min(f0, F_INICIO), max(f1, fin)                 # la escena no se acorta (Alfred llega a su propio final)
pausas = [(a, b) for a, b, n in tramos if "parada" in n]
print("CERDO tramos:", [(a, b, n.replace("slot_", "").replace("_cerdo_1", "").replace("_root", "")) for a, b, n in tramos])

# ---------------- grunidos ----------------
m = sys.modules.get("alfred_sonidos")
if m is None:
    sp = importlib.util.spec_from_file_location("alfred_sonidos", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py")
    m = importlib.util.module_from_spec(sp); sys.modules["alfred_sonidos"] = m; sp.loader.exec_module(m)
if not hasattr(sc, "mcsnd"): m.register()
if not sc.mcsnd.items: bpy.ops.mcsnd.indexar()
ed = sc.sequence_editor_create(); S_ = m._strips(ed)
for t_ in [t_ for t_ in S_ if t_.name.startswith("SND_p11_cerdo")]: S_.remove(t_)
rutas = m.rutas_de(sc.mcsnd, "entity.pig.ambient")
cuando = []
GRUNIDOS = 5                                                                    # en total: uno en cada pausa y el resto al caminar
for a, b in pausas[:GRUNIDOS]:
    cuando.append(a + int((b - a) * rng.uniform(0.25, 0.7)))
caminando = [(a, b) for a, b, n in tramos if "caminar" in n and b - a > 40]
for a, b in caminando[:max(0, GRUNIDOS - len(cuando))]: cuando.append(rng.randint(a + 10, b - 10))
n = 0
for f in sorted(cuando):
    if rutas and m.colocar(bpy.context, sc.mcsnd, rutas, f, "voces", "p11_cerdo_oink", 0.8, 0, rng, False): n += 1
print("CERDO: %d pausas mirando alrededor %s, %d grunidos en %s, frames %d-%d" % (len(pausas), pausas, n, sorted(cuando), F_INICIO, fin))
