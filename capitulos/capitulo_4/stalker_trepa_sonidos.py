# -*- coding: utf-8 -*-
"""alfred_cueva_5E.blend: sonidos de the_stalker_1 al correr, saltar y trepar: pasos de la carrera, despegue (golpe + silbido + grito), impacto del aterrizaje, y por cada agarre de una mano o un pie en la pared/techo
el golpe de la garra o el paso sobre la piedra, con trocitos que caen (grava / piedra rota) en algunos agarres. Usa el add-on Alfred Sonidos (tiras SND_, etiqueta mcsnd_origen = ORIGEN; se borran y se rehacen).
Requiere ejecutados antes: stalker_trepa_base.py, stalker_trepa_pared.py, stalker_trepa_ruta.py y planear/preparar_plan/trayecto (P, bv) en bpy.app.driver_namespace['trepa'].
Uso: sonorizar(P)"""
import bpy, importlib.util, sys, random, math

ADDON = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py"
MAN = "C:/Users/user/Desktop/Alfred_Animacion/sonidos/The Man From The Fog/"
ORIGEN = "stalker_trepa"


def cargar_addon():
    m = sys.modules.get("alfred_sonidos_local")
    if m is None:
        spec = importlib.util.spec_from_file_location("alfred_sonidos_local", ADDON)
        m = importlib.util.module_from_spec(spec)
        sys.modules["alfred_sonidos_local"] = m
        spec.loader.exec_module(m)
        m.register()
    return m


def sonorizar(P, semilla=3):
    m = cargar_addon()
    sc = bpy.context.scene
    p = sc.mcsnd
    m.indice(p, forzar=True)
    ed = sc.sequence_editor or sc.sequence_editor_create()
    for t in [t for t in m._strips(ed) if t.get("mcsnd_origen") == ORIGEN]:
        m._strips(ed).remove(t)
    rng = m.rng_de(p)
    az = random.Random(semilla)
    puestos = []
    f_act = sc.frame_current

    def poner(evento, frame, vol, grupo):
        rutas = m.rutas_de(p, evento)
        if not rutas:
            print("sin sonido:", evento)
            return
        t = m.colocar(bpy.context, p, rutas, int(frame), grupo, evento.replace(".", "_"), vol, 0, rng)
        if t:
            t["mcsnd_origen"] = ORIGEN
            puestos.append((evento, int(frame)))

    # impulso: raspa la grava al encogerse
    poner("block.gravel.step", 8, 0.3, "pasos")
    poner("block.gravel.step", 16, 0.35, "pasos")
    # carrera: un paso por apoyo de cada extremidad
    for n in NEUTRO:
        k = 1
        while True:
            td = F_RUN0 - BETA_C * T_CORRE + FASE[n] * T_CORRE + k * T_CORRE
            if td >= F_J0 - 1:
                break
            if td > F_RUN0:
                poner("block.stone.step", td, (0.45 if n[0] == "H" else 0.6) * az.uniform(0.9, 1.0), "pasos")
            k += 1
    # despegue: patada, silbido en el aire y el grito (la mandibula se abre en F_J0 - 3)
    poner("block.stone.hit", F_J0, 0.9, "golpes")
    poner("block.stone.step", F_J0, 0.7, "pasos")
    poner("entity.player.attack.sweep", F_J0 + 3, 0.6, "golpes")
    s = ed.strips.new_sound("SND_stalker_trepa_grito", MAN + "screams-version-2.ogg", 123, F_J0 - 3)
    s.volume = 0.3
    s["mcsnd_origen"] = ORIGEN
    puestos.append(("screams-version-2.ogg", F_J0 - 3))
    # aterrizaje: impacto de manos y pies contra el muro, piedra que se rompe y grava que cae
    poner("block.stone.hit", F_J1, 1.0, "golpes")
    poner("entity.generic.big_fall", F_J1, 0.7, "golpes")
    poner("block.stone.hit", F_J1 + 1, 0.8, "golpes")
    poner("block.stone.break", F_J1 + 2, 0.6, "golpes")
    poner("block.gravel.fall", F_J1 + 7, 0.45, "golpes")
    poner("block.gravel.fall", F_J1 + 14, 0.3, "golpes")
    # trepada: un sonido por agarre (garra: golpe de piedra; pie: paso) y, de vez en cuando, trocitos que caen
    n_g = 0
    for n in NEUTRO:
        m_ = 1
        while True:
            td = F_L1 - BETA_T * T_TREPA + FASE[n] * T_TREPA + m_ * T_TREPA
            if td > P["f_llega"]:
                break
            if td > F_L1:
                v = az.uniform(0.85, 1.0)
                if n[0] == "H":
                    poner("block.stone.hit", td, 0.5 * v, "agarres")
                    poner("block.stone.step", td, 0.25 * v, "agarres")
                else:
                    poner("block.stone.step", td, 0.45 * v, "agarres")
                n_g += 1
                if n_g % 3 == 0:
                    poner("block.gravel.fall" if n_g % 2 else "block.stone.fall", td + az.randint(5, 12), 0.22 * v, "trocitos")
                if n_g % 11 == 0:
                    poner("block.stone.break", td + 2, 0.3, "trocitos")
            m_ += 1
    # llega: ultimo agarre bajo la plataforma
    sc.frame_set(f_act)
    return {"tiras": len(puestos), "agarres": n_g}
