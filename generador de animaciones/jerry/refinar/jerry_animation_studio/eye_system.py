
from .blender_compat import get_fcurves as _get_action_fcurves, new_fcurve as _new_fcurve

# -*- coding: utf-8 -*-
"""
eye_system.py — Jerry Animation Studio v1.0
Sistema de expresiones de mallas rectangulares de ojos (shape keys)
y parpadeo de efecto cortina.
"""
import bpy
from bpy.types import Operator
from .constants import EYE_MESH_NAMES, PUPIL_MESH_NAMES, EYE_PUPIL_PAIRS, PUPIL_OFFSET_LIMIT

# =============================================================================
# UTILIDADES DE EXPRESION DE MALLAS
# =============================================================================

def _eye_apply_curve(factor, curve_mode):
    if curve_mode == "QUADRATIC":  return factor ** 2
    if curve_mode == "CUBIC":      return factor ** 3
    return factor

def _eye_detect_axes(mesh_obj):
    """Detecta ejes horizontal, vertical y profundidad por rango de coordenadas."""
    verts = [v.co for v in mesh_obj.data.vertices]
    if not verts:
        return "x", "z", "y"
    xs = [v.x for v in verts]; ys = [v.y for v in verts]; zs = [v.z for v in verts]
    ranges = {"x": max(xs) - min(xs), "y": max(ys) - min(ys), "z": max(zs) - min(zs)}
    sorted_r = sorted(ranges.items(), key=lambda i: i[1])
    depth_axis      = sorted_r[0][0]
    vertical_axis   = sorted_r[1][0]
    horizontal_axis = sorted_r[2][0]
    return horizontal_axis, vertical_axis, depth_axis

def _eye_compute_vertex(orig_co, h_axis, v_axis, bounds, expression, settings):
    """Desplaza un vertice segun la expresion. Devuelve nueva coordenada."""
    cx, cy, cz = bounds["cx"], bounds["cy"], bounds["cz"]
    rx, ry, rz = bounds["rx"], bounds["ry"], bounds["rz"]

    h_val = getattr(orig_co, h_axis)
    v_val = getattr(orig_co, v_axis)

    center_v = {"x": cx, "y": cy, "z": cz}[v_axis]
    range_v  = {"x": rx, "y": ry, "z": rz}[v_axis]
    center_h = {"x": cx, "y": cy, "z": cz}[h_axis]
    range_h  = {"x": rx, "y": ry, "z": rz}[h_axis]

    v_mult = -1 if settings.invert_vertical   else 1
    h_mult = -1 if settings.invert_horizontal else 1

    v_factor = (v_val - center_v) / (range_v / 2) if range_v > 0 else 0
    h_factor = (h_val - center_h) / (range_h / 2) if range_h > 0 else 0

    zone = settings.affect_zone
    if zone == "UPPER":
        if v_factor <= 0:
            return orig_co.copy()
        v_factor_norm = v_factor
    elif zone == "LOWER":
        if v_factor >= 0:
            return orig_co.copy()
        v_factor_norm = -v_factor
    else:
        v_factor_norm = abs(v_factor)

    offset = 0.0
    if expression in ("feliz", "triste"):
        curve = _eye_apply_curve(abs(h_factor), settings.curve_mode)
        intens = settings.intensity_feliz if expression == "feliz" else settings.intensity_triste
        sign   = 1 if expression == "feliz" else -1
        offset = sign * intens * curve * v_factor_norm * v_mult

    elif expression in ("sospecha", "enojado"):
        min_h  = center_h - range_h / 2
        h_norm = (h_val - min_h) / range_h if range_h > 0 else 0.5
        if expression == "sospecha":
            intens = settings.intensity_sospecha
            offset = (intens * h_norm - intens / 2) * v_factor_norm * v_mult * h_mult
        else:
            intens = settings.intensity_enojado
            offset = (-intens * h_norm + intens / 2) * v_factor_norm * v_mult * h_mult

    elif expression == "cerrado":
        offset = -(v_val - center_v) * 0.85

    elif expression == "cansado":
        # Mitad superior comprimida al 50%
        offset = -(v_val - center_v) * 0.4 * v_factor_norm

    elif expression == "sorpresa":
        # Expande ligeramente los vertices superiores
        offset = (v_val - center_v) * 0.15 * v_factor_norm

    new_co = orig_co.copy()
    setattr(new_co, v_axis, v_val + offset)
    return new_co


def _eye_ensure_subdivided(eye_obj, cuts):
    """Subdivide la malla si tiene muy pocos vertices."""
    if cuts <= 0 or len(eye_obj.data.vertices) > 12:
        return
    import bpy as _bpy
    _bpy.context.view_layer.objects.active = eye_obj
    _bpy.ops.object.mode_set(mode="EDIT")
    _bpy.ops.mesh.select_all(action="SELECT")
    for _ in range(cuts):
        _bpy.ops.mesh.subdivide(number_cuts=1)
    _bpy.ops.object.mode_set(mode="OBJECT")


def build_expression_shape_keys(eye_obj, settings):
    """
    Crea o regenera todos los shape keys de expresion para una malla de ojo.
    Nombres de shape keys: Basis, Feliz, Triste, Enojado, Sospecha, Cerrado, Cansado, Sorpresa, Closed
    """
    _eye_ensure_subdivided(eye_obj, settings.subdivide_cuts)

    # Limpiar shape keys anteriores de expresion (conservar Basis)
    if eye_obj.data.shape_keys:
        keep = {"Basis"}
        to_remove = [sk.name for sk in eye_obj.data.shape_keys.key_blocks if sk.name not in keep]
        eye_obj.shape_key_clear()  # limpia todo

    # Crear Basis
    if not eye_obj.data.shape_keys:
        eye_obj.shape_key_add(name="Basis", from_mix=False)

    mesh = eye_obj.data
    orig_coords = [v.co.copy() for v in mesh.vertices]

    # Calcular bounds  (MeshVertex expone .co, no .x/.y/.z directamente)
    xs = [v.co.x for v in mesh.vertices]
    ys = [v.co.y for v in mesh.vertices]
    zs = [v.co.z for v in mesh.vertices]
    bounds = {
        "cx": (max(xs)+min(xs))/2, "cy": (max(ys)+min(ys))/2, "cz": (max(zs)+min(zs))/2,
        "rx": max(xs)-min(xs),     "ry": max(ys)-min(ys),     "rz": max(zs)-min(zs),
    }

    h_axis, v_axis, _ = _eye_detect_axes(eye_obj)
    if settings.swap_axes:
        h_axis, v_axis = v_axis, h_axis

    all_expressions = ["feliz", "triste", "enojado", "sospecha", "cerrado", "cansado", "sorpresa"]

    for expr_lower in all_expressions:
        sk = eye_obj.shape_key_add(name=expr_lower.capitalize(), from_mix=False)
        sk.value = 0.0
        sk.slider_min = -2.0
        sk.slider_max = 2.0
        for i, orig in enumerate(orig_coords):
            sk.data[i].co = _eye_compute_vertex(orig, h_axis, v_axis, bounds, expr_lower, settings)

    # Shape key "Closed" — efecto cortina en espacio mundo (eje Z vertical)
    import mathutils as _mu
    sk_closed = eye_obj.shape_key_add(name="Closed", from_mix=False)
    sk_closed.value = 0.0
    _mat_w = eye_obj.matrix_world
    _mat_l = _mat_w.inverted()
    _verts_w = [_mat_w @ v.co for v in mesh.vertices]
    _min_z_w = min(vw.z for vw in _verts_w)
    for i, vw in enumerate(_verts_w):
        target_w = _mu.Vector((vw.x, vw.y, _min_z_w))
        sk_closed.data[i].co = _mat_l @ target_w

    return True


def apply_expression_to_eye(eye_obj, expression_name, value, frame):
    """Aplica el valor de un shape key de expresion en el frame dado."""
    if not eye_obj.data.shape_keys:
        return
    for sk in eye_obj.data.shape_keys.key_blocks:
        if sk.name == "Basis":
            continue
        target_val = value if sk.name.lower() == expression_name.lower() else 0.0
        sk.value = target_val
        sk.keyframe_insert(data_path="value", frame=frame)


def _get_eye_objects():
    """Devuelve (ojo_izq, ojo_der) o (None, None) si no se encuentran."""
    left  = bpy.data.objects.get("ojo_izquierdo_jerry")
    right = bpy.data.objects.get("ojo_derecho_jerry")
    return left, right


def _get_pupil_objects():
    """Devuelve (pupila_izq, pupila_der) o (None, None)."""
    left  = bpy.data.objects.get("pupila_izquierda_jerry")
    right = bpy.data.objects.get("pupila_derecha_jerry")
    return left, right


# =============================================================================
# SISTEMA DE PUPILAS — desplazamiento de mirada
# =============================================================================

def apply_pupil_offsets(scene, eye_s, frame, pin_constant=False):
    """
    Coloca cada pupila en su posicion BASE propia (del JSON) mas el offset de mirada.
    No usa la posicion de la esclerotica como referencia — cada pupila tiene
    sus propias coordenadas independientes.

    Si pin_constant=True fuerza interpolacion CONSTANT (usado al concatenar).
    """
    if not eye_s.pupil_enabled:
        return

    pupil_L, pupil_R = _get_pupil_objects()

    # Si mirada enlazada: pupila derecha copia offsets de la izquierda
    if eye_s.pupil_link:
        r_off_x = eye_s.pupil_L_offset_x
        r_off_z = eye_s.pupil_L_offset_z
    else:
        r_off_x = eye_s.pupil_R_offset_x
        r_off_z = eye_s.pupil_R_offset_z

    # Cada entry: (objeto, base_x, base_y, base_z, base_rot_z, off_x, off_z)
    configs = [
        (
            pupil_L,
            eye_s.pupil_L_base_x, eye_s.pupil_L_base_y, eye_s.pupil_L_base_z,
            eye_s.pupil_L_base_rot_z,
            eye_s.pupil_L_offset_x, eye_s.pupil_L_offset_z,
        ),
        (
            pupil_R,
            eye_s.pupil_R_base_x, eye_s.pupil_R_base_y, eye_s.pupil_R_base_z,
            eye_s.pupil_R_base_rot_z,
            r_off_x, r_off_z,
        ),
    ]

    for pupil_obj, base_x, base_y, base_z, base_rot_z, off_x, off_z in configs:
        if pupil_obj is None:
            continue

        # Clamp offset al limite
        ox = max(-PUPIL_OFFSET_LIMIT, min(PUPIL_OFFSET_LIMIT, off_x))
        oz = max(-PUPIL_OFFSET_LIMIT, min(PUPIL_OFFSET_LIMIT, off_z))

        # Posicion = base propia + offset de mirada
        pupil_obj.location.x = base_x + ox
        pupil_obj.location.y = base_y          # eje Y no cambia
        pupil_obj.location.z = base_z + oz

        # Rotacion base (pupila_izquierda tiene rot Z = pi, derecha = 0)
        pupil_obj.rotation_euler.x = 0.0
        pupil_obj.rotation_euler.y = 0.0
        pupil_obj.rotation_euler.z = base_rot_z

        pupil_obj.keyframe_insert(data_path="location",       frame=frame)
        pupil_obj.keyframe_insert(data_path="rotation_euler", frame=frame)

        if pin_constant and pupil_obj.animation_data and pupil_obj.animation_data.action:
            for fc in _get_action_fcurves(action):
                if fc.data_path in ("location", "rotation_euler"):
                    for kp in fc.keyframe_points:
                        if int(kp.co.x) == frame:
                            kp.interpolation = "CONSTANT"
                    fc.update()


def apply_pupil_range(scene, eye_s, start_frame, end_frame):
    """
    Clava la posicion de las pupilas durante todo el rango de animacion.
    Inserta keyframes CONSTANT en start y end para que no deriven.
    """
    for frm in (start_frame, end_frame):
        apply_pupil_offsets(scene, eye_s, frm, pin_constant=True)


def _blink_curve_value(offset, total_dur):
    """
    Devuelve el valor del shape key Closed [0.0 - 1.0] para un frame dado
    dentro del parpadeo, calculado dinamicamente segun total_dur.

    Curva de cortina:
      - Primer 40% del parpadeo: cierre  0→1  (acelerado, como un golpe de parpado)
      - Medio  20% del parpadeo: cerrado 1     (ojo completamente cerrado)
      - Ultimo 40% del parpadeo: apertura 1→0  (mas lento, natural)

    El reparto 40/20/40 replica el patron fisiologico real de un parpadeo.
    """
    t = max(0.0, min(1.0, (offset - 1) / max(total_dur - 1, 1)))
    close_end  = 0.40   # fraccion donde termina el cierre
    open_start = 0.60   # fraccion donde empieza la apertura

    if t <= close_end:
        # Cierre: smoothstep acelerado
        p = t / close_end
        return p * p * (3.0 - 2.0 * p)
    elif t <= open_start:
        # Ojo cerrado
        return 1.0
    else:
        # Apertura: smoothstep mas suave
        p = (t - open_start) / (1.0 - open_start)
        return 1.0 - (p * p * (3.0 - 2.0 * p))


def _set_shapekey_kf_interp(obj, sk_name, frame, interp="BEZIER"):
    """Fuerza el tipo de interpolacion del ultimo keyframe insertado en un shape key."""
    if not obj or not obj.data.shape_keys or not obj.data.shape_keys.animation_data:
        return
    action = obj.data.shape_keys.animation_data.action
    if not action:
        return
    dp = f'key_blocks["{sk_name}"].value'
    fc = _get_action_fcurves(action).find(dp)
    if not fc:
        return
    for kp in fc.keyframe_points:
        if abs(kp.co.x - frame) < 0.5:
            kp.interpolation = interp
            break


def _build_blink_map(start_frame, end_frame, blink_count, blink_duration):
    """Calcula (blink_map, anchor_zeros) para UN rango [start_frame, end_frame]
    con blink_count parpadeos distribuidos uniformemente. Logica extraida de
    apply_blink_with_pupils (Kebyn + Claude, 2026-08-07) para poder combinar
    los intervalos de VARIOS segmentos en una sola pasada de keyframes -- ver
    apply_blink_intervals_multi mas abajo."""
    dur = max(blink_duration, 6)   # minimo 6 frames para que el efecto sea visible
    total_frames = end_frame - start_frame + 1
    blink_count = max(1, blink_count)

    slot_size = total_frames / blink_count
    blink_starts = []
    for i in range(blink_count):
        slot_center = start_frame + slot_size * i + slot_size / 2
        bs = int(slot_center - dur / 2)
        bs = max(start_frame, min(bs, end_frame - dur + 1))
        blink_starts.append(bs)

    blink_map = {}
    for bs in blink_starts:
        for offset in range(1, dur + 1):
            frm = bs + offset - 1
            if frm > end_frame:
                break
            val = _blink_curve_value(offset, dur)
            blink_map[frm] = max(blink_map.get(frm, 0.0), val)

    anchor_zeros = set()
    for bs in blink_starts:
        anchor_zeros.add(max(start_frame, bs - 1))
        anchor_zeros.add(min(end_frame, bs + dur))
    anchor_zeros.add(start_frame)
    anchor_zeros.add(end_frame)

    return blink_map, anchor_zeros


def apply_blink_intervals_multi(intervals):
    """
    Version "multi-intervalo" de apply_blink_with_pupils: recibe una lista de
    tuplas (start_frame, end_frame, blink_count, blink_duration) -- tipicamente
    UNA por segmento del Paso 3 (seg.blink_intervals, "Parpadeo automatico por
    segmento") -- y las hornea TODAS en una sola pasada de keyframes sobre el
    shape key "Closed" de esclerotica + pupilas.

    Se procesa en una sola pasada (en vez de llamar apply_blink_with_pupils
    una vez por segmento) para no reconstruir el shape key "Closed" repetidas
    veces sobre la MISMA malla evaluando su matrix_world en frames distintos
    del scrubbing del bake -- eso podria dejar cada segmento con una forma de
    "cerrado" ligeramente distinta si el ojo se mueve en mundo (ej. rig con
    bobbing de cabeza). Con una sola pasada la geometria de "Closed" se
    calcula una unica vez, y todos los intervalos comparten esa misma forma.

    Los rangos de distintos segmentos NO deberian solaparse (los segmentos
    del Paso 3 ya se validan sin solapamiento); si dos intervalos igual
    llegaran a compartir un frame, se usa el valor mayor (mismo criterio que
    dentro de un unico intervalo).
    """
    left,   right   = _get_eye_objects()
    p_left, p_right = _get_pupil_objects()

    all_eyes   = [obj for obj in (left, right)     if obj]
    all_pupils = [obj for obj in (p_left, p_right) if obj]

    if not all_eyes and not all_pupils:
        return False

    for eye in all_eyes:
        _ensure_closed_shape_key(eye)

    # FIX (Kebyn + Claude, 2026-09-05): limpiar TODOS los keyframes previos
    # de la curva "Closed" antes de bakear los nuevos. Sin esto, cambiar la
    # config del panel (menos parpadeos, rango mas angosto, menos segmentos
    # activos) no borraba los keyframes de una corrida anterior que caian
    # fuera del rango actual -- se quedaban pegados en la accion y el
    # personaje seguia parpadeando en esos frames residuales ademas de los
    # nuevos. Afecta tanto a ojos (mismo shape key reutilizado por
    # _ensure_closed_shape_key) como a pupilas (se recrea la malla del
    # shape key pero el fcurve de "value" que lo anima sigue intacto).
    def _clear_closed_curve(obj):
        if not (obj.data.shape_keys and obj.data.shape_keys.animation_data
                and obj.data.shape_keys.animation_data.action):
            return
        action = obj.data.shape_keys.animation_data.action
        fc = _get_action_fcurves(action).find('key_blocks["Closed"].value')
        if fc:
            _get_action_fcurves(action).remove(fc)

    for eye in all_eyes:
        _clear_closed_curve(eye)
    for pupil in all_pupils:
        _clear_closed_curve(pupil)

    global_map = {}
    global_anchors = set()
    for (sf, ef, bc, bd) in intervals:
        if ef <= sf:
            continue
        bmap, anchors = _build_blink_map(sf, ef, bc, bd)
        for frm, val in bmap.items():
            global_map[frm] = max(global_map.get(frm, 0.0), val)
        global_anchors |= anchors

    if not global_map and not global_anchors:
        return False

    all_kf_frames = sorted(set(list(global_map.keys()) + list(global_anchors)))

    for eye in all_eyes:
        if not eye.data.shape_keys:
            continue
        ck = eye.data.shape_keys.key_blocks.get("Closed")
        if not ck:
            continue
        for frm in all_kf_frames:
            val = global_map.get(frm, 0.0)
            ck.value = val
            ck.keyframe_insert(data_path="value", frame=frm)
            interp = "BEZIER" if frm in global_map else "CONSTANT"
            _set_shapekey_kf_interp(eye, "Closed", frm, interp)

    import mathutils as _mu
    for pupil in all_pupils:
        if pupil.type != "MESH":
            continue
        if not pupil.data.shape_keys:
            pupil.shape_key_add(name="Basis", from_mix=False)
        existing = pupil.data.shape_keys.key_blocks.get("Closed")
        if existing:
            pupil.shape_key_remove(existing)
        sk_p = pupil.shape_key_add(name="Closed", from_mix=False)
        sk_p.value = 0.0

        mat_w = pupil.matrix_world
        mat_l = mat_w.inverted()
        verts_w = [mat_w @ v.co for v in pupil.data.vertices]
        min_z_w = min(vw.z for vw in verts_w)
        for i, vw in enumerate(verts_w):
            target_w = _mu.Vector((vw.x, vw.y, min_z_w))
            sk_p.data[i].co = mat_l @ target_w

        for frm in all_kf_frames:
            val = global_map.get(frm, 0.0)
            sk_p.value = val
            sk_p.keyframe_insert(data_path="value", frame=frm)
            _set_shapekey_kf_interp(pupil, "Closed", frm,
                                    "BEZIER" if frm in global_map else "CONSTANT")

    return True


def apply_blink_with_pupils(start_frame, end_frame, blink_count, blink_duration, eye_s=None):
    """
    Parpadeo sincronizado: esclerótica + pupilas con efecto cortina.

    Usa el shape key "Closed" con una curva dinamica calculada segun
    blink_duration real — el efecto siempre es visible y las configuraciones
    del panel tienen efecto inmediato.

    Los parpadeos se distribuyen uniformemente en el rango [start_frame, end_frame].
    Fuera de los parpadeos el shape key "Closed" permanece en 0.0.
    """
    apply_blink_intervals_multi([(start_frame, end_frame, blink_count, blink_duration)])


# =============================================================================
# OPERADORES DE EXPRESIONES DE OJOS
# =============================================================================

class JRRST_OT_BuildEyeShapeKeys(Operator):
    bl_idname     = "jrrst.build_eye_shape_keys"
    bl_label      = "Crear/Recrear Shape Keys de Expresion"
    bl_description = (
        "Genera (o regenera) los shape keys de expresion y parpadeo "
        "en las mallas ojo_izquierdo_jerry y ojo_derecho_jerry"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        eye_s = context.scene.jerryst.eye_expr
        left, right = _get_eye_objects()
        if not left or not right:
            self.report({"ERROR"}, "No se encontraron ojo_izquierdo_jerry / ojo_derecho_jerry")
            return {"CANCELLED"}
        ok = True
        for eye in (left, right):
            if eye.type != "MESH":
                self.report({"WARNING"}, f"{eye.name} no es una malla"); ok = False; continue
            build_expression_shape_keys(eye, eye_s)
        if ok:
            self.report({"INFO"}, "Shape keys de expresion creados en ambos ojos")
        return {"FINISHED"}


class JRRST_OT_ApplyEyeExpressionPreview(Operator):
    bl_idname     = "jrrst.apply_eye_expression_preview"
    bl_label      = "Aplicar Expresion en Frame Actual"
    bl_description = "Inserta keyframe con la expresion activa en el frame actual de la timeline"
    bl_options    = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene  = context.scene
        eye_s  = scene.jerryst.eye_expr
        expr   = eye_s.active_expression.lower()
        val    = eye_s.expression_value
        frame  = scene.frame_current
        left, right = _get_eye_objects()
        if not left or not right:
            self.report({"ERROR"}, "Ojos no encontrados"); return {"CANCELLED"}
        for eye in (left, right):
            if not eye.data.shape_keys:
                self.report({"WARNING"}, f"Crea los shape keys primero ({eye.name})")
                return {"CANCELLED"}
            apply_expression_to_eye(eye, expr, val, frame)
        self.report({"INFO"}, f"Expresion '{expr}' (val={val:.2f}) aplicada en frame {frame}")
        return {"FINISHED"}


class JRRST_OT_ResetEyeExpressions(Operator):
    bl_idname     = "jrrst.reset_eye_expressions"
    bl_label      = "Resetear Expresiones (frame actual)"
    bl_description = "Pone todos los shape keys de expresion a 0 en el frame actual"
    bl_options    = {"REGISTER", "UNDO"}

    def execute(self, context):
        frame  = context.scene.frame_current
        left, right = _get_eye_objects()
        for eye in (left, right):
            if eye and eye.data.shape_keys:
                for sk in eye.data.shape_keys.key_blocks:
                    if sk.name != "Basis":
                        sk.value = 0.0
                        sk.keyframe_insert(data_path="value", frame=frame)
        self.report({"INFO"}, f"Expresiones reseteadas en frame {frame}")
        return {"FINISHED"}


# =============================================================================
# SISTEMA DE PARPADEO (efecto cortina) — funciones de runtime
# =============================================================================

# BLINK_SEQUENCE_BASE eliminado — la curva ahora se genera dinamicamente
# en _blink_curve_value() segun blink_duration real del panel.

def _ensure_closed_shape_key(eye_obj):
    """
    Crea shape key Closed (efecto cortina) si no existe ya.

    El efecto cortina baja todos los vertices hacia el borde INFERIOR
    de la malla en el espacio de mundo — independientemente de la
    rotacion local del objeto.

    Estrategia:
      1. Convertir cada vertice a espacio mundo.
      2. Encontrar el minimo en Y mundo (abajo = Y- en Blender).
      3. Proyectar cada vertice al mismo Y mundo minimo.
      4. Convertir de vuelta a espacio local y guardar en el shape key.
    """
    if not eye_obj or eye_obj.type != "MESH":
        return
    if not eye_obj.data.shape_keys:
        eye_obj.shape_key_add(name="Basis", from_mix=False)
    names = [sk.name for sk in eye_obj.data.shape_keys.key_blocks]
    # Si ya existe Closed pero con datos incorrectos (eje local en vez de mundo),
    # se elimina y se recrea con la logica correcta.
    if "Closed" in names:
        old_sk = eye_obj.data.shape_keys.key_blocks.get("Closed")
        if old_sk:
            eye_obj.shape_key_remove(old_sk)
        names = [sk.name for sk in eye_obj.data.shape_keys.key_blocks]

    if "Closed" not in names:
        import mathutils
        sk = eye_obj.shape_key_add(name="Closed", from_mix=False)

        mat_world = eye_obj.matrix_world
        mat_local = mat_world.inverted()

        # Coordenadas de cada vertice en espacio mundo
        verts_world = [mat_world @ v.co for v in eye_obj.data.vertices]

        # El borde inferior de la malla en Z mundo (eje vertical en Blender)
        # Las mallas de ojo de Jerry tienen rot (0,-90,-90) por lo que el
        # eje vertical en mundo es Z. La cortina baja = vertices van al min Z mundo.
        min_z_world = min(vw.z for vw in verts_world)

        for i, vw in enumerate(verts_world):
            # Colapsar el eje Z mundo al minimo (borde inferior)
            target_world = mathutils.Vector((vw.x, vw.y, min_z_world))
            # Convertir de vuelta a espacio local
            target_local = mat_local @ target_world
            sk.data[i].co = target_local


def apply_blink_sequence(start_frame, end_frame, blink_count, blink_duration, eye_s=None):
    """
    Wrapper de compatibilidad — delega en apply_blink_with_pupils para que
    esclerótica y pupilas parpadeen sincronizadas.
    """
    apply_blink_with_pupils(start_frame, end_frame, blink_count, blink_duration, eye_s)



# =============================================================================
# OPERADORES DE PUPILAS
# =============================================================================

class JRRST_OT_ApplyPupilGaze(bpy.types.Operator):
    bl_idname     = "jrrst.apply_pupil_gaze"
    bl_label      = "Aplicar mirada en frame actual"
    bl_description = "Mueve las pupilas segun los offsets del panel e inserta keyframe"
    bl_options    = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene  = context.scene
        eye_s  = scene.jerryst.eye_expr
        if not eye_s.pupil_enabled:
            self.report({"WARNING"}, "Pupilas desactivadas en el panel"); return {"CANCELLED"}
        apply_pupil_offsets(scene, eye_s, scene.frame_current)
        self.report({"INFO"}, f"Mirada de pupilas aplicada en frame {scene.frame_current}")
        return {"FINISHED"}


class JRRST_OT_ResetPupilGaze(bpy.types.Operator):
    bl_idname     = "jrrst.reset_pupil_gaze"
    bl_label      = "Centrar pupilas"
    bl_description = "Pone los offsets a 0 y aplica keyframe de pupilas centradas"
    bl_options    = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        eye_s = scene.jerryst.eye_expr
        eye_s.pupil_L_offset_x = 0.0
        eye_s.pupil_L_offset_z = 0.0
        eye_s.pupil_R_offset_x = 0.0
        eye_s.pupil_R_offset_z = 0.0
        apply_pupil_offsets(scene, eye_s, scene.frame_current)
        self.report({"INFO"}, f"Pupilas centradas en frame {scene.frame_current}")
        return {"FINISHED"}

# =============================================================================
# FILTROS DE MOVIMIENTO ORGANICO  (post-proceso sobre fcurves)
# =============================================================================

def _noise_at(frame, freq, seed, dim=0):
    """Ruido procesal deterministico (sin-hash sin bpy.app.driver_namespace)."""
    v = math.sin(frame * freq * 1.3 + seed * 7.3 + dim * 3.7)
    v += math.sin(frame * freq * 2.7 + seed * 2.1 + dim * 5.1) * 0.5
    v += math.sin(frame * freq * 5.1 + seed * 4.9 + dim * 1.3) * 0.25
    return v / 1.75   # rango aprox. [-1, 1]

def _gaussian_smooth(values, factor):
    """Suavizado gaussiano de una lista de valores con factor [0,1]."""
    n = len(values)
    if n < 3:
        return values[:]
    out = values[:]
    w   = [0.25, 0.5, 0.25]
    for i in range(1, n - 1):
        out[i] = values[i - 1] * w[0] + values[i] * w[1] + values[i + 1] * w[2]
        out[i] = values[i] * (1 - factor) + out[i] * factor
    return out

def _apply_organic_filters(context, armature, start_frame, end_frame, org):
    """
    Aplica filtros organicos sobre las fcurves ya generadas.
    Lee los valores de los keyframes existentes, les suma las micro-variaciones
    y escribe los valores modificados de vuelta a los mismos keyframes.
    """
    scene = context.scene
    frames = list(range(start_frame, end_frame + 1))
    n = len(frames)
    if n < 3:
        return

    # ── FILTRO: suavizado de fcurves ──
    if org.smooth_curves_enabled and armature.animation_data and armature.animation_data.action:
        action = armature.animation_data.action
        for fc in _get_action_fcurves(action):
            kps = sorted(fc.keyframe_points, key=lambda k: k.co.x)
            vals = [k.co.y for k in kps]
            for _ in range(org.smooth_passes):
                vals = _gaussian_smooth(vals, org.smooth_factor)
            for k, v in zip(kps, vals):
                k.co.y = v
            fc.update()

    # ── Funciones auxiliares para modificar pose bones por frame ──
    def _mod_bone_rot(bone_name, axis, deltas):
        """Suma deltas[frame_idx] al rotation_euler[axis] del bone ya keyframeado."""
        if not armature.animation_data or not armature.animation_data.action:
            return
        dp   = f'pose.bones["{bone_name}"].rotation_euler'
        fc   = _get_action_fcurves(action).find(dp, index=axis)
        if fc is None:
            return
        kps = sorted(fc.keyframe_points, key=lambda k: k.co.x)
        # Construir mapa frame->kp para los frames en rango
        kmap = {int(k.co.x): k for k in kps if start_frame <= int(k.co.x) <= end_frame}
        for i, f in enumerate(frames):
            if f in kmap:
                kmap[f].co.y += deltas[i]
        fc.update()

    def _mod_bone_loc(bone_name, axis, deltas):
        if not armature.animation_data or not armature.animation_data.action:
            return
        dp = f'pose.bones["{bone_name}"].location'
        fc = _get_action_fcurves(action).find(dp, index=axis)
        if fc is None:
            return
        kps  = sorted(fc.keyframe_points, key=lambda k: k.co.x)
        kmap = {int(k.co.x): k for k in kps if start_frame <= int(k.co.x) <= end_frame}
        for i, f in enumerate(frames):
            if f in kmap:
                kmap[f].co.y += deltas[i]
        fc.update()

    def _mod_bone_scale(bone_name, axis, deltas):
        if not armature.animation_data or not armature.animation_data.action:
            return
        dp = f'pose.bones["{bone_name}"].scale'
        fc = _get_action_fcurves(action).find(dp, index=axis)
        if fc is None:
            return
        kps  = sorted(fc.keyframe_points, key=lambda k: k.co.x)
        kmap = {int(k.co.x): k for k in kps if start_frame <= int(k.co.x) <= end_frame}
        for i, f in enumerate(frames):
            if f in kmap:
                kmap[f].co.y += deltas[i]
        fc.update()

    # ── FILTRO: respiracion ──
    if org.breathing_enabled:
        amp   = org.breathing_amplitude
        speed = org.breathing_speed
        phase = org.breathing_phase
        deltas_x = [amp * math.sin(f * speed * 2 * math.pi + phase) for f in frames]
        deltas_z = [amp * 0.4 * math.sin(f * speed * 2 * math.pi + phase + 1.2) for f in frames]
        for bone in ("Spine_alfred", "Spine1_alfred"):
            _mod_bone_rot(bone, 0, deltas_x)   # X
            _mod_bone_rot(bone, 2, deltas_z)   # Z

    # ── FILTRO: micro-movimiento de cabeza ──
    if org.head_sway_enabled:
        amp   = org.head_sway_amplitude
        speed = org.head_sway_speed
        seed  = org.head_sway_seed
        for axis in range(3):
            deltas = [amp * _noise_at(f, speed, seed, axis) for f in frames]
            for bone in ("Neck_alfred", "face_alfred"):
                _mod_bone_rot(bone, axis, deltas)

    # ── FILTRO: desplazamiento de peso (hips lateral) ──
    if org.weight_shift_enabled:
        amp   = org.weight_shift_amplitude
        speed = org.weight_shift_speed
        deltas_loc_x = [amp * math.sin(f * speed * 2 * math.pi) for f in frames]
        deltas_rot_z = [amp * 0.8 * math.cos(f * speed * 2 * math.pi) for f in frames]
        _mod_bone_loc("Hips_alfred", 0, deltas_loc_x)
        _mod_bone_rot("Hips_alfred", 2, deltas_rot_z)

    # ── FILTRO: noise en hombros ──
    if org.shoulder_noise_enabled:
        amp   = org.shoulder_noise_amplitude
        speed = org.shoulder_noise_speed
        seed  = org.shoulder_noise_seed
        for axis in range(3):
            for bone, s_off in (("RightUpArm_alfred", 0), ("LeftUpArm_alfred", 17)):
                deltas = [amp * _noise_at(f, speed, seed + s_off, axis) for f in frames]
                _mod_bone_rot(bone, axis, deltas)

    # ── FILTRO: micro-escala organica ──
    if org.micro_scale_enabled:
        amp   = org.micro_scale_amplitude
        speed = org.breathing_speed  # sincronizado con respiracion
        phase = org.breathing_phase
        deltas_s = [amp * math.sin(f * speed * 2 * math.pi + phase) for f in frames]
        _mod_bone_scale("Spine1_alfred", 2, deltas_s)   # escala Z del Spine1

    # ── FILTRO: secondary motion brazos (retardo de codos) ──
    if org.secondary_motion_enabled:
        lag     = int(round(org.secondary_motion_lag))
        damping = org.secondary_motion_damping
        if armature.animation_data and armature.animation_data.action:
            action = armature.animation_data.action
            for bone in ("Rightelbow_alfred", "Leftelbow_alfred"):
                dp = f'pose.bones["{bone}"].rotation_euler'
                for axis in range(3):
                    fc = _get_action_fcurves(action).find(dp, index=axis)
                    if fc is None:
                        continue
                    kps  = sorted(fc.keyframe_points, key=lambda k: k.co.x)
                    kmap = {int(k.co.x): k for k in kps}
                    vals = [kmap[f].co.y if f in kmap else 0.0 for f in frames]
                    # Aplicar retardo: el elbow sigue al UpArm con lag frames de retraso
                    delayed = [0.0] * n
                    for i in range(n):
                        src_i = max(0, i - lag)
                        delayed[i] = vals[src_i] * (1 - damping) + vals[i] * damping
                    # Blend: 30% delayed + 70% original para no romper la pose base
                    for i, f in enumerate(frames):
                        if f in kmap:
                            kmap[f].co.y = vals[i] * 0.7 + delayed[i] * 0.3
                    fc.update()

    # ── FILTRO: noise en posicion del root ──
    if org.root_noise_enabled:
        root_obj = scene.objects.get("jerry")
        if root_obj and root_obj.animation_data and root_obj.animation_data.action:
            root_action = root_obj.animation_data.action
            strength = org.root_noise_strength
            freq     = org.root_noise_frequency
            seed     = org.root_noise_seed
            for axis in range(3):
                fc = _get_action_fcurves(root_action).find("location", index=axis)
                if fc is None:
                    continue
                kps  = sorted(fc.keyframe_points, key=lambda k: k.co.x)
                kmap = {int(k.co.x): k for k in kps}
                for i, f in enumerate(frames):
                    if f in kmap:
                        kmap[f].co.y += strength * _noise_at(f, freq, seed, axis)
                fc.update()


