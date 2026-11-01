# -*- coding: utf-8 -*-
"""
slot_001_caminar.py
Zombie - Slot 1

GENERADO AUTOMÁTICAMENTE
Fecha de generación: 2026-10-22
"""

import bpy
import math

# ============================================
# CONFIGURACIÓN DEL SLOT
# ============================================

SLOT_INDEX = 1
START_FRAME = 1
END_FRAME = 60  # 1 + 60 - 1
TOTAL_FRAMES = 60
FINAL_FRAME = END_FRAME

# ============================================
# DATOS DE TRAYECTORIA EMBEBIDOS - SLOT 1
# ============================================

EMBEDDED_TRAJECTORY_POINTS = [
    {
        "index": 0,
        "coordinates": {"x": 0, "y": 0, "z": 0},
        "texture": "grass_block_top",
        "face_index": "0"
    },
    {
        "index": 1,
        "coordinates": {"x": 1, "y": 1, "z": 0},
        "texture": "grass_block_top",
        "face_index": "0"
    },
    {
        "index": 2,
        "coordinates": {"x": 2, "y": 2, "z": 0},
        "texture": "grass_block_top",
        "face_index": "0"
    },
    {
        "index": 3,
        "coordinates": {"x": 3, "y": 2, "z": 0},
        "texture": "grass_block_top",
        "face_index": "0"
    },
    {
        "index": 4,
        "coordinates": {"x": 4, "y": 2, "z": 0},
        "texture": "grass_block_top",
        "face_index": "0"
    },
]

# ============================================
# FIN DE CONFIGURACIÓN DEL SLOT 1
# ============================================

ANIMATION_INFO = {
    'name': 'slot_001_caminar.py',
    'frame_count': 60,
    'fps': 24,
    'duration_seconds': 2.5000,
    'entity': 'Zombie',
    'slot': 1,
    'movement_type': 'walking_cycle_realistic',
    'walk_style': 'NORMAL',
}

ANIMATION_CONFIG = {
    'name': 'slot_001_caminar',
    'frame_count': 60,
    'fps': 24,
    'duration_seconds': 2.5000,
    'entity': 'Zombie',
    'slot': 1,
    'movement_type': 'walking_cycle_realistic',
    'walk_cycles': 3.0,
    'ranges': {
        # Valores base calibrados en NORMAL, escalados por el multiplicador
        # del estilo elegido ('NORMAL' = Caminar Normal) en tiempo
        # de generacion -- no en tiempo de ejecucion.
        'arm_base_x': math.radians(90.0000),
        'arm_base_y': 0,
        'arm_base_z': 0,
        'arm_swing_y': math.radians(70.0000),
        'arm_spread_z': 0,
        'elbow_flex': math.radians(50.0000),
        'leg_swing_x': math.radians(50.0000),
        'leg_sway_z': math.radians(3),
        'leg_rotation_y': math.radians(4),
        'knee_flex': math.radians(40.0000),
        'hip_forward': math.radians(3),
        'hip_sway': math.radians(4),
        'hip_tilt': math.radians(4),
        'spine_bend': math.radians(0.1000),
        'spine_compensation': 0.6,
        'neck_tilt': math.radians(1.5000),
        'neck_nod': math.radians(1.0000),
        'head_stabilization': 0.25,
    },
}

BLINK_SEQUENCE = {
    1: {"closed": 0.0, "hide": False},
    2: {"closed": 0.25, "hide": False},
    3: {"closed": 0.5, "hide": False},
    4: {"closed": 0.75, "hide": False},
    5: {"closed": 1.0, "hide": True},
    6: {"closed": 1.0, "hide": True},
    7: {"closed": 0.75, "hide": False},
    8: {"closed": 0.5, "hide": False},
    9: {"closed": 0.25, "hide": False},
}

TARGET_ROTATION = -90  # Grados - rotacion Z del root (eje Z solamente)
ROOT_ROTATION_X = 0  # Rotacion X del root en grados
ROOT_ROTATION_Y = 0  # Rotacion Y del root en grados
ROOT_ROTATION_Z = -90  # Rotacion Z del root en grados

# ============================================
# ESTILO DE CAMINATA (multiplexor)
# ============================================
WALK_STYLE       = "NORMAL"                       # NORMAL/LENTO
LEAN_FORWARD     = 0.0               # radianes, inclinacion CONSTANTE de columna (aplicado en spine_forward)
VERTICAL_BOB     = 0.0                # metros, rebote vertical del root por apoyo (aplicado sobre pos.z)
ASYM_RIGHT_LEG   = 0.0              # 0.0-1.0, debilita/atrasa pierna derecha / cojera (aplicado en right_leg_cycle/right_leg_swing)
KNEE_DAMAGE_RIGHT = 0.0                # 0.0-1.0, reduce/bloquea la flexion de la rodilla derecha (aplicado en calculate_knee_flex)
HEAD_LOCKED      = 0.0                 # 0.0-1.0, mezcla la cabeza hacia (0,0,0) = mirando siempre al frente, ignorando el balanceo del cuerpo
SPASM_AMP        = 0.0                   # radianes, amplitud de sacudidas musculares en rafagas (aplicado via _spasm_offset en brazos/columna)
ARM_DOWN_RIGHT   = 0.0               # 0.0-1.0, mezcla el brazo derecho desde la pose "Minecraft" hacia 0 (colgando pegado al cuerpo)
CLAW_ARMS        = 0.0                   # 0.0/1.0, reemplaza la pose "Minecraft" fija por brazos extendidos al frente + codo flexionando (zarpazos), ver bloque "estilo RAPIDO_B" en execute_animation
CLAW_ARM_SPEED   = 1.0                 # multiplicador sobre walk_cycle para la fase de los brazos (1.0 = misma cadencia que las piernas, <1.0 = brazos oscilan mas lento/pocas veces)
CLAW_ARM_ASYM    = 0.0                  # 0.0-1.0, brazo derecho "dominante" (zarpazo mas amplio y adelantado) vs izquierdo mas corto/rezagado -- mismo patron que ASYM_RIGHT_LEG pero aplicado a los brazos


# ============================================
# FUNCIONES DE EASING
# ============================================

def ease_in_out_sine(t):
    return -(math.cos(math.pi * t) - 1) / 2

def ease_in_out_cubic(t):
    if t < 0.5:
        return 4 * t * t * t
    return 1 - pow(-2 * t + 2, 3) / 2


# ============================================
# FUNCIONES BIOMECÁNICAS
# ============================================

def calculate_leg_swing(phase, config):
    max_swing = config['ranges']['leg_swing_x']
    return max_swing * math.sin(phase * 2 * math.pi)

def calculate_knee_flex(phase, config, damage=0.0):
    """Flexion de rodilla: se dobla al levantar la pierna (mitad del ciclo
    en que avanza hacia adelante), se estira al apoyar. 'damage' (0.0-1.0)
    reduce la flexion disponible -- una rodilla muy dañada (damage~1.0)
    queda practicamente rigida ('pata de palo')."""
    max_flex = config['ranges']['knee_flex'] * (1.0 - damage)
    return max(0.0, math.sin(phase * 2 * math.pi)) * max_flex

def _spasm_offset(t, amplitude):
    """Sacudida muscular en rafagas cortas e irregulares (no un tembleque
    continuo): la mayor parte del tiempo devuelve 0.0, y cada ~55 frames
    dispara una rafaga de ~8 frames con un jitter de alta frecuencia
    envuelto en una curva que sube y baja (para que no sea un corte seco).
    Determinista (depende solo de t) para que la bake sea reproducible."""
    if amplitude <= 0.0:
        return 0.0
    cycle = 55
    local = t % cycle
    burst_len = 8
    if local >= burst_len:
        return 0.0
    envelope = math.sin((local / burst_len) * math.pi)
    jitter = math.sin(t * 9.3) * math.sin(t * 3.7 + 1.1)
    return jitter * envelope * amplitude

def calculate_arm_swing(phase, config):
    max_swing = config['ranges']['arm_swing_y']
    if phase < 0.5:
        t = phase / 0.5
        return ease_in_out_sine(t) * max_swing * 2 - max_swing
    else:
        t = (phase - 0.5) / 0.5
        return max_swing - ease_in_out_sine(t) * max_swing * 2

def calculate_elbow_flex(phase, config):
    max_flex = config['ranges']['elbow_flex']
    if phase < 0.3:
        t = phase / 0.3
        return ease_in_out_sine(t) * max_flex * 0.85 + max_flex * 0.15
    elif phase < 0.7:
        t = (phase - 0.3) / 0.4
        return max_flex - ease_in_out_cubic(t) * max_flex * 0.6
    else:
        t = (phase - 0.7) / 0.3
        return max_flex * 0.4 - ease_in_out_sine(t) * max_flex * 0.25


# ============================================
# CARGA DE SEGMENTOS Y POSICIONAMIENTO
# ============================================

def _load_segments():
    pts = EMBEDDED_TRAJECTORY_POINTS
    segs = []
    for i in range(len(pts) - 1):
        s = pts[i]['coordinates']
        e = pts[i + 1]['coordinates']
        segs.append({
            'start': [s['x'], s['y'], s['z']],
            'end': [e['x'], e['y'], e['z']],
            'texture': pts[i].get('texture', 'grass_block_top')
        })
    return segs

# ============================================================
# SISTEMA DE SUAVIZADO DE ROTACIÓN
# ============================================================

class RotationSmoother:
    """Suaviza cambios de orientación con curva S (smoothstep)."""
    def __init__(self, smoothing_frames=12):
        self.smoothing_frames = smoothing_frames
        self.previous_rotation = None
        self.transition_start_frame = None
        self.transition_start_rotation = None
        self.target_rotation = None

    def smooth_rotation(self, target_rotation, current_frame):
        target_rotation = self._normalize(target_rotation)
        if self.previous_rotation is None:
            self.previous_rotation = target_rotation
            return target_rotation
        angle_diff = self._diff(target_rotation, self.previous_rotation)
        if abs(angle_diff) < 5:
            self.previous_rotation = target_rotation
            self.transition_start_frame = None
            return target_rotation
        if self.transition_start_frame is None:
            self.transition_start_frame = current_frame
            self.transition_start_rotation = self.previous_rotation
            self.target_rotation = target_rotation
        elapsed  = current_frame - self.transition_start_frame
        progress = min(elapsed / self.smoothing_frames, 1.0)
        eased    = self._smoothstep(progress)
        smoothed = self.transition_start_rotation + self._diff(self.target_rotation, self.transition_start_rotation) * eased
        if progress >= 1.0:
            self.previous_rotation = target_rotation
            self.transition_start_frame = None
            return target_rotation
        return smoothed

    def _normalize(self, a):
        while a >  180: a -= 360
        while a < -180: a += 360
        return a

    def _diff(self, target, current):
        d = target - current
        while d >  180: d -= 360
        while d < -180: d += 360
        return d

    def _smoothstep(self, x):
        if x <= 0: return 0.0
        if x >= 1: return 1.0
        return x * x * (3.0 - 2.0 * x)


def _compute_direction_angle_local(p0, p1):
    """Calcula ángulo de orientación cardinal/diagonal para un segmento."""
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    if dx == 0 and dy == 0:
        return None
    ang_raw = math.degrees(math.atan2(dx, dy))
    ang_rounded = round(ang_raw / 90.0) * 90.0
    ang_diff = abs(ang_raw - ang_rounded)
    if ang_diff < 45:
        ang = ang_rounded
    else:
        ang = -ang_raw
    while ang >  180: ang -= 360
    while ang < -180: ang += 360
    if   ang ==  90: ang = -90
    elif ang == -90: ang =  90
    return ang


def _get_segment_angle_for_frame(segments, frames_per_seg, cum_frames, frame):
    """Devuelve el ángulo del segmento activo para el frame dado."""
    prev = 0
    for j, cf in enumerate(cum_frames):
        if frame <= cf:
            s = segments[j]['start']
            e = segments[j]['end']
            ang = _compute_direction_angle_local(s, e)
            return ang if ang is not None else ROOT_ROTATION_Z
        prev = cf
    s = segments[-1]['start']
    e = segments[-1]['end']
    ang = _compute_direction_angle_local(s, e)
    return ang if ang is not None else ROOT_ROTATION_Z


# Instancia global del suavizador (smoothing_frames=12 → 0.5s a 24fps)
_rotation_smoother = RotationSmoother(smoothing_frames=12)


def _compute_frames_allocation(segments, total_frames):
    dists = []
    for seg in segments:
        s, e = seg['start'], seg['end']
        dx, dy, dz = e[0]-s[0], e[1]-s[1], e[2]-s[2]
        dists.append(max(0.0001, math.sqrt(dx*dx + dy*dy + dz*dz)))
    total_dist = sum(dists) or 1.0
    base_frames = [max(1, int(round(total_frames * (d/total_dist)))) for d in dists]
    diff = total_frames - sum(base_frames)
    i = 0
    while diff != 0:
        if diff > 0:
            base_frames[i % len(base_frames)] += 1
            diff -= 1
        else:
            if base_frames[i % len(base_frames)] > 1:
                base_frames[i % len(base_frames)] -= 1
                diff += 1
        i += 1
    cum = []
    acc = 0
    for f in base_frames:
        acc += f
        cum.append(acc)
    return base_frames, cum

def _get_position_for_frame(segments, frames_per_seg, cum_frames, frame):
    prev = 0
    for j, cf in enumerate(cum_frames):
        if frame <= cf:
            s, e = segments[j]['start'], segments[j]['end']
            steps = max(1, frames_per_seg[j])
            local = frame - prev
            f = max(0.0, min(1.0, local / steps))
            x = s[0] + (e[0]-s[0]) * f
            y = s[1] + (e[1]-s[1]) * f
            z = s[2] + (e[2]-s[2]) * f
            return (x, y, z)
        prev = cf
    return tuple(segments[-1]['end'])


# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

def execute_animation(player_parts, start_frame=START_FRAME, end_frame=END_FRAME):
    """
    Slot 1: Animación de caminar de Zombie (índices 0-4)
    5 puntos de trayectoria, Z constante
    """
    start_frame = START_FRAME
    end_frame = END_FRAME

    armature_obj = None
    for name in ['zombie_1_Armature', 'Armature', 'Armature_zombie_1', 'zombie_1_armature']:
        if name in bpy.data.objects:
            armature_obj = bpy.data.objects[name]
            break

    if not armature_obj:
        print("ERROR: No se encontró la armadura principal de Zombie")
        return False

    bone_mapping = {
        'main': 'Hips_zombie_1', 'body': 'Spine_zombie_1', 'head': 'Neck_zombie_1',
        'left_arm': 'LeftUpArm_zombie_1', 'right_arm': 'RightUpArm_zombie_1',
        'left_leg': 'LeftUpLeg_zombie_1', 'right_leg': 'RightUpLeg_zombie_1',
        'left_knee': 'Leftknee_zombie_1', 'right_knee': 'Rightknee_zombie_1',
        'left_elbow': 'Leftelbow_zombie_1', 'right_elbow': 'Rightelbow_zombie_1',
        # FIX (Kebyn, 2026-07-11): 'spine1'/'spine2'/'face' agregados.
        # Sin estos 3, generate_caminar() nunca tocaba Spine1_zombie_1,
        # Spine2_zombie_1 ni face_zombie_1 -- estos SI son parte de BONES_LISTA
        # y SI son escritos por CONCATENAR cuando un segmento tiene poses.
        # Resultado: si un segmento "parada"/con poses dejaba esos 3 huesos
        # en una posicion (ej. gesto de columna/rostro) y el SIGUIENTE
        # segmento era un "caminar" SIN poses propias (se salta en
        # ZOMBIE1SEG_OT_ConcatenateAll), nadie volvia a animar esos 3
        # canales -- Blender sostenia el ultimo valor evaluado hasta el
        # proximo segmento CON poses, dando la sensacion de que la pose de
        # la parada "se extendia" mucho mas alla de su propio frame_end al
        # reproducir todo el recorrido en secuencia (aislado se veia bien,
        # porque generate_parada SI resetea estos 3 huesos a rest).
        'spine1': 'Spine1_zombie_1', 'spine2': 'Spine2_zombie_1', 'face': 'face_zombie_1',
    }

    armature_map = {}
    for part, bone_name in bone_mapping.items():
        if bone_name in armature_obj.pose.bones:
            bone = armature_obj.pose.bones[bone_name]
            bone.rotation_mode = 'XYZ'
            armature_map[part] = bone
        else:
            armature_map[part] = None

    if armature_obj.mode != 'POSE':
        bpy.context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode='POSE')

    for bone in armature_obj.pose.bones:
        bone.rotation_mode = 'XYZ'

    # Root
    zombie_1_root = next((o for o in bpy.data.objects if o.name == 'zombie_1' and o.type == 'EMPTY'), None)
    if not zombie_1_root:
        print("ERROR: No se encontró el Empty 'zombie_1'")
        return False

    # ============================================
    # SETUP DE ACCIONES NLA
    # Crea acciones dedicadas para armature y root
    # para no interferir con los slots anteriores.
    # ============================================
    _arm_action_name  = f'slot_001_zombie_1_caminar_arm'
    _root_action_name = f'slot_001_zombie_1_caminar_root'

    if not armature_obj.animation_data:
        armature_obj.animation_data_create()
    _arm_existing = bpy.data.actions.get(_arm_action_name)
    if _arm_existing:
        bpy.data.actions.remove(_arm_existing)
    _arm_action = bpy.data.actions.new(name=_arm_action_name)
    armature_obj.animation_data.action = _arm_action

    if not zombie_1_root.animation_data:
        zombie_1_root.animation_data_create()
    _root_existing = bpy.data.actions.get(_root_action_name)
    if _root_existing:
        bpy.data.actions.remove(_root_existing)
    _root_action = bpy.data.actions.new(name=_root_action_name)
    zombie_1_root.animation_data.action = _root_action

    # ============================================
    # SETUP SHAPE KEYS DE PARPADEO
    # Crea automáticamente Basis + Closed si no existen
    # ============================================
    def _create_curtain_effect(eye_obj, shape_key):
        mesh = eye_obj.data
        min_z = min(v.co.z for v in mesh.vertices)
        for i, vert in enumerate(mesh.vertices):
            new_co = vert.co.copy()
            new_co.z = min_z
            shape_key.data[i].co = new_co

    def setup_blink_shape_keys():
        for obj_name in ["ojo_izquierdo_zombie_1", "ojo_derecho_zombie_1"]:
            eye_obj = bpy.data.objects.get(obj_name)
            if not eye_obj or eye_obj.type != "MESH":
                print(f"   setup_blink: WARNING '{obj_name}' no encontrado")
                continue
            if not eye_obj.data.shape_keys:
                eye_obj.shape_key_add(name="Basis", from_mix=False)
            existing = [sk.name for sk in eye_obj.data.shape_keys.key_blocks]
            if "Closed" not in existing:
                closed_key = eye_obj.shape_key_add(name="Closed", from_mix=False)
                _create_curtain_effect(eye_obj, closed_key)
                print(f"   setup_blink: 'Closed' creado en '{obj_name}'")
            else:
                print(f"   setup_blink: 'Closed' ya existe en '{obj_name}' -- OK")
    setup_blink_shape_keys()

        # Parpadeos en 25% y 75% del slot
    slot_duration = end_frame - start_frame + 1
    blink_starts = [
        start_frame + int(slot_duration * 0.25),
        start_frame + int(slot_duration * 0.75),
    ]

    # Segmentos de trayectoria
    segments = _load_segments()
    frames_per_seg, cum_global = _compute_frames_allocation(segments, TOTAL_FRAMES)

    # Ciclo de caminata
    base_cycle_duration = 24.0
    complete_cycles = math.floor(slot_duration / base_cycle_duration)
    remaining_frames = slot_duration % base_cycle_duration
    adjusted_cycle = (base_cycle_duration + (remaining_frames / complete_cycles)
                      if complete_cycles > 0 else slot_duration)
    speed = (2 * math.pi) / adjusted_cycle

    config = ANIMATION_CONFIG
    ranges = config['ranges']

    for t in range(start_frame, end_frame + 1):
        path_frame = t - start_frame + 1
        if path_frame > TOTAL_FRAMES:
            pos = tuple(segments[-1]['end'])
        else:
            pos = _get_position_for_frame(segments, frames_per_seg, cum_global, path_frame)

        # Calcular ángulo de orientación para este frame (segmento actual)
        _seg_ang = _get_segment_angle_for_frame(segments, frames_per_seg, cum_global, path_frame)
        _smoothed_ang = _rotation_smoother.smooth_rotation(_seg_ang, t)

        # NUEVO (Kebyn — estilo ZOMBIE_ASIM): VERTICAL_BOB agrega un hundimiento
        # extra del root justo cuando la pierna derecha (debilitada por
        # ASYM_RIGHT_LEG) carga peso, simulando una cojera. walk_cycle se
        # calcula aca (solo depende de t/start_frame/end_frame/config, sin
        # relacion con pos/rotacion) para poder aplicar el bob ANTES de
        # asignar zombie_1_root.location mas abajo; se reutiliza tal cual
        # en el resto del bucle (biomecanica de columna/piernas/cuello).
        walk_cycle = (t - start_frame) / (end_frame - start_frame) * config['walk_cycles']
        if VERTICAL_BOB:
            _right_phase = (walk_cycle + 0.5) % 1.0
            _bob = -abs(math.sin(_right_phase * math.pi)) * VERTICAL_BOB
            pos = (pos[0], pos[1], pos[2] + _bob)

        # FIX PERF (Kebyn — comparado contra chicken_1_animation_studio,
        # que no tiene NINGUNA llamada a frame_set() en todo su
        # generate_slots.py): antes se llamaba bpy.context.scene.frame_set(t)
        # aca, UNA VEZ POR FRAME de cada tramo "caminar" del recorrido.
        # frame_set() no es un simple contador -- fuerza una reevaluacion
        # COMPLETA del depsgraph de la escena entera (todos los objetos,
        # modifiers, drivers, constraints), no solo del armature de Zombie.
        # Nada en este loop depende de que la escena este realmente parada
        # en el frame t: la posicion/rotacion se escriben directo sobre
        # zombie_1_root.location/rotation_euler (asignacion pura, no se lee
        # nada evaluado), y CADA keyframe_insert() de aca abajo ya recibe su
        # propio frame=t explicito -- no necesita que bpy.context.scene.
        # frame_current coincida. _rotation_smoother.smooth_rotation()
        # tambien recibe t como parametro explicito, no lee el frame actual
        # de la escena. Quitar esta linea no cambia ningun keyframe
        # generado (mismos frame=t de siempre), solo elimina una
        # reevaluacion de escena completa y redundante por cada frame.
        zombie_1_root.location = pos
        zombie_1_root.rotation_euler = (math.radians(ROOT_ROTATION_X), math.radians(ROOT_ROTATION_Y), math.radians(_smoothed_ang))
        zombie_1_root.keyframe_insert(data_path="location", frame=t)
        zombie_1_root.keyframe_insert(data_path="rotation_euler", frame=t)

        # Parpadeos
        blink_applied = False
        for blink_start in blink_starts:
            # DESACTIVADO (Kebyn, 2026-09-08: "corrige este personaje no debe
            # parpadear, las mallas de los ojos no deben desaparecer") -- este
            # parpadeo estaba HORNEADO directamente en la Capa 1 (caminar/
            # saltar/parada), fuera de todo el sistema de "Parpadeo automatico"
            # / blink_intervals, por eso no se apagaba desde ningun panel.
            if False:
                blink_applied = True
                offset = t - blink_start + 1
                frame_data = BLINK_SEQUENCE.get(offset, {"closed": 0.0, "hide": False})
                progress = frame_data["closed"]
                hide_eye = frame_data["hide"]
                for eye_name in ["ojo_izquierdo_zombie_1", "ojo_derecho_zombie_1"]:
                    eye = bpy.data.objects.get(eye_name)
                    if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                        ck = eye.data.shape_keys.key_blocks.get("Closed")
                        if ck:
                            ck.value = progress
                            ck.keyframe_insert(data_path='value', frame=t)
                            eye.hide_viewport = hide_eye
                            eye.hide_render = hide_eye
                            eye.keyframe_insert(data_path="hide_viewport", frame=t)
                            eye.keyframe_insert(data_path="hide_render", frame=t)
                break

        if not blink_applied:
            for eye_name in ["ojo_izquierdo_zombie_1", "ojo_derecho_zombie_1"]:
                eye = bpy.data.objects.get(eye_name)
                if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                    ck = eye.data.shape_keys.key_blocks.get("Closed")
                    if ck:
                        ck.value = 0.0
                        ck.keyframe_insert(data_path='value', frame=t)
                        eye.hide_viewport = False
                        eye.hide_render = False
                        eye.keyframe_insert(data_path="hide_viewport", frame=t)
                        eye.keyframe_insert(data_path="hide_render", frame=t)

        # Biomecánica (walk_cycle ya se calculó arriba, antes de fijar la
        # posicion del root, para poder aplicar VERTICAL_BOB)

        # Hips_zombie_1 se comporta como root: forzar (0,0,0) en cada frame
        # para evitar que rotaciones residuales de otros slots afecten la orientacion
        if armature_map.get('main'):
            armature_map['main'].rotation_euler = (0, 0, 0)
            armature_map['main'].keyframe_insert(data_path="rotation_euler", frame=t)

        spine_forward = math.sin(walk_cycle * 2 * math.pi + math.pi/6) * ranges['spine_bend'] + LEAN_FORWARD
        spine_tilt = math.cos(walk_cycle * 2 * math.pi + math.pi/3) * ranges['spine_bend'] * 0.75
        # NUEVO (Kebyn — estilo ESPASMOS): sacudida muscular en rafagas
        # cortas sumada sobre la inclinacion lateral de columna.
        _spasm = _spasm_offset(t, SPASM_AMP)
        spine_tilt += _spasm
        if armature_map.get('body'):
            armature_map['body'].rotation_euler = (spine_forward, 0, spine_tilt)
            armature_map['body'].keyframe_insert(data_path="rotation_euler", frame=t)

        # FIX (Kebyn, 2026-07-11): Spine1_zombie_1/Spine2_zombie_1 acompanan a
        # Spine_zombie_1 con la misma biomecanica de columna (antes no se
        # tocaban en absoluto durante el caminar), y face_zombie_1 se
        # resetea a rest en cada frame -- igual que hace generate_parada.
        # Sin esto, un segmento "parada" con poses en estos 3 huesos podia
        # quedar "congelado" en cualquier tramo de caminar sin poses
        # propias, ya que nadie mas los volvia a animar hasta el siguiente
        # segmento con poses.
        if armature_map.get('spine1'):
            armature_map['spine1'].rotation_euler = (spine_forward, 0, spine_tilt)
            armature_map['spine1'].keyframe_insert(data_path="rotation_euler", frame=t)
        if armature_map.get('spine2'):
            armature_map['spine2'].rotation_euler = (spine_forward, 0, spine_tilt)
            armature_map['spine2'].keyframe_insert(data_path="rotation_euler", frame=t)
        if armature_map.get('face'):
            armature_map['face'].rotation_euler = (0, 0, 0)
            armature_map['face'].keyframe_insert(data_path="rotation_euler", frame=t)

        stabilization = ranges['head_stabilization']
        neck_forward = -spine_forward * stabilization
        neck_tilt = math.sin(walk_cycle * 2 * math.pi) * ranges['neck_tilt']
        neck_side = math.cos(walk_cycle * 2 * math.pi + math.pi/4) * ranges['neck_tilt'] * 0.5
        # NUEVO (Kebyn — estilo ESPASMOS, "mirando al frente"): HEAD_LOCKED
        # mezcla la rotacion de cabeza hacia (0,0,0) para que se mantenga
        # fija mirando al frente sin importar el balanceo del cuerpo. En
        # 0.0 (resto de estilos) esto no cambia nada.
        neck_forward = neck_forward * (1.0 - HEAD_LOCKED)
        neck_side = neck_side * (1.0 - HEAD_LOCKED)
        neck_tilt = neck_tilt * (1.0 - HEAD_LOCKED)
        if armature_map.get('head'):
            armature_map['head'].rotation_euler = (neck_forward, neck_side, neck_tilt)
            armature_map['head'].keyframe_insert(data_path="rotation_euler", frame=t)

        left_leg_swing = calculate_leg_swing(walk_cycle, config)
        if armature_map.get('left_leg'):
            armature_map['left_leg'].rotation_euler = (left_leg_swing, 0, 0)
            armature_map['left_leg'].keyframe_insert(data_path="rotation_euler", frame=t)

        # NUEVO (Kebyn — estilo ESPASMOS, "rodilla dañada"): la rodilla
        # izquierda flexiona normalmente; solo la derecha queda limitada
        # por KNEE_DAMAGE_RIGHT. En 0.0 (resto de estilos) el knee_flex
        # queda en su rango completo, igual que antes de agregar esto.
        left_knee_flex = calculate_knee_flex(walk_cycle, config, damage=0.0)
        if armature_map.get('left_knee'):
            # FIX (Kebyn, articulacion de rodilla invertida): calculate_knee_flex
            # siempre devuelve un valor positivo (0..max), pero el eje X local de
            # Leftknee_zombie_1 dobla la rodilla hacia adelante/afuera con signo
            # positivo -- lo correcto anatomicamente es que la pantorrilla vaya
            # hacia atras al levantar la pierna. Se invierte el signo al aplicarlo.
            armature_map['left_knee'].rotation_euler = (-left_knee_flex, 0, 0)
            armature_map['left_knee'].keyframe_insert(data_path="rotation_euler", frame=t)

        # NUEVO (Kebyn — estilo ZOMBIE_ASIM): ASYM_RIGHT_LEG retrasa la fase
        # de la pierna derecha (arrastre) y reduce su amplitud de swing
        # (debilidad), simulando una cojera. En 0.0 (NORMAL/LENTO) esto
        # no cambia nada: fase +0.5 exacta, amplitud completa, igual que
        # antes.
        right_leg_cycle = (walk_cycle + 0.5 + ASYM_RIGHT_LEG * 0.12) % 1.0
        right_leg_swing = calculate_leg_swing(right_leg_cycle, config) * (1.0 - ASYM_RIGHT_LEG * 0.55)
        if armature_map.get('right_leg'):
            armature_map['right_leg'].rotation_euler = (right_leg_swing, 0, 0)
            armature_map['right_leg'].keyframe_insert(data_path="rotation_euler", frame=t)

        right_knee_flex = calculate_knee_flex(right_leg_cycle, config, damage=KNEE_DAMAGE_RIGHT)
        if armature_map.get('right_knee'):
            # FIX (Kebyn, articulacion de rodilla invertida): mismo signo invertido
            # que left_knee, ver comentario arriba.
            armature_map['right_knee'].rotation_euler = (-right_knee_flex, 0, 0)
            armature_map['right_knee'].keyframe_insert(data_path="rotation_euler", frame=t)

        # Brazos "estilo Minecraft": siempre perpendiculares al cuerpo (rectos al
        # costado), sin balanceo ni flexion de codo. Se fija la rotacion en cada
        # frame para que ningun otro sistema (organic filters, oscilaciones) la
        # desvie del angulo recto.
        # FIX (Kebyn, 2026-08-28): el angulo base del brazo (arm_base_x, 90°)
        # va en el eje Z (-90° derecho, +90° izquierdo) segun la orientacion
        # real del bone en el rig de zombie_1. X e Y quedan en 0: se quita el
        # offset de 0.55 rad que quedaba en Y, ya que la unica rotacion debe
        # ser en Z.
        # NUEVO (Kebyn — estilo ESPASMOS): en rafaga, X/Y del brazo se
        # sacuden brevemente (SPASM_AMP); el resto del tiempo quedan en 0
        # como siempre, y Z (arm_base_x) nunca se toca -- la pose base
        # "Minecraft" sigue intacta entre rafagas.
        # NUEVO (Kebyn — estilo RAPIDO_B, "corriendo y arañando"): en vez de
        # la pose fija "Minecraft" (perpendicular al costado, sin balanceo
        # ni flexion de codo, ver bloque else de abajo), los brazos se
        # extienden al frente y se balancean -- reusa
        # calculate_arm_swing()/calculate_elbow_flex() que ya existian pero
        # no se llamaban desde ningun lado todavia. Se activa solo con
        # CLAW_ARMS=1.0 (estilo RAPIDO_B); en 0.0 (resto de los estilos)
        # cae en el else y nada cambia respecto a antes.
        #
        # FIX (Kebyn): la fase de brazo ahora SIEMPRE se envuelve con % 1.0
        # antes de pasarla a calculate_arm_swing()/calculate_elbow_flex()
        # (igual que right_leg_cycle mas arriba) -- sin esto, en slots de
        # mas de un ciclo de zancada (walk_cycle > 1.0) el "if phase < 0.5"
        # interno de esas funciones dejaba de alternar y los brazos se
        # quedaban pegados en la mitad final del rango a partir del 2do
        # ciclo.
        #
        # CLAW_ARM_SPEED < 1.0 hace que los brazos completen MENOS
        # oscilaciones que las piernas en el mismo tramo (cadencia mas
        # lenta y pesada, como un zarpazo que se toma su tiempo en vez de
        # vibrar al ritmo de la zancada).
        #
        # CLAW_ARM_ASYM rompe la simetria espejo (que antes era exacta,
        # +0.5 de fase e igual amplitud en ambos brazos): el brazo derecho
        # queda "dominante" (fase adelantada respecto al espejo perfecto +
        # mas amplitud de swing/flexion de codo) y el izquierdo se atrasa y
        # se queda mas corto -- mismo patron ya usado en ASYM_RIGHT_LEG
        # (fase + reduccion de amplitud combinadas en un solo 0.0-1.0).
        if CLAW_ARMS > 0.0:
            _left_arm_phase  = (walk_cycle * CLAW_ARM_SPEED) % 1.0
            _right_arm_phase = (walk_cycle * CLAW_ARM_SPEED + 0.5 - CLAW_ARM_ASYM * 0.18) % 1.0
            _left_arm_reach   = calculate_arm_swing(_left_arm_phase, config) * (1.0 - CLAW_ARM_ASYM * 0.35)
            _right_arm_reach  = calculate_arm_swing(_right_arm_phase, config) * (1.0 + CLAW_ARM_ASYM * 0.25)
            _left_elbow_claw  = calculate_elbow_flex(_left_arm_phase, config) * (1.0 - CLAW_ARM_ASYM * 0.35)
            _right_elbow_claw = calculate_elbow_flex(_right_arm_phase, config) * (1.0 + CLAW_ARM_ASYM * 0.25)
            # Los brazos bajan de la pose perpendicular (90°, arm_base_x) a
            # una pose extendida al frente (~40% de ese angulo) para que el
            # zarpazo se vea hacia adelante y no hacia el costado.
            _claw_base_z = ranges['arm_base_x'] * 0.4

            if armature_map.get('right_arm'):
                armature_map['right_arm'].rotation_euler = (_right_arm_reach, 0, -_claw_base_z)
                armature_map['right_arm'].keyframe_insert(data_path="rotation_euler", frame=t)

            if armature_map.get('right_elbow'):
                # NOTA (Kebyn): signo de flexion elegido por convencion, ya
                # que este hueso nunca se habia animado antes (siempre
                # (0,0,0)). Si en Blender el codo flexiona hacia atras en
                # vez de hacia adelante (como el zarpazo pide), invertir el
                # signo aqui -- mismo caso que el FIX de rodilla invertida
                # mas arriba.
                armature_map['right_elbow'].rotation_euler = (-_right_elbow_claw, 0, 0)
                armature_map['right_elbow'].keyframe_insert(data_path="rotation_euler", frame=t)

            if armature_map.get('left_arm'):
                armature_map['left_arm'].rotation_euler = (_left_arm_reach, 0, _claw_base_z)
                armature_map['left_arm'].keyframe_insert(data_path="rotation_euler", frame=t)

            if armature_map.get('left_elbow'):
                armature_map['left_elbow'].rotation_euler = (-_left_elbow_claw, 0, 0)
                armature_map['left_elbow'].keyframe_insert(data_path="rotation_euler", frame=t)
        else:
            if armature_map.get('right_arm'):
                _down_z = -ranges['arm_base_x'] * (1.0 - ARM_DOWN_RIGHT)
                armature_map['right_arm'].rotation_euler = (_spasm, -_spasm * 0.6, _down_z)
                armature_map['right_arm'].keyframe_insert(data_path="rotation_euler", frame=t)

            if armature_map.get('right_elbow'):
                armature_map['right_elbow'].rotation_euler = (0, 0, 0)
                armature_map['right_elbow'].keyframe_insert(data_path="rotation_euler", frame=t)

            if armature_map.get('left_arm'):
                armature_map['left_arm'].rotation_euler = (-_spasm, _spasm * 0.6, ranges['arm_base_x'])
                armature_map['left_arm'].keyframe_insert(data_path="rotation_euler", frame=t)

            if armature_map.get('left_elbow'):
                armature_map['left_elbow'].rotation_euler = (0, 0, 0)
                armature_map['left_elbow'].keyframe_insert(data_path="rotation_euler", frame=t)

    print(f"Animación Slot 1 completada: {start_frame}-{end_frame}")

    # ============================================
    # EMPUJAR ACCIONES AL NLA
    # ============================================

    if armature_obj.animation_data and armature_obj.animation_data.action:
        _arm_done  = armature_obj.animation_data.action
        armature_obj.animation_data.action = None
        _arm_track = armature_obj.animation_data.nla_tracks.new()
        _arm_track.name = f'Slot_001_arm'
        _arm_strip = _arm_track.strips.new(_arm_done.name, start_frame, _arm_done)
        _arm_strip.frame_end      = end_frame
        _arm_strip.extrapolation  = 'NOTHING'
        _arm_strip.use_auto_blend = False
        _arm_strip.blend_in       = 0
        _arm_strip.blend_out      = 0

    if zombie_1_root.animation_data and zombie_1_root.animation_data.action:
        _root_done  = zombie_1_root.animation_data.action
        zombie_1_root.animation_data.action = None
        _root_track = zombie_1_root.animation_data.nla_tracks.new()
        _root_track.name = f'Slot_001_root'
        _root_strip = _root_track.strips.new(_root_done.name, start_frame, _root_done)
        _root_strip.frame_end      = end_frame
        _root_strip.extrapolation  = 'HOLD_FORWARD'
        _root_strip.use_auto_blend = False
        _root_strip.blend_in       = 0
        _root_strip.blend_out      = 0

    return True


if __name__ == "__main__":
    execute_animation({}, start_frame=START_FRAME, end_frame=END_FRAME)
