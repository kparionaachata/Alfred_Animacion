# -*- coding: utf-8 -*-
"""(copia para alfred_cueva_3.blend, 2026-10-29) EXPORTA las animaciones de Alfred (acciones `alfredAction.210` / `ArmatureAction.210`, f1-390) de la escena viva a archivos .py independientes en `codigos de animacion/alfred/`, uno por escena, con el MISMO formato de los demas (`PAYLOAD` + `execute_animation(start_frame)`),
MAS los objetos con los que interactua (pico de piedra, bloque de mineral de hierro, hierro crudo y hacha de piedra a la espalda) empaquetados en `codigos de animacion/alfred/objetos/*.blend` (el .py los anade con `bpy.data.libraries.load` si faltan en la escena).
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
OBJS = ["stone_pickaxe", "bloque_iron_ore_-68_-19_-12", "raw_iron_soltado", "stone_axe"]          # pico (en la mano), bloque que pica, hierro que suelta, hacha a la espalda
HERR = OBJS; BLOQUES = []
MUNDO = {n: ("mineria_cueva3", OBJS) for n in OBJS}; APARENTADOS = {}; RIGS = {}
H = HERR
F_ORIG = sc.frame_current                                                                      # se restaura al terminar
TAG = "cueva3"                                                                                 # escena de origen (base_ranas_2.blend): acciones `alfred_rodea_ring` / `alfred_guardia_ring`, f1-745 (cinco fases marcadas: Estudio, Primer intercambio, Presion MMA, Climax, Reinicio)
ESCENAS = [
    ("01_pica_el_bloque_de_hierro_" + TAG, 1, 75, "pica el bloque de mineral de hierro con el pico de piedra: golpes en f12, f28, f44 y f60 con grietas hasta f73", H),
    ("02_el_bloque_se_rompe_y_suelta_hierro_" + TAG, 76, 100, "el bloque se rompe en f76 y suelta hierro crudo; Alfred termina el movimiento de los brazos", H),
    ("03_baja_y_suelta_el_pico_" + TAG, 101, 160, "baja el pico y lo deja en el suelo a su lado (entre f121 y f160)", H),
    ("04_quieto_mirando_alrededor_" + TAG, 161, 200, "quieto: respira y mueve solo el cuello mirando a su alrededor", H),
    ("05_gesto_con_el_brazo_derecho_" + TAG, 201, 240, "gesto con el brazo derecho (movimiento marcado en f231)", H),
    ("06_se_echa_atras_y_recoge_el_hierro_" + TAG, 241, 275, "se echa unos 0.4 m hacia atras, se inclina y recoge el hierro crudo (f252-274)", H),
    ("07_lanza_el_hierro_hacia_arriba_" + TAG, 276, 295, "lanza el hierro crudo hacia arriba (sube unos 7 m) con mucho movimiento de brazos", H),
    ("08_quieto_mientras_cae_el_hierro_y_la_estalactita_" + TAG, 296, 335, "quieto mientras el hierro cae (aterriza en f321) y una estalactita cae junto a el (f315-329)", H),
    ("09_cae_al_suelo_y_queda_tumbado_" + TAG, 336, 350, "cae al suelo tras caer la estalactita: el cuerpo gira unos 90 grados en el eje X (de pie a tumbado) en f336-350 y el root sube unos 0.25 m", H),
    ("10_queda_tumbado_" + TAG, 351, 390, "queda tumbado e inmovil en el suelo hasta el final", H),
]
R5 = lambda v: round(float(v), 5)

if FASE == "muestrear":
    A, B = int(globals()["A"]), int(globals()["B"]); D = ns.setdefault("ALF_EXP", {})
    objs = sorted({o for e in ESCENAS for o in e[4]})
    for f in range(A, B + 1):
        sc.frame_set(f); bpy.context.view_layer.update(); fr = {"bones": {}, "root": [list(map(R5, EA.location)), list(map(R5, (EA.rotation_quaternion.to_euler('XYZ') if EA.rotation_mode == 'QUATERNION' else EA.rotation_euler)))], "objs": {}}
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
    sc.frame_set(F_ORIG); print("muestreados f%d-%d; total en memoria: %d frames" % (A, B, len(D)))

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
    PLANTILLA = open(os.path.join(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones", "plantilla_animacion_alfred_cueva3.py.txt"), encoding="utf-8").read()
    rest = None
    for nombre, f0, f1, titulo, objs in ESCENAS:
        frames = list(range(f0, f1 + 1)); n = len(frames); bones = {}; const = {}
        for bn in D[f0]["bones"]:
            rot = [D[f]["bones"][bn][0] for f in frames]; loc = [D[f]["bones"][bn][1] for f in frames]; esc = [D[f]["bones"][bn][2] for f in frames]
            bones[bn] = {"rotation_euler": rot}
            for ch, vals in (("location", loc), ("scale", esc)):
                if max(abs(v[i] - vals[0][i]) for v in vals for i in range(3)) > 2e-5: bones[bn][ch] = vals
                else: const.setdefault(bn, {})[ch] = vals[0]
        payload = {"info": {"name": nombre + "_alfred", "frames": n, "fps": 24, "entity": "Alfred", "status": "sin aprobar", "fuente": "alfred_cueva_3 (escena viva) f%d-%d" % (f0, f1), "frame_original": f0, "descripcion": titulo, "objetos": objs,
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
    sc.frame_set(F_ORIG); print("LISTO")
