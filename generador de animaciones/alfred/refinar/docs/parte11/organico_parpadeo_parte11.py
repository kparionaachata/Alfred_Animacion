# -*- coding: utf-8 -*-
"""Parte 11: FILTROS ORGANICOS y PARPADEOS de ALFRED y JERRY (no al cerdo ni a la paloma: pedido del usuario).
Filtros = los de los estudios (alfred_animation_studio / jerry_animation_studio, _apply_organic_filters) con sus valores por defecto
(reglas_alfred / reglas_jerry): respiracion, micro-movimiento de cabeza, micro-escala del torso y (Jerry) ruido en los hombros.
NO se aplican el suavizado ni el retardo de codos: moverian las manos/patas de los contactos (pan, pescado, flechas).
Los tramos con POSE DEL USUARIO quedan exactos (sin ruido): la mirada de Alfred a Jerry y la pata de Jerry apuntando al bosque;
la cadera de Alfred flotando no se toca.
Parpadeo = curva fisiologica del estudio (9 frames: 40% cierra, 20% cerrado, 40% abre) en el shape key 'Closed' de ojos (y pupilas
de Jerry), cada 3-5 s al azar, sin pisar los parpadeos de las voces. Alfred deja de parpadear cuando cae al mar.
Ejecutar al final (despues de todos los scripts de animacion). Repetible: deshace lo que sumo antes."""
import bpy, math, random

MARCA = "p11_organico"
BLINK = 9


def _noise_at(frame, freq, seed, dim=0):
    v = math.sin(frame * freq * 1.3 + seed * 7.3 + dim * 3.7)
    v += math.sin(frame * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5
    v += math.sin(frame * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25
    return v / 1.75


def _blink(offset, dur=BLINK):
    t = max(0.0, min(1.0, (offset - 1) / max(dur - 1, 1)))
    if t <= 0.40: p = t / 0.40; return p * p * (3 - 2 * p)
    if t <= 0.60: return 1.0
    p = (t - 0.60) / 0.40; return 1.0 - p * p * (3 - 2 * p)


def _sstep(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


def _curvas(a):
    return {(fc.data_path, fc.array_index): fc for l in a.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves}


_CACHE = {}


def _sumar(a, idb, ruta, i, f, d):
    c = _CACHE.get((a.name, ruta, i))
    if c is None:
        fc = a.fcurve_ensure_for_datablock(idb, ruta, index=i)
        if len(fc.keyframe_points) == 0:                                       # curva nueva: su valor base (escala 1, rotacion 0)
            fc.keyframe_points.insert(1, 1.0 if ruta.endswith(".scale") else 0.0, options={'FAST'})
        c = _CACHE[(a.name, ruta, i)] = (fc, {int(round(k.co.x)): k for k in fc.keyframe_points})
    fc, km = c
    kp = km.get(f)
    if kp is None:
        kp = fc.keyframe_points.insert(f, fc.evaluate(f), options={'FAST'}); kp.interpolation = 'LINEAR'
        c = _CACHE[(a.name, ruta, i)] = (fc, {int(round(k.co.x)): k for k in fc.keyframe_points}); kp = c[1][f]
    kp.co.y += d; kp.handle_left.y += d; kp.handle_right.y += d
    return fc


def construir():
    sc = bpy.context.scene; T = sc["p11_tiempos"]; FIN = sc.frame_end
    # tramos con pose exacta del usuario (sin ruido en esos huesos)
    mira = sc.get("p11_voz_que_cocinaste"); pata = sc.get("p11_voz_jerry_anda_ve")
    LIBRE = {"alfred_cabeza": (int(mira["inicio"]) - 16, int(mira["fin"]) + 20) if mira else (0, -1),
             "jerry_pata": tuple(pata["pata"]) if pata else (0, -1)}

    PERS = [
        dict(arm="armature", resp=(("Spine_alfred", "Spine1_alfred"), 0.040, 0.020, 1.97), cab=(("Neck_alfred", "face_alfred"), 0.023, 0.079, 693),
             esc=("Spine1_alfred", 0.010), hombros=None, libre_cab="alfred_cabeza"),
        dict(arm="Dog_001_rig", resp=(("spine_1",), 0.05, 0.01, 0.0), cab=(("spine_1",), 0.008, 0.05, 42),
             esc=("spine_1", 0.005), hombros=(("front_shoulder.R", "front_shoulder.L"), 0.006, 0.07, 123), libre_hombro="jerry_pata"),
    ]
    for P in PERS:
        arm = bpy.data.objects[P["arm"]]; a = arm.animation_data.action
        prev = a.get(MARCA)                                                    # deshacer la pasada anterior
        if prev:
            cv = _curvas(a)
            for clave, v in prev.to_dict().items():
                ruta, i = clave.rsplit("|", 1); fc = cv.get((ruta, int(i)))
                if fc is None: continue
                km = {int(round(k.co.x)): k for k in fc.keyframe_points}
                for j, d in enumerate(v["vals"]):
                    k = km.get(v["ini"] + j)
                    if k: k.co.y -= d; k.handle_left.y -= d; k.handle_right.y -= d
                fc.update()
            del a[MARCA]
        hechos = {}

        def add(ruta, i, f, d):
            if abs(d) < 1e-7: return
            _sumar(a, arm, ruta, i, f, d); hechos.setdefault("%s|%d" % (ruta, i), {})[f] = d

        rb = 'pose.bones["%s"].rotation_euler'; sb = 'pose.bones["%s"].scale'
        bones, amp, speed, phase = P["resp"]; esc_vals = []
        for f in range(1, FIN + 1):
            lib = LIBRE.get(P.get("libre_cab", ""), (0, -1)); w = 1.0            # tramo con pose del usuario (cuello, cara, Spine1, Spine2): exacto
            if lib[0] <= f <= lib[1]: w = 1.0 - min(1.0, min(f - lib[0], lib[1] - f) / 8.0)
            for b in bones:                                                    # respiracion
                add(rb % b, 0, f, w * amp * math.sin(f * speed * 2 * math.pi + phase))
                add(rb % b, 2, f, w * amp * 0.4 * math.sin(f * speed * 2 * math.pi + phase + 1.2))
            cb, camp, cspeed, seed = P["cab"]                                  # micro-movimiento de cabeza
            for ax in range(3):
                for b in cb: add(rb % b, ax, f, w * camp * _noise_at(f, cspeed, seed, ax))
            eb, eamp = P["esc"]                                                # micro-escala del torso (con la respiracion)
            esc_vals.append(1.0 + w * eamp * math.sin(f * speed * 2 * math.pi + phase))
            if P["hombros"]:                                                   # ruido en hombros (Jerry)
                hb, hamp, hspeed, hseed = P["hombros"]; lib = LIBRE.get(P.get("libre_hombro", ""), (0, -1))
                for b, off in zip(hb, (0, 17)):
                    w = 0.0 if (b.endswith(".R") and lib[0] - 8 <= f <= lib[1] + 8) else 1.0
                    for ax in range(3): add(rb % b, ax, f, w * hamp * _noise_at(f, hspeed, hseed + off, ax))
        # micro-escala del torso: curva propia, una clave por frame con el valor exacto (nada mas anima esa escala)
        eb, eamp = P["esc"]
        for ax in range(3):
            fc = _curvas(a).get((sb % eb, ax))
            if fc is not None: fc.keyframe_points.clear()
        fc = a.fcurve_ensure_for_datablock(arm, sb % eb, index=2); fc.keyframe_points.clear(); fc.keyframe_points.add(len(esc_vals))
        fc.keyframe_points.foreach_set("co", [c for k, v in enumerate(esc_vals) for c in (k + 1, v)])
        fc.keyframe_points.foreach_set("interpolation", [1] * len(esc_vals))
        for fc in _curvas(a).values(): fc.update()
        a[MARCA] = {k: {"ini": min(v), "vals": [v.get(f, 0.0) for f in range(min(v), max(v) + 1)]} for k, v in hechos.items()}

    # ---- PARPADEOS ----
    rng = random.Random(77)
    ojos = {"alfred": ["ojo_izquierdo_alfred", "ojo_derecho_alfred"],
            "jerry": ["ojo_izquierdo_jerry", "ojo_derecho_jerry", "pupila_izquierda_jerry", "pupila_derecha_jerry"]}
    fin_ojos = {"alfred": int(T["pan_gana"]), "jerry": FIN}                  # Alfred no parpadea al caer al mar
    hechos_b = {}
    for quien, nombres in ojos.items():
        # quitar los parpadeos de la pasada anterior
        for n in nombres:
            o = bpy.data.objects[n]; sk = o.data.shape_keys; ad = sk.animation_data
            prev = sc.get(MARCA + "_parpadeos", {}).get(n)
            if prev and ad and ad.action:
                for fc in _curvas(ad.action).values():
                    if fc.data_path == 'key_blocks["Closed"].value':
                        for i in reversed(range(len(fc.keyframe_points))):
                            if int(round(fc.keyframe_points[i].co.x)) in set(prev): fc.keyframe_points.remove(fc.keyframe_points[i], fast=True)
                        fc.update()
        # frames ocupados por los parpadeos/expresiones de las voces (claves 'Closed' ya existentes)
        o0 = bpy.data.objects[nombres[0]]; ad = o0.data.shape_keys.animation_data; ocup = set()
        if ad and ad.action:
            for fc in _curvas(ad.action).values():
                if fc.data_path == 'key_blocks["Closed"].value':
                    ocup = {int(round(k.co.x)) for k in fc.keyframe_points if k.co.y > 0.01}
        f = rng.randint(20, 60); frames_b = []
        while f + BLINK < fin_ojos[quien]:
            if all(abs(f - x) > 30 for x in ocup): frames_b.append(f)
            f += rng.randint(72, 120)                                          # cada 3-5 s
        for n in nombres:
            ck = bpy.data.objects[n].data.shape_keys.key_blocks["Closed"]; puestos = []
            for b0 in frames_b:
                for off in range(0, BLINK + 2):
                    fr = b0 + off - 1
                    ck.value = _blink(off) if 1 <= off <= BLINK else 0.0
                    ck.keyframe_insert("value", frame=fr); puestos.append(fr)
            ck.value = 0.0; hechos_b[n] = puestos
        print("PARPADEOS", quien, frames_b)
    sc[MARCA + "_parpadeos"] = hechos_b
    print("FILTROS ORGANICOS: Alfred y Jerry (1-%d)" % FIN)


if __name__ in ("__main__", "x"):
    construir()
