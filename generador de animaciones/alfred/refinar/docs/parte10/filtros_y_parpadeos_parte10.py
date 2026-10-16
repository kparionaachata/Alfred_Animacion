# -*- coding: utf-8 -*-
"""Parte 10: FILTROS ORGANICOS y PARPADEOS (ejecutar DESPUES de `jerry_arrastra_alfred_parte10.py` y de la voz; repetible: guarda sus deltas en
`scene["p10_organicos"]` y los resta antes de volver a sumar; el script del arrastre los borra al rehacerse).
- ALFRED: respiracion lenta (inconsciente) que se hace normal al levantarse (`Spine_alfred`/`Spine1_alfred` X/Z) + micro-movimiento de cabeza (`Neck_alfred`/`face_alfred`).
  OJOS: inconsciente cerrados (0.92); al volver en si (f300-337) ASIMETRICOS: el izquierdo se abre (0.35-0.5, con temblor) y el derecho casi cerrado (0.8-0.88);
  al levantarse los dos se abren (el derecho tarde) y desde que esta de pie parpadea normal (9 f).
- JERRY: respiracion de `spine_1`, orejas `ear.L/R` y cola `tail_2` (valores del estudio, mas fuerte jadeando tras jalar), parpadeos en ojos y pupilas cada 80-140 f."""
import bpy, math, random
import numpy as np
sc = bpy.context.scene
TT = sc.get("p10_tiempos", {}); T_PARA, T_MUEVE, T_LEV = int(TT.get("T_PARA", 234)), int(TT.get("T_MUEVE", 300)), int(TT.get("T_LEV", 338)); FIN = sc.frame_end     # tiempos del arrastre
A = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'Hips_alfred' in o.pose.bones)
J = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'scull_1' in o.pose.bones)
def fcurvas(ob):
    return {(c.data_path, c.array_index): c for l in ob.animation_data.action.layers for st in l.strips for b in st.channelbags for c in b.fcurves}
def noise(f, fr, sd, dm=0):
    return (math.sin(f * fr * 1.3 + sd * 7.3 + dm * 3.7) + 0.5 * math.sin(f * fr * 2.7 + sd * 2.1 + dm * 5.1) + 0.25 * math.sin(f * fr * 5.1 + sd * 4.9 + dm * 1.3)) / 1.75
ss = lambda t: 0.0 if t <= 0 else (1.0 if t >= 1 else t * t * (3 - 2 * t))
# ---------- quitar los deltas anteriores ----------
prev = sc.get("p10_organicos", {})
for ob in (A, J):
    fcs = fcurvas(ob)
    for key, vals in prev.get(ob.name, {}).items():
        dp, ix = key.rsplit("|", 1); fc = fcs.get((dp, int(ix)))
        if not fc: continue
        for kp in fc.keyframe_points:
            k = str(int(round(kp.co.x)))
            if k in vals: kp.co.y -= vals[k]
        fc.update()
nuevo = {}
def sumar(ob, dp, ix, fn):
    fc = fcurvas(ob).get((dp, ix))
    if fc is None: return
    vals = {}
    for kp in fc.keyframe_points:
        f = int(round(kp.co.x)); dv = fn(f); kp.co.y += dv; vals[str(f)] = dv
    fc.update(); nuevo.setdefault(ob.name, {})["%s|%d" % (dp, ix)] = vals
# ---------- Alfred ----------
def resp_a(f):                                                                              # inconsciente: lenta y suave; de pie: normal
    w = ss((f - T_LEV) / 60.0); amp = 0.012 + 0.010 * w; vel = 0.006 + 0.006 * w
    return amp, vel
for n in ("Spine_alfred", "Spine1_alfred"):
    sumar(A, 'pose.bones["%s"].rotation_euler' % n, 0, lambda f: resp_a(f)[0] * math.sin(f * resp_a(f)[1] * 2 * math.pi))
    sumar(A, 'pose.bones["%s"].rotation_euler' % n, 2, lambda f: resp_a(f)[0] * 0.4 * math.sin(f * resp_a(f)[1] * 2 * math.pi + 1.2))
for n in ("Neck_alfred", "face_alfred"):
    for ax in range(3):
        sumar(A, 'pose.bones["%s"].rotation_euler' % n, ax, lambda f, ax=ax: (0.006 if f < T_MUEVE else 0.02) * noise(f, 0.079, 693, ax))
# ---------- Jerry ----------
def jad(f): return 1.0 + 1.2 * ss((f - T_PARA) / 10.0) * (1 - ss((f - T_PARA - 120) / 40.0))     # respira mas fuerte despues de jalar
FASE_J = {}; _ph = 0.0
for f_ in range(0, FIN + 200):                                                              # fase acumulada: el ritmo cambia sin saltos (antes vibraba: periodo de ~7 f)
    FASE_J[f_] = _ph; _ph += 2 * math.pi / (48.0 - 18.0 * (jad(f_) - 1.0) / 1.2)            # calmado 48 f por respiracion, jadeando ~30 f
sumar(J, 'pose.bones["spine_1"].rotation_euler', 0, lambda f: (0.012 + 0.008 * (jad(f) - 1.0) / 1.2) * math.sin(FASE_J.get(f, 0.0)))
sumar(J, 'pose.bones["spine_1"].rotation_euler', 2, lambda f: 0.008 * noise(f, 0.05, 42))
for n, fa in (("ear.L", 0.0), ("ear.R", 1.57)): sumar(J, 'pose.bones["%s"].rotation_euler' % n, 2, lambda f, fa=fa: 0.12 * math.sin(f * 0.06 + fa))
sumar(J, 'pose.bones["tail_2"].rotation_euler', 2, lambda f: 0.12 * math.sin(f * 0.12))
sc["p10_organicos"] = nuevo
# ---------- ojos ----------
SEQ = [0.0, 0.25, 0.5, 0.75, 1.0, 1.0, 0.75, 0.5, 0.25]
def poner_closed(objs, curva):
    for o in objs:
        sk = o.data.shape_keys
        if not sk or "Closed" not in sk.key_blocks: continue
        if sk.animation_data and sk.animation_data.action:
            for fc in [c for l in sk.animation_data.action.layers for st in l.strips for b in st.channelbags for c in b.fcurves if "Closed" in c.data_path]:
                while len(fc.keyframe_points): fc.keyframe_points.remove(fc.keyframe_points[0])
        ck = sk.key_blocks["Closed"]
        for f, v in curva(o.name): ck.value = v; ck.keyframe_insert("value", frame=f)
def horario(seed, a, b, gap=(80, 140)):
    rng = random.Random(seed); f = a + rng.randint(5, 30); out = []
    while f + 10 < b: out.append(f); f += rng.randint(*gap)
    return out
T_FLECHA = int(TT.get("T_FLECHA", 10 ** 6)); GOLPES_S = [int(g) for g in TT.get("GOLPES_S", [])]
PARP_A = (horario(31, int(TT["T_LEV2"]) + 60, FIN) if "T_LEV2" in TT else []) if "T_FLECHA" in TT else horario(31, T_LEV + 50, FIN)                            # con la flecha al pecho vuelve a quedar inconsciente: sin parpadeos
def curva_alfred(nombre):
    izq = "izquierdo" in nombre; pts = [(1, 0.92), (T_MUEVE, 0.92)]
    if izq: pts += [(T_MUEVE + 8, 0.5), (T_MUEVE + 12, 0.7), (T_MUEVE + 18, 0.38), (T_MUEVE + 26, 0.5), (T_LEV - 4, 0.35), (T_LEV + 25, 0.12)]
    else: pts += [(T_MUEVE + 10, 0.86), (T_MUEVE + 20, 0.8), (T_MUEVE + 28, 0.88), (T_LEV - 4, 0.8), (T_LEV + 30, 0.4)]   # ASIMETRICO: el derecho se resiste a abrir
    if T_FLECHA < FIN:
        pts = [p_ for p_ in pts if p_[0] < T_FLECHA] + [(T_FLECHA, 0.1 if izq else 0.35), (T_FLECHA + 1, 0.0), (T_FLECHA + 4, 0.6), (T_FLECHA + 8, 0.92)]   # la flecha: abre los ojos de golpe y se desmaya
        for g in GOLPES_S: pts += [(g, 0.92), (g + 2, 0.7 if izq else 0.82), (g + 7, 0.92)]                       # cada golpe con el sombrero: tiemblan los parpados
        if "T_REAC" in TT:                                                                  # tras el sombrero vuelve en si (asimetrico) y se levanta con los ojos abiertos
            tr, tl = int(TT["T_REAC"]), int(TT["T_LEV2"])
            pts += [(tr + 4, 0.45 if izq else 0.8), (tr + 10, 0.6 if izq else 0.88), (tl, 0.3 if izq else 0.6), (tl + 30, 0.0 if izq else 0.15), (tl + 50, 0.0)]
    else: pts += [(T_LEV + 45, 0.0)]
    for s_ in PARP_A: pts += [(s_ - 1, 0.0)] + [(s_ + i, v) for i, v in enumerate(SEQ)] + [(s_ + 9, 0.0)]
    pts = sorted(set(pts)); VA = sc.get("p10_voz_alfred")
    if VA:                                                                                  # la VOZ al levantarse: en cada golpe de voz aprieta los ojos (asimetrico)
        i0 = int(VA["inicio"]); env = list(VA["env"]); xs = [p_[0] for p_ in pts]; ys = [p_[1] for p_ in pts]
        base = lambda f: float(np.interp(f, xs, ys))
        pts = [p_ for p_ in pts if not (i0 <= p_[0] < i0 + len(env))]
        for k, e in enumerate(env): f = i0 + k; pts.append((f, min(0.95, base(f) + (0.30 if izq else 0.13) * e)))
        pts = sorted(pts)
    return pts
PARP_J = horario(47, 1, FIN)
def curva_jerry(nombre):
    pts = [(1, 0.0)]
    for s in PARP_J: pts += [(s - 1, 0.0)] + [(s + i, v) for i, v in enumerate(SEQ)] + [(s + 9, 0.0)]
    return sorted(set(pts))
poner_closed([bpy.data.objects[n] for n in ("ojo_izquierdo_alfred", "ojo_derecho_alfred") if n in bpy.data.objects], curva_alfred)
poner_closed([bpy.data.objects[n] for n in ("ojo_izquierdo_jerry", "ojo_derecho_jerry", "pupila_izquierda_jerry", "pupila_derecha_jerry") if n in bpy.data.objects], curva_jerry)
print("ORGANICOS: Alfred %d canales, Jerry %d canales; parpadeos Alfred %s, Jerry %s" % (len(nuevo.get(A.name, {})), len(nuevo.get(J.name, {})), PARP_A, PARP_J))
