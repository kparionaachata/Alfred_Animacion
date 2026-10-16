# -*- coding: utf-8 -*-
"""
slot_001_caminar.py
Jerry (perro) - Slot 1
GENERADO AUTOMATICAMENTE - 2026-10-09
Tipo: caminar  |  Frames: 1-32  (32 frames)
Trayectoria: punto 1 -> punto 2  (2 puntos)
"""

import bpy
import math

SLOT_INDEX   = 1
START_FRAME  = 1
END_FRAME    = 32
TOTAL_FRAMES = 32

ROOT_ROTATION_X = 0.0
ROOT_ROTATION_Y = 0.0
ROOT_ROTATION_Z = 0.0

EMBEDDED_TRAJECTORY_POINTS = [
    {"index": 1, "coordinates": {"x": 0, "y": 0, "z": 0}, "texture": "grass_block_top"},
    {"index": 2, "coordinates": {"x": 0, "y": 1, "z": 0}, "texture": "grass_block_top"},
]

ANIMATION_INFO = {
    'name': 'slot_001_jerry_caminar',
    'frame_count': 32,
    'fps': 24,
    'duration_seconds': 1.333,
    'entity': 'Jerry',
    'slot': 1,
    'movement_type': 'caminar',
    'walk_style': 'NORMAL',
}

# ============================================================
# ESTILO DE CAMINATA (multiplexor) — Kebyn, 2026-08-05
# ============================================================
WALK_STYLE      = "NORMAL"                # NORMAL/LENTO/HERIDO/RAPIDO/CORRER/CORRER_2
CYCLE_LENGTH    = 25                  # frames por ciclo de zancada (base 25)
RANGE_MULT      = {'leg': 1.0000, 'spine': 1.0000, 'tail': 1.0000, 'head': 1.0000, 'ear': 1.0000}
VERTICAL_BOB    = 0.0                # metros, rebote vertical extra del root
ASYM_REAR_LEG   = 0.0              # 0.0-1.0, debilita pata trasera derecha (cojera, solo HERIDO)

def sin_wave(frame, period, amplitude, phase=0, offset=0):
    return amplitude * math.sin(2 * math.pi * frame / period + phase) + offset

def cos_wave(frame, period, amplitude, phase=0, offset=0):
    return amplitude * math.cos(2 * math.pi * frame / period + phase) + offset

def lerp(start, end, t):
    return start + (end - start) * t

def ease_in_out(t):
    return t * t * (3 - 2 * t)

def ease_out(t):
    return 1 - (1 - t) * (1 - t)

def ease_in(t):
    return t * t


def _compute_direction_angle(p0, p1):
    dx = p1['x'] - p0['x']
    dy = p1['y'] - p0['y']
    if dx == 0 and dy == 0:
        return None
    ang_raw = math.degrees(math.atan2(dx, dy))
    ang_rounded = round(ang_raw / 90.0) * 90.0
    ang = ang_rounded if abs(ang_raw - ang_rounded) < 45 else -ang_raw
    while ang >  180: ang -= 360
    while ang < -180: ang += 360
    if   ang ==  90: ang = -90
    elif ang == -90: ang =  90
    elif ang == 180: ang = -180
    return ang

def _smoothstep_val(x):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    return x * x * (3.0 - 2.0 * x)

def _angle_diff_shortest(target, current):
    d = target - current
    while d >  180: d -= 360
    while d < -180: d += 360
    return d


# ============================================================
# SISTEMA DE PARPADEO
# ============================================================

BLINK_SEQUENCE = {
    1: {"closed": 0.0,  "hide": False},
    2: {"closed": 0.25, "hide": False},
    3: {"closed": 0.5,  "hide": False},
    4: {"closed": 0.75, "hide": False},
    5: {"closed": 1.0,  "hide": True},
    6: {"closed": 1.0,  "hide": True},
    7: {"closed": 0.75, "hide": False},
    8: {"closed": 0.5,  "hide": False},
    9: {"closed": 0.25, "hide": False},
}

EYE_NAMES = ["ojo_izquierdo_jerry", "ojo_derecho_jerry"]


def _create_curtain_effect(eye_obj, shape_key):
    """Deforma la shape key bajando todos los vertices al minimo Z (efecto parpado)."""
    mesh    = eye_obj.data
    min_z   = min(v.co.z for v in mesh.vertices)
    for i, vert in enumerate(mesh.vertices):
        new_co     = vert.co.copy()
        new_co.z   = min_z
        shape_key.data[i].co = new_co


def setup_blink_shape_keys():
    """Crea Basis + Closed en los ojos si no existen. Seguro llamar multiples veces."""
    import bpy
    for obj_name in EYE_NAMES:
        eye_obj = bpy.data.objects.get(obj_name)
        if not eye_obj or eye_obj.type != "MESH":
            print(f"   setup_blink: WARNING '{obj_name}' no encontrado o no es MESH")
            continue
        if not eye_obj.data.shape_keys:
            eye_obj.shape_key_add(name="Basis", from_mix=False)
            print(f"   setup_blink: Basis creado en '{obj_name}'")
        existing = [sk.name for sk in eye_obj.data.shape_keys.key_blocks]
        if "Closed" not in existing:
            closed_key = eye_obj.shape_key_add(name="Closed", from_mix=False)
            _create_curtain_effect(eye_obj, closed_key)
            print(f"   setup_blink: Shape key 'Closed' creada en '{obj_name}'")
        else:
            print(f"   setup_blink: 'Closed' ya existe en '{obj_name}' -- OK")


# ============================================================
# SISTEMA DE SUAVIZADO DE ROTACION
# ============================================================

class RotationSmoother:
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
        if abs(angle_diff) < 2:
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
    dx = p1[0]-p0[0]; dy = p1[1]-p0[1]
    if dx == 0 and dy == 0: return None
    ang_raw = math.degrees(math.atan2(dx, dy))
    ang_rounded = round(ang_raw/90.0)*90.0
    ang = ang_rounded if abs(ang_raw-ang_rounded) < 45 else -ang_raw
    while ang >  180: ang -= 360
    while ang < -180: ang += 360
    if   ang ==  90: ang = -90
    elif ang == -90: ang =  90
    if ang == 180: ang = -180
    return ang

def _get_segment_angle_for_frame(segments, frames_per_seg, cum_frames, frame):
    prev = 0
    for j, cf in enumerate(cum_frames):
        if frame <= cf:
            ang = _compute_direction_angle_local(segments[j]['start'], segments[j]['end'])
            return ang if ang is not None else ROOT_ROTATION_Z
        prev = cf
    ang = _compute_direction_angle_local(segments[-1]['start'], segments[-1]['end'])
    return ang if ang is not None else ROOT_ROTATION_Z

_rotation_smoother = RotationSmoother(smoothing_frames=12)

# ============================================================
# CICLO DE CAMINATA CUADRUPEDO (SniffingSearchCycle)
# ============================================================

class SniffingSearchCycle:
    # NUEVO (portado de Alfred, Kebyn 2026-08-05): range_mult/asym_rear
    # aplican el estilo de caminata elegido (RANGE_MULT/ASYM_REAR_LEG
    # arriba) sobre la MISMA formula base -- no se duplica el ciclo por
    # estilo, solo se escala su amplitud.
    def __init__(self, cycle_length=25, total_frames=100, range_mult=None, asym_rear=0.0):
        self.cycle_length  = cycle_length
        self.total_frames  = total_frames
        self.rm   = range_mult or {'leg': 1.0, 'spine': 1.0, 'tail': 1.0, 'head': 1.0, 'ear': 1.0}
        self.asym = asym_rear  # 0.0-1.0, debilita la pata trasera derecha (cojera)

    def normalize_frame(self, frame):
        return ((frame - 1) % self.cycle_length) + 1

    def sniff_down(self, frame):
        n = self.normalize_frame(frame)
        return (sin_wave(n, self.cycle_length, 0.03 * self.rm['head'], 0, 0), 0, 0)

    def look_around(self, frame):
        n = self.normalize_frame(frame)
        return (0, sin_wave(n, self.cycle_length, 0.05 * self.rm['head'], 0, 0), 0)

    def head_tilt(self, frame):
        n = self.normalize_frame(frame)
        return (0, 0, sin_wave(n, self.cycle_length, 0.016 * self.rm['head'], 0, 0))

    def ear_twitch(self, frame):
        n = self.normalize_frame(frame)
        return (0, sin_wave(n, self.cycle_length, 0.2 * self.rm['ear'], 0, 0), sin_wave(n, self.cycle_length, 0.1 * self.rm['ear'], 0, 0))

    def tail_wag_alert(self, frame):
        n = self.normalize_frame(frame)
        t = self.rm['tail']
        return (sin_wave(n, self.cycle_length, 0.4*t, 0, 0.2*t), sin_wave(n, self.cycle_length, 0.06*t, 0, 0), sin_wave(n, self.cycle_length, 0.16*t, 0, 0))

    def leg_slow_walk(self, frame, is_rear=False, is_left=True):
        n = self.normalize_frame(frame)
        phase = 0 if is_left else math.pi
        amp   = (0.4 if is_rear else 0.3) * self.rm['leg']
        # ASYM_REAR_LEG (solo HERIDO): la pata trasera DERECHA (is_rear
        # and not is_left) se debilita para simular cojera.
        if is_rear and not is_left:
            amp *= (1.0 - self.asym)
        return (-sin_wave(n, self.cycle_length, amp, phase, 0),
                -sin_wave(n, self.cycle_length, amp*0.15, phase, 0),
                -sin_wave(n, self.cycle_length, amp*0.03, phase, 0))

    def leg_bend(self, frame, is_rear=False, is_left=True):
        n = self.normalize_frame(frame)
        phase = 0 if is_left else math.pi
        bb    = (0.3 if is_rear else 0.24) * self.rm['leg']
        if is_rear and not is_left:
            bb *= (1.0 - self.asym)
        return (-abs(sin_wave(n, self.cycle_length, bb, phase, bb)),
                -sin_wave(n, self.cycle_length, 0.1, phase, 0),
                -sin_wave(n, self.cycle_length, 0.04, phase, 0))

    def foot_strike(self, frame, is_rear=False, is_left=True):
        n = self.normalize_frame(frame)
        phase = 0 if is_left else math.pi
        amp_x = (0.8 if is_rear else 0.6) * self.rm['leg']
        if is_rear and not is_left:
            amp_x *= (1.0 - self.asym)
        x = -sin_wave(n, self.cycle_length, amp_x, phase, 0.4 if is_rear else -0.1)
        y = abs(sin_wave(n, self.cycle_length, 0.04, phase, 0.02)) * (1.0 if is_rear else 0.5)
        z = -sin_wave(n, self.cycle_length, 0.04 if is_rear else 0.06, phase, 0.02)
        return (x, y, z)

    def toe_curl(self, frame, is_rear=False, is_left=True):
        n = self.normalize_frame(frame)
        phase = 0 if is_left else math.pi
        amp = 0.5 * self.rm['leg']
        if is_rear and not is_left:
            amp *= (1.0 - self.asym)
        return (abs(sin_wave(n, self.cycle_length, amp, phase, 0.4)),
                -sin_wave(n, self.cycle_length, 0.16, phase, 0),
                -sin_wave(n, self.cycle_length, 0.08, phase, 0.04))

    def spine_undulation(self, frame, segment, total_segments=7):
        n = self.normalize_frame(frame)
        ph = (segment / total_segments) * math.pi
        return (-sin_wave(n, self.cycle_length, 0.03 * self.rm['spine'], ph, -0.08 * self.rm['spine']), 0, 0)

    def vertical_bob(self, frame):
        # NUEVO: rebote vertical extra del root en cada apoyo de pata
        # trasera -- solo se nota en estilos con VERTICAL_BOB > 0
        # (HERIDO/RAPIDO/CORRER). En HERIDO se acentua en el apoyo de la
        # pata trasera sana para compensar la cojera.
        n = self.normalize_frame(frame)
        bob = VERTICAL_BOB * (0.5 - 0.5 * math.cos(2 * math.pi * n / self.cycle_length * 2))
        if self.asym > 0.0:
            bob += max(0.0, math.sin(2 * math.pi * n / self.cycle_length)) * VERTICAL_BOB * self.asym
        return bob


def generate_keyframes(total_frames=140):
    cl    = min(CYCLE_LENGTH, max(4, total_frames))
    cycle = SniffingSearchCycle(cycle_length=cl, total_frames=total_frames,
                                 range_mult=RANGE_MULT, asym_rear=ASYM_REAR_LEG)
    kf    = {}
    for frame in range(1, total_frames + 1):
        kf.setdefault('shoulder.L', {})[frame] = cycle.leg_slow_walk(frame, True, True)
        kf.setdefault('shoulder.R', {})[frame] = cycle.leg_slow_walk(frame, True, False)
        kf.setdefault('thigh.L', {})[frame]    = tuple(x*0.01  for x in cycle.leg_slow_walk(frame, True, True))
        kf.setdefault('thigh.R', {})[frame]    = tuple(x*-0.3  for x in cycle.leg_slow_walk(frame, True, False))
        kf.setdefault('shin.L', {})[frame]     = cycle.leg_bend(frame, True, True)
        kf.setdefault('shin.R', {})[frame]     = cycle.leg_bend(frame, True, False)
        kf.setdefault('foot.L', {})[frame]     = cycle.foot_strike(frame, True, True)
        kf.setdefault('foot.R', {})[frame]     = cycle.foot_strike(frame, True, False)
        kf.setdefault('toe.L', {})[frame]      = cycle.toe_curl(frame, True, True)
        kf.setdefault('toe.R', {})[frame]      = cycle.toe_curl(frame, True, False)
        kf.setdefault('front_shoulder.L', {})[frame] = cycle.leg_slow_walk(frame+12, False, True)
        kf.setdefault('front_shoulder.R', {})[frame] = cycle.leg_slow_walk(frame+12, False, False)
        kf.setdefault('front_thigh.L', {})[frame]    = tuple(x*0.6 for x in cycle.leg_slow_walk(frame+12, False, True))
        kf.setdefault('front_thigh.R', {})[frame]    = tuple(x*0.4 for x in cycle.leg_slow_walk(frame+12, False, False))
        kf.setdefault('front_shin.L', {})[frame]     = cycle.leg_bend(frame+12, False, True)
        kf.setdefault('front_shin.R', {})[frame]     = cycle.leg_bend(frame+12, False, False)
        kf.setdefault('front_foot.L', {})[frame]     = cycle.foot_strike(frame+12, False, True)
        kf.setdefault('front_foot.R', {})[frame]     = cycle.foot_strike(frame+12, False, False)
        kf.setdefault('front_toe.L', {})[frame]      = cycle.toe_curl(frame+12, False, True)
        kf.setdefault('front_toe.R', {})[frame]      = cycle.toe_curl(frame+12, False, False)
        for i in range(1, 8):
            kf.setdefault(f'spine_{i}', {})[frame] = cycle.spine_undulation(frame, i, 7)
        for i in range(1, 4):
            kf.setdefault(f'tail_{i}', {})[frame] = cycle.tail_wag_alert(frame)
        sniff = cycle.sniff_down(frame); look = cycle.look_around(frame); tilt = cycle.head_tilt(frame)
        kf.setdefault('scull', {})[frame]   = (sniff[0]+tilt[0]*0.3, look[1], tilt[2])
        kf.setdefault('jaw_top', {})[frame] = (0.224, 0, 0)
        kf.setdefault('ear.L', {})[frame]   = cycle.ear_twitch(frame)
        kf.setdefault('ear.R', {})[frame]   = cycle.ear_twitch(frame+6)
        kf.setdefault('sombrero', {})[frame]= (0, 0, 0)
    return kf


def _load_segments():
    pts  = EMBEDDED_TRAJECTORY_POINTS
    segs = []
    for i in range(len(pts)-1):
        s = pts[i]['coordinates']; e = pts[i+1]['coordinates']
        segs.append({'start':[s['x'],s['y'],s['z']], 'end':[e['x'],e['y'],e['z']], 'texture': pts[i].get('texture','grass_block_top')})
    return segs

def _compute_frames_allocation(segments, total_frames):
    dists = []
    for seg in segments:
        s,e = seg['start'],seg['end']
        dx,dy,dz = e[0]-s[0],e[1]-s[1],e[2]-s[2]
        dists.append(max(0.0001, math.sqrt(dx*dx+dy*dy+dz*dz)))
    total_dist = sum(dists) or 1.0
    bf = [max(1,int(round(total_frames*(d/total_dist)))) for d in dists]
    diff = total_frames - sum(bf); i = 0
    while diff != 0:
        if diff > 0: bf[i%len(bf)] += 1; diff -= 1
        else:
            if bf[i%len(bf)] > 1: bf[i%len(bf)] -= 1; diff += 1
        i += 1
    cum = []; acc = 0
    for f in bf: acc += f; cum.append(acc)
    return bf, cum

def _get_position_for_frame(segments, frames_per_seg, cum_frames, frame):
    prev = 0
    for j, cf in enumerate(cum_frames):
        if frame <= cf:
            s,e = segments[j]['start'],segments[j]['end']
            steps = max(1, frames_per_seg[j]); local = frame - prev
            f = max(0.0, min(1.0, local/steps))
            return (s[0]+(e[0]-s[0])*f, s[1]+(e[1]-s[1])*f, s[2]+(e[2]-s[2])*f)
        prev = cf
    return tuple(segments[-1]['end'])


def execute_animation(player_parts, start_frame=START_FRAME, end_frame=END_FRAME):
    start_frame = START_FRAME; end_frame = END_FRAME

    root = next((o for o in bpy.data.objects if o.name.lower() == 'jerry'), None)
    if not root:
        root = next((o for o in bpy.data.objects if 'jerry' in o.name.lower() and o.type in ('EMPTY','ARMATURE')), None)
    if not root:
        print("ERROR: No se encontro el empty 'jerry'"); return False

    armature = next((o for o in bpy.data.objects if o.type == 'ARMATURE' and o.parent == root), None)
    if not armature:
        armature = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
    if not armature:
        print("ERROR: No se encontro el Armature"); return False

    # ============================================
    # SETUP DE ACCIONES NLA
    # ============================================
    _arm_action_name  = f'slot_{1:03d}_jerry_caminar_arm'
    _root_action_name = f'slot_{1:03d}_jerry_caminar_root'

    if not armature.animation_data:
        armature.animation_data_create()
    _arm_existing = bpy.data.actions.get(_arm_action_name)
    if _arm_existing:
        bpy.data.actions.remove(_arm_existing)
    _arm_action = bpy.data.actions.new(name=_arm_action_name)
    armature.animation_data.action = _arm_action

    if not root.animation_data:
        root.animation_data_create()
    _root_existing = bpy.data.actions.get(_root_action_name)
    if _root_existing:
        bpy.data.actions.remove(_root_existing)
    _root_action = bpy.data.actions.new(name=_root_action_name)
    root.animation_data.action = _root_action

    bpy.context.view_layer.objects.active = armature
    if armature.mode != 'POSE': bpy.ops.object.mode_set(mode='POSE')
    for bone in armature.pose.bones: bone.rotation_mode = 'XYZ'

    kf_data = generate_keyframes(TOTAL_FRAMES)
    bones_applied = 0
    for bone_name, fd in kf_data.items():
        bone = armature.pose.bones.get(bone_name)
        if not bone: continue
        bone.rotation_mode = 'XYZ'
        for frame, rot in fd.items():
            adj = START_FRAME + (frame - 1)
            bone.rotation_euler = rot
            bone.keyframe_insert(data_path="rotation_euler", frame=adj)
        bones_applied += 1

    segments = _load_segments()
    frames_per_seg, cum_global = _compute_frames_allocation(segments, TOTAL_FRAMES)

    # Parpadeos al 25% y 75% del slot
    slot_duration = end_frame - start_frame + 1
    blink_starts  = [start_frame + int(slot_duration * 0.25), start_frame + int(slot_duration * 0.75)]

    setup_blink_shape_keys()

    # Ciclo auxiliar SOLO para el rebote vertical del root (VERTICAL_BOB)
    # -- reusa el mismo cycle_length/asimetria que ya animo los bones,
    # asi que el rebote queda sincronizado con el apoyo de las patas.
    _bob_cycle = SniffingSearchCycle(cycle_length=min(CYCLE_LENGTH, max(4, TOTAL_FRAMES)),
                                      total_frames=TOTAL_FRAMES, asym_rear=ASYM_REAR_LEG)

    for t in range(start_frame, end_frame + 1):
        path_frame  = t - start_frame + 1
        pos         = _get_position_for_frame(segments, frames_per_seg, cum_global, min(path_frame, TOTAL_FRAMES))
        seg_ang     = _get_segment_angle_for_frame(segments, frames_per_seg, cum_global, path_frame)
        smoothed_ang= _rotation_smoother.smooth_rotation(seg_ang, t)

        bpy.context.scene.frame_set(t)
        if VERTICAL_BOB > 0.0:
            _bob = _bob_cycle.vertical_bob(min(path_frame, TOTAL_FRAMES))
            pos = (pos[0], pos[1], pos[2] + _bob)
        root.location       = pos
        root.rotation_euler = (math.radians(ROOT_ROTATION_X), math.radians(ROOT_ROTATION_Y), math.radians(smoothed_ang))
        root.keyframe_insert(data_path="location",       frame=t)
        root.keyframe_insert(data_path="rotation_euler", frame=t)

        blink_applied = False
        for blink_start in blink_starts:
            if blink_start <= t < blink_start + 9:
                blink_applied = True
                offset     = t - blink_start + 1
                frame_data = BLINK_SEQUENCE.get(offset, {"closed": 0.0, "hide": False})
                progress   = frame_data["closed"]
                hide_eye   = frame_data["hide"]
                for eye_name in EYE_NAMES:
                    eye = bpy.data.objects.get(eye_name)
                    if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                        ck = eye.data.shape_keys.key_blocks.get("Closed")
                        if ck:
                            ck.value = progress
                            ck.keyframe_insert(data_path='value', frame=t)
                            eye.hide_viewport = hide_eye
                            eye.hide_render   = hide_eye
                            eye.keyframe_insert(data_path="hide_viewport", frame=t)
                            eye.keyframe_insert(data_path="hide_render",   frame=t)
                break
        if not blink_applied:
            for eye_name in EYE_NAMES:
                eye = bpy.data.objects.get(eye_name)
                if eye and hasattr(eye.data, 'shape_keys') and eye.data.shape_keys:
                    ck = eye.data.shape_keys.key_blocks.get("Closed")
                    if ck:
                        ck.value = 0.0
                        ck.keyframe_insert(data_path='value', frame=t)
                        eye.hide_viewport = False
                        eye.hide_render   = False
                        eye.keyframe_insert(data_path="hide_viewport", frame=t)
                        eye.keyframe_insert(data_path="hide_render",   frame=t)

    print(f"Slot {SLOT_INDEX} caminar completado: {bones_applied} bones, {TOTAL_FRAMES} frames")

    # ============================================
    # EMPUJAR ACCIONES AL NLA
    # ============================================
    if armature.animation_data and armature.animation_data.action:
        _arm_done  = armature.animation_data.action
        armature.animation_data.action = None
        _arm_track = armature.animation_data.nla_tracks.new()
        _arm_track.name = f'Slot_{1:03d}_arm'
        _arm_strip = _arm_track.strips.new(_arm_done.name, start_frame, _arm_done)
        _arm_strip.frame_end      = end_frame
        _arm_strip.extrapolation  = 'NOTHING'
        _arm_strip.use_auto_blend = False
        _arm_strip.blend_in       = 0
        _arm_strip.blend_out      = 0

    if root.animation_data and root.animation_data.action:
        _root_done  = root.animation_data.action
        root.animation_data.action = None
        _root_track = root.animation_data.nla_tracks.new()
        _root_track.name = f'Slot_{1:03d}_root'
        _root_strip = _root_track.strips.new(_root_done.name, start_frame, _root_done)
        _root_strip.frame_end      = end_frame
        _root_strip.extrapolation  = 'HOLD_FORWARD'
        _root_strip.use_auto_blend = False
        _root_strip.blend_in       = 0
        _root_strip.blend_out      = 0

    return True


if __name__ == "__main__":
    execute_animation({}, START_FRAME, END_FRAME)
