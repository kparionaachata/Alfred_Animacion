# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: sonidos de Jerry caminando por el tunel (pasos sobre piedra) y de soltar el pico (jerry_llega_salida.py).
Usa el add-on Alfred Sonidos; etiqueta mcsnd_origen = "jerry_salida". Uso en Blender: exec(open(ruta).read()); sonorizar()
Los frames se leen del movimiento real de `jerry` y `jerry_pico`."""
import bpy, importlib.util, sys

ADDON = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py"
ORIGEN = "jerry_salida"
F_INI, PASO = 180, 7                                   # empieza a caminar en F_INI; un paso cada PASO frames (ciclo rapido)


def cargar_addon():
    m = sys.modules.get("alfred_sonidos_local")
    if m is None:
        spec = importlib.util.spec_from_file_location("alfred_sonidos_local", ADDON)
        m = importlib.util.module_from_spec(spec)
        sys.modules["alfred_sonidos_local"] = m
        spec.loader.exec_module(m)
        m.register()
    return m


def _frames_mov(ob, eps, a=F_INI - 5, b=360):
    sc = bpy.context.scene
    prev, res = None, []
    for f in range(a, b):
        sc.frame_set(f)
        l = ob.matrix_world.translation.copy()
        if prev is not None and (l - prev).length > eps:
            res.append(f)
        prev = l
    return res


def sonorizar():
    m = cargar_addon()
    sc = bpy.context.scene
    O = bpy.data.objects
    guardado = sc.frame_current
    camina = _frames_mov(O["jerry"], 1e-4)
    pico = _frames_mov(O["jerry_pico"], 1e-3)
    sc.frame_set(guardado)
    f_ini, f_fin = camina[0], camina[-1]
    f_suelta = pico[-1]                                # el pico llega al suelo
    p = sc.mcsnd
    m.indice(p, forzar=True)
    ed = sc.sequence_editor or sc.sequence_editor_create()
    for t in [t for t in m._strips(ed) if t.name.startswith(m.PREFIJO) and t.get("mcsnd_origen") == ORIGEN]:
        m._strips(ed).remove(t)
    rng = m.rng_de(p)
    puestos = []

    def poner(evento, frame, vol, grupo):
        rutas = m.rutas_de(p, evento)
        if not rutas:
            print("sin sonido:", evento)
            return
        t = m.colocar(bpy.context, p, rutas, int(frame), grupo, evento.replace(".", "_"), vol, 0, rng)
        if t:
            t["mcsnd_origen"] = ORIGEN
            puestos.append((t.name, int(frame)))
    for i, f in enumerate(range(f_ini + 3, f_fin + 1, PASO)):
        break                                              # sin pisadas de Jerry (pedido del usuario)
        u = (f - f_ini) / max(1, f_fin - f_ini)                                           # viene de lejos: el paso crece al acercarse
        poner("block.stone.step", f, 0.5 * (0.08 + 0.75 * u ** 1.5 + 0.05 * (i % 2)), "pasos")   # la mitad (pedido del usuario)
    poner("block.stone.hit", f_suelta, 0.8, "objetos")                                    # el pico cae al suelo
    sc.frame_set(guardado)
    return dict(pasos=len([x for x in puestos if "step" in x[0]]), f_ini=f_ini, f_fin=f_fin, f_suelta=f_suelta)
