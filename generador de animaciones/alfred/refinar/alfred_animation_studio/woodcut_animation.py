"""Cortar madera: motor compartido por preview y slots autocontenidos.

Sin bpy al importar: el generador y las pruebas de agrupamiento usan Python puro.
El hacha real conserva su padre; su agarre se hornea en espacio local del padre.
"""
import math
from pathlib import Path

WOODCUT_TYPES = ('cortar_madera_inferior', 'cortar_madera_intermedio', 'cortar_madera_superior')
WOODCUT_FRAMES = 144
WOODCUT_HITS = (42, 60, 78, 96)  # offsets, 24 fps
WOODCUT_HEIGHTS = (0.48, 1.15, 1.85)

# Hacha (stone_axe).
#  - ESPALDA (reposo, antes y despues de CADA coordenada de cortar madera): estos
#    valores son relativos al padre que el hacha ya tiene en la escena (el que
#    muestra Object > Relations); el motor NO le cambia el padre.
#  - MANO: transformada local respecto al bone Rightelbow_alfred (origen = cola
#    del bone, igual que un parentesco de tipo Bone). Mientras el hacha esta en la
#    mano se hornea cada frame la matriz equivalente a ser hija de ese bone.
# Cada coordenada/slot es independiente: empieza con el hacha en reposo, la saca,
# corta, la guarda y termina con el hacha otra vez en reposo.
# rot_deg es Euler XYZ en grados.
WOODCUT_AXE_BACK_LOCAL = {
    'loc':     (-0.060745, -0.096576, -0.18395),
    'rot_deg': (0.47821, -185.87, 90.003),
    'scale':   (0.6, 0.6, 0.6),
}
WOODCUT_AXE_HAND_LOCAL = {
    'loc':     (0.19847, -0.36658, -0.017937),
    'rot_deg': (0.0, 0.0, -46.0),
    'scale':   (0.7, 0.7, 0.7),
}
WOODCUT_AXE_PARENT_BONE = 'Rightelbow_alfred'  # bone que sostiene el hacha en la mano

# Guardar el hacha al terminar: el brazo vuelve a la pose "hacia la espalda",
# el hacha se suelta de la mano y queda en la espalda, y el brazo regresa a reposo.
WOODCUT_STOW_START = 106        # offsets 96+10: el brazo sale de 'ready' hacia la espalda
WOODCUT_STOW_REACH_END = 116    # llega a la pose de la espalda; aqui se entrega el hacha
WOODCUT_STOW_HOLD_END = 124     # se sostiene un instante en la espalda
WOODCUT_STOW_REST_END = 136     # regresa a la pose de reposo
WOODCUT_STOW_RELEASE = 5        # frames que tarda el hacha en pasar de la mano a la espalda


def _local_matrix(spec):
    from mathutils import Matrix, Euler, Vector
    eul = Euler(tuple(math.radians(a) for a in spec['rot_deg']), 'XYZ')
    return Matrix.LocRotScale(Vector(spec['loc']), eul.to_quaternion(), Vector(spec['scale']))


def _apply_axe_local(axe, spec):
    """Escribe location/rotation/scale exactos (Euler XYZ) en la malla del hacha."""
    axe.rotation_mode = 'XYZ'
    axe.location = spec['loc']
    axe.rotation_euler = tuple(math.radians(a) for a in spec['rot_deg'])
    axe.scale = spec['scale']


def _check_axe_rest_parent(axe, arm):
    """El padre de reposo del hacha se respeta; solo se rechaza el residuo de la
    version que la dejaba emparentada al bone de la mano (no es su reposo)."""
    if (axe.parent is arm and axe.parent_type == 'BONE'
            and axe.parent_bone == WOODCUT_AXE_PARENT_BONE):
        raise RuntimeError(
            'stone_axe esta emparentado a '+WOODCUT_AXE_PARENT_BONE+' (residuo de una '
            'version anterior). Restaura su padre de reposo (el de la espalda) y '
            'vuelve a generar.')


def _hand_parent_matrix(arm):
    """Matriz de mundo que un parentesco tipo Bone daria a un hijo de Rightelbow_alfred."""
    pb = arm.pose.bones[WOODCUT_AXE_PARENT_BONE]
    m = pb.matrix.copy()
    m.translation = pb.tail
    return arm.matrix_world @ m


# Gesto "brazo derecho hacia la espalda" -- MISMOS valores calibrados que
# PRE_THROW_REACH_BACK_POSE en operators_anim.py (sistema de Lanzar/
# Recoger/Mantener Objetos). Se duplican aqui (en vez de importar
# operators_anim.py) porque este modulo esta pensado para poder probarse
# sin bpy al importar (ver docstring del archivo); operators_anim.py si
# importa bpy a nivel de modulo. Si se retoca la pose alla, hay que
# actualizar esta copia tambien.
#
# Antes, "sacar el hacha" apuntaba la mano via IK analitico (_aim_arm) a
# un punto adivinado -- eso movia la mano en linea mas o menos recta
# hasta la espalda, sin la curva de hombro/codo del gesto ya calibrado.
# Ahora el brazo pasa literalmente por esta pose durante los primeros
# WOODCUT_REACH_DRAW frames (offset 0 -> WOODCUT_REACH_DRAW), se sostiene
# hasta WOODCUT_REACH_HOLD_END, y de ahi en mas retoma el IK de siempre
# (windup, golpes) partiendo exactamente de donde ese gesto deja la mano.
WOODCUT_REACH_BACK_POSE = {
    'RightUpArm_alfred': {
        'loc':     (0.006603, 0.096746, -0.086079),
        'rot_deg': (28.5284, 198.1061, 62.0369),
    },
    'Rightelbow_alfred': {
        'loc':     (1e-05, -2e-06, 1.2e-05),
        'rot_deg': (-16.873, 18.6165, -107.9791),
    },
}
WOODCUT_REACH_DRAW = 10       # offsets 0->10: ida hacia la pose "en la espalda"
WOODCUT_REACH_HOLD_END = 18   # offsets 10->18: se sostiene ahi (agarre del hacha)
WOODCUT_RETURN_END = 28       # offsets 18->28: regreso en espejo hacia el frente


def is_woodcut(value):
    return str(value).lower() in WOODCUT_TYPES


def group_woodcut_points(points, legacy, as_dict=False):
    """Una accion puntual consume UN punto, incluso el ultimo o el unico.

    El enlace hacia el siguiente punto sigue siendo locomocion normal. Los
    puntos de igual coordenada no crean una caminata artificial.
    """
    from types import SimpleNamespace
    pts = list(points)
    kind = lambda p: p.get('tipo_segmento', 'AUTO') if as_dict else getattr(p, 'tipo_segmento', 'AUTO')
    coords = lambda p: tuple(p['coordinates'][a] for a in 'xyz') if as_dict else tuple(p.coords)
    def neutral(p):
        if as_dict:
            return dict(p, tipo_segmento='AUTO', es_parada_dup=False)
        return SimpleNamespace(coords=p.coords, texture=p.texture, face_index=p.face_index,
                               tipo_segmento='AUTO', es_parada_dup=False)
    result, chunk = [], []
    for p in pts:
        if is_woodcut(kind(p)):
            if chunk:
                if len(chunk) == 1 and tuple(round(x,2) for x in coords(chunk[0])) == tuple(round(x,2) for x in coords(p)):
                    chunk = []
                else:
                    result.extend(legacy(chunk + [p]))
            result.append({'type': kind(p).lower(), 'points': [p]})
            chunk = [neutral(p)]
        else:
            # No repetir un enlace sin distancia despues de cortar.
            if len(chunk) == 1 and result and is_woodcut(result[-1]['type']) and tuple(round(x,2) for x in coords(chunk[0])) == tuple(round(x,2) for x in coords(p)):
                chunk = [p]
            else:
                chunk.append(p)
    if len(chunk) > 1:
        result.extend(legacy(chunk))
    return result


def _smooth(t):
    t = min(1.0, max(0.0, t))
    return t*t*(3-2*t)


def _sample(keys, frame):
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if frame <= b:
            t = _smooth((frame-a)/max(1,b-a))
            return tuple(x+(y-x)*t for x,y in zip(va,vb))
    return keys[-1][1]


# --- Golpe diagonal de hacha -------------------------------------------------
# Ciclo de 18 frames por golpe (24 fps):
#   hit-LEAD -> hit        : bajada DIAGONAL acelerada (arriba-derecha -> abajo-izquierda)
#   hit -> hit+REBOUND     : rebote corto al chocar con el tronco
#   hit+REBOUND -> siguiente hit-LEAD : recuperacion en ARCO (el codo sube primero)
# La trayectoria de ida y la de vuelta son distintas (elipse), asi que la
# mano nunca retrocede por la misma linea: no hay efecto "piston".
WOODCUT_SWING_LEAD = 6
WOODCUT_SWING_REBOUND = 2
WOODCUT_SWING_BULGE = (0.10, 0.10, 0.08)      # curvatura de la bajada
WOODCUT_RECOVER_BULGE = (0.14, -0.06, -0.14)  # curvatura de la subida


def _lerp3(a, b, t):
    return tuple(x+(y-x)*t for x, y in zip(a, b))


def _arc3(a, b, t, bulge):
    k = math.sin(math.pi*min(1.0, max(0.0, t)))
    return tuple(x+(y-x)*t+bz*k for x, y, bz in zip(a, b, bulge))


def _chop_points(height):
    """Puntos clave de la mano (espacio del Armature) segun la altura del corte."""
    peak = (.58, -.02, min(2.05, height+.78))   # arriba, a la derecha, ligeramente atras
    contact = (.16, .55, height+.12)            # abajo, cruzando hacia la izquierda, al frente
    rebound = (.21, .49, height+.19)
    return peak, contact, rebound


def _chop_position(offset, ready, height):
    """(posicion_mano, fase). fase 0=brazo arriba, 1=impacto. (None, 0) fuera del tramo de golpes."""
    hits = WOODCUT_HITS
    lead, reb = WOODCUT_SWING_LEAD, WOODCUT_SWING_REBOUND
    peak, contact, rebound = _chop_points(height)
    if offset < hits[0]-lead:
        t = _smooth((offset-WOODCUT_RETURN_END)/max(1, hits[0]-lead-WOODCUT_RETURN_END))
        return _arc3(ready, peak, t, (0, 0, 0)), 0.0
    for i, hit in enumerate(hits):
        if hit-lead <= offset <= hit:
            t = (offset-(hit-lead))/lead
            e = t*t*(0.35+0.65*t)          # arranca suave y llega con velocidad maxima
            return _arc3(peak, contact, e, WOODCUT_SWING_BULGE), e
        if hit < offset <= hit+reb:
            t = (offset-hit)/reb
            return _lerp3(contact, rebound, 1-(1-t)*(1-t)), 1-.35*t
        last = i == len(hits)-1
        recover_end = hit+10 if last else hits[i+1]-lead
        if hit+reb < offset <= recover_end:
            t = _smooth((offset-hit-reb)/max(1, recover_end-hit-reb))
            if last:
                return _lerp3(rebound, ready, t), .65*(1-t)
            return _arc3(rebound, peak, t, WOODCUT_RECOVER_BULGE), .65*(1-t)
    return None, 0.0


def _curves(obj):
    from bpy_extras.anim_utils import action_ensure_channelbag_for_slot
    ad = obj.animation_data
    if hasattr(ad.action, 'fcurves'):
        return ad.action.fcurves
    return action_ensure_channelbag_for_slot(ad.action, ad.action_slot).fcurves


def _new_action(obj, name):
    import bpy
    obj.animation_data_create()
    obj.animation_data.action = bpy.data.actions.new(name)
    return obj.animation_data.action


def _keyframe_default_blink(start, end):
    """Un parpadeo de 9 frames; ojos abiertos en el resto del corte.

    El motor se incrusta en slots autocontenidos, por eso no importa el addon.
    Misma cortina que eye_system.BLINK_SEQUENCE_BASE. Solo se usa al generar
    Capa 1: el rehorneado de props no debe pisar los intervalos del Paso 3.
    """
    import bpy
    closed_values = (0.0, .25, .50, .75, 1.0, 1.0, .75, .50, .25)
    blink_start = start + (end - start + 1 - len(closed_values)) // 2
    for name in ('ojo_izquierdo_alfred', 'ojo_derecho_alfred'):
        eye = bpy.data.objects.get(name)
        if eye is None or eye.type != 'MESH':
            continue
        if eye.data.shape_keys is None:
            eye.shape_key_add(name='Basis', from_mix=False)
        closed = eye.data.shape_keys.key_blocks.get('Closed')
        if closed is None:
            closed = eye.shape_key_add(name='Closed', from_mix=False)
            min_z = min(v.co.z for v in eye.data.vertices)
            for vertex in closed.data:
                vertex.co.z = min_z
        for frame in range(start, end + 1):
            offset = frame - blink_start
            value = closed_values[offset] if 0 <= offset < len(closed_values) else 0.0
            closed.value = value
            closed.keyframe_insert('value', frame=frame)
            eye.hide_viewport = eye.hide_render = value == 1.0
            eye.keyframe_insert('hide_viewport', frame=frame)
            eye.keyframe_insert('hide_render', frame=frame)
        # No interpolar un booleano ni permitir sobreoscilacion de la cortina.
        # Se conservan las expresiones y las claves de los segmentos vecinos.
        for owner, paths, interpolation in (
                (eye, ('hide_viewport', 'hide_render'), 'CONSTANT'),
                (eye.data.shape_keys, ('key_blocks["Closed"].value',), 'LINEAR')):
            for fc in _curves(owner):
                if fc.data_path in paths:
                    for kp in fc.keyframe_points:
                        if start <= kp.co.x <= end:
                            kp.interpolation = interpolation


def _nla(obj, slot, suffix, start, end, hold=False):
    ad = obj.animation_data
    action = ad.action
    action_slot = getattr(ad, 'action_slot', None)
    for fc in _curves(obj):
        for kp in fc.keyframe_points:
            kp.interpolation = 'CONSTANT' if fc.data_path.startswith('hide_') else 'LINEAR'
    ad.action = None
    name = f'Slot_{slot:03d}_{suffix}'
    for track in list(ad.nla_tracks):
        if track.name == name:
            ad.nla_tracks.remove(track)
    track = ad.nla_tracks.new()
    track.name = name
    strip = track.strips.new(action.name, start, action)
    if action_slot is not None:
        strip.action_slot = action_slot
    strip.frame_start, strip.frame_end = start, end
    strip.extrapolation = 'HOLD_FORWARD' if hold else 'NOTHING'
    strip.blend_type = 'REPLACE'
    strip.use_auto_blend = False
    return action


def _asset_path(config):
    import bpy
    candidates = [Path(config.get('wood_asset', ''))]
    for origin in (bpy.data.filepath, globals().get('__file__', '')):
        if origin:
            candidates.extend(p/'objetos/vanilla/oak_planks/oak_planks.blend' for p in Path(origin).resolve().parents)
    for p in candidates:
        if p.is_file() and p.suffix == '.blend':
            return p
    raise FileNotFoundError('No se encuentra objetos/vanilla/oak_planks/oak_planks.blend')


def _aim_arm(arm, target, weight=1.0):
    """IK analitico de dos segmentos; el agarre esta en la malla, no en
    la punta larga del bone auxiliar del antebrazo de Alfred."""
    import bpy
    from mathutils import Vector
    upper = arm.pose.bones['RightUpArm_alfred']
    lower = arm.pose.bones['Rightelbow_alfred']
    bpy.context.view_layer.update()
    shoulder = upper.head.copy()
    d = Vector(target)-shoulder
    l1, l2 = upper.length, lower.length*0.50
    distance = max(.02, min(d.length, l1+l2-.003))
    direction = d.normalized()
    pole = Vector((1, -.4, -.35))
    pole = (pole-direction*pole.dot(direction)).normalized()
    along = (l1*l1-l2*l2+distance*distance)/(2*distance)
    elbow = shoulder + direction*along + pole*math.sqrt(max(0,l1*l1-along*along))
    for bone, aim in ((upper, elbow), (lower, Vector(target))):
        bpy.context.view_layer.update()
        matrix = bone.matrix.copy()
        q = (bone.tail-bone.head).normalized().rotation_difference((aim-bone.head).normalized())
        matrix = q.to_matrix().to_4x4() @ matrix
        matrix.translation = bone.head
        old = bone.rotation_euler.to_quaternion()
        bone.matrix = matrix
        solved = bone.rotation_euler.to_quaternion()
        bone.rotation_euler = old.slerp(solved, weight).to_euler('XYZ', bone.rotation_euler)
    bpy.context.view_layer.update()
    return lower.head.lerp(lower.tail, .50)


def execute_woodcut(config, start_frame=None, end_frame=None, body=True):
    import bpy, json
    from mathutils import Vector, Matrix, Euler
    scene = bpy.context.scene
    root = bpy.data.objects.get(config.get('root_name','alfred'))
    arm = bpy.data.objects.get(config.get('armature_name','Armature'))
    axe = bpy.data.objects.get(config.get('axe_name','stone_axe'))
    if not root or not arm or arm.type != 'ARMATURE' or not axe:
        raise RuntimeError('Cortar madera requiere el Empty, Armature y stone_axe del personaje')
    for name in ('RightUpArm_alfred','Rightelbow_alfred','Spine1_alfred'):
        if name not in arm.pose.bones:
            raise RuntimeError('Rig incompatible: falta '+name)
    asset = _asset_path(config)  # validar antes de modificar animacion
    start = int(config['start_frame'] if start_frame is None else start_frame)
    end = int(start+WOODCUT_FRAMES-1 if end_frame is None else end_frame)
    if end-start < 10:
        raise ValueError('El segmento de cortar madera necesita al menos 11 frames')
    frame_at = lambda offset: start + (end-start)*offset/(WOODCUT_FRAMES-1)
    slot = int(config['slot'])
    variant = config['variant']
    height = WOODCUT_HEIGHTS[WOODCUT_TYPES.index(variant)]
    owner = f'{root.name}:{slot}'
    # Repetir el mismo slot reemplaza solo su propio drop.
    for obj in list(bpy.data.objects):
        if obj.get('_woodcut_owner') == owner:
            mesh = obj.data if obj.type == 'MESH' else None
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh and not mesh.users:
                bpy.data.meshes.remove(mesh)
    with bpy.data.libraries.load(str(asset), link=False) as (src, dst):
        if 'oak_planks' not in src.objects:
            raise ValueError('oak_planks.blend no contiene el objeto oak_planks')
        dst.objects = ['oak_planks']
    drop = dst.objects[0]
    # El .blend de la biblioteca referencia una ruta antigua de MCprep.
    # Resolver sus texturas hermanas y empaquetarlas en la escena resultante.
    for material in drop.data.materials:
        if material and material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image and not node.image.packed_file:
                    texture = asset.parent / Path(node.image.filepath.replace('\\','/')).name
                    if texture.is_file():
                        node.image.filepath = str(texture)
                        node.image.reload()
                        node.image.pack()
    drop.name = f'oak_planks_drop_{root.name}_{slot:03d}'
    drop['_woodcut_owner'] = owner
    bpy.context.scene.collection.objects.link(drop)
    drop.parent = None
    drop.animation_data_clear()
    drop.rotation_mode = 'XYZ'
    # Normalizar el bloque a un cubo pequeno (0.22 unidades).
    extent = max(max(v[i] for v in drop.bound_box)-min(v[i] for v in drop.bound_box) for i in range(3))
    drop_scale = .22/max(extent,1e-6)
    _new_action(drop, f'woodcut_{slot:03d}_drop')
    _check_axe_rest_parent(axe, arm)
    back_basis = _local_matrix(WOODCUT_AXE_BACK_LOCAL)
    hand_basis = _local_matrix(WOODCUT_AXE_HAND_LOCAL)
    axe['_woodcut_back_basis'] = json.dumps([list(r) for r in back_basis])
    _apply_axe_local(axe, WOODCUT_AXE_BACK_LOCAL)  # reposo fuera de la tira NLA = espalda
    _new_action(axe, f'woodcut_{slot:03d}_axe')
    axe.rotation_mode = 'XYZ'
    if body:
        _new_action(arm, f'woodcut_{slot:03d}_arm')
        _new_action(root, f'woodcut_{slot:03d}_root')
    root.rotation_mode = 'XYZ'
    position = Vector(config['position'])
    rotation = Euler(tuple(math.radians(a) for a in config['root_rot']), 'XYZ')
    basis = Matrix.LocRotScale(position, rotation.to_quaternion(), root.scale)
    previous = scene.frame_current
    grip_local = Vector((-.25,-.32,0))
    rest = {'RightUpArm_alfred':(90,0,0),'LeftUpArm_alfred':(90,0,0),
            'Rightelbow_alfred':(0,0,-47.15),'Leftelbow_alfred':(0,0,19.16),
            'Rightknee_alfred':(-12,0,0)}
    # La mano alcanza primero el mango en la espalda, luego prepara el golpe.
    ready = (.40,.24,min(1.65,height+.43))
    contact = (.27,.53,height+.12)
    windup = (.46,.04,min(2.02,height+.73))
    if body:
        # FK "en seco" de WOODCUT_REACH_BACK_POSE: da el punto exacto al
        # que llega la mano con ESA pose (no un punto adivinado), para que
        # el tramo de IK que sigue (offset > WOODCUT_RETURN_END) no salte
        # al retomar el recorrido normal de 'keys'.
        _ru0 = arm.pose.bones['RightUpArm_alfred']
        _re0 = arm.pose.bones['Rightelbow_alfred']
        _ru0.rotation_mode = _re0.rotation_mode = 'XYZ'
        _ru0.rotation_euler = tuple(math.radians(a) for a in WOODCUT_REACH_BACK_POSE['RightUpArm_alfred']['rot_deg'])
        _ru0.location = WOODCUT_REACH_BACK_POSE['RightUpArm_alfred']['loc']
        _re0.rotation_euler = tuple(math.radians(a) for a in WOODCUT_REACH_BACK_POSE['Rightelbow_alfred']['rot_deg'])
        _re0.location = WOODCUT_REACH_BACK_POSE['Rightelbow_alfred']['loc']
        bpy.context.view_layer.update()
        reach_hand_point = tuple(_re0.head.lerp(_re0.tail, .5))
        # Y la MISMA rotacion que el IK generico calcularia para 'ready'
        # (el punto donde arranca el molinete antes del primer golpe).
        # Asi el regreso en espejo (18->WOODCUT_RETURN_END) puede terminar
        # exactamente en esa rotacion -- sin choque de "swivel" de codo al
        # entregarle el control a _aim_arm justo despues.
        _aim_arm(arm, ready, 1.0)
        ready_rot = {
            'RightUpArm_alfred': tuple(_ru0.rotation_euler),
            'Rightelbow_alfred': tuple(_re0.rotation_euler),
        }
    else:
        reach_hand_point = (.23,-.24,1.27)
        ready_rot = None
    keys = [(0,(.38,.02,.94)),(WOODCUT_REACH_DRAW,reach_hand_point),(WOODCUT_REACH_HOLD_END,reach_hand_point),(WOODCUT_RETURN_END,ready)]
    keys.append((WOODCUT_HITS[-1]+10, ready))  # tras el ultimo golpe: vuelve a 'ready'
    for frame in range(start,end+1):
        offset=(frame-start)*143/max(1,end-start)
        scene.frame_set(frame)
        if body:
            root.location=position
            root.rotation_euler=rotation
            for bone in arm.pose.bones:
                bone.rotation_mode='XYZ'
                bone.rotation_euler=tuple(math.radians(a) for a in rest.get(bone.name,(0,0,0)))
            activity=_smooth(offset/26)*(1-_smooth((offset-108)/27))
            chop_pos, pulse = _chop_position(offset, ready, height)  # pulse = fase del golpe (0..1)
            bend=(18 if height<.7 else (7 if height<1.5 else -7))*activity
            for name in ('Spine_alfred','Spine1_alfred','Spine2_alfred'):
                b=arm.pose.bones.get(name)
                if b: b.rotation_euler=(math.radians(-bend/3-2*pulse),0,math.radians(3*activity-6*pulse))
            neck=arm.pose.bones.get('Neck_alfred')
            if neck: neck.rotation_euler.x=math.radians((18 if height<.7 else -18 if height>1.5 else 0)*activity)
            left=arm.pose.bones.get('LeftUpArm_alfred')
            if left: left.rotation_euler.y=math.radians(-12*activity-6*pulse)
            if offset <= WOODCUT_REACH_HOLD_END:
                # Sacar el hacha: MISMO gesto calibrado "hacia la espalda"
                # del sistema de Lanzar/Recoger/Mantener Objetos, no el IK
                # generico -- ida (0->WOODCUT_REACH_DRAW) y sostenido
                # (->WOODCUT_REACH_HOLD_END) igual que apply_pre_throw_reach_back.
                _t = _smooth(offset/WOODCUT_REACH_DRAW)
                _ru = arm.pose.bones['RightUpArm_alfred']
                _re = arm.pose.bones['Rightelbow_alfred']
                for _pb, _name in ((_ru,'RightUpArm_alfred'), (_re,'Rightelbow_alfred')):
                    _rest_rot = tuple(math.radians(a) for a in rest[_name])
                    _back_rot = tuple(math.radians(a) for a in WOODCUT_REACH_BACK_POSE[_name]['rot_deg'])
                    _pb.rotation_euler = tuple(r0+(r1-r0)*_t for r0,r1 in zip(_rest_rot,_back_rot))
                    _pb.location = tuple(l*_t for l in WOODCUT_REACH_BACK_POSE[_name]['loc'])
                bpy.context.view_layer.update()
                hand = _re.head.lerp(_re.tail, .5)
            elif offset <= WOODCUT_RETURN_END:
                # Regreso en espejo: el mismo gesto pero invertido, de la
                # pose "en la espalda" hacia la posicion inicial del molinete
                # (ready_rot), en vez de soltarle el brazo al IK generico de
                # una (eso es lo que causaba el salto/teletransporte al
                # frente). ready_rot es la MISMA rotacion que calculara
                # _aim_arm mas abajo para offset > WOODCUT_RETURN_END, asi
                # que al entregarle el control no hay choque de "swivel".
                _t = _smooth((offset-WOODCUT_REACH_HOLD_END)/(WOODCUT_RETURN_END-WOODCUT_REACH_HOLD_END))
                _ru = arm.pose.bones['RightUpArm_alfred']
                _re = arm.pose.bones['Rightelbow_alfred']
                for _pb, _name in ((_ru,'RightUpArm_alfred'), (_re,'Rightelbow_alfred')):
                    _back_rot = tuple(math.radians(a) for a in WOODCUT_REACH_BACK_POSE[_name]['rot_deg'])
                    _pb.rotation_euler = tuple(r0+(r1-r0)*_t for r0,r1 in zip(_back_rot,ready_rot[_name]))
                    _pb.location = tuple(l*(1-_t) for l in WOODCUT_REACH_BACK_POSE[_name]['loc'])
                bpy.context.view_layer.update()
                hand = _re.head.lerp(_re.tail, .5)
            elif offset <= WOODCUT_STOW_START:
                hand=_aim_arm(arm,chop_pos if chop_pos is not None else _sample(keys,offset),
                              _smooth(offset/7))
            elif offset <= WOODCUT_STOW_HOLD_END:
                # Guardar el hacha: el brazo hace de nuevo el gesto calibrado
                # "hacia la espalda" (desde 'ready' hasta la pose de la espalda)
                # y se sostiene ahi mientras el hacha pasa de la mano a la espalda.
                _t = _smooth((offset-WOODCUT_STOW_START)/(WOODCUT_STOW_REACH_END-WOODCUT_STOW_START))
                _ru = arm.pose.bones['RightUpArm_alfred']
                _re = arm.pose.bones['Rightelbow_alfred']
                for _pb, _name in ((_ru,'RightUpArm_alfred'), (_re,'Rightelbow_alfred')):
                    _back_rot = tuple(math.radians(a) for a in WOODCUT_REACH_BACK_POSE[_name]['rot_deg'])
                    _pb.rotation_euler = tuple(r0+(r1-r0)*_t for r0,r1 in zip(ready_rot[_name],_back_rot))
                    _pb.location = tuple(l*_t for l in WOODCUT_REACH_BACK_POSE[_name]['loc'])
                bpy.context.view_layer.update()
                hand = _re.head.lerp(_re.tail, .5)
            elif offset <= WOODCUT_STOW_REST_END:
                # Con las manos vacias el brazo regresa de la espalda a reposo.
                _t = _smooth((offset-WOODCUT_STOW_HOLD_END)/(WOODCUT_STOW_REST_END-WOODCUT_STOW_HOLD_END))
                _ru = arm.pose.bones['RightUpArm_alfred']
                _re = arm.pose.bones['Rightelbow_alfred']
                for _pb, _name in ((_ru,'RightUpArm_alfred'), (_re,'Rightelbow_alfred')):
                    _back_rot = tuple(math.radians(a) for a in WOODCUT_REACH_BACK_POSE[_name]['rot_deg'])
                    _rest_rot = tuple(math.radians(a) for a in rest[_name])
                    _pb.rotation_euler = tuple(r0+(r1-r0)*_t for r0,r1 in zip(_back_rot,_rest_rot))
                    _pb.location = tuple(l*(1-_t) for l in WOODCUT_REACH_BACK_POSE[_name]['loc'])
                bpy.context.view_layer.update()
                hand = _re.head.lerp(_re.tail, .5)
            else:
                _re = arm.pose.bones['Rightelbow_alfred']
                _re.location = (0,0,0)
                arm.pose.bones['RightUpArm_alfred'].location = (0,0,0)
                bpy.context.view_layer.update()
                hand = _re.head.lerp(_re.tail, .5)
            for bone in arm.pose.bones:
                bone.keyframe_insert('rotation_euler',frame=frame)
                if bone.name in ('RightUpArm_alfred','Rightelbow_alfred'):
                    # Estos dos bones tambien reciben 'location' durante el
                    # gesto de sacar/regresar el hacha (WOODCUT_REACH_BACK_POSE);
                    # sin esto el desplazamiento se pierde al hornear.
                    bone.keyframe_insert('location',frame=frame)
            root.keyframe_insert('location',frame=frame)
            root.keyframe_insert('rotation_euler',frame=frame)
        else:
            bpy.context.view_layer.update()
            lower=arm.pose.bones['Rightelbow_alfred']
            hand=lower.head.lerp(lower.tail,.5)
        bpy.context.view_layer.update()
        # Espalda -> mano (al sacar el hacha) y mano -> espalda (al guardarlo).
        transfer=_smooth((offset-13)/6)*(1-_smooth((offset-WOODCUT_STOW_REACH_END)/WOODCUT_STOW_RELEASE))
        _apply_axe_local(axe, WOODCUT_AXE_BACK_LOCAL)   # reposo exacto en este frame
        if transfer > 1e-6:
            bpy.context.view_layer.update()
            back_world=axe.matrix_world.copy()
            parent_space=back_world@back_basis.inverted()   # incluye su padre y su inversa
            hand_world=_hand_parent_matrix(arm)@hand_basis  # = hijo del bone Rightelbow_alfred
            if transfer >= 1-1e-6:
                world=hand_world
            else:
                bp,bq,bs=back_world.decompose()
                hp,hq,hs=hand_world.decompose()
                world=Matrix.LocRotScale(bp.lerp(hp,transfer),bq.slerp(hq,transfer),bs.lerp(hs,transfer))
            axe.matrix_basis=parent_space.inverted()@world
        for channel in ('location','rotation_euler','scale'):
            axe.keyframe_insert(channel,frame=frame)
        # Drop: desprendimiento, caida, rebote, flotacion y absorcion.
        if offset < 96:
            local=Vector((.27,.93,height))
            shrink=1
        elif offset < 109:
            t=(offset-96)/13
            local=Vector((.27+.09*t,.93-.18*t,height*(1-t)+.23*t+.23*4*t*(1-t)))
            shrink=1
        elif offset < 124:
            t=offset-109
            local=Vector((.36,.75,.25+.045*math.sin(t*math.pi/7)))
            shrink=1
        else:
            t=_smooth((offset-124)/12)
            local=Vector((.36*(1-t),.75*(1-t),.25+.70*t))
            shrink=max(.001,1-t)
        drop.location=basis@local
        drop.scale=(drop_scale*shrink,)*3
        drop.rotation_euler=(.10,offset*.015,offset*.035)
        drop.hide_viewport=drop.hide_render=not (96<=offset<136)
        for channel in ('location','scale','rotation_euler','hide_viewport','hide_render'):
            drop.keyframe_insert(channel,frame=frame)
    if body:
        _nla(arm,slot,'arm',start,end)
        _nla(root,slot,'root',start,end,True)
        _keyframe_default_blink(start, end)
    # NLA restablece los canales animados a sus valores por defecto cuando
    # ninguna tira contribuye: asignar el reposo a mano no lo conserva.
    # Mantener la ultima pose (hacha guardada) durante la locomocion siguiente.
    _nla(axe,slot,'woodcut_axe',start,end,hold=True)
    # Drop necesita estar oculto tambien antes/despues de su intervalo.
    for fc in _curves(drop):
        for kp in fc.keyframe_points:
            kp.interpolation='CONSTANT' if fc.data_path.startswith('hide_') else 'LINEAR'
    _apply_axe_local(axe, WOODCUT_AXE_BACK_LOCAL)  # reposo tras la animacion
    configs=json.loads(root.get('_woodcut_configs','{}'))
    configs[str(slot)]=dict(config,start_frame=start,end_frame=end)
    root['_woodcut_configs']=json.dumps(configs)
    scene.frame_set(previous)
    return True


def regenerate_woodcut_props(scene, start, end):
    """Rehornear el agarre tras editar/concatenar poses del Paso 3."""
    import bpy, json
    root=bpy.data.objects.get('alfred')
    if root:
        for config in json.loads(root.get('_woodcut_configs','{}')).values():
            fs=config['start_frame']; fe=config.get('end_frame',fs+WOODCUT_FRAMES-1)
            if fs<=end and fe>=start:
                execute_woodcut(config,fs,fe,body=False)


def clear_woodcut_preview(root):
    import bpy, json
    from mathutils import Matrix
    for obj in list(bpy.data.objects):
        if str(obj.get('_woodcut_owner','')).startswith(root.name+':'):
            mesh=obj.data if obj.type=='MESH' else None
            bpy.data.objects.remove(obj,do_unlink=True)
            if mesh and not mesh.users:
                bpy.data.meshes.remove(mesh)
    axe=bpy.data.objects.get('stone_axe')
    if axe and axe.animation_data:
        for track in list(axe.animation_data.nla_tracks):
            if track.name.endswith('_woodcut_axe'):
                axe.animation_data.nla_tracks.remove(track)
        if axe.animation_data.action and axe.animation_data.action.name.startswith('woodcut_'):
            axe.animation_data.action=None
        _apply_axe_local(axe, WOODCUT_AXE_BACK_LOCAL)
    root['_woodcut_configs']='{}'


def bake_woodcut_base(scene, first, last):
    """Dar al Paso 3 un respaldo evaluado de Capa 1, incluido su NLA.
    Se ejecuta solo si el recorrido contiene cortar madera.
    """
    import bpy, json
    root=bpy.data.objects.get('alfred')
    if not root or not json.loads(root.get('_woodcut_configs','{}')):
        return
    arm=bpy.data.objects.get('Armature')
    previous=scene.frame_current
    samples=[]
    for f in range(first,last+1):
        scene.frame_set(f)
        samples.append((f,tuple(root.location),tuple(root.rotation_euler),
                        {b.name:(tuple(b.location),tuple(b.rotation_euler),tuple(b.scale)) for b in arm.pose.bones}))
    for obj in (root,arm):
        _new_action(obj,'woodcut_base_'+obj.name)
        for track in obj.animation_data.nla_tracks:
            track.mute=True
    for f,loc,rot,bones in samples:
        root.location=loc;root.rotation_euler=rot
        root.keyframe_insert('location',frame=f);root.keyframe_insert('rotation_euler',frame=f)
        for name,(bl,br,bs) in bones.items():
            bone=arm.pose.bones[name]
            bone.location=bl;bone.rotation_euler=br;bone.scale=bs
            for channel in ('location','rotation_euler','scale'):
                bone.keyframe_insert(channel,frame=f)
    for obj in (root,arm):
        for fc in _curves(obj):
            for kp in fc.keyframe_points: kp.interpolation='LINEAR'
    scene.alfst.anim_generated=True
    scene.alfst.end_frame_gen=last
    scene.frame_set(previous)


def build_export_appendix(scene, first, last):
    """Conservar hacha y drop tambien en Exportar .py del Paso 3."""
    import bpy, json
    root=bpy.data.objects.get('alfred')
    configs=list(json.loads(root.get('_woodcut_configs','{}')).values()) if root else []
    configs=[c for c in configs if c['start_frame']<=last and c.get('end_frame',c['start_frame']+143)>=first]
    if not configs:
        return ''
    source=Path(__file__).read_text(encoding='utf-8')
    return ("\n# Hacha y recoleccion: mismo motor que el recorrido.\n"
            "_woodcut_body_execute = execute_animation\n"
            "_woodcut_runtime = {}\nexec("+repr(source)+", _woodcut_runtime)\n"
            "_woodcut_export_configs = "+repr(configs)+"\n"
            "def execute_animation(player_parts=None, start_frame=None, end_frame=None):\n"
            "    result = _woodcut_body_execute(player_parts, start_frame, end_frame)\n"
            "    if result is False: return result\n"
            "    first = START_FRAME if start_frame is None else start_frame\n"
            "    last = first + TOTAL_FRAMES - 1 if end_frame is None else end_frame\n"
            "    ratio = (last-first)/max(1,TOTAL_FRAMES-1)\n"
            "    for config in _woodcut_export_configs:\n"
            f"        fs = round(first + (config['start_frame']-{first})*ratio)\n"
            f"        fe = round(first + (config.get('end_frame',config['start_frame']+143)-{first})*ratio)\n"
            "        _woodcut_runtime['execute_woodcut'](config,fs,fe,body=False)\n"
            "    return result\n")
