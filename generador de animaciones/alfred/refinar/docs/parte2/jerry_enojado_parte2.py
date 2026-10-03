"""Parte 2 - JERRY ENOJADO durante la patrulla y los empujones a los zombies (pedido de Kebyn). Solo toca las dos cejas (`sejas_1_jerry`, `sejas_2_jerry`).
Pose enojada = la del estudio (`_EMOTION_POSES['enojado']`, ver jerry/refinar/GUIA_ANIMACION_JERRY.md): rotacion XYZ (rad) y localizacion local de cada ceja. Hasta f1419 Jerry conserva sus cejas actuales
(las de `parte2_jerry_*`, fijas); desde f1419 (se levanta del descanso y empieza a patrullar) la pose enojada entra con smoothstep en 24 f (llena en f1445) y se mantiene hasta el final (f2150: sigue vigilando).
Dos usos (idempotentes):
  1) Artefacto (fuera de Blender; ejecutar DESPUES de compose_refugio_parte2.py, que regenera el JSON de Jerry):
         python alfred/refinar/docs/parte2/jerry_enojado_parte2.py          (desde 'generador de animaciones'; la 1a vez guarda `*.animacion.json.bak_antes_enojo` y siempre parte de esa copia)
  2) Escena abierta (dentro de Blender, SIN reimportar al personaje): edita las keyframes de las cejas de la accion `IA_parte2_jerry_refugio__armature`:
         exec(compile(open(RUTA, encoding="utf-8").read(), RUTA, "exec")); print(aplicar_en_blender())
"""
import json, os, shutil

F_INI, F_RAMPA = 1419, 24
POSE = {                                                                          # (rotacion XYZ rad, localizacion XYZ)
    "sejas_1_jerry": ((0.018057, 0.032724, 0.466682), (0.007460, -0.011135, 0.000709)),
    "sejas_2_jerry": ((0.059813, -0.027015, -0.463214), (0.020687, -0.018262, 0.005866)),
}


def peso(f):
    x = min(1.0, max(0.0, (f - F_INI) / float(F_RAMPA))); return x * x * (3 - 2 * x)


def main():
    here = os.path.dirname(os.path.abspath(__file__)); base = "generador de animaciones" if os.path.isdir("generador de animaciones") else "."
    ruta = os.path.join(base, "jerry/refinar/animaciones_ia/parte2_jerry_refugio/parte2_jerry_refugio.animacion.json"); bak = ruta + ".bak_antes_enojo"
    if not os.path.exists(bak): shutil.copyfile(ruta, bak)
    d = json.load(open(bak, encoding="utf-8")); B = d["armature"]["bones"]; n = d["frame_fin"]
    for bn, (rot, loc) in POSE.items():
        for canal, tgt in (("rotation_euler", rot), ("location", loc)):
            for a in range(3):
                c = B[bn][canal][a]
                if not isinstance(c, list): c = [c] * n
                B[bn][canal][a] = [round(c[i] + (tgt[a] - c[i]) * peso(i + 1), 5) for i in range(n)]
    json.dump(d, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"Jerry enojado: cejas hacia la pose del estudio desde f{F_INI} (llena en f{F_INI + F_RAMPA}) hasta f{n}; original en {os.path.basename(bak)}")


def aplicar_en_blender():
    import bpy
    from bpy_extras import anim_utils
    act = bpy.data.actions["IA_parte2_jerry_refugio__armature"]; cb = anim_utils.action_get_channelbag_for_slot(act, act.slots[0]); n = 0
    orig = bpy.app.driver_namespace.setdefault("jerry_cejas_orig", {})              # valores originales (para poder repetirlo o deshacerlo)
    for fc in cb.fcurves:
        for bn, (rot, loc) in POSE.items():
            for canal, tgt in (("rotation_euler", rot), ("location", loc)):
                if fc.data_path == f'pose.bones["{bn}"].{canal}':
                    key = (fc.data_path, fc.array_index)
                    if key not in orig: orig[key] = [k.co[1] for k in fc.keyframe_points]
                    for i, k in enumerate(fc.keyframe_points):
                        k.co[1] = orig[key][i] + (tgt[fc.array_index] - orig[key][i]) * peso(k.co[0]); n += 1
                    fc.update()
    return f"{n} keyframes de cejas actualizadas (f{F_INI}-{int(max(k.co[0] for k in cb.fcurves[0].keyframe_points))})"


if __name__ == "__main__":
    main()
