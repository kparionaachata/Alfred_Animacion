"""Se ejecuta DENTRO de Blender (exec): importa bloque_de_tablones_de_roble.blend una sola vez y crea los bloques del refugio (refugio_bloques.json),
ocultos hasta su frame de aparicion (visibilidad constante, abrupto como en 'Crear pared NxN'). Idempotente: borra la coleccion refugio_parte2 anterior."""
import json, os, bpy

BASE = r"C:\Users\user\Desktop\Alfred_Animacion"
J = json.load(open(os.path.join(BASE, r"generador de animaciones\alfred\refinar\docs\parte2\refugio_bloques.json"), encoding="utf-8"))
col = bpy.data.collections.get("refugio_parte2")
if col:
    for o in list(col.objects): bpy.data.objects.remove(o, do_unlink=True)
else:
    col = bpy.data.collections.new("refugio_parte2"); bpy.context.scene.collection.children.link(col)
src = bpy.data.objects.get("oak_planks_refugio_base")
if src is not None:                                                  # siempre se reimporta la fuente (para que cambiar de bloque surta efecto)
    _m = src.data; bpy.data.objects.remove(src, do_unlink=True); src = None
    if _m.users == 0: bpy.data.meshes.remove(_m)
if src is None:
    with bpy.data.libraries.load(os.path.join(BASE, r"bloques_dinamicos\bloque_de_tablones_de_roble.blend"), link=False) as (a, b): b.objects = ["oak_planks"]
    src = b.objects[0]; src.name = "oak_planks_refugio_base"
    for o in list(src.users_collection): o.objects.unlink(src)
    col.objects.link(src); src.hide_viewport = True; src.hide_render = True
for i, bl in enumerate(J["bloques"]):
    o = bpy.data.objects.new(f"refugio_bloque_{i:02d}", src.data); col.objects.link(o)
    o.location = (bl["x"], bl["y"], bl["z"]); o.rotation_euler = (0, 0, 0)
    f = bl["frame"]
    for prop in ("hide_viewport", "hide_render"):
        setattr(o, prop, True); o.keyframe_insert(prop, frame=max(1, f - 1))
        setattr(o, prop, False); o.keyframe_insert(prop, frame=f)
    if o.animation_data and o.animation_data.action:
        from bpy_extras import anim_utils
        act = o.animation_data.action
        for fc in anim_utils.action_get_channelbag_for_slot(act, o.animation_data.action_slot).fcurves if hasattr(anim_utils, "action_get_channelbag_for_slot") else []:
            for kp in fc.keyframe_points: kp.interpolation = "CONSTANT"
bpy.context.scene.frame_end = J["N"]
print("bloques", len(J["bloques"]), "frame_end", bpy.context.scene.frame_end)

# ---- antorcha que Alfred coloca al llegar al descanso (sistema Colocar antorcha del add-on: importa antorcha_1.blend completo en la coordenada y la oculta hasta el frame del ciclo en que Alfred esta agachado)
import sys
oiu = sys.modules.get("alfred_animation_studio.object_import_utils")
if oiu is None:
    import importlib; oiu = importlib.import_module("alfred_animation_studio.object_import_utils")
T = json.load(open(os.path.join(BASE, r"generador de animaciones\alfred\refinar\docs\parte2\antorcha_parte2.json"), encoding="utf-8"))
for o in [o for o in bpy.data.objects if o.get("refugio_antorcha")]:                 # idempotente: borra la antorcha de una importacion anterior (objetos y colecciones que trajo)
    bpy.data.objects.remove(o, do_unlink=True)
for c in [c for c in bpy.data.collections if c.get("refugio_antorcha")]:
    bpy.data.collections.remove(c)
_ob0 = set(bpy.data.objects.keys()); _co0 = set(bpy.data.collections.keys())
anchor, nombres = oiu.import_bloque_dinamico_full(os.path.join(BASE, "bloques_dinamicos", "antorcha_1.blend"), tuple(T["pos"]), "antorcha_1")
nuevos = [bpy.data.objects[n] for n in set(bpy.data.objects.keys()) - _ob0]
for c in [bpy.data.collections[n] for n in set(bpy.data.collections.keys()) - _co0]: c["refugio_antorcha"] = 1
for o in nuevos:
    o["refugio_antorcha"] = 1
    if o.name.startswith(("smoke_flame", "torch_flame_noImport")): o.hide_viewport = True; o.hide_render = True; continue          # mallas de referencia sueltas del .blend (no son la antorcha)
    oiu.hide_until_frame(o, T["frame_aparece"])
print("antorcha:", anchor.name if anchor else None, "objetos", len(nuevos), "aparece en f", T["frame_aparece"], "en", tuple(round(v, 2) for v in anchor.location) if anchor else None)
