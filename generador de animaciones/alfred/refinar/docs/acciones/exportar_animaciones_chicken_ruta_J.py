# -*- coding: utf-8 -*-
"""EXPORTA la carrera del POLLO (chicken_1) de base_ruta_J.blend (escena viva, pistas NLA: se muestrea con frame_set) a `codigos de animacion/chicken/`,
con el formato de los demas .py del pollo, MAS el sombrero de Jerry que lleva en el pico (objetos/sombrero_jerry_pico_pollo.blend, pegado a Jaw_bot_chicken_1)."""
import bpy, os
from mathutils import Matrix
DEST = r"C:\Users\user\Desktop\Alfred_Animacion\codigos de animacion\chicken"; OBJ = os.path.join(DEST, "objetos")
R5 = lambda v: round(float(v), 5)
ESCENAS = [("recibe_los_golpes_de_jerry_con_el_sombrero_en_el_pico_ruta_J", 260, 415, "recibe los golpes de Jerry: frena y aletea en el sitio con el sombrero de Jerry en el pico")]
_src = open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\exportar_animaciones_chicken_parte7.py", encoding="utf-8").read()
_a = _src.index("PLANTILLA = r'''") + len("PLANTILLA = r'''"); PLANTILLA = _src[_a:_src.index("'''", _a)]
PLANTILLA = (PLANTILLA.replace("parte 7, frames originales", "ruta J, frames originales").replace("Extraida de `base_parte_7.blend`", "Extraida de `base_ruta_J.blend`")
             .replace("posicion absoluta original de la parte 7", "posicion absoluta original de la ruta J"))
PEGADOS = '''    for nombre, (ruta, rig, hueso, matriz) in PAYLOAD.get('pegados', {}).items():                # objetos en el pico (sombrero de Jerry): pegados a un hueso
        import os
        if nombre not in bpy.data.objects:
            r = ruta
            if not os.path.isfile(r):
                try: r = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'objetos', os.path.basename(ruta))
                except NameError: pass
            with bpy.data.libraries.load(r, link=False) as (src, dst): dst.objects = [nombre]
            sc.collection.objects.link(dst.objects[0])
        ob = bpy.data.objects[nombre]; arm = bpy.data.objects[rig]; bpy.context.view_layer.update()
        ob.parent = arm; ob.parent_type = 'BONE'; ob.parent_bone = hueso; ob.matrix_world = arm.matrix_world @ arm.pose.bones[hueso].matrix @ Matrix(matriz)
'''
PLANTILLA = PLANTILLA.replace("    asegurar_modelos(); sc = bpy.context.scene\n", "    asegurar_modelos(); sc = bpy.context.scene\n" + PEGADOS)

sc = bpy.context.scene; cur = sc.frame_current; root = bpy.data.objects["chicken_1"]; arm = bpy.data.objects["Armature_chicken_1"]; hat = bpy.data.objects["sombrero_jerry"]
os.makedirs(OBJ, exist_ok=True)
c = hat.copy(); c.parent = None; c.animation_data_clear(); c.modifiers.clear(); c.matrix_world = Matrix.Identity(4); tmp = bpy.data.collections.new("__tmp"); sc.collection.children.link(tmp)
hat.name = "sombrero_jerry__orig"; c.name = "sombrero_jerry"; tmp.objects.link(c)
try: bpy.data.libraries.write(os.path.join(OBJ, "sombrero_jerry_pico_pollo.blend"), {c}, fake_user=True)
finally:
    bpy.data.objects.remove(c, do_unlink=True); bpy.data.collections.remove(tmp); hat.name = "sombrero_jerry"
for nombre, f0, f1, titulo in ESCENAS:
    fr = list(range(f0, f1 + 1)); rc = {}; ac = {}
    for f in fr:
        sc.frame_set(f)
        for d in ("location", "rotation_euler"):
            for i in range(3): rc.setdefault((d, i), []).append(R5(getattr(root, d)[i]))
        for b in arm.pose.bones:
            for d in ("location", "rotation_euler", "scale"):
                for i in range(3): ac.setdefault(('pose.bones["%s"].%s' % (b.name, d), i), []).append(R5(getattr(b, d)[i]))
    sc.frame_set(f0); bpy.context.view_layer.update(); pb = arm.pose.bones[hat.parent_bone]
    M = (arm.matrix_world @ pb.matrix).inverted() @ hat.matrix_world
    ids = {"chicken_1": {"tipo": "objeto", "nombre": "chicken_1", "canales": [[d, i, v] for (d, i), v in rc.items()]},
           "Armature_chicken_1": {"tipo": "objeto", "nombre": "Armature_chicken_1", "canales": [[d, i, v] for (d, i), v in ac.items() if max(v) - min(v) > 2e-5 or not d.endswith("scale")]}}
    payload = {"info": {"name": nombre + "_chicken", "frames": len(fr), "fps": 24, "entity": "Chicken", "status": "sin aprobar", "fuente": "base_ruta_J (escena viva) f%d-%d" % (f0, f1),
                        "frame_original": f0, "descripcion": titulo, "objetos": ["sombrero_jerry (en el pico)"]},
               "roots": ["chicken_1"], "modelos": {"pollo": [r"C:\Users\user\Desktop\Alfred_Animacion\estructura_lista\chicken_1.blend", ["chicken_1", "Armature_chicken_1"]]}, "ids": ids,
               "pegados": {"sombrero_jerry": [os.path.join(OBJ, "sombrero_jerry_pico_pollo.blend"), "Armature_chicken_1", hat.parent_bone, [[R5(x) for x in r] for r in M]]}}
    txt = (PLANTILLA.replace("@@NOMBRE@@", nombre).replace("@@F0@@", str(f0)).replace("@@F1@@", str(f1)).replace("@@N@@", str(len(fr))).replace("@@TITULO@@", titulo)
           .replace("@@EXTRA@@", ", mas el sombrero de Jerry en el pico").replace("@@PAYLOAD@@", repr(payload)))
    ruta = os.path.join(DEST, nombre + "_chicken.py"); open(ruta, "w", encoding="utf-8").write(txt); print("escrito", os.path.basename(ruta), os.path.getsize(ruta) // 1024, "KB")
sc.frame_set(cur); print("LISTO")
