# -*- coding: utf-8 -*-
"""alfred_cueva_5D.blend: sonidos de the_stalker_1 camino al pico: pasos (camina, corre, gatea con las cuatro patas), manotazos a los zombies, impactos de los zombies contra paredes y suelo,
y sonidos propios de la criatura al observar el pico y mirar hacia arriba. Usa el add-on Alfred Sonidos (tiras SND_, etiqueta mcsnd_origen = ORIGEN; se borran y se rehacen).
Requiere ejecutados antes: ruta_stalker_pico.py, stalker_camina_hasta_pico.py, fk_pose.py, stalker_tres_recorridos.py, fk_clearance.py.
Uso: exec(este); sonorizar()"""
import bpy, importlib.util, sys, math
from mathutils import Vector

ADDON = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py"
MAN = "C:/Users/user/Desktop/Alfred_Animacion/sonidos/The Man From The Fog/"
ORIGEN = "stalker_pico"
F_CORRE, F_GATEA, F_LLEGA = 458, 686, 891
GOLPES_F = (105, 205, 305, 405)
F_RISER_FIN = 1005
T_CICLO = 7.0                                   # gateo_terreno.T_CICLO: apoyo de cada extremidad cada 7 frames (diagonales en contrafase)
FASE = {"HL": 0.0, "FR": 0.0, "HR": 0.5, "FL": 0.5}


def cargar_addon():
    m = sys.modules.get("alfred_sonidos_local")
    if m is None:
        spec = importlib.util.spec_from_file_location("alfred_sonidos_local", ADDON)
        m = importlib.util.module_from_spec(spec)
        sys.modules["alfred_sonidos_local"] = m
        spec.loader.exec_module(m)
        m.register()
    return m


def _picos(vals, a, b, umbral, sep):
    """maximos locales de la serie vals[a..b] (dict frame->valor) por encima de `umbral`, separados al menos `sep` frames (gana el mayor)"""
    c = [fr for fr in range(a + 1, b) if vals[fr] > vals[fr - 1] and vals[fr] >= vals[fr + 1] and vals[fr] > umbral]
    c.sort(key=lambda fr: -vals[fr])
    ok = []
    for fr in c:
        if all(abs(fr - g) >= sep for g in ok):
            ok.append(fr)
    return sorted(ok)


def detectar():
    """frames de apoyo de cada pie al caminar/correr (maximo de avance del muslo), de las cuatro patas al gatear (calendario del ciclo) e impactos de cada zombie"""
    preparar()
    indexar_claves()
    pasos = []
    for lado in "LR":
        ang = {fr: _q("thigh.%s_1" % lado, fr).to_euler()[0] for fr in range(0, F_GATEA + 2)}
        for a, b, sep in ((1, F_CORRE, 17), (F_CORRE, F_GATEA - 4, 10)):
            for fr in _picos(ang, a, b, 0.15, sep):
                pasos.append((fr, lado, "camina" if fr < F_CORRE else "corre"))
    for nombre, fase in FASE.items():
        m = 0
        while True:
            fr = int(round(F_GATEA + 2 + fase * T_CICLO + m * T_CICLO))
            if fr > F_LLEGA - 3:
                break
            pasos.append((fr, nombre, "gatea"))
            m += 1
    imp = {}
    for k in range(len(GOLPES_F)):
        z = bpy.data.objects["zombie_cav_5_cruza%d" % k]
        fz = {(f.data_path, f.array_index): f for l in z.animation_data.action.layers for s in l.strips for cb in s.channelbags for f in cb.fcurves}
        P = lambda f: Vector([fz[("location", i)].evaluate(f) for i in range(3)])
        ks = [kp.co.x for kp in fz[("location", 2)].keyframe_points]
        acc = {fr: ((P(fr + 1) - P(fr)) - (P(fr) - P(fr - 1))).length for fr in range(int(ks[0]), int(ks[-1]) - 1)}
        acc[int(ks[0]) - 1] = 0.0
        imp[k] = [(fr, acc[fr]) for fr in _picos(acc, int(ks[0]), int(ks[-1]) - 2, 0.5, 4)]
    return pasos, imp


def sonorizar():
    m = cargar_addon()
    sc = bpy.context.scene
    p = sc.mcsnd
    m.indice(p, forzar=True)
    ed = sc.sequence_editor or sc.sequence_editor_create()
    for t in [t for t in m._strips(ed) if t.get("mcsnd_origen") == ORIGEN]:
        m._strips(ed).remove(t)
    rng = m.rng_de(p)
    puestos = []
    f_act = sc.frame_current

    def poner(evento, frame, vol, grupo):
        rutas = m.rutas_de(p, evento)
        if not rutas:
            print("sin sonido:", evento)
            return
        t = m.colocar(bpy.context, p, rutas, int(frame), grupo, evento.replace(".", "_"), vol * (0.5 if grupo == "golpes" else 1.0), 0, rng)       # golpes a la mitad (pedido del usuario)
        if t:
            t["mcsnd_origen"] = ORIGEN
            puestos.append((evento, int(frame)))

    pasos, imp = detectar()
    vol_paso = {"camina": 0.5, "corre": 0.7, "gatea": 0.55}
    for fr, miembro, tipo in pasos:
        v = vol_paso[tipo] * (0.7 if miembro in ("HL", "HR") else 1.0) * (0.9 + 0.1 * ((fr * 7) % 3) / 2.0)
        poner("block.stone.step", fr, v, "pasos")
        if tipo == "corre":
            poner("block.stone.hit", fr, 0.25, "pasos")                  # mas peso al correr
    for k, (fh, evs) in enumerate(imp.items()):
        Fh = GOLPES_F[k]
        poner("entity.player.attack.sweep", Fh - 4, 0.7, "golpes")      # el brazo corta el aire
        poner("entity.player.attack.knockback", Fh, 1.0, "golpes")      # manotazo violento
        poner("entity.player.attack.strong", Fh + 1, 0.8, "golpes")
        for fr, a in evs:
            if fr <= Fh + 2:
                continue
            v = max(0.3, min(1.0, a / 1.6))
            poner("block.stone.hit", fr, v, "golpes")                    # rebota o se estrella contra pared o suelo
            if a > 0.9:
                poner("entity.generic.small_fall", fr + 1, v * 0.8, "golpes")
        if evs:
            poner("entity.generic.big_fall", evs[-1][0] + 1, 0.8, "golpes")      # cae al suelo y queda inmovil
    poner("block.stone.hit", 339, 0.6, "golpes")                          # el zombie 2 vuelca de la cornisa (zombies_cruzan_camino.asentar_zombie) y queda en el suelo
    poner("entity.generic.small_fall", 340, 0.5, "golpes")
    # propios de la criatura (The Man From The Fog): aparece, grita al empezar a correr y suena chasedv2 justo al empezar a gatear (f686) y el crescendo termina al mirar hacia arriba
    for fr, arch, vol, canal in ((2, "spawn1.ogg", 1.0, 120), (F_CORRE, "screams-version-2.ogg", 0.2, 121), (F_GATEA, "chasedv2.ogg", 0.5, 127), (None, "ghost-scream-riser-joshua-chivers-1-00-09_1.ogg", 0.3, 122)):
        s = ed.strips.new_sound("SND_stalker_%s" % arch[:-4], MAN + arch, canal, fr or 1)
        if fr is None:
            s.frame_start = F_RISER_FIN - s.frame_final_duration            # el riser termina cuando la criatura ya mira hacia arriba
            fr = s.frame_start
        s.volume = vol
        s["mcsnd_origen"] = ORIGEN
        puestos.append((arch, int(fr)))
    # ambiente de la cueva (The Man From The Fog), a volumen bajo y repartido por toda la escena
    for fr, arch, vol, canal in ((30, "spawn-version-1.ogg", 1.44, 123), (280, "spawn-version-2.ogg", 1.44, 124), (540, "spawn-version-3.ogg", 1.44, 125), (780, "spotted.ogg", 1.44, 126)):
        s = ed.strips.new_sound("SND_ambiente_%s" % arch[:-4], MAN + arch, canal, fr)
        s.volume = vol
        s["mcsnd_origen"] = ORIGEN
        puestos.append((arch, fr))
    sc.frame_set(f_act)
    return {"tiras": len(puestos), "pasos": len(pasos), "impactos_zombies": {k: len(v) for k, v in imp.items()}}
