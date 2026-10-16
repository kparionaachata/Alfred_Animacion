# -*- coding: utf-8 -*-
"""Parte 10: SONIDOS de Minecraft (add-on `alfred_sonidos`) de `jerry_arrastra_alfred_parte10.py` (ejecutar DESPUES; repetible: borra sus propias tiras SND_p10_*).
SIN sonidos de lobo (a pedido) y sin voces.
  - en cada TIRON: el cuerpo de Alfred raspa el suelo (`block.gravel.step` dentro del tunel, `block.grass.step` afuera) y un paso suave de Jerry;
  - las CACHETADAS: `entity.player.attack.weak` en el contacto (f266 y f286);
  - al LEVANTARSE Alfred: roce al sentarse y pasos en el pasto al ponerse de pie."""
import bpy, sys, random, importlib.util
sc = bpy.context.scene
m = sys.modules.get("alfred_sonidos")
if m is None:
    sp = importlib.util.spec_from_file_location("alfred_sonidos", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py"); m = importlib.util.module_from_spec(sp); sys.modules["alfred_sonidos"] = m; sp.loader.exec_module(m)
if not hasattr(sc, 'mcsnd'): m.register()
if not sc.mcsnd.items: bpy.ops.mcsnd.indexar()
p_ = sc.mcsnd; ed = sc.sequence_editor_create(); S_ = m._strips(ed); rng = random.Random(10)
T_MUERDE, N, TIRON, X0, PASO = 10, 16, 14, -110.1, 0.35; T_PARA = T_MUERDE + N * TIRON
TT = sc.get("p10_tiempos", {}); CONTACTOS = list(TT.get("CONTACTOS", [266, 288])); T_LEV = int(TT.get("T_LEV", T_PARA + 104))     # tiempos del arrastre
EV = []
for i in range(N):
    f = T_MUERDE + i * TIRON + 4; x = X0 + (i + 0.5) * PASO
    EV.append((f, 'block.gravel.step' if x < -106.5 else 'block.grass.step', 'pasos', 0.35, 'p10_alfred_arrastre'))
    EV.append((f + 2, 'block.gravel.step' if x < -106.0 else 'block.grass.step', 'pasos', 0.15, 'p10_jerry_paso'))
for c in CONTACTOS: EV.append((c, 'entity.player.attack.weak', 'golpes', 0.8, 'p10_cachetada'))
if "T_FLECHA" in TT:                                                                         # duerme de costado, se medio levanta, FLECHA al pecho, arrastre a la izquierda y el sombrero
    tf = int(TT["T_FLECHA"])
    EV += [(int(TT["T_SIENTA0"]) + 6, 'block.grass.step', 'pasos', 0.3, 'p10_alfred_sienta'),
           (tf - 10, 'entity.arrow.shoot', 'objetos', 0.5, 'p10_flecha_disparo'), (tf, 'entity.arrow.hit', 'golpes', 1.0, 'p10_flecha_impacto'), (tf + 1, 'entity.player.hurt', 'voces', 0.85, 'p10_alfred_quejido'),
           (int(TT["T_CAE1"]), 'entity.player.attack.strong', 'golpes', 0.6, 'p10_alfred_cae')]
    for i in range(int(TT["N2"])):
        f = int(TT["T_ARR0"]) + i * TIRON + 4; EV += [(f, 'block.grass.step', 'pasos', 0.35, 'p10_alfred_arrastre2'), (f + 2, 'block.grass.step', 'pasos', 0.15, 'p10_jerry_paso2')]
    EV.append((int(TT["T_SOMB_AG"]), 'item.armor.equip_leather', 'objetos', 0.6, 'p10_jerry_sombrero'))
    for g in TT["GOLPES_S"]: EV.append((int(g), 'block.wool.hit', 'golpes', 0.9, 'p10_golpe_sombrero'))
    if "T_PONE" in TT: EV.append((int(TT["T_PONE"]), 'item.armor.equip_leather', 'objetos', 0.6, 'p10_jerry_pone_sombrero'))
    if "T_LEV2" in TT:
        for k, v in ((20, 0.3), (45, 0.3), (62, 0.45), (74, 0.5), (88, 0.45)): EV.append((int(TT["T_LEV2"]) + k, 'block.grass.step', 'pasos', v, 'p10_alfred_levanta2'))
else:
    for k, v in ((20, 0.3), (45, 0.3), (62, 0.45), (74, 0.5), (88, 0.45)): EV.append((T_LEV + k, 'block.grass.step', 'pasos', v, 'p10_alfred_levanta'))
for t in [t for t in S_ if t.name.startswith('SND_p10_')]: S_.remove(t)
n = 0; falt = set()
for f, ev, g, v, et in sorted(EV):
    r = m.rutas_de(p_, ev)
    if not r: falt.add(ev); continue
    m.colocar(bpy.context, p_, r, int(f), g, et, v, 0, rng, False); n += 1
print("SONIDOS PARTE 10: %d tiras; faltan %s" % (n, sorted(falt)))
