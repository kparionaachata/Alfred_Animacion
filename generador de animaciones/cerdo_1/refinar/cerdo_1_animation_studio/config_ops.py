# -*- coding: utf-8 -*-
"""
config_ops.py — Cerdo_1 Animation Studio v1.8
Operadores de configuracion de sesion: SaveConfig, LoadConfig, OpenConfigFolder.
Serializacion/deserializacion completa incluyendo eye_expr y organic.
"""
import bpy, json, os
from datetime import datetime
from bpy.types import Operator
from bpy.props import StringProperty
from .pose_utils import open_folder
from .properties import load_historia_json, get_key_points
try:
    from . import guion_v2 as _gv2          # guion 2.0 (secciones nuevas opcionales); si falta, todo sigue como antes
except Exception:
    _gv2 = None

def _calcular_frames_por_parada(data):
    """
    NUEVO (pedido de Kebyn): calcula, para cada tramo 'parada' del
    recorrido, la SUMA de frames de las poses de accion que caen dentro de ese tramo, leyendo unicamente lo que
    ya trae el configuracion.json. Reemplaza el valor editable a mano
    (antes: pc.paradas_frames[i].frames por defecto = pc.frames_parada,
    60, desconectado de las poses reales) por un numero que representa
    fielmente la configuracion cargada.

    FIX 2026-07-10 (pedido de Kebyn: poses solapando saltar_subir/
    saltar_bajar): la version anterior usaba un cursor GLOBAL continuo
    (cursor = start_frame; cursor += duration por cada pose, sin
    excepcion) para traducir la secuencia plana de action_poses
    a frames absolutos. Eso ignoraba que el
    timeline real de paso1_path.segmentos_recorrido tiene huecos que NO
    llevan pose (saltar_subir, saltar_bajar, y los tramos "caminar" con
    intervalo_caminata_normal=True) — cerdo_1_story_generator.py NUNCA
    asigna poses a esos huecos (ver _distribuir_poses_en_segmentos), asi
    que la secuencia plana de action_poses solo cubre, en orden, los
    tramos "caminar"/"parada". Un cursor que avanza sin saltarse esos
    huecos se desincroniza del timeline real apenas se cruza el primer
    salto, y ese desfase se acumula: el sintoma mas visible era
    pc.paradas_frames[i].frames mal calculado, que luego usa
    path_recorder.py para generar la duracion REAL de cada tramo
    "parada" en Blender — una parada con duracion incorrecta corre todo
    lo que viene despues, incluido el siguiente salto, y ahi es donde
    las poses terminan pisando la animacion base de saltar_subir/
    saltar_bajar.

    Ahora, en vez de un cursor global, se recorren SOLO los tramos
    "caminar"/"parada" (sin intervalo_caminata_normal) de
    segmentos_recorrido, en orden, y el cursor se reinicia al
    frame_start real de cada tramo, consumiendo el pool de poses
    (action_poses, mismo orden de siempre)
    limitando lo consumido al presupuesto de frames de ese tramo
    (seg_end - seg_start + 1) — exactamente igual que ya hace
    _distribuir_poses_en_segmentos() en cerdo_1_story_generator.py al
    generar la config. Con esto los intervalos calculados quedan en
    frames absolutos reales, nunca solapan un salto, y las paradas
    reciben su duracion correcta.

    Devuelve una lista de ints (uno por tramo 'parada', en el mismo
    orden en que aparecen en segmentos_recorrido) o None si la
    configuracion no trae los datos necesarios (paso1_path.
    segmentos_recorrido y/o action_poses) para
    calcularlo — en ese caso el llamador debe conservar el
    comportamiento anterior (paradas_frames explicito o default).
    """
    segmentos = data.get("paso1_path", {}).get("segmentos_recorrido")
    if not segmentos:
        return None

    paradas_segs = [s for s in segmentos if s.get("tipo") == "parada"]
    if not paradas_segs:
        return None

    if "action_poses" not in data:
        return None

    # Pool secuencial de poses de accion, mismo orden que arma
    # cerdo_1_story_generator.py: action_poses.
    # FIX 2026-07-10 (bug "no reconoce el recorrido" / "Agrega al menos
    # 1 punto" al cargar una config valida): pi/pf (pose_inicio/pose_fin)
    # se usaban mas abajo sin haber sido definidos nunca -- el NameError
    # resultante lo atrapaba el try/except de load_config() (mas arriba,
    # en apply_config_dict) y abortaba en silencio TODA la restauracion
    # de cerdo_1_path, path_points incluido, dejando el panel de Paso 1
    # con 0 puntos aunque el JSON trajera el recorrido completo.
    #
    # FIX 2026-07-10 (b) (reportado por Kebyn: "pose de parado
    # harcodeada bloqueando las poses de la configuracion"): pose_inicio/
    # pose_fin son el esquema VIEJO, ya eliminado de Cerdo_1StudioSettings
    # y Cerdo_1AnimSegment (ver SECUENCIA_PIPELINE.md). Algunos JSON
    # generados por versiones previas del pipeline aun traen estos
    # campos a nivel raiz con una pose "parado" fija (parado.json). Se
    # Ya NO se lee ni se agrega pose_inicio/pose_fin al pool: sumar sus
    # duraciones insertaba una pose ajena a la configuracion al
    # principio/final de la secuencia y corria en una posicion todas las
    # poses reales de action_poses respecto a los tramos caminar/parada
    # a los que en verdad pertenecen. El pool sale unicamente de
    # action_poses (unica fuente de verdad actual). Si un JSON viejo aun
    # trae esos campos, simplemente se ignoran.
    pool = []  # duraciones en orden

    for ap in data.get("action_poses", []):
        pool.append(int(ap.get("duration", 0)))

    # Tramos que SI reciben poses de este pool, en el mismo orden y con
    # el mismo criterio que segmentos_caminar en
    # cerdo_1_story_generator.py._construir_config: "caminar"/"parada",
    # excluyendo los huecos de caminata_normal (y, por construccion,
    # excluyendo tambien saltar_subir/saltar_bajar).
    segmentos_con_pose = [
        s for s in segmentos
        if s.get("tipo") in ("caminar", "parada") and not s.get("intervalo_caminata_normal")
    ]

    intervalos = []  # (frame_start, frame_end, duration) en frames absolutos
    idx_pool = 0
    for seg in segmentos_con_pose:
        seg_start = seg.get("frame_start", 0)
        seg_end   = seg.get("frame_end", 0)
        budget    = seg_end - seg_start + 1
        cursor    = seg_start
        consumido = 0
        while idx_pool < len(pool) and consumido + pool[idx_pool] <= budget:
            dur = pool[idx_pool]
            intervalos.append((cursor, cursor + dur - 1, dur))
            cursor += dur
            consumido += dur
            idx_pool += 1

    sumas = []
    for seg in paradas_segs:
        seg_start = seg.get("frame_start", 0)
        seg_end   = seg.get("frame_end", 0)
        total = 0
        for iv_start, iv_end, dur in intervalos:
            # Se considera "dentro" de la parada si el intervalo de la
            # pose se solapa con el rango de frames del tramo.
            if iv_start <= seg_end and iv_end >= seg_start:
                total += dur
        sumas.append(total)

    return sumas


def _get_key_point_coordinates(st):
    """Lee las coordenadas reales del key_point seleccionado (root_pos_key_point)
    desde historia_cerdo_1.json y las devuelve como dict para embeber en el JSON guardado.
    """
    try:
        historia = load_historia_json(st.historia_json)
        kps = get_key_points(historia)
        kp_idx = int(st.root_pos_key_point)
        kp = next((k for k in kps if k.get("index") == kp_idx), None)
        if kp:
            return {
                "index":      kp.get("index"),
                "coordinates": kp.get("coordinates", {"x": 0, "y": 0, "z": 0}),
                "texture":    kp.get("texture", ""),
                "face_index": kp.get("face_index", ""),
            }
    except Exception:
        pass
    return {}


def _resolver_tipo_segmento_auto(pts_list, idx):
    """Resuelve el movimiento real de un punto marcado como 'AUTO' comparando
    su Z contra la del punto anterior. Mismo criterio que _detect_move() en
    path_recorder.py, _detectar_movimiento_recorrido() en
    cerdo_1_story_generator.py y detect_movement_type() en
    generate_slots_cerdo_1.py -- los 3 deben coincidir si esto se modifica.

    Devuelve: "caminar", "saltar_subir", "saltar_bajar" o "parada"
    (coordenadas identicas al punto anterior). El primer punto del recorrido
    no tiene punto anterior, asi que se reporta como "caminar" (es el punto
    de partida, no un tramo de movimiento).

    FIX (Kebyn, 2026-08-23): redondeo a 4 decimales antes de comparar --
    mismo fix y mismo motivo que en _detect_move() de path_recorder.py
    (ruido de punto flotante del raycast de seleccion de faces hacia que
    una diagonal de Z constante se detectara como salto).

    FIX (Kebyn, 2026-08-23) v2: 4 decimales resulto insuficiente para
    ruido geometrico real de la malla del escenario (no solo del
    raycast) -- se baja a 2 decimales, misma precision que el panel le
    muestra al usuario. Ademas, coordenadas identicas ya NO resuelven
    como "parada" aca -- esta funcion solo se invoca para puntos que NO
    estan marcados manualmente como PARADA (ver el caller mas abajo,
    que ya filtra ese caso), asi que una coordenada repetida en AUTO
    ahora resuelve como "caminar" (en el lugar, sin desplazarse) en vez
    de "parada". Ver docstring de detect_movement_type()
    (generate_slots_cerdo_1.py) y de _detect_move() (path_recorder.py)
    para el detalle -- las 4 copias de este criterio deben coincidir.
    """
    if idx == 0:
        return "caminar"
    p0 = pts_list[idx - 1]
    p1 = pts_list[idx]
    x0, y0, z0 = p0.coords[0], p0.coords[1], p0.coords[2]
    x1, y1, z1 = p1.coords[0], p1.coords[1], p1.coords[2]
    x0, y0, z0 = round(x0, 2), round(y0, 2), round(z0, 2)
    x1, y1, z1 = round(x1, 2), round(y1, 2), round(z1, 2)
    if x0 == x1 and y0 == y1 and z0 == z1:
        return "caminar"
    if z1 > z0:
        return "saltar_subir"
    elif z1 < z0:
        return "saltar_bajar"
    else:
        return "caminar"


def _serialize_configuracion(st):
    """
    Serializa toda la configuracion activa del trabajo (secuencia, poses,
    interpolaciones, posiciones, rotaciones, ajustes de timeline, etc.)
    en un diccionario listo para guardar como JSON.
    NO incluye keyframes de animacion acabada: eso es el .py exportado.
    """
    # Poses de accion
    action_poses_data = []
    for item in st.action_poses:
        action_poses_data.append({
            "pose_name":  item.pose_name,
            "json_file":  item.json_file,
            "pose_index": item.pose_index,
            "duration":   item.duration,
            "rot_x": item.rot_x,
            "rot_y": item.rot_y,
            "rot_z": item.rot_z,
            "pos_x": item.pos_x,
            "pos_y": item.pos_y,
            "pos_z": item.pos_z,
            "interp_type": item.interp_type,
        })

    # Filtros organicos
    org = st.organic
    organic_data = {
        "enabled":                   org.enabled,
        "breathing_enabled":         org.breathing_enabled,
        "breathing_amplitude":       org.breathing_amplitude,
        "breathing_speed":           org.breathing_speed,
        "breathing_phase":           org.breathing_phase,
        "head_sway_enabled":         org.head_sway_enabled,
        "head_sway_amplitude":       org.head_sway_amplitude,
        "head_sway_speed":           org.head_sway_speed,
        "head_sway_seed":            org.head_sway_seed,
        "weight_shift_enabled":      org.weight_shift_enabled,
        "weight_shift_amplitude":    org.weight_shift_amplitude,
        "weight_shift_speed":        org.weight_shift_speed,
        "root_noise_enabled":        org.root_noise_enabled,
        "root_noise_strength":       org.root_noise_strength,
        "root_noise_frequency":      org.root_noise_frequency,
        "root_noise_seed":           org.root_noise_seed,
        "secondary_motion_enabled":  org.secondary_motion_enabled,
        "secondary_motion_lag":      org.secondary_motion_lag,
        "secondary_motion_damping":  org.secondary_motion_damping,
        "smooth_curves_enabled":     org.smooth_curves_enabled,
        "smooth_passes":             org.smooth_passes,
        "smooth_factor":             org.smooth_factor,
        "micro_scale_enabled":       org.micro_scale_enabled,
        "micro_scale_amplitude":     org.micro_scale_amplitude,
        "shoulder_noise_enabled":    org.shoulder_noise_enabled,
        "shoulder_noise_amplitude":  org.shoulder_noise_amplitude,
        "shoulder_noise_speed":      org.shoulder_noise_speed,
        "shoulder_noise_seed":       org.shoulder_noise_seed,
    }

    # Expresiones de ojos
    eye_s = st.eye_expr
    eye_data = {
        "enabled":              eye_s.enabled,
        "intensity_feliz":      eye_s.intensity_feliz,
        "intensity_triste":     eye_s.intensity_triste,
        "intensity_enojado":    eye_s.intensity_enojado,
        "intensity_sospecha":   eye_s.intensity_sospecha,
        "curve_mode":           eye_s.curve_mode,
        "affect_zone":          eye_s.affect_zone,
        "swap_axes":            eye_s.swap_axes,
        "invert_vertical":      eye_s.invert_vertical,
        "invert_horizontal":    eye_s.invert_horizontal,
        "subdivide_cuts":       eye_s.subdivide_cuts,
        "active_expression":    eye_s.active_expression,
        "expression_value":     eye_s.expression_value,
        "blink_enabled":        eye_s.blink_enabled,
        "blink_count":          eye_s.blink_count,
        "blink_duration":       eye_s.blink_duration,
    }

    # ── Paso 1 y 2: cerdo_1_path (recorrido, personaje, slots, frames) ──
    paso1_data = {}
    try:
        pc = bpy.context.scene.cerdo_1_path
        path_points_data = []
        pts_list = list(pc.path_points)
        for idx, pt in enumerate(pts_list):
            tipo_seg_raw = getattr(pt, "tipo_segmento", "AUTO")
            # CORREGIDO (Kebyn, 2026-08-02): "AUTO" es el nombre del enum de
            # Blender (significa "que el sistema decida"), pero al exportar
            # el JSON no dice nada util -- el usuario no puede saber si ese
            # tramo termino siendo caminar, saltar_subir o saltar_bajar.
            # Aqui se resuelve el movimiento REAL comparando la Z de este
            # punto contra la del punto anterior, con el mismo criterio que
            # _detect_move() en path_recorder.py, _detectar_movimiento_
            # recorrido() en cerdo_1_story_generator.py y
            # detect_movement_type() en generate_slots_cerdo_1.py (los 3
            # deben coincidir). Un override manual (PARADA o cualquiera de
            # los overrides de accion puntual) se respeta siempre, sin
            # recalcular.
            #
            # FIX (2026-08-24, reportado por Kebyn: "Paso 1 no se guarda o
            # no se importa bien"): esta rama solo comparaba contra
            # "PARADA" -- cualquier otro override manual (COLOCAR_ANTORCHA,
            # GOLPE_ESTOMAGO_1, COLOCAR_MESA_CRAFTEO, LEVANTARSE_1/2,
            # ARRODILLARSE_1, CONVERSAR_1) caia en el else y se pisaba con
            # el resultado de _resolver_tipo_segmento_auto() (que SOLO
            # devuelve caminar/saltar_subir/saltar_bajar/parada) -- el
            # override se perdia ya en el .json exportado, mucho antes de
            # llegar a importarlo. Ahora cualquier valor que no sea "AUTO"
            # se conserva tal cual (en minuscula, para el campo legible
            # "tipo_segmento"); solo "AUTO" dispara la resolucion
            # geometrica. Ademas se guarda "tipo_segmento_raw" con el
            # identificador EXACTO del enum de Blender (mayusculas), que es
            # lo que _aplicar_configuracion() usa para restaurar sin
            # depender de una lista fija de overrides conocidos (a prueba
            # de overrides nuevos que se agreguen a futuro).
            if tipo_seg_raw == "AUTO":
                tipo_seg = _resolver_tipo_segmento_auto(pts_list, idx)
            else:
                tipo_seg = tipo_seg_raw.lower()
            pt_data = {
                "coords":       list(pt.coords),
                "texture":      pt.texture,
                "face_index":   pt.face_index,
                "tipo_segmento": tipo_seg,
                # Identificador exacto del enum (fuente de verdad para la
                # importacion) -- "AUTO" tambien se guarda explicitamente
                # para distinguirlo de un JSON viejo que no trae esta clave.
                "tipo_segmento_raw": tipo_seg_raw,
            }
            # "parada_frames_punto" SOLO se guarda cuando el punto esta
            # realmente marcado como "PARADA" -- si se incluyera siempre
            # (incluso en caminar/salto/otros overrides) el JSON da la
            # falsa impresion de que todas las coordenadas son paradas, y
            # esos otros overrides no usan este valor (tienen su propia
            # cantidad de frames fija en generate_slots_cerdo_1.py).
            if tipo_seg_raw == "PARADA":
                pt_data["parada_frames_punto"] = getattr(pt, "parada_frames_punto", 24)
                # NUEVO (Kebyn, 2026-09-13): animacion .py importada para
                # este punto de parada (ver CERDO_1PathPoint.parada_anim_file
                # / CERDO_1PR_OT_ImportParadaAnim en path_recorder.py). Igual
                # que parada_frames_punto, solo tiene sentido guardarlo
                # cuando el punto es realmente una "PARADA"; y solo se
                # guarda si el usuario efectivamente asocio un archivo (no
                # se guarda una clave vacia para no ensuciar el JSON).
                _anim_file_raw = getattr(pt, "parada_anim_file", "") or ""
                if _anim_file_raw:
                    # NUEVO (Kebyn, 2026-09-13, fix rutas): se normaliza a
                    # ruta ABSOLUTA (bpy.path.abspath) antes de guardarla en
                    # el JSON -- mismo criterio que blend_filepath mas abajo
                    # -- para que la ruta siga siendo valida al importar el
                    # config desde otro .blend/otra carpeta relativa, en vez
                    # de arrastrar un "//" relativo al .blend de origen.
                    pt_data["parada_anim_file"] = bpy.path.abspath(_anim_file_raw)
                # NUEVO (Kebyn, 2026-09-13): orientacion (heading) guardada
                # a mano para este punto de parada -- ver
                # CERDO_1PathPoint.parada_rot_saved/parada_rot_z y
                # CERDO_1PR_OT_SaveParadaRot (path_recorder.py). Igual que
                # parada_anim_file, solo se guarda si el usuario realmente
                # la fijo (no se ensucia el JSON con paradas sin orientacion
                # guardada).
                if getattr(pt, "parada_rot_saved", False):
                    pt_data["parada_rot_saved"] = True
                    pt_data["parada_rot_z"] = getattr(pt, "parada_rot_z", 0.0)
            # NUEVO ("crear pared NxN bloques"): mismo criterio que
            # "parada_frames_punto" de arriba -- estos 3 campos solo tienen
            # sentido cuando el punto esta realmente marcado como
            # "CREAR_PARED_NXN" (ver CERDO_1PathPoint.pared_bloque_blend_path
            # /pared_filas/pared_columnas, path_recorder.py).
            if tipo_seg_raw == "CREAR_PARED_NXN":
                pt_data["pared_filas"] = getattr(pt, "pared_filas", 2)
                pt_data["pared_columnas"] = getattr(pt, "pared_columnas", 2)
                # NUEVO (Kebyn, "elegir cuantos frames dura toda la
                # animacion de crear pared"): 0 = automatico, mismo
                # criterio de "solo se guarda si aplica" que el resto de
                # este bloque -- ver pared_total_frames (path_recorder.py).
                pt_data["pared_total_frames"] = getattr(pt, "pared_total_frames", 0)
                _pared_blend_raw = getattr(pt, "pared_bloque_blend_path", "") or ""
                if _pared_blend_raw:
                    # Misma normalizacion a ruta ABSOLUTA que
                    # parada_anim_file/blend_filepath (ver comentario arriba).
                    pt_data["pared_bloque_blend_path"] = bpy.path.abspath(_pared_blend_raw)
            path_points_data.append(pt_data)
        paso1_data = {
            "blend_filepath":    bpy.path.abspath(pc.blend_filepath) if pc.blend_filepath else "",
            "slot_inicio":       pc.slot_inicio,
            "frame_inicio":      pc.frame_inicio,
            "frame_fin_manual":  pc.frame_fin_manual,
            "frames_por_bloque": pc.frames_por_bloque,
            "frames_parada":     pc.frames_parada,
            "paradas_frames":    [item.frames for item in pc.paradas_frames],
            # NUEVO (fix Kebyn, 2026-08-04): estilo de caminata por tramo
            # ("Normal"/"Lento"/"Herido"/"Rapido"/"Correr") no se estaba
            # guardando -- al reimportar la configuracion siempre volvia
            # a "Caminar Normal" en todos los tramos, aunque el panel
            # mostrara otro estilo al momento de exportar. walk_style es
            # el default global para tramos nuevos; walk_styles es la
            # coleccion real (una entrada por tramo 'caminar', mismo
            # orden que el recorrido) que decide la animacion generada.
            "walk_style":        pc.walk_style,
            "walk_styles":       [
                {"style": item.style, "applied_style": item.applied_style}
                for item in pc.walk_styles
            ],
            "root_rot_x":        pc.root_rot_x,
            "root_rot_y":        pc.root_rot_y,
            "root_rot_z":        pc.root_rot_z,
            "output_dir":        bpy.path.abspath(pc.output_dir) if pc.output_dir else "",
            "path_points":       path_points_data,
        }
    except Exception as e:
        print(f"[Cerdo_1] advertencia: no se pudo serializar cerdo_1_path: {e}")

    # ── Estimacion de slots (Paso 2) ──
    # NUEVO 2026-08-02 (pedido de Kebyn): antes esta informacion (la
    # misma que muestra el panel "Estimacion de slots") solo vivia en la
    # UI mientras Blender estaba abierto -- el configuracion.json
    # exportado no la incluia, asi que se perdia apenas se guardaba la
    # sesion. Se calcula con la MISMA funcion que usa panels.py
    # (path_recorder.calcular_estimacion_slots), para que nunca
    # diverjan entre lo que se ve en pantalla y lo que se exporta.
    try:
        from .path_recorder import calcular_estimacion_slots
        _slots_data, _fuente_slots = calcular_estimacion_slots(st.id_data)
    except Exception as e:
        print(f"[Cerdo_1] advertencia: no se pudo calcular estimacion_slots: {e}")
        _slots_data, _fuente_slots = [], None
    estimacion_slots_data = {
        "fuente": _fuente_slots,  # "paso3_segmentos" | "estimacion_geometrica" | null
        "slots": _slots_data,
    }

    cfg = {
        "version": "2.0",
        "timestamp": datetime.now().isoformat(),
        "description": "Configuracion de trabajo Cerdo_1 Animation Studio",
        # ── Paso 1 y 2 (cerdo_1_path) ──
        "paso1_path": paso1_data,
        # ── Estimacion de slots (Paso 2, informativo — ver nota arriba) ──
        "estimacion_slots": estimacion_slots_data,
        # ── Rutas ──
        "poses_dir":    bpy.path.abspath(st.poses_dir),
        "anim_dir":     bpy.path.abspath(st.anim_dir),
        "historia_json": bpy.path.abspath(st.historia_json),
        "config_dir":   bpy.path.abspath(st.config_dir),
        # ── Armature ──
        "armature_name": st.armature_name,
        # ── Timeline ──
        "start_frame": st.start_frame,
        "fps":         st.fps,
        "entry_ratio": st.entry_ratio,
        "exit_ratio":  st.exit_ratio,
        # ── Poses de accion ──
        "action_poses": action_poses_data,
        # ── Exportacion ──
        "export_slot_number": st.export_slot_number,
        "export_name":        st.export_name,
        "export_type":        st.export_type,
        "export_desc":        st.export_desc,
        "selected_key_point": st.selected_key_point,
        "root_pos_key_point": st.root_pos_key_point,
        "key_point_coordinates": _get_key_point_coordinates(st),
        # ── Filtros organicos ──
        "organic": organic_data,
        # ── Expresiones de ojos (legacy) ──
        "eye_expr": eye_data,
        # ── Secuencia de ojos completa (inicio/intermedios/fin + parpadeo) ──
        "eye_sequence": _serialize_eye_config(st),
        # ── Oscilaciones de bones personalizadas ──
        "bone_oscillations": _serialize_bone_oscillations(st),
        # ── Importacion de Objetos (escudo, espada, etc.) ──
        "object_imports": _serialize_object_imports(st),
        # ── Segmentos del Paso 3 (frames, poses, filtros, throws incluidos) ──
        "cerdo_1_segs": _serialize_cerdo_1_segs(st),
        # ── Lanzar / Recoger Objetos (por segmento) — mantenido por compatibilidad ──
        "segments_throw": _serialize_throw_settings(st),
    }
    if _gv2 is not None:                       # conserva las secciones del guion 2.0 (audio, camara, exactos...) que el panel no edita
        try:
            _gv2.fusionar_en(cfg, _gv2.recordado(bpy.context.scene))
        except Exception as e:
            print('[guion_v2] no se pudieron conservar las secciones 2.0:', e)
    return cfg


def _aplicar_configuracion(st, data):
    """
    Aplica el diccionario deserializado del JSON de configuracion
    sobre el Cerdo_1StudioSettings activo.
    Omite silenciosamente claves que no existan (compatibilidad hacia atras).
    """
    if _gv2 is not None:                       # recuerda las secciones del guion 2.0 para no perderlas al volver a guardar
        try:
            _gv2.recordar(data, bpy.context.scene)
        except Exception as e:
            print('[guion_v2] no se pudieron recordar las secciones 2.0:', e)
    def _get(d, *keys, default=None):
        cur = d
        for k in keys:
            if not isinstance(cur, dict):
                return default
            cur = cur.get(k, default)
        return cur

    # ── Paso 1 y 2: cerdo_1_path (recorrido, personaje, slots, frames) ──
    paso1_data = data.get("paso1_path", {})
    if paso1_data:
        try:
            import bpy as _bpy
            pc = _bpy.context.scene.cerdo_1_path

            if paso1_data.get("blend_filepath"):
                pc.blend_filepath    = paso1_data["blend_filepath"]
            if "slot_inicio"       in paso1_data: pc.slot_inicio       = paso1_data["slot_inicio"]
            if "frame_inicio"      in paso1_data: pc.frame_inicio      = paso1_data["frame_inicio"]
            if "frame_fin_manual"  in paso1_data: pc.frame_fin_manual  = paso1_data["frame_fin_manual"]
            if "frames_por_bloque" in paso1_data: pc.frames_por_bloque = paso1_data["frames_por_bloque"]
            # CORRECCION 2026-07-09 (pedido de Kebyn): "al cargar la
            # configuracion .json ahora dice 60 frames por parada" — antes
            # frames_parada no se serializaba/deserializaba aca, asi que
            # cargar una config vieja (o una nueva sin este campo) dejaba
            # el panel siempre en el default de la propiedad (60), sin
            # importar que valor se habia usado realmente al generarla.
            # Ahora se restaura desde el archivo si esta presente; si el
            # JSON es de antes de este fix y no trae la clave, se deja
            # pc.frames_parada como esta (no se pisa con un default).
            if "frames_parada" in paso1_data: pc.frames_parada = paso1_data["frames_parada"]

            # Frames por-parada individuales: YA NO es un valor editable
            # a mano. Se calcula como la SUMA de frames de las poses
            # (action_poses) que caen dentro de
            # cada tramo "parada", leyendo unicamente lo que trae este
            # configuracion.json (ver _calcular_frames_por_parada). Solo
            # si la config no trae los datos necesarios para calcularlo
            # (configs viejas, anteriores a este fix) se cae de vuelta a
            # "paradas_frames" explicito si existe, o al default via
            # sync_paradas_frames() mas abajo.
            _frames_calc = _calcular_frames_por_parada(data)
            if _frames_calc is not None:
                pc.paradas_frames.clear()
                for _f in _frames_calc:
                    _item = pc.paradas_frames.add()
                    _item.frames = int(_f)
            elif "paradas_frames" in paso1_data:
                pc.paradas_frames.clear()
                for _f in paso1_data["paradas_frames"]:
                    _item = pc.paradas_frames.add()
                    _item.frames = int(_f)
            if "root_rot_x"        in paso1_data: pc.root_rot_x        = paso1_data["root_rot_x"]
            if "root_rot_y"        in paso1_data: pc.root_rot_y        = paso1_data["root_rot_y"]
            if "root_rot_z"        in paso1_data: pc.root_rot_z        = paso1_data["root_rot_z"]
            if paso1_data.get("output_dir"):
                pc.output_dir = paso1_data["output_dir"]

            # Restaurar puntos del recorrido
            pts_data = paso1_data.get("path_points", [])
            if pts_data:
                pc.path_points.clear()
                for ptd in pts_data:
                    pt            = pc.path_points.add()
                    pt.coords     = tuple(ptd.get("coords", [0.0, 0.0, 0.0]))
                    pt.texture    = ptd.get("texture", "")
                    pt.face_index = ptd.get("face_index", "")
                    # NUEVO (Kebyn, 2026-08-02): tipo de segmento editable por
                    # punto. Compatibilidad con configs viejos que guardaban
                    # el booleano "is_parada" en vez de "tipo_segmento", y con
                    # configs viejas que guardaban el enum crudo de Blender
                    # ("AUTO"/"PARADA") en vez del movimiento legible
                    # ("caminar"/"saltar_subir"/"saltar_bajar"/"parada").
                    #
                    # FIX (2026-08-24, reportado por Kebyn: "Paso 1 no se
                    # guarda o no se importa bien"): esta rama solo
                    # reconocia "PARADA"/"parada" -- cualquier otro override
                    # de accion puntual (COLOCAR_ANTORCHA, GOLPE_ESTOMAGO_1,
                    # COLOCAR_MESA_CRAFTEO, LEVANTARSE_1/2, ARRODILLARSE_1,
                    # CONVERSAR_1) se forzaba de vuelta a "AUTO" al
                    # importar, aunque el .json trajera el override
                    # correcto. Ahora se usa "tipo_segmento_raw" (guardado
                    # por _serialize_configuracion desde 2026-08-24) como
                    # fuente de verdad: es el identificador EXACTO del enum
                    # de Blender, valido para CUALQUIER override presente o
                    # futuro sin necesidad de listarlos aca uno por uno. Se
                    # valida contra los identificadores reales del enum
                    # (bl_rna) antes de asignar, por si el .json viene de
                    # una version del addon con overrides que esta version
                    # todavia no conoce -- en ese caso se cae a "AUTO" en
                    # vez de fallar. Si el .json es viejo y no trae
                    # "tipo_segmento_raw", se conserva el comportamiento
                    # anterior (solo reconoce PARADA/parada/is_parada).
                    # FIX (2026-09-29, Blender 5.2): "tipo_segmento" es un enum
                    # DINAMICO; bl_rna.properties[...].enum_items devuelve []
                    # (no hay instancia para el callback), asi que la lista de
                    # validos salia vacia y TODO override caia a "AUTO" (se
                    # perdian las PARADA y las acciones puntuales al importar).
                    # Ahora se intenta asignar directamente: Blender rechaza un
                    # identificador desconocido con TypeError y ahi si se cae a
                    # "AUTO", que era la intencion original.
                    if "tipo_segmento_raw" in ptd:
                        _traw = ptd.get("tipo_segmento_raw", "AUTO")
                        try:
                            pt.tipo_segmento = _traw
                        except TypeError:
                            pt.tipo_segmento = "AUTO"
                    elif "tipo_segmento" in ptd:
                        _tseg = ptd.get("tipo_segmento", "AUTO")
                        pt.tipo_segmento = "PARADA" if _tseg in ("PARADA", "parada") else "AUTO"
                    elif ptd.get("is_parada"):
                        pt.tipo_segmento = "PARADA"
                    pt.parada_frames_punto = ptd.get("parada_frames_punto", 24)
                    # NUEVO (Kebyn, 2026-09-13): restaurar la animacion .py
                    # importada asociada a este punto de parada, si el JSON
                    # la trae (ver _serialize_configuracion mas arriba). Si
                    # no viene la clave (JSON viejo, o el punto no tenia
                    # animacion asociada), se deja vacio -- comportamiento
                    # de "parada" normal.
                    pt.parada_anim_file = ptd.get("parada_anim_file", "")
                    # NUEVO (Kebyn, 2026-09-13): restaurar la orientacion
                    # (heading) guardada a mano para este punto de parada,
                    # si el JSON la trae -- ver _serialize_configuracion
                    # mas arriba. Si no viene la clave (JSON viejo, o el
                    # punto no tenia orientacion guardada), se deja en False
                    # -- comportamiento de heading automatico normal.
                    pt.parada_rot_saved = bool(ptd.get("parada_rot_saved", False))
                    pt.parada_rot_z = float(ptd.get("parada_rot_z", 0.0))
                    # NUEVO ("crear pared NxN bloques"): restaurar filas/
                    # columnas y la ruta del .blend del bloque, si el JSON
                    # las trae -- mismo criterio que parada_anim_file de
                    # arriba (default seguro si el JSON es viejo o el punto
                    # no era "CREAR_PARED_NXN").
                    pt.pared_filas = int(ptd.get("pared_filas", 2))
                    pt.pared_columnas = int(ptd.get("pared_columnas", 2))
                    pt.pared_bloque_blend_path = ptd.get("pared_bloque_blend_path", "")
                    # NUEVO (Kebyn, "elegir cuantos frames dura toda la
                    # animacion de crear pared"): 0 = automatico si el
                    # JSON es viejo o no lo trae.
                    pt.pared_total_frames = int(ptd.get("pared_total_frames", 0))

            # NUEVO 2026-07-09: re-sincronizar paradas_frames con el
            # recorrido recien cargado. Si el JSON ya traia
            # "paradas_frames" explicito, esto es un no-op (coincide);
            # si el JSON es viejo y no lo trae, o el recorrido cargado
            # tiene un numero de paradas distinto al de la coleccion
            # restaurada, esto ajusta el tamaño usando pc.frames_parada
            # como default — nunca deja el panel mostrando una coleccion
            # desincronizada con el recorrido real.
            from .path_recorder import sync_paradas_frames as _sync_pf
            _sync_pf(pc)

            # Restaurar estilo de caminata (fix Kebyn, 2026-08-04): antes
            # no se leia nada aca, asi que sync_walk_styles() de mas abajo
            # siempre recreaba walk_styles desde cero usando pc.walk_style
            # (default "NORMAL"), perdiendo cualquier "Caminar Lento" /
            # "Caminar Herido" / etc. que el usuario hubiera elegido antes
            # de exportar. Se restaura ANTES de sincronizar para que, si
            # la cantidad de tramos 'caminar' coincide con el recorrido
            # recien cargado (caso normal), sync_walk_styles no tenga
            # nada que ajustar y los estilos queden exactamente como se
            # guardaron.
            if "walk_style" in paso1_data:
                pc.walk_style = paso1_data["walk_style"]
            if "walk_styles" in paso1_data:
                pc.walk_styles.clear()
                for _ws in paso1_data["walk_styles"]:
                    _item = pc.walk_styles.add()
                    _item.style = _ws.get("style", "NORMAL")
                    _item.applied_style = _ws.get("applied_style", "")

            from .path_recorder import sync_walk_styles as _sync_ws
            _sync_ws(pc)
        except Exception as e:
            print(f"[Cerdo_1] advertencia: no se pudo restaurar cerdo_1_path: {e}")

    # Rutas (solo si el usuario quiere recuperarlas; no sobreescribir si estan vacias)
    if _get(data, "poses_dir"):
        st.poses_dir     = data["poses_dir"]
    if _get(data, "anim_dir"):
        st.anim_dir      = data["anim_dir"]
    if _get(data, "historia_json"):
        st.historia_json = data["historia_json"]
    if _get(data, "config_dir"):
        st.config_dir    = data["config_dir"]

    # Armature
    if _get(data, "armature_name"):
        st.armature_name = data["armature_name"]

    # Timeline
    if "start_frame" in data: st.start_frame = data["start_frame"]
    if "fps"         in data: st.fps         = data["fps"]
    if "entry_ratio" in data: st.entry_ratio = data["entry_ratio"]
    if "exit_ratio"  in data: st.exit_ratio  = data["exit_ratio"]

    # Poses de accion
    st.action_poses.clear()
    for ap in data.get("action_poses", []):
        item             = st.action_poses.add()
        item.pose_name   = ap.get("pose_name",  "")
        item.json_file   = ap.get("json_file",  "")
        item.pose_index  = ap.get("pose_index", 0)
        item.duration    = ap.get("duration",   20)
        item.rot_x       = ap.get("rot_x",      0.0)
        item.rot_y       = ap.get("rot_y",      0.0)
        item.rot_z       = ap.get("rot_z",      0.0)
        item.pos_x       = ap.get("pos_x",      0.0)
        item.pos_y       = ap.get("pos_y",      0.0)
        item.pos_z       = ap.get("pos_z",      0.0)
        item.interp_type = ap.get("interp_type","SMOOTH")

    # Exportacion
    if "export_slot_number" in data: st.export_slot_number = data["export_slot_number"]
    if "export_name"        in data: st.export_name        = data["export_name"]
    if "export_type"        in data: st.export_type        = data["export_type"]
    if "export_desc"        in data: st.export_desc        = data["export_desc"]
    if "selected_key_point" in data: st.selected_key_point = data["selected_key_point"]
    if "root_pos_key_point" in data:
        try:
            st.root_pos_key_point = str(data["root_pos_key_point"])
        except Exception:
            pass

    # Filtros organicos
    org_data = data.get("organic", {})
    if org_data:
        org = st.organic
        for key, val in org_data.items():
            try:
                setattr(org, key, val)
            except Exception:
                pass

    # Expresiones de ojos (legacy)
    eye_data_load = data.get("eye_expr", {})
    if eye_data_load:
        eye_s = st.eye_expr
        for key, val in eye_data_load.items():
            try:
                setattr(eye_s, key, val)
            except Exception:
                pass

    # Secuencia de ojos completa (inicio/intermedios/fin + parpadeo)
    eye_seq = data.get("eye_sequence", {})
    if eye_seq:
        # _aplicar_eye_config ya recrea shape keys internamente si hay shape_keys_setup
        _aplicar_eye_config(st, eye_seq)

        # Ejecutar CONCATENAR_2 automaticamente para insertar los keyframes de ojos
        # (equivalente al flujo manual: Crear Shape Keys → CONCATENAR_2)
        try:
            result = bpy.ops.cerdo_1_st.concatenate_2()
            if result == {"FINISHED"}:
                print("[Cerdo_1] CONCATENAR_2 ejecutado automaticamente al importar configuracion")
            else:
                print("[Cerdo_1] ADVERTENCIA: CONCATENAR_2 no pudo ejecutarse automaticamente — ejecutalo manualmente")
        except Exception as e:
            print(f"[Cerdo_1] No se pudo ejecutar CONCATENAR_2 automaticamente: {e}")

    # ── Oscilaciones de bones ──────────────────────────────────────────────
    bone_osc_data = data.get("bone_oscillations", {})
    if bone_osc_data:
        _aplicar_bone_oscillations(st, bone_osc_data)

    # ── Importacion de Objetos (escudo, espada, etc.) ───────────────────────
    obj_imports_data = data.get("object_imports", {})
    if obj_imports_data:
        _aplicar_object_imports(st, obj_imports_data)

    # ── Segmentos del Paso 3 (frames, poses, filtros, throws incluidos) ──────
    # Primero intentar con la clave nueva "cerdo_1_segs" (version >= 2.0).
    # Si no existe, caer en la clave legacy "segments_throw" para JSONs antiguos.
    if "cerdo_1_segs" in data:
        segs_data = data.get("cerdo_1_segs", [])
        if segs_data:
            try:
                _aplicar_cerdo_1_segs(st, segs_data)
            except Exception as _e_segs:
                print(f"[Cerdo_1] advertencia cerdo_1_segs: {_e_segs}")
                import traceback; traceback.print_exc()
        else:
            # FIX (Kebyn, 2026-08-02): la clave "cerdo_1_segs" SI viene en el
            # JSON pero vacia -- esta configuracion explicitamente no tiene
            # segmentos del Paso 3 todavia (recorrido recien grabado, sin
            # dividir aun). Antes esta rama no hacia nada y dejaba
            # sobreviviendo cualquier segmento viejo que ya estuviera en la
            # escena de Blender (de una sesion/config anterior), asi que el
            # panel "Estimacion de segmentos" mostraba una mezcla de
            # segmentos obsoletos con el recorrido nuevo recien cargado
            # (ej. el primer segmento con una duracion vieja que no
            # corresponde al recorrido de este archivo). Limpiar aqui deja
            # la escena consistente con lo que el JSON realmente describe:
            # cero segmentos, listo para "Dividir segmentos" desde cero.
            try:
                scene = st.id_data
                scene.cerdo_1_segs.segments.clear()
            except Exception as _e_clear:
                print(f"[Cerdo_1] advertencia al limpiar cerdo_1_segs: {_e_clear}")
    else:
        # Compatibilidad con JSONs viejos: solo restaurar los throws
        throw_data = data.get("segments_throw", [])
        if throw_data:
            try:
                _aplicar_throw_settings(st, throw_data)
            except Exception as _e_throw:
                print(f"[Cerdo_1] advertencia throw_settings (legacy): {_e_throw}")


def _serialize_cerdo_1_segs(st):
    """
    Serializa todos los segmentos del Paso 3 (cerdo_1_segs.segments),
    incluyendo poses, filtros de bones y throws (Lanzar/Recoger).
    """
    result = []
    try:
        scene = st.id_data
        segs  = scene.cerdo_1_segs.segments
    except Exception as e:
        print(f"[Cerdo_1] ERROR _serialize_cerdo_1_segs: no se pudo acceder a "
              f"scene.cerdo_1_segs.segments ({e}). LOS SEGMENTOS NO SE GUARDARON.")
        return result

    for seg in segs:
        # Slots de accion del segmento
        action_poses_data = []
        for ap in seg.action_poses:
            action_poses_data.append({
                "json_file":   ap.json_file,
                "pose_label":  ap.pose_label,
                "pose_name":   ap.pose_name,
                "duration":    ap.duration,
                "entry_ratio": round(ap.entry_ratio, 3),
                "exit_ratio":  round(ap.exit_ratio, 3),
                "interp_type": ap.interp_type,
                "rot_x": round(ap.rot_x, 4), "rot_y": round(ap.rot_y, 4), "rot_z": round(ap.rot_z, 4),
                "pos_x": round(ap.pos_x, 4), "pos_y": round(ap.pos_y, 4), "pos_z": round(ap.pos_z, 4),
                "manual_start":    bool(ap.manual_start),
                "frame_abs_start": int(ap.frame_abs_start),
            })

        # Throws del segmento
        th = seg.throws
        throw_items = []
        for item in th.items:
            wps = [{"label": wp.label, "x": round(wp.x,4), "y": round(wp.y,4),
                    "z": round(wp.z,4), "easing": wp.easing, "enabled": wp.enabled}
                   for wp in item.waypoints]
            throw_items.append({
                "enabled":            item.enabled,
                "label":              item.label,
                # uid interno (Kebyn + Claude, 2026-09-01 ter): identifica
                # este item de forma estable para el barrido de objetos
                # huerfanos en run_throws_for_segments(). Ver
                # Cerdo_1ThrowItem.uid en properties.py.
                "uid":                item.uid,
                "mode":               item.mode,
                "blend_path":         item.blend_path,
                "object_folder":      item.object_folder,
                "blend_filename":     item.blend_filename,
                "object_name":        item.object_name,
                "levels_up":          item.levels_up,
                "frame_start":        item.frame_start,
                "frame_end":          item.frame_end,
                "parent_armature":    item.parent_armature,
                "parent_bone":        item.parent_bone,
                "loc_x": round(item.loc_x,4), "loc_y": round(item.loc_y,4), "loc_z": round(item.loc_z,4),
                "rot_x": round(item.rot_x,4), "rot_y": round(item.rot_y,4), "rot_z": round(item.rot_z,4),
                "scale_uniform":      round(item.scale_uniform, 3),
                "target_object":      item.target_object,
                "target_armature":    item.target_armature,
                "target_bone":        item.target_bone,
                "dest_x": round(item.dest_x,4), "dest_y": round(item.dest_y,4), "dest_z": round(item.dest_z,4),
                "easing_global":      item.easing_global,
                "spin_during_flight": item.spin_during_flight,
                "spin_turns":         round(item.spin_turns, 2),
                "transition_in":            item.transition_in,
                "transition_in_duration":   item.transition_in_duration,
                "transition_out":           item.transition_out,
                "reach_back_duration_in":   item.reach_back_duration_in,
                "reach_back_enabled_out":   item.reach_back_enabled_out,
                "reach_back_duration_out":  item.reach_back_duration_out,
                "transition_out_duration":  item.transition_out_duration,
                "waypoints":          wps,
            })

        # Invisibilidad de Malla del segmento (debajo de Lanzar/Recoger/
        # Mantener -- mismo criterio de serializacion que throw_items arriba).
        hm = seg.hide_mesh
        hide_mesh_items = []
        for hitem in hm.items:
            hide_mesh_items.append({
                "enabled":     hitem.enabled,
                "label":       hitem.label,
                "uid":         hitem.uid,
                "mesh_object": hitem.mesh_object,
                "frame_start": hitem.frame_start,
                "frame_end":   hitem.frame_end,
            })

        result.append({
            "label":       seg.label,
            "frame_start": seg.frame_start,
            "frame_end":   seg.frame_end,
            # Foto del Paso 2 (ver Cerdo_1AnimSegment.frame_start_planned,
            # properties.py) -- se guarda aparte de frame_start/frame_end
            # para que la "Estimacion de segmentos" del Paso 2 no cambie
            # sola al recargar una config con poses ya cargadas.
            "frame_start_planned": seg.frame_start_planned,
            "frame_end_planned":   seg.frame_end_planned,
            "single_coord_mode": seg.single_coord_mode,
            "enabled":     seg.enabled,
            "seg_action_name": seg.seg_action_name,
            # Slots de accion
            "action_poses": action_poses_data,
            # Config
            "fps":         seg.fps,
            "entry_ratio": round(seg.entry_ratio, 3),
            "exit_ratio":  round(seg.exit_ratio, 3),
            "export_slot_number": seg.export_slot_number,
            "export_type":        seg.export_type,
            "export_desc":        seg.export_desc,
            "blend_in_frames":    seg.blend_in_frames,
            "blend_out_frames":   seg.blend_out_frames,
            # Grupos afectados
            "affect_body":      seg.affect_body,
            "affect_left_arm":  seg.affect_left_arm,
            "affect_right_arm": seg.affect_right_arm,
            "affect_left_leg":  seg.affect_left_leg,
            "affect_right_leg": seg.affect_right_leg,
            "affect_root":      seg.affect_root,
            "affect_shield":    seg.affect_shield,
            "affect_spear":     seg.affect_spear,
            # Filtros de bones
            "filter_show":         seg.filter_show,
            "filter_main_bone":    seg.filter_main_bone,
            "filter_hips":         seg.filter_hips,
            "filter_body":         seg.filter_body,
            "filter_spine":        seg.filter_spine,
            "filter_spine1":       seg.filter_spine1,
            "filter_spine2":       seg.filter_spine2,
            "filter_neck":         seg.filter_neck,
            "filter_face":         seg.filter_face,
            "filter_right_arm":    seg.filter_right_arm,
            "filter_right_elbow":  seg.filter_right_elbow,
            "filter_left_arm":     seg.filter_left_arm,
            "filter_left_elbow":   seg.filter_left_elbow,
            "filter_right_leg":    seg.filter_right_leg,
            "filter_right_knee":   seg.filter_right_knee,
            "filter_left_leg":     seg.filter_left_leg,
            "filter_left_knee":    seg.filter_left_knee,
            "filter_no_bone_01":   seg.filter_no_bone_01,
            "filter_no_bone_02":   seg.filter_no_bone_02,
            "filter_no_bone_03":   seg.filter_no_bone_03,
            "filter_no_bone_04":   seg.filter_no_bone_04,
            "filter_no_bone_05":   seg.filter_no_bone_05,
            "filter_no_bone_06":   seg.filter_no_bone_06,
            "filter_no_bone_07":   seg.filter_no_bone_07,
            "filter_no_bone_08":   seg.filter_no_bone_08,
            # Bloqueador de bones: intervalos de frames por bone
            "bone_blocks": [
                {
                    "bone_key": entry.bone_key,
                    "intervals": [
                        {
                            "frame_start": iv.frame_start,
                            "frame_end":   iv.frame_end,
                            "enabled":     iv.enabled,
                        }
                        for iv in entry.intervals
                    ],
                }
                for entry in seg.bone_blocks
            ],
            # Filtros organicos PROPIOS de este segmento (AISLAMIENTO POR
            # SEGMENTO, Kebyn + Claude, 2026-08-03) -- FIX (2026-08-12):
            # faltaban por completo en este exportador. seg.organic vive
            # aislado por segmento desde el fix de aislamiento, pero
            # _serialize_cerdo_1_segs (usada por el boton real "GUARDAR
            # configuracion actual" -> cerdo_1_st.save_config) nunca los leia;
            # solo el operador cerdo_1seg.save_config (no conectado a
            # ningun boton del panel) los guardaba. Resultado: al editar
            # los filtros organicos de un segmento y luego Guardar/Cargar,
            # los valores editados se perdian y el segmento reimportado
            # volvia a caer en los defaults de reglas_cerdo_1.zip via
            # _aplicar_defaults_organicos_y_parpadeo (que solo pisa un
            # segmento con organic.enabled=False, como queda uno recien
            # creado sin datos en el JSON).
            "organic": {a: getattr(seg.organic, a) for a in (
                "enabled",
                "breathing_enabled", "breathing_amplitude", "breathing_speed", "breathing_phase",
                "head_sway_enabled", "head_sway_amplitude", "head_sway_speed", "head_sway_seed",
                "weight_shift_enabled", "weight_shift_amplitude", "weight_shift_speed",
                "root_noise_enabled", "root_noise_strength", "root_noise_frequency", "root_noise_seed",
                "secondary_motion_enabled", "secondary_motion_lag", "secondary_motion_damping",
                "smooth_curves_enabled", "smooth_passes", "smooth_factor",
                "micro_scale_enabled", "micro_scale_amplitude",
                "shoulder_noise_enabled", "shoulder_noise_amplitude", "shoulder_noise_speed", "shoulder_noise_seed",
            )},
            # Intervalos de parpadeo PROPIOS de este segmento (mismo bug y
            # mismo fix que "organic" arriba -- vive en seg.blink_intervals,
            # nunca se leia desde aca).
            "blink_intervals": [
                {
                    "label":          bi.label,
                    "frame_start":    bi.frame_start,
                    "frame_end":      bi.frame_end,
                    "blink_count":    bi.blink_count,
                    "blink_duration": bi.blink_duration,
                    "enabled":        bi.enabled,
                }
                for bi in seg.blink_intervals
            ],
            "blink_interval_idx": seg.blink_interval_idx,
            # Intervalos del filtro "Reir" PROPIOS de este segmento (Kebyn,
            # 2026-08-18) -- mismo criterio que blink_intervals arriba.
            "laugh_intervals": [
                {
                    "label":             li.label,
                    "frame_start":       li.frame_start,
                    "frame_end":         li.frame_end,
                    "oscillation_count": li.oscillation_count,
                    "enabled":           li.enabled,
                }
                for li in seg.laugh_intervals
            ],
            "laugh_interval_idx": seg.laugh_interval_idx,
            # Intervalos del filtro "Entendiendo" PROPIOS de este segmento
            # (Kebyn, 2026-08-18) -- mismo criterio que laugh_intervals arriba.
            "understand_intervals": [
                {
                    "label":       ui.label,
                    "frame_start": ui.frame_start,
                    "frame_end":   ui.frame_end,
                    "direction":   ui.direction,
                    "enabled":     ui.enabled,
                }
                for ui in seg.understand_intervals
            ],
            "understand_interval_idx": seg.understand_interval_idx,
            # Setup de Shape Keys de ojos PROPIO de este segmento (mismo bug
            # y mismo fix -- vive en seg.eye_shapekey, nunca se leia desde
            # aca pese a que el aislamiento por segmento ya existia).
            "eye_shapekey": {
                "curve_mode":         seg.eye_shapekey.curve_mode,
                "affect_zone":        seg.eye_shapekey.affect_zone,
                "swap_axes":          seg.eye_shapekey.swap_axes,
                "invert_vertical":    seg.eye_shapekey.invert_vertical,
                "invert_horizontal":  seg.eye_shapekey.invert_horizontal,
                "subdivide_cuts":     seg.eye_shapekey.subdivide_cuts,
                "intensity_feliz":    seg.eye_shapekey.intensity_feliz,
                "intensity_triste":   seg.eye_shapekey.intensity_triste,
                "intensity_enojado":  seg.eye_shapekey.intensity_enojado,
                "intensity_sospecha": seg.eye_shapekey.intensity_sospecha,
                "migrated_from_global": seg.eye_shapekey.migrated_from_global,
            },
            # Expresiones de ojos PROPIAS de este segmento (independientes de
            # la lista global scene.cerdo_1_st.expr_intervals) -- FIX (2026-08-05):
            # faltaban por completo en la exportacion de segmentos. El panel
            # del Paso 3 ya permite configurar expresiones por segmento desde
            # el fix de _resolve_expr_container (Kebyn, 2026-08-04), pero esa
            # coleccion (seg.expr_intervals) nunca se escribia en el JSON, asi
            # que al reimportar la configuracion aparecia vacia.
            "expr_interval_idx": seg.expr_interval_idx,
            "expr_intervals": [
                {
                    "label":            ei.label,
                    "duration":         ei.duration,
                    "expression":       ei.expression,
                    "expression_value": ei.expression_value,
                    "interp_in":        ei.interp_in,
                    "interp_out":       ei.interp_out,
                    "enabled":          ei.enabled,
                    "eye_L_loc_x": ei.eye_L_loc_x, "eye_L_loc_y": ei.eye_L_loc_y, "eye_L_loc_z": ei.eye_L_loc_z,
                    "eye_L_rot_x": ei.eye_L_rot_x, "eye_L_rot_y": ei.eye_L_rot_y, "eye_L_rot_z": ei.eye_L_rot_z,
                    "eye_L_sca_x": ei.eye_L_sca_x, "eye_L_sca_y": ei.eye_L_sca_y, "eye_L_sca_z": ei.eye_L_sca_z,
                    "eye_R_loc_x": ei.eye_R_loc_x, "eye_R_loc_y": ei.eye_R_loc_y, "eye_R_loc_z": ei.eye_R_loc_z,
                    "eye_R_rot_x": ei.eye_R_rot_x, "eye_R_rot_y": ei.eye_R_rot_y, "eye_R_rot_z": ei.eye_R_rot_z,
                    "eye_R_sca_x": ei.eye_R_sca_x, "eye_R_sca_y": ei.eye_R_sca_y, "eye_R_sca_z": ei.eye_R_sca_z,
                    # Setup de Shape Keys de ojos PROPIO de esta expresion
                    # (Kebyn, 2026-08-18: "cada expresion tenga su propia
                    # setup de shape keys de ojos"). use_own_shapekey=False
                    # (default) => esta expresion sigue heredando
                    # seg["eye_shapekey"] de arriba; own_shapekey solo se usa
                    # cuando use_own_shapekey=True.
                    "use_own_shapekey": ei.use_own_shapekey,
                    "own_shapekey": {
                        "curve_mode":         ei.own_shapekey.curve_mode,
                        "affect_zone":        ei.own_shapekey.affect_zone,
                        "swap_axes":          ei.own_shapekey.swap_axes,
                        "invert_vertical":    ei.own_shapekey.invert_vertical,
                        "invert_horizontal":  ei.own_shapekey.invert_horizontal,
                        "subdivide_cuts":     ei.own_shapekey.subdivide_cuts,
                        "intensity_feliz":    ei.own_shapekey.intensity_feliz,
                        "intensity_triste":   ei.own_shapekey.intensity_triste,
                        "intensity_enojado":  ei.own_shapekey.intensity_enojado,
                        "intensity_sospecha": ei.own_shapekey.intensity_sospecha,
                    },
                }
                for ei in seg.expr_intervals
            ],
            # Throws (Lanzar/Recoger)
            "throws_enabled": th.enabled,
            "throws_items":   throw_items,
            # Invisibilidad de Malla (debajo de Lanzar/Recoger/Mantener)
            "hide_mesh_enabled": hm.enabled,
            "hide_mesh_items":   hide_mesh_items,
        })
    if not result:
        print("[Cerdo_1] AVISO _serialize_cerdo_1_segs: 0 segmentos en "
              "scene.cerdo_1_segs.segments al momento de guardar. Si esperabas "
              "segmentos con poses/Root configurados, revisa que el segmento "
              "siga existiendo en la escena ANTES de pulsar 'Guardar Config'.")
    return result


def _aplicar_cerdo_1_segs(st, data_list):
    """
    Restaura los segmentos del Paso 3 desde la lista serializada.
    Crea los segmentos desde cero (limpia los existentes) y aplica
    todas sus propiedades incluyendo los throws.
    """
    try:
        scene = st.id_data
        segs  = scene.cerdo_1_segs
    except Exception as e:
        print(f"[SEGS_IMPORT] ERROR accediendo cerdo_1_segs: {e}")
        return

    segs.segments.clear()

    for seg_data in data_list:
        seg = segs.segments.add()
        seg.label            = seg_data.get("label", "Segmento")
        seg.frame_start      = int(seg_data.get("frame_start", 1))
        seg.frame_end        = int(seg_data.get("frame_end", 48))
        # Foto del Paso 2 -- si el JSON es de antes de este fix y no la
        # trae, se cae a 0/0 (calcular_estimacion_slots hace fallback a
        # frame_start/frame_end en ese caso, ver path_recorder.py).
        seg.frame_start_planned = int(seg_data.get("frame_start_planned", 0))
        seg.frame_end_planned   = int(seg_data.get("frame_end_planned", 0))
        seg.single_coord_mode = bool(seg_data.get("single_coord_mode", False))
        seg.enabled          = bool(seg_data.get("enabled", True))
        seg.seg_action_name  = seg_data.get("seg_action_name", "")
        # Slots intermedios
        seg.action_poses.clear()
        for ap_data in seg_data.get("action_poses", []):
            ap = seg.action_poses.add()
            ap.json_file   = ap_data.get("json_file", "")
            ap.pose_label  = ap_data.get("pose_label", "")
            ap.pose_name   = ap_data.get("pose_name", "")
            # FIX (Kebyn, 2026-07-11): "duration" tiene update=
            # _on_pose_slot_duration_update (properties.py), que recalcula
            # seg.frame_end como suma de las poses YA agregadas hasta ese
            # instante (el bucle de import todavia no termino de agregar
            # todas) y CASCADEA ese delta a frame_start/frame_end de TODOS
            # los segmentos posteriores (other.frame_start > seg.frame_start).
            # Eso tiene sentido para segmentos single_coord_mode (duracion
            # = suma de sus poses) pero rompe los tramos de recorrido
            # (ej. "05_caminar" 112f con poses que no llenan todo el
            # presupuesto -- el resto es caminata pura): dispara en cada
            # segmento con >=1 pose durante el import y termina
            # descuadrando/solapando la timeline completa de los 11
            # segmentos (visible como "se divide en 1 segmento"). Se
            # escribe el ID-property directo (bypass del update callback)
            # para que la importacion NUNCA recalcule ni desplace
            # frame_start/frame_end -- esos ya se restauraron arriba tal
            # cual venian en el JSON, que es la unica fuente de verdad
            # durante un import.
            ap["duration"] = int(ap_data.get("duration", 24))
            ap.entry_ratio = float(ap_data.get("entry_ratio", 0.3))
            ap.exit_ratio  = float(ap_data.get("exit_ratio", 0.3))
            try: ap.interp_type = ap_data.get("interp_type", "SMOOTH")
            except Exception: pass
            ap.rot_x = float(ap_data.get("rot_x", 0.0))
            ap.rot_y = float(ap_data.get("rot_y", 0.0))
            ap.rot_z = float(ap_data.get("rot_z", 0.0))
            ap.pos_x = float(ap_data.get("pos_x", 0.0))
            ap.pos_y = float(ap_data.get("pos_y", 0.0))
            ap.pos_z = float(ap_data.get("pos_z", 0.0))
            ap.manual_start    = bool(ap_data.get("manual_start", False))
            ap.frame_abs_start = int(ap_data.get("frame_abs_start", 0))
        # Config
        seg.fps            = int(seg_data.get("fps", 24))
        seg.entry_ratio    = float(seg_data.get("entry_ratio", 0.3))
        seg.exit_ratio     = float(seg_data.get("exit_ratio", 0.3))
        seg.export_slot_number = int(seg_data.get("export_slot_number", 1))
        seg.export_type    = seg_data.get("export_type", "idle")
        seg.export_desc    = seg_data.get("export_desc", "")
        seg.blend_in_frames  = int(seg_data.get("blend_in_frames", 8))
        seg.blend_out_frames = int(seg_data.get("blend_out_frames", 8))
        # Grupos afectados
        seg.affect_body      = bool(seg_data.get("affect_body", True))
        seg.affect_left_arm  = bool(seg_data.get("affect_left_arm", True))
        seg.affect_right_arm = bool(seg_data.get("affect_right_arm", True))
        seg.affect_left_leg  = bool(seg_data.get("affect_left_leg", True))
        seg.affect_right_leg = bool(seg_data.get("affect_right_leg", True))
        seg.affect_root      = bool(seg_data.get("affect_root", False))
        seg.affect_shield    = bool(seg_data.get("affect_shield", False))
        seg.affect_spear     = bool(seg_data.get("affect_spear", False))
        # Filtros de bones
        seg.filter_show        = bool(seg_data.get("filter_show", False))
        seg.filter_main_bone   = bool(seg_data.get("filter_main_bone", False))
        seg.filter_hips        = bool(seg_data.get("filter_hips", False))
        seg.filter_body        = bool(seg_data.get("filter_body", False))
        seg.filter_spine       = bool(seg_data.get("filter_spine", False))
        seg.filter_spine1      = bool(seg_data.get("filter_spine1", False))
        seg.filter_spine2      = bool(seg_data.get("filter_spine2", False))
        seg.filter_neck        = bool(seg_data.get("filter_neck", False))
        seg.filter_face        = bool(seg_data.get("filter_face", False))
        seg.filter_right_arm   = bool(seg_data.get("filter_right_arm", False))
        seg.filter_right_elbow = bool(seg_data.get("filter_right_elbow", False))
        seg.filter_left_arm    = bool(seg_data.get("filter_left_arm", False))
        seg.filter_left_elbow  = bool(seg_data.get("filter_left_elbow", False))
        seg.filter_right_leg   = bool(seg_data.get("filter_right_leg", True))
        seg.filter_right_knee  = bool(seg_data.get("filter_right_knee", True))
        seg.filter_left_leg    = bool(seg_data.get("filter_left_leg", True))
        seg.filter_left_knee   = bool(seg_data.get("filter_left_knee", True))
        seg.filter_no_bone_01  = bool(seg_data.get("filter_no_bone_01", False))
        seg.filter_no_bone_02  = bool(seg_data.get("filter_no_bone_02", False))
        seg.filter_no_bone_03  = bool(seg_data.get("filter_no_bone_03", False))
        seg.filter_no_bone_04  = bool(seg_data.get("filter_no_bone_04", False))
        seg.filter_no_bone_05  = bool(seg_data.get("filter_no_bone_05", False))
        seg.filter_no_bone_06  = bool(seg_data.get("filter_no_bone_06", False))
        seg.filter_no_bone_07  = bool(seg_data.get("filter_no_bone_07", False))
        seg.filter_no_bone_08  = bool(seg_data.get("filter_no_bone_08", False))
        # Bloqueador de bones: intervalos de frames por bone
        seg.bone_blocks.clear()
        for bb_data in seg_data.get("bone_blocks", []):
            entry = seg.bone_blocks.add()
            entry.bone_key = str(bb_data.get("bone_key", ""))
            for iv_data in bb_data.get("intervals", []):
                iv = entry.intervals.add()
                iv.frame_start = int(iv_data.get("frame_start", 0))
                iv.frame_end   = int(iv_data.get("frame_end", 0))
                iv.enabled     = bool(iv_data.get("enabled", True))
        # Filtros organicos propios de este segmento -- FIX (2026-08-12):
        # ver comentario en _serialize_cerdo_1_segs. Si el JSON no trae
        # "organic" (config vieja, o segmento nunca editado), se dejan los
        # defaults de reglas_cerdo_1.zip via _aplicar_defaults_organicos_y_
        # parpadeo mas abajo -- igual que un segmento recien creado.
        _organic_data = seg_data.get("organic")
        if _organic_data:
            for _a, _v in _organic_data.items():
                try:
                    setattr(seg.organic, _a, _v)
                except Exception:
                    pass
        # Intervalos de parpadeo propios de este segmento
        seg.blink_intervals.clear()
        for bi_data in seg_data.get("blink_intervals", []):
            bi = seg.blink_intervals.add()
            bi.label          = str(bi_data.get("label", "Parpadeo"))
            bi.frame_start    = int(bi_data.get("frame_start", seg.frame_start))
            bi.frame_end      = int(bi_data.get("frame_end", seg.frame_end))
            bi.blink_count    = int(bi_data.get("blink_count", 1))
            bi.blink_duration = int(bi_data.get("blink_duration", 9))
            bi.enabled        = bool(bi_data.get("enabled", True))
        seg.blink_interval_idx = int(seg_data.get("blink_interval_idx", 0))
        # Intervalos del filtro "Reir" propios de este segmento (Kebyn,
        # 2026-08-18). Retrocompatible: si el JSON es de antes de este
        # filtro, seg_data.get("laugh_intervals", []) da lista vacia y
        # seg.laugh_intervals queda vacio (el filtro simplemente no se
        # aplica al reimportar, sin errores).
        seg.laugh_intervals.clear()
        for li_data in seg_data.get("laugh_intervals", []):
            li = seg.laugh_intervals.add()
            li.label             = str(li_data.get("label", "Reir"))
            li.frame_start       = int(li_data.get("frame_start", seg.frame_start))
            li.frame_end         = int(li_data.get("frame_end", seg.frame_end))
            li.oscillation_count = int(li_data.get("oscillation_count", 3))
            li.enabled           = bool(li_data.get("enabled", True))
        seg.laugh_interval_idx = int(seg_data.get("laugh_interval_idx", 0))
        # Intervalos del filtro "Entendiendo" propios de este segmento
        # (Kebyn, 2026-08-18). Retrocompatible: si el JSON es de antes de
        # este filtro, seg_data.get("understand_intervals", []) da lista
        # vacia y seg.understand_intervals queda vacio (el filtro
        # simplemente no se aplica al reimportar, sin errores).
        seg.understand_intervals.clear()
        for ui_data in seg_data.get("understand_intervals", []):
            ui_ = seg.understand_intervals.add()
            ui_.label       = str(ui_data.get("label", "Entendiendo"))
            ui_.frame_start = int(ui_data.get("frame_start", seg.frame_start))
            ui_.frame_end   = int(ui_data.get("frame_end", seg.frame_end))
            ui_.direction   = str(ui_data.get("direction", "IZQUIERDA"))
            ui_.enabled     = bool(ui_data.get("enabled", True))
        seg.understand_interval_idx = int(seg_data.get("understand_interval_idx", 0))
        # Si el JSON no trae organic NI blink_intervals propios (config de
        # antes de este fix), se aplican los defaults de reglas_cerdo_1.zip
        # a este segmento, igual que a uno recien creado.
        if not _organic_data and not seg.blink_intervals:
            try:
                from .operators_segments import _aplicar_defaults_organicos_y_parpadeo
                _aplicar_defaults_organicos_y_parpadeo(bpy.context, seg)
            except Exception as _e_org_defaults:
                print(f"[Cerdo_1] advertencia defaults organicos: {_e_org_defaults}")
        # Setup de Shape Keys de ojos propio de este segmento -- FIX
        # (2026-08-12): mismo bug, ver comentario en _serialize_cerdo_1_segs.
        _sk_data = seg_data.get("eye_shapekey")
        if _sk_data:
            for _a, _v in _sk_data.items():
                try:
                    setattr(seg.eye_shapekey, _a, _v)
                except Exception:
                    pass
            seg.eye_shapekey.migrated_from_global = True
        # Expresiones de ojos propias de este segmento -- FIX (2026-08-05):
        # ver comentario en _serialize_cerdo_1_segs.
        seg.expr_intervals.clear()
        for eid in seg_data.get("expr_intervals", []):
            eiv = seg.expr_intervals.add()
            eiv.label = eid.get("label", "Expresion")
            eiv.duration = eid.get("duration", 40)
            try: eiv.expression = eid.get("expression", "NEUTRAL")
            except Exception: pass
            eiv.expression_value = eid.get("expression_value", 0.06)
            try: eiv.interp_in  = eid.get("interp_in",  "SMOOTH")
            except Exception: pass
            try: eiv.interp_out = eid.get("interp_out", "SMOOTH")
            except Exception: pass
            eiv.enabled = bool(eid.get("enabled", True))
            eiv.eye_L_loc_x = eid.get("eye_L_loc_x",  0.106646)
            eiv.eye_L_loc_y = eid.get("eye_L_loc_y",  0.270456)
            eiv.eye_L_loc_z = eid.get("eye_L_loc_z",  1.70082)
            eiv.eye_L_rot_x = eid.get("eye_L_rot_x",  0.0)
            eiv.eye_L_rot_y = eid.get("eye_L_rot_y",  0.0)
            eiv.eye_L_rot_z = eid.get("eye_L_rot_z",  0.0)
            eiv.eye_L_sca_x = eid.get("eye_L_sca_x",  1.555)
            eiv.eye_L_sca_y = eid.get("eye_L_sca_y",  0.496018)
            eiv.eye_L_sca_z = eid.get("eye_L_sca_z",  3.55)
            eiv.eye_R_loc_x = eid.get("eye_R_loc_x", -0.1053)
            eiv.eye_R_loc_y = eid.get("eye_R_loc_y",  0.256331)
            eiv.eye_R_loc_z = eid.get("eye_R_loc_z",  1.70043)
            eiv.eye_R_rot_x = eid.get("eye_R_rot_x",  0.0)
            eiv.eye_R_rot_y = eid.get("eye_R_rot_y",  0.0)
            eiv.eye_R_rot_z = eid.get("eye_R_rot_z",  0.0)
            eiv.eye_R_sca_x = eid.get("eye_R_sca_x",  1.555)
            eiv.eye_R_sca_y = eid.get("eye_R_sca_y",  0.496018)
            eiv.eye_R_sca_z = eid.get("eye_R_sca_z",  3.55)
            # Setup de Shape Keys de ojos PROPIO de esta expresion (Kebyn,
            # 2026-08-18). Si el JSON es de antes de este fix, no trae
            # "use_own_shapekey"/"own_shapekey" -- eiv.use_own_shapekey
            # queda en su default (False), o sea la expresion sigue
            # heredando seg.eye_shapekey, igual que se comportaba antes.
            eiv.use_own_shapekey = bool(eid.get("use_own_shapekey", False))
            _ei_sk_data = eid.get("own_shapekey")
            if _ei_sk_data:
                for _a, _v in _ei_sk_data.items():
                    try:
                        setattr(eiv.own_shapekey, _a, _v)
                    except Exception:
                        pass
        seg.expr_interval_idx = min(
            seg_data.get("expr_interval_idx", 0),
            max(0, len(seg.expr_intervals) - 1)
        )
        # Throws (Lanzar/Recoger)
        th = seg.throws
        th.enabled = bool(seg_data.get("throws_enabled", False))
        th.items.clear()
        for item_data in seg_data.get("throws_items", []):
            item = th.items.add()
            item.segment_idx        = int(item_data.get("segment_idx", 0))
            item.enabled            = bool(item_data.get("enabled", True))
            item.label              = str(item_data.get("label", "Lanzamiento"))
            # uid interno: si el JSON es de antes de este fix, viene vacio
            # -- run_throws_for_segments() le asigna uno nuevo la primera
            # vez que lo procesa (ver "if not item.uid" ahi).
            item.uid                = str(item_data.get("uid", ""))
            item.mode               = str(item_data.get("mode", "THROW"))
            item.blend_path         = str(item_data.get("blend_path", ""))
            item.object_folder      = str(item_data.get("object_folder", ""))
            item.blend_filename     = str(item_data.get("blend_filename", ""))
            item.object_name        = str(item_data.get("object_name", ""))
            item.levels_up          = int(item_data.get("levels_up", 4))
            item.frame_start        = int(item_data.get("frame_start", 1))
            item.frame_end          = int(item_data.get("frame_end", 30))
            item.parent_armature    = str(item_data.get("parent_armature", "pig.arma_cerdo_1"))
            item.parent_bone        = str(item_data.get("parent_bone", ""))
            item.loc_x              = float(item_data.get("loc_x", 0.0))
            item.loc_y              = float(item_data.get("loc_y", 0.0))
            item.loc_z              = float(item_data.get("loc_z", 0.0))
            item.rot_x              = float(item_data.get("rot_x", 0.0))
            item.rot_y              = float(item_data.get("rot_y", 0.0))
            item.rot_z              = float(item_data.get("rot_z", 0.0))
            item.scale_uniform      = float(item_data.get("scale_uniform", 1.0))
            item.target_object      = str(item_data.get("target_object", ""))
            item.target_armature    = str(item_data.get("target_armature", "pig.arma_cerdo_1"))
            item.target_bone        = str(item_data.get("target_bone", ""))
            item.dest_x             = float(item_data.get("dest_x", 0.0))
            item.dest_y             = float(item_data.get("dest_y", 3.0))
            item.dest_z             = float(item_data.get("dest_z", 0.0))
            item.easing_global      = str(item_data.get("easing_global", "SMOOTH"))
            item.spin_during_flight = bool(item_data.get("spin_during_flight", False))
            item.spin_turns         = float(item_data.get("spin_turns", 1.0))
            item.transition_in            = str(item_data.get("transition_in", "NONE"))
            item.transition_in_duration   = int(item_data.get("transition_in_duration", 8))
            item.transition_out           = str(item_data.get("transition_out", "NONE"))
            item.transition_out_duration  = int(item_data.get("transition_out_duration", 8))
            item.reach_back_duration_in   = int(item_data.get("reach_back_duration_in", 8))
            item.reach_back_enabled_out   = bool(item_data.get("reach_back_enabled_out", True))
            item.reach_back_duration_out  = int(item_data.get("reach_back_duration_out", 8))
            item.imported_object_name = ""
            item.waypoints.clear()
            for wp_data in item_data.get("waypoints", []):
                wp         = item.waypoints.add()
                wp.label   = str(wp_data.get("label", "Punto"))
                wp.x       = float(wp_data.get("x", 0.0))
                wp.y       = float(wp_data.get("y", 0.0))
                wp.z       = float(wp_data.get("z", 2.0))
                wp.easing  = str(wp_data.get("easing", "SMOOTH"))
                wp.enabled = bool(wp_data.get("enabled", True))
        print(f"[SEGS_IMPORT] seg '{seg.label}' [{seg.frame_start}→{seg.frame_end}] "
              f"{len(th.items)} throw(s)")

        # Invisibilidad de Malla (debajo de Lanzar/Recoger/Mantener) --
        # mismo criterio de restauracion que throws arriba.
        hm = seg.hide_mesh
        hm.enabled = bool(seg_data.get("hide_mesh_enabled", False))
        hm.items.clear()
        for hitem_data in seg_data.get("hide_mesh_items", []):
            hitem = hm.items.add()
            hitem.segment_idx = int(hitem_data.get("segment_idx", 0))
            hitem.enabled     = bool(hitem_data.get("enabled", True))
            hitem.label       = str(hitem_data.get("label", "Invisibilidad"))
            # uid interno: si el JSON es de antes de este fix (o no trae la
            # clave), viene vacio -- run_hide_mesh_for_segments() le asigna
            # uno nuevo la primera vez que lo procesa (mismo criterio que
            # item.uid en throws, ver "if not item.uid" ahi).
            hitem.uid         = str(hitem_data.get("uid", ""))
            hitem.mesh_object = str(hitem_data.get("mesh_object", ""))
            hitem.frame_start = int(hitem_data.get("frame_start", 1))
            hitem.frame_end   = int(hitem_data.get("frame_end", 30))
        print(f"[SEGS_IMPORT] seg '{seg.label}' [{seg.frame_start}→{seg.frame_end}] "
              f"{len(hm.items)} invisibilidad(es) de malla")


def _serialize_bone_oscillations(st):
    """Serializa la config completa de bone_oscillations para el JSON."""
    osc = st.bone_oscillations
    items_list = []
    for item in osc.items:
        items_list.append({
            "label":        item.label,
            "bone_name":    item.bone_name,
            "frame_start":  item.frame_start,
            "frame_end":    item.frame_end,
            "axis_x":       item.axis_x,
            "axis_y":       item.axis_y,
            "axis_z":       item.axis_z,
            "amplitude":    round(item.amplitude, 2),
            "angle_offset": round(item.angle_offset, 2),
            "num_cycles":   item.num_cycles,
            "phase":        round(item.phase, 4),
            "wave_type":    item.wave_type,
            "fade_in":      item.fade_in,
            "fade_out":     item.fade_out,
            "noise_seed":   item.noise_seed,
            "enabled":      item.enabled,
        })
    return {
        "enabled": osc.enabled,
        "items":   items_list,
    }


def _aplicar_bone_oscillations(st, data):
    """Restaura la config de bone_oscillations desde un dict deserializado."""
    osc = st.bone_oscillations
    osc.enabled = bool(data.get("enabled", False))
    osc.items.clear()
    for item_data in data.get("items", []):
        item = osc.items.add()
        item.label        = item_data.get("label", "")
        item.bone_name    = item_data.get("bone_name", "")
        item.frame_start  = int(item_data.get("frame_start", 1))
        item.frame_end    = int(item_data.get("frame_end", 60))
        _legacy = item_data.get("axis", "")
        item.axis_x       = bool(item_data.get("axis_x", _legacy == "X"))
        item.axis_y       = bool(item_data.get("axis_y", _legacy == "Y"))
        item.axis_z       = bool(item_data.get("axis_z", _legacy == "Z" or not _legacy))
        item.amplitude    = float(item_data.get("amplitude", 30.0))
        item.angle_offset = float(item_data.get("angle_offset", 0.0))
        item.num_cycles   = int(item_data.get("num_cycles", 4))
        item.phase        = float(item_data.get("phase", 0.0))
        item.wave_type    = item_data.get("wave_type", "SINE")
        item.fade_in      = int(item_data.get("fade_in", 6))
        item.fade_out     = int(item_data.get("fade_out", 6))
        item.noise_seed   = int(item_data.get("noise_seed", 42))
        item.enabled      = bool(item_data.get("enabled", True))


def _serialize_object_imports(st):
    """Serializa la config completa de Importacion de Objetos (escudo, espada, etc.) para el JSON."""
    oi = st.object_imports
    items_list = []
    for item in oi.items:
        items_list.append({
            "label":               item.label,
            "object_folder":       item.object_folder,
            "blend_filename":      item.blend_filename,
            "object_name":         item.object_name,
            "frame_start":         item.frame_start,
            "frame_end":           item.frame_end,
            "parent_armature":     item.parent_armature,
            "parent_bone":         item.parent_bone,
            "loc_x":               round(item.loc_x, 4),
            "loc_y":               round(item.loc_y, 4),
            "loc_z":               round(item.loc_z, 4),
            "rot_x":               round(item.rot_x, 4),
            "rot_y":               round(item.rot_y, 4),
            "rot_z":               round(item.rot_z, 4),
            "scale_uniform":       round(item.scale_uniform, 4),
            "levels_up":           item.levels_up,
            "enabled":             item.enabled,
            "segment_idx":         item.segment_idx,
            "transition_in":           getattr(item, "transition_in", "NONE"),
            "transition_in_duration":  getattr(item, "transition_in_duration", 8),
            "transition_out":          getattr(item, "transition_out", "NONE"),
            "transition_out_duration": getattr(item, "transition_out_duration", 8),
            "imported_object_name": item.imported_object_name,
        })
    return {
        "enabled": oi.enabled,
        "items":   items_list,
        # ── Editor de nuevo objeto (para continuar editando donde se dejo) ──
        "editor": {
            "edit_label":           oi.edit_label,
            "edit_object_folder":   oi.edit_object_folder,
            "edit_blend_filename":  oi.edit_blend_filename,
            "edit_object_name":     oi.edit_object_name,
            "edit_frame_start":     oi.edit_frame_start,
            "edit_frame_end":       oi.edit_frame_end,
            "edit_parent_armature": oi.edit_parent_armature,
            "edit_parent_bone":     oi.edit_parent_bone,
            "edit_loc_x":           round(oi.edit_loc_x, 4),
            "edit_loc_y":           round(oi.edit_loc_y, 4),
            "edit_loc_z":           round(oi.edit_loc_z, 4),
            "edit_rot_x":           round(oi.edit_rot_x, 4),
            "edit_rot_y":           round(oi.edit_rot_y, 4),
            "edit_rot_z":           round(oi.edit_rot_z, 4),
            "edit_scale_uniform":   round(oi.edit_scale_uniform, 4),
            "edit_levels_up":       oi.edit_levels_up,
            "edit_segment_idx":     oi.edit_segment_idx,
        },
    }


def _aplicar_object_imports(st, data):
    """Restaura la config de Importacion de Objetos desde un dict deserializado."""
    oi = st.object_imports
    oi.enabled = bool(data.get("enabled", False))
    oi.items.clear()
    for item_data in data.get("items", []):
        item = oi.items.add()
        item.label                = item_data.get("label", "Objeto")
        item.object_folder        = item_data.get("object_folder", "shield")
        item.blend_filename       = item_data.get("blend_filename", "shield.blend")
        item.object_name          = item_data.get("object_name", "shield")
        item.frame_start          = int(item_data.get("frame_start", 1))
        item.frame_end            = int(item_data.get("frame_end", 60))
        item.parent_armature      = item_data.get("parent_armature", "pig.arma_cerdo_1")
        item.parent_bone          = item_data.get("parent_bone", "")
        item.loc_x                = float(item_data.get("loc_x", 0.0))
        item.loc_y                = float(item_data.get("loc_y", 0.0))
        item.loc_z                = float(item_data.get("loc_z", 0.0))
        item.rot_x                = float(item_data.get("rot_x", 0.0))
        item.rot_y                = float(item_data.get("rot_y", 0.0))
        item.rot_z                = float(item_data.get("rot_z", 0.0))
        item.scale_uniform        = float(item_data.get("scale_uniform", 1.0))
        item.levels_up            = int(item_data.get("levels_up", 4))
        item.enabled              = bool(item_data.get("enabled", True))
        item.segment_idx          = int(item_data.get("segment_idx", -1))
        t_in = item_data.get("transition_in", "NONE")
        if hasattr(item, "transition_in"):
            item.transition_in = t_in if t_in else "NONE"
        t_in_dur = item_data.get("transition_in_duration", 8)
        if hasattr(item, "transition_in_duration"):
            item.transition_in_duration = int(t_in_dur)
        t_out = item_data.get("transition_out", "NONE")
        if hasattr(item, "transition_out"):
            item.transition_out = t_out if t_out else "NONE"
        t_out_dur = item_data.get("transition_out_duration", 8)
        if hasattr(item, "transition_out_duration"):
            item.transition_out_duration = int(t_out_dur)
        # imported_object_name NO se restaura: el objeto de una sesion anterior
        # ya no existe en esta escena. Se reimportara limpio en el proximo CONCATENAR.
        item.imported_object_name = ""

    editor = data.get("editor", {})
    if editor:
        oi.edit_label           = editor.get("edit_label",           oi.edit_label)
        oi.edit_object_folder   = editor.get("edit_object_folder",   oi.edit_object_folder)
        oi.edit_blend_filename  = editor.get("edit_blend_filename",  oi.edit_blend_filename)
        oi.edit_object_name     = editor.get("edit_object_name",     oi.edit_object_name)
        oi.edit_frame_start     = int(editor.get("edit_frame_start", oi.edit_frame_start))
        oi.edit_frame_end       = int(editor.get("edit_frame_end",   oi.edit_frame_end))
        oi.edit_parent_armature = editor.get("edit_parent_armature", oi.edit_parent_armature)
        oi.edit_parent_bone     = editor.get("edit_parent_bone",     oi.edit_parent_bone)
        oi.edit_loc_x           = float(editor.get("edit_loc_x",           oi.edit_loc_x))
        oi.edit_loc_y           = float(editor.get("edit_loc_y",           oi.edit_loc_y))
        oi.edit_loc_z           = float(editor.get("edit_loc_z",           oi.edit_loc_z))
        oi.edit_rot_x           = float(editor.get("edit_rot_x",           oi.edit_rot_x))
        oi.edit_rot_y           = float(editor.get("edit_rot_y",           oi.edit_rot_y))
        oi.edit_rot_z           = float(editor.get("edit_rot_z",           oi.edit_rot_z))
        oi.edit_scale_uniform   = float(editor.get("edit_scale_uniform",   oi.edit_scale_uniform))
        oi.edit_levels_up       = int(editor.get("edit_levels_up",   oi.edit_levels_up))
        oi.edit_segment_idx     = int(editor.get("edit_segment_idx", oi.edit_segment_idx))




def _serialize_throw_settings(st):
    """Serializa los throws de TODOS los segmentos. Un entry por item de cada segmento."""
    result = []
    try:
        scene = st.id_data
        segs  = scene.cerdo_1_segs.segments
    except Exception:
        return result

    for seg_idx, seg in enumerate(segs):
        th = seg.throws
        for item_idx, item in enumerate(th.items):
            wps = [{"label": wp.label, "x": round(wp.x,4), "y": round(wp.y,4),
                    "z": round(wp.z,4), "easing": wp.easing, "enabled": wp.enabled}
                   for wp in item.waypoints]
            result.append({
                "seg_idx":            seg_idx,
                "item_idx":           item_idx,
                "enabled":            item.enabled,
                "label":              item.label,
                "mode":               item.mode,
                "blend_path":         item.blend_path,
                "object_folder":      item.object_folder,
                "blend_filename":     item.blend_filename,
                "object_name":        item.object_name,
                "levels_up":          item.levels_up,
                "frame_start":        item.frame_start,
                "frame_end":          item.frame_end,
                "parent_armature":    item.parent_armature,
                "parent_bone":        item.parent_bone,
                "loc_x":              round(item.loc_x, 4),
                "loc_y":              round(item.loc_y, 4),
                "loc_z":              round(item.loc_z, 4),
                "rot_x":              round(item.rot_x, 4),
                "rot_y":              round(item.rot_y, 4),
                "rot_z":              round(item.rot_z, 4),
                "scale_uniform":      round(item.scale_uniform, 3),
                "target_object":      item.target_object,
                "target_armature":    item.target_armature,
                "target_bone":        item.target_bone,
                "dest_x":             round(item.dest_x, 4),
                "dest_y":             round(item.dest_y, 4),
                "dest_z":             round(item.dest_z, 4),
                "easing_global":      item.easing_global,
                "spin_during_flight": item.spin_during_flight,
                "spin_turns":         round(item.spin_turns, 2),
                "transition_in":            item.transition_in,
                "transition_in_duration":   item.transition_in_duration,
                "transition_out":           item.transition_out,
                "transition_out_duration":  item.transition_out_duration,
                "reach_back_duration_in":   item.reach_back_duration_in,
                "reach_back_enabled_out":   item.reach_back_enabled_out,
                "reach_back_duration_out":  item.reach_back_duration_out,
                "waypoints":          wps,
            })
    return result


def _aplicar_throw_settings(st, data_list):
    """Restaura los throws de los segmentos desde la lista serializada."""
    try:
        scene = st.id_data
        segs  = scene.cerdo_1_segs.segments
    except Exception as e:
        print(f"[THROW_IMPORT] ERROR: {e}")
        return

    # Limpiar items existentes antes de reconstruir
    for seg in segs:
        seg.throws.items.clear()

    for entry in data_list:
        seg_idx = int(entry.get("seg_idx", -1))
        if seg_idx < 0 or seg_idx >= len(segs):
            continue
        th   = segs[seg_idx].throws
        th.enabled = True  # Si hay items en JSON, el filtro estaba activo
        item = th.items.add()
        item.enabled            = bool(entry.get("enabled", True))
        item.label              = str(entry.get("label", "Lanzamiento"))
        item.mode               = str(entry.get("mode", "THROW"))
        item.blend_path         = str(entry.get("blend_path", ""))
        item.object_folder      = str(entry.get("object_folder", ""))
        item.blend_filename     = str(entry.get("blend_filename", ""))
        item.object_name        = str(entry.get("object_name", ""))
        item.levels_up          = int(entry.get("levels_up", 4))
        item.frame_start        = int(entry.get("frame_start", 1))
        item.frame_end          = int(entry.get("frame_end", 30))
        item.parent_armature    = str(entry.get("parent_armature", "pig.arma_cerdo_1"))
        item.parent_bone        = str(entry.get("parent_bone", ""))
        item.loc_x              = float(entry.get("loc_x", 0.0))
        item.loc_y              = float(entry.get("loc_y", 0.0))
        item.loc_z              = float(entry.get("loc_z", 0.0))
        item.rot_x              = float(entry.get("rot_x", 0.0))
        item.rot_y              = float(entry.get("rot_y", 0.0))
        item.rot_z              = float(entry.get("rot_z", 0.0))
        item.scale_uniform      = float(entry.get("scale_uniform", 1.0))
        item.target_object      = str(entry.get("target_object", ""))
        item.target_armature    = str(entry.get("target_armature", "pig.arma_cerdo_1"))
        item.target_bone        = str(entry.get("target_bone", ""))
        item.dest_x             = float(entry.get("dest_x", 0.0))
        item.dest_y             = float(entry.get("dest_y", 3.0))
        item.dest_z             = float(entry.get("dest_z", 0.0))
        item.easing_global      = str(entry.get("easing_global", "SMOOTH"))
        item.spin_during_flight = bool(entry.get("spin_during_flight", False))
        item.spin_turns         = float(entry.get("spin_turns", 1.0))
        item.transition_in            = str(entry.get("transition_in", "NONE"))
        item.transition_in_duration   = int(entry.get("transition_in_duration", 8))
        item.transition_out           = str(entry.get("transition_out", "NONE"))
        item.transition_out_duration  = int(entry.get("transition_out_duration", 8))
        item.reach_back_duration_in   = int(entry.get("reach_back_duration_in", 8))
        item.reach_back_enabled_out   = bool(entry.get("reach_back_enabled_out", True))
        item.reach_back_duration_out  = int(entry.get("reach_back_duration_out", 8))
        item.imported_object_name = ""
        item.waypoints.clear()
        for wp_data in entry.get("waypoints", []):
            wp         = item.waypoints.add()
            wp.label   = str(wp_data.get("label", "Punto"))
            wp.x       = float(wp_data.get("x", 0.0))
            wp.y       = float(wp_data.get("y", 0.0))
            wp.z       = float(wp_data.get("z", 2.0))
            wp.easing  = str(wp_data.get("easing", "SMOOTH"))
            wp.enabled = bool(wp_data.get("enabled", True))
        print(f"[THROW_IMPORT] seg[{seg_idx}] item[{len(th.items)-1}]: "
              f"'{item.object_name}' {item.frame_start}→{item.frame_end}")


class CERDO_1_ST_OT_SaveConfig(Operator):
    bl_idname    = "cerdo_1_st.save_config"
    bl_label     = "Guardar Configuracion"
    bl_description = (
        "Guarda la secuencia completa de trabajo (poses, rotaciones, posiciones, "
        "interpolaciones, duraciones, filtros) como archivo .json en la carpeta "
        "de configuraciones. NO incluye los keyframes de la animacion terminada"
    )
    bl_options = {"REGISTER"}

    config_name: bpy.props.StringProperty(
        name="Nombre del archivo",
        default="mi_configuracion",
        description="Nombre del archivo de configuracion a guardar (sin extension .json)",
    )

    def invoke(self, context, event):
        self.config_name = context.scene.cerdo_1_st.config_name or "mi_configuracion"
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        st = context.scene.cerdo_1_st
        layout.label(text="Nombre del archivo de configuracion:", icon="FILE_BLANK")
        layout.prop(self, "config_name", text="")
        layout.separator()
        out_dir = bpy.path.abspath(st.config_dir)
        _FORBIDDEN = set('/\\:*?"<>|')
        safe = "".join(c if c not in _FORBIDDEN else "_" for c in self.config_name).strip()
        fname = f"{safe or 'configuracion'}.json"
        layout.label(text=f"  -> {os.path.join(out_dir, fname)}", icon="INFO")
        layout.separator()
        layout.label(text="Se guardara la sesion completa:", icon="CHECKMARK")
        # Paso 1 y 2
        try:
            pc = context.scene.cerdo_1_path
            n_pts = len(pc.path_points)
            blend_name = os.path.basename(pc.blend_filepath) if pc.blend_filepath else "(sin seleccionar)"
            layout.label(text=f"  - Paso 1: personaje '{blend_name}',  {n_pts} punto(s) de recorrido")
            layout.label(text=f"  - Paso 2: slot {pc.slot_inicio},  frame {pc.frame_inicio}→{pc.frame_fin_manual},  rot Z {pc.root_rot_z:.1f}°")
            # NUEVO (Kebyn, 2026-09-13): resumen de paradas con animacion
            # .py importada y/o orientacion guardada a mano -- ver
            # CERDO_1PathPoint.parada_anim_file/parada_rot_saved
            # (path_recorder.py) y su serializacion mas arriba en este
            # archivo (_serialize_configuracion).
            n_parada_anim = sum(
                1 for pt in pc.path_points
                if getattr(pt, "tipo_segmento", "AUTO") == "PARADA"
                and getattr(pt, "parada_anim_file", "")
            )
            n_parada_rot = sum(
                1 for pt in pc.path_points
                if getattr(pt, "tipo_segmento", "AUTO") == "PARADA"
                and getattr(pt, "parada_rot_saved", False)
            )
            if n_parada_anim or n_parada_rot:
                layout.label(
                    text=(
                        f"  - Paradas: {n_parada_anim} con animacion .py importada,  "
                        f"{n_parada_rot} con orientacion guardada"
                    ),
                    icon="PAUSE",
                )
        except Exception:
            layout.label(text="  - Paso 1 y 2: (no disponible)")
        layout.separator()
        layout.label(text=f"  - Poses de ACCION: todas las poses de la secuencia")
        layout.label(text=f"  - Configuracion: fps, frames, blend, filtros organicos")
        layout.label(text=f"  - Estimacion de slots: duracion estimada por tramo (Paso 2)")
        try:
            oi = context.scene.cerdo_1_st.object_imports
            n_oi = len(oi.items)
            layout.label(text=f"  - Importacion de Objetos: {n_oi} objeto(s) (escudo, espada, etc.)")
        except Exception:
            pass

    def execute(self, context):
        st = context.scene.cerdo_1_st

        _FORBIDDEN = set('/\\:*?"<>|')
        safe = "".join(c if c not in _FORBIDDEN else "_" for c in self.config_name).strip()
        if not safe:
            safe = "configuracion"
        filename = f"{safe}.json"

        # Guardar nombre para uso futuro
        st.config_name = self.config_name

        out_dir = bpy.path.abspath(st.config_dir)
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            self.report({"ERROR"}, f"No se pudo crear la carpeta: {e}")
            return {"CANCELLED"}

        filepath = os.path.join(out_dir, filename)
        cfg = _serialize_configuracion(st)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.report({"ERROR"}, f"Error al escribir el archivo: {e}")
            return {"CANCELLED"}

        n_acciones = len(st.action_poses)
        self.report({"INFO"},
            f"Configuracion guardada: {filename}  "
            f"({n_acciones} pose(s) de accion)  ->  {filepath}")
        return {"FINISHED"}


class CERDO_1_ST_OT_LoadConfig(Operator):
    bl_idname    = "cerdo_1_st.load_config"
    bl_label     = "Importar Configuracion"
    bl_description = (
        "Carga una configuracion de trabajo desde un .json de la carpeta de "
        "configuraciones. Restaura toda la secuencia: poses, interpolaciones, "
        "posiciones, rotaciones y filtros organicos"
    )
    bl_options = {"REGISTER", "UNDO"}

    filepath:    bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        start = bpy.path.abspath(context.scene.cerdo_1_st.config_dir)
        if os.path.isdir(start):
            self.filepath = start + os.sep
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        st   = context.scene.cerdo_1_st
        path = bpy.path.abspath(self.filepath)

        if not os.path.isfile(path):
            self.report({"ERROR"}, f"Archivo no encontrado: {path}")
            return {"CANCELLED"}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.report({"ERROR"}, f"Error al leer el JSON: {e}")
            return {"CANCELLED"}

        # Validacion basica
        if "action_poses" not in data:
            self.report({"WARNING"},
                "El archivo no parece una configuracion de Cerdo_1 Studio "
                "(falta 'action_poses'). Se intentara importar igual.")

        _aplicar_configuracion(st, data)
        n_portables = 0
        try:
            # Los props declarados por el guion deben existir desde el momento
            # de cargar el JSON. Antes solo se importaban al final de
            # "Concatenar segmentos", por lo que con otros botones de
            # concatenacion el hacha/antorcha/item nunca aparecia.
            from . import objetos_mundo as _objetos_mundo
            n_portables = len(_objetos_mundo.asegurar_portables_al_cargar(data))
        except Exception as _e:
            print(f"[guion] assets portatiles al cargar: {_e}")
        try:   # guion 2.0 con voces: se sincronizan con Voz Sync en el inicio que dice el guion (audio_import)
            from . import audio_import as _audio_import
            _audio_import.post_cargar(context)
        except Exception as _e:
            print(f"[guion] audio: {_e}")

        n_acciones = len(st.action_poses)
        n_obj_imp  = len(st.object_imports.items)
        version    = data.get("version", "?")
        ts         = data.get("timestamp", "")[:19].replace("T", " ")
        self.report({"INFO"},
            f"Configuracion cargada: {os.path.basename(path)}  "
            f"v{version}  {ts}  "
            f"({n_acciones} pose(s) de accion, {n_obj_imp} objeto(s) del panel, "
            f"{n_portables} asset(s) portable(s) importado(s))")
        return {"FINISHED"}


class CERDO_1_ST_OT_OpenConfigFolder(Operator):
    bl_idname    = "cerdo_1_st.open_config_folder"
    bl_label     = "Abrir carpeta configuraciones"
    bl_description = "Abre la carpeta de configuraciones en el explorador de archivos"

    def execute(self, context):
        open_folder(bpy.path.abspath(context.scene.cerdo_1_st.config_dir))
        return {"FINISHED"}


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACION DE OJOS — serializar / deserializar
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_EYE_CONFIG_DIR = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\cerdo_1\refinar\configuraciones_ojos"
)


def _serialize_eye_config(st):
    """
    Serializa toda la secuencia de ojos activa:
      - Frame de inicio global
      - Estado INICIO (duracion, interp)
      - Slots intermedios completos (loc/rot/sca ambos ojos, expresion, geometria, interp)
      - Estado FIN (duracion, interp)
      - Configuracion de parpadeo
    Formato identico al de poses (inicio / intermedios / fin).
    """
    eye_s = st.eye_expr

    # Slots intermedios
    slots_data = []
    for slot in st.eye_slots:
        slots_data.append({
            "slot_label":       slot.slot_label,
            "duration":         slot.duration,
            "interp_type":      slot.interp_type,
            "active_expression": slot.active_expression,
            "expression_value": slot.expression_value,
            "geo_edit_mode":    slot.geo_edit_mode,
            "geo_intensity":    slot.geo_intensity,
            "eye_L_loc_x": slot.eye_L_loc_x, "eye_L_loc_y": slot.eye_L_loc_y, "eye_L_loc_z": slot.eye_L_loc_z,
            "eye_L_rot_x": slot.eye_L_rot_x, "eye_L_rot_y": slot.eye_L_rot_y, "eye_L_rot_z": slot.eye_L_rot_z,
            "eye_L_sca_x": slot.eye_L_sca_x, "eye_L_sca_y": slot.eye_L_sca_y, "eye_L_sca_z": slot.eye_L_sca_z,
            "eye_R_loc_x": slot.eye_R_loc_x, "eye_R_loc_y": slot.eye_R_loc_y, "eye_R_loc_z": slot.eye_R_loc_z,
            "eye_R_rot_x": slot.eye_R_rot_x, "eye_R_rot_y": slot.eye_R_rot_y, "eye_R_rot_z": slot.eye_R_rot_z,
            "eye_R_sca_x": slot.eye_R_sca_x, "eye_R_sca_y": slot.eye_R_sca_y, "eye_R_sca_z": slot.eye_R_sca_z,
        })

    return {
        "version":   "1.1",
        "timestamp": datetime.now().isoformat(),
        "description": "Configuracion de secuencia de ojos — Cerdo_1 Animation Studio",
        # Frame de inicio
        "eye_global_start_frame": st.eye_global_start_frame,
        # Toggle general del sistema de N° Cambios de Ojos (Inicio/intermedios/Fin)
        "eye_changes_enabled": st.eye_changes_enabled,
        # Estado INICIO
        "eye_inicio": {
            "duration":       st.eye_start_duration,
            "interp":         st.eye_start_interp,
            "blink_mode":     st.eye_start_blink_mode,
            "blink_count":    st.eye_start_blink_count,
            "blink_duration": st.eye_start_blink_duration,
            "expression":     st.eye_start_expression,
            "expr_value":     st.eye_start_expr_value,
            "geo_mode":       st.eye_start_geo_mode,
            "geo_intensity":  st.eye_start_geo_intensity,
            "eye_L_loc_x": st.eye_start_L_loc_x, "eye_L_loc_y": st.eye_start_L_loc_y, "eye_L_loc_z": st.eye_start_L_loc_z,
            "eye_L_rot_x": st.eye_start_L_rot_x, "eye_L_rot_y": st.eye_start_L_rot_y, "eye_L_rot_z": st.eye_start_L_rot_z,
            "eye_L_sca_x": st.eye_start_L_sca_x, "eye_L_sca_y": st.eye_start_L_sca_y, "eye_L_sca_z": st.eye_start_L_sca_z,
            "eye_R_loc_x": st.eye_start_R_loc_x, "eye_R_loc_y": st.eye_start_R_loc_y, "eye_R_loc_z": st.eye_start_R_loc_z,
            "eye_R_rot_x": st.eye_start_R_rot_x, "eye_R_rot_y": st.eye_start_R_rot_y, "eye_R_rot_z": st.eye_start_R_rot_z,
            "eye_R_sca_x": st.eye_start_R_sca_x, "eye_R_sca_y": st.eye_start_R_sca_y, "eye_R_sca_z": st.eye_start_R_sca_z,
        },
        # Slots intermedios
        "eye_slots": slots_data,
        # Estado FIN
        "eye_fin": {
            "duration":       st.eye_end_duration,
            "interp":         st.eye_end_interp,
            "blink_mode":     st.eye_end_blink_mode,
            "blink_count":    st.eye_end_blink_count,
            "blink_duration": st.eye_end_blink_duration,
            "expression":     st.eye_end_expression,
            "expr_value":     st.eye_end_expr_value,
            "geo_mode":       st.eye_end_geo_mode,
            "geo_intensity":  st.eye_end_geo_intensity,
            "eye_L_loc_x": st.eye_end_L_loc_x, "eye_L_loc_y": st.eye_end_L_loc_y, "eye_L_loc_z": st.eye_end_L_loc_z,
            "eye_L_rot_x": st.eye_end_L_rot_x, "eye_L_rot_y": st.eye_end_L_rot_y, "eye_L_rot_z": st.eye_end_L_rot_z,
            "eye_L_sca_x": st.eye_end_L_sca_x, "eye_L_sca_y": st.eye_end_L_sca_y, "eye_L_sca_z": st.eye_end_L_sca_z,
            "eye_R_loc_x": st.eye_end_R_loc_x, "eye_R_loc_y": st.eye_end_R_loc_y, "eye_R_loc_z": st.eye_end_R_loc_z,
            "eye_R_rot_x": st.eye_end_R_rot_x, "eye_R_rot_y": st.eye_end_R_rot_y, "eye_R_rot_z": st.eye_end_R_rot_z,
            "eye_R_sca_x": st.eye_end_R_sca_x, "eye_R_sca_y": st.eye_end_R_sca_y, "eye_R_sca_z": st.eye_end_R_sca_z,
        },
        # Sistema de expresiones por intervalos (multi-intervalo, independiente
        # de la secuencia lineal inicio/intermedios/fin) — NUEVO, faltaba
        # por completo en el exportador aunque el panel ya lo expone.
        "expr_intervals_enabled": eye_s.expr_intervals_enabled,
        "expr_interval_idx":      st.expr_interval_idx,
        "expr_intervals": [
            {
                "label":            ei.label,
                "duration":         ei.duration,
                "expression":       ei.expression,
                "expression_value": ei.expression_value,
                "interp_in":        ei.interp_in,
                "interp_out":       ei.interp_out,
                "enabled":          ei.enabled,
                "eye_L_loc_x": ei.eye_L_loc_x, "eye_L_loc_y": ei.eye_L_loc_y, "eye_L_loc_z": ei.eye_L_loc_z,
                "eye_L_rot_x": ei.eye_L_rot_x, "eye_L_rot_y": ei.eye_L_rot_y, "eye_L_rot_z": ei.eye_L_rot_z,
                "eye_L_sca_x": ei.eye_L_sca_x, "eye_L_sca_y": ei.eye_L_sca_y, "eye_L_sca_z": ei.eye_L_sca_z,
                "eye_R_loc_x": ei.eye_R_loc_x, "eye_R_loc_y": ei.eye_R_loc_y, "eye_R_loc_z": ei.eye_R_loc_z,
                "eye_R_rot_x": ei.eye_R_rot_x, "eye_R_rot_y": ei.eye_R_rot_y, "eye_R_rot_z": ei.eye_R_rot_z,
                "eye_R_sca_x": ei.eye_R_sca_x, "eye_R_sca_y": ei.eye_R_sca_y, "eye_R_sca_z": ei.eye_R_sca_z,
            }
            for ei in st.expr_intervals
        ],
        # Parpadeo independiente
        "parpadeo": {
            "enabled":      eye_s.blink_enabled,
            "count":        eye_s.blink_count,
            "duration":     eye_s.blink_duration,
            "frame_start":  eye_s.blink_frame_start,
            "frame_end":    eye_s.blink_frame_end,
            "blink_intervals": [
                {
                    "label":          bi.label,
                    "frame_start":    bi.frame_start,
                    "frame_end":      bi.frame_end,
                    "blink_count":    bi.blink_count,
                    "blink_duration": bi.blink_duration,
                    "enabled":        bi.enabled,
                }
                for bi in st.blink_intervals
            ],
            "blink_interval_idx": st.blink_interval_idx,
        },
        # Setup de shape keys
        "shape_keys_setup": {
            "subdivide_cuts":    eye_s.subdivide_cuts,
            "curve_mode":        eye_s.curve_mode,
            "affect_zone":       eye_s.affect_zone,
            "swap_axes":         eye_s.swap_axes,
            "invert_vertical":   eye_s.invert_vertical,
            "invert_horizontal": eye_s.invert_horizontal,
        },
    }


def _aplicar_eye_config(st, data):
    """
    Restaura la secuencia de ojos desde el diccionario leído del JSON.
    Omite claves inexistentes (compatibilidad hacia atrás).
    Al final recrea automáticamente los shape keys con el setup guardado.
    """
    eye_s = st.eye_expr

    # Frame de inicio global
    if "eye_global_start_frame" in data:
        st.eye_global_start_frame = data["eye_global_start_frame"]

    # Toggle general del sistema de N° Cambios de Ojos
    if "eye_changes_enabled" in data:
        st.eye_changes_enabled = bool(data["eye_changes_enabled"])

    # Estado INICIO
    ei = data.get("eye_inicio", {})
    if ei:
        st.eye_start_duration = ei.get("duration", 20)
        st.eye_start_interp   = ei.get("interp",   "SMOOTH")
        try: st.eye_start_blink_mode     = ei.get("blink_mode",     "BLINK")
        except Exception: pass
        st.eye_start_blink_count    = ei.get("blink_count",    2)
        st.eye_start_blink_duration = ei.get("blink_duration", 9)
        try: st.eye_start_expression = ei.get("expression", "NEUTRAL")
        except Exception: pass
        st.eye_start_expr_value = ei.get("expr_value", 1.0)
        try: st.eye_start_geo_mode = ei.get("geo_mode", "NONE")
        except Exception: pass
        st.eye_start_geo_intensity = ei.get("geo_intensity", 1.0)
        st.eye_start_L_loc_x = ei.get("eye_L_loc_x",  0.106646)
        st.eye_start_L_loc_y = ei.get("eye_L_loc_y",  0.270456)
        st.eye_start_L_loc_z = ei.get("eye_L_loc_z",  1.70082)
        st.eye_start_L_rot_x = ei.get("eye_L_rot_x",  0.0)
        st.eye_start_L_rot_y = ei.get("eye_L_rot_y",  0.0)
        st.eye_start_L_rot_z = ei.get("eye_L_rot_z",  0.0)
        st.eye_start_L_sca_x = ei.get("eye_L_sca_x",  1.555)
        st.eye_start_L_sca_y = ei.get("eye_L_sca_y",  0.496018)
        st.eye_start_L_sca_z = ei.get("eye_L_sca_z",  3.55)
        st.eye_start_R_loc_x = ei.get("eye_R_loc_x", -0.1053)
        st.eye_start_R_loc_y = ei.get("eye_R_loc_y",  0.256331)
        st.eye_start_R_loc_z = ei.get("eye_R_loc_z",  1.70043)
        st.eye_start_R_rot_x = ei.get("eye_R_rot_x",  0.0)
        st.eye_start_R_rot_y = ei.get("eye_R_rot_y",  0.0)
        st.eye_start_R_rot_z = ei.get("eye_R_rot_z",  0.0)
        st.eye_start_R_sca_x = ei.get("eye_R_sca_x",  1.555)
        st.eye_start_R_sca_y = ei.get("eye_R_sca_y",  0.496018)
        st.eye_start_R_sca_z = ei.get("eye_R_sca_z",  3.55)

    # Estado FIN
    ef = data.get("eye_fin", {})
    if ef:
        st.eye_end_duration = ef.get("duration", 20)
        st.eye_end_interp   = ef.get("interp",   "SMOOTH")
        try: st.eye_end_blink_mode     = ef.get("blink_mode",     "BLINK")
        except Exception: pass
        st.eye_end_blink_count    = ef.get("blink_count",    2)
        st.eye_end_blink_duration = ef.get("blink_duration", 9)
        try: st.eye_end_expression = ef.get("expression", "NEUTRAL")
        except Exception: pass
        st.eye_end_expr_value = ef.get("expr_value", 1.0)
        try: st.eye_end_geo_mode = ef.get("geo_mode", "NONE")
        except Exception: pass
        st.eye_end_geo_intensity = ef.get("geo_intensity", 1.0)
        st.eye_end_L_loc_x = ef.get("eye_L_loc_x",  0.106646)
        st.eye_end_L_loc_y = ef.get("eye_L_loc_y",  0.270456)
        st.eye_end_L_loc_z = ef.get("eye_L_loc_z",  1.70082)
        st.eye_end_L_rot_x = ef.get("eye_L_rot_x",  0.0)
        st.eye_end_L_rot_y = ef.get("eye_L_rot_y",  0.0)
        st.eye_end_L_rot_z = ef.get("eye_L_rot_z",  0.0)
        st.eye_end_L_sca_x = ef.get("eye_L_sca_x",  1.555)
        st.eye_end_L_sca_y = ef.get("eye_L_sca_y",  0.496018)
        st.eye_end_L_sca_z = ef.get("eye_L_sca_z",  3.55)
        st.eye_end_R_loc_x = ef.get("eye_R_loc_x", -0.1053)
        st.eye_end_R_loc_y = ef.get("eye_R_loc_y",  0.256331)
        st.eye_end_R_loc_z = ef.get("eye_R_loc_z",  1.70043)
        st.eye_end_R_rot_x = ef.get("eye_R_rot_x",  0.0)
        st.eye_end_R_rot_y = ef.get("eye_R_rot_y",  0.0)
        st.eye_end_R_rot_z = ef.get("eye_R_rot_z",  0.0)
        st.eye_end_R_sca_x = ef.get("eye_R_sca_x",  1.555)
        st.eye_end_R_sca_y = ef.get("eye_R_sca_y",  0.496018)
        st.eye_end_R_sca_z = ef.get("eye_R_sca_z",  3.55)

    # Sistema de expresiones por intervalos (multi-intervalo)
    if "expr_intervals_enabled" in data:
        eye_s.expr_intervals_enabled = bool(data["expr_intervals_enabled"])
    expr_intervals_data = data.get("expr_intervals", [])
    if expr_intervals_data or "expr_intervals" in data:
        st.expr_intervals.clear()
        for eid in expr_intervals_data:
            eiv = st.expr_intervals.add()
            eiv.label            = eid.get("label",            "Expresion")
            # Compat con configs viejas guardadas con inicio/pico/fin: si no
            # hay "duration" pero si hay frame_start/frame_end, se deriva.
            if "duration" in eid:
                eiv.duration = eid.get("duration", 40)
            elif "frame_start" in eid and "frame_end" in eid:
                eiv.duration = max(2, eid.get("frame_end", 40) - eid.get("frame_start", 1) + 1)
            else:
                eiv.duration = 40
            try: eiv.expression = eid.get("expression", "NEUTRAL")
            except Exception: pass
            eiv.expression_value = min(eid.get("expression_value", 0.06), 0.06)
            try: eiv.interp_in  = eid.get("interp_in",  "SMOOTH")
            except Exception: pass
            try: eiv.interp_out = eid.get("interp_out", "SMOOTH")
            except Exception: pass
            eiv.enabled           = bool(eid.get("enabled", True))
            eiv.eye_L_loc_x = eid.get("eye_L_loc_x",  0.106646)
            eiv.eye_L_loc_y = eid.get("eye_L_loc_y",  0.270456)
            eiv.eye_L_loc_z = eid.get("eye_L_loc_z",  1.70082)
            eiv.eye_L_rot_x = eid.get("eye_L_rot_x",  0.0)
            eiv.eye_L_rot_y = eid.get("eye_L_rot_y",  0.0)
            eiv.eye_L_rot_z = eid.get("eye_L_rot_z",  0.0)
            eiv.eye_L_sca_x = eid.get("eye_L_sca_x",  1.555)
            eiv.eye_L_sca_y = eid.get("eye_L_sca_y",  0.496018)
            eiv.eye_L_sca_z = eid.get("eye_L_sca_z",  3.55)
            eiv.eye_R_loc_x = eid.get("eye_R_loc_x", -0.1053)
            eiv.eye_R_loc_y = eid.get("eye_R_loc_y",  0.256331)
            eiv.eye_R_loc_z = eid.get("eye_R_loc_z",  1.70043)
            eiv.eye_R_rot_x = eid.get("eye_R_rot_x",  0.0)
            eiv.eye_R_rot_y = eid.get("eye_R_rot_y",  0.0)
            eiv.eye_R_rot_z = eid.get("eye_R_rot_z",  0.0)
            eiv.eye_R_sca_x = eid.get("eye_R_sca_x",  1.555)
            eiv.eye_R_sca_y = eid.get("eye_R_sca_y",  0.496018)
            eiv.eye_R_sca_z = eid.get("eye_R_sca_z",  3.55)
        st.expr_interval_idx = min(
            data.get("expr_interval_idx", 0),
            max(0, len(st.expr_intervals) - 1)
        )

    # Slots intermedios
    st.eye_slots.clear()
    for sd in data.get("eye_slots", []):
        slot = st.eye_slots.add()
        slot.slot_label        = sd.get("slot_label",        "cambio")
        slot.duration          = sd.get("duration",          20)
        slot.interp_type       = sd.get("interp_type",       "SMOOTH")
        slot.active_expression = sd.get("active_expression", "NEUTRAL")
        slot.expression_value  = min(sd.get("expression_value",  0.05), 0.05)
        slot.geo_edit_mode     = sd.get("geo_edit_mode",     "NONE")
        slot.geo_intensity     = sd.get("geo_intensity",     1.0)
        slot.eye_L_loc_x = sd.get("eye_L_loc_x",  0.106646)
        slot.eye_L_loc_y = sd.get("eye_L_loc_y",  0.270456)
        slot.eye_L_loc_z = sd.get("eye_L_loc_z",  1.700815)
        slot.eye_L_rot_x = sd.get("eye_L_rot_x",  0.0)
        slot.eye_L_rot_y = sd.get("eye_L_rot_y",  0.0)
        slot.eye_L_rot_z = sd.get("eye_L_rot_z",  0.0)
        slot.eye_L_sca_x = sd.get("eye_L_sca_x",  1.555)
        slot.eye_L_sca_y = sd.get("eye_L_sca_y",  0.496018)
        slot.eye_L_sca_z = sd.get("eye_L_sca_z",  3.55)
        slot.eye_R_loc_x = sd.get("eye_R_loc_x", -0.1053)
        slot.eye_R_loc_y = sd.get("eye_R_loc_y",  0.256331)
        slot.eye_R_loc_z = sd.get("eye_R_loc_z",  1.700426)
        slot.eye_R_rot_x = sd.get("eye_R_rot_x",  0.0)
        slot.eye_R_rot_y = sd.get("eye_R_rot_y",  0.0)
        slot.eye_R_rot_z = sd.get("eye_R_rot_z",  0.0)
        slot.eye_R_sca_x = sd.get("eye_R_sca_x",  1.555)
        slot.eye_R_sca_y = sd.get("eye_R_sca_y",  0.496018)
        slot.eye_R_sca_z = sd.get("eye_R_sca_z",  3.55)

    # Parpadeo
    pb = data.get("parpadeo", {})
    if pb:
        eye_s.blink_enabled     = pb.get("enabled",     False)
        eye_s.blink_count       = pb.get("count",       2)
        eye_s.blink_duration    = pb.get("duration",    9)
        eye_s.blink_frame_start = pb.get("frame_start", 1)
        eye_s.blink_frame_end   = pb.get("frame_end",   60)

        # Restaurar la coleccion completa de intervalos de parpadeo
        intervals_data = pb.get("blink_intervals", [])
        if intervals_data:
            st.blink_intervals.clear()
            for bd in intervals_data:
                bi = st.blink_intervals.add()
                bi.label          = bd.get("label",          "Parpadeo")
                bi.frame_start    = bd.get("frame_start",    1)
                bi.frame_end      = bd.get("frame_end",      60)
                bi.blink_count    = bd.get("blink_count",    2)
                bi.blink_duration = bd.get("blink_duration", 9)
                bi.enabled        = bd.get("enabled",        True)
            st.blink_interval_idx = min(
                pb.get("blink_interval_idx", 0),
                max(0, len(st.blink_intervals) - 1)
            )

    # ── Setup shape keys — PRIMERO aplicar los valores, LUEGO recrear ────────
    sk = data.get("shape_keys_setup", {})
    if sk:
        # Aplicar todos los parámetros de configuración al eye_s
        try:
            eye_s.subdivide_cuts     = sk.get("subdivide_cuts",    2)
        except Exception:
            pass
        try:
            eye_s.curve_mode         = sk.get("curve_mode",        "SMOOTH")
        except Exception:
            pass
        try:
            eye_s.affect_zone        = sk.get("affect_zone",       "FULL")
        except Exception:
            pass
        eye_s.swap_axes          = sk.get("swap_axes",          False)
        eye_s.invert_vertical    = sk.get("invert_vertical",    False)
        eye_s.invert_horizontal  = sk.get("invert_horizontal",  False)

        # Recrear shape keys automáticamente con el setup recién restaurado
        try:
            result = bpy.ops.cerdo_1_st.build_eye_shape_keys()
            if result == {"FINISHED"}:
                print("[Cerdo_1] Shape keys recreados automáticamente al importar config de ojos")
            else:
                print("[Cerdo_1] ADVERTENCIA: build_eye_shape_keys no pudo ejecutarse — hazlo manualmente")
        except Exception as e:
            print(f"[Cerdo_1] No se pudo recrear shape keys automáticamente: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# OPERADORES EXPORTAR / IMPORTAR CONFIGURACION DE OJOS
# ─────────────────────────────────────────────────────────────────────────────

class CERDO_1_ST_OT_SaveEyeConfig(Operator):
    bl_idname    = "cerdo_1_st.save_eye_config"
    bl_label     = "Exportar configuracion de ojos"
    bl_description = (
        "Guarda la secuencia completa de ojos (inicio / intermedios / fin + parpadeo) "
        "como archivo .json en la carpeta de configuraciones de ojos"
    )
    bl_options = {"REGISTER"}

    config_name: bpy.props.StringProperty(
        name="Nombre del archivo",
        default="ojos_config",
        description="Nombre del archivo (sin .json)",
    )

    def invoke(self, context, event):
        self.config_name = context.scene.cerdo_1_st.eye_config_name or "ojos_config"
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        layout = self.layout
        st     = context.scene.cerdo_1_st
        layout.label(text="Nombre del archivo:", icon="FILE_BLANK")
        layout.prop(self, "config_name", text="")
        layout.separator()
        _FORBIDDEN = set('/\\:*?"<>|')
        safe  = "".join(c if c not in _FORBIDDEN else "_" for c in self.config_name).strip()
        fname = f"{safe or 'ojos_config'}.json"
        layout.label(text=f"  -> {os.path.join(DEFAULT_EYE_CONFIG_DIR, fname)}", icon="INFO")
        layout.separator()
        layout.label(text="Se guardara la secuencia completa de ojos:", icon="CHECKMARK")
        layout.label(text=f"  - INICIO: duracion + interp")
        n = len(st.eye_slots)
        layout.label(text=f"  - {n} cambio(s) intermedio(s) con transforms + expresion + geo")
        layout.label(text=f"  - FIN: duracion + interp")
        layout.label(text=f"  - Parpadeo: {'activado' if st.eye_expr.blink_enabled else 'desactivado'}")
        n_ei = len(st.expr_intervals)
        layout.label(text=f"  - Expresion por intervalos: "
                           f"{'activado' if st.eye_expr.expr_intervals_enabled else 'desactivado'}"
                           f" ({n_ei} intervalo(s))")

    def execute(self, context):
        st = context.scene.cerdo_1_st

        _FORBIDDEN = set('/\\:*?"<>|')
        safe = "".join(c if c not in _FORBIDDEN else "_" for c in self.config_name).strip()
        if not safe:
            safe = "ojos_config"
        filename = f"{safe}.json"
        st.eye_config_name = self.config_name

        out_dir = DEFAULT_EYE_CONFIG_DIR
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            self.report({"ERROR"}, f"No se pudo crear la carpeta: {e}")
            return {"CANCELLED"}

        filepath = os.path.join(out_dir, filename)
        cfg = _serialize_eye_config(st)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.report({"ERROR"}, f"Error al escribir: {e}")
            return {"CANCELLED"}

        self.report({"INFO"},
            f"Config ojos guardada: {filename}  "
            f"({len(st.eye_slots)} slot(s))  ->  {filepath}")
        return {"FINISHED"}


class CERDO_1_ST_OT_LoadEyeConfig(Operator):
    bl_idname    = "cerdo_1_st.load_eye_config"
    bl_label     = "Importar configuracion de ojos"
    bl_description = (
        "Carga una configuracion de ojos desde un .json. "
        "Restaura inicio / intermedios / fin y parpadeo"
    )
    bl_options = {"REGISTER", "UNDO"}

    filepath:    bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        start = DEFAULT_EYE_CONFIG_DIR
        if os.path.isdir(start):
            self.filepath = start + os.sep
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        st   = context.scene.cerdo_1_st
        path = bpy.path.abspath(self.filepath)

        if not os.path.isfile(path):
            self.report({"ERROR"}, f"Archivo no encontrado: {path}")
            return {"CANCELLED"}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.report({"ERROR"}, f"Error al leer: {e}")
            return {"CANCELLED"}

        if "eye_slots" not in data and "eye_inicio" not in data:
            self.report({"WARNING"},
                "El archivo no parece una configuracion de ojos de Cerdo_1 Studio")

        _aplicar_eye_config(st, data)

        n      = len(st.eye_slots)
        ts     = data.get("timestamp", "")[:19].replace("T", " ")
        has_sk = bool(data.get("shape_keys_setup"))
        sk_msg = "  — Shape keys recreados automaticamente" if has_sk else ""
        self.report({"INFO"},
            f"Config ojos cargada: {os.path.basename(path)}  "
            f"{ts}  ({n} slot(s)){sk_msg}")
        return {"FINISHED"}


