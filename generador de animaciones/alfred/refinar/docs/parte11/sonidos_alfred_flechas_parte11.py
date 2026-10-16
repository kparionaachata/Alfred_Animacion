# -*- coding: utf-8 -*-
"""Parte 11: SONIDOS de Alfred sacandose las flechas y tirandolas al mar (sonidos de Minecraft, add-on alfred_sonidos).
Ejecutar DESPUES de `alfred_saca_flechas_parte11.py` (usa sus tiempos `p11_tiempos`). Repetible: borra sus propias tiras SND_p11_alfred_*.
Por cada flecha (pedido del usuario: un solo sonido al sacarla y uno de lanzar cualquier objeto):
  - al arrancarla: UN sonido (entity.arrow.hit);
  - al lanzarla: zumbido del brazo al lanzar un objeto (entity.player.attack.sweep; el 'throw' de Minecraft es el sonido del arco);
  - al caer al mar: chapuzon (entity.generic.splash) que suena DESDE LA FLECHA (propiedad mic_emisor), no desde Alfred.
Despues hay que aplicar el MICROFONO de camara (ultimo paso de la cadena): la distancia de cada sonido a la camara decide su volumen."""
import bpy, sys, random, importlib.util

sc = bpy.context.scene; TT = sc["p11_tiempos"]; rng = random.Random(21)
m = sys.modules.get("alfred_sonidos")
if m is None:
    sp = importlib.util.spec_from_file_location("alfred_sonidos", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py")
    m = importlib.util.module_from_spec(sp); sys.modules["alfred_sonidos"] = m; sp.loader.exec_module(m)
if not hasattr(sc, "mcsnd"): m.register()
if not sc.mcsnd.items: bpy.ops.mcsnd.indexar()
p_ = sc.mcsnd; ed = sc.sequence_editor_create(); S_ = m._strips(ed)
for t in [t for t in S_ if t.name.startswith("SND_p11_alfred")]: S_.remove(t)

FLECHAS = ("flecha_mano_izq", "flecha_mano_der", "flecha_pecho", "flecha_alfred", "flecha_entrepierna")
PER = 12; VUELO = 20                                                              # frames por vaiven y de vuelo de la flecha (los del script de la animacion)
EV = []                                                                           # (frame, evento, grupo, volumen, etiqueta, emisor)
LANZAR = "entity.player.attack.sweep"                                             # zumbido del brazo al lanzar (el "throw" generico de Minecraft usa el sonido del arco)
for n in FLECHAS:
    if n + "_m0" not in TT: continue
    m0, e0, rel = int(TT[n + "_m0"]), int(TT[n + "_e0"]), int(TT[n + "_rel"])
    EV.append((e0 + 4, "entity.arrow.hit", "golpes", 0.45, "p11_alfred_saca_flecha", None))         # UN solo sonido al sacarla (0.45 = -4 dB respecto a 0.7, pedido del usuario)
    EV.append((rel, LANZAR, "objetos", 0.8, "p11_alfred_lanza", None))                               # lanzar un objeto cualquiera
    EV.append((rel + VUELO, "entity.generic.splash", "objetos", 0.8, "p11_alfred_flecha_agua", n))

n_ok = 0; falt = set()
for f, ev, g, v, et, emisor in sorted(EV, key=lambda x: x[0]):
    r = m.rutas_de(p_, ev)
    if not r: falt.add(ev); continue
    t = m.colocar(bpy.context, p_, r, int(f), g, et, v, 0, rng, False)
    if t is not None:
        n_ok += 1
        if emisor: t["mic_emisor"] = emisor                                       # el microfono lo escucha desde la flecha en el agua
print("SONIDOS ALFRED FLECHAS: %d tiras; faltan %s" % (n_ok, sorted(falt)))
