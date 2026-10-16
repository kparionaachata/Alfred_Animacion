# -*- coding: utf-8 -*-
"""Parte 11: Jerry le RESPONDE a Alfred "Te esta bien huevon, ¿no? Solo te estoy preguntando, anda ve por tu comida."
- Voz + cara (boca, cabeza, cejas, ojos, pupilas): voz_jerry_comun.aplicar con el archivo del usuario
  (audios/jerry/jerry_te_esta_bien_anda_ve_por_tu_comida.cara_original.py).
- SINCRONIA: el silencio del audio tras "¿no?" (frames 31-37 del audio) cae sobre el "Oh" de la ultima flecha de Alfred (entrepierna).
- En "anda ve por tu comida" (frames 70-95 del audio): gira un poco hacia el BOSQUE (oeste-noroeste, robles a ~5 m), levanta la pata
  delantera DERECHA apuntandolo, la baja rapido y se voltea con pasitos hacia la FOGATA a mirar como se cocina (cabeza un poco abajo).
Se suma a la accion de jerry_nada_pescado_parte11.py guardando lo sumado (se deshace al repetir). Al final aplica el MICROFONO."""
import bpy, os, math, importlib.util

BASE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\parte11"
AUDIO = r"C:\Users\user\Desktop\Alfred_Animacion\audios\jerry\jerry_te_esta_bien_anda_ve_por_tu_comida.wav"
CARA = r"C:\Users\user\Desktop\Alfred_Animacion\audios\jerry\jerry_te_esta_bien_anda_ve_por_tu_comida.cara_original.py"
NOMBRE = "VOZ_p11_jerry_anda_ve"; MARCA = "voz_jerry_anda_ve"; MARCA_GESTO = "gesto_anda_ve"
VOLUMEN = 1.3                                # como la otra voz de Jerry
SILENCIO_AUDIO = 31                          # frame del audio donde empieza el silencio tras "¿no?" (cae en el "Oh")
YAW_BOSQUE = 165.0                           # grados del root: el bosque (150 grados en planta) le queda a la derecha
YAW_FOGATA = 90.0                            # mira a -X: la fogata
# pata delantera derecha apuntando al bosque: front_shoulder.R con el valor que dio el usuario
PATA = {"front_shoulder.R": (72.074, 29.231, 2.4541), "front_thigh.R": (0, 0, 0), "front_shin.R": (0, 0, 0),
        "front_foot.R": (0, 0, 0), "front_toe.R": (0, 0, 0)}
MIRA_FUEGO = {"scull": 0.30, "scull_1": 0.12}  # rad X+ = hocico abajo: mira la comida en la fogata
PIERNAS = ("shoulder", "thigh", "shin", "foot", "toe")


def _mod(nombre, ruta):
    sp = importlib.util.spec_from_file_location(nombre, ruta); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


def _sstep(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


def _curvas(idb):
    a = idb.animation_data.action
    return {(fc.data_path, fc.array_index): fc for l in a.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves}


def _mover(fc, f, d):
    k = fc.keyframe_points[f - 1]
    if int(round(k.co.x)) != f: raise RuntimeError("clave inesperada %s %d" % (fc.data_path, f))
    k.co.y += d; k.handle_left.y += d; k.handle_right.y += d


def _deshacer(idb, marca):
    a = idb.animation_data.action; dd = a.get(marca + "_deltas")
    if dd:
        cv = _curvas(idb)
        for clave, v in dd.to_dict().items():
            ruta, idx = clave.rsplit("|", 1); fc = cv[(ruta, int(idx))]
            for j, x in enumerate(v["vals"]): _mover(fc, v["ini"] + j, -x)
        for fc in cv.values(): fc.update()
        del a[marca + "_deltas"]
    if marca in a: del a[marca]


def construir(con_microfono=True):
    sc = bpy.context.scene; TT = sc["p11_tiempos"]; comun = _mod("voz_jerry_comun", os.path.join(BASE, "voz_jerry_comun.py"))
    F0 = int(TT["flecha_entrepierna_e0"]) + 5 - SILENCIO_AUDIO + 1        # el "Oh" (e0+5) cae en el silencio del audio
    arm = bpy.data.objects["Dog_001_rig"]; root = bpy.data.objects["jerry_sin_armadura"]
    F0, F1 = comun.aplicar(AUDIO, CARA, NOMBRE, F0, MARCA, VOLUMEN, 31, False)

    # ---- gesto + voltear a la fogata (deltas guardados)
    for idb in (arm, root): _deshacer(idb, MARCA_GESTO)
    fa = lambda k: F0 + k - 1                                          # frame del audio -> escena
    G0, G1 = fa(60), fa(71)                                            # gira hacia el bosque
    P0, P1, P2, P3 = fa(66), fa(73), fa(88), fa(93)                    # pata: sube rapido, apunta, baja rapido
    T0, T1 = fa(93), fa(93) + 28                                       # se voltea a la fogata con pasitos
    FIN = sc.frame_end; rango = list(range(G0 - 1, FIN + 1))
    cv_r = _curvas(root); cv_a = _curvas(arm); dr = {}; da = {}

    fyaw = cv_r[("rotation_euler", 2)]; base_yaw = fyaw.evaluate(G0 - 1)
    for f in rango:
        w1 = _sstep((f - G0) / (G1 - G0)); w2 = _sstep((f - T0) / (T1 - T0))
        objetivo = base_yaw + (math.radians(YAW_BOSQUE) - base_yaw) * w1 + (math.radians(YAW_FOGATA) - math.radians(YAW_BOSQUE)) * w2
        dr.setdefault("rotation_euler|2", []).append(objetivo - fyaw.evaluate(f))

    paso = _mod("p11_caminar_g", os.path.join(BASE, "jerry_fuentes", "caminar_jerry.py")).generate_keyframes(T1 - T0 + 1)
    for f in rango:
        wp = _sstep((f - P0) / (P1 - P0)) * (1 - _sstep((f - P2) / (P3 - P2)))
        wt = math.sin(math.pi * max(0.0, min(1.0, (f - T0) / (T1 - T0))))                 # pasitos solo mientras gira
        wf = _sstep((f - T0 - 10) / 14)                                                  # cabeza hacia la comida
        for b in [pb.name for pb in arm.pose.bones]:
            for i in range(3):
                ruta = 'pose.bones["%s"].rotation_euler' % b; fc = cv_a.get((ruta, i))
                if fc is None: continue
                d = 0.0
                if b in PATA and wp > 0: d += (math.radians(PATA[b][i]) - fc.evaluate(f)) * wp
                if wt > 0 and any(p in b for p in PIERNAS) and b in paso:
                    d += paso[b][min(len(paso[b]), max(1, f - T0 + 1))][i] * 0.6 * wt
                if i == 0 and b in MIRA_FUEGO: d += MIRA_FUEGO[b] * wf
                if d: da.setdefault("%s|%d" % (ruta, i), [0.0] * len(rango))[f - rango[0]] = d
    for clave, vals in dr.items():
        r, i = clave.rsplit("|", 1)
        for j, d in enumerate(vals): _mover(cv_r[(r, int(i))], rango[j], d)
    for clave, vals in da.items():
        r, i = clave.rsplit("|", 1)
        for j, d in enumerate(vals): _mover(cv_a[(r, int(i))], rango[j], d)
    for fc in list(cv_r.values()) + list(cv_a.values()): fc.update()

    # apoyo en el suelo (los pasitos/la pata pueden hundir o levantar unos cm): se corrige la altura del root
    fz = cv_r[("location", 2)]; ms = [o for o in arm.children if o.type == 'MESH' and not o.name.startswith("pescado")]; dz = []
    for f in rango:
        sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); lo = 99
        for o in ms:
            e = o.evaluated_get(dg); m = e.to_mesh(); mw = o.matrix_world
            lo = min(lo, min((mw @ v.co).z for v in m.vertices)); e.to_mesh_clear()
        d = 8.0 - lo if lo < 8.0 else 0.0; dz.append(d)
        if d: _mover(fz, f, d)
    fz.update(); dr["location|2"] = dz
    root.animation_data.action[MARCA_GESTO + "_deltas"] = {k: {"ini": rango[0], "vals": v} for k, v in dr.items()}
    arm.animation_data.action[MARCA_GESTO + "_deltas"] = {k: {"ini": rango[0], "vals": v} for k, v in da.items()}
    for idb in (arm, root): idb.animation_data.action[MARCA_GESTO] = F0

    if con_microfono: comun.microfono()
    sc["p11_voz_jerry_anda_ve"] = {"inicio": F0, "fin": F1, "pata": [P0, P3], "a_fogata": [T0, T1]}
    print("VOZ JERRY 'anda ve':", F0, "-", F1, "pata", P0, "-", P3, "fogata", T0, "-", T1)
    return F0


if __name__ in ("__main__", "x"):
    construir()
