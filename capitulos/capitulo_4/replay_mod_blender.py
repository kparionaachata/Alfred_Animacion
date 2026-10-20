bl_info = {
    "name": "Replay Mod",
    "author": "Replay Team",
    "version": (1, 3, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Replay",
    "description": "Sistema de grabación y reproducción cinematográfica inspirado en Minecraft Replay Mod",
    "category": "Animation",
}

import bpy
import json
import os
import math
import datetime


def get_action_fcurves(obj):
    """Devuelve las fcurves de la action activa de obj.
    Compatible con Blender < 4.4 (action.fcurves directo) y con
    Blender >= 4.4 (Slotted Actions, incluye 5.2), donde las fcurves
    viven dentro del channelbag del slot asignado."""
    anim_data = obj.animation_data
    if not anim_data or not anim_data.action:
        return []

    action = anim_data.action

    # Blender < 4.4: API legacy
    if hasattr(action, "fcurves") and not hasattr(action, "layers"):
        return action.fcurves

    # Blender >= 4.4: Slotted Actions
    from bpy_extras import anim_utils

    slot = anim_data.action_slot
    if slot is None:
        return []

    channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)
    return channelbag.fcurves if channelbag else []
from bpy.props import (
    StringProperty, 
    BoolProperty, 
    IntProperty, 
    FloatProperty,
    EnumProperty,
    CollectionProperty,
    PointerProperty
)
from bpy.types import (
    Panel, 
    Operator, 
    PropertyGroup,
    UIList
)
from mathutils import Vector, Euler, Matrix


def _ajustes(context):
    """Ajustes del replay. Viven en el World y NO en la Scene: si la Scene tiene animacion (p.ej. el volumen
    de los sonidos animado por el ducking de voces), Blender busca la curva de cada casilla que lee la Scene y
    cada una tarda ~50 ms (todo el panel Replay iba a ~1 s por redibujo). El World no tiene animacion."""
    sc = context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new("World")
    return sc.world.replay_settings


def _copiar_ajustes(src, dst):
    """Copia recursivamente un grupo de propiedades guardado como IDProperty (el de la Scene) a `dst`."""
    for k in list(src.keys()):
        p = dst.bl_rna.properties.get(k)
        if p is None or p.identifier in ("rna_type", "migrado"):
            continue
        v = src[k]
        try:
            if p.type == 'COLLECTION':
                col = getattr(dst, k)
                col.clear()
                for it in v:
                    _copiar_ajustes(it, col.add())
            elif p.type == 'POINTER':
                setattr(dst, k, v)
            elif p.type == 'ENUM':
                nombre = next((e.identifier for e in p.enum_items if e.value == v), None)
                if nombre:
                    setattr(dst, k, nombre)
            else:
                setattr(dst, k, v.to_list() if hasattr(v, "to_list") else v)
        except Exception as e:
            print(f"Replay: no se pudo migrar '{k}': {e}")


def _migrar_ajustes(*_):
    """Pasa los ajustes antiguos (guardados en la Scene) al World, una sola vez."""
    for sc in bpy.data.scenes:
        viejo = sc.get("replay_settings")
        if viejo is None:
            continue
        if sc.world is None:
            sc.world = bpy.data.worlds.new("World")
        nuevo = sc.world.replay_settings
        if not nuevo.migrado:
            _copiar_ajustes(viejo, nuevo)
            nuevo.migrado = True
            print(f"Replay: ajustes de '{sc.name}' migrados al World '{sc.world.name}'")


def _orbit_update(self, context):
    """Activa/desactiva que la camara gire alrededor del foco: la camara se hace hija del foco
    (sin moverse), asi al rotar o mover el foco la camara orbita a su alrededor."""
    cam = self.active_camera if self.active_camera else context.scene.camera
    foco = _obtener_foco(context)
    if cam is None or foco is None:
        return
    if self.orbit_focus:
        if cam.parent is not foco:
            cam.parent = foco
            cam.matrix_parent_inverse = foco.matrix_world.inverted()
    elif cam.parent is foco:
        mw = cam.matrix_world.copy()
        cam.parent = None
        cam.matrix_world = mw


# ============================================
# CLASES DE DATOS
# ============================================

class ReplayKeyframe(PropertyGroup):
    frame: IntProperty(name="Frame", default=1)
    location_x: FloatProperty(name="Location X", default=0.0)
    location_y: FloatProperty(name="Location Y", default=0.0)
    location_z: FloatProperty(name="Location Z", default=0.0)
    rotation_x: FloatProperty(name="Rotation X", default=0.0)
    rotation_y: FloatProperty(name="Rotation Y", default=0.0)
    rotation_z: FloatProperty(name="Rotation Z", default=0.0)
    # Lente (distancia focal en mm) PROPIA de cada keyframe: se graba con el keyframe, se puede editar en el panel y se anima entre keyframes
    fov: FloatProperty(name="Lente (mm)", default=50.0, min=1.0, max=5000.0, description="Distancia focal de la cámara en este keyframe (independiente en cada keyframe)")
    # Congelar camara: si esta activo, la camara (y el foco) se queda quieta en este keyframe `freeze_frames` frames
    freeze: BoolProperty(name="Congelar", default=False, description="Congelar la cámara en este keyframe durante los frames indicados")
    freeze_frames: IntProperty(name="Frames", default=12, min=1, max=10000, description="Cuántos frames se queda la cámara en esta posición")
    # Foco (objeto al que apunta la camara): posicion y rotacion en este keyframe
    has_focus: BoolProperty(name="Tiene Foco", default=False)
    focus_x: FloatProperty(name="Foco X", default=0.0)
    focus_y: FloatProperty(name="Foco Y", default=0.0)
    focus_z: FloatProperty(name="Foco Z", default=0.0)
    focus_rx: FloatProperty(name="Foco Rot X", default=0.0)
    focus_ry: FloatProperty(name="Foco Rot Y", default=0.0)
    focus_rz: FloatProperty(name="Foco Rot Z", default=0.0)

class ReplayCameraPath(PropertyGroup):
    name: StringProperty(name="Nombre", default="Path")
    keyframes: CollectionProperty(type=ReplayKeyframe)
    active_keyframe: IntProperty(name="Keyframe Activo", default=0)
    interpolation: EnumProperty(
        name="Interpolación",
        items=[
            ('LINEAR', "Lineal", "Interpolación lineal"),
            ('BEZIER', "Bezier", "Interpolación suave"),
            ('CONSTANT', "Constante", "Sin interpolación")
        ],
        default='BEZIER'
    )

class ReplayRecording(PropertyGroup):
    name: StringProperty(name="Nombre", default="Recording")
    start_frame: IntProperty(name="Inicio", default=1)
    end_frame: IntProperty(name="Fin", default=250)
    filepath: StringProperty(name="Archivo", subtype='FILE_PATH')

class ReplaySettings(PropertyGroup):
    migrado: BoolProperty(default=False, options={'HIDDEN'})
    is_preview: BoolProperty(name="Vista Previa", default=False)
    is_recording: BoolProperty(name="Grabando", default=False)
    is_playing: BoolProperty(name="Reproduciendo", default=False)
    
    active_camera: PointerProperty(
        type=bpy.types.Object,
        name="Cámara Activa",
        description="Cámara que se usará para la grabación",
        poll=lambda self, obj: obj.type == 'CAMERA'
    )
    
    focus_object: PointerProperty(
        type=bpy.types.Object,
        name="Foco",
        description="Objeto foco de la camara (se graba y se anima junto con ella). Si esta vacio se usa 'Foco_Conversacion' cuando existe"
    )
    record_focus: BoolProperty(
        name="Grabar Foco",
        default=True,
        description="Guardar tambien posicion y rotacion del foco en cada keyframe"
    )
    orbit_focus: BoolProperty(
        name="Cámara gira alrededor del foco",
        default=False,
        update=_orbit_update,
        description="El foco es el pivote de la cámara: al rotar o mover el foco, toda la cámara orbita a su alrededor (la cámara se hace hija del foco)"
    )

    recordings: CollectionProperty(type=ReplayRecording)
    active_recording: IntProperty(name="Grabación Activa", default=0)
    
    camera_paths: CollectionProperty(type=ReplayCameraPath)
    active_path: IntProperty(name="Path Activo", default=0)
    
    playback_speed: FloatProperty(
        name="Velocidad",
        default=1.0,
        min=0.1,
        max=10.0,
        description="Velocidad de reproducción"
    )

    loop_playback: BoolProperty(
        name="Loop (Cíclico)",
        default=False,
        description="Reproducir en bucle continuo"
    )
    
    auto_record: BoolProperty(
        name="Auto Grabar",
        default=False,
        description="Grabar automáticamente al reproducir"
    )
    
    camera_smooth: FloatProperty(
        name="Suavizado",
        default=0.5,
        min=0.0,
        max=1.0,
        description="Suavizado de movimiento de cámara"
    )
    
    output_path: StringProperty(
        name="Ruta de salida",
        default="//replays/",
        subtype='DIR_PATH'
    )

# ============================================
# OPERADORES
# ============================================

class REPLAY_OT_TogglePreview(Operator):
    bl_idname = "replay.toggle_preview"
    bl_label = "Vista Previa"
    bl_description = "Activar/Desactivar vista previa de cámara en ventana separada"
    
    def execute(self, context):
        settings = _ajustes(context)
        settings.is_preview = not settings.is_preview
        
        if settings.is_preview:
            if not settings.active_camera:
                self.report({'ERROR'}, "Selecciona una cámara primero")
                settings.is_preview = False
                return {'CANCELLED'}
            
            bpy.ops.screen.userpref_show('INVOKE_DEFAULT')
            
            for window in context.window_manager.windows:
                screen = window.screen
                for area in screen.areas:
                    if area.type == 'VIEW_3D':
                        for space in area.spaces:
                            if space.type == 'VIEW_3D':
                                space.region_3d.view_perspective = 'CAMERA'
                                context.scene.camera = settings.active_camera
                                break
                        break
            
            self.report({'INFO'}, f"Vista previa activada: {settings.active_camera.name}")
        else:
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        for space in area.spaces:
                            if space.type == 'VIEW_3D':
                                space.region_3d.view_perspective = 'PERSP'
                                break
            
            self.report({'INFO'}, "Vista previa desactivada")
        
        return {'FINISHED'}

class REPLAY_OT_OpenPreviewWindow(Operator):
    bl_idname = "replay.open_preview_window"
    bl_label = "Abrir Ventana de Vista Previa"
    bl_description = "Abre una ventana separada mostrando la vista de la cámara seleccionada"
    
    def execute(self, context):
        settings = _ajustes(context)
        
        if not settings.active_camera:
            self.report({'ERROR'}, "Selecciona una cámara primero")
            return {'CANCELLED'}
        
        bpy.ops.wm.window_new()
        
        new_window = context.window_manager.windows[-1]
        new_area = new_window.screen.areas[0]
        new_area.type = 'VIEW_3D'
        
        for space in new_area.spaces:
            if space.type == 'VIEW_3D':
                space.region_3d.view_perspective = 'CAMERA'
                space.overlay.show_overlays = True
                space.overlay.show_floor = False
                space.overlay.show_axis_x = False
                space.overlay.show_axis_y = False
                space.overlay.show_axis_z = False
                space.overlay.show_text = True
                space.overlay.show_stats = True
                space.shading.type = 'SOLID'
                space.shading.light = 'STUDIO'
                break
        
        context.scene.camera = settings.active_camera
        settings.is_preview = True
        
        self.report({'INFO'}, f"Ventana de preview abierta: {settings.active_camera.name}")
        return {'FINISHED'}


class REPLAY_OT_StartRecording(Operator):
    bl_idname = "replay.start_recording"
    bl_label = "Iniciar Grabación"
    bl_description = "Comenzar a grabar la sesión actual"
    
    def execute(self, context):
        settings = _ajustes(context)
        
        if not settings.active_camera:
            self.report({'ERROR'}, "Selecciona una cámara antes de grabar")
            return {'CANCELLED'}
        
        if settings.is_preview:
            settings.is_preview = False
        
        settings.is_recording = True
        context.scene.camera = settings.active_camera
        
        rec = settings.recordings.add()
        rec.name = f"Recording_{len(settings.recordings)}"
        rec.start_frame = bpy.context.scene.frame_current
        rec.end_frame = context.scene.frame_end
        
        self.report({'INFO'}, f"Grabación iniciada con cámara: {settings.active_camera.name}")
        return {'FINISHED'}

class REPLAY_OT_StopRecording(Operator):
    bl_idname = "replay.stop_recording"
    bl_label = "Detener Grabación"
    bl_description = "Detener la grabación actual"
    
    def execute(self, context):
        settings = _ajustes(context)
        settings.is_recording = False
        
        if len(settings.recordings) > 0:
            rec = settings.recordings[settings.active_recording]
            rec.end_frame = bpy.context.scene.frame_current
            self.save_recording(context, rec)
        
        self.report({'INFO'}, "Grabación detenida")
        return {'FINISHED'}
    
    def save_recording(self, context, recording):
        data = {
            'name': recording.name,
            'start_frame': recording.start_frame,
            'end_frame': recording.end_frame,
            'objects': []
        }
        
        for obj in context.selected_objects:
            obj_data = {
                'name': obj.name,
                'location': list(obj.location),
                'rotation': list(obj.rotation_euler),
                'scale': list(obj.scale)
            }
            data['objects'].append(obj_data)
        
        output_dir = bpy.path.abspath(_ajustes(context).output_path)
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, f"{recording.name}.json")
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        
        recording.filepath = filepath

class REPLAY_OT_CreateCameraPath(Operator):
    bl_idname = "replay.create_camera_path"
    bl_label = "Crear Path"
    bl_description = "Crear un nuevo path de cámara"
    
    def execute(self, context):
        settings = _ajustes(context)
        path = settings.camera_paths.add()
        path.name = f"CameraPath_{len(settings.camera_paths)}"
        settings.active_path = len(settings.camera_paths) - 1
        
        self.report({'INFO'}, f"Path creado: {path.name}")
        return {'FINISHED'}

def _obtener_cam_eval_activa(context, operator):
    """
    Devuelve (cam, cam_eval) de la cámara activa seleccionada en el panel,
    ya evaluada con el depsgraph (con todas las transformaciones aplicadas).
    Si no hay cámara activa o ya no existe en la escena, reporta el error en
    `operator` y devuelve (None, None).
    """
    settings = _ajustes(context)

    if not settings.active_camera:
        operator.report({'ERROR'}, "⚠ Selecciona una cámara en el panel primero")
        return None, None

    cam_name = settings.active_camera.name
    if cam_name not in context.scene.objects:
        operator.report({'ERROR'}, "⚠ La cámara seleccionada no existe en la escena")
        return None, None

    cam = context.scene.objects[cam_name]
    depsgraph = context.evaluated_depsgraph_get()
    cam_eval = cam.evaluated_get(depsgraph)
    return cam, cam_eval


def _obtener_foco(context):
    """Objeto foco a usar: el del panel o, si esta vacio, 'Foco_Conversacion' si existe en la escena.
    Devuelve None si no hay foco o no se quiere grabar."""
    settings = _ajustes(context)
    if not settings.record_focus:
        return None
    foco = settings.focus_object
    if foco is None:
        foco = context.scene.objects.get("Foco_Conversacion")
    if foco is not None and foco.name not in context.scene.objects:
        return None
    return foco


def _asignar_transform_a_keyframe(kf, cam_eval, foco_eval=None):
    """Copia posición/rotación/FOV actuales de `cam_eval` (y del foco, si hay) al ReplayKeyframe `kf`."""
    if cam_eval.parent is not None:
        # camara hija del foco: se guarda su pose en el mundo, no la local
        loc, rot, _ = cam_eval.matrix_world.decompose()
        rot = rot.to_euler('XYZ')
    else:
        loc, rot = cam_eval.location, cam_eval.rotation_euler
    kf.location_x = loc.x
    kf.location_y = loc.y
    kf.location_z = loc.z
    kf.rotation_x = rot.x
    kf.rotation_y = rot.y
    kf.rotation_z = rot.z
    if cam_eval.data.type == 'PERSP':
        kf.fov = cam_eval.data.lens
    if foco_eval is not None:
        kf.has_focus = True
        kf.focus_x = foco_eval.location.x
        kf.focus_y = foco_eval.location.y
        kf.focus_z = foco_eval.location.z
        kf.focus_rx = foco_eval.rotation_euler.x
        kf.focus_ry = foco_eval.rotation_euler.y
        kf.focus_rz = foco_eval.rotation_euler.z
    else:
        kf.has_focus = False


def _foco_eval(context, foco):
    """Version evaluada del foco (o None)."""
    if foco is None:
        return None
    return foco.evaluated_get(context.evaluated_depsgraph_get())


def _aplicar_keyframe_a_objetos(kf, cam, foco):
    """Mueve la camara (y el foco) a los valores guardados en `kf`, sin crear claves."""
    if foco is not None and kf.has_focus:
        foco.location = Vector((kf.focus_x, kf.focus_y, kf.focus_z))
        foco.rotation_euler = Euler((kf.focus_rx, kf.focus_ry, kf.focus_rz))
    loc = Vector((kf.location_x, kf.location_y, kf.location_z))
    rot = Euler((kf.rotation_x, kf.rotation_y, kf.rotation_z))
    if cam.parent is not None:
        # camara hija del foco: la pose guardada es la del mundo
        bpy.context.view_layer.update()
        cam.matrix_world = Matrix.LocRotScale(loc, rot, None)
    else:
        cam.location = loc
        cam.rotation_euler = rot
    if cam.data.type == 'PERSP':
        cam.data.lens = kf.fov


def _interpolar(idblock, modo):
    for fcurve in get_action_fcurves(idblock):
        for kf_point in fcurve.keyframe_points:
            if modo == 'BEZIER':
                kf_point.interpolation = 'BEZIER'
                kf_point.handle_left_type = 'AUTO_CLAMPED'
                kf_point.handle_right_type = 'AUTO_CLAMPED'
            elif modo == 'LINEAR':
                kf_point.interpolation = 'LINEAR'
            else:
                kf_point.interpolation = 'CONSTANT'


def _hornear_path(context, path, cam, foco):
    """Escribe en `cam` (y en `foco`, si el path tiene datos de foco) las claves del path.
    No cambia de frame para cada clave (es mucho mas rapido en escenas pesadas):
    pone el valor y lo clava con keyframe_insert(frame=...)."""
    usar_foco = foco is not None and any(kf.has_focus for kf in path.keyframes)
    # orbita: la camara es hija del foco y TODOS los keyframes tienen foco -> se hornea la pose
    # de la camara relativa al foco, asi al girar el foco entre keyframes la camara orbita a su alrededor
    orbita = (usar_foco and cam.parent is foco and all(kf.has_focus for kf in path.keyframes))
    for ob in ((cam, foco) if usar_foco else (cam,)):
        if ob.animation_data:
            ob.animation_data_clear()
    if cam.data.animation_data:
        cam.data.animation_data_clear()
    if orbita:
        cam.matrix_parent_inverse = Matrix.Identity(4)
    elif cam.parent is not None and cam.parent is foco:
        cam.parent = None       # sin orbita: la camara se hornea en el mundo
        _ajustes(context).orbit_focus = False

    ordenados = sorted(path.keyframes, key=lambda k: k.frame)

    def _clavar(kf, frame):
        if orbita:
            foco.location = Vector((kf.focus_x, kf.focus_y, kf.focus_z))
            foco.rotation_euler = Euler((kf.focus_rx, kf.focus_ry, kf.focus_rz))
            f_mat = Matrix.LocRotScale(foco.location, foco.rotation_euler, foco.scale)
            c_mat = Matrix.LocRotScale(Vector((kf.location_x, kf.location_y, kf.location_z)),
                                       Euler((kf.rotation_x, kf.rotation_y, kf.rotation_z)), None)
            local = f_mat.inverted() @ c_mat
            cam.location = local.to_translation()
            cam.rotation_euler = local.to_euler('XYZ', cam.rotation_euler)
            if cam.data.type == 'PERSP':
                cam.data.lens = kf.fov
        else:
            _aplicar_keyframe_a_objetos(kf, cam, foco if usar_foco else None)
        cam.keyframe_insert(data_path="location", frame=frame)
        cam.keyframe_insert(data_path="rotation_euler", frame=frame)
        if cam.data.type == 'PERSP':
            cam.data.keyframe_insert(data_path="lens", frame=frame)
        if usar_foco and kf.has_focus:
            foco.keyframe_insert(data_path="location", frame=frame)
            foco.keyframe_insert(data_path="rotation_euler", frame=frame)

    for i, kf in enumerate(ordenados):
        _clavar(kf, kf.frame)
        if kf.freeze:
            # congelar: segunda clave igual `freeze_frames` frames despues (sin pasar del siguiente keyframe)
            fin = kf.frame + kf.freeze_frames
            if i + 1 < len(ordenados):
                fin = min(fin, ordenados[i + 1].frame - 1)
            if fin > kf.frame:
                _clavar(kf, fin)

    _interpolar(cam, path.interpolation)
    _interpolar(cam.data, path.interpolation)
    if usar_foco:
        _interpolar(foco, path.interpolation)
    context.scene.camera = cam
    context.scene.frame_set(context.scene.frame_current)     # refresca con las claves nuevas
    return usar_foco


class REPLAY_OT_AddKeyframe(Operator):
    bl_idname = "replay.add_keyframe"
    bl_label = "Aplicar"
    bl_description = "Grabar estado actual de la cámara en el frame seleccionado"

    def execute(self, context):
        settings = _ajustes(context)

        if not settings.active_camera:
            self.report({'ERROR'}, "⚠ Selecciona una cámara en el panel primero")
            return {'CANCELLED'}

        # 🔧 FIX: Obtener cámara directamente desde la escena
        cam_name = settings.active_camera.name
        if cam_name not in context.scene.objects:
            self.report({'ERROR'}, "⚠ La cámara seleccionada no existe en la escena")
            return {'CANCELLED'}
        
        # ✅ CORRECTO: Leer desde la escena actual
        cam = context.scene.objects[cam_name]
        
        # Obtener versión evaluada (con todas las transformaciones aplicadas)
        depsgraph = context.evaluated_depsgraph_get()
        cam_eval = cam.evaluated_get(depsgraph)

        if len(settings.camera_paths) == 0:
            path = settings.camera_paths.add()
            path.name = f"CameraPath_Auto"
            settings.active_path = 0
            self.report({'INFO'}, "Path automático creado")

        path = settings.camera_paths[settings.active_path]
        current_frame = context.scene.frame_current
        
        # Usar cam_eval para valores actualizados
        rot_x_deg = math.degrees(cam_eval.rotation_euler.x)
        rot_y_deg = math.degrees(cam_eval.rotation_euler.y)
        rot_z_deg = math.degrees(cam_eval.rotation_euler.z)
        
        print(f"\n=== DEBUG KEYFRAME ===")
        print(f"Frame actual: {current_frame}")
        print(f"Cámara: {cam.name}")
        print(f"Ubicación: X={cam_eval.location.x:.3f} Y={cam_eval.location.y:.3f} Z={cam_eval.location.z:.3f}")
        print(f"Rotación (radianes): X={cam_eval.rotation_euler.x:.4f} Y={cam_eval.rotation_euler.y:.4f} Z={cam_eval.rotation_euler.z:.4f}")
        print(f"Rotación (grados): X={rot_x_deg:.2f}° Y={rot_y_deg:.2f}° Z={rot_z_deg:.2f}°")
        if cam_eval.data.type == 'PERSP':
            print(f"FOV (lens): {cam_eval.data.lens}mm")
        print(f"======================\n")

        # Verificar si ya existe keyframe en este frame
        existing_kf_index = None
        for idx, existing_kf in enumerate(path.keyframes):
            if existing_kf.frame == current_frame:
                existing_kf_index = idx
                break
        
        if existing_kf_index is not None:
            self.report({'WARNING'}, f"⚠️ Sobrescribiendo keyframe en frame {current_frame}")
            path.keyframes.remove(existing_kf_index)

        # 🔧 FIX CRÍTICO: Crear keyframe y asignar valores INMEDIATAMENTE
        kf = path.keyframes.add()
        kf.frame = current_frame
        foco = _obtener_foco(context)
        _asignar_transform_a_keyframe(kf, cam_eval, _foco_eval(context, foco))
        if foco is not None and settings.focus_object is None:
            settings.focus_object = foco

        # Verificación de guardado
        print(f"✅ KEYFRAME GUARDADO:")
        print(f"   Frame: {kf.frame}")
        print(f"   Location guardada: ({kf.location_x:.3f}, {kf.location_y:.3f}, {kf.location_z:.3f})")
        print(f"   Rotation guardada: ({math.degrees(kf.rotation_x):.2f}°, {math.degrees(kf.rotation_y):.2f}°, {math.degrees(kf.rotation_z):.2f}°)")
        print(f"   Total keyframes en path: {len(path.keyframes)}\n")

        self.report({'INFO'}, f"✅ Keyframe grabado en Frame {current_frame} - Total: {len(path.keyframes)} keyframes")
        
        # Forzar actualización de UI
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}

class REPLAY_OT_InsertKeyframe(Operator):
    bl_idname = "replay.insert_keyframe"
    bl_label = "Insertar Keyframe"
    bl_description = (
        "Insertar el estado actual de la cámara como keyframe en el frame "
        "actual, acomodándolo en su posición correcta dentro de la lista "
        "existente (ordenada por frame) -- a diferencia de 'Aplicar', que "
        "siempre agrega al final de la lista"
    )

    def execute(self, context):
        settings = _ajustes(context)

        cam, cam_eval = _obtener_cam_eval_activa(context, self)
        if cam is None:
            return {'CANCELLED'}

        if len(settings.camera_paths) == 0:
            path = settings.camera_paths.add()
            path.name = "CameraPath_Auto"
            settings.active_path = 0
            self.report({'INFO'}, "Path automático creado")

        path = settings.camera_paths[settings.active_path]
        current_frame = context.scene.frame_current
        foco = _obtener_foco(context)
        foco_eval = _foco_eval(context, foco)
        if foco is not None and settings.focus_object is None:
            settings.focus_object = foco

        # Si ya hay un keyframe exactamente en este frame, se sobrescribe en
        # su mismo lugar (igual que "Aplicar") en vez de crear un duplicado.
        for idx, existing_kf in enumerate(path.keyframes):
            if existing_kf.frame == current_frame:
                self.report({'WARNING'}, f"⚠️ Sobrescribiendo keyframe existente en frame {current_frame}")
                _asignar_transform_a_keyframe(existing_kf, cam_eval, foco_eval)
                path.active_keyframe = idx
                for area in context.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
                return {'FINISHED'}

        # Frame nuevo: calcular en qué posición de la lista (ordenada por
        # frame, de menor a mayor) debe quedar -- tantos keyframes existentes
        # como tengan un frame menor al actual.
        posicion_destino = sum(1 for kf in path.keyframes if kf.frame < current_frame)

        # bpy solo permite agregar colecciones al final; se agrega ahí y
        # luego se reordena a su posición correcta con move().
        kf = path.keyframes.add()
        kf.frame = current_frame
        _asignar_transform_a_keyframe(kf, cam_eval, foco_eval)

        indice_actual = len(path.keyframes) - 1
        if posicion_destino != indice_actual:
            path.keyframes.move(indice_actual, posicion_destino)

        path.active_keyframe = posicion_destino

        print(f"\n=== DEBUG INSERTAR KEYFRAME ===")
        print(f"Frame: {current_frame} -> posición {posicion_destino + 1} de {len(path.keyframes)}")
        print(f"Ubicación: ({cam_eval.location.x:.3f}, {cam_eval.location.y:.3f}, {cam_eval.location.z:.3f})")
        print("================================\n")

        self.report(
            {'INFO'},
            f"➕ Keyframe insertado en Frame {current_frame} "
            f"(posición {posicion_destino + 1} de {len(path.keyframes)})"
        )

        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        return {'FINISHED'}


class REPLAY_OT_ApplyCameraPath(Operator):
    bl_idname = "replay.apply_camera_path"
    bl_label = "Aplicar Path"
    bl_description = "Aplicar el path de cámara a la animación"
    
    def execute(self, context):
        settings = _ajustes(context)
        
        if len(settings.camera_paths) == 0:
            self.report({'WARNING'}, "No hay paths creados")
            return {'CANCELLED'}
        
        path = settings.camera_paths[settings.active_path]
        cam = settings.active_camera if settings.active_camera else context.scene.camera
        
        if not cam:
            self.report({'WARNING'}, "No hay cámara seleccionada")
            return {'CANCELLED'}
        
        if len(path.keyframes) < 1:
            self.report({'WARNING'}, "Se necesita al menos 1 keyframe")
            return {'CANCELLED'}
        
        foco = _obtener_foco(context)
        usar_foco = _hornear_path(context, path, cam, foco)

        extra = f" y foco: {foco.name}" if usar_foco else ""
        self.report({'INFO'}, f"Path aplicado a: {cam.name}{extra}")
        return {'FINISHED'}

class REPLAY_OT_PlayReplay(Operator):
    bl_idname = "replay.play_replay"
    bl_label = "Reproducir"
    bl_description = "Reproducir la secuencia de keyframes grabados"

    def execute(self, context):
        settings = _ajustes(context)

        if len(settings.camera_paths) == 0:
            self.report({'WARNING'}, "No hay paths de cámara creados")
            return {'CANCELLED'}

        path = settings.camera_paths[settings.active_path]

        if len(path.keyframes) < 1:
            self.report({'WARNING'}, "Se necesita al menos 1 keyframe para reproducir")
            return {'CANCELLED'}

        cam = settings.active_camera if settings.active_camera else context.scene.camera

        if not cam:
            self.report({'WARNING'}, "No hay cámara seleccionada")
            return {'CANCELLED'}

        # Calcular rango de frames basado en los keyframes
        first_frame = min(kf.frame for kf in path.keyframes)
        last_frame = max(kf.frame for kf in path.keyframes)

        # ✅ NO MODIFICAR frame_start/frame_end - Dejar que el usuario maneje eso
        print(f"🎬 Reproduciendo desde frame {first_frame} hasta {last_frame}")
        print(f"📊 Timeline actual: {context.scene.frame_start} - {context.scene.frame_end}")

        if settings.loop_playback:
            if len(path.keyframes) > 1:
                first_kf = path.keyframes[0]
                
                context.scene.frame_set(last_frame)
                cam.location = Vector((first_kf.location_x, first_kf.location_y, first_kf.location_z))
                cam.rotation_euler = Euler((first_kf.rotation_x, first_kf.rotation_y, first_kf.rotation_z))
                if cam.data.type == 'PERSP':
                    cam.data.lens = first_kf.fov

                cam.keyframe_insert(data_path="location", frame=last_frame)
                cam.keyframe_insert(data_path="rotation_euler", frame=last_frame)
                if cam.data.type == 'PERSP':
                    cam.data.keyframe_insert(data_path="lens", frame=last_frame)

        self.apply_camera_path_to_animation(context, path, cam)

        context.scene.frame_set(first_frame)
        bpy.ops.screen.animation_play()
        settings.is_playing = True

        loop_text = " (Loop)" if settings.loop_playback else ""
        self.report({'INFO'}, f"🎬 Reproduciendo path: {path.name} ({len(path.keyframes)} keyframes){loop_text}")
        return {'FINISHED'}

    def apply_camera_path_to_animation(self, context, path, cam):
        _hornear_path(context, path, cam, _obtener_foco(context))

class REPLAY_OT_DeletePath(Operator):
    bl_idname = "replay.delete_path"
    bl_label = "Eliminar Path"
    bl_description = "Eliminar el path seleccionado"
    
    def execute(self, context):
        settings = _ajustes(context)
        
        if len(settings.camera_paths) > 0:
            settings.camera_paths.remove(settings.active_path)
            settings.active_path = max(0, settings.active_path - 1)
            self.report({'INFO'}, "Path eliminado")
        
        return {'FINISHED'}

class REPLAY_OT_DeleteKeyframe(Operator):
    bl_idname = "replay.delete_keyframe"
    bl_label = "Eliminar Keyframe"
    bl_description = "Eliminar el keyframe seleccionado"
    
    keyframe_index: IntProperty()
    
    def execute(self, context):
        settings = _ajustes(context)
        
        if len(settings.camera_paths) == 0:
            self.report({'WARNING'}, "No hay paths creados")
            return {'CANCELLED'}
        
        path = settings.camera_paths[settings.active_path]
        
        if self.keyframe_index < len(path.keyframes):
            frame_num = path.keyframes[self.keyframe_index].frame
            path.keyframes.remove(self.keyframe_index)
            self.report({'INFO'}, f"Keyframe eliminado del frame {frame_num}")
        
        return {'FINISHED'}

class REPLAY_OT_GotoKeyframe(Operator):
    bl_idname = "replay.goto_keyframe"
    bl_label = "Ir al Keyframe"
    bl_description = "Ir al frame del keyframe y poner la cámara y el foco en sus valores guardados (sin crear claves; ajusta y vuelve a pulsar Aplicar para sobrescribir)"

    keyframe_index: IntProperty()

    def execute(self, context):
        settings = _ajustes(context)
        if len(settings.camera_paths) == 0:
            self.report({'WARNING'}, "No hay paths creados")
            return {'CANCELLED'}
        path = settings.camera_paths[settings.active_path]
        if self.keyframe_index >= len(path.keyframes):
            return {'CANCELLED'}
        cam = settings.active_camera if settings.active_camera else context.scene.camera
        if not cam:
            self.report({'WARNING'}, "No hay cámara seleccionada")
            return {'CANCELLED'}
        kf = path.keyframes[self.keyframe_index]
        context.scene.frame_set(kf.frame)
        _aplicar_keyframe_a_objetos(kf, cam, _obtener_foco(context))
        path.active_keyframe = self.keyframe_index
        self.report({'INFO'}, f"Frame {kf.frame}: cámara{' y foco' if kf.has_focus else ''} en sus valores guardados")
        return {'FINISHED'}


class REPLAY_OT_SelectKeyframe(Operator):
    bl_idname = "replay.select_keyframe"
    bl_label = "Seleccionar Keyframe"
    bl_description = "Hacer activo este keyframe (edita su lente y congelado en la caja de abajo)"

    keyframe_index: IntProperty()

    def execute(self, context):
        settings = _ajustes(context)
        if len(settings.camera_paths) == 0:
            return {'CANCELLED'}
        path = settings.camera_paths[settings.active_path]
        if 0 <= self.keyframe_index < len(path.keyframes):
            path.active_keyframe = self.keyframe_index
        return {'FINISHED'}


class REPLAY_OT_AddFocus(Operator):
    bl_idname = "replay.add_focus"
    bl_label = "Crear punto focal"
    bl_description = "Crear el punto focal (empty 'Foco_Conversacion') frente a la cámara y usarlo como foco del replay"

    def execute(self, context):
        settings = _ajustes(context)
        cam = settings.active_camera if settings.active_camera else context.scene.camera

        foco = context.scene.objects.get("Foco_Conversacion")
        if foco is None:
            foco = bpy.data.objects.new("Foco_Conversacion", None)
            foco.empty_display_type = 'SPHERE'
            foco.empty_display_size = 0.5
            context.collection.objects.link(foco)
            if cam is not None:
                # 5 m delante de la camara (la camara mira hacia su -Z local)
                foco.location = cam.matrix_world @ Vector((0.0, 0.0, -5.0))

        settings.focus_object = foco
        settings.orbit_focus = True      # la camara pasa a girar alrededor del punto focal
        self.report({'INFO'}, f"Punto focal: {foco.name}")
        return {'FINISHED'}


class REPLAY_OT_TakeKeyframeLens(Operator):
    bl_idname = "replay.take_keyframe_lens"
    bl_label = "Tomar lente actual"
    bl_description = "Copiar la lente (mm) actual de la cámara SOLO al keyframe seleccionado (los demás keyframes no cambian)"

    keyframe_index: IntProperty(default=-1)

    def execute(self, context):
        settings = _ajustes(context)
        if len(settings.camera_paths) == 0:
            self.report({'WARNING'}, "No hay paths creados")
            return {'CANCELLED'}
        path = settings.camera_paths[settings.active_path]
        idx = self.keyframe_index if self.keyframe_index >= 0 else path.active_keyframe
        if not (0 <= idx < len(path.keyframes)):
            return {'CANCELLED'}
        cam = settings.active_camera if settings.active_camera else context.scene.camera
        if not cam or cam.data.type != 'PERSP':
            self.report({'WARNING'}, "Se necesita una cámara en perspectiva")
            return {'CANCELLED'}
        kf = path.keyframes[idx]
        kf.fov = cam.data.lens
        self.report({'INFO'}, f"Frame {kf.frame}: lente {kf.fov:.1f} mm")
        return {'FINISHED'}


class REPLAY_OT_PauseReplay(Operator):
    bl_idname = "replay.pause_replay"
    bl_label = "Pausar"
    bl_description = "Pausar o reanudar la reproducción actual"

    def execute(self, context):
        settings = _ajustes(context)

        # Verificar si hay una animación reproduciéndose
        if context.screen.is_animation_playing:
            # Pausar la reproducción
            bpy.ops.screen.animation_play()
            settings.is_playing = False
            self.report({'INFO'}, "⏸️ Reproducción pausada")
        else:
            # Reanudar la reproducción si estaba pausada
            if len(settings.camera_paths) > 0:
                path = settings.camera_paths[settings.active_path]
                if len(path.keyframes) >= 1:
                    bpy.ops.screen.animation_play()
                    settings.is_playing = True
                    self.report({'INFO'}, "▶️ Reproducción reanudada")
                else:
                    self.report({'WARNING'}, "No hay keyframes suficientes para reproducir")
            else:
                self.report({'WARNING'}, "No hay camera paths para reproducir")

        return {'FINISHED'}

class REPLAY_OT_StopReplay(Operator):
    bl_idname = "replay.stop_replay"
    bl_label = "Detener"
    bl_description = "Detener y resetear timeline"

    def execute(self, context):
        # Ejecutar el archivo blender_timeline_reset.py
        reset_file_path = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_1\blender_timeline_reset.py"

        try:
            # Ejecutar el archivo de reset del timeline
            exec(open(reset_file_path).read())

            self.report({'INFO'}, "⏹️ Timeline reseteado completamente")
        except FileNotFoundError:
            self.report({'ERROR'}, f"Archivo no encontrado: {reset_file_path}")
        except Exception as e:
            self.report({'ERROR'}, f"Error ejecutando reset: {str(e)}")

        return {'FINISHED'}

class REPLAY_OT_ExportVideo(Operator):
    bl_idname = "replay.export_video"
    bl_label = "Exportar Video"
    bl_description = "Renderizar la reproducción a video"

    filepath: StringProperty(subtype='FILE_PATH')

    def execute(self, context):
        settings = _ajustes(context)

        if len(settings.recordings) == 0:
            self.report({'WARNING'}, "No hay grabaciones para exportar")
            return {'CANCELLED'}

        rec = settings.recordings[settings.active_recording]

        context.scene.frame_start = rec.start_frame
        context.scene.frame_end = rec.end_frame

        bpy.ops.render.render('INVOKE_DEFAULT', animation=True)

        self.report({'INFO'}, "Exportación iniciada")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class REPLAY_OT_ExportSequence(Operator):
    bl_idname = "replay.export_sequence"
    bl_label = "Exportar Secuencia"
    bl_description = "Exportar la secuencia de camera paths para importar después"

    filepath: StringProperty(subtype='FILE_PATH')

    def execute(self, context):
        settings = _ajustes(context)

        if len(settings.camera_paths) == 0:
            self.report({'WARNING'}, "No hay camera paths para exportar")
            return {'CANCELLED'}

        # Preparar datos para exportar
        export_data = {
            'version': '1.0',
            'export_timestamp': str(datetime.datetime.now()),
            'camera_paths': []
        }

        for path in settings.camera_paths:
            path_data = {
                'name': path.name,
                'interpolation': path.interpolation,
                'keyframes': []
            }

            for kf in path.keyframes:
                kf_data = {
                    'frame': kf.frame,
                    'location_x': kf.location_x,
                    'location_y': kf.location_y,
                    'location_z': kf.location_z,
                    'rotation_x': kf.rotation_x,
                    'rotation_y': kf.rotation_y,
                    'rotation_z': kf.rotation_z,
                    'fov': kf.fov,
                    'freeze': kf.freeze,
                    'freeze_frames': kf.freeze_frames,
                    'has_focus': kf.has_focus,
                    'focus_x': kf.focus_x,
                    'focus_y': kf.focus_y,
                    'focus_z': kf.focus_z,
                    'focus_rx': kf.focus_rx,
                    'focus_ry': kf.focus_ry,
                    'focus_rz': kf.focus_rz
                }
                path_data['keyframes'].append(kf_data)

            export_data['camera_paths'].append(path_data)

        # Guardar archivo
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.report({'INFO'}, f"Secuencia exportada: {len(settings.camera_paths)} paths")
            print(f"✅ Secuencia exportada a: {self.filepath}")
            print(f"📊 Paths exportados: {len(settings.camera_paths)}")

        except Exception as e:
            self.report({'ERROR'}, f"Error exportando secuencia: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}

    def invoke(self, context, event):
        # Nombre por defecto
        settings = _ajustes(context)
        if len(settings.camera_paths) > 0:
            path_names = [p.name for p in settings.camera_paths[:3]]  # Primeros 3 paths
            default_name = "_".join(path_names) + "_sequence.json"
        else:
            default_name = "camera_sequence.json"

        self.filepath = default_name
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class REPLAY_OT_ImportSequence(Operator):
    bl_idname = "replay.import_sequence"
    bl_label = "Importar Secuencia"
    bl_description = "Importar una secuencia de camera paths previamente exportada"

    filepath: StringProperty(subtype='FILE_PATH')

    def execute(self, context):
        settings = _ajustes(context)

        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            if 'camera_paths' not in import_data:
                self.report({'ERROR'}, "Archivo no válido - falta 'camera_paths'")
                return {'CANCELLED'}

            imported_count = 0
            for path_data in import_data['camera_paths']:
                # Crear nuevo path
                path = settings.camera_paths.add()
                path.name = path_data.get('name', f"Imported_Path_{len(settings.camera_paths)}")
                path.interpolation = path_data.get('interpolation', 'BEZIER')

                # Importar keyframes
                for kf_data in path_data.get('keyframes', []):
                    kf = path.keyframes.add()
                    kf.frame = kf_data['frame']
                    kf.location_x = kf_data['location_x']
                    kf.location_y = kf_data['location_y']
                    kf.location_z = kf_data['location_z']
                    kf.rotation_x = kf_data['rotation_x']
                    kf.rotation_y = kf_data['rotation_y']
                    kf.rotation_z = kf_data['rotation_z']
                    kf.fov = kf_data.get('fov', 50.0)
                    kf.freeze = kf_data.get('freeze', False)
                    kf.freeze_frames = kf_data.get('freeze_frames', 12)
                    kf.has_focus = kf_data.get('has_focus', False)
                    kf.focus_x = kf_data.get('focus_x', 0.0)
                    kf.focus_y = kf_data.get('focus_y', 0.0)
                    kf.focus_z = kf_data.get('focus_z', 0.0)
                    kf.focus_rx = kf_data.get('focus_rx', 0.0)
                    kf.focus_ry = kf_data.get('focus_ry', 0.0)
                    kf.focus_rz = kf_data.get('focus_rz', 0.0)

                imported_count += 1
                print(f"✅ Path importado: {path.name} ({len(path.keyframes)} keyframes)")

            if imported_count > 0:
                settings.active_path = len(settings.camera_paths) - 1
                self.report({'INFO'}, f"Secuencia importada: {imported_count} paths")
                print(f"🎬 Secuencia importada exitosamente: {imported_count} camera paths")
            else:
                self.report({'WARNING'}, "No se importaron paths")

        except FileNotFoundError:
            self.report({'ERROR'}, f"Archivo no encontrado: {self.filepath}")
            return {'CANCELLED'}
        except json.JSONDecodeError:
            self.report({'ERROR'}, "Archivo JSON inválido")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error importando secuencia: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# ============================================
# UI LISTS
# ============================================

class REPLAY_UL_Recordings(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, icon='SEQUENCE')
            layout.label(text=f"[{item.start_frame}-{item.end_frame}]")
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='SEQUENCE')

class REPLAY_UL_CameraPaths(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, icon='CAMERA_DATA')
            layout.label(text=f"{len(item.keyframes)} KF")
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='CAMERA_DATA')

class REPLAY_UL_Keyframes(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            rot_x_deg = math.degrees(item.rotation_x)
            rot_y_deg = math.degrees(item.rotation_y)
            rot_z_deg = math.degrees(item.rotation_z)
            
            row = layout.row(align=True)
            # casilla de congelar a la izquierda de la fila (y los frames que se queda quieta, si esta activa)
            row.prop(item, "freeze", text="", icon='FREEZE')
            if item.freeze:
                sub = row.row(align=True)
                sub.scale_x = 0.55
                sub.prop(item, "freeze_frames", text="")
            row.label(text=f"Frame {item.frame}", icon='KEYFRAME')

            col = row.column(align=True)
            col.scale_x = 0.6
            col.label(text=f"{item.fov:g}mm")

            col = row.column(align=True)
            col.scale_x = 0.8
            col.label(text=f"Pos: ({item.location_x:.2f}, {item.location_y:.2f}, {item.location_z:.2f})")
            
            col = row.column(align=True)
            col.scale_x = 0.8
            col.label(text=f"Rot: ({rot_x_deg:.1f}°, {rot_y_deg:.1f}°, {rot_z_deg:.1f}°)")
            
            if item.has_focus:
                col = row.column(align=True)
                col.scale_x = 0.8
                col.label(text=f"Foco: ({item.focus_x:.2f}, {item.focus_y:.2f}, {item.focus_z:.2f})")

            op = row.operator("replay.goto_keyframe", text="", icon='TRIA_RIGHT')
            op.keyframe_index = index
            op = row.operator("replay.delete_keyframe", text="", icon='X')
            op.keyframe_index = index
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='KEYFRAME')

# ============================================
# PANELES
# ============================================

class REPLAY_PT_MainPanel(Panel):
    bl_label = "🎬 Replay Mod - Recorridos de Cámara"
    bl_idname = "REPLAY_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Replay"
    
    def draw(self, context):
        layout = self.layout
        settings = _ajustes(context)
        
        workflow_box = layout.box()
        workflow_box.label(text="🎯 Workflow:", icon='HELP')
        col = workflow_box.column(align=True)
        col.scale_y = 0.9
        col.label(text="1. Seleccionar cámara")
        col.label(text="2. Mover cámara en viewport")
        col.label(text="3. Cambiar frame → Aplicar")
        col.label(text="4. Repetir para crear recorrido")
        col.label(text="5. Reproducir automáticamente")

        box = layout.box()
        row = box.row()
        row.scale_y = 1.5

        if settings.is_recording:
            row.label(text="⬤ GRABANDO", icon='REC')
            row.alert = True
        elif settings.is_playing:
            row.label(text="▶ REPRODUCIENDO", icon='PLAY')
        elif settings.is_preview:
            row.label(text="👁 VISTA PREVIA", icon='CAMERA_DATA')
        else:
            row.label(text="⬤ LISTO", icon='RADIOBUT_OFF')

        layout.separator()
        
        box = layout.box()
        box.label(text="Cámara:", icon='OUTLINER_OB_CAMERA')
        
        row = box.row()
        row.prop_search(settings, "active_camera", context.scene, "objects", text="", icon='CAMERA_DATA')
        
        if settings.active_camera:
            info_box = box.box()
            info_box.scale_y = 0.8
            col = info_box.column(align=True)
            col.label(text=f"Cámara seleccionada:", icon='CHECKMARK')
            col.label(text=f"  • {settings.active_camera.name}")
            
            cam_data = settings.active_camera.data
            if cam_data.type == 'PERSP':
                fov = cam_data.angle * 57.2958
                col.label(text=f"  • FOV: {fov:.1f}°")
                col.label(text=f"  • Focal: {cam_data.lens}mm")
            col.label(text=f"  • Tipo: {cam_data.type}")
            
            cam = settings.active_camera
            col.separator()
            col.label(text="Transform actual:")
            col.label(text=f"  Loc: ({cam.location.x:.3f}, {cam.location.y:.3f}, {cam.location.z:.3f})")
            
            rot_x_deg = math.degrees(cam.rotation_euler.x)
            rot_y_deg = math.degrees(cam.rotation_euler.y)
            rot_z_deg = math.degrees(cam.rotation_euler.z)
            col.label(text=f"  Rot: ({rot_x_deg:.2f}°, {rot_y_deg:.2f}°, {rot_z_deg:.2f}°)")
        else:
            warning_box = box.box()
            warning_box.label(text="⚠ Selecciona una cámara", icon='ERROR')

        layout.separator()

        box = layout.box()
        box.label(text="Foco de la cámara:", icon='EMPTY_AXIS')
        box.prop(settings, "record_focus")
        row = box.row(align=True)
        row.prop_search(settings, "focus_object", context.scene, "objects", text="", icon='EMPTY_AXIS')
        row.operator("replay.add_focus", text="", icon='ADD')
        row2 = box.row()
        row2.prop(settings, "orbit_focus")
        row2.enabled = _obtener_foco(context) is not None
        foco = _obtener_foco(context)
        if foco is not None:
            col = box.column(align=True)
            col.scale_y = 0.8
            col.label(text=f"  • {foco.name}", icon='CHECKMARK')
            col.label(text=f"  Loc: ({foco.location.x:.3f}, {foco.location.y:.3f}, {foco.location.z:.3f})")
            col.label(text=f"  Rot: ({math.degrees(foco.rotation_euler.x):.2f}°, {math.degrees(foco.rotation_euler.y):.2f}°, {math.degrees(foco.rotation_euler.z):.2f}°)")
            box.prop(foco, "location", text="Mover foco")
            box.prop(foco, "rotation_euler", text="Rotar foco")
        elif settings.record_focus:
            box.label(text="Sin foco (se usa 'Foco_Conversacion' si existe)", icon='INFO')

        layout.separator()

        box = layout.box()
        box.label(text="Vista Previa:", icon='WINDOW')
        
        row = box.row()
        row.scale_y = 1.4
        row.operator("replay.open_preview_window", text="Abrir Ventana de Preview", icon='WINDOW')
        row.enabled = settings.active_camera is not None
        
        if settings.is_preview:
            info_box = box.box()
            info_box.label(text="✓ Preview activo", icon='HIDE_OFF')
        
        layout.separator()
        
        box = layout.box()
        box.label(text="Grabación:", icon='RENDER_ANIMATION')
        
        row = box.row(align=True)
        row.scale_y = 1.2
        
        if not settings.is_recording:
            row.operator("replay.start_recording", text="Iniciar Grabación", icon='REC')
            row.enabled = settings.active_camera is not None
        else:
            row.operator("replay.stop_recording", text="Detener Grabación", icon='SNAP_FACE')
            row.alert = True
        
        box.prop(settings, "auto_record")
        box.prop(settings, "output_path")

class REPLAY_PT_RecordingsPanel(Panel):
    bl_label = "Grabaciones"
    bl_idname = "REPLAY_PT_recordings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Replay"
    bl_parent_id = "REPLAY_PT_main"
    
    def draw(self, context):
        layout = self.layout
        settings = _ajustes(context)
        
        row = layout.row()
        row.template_list(
            "REPLAY_UL_Recordings", "",
            settings, "recordings",
            settings, "active_recording"
        )
        
        if len(settings.recordings) > 0:
            box = layout.box()
            box.operator("replay.play_replay", icon='PLAY')
            box.prop(settings, "playback_speed")
            box.operator("replay.export_video", icon='RENDER_ANIMATION')

class REPLAY_PT_CameraPathPanel(Panel):
    bl_label = "🎬 Recorrido de Cámara"
    bl_idname = "REPLAY_PT_camera_path"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Replay"
    bl_parent_id = "REPLAY_PT_main"

    def draw(self, context):
        layout = self.layout
        settings = _ajustes(context)

        box = layout.box()
        box.label(text="PASO 1: Crear Recorrido", icon='ADD')

        if len(settings.camera_paths) == 0:
            box.operator("replay.create_camera_path", text="Crear Nuevo Recorrido", icon='ADD')
            box.label(text="⚠ Crea un recorrido primero", icon='ERROR')
        else:
            row = box.row()
            row.template_list(
                "REPLAY_UL_CameraPaths", "",
                settings, "camera_paths",
                settings, "active_path"
            )

            col = row.column(align=True)
            col.operator("replay.delete_path", text="", icon='REMOVE')

            path = settings.camera_paths[settings.active_path]
            box.label(text=f"📋 Recorrido: {path.name}")
            box.prop(path, "interpolation")

        layout.separator()

        box = layout.box()
        box.label(text="PASO 2: Grabar Posiciones", icon='KEYFRAME_HLT')

        if len(settings.camera_paths) == 0:
            box.label(text="⚠ Crea un recorrido primero", icon='ERROR')
        else:
            current_frame = context.scene.frame_current
            box.label(text=f"🎯 Frame actual de la escena: {current_frame}", icon='TIME')
            
            if settings.active_camera:
                cam_name = settings.active_camera.name
                if cam_name in context.scene.objects:
                    cam = context.scene.objects[cam_name]
                    depsgraph = context.evaluated_depsgraph_get()
                    cam_eval = cam.evaluated_get(depsgraph)
                    
                    transform_box = box.box()
                    transform_box.label(text="Transform a grabar:", icon='ORIENTATION_LOCAL')
                    col = transform_box.column(align=True)
                    col.scale_y = 0.8
                    col.label(text=f"Ubicación: ({cam_eval.location.x:.3f}, {cam_eval.location.y:.3f}, {cam_eval.location.z:.3f})")
                    
                    rot_x_deg = math.degrees(cam_eval.rotation_euler.x)
                    rot_y_deg = math.degrees(cam_eval.rotation_euler.y)
                    rot_z_deg = math.degrees(cam_eval.rotation_euler.z)
                    col.label(text=f"Rotación: ({rot_x_deg:.2f}°, {rot_y_deg:.2f}°, {rot_z_deg:.2f}°)")

                    foco = _obtener_foco(context)
                    if foco is not None:
                        foco_eval = foco.evaluated_get(depsgraph)
                        col.label(text=f"Foco {foco.name}: ({foco_eval.location.x:.3f}, {foco_eval.location.y:.3f}, {foco_eval.location.z:.3f})")

            row = box.row()
            row.scale_y = 1.5
            row.operator("replay.add_keyframe", text="🎬 Aplicar (Grabar Keyframe)", icon='KEYFRAME_HLT')
            row.enabled = settings.active_camera is not None

            row2 = box.row()
            row2.scale_y = 1.5
            row2.operator("replay.insert_keyframe", text="➕ Insertar Keyframe", icon='KEYFRAME')
            row2.enabled = settings.active_camera is not None

            path = settings.camera_paths[settings.active_path]
            box.label(text=f"📊 Keyframes grabados: {len(path.keyframes)}", icon='SNAP_FACE')

            if path.keyframes:
                keyframe_box = box.box()
                keyframe_box.label(text="Lista de Keyframes grabados:", icon='PRESET')
                
                # Lista completa dibujada a mano: una fila por keyframe (en todos).
                total = len(path.keyframes)
                col = keyframe_box.column(align=True)
                for i in range(total):
                    kf_i = path.keyframes[i]
                    row = col.row(align=True)
                    row.prop(kf_i, "freeze", text="", icon='FREEZE')
                    op = row.operator("replay.select_keyframe", text=f"Frame {kf_i.frame}  {kf_i.fov:g}mm",
                                      icon='KEYFRAME_HLT' if i == path.active_keyframe else 'KEYFRAME',
                                      depress=(i == path.active_keyframe))
                    op.keyframe_index = i
                    op = row.operator("replay.goto_keyframe", text="", icon='TRIA_RIGHT')
                    op.keyframe_index = i
                    op = row.operator("replay.delete_keyframe", text="", icon='X')
                    op.keyframe_index = i

                if 0 <= path.active_keyframe < len(path.keyframes):
                    akf = path.keyframes[path.active_keyframe]
                    fbox = keyframe_box.box()
                    fbox.label(text=f"Keyframe activo: frame {akf.frame}", icon='KEYFRAME_HLT')
                    fcol = fbox.column(align=True)
                    fcol.scale_y = 0.8
                    fcol.label(text=f"Pos: ({akf.location_x:.2f}, {akf.location_y:.2f}, {akf.location_z:.2f})")
                    fcol.label(text=f"Rot: ({math.degrees(akf.rotation_x):.1f}°, {math.degrees(akf.rotation_y):.1f}°, {math.degrees(akf.rotation_z):.1f}°)")
                    if akf.has_focus:
                        fcol.label(text=f"Foco: ({akf.focus_x:.2f}, {akf.focus_y:.2f}, {akf.focus_z:.2f})")
                    lrow = fbox.row(align=True)
                    lrow.prop(akf, "fov", text="Lente (mm)")
                    op = lrow.operator("replay.take_keyframe_lens", text="", icon='EYEDROPPER')
                    op.keyframe_index = path.active_keyframe
                    fbox.prop(akf, "freeze", text="Congelar cámara en este keyframe", icon='FREEZE')
                    if akf.freeze:
                        fbox.prop(akf, "freeze_frames", text="Frames quieta")
                        fbox.label(text=f"Quieta del frame {akf.frame} al {akf.frame + akf.freeze_frames}")

        layout.separator()

        box = layout.box()
        box.label(text="PASO 3: Reproducir Recorrido", icon='PLAY')

        if len(settings.camera_paths) == 0:
            box.label(text="⚠ No hay recorridos", icon='ERROR')
        else:
            path = settings.camera_paths[settings.active_path]
            if len(path.keyframes) < 1:
                box.label(text="⚠ Se necesita al menos 1 posición", icon='ERROR')
            else:
                row = box.row(align=True)
                row.scale_y = 1.3

                row.operator("replay.play_replay", text="▶️ Reproducir", icon='PLAY')
                row.operator("replay.pause_replay", text="⏸️ Pausar", icon='PAUSE')
                row.operator("replay.stop_replay", text="⏹️ Detener", icon='SNAP_FACE')

                col = box.column(align=True)
                col.prop(settings, "playback_speed")
                col.prop(settings, "loop_playback")

                frames = [kf.frame for kf in path.keyframes]
                if frames:
                    box.label(text=f"📅 Frames: {min(frames)} - {max(frames)}")
                    box.label(text=f"🎬 Duración: {max(frames) - min(frames)} frames")

        layout.separator()

        box = layout.box()
        box.label(text="💾 Exportar/Importar Secuencia", icon='FILE')

        if len(settings.camera_paths) > 0:
            row = box.row(align=True)
            row.scale_y = 1.2
            row.operator("replay.export_sequence", text="📤 Exportar Secuencia", icon='EXPORT')
            row.operator("replay.import_sequence", text="📥 Importar Secuencia", icon='IMPORT')

            info_box = box.box()
            info_box.scale_y = 0.8
            col = info_box.column(align=True)
            col.label(text="💡 Exporta todos los camera paths", icon='INFO')
            col.label(text="   para reutilizarlos después")
            col.label(text="🔄 Formato: JSON con keyframes")
        else:
            box.label(text="⚠ Crea al menos un path para exportar", icon='ERROR')

# ============================================
# REGISTRO
# ============================================

classes = (
    ReplayKeyframe,
    ReplayCameraPath,
    ReplayRecording,
    ReplaySettings,
    REPLAY_OT_TogglePreview,
    REPLAY_OT_OpenPreviewWindow,
    REPLAY_OT_StartRecording,
    REPLAY_OT_StopRecording,
    REPLAY_OT_CreateCameraPath,
    REPLAY_OT_AddKeyframe,
    REPLAY_OT_InsertKeyframe,
    REPLAY_OT_ApplyCameraPath,
    REPLAY_OT_PlayReplay,
    REPLAY_OT_PauseReplay,
    REPLAY_OT_StopReplay,
    REPLAY_OT_DeletePath,
    REPLAY_OT_DeleteKeyframe,
    REPLAY_OT_GotoKeyframe,
    REPLAY_OT_TakeKeyframeLens,
    REPLAY_OT_SelectKeyframe,
    REPLAY_OT_AddFocus,
    REPLAY_OT_ExportVideo,
    REPLAY_OT_ExportSequence,
    REPLAY_OT_ImportSequence,
    REPLAY_UL_Recordings,
    REPLAY_UL_CameraPaths,
    REPLAY_UL_Keyframes,
    REPLAY_PT_MainPanel,
    REPLAY_PT_RecordingsPanel,
    REPLAY_PT_CameraPathPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.World.replay_settings = PointerProperty(type=ReplaySettings)
    _migrar_ajustes()
    if _migrar_ajustes not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_migrar_ajustes)

def unregister():
    if _migrar_ajustes in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_migrar_ajustes)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.World.replay_settings

if __name__ == "__main__":
    register()