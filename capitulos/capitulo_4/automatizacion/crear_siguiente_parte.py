# -*- coding: utf-8 -*-
"""CREAR LA SIGUIENTE PARTE a partir del ULTIMO frame de animacion de los personajes de la parte anterior.
Uso (en segundo plano):
  blender.exe -b base_parte_N.blend --python crear_siguiente_parte.py -- <salida.blend> [frame] [fin_nuevo] [prefijo_sonidos]
  - frame: frame de la parte anterior que se congela (por defecto el final de la escena)
  - fin_nuevo: final de la escena nueva (por defecto 250)
  - prefijo_sonidos: las tiras de sonido/voz cuyo nombre lo contenga se quitan (por defecto "_p<N>_")
Que hace:
  1. Va al frame elegido y CONGELA a los personajes y sus objetos (raices con armadura y todo lo que cuelga de ellas, flechas, items, peces...):
     transformaciones, pose de TODOS los huesos, shape keys (ojos) y visibilidad. Luego les quita la animacion (acciones y NLA).
  2. Quita los sonidos y voces de la parte anterior (y sus curvas de volumen/paneo) y las propiedades de tiempos de esa parte (pN_*).
  3. La escena nueva empieza en el frame 1.
NO toca la CAMARA ni su foco (los maneja el usuario), ni el entorno animado (agua, fuego, cielo, luces)."""
import bpy, sys, re

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SALIDA = args[0]
sc = bpy.context.scene
FRAME = int(args[1]) if len(args) > 1 and args[1] != "-" else sc.frame_end
FIN_NUEVO = int(args[2]) if len(args) > 2 and args[2] != "-" else 250
m = re.search(r"base_parte_(\d+)", bpy.data.filepath)
N = int(m.group(1)) if m else 0
PREF = args[3] if len(args) > 3 else "_p%d_" % N
OCULTAR = [a for a in args[4].split(",")] if len(args) > 4 and args[4] else []     # raices que ya no deben verse (se fueron)

# ---- 1. que se congela: las raices de personaje (EMPTY sin padre con una armadura) y todo lo suyo + objetos animados sueltos que no son camara/entorno
raices = [o for o in sc.objects if o.parent is None and o.type == 'EMPTY' and any(c.type == 'ARMATURE' for c in o.children_recursive)]
congelar = set()
for r in raices: congelar.add(r); congelar.update(r.children_recursive)
NO_TOCAR = ("camera", "camara", "foco", "sun", "sol", "luz", "light", "ocean", "water", "agua", "smoke", "flame", "fire", "fuego", "campfire", "torch", "antorcha", "sky", "cielo", "ruta_camara")
for o in sc.objects:
    ad = o.animation_data
    if o in congelar or o.type in ('CAMERA', 'LIGHT') or not (ad and (ad.action or len(ad.nla_tracks))): continue
    if any(k in o.name.lower() for k in NO_TOCAR): continue
    congelar.add(o)
congelar = [o for o in congelar if o.type not in ('CAMERA', 'LIGHT')]

sc.frame_set(FRAME)
estado = {}
for o in congelar:
    e = {"loc": o.location.copy(), "rm": o.rotation_mode, "rq": o.rotation_quaternion.copy(), "re": o.rotation_euler.copy(),
         "esc": o.scale.copy(), "hv": o.hide_viewport, "hr": o.hide_render, "huesos": {}, "sk": {}}
    if o.type == 'ARMATURE':
        for pb in o.pose.bones:
            e["huesos"][pb.name] = (pb.location.copy(), pb.rotation_mode, pb.rotation_quaternion.copy(), pb.rotation_euler.copy(), pb.rotation_axis_angle[:], pb.scale.copy())
    if o.type == 'MESH' and o.data.shape_keys:
        e["sk"] = {k.name: k.value for k in o.data.shape_keys.key_blocks}
    estado[o.name] = e

acciones = set()
for o in congelar:
    for ad in (o.animation_data, getattr(getattr(o, "data", None), "shape_keys", None) and o.data.shape_keys.animation_data):
        if ad:
            if ad.action: acciones.add(ad.action)
            for t in ad.nla_tracks:
                for s in t.strips:
                    if s.action: acciones.add(s.action)
    o.animation_data_clear()
    if o.type == 'MESH' and o.data.shape_keys: o.data.shape_keys.animation_data_clear()
for o in congelar:
    e = estado[o.name]
    o.location = e["loc"]; o.rotation_mode = e["rm"]; o.rotation_quaternion = e["rq"]; o.rotation_euler = e["re"]; o.scale = e["esc"]
    o.hide_viewport = e["hv"]; o.hide_render = e["hr"]
    for n, (l, rm, rq, re_, raa, s) in e["huesos"].items():
        pb = o.pose.bones[n]; pb.location = l; pb.rotation_mode = rm; pb.rotation_quaternion = rq; pb.rotation_euler = re_; pb.rotation_axis_angle = raa; pb.scale = s
    for n, v in e["sk"].items(): o.data.shape_keys.key_blocks[n].value = v
for a in acciones:
    if a.users == 0: bpy.data.actions.remove(a)
for nombre in OCULTAR:                                                        # personajes/objetos que ya se fueron de la escena
    o = bpy.data.objects.get(nombre)
    if o:
        for x in [o] + list(o.children_recursive): x.hide_viewport = True; x.hide_render = True

# ---- 2. sonidos y voces de la parte anterior
ed = sc.sequence_editor; quitadas = 0
if ed:
    S_ = ed.strips if hasattr(ed, "strips") else ed.sequences
    nombres = [s.name for s in ed.strips_all if s.type == 'SOUND' and PREF in s.name]
    for n in nombres: S_.remove(ed.strips_all[n]); quitadas += 1
    ad = sc.animation_data
    if ad and ad.action:
        for l in ad.action.layers:
            for st in l.strips:
                for cb in st.channelbags:
                    for fc in [fc for fc in cb.fcurves if any('["%s"]' % n in fc.data_path for n in nombres)]: cb.fcurves.remove(fc)
for k in [k for k in sc.keys() if k.startswith("p%d_" % N)]: del sc[k]

# ---- 3. escena nueva desde el frame 1
sc.frame_start = 1; sc.frame_end = FIN_NUEVO; sc.frame_current = 1
sc["parte_anterior"] = {"archivo": bpy.path.basename(bpy.data.filepath), "frame_congelado": FRAME}
bpy.ops.wm.save_as_mainfile(filepath=SALIDA, compress=False)
print("SIGUIENTE PARTE: %s | congelado el frame %d de %s | %d objetos congelados, %d acciones quitadas, %d tiras de sonido quitadas | ocultos: %s"
      % (SALIDA, FRAME, bpy.path.basename(bpy.data.filepath), len(congelar), len(acciones), quitadas, OCULTAR))
print("CONGELADOS:", sorted(o.name for o in congelar)[:80])
