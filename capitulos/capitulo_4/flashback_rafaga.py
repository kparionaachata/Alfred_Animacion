# -*- coding: utf-8 -*-
bl_info = {
    "name": "Flashback Rafaga",
    "author": "Alfred Animacion",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "Vista 3D > Barra lateral (N) > Flashback",
    "description": "Montaje rapido / cortes subliminales: fotogramas de imagenes que tapan toda la camara en rafagas muy cortas (con negros y parpadeo) entre dos frames",
    "category": "Animation",
}
"""Flashback Rafaga: montaje rapido / burst montage / flash-cutting.
Coloca las imagenes que el usuario indique como planos pegados a la camara (con el tamano de su encuadre, siguen su lente animada con drivers) y los muestra uno a uno en
rafagas de pocos frames, con huecos que pueden ser negro total (parpadeo) o dejar ver la escena. Entre el frame de inicio y el de fin, los flashes se van haciendo mas
frecuentes (rampa) si se activa. Cada flash es un plano con material emisivo; la visibilidad se anima con claves CONSTANTES de hide_render/hide_viewport.
Todo vive en la coleccion `flashback_rafaga` y se puede borrar con "Quitar efecto". Los planos no iluminan la escena ni proyectan sombras (Cycles).
Uso: panel "Flashback" en la barra lateral (N) de la Vista 3D:
 1. "Agregar imagenes" (varias a la vez) o "Cargar carpeta".
 2. Fijar inicio/fin, duracion de cada flash y del hueco, probabilidad de negro, semilla, brillo, distancia del plano.
 3. "Construir efecto".
Sin interfaz: bpy.context.scene.flashback_rafaga.imagenes.add().ruta = "C:/ruta/imagen.png"; bpy.ops.flashback.construir()
"""
import bpy, bmesh, random, os, wave
import numpy as np
from bpy.props import (StringProperty, IntProperty, FloatProperty, BoolProperty, CollectionProperty, PointerProperty, EnumProperty)
from bpy.types import PropertyGroup, Operator, Panel, OperatorFileListElement

COL = "flashback_rafaga"
EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tga", ".tif", ".tiff")


class FB_Imagen(PropertyGroup):
    ruta: StringProperty(name="Ruta", subtype='FILE_PATH')
    grupo: IntProperty(name="Grupo", description="0 = A, 1 = B (se alternan si 'intercalar' esta activo)", default=0, min=0, max=1)


class FB_Props(PropertyGroup):
    imagenes: CollectionProperty(type=FB_Imagen)
    carpeta: StringProperty(name="Carpeta", subtype='DIR_PATH')
    inicio: IntProperty(name="Inicio", default=600, min=0)
    fin: IntProperty(name="Fin", default=770, min=1)
    dur_min: IntProperty(name="Flash min (frames)", default=1, min=1)
    dur_max: IntProperty(name="Flash max (frames)", default=3, min=1)
    hueco_min: IntProperty(name="Hueco min (frames)", default=2, min=0)
    hueco_max: IntProperty(name="Hueco max (frames)", default=14, min=0)
    prob_negro: FloatProperty(name="Prob. negro en el hueco", default=0.6, min=0.0, max=1.0)
    rampa: BoolProperty(name="Rafaga cada vez mas rapida", default=True)
    cobertura: FloatProperty(name="Cobertura inicial", description="Fraccion de los flashes que se muestran al principio (1 = todos); sube a 1 hacia el final", default=0.35, min=0.0, max=1.0)
    brillo: FloatProperty(name="Brillo", default=1.0, min=0.0, max=10.0)
    distancia: FloatProperty(name="Distancia al plano (m)", default=0.3, min=0.11, max=5.0)
    semilla: IntProperty(name="Semilla", default=7)
    sin_repetir: BoolProperty(name="No repetir la misma imagen seguida", default=True)
    zooms_por_imagen: IntProperty(name="Zooms por imagen", description="Cada imagen genera N imagenes nuevas ampliando una parte al azar (recorte con el encuadre de la camara)", default=5, min=0, max=30)
    zoom_min: FloatProperty(name="Zoom min (fraccion del ancho)", default=0.22, min=0.05, max=1.0)
    zoom_max: FloatProperty(name="Zoom max (fraccion del ancho)", default=0.55, min=0.05, max=1.0)
    espejo: FloatProperty(name="Prob. espejo", default=0.4, min=0.0, max=1.0)
    negativo: FloatProperty(name="Prob. negativo", default=0.15, min=0.0, max=1.0)
    incluir_originales: BoolProperty(name="Incluir las imagenes originales", default=True)
    cache: StringProperty(name="Carpeta de recortes", subtype='DIR_PATH', default="//flashback_cache/")
    intercalar: BoolProperty(name="Intercalar grupos A y B", description="Con la sincronia por pulsos, alterna un flash del grupo A y uno del B (las laminas y sus zooms)", default=False)
    usar_pulsos: BoolProperty(name="Sincronizar con los pulsos del audio", description="Un flash en cada frame de la lista 'pulsos' (en vez de la agenda aleatoria)", default=False)
    audio_sync: StringProperty(name="Audio (WAV 16 bits)", subtype='FILE_PATH')
    audio_inicio: IntProperty(name="Frame donde empieza el audio", default=1)
    sensibilidad: FloatProperty(name="Sensibilidad de pulsos", description="Un pico cuenta si supera esta fraccion del maximo local de la envolvente", default=0.5, min=0.1, max=0.95)
    separacion: FloatProperty(name="Separacion minima (s)", default=0.15, min=0.04, max=2.0)
    pulsos: StringProperty(name="Pulsos (frames)", default="")
    tapar_siempre: BoolProperty(name="Negro al final (tapa toda la camara)", description="Termina con unos frames de negro total", default=False)


def _cam(context):
    cam = context.scene.camera
    if cam is None or cam.type != 'CAMERA':
        raise RuntimeError("La escena no tiene camara activa")
    return cam


def _mat_emisivo(nombre, imagen=None, brillo=1.0):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    sal = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = brillo
    if imagen is not None:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = imagen
        tex.interpolation = 'Linear'
        tex.extension = 'CLIP'
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mx = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(tex.outputs["Color"], em.inputs["Color"])
        nt.links.new(tex.outputs["Alpha"], mx.inputs["Fac"])
        nt.links.new(tr.outputs["BSDF"], mx.inputs[1])
        nt.links.new(em.outputs["Emission"], mx.inputs[2])
        nt.links.new(mx.outputs["Shader"], sal.inputs["Surface"])
    else:
        em.inputs["Color"].default_value = (0, 0, 0, 1)
        nt.links.new(em.outputs["Emission"], sal.inputs["Surface"])
    return m


def _plano(nombre, cam, mat, dist, col, orden):
    me = bpy.data.meshes.new(nombre)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new(p) for p in ((-0.5, -0.5, 0), (0.5, -0.5, 0), (0.5, 0.5, 0), (-0.5, 0.5, 0))]
    f = bm.faces.new(vs)
    for lp, uvc in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        lp[uv].uv = uvc
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(nombre, me)
    col.objects.link(ob)
    ob.parent = cam
    ob.location = (0, 0, -(dist + orden * 0.001))
    ob.rotation_euler = (0, 0, 0)
    for a in ("visible_shadow", "visible_diffuse", "visible_glossy", "visible_transmission", "visible_volume_scatter"):
        if hasattr(ob, a):
            setattr(ob, a, False)
    ob.hide_select = True
    return ob


def _driver_tamano(ob, cam, dist, rx, ry):
    for i in (0, 1):
        fc = ob.driver_add("scale", i)
        d = fc.driver
        d.type = 'SCRIPTED'
        for nom, prop in (("lens", "lens"), ("sens", "sensor_width")):
            v = d.variables.new()
            v.name = nom
            v.type = 'SINGLE_PROP'
            v.targets[0].id_type = 'CAMERA'
            v.targets[0].id = cam.data
            v.targets[0].data_path = prop
        base = "%f*sens/lens*1.06" % (dist + 0.0)
        d.expression = base if i == 0 else "%s*%f" % (base, ry / float(rx))
    ob.scale = (1, 1, 1)


def _aceptable(rgb, claro=False):
    """descarta imagenes/recortes sin sentido: casi todo negro, casi todo blanco o sin estructura (rgb: array HxWx3 en 0-1).
    claro=True: laminas sobre pergamino (fondo claro): basta con que tengan tinta (desviacion minima baja)"""
    lum = rgb @ np.array([0.30, 0.59, 0.11], dtype=np.float32)
    if claro:
        return 0.30 < float(lum.mean()) < 0.86 and float(lum.std()) > 0.10
    return 0.14 < float(lum.mean()) < 0.90 and float(lum.std()) > 0.22 and 0.10 < float((lum > 0.5).mean()) < 0.90


def _zooms(ruta, p, rnd, cache, rx, ry, claro=False):
    """genera p.zooms_por_imagen recortes ampliados de la imagen (con el aspecto de la camara), a veces en espejo o en negativo; devuelve sus rutas"""
    img = bpy.data.images.load(ruta, check_existing=True)
    W, H = img.size
    arr = np.empty(W * H * 4, dtype=np.float32)
    img.pixels.foreach_get(arr)
    arr = arr.reshape(H, W, 4)
    stem = os.path.splitext(os.path.basename(ruta))[0]
    os.makedirs(cache, exist_ok=True)
    salida = []
    for k in range(p.zooms_por_imagen):
        crop = None
        for _ in range(40):                              # busca un recorte con sentido (no negro, no vacio)
            s = rnd.uniform(p.zoom_min, max(p.zoom_min, p.zoom_max))
            cw = max(8, int(W * s))
            ch = int(cw * ry / float(rx))
            if ch > H:
                ch = H
                cw = int(ch * rx / float(ry))
            x0 = rnd.randint(int(0.04 * (W - cw)), max(int(0.04 * (W - cw)), int(0.96 * (W - cw))))
            y0 = rnd.randint(int(0.04 * (H - ch)), max(int(0.04 * (H - ch)), int(0.96 * (H - ch))))
            c = arr[y0:y0 + ch, x0:x0 + cw].copy()
            if _aceptable(c[:, :, :3], claro):
                crop = c
                break
        if crop is None:
            continue
        if rnd.random() < p.espejo:
            crop = crop[:, ::-1].copy()
        if rnd.random() < p.negativo:
            crop[:, :, :3] = 1.0 - crop[:, :, :3]
        ch, cw = crop.shape[:2]
        nuevo = bpy.data.images.new("fb_tmp", cw, ch, alpha=True)
        nuevo.pixels.foreach_set(np.ascontiguousarray(crop).reshape(-1))
        nuevo.scale(1280, int(round(1280 * ry / float(rx))))
        ruta_out = os.path.join(cache, "%s_zoom%02d_s%d.png" % (stem, k, p.semilla))
        nuevo.filepath_raw = ruta_out
        nuevo.file_format = 'PNG'
        nuevo.save()
        bpy.data.images.remove(nuevo)
        salida.append(ruta_out)
    return salida


def _agenda(p, n_img, grupos=None):
    """lista de (frame_ini, frame_fin, indice_imagen|-1 para negro) respetando la configuracion"""
    rnd = random.Random(p.semilla)
    if p.usar_pulsos and p.pulsos.strip():                 # un flash por pulso del audio (empieza 1 frame antes del pico)
        orden = {0: [], 1: []}
        ultimo, out, k = -1, [], 0
        idxs = {0: [i for i in range(n_img) if not grupos or grupos[i] == 0], 1: [i for i in range(n_img) if grupos and grupos[i] == 1]}
        for f in [int(x) for x in p.pulsos.split(",") if x.strip()]:
            if not n_img or f < p.inicio or f > p.fin:
                continue
            g = (k % 2) if (p.intercalar and idxs[1] and idxs[0]) else None
            k += 1
            pool = idxs[g] if g is not None else list(range(n_img))
            clave = g if g is not None else 0
            if not orden[clave]:
                orden[clave] = list(pool)
                rnd.shuffle(orden[clave])
                if p.sin_repetir and len(orden[clave]) > 1 and orden[clave][0] == ultimo:
                    orden[clave].append(orden[clave].pop(0))
            idx = orden[clave].pop(0)
            ultimo = idx
            out.append((f - 1, f - 1 + rnd.randint(p.dur_min, max(p.dur_min, p.dur_max)), idx))
        return out
    out = []
    t = p.inicio
    ultimo = -1
    orden = []
    total = max(1, p.fin - p.inicio)
    while t < p.fin:
        u = (t - p.inicio) / total
        d = rnd.randint(p.dur_min, max(p.dur_min, p.dur_max))
        # cobertura: probabilidad de que el flash se muestre (crece con el tiempo)
        prob = p.cobertura + (1.0 - p.cobertura) * u if p.rampa else 1.0
        if n_img and rnd.random() <= prob:
            if not orden:
                orden = list(range(n_img))
                rnd.shuffle(orden)
                if p.sin_repetir and len(orden) > 1 and orden[0] == ultimo:
                    orden.append(orden.pop(0))
            idx = orden.pop(0)
            ultimo = idx
            out.append((t, min(t + d, p.fin), idx))
        t += d
        g = rnd.randint(p.hueco_min, max(p.hueco_min, p.hueco_max))
        if p.rampa:
            g = int(round(g * (1.0 - 0.8 * u)))          # los huecos se acortan hacia el final
        if g > 0 and rnd.random() < p.prob_negro:
            out.append((t, min(t + g, p.fin), -1))
        t += g
    if p.tapar_siempre:
        out.append((p.fin, p.fin + 6, -1))
    return out


class FB_OT_agregar(Operator):
    bl_idname = "flashback.agregar"
    bl_label = "Agregar imagenes"
    bl_description = "Agrega una o varias imagenes a la lista del flashback"
    directory: StringProperty(subtype='DIR_PATH')
    files: CollectionProperty(type=OperatorFileListElement)
    filter_image: BoolProperty(default=True, options={'HIDDEN'})
    filter_folder: BoolProperty(default=True, options={'HIDDEN'})

    def execute(self, context):
        p = context.scene.flashback_rafaga
        n = 0
        for f in self.files:
            it = p.imagenes.add()
            it.ruta = os.path.join(self.directory, f.name)
            n += 1
        self.report({'INFO'}, "%d imagen(es) agregada(s)" % n)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class FB_OT_carpeta(Operator):
    bl_idname = "flashback.cargar_carpeta"
    bl_label = "Cargar carpeta"
    bl_description = "Agrega todas las imagenes de la carpeta indicada"

    def execute(self, context):
        p = context.scene.flashback_rafaga
        d = bpy.path.abspath(p.carpeta)
        if not os.path.isdir(d):
            self.report({'ERROR'}, "La carpeta no existe")
            return {'CANCELLED'}
        n = 0
        for f in sorted(os.listdir(d)):
            if f.lower().endswith(EXT):
                p.imagenes.add().ruta = os.path.join(d, f)
                n += 1
        self.report({'INFO'}, "%d imagen(es) cargada(s)" % n)
        return {'FINISHED'}


class FB_OT_pulsos(Operator):
    bl_idname = "flashback.detectar_pulsos"
    bl_label = "Detectar pulsos del audio"
    bl_description = "Busca los picos de la envolvente del WAV (oscilacion del sonido) y los convierte en frames de la escena"

    def execute(self, context):
        sc = context.scene
        p = sc.flashback_rafaga
        ruta = bpy.path.abspath(p.audio_sync)
        if not os.path.exists(ruta):
            self.report({'ERROR'}, "No existe el audio")
            return {'CANCELLED'}
        w = wave.open(ruta)
        if w.getsampwidth() != 2:
            self.report({'ERROR'}, "Solo WAV de 16 bits")
            return {'CANCELLED'}
        sr, ch = w.getframerate(), w.getnchannels()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, ch).mean(axis=1) / 32768.0
        hop = int(sr * 0.01)
        env = np.array([np.sqrt((a[i:i + hop * 3] ** 2).mean()) for i in range(0, len(a) - hop * 3, hop)])
        e = np.convolve(env, np.ones(4) / 4, 'same')
        fps = sc.render.fps / sc.render.fps_base
        fr, ult = [], -9
        for i in range(12, len(e) - 12):
            if e[i] == e[i - 12:i + 13].max() and e[i] > p.sensibilidad * e[max(0, i - 100):i + 100].max():
                t = i * 0.01
                if t - ult >= p.separacion:
                    f = int(round(p.audio_inicio + fps * t))
                    if p.inicio <= f <= p.fin:
                        fr.append(f)
                    ult = t
        p.pulsos = ",".join(str(f) for f in fr)
        p.usar_pulsos = True
        self.report({'INFO'}, "%d pulsos entre f%d y f%d" % (len(fr), p.inicio, p.fin))
        return {'FINISHED'}


class FB_OT_vaciar(Operator):
    bl_idname = "flashback.vaciar"
    bl_label = "Vaciar lista"

    def execute(self, context):
        context.scene.flashback_rafaga.imagenes.clear()
        return {'FINISHED'}


class FB_OT_quitar(Operator):
    bl_idname = "flashback.quitar"
    bl_label = "Quitar efecto"
    bl_description = "Borra los planos, materiales y claves del efecto"

    def execute(self, context):
        _limpiar()
        return {'FINISHED'}


def _limpiar():
    col = bpy.data.collections.get(COL)
    if col:
        for o in list(col.objects):
            me = o.data
            bpy.data.objects.remove(o)
            if me and me.users == 0:
                bpy.data.meshes.remove(me)
        bpy.data.collections.remove(col)
    for m in [m for m in bpy.data.materials if m.name.startswith("flashback_")]:
        bpy.data.materials.remove(m)


class FB_OT_construir(Operator):
    bl_idname = "flashback.construir"
    bl_label = "Construir efecto"
    bl_description = "Crea los planos pegados a la camara y anima su visibilidad"

    def execute(self, context):
        sc = context.scene
        p = sc.flashback_rafaga
        if not p.imagenes:
            self.report({'ERROR'}, "Agrega al menos una imagen")
            return {'CANCELLED'}
        if p.fin <= p.inicio:
            self.report({'ERROR'}, "El fin debe ser mayor que el inicio")
            return {'CANCELLED'}
        cam = _cam(context)
        _limpiar()
        col = bpy.data.collections.new(COL)
        sc.collection.children.link(col)
        rx, ry = sc.render.resolution_x, sc.render.resolution_y
        planos = []
        rutas = []
        grupos = []
        rnd = random.Random(p.semilla + 1)
        cache = bpy.path.abspath(p.cache)
        for it in p.imagenes:
            ruta = bpy.path.abspath(it.ruta)
            if not os.path.exists(ruta):
                self.report({'WARNING'}, "No existe: %s" % ruta)
                continue
            im0 = bpy.data.images.load(ruta, check_existing=True)
            a0 = np.empty(im0.size[0] * im0.size[1] * 4, dtype=np.float32)
            im0.pixels.foreach_get(a0)
            a0 = a0.reshape(im0.size[1], im0.size[0], 4)
            claro = float((a0[:, :, :3] @ np.array([0.30, 0.59, 0.11], dtype=np.float32)).mean()) > 0.5
            n0 = len(rutas)
            if p.incluir_originales:
                if _aceptable(a0[:, :, :3], claro):
                    rutas.append(ruta)
                else:
                    self.report({'WARNING'}, "Descartada por poco contenido: %s" % os.path.basename(ruta))
            if p.zooms_por_imagen and (it.grupo == 1 or not p.intercalar):          # con 'intercalar', solo el grupo B (laminas) genera zooms
                rutas += _zooms(ruta, p, rnd, cache, rx, ry, claro)
            grupos += [it.grupo] * (len(rutas) - n0)
        for i, ruta in enumerate(rutas):
            img = bpy.data.images.load(ruta, check_existing=True)
            mat = _mat_emisivo("flashback_img_%02d" % i, img, p.brillo)
            ob = _plano("flash_img_%02d" % i, cam, mat, p.distancia, col, i + 1)
            _driver_tamano(ob, cam, p.distancia, rx, ry)
            planos.append(ob)
        negro = _plano("flash_negro", cam, _mat_emisivo("flashback_negro", None), p.distancia, col, 0)
        _driver_tamano(negro, cam, p.distancia, rx, ry)
        todos = planos + [negro]
        for ob in todos:
            ob.hide_render = True
            ob.hide_viewport = True
            ob.keyframe_insert("hide_render", frame=1)
            ob.keyframe_insert("hide_viewport", frame=1)
        agenda = _agenda(p, len(planos), grupos[:len(planos)])
        for ini, fin, idx in agenda:
            ob = negro if idx < 0 else planos[idx]
            for prop in ("hide_render", "hide_viewport"):
                setattr(ob, prop, False)
                ob.keyframe_insert(prop, frame=ini)
                setattr(ob, prop, True)
                ob.keyframe_insert(prop, frame=fin)
        for ob in todos:
            if ob.animation_data and ob.animation_data.action:
                for l in ob.animation_data.action.layers:
                    for s in l.strips:
                        for cb in s.channelbags:
                            for fc in cb.fcurves:
                                for kp in fc.keyframe_points:
                                    kp.interpolation = 'CONSTANT'
                                fc.update()
        self.report({'INFO'}, "Flashback: %d flashes entre f%d y f%d (%d imagenes)" % (len([a for a in agenda if a[2] >= 0]), p.inicio, p.fin, len(planos)))
        return {'FINISHED'}


class FB_PT_panel(Panel):
    bl_label = "Flashback Rafaga"
    bl_idname = "FB_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Flashback"

    def draw(self, context):
        p = context.scene.flashback_rafaga
        l = self.layout
        c = l.column(align=True)
        c.label(text="Imagenes (%d)" % len(p.imagenes))
        c.operator("flashback.agregar", icon='IMAGE_DATA')
        r = c.row(align=True)
        r.prop(p, "carpeta", text="")
        r.operator("flashback.cargar_carpeta", text="", icon='FILE_FOLDER')
        c.operator("flashback.vaciar", icon='X')
        for it in p.imagenes[:8]:
            c.label(text=os.path.basename(it.ruta), icon='DOT')
        if len(p.imagenes) > 8:
            c.label(text="...")
        b = l.box().column(align=True)
        b.prop(p, "inicio")
        b.prop(p, "fin")
        b.prop(p, "dur_min")
        b.prop(p, "dur_max")
        b.prop(p, "hueco_min")
        b.prop(p, "hueco_max")
        b.prop(p, "prob_negro")
        b.prop(p, "rampa")
        if p.rampa:
            b.prop(p, "cobertura")
        b.prop(p, "brillo")
        b.prop(p, "distancia")
        b.prop(p, "semilla")
        b.prop(p, "sin_repetir")
        b.prop(p, "tapar_siempre")
        y = l.box().column(align=True)
        y.label(text="Sincronia con audio")
        y.prop(p, "audio_sync", text="")
        y.prop(p, "audio_inicio")
        y.prop(p, "sensibilidad")
        y.prop(p, "separacion")
        y.operator("flashback.detectar_pulsos", icon='SOUND')
        y.prop(p, "usar_pulsos")
        y.prop(p, "pulsos", text="")
        z = l.box().column(align=True)
        z.label(text="Variaciones por zoom")
        z.prop(p, "zooms_por_imagen")
        z.prop(p, "zoom_min")
        z.prop(p, "zoom_max")
        z.prop(p, "espejo")
        z.prop(p, "negativo")
        z.prop(p, "incluir_originales")
        z.prop(p, "cache")
        l.operator("flashback.construir", icon='PLAY')
        l.operator("flashback.quitar", icon='TRASH')


CLASES = (FB_Imagen, FB_Props, FB_OT_agregar, FB_OT_carpeta, FB_OT_pulsos, FB_OT_vaciar, FB_OT_quitar, FB_OT_construir, FB_PT_panel)


def register():
    for c in CLASES:
        try:
            bpy.utils.register_class(c)
        except ValueError:
            bpy.utils.unregister_class(c)
            bpy.utils.register_class(c)
    bpy.types.Scene.flashback_rafaga = PointerProperty(type=FB_Props)


def unregister():
    if hasattr(bpy.types.Scene, "flashback_rafaga"):
        del bpy.types.Scene.flashback_rafaga
    for c in reversed(CLASES):
        try:
            bpy.utils.unregister_class(c)
        except RuntimeError:
            pass


if __name__ == "__main__":
    register()
