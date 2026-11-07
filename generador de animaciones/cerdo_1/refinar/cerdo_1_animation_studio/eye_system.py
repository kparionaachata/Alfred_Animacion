# -*- coding: utf-8 -*-
"""
eye_system.py — Cerdo_1 Animation Studio v1.8
Sistema de expresiones de mallas rectangulares de ojos (shape keys)
y parpadeo de efecto cortina.
"""
import bpy
from bpy.types import Operator
from bpy.props import BoolProperty
from .blender_compat import get_fcurves
from .constants import (
    EYE_MESH_NAMES,
    SUENO_1_HOLD_RATIO,
    SUENO_2_OSCILLATION_COUNT, SUENO_2_OSCILLATION_LOW, SUENO_2_END_CLOSED,
)

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

def _eye_compute_vertex(orig_co, h_axis, v_axis, bounds, expression, settings, mirror_h=False):
    """
    Desplaza un vertice segun la expresion. Devuelve nueva coordenada.
    mirror_h=True invierte el eje horizontal para el ojo derecho,
    garantizando simetria especular correcta en expresiones asimetricas
    como 'enojado' y 'sospecha'.
    """
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

    # Aplicar espejo horizontal para el ojo derecho en expresiones
    # que tienen componente asimetrica (enojado, sospecha).
    if mirror_h:
        h_factor = -h_factor

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
        # h_norm calculado sobre h_val original (geometria) + efecto espejo via h_factor
        h_norm = (h_val - min_h) / range_h if range_h > 0 else 0.5
        if mirror_h:
            # Espejo: el lado "interior" del ojo derecho corresponde al lado "exterior"
            h_norm = 1.0 - h_norm
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


def build_expression_shape_keys(eye_obj, settings, is_right_eye=False, name_suffix="",
                                preserve_existing=False):
    """
    Crea o regenera los shape keys de expresion para una malla de ojo.
    Nombres de shape keys sin sufijo (name_suffix=""): Basis, Feliz, Triste,
    Enojado, Sospecha, Cerrado, Cansado, Sorpresa, Closed -- este es el juego
    GLOBAL usado por el sistema Inicio/Fin (panel "2b Secuencia de Ojos") y
    la previsualizacion de "Aplicar Expresion en Frame Actual".

    name_suffix (ej. "__seg0"): genera un juego INDEPENDIENTE de shape keys
    con nombres "Feliz__seg0", "Triste__seg0", etc. -- usado por segmentos
    del Paso 3 (Cerdo_1AnimSegment.eye_shapekey) para que la geometria
    (Zona/Curva/Subdivisiones/Swap/Inv) de cada segmento sea completamente
    independiente de la de los demas segmentos y del juego global. Solo se
    reemplazan los shape keys que ya tuvieran ESE MISMO sufijo -- Basis,
    "Closed" (compartido, no depende de Zona/Curva) y los juegos de otros
    segmentos/el global se conservan intactos.

    is_right_eye=True activa el espejo horizontal para garantizar simetria especular
    correcta en expresiones asimetricas (enojado, sospecha).
    """
    _eye_ensure_subdivided(eye_obj, settings.subdivide_cuts)

    if not name_suffix and not preserve_existing:
        # Comportamiento historico (juego global, sin sufijo): limpiar TODO
        # y reconstruir desde cero, igual que siempre.
        if eye_obj.data.shape_keys:
            eye_obj.shape_key_clear()  # limpia todo
        if not eye_obj.data.shape_keys:
            eye_obj.shape_key_add(name="Basis", from_mix=False)
    elif name_suffix:
        # Juego con sufijo (por segmento): NO tocar Basis, "Closed" ni los
        # shape keys de otros sufijos/el global -- solo remover los que ya
        # tuvieran este mismo sufijo, para poder regenerarlos sin duplicar.
        if not eye_obj.data.shape_keys:
            eye_obj.shape_key_add(name="Basis", from_mix=False)
        existing = eye_obj.data.shape_keys.key_blocks
        _to_remove = [sk.name for sk in existing if sk.name.endswith(name_suffix)]
        for _name in _to_remove:
            eye_obj.shape_key_remove(existing[_name])
    else:
        # Las animaciones .py importadas del Paso 1 viven en pistas NLA del
        # datablock Key. Borrar todos los shape keys aqui destruye ese datablock
        # y, con el, las expresiones/parpadeos importados. En modo preservacion
        # mantenemos Basis, geometria y NLA; solo creamos los nombres globales
        # que falten para que el resto del sistema de ojos pueda coexistir.
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
        _shape_name = f"{expr_lower.capitalize()}{name_suffix}"
        if preserve_existing and not name_suffix:
            sk = eye_obj.data.shape_keys.key_blocks.get(_shape_name)
            if sk is not None:
                continue
        sk = eye_obj.shape_key_add(name=_shape_name, from_mix=False)
        sk.value = 0.0
        sk.slider_min = -2.0
        sk.slider_max = 2.0
        for i, orig in enumerate(orig_coords):
            sk.data[i].co = _eye_compute_vertex(
                orig, h_axis, v_axis, bounds, expr_lower, settings,
                mirror_h=is_right_eye,
            )

    # Shape key "Closed" para parpadeo cortina (lleva todos los vertices al Z
    # minimo) -- SIEMPRE compartido/sin sufijo: no depende de Zona/Curva/
    # Subdivisiones, asi que no hace falta un "Closed" propio por segmento.
    if "Closed" not in eye_obj.data.shape_keys.key_blocks:
        sk_closed = eye_obj.shape_key_add(name="Closed", from_mix=False)
        sk_closed.value = 0.0
        min_z = min(v.co.z for v in mesh.vertices)
        for i, v in enumerate(mesh.vertices):
            new_co = v.co.copy()
            new_co.z = min_z
            sk_closed.data[i].co = new_co

    return True


def apply_expression_to_eye(eye_obj, expression_name, value, frame, name_suffix=""):
    """
    Aplica el valor de un shape key de expresion en el frame dado.

    name_suffix (ej. "__seg0"): apunta exclusivamente al juego de shape
    keys propio de ese segmento ("Feliz__seg0", etc.) y solo resetea/
    keyframea esos mismos -- nunca toca "Basis", "Closed", ni los shape
    keys del juego global o de otros segmentos. Sin sufijo (""), apunta al
    juego global (nombres sin sufijo), ignorando los shape keys con sufijo
    de segmentos -- mismo comportamiento historico para el sistema
    Inicio/Fin y la previsualizacion.
    """
    if not eye_obj.data.shape_keys:
        return
    for sk in eye_obj.data.shape_keys.key_blocks:
        if sk.name in ("Basis", "Closed"):
            continue
        if name_suffix:
            if not sk.name.endswith(name_suffix):
                continue
            sk_base_name = sk.name[: -len(name_suffix)]
        else:
            if "__seg" in sk.name:
                continue
            sk_base_name = sk.name
        target_val = value if sk_base_name.lower() == expression_name.lower() else 0.0
        sk.value = target_val
        sk.keyframe_insert(data_path="value", frame=frame)


def apply_expression_interval(eye_obj, expression_name, value, frame_start, frame_end, name_suffix=""):
    """
    Aplica UN intervalo completo de "Expresiones de ojos por intervalos"
    sobre un unico objeto de ojo (se llama una vez por cada malla,
    ojo_izquierdo_cerdo_1 y ojo_derecho_cerdo_1).

    Para las expresiones "normales" (Feliz/Triste/Enojado/Sospecha/
    Cerrado/Cansado/Sorpresa) sigue el patron Inicio/Pico/Fin descrito en
    Cerdo_1EyeExprInterval: neutral en frame_start, el valor de la
    expresion (`value`) en el frame central, y de vuelta a neutral en
    frame_end -- para que el intervalo siguiente arranque limpio.

    "sueno_1" y "sueno_2" (Kebyn, 2026-09-27) son casos especiales que no
    se resuelven con un shape key de expresion propio ni respetan
    `value` -- delegan por completo en los helpers dedicados de abajo,
    que animan el shape key compartido "Closed" (el mismo del parpadeo)
    y, en el caso de sueno_1, tambien hide_viewport/hide_render.
    """
    expr = (expression_name or "").lower()

    # Limpieza previa del canal "Closed"/hide_viewport/hide_render en este
    # rango: _clear_expression_keyframes_in_range (llamada antes por el
    # caller para el resto de shape keys) NUNCA toca "Closed" a proposito
    # (ver su docstring), asi que si este intervalo era antes sueno_1/2 y
    # ahora cambio a otra expresion (o viceversa), un residuo de ojo
    # cerrado/oculto quedaria pisando la expresion nueva sin este paso.
    # frame_start se deja FUERA del rango a limpiar: coincide con el
    # frame_end del intervalo anterior (se encadenan), y ese keyframe
    # (por ejemplo el final "a medias" de un Sueno 2 previo) pertenece al
    # intervalo anterior, no a este -- los helpers de sueno_1/2 de abajo
    # ya sobreescriben frame_start con su propio valor de entrada cuando
    # SI les corresponde a ellos.
    if eye_obj is not None and frame_end > frame_start:
        _clear_blink_keyframes_in_range(eye_obj, frame_start + 1, frame_end)

    if expr == "sueno_1":
        _apply_sueno_1_interval(eye_obj, frame_start, frame_end)
        return
    if expr == "sueno_2":
        _apply_sueno_2_interval(eye_obj, frame_start, frame_end)
        return

    if frame_end <= frame_start:
        apply_expression_to_eye(eye_obj, expr, value, frame_start, name_suffix=name_suffix)
        return

    frame_peak = frame_start + (frame_end - frame_start) // 2
    apply_expression_to_eye(eye_obj, expr, 0.0,   frame_start, name_suffix=name_suffix)
    apply_expression_to_eye(eye_obj, expr, value, frame_peak,  name_suffix=name_suffix)
    apply_expression_to_eye(eye_obj, expr, 0.0,   frame_end,   name_suffix=name_suffix)


def _apply_sueno_1_interval(eye_obj, frame_start, frame_end):
    """
    "Sueno 1" (Kebyn, 2026-09-27: "donde tiene los ojos cerrados las
    mallas de los ojos desaparecen"). Reusa el shape key compartido
    "Closed" (el mismo que usa el parpadeo, ver _ensure_closed_shape_key)
    + hide_viewport/hide_render, en lugar de un shape key propio de esta
    expresion -- mismo mecanismo que apply_blink_sequence, pero sostenido
    durante todo el tramo central del intervalo en vez de unos pocos
    frames de parpadeo.

    Entrada (parpado abierto/visible -> cerrado, justo antes de ocultar)
    en la primera fraccion del intervalo, se mantiene cerrado+invisible
    durante el tramo central (SUENO_1_HOLD_RATIO de la duracion total,
    ver constants.py) y sale (vuelve a mostrarse y reabre el parpado) en
    la ultima fraccion, para que el intervalo siguiente arranque desde un
    estado neutral limpio.
    """
    if eye_obj is None or eye_obj.data is None:
        return
    _clear_blink_keyframes_in_range(eye_obj, frame_start, frame_end)
    _ensure_closed_shape_key(eye_obj)
    ck = eye_obj.data.shape_keys.key_blocks.get("Closed") if eye_obj.data.shape_keys else None

    def _key_closed(frame, val):
        if ck:
            ck.value = val
            ck.keyframe_insert(data_path="value", frame=int(round(frame)))

    def _key_hidden(frame, hidden):
        eye_obj.hide_viewport = hidden
        eye_obj.hide_render   = hidden
        eye_obj.keyframe_insert(data_path="hide_viewport", frame=int(round(frame)))
        eye_obj.keyframe_insert(data_path="hide_render",   frame=int(round(frame)))

    duration = frame_end - frame_start
    if duration < 4:
        # Intervalo demasiado corto para una transicion visible de
        # aparicion/desaparicion -- cierra el parpado pero no oculta la
        # malla (evita un "parpadeo" fantasma de un solo frame).
        _key_closed(frame_start, 0.0)
        _key_closed(frame_end,   1.0)
        _key_hidden(frame_start, False)
        return

    hold_span  = duration * SUENO_1_HOLD_RATIO
    transition = (duration - hold_span) / 2.0
    hold_start = max(frame_start + 1, min(frame_start + transition, frame_end - 2))
    hold_end   = max(hold_start + 1,  min(frame_end - transition,   frame_end - 1))

    _key_closed(frame_start, 0.0)
    _key_closed(hold_start,  1.0)
    _key_closed(hold_end,    1.0)
    _key_closed(frame_end,   0.0)

    _key_hidden(frame_start, False)
    _key_hidden(hold_start,  True)
    _key_hidden(hold_end,    False)

    # hide_viewport/hide_render en CONSTANT: la malla debe ocultarse o
    # mostrarse de golpe en el frame exacto, no a medio interpolar.
    if eye_obj.animation_data and eye_obj.animation_data.action:
        for dp in ("hide_viewport", "hide_render"):
            fc = get_fcurves(eye_obj.animation_data.action).find(dp)
            if fc:
                for kp in fc.keyframe_points:
                    if frame_start <= kp.co.x <= frame_end:
                        kp.interpolation = "CONSTANT"
    # "Closed" con transicion suave (mismo criterio que apply_laugh_sequence).
    if ck and eye_obj.data.shape_keys.animation_data and eye_obj.data.shape_keys.animation_data.action:
        fc = get_fcurves(eye_obj.data.shape_keys.animation_data.action).find('key_blocks["Closed"].value')
        if fc:
            for kp in fc.keyframe_points:
                if frame_start <= kp.co.x <= frame_end:
                    kp.interpolation = "BEZIER"
                    kp.easing = "AUTO"


def _apply_sueno_2_interval(eye_obj, frame_start, frame_end):
    """
    "Sueno 2" (Kebyn, 2026-09-27: "intenta abrir oscilantemente la malla
    del ojo derecho, despues del ojo izquierdo; al final se quedan ambas
    mallas a medias, semiabiertas"). Ambas mallas arrancan cerradas
    (Closed=1.0, sin ocultarse -- a diferencia de Sueno 1, aca el ojo
    esta cerrado pero SIEMPRE visible, intentando abrirse).

    Durante la primera mitad del intervalo, solo la malla del OJO
    DERECHO oscila intentando abrirse (SUENO_2_OSCILLATION_COUNT
    intentos, entre Closed=1.0 y Closed=SUENO_2_OSCILLATION_LOW, ver
    constants.py) mientras la del ojo izquierdo se mantiene cerrada;
    durante la segunda mitad ocurre lo mismo pero con la malla del OJO
    IZQUIERDO. Al llegar a frame_end, AMBAS mallas terminan fijas en
    SUENO_2_END_CLOSED (0.5 por defecto -- "a medias, semiabiertas").
    """
    if eye_obj is None or eye_obj.data is None:
        return
    _clear_blink_keyframes_in_range(eye_obj, frame_start, frame_end)
    _ensure_closed_shape_key(eye_obj)
    ck = eye_obj.data.shape_keys.key_blocks.get("Closed") if eye_obj.data.shape_keys else None
    if ck is None:
        return

    # La malla nunca se oculta en Sueno 2 -- por si un "Sueno 1" anterior
    # la hubiera dejado oculta, la re-mostramos al arrancar el intervalo.
    eye_obj.hide_viewport = eye_obj.hide_render = False
    eye_obj.keyframe_insert(data_path="hide_viewport", frame=frame_start)
    eye_obj.keyframe_insert(data_path="hide_render",   frame=frame_start)

    def _key(frame, val):
        ck.value = val
        ck.keyframe_insert(data_path="value", frame=int(round(frame)))

    _key(frame_start, 1.0)  # ambas mallas arrancan cerradas

    duration = frame_end - frame_start
    if duration <= 0:
        _key(frame_end, SUENO_2_END_CLOSED)
        return

    is_right = (eye_obj.name == "ojo_derecho_cerdo_1")
    mid      = frame_start + duration / 2.0
    # Derecho primero (frame_start -> mid), izquierdo despues (mid -> frame_end).
    own_start, own_end = (frame_start, mid) if is_right else (mid, frame_end)

    if not is_right:
        # Se mantiene cerrada hasta que le toca su turno (evita que la
        # interpolacion "sangre" hacia atras desde su propio intento).
        _key(own_start, 1.0)

    span = own_end - own_start
    if span > 0:
        cycles = max(1, SUENO_2_OSCILLATION_COUNT)
        step   = span / (cycles * 2)
        for i in range(cycles):
            t_open  = own_start + step * (2 * i + 1)
            t_close = own_start + step * (2 * i + 2)
            _key(t_open, SUENO_2_OSCILLATION_LOW)
            if i < cycles - 1:
                _key(t_close, 1.0)

    _key(frame_end, SUENO_2_END_CLOSED)  # final compartido: a medias, semiabiertas

    if eye_obj.data.shape_keys.animation_data and eye_obj.data.shape_keys.animation_data.action:
        fc = get_fcurves(eye_obj.data.shape_keys.animation_data.action).find('key_blocks["Closed"].value')
        if fc:
            for kp in fc.keyframe_points:
                if frame_start <= kp.co.x <= frame_end:
                    kp.interpolation = "BEZIER"
                    kp.easing = "AUTO"


def _get_eye_objects():
    """Devuelve (ojo_izq, ojo_der) o (None, None) si no se encuentran."""
    left  = bpy.data.objects.get("ojo_izquierdo_cerdo_1")
    right = bpy.data.objects.get("ojo_derecho_cerdo_1")
    return left, right


def _clear_expression_keyframes_in_range(eye, start_frame, end_frame, suffix_filter=""):
    """
    Elimina keyframes previos de shape keys de EXPRESION (Feliz/Triste/
    Enojado/Sospecha/Cerrado/Cansado/Sorpresa) y de Location/Rotation/Scale
    del objeto, en el rango [start_frame, end_frame].

    FIX (residuo al re-concatenar "Expresiones de ojos"): a diferencia de
    Parpadeo/Reir/Entendiendo (que ya limpian su propio rango antes de
    escribir, ver _clear_blink_keyframes_in_range / _clear_laugh_keyframes_in_range
    / _clear_understand_keyframes_in_range), el bloque de "Expresiones de
    ojos por intervalos" nunca borraba keyframes previos -- como los
    intervalos van encadenados (cada uno arranca donde termino el anterior),
    editar duraciones/agregar/quitar/reordenar entradas en la lista corre
    las posiciones de frame de la nueva corrida, pero los keyframes de la
    corrida anterior (en las posiciones viejas) seguian ahi, solapandose
    con los valores nuevos. Se limpia aca ANTES de insertar, igual que ya
    se hace con los otros sistemas de ojos.

    suffix_filter="":       solo shape keys SIN sufijo de segmento (juego
                             global, mismo criterio que build_expression_
                             shape_keys/apply_expression_to_eye sin sufijo).
    suffix_filter="__segN": shape keys que CONTENGAN ese sufijo -- cubre
                             tanto "Feliz__segN" (juego compartido del
                             segmento) como "Feliz__segN_ei0", "..._ei1"
                             etc. (shape keys propios por expresion).
    """
    if eye is None:
        return
    # Shape keys de expresion
    if (eye.data and hasattr(eye.data, "shape_keys")
            and eye.data.shape_keys
            and eye.data.shape_keys.animation_data
            and eye.data.shape_keys.animation_data.action):
        action = eye.data.shape_keys.animation_data.action
        for sk in eye.data.shape_keys.key_blocks:
            if sk.name in ("Basis", "Closed"):
                continue
            if suffix_filter:
                if suffix_filter not in sk.name:
                    continue
            else:
                if "__seg" in sk.name:
                    continue
            fc = get_fcurves(action).find('key_blocks["%s"].value' % sk.name)
            if fc:
                to_remove = [kp for kp in fc.keyframe_points
                             if start_frame <= kp.co.x <= end_frame]
                for kp in reversed(to_remove):
                    fc.keyframe_points.remove(kp)
    # Location / Rotation / Scale del objeto (transforms editables por intervalo)
    if eye.animation_data and eye.animation_data.action:
        action = eye.animation_data.action
        for fc in get_fcurves(action):
            if fc.data_path not in ("location", "rotation_euler", "scale"):
                continue
            to_remove = [kp for kp in fc.keyframe_points
                         if start_frame <= kp.co.x <= end_frame]
            for kp in reversed(to_remove):
                fc.keyframe_points.remove(kp)


def _clear_laugh_keyframes_in_range(eye, start_frame, end_frame):
    """
    Elimina keyframes previos del canal Location Z en [start_frame,
    end_frame] antes de regenerar la oscilacion de 'Reir' -- mismo
    criterio que _clear_blink_keyframes_in_range, para evitar que queden
    keyframes viejos (de una config anterior con otro numero de
    oscilaciones) mezclados con los nuevos.
    """
    if eye is None or not eye.animation_data or not eye.animation_data.action:
        return
    fc = get_fcurves(eye.animation_data.action).find("location", index=2)
    if not fc:
        return
    to_remove = [kp for kp in fc.keyframe_points
                 if start_frame <= kp.co.x <= end_frame]
    for kp in reversed(to_remove):
        fc.keyframe_points.remove(kp)


def apply_laugh_sequence(start_frame, end_frame, oscillation_count):
    """
    Filtro "Reir" (Kebyn, 2026-08-18, ajustado 2026-08-18: "solo debe
    oscilar entre Z=1.73 y Z=1.66"): oscila ambas mallas de ojo
    (ojo_izquierdo_cerdo_1, ojo_derecho_cerdo_1) en Z, de forma SINCRONIZADA
    -- exactamente el mismo movimiento y al mismo tiempo en las dos --
    entre start_frame y end_frame. La oscilacion es EXCLUSIVAMENTE entre
    los dos valores fijos EYE_LAUGH_Z_HIGH (1.73) y EYE_LAUGH_Z_LOW (1.66)
    -- no pasa por la posicion base intermedia. Cada oscilacion es medio
    ciclo Alta->Baja; oscillation_count ciclos completos (Alta->Baja->
    Alta) se distribuyen uniformemente en el rango, cerrando siempre en
    Alta al final del intervalo. Solo se anima Location Z; X/Y no se
    tocan.
    """
    from .constants import EYE_LAUGH_Z_HIGH, EYE_LAUGH_Z_LOW

    left, right = _get_eye_objects()
    eyes = [e for e in (left, right) if e]
    if not eyes or oscillation_count <= 0 or end_frame <= start_frame:
        return

    for eye in eyes:
        _clear_laugh_keyframes_in_range(eye, start_frame, end_frame)

    def _key_z(eye, z, frame):
        eye.location.z = z
        eye.keyframe_insert(data_path="location", index=2, frame=frame)

    slot_dur  = end_frame - start_frame
    cycle_dur = slot_dur / oscillation_count
    half_dur  = cycle_dur / 2.0

    _used_frames = {eye.name: set() for eye in eyes}

    def _insert(eye, frame_raw, z):
        f = int(round(frame_raw))
        if f in _used_frames[eye.name]:
            return
        _used_frames[eye.name].add(f)
        _key_z(eye, z, f)

    for i in range(oscillation_count):
        c_start = start_frame + cycle_dur * i
        for eye in eyes:
            _insert(eye, c_start,             EYE_LAUGH_Z_HIGH)
            _insert(eye, c_start + half_dur,  EYE_LAUGH_Z_LOW)

    # Cierra el ultimo ciclo volviendo a Alta en end_frame (evita que la
    # oscilacion "se congele" en Baja despues del ultimo medio-ciclo).
    for eye in eyes:
        _insert(eye, end_frame, EYE_LAUGH_Z_HIGH)

    # Interpolacion suave (BEZIER + AUTO), mismo criterio que el resto del
    # sistema de ojos (ver comentarios de interpolacion en operators_anim.py).
    for eye in eyes:
        if eye.animation_data and eye.animation_data.action:
            fc = get_fcurves(eye.animation_data.action).find("location", index=2)
            if fc:
                for kp in fc.keyframe_points:
                    if start_frame <= kp.co.x <= end_frame:
                        kp.interpolation = "BEZIER"
                        kp.easing = "AUTO"


def _clear_understand_keyframes_in_range(eye, start_frame, end_frame):
    """
    Elimina keyframes previos de Location X y Z en [start_frame, end_frame]
    antes de regenerar el glance de "Entendiendo" -- mismo criterio que
    _clear_laugh_keyframes_in_range, pero sobre DOS canales (X y Z),
    porque este filtro desplaza ambos ejes (Reir solo toca Z).
    """
    if eye is None or not eye.animation_data or not eye.animation_data.action:
        return
    for axis_index in (0, 2):
        fc = get_fcurves(eye.animation_data.action).find("location", index=axis_index)
        if not fc:
            continue
        to_remove = [kp for kp in fc.keyframe_points
                     if start_frame <= kp.co.x <= end_frame]
        for kp in reversed(to_remove):
            fc.keyframe_points.remove(kp)


def apply_understand_sequence(start_frame, end_frame, direction):
    """
    Filtro "Entendiendo" (Kebyn, 2026-08-18): mueve ambas mallas de ojo
    (ojo_izquierdo_cerdo_1, ojo_derecho_cerdo_1) EN SIMULTANEO trazando una
    parabola en el plano X/Z entre 3 posiciones -- Base (start_frame,
    igual a EYE_BASE_TRANSFORMS) -> Apice (frame medio, Z mas alta) ->
    Destino (end_frame, Z de vuelta al nivel de la base, X mas desplazada
    que en el apice) -- exactamente la secuencia de las 3 posiciones de
    referencia capturadas en Blender.

    direction="IZQUIERDA" usa los deltas de X de EYE_UNDERSTAND_APEX_DX /
    EYE_UNDERSTAND_END_DX tal como fueron capturados (ambos ojos se
    desplazan hacia -X). direction="DERECHA" es el espejo horizontal
    exacto -- mismos deltas de Z, deltas de X con el signo invertido --
    para el gesto equivalente hacia el lado opuesto.
    """
    from .constants import (
        EYE_BASE_TRANSFORMS,
        EYE_UNDERSTAND_APEX_DX, EYE_UNDERSTAND_APEX_DZ,
        EYE_UNDERSTAND_END_DX,  EYE_UNDERSTAND_END_DZ,
    )

    left, right = _get_eye_objects()
    eyes = [e for e in (left, right) if e]
    if not eyes or end_frame <= start_frame:
        return

    for eye in eyes:
        _clear_understand_keyframes_in_range(eye, start_frame, end_frame)

    sign      = 1.0 if direction == "IZQUIERDA" else -1.0
    mid_frame = int(round(start_frame + (end_frame - start_frame) / 2.0))
    # Evita que el frame medio colisione con inicio/fin en rangos muy cortos.
    mid_frame = max(start_frame + 1, min(end_frame - 1, mid_frame)) \
        if end_frame - start_frame >= 2 else mid_frame

    def _key_xz(eye, x, z, frame):
        eye.location.x = x
        eye.location.z = z
        eye.keyframe_insert(data_path="location", index=0, frame=frame)
        eye.keyframe_insert(data_path="location", index=2, frame=frame)

    for eye in eyes:
        base = EYE_BASE_TRANSFORMS.get(eye.name)
        if base is None:
            continue
        base_x, _base_y, base_z = base["loc"]

        apex_x = base_x + sign * EYE_UNDERSTAND_APEX_DX[eye.name]
        apex_z = base_z + EYE_UNDERSTAND_APEX_DZ[eye.name]
        end_x  = base_x + sign * EYE_UNDERSTAND_END_DX[eye.name]
        end_z  = base_z + EYE_UNDERSTAND_END_DZ[eye.name]

        _key_xz(eye, base_x, base_z, start_frame)
        _key_xz(eye, apex_x, apex_z, mid_frame)
        _key_xz(eye, end_x,  end_z,  end_frame)

    # Interpolacion suave (BEZIER + AUTO), mismo criterio que apply_laugh_sequence.
    for eye in eyes:
        if eye.animation_data and eye.animation_data.action:
            for axis_index in (0, 2):
                fc = get_fcurves(eye.animation_data.action).find("location", index=axis_index)
                if fc:
                    for kp in fc.keyframe_points:
                        if start_frame <= kp.co.x <= end_frame:
                            kp.interpolation = "BEZIER"
                            kp.easing = "AUTO"


# =============================================================================
# OPERADORES DE EXPRESIONES DE OJOS
# =============================================================================

class CERDO_1_ST_OT_BuildEyeShapeKeys(Operator):
    bl_idname     = "cerdo_1_st.build_eye_shape_keys"
    bl_label      = "Crear/Recrear Shape Keys de Expresion"
    bl_description = (
        "Genera (o regenera) los shape keys de expresion y parpadeo "
        "en las mallas ojo_izquierdo_cerdo_1 y ojo_derecho_cerdo_1"
    )
    bl_options = {"REGISTER", "UNDO"}

    preserve_existing: BoolProperty(
        name="Conservar animacion importada",
        description=(
            "Conserva el datablock, la geometria y las pistas NLA existentes; "
            "solo agrega los shape keys globales que falten"
        ),
        default=False,
        options={"HIDDEN", "SKIP_SAVE"},
    )

    def execute(self, context):
        eye_s = context.scene.cerdo_1_st.eye_expr
        left, right = _get_eye_objects()
        if not left or not right:
            self.report({"ERROR"}, "No se encontraron ojo_izquierdo_cerdo_1 / ojo_derecho_cerdo_1")
            return {"CANCELLED"}
        ok = True
        for eye in (left, right):
            if eye.type != "MESH":
                self.report({"WARNING"}, f"{eye.name} no es una malla"); ok = False; continue
            is_right = (eye == right)
            build_expression_shape_keys(
                eye, eye_s, is_right_eye=is_right,
                preserve_existing=self.preserve_existing,
            )
        if ok:
            self.report({"INFO"}, "Shape keys de expresion creados en ambos ojos")
        return {"FINISHED"}


class CERDO_1_ST_OT_ApplyEyeExpressionPreview(Operator):
    bl_idname     = "cerdo_1_st.apply_eye_expression_preview"
    bl_label      = "Aplicar Expresion en Frame Actual"
    bl_description = "Inserta keyframe con la expresion activa en el frame actual de la timeline"
    bl_options    = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene  = context.scene
        eye_s  = scene.cerdo_1_st.eye_expr
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


class CERDO_1_ST_OT_ResetEyeExpressions(Operator):
    bl_idname     = "cerdo_1_st.reset_eye_expressions"
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

BLINK_SEQUENCE_BASE = {
    1: {"closed": 0.00, "hide": False},
    2: {"closed": 0.25, "hide": False},
    3: {"closed": 0.50, "hide": False},
    4: {"closed": 0.75, "hide": False},
    5: {"closed": 1.00, "hide": True},
    6: {"closed": 1.00, "hide": True},
    7: {"closed": 0.75, "hide": False},
    8: {"closed": 0.50, "hide": False},
    9: {"closed": 0.25, "hide": False},
}

def _ensure_closed_shape_key(eye_obj):
    """Crea shape key Closed (cortina) si no existe ya."""
    if not eye_obj or eye_obj.type != "MESH":
        return
    if not eye_obj.data.shape_keys:
        eye_obj.shape_key_add(name="Basis", from_mix=False)
    names = [sk.name for sk in eye_obj.data.shape_keys.key_blocks]
    if "Closed" not in names:
        sk = eye_obj.shape_key_add(name="Closed", from_mix=False)
        min_z = min(v.co.z for v in eye_obj.data.vertices)
        for i, v in enumerate(eye_obj.data.vertices):
            new_co = v.co.copy()
            new_co.z = min_z
            sk.data[i].co = new_co


def _clear_blink_keyframes_in_range(eye, start_frame, end_frame):
    """
    Elimina keyframes previos de 'Closed', hide_viewport y hide_render
    en el rango [start_frame, end_frame] para evitar interpolacion desde frame 1.
    """
    if eye is None:
        return
    # Limpiar hide_viewport / hide_render del objeto
    if eye.animation_data and eye.animation_data.action:
        for dp in ("hide_viewport", "hide_render"):
            fc = get_fcurves(eye.animation_data.action).find(dp)
            if fc:
                to_remove = [kp for kp in fc.keyframe_points
                             if start_frame <= kp.co.x <= end_frame]
                for kp in reversed(to_remove):
                    fc.keyframe_points.remove(kp)
    # Limpiar shape key 'Closed'
    if (eye.data and hasattr(eye.data, "shape_keys")
            and eye.data.shape_keys
            and eye.data.shape_keys.animation_data
            and eye.data.shape_keys.animation_data.action):
        fc = get_fcurves(eye.data.shape_keys.animation_data.action).find(
            "key_blocks[\"Closed\"].value")
        if fc:
            to_remove = [kp for kp in fc.keyframe_points
                         if start_frame <= kp.co.x <= end_frame]
            for kp in reversed(to_remove):
                fc.keyframe_points.remove(kp)


def apply_blink_sequence(start_frame, end_frame, blink_count, blink_duration):
    """
    Inserta keyframes de parpadeo distribuidos uniformemente entre start_frame y end_frame.
    Usa shape key 'Closed' + hide_viewport/hide_render.
    """
    left, right = _get_eye_objects()
    for eye in (left, right):
        if eye:
            _ensure_closed_shape_key(eye)
            # [FIX] Limpiar keyframes previos del rango para evitar
            # interpolacion indeseada desde frame 1 hasta start_frame.
            _clear_blink_keyframes_in_range(eye, start_frame, end_frame)

    slot_dur = end_frame - start_frame + 1
    # Distribuir parpadeos uniformemente: N segmentos iguales, parpadeo centrado en cada uno
    blink_starts = []
    _segment = slot_dur / blink_count if blink_count > 0 else slot_dur
    for i in range(blink_count):
        _center = start_frame + _segment * (i + 0.5)
        bs = int(_center - blink_duration / 2)
        bs = max(start_frame, min(bs, end_frame - blink_duration))
        blink_starts.append(bs)

    blink_ranges = set()
    for bs in blink_starts:
        for offset in range(blink_duration):
            blink_ranges.add(bs + offset)

    for t in range(start_frame, end_frame + 1):
        blink_applied = False
        for bs in blink_starts:
            if bs <= t < bs + blink_duration:
                blink_applied = True
                offset = t - bs + 1
                fd     = BLINK_SEQUENCE_BASE.get(min(offset, 9), {"closed": 0.0, "hide": False})
                progress = fd["closed"]
                hide     = fd["hide"]
                for eye in (left, right):
                    if eye and eye.data.shape_keys:
                        ck = eye.data.shape_keys.key_blocks.get("Closed")
                        if ck:
                            ck.value = progress
                            ck.keyframe_insert(data_path="value", frame=t)
                        eye.hide_viewport = hide
                        eye.hide_render   = hide
                        eye.keyframe_insert(data_path="hide_viewport", frame=t)
                        eye.keyframe_insert(data_path="hide_render",   frame=t)
                break
        if not blink_applied:
            for eye in (left, right):
                if eye and eye.data.shape_keys:
                    ck = eye.data.shape_keys.key_blocks.get("Closed")
                    if ck:
                        ck.value = 0.0
                        ck.keyframe_insert(data_path="value", frame=t)
                    eye.hide_viewport = False
                    eye.hide_render   = False
                    eye.keyframe_insert(data_path="hide_viewport", frame=t)
                    eye.keyframe_insert(data_path="hide_render",   frame=t)
