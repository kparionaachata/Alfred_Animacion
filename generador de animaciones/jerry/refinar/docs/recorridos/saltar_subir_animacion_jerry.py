import bpy
SLOT = 3
START_FRAME = 1
END_FRAME = 15
P0 = (0, 0, 0)
P1 = (1, 0, 1)
TIMING = (2, 9, 3)
KIND = 'subir'
ROT = (0.0, 0.0, -90.0)
POSE_DATA = None
ROOT_NAME = 'jerry'
ARM_NAME = 'Dog_001_rig'
ANIMATION_INFO = {'name': 'slot_003_jerry_saltar_subir', 'frame_count': 15, 'fps': 24.0, 'duration_seconds': 0.625, 'entity': 'jerry', 'slot': 3, 'movement_type': 'saltar_subir', 'animation_type': 'procedural'}
import math
JUMP_FLIGHT_FACTOR = 0.25

def jump_timing(p0, p1, kind, fps=24.0):
    """Tiempo artistico calibrado al salto original de una unidad a 24 fps.

    Solo se alarga el vuelo: sqrt(desnivel) conserva la escala temporal
    de una parabola; distancia horizontal limita la velocidad de avance.
    Las coordenadas usan unidades del recorrido, no metros fisicos.
    Devuelve intervalos de preparacion, vuelo y recepcion.
    """
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError('FPS debe ser positivo y finito')
    if not all(math.isfinite(v) for v in (*p0, *p1)):
        raise ValueError('Coordenadas del salto deben ser finitas')
    base = 23 if kind == 'bajar' else 14
    scale = max(1.0, math.sqrt(abs(p1[2]-p0[2])),
                math.hypot(p1[0]-p0[0], p1[1]-p0[1]))
    rate = fps / 24.0
    prep = max(1, round(base * 0.16 * rate))
    land = max(1, round(base * 0.20 * rate))
    flight = max(1, math.ceil((base-round(base*0.16)-round(base*0.20))*scale*rate))
    # Vuelo reducido a la mitad (2da pasada: 0.5 * 0.5 = 25% del original),
    # redondeado hacia arriba a fotogramas enteros. Aplica solo al salto
    # horizontal de largas distancias; las animaciones base 'subir' y
    # 'bajar' conservan su duracion unica (15 y 24 frames respectivamente).
    if kind == 'horizontal':
        flight = max(1, math.ceil(flight * JUMP_FLIGHT_FACTOR))
    return prep, flight, land

def jump_frame_count(p0, p1, kind, fps=24.0):
    return sum(jump_timing(p0, p1, kind, fps)) + 1

def jump_smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t*t*(3.0-2.0*t)

def jump_position(p0, p1, t, kind):
    """Arco Bezier cuadratico (parabola), con impulso y recepcion en suelo.

    El control alto se acerca al lado inferior: al bajar se avanza antes
    de caer; al subir se gana altura antes de acercarse al borde.
    Los puntos del recorrido y las duraciones originales se conservan.
    """
    t = min(max(t, 0.0), 1.0)
    u = min(max((t-0.16)/0.64, 0.0), 1.0)
    distance = math.hypot(p1[0]-p0[0], p1[1]-p0[1])
    height = abs(p1[2]-p0[2])
    bias = 0.18 if kind == 'subir' else 0.82 if kind == 'bajar' else 0.5
    control_z = max(p0[2], p1[2]) + max(0.8, 1.4*height, 0.45*distance)
    control = (p0[0]+bias*(p1[0]-p0[0]),
               p0[1]+bias*(p1[1]-p0[1]), control_z)
    return tuple((1-u)**2*a + 2*u*(1-u)*c + u*u*b
                 for a,b,c in zip(p0,p1,control))

def jump_phase(elapsed, timing):
    prep, flight, land = timing
    if elapsed <= prep:
        return 0.16 * elapsed / prep
    if elapsed <= prep + flight:
        return 0.16 + 0.64 * (elapsed-prep) / flight
    return min(1.0, 0.80 + 0.20 * (elapsed-prep-flight) / land)


def key_root(root, frame, p0, p1, phase, kind, rot):
    dx, dy = p1[0]-p0[0], p1[1]-p0[1]
    heading = math.degrees(math.atan2(-dx,dy)) if math.hypot(dx,dy)>1e-8 else rot[2]
    delta = (heading-rot[2]+180)%360-180
    root.rotation_mode = 'XYZ'
    root.location = jump_position(p0,p1,phase,kind)
    root.rotation_euler = (math.radians(rot[0]),math.radians(rot[1]),
                           math.radians(rot[2]+delta*jump_smooth(phase/0.16)))
    root.keyframe_insert(data_path='location',frame=frame)
    root.keyframe_insert(data_path='rotation_euler',frame=frame)


def action_curves(action):
    if hasattr(action,'fcurves'):
        return list(action.fcurves)
    return [fc for layer in action.layers for strip in layer.strips
            for bag in strip.channelbags for fc in bag.fcurves]


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

class DogJumpCycle:
    """Animacion de salto para perro - 15 frames"""
    def __init__(self, total_frames=15):
        self.total_frames = total_frames
        self.impulse_frames = (1, 5)
        self.jump_frames    = (6, 11)
        self.fall_frames    = (12, 15)

    def get_phase_progress(self, frame):
        for (s, e), phase in [(self.impulse_frames,'impulse'),(self.jump_frames,'jump'),(self.fall_frames,'fall')]:
            if s <= frame <= e:
                return phase, (frame - s) / max(1, e - s)
        return 'neutral', 0

    def rear_thigh(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        s = 1 if is_left else -1
        if ph == 'impulse': c = ease_in_out(pr)*0.20; return (-c, sin_wave(pr*6,6,0.03*s,0,0), sin_wave(pr*4,4,0.02,0,0))
        elif ph == 'jump':  e = ease_out(pr)*0.25;   return (-e, sin_wave(pr*12,12,0.015*s,0,0), sin_wave(pr*10,10,0.025,0,0))
        elif ph == 'fall':  t = ease_in(pr)*0.15;    return (-t, sin_wave(pr*8,8,0.01*s,0,0), sin_wave(pr*6,6,-0.01,0,0))
        return (0,0,0)

    def rear_shin(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        s = 1 if is_left else -1
        if ph == 'impulse': return (-ease_in_out(pr)*0.18, sin_wave(pr*8,8,0.02*s,0,0), sin_wave(pr*6,6,0.015,0,0))
        elif ph == 'jump':  return (-ease_out(pr)*0.22,    sin_wave(pr*12,12,0.01*s,0,0), sin_wave(pr*8,8,0.02,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.12,     sin_wave(pr*8,8,0.008*s,0,0), sin_wave(pr*4,4,0.01,0,0))
        return (0,0,0)

    def rear_foot(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        s = 1 if is_left else -1
        if ph == 'impulse': return (-ease_in_out(pr)*0.15, sin_wave(pr*12,12,0.03*s,0,0), sin_wave(pr*10,10,0.02,0,0))
        elif ph == 'jump':  return (-ease_out(pr)*0.18,    sin_wave(pr*25,25,0.02*s,0,0), sin_wave(pr*15,15,0.03,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.1,      sin_wave(pr*15,15,0.01*s,0,0), sin_wave(pr*8,8,0.015,0,0))
        return (0,0,0)

    def rear_toe(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': return (ease_in_out(pr)*0.12, 0, 0)
        elif ph == 'jump':  return (ease_out(pr)*0.08,    0, 0)
        elif ph == 'fall':  return (ease_in(pr)*0.05,     0, 0)
        return (0,0,0)

    def front_thigh(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        s = 1 if is_left else -1
        if ph == 'impulse': return (-ease_in_out(pr)*0.1,  sin_wave(pr*8,8,0.04*s,0,0), sin_wave(pr*6,6,-0.02,0,0))
        elif ph == 'jump':  return ( ease_out(pr)*0.35,    sin_wave(pr*15,15,0.03*s,0,0), sin_wave(pr*12,12,0.04,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.3,      sin_wave(pr*10,10,0.02*s,0,0), sin_wave(pr*8,8,0.02,0,0))
        return (0,0,0)

    def front_shin(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        s = 1 if is_left else -1
        if ph == 'impulse': return (-ease_in_out(pr)*0.15, sin_wave(pr*10,10,0.03*s,0,0), sin_wave(pr*8,8,-0.01,0,0))
        elif ph == 'jump':  return (-ease_out(pr)*0.25,    sin_wave(pr*20,20,0.02*s,0,0), sin_wave(pr*15,15,0.03,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.18,     sin_wave(pr*12,12,0.015*s,0,0), sin_wave(pr*10,10,0.02,0,0))
        return (0,0,0)

    def front_foot(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        s = 1 if is_left else -1
        if ph == 'impulse': return (-ease_in_out(pr)*0.12, sin_wave(pr*12,12,0.02*s,0,0), sin_wave(pr*8,8,-0.015,0,0))
        elif ph == 'jump':  return (-ease_out(pr)*0.2,     sin_wave(pr*18,18,0.015*s,0,0), sin_wave(pr*12,12,0.02,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.15,     sin_wave(pr*10,10,0.01*s,0,0), sin_wave(pr*6,6,0.01,0,0))
        return (0,0,0)

    def front_toe(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': return (ease_in_out(pr)*0.08, 0, 0)
        elif ph == 'jump':  return (ease_out(pr)*0.1,     0, 0)
        elif ph == 'fall':  return (ease_in(pr)*0.06,     0, 0)
        return (0,0,0)

    def spine_action(self, frame, segment, total_segments=7):
        ph, pr = self.get_phase_progress(frame)
        sf = segment / total_segments
        if ph == 'impulse': return (-ease_in_out(pr)*0.2*sf, sin_wave(pr*6,6,0.03*sf,0,0), ease_in_out(pr)*0.08*sf)
        elif ph == 'jump':  return ( ease_out(pr)*0.25*sf,   sin_wave(pr*10,10,0.02*sf,0,0), ease_out(pr)*0.12*sf)
        elif ph == 'fall':  return (-ease_in(pr)*0.15*sf,    sin_wave(pr*8,8,0.015*sf,0,0), ease_in(pr)*0.06*sf)
        return (0,0,0)

    def head_movement(self, frame):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': return (-ease_in_out(pr)*0.06, sin_wave(pr*8,8,0.03,0,0), sin_wave(pr*6,6,0.02,0,0))
        elif ph == 'jump':  return ( ease_out(pr)*0.08,    sin_wave(pr*12,12,0.04,0,0), sin_wave(pr*10,10,0.03,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.05,     sin_wave(pr*8,8,0.02,0,0), sin_wave(pr*6,6,0.015,0,0))
        return (0,0,0)

    def jaw_movement(self, frame):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': return (ease_in_out(pr)*0.03, 0, 0)
        elif ph == 'jump':  return (ease_out(pr)*0.04,    0, 0)
        elif ph == 'fall':  return (ease_in(pr)*0.02,     0, 0)
        return (0,0,0)

    def ear_movement(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        d = -1 if is_left else 1
        if ph == 'impulse': return (ease_in_out(pr)*0.05*d, sin_wave(pr*15,15,0.02,0,0), sin_wave(pr*12,12,0.015,0,0))
        elif ph == 'jump':  return (ease_out(pr)*0.06*d,    sin_wave(pr*20,20,0.025,0,0), sin_wave(pr*18,18,0.02,0,0))
        elif ph == 'fall':  return (-ease_in(pr)*0.04*d,    sin_wave(pr*12,12,0.015,0,0), sin_wave(pr*10,10,0.01,0,0))
        return (0,0,0)

    def neck_movement(self, frame):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': return (-ease_in_out(pr)*0.04, sin_wave(pr*8,8,0.02,0,0), 0)
        elif ph == 'jump':  return ( ease_out(pr)*0.05,    sin_wave(pr*12,12,0.03,0,0), 0)
        elif ph == 'fall':  return (-ease_in(pr)*0.03,     sin_wave(pr*8,8,0.02,0,0), 0)
        return (0,0,0)

    def tail_movement(self, frame, segment):
        ph, pr = self.get_phase_progress(frame)
        sf = segment / 3
        if ph == 'impulse': return (-ease_in_out(pr)*0.15*sf, sin_wave(pr*25,25,0.06*sf,0,0), sin_wave(pr*20,20,0.04*sf,0,0))
        elif ph == 'jump':  return ( ease_out(pr)*0.25*sf,    sin_wave(pr*40,40,0.1*sf,0,0), sin_wave(pr*35,35,0.08*sf,0,0))
        elif ph == 'fall':  return ( ease_in(pr)*0.15*sf,     sin_wave(pr*25,25,0.05*sf,0,0), sin_wave(pr*20,20,0.03*sf,0,0))
        return (0,0,0)

class QuadrupedWalkPlainCycle:
    def __init__(self, total_frames=24):
        self.total_frames    = total_frames
        self.impulse_frames  = (1, 6)
        self.jump_frames     = (7, 14)
        self.fall_frames     = (15, 21)
        self.recovery_frames = (22, total_frames)

    def get_phase_progress(self, frame):
        for (s, e), ph in [(self.impulse_frames,'impulse'),(self.jump_frames,'jump'),
                           (self.fall_frames,'fall'),(self.recovery_frames,'recovery')]:
            if s <= frame <= e:
                return ph, (frame - s) / max(1, e - s)
        return 'neutral', 0

    def get_leg_rotation(self, frame, is_rear=False, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse':
            a = ease_in_out(pr)*(0.2 if is_rear else 0.15)
            return (-a, sin_wave(pr*15,15,0.01,0,0), sin_wave(pr*10,10,0.005,0,0))
        elif ph == 'jump':
            e = 0.15 if is_rear else 0.08
            return (-e, sin_wave(pr*20,20,0.02,0,0), 0)
        elif ph == 'fall':
            if pr < 0.1: return (0, sin_wave(pr*12,12,0.01,0,0), sin_wave(pr*10,10,0.005,0,0))
            ap = (pr-0.1)/0.9; r = ease_out(ap)*(0.35 if is_rear else 0.2); b = 0.4 if is_rear else 0.25
            return (-b+r, sin_wave(pr*12,12,0.01,0,0), sin_wave(pr*10,10,0.005,0,0))
        return (0,0,0)

    def spine_jump_down(self, frame, segment, total_segments=7):
        ph, pr = self.get_phase_progress(frame)
        sf = segment / total_segments
        if ph == 'impulse': return (ease_in_out(pr)*0.1*sf, 0, 0)
        elif ph == 'jump':  return (-ease_out(pr)*0.25*sf, 0, 0)
        elif ph == 'fall':  x = -0.25*sf + ease_out(pr)*0.3*sf; return (x, 0, 0)
        return (0,0,0)

    def tail_jump_down(self, frame, segment):
        ph, pr = self.get_phase_progress(frame)
        sf = segment / 3
        if ph == 'impulse': return (ease_in_out(pr)*0.1*sf, sin_wave(pr*20,20,0.015,segment*3.14/6,0), sin_wave(frame,30,0.008,segment*3.14/8,0))
        elif ph == 'jump':  return (-ease_out(pr)*0.25*sf,  sin_wave(pr*25,25,0.025,segment*3.14/4,0), sin_wave(frame,30,0.008,segment*3.14/8,0))
        elif ph == 'fall':  x = -0.25*sf + ease_out(pr)*0.25*sf; return (x, sin_wave(pr*15,15,0.015,segment*3.14/3,0), sin_wave(frame,30,0.008,segment*3.14/8,0))
        return (0,0,sin_wave(frame,30,0.008,segment*3.14/8,0))

    def head_jump_down(self, frame):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': return (ease_in_out(pr)*0.02, sin_wave(pr*12,12,0.005,0,0), 0)
        elif ph == 'jump':  return (-ease_out(pr)*0.04,   sin_wave(pr*18,18,0.008,0,0), 0)
        elif ph == 'fall':  return (-0.04+ease_out(pr)*0.04, sin_wave(pr*10,10,0.005,0,0), 0)
        return (0,0,0)

    def ear_jump_down(self, frame, is_left=True):
        ph, pr = self.get_phase_progress(frame)
        if ph == 'impulse': a = ease_in_out(pr)*0.02; return (a if is_left else -a, sin_wave(pr*15,15,0.005,0,0), sin_wave(frame,25,0.003,0,0))
        elif ph == 'jump':  b = ease_out(pr)*0.03;    return (-b if is_left else b, sin_wave(pr*20,20,0.008,0.78,0), sin_wave(frame,25,0.003,0,0))
        elif ph == 'fall':  c = (-0.03+ease_out(pr)*0.03) if is_left else (0.03-ease_out(pr)*0.03); return (c, sin_wave(pr*12,12,0.005,0,0), sin_wave(frame,25,0.003,0,0))
        return (0,0,sin_wave(frame,25,0.003,0,0))

class NativeJumpPose:
    @staticmethod
    def _kfb(bone,frame):
        bone.rotation_mode="XYZ"
        bone.keyframe_insert(data_path="rotation_euler",frame=frame)

    def _bones_saltar_subir(self, bones, frame, rf):
            """Anima todos los bones del cuadrupedo en salto ascendente usando DogJumpCycle."""
            jump = DogJumpCycle(total_frames=15)
            lf = rf + 1  # local frame 1-based

            for side, is_l in (('L', True), ('R', False)):
                for key, rot in (
                    (f'thigh.{side}',        jump.rear_thigh(lf, is_l)),
                    (f'shin.{side}',         jump.rear_shin(lf, is_l)),
                    (f'foot.{side}',         jump.rear_foot(lf, is_l)),
                    (f'toe.{side}',          jump.rear_toe(lf, is_l)),
                    (f'front_thigh.{side}',  jump.front_thigh(lf, is_l)),
                    (f'front_shin.{side}',   jump.front_shin(lf, is_l)),
                    (f'front_foot.{side}',   jump.front_foot(lf, is_l)),
                    (f'front_toe.{side}',    jump.front_toe(lf, is_l)),
                    (f'ear.{side}',          jump.ear_movement(lf, is_l)),
                ):
                    if key in bones:
                        bones[key].rotation_euler = rot
                        self._kfb(bones[key], frame)

            for i in range(1, 8):
                key = f'spine_{i}'
                if key in bones:
                    bones[key].rotation_euler = jump.spine_action(lf, i, 7)
                    self._kfb(bones[key], frame)

            for i in range(1, 4):
                key = f'tail_{i}'
                if key in bones:
                    bones[key].rotation_euler = jump.tail_movement(lf, i)
                    self._kfb(bones[key], frame)

            if 'neck' in bones:
                bones['neck'].rotation_euler = jump.neck_movement(lf)
                self._kfb(bones['neck'], frame)
            if 'scull' in bones:
                bones['scull'].rotation_euler = jump.head_movement(lf)
                self._kfb(bones['scull'], frame)
            if 'scull_1' in bones:
                h = jump.head_movement(lf)
                bones['scull_1'].rotation_euler = tuple(x * 0.5 for x in h)
                self._kfb(bones['scull_1'], frame)
            if 'jaw_top' in bones:
                bones['jaw_top'].rotation_euler = jump.jaw_movement(lf)
                self._kfb(bones['jaw_top'], frame)

    def _bones_saltar_bajar(self, bones, frame, rf):
            """Anima todos los bones del cuadrupedo en salto descendente usando QuadrupedWalkPlainCycle."""
            cyc = QuadrupedWalkPlainCycle(total_frames=24)
            lf = rf + 1  # local frame 1-based
            ph, _ = cyc.get_phase_progress(lf)

            for side, is_l in (('L', True), ('R', False)):
                rear_rot  = cyc.get_leg_rotation(lf, True,  is_l)
                front_rot = cyc.get_leg_rotation(lf, False, is_l)
                front_fall = tuple(-x for x in front_rot) if ph == 'fall' else front_rot

                mapping = [
                    (f'shoulder.{side}',      (tuple(x * (0.2 if ph == 'impulse' else 1) for x in rear_rot)
                                               if ph != 'fall' else tuple(-x for x in rear_rot))),
                    (f'thigh.{side}',         tuple(x * 0.5 for x in rear_rot)),
                    (f'shin.{side}',          rear_rot),
                    (f'foot.{side}',          tuple(x * 0.8 for x in rear_rot)),
                    (f'toe.{side}',           tuple(x * 0.6 for x in rear_rot)),
                    (f'front_thigh.{side}',   tuple(x * 0.4 for x in front_rot)),
                    (f'front_shin.{side}',    front_rot),
                    (f'front_foot.{side}',    tuple(x * 0.7 for x in front_rot)),
                    (f'front_toe.{side}',     tuple(x * 0.5 for x in front_rot)),
                    (f'ear.{side}',           cyc.ear_jump_down(lf, is_l)),
                ]
                for key, rot in mapping:
                    if key in bones:
                        bones[key].rotation_euler = rot
                        self._kfb(bones[key], frame)

            for i in range(1, 8):
                key = f'spine_{i}'
                if key in bones:
                    bones[key].rotation_euler = cyc.spine_jump_down(lf, i, 7)
                    self._kfb(bones[key], frame)

            for i in range(1, 4):
                key = f'tail_{i}'
                if key in bones:
                    bones[key].rotation_euler = cyc.tail_jump_down(lf, i)
                    self._kfb(bones[key], frame)

            if 'scull' in bones:
                bones['scull'].rotation_euler = cyc.head_jump_down(lf)
                self._kfb(bones['scull'], frame)
            if 'scull_1' in bones:
                h = cyc.head_jump_down(lf)
                bones['scull_1'].rotation_euler = tuple(x * 0.5 for x in h)
                self._kfb(bones['scull_1'], frame)
            if 'jaw_top' in bones:
                bones['jaw_top'].rotation_euler = (0, 0, 0)
                self._kfb(bones['jaw_top'], frame)
            if 'neck' in bones:
                bones['neck'].rotation_euler = (0, 0, 0)
                self._kfb(bones['neck'], frame)


def key_pose(bones,frame,phase,kind,data=None):
    native=NativeJumpPose()
    if kind=='bajar': native._bones_saltar_bajar(bones,frame,phase*23)
    else: native._bones_saltar_subir(bones,frame,phase*14)
    if kind!='bajar' and phase>=0.80:
        recovery=jump_smooth((phase-0.80)/0.20)
        for bone in bones:
            bone.rotation_mode='XYZ'
            bone.rotation_euler=tuple(value*(1.0-recovery) for value in bone.rotation_euler)
            bone.keyframe_insert(data_path='rotation_euler',frame=frame)

def execute_animation(op=None, **kwargs):
    import bpy
    root=bpy.data.objects.get(ROOT_NAME)
    arm=bpy.data.objects.get(ARM_NAME)
    if root is None or arm is None:
        raise RuntimeError('No se encontro el root o rig del personaje')
    for obj, suffix in ((root,'root'),(arm,'arm')):
        obj.animation_data_create()
        obj.animation_data.action=bpy.data.actions.new(f'Slot_{SLOT:03d}_saltar_{KIND}_{suffix}')
    for frame in range(START_FRAME,END_FRAME+1):
        phase=jump_phase(frame-START_FRAME,TIMING)
        key_root(root,frame,P0,P1,phase,KIND,ROT)
        key_pose(arm.pose.bones,frame,phase,KIND,POSE_DATA)
    for obj,suffix in ((root,'root'),(arm,'arm')):
        action=obj.animation_data.action
        action['adaptive_jump']=KIND
        action['jump_ground_blend']=max(1,min(TIMING[0],TIMING[2])//2)
        for fc in action_curves(action):
            for key in fc.keyframe_points:
                key.interpolation='LINEAR'
        slot=obj.animation_data.action_slot
        obj.animation_data.action=None
        track=obj.animation_data.nla_tracks.new()
        track.name=f'Slot_{SLOT:03d}_{suffix}'
        strip=track.strips.new(action.name,START_FRAME,action)
        if slot is not None and hasattr(strip,'action_slot'):
            strip.action_slot=slot
        strip.frame_end=END_FRAME
        strip.extrapolation='NOTHING' if suffix=='arm' else 'HOLD_FORWARD'
        strip.use_auto_blend=False
    return True

if __name__ == "__main__":
    execute_animation()
