# -*- coding: utf-8 -*-
"""Saltos adaptativos: trayectoria y poses nativas compartidas por preview y exportacion."""
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
    # DogJumpCycle acababa en la compresion de recepcion. En el ultimo 20 %
    # recuperamos gradualmente la pose neutra para terminar con Jerry parado.
    if kind!='bajar' and phase>=0.80:
        recovery=jump_smooth((phase-0.80)/0.20)
        for bone in bones:
            bone.rotation_mode='XYZ'
            bone.rotation_euler=tuple(value*(1.0-recovery) for value in bone.rotation_euler)
            bone.keyframe_insert(data_path='rotation_euler',frame=frame)


RUNTIME = 'import math\nJUMP_FLIGHT_FACTOR = 0.25\n\ndef jump_timing(p0, p1, kind, fps=24.0):\n    """Tiempo artistico calibrado al salto original de una unidad a 24 fps.\n\n    Solo se alarga el vuelo: sqrt(desnivel) conserva la escala temporal\n    de una parabola; distancia horizontal limita la velocidad de avance.\n    Las coordenadas usan unidades del recorrido, no metros fisicos.\n    Devuelve intervalos de preparacion, vuelo y recepcion.\n    """\n    if not math.isfinite(fps) or fps <= 0:\n        raise ValueError(\'FPS debe ser positivo y finito\')\n    if not all(math.isfinite(v) for v in (*p0, *p1)):\n        raise ValueError(\'Coordenadas del salto deben ser finitas\')\n    base = 23 if kind == \'bajar\' else 14\n    scale = max(1.0, math.sqrt(abs(p1[2]-p0[2])),\n                math.hypot(p1[0]-p0[0], p1[1]-p0[1]))\n    rate = fps / 24.0\n    prep = max(1, round(base * 0.16 * rate))\n    land = max(1, round(base * 0.20 * rate))\n    flight = max(1, math.ceil((base-round(base*0.16)-round(base*0.20))*scale*rate))\n    # Vuelo reducido a la mitad (2da pasada: 0.5 * 0.5 = 25% del original),\n    # redondeado hacia arriba a fotogramas enteros. Aplica solo al salto\n    # horizontal de largas distancias; las animaciones base \'subir\' y\n    # \'bajar\' conservan su duracion unica (15 y 24 frames respectivamente).\n    if kind == \'horizontal\':\n        flight = max(1, math.ceil(flight * JUMP_FLIGHT_FACTOR))\n    return prep, flight, land\n\ndef jump_frame_count(p0, p1, kind, fps=24.0):\n    return sum(jump_timing(p0, p1, kind, fps)) + 1\n\ndef jump_smooth(t):\n    t = min(max(t, 0.0), 1.0)\n    return t*t*(3.0-2.0*t)\n\ndef jump_position(p0, p1, t, kind):\n    """Arco Bezier cuadratico (parabola), con impulso y recepcion en suelo.\n\n    El control alto se acerca al lado inferior: al bajar se avanza antes\n    de caer; al subir se gana altura antes de acercarse al borde.\n    Los puntos del recorrido y las duraciones originales se conservan.\n    """\n    t = min(max(t, 0.0), 1.0)\n    u = min(max((t-0.16)/0.64, 0.0), 1.0)\n    distance = math.hypot(p1[0]-p0[0], p1[1]-p0[1])\n    height = abs(p1[2]-p0[2])\n    bias = 0.18 if kind == \'subir\' else 0.82 if kind == \'bajar\' else 0.5\n    control_z = max(p0[2], p1[2]) + max(0.8, 1.4*height, 0.45*distance)\n    control = (p0[0]+bias*(p1[0]-p0[0]),\n               p0[1]+bias*(p1[1]-p0[1]), control_z)\n    return tuple((1-u)**2*a + 2*u*(1-u)*c + u*u*b\n                 for a,b,c in zip(p0,p1,control))\n\ndef jump_phase(elapsed, timing):\n    prep, flight, land = timing\n    if elapsed <= prep:\n        return 0.16 * elapsed / prep\n    if elapsed <= prep + flight:\n        return 0.16 + 0.64 * (elapsed-prep) / flight\n    return min(1.0, 0.80 + 0.20 * (elapsed-prep-flight) / land)\n\n\ndef key_root(root, frame, p0, p1, phase, kind, rot):\n    dx, dy = p1[0]-p0[0], p1[1]-p0[1]\n    heading = math.degrees(math.atan2(-dx,dy)) if math.hypot(dx,dy)>1e-8 else rot[2]\n    delta = (heading-rot[2]+180)%360-180\n    root.rotation_mode = \'XYZ\'\n    root.location = jump_position(p0,p1,phase,kind)\n    root.rotation_euler = (math.radians(rot[0]),math.radians(rot[1]),\n                           math.radians(rot[2]+delta*jump_smooth(phase/0.16)))\n    root.keyframe_insert(data_path=\'location\',frame=frame)\n    root.keyframe_insert(data_path=\'rotation_euler\',frame=frame)\n\n\ndef action_curves(action):\n    if hasattr(action,\'fcurves\'):\n        return list(action.fcurves)\n    return [fc for layer in action.layers for strip in layer.strips\n            for bag in strip.channelbags for fc in bag.fcurves]\n\n\ndef sin_wave(frame, period, amplitude, phase=0, offset=0):\n    return amplitude * math.sin(2 * math.pi * frame / period + phase) + offset\n\ndef cos_wave(frame, period, amplitude, phase=0, offset=0):\n    return amplitude * math.cos(2 * math.pi * frame / period + phase) + offset\n\ndef lerp(start, end, t):\n    return start + (end - start) * t\n\ndef ease_in_out(t):\n    return t * t * (3 - 2 * t)\n\ndef ease_out(t):\n    return 1 - (1 - t) * (1 - t)\n\ndef ease_in(t):\n    return t * t\n\nclass DogJumpCycle:\n    """Animacion de salto para perro - 15 frames"""\n    def __init__(self, total_frames=15):\n        self.total_frames = total_frames\n        self.impulse_frames = (1, 5)\n        self.jump_frames    = (6, 11)\n        self.fall_frames    = (12, 15)\n\n    def get_phase_progress(self, frame):\n        for (s, e), phase in [(self.impulse_frames,\'impulse\'),(self.jump_frames,\'jump\'),(self.fall_frames,\'fall\')]:\n            if s <= frame <= e:\n                return phase, (frame - s) / max(1, e - s)\n        return \'neutral\', 0\n\n    def rear_thigh(self, frame, is_left=True):\n        ph, pr = self.get_phase_progress(frame)\n        s = 1 if is_left else -1\n        if ph == \'impulse\': c = ease_in_out(pr)*0.20; return (-c, sin_wave(pr*6,6,0.03*s,0,0), sin_wave(pr*4,4,0.02,0,0))\n        elif ph == \'jump\':  e = ease_out(pr)*0.25;   return (-e, sin_wave(pr*12,12,0.015*s,0,0), sin_wave(pr*10,10,0.025,0,0))\n        elif ph == \'fall\':  t = ease_in(pr)*0.15;    return (-t, sin_wave(pr*8,8,0.01*s,0,0), sin_wave(pr*6,6,-0.01,0,0))\n        return (0,0,0)\n\n    def rear_shin(self, frame, is_left=True):\n        ph, pr = self.get_phase_progress(frame)\n        s = 1 if is_left else -1\n        if ph == \'impulse\': return (-ease_in_out(pr)*0.18, sin_wave(pr*8,8,0.02*s,0,0), sin_wave(pr*6,6,0.015,0,0))\n        elif ph == \'jump\':  return (-ease_out(pr)*0.22,    sin_wave(pr*12,12,0.01*s,0,0), sin_wave(pr*8,8,0.02,0,0))\n        elif ph == \'fall\':  return (-ease_in(pr)*0.12,     sin_wave(pr*8,8,0.008*s,0,0), sin_wave(pr*4,4,0.01,0,0))\n        return (0,0,0)\n\n    def rear_foot(self, frame, is_left=True):\n        ph, pr = self.get_phase_progress(frame)\n        s = 1 if is_left else -1\n        if ph == \'impulse\': return (-ease_in_out(pr)*0.15, sin_wave(pr*12,12,0.03*s,0,0), sin_wave(pr*10,10,0.02,0,0))\n        elif ph == \'jump\':  return (-ease_out(pr)*0.18,    sin_wave(pr*25,25,0.02*s,0,0), sin_wave(pr*15,15,0.03,0,0))\n        elif ph == \'fall\':  return (-ease_in(pr)*0.1,      sin_wave(pr*15,15,0.01*s,0,0), sin_wave(pr*8,8,0.015,0,0))\n        return (0,0,0)\n\n    def rear_toe(self, frame, is_left=True):\n        ph, pr = self.get_phase_progress(frame)\n        if ph == \'impulse\': return (ease_in_out(pr)*0.12, 0, 0)\n        elif ph == \'jump\':  return (ease_out(pr)*0.08,    0, 0)\n        elif ph == \'fall\':  return (ease_in(pr)*0.05,     0, 0)\n        return (0,0,0)\n\n    def front_thigh(self, frame, is_left=True):\n        ph, pr = self.get_phase_progress(frame)\n        s = 1 if is_left else -1\n        if ph == \'impulse\': return (-ease_in_out(pr)*0.1,  sin_wave(pr*8,8,0.04*s,0,0), sin_wave(pr*6,6,-0.02,0,0))\n        elif ph == \'jump\':  return ( ease_out(pr)*0.35,    sin_wave(pr*15,15,0.03*s,0,0), sin_wave(pr*12,12,0.04,0,0))\n        elif ph == \'fall\':  return (-ease_in(pr)*0.3,      sin_wave(pr*10,10,0.02*s,0,0), sin_wave(pr*8,8,0.02,0,0))\n        return (0,0,0)\n\n    def front_shin(self, frame, is_left=True):\n        ph, pr = self.get_phase_progress(frame)\n        s = 1 if is_left else -1\n        if ph == \'impulse\': return (-ease_in_out(pr)*0.15, sin_wave(pr*10,10,0.03*s,0,0), sin_wave(pr*8,8,-0.01,0,0))\n        elif ph == \'jump\':  return (-ease_out(pr)*0.25,    sin_wave(pr*20,20,0.02*s,0,0), sin_wave(pr*15,15,0.03,0,0))\n        elif ph == \'fall\':  return (-ease_in(pr)*0.18,     sin_wave(pr*12,12,0.015*s,0,0), sin_wave(pr*10,10,0.02,0,0))\n        return (0,0,0)\n\n    def front_foot(self, frame, is_left=True):\n        ph, pr = self.get_phase_progress(frame)\n        s = 1 if is_left else -1\n        if ph == \'impulse\': return (-ease_in_out(pr)*0.12, sin_wave(pr*12,12,0.02*s,0,0), sin_wave(pr*8,8,-0.015,0,0))\n        elif ph == \'jump\':  return (-ease_out(pr)*0.2,     sin_wave(pr*18,18,0.015*s,0,0), sin_wave(pr*12,12,0.02,0,0))\n        elif ph == \'fall\':  return (-ease_in(pr)*0.15,     sin_wave(pr*10,10,0.01*s,0,0), sin_wave(pr*6,6,0.01,0,0))\n        return (0,0,0)\n\n    def front_toe(self, frame, is_left=True):\n        ph, pr = self.get_phase_progress(frame)\n        if ph == \'impulse\': return (ease_in_out(pr)*0.08, 0, 0)\n        elif ph == \'jump\':  return (ease_out(pr)*0.1,     0, 0)\n        elif ph == \'fall\':  return (ease_in(pr)*0.06,     0, 0)\n        return (0,0,0)\n\n    def spine_action(self, frame, segment, total_segments=7):\n        ph, pr = self.get_phase_progress(frame)\n        sf = segment / total_segments\n        if ph == \'impulse\': return (-ease_in_out(pr)*0.2*sf, sin_wave(pr*6,6,0.03*sf,0,0), ease_in_out(pr)*0.08*sf)\n        elif ph == \'jump\':  return ( ease_out(pr)*0.25*sf,   sin_wave(pr*10,10,0.02*sf,0,0), ease_out(pr)*0.12*sf)\n        elif ph == \'fall\':  return (-ease_in(pr)*0.15*sf,    sin_wave(pr*8,8,0.015*sf,0,0), ease_in(pr)*0.06*sf)\n        return (0,0,0)\n\n    def head_movement(self, frame):\n        ph, pr = self.get_phase_progress(frame)\n        if ph == \'impulse\': return (-ease_in_out(pr)*0.06, sin_wave(pr*8,8,0.03,0,0), sin_wave(pr*6,6,0.02,0,0))\n        elif ph == \'jump\':  return ( ease_out(pr)*0.08,    sin_wave(pr*12,12,0.04,0,0), sin_wave(pr*10,10,0.03,0,0))\n        elif ph == \'fall\':  return (-ease_in(pr)*0.05,     sin_wave(pr*8,8,0.02,0,0), sin_wave(pr*6,6,0.015,0,0))\n        return (0,0,0)\n\n    def jaw_movement(self, frame):\n        ph, pr = self.get_phase_progress(frame)\n        if ph == \'impulse\': return (ease_in_out(pr)*0.03, 0, 0)\n        elif ph == \'jump\':  return (ease_out(pr)*0.04,    0, 0)\n        elif ph == \'fall\':  return (ease_in(pr)*0.02,     0, 0)\n        return (0,0,0)\n\n    def ear_movement(self, frame, is_left=True):\n        ph, pr = self.get_phase_progress(frame)\n        d = -1 if is_left else 1\n        if ph == \'impulse\': return (ease_in_out(pr)*0.05*d, sin_wave(pr*15,15,0.02,0,0), sin_wave(pr*12,12,0.015,0,0))\n        elif ph == \'jump\':  return (ease_out(pr)*0.06*d,    sin_wave(pr*20,20,0.025,0,0), sin_wave(pr*18,18,0.02,0,0))\n        elif ph == \'fall\':  return (-ease_in(pr)*0.04*d,    sin_wave(pr*12,12,0.015,0,0), sin_wave(pr*10,10,0.01,0,0))\n        return (0,0,0)\n\n    def neck_movement(self, frame):\n        ph, pr = self.get_phase_progress(frame)\n        if ph == \'impulse\': return (-ease_in_out(pr)*0.04, sin_wave(pr*8,8,0.02,0,0), 0)\n        elif ph == \'jump\':  return ( ease_out(pr)*0.05,    sin_wave(pr*12,12,0.03,0,0), 0)\n        elif ph == \'fall\':  return (-ease_in(pr)*0.03,     sin_wave(pr*8,8,0.02,0,0), 0)\n        return (0,0,0)\n\n    def tail_movement(self, frame, segment):\n        ph, pr = self.get_phase_progress(frame)\n        sf = segment / 3\n        if ph == \'impulse\': return (-ease_in_out(pr)*0.15*sf, sin_wave(pr*25,25,0.06*sf,0,0), sin_wave(pr*20,20,0.04*sf,0,0))\n        elif ph == \'jump\':  return ( ease_out(pr)*0.25*sf,    sin_wave(pr*40,40,0.1*sf,0,0), sin_wave(pr*35,35,0.08*sf,0,0))\n        elif ph == \'fall\':  return ( ease_in(pr)*0.15*sf,     sin_wave(pr*25,25,0.05*sf,0,0), sin_wave(pr*20,20,0.03*sf,0,0))\n        return (0,0,0)\n\nclass QuadrupedWalkPlainCycle:\n    def __init__(self, total_frames=24):\n        self.total_frames    = total_frames\n        self.impulse_frames  = (1, 6)\n        self.jump_frames     = (7, 14)\n        self.fall_frames     = (15, 21)\n        self.recovery_frames = (22, total_frames)\n\n    def get_phase_progress(self, frame):\n        for (s, e), ph in [(self.impulse_frames,\'impulse\'),(self.jump_frames,\'jump\'),\n                           (self.fall_frames,\'fall\'),(self.recovery_frames,\'recovery\')]:\n            if s <= frame <= e:\n                return ph, (frame - s) / max(1, e - s)\n        return \'neutral\', 0\n\n    def get_leg_rotation(self, frame, is_rear=False, is_left=True):\n        ph, pr = self.get_phase_progress(frame)\n        if ph == \'impulse\':\n            a = ease_in_out(pr)*(0.2 if is_rear else 0.15)\n            return (-a, sin_wave(pr*15,15,0.01,0,0), sin_wave(pr*10,10,0.005,0,0))\n        elif ph == \'jump\':\n            e = 0.15 if is_rear else 0.08\n            return (-e, sin_wave(pr*20,20,0.02,0,0), 0)\n        elif ph == \'fall\':\n            if pr < 0.1: return (0, sin_wave(pr*12,12,0.01,0,0), sin_wave(pr*10,10,0.005,0,0))\n            ap = (pr-0.1)/0.9; r = ease_out(ap)*(0.35 if is_rear else 0.2); b = 0.4 if is_rear else 0.25\n            return (-b+r, sin_wave(pr*12,12,0.01,0,0), sin_wave(pr*10,10,0.005,0,0))\n        return (0,0,0)\n\n    def spine_jump_down(self, frame, segment, total_segments=7):\n        ph, pr = self.get_phase_progress(frame)\n        sf = segment / total_segments\n        if ph == \'impulse\': return (ease_in_out(pr)*0.1*sf, 0, 0)\n        elif ph == \'jump\':  return (-ease_out(pr)*0.25*sf, 0, 0)\n        elif ph == \'fall\':  x = -0.25*sf + ease_out(pr)*0.3*sf; return (x, 0, 0)\n        return (0,0,0)\n\n    def tail_jump_down(self, frame, segment):\n        ph, pr = self.get_phase_progress(frame)\n        sf = segment / 3\n        if ph == \'impulse\': return (ease_in_out(pr)*0.1*sf, sin_wave(pr*20,20,0.015,segment*3.14/6,0), sin_wave(frame,30,0.008,segment*3.14/8,0))\n        elif ph == \'jump\':  return (-ease_out(pr)*0.25*sf,  sin_wave(pr*25,25,0.025,segment*3.14/4,0), sin_wave(frame,30,0.008,segment*3.14/8,0))\n        elif ph == \'fall\':  x = -0.25*sf + ease_out(pr)*0.25*sf; return (x, sin_wave(pr*15,15,0.015,segment*3.14/3,0), sin_wave(frame,30,0.008,segment*3.14/8,0))\n        return (0,0,sin_wave(frame,30,0.008,segment*3.14/8,0))\n\n    def head_jump_down(self, frame):\n        ph, pr = self.get_phase_progress(frame)\n        if ph == \'impulse\': return (ease_in_out(pr)*0.02, sin_wave(pr*12,12,0.005,0,0), 0)\n        elif ph == \'jump\':  return (-ease_out(pr)*0.04,   sin_wave(pr*18,18,0.008,0,0), 0)\n        elif ph == \'fall\':  return (-0.04+ease_out(pr)*0.04, sin_wave(pr*10,10,0.005,0,0), 0)\n        return (0,0,0)\n\n    def ear_jump_down(self, frame, is_left=True):\n        ph, pr = self.get_phase_progress(frame)\n        if ph == \'impulse\': a = ease_in_out(pr)*0.02; return (a if is_left else -a, sin_wave(pr*15,15,0.005,0,0), sin_wave(frame,25,0.003,0,0))\n        elif ph == \'jump\':  b = ease_out(pr)*0.03;    return (-b if is_left else b, sin_wave(pr*20,20,0.008,0.78,0), sin_wave(frame,25,0.003,0,0))\n        elif ph == \'fall\':  c = (-0.03+ease_out(pr)*0.03) if is_left else (0.03-ease_out(pr)*0.03); return (c, sin_wave(pr*12,12,0.005,0,0), sin_wave(frame,25,0.003,0,0))\n        return (0,0,sin_wave(frame,25,0.003,0,0))\n\nclass NativeJumpPose:\n    @staticmethod\n    def _kfb(bone,frame):\n        bone.rotation_mode="XYZ"\n        bone.keyframe_insert(data_path="rotation_euler",frame=frame)\n\n    def _bones_saltar_subir(self, bones, frame, rf):\n            """Anima todos los bones del cuadrupedo en salto ascendente usando DogJumpCycle."""\n            jump = DogJumpCycle(total_frames=15)\n            lf = rf + 1  # local frame 1-based\n\n            for side, is_l in ((\'L\', True), (\'R\', False)):\n                for key, rot in (\n                    (f\'thigh.{side}\',        jump.rear_thigh(lf, is_l)),\n                    (f\'shin.{side}\',         jump.rear_shin(lf, is_l)),\n                    (f\'foot.{side}\',         jump.rear_foot(lf, is_l)),\n                    (f\'toe.{side}\',          jump.rear_toe(lf, is_l)),\n                    (f\'front_thigh.{side}\',  jump.front_thigh(lf, is_l)),\n                    (f\'front_shin.{side}\',   jump.front_shin(lf, is_l)),\n                    (f\'front_foot.{side}\',   jump.front_foot(lf, is_l)),\n                    (f\'front_toe.{side}\',    jump.front_toe(lf, is_l)),\n                    (f\'ear.{side}\',          jump.ear_movement(lf, is_l)),\n                ):\n                    if key in bones:\n                        bones[key].rotation_euler = rot\n                        self._kfb(bones[key], frame)\n\n            for i in range(1, 8):\n                key = f\'spine_{i}\'\n                if key in bones:\n                    bones[key].rotation_euler = jump.spine_action(lf, i, 7)\n                    self._kfb(bones[key], frame)\n\n            for i in range(1, 4):\n                key = f\'tail_{i}\'\n                if key in bones:\n                    bones[key].rotation_euler = jump.tail_movement(lf, i)\n                    self._kfb(bones[key], frame)\n\n            if \'neck\' in bones:\n                bones[\'neck\'].rotation_euler = jump.neck_movement(lf)\n                self._kfb(bones[\'neck\'], frame)\n            if \'scull\' in bones:\n                bones[\'scull\'].rotation_euler = jump.head_movement(lf)\n                self._kfb(bones[\'scull\'], frame)\n            if \'scull_1\' in bones:\n                h = jump.head_movement(lf)\n                bones[\'scull_1\'].rotation_euler = tuple(x * 0.5 for x in h)\n                self._kfb(bones[\'scull_1\'], frame)\n            if \'jaw_top\' in bones:\n                bones[\'jaw_top\'].rotation_euler = jump.jaw_movement(lf)\n                self._kfb(bones[\'jaw_top\'], frame)\n\n    def _bones_saltar_bajar(self, bones, frame, rf):\n            """Anima todos los bones del cuadrupedo en salto descendente usando QuadrupedWalkPlainCycle."""\n            cyc = QuadrupedWalkPlainCycle(total_frames=24)\n            lf = rf + 1  # local frame 1-based\n            ph, _ = cyc.get_phase_progress(lf)\n\n            for side, is_l in ((\'L\', True), (\'R\', False)):\n                rear_rot  = cyc.get_leg_rotation(lf, True,  is_l)\n                front_rot = cyc.get_leg_rotation(lf, False, is_l)\n                front_fall = tuple(-x for x in front_rot) if ph == \'fall\' else front_rot\n\n                mapping = [\n                    (f\'shoulder.{side}\',      (tuple(x * (0.2 if ph == \'impulse\' else 1) for x in rear_rot)\n                                               if ph != \'fall\' else tuple(-x for x in rear_rot))),\n                    (f\'thigh.{side}\',         tuple(x * 0.5 for x in rear_rot)),\n                    (f\'shin.{side}\',          rear_rot),\n                    (f\'foot.{side}\',          tuple(x * 0.8 for x in rear_rot)),\n                    (f\'toe.{side}\',           tuple(x * 0.6 for x in rear_rot)),\n                    (f\'front_thigh.{side}\',   tuple(x * 0.4 for x in front_rot)),\n                    (f\'front_shin.{side}\',    front_rot),\n                    (f\'front_foot.{side}\',    tuple(x * 0.7 for x in front_rot)),\n                    (f\'front_toe.{side}\',     tuple(x * 0.5 for x in front_rot)),\n                    (f\'ear.{side}\',           cyc.ear_jump_down(lf, is_l)),\n                ]\n                for key, rot in mapping:\n                    if key in bones:\n                        bones[key].rotation_euler = rot\n                        self._kfb(bones[key], frame)\n\n            for i in range(1, 8):\n                key = f\'spine_{i}\'\n                if key in bones:\n                    bones[key].rotation_euler = cyc.spine_jump_down(lf, i, 7)\n                    self._kfb(bones[key], frame)\n\n            for i in range(1, 4):\n                key = f\'tail_{i}\'\n                if key in bones:\n                    bones[key].rotation_euler = cyc.tail_jump_down(lf, i)\n                    self._kfb(bones[key], frame)\n\n            if \'scull\' in bones:\n                bones[\'scull\'].rotation_euler = cyc.head_jump_down(lf)\n                self._kfb(bones[\'scull\'], frame)\n            if \'scull_1\' in bones:\n                h = cyc.head_jump_down(lf)\n                bones[\'scull_1\'].rotation_euler = tuple(x * 0.5 for x in h)\n                self._kfb(bones[\'scull_1\'], frame)\n            if \'jaw_top\' in bones:\n                bones[\'jaw_top\'].rotation_euler = (0, 0, 0)\n                self._kfb(bones[\'jaw_top\'], frame)\n            if \'neck\' in bones:\n                bones[\'neck\'].rotation_euler = (0, 0, 0)\n                self._kfb(bones[\'neck\'], frame)\n\n\ndef key_pose(bones,frame,phase,kind,data=None):\n    native=NativeJumpPose()\n    if kind==\'bajar\': native._bones_saltar_bajar(bones,frame,phase*23)\n    else: native._bones_saltar_subir(bones,frame,phase*14)\n\ndef execute_animation(op=None, **kwargs):\n    import bpy\n    root=bpy.data.objects.get(ROOT_NAME)\n    arm=bpy.data.objects.get(ARM_NAME)\n    if root is None or arm is None:\n        raise RuntimeError(\'No se encontro el root o rig del personaje\')\n    for obj, suffix in ((root,\'root\'),(arm,\'arm\')):\n        obj.animation_data_create()\n        obj.animation_data.action=bpy.data.actions.new(f\'Slot_{SLOT:03d}_saltar_{KIND}_{suffix}\')\n    for frame in range(START_FRAME,END_FRAME+1):\n        phase=jump_phase(frame-START_FRAME,TIMING)\n        key_root(root,frame,P0,P1,phase,KIND,ROT)\n        key_pose(arm.pose.bones,frame,phase,KIND,POSE_DATA)\n    for obj,suffix in ((root,\'root\'),(arm,\'arm\')):\n        action=obj.animation_data.action\n        action[\'adaptive_jump\']=KIND\n        action[\'jump_ground_blend\']=max(1,min(TIMING[0],TIMING[2])//2)\n        for fc in action_curves(action):\n            for key in fc.keyframe_points:\n                key.interpolation=\'LINEAR\'\n        slot=obj.animation_data.action_slot\n        obj.animation_data.action=None\n        track=obj.animation_data.nla_tracks.new()\n        track.name=f\'Slot_{SLOT:03d}_{suffix}\'\n        strip=track.strips.new(action.name,START_FRAME,action)\n        if slot is not None and hasattr(strip,\'action_slot\'):\n            strip.action_slot=slot\n        strip.frame_end=END_FRAME\n        strip.extrapolation=\'NOTHING\' if suffix==\'arm\' else \'HOLD_FORWARD\'\n        strip.use_auto_blend=False\n    return True\n'


# Mantener el runtime exportado sincronizado con key_pose(). La sustitucion
# incorpora la recuperacion final en cada .py generado sin duplicar a mano el
# bloque RUNTIME completo.
_KEY_POSE_BASE = """def key_pose(bones,frame,phase,kind,data=None):
    native=NativeJumpPose()
    if kind=='bajar': native._bones_saltar_bajar(bones,frame,phase*23)
    else: native._bones_saltar_subir(bones,frame,phase*14)
"""
_KEY_POSE_STANDING = _KEY_POSE_BASE + """    if kind!='bajar' and phase>=0.80:
        recovery=jump_smooth((phase-0.80)/0.20)
        for bone in bones:
            bone.rotation_mode='XYZ'
            bone.rotation_euler=tuple(value*(1.0-recovery) for value in bone.rotation_euler)
            bone.keyframe_insert(data_path='rotation_euler',frame=frame)
"""
if _KEY_POSE_BASE not in RUNTIME:
    raise RuntimeError('No se encontro key_pose en el runtime embebido de Jerry')
RUNTIME=RUNTIME.replace(_KEY_POSE_BASE,_KEY_POSE_STANDING,1)


def generate_jump(slot_index,start_frame,points,root_rot,kind,fps=24.0,pose_data=None):
    p0=tuple(points[0]['coordinates'][c] for c in ('x','y','z'))
    p1=tuple(points[-1]['coordinates'][c] for c in ('x','y','z'))
    timing=jump_timing(p0,p1,kind,fps)
    end=start_frame+sum(timing)
    values=dict(SLOT=slot_index,START_FRAME=start_frame,END_FRAME=end,
                P0=p0,P1=p1,TIMING=timing,KIND=kind,ROT=tuple(root_rot),
                POSE_DATA=pose_data,ROOT_NAME=ROOT_NAME,ARM_NAME=ARM_NAME)
    values['ANIMATION_INFO']=dict(name=f'slot_{slot_index:03d}_{ROOT_NAME}_saltar_{kind}',
        frame_count=end-start_frame+1,fps=fps,duration_seconds=(end-start_frame+1)/fps,
        entity=ROOT_NAME,slot=slot_index,movement_type='saltar_'+kind,animation_type='procedural')
    header='import bpy\n'+'\n'.join(f'{k} = {v!r}' for k,v in values.items())+'\n'
    return header+RUNTIME+'\nif __name__ == "__main__":\n    execute_animation()\n',end

ROOT_NAME = 'jerry'
ARM_NAME = 'Dog_001_rig'
