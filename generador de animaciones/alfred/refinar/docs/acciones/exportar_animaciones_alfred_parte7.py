# -*- coding: utf-8 -*-
"""EXPORTA las animaciones de Alfred de la PARTE 7 (escena viva) a archivos .py independientes en `codigos de animacion/alfred/`, uno por escena, con el MISMO formato de los demas (`PAYLOAD` + `execute_animation(start_frame)`),
MAS los objetos con los que interactua (herramientas de piedra a la espalda y el POLLO que agarra y lanza, con la pose de sus huesos) empaquetados en `codigos de animacion/alfred/objetos/*.blend` (el .py los anade con `bpy.data.libraries.load` si faltan en la escena).
NO incluye hablar ni expresiones: ni las voces, ni los ojos (`Closed`, `Voz_*`), ni su parpadeo, ni el audio.
Se ejecuta DENTRO de Blender en dos fases (el muestreo recorre todos los frames y tarda):
    ex = {"__name__": "exp", "FASE": "muestrear", "A": 1, "B": 420}   exec(open(RUTA).read(), ex)     # repetir por tramos para muestrear f131-734 (los datos quedan en bpy.app.driver_namespace["ALF_EXP"])
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
POLLO = ["chicken_1"] + [c.name for c in bpy.data.objects["chicken_1"].children_recursive]
MUNDO = {"chicken_1": ("pollo", POLLO)}
RIGS = {"chicken_1": "Armature_chicken_1"}                                                    # objeto con armature propio: se guarda tambien la pose de sus huesos
PIEDRA = ["stone_axe", "stone_shovel"]
ESCENAS = [
    ("llega_corriendo_parte7", 131, 181, "aparece corriendo por el camino (ciclo CORRER del estudio) gritando a Jerry que lo espere", PIEDRA),
    ("se_tuerce_el_tobillo_y_cae_de_cara_parte7", 182, 206, "pisa mal, se le tuerce el tobillo derecho y cae de cara (4 f), rebota tres veces de la cintura para arriba y queda tumbado boca abajo quejandose", PIEDRA),
    ("se_incorpora_y_se_soba_el_tobillo_parte7", 207, 383, "gira 180 grados, se incorpora sentado y se soba el tobillo derecho subiendo y bajando la mano por la espinilla", PIEDRA),
    ("ve_al_creeper_y_entra_en_panico_parte7", 384, 419, "levanta la cabeza de golpe al ver al creeper, agita los brazos rectos como alas y busca con la cabeza", PIEDRA),
    ("agarra_al_pollo_y_lo_lanza_al_creeper_parte7", 420, 439, "se inclina, agarra al pollo por el cuello (f427), toma impulso y se lo lanza al creeper a la cara (suelta en f437)", PIEDRA + ["chicken_1"]),
    ("se_cubre_la_cara_y_asoma_la_cabeza_parte7", 440, 493, "reflejo: se cubre la cara con los antebrazos (f440-446), espera encogido y asoma la cabeza para ver que no paso nada (f481-489)", PIEDRA),
    ("se_levanta_cojeando_parte7", 494, 524, "recoge las piernas, empuja con las manos y se levanta apoyado en la pierna izquierda (tobillo derecho danado)", PIEDRA),
    ("se_acerca_cojeando_al_creeper_parte7", 525, 670, "camina cojeando despacio y con precaucion hasta el creeper tumbado, siempre mirandolo, con una pausa de alerta, y lo observa con la cabeza gacha", PIEDRA),
    ("se_asusta_y_huye_cojeando_parte7", 671, 715, "el creeper convulsiona: se asusta (brazos rectos arriba) y huye intentando correr con el tobillo adolorido", PIEDRA),
    ("se_vuelve_a_torcer_el_tobillo_y_cae_parte7", 716, 734, "al final de la huida se le vuelve a torcer el tobillo y cae de cara con rebotes, como la primera vez", PIEDRA),
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
                if n in RIGS:
                    fr["objs"][n]["huesos"] = {}
                    for pb in bpy.data.objects[RIGS[n]].pose.bones:
                        l_, q_, s_ = pb.matrix_basis.decompose(); fr["objs"][n]["huesos"][pb.name] = (list(map(R5, q_.to_euler('XYZ'))), list(map(R5, l_)), list(map(R5, s_)))
        D[f] = fr
    sc.frame_set(131); print("muestreados f%d-%d; total en memoria: %d frames" % (A, B, len(D)))

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
                if o.parent in originales: c.parent = None; c.matrix_basis = o.matrix_basis.copy()      # hijo (huesos/mallas del pollo): conserva su transformacion LOCAL
                else: c.parent = None; c.matrix_world = Matrix.Identity(4)
                tmp.objects.link(c); copias.append(c)
            for c, o in zip(copias, originales):                                              # conserva la jerarquia (mesa -> malla)
                if o.parent in originales: c.parent = copias[originales.index(o.parent)]; c.parent_type = o.parent_type; c.parent_bone = o.parent_bone; c.matrix_parent_inverse = o.matrix_parent_inverse.copy(); c.matrix_basis = o.matrix_basis.copy()
                for md in getattr(c, 'modifiers', []):                                        # el modificador Armature apunta a la COPIA del armature
                    if md.type == 'ARMATURE' and md.object in originales: md.object = copias[originales.index(md.object)]
            bpy.data.libraries.write(os.path.join(OBJ_DIR, arch + ".blend"), set(copias), fake_user=True)
        finally:
            for c in copias: bpy.data.objects.remove(c, do_unlink=True)
            bpy.data.collections.remove(tmp)
            for o in originales: o.name = o.name[:-6]
        print("paquete", arch + ".blend", nombres)
    # ---------- 2) un .py por escena ----------
    PLANTILLA = open(os.path.join(os.path.dirname(os.path.abspath(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\exportar_animaciones_alfred_parte7.py")), "plantilla_animacion_alfred.py.txt"), encoding="utf-8").read()
    rest = None
    for nombre, f0, f1, titulo, objs in ESCENAS:
        frames = list(range(f0, f1 + 1)); n = len(frames); bones = {}; const = {}
        for bn in D[f0]["bones"]:
            rot = [D[f]["bones"][bn][0] for f in frames]; loc = [D[f]["bones"][bn][1] for f in frames]; esc = [D[f]["bones"][bn][2] for f in frames]
            bones[bn] = {"rotation_euler": rot}
            for ch, vals in (("location", loc), ("scale", esc)):
                if max(abs(v[i] - vals[0][i]) for v in vals for i in range(3)) > 2e-5: bones[bn][ch] = vals
                else: const.setdefault(bn, {})[ch] = vals[0]
        payload = {"info": {"name": nombre + "_alfred", "frames": n, "fps": 24, "entity": "Alfred", "status": "sin aprobar", "fuente": "base_parte_7 (escena viva) f%d-%d" % (f0, f1), "frame_original": f0, "descripcion": titulo, "objetos": objs,
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
            if on in RIGS:
                rec["rig"] = RIGS[on]; rec["enlazar_todo"] = True; rb = {}
                for bn in ds[0]["huesos"]:
                    rb[bn] = {"rotation_euler": [d["huesos"][bn][0] for d in ds]}
                    for k_, ch in ((1, "location"), (2, "scale")):
                        vals = [d["huesos"][bn][k_] for d in ds]
                        if max(abs(v[i] - vals[0][i]) for v in vals for i in range(3)) > 2e-5 or ch == "location": rb[bn][ch] = vals
                rec["rig_bones"] = rb
            if any(h != hide[0] for h in hide): rec["hide"] = hide
            else: rec["hide_const"] = hide[0]
            payload["objetos"][on] = rec
        txt = PLANTILLA.replace("@@TITULO@@", titulo).replace("@@NOMBRE@@", nombre).replace("@@F0@@", str(f0)).replace("@@F1@@", str(f1)).replace("@@N@@", str(n)).replace("@@DEST@@", DEST.replace("\\", "/")).replace("@@PAYLOAD@@", repr(payload))
        ruta = os.path.join(DEST, nombre + "_alfred.py"); open(ruta, "w", encoding="utf-8").write(txt); print("escrito", ruta, "%d KB" % (os.path.getsize(ruta) // 1024), "objetos:", objs)
    sc.frame_set(131); print("LISTO")
