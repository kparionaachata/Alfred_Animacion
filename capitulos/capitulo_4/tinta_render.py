# -*- coding: utf-8 -*-
bl_info = {
    "name": "Tinta Render",
    "author": "Alfred Animacion",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "Vista 3D > Barra lateral (N) > Tinta",
    "description": "Renderiza toda una animacion con el efecto de grabado / tinta china (silueta negra, ojos y dientes blancos, contraluz y tramado de puntos) y lo muestra en la camara",
    "category": "Render",
}
"""Tinta Render: renderiza una animacion completa con el estilo de grabado en tinta (el de los flashbacks del capitulo 4).
Por cada frame se hacen 4 pasadas Workbench con la camara de la escena y se componen con numpy:
  1. fondo: toda la escena en arcilla gris (cavidad + contorno) SIN la criatura (la vista "tinta_fondo" excluye su coleccion);
  2. silueta: solo la coleccion de la criatura, plana y negra, sobre transparente (vista "tinta_sil", el resto de colecciones excluidas);
  3. ojos: solo los objetos de ojos, en blanco;  4. dientes: solo las caras del material de dientes, en blanco.
Composicion: contraluz pálido (degradado radial) detras de la cabeza + cueva oscura modulada por la arcilla, TRAMADO DE PUNTOS (estarcido con ruido en bloques de `punto` px) a dos colores
(crema/negro), silueta negra con borde crema fino, brillo de ojos/dientes y grano de papel. Salida: PNG tinta_NNNN.png en la carpeta elegida.
"Mostrar en la camara" pone esa secuencia como imagen de fondo de la camara (vista de camara de la Vista 3D) para ver el resultado reproduciendo la animacion.
Uso: panel "Tinta" (barra lateral N de la Vista 3D) -> elegir carpeta de salida, coleccion de la criatura, ojos y dientes ("Preparar Stalker" lo deja listo en este proyecto) ->
"Probar frame actual" -> "Renderizar animacion" (Esc cancela) -> "Mostrar en la camara".
Sin interfaz:  bpy.ops.tinta.preparar_stalker(); bpy.ops.tinta.probar(); bpy.ops.tinta.render_animacion()
"""
import bpy, os, math, shutil
import numpy as np
from bpy.props import (StringProperty, IntProperty, FloatProperty, BoolProperty, PointerProperty, FloatVectorProperty)
from bpy.types import PropertyGroup, Operator, Panel


# ------------------------------------------------------------------------------------------------------------------------------ propiedades
class TINTA_Props(PropertyGroup):
    salida: StringProperty(name="Carpeta de salida", subtype='DIR_PATH', default="//tinta_render/")
    inicio: IntProperty(name="Inicio", default=1, min=0)
    fin: IntProperty(name="Fin", default=250, min=1)
    paso: IntProperty(name="Paso", description="1 = todos los frames", default=1, min=1)
    escala: IntProperty(name="Resolucion %", description="Porcentaje de la resolucion de render (mas bajo = mucho mas rapido)", default=100, min=10, max=100)
    col_criatura: PointerProperty(name="Coleccion de la criatura", type=bpy.types.Collection)
    ojos: StringProperty(name="Objetos de los ojos", description="Nombres separados por coma", default="")
    dientes_obj: StringProperty(name="Objetos con dientes", description="Nombres separados por coma", default="")
    mat_dientes: StringProperty(name="Material de los dientes", default="")
    mats_cuerpo: StringProperty(name="Materiales del cuerpo (se ponen en negro en la pasada de dientes)", default="")
    punto: IntProperty(name="Tamano del punto (px)", default=2, min=1, max=6)
    halo_ancho: FloatProperty(name="Contraluz: ancho", default=0.70, min=0.1, max=2.0)
    halo_alto: FloatProperty(name="Contraluz: alto", default=0.90, min=0.1, max=2.0)
    halo_fuerza: FloatProperty(name="Contraluz: fuerza", default=0.95, min=0.0, max=2.0)
    borde: IntProperty(name="Borde crema (px)", default=3, min=0, max=10)
    ruido: FloatProperty(name="Dureza del tramado", description="Mas alto = mas granulado", default=0.55, min=0.0, max=1.5)
    semilla: IntProperty(name="Semilla", default=5)
    color_crema: FloatVectorProperty(name="Claro", subtype='COLOR', size=3, default=(0.95, 0.92, 0.82), min=0.0, max=1.0)
    color_negro: FloatVectorProperty(name="Oscuro", subtype='COLOR', size=3, default=(0.0, 0.0, 0.0), min=0.0, max=1.0)
    paso_prev: IntProperty(name="Vista previa: paso", description="Renderiza 1 de cada N frames y rellena los demas con el anterior", default=8, min=1)
    escala_prev: IntProperty(name="Vista previa: resolucion %", default=25, min=10, max=100)
    filtro_activo: BoolProperty(name="Filtro de tinta en tiempo real", description="Enciende / apaga el filtro en la vista de camara (compositor del viewport)", default=False, update=lambda self, ctx: _filtro_toggle(ctx))
    ver_camara: BoolProperty(name="Mostrar en la camara al terminar", default=True)


# ------------------------------------------------------------------------------------------------------------------------------ utilidades numericas
def _caja(a, n):
    """desenfoque de caja (ancho n) separable con sumas acumuladas; una pasada por eje"""
    r = max(1, n // 2)
    for eje in (0, 1):
        pad = [(0, 0), (0, 0)]
        pad[eje] = (r + 1, r)
        c = np.cumsum(np.pad(a, pad, mode='edge'), axis=eje, dtype=np.float32)
        if eje == 0:
            a = (c[2 * r + 1:] - c[:-(2 * r + 1)]) / (2 * r + 1)
        else:
            a = (c[:, 2 * r + 1:] - c[:, :-(2 * r + 1)]) / (2 * r + 1)
    return a


def _blur(a, n, veces=2):
    for _ in range(veces):
        a = _caja(a, n)
    return a


def _dilatar(m, n):
    out = m
    for eje in (0, 1):
        acum = out.copy()
        for d in range(1, n + 1):
            acum = np.maximum(acum, np.roll(out, d, eje))
            acum = np.maximum(acum, np.roll(out, -d, eje))
        out = acum
    return out


def _leer(ruta):
    im = bpy.data.images.load(ruta, check_existing=False)
    w, h = im.size
    a = np.empty(w * h * 4, dtype=np.float32)
    im.pixels.foreach_get(a)
    bpy.data.images.remove(im)
    return a.reshape(h, w, 4)


def componer(fondo, sil, ojos, dientes, p, rnd):
    """fondo: HxWx3 (arcilla), sil: HxW alfa de la criatura, ojos/dientes: HxW (0-1) -> HxWx3 en el estilo de tinta"""
    h, w = sil.shape
    crema = np.array(p.color_crema, dtype=np.float32)
    negro = np.array(p.color_negro, dtype=np.float32)
    gris = fondo @ np.array([0.30, 0.59, 0.11], dtype=np.float32)
    lo, hi = np.percentile(gris, 2), np.percentile(gris, 98)
    gn = np.clip((gris - lo) / max(hi - lo, 1e-3), 0, 1)
    gy, gx = np.gradient(_blur(gn, 3, 1))
    borde = np.hypot(gx, gy)
    borde = np.clip(borde / max(np.percentile(borde, 99.3), 1e-4), 0, 1)
    ys, xs = np.nonzero(sil > 0.5)
    if len(xs):
        cx, cy = float(np.median(xs)), float(np.percentile(ys, 25))
    else:
        cx, cy = w / 2.0, h / 2.0
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    rad = np.hypot((x - cx) / (p.halo_ancho * w), (y - cy) / (p.halo_alto * h))
    halo = np.exp(-(rad ** 2) * 1.3) * p.halo_fuerza
    B = (0.10 + 0.95 * halo) * (0.30 + 0.70 * gn)
    B = np.clip(B + 0.55 * borde * (0.25 + halo), 0, 1)
    veta = _blur(np.tile(rnd.rand(1, w).astype(np.float32), (h, 1)), 5, 1)
    B = np.clip(B * (0.85 + 0.30 * veta), 0, 1)
    b = p.punto
    ruido = np.kron(rnd.rand(h // b + 1, w // b + 1).astype(np.float32), np.ones((b, b), dtype=np.float32))[:h, :w]
    pts = (B + (ruido - 0.5) * p.ruido > 0.5).astype(np.float32)
    s = (sil > 0.5).astype(np.float32)
    aro = np.clip(_dilatar(s, p.borde) - s, 0, 1) if p.borde else np.zeros_like(s)
    res = pts[:, :, None] * crema + (1 - pts[:, :, None]) * negro
    res = res * (1 - s[:, :, None]) + negro * s[:, :, None]
    res = res * (1 - aro[:, :, None] * 0.9) + crema * aro[:, :, None] * 0.9
    brillo = np.clip(_blur(ojos + dientes, 15, 2) * 2.5, 0, 1)
    res = res * (1 - brillo[:, :, None] * 0.55) + crema * brillo[:, :, None] * 0.55
    blanco = np.clip((ojos + dientes) * 1.4, 0, 1)
    res = res * (1 - blanco[:, :, None]) + np.array([1, 1, 0.97], dtype=np.float32) * blanco[:, :, None]
    res *= (0.96 + 0.06 * rnd.rand(h, w, 1)).astype(np.float32)
    return np.clip(res, 0, 1).astype(np.float32)


# ------------------------------------------------------------------------------------------------------------------------------ renderizado por pasadas
def _nombres(txt):
    return [n.strip() for n in txt.split(",") if n.strip()]


class _Trabajo:
    """estado temporal del render por pasadas (se restaura siempre en cerrar())"""

    def __init__(self, context, escala=None, subcarpeta=""):
        self.sc = context.scene
        self.p = self.sc.tinta
        sc = self.sc
        if sc.camera is None:
            raise RuntimeError("La escena no tiene camara activa")
        if self.p.col_criatura is None:
            raise RuntimeError("Falta la coleccion de la criatura")
        self.crea = self.p.col_criatura
        self.objs = list(self.crea.all_objects)
        self.ojos = [o for o in self.objs if o.name in _nombres(self.p.ojos)]
        self.dientes = [o for o in self.objs if o.name in _nombres(self.p.dientes_obj)]
        sh = sc.display.shading
        self.g = dict(motor=sc.render.engine, rx=sc.render.resolution_percentage, ruta=sc.render.filepath, fmt=sc.render.image_settings.file_format,
                      modo=sc.render.image_settings.color_mode, trans=sc.render.film_transparent, mundo=sc.world, cm=sc.view_settings.view_transform,
                      vl=context.window.view_layer if context.window else None, aa=sc.display.render_aa,
                      sh=(sh.light, sh.color_type, tuple(sh.single_color), sh.show_cavity, sh.cavity_type, sh.show_object_outline, sh.background_type),
                      ocultos={o.name: o.hide_render for o in self.objs})
        self.cols_mat = {}
        for nm in [self.p.mat_dientes] + _nombres(self.p.mats_cuerpo):
            m = bpy.data.materials.get(nm)
            if m:
                self.cols_mat[nm] = tuple(m.diffuse_color)
        self.w_tmp = bpy.data.worlds.new("tinta_world")
        self.w_tmp.use_nodes = False
        self.w_tmp.color = (1, 1, 1)
        self.vl_fondo = sc.view_layers.new("tinta_fondo")
        self.vl_sil = sc.view_layers.new("tinta_sil")
        self._excluir()
        sc.render.engine = 'BLENDER_WORKBENCH'
        sc.render.resolution_percentage = escala if escala else self.p.escala
        sc.render.image_settings.file_format = 'PNG'
        sc.render.image_settings.color_mode = 'RGBA'
        sc.view_settings.view_transform = 'Standard'
        sc.world = self.w_tmp
        sc.display.render_aa = '8'
        self.dir = os.path.join(bpy.path.abspath(self.p.salida), subcarpeta) if subcarpeta else bpy.path.abspath(self.p.salida)
        self.raw = os.path.join(self.dir, "_pasadas")
        os.makedirs(self.raw, exist_ok=True)

    def _excluir(self):
        def contiene(lc):
            if lc.collection is self.crea:
                return True
            return any(contiene(h) for h in lc.children)

        def solo(lc):
            lc.exclude = not contiene(lc)
            if lc.collection is not self.crea:
                for h in lc.children:
                    solo(h)

        def sin(lc):
            if lc.collection is self.crea:
                lc.exclude = True
                return
            for h in lc.children:
                sin(h)
        for h in self.vl_sil.layer_collection.children:
            solo(h)
        for h in self.vl_fondo.layer_collection.children:
            sin(h)

    def _render(self, capa, nombre):
        self.sc.render.filepath = os.path.join(self.raw, nombre)
        bpy.ops.render.render(write_still=True, layer=capa)
        return _leer(os.path.join(self.raw, nombre) + ".png") if os.path.exists(os.path.join(self.raw, nombre) + ".png") else _leer(os.path.join(self.raw, nombre))

    def frame(self, fr):
        sc, p = self.sc, self.p
        sc.frame_set(fr)
        sh = sc.display.shading
        # 1) fondo en arcilla
        sc.render.film_transparent = False
        sh.light, sh.color_type, sh.single_color = 'STUDIO', 'SINGLE', (0.85, 0.85, 0.85)
        sh.show_cavity, sh.cavity_type, sh.show_object_outline, sh.background_type = True, 'BOTH', True, 'WORLD'
        fondo = self._render("tinta_fondo", "fondo")[:, :, :3]
        # 2) silueta plana y negra
        sc.render.film_transparent = True
        sh.light, sh.color_type, sh.single_color = 'FLAT', 'SINGLE', (0, 0, 0)
        sh.show_cavity, sh.show_object_outline = False, False
        for o in self.objs:
            o.hide_render = self.g["ocultos"][o.name]
        sil = self._render("tinta_sil", "sil")[:, :, 3]
        # 3) ojos
        sh.single_color = (1, 1, 1)
        for o in self.objs:
            o.hide_render = o not in self.ojos
        ojo = self._render("tinta_sil", "ojos")
        ojos = ojo[:, :, 3] * ojo[:, :, :3].mean(axis=2) if self.ojos else np.zeros_like(sil)
        # 4) dientes
        dientes = np.zeros_like(sil)
        if self.dientes and p.mat_dientes in self.cols_mat:
            sh.color_type = 'MATERIAL'
            for nm in self.cols_mat:
                bpy.data.materials[nm].diffuse_color = (1, 1, 1, 1) if nm == p.mat_dientes else (0, 0, 0, 1)
            for o in self.objs:
                o.hide_render = o not in self.dientes
            d = self._render("tinta_sil", "dientes")
            dientes = d[:, :, 3] * np.clip((d[:, :, :3].mean(axis=2) - 0.55) * 3, 0, 1)
            for nm, col in self.cols_mat.items():
                bpy.data.materials[nm].diffuse_color = col
            sh.color_type = 'SINGLE'
        for o in self.objs:
            o.hide_render = self.g["ocultos"][o.name]
        rnd = np.random.RandomState(p.semilla + fr)
        res = componer(fondo, sil, ojos, dientes, p, rnd)
        h, w = res.shape[:2]
        im = bpy.data.images.new("tinta_tmp", w, h, alpha=True)
        im.pixels.foreach_set(np.ascontiguousarray(np.concatenate([res, np.ones((h, w, 1), dtype=np.float32)], axis=2)).reshape(-1))
        ruta = os.path.join(self.dir, "tinta_%04d.png" % fr)
        im.filepath_raw = ruta
        im.file_format = 'PNG'
        im.save()
        bpy.data.images.remove(im)
        return ruta

    def cerrar(self):
        sc = self.sc
        for o in self.objs:
            o.hide_render = self.g["ocultos"].get(o.name, False)
        for nm, col in self.cols_mat.items():
            bpy.data.materials[nm].diffuse_color = col
        sh = sc.display.shading
        sh.light, sh.color_type, sh.single_color, sh.show_cavity, sh.cavity_type, sh.show_object_outline, sh.background_type = self.g["sh"]
        sc.display.render_aa = self.g["aa"]
        sc.render.engine = self.g["motor"]
        sc.render.resolution_percentage = self.g["rx"]
        sc.render.filepath = self.g["ruta"]
        sc.render.image_settings.file_format = self.g["fmt"]
        sc.render.image_settings.color_mode = self.g["modo"]
        sc.render.film_transparent = self.g["trans"]
        sc.view_settings.view_transform = self.g["cm"]
        sc.world = self.g["mundo"]
        for vl in (self.vl_fondo, self.vl_sil):
            try:
                sc.view_layers.remove(vl)
            except Exception:
                pass
        try:
            bpy.data.worlds.remove(self.w_tmp)
        except Exception:
            pass


# ------------------------------------------------------------------------------------------------------------------------------ operadores
class TINTA_OT_preparar(Operator):
    bl_idname = "tinta.preparar_stalker"
    bl_label = "Preparar Stalker"
    bl_description = "Deja la configuracion lista para the_stalker_1 de este proyecto (coleccion, ojos, dientes y materiales)"

    def execute(self, context):
        p = context.scene.tinta
        p.col_criatura = bpy.data.collections.get("the_stalker_from_the_fog.geo")
        p.ojos = "Ojo_Terror_Rombo_L_1,Ojo_Terror_Rombo_R_1"
        p.dientes_obj = "Mesh_1,Mesh_0_1"
        p.mat_dientes = "Material_0.001_dientes_sin_brillo"
        p.mats_cuerpo = "Material_0.001"
        p.inicio, p.fin = context.scene.frame_start, context.scene.frame_end
        return {'FINISHED'}


class TINTA_OT_probar(Operator):
    bl_idname = "tinta.probar"
    bl_label = "Probar frame actual"
    bl_description = "Renderiza solo el frame actual con el efecto y lo guarda en la carpeta de salida"

    def execute(self, context):
        t = None
        try:
            t = _Trabajo(context)
            ruta = t.frame(context.scene.frame_current)
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        finally:
            if t:
                t.cerrar()
        self.report({'INFO'}, "Guardado: %s" % ruta)
        return {'FINISHED'}


class TINTA_OT_render(Operator):
    bl_idname = "tinta.render_animacion"
    bl_label = "Renderizar animacion"
    bl_description = "Renderiza del frame de inicio al de fin con el efecto (Esc cancela). Cada frame queda en la carpeta de salida"
    previa: BoolProperty(default=False, options={'HIDDEN'})
    _timer = None
    _t = None
    _frames = None
    _i = 0
    _zona = None

    def modal(self, context, event):
        if event.type == 'ESC':
            return self._fin(context, "Cancelado en el frame %d" % self._frames[min(self._i, len(self._frames) - 1)])
        if event.type == 'TIMER':
            if self._i >= len(self._frames):
                return self._fin(context, "Listo: %d frames en %s" % (len(self._frames), self._t.dir))
            fr = self._frames[self._i]
            try:
                self._t.frame(fr)
            except Exception as e:
                return self._fin(context, "Error en el frame %d: %s" % (fr, e), error=True)
            self._i += 1
            context.window_manager.progress_update(self._i)
        return {'RUNNING_MODAL'}

    def _fin(self, context, msg, error=False):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        wm.progress_end()
        self._t.cerrar()
        hechos = self._i
        if self.previa and hechos > 0:
            f0, f1 = self._frames[0], self._frames[hechos - 1] + context.scene.tinta.paso_prev - 1
            d = self._t.dir
            ult = None
            for fr in range(f0, f1 + 1):                    # rellena los frames saltados con el ultimo renderizado
                ruta = os.path.join(d, "tinta_%04d.png" % fr)
                if os.path.exists(ruta):
                    ult = ruta
                elif ult:
                    shutil.copyfile(ult, ruta)
            mostrar_en_camara(context.scene, f0, f1, d)
        elif context.scene.tinta.ver_camara and hechos > 0 and not error:
            mostrar_en_camara(context.scene, self._frames[0], self._frames[hechos - 1])
        self.report({'ERROR' if error else 'INFO'}, msg)
        return {'CANCELLED' if error else 'FINISHED'}

    def execute(self, context):
        p = context.scene.tinta
        if p.fin < p.inicio:
            self.report({'ERROR'}, "El fin debe ser >= inicio")
            return {'CANCELLED'}
        try:
            self._t = _Trabajo(context, p.escala_prev, "_previa") if self.previa else _Trabajo(context)
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        self._frames = list(range(p.inicio, p.fin + 1, p.paso_prev if self.previa else p.paso))
        self._i = 0
        wm = context.window_manager
        wm.progress_begin(0, len(self._frames))
        self._timer = wm.event_timer_add(0.2, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}


def mostrar_en_camara(sc, f0, f1, carpeta=None):
    """pone la secuencia tinta_NNNN.png como imagen de fondo de la camara activa (visible en la vista de camara de la Vista 3D)"""
    p = sc.tinta
    cam = sc.camera
    ruta = os.path.join(carpeta or bpy.path.abspath(p.salida), "tinta_%04d.png" % f0)
    if not os.path.exists(ruta):
        raise RuntimeError("No hay frames renderizados todavia")
    img = bpy.data.images.load(ruta, check_existing=False)
    img.source = 'SEQUENCE'
    for bg in [b for b in cam.data.background_images if b.image and b.image.name.startswith("tinta_")]:
        cam.data.background_images.remove(bg)
    bg = cam.data.background_images.new()
    bg.image = img
    bg.image_user.frame_start = f0
    bg.image_user.frame_offset = f0 - 1
    bg.image_user.frame_duration = f1 - f0 + 1
    bg.image_user.use_auto_refresh = True
    bg.alpha = 1.0
    bg.display_depth = 'FRONT'
    bg.frame_method = 'FIT'
    cam.data.show_background_images = True


class TINTA_OT_camara(Operator):
    bl_idname = "tinta.mostrar_camara"
    bl_label = "Mostrar en la camara"
    bl_description = "Muestra la secuencia renderizada dentro de la vista de camara (mira por la camara con el numpad 0 y reproduce)"

    def execute(self, context):
        p = context.scene.tinta
        d = bpy.path.abspath(p.salida)
        nums = sorted(int(f[6:10]) for f in os.listdir(d) if f.startswith("tinta_") and f.endswith(".png") and f[6:10].isdigit()) if os.path.isdir(d) else []
        if not nums:
            self.report({'ERROR'}, "No hay frames renderizados en la carpeta")
            return {'CANCELLED'}
        try:
            mostrar_en_camara(context.scene, nums[0], nums[-1])
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        self.report({'INFO'}, "Camara: frames %d-%d" % (nums[0], nums[-1]))
        return {'FINISHED'}


class TINTA_OT_quitar_camara(Operator):
    bl_idname = "tinta.quitar_camara"
    bl_label = "Quitar de la camara"

    def execute(self, context):
        cam = context.scene.camera
        for bg in [b for b in cam.data.background_images if b.image and b.image.name.startswith("tinta_")]:
            cam.data.background_images.remove(bg)
        return {'FINISHED'}


# ------------------------------------------------------------------------------------------------------------------------------ FILTRO EN TIEMPO REAL (compositor del viewport)
# Vista de camara en modo Solido (Workbench) con colores de material convertidos: escena en gris claro, criatura en NEGRO, ojos y dientes en BLANCO, cavidad + contorno negro.
# El compositor del viewport (nodos) lo convierte al estilo de tinta en vivo: silueta negra con borde crema, ojos/dientes blancos y fondo con contraluz + TRAMADO DE PUNTOS con una
# imagen de ruido. El centro del contraluz sigue a la cabeza de la criatura (un handler actualiza dos valores). Boton de encendido/apagado: todo se restaura al apagar.
GRUPO = "tinta_compositor"
_H = {"activo": False}


def _areas_camara(context):
    res = [a for w in context.window_manager.windows for a in w.screen.areas if a.type == 'VIEW_3D']
    cam = [a for a in res if a.spaces[0].region_3d.view_perspective == 'CAMERA']
    if not cam and res:
        res[0].spaces[0].region_3d.view_perspective = 'CAMERA'
        cam = [res[0]]
    return cam


def _ruido_png():
    base = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else bpy.app.tempdir
    ruta = os.path.join(base, "tinta_ruido.png")
    if not os.path.exists(ruta):
        rnd = np.random.RandomState(7)
        w, h, b = 1920, 1080, 2
        a = np.kron(rnd.rand(h // b + 1, w // b + 1).astype(np.float32), np.ones((b, b), dtype=np.float32))[:h, :w]
        im = bpy.data.images.new("tinta_ruido_tmp", w, h, alpha=False)
        im.pixels.foreach_set(np.repeat(a[:, :, None], 4, axis=2).reshape(-1))
        im.filepath_raw = ruta
        im.file_format = 'PNG'
        im.save()
        bpy.data.images.remove(im)
    return ruta


def _crear_grupo(p):
    if GRUPO in bpy.data.node_groups:
        bpy.data.node_groups.remove(bpy.data.node_groups[GRUPO])
    ng = bpy.data.node_groups.new(GRUPO, 'CompositorNodeTree')
    ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    N, L = ng.nodes, ng.links
    k = {"x": -1400}

    def nodo(tipo, **props):
        n = N.new(tipo)
        n.location = (k["x"], 0)
        k["x"] += 180
        for a, v in props.items():
            setattr(n, a, v)
        return n

    def mat(op, a=None, b=None, c=None, clamp=False):
        n = nodo('ShaderNodeMath', operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                L.new(v, n.inputs[i])
        return n.outputs[0]

    def mezcla(f, a, b):
        n = nodo('ShaderNodeMix', data_type='RGBA', blend_type='MIX')
        for sock, v in ((n.inputs[0], f), (n.inputs[6], a), (n.inputs[7], b)):
            if isinstance(v, (tuple, int, float)):
                sock.default_value = v
            else:
                L.new(v, sock)
        return n.outputs[2]

    rl = nodo('CompositorNodeRLayers')
    bw = nodo('CompositorNodeRGBToBW')
    L.new(rl.outputs['Image'], bw.inputs['Image'])
    Lg = bw.outputs['Val']
    sil_raw = mat('LESS_THAN', Lg, 0.035)                        # negro puro: silueta de la criatura + lineas de contorno
    ojos = mat('GREATER_THAN', Lg, 0.90)                        # blanco puro: ojos y dientes
    er = nodo('CompositorNodeDilateErode')                      # silueta "abierta": quita las lineas finas (en esta version el tamano es un socket)
    er.inputs['Size'].default_value = -2
    L.new(sil_raw, er.inputs[0])
    di = nodo('CompositorNodeDilateErode')
    di.inputs['Size'].default_value = 2
    L.new(er.outputs[0], di.inputs[0])
    di2 = nodo('CompositorNodeDilateErode')
    di2.inputs['Size'].default_value = max(0, p.borde)
    L.new(di.outputs[0], di2.inputs[0])
    rim = mat('SUBTRACT', di2.outputs[0], di.outputs[0], clamp=True)
    gn = nodo('ShaderNodeMapRange', clamp=True)
    L.new(Lg, gn.inputs['Value'])
    gn.inputs["From Min"].default_value = 0.02
    gn.inputs["From Max"].default_value = 0.75
    co = nodo('CompositorNodeImageCoordinates')
    L.new(rl.outputs['Image'], co.inputs['Image'])
    sep = nodo('ShaderNodeSeparateXYZ')
    L.new(co.outputs['Normalized'], sep.inputs['Vector'])
    cx = nodo('ShaderNodeValue')
    cx.name = cx.label = "tinta_cx"
    cx.outputs[0].default_value = 0.5
    cy = nodo('ShaderNodeValue')
    cy.name = cy.label = "tinta_cy"
    cy.outputs[0].default_value = 0.6
    dx = mat('DIVIDE', mat('SUBTRACT', sep.outputs['X'], cx.outputs[0]), max(0.05, p.halo_ancho))
    dy = mat('DIVIDE', mat('SUBTRACT', sep.outputs['Y'], cy.outputs[0]), max(0.05, p.halo_alto))
    r2 = mat('ADD', mat('MULTIPLY', dx, dx), mat('MULTIPLY', dy, dy))
    halo = mat('MULTIPLY', mat('EXPONENT', mat('MULTIPLY', r2, -1.3)), p.halo_fuerza)
    B = mat('MULTIPLY', mat('ADD', 0.20, mat('MULTIPLY', halo, 0.85)), mat('ADD', 0.30, mat('MULTIPLY', gn.outputs['Result'], 0.70)))
    img = nodo('CompositorNodeImage')
    img.image = bpy.data.images.load(_ruido_png(), check_existing=True)
    sc2 = nodo('CompositorNodeScale')
    for nombre, valores in (('Type', ('Render Size', 'Render size', 'RENDER_SIZE')), ('Frame Type', ('Crop', 'CROP'))):
        for v in valores:
            try:
                sc2.inputs[nombre].default_value = v
                break
            except Exception:
                continue
    L.new(img.outputs['Image'], sc2.inputs['Image'])
    nbw = nodo('CompositorNodeRGBToBW')
    L.new(sc2.outputs['Image'], nbw.inputs['Image'])
    pts = mat('GREATER_THAN', mat('ADD', B, mat('MULTIPLY', mat('SUBTRACT', nbw.outputs['Val'], 0.5), p.ruido)), 0.5)
    crema, negro = tuple(p.color_crema) + (1.0,), tuple(p.color_negro) + (1.0,)
    col = mezcla(pts, negro, crema)
    col = mezcla(sil_raw, col, negro)
    col = mezcla(ojos, col, (1.0, 1.0, 0.97, 1.0))
    sal = nodo('NodeGroupOutput')
    L.new(col, sal.inputs[0])
    return ng


def _pos_cabeza(sc):
    from bpy_extras.object_utils import world_to_camera_view
    ar = bpy.data.objects.get("torso_1")
    cam = sc.camera
    if not ar or not cam:
        return None
    try:
        h = ar.matrix_world @ ar.pose.bones["head_1"].head
    except Exception:
        return None
    v = world_to_camera_view(sc, cam, h)
    return max(-0.5, min(1.5, v.x)), max(-0.5, min(1.5, v.y + 0.12))


def _handler(scene, *a):
    ng = scene.compositing_node_group
    if not _H["activo"] or ng is None or ng.name != GRUPO:
        return
    for w in bpy.context.window_manager.windows:                 # el filtro solo tiene sentido en Material Preview con el material de sustitucion: se mantiene aunque algo cambie la vista
        for ar in w.screen.areas:
            if ar.type == 'VIEW_3D' and ar.spaces[0].region_3d.view_perspective == 'CAMERA':
                sh = ar.spaces[0].shading
                if sh.type != 'MATERIAL':
                    sh.type = 'MATERIAL'
                if sh.use_compositor != 'CAMERA':
                    sh.use_compositor = 'CAMERA'
    pos = _pos_cabeza(scene)
    if pos:
        ng.nodes["tinta_cx"].outputs[0].default_value = pos[0]
        ng.nodes["tinta_cy"].outputs[0].default_value = pos[1]


def _filtro_toggle(context):
    if context.scene.tinta.filtro_activo:
        _filtro_on(context)
    else:
        _filtro_off(context)


def _mat_override():
    """material unico para el viewport (Material Preview). Se distingue por el COLOR DEL OBJETO (canal R): 1 = escena (difuso gris iluminado por el HDRI), 0 = criatura (negro),
    0.5 = ojos (emision blanca). Los dientes son un atributo de color `tinta_dientes` (R = 1 en sus caras) -> emision blanca. El compositor recibe negro / blanco / gris con volumen."""
    m = bpy.data.materials.get("tinta_override")
    if m:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new("tinta_override")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes, nt.links

    def mat(op, a, b):
        n = N.new("ShaderNodeMath")
        n.operation = op
        for i, v in enumerate((a, b)):
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                L.new(v, n.inputs[i])
        return n.outputs[0]
    sal = N.new("ShaderNodeOutputMaterial")
    oi = N.new("ShaderNodeObjectInfo")
    sep = N.new("ShaderNodeSeparateColor")
    L.new(oi.outputs["Color"], sep.inputs[0])
    at = N.new("ShaderNodeAttribute")
    at.attribute_name = "tinta_dientes"
    sep2 = N.new("ShaderNodeSeparateColor")
    L.new(at.outputs["Color"], sep2.inputs[0])
    R = sep.outputs[0]
    escena = mat("GREATER_THAN", R, 0.75)
    ojos = mat("MULTIPLY", mat("GREATER_THAN", R, 0.25), mat("LESS_THAN", R, 0.75))
    emi = mat("MAXIMUM", ojos, mat("GREATER_THAN", sep2.outputs[0], 0.5))
    df = N.new("ShaderNodeBsdfDiffuse")
    L.new(mat("MULTIPLY", escena, 0.80), df.inputs["Color"])
    em = N.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1, 1, 1, 1)
    L.new(mat("MULTIPLY", emi, 3.0), em.inputs["Strength"])
    add = N.new("ShaderNodeAddShader")
    L.new(df.outputs[0], add.inputs[0])
    L.new(em.outputs[0], add.inputs[1])
    L.new(add.outputs[0], sal.inputs["Surface"])
    return m


def _atributo_dientes(p, poner):
    """crea (o quita) el atributo de color `tinta_dientes` en las mallas de dientes: 1 en las esquinas de las caras con el material de dientes"""
    for nm in _nombres(p.dientes_obj):
        ob = bpy.data.objects.get(nm)
        if not ob or ob.type != 'MESH':
            continue
        me = ob.data
        a = me.color_attributes.get("tinta_dientes")
        if a:
            me.color_attributes.remove(a)
        if not poner:
            continue
        idx = [i for i, s in enumerate(ob.material_slots) if s.material and s.material.name == p.mat_dientes]
        if not idx:
            continue
        a = me.color_attributes.new("tinta_dientes", 'FLOAT_COLOR', 'CORNER')
        datos = np.zeros(len(me.loops) * 4, dtype=np.float32)
        for pol in me.polygons:
            if pol.material_index == idx[0]:
                for li in range(pol.loop_start, pol.loop_start + pol.loop_total):
                    datos[li * 4:li * 4 + 4] = (1, 1, 1, 1)
        a.data.foreach_set("color", datos)


def _filtro_on(context):
    import json
    sc = context.scene
    p = sc.tinta
    if p.col_criatura is None:
        p.filtro_activo = False
        raise RuntimeError("Falta la coleccion de la criatura")
    vl = context.view_layer
    objs = [o for o in p.col_criatura.all_objects if o.type == 'MESH']
    guardado = {"vt": sc.view_settings.view_transform, "vl": vl.name, "ov": vl.material_override.name if vl.material_override else "", "grupo": sc.compositing_node_group.name if sc.compositing_node_group else "",
                "colores": {o.name: list(o.color) for o in objs}, "areas": []}
    for o in objs:
        o.color = (0.5, 0.5, 0.5, 1.0) if o.name in _nombres(p.ojos) else (0.0, 0.0, 0.0, 1.0)
    _atributo_dientes(p, True)
    vl.material_override = _mat_override()
    for a in _areas_camara(context):
        sh = a.spaces[0].shading
        guardado["areas"].append((a.as_pointer(), sh.type, sh.use_compositor))
        sh.type = 'MATERIAL'                           # Material Preview: ahi funciona el compositor del viewport y se ve el resultado en vivo
        sh.use_compositor = 'CAMERA'                   # el compositor solo actua al mirar por la camara
    sc.view_settings.view_transform = 'Standard'       # sin AgX/Filmic: los blancos y negros del filtro quedan puros
    sc["tinta_guardado"] = json.dumps(guardado)
    sc.compositing_node_group = _crear_grupo(p)
    _H["activo"] = True
    if _handler not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(_handler)
    if _handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_handler)
    _handler(sc)


def _filtro_off(context):
    import json
    sc = context.scene
    p = sc.tinta
    _H["activo"] = False
    for h in (bpy.app.handlers.frame_change_post, bpy.app.handlers.depsgraph_update_post):
        for f in [f for f in h if getattr(f, "__name__", "") == "_handler"]:
            h.remove(f)
    if "tinta_guardado" in sc:
        g = json.loads(sc["tinta_guardado"])
        vl = sc.view_layers.get(g.get("vl", "")) or context.view_layer
        vl.material_override = bpy.data.materials.get(g["ov"]) if g.get("ov") else None
        for nm, col in g.get("colores", {}).items():
            o = bpy.data.objects.get(nm)
            if o:
                o.color = col
        sc.view_settings.view_transform = g.get("vt", sc.view_settings.view_transform)
        sc.compositing_node_group = bpy.data.node_groups.get(g["grupo"]) if g["grupo"] else None
        areas = {a.as_pointer(): a for w in context.window_manager.windows for a in w.screen.areas if a.type == 'VIEW_3D'}
        for ptr, tipo, comp in g["areas"]:
            a = areas.get(ptr)
            if a:
                a.spaces[0].shading.use_compositor = comp
                a.spaces[0].shading.type = tipo
        del sc["tinta_guardado"]
    else:
        sc.compositing_node_group = None
    _atributo_dientes(p, False)
    if sc.world is None or sc.world.name == "tinta_world":          # nunca dejar la escena sin mundo (el add-on Replay lo necesita)
        otro = next((w for w in bpy.data.worlds if w.name != "tinta_world"), None)
        sc.world = otro
    for nm, tipo in (("tinta_override", bpy.data.materials), ("tinta_world", bpy.data.worlds)):
        if nm in tipo:
            tipo.remove(tipo[nm])
    if GRUPO in bpy.data.node_groups:
        bpy.data.node_groups.remove(bpy.data.node_groups[GRUPO])


class TINTA_OT_aplicar_filtro(Operator):
    bl_idname = "tinta.aplicar_filtro"
    bl_label = "Aplicar filtro"
    bl_description = "Enciende el filtro de tinta en tiempo real en la vista de camara"

    def execute(self, context):
        p = context.scene.tinta
        for nombre in ("punto", "ruido", "halo_ancho", "halo_alto", "halo_fuerza", "borde", "semilla", "color_crema", "color_negro"):
            p.property_unset(nombre)                    # cada vez que se aplica el filtro vuelven los valores por defecto (los de ahora)
        try:
            _filtro_on(context)
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        import json
        context.scene["tinta_aplicado"] = json.dumps(_snap(p))
        _guardar_historial(context.scene, [])
        return {'FINISHED'}


class TINTA_OT_quitar_filtro(Operator):
    bl_idname = "tinta.quitar_filtro"
    bl_label = "Quitar filtro"
    bl_description = "Apaga el filtro y restaura los colores de material, la vista y el compositor"

    def execute(self, context):
        _filtro_off(context)
        return {'FINISHED'}


ESTILO = ("punto", "ruido", "halo_ancho", "halo_alto", "halo_fuerza", "borde", "semilla", "color_crema", "color_negro")


def _snap(p):
    return {k: (list(getattr(p, k)) if k.startswith("color") else getattr(p, k)) for k in ESTILO}


def _historial(sc):
    import json
    return json.loads(sc.get("tinta_historial", "[]"))


def _guardar_historial(sc, h):
    import json
    sc["tinta_historial"] = json.dumps(h[-30:])


def _reconstruir(context):
    sc = context.scene
    sc.compositing_node_group = _crear_grupo(sc.tinta)
    _handler(sc)


class TINTA_OT_editar(Operator):
    bl_idname = "tinta.editar_filtro"
    bl_label = "Editar"
    bl_description = "Aplica al filtro los valores actuales de la seccion Estilo (el estado anterior queda guardado para Retroceder)"

    def execute(self, context):
        sc = context.scene
        h = _historial(sc)
        actual = sc.get("tinta_aplicado")
        import json
        if actual:
            h.append(json.loads(actual))
            _guardar_historial(sc, h)
        sc["tinta_aplicado"] = json.dumps(_snap(sc.tinta))
        _reconstruir(context)
        return {'FINISHED'}


class TINTA_OT_retroceder(Operator):
    bl_idname = "tinta.retroceder_filtro"
    bl_label = "Retroceder"
    bl_description = "Vuelve a los valores de Estilo de la edicion anterior y los aplica al filtro"

    def execute(self, context):
        import json
        sc = context.scene
        h = _historial(sc)
        if not h:
            self.report({'INFO'}, "No hay ediciones anteriores")
            return {'CANCELLED'}
        previo = h.pop()
        _guardar_historial(sc, h)
        p = sc.tinta
        for k, v in previo.items():
            setattr(p, k, v)
        sc["tinta_aplicado"] = json.dumps(previo)
        _reconstruir(context)
        return {'FINISHED'}


class TINTA_PT_panel(Panel):
    bl_label = "Tinta Render"
    bl_idname = "TINTA_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tinta"

    def draw(self, context):
        p = context.scene.tinta
        l = self.layout
        l.operator("tinta.preparar_stalker", icon='ARMATURE_DATA')
        activo = bpy.data.node_groups.get(GRUPO) is not None and context.scene.compositing_node_group is not None and context.scene.compositing_node_group.name == GRUPO
        f = l.column(align=True)
        f.scale_y = 1.4
        r1 = f.row()
        r1.enabled = not activo
        r1.operator("tinta.aplicar_filtro", icon='SHADERFX')
        r2 = f.row()
        r2.enabled = activo
        r2.operator("tinta.quitar_filtro", icon='X')
        c = l.box().column(align=True)
        c.prop(p, "col_criatura")
        c.prop(p, "ojos")
        c.prop(p, "dientes_obj")
        c.prop(p, "mat_dientes")
        c.prop(p, "mats_cuerpo")
        c = l.box().column(align=True)
        c.label(text="Estilo")
        c.prop(p, "punto")
        c.prop(p, "ruido")
        c.prop(p, "halo_ancho")
        c.prop(p, "halo_alto")
        c.prop(p, "halo_fuerza")
        c.prop(p, "borde")
        c.prop(p, "semilla")
        r = c.row(align=True)
        r.prop(p, "color_crema")
        r.prop(p, "color_negro")
        e = l.row(align=True)
        e.scale_y = 1.3
        e.enabled = activo
        e.operator("tinta.editar_filtro", icon='GREASEPENCIL')
        r2 = e.row(align=True)
        r2.enabled = bool(_historial(context.scene))
        r2.operator("tinta.retroceder_filtro", icon='LOOP_BACK')


CLASES = (TINTA_Props, TINTA_OT_preparar, TINTA_OT_probar, TINTA_OT_render, TINTA_OT_camara, TINTA_OT_quitar_camara, TINTA_OT_aplicar_filtro, TINTA_OT_quitar_filtro, TINTA_OT_editar, TINTA_OT_retroceder, TINTA_PT_panel)


def register():
    for c in CLASES:
        try:
            bpy.utils.register_class(c)
        except ValueError:
            bpy.utils.unregister_class(c)
            bpy.utils.register_class(c)
    bpy.types.Scene.tinta = PointerProperty(type=TINTA_Props)


def unregister():
    if hasattr(bpy.types.Scene, "tinta"):
        del bpy.types.Scene.tinta
    for c in reversed(CLASES):
        try:
            bpy.utils.unregister_class(c)
        except RuntimeError:
            pass


if __name__ == "__main__":
    register()
