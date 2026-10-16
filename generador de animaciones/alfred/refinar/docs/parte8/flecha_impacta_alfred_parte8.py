# -*- coding: utf-8 -*-
"""Parte 8: 20 f despues de que Alfred termina "Ahora si, listo para buscar materiales." (voz hasta f2516), una FLECHA (`objetos/vanilla/arrow/arrow.blend`, objeto `arrow`)
sale de la cueva, vuela hacia el y SE CLAVA EN SU FRENTE en IMPACTO (2536); la cabeza rebota hacia atras por el golpe y vuelve con rebote elastico; la flecha queda clavada
siguiendo la cabeza (horneada por frame relativa al hueso `Neck_alfred`).
- La flecha es un sprite plano (Solidify) en el plano XY local, en diagonal: la PUNTA es el vertice mas lejano en la direccion (1, 1, 0). Escala 0.45 (~0.5 m).
- Vuelo VUELO f, desde DIST m delante de Alfred (en la direccion en que mira, hacia la cueva), arco bajo; la flecha apunta siempre a la tangente y su plano queda vertical.
- Reaccion (en `tunel_alfred_armature`, se SUMA; base guardada en `scene["alfred_flecha_base"]`): `Neck_alfred` X -0.45 (atras) y `Spine2_alfred` X -0.15 en 2 f, vuelta ELASTIC OUT en 18 f.
Ejecutar DESPUES de `alfred_antorcha_pared_parte8.py`. Repetible."""
import bpy, math
from mathutils import Vector, Matrix, Quaternion

IMPACTO = globals().get('IMPACTO', 2536); VUELO = 14; DIST = 14.0; ESC = 0.45; HUNDE = 0.08; FIN = globals().get('FIN', 2580)
ss = lambda t: 0.0 if t <= 0 else 1.0 if t >= 1 else t * t * (3 - 2 * t)
def ela_out(t):
    if t <= 0: return 0.0
    if t >= 1: return 1.0
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi) / 3) + 1
sc = bpy.context.scene
ARM = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'Hips_alfred' in o.pose.bones); ROOT = ARM.parent
FA = {(fc.data_path, fc.array_index): fc for l in ARM.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves}
def key(fc, f, v, interp='LINEAR'):
    k = fc.keyframe_points.insert(f, v); k.interpolation = interp

# ---------------- 1) reaccion de la cabeza ----------------
REAC = [('Neck_alfred', 0, -0.45), ('Spine2_alfred', 0, -0.15)]
RA = range(IMPACTO - 1, IMPACTO + 22)
base = sc.get("alfred_flecha_base")
if base is None:
    base = {"%s|%d" % (b, i): [FA[('pose.bones["%s"].rotation_euler' % b, i)].evaluate(f) for f in RA] for b, i, _ in REAC}; sc["alfred_flecha_base"] = base
for b, i, amp in REAC:
    fc = FA[('pose.bones["%s"].rotation_euler' % b, i)]; bs = list(base["%s|%d" % (b, i)])
    for j, f in enumerate(RA):
        w = 0.0 if f <= IMPACTO else ((f - IMPACTO) / 2.0 if f <= IMPACTO + 2 else 1.0 - ela_out((f - IMPACTO - 2) / 18.0))
        key(fc, f, bs[j] + amp * w)
    fc.update()

# ---------------- 2) flecha ----------------
fl = bpy.data.objects.get("flecha_alfred")
if fl is None:
    with bpy.data.libraries.load(r"C:\Users\user\Desktop\Alfred_Animacion\objetos\vanilla\arrow\arrow.blend", link=False) as (src, dst): dst.objects = ["arrow"]
    fl = dst.objects[0]; fl.name = "flecha_alfred"; sc.collection.objects.link(fl)
if fl.animation_data: fl.animation_data_clear()
fl.rotation_mode = 'QUATERNION'
D_loc = Vector((1, 1, 0)).normalized(); N_loc = Vector((0, 0, 1))
punta_loc = max((v.co for v in fl.data.vertices), key=lambda c: c.dot(D_loc))
def M_flecha(punta_w, dir_w):
    """matriz de mundo con la direccion local D -> dir_w, el plano del sprite VERTICAL, y el vertice de la punta en `punta_w`"""
    d = dir_w.normalized(); lado = d.cross(Vector((0, 0, 1)))
    if lado.length < 1e-6: lado = Vector((1, 0, 0))
    lado.normalize()                                                                           # normal del plano del sprite (horizontal, perpendicular al vuelo)
    perp_loc = N_loc.cross(D_loc).normalized()                                                  # direccion del plano local perpendicular a D
    Rl = Matrix((D_loc, perp_loc, N_loc)).transposed(); up_w = lado.cross(d).normalized()
    Rw = Matrix((d, up_w, lado)).transposed(); R = (Rw @ Rl.inverted()).to_4x4()
    S = Matrix.Diagonal((ESC, ESC, ESC, 1)); M = R @ S
    return Matrix.Translation(punta_w - (M @ punta_loc.to_4d()).to_3d()) @ M
sc.frame_set(IMPACTO); dg = bpy.context.evaluated_depsgraph_get()
cab = bpy.data.objects["Mesh_0_alfred"].evaluated_get(dg); vs = [cab.matrix_world @ v.co for v in cab.data.vertices]
fwd = (ROOT.matrix_world.to_3x3() @ Vector((0, 1, 0))); fwd.z = 0; fwd.normalize()            # hacia donde mira Alfred (la cueva)
frente_max = max(v.dot(fwd) for v in vs); zmin = min(v.z for v in vs); zmax = max(v.z for v in vs)
cen = sum(vs, Vector()) / len(vs)
frente = cen + fwd * (frente_max - cen.dot(fwd)); frente.z = zmin + 0.72 * (zmax - zmin)          # la frente: cara delantera de la cabeza, arriba
dir_imp = (-fwd + Vector((0, 0, -0.06))).normalized()                                          # entra casi horizontal, algo hacia abajo
p_imp = frente + dir_imp * HUNDE                                                                # la punta queda HUNDE m dentro de la cabeza
p_ini = frente + fwd * DIST + Vector((0, 0.0, 0.5))
def vuelo(u):
    p = p_ini.lerp(p_imp, u); p.z += 0.35 * 4 * u * (1 - u); return p
can = {("location", i): [] for i in range(3)}; can.update({("rotation_quaternion", i): [] for i in range(4)}); can.update({("scale", i): [] for i in range(3)})
def poner(f, M):
    l, q, s = M.decompose()
    for i in range(3): can[("location", i)].append((f, l[i])); can[("scale", i)].append((f, s[i]))
    for i in range(4): can[("rotation_quaternion", i)].append((f, q[i]))
for k in range(0, VUELO + 1):
    f = IMPACTO - VUELO + k; u = k / VUELO; p = vuelo(u); d = (vuelo(min(1, u + 0.02)) - vuelo(max(0, u - 0.02))) if k < VUELO else dir_imp
    poner(f, M_flecha(p, d))
M_imp = M_flecha(p_imp, dir_imp)
cuello = lambda: ARM.matrix_world @ ARM.pose.bones["Neck_alfred"].matrix
sc.frame_set(IMPACTO); OFF = cuello().inverted() @ M_imp
for f in range(IMPACTO + 1, FIN + 1):
    sc.frame_set(f); poner(f, cuello() @ OFF)
a = bpy.data.actions.new("flecha_alfred_accion"); slot = a.slots.new(id_type='OBJECT', name=fl.name); cb = a.layers.new("Capa").strips.new(type='KEYFRAME').channelbag(slot, ensure=True)
for (dp, i), pts in can.items():
    fc = cb.fcurves.new(dp, index=i); fc.keyframe_points.add(len(pts)); fc.keyframe_points.foreach_set("co", [v for p in pts for v in p])
    for k_ in fc.keyframe_points: k_.interpolation = 'LINEAR'
    fc.update()
for dp in ("hide_viewport", "hide_render"):
    fc = cb.fcurves.new(dp, index=0); fc.keyframe_points.add(2); fc.keyframe_points.foreach_set("co", [1, 1.0, IMPACTO - VUELO, 0.0])
    for k_ in fc.keyframe_points: k_.interpolation = 'CONSTANT'
fl.animation_data_create(); fl.animation_data.action = a; fl.animation_data.action_slot = slot
sc.frame_end = max(sc.frame_end, FIN); sc.frame_set(IMPACTO)
print("Flecha: sale f%d desde %s, se clava en la frente en f%d (%s), sigue a la cabeza hasta f%d" % (IMPACTO - VUELO, tuple(round(v, 2) for v in p_ini), IMPACTO, tuple(round(v, 2) for v in frente), FIN))
