"""Comprueba en Blender (segundo plano): todos los .glb de animacion, que un clip mueve al personaje como en el juego,
y hace una foto por accion con el efecto de disparo.

blender -b --factory-startup --python comprobar_mecanicas.py -- carpeta_salida
"""
import glob, json, math, os, sys

import bpy
from mathutils import Vector

ext = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(ext)
MEC = os.path.join(RAIZ, "efectos_y_mecanicas")
PER = os.path.join(RAIZ, "personajes_napoleon")
sys.path.append(os.path.join(MEC, "efectos"))
sys.path.append(MEC)
import crear_efecto
from poner_clip import boca_arma, poner_arma, poner_clip

salida = sys.argv[sys.argv.index("--") + 1]
os.makedirs(salida, exist_ok=True)


def limpiar():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    crear_efecto.bpy.data  # el modulo sigue valido tras limpiar


def importar(f):
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=f)
    return [o for o in bpy.data.objects if o not in antes]


def armadura(obs):
    return next(o for o in obs if o.type == "ARMATURE")


# 1) todos los glb importan como armadura con sus clips
clips = json.load(open(os.path.join(MEC, "mecanicas", "clips.json")))
por_glb = {}
for v in clips.values():
    por_glb.setdefault(v["glb"], []).append(v["clip"])
malos = 0
lista = sorted(por_glb)
if "--todos" in sys.argv:
    for g in lista:
        limpiar()
        obs = importar(os.path.join(MEC, g))
        hay = {a.name for a in bpy.data.actions}
        faltan = [c for c in por_glb[g] if not any(h.startswith(c) for h in hay)]
        ok = any(o.type == "ARMATURE" for o in obs) and not faltan
        malos += 0 if ok else 1
        print("GLB", "ok " if ok else "MAL", g, len(por_glb[g]), "acciones", len(hay), "faltan", faltan[:4], flush=True)
    print("TOTAL_GLB", len(lista), "MAL", malos, flush=True)

# 2) escena de prueba
SOLDADO = os.path.join(PER, "highlanders", "britain_inf_line_british_highland_foot.soldier.glb")
OFICIAL = os.path.join(PER, "highlanders", "britain_inf_line_british_highland_foot.officer.glb")
HUSAR = os.path.join(PER, "husares_rusos", "russia_cav_light_russian_hussars.soldier.glb")
CABALLO = os.path.join(PER, "caballos", "horse_a_hussar.glb")
COSACO = os.path.join(PER, "cosacos_rusos", "russia_cav_lancer_russian_cossack_cavalry.soldier.glb")
AN = os.path.join(MEC, "animaciones")
LANZA = next(v["clip"] for v in clips.values() if v["glb"].endswith("c_lan.glb") and "charge" in v["clip"])
print("LANZA", LANZA, flush=True)

limpiar()
sc = bpy.context.scene
sc.render.fps = 20
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x, sc.render.resolution_y = 900, 600
w = bpy.data.worlds.new("w")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (.55, .6, .65, 1)
sc.world = w
s = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
s.data.energy = 3
s.rotation_euler = (math.radians(55), 0, math.radians(30))
sc.collection.objects.link(s)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 40


def poner(arm, nombre):
    """Trae un arma de armas_napoleon y la une a su hueso."""
    o = next(x for x in importar(os.path.join(RAIZ, "armas_napoleon", nombre + ".glb")) if x.type == "MESH" and "Icosphere" not in x.name)
    poner_arma(arm, o)
    return o


def actor(glb_personaje, glb_anim, clip, x):
    """Importa el personaje y el .glb de clips, borra el esqueleto auxiliar y aplica el clip."""
    p = importar(glb_personaje)
    a = armadura(p)
    aux = importar(glb_anim)
    acc = next(ac for ac in bpy.data.actions if ac.name.startswith(clip))
    for o in aux:
        bpy.data.objects.remove(o)
    poner_clip(a, acc)
    a.location.x += x
    for o in p:
        if o.type == "MESH" and "Icosphere" in o.name:
            o.hide_render = True
    return a


# verificacion numerica: la culata del hueso Weapon1 debe caer donde dice el .anim
sold = actor(SOLDADO, os.path.join(AN, "infanteria_mosquete", "mus_poised.glb"), "mus_fire_med", 0.0)
ofi = actor(OFICIAL, os.path.join(AN, "infanteria_sable", "sab_medium_guards.glb"), "sab_mguard_cut_3", 3.0)
car = actor(SOLDADO, os.path.join(AN, "infanteria_mosquete", "mus_charge.glb"), "mus_charge_651cm", 6.0)
rel = actor(SOLDADO, os.path.join(AN, "infanteria_mosquete", "mus_poised.glb"), "mus_reload_01", -3.0)
jin = actor(HUSAR, os.path.join(AN, "jinete", "c_sab.glb"), "c_sab_charge_attack", 10.0)
cab = actor(CABALLO, os.path.join(AN, "caballo", "general.glb"), "horse_gallop", 10.0)
cos = actor(COSACO, os.path.join(AN, "jinete", "c_lan.glb"), LANZA, 16.0)
cab2 = actor(CABALLO, os.path.join(AN, "caballo", "general.glb"), "horse_gallop", 16.0)
mosquete = poner(sold, "euro_musket01")
for a, n in ((ofi, "euro_straightsabre"), (car, "euro_musket01"), (rel, "euro_musket01"), (jin, "euro_cavalrysabre"), (cos, "gen_lance")):
    poner(a, n)

esperado = {}
for nom, arm in (("sold", sold),):
    sc.frame_set(1)
    bpy.context.view_layer.update()
    esperado[nom] = {b: list(arm.matrix_world @ arm.pose.bones[b].head) for b in ("Hips", "Head", "RightHand", "Weapon1")}
print("HUESOS_F1", esperado, flush=True)
print("ACCIONES", len(bpy.data.actions), flush=True)

# humo de disparo: sale de la boca del mosquete del soldado, hacia donde apunta
sc.frame_set(3)
bpy.context.view_layer.update()
boca, adelante = boca_arma(sold, mosquete)
print("BOCA", list(boca), list(adelante), flush=True)
cam.location = (-10.0, -5.5, 1.8)
cam.rotation_euler = (Vector((0, -5.5, 1.5)) - cam.location).to_track_quat("-Z", "Y").to_euler()
crear_efecto.crear("MusketFire", frame=3, ubicacion=tuple(boca), direccion=tuple(adelante), semilla=3)
print("PARTICULAS", sum(1 for o in bpy.data.objects if o.name.startswith("fx_")), flush=True)
for f in (4, 8, 14, 30, 60):
    sc.frame_set(f)
    sc.render.filepath = os.path.join(salida, "humo_f%02d.png" % f)
    bpy.ops.render.render(write_still=True)
cam.location = (3.5, -9.0, 2.2)
cam.rotation_euler = (Vector((3.5, 0, 1.0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
for f in (10, 25):
    sc.frame_set(f)
    sc.render.filepath = os.path.join(salida, "infanteria_f%02d.png" % f)
    bpy.ops.render.render(write_still=True)
cam.location = (13.0, -11.0, 2.2)
cam.rotation_euler = (Vector((13.0, -2, 1.3)) - cam.location).to_track_quat("-Z", "Y").to_euler()
for f in (4, 9):
    sc.frame_set(f)
    # los clips c_sab_* y c_lan_* no avanzan: el jinete sigue al caballo a la velocidad del galope
    for a in (jin, cos):
        a.location.y = -10.19 * (f - 1) / sc.render.fps
    bpy.context.view_layer.update()
    sc.render.filepath = os.path.join(salida, "jinete_f%02d.png" % f)
    bpy.ops.render.render(write_still=True)
print("FIN", flush=True)
