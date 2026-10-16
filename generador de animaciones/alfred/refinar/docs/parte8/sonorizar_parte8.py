# -*- coding: utf-8 -*-
"""Parte 8 - SONIDOS DEL JUEGO sincronizados con las animaciones (add-on `alfred_sonidos`: sonidos originales de Minecraft de `sonidos/`). Los eventos se LEEN de las animaciones:
 - PASOS de Alfred y Jerry: tramos en que su empty avanza en el plano con la z entera (no en los saltos); un paso cada PASO_A / PASO_J frames; superficie = lo que hay justo debajo
   (rayo hacia abajo: bloques / mallas de piedra -> `block.stone.step`, tierra -> `block.gravel.step`, que es el sonido de la tierra en Minecraft).
 - PICAR: cada bloque de los tuneles (`tunel_bloque_*`, `tunel_jerry_bloque_*`) que se rompe: los golpes son los frames en que su escala baja (claves de `_romper_claves`) y la rotura el
   frame con escala 0.857; piedra -> `block.stone.hit` / `block.stone.break`, tierra -> `block.gravel.hit` / `.break`. Dueno: Alfred (coleccion `tunel`) o Jerry (`tunel_jerry`).
 - MINI BLOQUES absorbidos (`tunel_item_*`, `tunel_jerry_item_*`): `entity.item.pickup` cuando su escala llega a 0.
 - HERRAMIENTA: Alfred saca / guarda el pico (cambios de la influencia `Mano` de `stone_pickaxe`) -> `item.armor.equip_generic`; Jerry agarra su pico con la boca (f28).
 - ATERRIZAJES de los saltos (la z del empty termina un cambio de 1 m): `block.stone.fall`.
 - EVENTOS de la historia (lista EV): sentarse / pararse de Jerry, lanzar el pico, golpe en la cabeza de Alfred, el pico cae al piso, antorcha, flecha (disparo, impacto, quejido), ambiente de cueva.
Repetible: borra antes todas las tiras `SND_` de la escena. Al final `ducking_voces.py` (ducking bajo las voces + distancia a la camara). Ejecutar con `bpy.app.timers.register` (tarda)."""
import bpy, sys, importlib.util, random, math
from mathutils import Vector

sc = bpy.context.scene
m = sys.modules.get("alfred_sonidos")
if m is None:
    spec = importlib.util.spec_from_file_location("alfred_sonidos", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py"); m = importlib.util.module_from_spec(spec); sys.modules["alfred_sonidos"] = m; spec.loader.exec_module(m)
if not sc.mcsnd.items: bpy.ops.mcsnd.indexar()
p = sc.mcsnd; ed = sc.sequence_editor; S = m._strips(ed); rng = random.Random(8)
for t in [t for t in S if t.name.startswith('SND_')]: S.remove(t)
FIN = sc.frame_end; PASO_A = 10; PASO_J = 7; LOG = {}
def poner(f, ev, grupo, vol, et):
    r = m.rutas_de(p, ev)
    if r: m.colocar(bpy.context, p, r, int(f), grupo, et, vol, 0, rng, False); LOG[et] = LOG.get(et, 0) + 1
def curvas(o): return {(fc.data_path, fc.array_index): fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves}
A = bpy.data.objects['alfred']; J = bpy.data.objects['jerry']; FA_, FJ_ = curvas(A), curvas(J)
def pos(fc, f): return Vector((fc[('location', 0)].evaluate(f), fc[('location', 1)].evaluate(f), fc[('location', 2)].evaluate(f)))

# ---------- superficie bajo los pies ----------
OCU = [o for o in bpy.data.objects if o.type == 'MESH' and (o.name.endswith('_alfred') or o.name.endswith('_jerry') or o.name in ('stone_pickaxe', 'tunel_jerry_pico', 'flecha_alfred'))]
def superficie(p_, f):
    sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); o_ = Vector((p_.x, p_.y, p_.z + 0.3))
    for _ in range(4):
        ok, loc, nor, i, ob, mt = sc.ray_cast(dg, o_, Vector((0, 0, -1)), distance=2.0)
        if not ok: return 'stone'
        ob = ob.original
        if ob in OCU: o_ = loc + Vector((0, 0, -0.01)); continue
        n = ob.name.lower()
        if 'tierra' in n or n in ('dirt', 'a.001', 'gravel') or 'dirt' in n: return 'gravel'
        return 'stone'
    return 'stone'

# ---------- pasos ----------
def pasos(fc, f0, f1, cada, dueno, vol, umbral=0.012):
    ult = -99; n = 0
    for f in range(f0 + 1, f1 + 1):
        a, b = pos(fc, f - 1), pos(fc, f); v = math.hypot(b.x - a.x, b.y - a.y)
        if v > umbral and abs(b.z - round(b.z)) < 0.02 and abs(a.z - b.z) < 0.01 and f - ult >= cada:
            poner(f, 'block.%s.step' % superficie(b, f), 'pasos', vol, '%s_paso' % dueno); ult = f; n += 1
    return n
pasos(FA_, 1, FIN, PASO_A, 'alfred', p.paso_volumen)
pasos(FJ_, 1, FIN, PASO_J, 'jerry', p.paso_volumen * 0.7)
for f in (2376, 2382, 2388): poner(f, 'block.stone.step', 'pasos', p.paso_volumen * 0.5, 'jerry_paso_giro')       # gira en el sitio dando pasitos

# ---------- aterrizajes de los saltos ----------
for fc, dueno in ((FA_, 'alfred'), (FJ_, 'jerry')):
    enaire = False; zini = None
    for f in range(2, FIN + 1):
        z0, z1 = fc[('location', 2)].evaluate(f - 1), fc[('location', 2)].evaluate(f)
        if abs(z1 - z0) > 0.005:
            if not enaire: zini = z0
            enaire = True
        elif enaire:
            if abs(z1 - round(z1)) < 0.02 and abs(z1 - zini) > 0.5: poner(f, 'block.stone.fall', 'golpes', 0.55, '%s_aterriza' % dueno)   # solo SALTOS de 1 m (no al sentarse / pararse)
            enaire = False

# ---------- picar: golpes y roturas ----------
for col, dueno in (('tunel', 'alfred'), ('tunel_jerry', 'jerry')):
    c = bpy.data.collections.get(col)
    if not c: continue
    for o in c.objects:
        if not (o.name.startswith('tunel_bloque_') or o.name.startswith('tunel_jerry_bloque_')) or not o.animation_data or not o.animation_data.action: continue
        sx = curvas(o).get(('scale', 0))
        if sx is None: continue
        ks = sorted((k.co.x, k.co.y) for k in sx.keyframe_points); mat = 'stone' if 'piedra' in o.name else 'gravel'
        rotura = next((fa for fa, va in ks if abs(va - 0.857) < 0.01), None)
        golpes = [fa for (fa, va), (fb, vb) in zip(ks, ks[1:]) if fb - fa < 1.5 and vb < va - 0.01 and va > 0.9 and (rotura is None or fa < rotura - 1)]   # sin el frame previo a la rotura (es el mismo golpe final)
        for g in golpes: poner(g, 'block.%s.hit' % mat, 'golpes', 0.7, '%s_pica' % dueno)
        if rotura is not None: poner(rotura, 'block.%s.hit' % mat, 'golpes', 0.75, '%s_pica' % dueno); poner(rotura + 1, 'block.%s.break' % mat, 'golpes', 0.8, '%s_rompe' % dueno)

# ---------- mini bloques absorbidos ----------
for o in bpy.data.objects:
    if not (o.name.startswith('tunel_item_') or o.name.startswith('tunel_jerry_item_')) or not o.animation_data or not o.animation_data.action: continue
    sx = curvas(o).get(('scale', 0))
    if sx is None: continue
    cero = next((k.co.x for k in sx.keyframe_points if k.co.y < 0.01), None)
    if cero: poner(cero - 2, 'entity.item.pickup', 'objetos', 0.45, ('jerry' if 'jerry' in o.name else 'alfred') + '_recoge_item')

# ---------- herramientas ----------
pk = bpy.data.objects['stone_pickaxe']; im = curvas(pk).get(('constraints["Mano"].influence', 0))
if im:
    ks = sorted((k.co.x, k.co.y) for k in im.keyframe_points)
    for (fa, va), (fb, vb) in zip(ks, ks[1:]):
        if abs(vb - va) > 0.5: poner(fb, 'item.armor.equip_generic', 'objetos', 0.6, 'alfred_pico_' + ('saca' if vb > va else 'guarda'))
poner(28, 'item.armor.equip_generic', 'objetos', 0.5, 'jerry_agarra_pico')

# ---------- el pico de Jerry cae al piso despues del golpe ----------
pj = bpy.data.objects['tunel_jerry_pico']; fpj = curvas(pj); piso = 6.03; bote = []
for f in range(2031, min(FIN, 2100)):
    z0, z1, z2 = fpj[('location', 2)].evaluate(f - 1), fpj[('location', 2)].evaluate(f), fpj[('location', 2)].evaluate(f + 1)
    if z1 <= z0 and z1 <= z2 and z1 < piso + 0.25: bote.append(f)
for i, f in enumerate(bote[:3]): poner(f, 'block.stone.hit', 'golpes', 0.55 / (i + 1), 'alfred_pico_cae_piso')

# ---------- eventos de la historia ----------
EV = [(1903, 'block.wool.step', 'pasos', 0.55, 'jerry_se_sienta'), (2087, 'block.wool.step', 'pasos', 0.55, 'jerry_se_para'),
      (2009, 'entity.player.attack.sweep', 'objetos', 0.8, 'jerry_lanza_pico'),
      (2030, 'entity.player.attack.strong', 'golpes', 0.9, 'alfred_golpe_pico'), (2031, 'entity.player.hurt', 'voces', 0.75, 'alfred_quejido_pico'),
      (2398, 'block.wood.place', 'objetos', 0.8, 'alfred_antorcha'),
      (2522, 'entity.arrow.shoot', 'objetos', 0.55, 'alfred_flecha_disparo'), (2536, 'entity.arrow.hit_player', 'golpes', 0.9, 'alfred_flecha_impacto'),
      (2537, 'entity.player.hurt', 'voces', 0.85, 'alfred_quejido_flecha'),
      (600, 'ambient.cave', 'ambiente', 0.35, 'alfred_ambiente_cueva'), (1750, 'ambient.cave', 'ambiente', 0.35, 'alfred_ambiente_cueva')]                                                                       # (sin el de f2470: sonaba durante la flecha; quitado a pedido)
for f, ev, g, v, et in EV: poner(f, ev, g, v, et)

exec(open(r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/ducking_voces.py", encoding="utf-8").read(), {"__name__": "x"})
print("SONIDOS parte 8:", len([t for t in S if t.name.startswith('SND_')]), "tiras;", sorted(LOG.items()))
