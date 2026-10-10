# -*- coding: utf-8 -*-
"""Parte 7 - SONIDOS de la historia (pedido de Kebyn). Usa el add-on `alfred_sonidos` (carpeta `capitulos/capitulo_4/alfred_sonidos`, sonidos originales de Minecraft de `sonidos/`).
1) Automatico (`bpy.ops.mcsnd.sonorizar(modo="TODO")` con la escena recortada a f1-760): pasos de Alfred y del creeper por la superficie bajo el pie, contacto del cuerpo al sentarse / caer.
2) Se quitan los falsos positivos: tiras de `stone_axe` / `stone_shovel` (las herramientas que Alfred lleva en la espalda parecian lanzadas), pasos de lobo de Jerry (`wolf_step`: Jerry tiene voz propia y no lleva sonidos de lobo) y pasos del creeper desde f396 (eran el ajuste de los pies al cargar / caer).
3) Se anaden: pasos de Jerry (`block.grass.step`, cada 6 f al correr y 10 f al andar, sin los saltos) y los eventos de la historia (lista EV).
Las tiras van a los canales 10+ (`SND_<evento>_<frame>`); no hay voces de Voz Sync en la escena, por eso no hay ducking. Se ejecuta DENTRO de Blender: exec(open(RUTA, encoding='utf-8').read()); tarda ~25 s (si da timeout por MCP, llamarlo desde un temporizador `bpy.app.timers.register`)."""
import bpy, sys, importlib.util, random, math

sc = bpy.context.scene
m = sys.modules.get("alfred_sonidos")
if m is None:
    spec = importlib.util.spec_from_file_location("alfred_sonidos", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py"); m = importlib.util.module_from_spec(spec); sys.modules["alfred_sonidos"] = m; spec.loader.exec_module(m); m.register()
if not sc.mcsnd.items: bpy.ops.mcsnd.indexar()
p = sc.mcsnd; p.semilla = 7
fe = sc.frame_end
try:
    sc.frame_end = 760; bpy.ops.mcsnd.sonorizar(modo="TODO")                                       # 1) automatico
finally:
    sc.frame_end = fe
ed = sc.sequence_editor; S = m._strips(ed); rng = random.Random(11)
for t in [t for t in S if t.name.startswith('SND_') and (('stone_axe' in t.name) or ('stone_shovel' in t.name) or ('wolf_step' in t.name) or ('creeper' in t.name and 'step' in t.name and int(t.frame_final_start) >= 396))]: S.remove(t)     # 2)
def poner(f, ev, grupo, vol, et):
    r = m.rutas_de(p, ev)
    return m.colocar(bpy.context, p, r, f, grupo, et, vol, 0, rng, False) if r else None
def fc_eval(obj, idx, f):
    for l in obj.animation_data.action.layers:
        for s in l.strips:
            for cb in s.channelbags:
                for fc in cb.fcurves:
                    if fc.data_path == 'location' and fc.array_index == idx: return fc.evaluate(f)
def tramos(obj, f0, f1, thr):
    out = []; cur = None
    for f in range(f0, f1 + 1):
        v = math.hypot(fc_eval(obj, 0, f) - fc_eval(obj, 0, f - 1), fc_eval(obj, 1, f) - fc_eval(obj, 1, f - 1))
        if v > thr:
            if cur is None: cur = [f, f, v]
            else: cur[1] = f; cur[2] = max(cur[2], v)
        elif cur is not None and f - cur[1] > 4: out.append(tuple(cur)); cur = None
    if cur: out.append(tuple(cur))
    return out
J = bpy.data.objects['jerry']; CH = bpy.data.objects['chicken_1']
SALTOS = [(87, 101), (212, 240), (262, 276), (717, 731)]                                           # Jerry en el aire (sin pasos)
for a, b, vmax in tramos(J, 2, 760, 0.01):                                                         # 3) pasos de Jerry
    for f in range(a + 3, b, 6 if vmax > 0.1 else 10):
        if not any(x <= f <= y for x, y in SALTOS): poner(f, 'block.grass.step', 'pasos', p.paso_volumen, 'jerry_paso')
# (el pollo NO lleva pasos: se quitaron los `entity.chicken.step`, que sonaban como pitidos al caminar)
EV = [(182, 'entity.player.hurt', 'voces', 0.9, 'alfred_dolor_tobillo'), 
      (213, 'block.wool.step', 'pasos', 0.7, 'alfred_se_sienta'), (716, 'entity.player.hurt', 'voces', 0.9, 'alfred_dolor_tobillo_2'), (494, 'block.wool.step', 'pasos', 0.7, 'alfred_se_incorpora'), (507, 'block.wool.step', 'pasos', 0.6, 'alfred_empuja'), (522, 'block.wool.step', 'pasos', 0.6, 'alfred_de_pie'),
      (396, 'entity.creeper.primed', 'voces', 0.9, 'creeper_primed_1'), (440, 'entity.creeper.hurt', 'voces', 0.9, 'creeper_herido'), (449, 'entity.generic.big_fall', 'golpes', 0.8, 'creeper_cae'), (451, 'block.grass.fall', 'golpes', 0.4, 'creeper_rebote'), (668, 'entity.creeper.primed', 'voces', 0.9, 'creeper_primed_2'),
      (427, 'entity.chicken.hurt', 'voces', 0.7, 'pollo_atrapado'), (437, 'entity.player.attack.sweep', 'objetos', 0.8, 'alfred_lanza_pollo'), (440, 'entity.player.attack.weak', 'golpes', 0.9, 'pollo_golpea_creeper'), (441, 'entity.chicken.hurt', 'voces', 0.8, 'pollo_golpe_1'),
      (456, 'block.wood.hit', 'golpes', 0.9, 'pollo_choca_tronco'), (457, 'entity.chicken.hurt', 'voces', 0.8, 'pollo_golpe_2'), (554, 'entity.generic.small_fall', 'golpes', 0.7, 'pollo_cae_boca_abajo'), (560, 'block.grass.hit', 'golpes', 0.5, 'pollo_rebote_1'), (564, 'block.grass.hit', 'golpes', 0.4, 'pollo_rebote_2'), (567, 'block.grass.hit', 'golpes', 0.3, 'pollo_rebote_3'),
      (70, 'entity.chicken.ambient', 'ambiente', 0.5, 'pollo_cacarea'), (150, 'entity.chicken.ambient', 'ambiente', 0.5, 'pollo_cacarea'), (250, 'entity.chicken.ambient', 'ambiente', 0.5, 'pollo_cacarea'), (330, 'entity.chicken.ambient', 'ambiente', 0.5, 'pollo_cacarea'),
      (311, 'block.wool.step', 'pasos', 0.6, 'jerry_se_sienta'), (526, 'block.wool.step', 'pasos', 0.6, 'jerry_quita_patas'), (540, 'block.wool.step', 'pasos', 0.6, 'jerry_se_sienta_2'), (559, 'block.wool.step', 'pasos', 0.6, 'jerry_se_para'),
      (101, 'block.grass.fall', 'golpes', 0.5, 'jerry_aterriza'), (240, 'block.grass.fall', 'golpes', 0.5, 'jerry_aterriza'), (276, 'block.grass.fall', 'golpes', 0.5, 'jerry_aterriza'), (678, 'block.grass.fall', 'golpes', 0.5, 'jerry_aterriza_brinco'), (731, 'block.grass.fall', 'golpes', 0.5, 'jerry_aterriza')]
for f, ev, g, v, et in EV: poner(f, ev, g, v, et)
# la caida de Alfred (f187 y tres rebotes) suena IGUAL que el pollo al chocar con el tronco (f456): el mismo .ogg de `block.wood.hit`
tree = next(t for t in S if t.name.startswith('SND_pollo_choca_tronco_')); ruta_arbol = bpy.path.abspath(tree.sound.filepath)
for t in [t for t in S if t.name.startswith('SND_') and 'cuerpo_armature_' in t.name and 'grass_fall' in t.name]: S.remove(t)                     # el golpe automatico de su caida (pasto)
for f, v, et in ((187, 0.9, 'alfred_cae'), (192, 0.35, 'alfred_rebote_1'), (196, 0.25, 'alfred_rebote_2'), (199, 0.15, 'alfred_rebote_3')): m.colocar(bpy.context, p, [(ruta_arbol, 1.0)], f, 'golpes', et, v, 0, rng, False)
# segunda caida de Alfred (f720 y rebotes f726/730/733): el mismo sonido de madera; pasos de la carrera cojeando (f684-712, uno cada 7 f, izquierdo fuerte y derecho flojo); se quitan los pasos automaticos de la huida (>= f681)
for t in [t for t in S if t.name.startswith('SND_grass_step_armature_') and int(t.frame_final_start) >= 681]: S.remove(t)
for i, f in enumerate(range(684, 716, 7)): poner(f, 'block.grass.step', 'pasos', 0.55 if i % 2 == 0 else 0.3, 'alfred_paso_cojo')
for f, v, et in ((720, 0.9, 'alfred_cae_2'), (726, 0.35, 'alfred_rebote_2_1'), (730, 0.25, 'alfred_rebote_2_2'), (733, 0.15, 'alfred_rebote_2_3')): m.colocar(bpy.context, p, [(ruta_arbol, 1.0)], f, 'golpes', et, v, 0, rng, False)
print("Sonidos parte 7: %d tiras de sonido" % len([t for t in S if t.type == 'SOUND']))
