"""Se ejecuta DENTRO de Blender (exec). Actualiza EN SITIO las keyframes de los zombies 1-5 con los artefactos `parte2_zombie_N_sigue` (p. ej. tras cambiar el levantarse), SIN reimportar a los personajes
(las acciones `IA_parte2_zombie_N_sigue__root` y `__armature` guardan una keyframe LINEAL por frame; se reescribe el valor de las que cambian). Idempotente.
    exec(compile(open(RUTA, encoding="utf-8").read(), RUTA, "exec")); print(aplicar())          # todos los zombies
"""
import bpy, json, os, re
from bpy_extras import anim_utils

_BASE_Z = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones"


def _val(c, i):
    return c[i] if isinstance(c, list) else c


def aplicar(zombies=(1, 2, 3, 4, 5)):
    informe = []
    for n in zombies:
        D = json.load(open(os.path.join(_BASE_Z, f"zombie_{n}", "refinar", "animaciones_ia", f"parte2_zombie_{n}_sigue", f"parte2_zombie_{n}_sigue.animacion.json"), encoding="utf-8"))
        cambios = 0
        act = bpy.data.actions[f"IA_parte2_zombie_{n}_sigue__root"]; cb = anim_utils.action_get_channelbag_for_slot(act, act.slots[0])
        for fc in cb.fcurves:
            canal = D["root"]["canales"].get(fc.data_path)
            if canal is None: continue
            for i, k in enumerate(fc.keyframe_points):
                v = _val(canal[fc.array_index], i)
                if abs(k.co[1] - v) > 1e-6: k.co[1] = v; cambios += 1
            fc.update()
        act = bpy.data.actions[f"IA_parte2_zombie_{n}_sigue__armature"]; cb = anim_utils.action_get_channelbag_for_slot(act, act.slots[0])
        for fc in cb.fcurves:
            m = re.match(r'pose\.bones\["(.+)"\]\.rotation_euler', fc.data_path)
            if not m or m.group(1) not in D["armature"]["bones"]: continue
            canal = D["armature"]["bones"][m.group(1)]["rotation_euler"][fc.array_index]
            for i, k in enumerate(fc.keyframe_points):
                v = _val(canal, i)
                if abs(k.co[1] - v) > 1e-6: k.co[1] = v; cambios += 1
            fc.update()
        informe.append((n, cambios))
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    return informe
