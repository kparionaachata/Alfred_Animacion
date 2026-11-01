# -*- coding: utf-8 -*-
"""alfred_cueva_5B.blend: dibujos en estilo GRABADO / TINTA CHINA (referencias del usuario): silueta negra de the_stalker_1 con ojos y dientes blancos, fondo palido con luz de
contraluz y cueva negra punteada (tramado de puntos), borde crema fino alrededor de la silueta. SIN texto.
Por cada vista de flashback_dibujos.VISTAS se renderizan 4 pasadas Workbench (fondo en arcilla, silueta, ojos, dientes) y se componen con tramado.
Salen a flashback_imagenes/tinta_NN.png. Requiere haber ejecutado antes flashback_dibujos.py (usa VISTAS, RAW, CARPETA, W, H, _desenfoque).
Uso: exec(flashback_dibujos.py); exec(este); renderizar_pasadas([0,1,2]); tinta([0,1,2])
"""
import bpy, math, os
import numpy as np
from mathutils import Vector

CRIATURA = ["Mesh_0_1", "Mesh_1", "Mesh_2_1", "Mesh_3_1", "stalker_fx_fragmentos", "stalker_fx_fragmentos_cabeza", "stalker_fx_boca", "stalker_fx_rojos_pecho", "stalker_fx_gotas_ojos"]
OJOS = ["Ojo_Terror_Rombo_L_1", "Ojo_Terror_Rombo_R_1"]
DIENTES_OBJ = ["Mesh_1", "Mesh_0_1"]
# FRAGMENTOS (indices 10-18): la criatura NUNCA se ve entera, solo una parte en encuadre cerrado o muy lejos y diminuta (el miedo a lo desconocido)
# (frame, azimut, distancia, altura de camara (0 = a la altura del objetivo), lente, altura objetivo, hueso al que apunta)
VISTAS += [
    (700, 0, 1.3, 8.2, 50, 8.0, "head_1"),          # 10 ojos y dientes en la oscuridad
    (620, 20, 1.0, 0, 60, 8.0, "jaw_1"),            # 11 la boca
    (640, 60, 1.6, 6.6, 45, 7.0, "finger_2.L_1"),   # 12 garras cerca del suelo
    (665, -70, 1.8, 6.4, 40, 7.0, "shin.R_1"),      # 13 pierna y pie
    (600, 10, 1.6, 7.9, 50, 7.0, "heart_1"),        # 14 la cavidad del pecho
    (720, 170, 1.8, 8.2, 45, 7.0, "spine_1"),       # 15 la espalda
    (580, -90, 14.0, 14.0, 35, 7.0, None),          # 16 diminuta y lejana desde arriba
    (690, 0, 3.0, 6.2, 20, 7.0, "thigh.L_1"),       # 17 contrapicado, solo las piernas
    (740, -20, 2.2, 8.4, 70, 8.0, "head_1"),        # 18 mirada fija entre sombras
]


def renderizar_pasadas(indices):
    sc = bpy.context.scene
    O = bpy.data.objects
    st = O["the_stalker_1"]
    os.makedirs(RAW, exist_ok=True)
    visibles = [o for o in O if o.type in ('MESH', 'CURVE', 'FONT', 'META', 'SURFACE') and not o.hide_render]
    modo_color = sc.render.image_settings.color_mode
    g = dict(motor=sc.render.engine, cam=sc.camera, rx=sc.render.resolution_x, ry=sc.render.resolution_y, pct=sc.render.resolution_percentage, ruta=sc.render.filepath,
             fmt=sc.render.image_settings.file_format, frame=sc.frame_current, mundo=sc.world, trans=sc.render.film_transparent, cm=sc.view_settings.view_transform)
    col_fb = bpy.data.collections.get("flashback_rafaga")
    ocultos = col_fb.hide_render if col_fb else None
    cols_mat = {nm: tuple(bpy.data.materials[nm].diffuse_color) for nm in ("Material_0.001", "Material_0.001_dientes_sin_brillo") if nm in bpy.data.materials}
    cam_d = bpy.data.cameras.new("sketch_cam")
    cam = bpy.data.objects.new("sketch_cam", cam_d)
    sc.collection.objects.link(cam)
    w_tmp = bpy.data.worlds.new("sketch_world")
    w_tmp.use_nodes = False
    w_tmp.color = (1, 1, 1)
    sh = sc.display.shading
    sh_prev = (sh.light, sh.color_type, tuple(sh.single_color), sh.show_cavity, sh.cavity_type, sh.show_object_outline)
    try:
        sc.render.engine = 'BLENDER_WORKBENCH'
        sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
        sc.render.image_settings.file_format = 'PNG'
        sc.render.image_settings.color_mode = 'RGBA'
        sc.view_settings.view_transform = 'Standard'
        sc.world = w_tmp
        sc.display.render_aa = '8'
        if col_fb:
            col_fb.hide_render = True
        sc.camera = cam
        for i in indices:
            fr, az, dist, h, lente, objz = VISTAS[i][:6]
            hueso = VISTAS[i][6] if len(VISTAS[i]) > 6 else None
            sc.frame_set(fr)
            yaw = st.matrix_world.to_euler().z
            f = Vector((-math.sin(yaw), math.cos(yaw), 0))
            r = Vector((math.cos(yaw), math.sin(yaw), 0))
            c = Vector(st.matrix_world.translation)
            a = math.radians(az)
            d = f * math.cos(a) + r * math.sin(a)
            cam.location = Vector((c.x + d.x * dist, c.y + d.y * dist, h))
            if hueso:                                   # fragmento: se apunta a un hueso (encuadre cerrado, la criatura nunca sale entera)
                ar = O["torso_1"]
                c = ar.matrix_world @ ar.pose.bones[hueso].head
                cam.location = Vector((c.x + d.x * dist, c.y + d.y * dist, h if h > 0 else c.z))
                objetivo = c
            else:
                objetivo = Vector((c.x, c.y, objz))
            cam.rotation_euler = (objetivo - cam.location).to_track_quat('-Z', 'Y').to_euler()
            cam_d.lens, cam_d.clip_start, cam_d.clip_end = lente, 0.1, 400
            # 1) fondo: la cueva en arcilla, sin la criatura ni los ojos
            sc.render.film_transparent = False
            sh.light, sh.color_type, sh.single_color = 'STUDIO', 'SINGLE', (0.85, 0.85, 0.85)
            sh.show_cavity, sh.cavity_type, sh.show_object_outline = True, 'BOTH', True
            for o in visibles:
                o.hide_render = o.name in CRIATURA or o.name in OJOS
            sc.render.filepath = RAW + "fondo_%02d.png" % i
            bpy.ops.render.render(write_still=True)
            # 2) silueta negra plana sobre transparente
            sc.render.film_transparent = True
            sh.light, sh.color_type, sh.single_color = 'FLAT', 'SINGLE', (0, 0, 0)
            sh.show_cavity, sh.show_object_outline = False, False
            for o in visibles:
                o.hide_render = o.name not in CRIATURA
            sc.render.filepath = RAW + "sil_%02d.png" % i
            bpy.ops.render.render(write_still=True)
            # 3) ojos en blanco
            sh.single_color = (1, 1, 1)
            for o in visibles:
                o.hide_render = o.name not in OJOS
            sc.render.filepath = RAW + "ojos_%02d.png" % i
            bpy.ops.render.render(write_still=True)
            # 4) dientes: caras del material de dientes en blanco, el resto de la malla en negro
            sh.color_type = 'MATERIAL'
            if "Material_0.001" in cols_mat:
                bpy.data.materials["Material_0.001"].diffuse_color = (0, 0, 0, 1)
            if "Material_0.001_dientes_sin_brillo" in cols_mat:
                bpy.data.materials["Material_0.001_dientes_sin_brillo"].diffuse_color = (1, 1, 1, 1)
            for o in visibles:
                o.hide_render = o.name not in DIENTES_OBJ
            sc.render.filepath = RAW + "dientes_%02d.png" % i
            bpy.ops.render.render(write_still=True)
            for nm, col in cols_mat.items():
                bpy.data.materials[nm].diffuse_color = col
    finally:
        for o in visibles:
            o.hide_render = False
        for nm, col in cols_mat.items():
            bpy.data.materials[nm].diffuse_color = col
        sh.light, sh.color_type, sh.single_color, sh.show_cavity, sh.cavity_type, sh.show_object_outline = sh_prev
        sc.camera = g["cam"]
        sc.render.engine = g["motor"]
        sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = g["rx"], g["ry"], g["pct"]
        sc.render.filepath = g["ruta"]
        sc.render.image_settings.file_format = g["fmt"]
        sc.render.image_settings.color_mode = modo_color
        sc.render.film_transparent = g["trans"]
        sc.view_settings.view_transform = g["cm"]
        sc.world = g["mundo"]
        if col_fb is not None:
            col_fb.hide_render = ocultos
        bpy.data.objects.remove(cam)
        bpy.data.cameras.remove(cam_d)
        bpy.data.worlds.remove(w_tmp)
        sc.frame_set(g["frame"])


def _rgba(ruta):
    im = bpy.data.images.load(ruta, check_existing=False)
    w, h = im.size
    a = np.empty(w * h * 4, dtype=np.float32)
    im.pixels.foreach_get(a)
    bpy.data.images.remove(im)
    return a.reshape(h, w, 4)


def _dilatar(m, n):
    out = m.copy()
    for dy in range(-n, n + 1):
        for dx in range(-n, n + 1):
            if dx * dx + dy * dy <= n * n:
                out = np.maximum(out, np.roll(np.roll(m, dy, 0), dx, 1))
    return out


def tinta(indices, semilla=5):
    rnd = np.random.RandomState(semilla)
    CREMA = np.array([0.95, 0.92, 0.82], dtype=np.float32)
    NEGRO = np.array([0.03, 0.03, 0.04], dtype=np.float32)
    for i in indices:
        fondo = _rgba(RAW + "fondo_%02d.png" % i)[:, :, :3]
        sil = _rgba(RAW + "sil_%02d.png" % i)[:, :, 3]
        ojo = _rgba(RAW + "ojos_%02d.png" % i)
        dien = _rgba(RAW + "dientes_%02d.png" % i)
        h, w = sil.shape
        ojos = ojo[:, :, 3] * ojo[:, :, :3].mean(axis=2)
        dientes = dien[:, :, 3] * np.clip((dien[:, :, :3].mean(axis=2) - 0.55) * 3, 0, 1)
        gris = fondo @ np.array([0.30, 0.59, 0.11], dtype=np.float32)
        lo, hi = np.percentile(gris, 2), np.percentile(gris, 98)
        gn = np.clip((gris - lo) / max(hi - lo, 1e-3), 0, 1)
        gy, gx = np.gradient(_desenfoque(gn, 3))
        borde = np.hypot(gx, gy)
        borde = np.clip(borde / max(np.percentile(borde, 99.3), 1e-4), 0, 1)
        ys, xs = np.nonzero(sil > 0.5)
        if len(xs):
            cx, cy = float(np.median(xs)), float(np.percentile(ys, 25))
        else:
            cx, cy = w / 2.0, h / 2.0
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        rad = np.hypot((x - cx) / (0.55 * w), (y - cy) / (0.75 * h))
        halo = np.exp(-(rad ** 2) * 1.3)
        B = (0.10 + 0.95 * halo) * (0.30 + 0.70 * gn)
        B = np.clip(B + 0.55 * borde * (0.25 + halo), 0, 1)
        veta = _desenfoque(np.tile(rnd.rand(1, w).astype(np.float32), (h, 1)), 5)
        B = np.clip(B * (0.85 + 0.30 * veta), 0, 1)
        ruido = np.kron(rnd.rand(h // 2 + 1, w // 2 + 1).astype(np.float32), np.ones((2, 2), dtype=np.float32))[:h, :w]
        pts = (B + (ruido - 0.5) * 0.55 > 0.5).astype(np.float32)
        s = (sil > 0.5).astype(np.float32)
        aro = np.clip(_dilatar(s, 3) - s, 0, 1)
        res = pts[:, :, None] * CREMA + (1 - pts[:, :, None]) * NEGRO
        res = res * (1 - s[:, :, None]) + NEGRO * s[:, :, None]
        res = res * (1 - aro[:, :, None] * 0.9) + CREMA * aro[:, :, None] * 0.9
        brillo = np.clip(_desenfoque(ojos + dientes, 15) * 2.5, 0, 1)
        res = res * (1 - brillo[:, :, None] * 0.55) + CREMA * brillo[:, :, None] * 0.55
        blanco = np.clip(ojos * 1.4 + dientes * 1.4, 0, 1)
        res = res * (1 - blanco[:, :, None]) + np.array([1, 1, 0.97], dtype=np.float32) * blanco[:, :, None]
        res *= (0.96 + 0.06 * rnd.rand(h, w, 1)).astype(np.float32)
        res = np.clip(res, 0, 1).astype(np.float32)
        im = bpy.data.images.new("tinta_tmp", w, h, alpha=True)
        out = np.concatenate([res, np.ones((h, w, 1), dtype=np.float32)], axis=2)
        im.pixels.foreach_set(np.ascontiguousarray(out).reshape(-1))
        im.filepath_raw = CARPETA + "tinta_%02d.png" % i
        im.file_format = 'PNG'
        im.save()
        bpy.data.images.remove(im)
