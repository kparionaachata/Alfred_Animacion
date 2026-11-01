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
    base = 34 if kind == 'bajar' else 17
    scale = max(1.0, math.sqrt(abs(p1[2]-p0[2])),
                math.hypot(p1[0]-p0[0], p1[1]-p0[1]))
    rate = fps / 24.0
    prep = max(1, round(base * 0.16 * rate))
    land = max(1, round(base * 0.20 * rate))
    flight = max(1, math.ceil((base-round(base*0.16)-round(base*0.20))*scale*rate))
    # Vuelo reducido a la mitad (2da pasada: 0.5 * 0.5 = 25% del original),
    # redondeado hacia arriba a fotogramas enteros. Aplica solo al salto
    # horizontal de largas distancias; las animaciones base 'subir' y
    # 'bajar' conservan su duracion unica.
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


def key_pose(bones,frame,phase,kind,data):
    for name,keys in data.items():
        bone=bones.get(name)
        if bone is None: continue
        frames=sorted(keys)
        sample=phase*frames[-1]
        lo=max((f for f in frames if f<=sample),default=frames[0])
        hi=min((f for f in frames if f>=sample),default=frames[-1])
        w=(sample-lo)/(hi-lo) if hi!=lo else 0.0
        bone.rotation_mode='XYZ'
        bone.rotation_euler=tuple(a+(b-a)*w for a,b in zip(keys[lo],keys[hi]))
        bone.keyframe_insert(data_path='rotation_euler',frame=frame)


RUNTIME = 'import math\nJUMP_FLIGHT_FACTOR = 0.25\n\ndef jump_timing(p0, p1, kind, fps=24.0):\n    """Tiempo artistico calibrado al salto original de una unidad a 24 fps.\n\n    Solo se alarga el vuelo: sqrt(desnivel) conserva la escala temporal\n    de una parabola; distancia horizontal limita la velocidad de avance.\n    Las coordenadas usan unidades del recorrido, no metros fisicos.\n    Devuelve intervalos de preparacion, vuelo y recepcion.\n    """\n    if not math.isfinite(fps) or fps <= 0:\n        raise ValueError(\'FPS debe ser positivo y finito\')\n    if not all(math.isfinite(v) for v in (*p0, *p1)):\n        raise ValueError(\'Coordenadas del salto deben ser finitas\')\n    base = 34 if kind == \'bajar\' else 17\n    scale = max(1.0, math.sqrt(abs(p1[2]-p0[2])),\n                math.hypot(p1[0]-p0[0], p1[1]-p0[1]))\n    rate = fps / 24.0\n    prep = max(1, round(base * 0.16 * rate))\n    land = max(1, round(base * 0.20 * rate))\n    flight = max(1, math.ceil((base-round(base*0.16)-round(base*0.20))*scale*rate))\n    # Vuelo reducido a la mitad (2da pasada: 0.5 * 0.5 = 25% del original),\n    # redondeado hacia arriba a fotogramas enteros. Aplica solo al salto\n    # horizontal de largas distancias; las animaciones base \'subir\' y\n    # \'bajar\' conservan su duracion unica.\n    if kind == \'horizontal\':\n        flight = max(1, math.ceil(flight * JUMP_FLIGHT_FACTOR))\n    return prep, flight, land\n\ndef jump_frame_count(p0, p1, kind, fps=24.0):\n    return sum(jump_timing(p0, p1, kind, fps)) + 1\n\ndef jump_smooth(t):\n    t = min(max(t, 0.0), 1.0)\n    return t*t*(3.0-2.0*t)\n\ndef jump_position(p0, p1, t, kind):\n    """Arco Bezier cuadratico (parabola), con impulso y recepcion en suelo.\n\n    El control alto se acerca al lado inferior: al bajar se avanza antes\n    de caer; al subir se gana altura antes de acercarse al borde.\n    Los puntos del recorrido y las duraciones originales se conservan.\n    """\n    t = min(max(t, 0.0), 1.0)\n    u = min(max((t-0.16)/0.64, 0.0), 1.0)\n    distance = math.hypot(p1[0]-p0[0], p1[1]-p0[1])\n    height = abs(p1[2]-p0[2])\n    bias = 0.18 if kind == \'subir\' else 0.82 if kind == \'bajar\' else 0.5\n    control_z = max(p0[2], p1[2]) + max(0.8, 1.4*height, 0.45*distance)\n    control = (p0[0]+bias*(p1[0]-p0[0]),\n               p0[1]+bias*(p1[1]-p0[1]), control_z)\n    return tuple((1-u)**2*a + 2*u*(1-u)*c + u*u*b\n                 for a,b,c in zip(p0,p1,control))\n\ndef jump_phase(elapsed, timing):\n    prep, flight, land = timing\n    if elapsed <= prep:\n        return 0.16 * elapsed / prep\n    if elapsed <= prep + flight:\n        return 0.16 + 0.64 * (elapsed-prep) / flight\n    return min(1.0, 0.80 + 0.20 * (elapsed-prep-flight) / land)\n\n\ndef key_root(root, frame, p0, p1, phase, kind, rot):\n    dx, dy = p1[0]-p0[0], p1[1]-p0[1]\n    heading = math.degrees(math.atan2(-dx,dy)) if math.hypot(dx,dy)>1e-8 else rot[2]\n    delta = (heading-rot[2]+180)%360-180\n    root.rotation_mode = \'XYZ\'\n    root.location = jump_position(p0,p1,phase,kind)\n    root.rotation_euler = (math.radians(rot[0]),math.radians(rot[1]),\n                           math.radians(rot[2]+delta*jump_smooth(phase/0.16)))\n    root.keyframe_insert(data_path=\'location\',frame=frame)\n    root.keyframe_insert(data_path=\'rotation_euler\',frame=frame)\n\n\ndef action_curves(action):\n    if hasattr(action,\'fcurves\'):\n        return list(action.fcurves)\n    return [fc for layer in action.layers for strip in layer.strips\n            for bag in strip.channelbags for fc in bag.fcurves]\n\n\ndef key_pose(bones,frame,phase,kind,data):\n    for name,keys in data.items():\n        bone=bones.get(name)\n        if bone is None: continue\n        frames=sorted(keys)\n        sample=phase*frames[-1]\n        lo=max((f for f in frames if f<=sample),default=frames[0])\n        hi=min((f for f in frames if f>=sample),default=frames[-1])\n        w=(sample-lo)/(hi-lo) if hi!=lo else 0.0\n        bone.rotation_mode=\'XYZ\'\n        bone.rotation_euler=tuple(a+(b-a)*w for a,b in zip(keys[lo],keys[hi]))\n        bone.keyframe_insert(data_path=\'rotation_euler\',frame=frame)\n\ndef execute_animation(op=None, **kwargs):\n    import bpy\n    root=bpy.data.objects.get(ROOT_NAME)\n    arm=bpy.data.objects.get(ARM_NAME)\n    if root is None or arm is None:\n        raise RuntimeError(\'No se encontro el root o rig del personaje\')\n    for obj, suffix in ((root,\'root\'),(arm,\'arm\')):\n        obj.animation_data_create()\n        obj.animation_data.action=bpy.data.actions.new(f\'Slot_{SLOT:03d}_saltar_{KIND}_{suffix}\')\n    for frame in range(START_FRAME,END_FRAME+1):\n        phase=jump_phase(frame-START_FRAME,TIMING)\n        key_root(root,frame,P0,P1,phase,KIND,ROT)\n        key_pose(arm.pose.bones,frame,phase,KIND,POSE_DATA)\n    for obj,suffix in ((root,\'root\'),(arm,\'arm\')):\n        action=obj.animation_data.action\n        action[\'adaptive_jump\']=KIND\n        action[\'jump_ground_blend\']=max(1,min(TIMING[0],TIMING[2])//2)\n        for fc in action_curves(action):\n            for key in fc.keyframe_points:\n                key.interpolation=\'LINEAR\'\n        slot=obj.animation_data.action_slot\n        obj.animation_data.action=None\n        track=obj.animation_data.nla_tracks.new()\n        track.name=f\'Slot_{SLOT:03d}_{suffix}\'\n        strip=track.strips.new(action.name,START_FRAME,action)\n        if slot is not None and hasattr(strip,\'action_slot\'):\n            strip.action_slot=slot\n        strip.frame_end=END_FRAME\n        strip.extrapolation=\'NOTHING\' if suffix==\'arm\' else \'HOLD_FORWARD\'\n        strip.use_auto_blend=False\n    return True\n'


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

ROOT_NAME = 'alfred'
ARM_NAME = 'Armature'
