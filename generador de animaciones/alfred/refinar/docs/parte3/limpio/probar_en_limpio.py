# -*- coding: utf-8 -*-
"""PRUEBA EN LIMPIO del guion completo (fase 6). Se ejecuta en un Blender APARTE, sin guardar nada:
  blender.exe --background --factory-startup base_parte_3.blend --python probar_en_limpio.py
1. Activa el add-on INSTALADO `alfred_animation_studio` (comprueba que registra sus operadores y paneles nuevos).
2. Foto "ANTES" de la escena guardada (lo que dejo el generador): pose de Alfred sin voces, objetos, camara, voces y sonidos.
3. LIMPIA en memoria todo lo que el guion debe reconstruir: animacion de Alfred y de su root, voces (NLA y VSE), sonidos manuales, camara y foco, pala / items / pozo.
4. Carga `configuraciones/guion_alfred_parte3.json` y lo reproduce (`reproducir_guion.reproducir`).
5. Foto "DESPUES" y comparacion con la foto ANTES. Escribe `informe_prueba.json` y NO guarda el .blend."""
import json
import math
import os
import sys
import time
import traceback

import bpy

T0 = time.time()
REFINAR = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"; SALIDA = os.path.join(REFINAR, "docs", "parte3", "limpio", "informe_prueba.json")
GUION = os.path.join(REFINAR, "configuraciones", "guion_alfred_parte3.json"); RAIZ = r"C:\Users\user\Desktop\Alfred_Animacion"
inf = {"inicio": time.strftime("%Y-%m-%dT%H:%M:%S"), "blend": bpy.data.filepath, "pasos": {}}


def log(*a):
    print("[limpio %5.0fs]" % (time.time() - T0), *a, flush=True)


# ---------------------------------------------------------------------------------------------------------------- 1. add-on instalado
import addon_utils
try:
    mod = addon_utils.enable("alfred_animation_studio", default_set=False, persistent=False)
    reg = {"modulo": getattr(mod, "__file__", None), "version": getattr(mod, "bl_info", {}).get("version"),
           "operadores": {n: hasattr(bpy.ops.alfst, n) for n in ("guion_reproducir", "guion_cargar_archivo", "audio_importar", "audio_sincronizar", "obj_aplicar", "mov_hornear", "mov_comparar", "snd_aplicar", "cam_aplicar")},
           "paneles": {n: hasattr(bpy.types, n) for n in ("ALFST_PT_audio", "ALFST_PT_objetos", "ALFST_PT_movimiento", "ALFST_PT_escena_guion", "ALFST_PT_reproducir")}}
    inf["addon"] = reg; log("add-on:", reg["version"], "| operadores", sum(reg["operadores"].values()), "/", len(reg["operadores"]), "| paneles", sum(reg["paneles"].values()), "/", len(reg["paneles"]))
except Exception:
    inf["addon"] = {"error": traceback.format_exc()}; log("ERROR al activar el add-on", traceback.format_exc()); json.dump(inf, open(SALIDA, "w", encoding="utf-8"), indent=1); sys.exit(1)
ad = sys.modules["alfred_animation_studio"]
from alfred_animation_studio import audio_import as ai, guion_v2 as gv, motor_alfred as ma, reproducir_guion as rg, sonidos_guion as sg

sc = bpy.context.scene; ctx = bpy.context
A, O = ma._rig(); C = bpy.data.objects["Camera.001"]; F = bpy.data.objects["Foco_Conversacion"]; NUEVOS = ("stone_shovel", "tierra_item", "tablon_item", "stick_1", "stick_2", "cobblestone", "plank_1", "plank_2", "plank_3", "slab_1", "slab_2", "slab_3", "slab_4", "slab_5", "slab_6", "antorcha_2", "mesa_de_crafteo_1")
OBJS = ("stone_axe", "wooden_pickaxe", "wooden_axe") + NUEVOS
VUELO = {"wooden_pickaxe": (220, 229), "wooden_axe": (238, 247), "stone_axe": (256, 265)}                  # frames del vuelo de cada herramienta (suelta + 9)
FRAMES = sorted(set(range(1, 1161, 23)) | {50, 52, 100, 190, 191, 201, 206, 215, 221, 226, 230, 240, 250, 260, 270, 300, 340, 341, 500, 686, 700, 865, 912, 938, 984, 1000, 1026, 1038, 1062, 1070, 1090, 1100, 1120, 1160})


def foto():
    """pose de Alfred (sin voces), objetos, camara y foco en FRAMES + voces y sonidos."""
    trs = [t for t in A.animation_data.nla_tracks if t.name.startswith("VozSync")] if A.animation_data else []
    for t in trs: t.mute = True
    f = {"pose": {}, "obj": {}, "cam": {}}
    try:
        for k in FRAMES:
            sc.frame_set(k); bpy.context.view_layer.update()
            f["pose"][k] = ({b.name: tuple(b.rotation_euler) for b in A.pose.bones}, tuple(A.pose.bones["Hips_alfred"].location), tuple(O.location), O.rotation_euler.z)
            f["cam"][k] = (tuple(C.location), C.data.lens, C.data.dof.aperture_fstop, tuple(F.location))
            f["obj"][k] = {n: (tuple(bpy.data.objects[n].matrix_world.to_translation()), bpy.data.objects[n].matrix_world.to_scale().x, bpy.data.objects[n].hide_viewport) for n in OBJS if bpy.data.objects.get(n)}
    finally:
        for t in trs: t.mute = False
    ed = sc.sequence_editor
    f["voces"] = sorted((int(s.frame_start), s.name) for s in ed.strips_all if s.name.startswith("VozSync_ALFRED"))
    f["sonidos"] = {s.name: (int(s.frame_start), s.channel, round(s.volume, 3)) for s in ed.strips_all if s.type == 'SOUND' and s.name.startswith("SND_") and s.get("guion_id") is None and not s.get("mcsnd_auto")}
    f["pistas_nla"] = sorted(t.name for t in A.animation_data.nla_tracks) if A.animation_data else []
    return f


# ---------------------------------------------------------------------------------------------------------------- 2. foto ANTES
guion = gv.cargar(GUION); plan = {m["etiqueta"] for m in sg.plan_sonidos(guion)}
log("foto ANTES ..."); antes = foto(); log("antes: %d frames, %d voces, %d sonidos manuales" % (len(FRAMES), len(antes["voces"]), len(antes["sonidos"])))

# ---------------------------------------------------------------------------------------------------------------- 3. LIMPIAR (en memoria)
def limpiar():
    for ob in (A, O, C, F, C.data):
        if ob.animation_data:
            ob.animation_data.action = None
            for t in list(ob.animation_data.nla_tracks): ob.animation_data.nla_tracks.remove(t)
    for n in ("stone_axe", "wooden_axe", "wooden_pickaxe"):         # las herramientas existen en la base; se quita su animacion (el guion las anima: espalda, lanzamiento y, el hacha de piedra, desde f984)
        ob = bpy.data.objects[n]
        if ob.animation_data: ob.animation_data_clear()
    for n in NUEVOS + ("pozo_tierra",):                                # lo que el guion crea: se borra con sus hijos (mesa, antorcha 2 con su luz)
        ob = bpy.data.objects.get(n)
        if ob:
            for h in list(ob.children_recursive): bpy.data.objects.remove(h)
            bpy.data.objects.remove(ob)
    ed = sc.sequence_editor
    for s in list(ed.strips_all):
        if s.name.startswith("VozSync_ALFRED") or (s.name.startswith("SND_") and not s.get("mcsnd_auto") and any(s.name.startswith("SND_%s_" % e) for e in plan)): ed.strips.remove(s)
    for b in A.pose.bones: b.rotation_euler = (0, 0, 0); b.location = (0, 0, 0)
    C.location = (0, 0, 0); F.location = (0, 0, 0)


limpiar(); sc.frame_set(1); log("escena LIMPIA: voces VSE %d, pistas NLA de Alfred %d, tiras SND_ manuales %d" % (len([s for s in sc.sequence_editor.strips_all if s.name.startswith("VozSync_ALFRED")]), len(A.animation_data.nla_tracks) if A.animation_data else 0, len([s for s in sc.sequence_editor.strips_all if s.name.startswith("SND_") and not s.get("mcsnd_auto") and any(s.name.startswith("SND_%s_" % e) for e in plan)])))
inf["limpia"] = {"objetos_borrados": [n for n in OBJS + ("pozo_tierra",) if bpy.data.objects.get(n) is None]}

# ---------------------------------------------------------------------------------------------------------------- 4. reproducir el guion
r = gv.validar(guion, RAIZ); inf["validacion"] = r; log("validacion del guion:", len(r["errores"]), "errores,", len(r["avisos"]), "avisos")
t1 = time.time(); informe = rg.reproducir(ctx, guion, log=log); inf["pasos"] = informe; inf["seg_reproducir"] = round(time.time() - t1, 1)
log("reproducido en %.0f s" % inf["seg_reproducir"])

# ---------------------------------------------------------------------------------------------------------------- 5. foto DESPUES y comparacion
log("foto DESPUES ..."); desp = foto(); cmp = {}
mr = mh = mo = 0.0; peor = None
for k in FRAMES:
    a, b = antes["pose"][k], desp["pose"][k]
    for nm in a[0]:
        e = max(abs(a[0][nm][q] - b[0][nm][q]) for q in range(3));
        if e > mr: mr, peor = e, (k, nm)
    mh = max(mh, max(abs(a[1][q] - b[1][q]) for q in range(3))); mo = max(mo, max(abs(a[2][q] - b[2][q]) for q in range(3)), abs(a[3] - b[3]))
cmp["alfred_pose"] = {"rot_max_grados": round(math.degrees(mr), 5), "peor": peor, "hips_loc_max_m": round(mh, 7), "root_max": round(mo, 7), "frames": len(FRAMES)}
mc = [0.0] * 8; mk = [None] * 8
for k in FRAMES:
    a, b = antes["cam"][k], desp["cam"][k]; va = [*a[0], a[1], a[2], *a[3]]; vb = [*b[0], b[1], b[2], *b[3]]
    for i in range(8):
        if abs(va[i] - vb[i]) > mc[i]: mc[i] = abs(va[i] - vb[i]); mk[i] = k
cmp["camara"] = {"dif_max": [round(x, 6) for x in mc], "peor_frame": mk, "canales": ["cam.x", "cam.y", "cam.z", "lente", "apertura", "foco.x", "foco.y", "foco.z"]}
co = {}
for n in OBJS:
    mx = 0.0; pk = None; ms = 0.0
    for k in FRAMES:
        a = antes["obj"][k].get(n); b = desp["obj"][k].get(n)
        if a is None or b is None or (a[1] < 0.002 and b[1] < 0.002) or a[2] or b[2]: continue          # oculto en uno de los dos (el motor oculta la pala hasta que aparece; el generador la dejaba a escala 0.001)
        if n in ("stone_axe", "wooden_axe", "wooden_pickaxe"):
            if VUELO[n][0] <= k <= VUELO[n][1]: continue                    # el generador teletransportaba la herramienta ~1.3 m al soltarla (error de variable: el vuelo partia de la posicion de la vuelta desde Jerry); el motor la lanza desde la mano
        e = math.dist(a[0], b[0]) * 100
        if e > mx: mx, pk = e, k
        ms = max(ms, abs(a[1] - b[1]))
    co[n] = {"loc_max_cm": round(mx, 2), "peor_frame": pk, "escala_max": round(ms, 4)}
cmp["objetos"] = co
cmp["voces"] = {"antes": antes["voces"], "despues": desp["voces"], "iguales": antes["voces"] == desp["voces"]}
sa = {n: v for n, v in antes["sonidos"].items() if any(n.startswith("SND_%s_" % e) for e in plan)}                # solo los sonidos que el guion gobierna (no los de lobo / zombies / Jerry)
sd2 = {s.name: (int(s.frame_start), s.channel, round(s.volume, 3)) for s in sc.sequence_editor.strips_all if s.type == 'SOUND' and s.get("guion_id")}
cmp["sonidos"] = {"antes_del_guion": len(sa), "despues_del_guion": len(sd2), "iguales": set(sa) == set(sd2) and all(sd2[n][:2] == sa[n][:2] and abs(sd2[n][2] - sa[n][2]) < 0.002 for n in sa), "distintos": [n for n in sa if n not in sd2 or sd2[n][:2] != sa[n][:2] or abs(sd2[n][2] - sa[n][2]) >= 0.002][:6]}
cmp["pistas_nla"] = {"antes": antes["pistas_nla"], "despues": desp["pistas_nla"]}
inf["comparacion"] = cmp; inf["total_seg"] = round(time.time() - T0, 1)
json.dump(inf, open(SALIDA, "w", encoding="utf-8"), indent=1, default=str); log("INFORME", json.dumps(cmp, default=str)[:2500]); log("NO se guardo el .blend. Total %.0f s" % (time.time() - T0))
