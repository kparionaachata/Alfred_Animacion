# -*- coding: utf-8 -*-
"""Hoja de contacto de fotogramas (Workbench) para revisar la animacion de bonobos/Alfred. Uso:
    hoja([f1,f2,...], centro=(x,y,z), off=(dx,dy,dz), archivo='nombre', visibles=None|'todo'|[nombres], res=240)
Guarda PNG por fotograma en %TEMP%/prev/ y devuelve las rutas. No toca la escena (restaura engine, visibilidad, camara y frame)."""
import bpy, os, mathutils, math

OUT = os.path.join(os.environ.get('TEMP', r'C:\Temp'), 'prev')
os.makedirs(OUT, exist_ok=True)


def hoja(frames, centro, off=(-2.4, -1.8, 1.4), archivo='hoja', visibles=None, res=240, mira=None, lente=32, color=(0.85, 0.85, 0.85), singlecolor=True):
    sc = bpy.context.scene; r = sc.render; im = r.image_settings
    cam = bpy.data.objects.get('Cam_prev')
    if cam is None:
        cd = bpy.data.cameras.new('Cam_prev'); cam = bpy.data.objects.new('Cam_prev', cd); sc.collection.objects.link(cam)
    cam.data.lens = lente; cam.data.clip_start = 0.05; cam.data.clip_end = 400
    cam0 = sc.camera; f0 = sc.frame_current; eng0 = r.engine; res0 = (r.resolution_x, r.resolution_y, r.resolution_percentage)
    mt0 = im.media_type; fp0 = r.filepath
    estado = {o.name: o.hide_render for o in bpy.data.objects}
    if visibles != 'todo':
        keep = set(visibles or [])
        # por defecto: Alfred, bonobos, objetos del guion (prefijo bm_) y la camara de prueba
        for o in bpy.data.objects:
            if o.name in keep or o.name == 'Cam_prev' or o.name.startswith('bm_'):
                continue
            o.hide_render = True
        for o in bpy.data.objects:
            if o.name in ('alfred', 'Armature') or (o.parent and (o.parent.name == 'Armature' or o.parent.name == 'alfred')):
                o.hide_render = False
            if any(o.name.startswith(p) for p in ('bonobo', 'mesh_root_bonobo', 'Mesh_0_bonobo', 'Ojo_', 'Pupila_', 'Ceja_', 'Brillo_', 'Nariz', 'Boca_', 'stone_axe', 'rat_1', 'Mesh_0_1', 'body1_1',
                                                    'chicken', 'snake', 'Armature_chicken', 'Body_chicken', 'Head', 'Beak', 'Wing', 'Leg', 'Eyes', 'ojo_', 'pupila', 'parpado', 'ceja')):
                o.hide_render = False
    r.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading; sh.light = 'STUDIO'
    if singlecolor:
        sh.color_type = 'SINGLE'; sh.single_color = color
    else:
        sh.color_type = 'TEXTURE'
    r.resolution_x = res; r.resolution_y = res; r.resolution_percentage = 100
    im.media_type = 'IMAGE'; im.file_format = 'PNG'
    sc.camera = cam
    mk = [(m, m.camera) for m in sc.timeline_markers]
    for m, _c in mk:
        m.camera = None                              # si no, el render cambia a la camara del marcador
    rutas = []
    try:
        for k, f in enumerate(frames):
            sc.frame_set(int(f))
            sc.camera = cam                              # los marcadores de camara cambian sc.camera en frame_set
            c = centro(f) if callable(centro) else centro
            c = mathutils.Vector(c)
            cam.location = c + mathutils.Vector(off)
            tgt = mathutils.Vector(mira(f) if callable(mira) else (mira if mira else c))
            d = tgt - cam.location
            cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
            r.filepath = os.path.join(OUT, '%s_%02d.png' % (archivo, k))
            bpy.ops.render.render(write_still=True)
            rutas.append(r.filepath)
    finally:
        for m, c_ in mk:
            m.camera = c_
        for o in bpy.data.objects:
            if o.name in estado:
                o.hide_render = estado[o.name]
        r.engine = eng0; sc.camera = cam0; r.resolution_x, r.resolution_y, r.resolution_percentage = res0
        im.media_type = mt0; r.filepath = fp0
        sc.frame_set(f0)
    return rutas
