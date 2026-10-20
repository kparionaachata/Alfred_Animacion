# -*- coding: utf-8 -*-
"""Sonidos de Minecraft para las animaciones que faltaban: el agua que cae por el hueco (-49, -19), Jerry (trote, salto al agua, rebote, vadeo, sacudida) y Alfred levantandose.
Usa el add-on Alfred Sonidos (tiras SND_ en el editor de secuencias). Uso en Blender: exec(open(ruta).read()); sonorizar()
Los frames salen de las propiedades que dejaron los guiones: `jerry["jerry_agua"]` (jerry_baja_agua.py) y `alfred["f_levanta"]` (alfred_levantarse.py).
"""
import bpy, importlib.util, sys, json

ADDON = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py"
ORIGEN = "jerry_agua"


def cargar_addon():
    m = sys.modules.get("alfred_sonidos_local")
    if m is None:
        spec = importlib.util.spec_from_file_location("alfred_sonidos_local", ADDON)
        m = importlib.util.module_from_spec(spec)
        sys.modules["alfred_sonidos_local"] = m
        spec.loader.exec_module(m)
        m.register()
    return m


def sonorizar(f_agua=150, t_caida=100):
    m = cargar_addon()
    sc = bpy.context.scene
    ob = bpy.data.objects
    J = json.loads(ob["jerry"]["jerry_agua"])
    f_ini, f_parada, f_baja = J["f_ini"], J["f_parada"], J["f_baja"]
    f_choque, f_aterriza, f_borde, f_seco, f_fin = J["f_choque"], J["f_aterriza"], J["f_borde"], J["f_seco"], J["f_fin"]
    f_ruta_ini, f_lanza = int(J.get("f_ruta_ini", 0)), int(J.get("f_lanza", 0))
    f_rel, f_golpe = int(J.get("f_rel", 0)), int(J.get("f_golpe", 0))
    f_levanta = int(ob["alfred"].get("f_levanta", 370))
    p = sc.mcsnd
    m.indice(p, forzar=True)
    ed = sc.sequence_editor or sc.sequence_editor_create()
    for t in [t for t in m._strips(ed) if t.name.startswith(m.PREFIJO) and t.get("mcsnd_origen") == ORIGEN]:
        m._strips(ed).remove(t)
    rng = m.rng_de(p)
    puestos = []

    def poner(evento, frame, vol=1.0, grupo="golpes"):
        rutas = m.rutas_de(p, evento)
        if not rutas:
            print("sin sonido:", evento)
            return
        t = m.colocar(bpy.context, p, rutas, int(frame), grupo, evento.replace(".", "_"), vol, 0, rng)
        if t:
            t["mcsnd_origen"] = ORIGEN
            puestos.append((t.name, int(frame)))

    # --- agua: se vacia el cubo en el hueco, cae la columna y despues suena el agua corriendo
    poner("item.bucket.empty", f_agua, 1.0, "objetos")
    for f in range(f_agua + 8, f_levanta + 185, 70):
        poner("block.water.ambient", f, 0.55, "ambiente")
    # --- cae al agua: salpicadura al entrar, nada por la columna, golpe al fondo, rebote y vadeo
    poner("entity.generic.splash", f_baja + 12, 1.0, "golpes")
    for f in range(f_baja + 22, f_choque - 6, 14):
        poner("entity.generic.swim", f, 0.5, "golpes")
    poner("entity.player.splash.high_speed", f_choque, 1.0, "golpes")
    poner("entity.generic.splash", f_aterriza, 0.7, "golpes")
    for f in range(f_aterriza + 4, f_borde, 8):
        poner("entity.generic.swim", f, 0.4, "golpes")
    poner("entity.generic.splash", f_borde, 0.6, "golpes")                               # salta fuera del agua
    # --- aterriza en el suelo seco, trota y se sacude
    poner("entity.wolf.shake", f_seco + 1, 1.0, "voces")
    # --- camina por piedra hacia Alfred: un sonido por cada apoyo real de las cuatro patas
    rig = ob.get("Dog_001_rig")
    if rig and f_ruta_ini and f_lanza:
        nombres = m.huesos_apoyo(rig)
        colas = {nombre: rig.pose.bones[nombre] for nombre in nombres}
        datos = m.muestrear(bpy.context, f_ruta_ini, f_lanza,
                            lambda: {nombre: rig.matrix_world @ hueso.tail for nombre, hueso in colas.items()})
        series = {nombre: [(frame, muestra[nombre].copy()) for frame, muestra in datos] for nombre in nombres}
        for frame, _hueso in m.detectar_pasos(series, p.umbral, p.lev_min, p.dist_min, p.hueco):
            poner("block.stone.step", frame, 0.55, "pasos")
    # --- Jerry suelta el cubo y este golpea a Alfred
    if f_rel:
        poner("entity.player.attack.sweep", f_rel, 0.8, "objetos")
    if f_golpe:
        poner("entity.player.attack.strong", f_golpe, 0.75, "golpes")
    # --- Alfred se levanta: solo el roce de la ropa (los pasos sobre piedra sonaban a picar)
    poner("item.armor.equip_generic", f_levanta + 4, 0.6, "objetos")
    poner("item.armor.equip_generic", f_levanta + 72, 0.5, "objetos")
    f_ant = int(ob["alfred"].get("f_antorcha", 0))                                  # Alfred planta la antorcha (alfred_coloca_antorcha.py)
    if f_ant:
        poner("block.wood.place", f_ant, 0.9, "objetos")
    # Conserva los ajustes de mezcla aprobados: agua -30 %, chapoteos de la caida -40 %.
    for tira in [t for t in m._strips(ed) if t.name.startswith(m.PREFIJO) and t.get("mcsnd_origen") == ORIGEN]:
        nombre = tira.name.lower()
        factor = 0.60 if "splash" in nombre else (0.70 if "water" in nombre or "swim" in nombre else None)
        if factor is not None:
            base = float(tira.get("volumen_antes_reduccion_usuario", tira.volume))
            tira["volumen_antes_reduccion_usuario"] = base
            tira["factor_volumen_usuario"] = factor
            tira.volume = base * factor
    sc.frame_set(sc.frame_current)
    return puestos
