# -*- coding: utf-8 -*-
"""Parte 11: SONIDOS de Jerry (nadar, salir del agua, sacudirse, pasos) y de la FOGATA (sonidos de Minecraft, add-on alfred_sonidos).
Ejecutar DESPUES de `jerry_nada_pescado_parte11.py` (usa sus tiempos `p11_jerry`). Repetible: borra sus propias tiras SND_p11_jerry_* y SND_p11_fogata_*.
Cada tira lleva `mic_emisor` (Jerry sin armadura o la fogata) para que el MICROFONO de camara la escuche desde ahi: aplicarlo despues (ultimo paso)."""
import bpy, sys, random, importlib.util


def _borrar_curvas_de_tiras(sc, prefijos):
    """al recrear una tira con el mismo nombre, Blender le deja las curvas de volumen/pan de la anterior (y el microfono las tomaria como
    originales): se borran las de las tiras de este script"""
    ad = sc.animation_data
    if not (ad and ad.action): return
    for l in ad.action.layers:
        for st in l.strips:
            for cb in st.channelbags:
                for fc in [fc for fc in cb.fcurves if any('["%s' % p in fc.data_path for p in prefijos)]: cb.fcurves.remove(fc)
    ad.action.update_tag(); sc.update_tag(); bpy.context.view_layer.update()     # si no, Blender sigue evaluando las curvas borradas

sc = bpy.context.scene; J = sc["p11_jerry"]; rng = random.Random(33)
m = sys.modules.get("alfred_sonidos")
if m is None:
    sp = importlib.util.spec_from_file_location("alfred_sonidos", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py")
    m = importlib.util.module_from_spec(sp); sys.modules["alfred_sonidos"] = m; sp.loader.exec_module(m)
if not hasattr(sc, "mcsnd"): m.register()
if not sc.mcsnd.items: bpy.ops.mcsnd.indexar()
p_ = sc.mcsnd; ed = sc.sequence_editor_create(); S_ = m._strips(ed)
for t in [t for t in S_ if t.name.startswith(("SND_p11_jerry", "SND_p11_fogata"))]: S_.remove(t)
_borrar_curvas_de_tiras(sc, ("SND_p11_jerry", "SND_p11_fogata"))

JERRY = "jerry_sin_armadura"; FOGATA = "campfire_log"
nado, salto, seca, camina, suelta = (tuple(J[k]) for k in ("nado", "salto", "seca", "camina", "suelta"))
EV = []                                                                     # (frame, evento, grupo, volumen, etiqueta, emisor)
for f in range(nado[0] + 6, nado[1] - 4, 20):                               # una brazada cada 20 frames (ciclo de nadar.py: 8 en 160)
    EV.append((f + rng.randint(-2, 2), "entity.generic.swim", "objetos", 0.55, "p11_jerry_nada", JERRY))
EV.append((salto[0] + 1, "entity.player.splash", "objetos", 0.7, "p11_jerry_sale_agua", JERRY))   # se impulsa fuera del agua
EV.append((salto[1] - 1, "entity.wolf.step", "pasos", 0.9, "p11_jerry_aterriza", JERRY))         # cae en la piedra
EV.append((seca[0] + 4, "entity.wolf.shake", "objetos", 0.9, "p11_jerry_sacude", JERRY))          # se sacude el agua
for f in range(camina[0] + 2, suelta[0] + 4, 8):                             # pasos hasta la fogata
    EV.append((f, "entity.wolf.step", "pasos", 0.8, "p11_jerry_paso", JERRY))
f = 1                                                                       # chisporroteo de la fogata toda la escena
while f < sc.frame_end:
    EV.append((f, "block.campfire.crackle", "ambiente", 0.5, "p11_fogata_crepita", FOGATA)); f += rng.randint(26, 48)

n_ok = 0; falt = set()
techo = False; p_.techo_voces = False      # techo de voces APAGADO en esta escena: el microfono de camara maneja los niveles                               # sin techo de voces: el techo los dejaba ~13 dB mas bajos de lo pedido
for f, ev, g, v, et, emisor in sorted(EV, key=lambda x: x[0]):
    r = m.rutas_de(p_, ev)
    if not r: falt.add(ev); continue
    t = m.colocar(bpy.context, p_, r, int(f), g, et, v, 0, rng, False)
    if t is not None: n_ok += 1; t["mic_emisor"] = emisor
print("SONIDOS JERRY + FOGATA: %d tiras; faltan %s" % (n_ok, sorted(falt)))
p_.techo_voces = techo
