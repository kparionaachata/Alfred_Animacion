# -*- coding: utf-8 -*-
"""Parte 8: mientras dice "¿Sera porque yo tengo que picar dos bloques y tu solo uno?" (voz f2158-2212), Alfred saca el pico de piedra, PICA el bloque que tiene delante
(`tunel_bloque_piedra_-132_-71_7`, piedra: 3 golpes), lo rompe (tiembla, se agrieta y desaparece; suelta su mini bloque) y despues guarda el pico y SUBE de un salto al escalon
(el bloque de z6 que queda debajo) con la animacion `animacion_alfred (12).py` (Mixamo: sube 1 m y avanza 0.81 m; copia en `acciones/animacion_alfred_salta_fuera_fosa.py`).
Ejecutar DESPUES de `alfred_se_soba_cabeza_golpe_parte8.py` y `alfred_mira_a_jerry_parte8.py`. Usa del add-on de tunel de Alfred las poses (Biblioteca: tomar el pico, ciclo de picar,
guardar, reposo), la forma de sostener el pico del usuario (`stone_pickaxe["tunel_grip_pico_usuario"]`) y las claves de romper un bloque (`_romper_claves`).
Escribe en `tunel_alfred_armature` / `tunel_alfred_root` / `tunel_pico` y en la accion de visibilidad del bloque. Repetible (borra sus claves > T0 y rehace el bloque / item)."""
import bpy, math, ast
from mathutils import Matrix, Vector, Euler, Quaternion
import alfred_animation_studio.tunel as tn

ADEL = globals().get('ADEL', -0.20); LAT = globals().get('LAT', 0.20); GIRO = globals().get('GIRO', 15.0)   # mientras saca el pico: colocacion (ADEL m hacia delante; negativo = atras), de lado (el golpe con la mano derecha cae a su derecha) y girado GIRO grados; vuelve al centro al guardarlo
T0 = globals().get('T0', 2218); BLOQUE = "tunel_bloque_piedra_-132_-71_7"; GOLPES = 3; FIN = globals().get('FIN', 2395)
SALTO = r"C:/Users/user/Desktop/Alfred_Animacion/generador de animaciones/alfred/refinar/docs/acciones/animacion_alfred_salta_fuera_fosa.py"
ss = tn.ss; sc = bpy.context.scene; bib = tn.Biblioteca(); ROOT, ARM = tn.rig_alfred(); pk = bpy.data.objects["stone_pickaxe"]; vl = bpy.context.view_layer
pk.rotation_mode = "QUATERNION"                                                                # las claves del pico son cuaternion: en modo Euler Blender las ignora (el pico quedaba girado 160 grados)
def fcs(o): return {(fc.data_path, fc.array_index): fc for l in o.animation_data.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves}
FA, FR, FP = fcs(ARM), fcs(ROOT), fcs(pk)
# limpieza previa: los huesos que NO animan los scripts de sobarse / mirar a Jerry conservaban, entre BASE_F y T0, claves de ejecuciones anteriores de este script
# (saltos de postura, p. ej. f2200 -> 2201): se dejan en la postura que tienen en BASE_F
BASE_F = globals().get('BASE_F', 2141)
PROPIOS = {('pose.bones["RightUpArm_alfred"].rotation_euler', i) for i in range(3)} | {('pose.bones["RightUpArm_alfred"].location', i) for i in range(3)} | \
          {('pose.bones["Rightelbow_alfred"].rotation_euler', i) for i in range(3)} | {('pose.bones["Neck_alfred"].rotation_euler', i) for i in range(3)}
for c, fc in FA.items():
    if c in PROPIOS or not c[0].startswith('pose.bones'): continue
    v = fc.evaluate(BASE_F)
    for k in [k for k in fc.keyframe_points if BASE_F + 0.5 < k.co.x < T0 + 0.5][::-1]: fc.keyframe_points.remove(k)
    for f_ in (BASE_F + 1, T0):
        k = fc.keyframe_points.insert(f_, v); k.interpolation = 'LINEAR'
    fc.update()
CH = [("rotation_euler", 0), ("rotation_euler", 1), ("rotation_euler", 2), ("location", 0), ("location", 1), ("location", 2), ("scale", 0), ("scale", 1), ("scale", 2)]
def pose_actual(f):
    return {n: tuple((math.degrees(FA[('pose.bones["%s"].%s' % (n, dp), i)].evaluate(f)) if dp == "rotation_euler" else FA[('pose.bones["%s"].%s' % (n, dp), i)].evaluate(f)) for dp, i in CH) for n in bib.bones}

# ---------------- linea de tiempo (poses en grados + loc + escala, como el add-on) ----------------
def _mezq(p, q, t):
    """mezcla de poses con la ROTACION por cuaternion (slerp): mezclar Euler numero a numero da vueltas de golpe cuando las dos poses usan formas distintas de la misma rotacion"""
    out = {}
    for n in p:
        a_, b_ = p[n], q[n]
        qa = Euler([math.radians(x) for x in a_[0:3]], 'XYZ').to_quaternion(); qb = Euler([math.radians(x) for x in b_[0:3]], 'XYZ').to_quaternion()
        if qa.dot(qb) < 0: qb.negate()
        e = qa.slerp(qb, t).to_euler('XYZ', Euler([math.radians(x) for x in a_[0:3]], 'XYZ'))
        out[n] = tuple(math.degrees(x) for x in e) + tuple(a_[k] + (b_[k] - a_[k]) * t for k in range(3, 9))
    return out
tn._mezcla = _mezq
TL = {}; ACC = []; GOLPE_F = []
BASE_F = globals().get('BASE_F', 2141)                                                # posicion de Alfred ANTES de cualquier ejecucion de este script (las claves > T0 de una ejecucion anterior lo tienen desplazado)
x0, y0, z0 = (FR[('location', i)].evaluate(BASE_F) for i in range(3)); rz0 = math.degrees(FR[('rotation_euler', 2)].evaluate(T0))
ult = {"pose": pose_actual(T0)}; cur = [T0 + 1]
def poner(p, root=None):
    TL[cur[0]] = dict(pose=p, root=root); ult["pose"] = p; cur[0] += 1
def secuencia(seq, mezcla_in=3):
    p0 = ult["pose"]
    for i, p in enumerate(seq): poner(tn._mezcla(p0, p, ss((i + 1) / (mezcla_in + 1))) if i < mezcla_in else p)
t_toma = cur[0]; secuencia(bib.toma, 4); ACC.append((t_toma + bib.toma_agarre, "toma"))                      # saca el pico de la espalda (agarra en el frame 23)
secuencia([tn._mezcla(bib.listo, bib.HA[1022], ss((j + 1) / 7.0)) for j in range(7)], 4)    # entra desde el final de tomar el pico (sin salto)
PAUSA_TRAS = globals().get('PAUSA_TRAS', 1); PAUSA = globals().get('PAUSA', 0)                               # tras el 1.er golpe se detiene a MIRAR A JERRY (arriba) PAUSA frames y despues termina de picar
def mira_jerry(n):
    listo = bib.HA[1022]; arriba = dict(listo); v = list(arriba["Neck_alfred"]); v[0] = -35.0; arriba["Neck_alfred"] = tuple(v)
    v = list(arriba["Spine2_alfred"]); v[0] -= 6.0; arriba["Spine2_alfred"] = tuple(v)
    seq = []
    for i in range(n):
        if i < 6: seq.append(tn._mezcla(listo, arriba, ss((i + 1) / 6.0)))
        elif i >= n - 6: seq.append(tn._mezcla(arriba, listo, ss((i - (n - 6) + 1) / 6.0)))
        else:
            q = dict(arriba); w = list(q["Neck_alfred"]); w[0] += 1.5 * math.sin(i * 0.5); q["Neck_alfred"] = tuple(w); seq.append(q)
    return seq
for g in range(GOLPES):                                                                                      # 3 golpes (piedra): ciclo de picar de 12 f, impacto en el 4.o
    t = cur[0]; secuencia([bib.pico_ciclo(8 + j) for j in range(12)], 5 if g == 0 or g == PAUSA_TRAS else 0); GOLPE_F.append(t + 4)
    if g + 1 == PAUSA_TRAS and PAUSA > 0: secuencia(mira_jerry(PAUSA), 4)
t_g = cur[0]; secuencia([bib.PA[f] for f in range(945, 960)], 3); ACC.append((t_g + 11, "guarda"))           # guarda el pico en la espalda
secuencia([tn._mezcla(bib.PA[959], bib.reposo, ss((i + 1) / 10.0)) for i in range(10)], 0)
# salto (payload de animacion_alfred (12).py): huesos + raiz relativa a donde esta Alfred
src = open(SALTO, encoding="utf-8").read()
P = next(ast.literal_eval(n.value) for n in ast.parse(src).body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "PAYLOAD")
NF = P["info"]["frames"]; mat = lambda l, e: Matrix.LocRotScale(Vector(l), Euler(e, 'XYZ').to_quaternion(), Vector((1, 1, 1)))
R0 = mat(P["root"]["location"][0], P["root"]["rotation_euler"][0])
FWD = Vector((-math.sin(math.radians(rz0)), math.cos(math.radians(rz0)), 0)); P_ADEL = Vector((x0, y0, z0)) + FWD * ADEL
Mstart = Matrix.LocRotScale(Vector((x0, y0, z0)), Euler((0, 0, math.radians(rz0)), 'XYZ').to_quaternion(), Vector((1, 1, 1))); Tm = Mstart @ R0.inverted()
t_salto = cur[0]; base = dict(ult["pose"]); prev = Euler((0, 0, math.radians(rz0)), 'XYZ')
for i in range(NF):
    p = {}
    for n in bib.bones:
        v = list(base[n])
        for ch, val in P["constantes"].get(n, {}).items():
            off = {"rotation_euler": 0, "location": 3, "scale": 6}[ch]
            for k in range(3): v[off + k] = math.degrees(val[k]) if ch == "rotation_euler" else val[k]
        for ch, vals in P["bones"].get(n, {}).items():
            off = {"rotation_euler": 0, "location": 3, "scale": 6}[ch]
            for k in range(3): v[off + k] = math.degrees(vals[i][k]) if ch == "rotation_euler" else vals[i][k]
        p[n] = tuple(v)
    if i < 4: p = tn._mezcla(base, p, ss((i + 1) / 5.0))
    M = Tm @ mat(P["root"]["location"][i], P["root"]["rotation_euler"][i]); l, q, _ = M.decompose(); e = q.to_euler('XYZ', prev); prev = e
    poner(p, root=(l.x, l.y, l.z, math.degrees(e.z)))
t_fin = cur[0] - 1
while cur[0] <= FIN: poner(ult["pose"], root=TL[t_fin]["root"])
IZQ = Vector((-FWD.y, FWD.x, 0))
def raiz(f):
    if TL[f]["root"]: return TL[f]["root"]
    u = ss((f - T0 - 1) / 20.0) * (1.0 - ss((f - t_g) / 14.0)); p = Vector((x0, y0, z0)) + FWD * ADEL * u + IZQ * LAT * u; return (p.x, p.y, p.z, rz0 + GIRO * u)

# ---------------- pico: matrices de la mano / espalda en los cambios (poniendo la pose a mano, antes de escribir claves) ----------------
REL = Matrix([list(pk["tunel_rel_espalda"][i * 4:i * 4 + 4]) for i in range(4)]); UP = pk["tunel_grip_pico_usuario"]; GRIP = Matrix([list(UP[i * 4:i * 4 + 4]) for i in range(4)])
for o in (ROOT, ARM):
    if o.animation_data: o.animation_data.action_slot = o.animation_data.action_slot
acc_r, acc_a = ROOT.animation_data.action, ARM.animation_data.action; ROOT.animation_data.action = None; ARM.animation_data.action = None
def mats(f):
    r = raiz(f); ROOT.location = r[:3]; ROOT.rotation_euler = (0, 0, math.radians(r[3]))
    for n, v in TL[f]["pose"].items():
        b = ARM.pose.bones[n]; b.rotation_mode = 'XYZ'; b.rotation_euler = tuple(math.radians(a) for a in v[0:3]); b.location = v[3:6]; b.scale = v[6:9]
    vl.update(); return (ARM.matrix_world @ ARM.pose.bones["Rightelbow_alfred"].matrix).copy(), (ARM.matrix_world @ ARM.pose.bones["Spine1_alfred"].matrix).copy()
B = {}
(ta, _), (tg, _) = ACC
hand, sp1 = mats(ta); B0 = hand.inverted() @ (sp1 @ REL); B[ta - 1] = REL; B[ta] = B0
for i in range(1, 5): B[ta + i] = tn._mixM(B0, GRIP, i / 4.0)
for i in range(4, -1, -1):
    t = tg - i; hand, sp1 = mats(t); Bb = hand.inverted() @ (sp1 @ REL); B[t] = tn._mixM(GRIP, Bb, (4 - i) / 4.0)
B[tg + 1] = REL; B[T0] = REL; B[BASE_F] = REL
for t in range(ta + 5, tg - 4): B[t] = GRIP
ROOT.animation_data.action = acc_r; ARM.animation_data.action = acc_a

# ---------------- claves ----------------
def key(fc, f, v, interp='LINEAR'):
    k = fc.keyframe_points.insert(f, v); k.interpolation = interp
def limpiar(fc, desde):
    for k in [k for k in fc.keyframe_points if k.co.x > desde + 0.5][::-1]: fc.keyframe_points.remove(k)
for fc in FA.values(): limpiar(fc, T0)
for i in range(3): limpiar(FR[('location', i)], BASE_F)                                     # la POSICION del empty: desde BASE_F (quedaban claves de ejecuciones anteriores que lo movian a saltos mientras se sobaba)
limpiar(FR[('rotation_euler', 2)], T0)
for f in range(BASE_F + 1, T0 + 1):
    for i, v in enumerate((x0, y0, z0)): key(FR[('location', i)], f, v)
for fc in FP.values(): limpiar(fc, BASE_F)                                                   # el pico: desde BASE_F (quedaban claves de ejecuciones anteriores con el pico en la mano mientras se soba)
_prev_e = {n: Euler([FA[('pose.bones["%s"].rotation_euler' % n, i)].evaluate(T0) for i in range(3)], 'XYZ') for n in bib.bones}
for f in sorted(TL):
    for n, v in TL[f]["pose"].items():
        e = Euler([math.radians(x) for x in v[0:3]], 'XYZ'); e.make_compatible(_prev_e[n]); _prev_e[n] = e        # rotacion continua respecto al frame anterior
        for j, (dp, i) in enumerate(CH): key(FA[('pose.bones["%s"].%s' % (n, dp), i)], f, e[i] if dp == "rotation_euler" else v[j])
    r = raiz(f)
    for i in range(3): key(FR[('location', i)], f, r[i])
    key(FR[('rotation_euler', 2)], f, math.radians(r[3]))
for t in sorted(B):
    l, q, s = B[t].decompose()
    for i in range(3): key(FP[('location', i)], t, l[i]); key(FP[('scale', i)], t, s[i])
    for i in range(4): key(FP[('rotation_quaternion', i)], t, q[i])
ie = [(BASE_F, 1.0), (T0, 1.0), (ta - 1, 1.0), (ta, 0.0), (tg, 0.0), (tg + 1, 1.0)]; im = [(BASE_F, 0.0), (T0, 0.0), (ta - 1, 0.0), (ta, 1.0), (tg, 1.0), (tg + 1, 0.0)]
for (dp, vals) in (('constraints["Espalda"].influence', ie), ('constraints["Mano"].influence', im)):
    for f, v in vals: key(FP[(dp, 0)], f, v, 'CONSTANT')
for d in (FA, FR, FP):
    for fc in d.values(): fc.update()

# ---------------- el bloque se rompe en el 3.er golpe; su mini bloque cae al escalon y lo absorbe al subir ----------------
ob = bpy.data.objects[BLOQUE]; tC = GOLPE_F[-1]
_c = [int(v) for v in BLOQUE.rsplit('_', 3)[1:]]; basep = Vector((_c[0] + 0.5, _c[1] + 0.5, _c[2] + 0.5))     # reposo = CENTRO de su celda (no `ob.location`, que puede estar temblando)
ob.location = basep; ob.scale = (1.0, 1.0, 1.0)
a = ob.animation_data.action; cb = a.layers[0].strips[0].channelbags[0]
for fc in list(cb.fcurves):
    if fc.data_path in ("location", "scale"): cb.fcurves.remove(fc)
    elif fc.data_path.startswith("hide"):
        for k in [k for k in fc.keyframe_points if k.co.x > 1.5][::-1]: fc.keyframe_points.remove(k)
        key(fc, tC + 3, 1.0, 'CONSTANT'); fc.update()
for (dp, i), pts in tn._romper_claves(tC, basep, GOLPE_F[:-1]).items():
    fc = cb.fcurves.new(dp, index=i); fc.keyframe_points.add(len(pts)); fc.keyframe_points.foreach_set("co", [v for p in pts for v in p])
    for k in fc.keyframe_points: k.interpolation = 'LINEAR'
    fc.update()
nom = "tunel_item_golpe_-132_-71_7"
if nom in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[nom], do_unlink=True)
it = bpy.data.objects.new(nom, bpy.data.meshes["tunel_bloque_piedra"]); it.scale = (0.25,) * 3; bpy.data.collections["tunel"].objects.link(it)
suelo = basep.z - 0.5 + 0.125; land = tC + 6
t_pick = next((f for f in range(land + 6, FIN) if TL.get(f, {}).get("root") and abs(TL[f]["root"][2] - (basep.z - 0.5)) < 0.3 and math.hypot(TL[f]["root"][0] - basep.x, TL[f]["root"][1] - basep.y) < 1.2), FIN - 8)
ra = raiz(t_pick + 6); dst = Vector((ra[0], ra[1], ra[2] + 1.1))
ex = {("location", i): [] for i in range(3)}; ex.update({("scale", i): [] for i in range(3)})
for k_, u in ((0, 0.0), (3, 0.4), (6, 1.0)):
    for i, v in enumerate((basep.x, basep.y, basep.z + (suelo - basep.z) * u * u)): ex[("location", i)].append((tC + k_, v))
for i, v in enumerate((basep.x, basep.y, suelo + 0.1)): ex[("location", i)].append((land + 2, v))
for i, v in enumerate((basep.x, basep.y, suelo)): ex[("location", i)].append((land + 4, v)); ex[("location", i)].append((t_pick, v))
for k_ in (2, 4, 6):
    u = ss(k_ / 6.0)
    for i, (v0, v1) in enumerate(zip((basep.x, basep.y, suelo), dst)): ex[("location", i)].append((t_pick + k_, v0 + (v1 - v0) * u))
for i in range(3): ex[("scale", i)] = [(tC, 0.25), (t_pick, 0.25), (t_pick + 6, 0.0)]
ex[("rotation_euler", 2)] = [(tC, 0.0), (t_pick + 6, 2 * math.pi * (t_pick + 6 - tC) / 15.0)]
tn._vis(it, tC, t_pick + 7, ex)
sc.frame_end = max(sc.frame_end, FIN)
print("Alfred: toma el pico f%d (agarra f%d), golpes %s, bloque roto f%d, guarda f%d, salto f%d-%d, item absorbido f%d" % (t_toma, ta, GOLPE_F, tC + 3, tg, t_salto, t_fin, t_pick + 6))
