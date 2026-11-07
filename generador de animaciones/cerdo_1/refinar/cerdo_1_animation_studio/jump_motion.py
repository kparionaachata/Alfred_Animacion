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

CUERPO_FRENTE = 0.988   # m: del root a la punta del hocico (rig del cerdo)
CUERPO_ATRAS = 0.492    # m: del root a las ancas
HOLGURA = 0.06         # m: distancia minima al bloque

def jump_position(p0, p1, t, kind):
    """Trayectoria del root para un cuerpo LARGO sobre bloques de 1 m3.
    subir: sube casi en vertical hasta pasar el borde del bloque y despues avanza encima (el hocico nunca entra en el bloque);
    bajar: avanza hasta que las ancas salen del bloque y recien ahi cae; horizontal: arco de siempre."""
    t = min(max(t, 0.0), 1.0)
    u = min(max((t-0.16)/0.64, 0.0), 1.0)
    dx, dy = p1[0]-p0[0], p1[1]-p0[1]
    D = math.hypot(dx, dy)
    sm = lambda x: x*x*(3.0-2.0*x)
    if kind not in ('subir', 'bajar') or D < 1e-6:
        height = abs(p1[2]-p0[2])
        control_z = max(p0[2], p1[2]) + max(0.8, 1.4*height, 0.45*D)
        control = (p0[0]+0.5*dx, p0[1]+0.5*dy, control_z)
        return tuple((1-u)**2*a + 2*u*(1-u)*c + u*u*b for a,b,c in zip(p0,p1,control))
    z0, z1 = p0[2], p1[2]
    if kind == 'subir':
        borde = D - 0.5                                        # borde del bloque (el punto final es el centro de su cara)
        s1 = max(0.0, min(0.5, (borde - CUERPO_FRENTE - 0.01) / D))
        alto = z1 + 0.15
        if u < 0.45:
            w = u / 0.45; s = s1*sm(w); z = z0 + (alto-z0)*(1-(1-w)**2)
        else:
            w = (u-0.45)/0.55; s = s1 + (1-s1)*sm(w); z = alto + (z1-alto)*w*w
    else:
        borde = 0.5                                            # el punto inicial es el centro de la cara superior del bloque
        se = min(0.95, (borde + CUERPO_ATRAS + 0.16) / D)
        if u < 0.55:
            w = u / 0.55; s = se*sm(w); z = z0 + 0.12*math.sin(math.pi*w)
        else:
            w = (u-0.55)/0.45; s = se + (1-se)*w; z = z0 + (z1-z0)*w*w
    return (p0[0]+dx*s, p0[1]+dy*s, z)

PEZUNAS = (('Leg:FL:Bend_cerdo_1', 0.1235), ('Leg:FR:Bend_cerdo_1', 0.1235), ('Leg:BL:Bend_cerdo_1', 0.1235), ('Leg:BR:Bend_cerdo_1', 0.1235))   # parte baja de cada pata y medio ancho de su pezuna
PEZUNAS_REPOSO = 0.0048   # m: esquina mas baja de las pezunas sobre el root, en reposo (medido en el rig)

def _alza_pezunas(arm, root):
    """Cuanto subir el root para que la esquina MAS BAJA de las pezunas (con la pose actual, medida de verdad) no se hunda en el bloque."""
    import bpy
    from mathutils import Vector
    bpy.context.view_layer.update()
    W = arm.matrix_world; zr = root.matrix_world.translation.z; zmin = None
    for n, w in PEZUNAS:
        pb = arm.pose.bones.get(n)
        if pb is None:
            continue
        M = W @ pb.matrix
        for sx in (-1, 1):
            for sz in (-1, 1):
                z = (M @ Vector((sx * w, pb.length, sz * w))).z
                if zmin is None or z < zmin:
                    zmin = z
    return 0.0 if zmin is None else max(0.0, PEZUNAS_REPOSO - (zmin - zr))

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


RUNTIME = 'import math\nJUMP_FLIGHT_FACTOR = 0.25\n\ndef jump_timing(p0, p1, kind, fps=24.0):\n    """Tiempo artistico calibrado al salto original de una unidad a 24 fps.\n\n    Solo se alarga el vuelo: sqrt(desnivel) conserva la escala temporal\n    de una parabola; distancia horizontal limita la velocidad de avance.\n    Las coordenadas usan unidades del recorrido, no metros fisicos.\n    Devuelve intervalos de preparacion, vuelo y recepcion.\n    """\n    if not math.isfinite(fps) or fps <= 0:\n        raise ValueError(\'FPS debe ser positivo y finito\')\n    if not all(math.isfinite(v) for v in (*p0, *p1)):\n        raise ValueError(\'Coordenadas del salto deben ser finitas\')\n    base = 34 if kind == \'bajar\' else 17\n    scale = max(1.0, math.sqrt(abs(p1[2]-p0[2])),\n                math.hypot(p1[0]-p0[0], p1[1]-p0[1]))\n    rate = fps / 24.0\n    prep = max(1, round(base * 0.16 * rate))\n    land = max(1, round(base * 0.20 * rate))\n    flight = max(1, math.ceil((base-round(base*0.16)-round(base*0.20))*scale*rate))\n    # Vuelo reducido a la mitad (2da pasada: 0.5 * 0.5 = 25% del original),\n    # redondeado hacia arriba a fotogramas enteros. Aplica solo al salto\n    # horizontal de largas distancias; las animaciones base \'subir\' y\n    # \'bajar\' conservan su duracion unica.\n    if kind == \'horizontal\':\n        flight = max(1, math.ceil(flight * JUMP_FLIGHT_FACTOR))\n    return prep, flight, land\n\ndef jump_frame_count(p0, p1, kind, fps=24.0):\n    return sum(jump_timing(p0, p1, kind, fps)) + 1\n\ndef jump_smooth(t):\n    t = min(max(t, 0.0), 1.0)\n    return t*t*(3.0-2.0*t)\n\nCUERPO_FRENTE = 0.988   # m: del root a la punta del hocico (rig del cerdo)\nCUERPO_ATRAS = 0.492    # m: del root a las ancas\nHOLGURA = 0.06         # m: distancia minima al bloque\n\ndef jump_position(p0, p1, t, kind):\n    """Trayectoria del root para un cuerpo LARGO sobre bloques de 1 m3.\n    subir: sube casi en vertical hasta pasar el borde del bloque y despues avanza encima (el hocico nunca entra en el bloque);\n    bajar: avanza hasta que las ancas salen del bloque y recien ahi cae; horizontal: arco de siempre."""\n    t = min(max(t, 0.0), 1.0)\n    u = min(max((t-0.16)/0.64, 0.0), 1.0)\n    dx, dy = p1[0]-p0[0], p1[1]-p0[1]\n    D = math.hypot(dx, dy)\n    sm = lambda x: x*x*(3.0-2.0*x)\n    if kind not in (\'subir\', \'bajar\') or D < 1e-6:\n        height = abs(p1[2]-p0[2])\n        control_z = max(p0[2], p1[2]) + max(0.8, 1.4*height, 0.45*D)\n        control = (p0[0]+0.5*dx, p0[1]+0.5*dy, control_z)\n        return tuple((1-u)**2*a + 2*u*(1-u)*c + u*u*b for a,b,c in zip(p0,p1,control))\n    z0, z1 = p0[2], p1[2]\n    if kind == \'subir\':\n        borde = D - 0.5                                        # borde del bloque (el punto final es el centro de su cara)\n        s1 = max(0.0, min(0.5, (borde - CUERPO_FRENTE - 0.01) / D))\n        alto = z1 + 0.15\n        if u < 0.45:\n            w = u / 0.45; s = s1*sm(w); z = z0 + (alto-z0)*(1-(1-w)**2)\n        else:\n            w = (u-0.45)/0.55; s = s1 + (1-s1)*sm(w); z = alto + (z1-alto)*w*w\n    else:\n        borde = 0.5                                            # el punto inicial es el centro de la cara superior del bloque\n        se = min(0.95, (borde + CUERPO_ATRAS + 0.16) / D)\n        if u < 0.55:\n            w = u / 0.55; s = se*sm(w); z = z0 + 0.12*math.sin(math.pi*w)\n        else:\n            w = (u-0.55)/0.45; s = se + (1-se)*w; z = z0 + (z1-z0)*w*w\n    return (p0[0]+dx*s, p0[1]+dy*s, z)\n\nPEZUNAS = ((\'Leg:FL:Bend_cerdo_1\', 0.1235), (\'Leg:FR:Bend_cerdo_1\', 0.1235), (\'Leg:BL:Bend_cerdo_1\', 0.1235), (\'Leg:BR:Bend_cerdo_1\', 0.1235))   # parte baja de cada pata y medio ancho de su pezuna\nPEZUNAS_REPOSO = 0.0048   # m: esquina mas baja de las pezunas sobre el root, en reposo (medido en el rig)\n\ndef _alza_pezunas(arm, root):\n    """Cuanto subir el root para que la esquina MAS BAJA de las pezunas (con la pose actual, medida de verdad) no se hunda en el bloque."""\n    import bpy\n    from mathutils import Vector\n    bpy.context.view_layer.update()\n    W = arm.matrix_world; zr = root.matrix_world.translation.z; zmin = None\n    for n, w in PEZUNAS:\n        pb = arm.pose.bones.get(n)\n        if pb is None:\n            continue\n        M = W @ pb.matrix\n        for sx in (-1, 1):\n            for sz in (-1, 1):\n                z = (M @ Vector((sx * w, pb.length, sz * w))).z\n                if zmin is None or z < zmin:\n                    zmin = z\n    return 0.0 if zmin is None else max(0.0, PEZUNAS_REPOSO - (zmin - zr))\n\ndef jump_phase(elapsed, timing):\n    prep, flight, land = timing\n    if elapsed <= prep:\n        return 0.16 * elapsed / prep\n    if elapsed <= prep + flight:\n        return 0.16 + 0.64 * (elapsed-prep) / flight\n    return min(1.0, 0.80 + 0.20 * (elapsed-prep-flight) / land)\n\n\ndef key_root(root, frame, p0, p1, phase, kind, rot):\n    dx, dy = p1[0]-p0[0], p1[1]-p0[1]\n    heading = math.degrees(math.atan2(-dx,dy)) if math.hypot(dx,dy)>1e-8 else rot[2]\n    delta = (heading-rot[2]+180)%360-180\n    root.rotation_mode = \'XYZ\'\n    root.location = jump_position(p0,p1,phase,kind)\n    root.rotation_euler = (math.radians(rot[0]),math.radians(rot[1]),\n                           math.radians(rot[2]+delta*jump_smooth(phase/0.16)))\n    root.keyframe_insert(data_path=\'location\',frame=frame)\n    root.keyframe_insert(data_path=\'rotation_euler\',frame=frame)\n\n\ndef action_curves(action):\n    if hasattr(action,\'fcurves\'):\n        return list(action.fcurves)\n    return [fc for layer in action.layers for strip in layer.strips\n            for bag in strip.channelbags for fc in bag.fcurves]\n\n\ndef key_pose(bones,frame,phase,kind,data):\n    for name,keys in data.items():\n        bone=bones.get(name)\n        if bone is None: continue\n        frames=sorted(keys)\n        sample=phase*frames[-1]\n        lo=max((f for f in frames if f<=sample),default=frames[0])\n        hi=min((f for f in frames if f>=sample),default=frames[-1])\n        w=(sample-lo)/(hi-lo) if hi!=lo else 0.0\n        bone.rotation_mode=\'XYZ\'\n        bone.rotation_euler=tuple(a+(b-a)*w for a,b in zip(keys[lo],keys[hi]))\n        bone.keyframe_insert(data_path=\'rotation_euler\',frame=frame)\n\ndef execute_animation(op=None, **kwargs):\n    import bpy\n    root=bpy.data.objects.get(ROOT_NAME)\n    arm=bpy.data.objects.get(ARM_NAME)\n    if root is None or arm is None:\n        raise RuntimeError(\'No se encontro el root o rig del personaje\')\n    for obj, suffix in ((root,\'root\'),(arm,\'arm\')):\n        obj.animation_data_create()\n        obj.animation_data.action=bpy.data.actions.new(f\'Slot_{SLOT:03d}_saltar_{KIND}_{suffix}\')\n    for frame in range(START_FRAME,END_FRAME+1):\n        phase=jump_phase(frame-START_FRAME,TIMING)\n        key_root(root,frame,P0,P1,phase,KIND,ROT)\n        key_pose(arm.pose.bones,frame,phase,KIND,POSE_DATA)\n        _alza=_alza_pezunas(arm,root)\n        if _alza>0.0:\n            root.location.z+=_alza\n            root.keyframe_insert(data_path=\'location\',frame=frame)\n    for obj,suffix in ((root,\'root\'),(arm,\'arm\')):\n        action=obj.animation_data.action\n        action[\'adaptive_jump\']=KIND\n        action[\'jump_ground_blend\']=max(1,min(TIMING[0],TIMING[2])//2)\n        for fc in action_curves(action):\n            for key in fc.keyframe_points:\n                key.interpolation=\'LINEAR\'\n        slot=obj.animation_data.action_slot\n        obj.animation_data.action=None\n        track=obj.animation_data.nla_tracks.new()\n        track.name=f\'Slot_{SLOT:03d}_{suffix}\'\n        strip=track.strips.new(action.name,START_FRAME,action)\n        if slot is not None and hasattr(strip,\'action_slot\'):\n            strip.action_slot=slot\n        strip.frame_end=END_FRAME\n        strip.extrapolation=\'NOTHING\' if suffix==\'arm\' else \'HOLD_FORWARD\'\n        strip.use_auto_blend=False\n    return True\n'


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

ROOT_NAME = 'cerdo_1'
ARM_NAME = "pig.arma_cerdo_1"
