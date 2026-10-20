# -*- coding: utf-8 -*-
"""Sonidos de Minecraft para alfred_cae_estalagmita.py (pico en la piedra, bloque que se rompe, caida, dolor, herramientas que rebotan).
Usa el add-on Alfred Sonidos (tiras SND_ en el editor de secuencias). Uso en Blender: exec(open(ruta).read());  sonorizar()
"""
import bpy, importlib.util, sys

ADDON = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py"
GOLPES = [10, 26, 42, 58]
F_ROMPE = 58


def cargar_addon():
    m = sys.modules.get("alfred_sonidos_local")
    if m is None:
        spec = importlib.util.spec_from_file_location("alfred_sonidos_local", ADDON)
        m = importlib.util.module_from_spec(spec)
        sys.modules["alfred_sonidos_local"] = m
        spec.loader.exec_module(m)
        m.register()
    return m


def rebotes(ob, f0, f1, minimo=0.02):
    """frames en que la herramienta toca el suelo (minimos de altura) y su velocidad de impacto (m/s)"""
    sc = bpy.context.scene
    z = []
    for f in range(f0 - 1, f1 + 2):
        sc.frame_set(f)
        z.append(ob.matrix_world.translation.z)
    out = []
    for i in range(1, len(z) - 1):
        v_in = (z[i] - z[i - 1]) * 24
        if v_in < -0.5 and z[i] <= z[i + 1] + 1e-6:
            out.append((f0 - 1 + i, -v_in))
    return out


def sonorizar(f_imp=None, f_fin=None):
    m = cargar_addon()
    sc = bpy.context.scene
    raiz = bpy.data.objects["alfred"]
    f_imp = f_imp or int(raiz.get("f_imp", 83))
    f_fin = f_fin or int(raiz.get("f_fin", 143))
    f_at, f_tu = int(raiz.get("f_aterriza", 0)), int(raiz.get("f_tumba", 0))
    p = sc.mcsnd
    m.indice(p, forzar=True)
    ed = sc.sequence_editor or sc.sequence_editor_create()
    for t in [t for t in m._strips(ed) if t.name.startswith(m.PREFIJO) and "alfred_cae" in t.get("mcsnd_origen", "")]:
        m._strips(ed).remove(t)
    rng = m.rng_de(p)
    puestos = []

    def poner(evento, frame, vol=1.0, grupo="golpes", archivo=None):
        rutas = m.rutas_de(p, evento)
        if archivo:
            rutas = [r for r in rutas if r[0].endswith(archivo)] or rutas
        if not rutas:
            print("sin sonido:", evento)
            return
        t = m.colocar(bpy.context, p, rutas, frame, grupo, evento.replace(".", "_"), vol, 0, rng)
        if t:
            t["mcsnd_origen"] = "alfred_cae"
            puestos.append((t.name, frame))

    for g, vol in zip(GOLPES[:-1], (0.55, 0.7, 0.85)):                 # picando: lascas de piedra (el "hit" del juego es el mismo audio que los pasos, por eso sonaba a caminar)
        poner("block.stone.break", g, vol)
    poner("block.stone.break", F_ROMPE, 1.0)                           # el cuarto golpe rompe el bloque del techo
    poner("block.stone.fall", F_ROMPE + 8, 0.6)                        # los trozos caen
    poner("entity.generic.big_fall", f_imp, 1.0)                       # el cuerpo contra la estalagmita
    for nombre in ("stone_pickaxe", "stone_axe"):                      # herramientas contra el suelo: golpe sordo y grave (packed_mud), cada rebote mas suave
        ob = bpy.data.objects[nombre]
        for i, (f, v) in enumerate([r for r in rebotes(ob, f_imp, f_fin) if r[0] > f_imp + 3]):   # el primer minimo es solo el soltarse de la mano
            poner("block.packed_mud.fall", f, 1.6 * min(1.0, v / 6.0) * (0.85 ** i), "objetos")
    if f_at:                                                           # cae al suelo despues de resbalar: golpe grave al aterrizar y al desplomarse
        poner("entity.generic.big_fall", f_at, 1.0)                    # el mismo sonido que al caer sobre la estalagmita
        poner("entity.generic.big_fall", f_tu, 0.6)
    sc.frame_set(1)
    return puestos
