# -*- coding: utf-8 -*-
"""Parte 11: SONIDOS de Minecraft del tramo del PAN (add-on alfred_sonidos):
  - PALOMA: aleteos (parrot.fly) mientras vuela y mas seguidos/fuertes mientras forcejea, arrullos (parrot.ambient), despegue al ganar (bat.takeoff);
  - ALFRED: saca el pan de la espalda (armor.equip_generic), tirones del forcejeo (player.attack.sweep), el tiron final que lo lanza
    (player.attack.knockback + silbido), el golpe contra el agua (player.splash.high_speed + generic.splash) y el chapoteo mientras flota;
  - JERRY con su comida: olfateos (fox.sniff), el pescado al moverlo con el hocico o la pata (cod.flop) y sus pasos al levantar la pata.
Tiempos de `p11_tiempos` (pan_*) y `p11_jerry_observa`. Cada tira lleva `mic_emisor` (la paloma, Alfred, Jerry o el pescado).
Repetible: borra sus propias tiras (SND_p11_paloma_*, SND_p11_pan_*, SND_p11_jerry_comida_*). Despues aplica el MICROFONO (ultimo paso)."""
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

sc = bpy.context.scene; T = sc["p11_tiempos"]; JO = sc.get("p11_jerry_observa", {}); rng = random.Random(55)
m = sys.modules.get("alfred_sonidos")
if m is None:
    sp = importlib.util.spec_from_file_location("alfred_sonidos", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py")
    m = importlib.util.module_from_spec(sp); sys.modules["alfred_sonidos"] = m; sp.loader.exec_module(m)
if not hasattr(sc, "mcsnd"): m.register()
if not sc.mcsnd.items: bpy.ops.mcsnd.indexar()
p_ = sc.mcsnd; ed = sc.sequence_editor_create(); S_ = m._strips(ed)
for t in [t for t in S_ if t.name.startswith(("SND_p11_paloma", "SND_p11_pan", "SND_p11_jerry_comida"))]: S_.remove(t)
_borrar_curvas_de_tiras(sc, ("SND_p11_paloma", "SND_p11_pan", "SND_p11_jerry_comida"))

PAL = "pigeon_1"; ALF = "alfred"; JER = "jerry_sin_armadura"; PEZ = "pescado_fogata_jerry"
SACA, ENTRA, LLEGA, GANA, CAE, TIRON = (int(T[k]) for k in ("pan_saca", "pan_entra", "pan_llega", "pan_gana", "pan_cae", "pan_tiron"))
FIN = sc.frame_end
EV = []                                                                       # (frame, evento, grupo, volumen, etiqueta, emisor)
# ---- paloma ----
f = ENTRA + 2
while f < GANA + 70:                                                          # aleteos: cada 8 frames volando, cada 6 forcejeando
    forcejea = LLEGA <= f < GANA
    EV.append((f + rng.randint(-1, 1), "entity.chicken.step", "objetos", 1.0 if forcejea else 0.85, "p11_paloma_aleteo", PAL))   # aleteo = sonido del pollo
    f += 4 if forcejea else 5
for f in (ENTRA + 14, LLEGA - 3, LLEGA + 22, LLEGA + 50):
    EV.append((f, "entity.parrot.ambient", "voces", 0.7, "p11_paloma_arrullo", PAL))
EV.append((GANA, "entity.bat.takeoff", "objetos", 0.7, "p11_paloma_despega", PAL))
EV.append((GANA + 3, "entity.parrot.ambient", "voces", 0.7, "p11_paloma_gana", PAL))
# ---- Alfred y el pan ----
EV.append((SACA - 2, "item.armor.equip_generic", "objetos", 0.6, "p11_pan_saca", ALF))
for k in range(LLEGA + TIRON // 4, GANA - 4, TIRON):                          # cada tiron del forcejeo (cuando cambia de lado)
    EV.append((k, "entity.player.attack.sweep", "objetos", 0.35, "p11_pan_tiron", ALF))
EV.append((GANA, "entity.player.attack.knockback", "golpes", 0.8, "p11_pan_lanzado", ALF))
EV.append((GANA + 4, "entity.player.attack.sweep", "objetos", 0.9, "p11_pan_vuela", ALF))
EV.append((GANA + 12, "entity.player.attack.sweep", "objetos", 0.7, "p11_pan_vuela", ALF))       # silba en el aire
EV.append((CAE + 2, "entity.player.splash.high_speed", "golpes", 1.4, "p11_pan_cae_agua", ALF))  # golpe contra el agua
EV.append((CAE + 4, "entity.generic.splash", "objetos", 1.1, "p11_pan_salpica", ALF))
EV.append((CAE + 10, "entity.player.splash", "objetos", 0.8, "p11_pan_salpica", ALF))
EV.append((CAE + 18, "block.water.ambient", "ambiente", 0.7, "p11_pan_agua", ALF))
f = CAE + 14
while f < FIN - 6:                                                            # chapoteo mientras flota (el agua lo mece)
    EV.append((f, "entity.player.swim", "objetos", 0.6, "p11_pan_flota", ALF)); f += rng.randint(14, 22)
# ---- Jerry con su comida ----
for f in JO.get("olfatea", []): EV.append((int(f) + 1, "entity.fox.sniff", "voces", 0.6, "p11_jerry_comida_huele", JER))
for f in JO.get("empujones", []): EV.append((int(f) + 2, "entity.cod.flop", "objetos", 0.5, "p11_jerry_comida_empuja", PEZ))
for f in JO.get("patas", []):
    EV.append((int(f) - 7, "entity.wolf.step", "pasos", 0.5, "p11_jerry_comida_pata", JER))
    EV.append((int(f) + 2, "entity.cod.flop", "objetos", 0.5, "p11_jerry_comida_mueve", PEZ))
    EV.append((int(f) + 13, "entity.wolf.step", "pasos", 0.45, "p11_jerry_comida_pata", JER))

n_ok = 0; falt = set()
techo = False; p_.techo_voces = False      # techo de voces APAGADO en esta escena: el microfono de camara maneja los niveles                               # estos efectos no se pisan con voces: sin techo (si no quedaban a ~0.005 de volumen)
for f, ev, g, v, et, emisor in sorted(EV, key=lambda x: x[0]):
    r = m.rutas_de(p_, ev)
    if not r: falt.add(ev); continue
    t = m.colocar(bpy.context, p_, r, int(f), g, et, v, 0, rng, False)
    if t is not None: n_ok += 1; t["mic_emisor"] = emisor
print("SONIDOS PALOMA / PAN / JERRY COMIDA: %d tiras; faltan %s" % (n_ok, sorted(falt)))
p_.techo_voces = techo
