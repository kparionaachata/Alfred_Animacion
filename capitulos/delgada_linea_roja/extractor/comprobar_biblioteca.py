"""Comprueba en Blender (segundo plano) cada .blend de biblioteca_personajes y que clip y arma funcionen sobre el.

blender -b --factory-startup --python comprobar_biblioteca.py -- carpeta_foto
"""
import glob, os, sys

import bpy
from mathutils import Vector

ext = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(ext)
BIB = os.path.join(RAIZ, "biblioteca_personajes")
MEC = os.path.join(RAIZ, "efectos_y_mecanicas")
sys.path.append(MEC)
from poner_clip import poner_arma, poner_clip

fotos = sys.argv[sys.argv.index("--") + 1]
os.makedirs(fotos, exist_ok=True)
malos = 0
archivos = sorted(glob.glob(os.path.join(BIB, "**", "*.blend"), recursive=True))
for f in archivos:
    bpy.ops.wm.open_mainfile(filepath=f, load_ui=False)
    # has_data es falso hasta que la imagen se usa: lo que importa es que venga empaquetada y se pueda leer
    sin_emp = [i.name for i in bpy.data.images if i.type == "IMAGE" and not i.packed_file]
    sin_datos = [i.name for i in bpy.data.images if i.type == "IMAGE" and i.size[0] == 0]
    objs = bpy.data.objects
    rel = os.path.relpath(f, BIB)
    if rel.startswith("armas"):
        ok = len(objs) == 1 and objs[0].get("hueso") and not sin_emp and not sin_datos
        info = "hueso %s" % (objs[0].get("hueso") if len(objs) else None)
    elif rel.startswith("equipo"):
        ok = len(objs) > 10 and not sin_emp and not sin_datos
        info = "objetos %d" % len(objs)
    else:
        arm = [o for o in objs if o.type == "ARMATURE"]
        mallas = [o for o in objs if o.type == "MESH"]
        sueltas = [o.name for o in mallas if not any(m.type == "ARMATURE" and m.object for m in o.modifiers)]
        vis = [o for o in mallas if o.visible_get()]
        z = [(o.matrix_world @ Vector(c)).z for o in vis for c in o.bound_box]
        con_arma = [o.name for o in mallas if any(x in o.name for x in ("musket", "sabre", "lance", "bayonet", "ramrod", "hanger", "flagpole"))]
        ok = len(arm) == 1 and not sueltas and not sin_emp and not sin_datos and min(z) < .2 and "Icosphere" not in objs and not con_arma
        info = "piezas %d visibles %d suelo %.2f alto %.2f armas_dentro %s sueltas %s" % (len(mallas), len(vis), min(z), max(z), con_arma, sueltas)
    malos += 0 if ok else 1
    print("BIB", "ok " if ok else "MAL", rel, info, flush=True)
print("TOTAL", len(archivos), "MAL", malos, flush=True)

# un clip real y su arma sobre los .blend de la biblioteca
HL = "highlanders/britain_inf_line_british_highland_foot.%s/britain_inf_line_british_highland_foot.%s.blend"
CO = "cosacos_rusos/russia_cav_lancer_russian_cossack_cavalry.soldier/russia_cav_lancer_russian_cossack_cavalry.soldier.blend"
casos = [(HL % ("soldier", "soldier"), "infanteria_mosquete/mus_poised.glb", "mus_fire_med", 10, "fuego", ["euro_musket01", "gen_socket_bayonet"]),
         (HL % ("soldier", "soldier"), "infanteria_mosquete/mus_poised.glb", "mus_reload_01", 12, "recarga", ["euro_musket01", "gen_musket_ramrod01"]),
         (HL % ("officer", "officer"), "infanteria_sable/sab_medium_guards.glb", "sab_mguard_cut_3", 12, "sable", ["euro_straightsabre"]),
         (CO, "jinete/c_lan.glb", "c_lan_charge_guard", 10, "lanza", ["gen_lance"])]
for blend, glb, clip, fr, nom, armas in casos:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(BIB, blend), load_ui=False)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(MEC, "animaciones", glb))
    for o in [o for o in bpy.data.objects if o not in antes]:
        bpy.data.objects.remove(o)
    poner_clip(arm, next(a for a in bpy.data.actions if a.name.startswith(clip)))
    sc = bpy.context.scene
    puestas = []
    for a in armas:
        with bpy.data.libraries.load(os.path.join(BIB, "armas", a, a + ".blend")) as (de, a_):
            a_.objects = [a]
        o = bpy.data.objects[a]
        sc.collection.objects.link(o)
        poner_arma(arm, o)
        puestas.append(o)
    sc.frame_set(fr)
    bpy.context.view_layer.update()
    mano = arm.matrix_world @ arm.pose.bones["RightHand"].head
    izq = arm.matrix_world @ arm.pose.bones["LeftHand"].head
    print("CLIP", nom, "cadera", [round(x, 2) for x in arm.pose.bones["Hips"].head],
          {o.name: (o["hueso"], round(min(min((o.matrix_world @ v.co - mano).length, (o.matrix_world @ v.co - izq).length) for v in o.data.vertices), 2)) for o in puestas}, flush=True)
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 700, 700
    mu = bpy.data.worlds.new("w")
    mu.use_nodes = True
    mu.node_tree.nodes["Background"].inputs[0].default_value = (.7, .72, .75, 1)
    mu.node_tree.nodes["Background"].inputs[1].default_value = 1.2
    sc.world = mu
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens = 35
    cam.location = (4.0, -6.0, 2.0)
    cam.rotation_euler = (Vector((0, -.3, 1.2)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(fotos, nom + ".png")
    bpy.ops.render.render(write_still=True)
print("FIN", flush=True)
