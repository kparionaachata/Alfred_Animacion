"""Se ejecuta DENTRO de Blender (exec). Hoja de contactos de la subida de un zombie: coloca el vacio y los huesos segun el artefacto `parte2_zombie_N_sigue` frame a frame (NLA de ese zombie desactivado
temporalmente y restaurado al final) y hace un render OpenGL de la vista 3D activa (vista local del zombie, lateral). Uso:
"""
import bpy, os, math
from mathutils import Euler, Vector
exec(compile(open(os.path.join(os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\parte2", "medir_levantarse.py"), encoding="utf-8").read(), "medir", "exec"))


def _hijos(o):
    r = [o]
    for c in o.children: r += _hijos(c)
    return r


def hoja(n, qs, carpeta, k0=None, vista=None):
    sc = bpy.context.scene; D = cargar(n); ev = json.load(open(os.path.join(HERE, "empujes_zombies.json"), encoding="utf-8"))["eventos"][str(n)]
    k0 = k0 if k0 is not None else rango(n, ev["frame_golpe"], ev["frame_libre"])[0]
    objs = _hijos(bpy.data.objects[f"zombie_{n}"]); estado = []
    for o in objs:
        if o.animation_data: estado.append((o.animation_data, o.animation_data.use_nla)); o.animation_data.use_nla = False
    area = [a for a in bpy.context.window.screen.areas if a.type == 'VIEW_3D'][0]; reg = [r for r in area.regions if r.type == 'WINDOW'][0]
    r3 = area.spaces[0].region_3d; rz = val(D["root"]["canales"]["rotation_euler"][2], k0)
    th = math.atan2(math.cos(rz), -math.sin(rz)); emp0 = bpy.data.objects[f"zombie_{n}"]
    r3.view_perspective = 'ORTHO'; r3.view_distance = 4.2; r3.view_rotation = Euler((math.radians(90), 0, th), 'XYZ').to_quaternion()
    L = D["root"]["canales"]["location"]; r3.view_location = Vector((val(L[0], k0), val(L[1], k0), val(L[2], k0) + 1.0)) if vista is None else Vector(vista)
    r0 = (sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage); sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 560, 560, 100
    area.spaces[0].overlay.show_overlays = False; area.spaces[0].shading.type = 'SOLID'; salidas = []
    try:
        for q in qs:
            poner(n, D, k0 + q); bpy.context.view_layer.update()
            with bpy.context.temp_override(window=bpy.context.window, area=area, region=reg, space_data=area.spaces[0]):
                bpy.ops.render.opengl(view_context=True)
            fn = os.path.join(carpeta, f"lev{n}_{q:02d}.png"); bpy.data.images["Render Result"].save_render(fn); salidas.append(fn)
    finally:
        sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = r0
        for ad, st in estado: ad.use_nla = st
        sc.frame_set(sc.frame_current)
    return salidas
