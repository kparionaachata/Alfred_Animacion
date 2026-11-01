# -*- coding: utf-8 -*-
"""(copia para base_ranas_2.blend, 2026-10-26) EXPORTA las animaciones de Alfred (acciones `alfred_rodea_ring` / `alfred_guardia_ring`, f1-745) de la escena viva a archivos .py independientes en `codigos de animacion/alfred/`, uno por escena, con el MISMO formato de los demas (`PAYLOAD` + `execute_animation(start_frame)`),
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
APARENTADOS = {}
HERR = []; BLOQUES = []                                                                        # en este .blend Alfred no interactua con ningun objeto
MUNDO = {}; APARENTADOS = {}; RIGS = {}
H = HERR
F_ORIG = sc.frame_current                                                                      # se restaura al terminar
TAG = "ranas2"                                                                                 # escena de origen (base_ranas_2.blend): acciones `alfred_rodea_ring` / `alfred_guardia_ring`, f1-745 (cinco fases marcadas: Estudio, Primer intercambio, Presion MMA, Climax, Reinicio)
ESCENAS = [
    ("01_guardia_con_rebote_y_jab_izquierdo_" + TAG, 1, 30, "Fase 1 Estudio: guardia con rebote y jab izquierdo en el sitio", H),
    ("02_rodea_al_rival_en_guardia_" + TAG, 31, 131, "Fase 1 Estudio: rodea al rival en circulo (giro de 90 a 165 grados) con guardia y jabs", H),
    ("03_gira_de_vuelta_y_se_estabiliza_" + TAG, 132, 159, "Fase 1 Estudio: gira de vuelta (165 a 141 grados) y se estabiliza", H),
    ("04_avanza_un_paso_de_ajuste_" + TAG, 160, 175, "Fase 2 Primer intercambio: pequeno avance de ajuste", H),
    ("05_golpea_con_el_brazo_izquierdo_y_patea_" + TAG, 176, 206, "Fase 2 Primer intercambio: golpe con el brazo izquierdo y patada con la pierna derecha", H),
    ("06_combina_con_la_pierna_levantada_" + TAG, 207, 250, "Fase 2 Primer intercambio: combinacion con la pierna levantada y la cadera inclinada", H),
    ("07_vuelve_a_rodear_al_rival_" + TAG, 251, 329, "Fase 2 Primer intercambio: vuelve a rodear (134 a 164 grados) con guardia y jabs", H),
    ("08_orbita_mas_rapido_" + TAG, 330, 345, "Fase 3 Presion MMA: orbita mas rapido (173 a 186 grados)", H),
    ("09_ataque_bajo_con_salto_" + TAG, 346, 371, "Fase 3 Presion MMA: ataque bajo con salto (baja y sube la cadera, la pierna se lanza hacia atras)", H),
    ("10_se_reposiciona_girando_" + TAG, 372, 390, "Fase 3 Presion MMA: se reposiciona girando (211 a 225 grados)", H),
    ("11_giro_lateral_rapido_" + TAG, 391, 410, "Fase 3 Presion MMA: giro lateral rapido de unos 66 grados (esquiva o pivote)", H),
    ("12_patada_con_la_pierna_derecha_" + TAG, 411, 430, "Fase 3 Presion MMA: patada con la pierna derecha", H),
    ("13_guardia_y_presion_con_jabs_" + TAG, 431, 499, "Fase 3 Presion MMA: guardia, rebote y presion con jabs", H),
    ("14_ataque_explosivo_baja_la_guardia_y_rodillazo_" + TAG, 500, 510, "Fase 4 Climax: ataque explosivo, baja la guardia y levanta la rodilla", H),
    ("15_combos_con_la_pierna_" + TAG, 511, 545, "Fase 4 Climax: combos rapidos con la pierna", H),
    ("16_patada_giratoria_" + TAG, 546, 575, "Fase 4 Climax: patada giratoria con giro brusco del cuerpo", H),
    ("17_recupera_tras_el_giro_con_un_salto_" + TAG, 576, 605, "Fase 4 Climax: recuperacion tras el giro con un pequeno salto", H),
    ("18_rodea_en_sentido_contrario_" + TAG, 606, 649, "Fase 4 Climax: rodea en sentido contrario con jabs", H),
    ("19_sigue_la_orbita_" + TAG, 650, 680, "Fase 5 Reinicio: sigue la orbita (-44 a 13 grados)", H),
    ("20_recoloca_los_brazos_y_jab_con_el_codo_" + TAG, 681, 705, "Fase 5 Reinicio: recoloca los brazos y da un jab con movimiento fuerte del codo izquierdo", H),
    ("21_guardia_final_con_rebote_" + TAG, 706, 745, "Fase 5 Reinicio: ultima guardia con rebote", H),
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
        payload = {"info": {"name": nombre + "_alfred", "frames": n, "fps": 24, "entity": "Alfred", "status": "sin aprobar", "fuente": "base_ranas_2 (escena viva) f%d-%d" % (f0, f1), "frame_original": f0, "descripcion": titulo, "objetos": objs,
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
