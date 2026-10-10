# -*- coding: utf-8 -*-
"""EXPORTA las animaciones de Alfred de la parte 6 (escena viva) a archivos .py independientes en `codigos de animacion/alfred/`, uno por escena, con el MISMO formato de los demas (`PAYLOAD` + `execute_animation(start_frame)`),
MAS los objetos con los que interactua (herramientas de piedra y de madera, mesa de crafteo, bloques de la puerta, tablones) empaquetados en `codigos de animacion/alfred/objetos/*.blend` (el .py los anade con `bpy.data.libraries.load` si faltan en la escena).
NO incluye hablar ni expresiones: ni las voces, ni los ojos (`Closed`, `Voz_*`), ni su parpadeo, ni el audio.
Se ejecuta DENTRO de Blender en dos fases (el muestreo recorre todos los frames y tarda):
    ex = {"__name__": "exp", "FASE": "muestrear", "A": 1, "B": 420}   exec(open(RUTA).read(), ex)     # repetir por tramos para muestrear f1-1257 (los datos quedan en bpy.app.driver_namespace["ALF_EXP"])
    ex = {"__name__": "exp", "FASE": "escribir"}                        exec(open(RUTA).read(), ex)     # escribe los .py y los .blend de objetos
Muestrea con `frame_set` (no cambia nada; al terminar deja la escena en f120). Valores = los de la escena (incluyen los filtros organicos)."""
import bpy, json, math, os
from mathutils import Matrix, Vector, Euler, Quaternion

DEST = r"C:\Users\user\Desktop\Alfred_Animacion\codigos de animacion\alfred"
OBJ_DIR = os.path.join(DEST, "objetos")
FASE = globals().get("FASE", "muestrear")
sc = bpy.context.scene; ns = bpy.app.driver_namespace
AA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "Hips_alfred" in o.pose.bones); EA = AA.parent
APARENTADOS = {"stone_axe": ("herramientas_piedra", ["stone_axe", "stone_shovel"]), "stone_shovel": ("herramientas_piedra", ["stone_axe", "stone_shovel"])}
MUNDO = {"wooden_axe": ("herramientas_madera", ["wooden_axe", "wooden_pickaxe"]), "wooden_pickaxe": ("herramientas_madera", ["wooden_axe", "wooden_pickaxe"]),
         "mesa_de_crafteo_1": ("mesa_de_crafteo", ["mesa_de_crafteo_1"] + [c.name for c in bpy.data.objects["mesa_de_crafteo_1"].children_recursive]),
         "refugio_bloque_06": ("bloques_puerta", ["refugio_bloque_06", "refugio_bloque_07", "drop_tablon_1", "drop_tablon_2"]), "refugio_bloque_07": ("bloques_puerta", ["refugio_bloque_06", "refugio_bloque_07", "drop_tablon_1", "drop_tablon_2"]),
         "drop_tablon_1": ("bloques_puerta", ["refugio_bloque_06", "refugio_bloque_07", "drop_tablon_1", "drop_tablon_2"]), "drop_tablon_2": ("bloques_puerta", ["refugio_bloque_06", "refugio_bloque_07", "drop_tablon_1", "drop_tablon_2"])}
PIEDRA = ["stone_axe", "stone_shovel"]
ESCENAS = [
    ("dormido_en_el_pozo", 1, 159, "Alfred dormido sentado en el pozo (pose heredada de la parte 5), con el hacha y la pala de piedra a la espalda; solo respiracion y micro-movimientos organicos", PIEDRA),
    ("recibe_hacha_y_pico_en_la_cabeza", 160, 225, "Jerry le tira con la cola el hacha y el pico de madera a la cabeza (golpes en f164 y f206): reaccion del cuello y temblor", PIEDRA + ["wooden_axe", "wooden_pickaxe"]),
    ("mira_alrededor_en_alerta", 226, 283, "tras el segundo golpe despierta de golpe y gira la cabeza tres veces de derecha a izquierda", PIEDRA),
    ("se_levanta_apoyado_en_la_pared", 284, 347, "se levanta apoyando la mano izquierda en la pared de madera y la derecha en el pasto, junto con la pala y el hacha de piedra", PIEDRA),
    ("se_soba_la_cabeza", 348, 429, "de pie, se soba la cabeza con la mano derecha, confundido", PIEDRA),
    ("gira_y_rompe_la_mesa_de_crafteo", 540, 675, "gira 180 grados, saca el hacha, golpea la mesa de crafteo (f590, 601, 611, 620), la mesa se rompe, flota y la absorbe; guarda el hacha en la espalda", PIEDRA + ["mesa_de_crafteo_1"]),
    ("salta_fuera_de_la_fosa", 676, 733, "salta fuera de la fosa con la animacion Mixamo de saltar", PIEDRA),
    ("talla_la_puerta", 734, 825, "gira 90 grados a la derecha, saca el hacha de la espalda con la animacion del brazo del usuario y rompe los dos bloques de la puerta (f775-821)", PIEDRA + ["refugio_bloque_06", "refugio_bloque_07"]),
    ("sale_caminando_y_absorbe_los_tablones", 826, 925, "sale caminando por su ruta (ciclo de caminar del estudio), guarda el hacha en la espalda caminando (f834-850) y absorbe los tablones de la puerta (f831-840)", PIEDRA + ["drop_tablon_1", "drop_tablon_2"]),
    ("parado_manos_en_la_cintura_tras_el_recorrido", 926, 1119, "al terminar el recorrido gira a -450 grados y adopta la pose de manos en la cintura (f926-943), que mantiene", PIEDRA),
    ("se_asusta_del_creeper_y_huye_corriendo", 1120, 1257, "gira la cabeza al creeper (f1120-1131), se voltea (f1160-1162), se asusta con los brazos en V y las piernas abiertas (f1162-1190) y sale corriendo al oeste (f1190-1255)", PIEDRA),
]
R5 = lambda v: round(float(v), 5)

if FASE == "muestrear":
    A, B = int(globals()["A"]), int(globals()["B"]); D = ns.setdefault("ALF_EXP", {})
    objs = sorted({o for e in ESCENAS for o in e[4]})
    for f in range(A, B + 1):
        sc.frame_set(f); bpy.context.view_layer.update(); fr = {"bones": {}, "root": [list(map(R5, EA.location)), list(map(R5, EA.rotation_euler))], "objs": {}}
        for b in AA.pose.bones: fr["bones"][b.name] = (list(map(R5, b.rotation_euler)), list(map(R5, b.location)), list(map(R5, b.scale)))
        for n in objs:
            o = bpy.data.objects[n]
            if n in APARENTADOS:
                fr["objs"][n] = {"loc": list(map(R5, o.location)), "quat": list(map(R5, o.rotation_quaternion)), "euler": list(map(R5, o.rotation_euler)), "scale": list(map(R5, o.scale)), "infl": {c.name: R5(c.influence) for c in o.constraints}, "hide": [bool(o.hide_viewport), bool(o.hide_render)]}
            else:
                l, q, s = o.matrix_world.decompose(); fr["objs"][n] = {"loc": list(map(R5, l)), "quat": list(map(R5, q)), "scale": list(map(R5, s)), "hide": [bool(o.hide_viewport), bool(o.hide_render)]}
        D[f] = fr
    sc.frame_set(120); print("muestreados f%d-%d; total en memoria: %d frames" % (A, B, len(D)))

elif FASE == "escribir":
    D = ns["ALF_EXP"]; os.makedirs(DEST, exist_ok=True); os.makedirs(OBJ_DIR, exist_ok=True)
    # ---------- 1) paquetes de objetos (.blend) ----------
    packs = {}
    for n in {o for e in ESCENAS for o in e[4]}:
        arch, nombres = (APARENTADOS.get(n) or MUNDO[n]); packs[arch] = nombres
    for arch, nombres in packs.items():
        originales = [bpy.data.objects[n] for n in nombres]; copias = []; tmp = bpy.data.collections.new("__export_tmp"); sc.collection.children.link(tmp)
        try:
            for o in originales: o.name = o.name + "__orig"
            for o in originales:
                c = o.copy(); c.name = o.name[:-6]; c.animation_data_clear()
                for k in list(c.constraints): c.constraints.remove(k)
                c.parent = None; c.matrix_world = Matrix.Identity(4); tmp.objects.link(c); copias.append(c)
            for c, o in zip(copias, originales):                                              # conserva la jerarquia (mesa -> malla)
                if o.parent in originales: c.parent = copias[originales.index(o.parent)]
            bpy.data.libraries.write(os.path.join(OBJ_DIR, arch + ".blend"), set(copias), fake_user=True)
        finally:
            for c in copias: bpy.data.objects.remove(c, do_unlink=True)
            bpy.data.collections.remove(tmp)
            for o in originales: o.name = o.name[:-6]
        print("paquete", arch + ".blend", nombres)
    # ---------- 2) un .py por escena ----------
    PLANTILLA = open(os.path.join(os.path.dirname(os.path.abspath(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\exportar_animaciones_alfred_parte6.py")), "plantilla_animacion_alfred.py.txt"), encoding="utf-8").read()
    rest = None
    for nombre, f0, f1, titulo, objs in ESCENAS:
        frames = list(range(f0, f1 + 1)); n = len(frames); bones = {}; const = {}
        for bn in D[f0]["bones"]:
            rot = [D[f]["bones"][bn][0] for f in frames]; loc = [D[f]["bones"][bn][1] for f in frames]; esc = [D[f]["bones"][bn][2] for f in frames]
            bones[bn] = {"rotation_euler": rot}
            for ch, vals in (("location", loc), ("scale", esc)):
                if max(abs(v[i] - vals[0][i]) for v in vals for i in range(3)) > 2e-5: bones[bn][ch] = vals
                else: const.setdefault(bn, {})[ch] = vals[0]
        payload = {"info": {"name": nombre + "_alfred", "frames": n, "fps": 24, "entity": "Alfred", "status": "sin aprobar", "fuente": "base_parte_6 (escena viva) f%d-%d" % (f0, f1), "frame_original": f0, "descripcion": titulo, "objetos": objs,
                            "sin": "hablar ni expresiones (voz, ojos, parpadeo)"}, "bones": bones, "constantes": const,
                   "root": {"location": [D[f]["root"][0] for f in frames], "rotation_euler": [D[f]["root"][1] for f in frames]}, "objetos": {}}
        for on in objs:
            arch, nombres = (APARENTADOS.get(on) or MUNDO[on]); o = bpy.data.objects[on]; ds = [D[f]["objs"][on] for f in frames]
            hide = [d["hide"] for d in ds]; rec = {"tipo": "aparentado" if on in APARENTADOS else "mundo", "archivo": "objetos/%s.blend" % arch, "paquete": nombres, "rotation_mode": o.rotation_mode if on in APARENTADOS else "QUATERNION"}
            if on in APARENTADOS:
                rec["constraints"] = [[c.name, c.subtarget] for c in o.constraints]; rec["location"] = [d["loc"] for d in ds]; rec["scale"] = [d["scale"] for d in ds]
                rec["rotation"] = [d["quat"] if o.rotation_mode == 'QUATERNION' else d["euler"] for d in ds]; rec["influencia"] = {c.name: [d["infl"][c.name] for d in ds] for c in o.constraints}
            else:
                rec["location"] = [d["loc"] for d in ds]; rec["rotation_quaternion"] = [d["quat"] for d in ds]; rec["scale"] = [d["scale"] for d in ds]
            if any(h != hide[0] for h in hide): rec["hide"] = hide
            else: rec["hide_const"] = hide[0]
            payload["objetos"][on] = rec
        txt = PLANTILLA.replace("@@TITULO@@", titulo).replace("@@NOMBRE@@", nombre).replace("@@F0@@", str(f0)).replace("@@F1@@", str(f1)).replace("@@N@@", str(n)).replace("@@DEST@@", DEST.replace("\\", "/")).replace("@@PAYLOAD@@", repr(payload))
        ruta = os.path.join(DEST, nombre + "_alfred.py"); open(ruta, "w", encoding="utf-8").write(txt); print("escrito", ruta, "%d KB" % (os.path.getsize(ruta) // 1024), "objetos:", objs)
    sc.frame_set(120); print("LISTO")
