# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: 2 slimes (estructura_lista/slime_1.blend: `slime_1` + `slima.arma_slime_1` + `slime.body_slime_1` + `slime.inner_body_slime_1`) que saltan por el suelo de la
caverna como en el juego (Minecraft Java, valores en ticks de 20/s, convertidos a 24 fps):
  - esperan en el suelo un tiempo al azar de 10 a 29 ticks (`getJumpDelay`: nextInt(20) + 10) y saltan;
  - el salto sale con velocidad vertical 0.42 bloques/tick, gravedad 0.08 y rozamiento 0.98 por tick (se simula tick a tick: ~10 ticks en el aire, ~1.1 bloques de altura);
  - solo se desplazan en el aire (~2 m por salto) y cambian de rumbo al azar cada 40 a 99 ticks (con un pequeno desvio en cada salto);
  - estiran / aplastan el cuerpo como el modelo del juego: se agachan antes de saltar, se estiran al despegar y se aplastan al caer (escala del empty `slime_1`, que tiene el origen en la base).
Igual que las criaturas, cada slime cruza por el punto del suelo que la camara mira (T_CAM) y pisa el suelo real (raycast BVH), sin lava ni desniveles de mas de 1 bloque.
Cada empty guarda sus saltos en la propiedad `saltos` (JSON: [(frame_despegue, frame_aterrizaje)]) para los sonidos (camara_caverna_sonidos.py: entity.slime.jump_small / squish_small).
Uso en Blender: exec(open(ruta, encoding="utf8").read()); construir()      (repetible: borra los slimes anteriores)
"""
import bpy, math, random, json
from mathutils import Vector

BASE = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/"
BLEND = "C:/Users/user/Desktop/Alfred_Animacion/estructura_lista/slime_1.blend"
RAIZ = "slime_1"
COL = "caverna_criaturas"
F0, F1 = 250, 900
FPS_TICK = 24.0 / 20.0                         # frames por tick del juego
SLIMES = [(660, 18), (770, 18)]                # (frame en que la camara los mira, grados bajo el centro del cuadro)
DIST_SALTO = 2.0                               # m que avanza en cada salto
SEMILLA = 17
MAX_ESCALON = 1.05


def _salto_vertical():
    """altura (bloques) en cada tick del salto con la fisica del juego: vy = 0.42; y += vy; vy = (vy - 0.08) * 0.98 hasta volver a y <= 0"""
    y, vy, hs = 0.0, 0.42, [0.0]
    while True:
        y += vy
        vy = (vy - 0.08) * 0.98
        if y <= 0:
            break
        hs.append(y)
    return hs                                  # hs[tick] ; len(hs) = ticks en el aire


def _altura(hs, u):
    """altura en bloques para u en [0, 1] del tiempo en el aire (interpola entre ticks)"""
    x = u * len(hs)
    i = int(x)
    a = hs[min(i, len(hs) - 1)]
    b = hs[i + 1] if i + 1 < len(hs) else 0.0
    return a + (b - a) * (x - i)


def _traer(k):
    obj = bpy.data.objects
    with bpy.data.libraries.load(BLEND, link=False) as (src, dst):
        raiz = obj_names = None
        dst.objects = [n for n in src.objects if n in (RAIZ, "slima.arma_slime_1", "slime.body_slime_1", "slime.inner_body_slime_1")]
    nuevos = [o for o in dst.objects if o is not None]
    col = bpy.data.collections.get(COL)
    if col is None:
        col = bpy.data.collections.new(COL)
        bpy.context.scene.collection.children.link(col)
    for o in nuevos:
        col.objects.link(o)
    raiz = next(o for o in nuevos if o.parent is None)
    raiz.name = "slime_cav_%d" % k
    return raiz


def _borrar(k):
    obj = bpy.data.objects
    r = obj.get("slime_cav_%d" % k)
    if r is not None:
        for o in list(r.children_recursive):
            obj.remove(o, do_unlink=True)
        obj.remove(r, do_unlink=True)


def _escala(fase, t):
    """(sx, sy, sz) segun la fase del salto; t = frames desde que empieza la fase"""
    if fase == "espera":
        return (1.0, 1.0, 1.0)
    return (1.0, 1.0, 1.0)


def construir():
    sc = bpy.context.scene
    O = bpy.data.objects
    cam = O["Camera.001"]
    cr = {"__name__": "criaturas_local"}
    exec(open(BASE + "criaturas_caverna.py", encoding="utf8").read(), cr)
    dg = bpy.context.evaluated_depsgraph_get()
    hs = _salto_vertical()
    n_aire = len(hs)
    f_aire = n_aire * FPS_TICK                                  # frames en el aire
    res = []
    for k, (t_cam, ang) in enumerate(SLIMES):
        rng = random.Random(SEMILLA + k)
        # ---- agenda de saltos: [(despegue, aterrizaje, rumbo)]
        saltos, f, rumbo, cambia = [], F0 + rng.randint(0, 20), rng.uniform(0, 2 * math.pi), 0.0
        while f < F1:
            espera = (rng.randint(0, 19) + 10) * FPS_TICK         # getJumpDelay: nextInt(20) + 10
            f += espera
            if f >= cambia:
                rumbo = rng.uniform(0, 2 * math.pi)
                cambia = f + (40 + rng.randint(0, 59)) * FPS_TICK
            saltos.append([f, f + f_aire, rumbo + rng.uniform(-0.17, 0.17)])
            f += f_aire
        # ---- posiciones de aterrizaje: ancladas en T en el salto que esta en el aire cuando la camara mira
        T, fwd = cr["_objetivo"](sc, dg, cam, t_cam, ang)
        dg = bpy.context.evaluated_depsgraph_get()
        j = min(range(len(saltos)), key=lambda i: abs(saltos[i][1] - t_cam))
        pos = {j: (T.x, T.y, T.z)}                                # aterrizaje del salto j
        for i in range(j + 1, len(saltos)):                       # hacia adelante
            x, y, z = pos[i - 1]
            for _ in range(24):
                h = saltos[i][2]
                nx, ny = x + math.cos(h) * DIST_SALTO, y + math.sin(h) * DIST_SALTO
                nz = cr["_piso"](sc, dg, nx, ny, z)
                if nz is not None and abs(nz - z) <= MAX_ESCALON and nz < 14:
                    break
                saltos[i][2] = rng.uniform(0, 2 * math.pi)
            else:
                nx, ny, nz = x, y, z
            pos[i] = (nx, ny, nz)
        for i in range(j - 1, -1, -1):                            # hacia atras (el salto i+1 sale del aterrizaje i)
            x, y, z = pos[i + 1]
            for _ in range(24):
                h = saltos[i + 1][2]
                px, py = x - math.cos(h) * DIST_SALTO, y - math.sin(h) * DIST_SALTO
                pz = cr["_piso"](sc, dg, px, py, z)
                if pz is not None and abs(pz - z) <= MAX_ESCALON and pz < 14:
                    break
                saltos[i + 1][2] = rng.uniform(0, 2 * math.pi)
            else:
                px, py, pz = x, y, z
            pos[i] = (px, py, pz)
        inicio = pos[0]
        # posicion de partida del primer salto: un salto antes del primer aterrizaje
        h0 = saltos[0][2]
        pre = (inicio[0] - math.cos(h0) * DIST_SALTO, inicio[1] - math.sin(h0) * DIST_SALTO, inicio[2])
        # ---- animacion
        _borrar(k)
        raiz = _traer(k)
        raiz.rotation_mode = 'XYZ'
        raiz["saltos"] = json.dumps([[round(a, 1), round(b, 1)] for a, b, _ in saltos])
        for fr in range(F0, F1 + 1):
            # salto actual / en espera
            idx = None
            for i, (a, b, h) in enumerate(saltos):
                if fr < a:
                    idx = i
                    break
                if a <= fr <= b:
                    idx = i
                    break
            if idx is None:
                idx = len(saltos) - 1
            a, b, h = saltos[idx]
            ant = pos[idx - 1] if idx > 0 else pre
            dest = pos[idx]
            if fr < a:                                            # en el suelo antes de saltar
                u = 0.0
            elif fr <= b:
                u = (fr - a) / (b - a)
            else:
                u = 1.0
            x = ant[0] + (dest[0] - ant[0]) * u
            y = ant[1] + (dest[1] - ant[1]) * u
            zs = ant[2] + (dest[2] - ant[2]) * u
            alt = _altura(hs, u) if 0 < u < 1 else 0.0
            # escala (aplasta / estira)
            sx = sy = sz = 1.0
            ta = a - fr                                           # frames que faltan para despegar
            tl = fr - b                                           # frames desde que aterrizo
            if 0 <= ta <= 5:                                      # se agacha antes de saltar
                p = 1 - ta / 5.0
                sz, sx = 1 - 0.25 * p, 1 + 0.12 * p
            elif 0 < u < 1:                                       # en el aire: estirado al despegar y al apice
                est = math.sin(math.pi * u)
                sz, sx = 1 + 0.18 * est, 1 - 0.07 * est
            elif tl >= 0 and tl <= 10 and idx < len(saltos):      # aplastado al caer y recupera con rebote
                p = tl / 10.0
                amort = math.exp(-3.0 * p) * math.cos(2 * math.pi * p * 1.2)
                sz, sx = 1 - 0.35 * amort, 1 + 0.2 * amort
            sy = sx
            rz = h - math.pi / 2
            raiz.location = (x, y, zs + alt)
            raiz.rotation_euler = (0, 0, rz)
            raiz.scale = (sx, sy, sz)
            raiz.keyframe_insert("location", frame=fr)
            raiz.keyframe_insert("rotation_euler", frame=fr)
            raiz.keyframe_insert("scale", frame=fr)
        from bpy_extras import anim_utils                          # rumbos continuos (sin saltos de 2 pi) y claves lineales
        cb = anim_utils.action_get_channelbag_for_slot(raiz.animation_data.action, raiz.animation_data.action_slot)
        for fc in cb.fcurves:
            if fc.data_path == "rotation_euler" and fc.array_index == 2:
                prev = None
                for kp in fc.keyframe_points:
                    if prev is not None:
                        while kp.co.y - prev > math.pi:
                            kp.co.y -= 2 * math.pi
                        while kp.co.y - prev < -math.pi:
                            kp.co.y += 2 * math.pi
                        kp.handle_left.y = kp.handle_right.y = kp.co.y
                    prev = kp.co.y
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
            fc.update()
        res.append((raiz.name, len(saltos), tuple(round(c, 1) for c in pos[j])))
    sc.frame_set(1)
    return res
