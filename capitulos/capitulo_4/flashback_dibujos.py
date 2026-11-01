# -*- coding: utf-8 -*-
"""alfred_cueva_5B.blend: dibujos a mano alzada (lapiz/tinta sobre pergamino, SIN texto) de the_stalker_1 en las cavernas para el montaje de flashbacks (flashback_rafaga.py).
Cada dibujo sale de una vista de la propia escena: se renderiza con Workbench (luz plana, contorno y cavidad, color unico claro) desde una camara temporal y despues se pasa por
un filtro de "lapiz" (dodge de desenfoque inverso + sombreado de lineas cruzadas + temblor de linea) sobre papel envejecido (mancha, grano, vineta). Salen a flashback_imagenes/dibujo_NN.png.
Uso en Blender: exec(open(ruta, encoding="utf8").read()); renderizar([0,1,2]); dibujar([0,1,2])      (repetible; la camara de la escena y el motor se restauran siempre)
"""
import bpy, math, os, random
import numpy as np
from mathutils import Vector

CARPETA = "C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/flashback_imagenes/"
RAW = CARPETA + "_raw/"
W, H = 1280, 720
# (frame de la escena, azimut respecto al frente del Stalker en grados, distancia, altura de camara, lente, altura del objetivo)
VISTAS = [
    (560, 20, 6.0, 7.5, 28, 7.2),     # 0 primer andar, plano general
    (590, -50, 5.0, 6.4, 24, 7.5),    # 1 contrapicado
    (630, 90, 7.0, 8.5, 30, 7.2),     # 2 de perfil
    (660, 160, 6.0, 8.0, 28, 7.4),    # 3 de espaldas
    (700, 0, 2.6, 8.0, 40, 8.0),      # 4 primer plano de la cabeza
    (720, -120, 8.0, 10.0, 24, 7.0),  # 5 picado, caverna ancha
    (745, 45, 4.0, 5.5, 20, 7.8),     # 6 contrapicado extremo
    (500, 10, 7.0, 8.0, 28, 8.2),     # 7 sosteniendo al zombie
    (535, 30, 9.0, 9.0, 26, 7.5),     # 8 la guarida (herramientas y extremidades)
    (770, 200, 10.0, 7.0, 26, 7.2),   # 9 lejos, de espaldas
]


def renderizar(indices):
    sc = bpy.context.scene
    st = bpy.data.objects["the_stalker_1"]
    os.makedirs(RAW, exist_ok=True)
    guardado = dict(motor=sc.render.engine, cam=sc.camera, rx=sc.render.resolution_x, ry=sc.render.resolution_y, pct=sc.render.resolution_percentage, ruta=sc.render.filepath,
                    fmt=sc.render.image_settings.file_format, frame=sc.frame_current, mundo=sc.world, trans=sc.render.film_transparent)
    col_fb = bpy.data.collections.get("flashback_rafaga")
    ocultos = col_fb.hide_render if col_fb else None
    cam_d = bpy.data.cameras.new("sketch_cam")
    cam = bpy.data.objects.new("sketch_cam", cam_d)
    sc.collection.objects.link(cam)
    w_tmp = bpy.data.worlds.new("sketch_world")
    w_tmp.use_nodes = False
    w_tmp.color = (1, 1, 1)
    try:
        sc.render.engine = 'BLENDER_WORKBENCH'
        sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
        sc.render.image_settings.file_format = 'PNG'
        sc.render.film_transparent = False
        sc.world = w_tmp
        sh = sc.display.shading
        sh.light = 'STUDIO'
        sh.color_type = 'SINGLE'
        sh.single_color = (0.85, 0.85, 0.85)
        sh.show_cavity = True
        sh.cavity_type = 'BOTH'
        sh.show_object_outline = True
        sh.object_outline_color = (0, 0, 0)
        sh.background_type = 'WORLD'
        sc.display.render_aa = '8'
        if col_fb:
            col_fb.hide_render = True
        sc.camera = cam
        for i in indices:
            fr, az, dist, h, lente, objz = VISTAS[i]
            sc.frame_set(fr)
            yaw = st.matrix_world.to_euler().z
            f = Vector((-math.sin(yaw), math.cos(yaw), 0))
            r = Vector((math.cos(yaw), math.sin(yaw), 0))
            c = Vector(st.matrix_world.translation)
            a = math.radians(az)
            d = f * math.cos(a) + r * math.sin(a)
            cam.location = Vector((c.x + d.x * dist, c.y + d.y * dist, h))
            tg = Vector((c.x, c.y, objz))
            cam.rotation_euler = (tg - cam.location).to_track_quat('-Z', 'Y').to_euler()
            cam_d.lens = lente
            cam_d.clip_start = 0.1
            cam_d.clip_end = 400
            sc.render.filepath = RAW + "raw_%02d.png" % i
            bpy.ops.render.render(write_still=True)
    finally:
        sc.camera = guardado["cam"]
        sc.render.engine = guardado["motor"]
        sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = guardado["rx"], guardado["ry"], guardado["pct"]
        sc.render.filepath = guardado["ruta"]
        sc.render.image_settings.file_format = guardado["fmt"]
        sc.render.film_transparent = guardado["trans"]
        sc.world = guardado["mundo"]
        if col_fb is not None:
            col_fb.hide_render = ocultos
        bpy.data.objects.remove(cam)
        bpy.data.cameras.remove(cam_d)
        bpy.data.worlds.remove(w_tmp)
        sc.frame_set(guardado["frame"])


def _desenfoque(a, n):
    """desenfoque gaussiano aproximado con cajas separables"""
    k = np.ones(n) / n
    for _ in range(3):
        a = np.apply_along_axis(lambda m: np.convolve(m, k, mode='same'), 1, a)
        a = np.apply_along_axis(lambda m: np.convolve(m, k, mode='same'), 0, a)
    return a


def _cargar(ruta):
    im = bpy.data.images.load(ruta, check_existing=False)
    w, h = im.size
    a = np.empty(w * h * 4, dtype=np.float32)
    im.pixels.foreach_get(a)
    bpy.data.images.remove(im)
    return a.reshape(h, w, 4)[:, :, :3]


def _papel(h, w, rnd):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    base = np.array([0.93, 0.84, 0.66], dtype=np.float32)
    papel = np.ones((h, w, 3), dtype=np.float32) * base
    ruido = np.random.RandomState(rnd.randint(0, 99999)).rand(h // 8 + 1, w // 8 + 1).astype(np.float32)
    ruido = np.kron(ruido, np.ones((8, 8), dtype=np.float32))[:h, :w]
    ruido = _desenfoque(ruido, 21)
    papel *= (0.90 + 0.18 * ruido)[:, :, None]
    # manchas oscuras en los bordes y vineta
    dx = (x - w / 2) / (w / 2)
    dy = (y - h / 2) / (h / 2)
    vin = 1.0 - 0.38 * np.clip(dx ** 2 + dy ** 2 - 0.35, 0, 1.6)
    papel *= vin[:, :, None]
    papel *= (1.0 - 0.06 * np.random.RandomState(rnd.randint(0, 99999)).rand(h, w, 1)).astype(np.float32)
    return np.clip(papel, 0, 1)


def dibujar(indices, semilla=3):
    rnd = random.Random(semilla)
    for i in indices:
        rgb = _cargar(RAW + "raw_%02d.png" % i)
        h, w = rgb.shape[:2]
        gris = rgb @ np.array([0.30, 0.59, 0.11], dtype=np.float32)
        lo, hi = np.percentile(gris, 2), np.percentile(gris, 98)
        gn = np.clip((gris - lo) / max(hi - lo, 1e-3), 0, 1)              # contraste normalizado
        gy, gx = np.gradient(_desenfoque(gn, 3))
        borde = np.hypot(gx, gy)
        borde = np.clip(borde / max(np.percentile(borde, 99.3), 1e-4), 0, 1)       # contornos (sobel)
        bl = _desenfoque(1.0 - gn, 9)
        suave = 1.0 - np.clip(gn / np.clip(1.0 - bl, 0.04, 1.0), 0, 1)         # trazo "dodge" de lapiz suave
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        sombra = np.clip((0.55 - gn) / 0.45, 0, 1)
        hat1 = (np.sin((x + y) * 0.50) > 0.30).astype(np.float32)
        hat2 = (np.sin((x - y) * 0.50) > 0.45).astype(np.float32)
        tinta = np.clip(1.5 * borde ** 0.8 + 0.7 * suave + sombra * (0.55 * hat1 + 0.40 * hat2 * (sombra > 0.55)), 0, 1)
        # temblor de mano: desplazar la tinta con un campo suave
        rs = np.random.RandomState(rnd.randint(0, 99999))
        dxs = _desenfoque(rs.randn(h, w).astype(np.float32), 61) * 90
        dys = _desenfoque(rs.randn(h, w).astype(np.float32), 61) * 90
        xi = np.clip((x + dxs * 6).astype(int), 0, w - 1)
        yi = np.clip((y + dys * 6).astype(int), 0, h - 1)
        tinta = tinta[yi, xi]
        tinta *= (0.80 + 0.20 * rs.rand(h, w)).astype(np.float32)
        papel = _papel(h, w, rnd)
        color_tinta = np.array([0.13, 0.09, 0.06], dtype=np.float32)
        res = papel * (1 - 0.92 * tinta[:, :, None]) + color_tinta * tinta[:, :, None] * 0.12
        res = np.clip(res, 0, 1)
        im = bpy.data.images.new("dibujo_tmp", w, h, alpha=True)
        out = np.concatenate([res, np.ones((h, w, 1), dtype=np.float32)], axis=2)
        im.pixels.foreach_set(np.ascontiguousarray(out).astype(np.float32).reshape(-1))
        im.filepath_raw = CARPETA + "dibujo_%02d.png" % i
        im.file_format = 'PNG'
        im.save()
        bpy.data.images.remove(im)
