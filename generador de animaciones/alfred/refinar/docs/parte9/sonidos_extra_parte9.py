# -*- coding: utf-8 -*-
"""Parte 9: sonidos de Minecraft que faltaban (add-on `alfred_sonidos`), EJECUTAR DESPUES de `alfred_pan_flechas_cae_parte9.py` y del esqueleto
(el script de Alfred borra todas las tiras SND_) y antes de `ducking_voces.py`. Repetible: borra solo sus propias etiquetas.
- Esqueleto: disparos con `entity.skeleton.shoot` (reemplaza las tiras `entity.arrow.shoot` si el script de Alfred era anterior), traqueteo `entity.skeleton.ambient`,
  susto en f522, pasos al girar y al huir corriendo (`entity.skeleton.step` cada media zancada, bajando de volumen al alejarse).
- Jerry (SIN sonidos de lobo, a pedido): se quita el sombrero (`item.armor.equip_leather`), el sombrero cae al suelo (`block.wool.place`).
- Alfred: caida fuerte sobre la piedra (`entity.player.big_fall` + `block.stone.hit`) y roce del cuerpo contra la piedra en cada espasmo (`block.stone.step`, bajo)."""
import bpy, sys, random, importlib.util
sc = bpy.context.scene
m = sys.modules.get("alfred_sonidos")
if m is None:
    sp = importlib.util.spec_from_file_location("alfred_sonidos", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py"); m = importlib.util.module_from_spec(sp); sys.modules["alfred_sonidos"] = m; sp.loader.exec_module(m)
if not hasattr(sc, 'mcsnd'): m.register()
p_ = sc.mcsnd; ed = sc.sequence_editor_create(); S_ = m._strips(ed); rng = random.Random(19)
DISP = list(sc.get("p9_disparos", [152, 230, 316, 398])); F_SUELO = int(sc.get("p9_f_suelo", 376)); FIN = 700
T_SUSTO = 522; T_GIRA = 541; T_CORRE = 547
EV = []
# ---- esqueleto ----
for f in (40, 105, 262, 352, 470): EV.append((f, 'entity.skeleton.ambient', 'objetos', 0.55, 'esqueleto_ambiente'))
EV.append((T_SUSTO, 'entity.skeleton.hurt', 'objetos', 0.8, 'esqueleto_susto'))
for f in (T_GIRA + 1, T_GIRA + 4): EV.append((f, 'entity.skeleton.step', 'pasos', 0.6, 'esqueleto_paso'))
f, k = float(T_CORRE + 2), 0
while f < FIN:
    EV.append((int(f), 'entity.skeleton.step', 'pasos', max(0.15, 0.75 - 0.0045 * (f - T_CORRE)), 'esqueleto_paso')); f += 5.5
for t in [t for t in S_ if t.name.startswith(('SND_alfred_flecha_disparo', 'SND_jerry_flecha_disparo'))]: S_.remove(t)      # el disparo es del ESQUELETO
for i, d in enumerate(DISP): EV.append((d, 'entity.skeleton.shoot', 'objetos', 0.6, 'esqueleto_dispara'))
# ---- Jerry ----
EV += [(426, 'item.armor.equip_leather', 'objetos', 0.6, 'jerry_quita_sombrero'), (438, 'block.wool.place', 'objetos', 0.5, 'jerry_sombrero_suelo')]
# ---- Alfred ----
EV += [(F_SUELO, 'entity.player.big_fall', 'golpes', 0.8, 'alfred_caida_fuerte'), (F_SUELO, 'block.stone.hit', 'golpes', 0.6, 'alfred_cae_piedra')]
rng_e = random.Random(77); f_ = F_SUELO + 8; ESP = []                                       # MISMOS espasmos que alfred_pan_flechas_cae_parte9.py (semilla 77)
NOMS_E = ["RightUpArm_alfred", "LeftUpArm_alfred", "Rightelbow_alfred", "Leftelbow_alfred", "RightUpLeg_alfred", "LeftUpLeg_alfred", "Rightknee_alfred", "Leftknee_alfred", "Spine1_alfred", "Neck_alfred"]
while f_ < FIN - 6:
    a = rng_e.uniform(0.5, 1.0); rng_e.sample(NOMS_E, 3); [rng_e.uniform(-1, 1) for _ in range(3)]; ESP.append((f_, a))
    f_ += rng_e.randint(9, 26) if f_ < F_SUELO + 120 else rng_e.randint(18, 40)
for f0, a in ESP: EV.append((f0 + 1, 'block.stone.step', 'golpes', 0.18 + 0.2 * a, 'alfred_espasmo'))
# ---- colocar ----
ETQ = {e[4] for e in EV} | {'jerry_gime', 'jerry_jadeo'}                                # (los de lobo se quitaron a pedido)
for t in [t for t in S_ if t.name.startswith('SND_') and t.name[4:].rsplit('_', 1)[0] in ETQ]: S_.remove(t)
falt = set(); n = 0
for f, ev, g, v, et in sorted(EV):
    r = m.rutas_de(p_, ev)
    if not r: falt.add(ev); continue
    m.colocar(bpy.context, p_, r, int(f), g, et, v, 0, rng, False); n += 1
print("SONIDOS EXTRA: %d tiras; faltan %s" % (n, sorted(falt)))
