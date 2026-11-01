# -*- coding: utf-8 -*-
"""alfred_cueva_5A.blend: toma cinematografica de la camara (Camera.001) con el add-on Replay Mod (replay_mod_blender.py).
Conserva las primeras tomas (Alfred picando, frames 1-178) y desde el 178 agrega: primer plano de Alfred descubriendo la caverna (178-232),
giro rapido hacia la caverna (232-258) y vuelo cinematografico por ella, bajando hacia los lagos de lava (258-440), 60 frames mas dentro de la caverna (440-520), VIAJE EXTRA de 300 frames (520-860, TOUR) dando una vuelta por la caverna a baja altura para capturar a las criaturas que caminan, giro para mirar hacia Alfred y Jerry (860-890) y regreso para grabarlos (890-920), quieta enfocandolos hasta el 1246, y desde ahi siguiendo la caida y los rebotes del pico (1246-1380).
Crea el path `CameraPath_Caverna` en los ajustes del Replay Mod (World.replay_settings) y lo aplica con `replay.apply_camera_path`.
Uso en Blender (con el add-on Replay Mod registrado): exec(open(ruta, encoding="utf8").read()); construir()   (repetible)
"""
import bpy, math
from mathutils import Euler

CAMARA = "Camera.001"
PATH = "CameraPath_Caverna"
# (frame, (x, y, z), yaw, pitch_abajo, lente). yaw 0 = mira +Y (a Alfred), 180 = mira -Y (a la caverna); pitch negativo = mira hacia arriba
NUEVOS = [
    (200, (0.51, 82.35, 67.62), 3, 0, 24),      # empuja hacia su cara: lo descubre
    (232, (0.51, 82.55, 67.66), 3, 0, 28),      # primer plano de su reaccion
    (258, (0.51, 81.90, 67.30), 180, 6, 24),     # giro rapido: la caverna entra en cuadro
    (300, (0.40, 76.00, 66.80), 183, 8, 20),     # sale del tunel a la caverna
    (350, (-2.0, 66.0, 63.50), 190, 14, 18),     # baja despacio
    (400, (-8.0, 54.0, 57.00), 205, 20, 18),     # barre hacia las cascadas de lava
    (440, (-14.0, 44.0, 52.00), 222, 24, 18),    # sobre los lagos
    (480, (-20.0, 38.0, 48.00), 238, 20, 18),    # sigue adentrandose en la caverna
    (520, (-24.0, 34.0, 45.00), 250, 16, 18),    # lo mas profundo del viaje; desde aqui el VIAJE EXTRA (TOUR) de 300 frames
]
INSERTADOS = 300                                 # frames insertados en el viaje (insertar_frames.py desde el 570): todo lo de Alfred/Jerry/pico va 300 frames despues
F_TOUR = (520, 860)
VUELTA = 360                                     # el viaje extra da una vuelta completa (CCW): la guinada final suma 360 deg
NUEVOS_B = [
    (860, (-24.0, 34.0, 45.50), 333 + VUELTA, -16, 16),   # gira para mirar hacia Alfred y Jerry: se ve lo enorme que es la caverna
    (890, (-6.0, 62.0, 60.00), 345 + VUELTA, -15, 20),    # regresa hacia ellos
    (910, (0.10, 76.5, 66.30), 358 + VUELTA, 0, 26),
    (920, (0.2218, 80.686, 66.719), 360 + VUELTA, 0, 28), # los graba de cerca a los dos en la salida (posicion indicada por el usuario)
    (946 + INSERTADOS, (0.2218, 80.686, 66.719), 360 + VUELTA, 0, 28),  # sigue con ellos hasta que Alfred termina de hablar; de aqui sigue al pico (_seguir_pico)
]
# puntos del recorrido bajo del viaje extra (tiempo, x, y, z): vuelta antihoraria alrededor del centro de la caverna que pasa cerca del suelo
RUTA = [(520, -24, 34, 45), (560, -27, 20, 36), (600, -18, 5, 28), (650, -4, -4, 24), (700, 10, 0, 24), (750, 18, 16, 27),
        (790, 17, 38, 34), (820, 8, 54, 40), (845, -10, 50, 44), (860, -24, 34, 45.5)]


def _tour():
    """claves cada 10 frames del recorrido RUTA (Catmull-Rom); mira hacia el interior (50 deg a la izquierda del avance) y 24 deg hacia abajo; se aparta de la roca"""
    from mathutils import Vector
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    P = [(t, Vector((x, y, z))) for t, x, y, z in RUTA]
    def en(t):
        for i in range(len(P) - 1):
            (t0, p0), (t1, p1) = P[i], P[i + 1]
            if t0 <= t <= t1:
                m0 = (P[i + 1][1] - P[i - 1][1]) / (P[i + 1][0] - P[i - 1][0]) if i > 0 else (p1 - p0) / (t1 - t0)
                m1 = (P[i + 2][1] - P[i][1]) / (P[i + 2][0] - P[i][0]) if i + 2 < len(P) else (p1 - p0) / (t1 - t0)
                u = (t - t0) / float(t1 - t0)
                h = t1 - t0
                return (2 * u**3 - 3 * u**2 + 1) * p0 + (u**3 - 2 * u**2 + u) * h * m0 + (-2 * u**3 + 3 * u**2) * p1 + (u**3 - u**2) * h * m1
        return P[-1][1]
    dirs = [Vector(v).normalized() for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1), (1, 1, 0), (-1, -1, 0), (1, -1, 0), (-1, 1, 0))]
    S = lambda x: (lambda u: u * u * (3 - 2 * u))(max(0.0, min(1.0, x)))
    pts, yaw_prev = [], None
    YAW0, YAW1 = 250.0, 333.0 + VUELTA                   # yaw con que llega (frame 520) y con el que sale a mirar hacia Alfred y Jerry (frame 860)
    for t in range(F_TOUR[0] + 10, F_TOUR[1], 10):
        c = en(t)
        for _ in range(8):                                  # despejar: nada de roca a menos de 2.5 m (sube si hay)
            libre = True
            for d in dirs:
                ok, hp, nor, idx, ob, mw = sc.ray_cast(dg, c, d, distance=2.5)
                if ok:
                    libre = False
                    break
            if libre:
                break
            c = c + Vector((0, 0, 2.0))
        a, b = en(max(F_TOUR[0], t - 4)), en(min(F_TOUR[1], t + 4))
        tg = b - a
        yaw = math.degrees(math.atan2(-tg.x, tg.y)) + 50.0
        ref = yaw_prev if yaw_prev is not None else YAW0
        while yaw - ref > 180:
            yaw -= 360
        while yaw - ref < -180:
            yaw += 360
        yaw_prev = yaw
        pts.append((t, c, yaw))
    # giro suave: al entrar parte del yaw de 520 y al salir llega al de 860 en ~100 frames (sin saltos de decenas de grados en 10 frames)
    N_IN, N_OUT = 100.0, 170.0
    out = []
    for t, c, yaw in pts:
        w_in = S((t - F_TOUR[0]) / N_IN)
        w_out = S((t - (F_TOUR[1] - N_OUT)) / N_OUT)
        y = (1 - w_in) * YAW0 + w_in * ((1 - w_out) * yaw + w_out * YAW1)
        out.append((t, (c.x, c.y, c.z), y, 24, 18))
    return out


def _seguir_pico():
    """claves de camara desde el 946 + INSERTADOS: se inclina a ver caer el pico (alfred_pico_piedra) desde la salida del tunel, y tras el primer rebote baja hacia el y lo sigue
    (a una distancia fija y mirandolo) por cada rebote hasta que queda quieto. Posiciones del pico leidas de sus claves; se evita que el suelo tape la vista."""
    import math
    from mathutils import Vector
    from bpy_extras import anim_utils
    sc = bpy.context.scene
    pico = bpy.data.objects["alfred_pico_piedra"]
    cbp = anim_utils.action_get_channelbag_for_slot(pico.animation_data.action, pico.animation_data.action_slot)
    fcs = [cbp.fcurves.find("location", index=i) for i in range(3)]
    pos = lambda f: Vector([fc.evaluate(f) for fc in fcs])
    boca = Vector((0.2218, 80.686, 66.719))
    OFF = Vector((-2.0, -2.6, 1.4))
    S = lambda t: (lambda x: x * x * (3 - 2 * x))(max(0.0, min(1.0, t)))
    D = INSERTADOS
    out, yaw_prev = [], 360.0 + VUELTA
    dg = bpy.context.evaluated_depsgraph_get()

    def mira(c, t, f, lens):
        nonlocal yaw_prev
        d = pos(f) - c
        pit = math.degrees(math.asin(max(-1.0, min(1.0, -d.z / d.length))))
        if pit < 78:
            yaw = math.degrees(math.atan2(-d.x, d.y))
            while yaw - yaw_prev > 180:
                yaw -= 360
            while yaw - yaw_prev < -180:
                yaw += 360
            yaw_prev = yaw
        out.append((f, (c.x, c.y, c.z), yaw_prev, min(pit, 88.0), lens))
    for f in (952 + D, 958 + D):                                       # se inclina desde la salida del tunel
        mira(boca, 0, f, 24 if f == 952 + D else 18)
    for f in range(964 + D, 1081 + D, 6):
        e = S((f - (960 + D)) / 48.0)                                   # baja hacia el pico entre el 960 y el 1008 (+ D)
        objetivo = pos(max(960 + D, f - 6)) + OFF
        c = boca.lerp(objetivo, e)
        for _ in range(8):                                              # que el suelo no tape: sube hasta que el rayo camara -> pico quede libre
            d = pos(f) - c
            ok, hp, nor, idx, ob, mw = sc.ray_cast(dg, c, d.normalized(), distance=max(0.1, d.length - 0.3))
            if not ok:
                break
            c = c + Vector((0, 0, 1.5))
        mira(c, 0, f, 18 + 14 * e)
    return out


def construir():
    sc = bpy.context.scene
    cam = bpy.data.objects[CAMARA]
    ws = sc.world.replay_settings
    ws.active_camera = cam
    ws.record_focus = False
    ws.orbit_focus = False
    # primeras tomas: se leen de la camara tal como esta (si ya hay un path aplicado se reutilizan sus claves 1-178)
    previas = []
    if cam.animation_data and cam.animation_data.action:
        from bpy_extras import anim_utils
        cb = anim_utils.action_get_channelbag_for_slot(cam.animation_data.action, cam.animation_data.action_slot)
        frames = sorted({int(k.co.x) for fc in cb.fcurves for k in fc.keyframe_points if k.co.x <= 178})
        for f in frames:
            sc.frame_set(f)
            e = cam.matrix_world.to_euler('XYZ', Euler((math.pi / 2, 0, 0)))
            previas.append((f, tuple(cam.location), tuple(e), cam.data.lens))
        sc.frame_set(1)
    for i in [i for i, p in enumerate(ws.camera_paths) if p.name == PATH][::-1]:
        ws.camera_paths.remove(i)
    path = ws.camera_paths.add()
    path.name = PATH
    path.interpolation = 'BEZIER'
    for f, loc, rot, lens in previas:
        kf = path.keyframes.add()
        kf.frame = f
        kf.location_x, kf.location_y, kf.location_z = loc
        kf.rotation_x, kf.rotation_y, kf.rotation_z = rot
        kf.fov = lens
    for f, loc, yaw, pit, lens in NUEVOS + _tour() + NUEVOS_B + _seguir_pico():
        kf = path.keyframes.add()
        kf.frame = f
        kf.location_x, kf.location_y, kf.location_z = loc
        kf.rotation_x, kf.rotation_y, kf.rotation_z = math.radians(90 - pit), 0.0, math.radians(yaw)
        kf.fov = lens
    ws.active_path = [p.name for p in ws.camera_paths].index(PATH)
    bpy.ops.replay.apply_camera_path()
    sc.frame_end = max(sc.frame_end, 1080 + INSERTADOS)
    sc.camera = cam
    sc.frame_set(1)
    return len(path.keyframes)


def luz_reflejo_lava():
    """Luz de area anaranjada delante de la salida del tunel: simula el brillo de los lagos y cascadas de lava reflejado en las paredes,
    para que Alfred, Jerry y la salida no queden a oscuras en las tomas finales (frames 480-560)."""
    import mathutils
    sc = bpy.context.scene
    nombre = "caverna_luz_reflejo_lava"
    if nombre in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[nombre], do_unlink=True)
    d = bpy.data.lights.new(nombre, 'AREA')
    d.shape, d.size, d.size_y = 'RECTANGLE', 16, 10
    d.color, d.energy, d.spread = (1.0, 0.35, 0.08), 3500, math.radians(150)
    o = bpy.data.objects.new(nombre, d)
    sc.collection.objects.link(o)
    o.location = (0.5, 72.0, 62.0)
    for f, v in ((1, 0.0), (880, 0.0), (905, 3500.0), (1250, 3500.0), (1262, 0.0), (sc.frame_end, 0.0)):    # solo se enciende para el plano final de Alfred y Jerry (905-1250): en el viaje no hay luz cercana que brille en el techo
        d.energy = v
        d.keyframe_insert("energy", frame=f)
    d.energy = 0.0
    o.rotation_euler = (mathutils.Vector((0.3, 83.8, 66.0)) - o.location).to_track_quat('-Z', 'Y').to_euler()
    return o.name
