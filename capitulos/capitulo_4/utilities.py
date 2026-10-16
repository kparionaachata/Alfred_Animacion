#!/usr/bin/env python3
"""
utilities.py - Funciones de utilidad y helpers del sistema Multi-Entity Animation Blocks Manager
Contiene funciones auxiliares, validaciones y herramientas comunes
"""

import bpy
import os
import json
import datetime
import importlib.util
import math
import mathutils

# ============================================================================
# FUNCIONES DE SOPORTE GENERALES
# ============================================================================

def get_blocks_manager():
    """Retorna la instancia global del manager"""
    # CORRECCIÓN: Usar importaciones absolutas
    import core_system
    return core_system.blocks_manager

def show_translation_examples():
    """Muestra ejemplos de traducciones disponibles para debugging"""
    # CORRECCIÓN: Usar importaciones absolutas
    from translation_system import show_translation_examples as _show_translation_examples
    return _show_translation_examples()

# ============================================================================
# FUNCIONES DE VALIDACIÓN
# ============================================================================

def validate_animation_file(filepath: str) -> dict:
    """Valida un archivo de animación - SOLO TEXTO, sin importar módulos"""
    try:
        print(f"      🔍 Validando archivo: {os.path.basename(filepath)}")

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Buscar función execute_ (solo patrón de texto)
        import re
        execute_functions = re.findall(r'def (execute_\w+)\(', content)
        print(f"      📋 Funciones execute_ encontradas: {execute_functions}")

        if not execute_functions:
            return {"valid": False, "error": "No contiene función execute_*"}

        # Extraer información básica
        result = {
            "valid": True,
            "name": os.path.splitext(os.path.basename(filepath))[0],
            "frame_count": 48,  # Default - será sobrescrito por metadata
            "fps": 24,
            "description": "Animación cargada"
        }

        # Intentar extraer información del ANIMATION_INFO si existe
        if "ANIMATION_INFO =" in content:
            try:
                # Buscar el diccionario ANIMATION_INFO
                info_match = re.search(r'ANIMATION_INFO\s*=\s*\{(.*?)\}', content, re.DOTALL)
                if info_match:
                    print(f"      ✅ ANIMATION_INFO encontrado en {os.path.basename(filepath)}")
                    # Intentar parsear el diccionario
                    info_dict = {}
                    info_content = info_match.group(1)
                    # Extraer valores simples
                    frame_match = re.search(r"'frame_count'\s*:\s*(\d+)", info_content)
                    if frame_match:
                        result['frame_count'] = int(frame_match.group(1))
                    fps_match = re.search(r"'fps'\s*:\s*(\d+)", info_content)
                    if fps_match:
                        result['fps'] = int(fps_match.group(1))
                    name_match = re.search(r"'name'\s*:\s*'([^']+)'", info_content)
                    if name_match:
                        result['name'] = name_match.group(1)
            except Exception as info_e:
                print(f"      ⚠️ Error parseando ANIMATION_INFO: {info_e}")

        print(f"      ✅ Archivo válido: {result['name']} ({result['frame_count']} frames)")
        return result

    except Exception as e:
        print(f"      ❌ Error validando archivo: {e}")
        return {"valid": False, "error": str(e)}

# ============================================================================
# FUNCIONES DE CARGA Y GESTIÓN
# ============================================================================

def load_animation_block(slot: int, animation_file: str) -> bool:
    """Carga una animación en un slot específico (función de compatibilidad)"""
    try:
        # CORRECCIÓN: Usar importaciones absolutas
        import core_system
        blocks_manager = core_system.blocks_manager

        print(f"🎬 Cargando animación en slot {slot}: {os.path.basename(animation_file)}")

        if slot not in blocks_manager.blocks:
            print(f"❌ Slot {slot} no existe")
            return False

        # Validar archivo
        validation = validate_animation_file(animation_file)
        if not validation["valid"]:
            print(f"❌ Archivo inválido: {validation['error']}")
            return False

        # Actualizar bloque
        blocks_manager.blocks[slot].update({
            'name': validation['name'],
            'file_path': animation_file,
            'frame_count': validation['frame_count'],
            'is_loaded': True,
            'description': validation['description'],
            'fps': validation['fps']
        })

        print(f"✅ Animación '{validation['name']}' cargada en slot {slot} ({validation['frame_count']} frames)")
        return True

    except Exception as e:
        print(f"❌ Error cargando animación: {e}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# FUNCIONES DE UI Y VISUALIZACIÓN
# ============================================================================

def initialize_slot_indicators():
    """Inicializa indicadores visuales para cada slot"""
    # CORRECCIÓN: Usar importaciones absolutas
    import core_system
    for i in range(1, core_system.blocks_manager.max_slots + 1):
        core_system.blocks_manager.active_slot_indicators[i] = False

def initialize_entity_slot_indicators(entity_name: str):
    """Inicializa indicadores visuales para una entidad específica"""
    # CORRECCIÓN: Usar importaciones absolutas
    import core_system
    if entity_name not in core_system.blocks_manager.active_entity_slot_indicators:
        core_system.blocks_manager.active_entity_slot_indicators[entity_name] = {}
        # Inicializar slots 1-20 para esta entidad
        for slot in range(1, 21):
            core_system.blocks_manager.active_entity_slot_indicators[entity_name][slot] = False

def update_visual_indicators(current_frame: int):
    """Actualiza los indicadores visuales según el frame actual"""
    # CORRECCIÓN: Usar importaciones absolutas
    import core_system
    blocks_manager = core_system.blocks_manager

    # Limpiar indicadores anteriores
    for slot in blocks_manager.active_slot_indicators:
        blocks_manager.active_slot_indicators[slot] = False

    for entity_name in blocks_manager.active_entity_slot_indicators:
        for slot in blocks_manager.active_entity_slot_indicators[entity_name]:
            blocks_manager.active_entity_slot_indicators[entity_name][slot] = False

    # Verificar qué slots están activos en el frame actual
    for slot, frame_range in blocks_manager.sequence_frame_ranges.items():
        if frame_range['start_frame'] <= current_frame <= frame_range['end_frame']:
            blocks_manager.active_slot_indicators[slot] = True

    # Verificar slots por entidad
    for entity_name, entity_data in blocks_manager.entities.items():
        entity_controller = entity_data.get('controller')
        if entity_controller:
            for slot, frame_range in entity_controller.slot_frame_ranges.items():
                if frame_range['start_frame'] <= current_frame <= frame_range['end_frame']:
                    if entity_name not in blocks_manager.active_entity_slot_indicators:
                        initialize_entity_slot_indicators(entity_name)
                    blocks_manager.active_entity_slot_indicators[entity_name][slot] = True

def register_visual_indicators_handler():
    """Registra el handler para indicadores visuales en tiempo real"""
    def frame_change_handler(scene):
        update_visual_indicators(scene.frame_current)

    # Remover handlers existentes
    handlers_to_remove = []
    for handler in bpy.app.handlers.frame_change_post:
        if hasattr(handler, '__name__') and 'frame_change_handler' in handler.__name__:
            handlers_to_remove.append(handler)

    for handler in handlers_to_remove:
        bpy.app.handlers.frame_change_post.remove(handler)

    # Agregar nuevo handler
    bpy.app.handlers.frame_change_post.append(frame_change_handler)
    print("✅ Handler de indicadores visuales registrado")

def unregister_visual_indicators_handler():
    """Desregistra el handler de indicadores visuales"""
    handlers_to_remove = []
    for handler in bpy.app.handlers.frame_change_post:
        if hasattr(handler, '__name__') and 'frame_change_handler' in handler.__name__:
            handlers_to_remove.append(handler)

    for handler in handlers_to_remove:
        bpy.app.handlers.frame_change_post.remove(handler)
        print("🗑️ Handler de indicadores visuales removido")

# ============================================================================
# FUNCIONES DE ANIMACIÓN RELATIVA
# ============================================================================

def toggle_narrative_mode():
    """Alterna entre modo coherencia visual y modo narrativa expresiva"""
    # CORRECCIÓN: Usar importaciones absolutas
    import core_system
    core_system.blocks_manager.narrative_mode = not core_system.blocks_manager.narrative_mode
    print(f"🎭 Modo narrativo: {'ACTIVADO' if core_system.blocks_manager.narrative_mode else 'DESACTIVADO'}")
    return core_system.blocks_manager.narrative_mode

def capture_all_base_orientations():
    """Captura las orientaciones base de todas las entidades"""
    # CORRECCIÓN: Usar importaciones absolutas
    import core_system
    blocks_manager = core_system.blocks_manager

    if not blocks_manager.entities:
        print("⚠️ No hay entidades para capturar orientaciones")
        return False

    success_count = 0
    for entity_name, entity_data in blocks_manager.entities.items():
        entity_controller = entity_data.get('controller')
        if entity_controller:
            if entity_controller.capture_base_orientation():
                success_count += 1

    if success_count > 0:
        print(f"✅ Orientaciones capturadas: {success_count}/{len(blocks_manager.entities)} entidades")
        return True
    else:
        print("❌ Error capturando orientaciones base")
        return False

# ============================================================================
# FUNCIONES DE COMPATIBILIDAD
# ============================================================================

def calculate_total_frames():
    """Calcula el total de frames de todos los bloques cargados"""
    # CORRECCIÓN: Usar importaciones absolutas
    import core_system
    total = 0
    for block in core_system.blocks_manager.blocks.values():
        if block['is_loaded']:
            total += block['frame_count']
    return total

def get_loaded_blocks_sequence():
    """Retorna lista de bloques cargados para compatibilidad"""
    # CORRECCIÓN: Usar importaciones absolutas
    import core_system
    sequence = []
    for slot in range(1, core_system.blocks_manager.max_slots + 1):
        if core_system.blocks_manager.blocks[slot]['is_loaded']:
            block_data = core_system.blocks_manager.blocks[slot].copy()
            block_data['slot'] = slot
            sequence.append(block_data)
    return sequence

# ============================================================================
# FUNCIONES DE CARGA DE PROMPT
# ============================================================================

def load_prompt_folder(folder_path: str) -> bool:
    """Carga una carpeta Prompt_X completa con metadata.json"""
    try:
        # CORRECCIÓN: Usar importaciones absolutas en lugar de relativas
        import core_system
        blocks_manager = core_system.blocks_manager
        from entity_system import EntityController
        from translation_system import translate_entity_name, find_blend_file_with_translation

        print(f"CARGANDO CARPETA PROMPT: {os.path.basename(folder_path) if folder_path else 'None'}")

        if not folder_path or not os.path.exists(folder_path):
            print(f"ERROR: Carpeta no existe o path vacio: '{folder_path}'")
            return False

        # Buscar metadata.json
        metadata_path = os.path.join(folder_path, "metadata.json")
        if not os.path.exists(metadata_path):
            print(f"❌ No se encontró metadata.json en: {folder_path}")
            return False

        # Cargar metadata
        with open(metadata_path, 'r', encoding='utf-8') as f:
            blocks_manager.prompt_metadata = json.load(f)

        blocks_manager.current_prompt_folder = folder_path

        print(f"✅ Metadata cargada: {blocks_manager.prompt_metadata.get('prompt_info', {}).get('original_prompt', 'Sin descripción')[:50]}...")

        # Detectar tipo de estructura
        subdirs = [d for d in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, d)) and not d.startswith('.')]

        if subdirs:
            # NUEVA ESTRUCTURA: Separar ecenario de entidades
            scenario_dir = None
            entity_dirs = []

            for subdir in subdirs:
                # FILTRAR: Excluir carpeta 'ecena' específicamente
                if subdir.lower() == 'ecena':
                    print(f"ℹ️ Carpeta '{subdir}' excluida del procesamiento (carpeta especial)")
                    continue
                elif subdir.lower() == 'ecenario':
                    scenario_dir = subdir
                else:
                    entity_dirs.append(subdir)

            if scenario_dir:
                print(f"🎬 Estructura nueva detectada: carpeta 'ecenario/' + {len(entity_dirs)} entidades")
                success = load_new_scenario_entity_structure(folder_path, scenario_dir, entity_dirs)
            else:
                print(f"INFO: Detectadas {len(subdirs)} carpetas de entidad (sin carpeta ecenario): {', '.join(subdirs)}")
                # Estructura por entidades (anterior)
                success = load_entity_based_structure(folder_path, subdirs)
        else:
            print("INFO: Estructura de archivos planos detectada")
            # Estructura antigua (compatibilidad)
            success = load_flat_structure(folder_path)

        if success:
            # CORRECCIÓN: Eliminar completamente la importación relativa problemática
            # Configurar timeline compartido (comentado para evitar errores)
            # try:
            #     from animation_engine import setup_shared_timeline
            #     setup_shared_timeline()
            # except ImportError:
            #     print("⚠️ setup_shared_timeline no disponible")

            # NUEVO: Procesar objetos dinámicos si el sistema está disponible
            if blocks_manager.dynamic_objects_enabled and blocks_manager.prompt_metadata:
                process_dynamic_objects_for_prompt()

            print("✅ Configuración de carpeta completada")

            print(f"SUCCESS: CARPETA PROMPT '{os.path.basename(folder_path)}' CARGADA")
            print(f"INFO: {len(blocks_manager.entities)} entidades configuradas")
            if blocks_manager.dynamic_objects_enabled:
                total_objects = sum(len(objects) for objects in blocks_manager.imported_dynamic_objects.values())
                print(f"🎭 OBJETOS DINÁMICOS: {total_objects} objetos importados automáticamente")
            return True
        else:
            print("ERROR: Error cargando estructura")
            return False

    except Exception as e:
        print(f"ERROR: Error cargando carpeta prompt: {e}")
        import traceback
        traceback.print_exc()
        return False

def load_entity_based_structure(folder_path: str, entity_dirs: list) -> bool:
    """Carga estructura organizada por entidades (cada entidad en su carpeta)"""
    try:
        # CORRECCIÓN: Usar importaciones absolutas
        import core_system
        blocks_manager = core_system.blocks_manager
        from entity_system import EntityController
        from translation_system import translate_entity_name, find_blend_file_with_translation

        print("🎭 CARGANDO ESTRUCTURA POR ENTIDADES:")

        if not blocks_manager.prompt_metadata or 'entidades' not in blocks_manager.prompt_metadata:
            print("❌ Metadata no contiene información de entidades")
            return False

        entities_config = blocks_manager.prompt_metadata['entidades']
        success_count = 0

        for entity_dir in entity_dirs:
            entity_path = os.path.join(folder_path, entity_dir)

            # Verificar que existe la carpeta
            if not os.path.exists(entity_path):
                print(f"⚠️ Carpeta de entidad no encontrada: {entity_dir}")
                continue

            # FILTRAR: Solo procesar directorios que tengan configuración en metadata
            entity_config = entities_config.get(entity_dir)
            if not entity_config:
                print(f"ℹ️ Carpeta '{entity_dir}' no es una entidad (sin configuración en metadata), omitiendo")
                continue

            print(f"  📦 Procesando entidad: {entity_dir}")

            # Crear EntityController para esta entidad
            entity_controller = EntityController(
                name=entity_dir,
                entity_type=entity_config.get('tipo', 'unknown'),
                blend_file=entity_config.get('estructura_blend_requerida', '')
            )

            # NUEVO: Detectar y cargar script object_importer.py para esta entidad
            object_importer_path = os.path.join(entity_path, 'object_importer.py')
            if os.path.exists(object_importer_path):
                try:
                    # Importar el módulo object_importer dinámicamente
                    spec = importlib.util.spec_from_file_location(f"object_importer_{entity_dir}", object_importer_path)
                    if spec and spec.loader:
                        importer_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(importer_module)

                        # Verificar que tenga la clase ObjectImporter
                        if hasattr(importer_module, 'ObjectImporter'):
                            importer_class = importer_module.ObjectImporter
                            entity_controller.object_importer = importer_class(entity_name=entity_dir)
                            print(f"    ✅ Script object_importer.py cargado para {entity_dir}")
                        else:
                            print(f"    ⚠️ object_importer.py encontrado pero sin clase ObjectImporter para {entity_dir}")
                    else:
                        print(f"    ❌ Error cargando spec para object_importer.py de {entity_dir}")
                except Exception as e:
                    print(f"    ❌ Error importando object_importer.py para {entity_dir}: {e}")
            else:
                print(f"    ℹ️ No se encontró object_importer.py para {entity_dir} (opcional)")

            # Cargar animaciones desde archivos slot_xxx_*.py
            py_files = [f for f in os.listdir(entity_path) if f.endswith('.py') and f.startswith('slot_')]
            print(f"    🎬 Encontrados {len(py_files)} archivos de animación: {py_files}")

            loaded_count = 0
            for py_file in py_files:
                filepath = os.path.join(entity_path, py_file)

                # Extraer slot del nombre del archivo (slot_001_accion.py)
                slot_match = extract_slot_from_filename(py_file)
                print(f"      🔍 Procesando {py_file} → Slot {slot_match}")

                if slot_match:
                    success = entity_controller.load_animation_block(slot_match, filepath)
                    if success:
                        # SINCRONIZAR CON METADATA: Actualizar frame_count usando datos del metadata.json
                        if blocks_manager.prompt_metadata and 'scenes' in blocks_manager.prompt_metadata:
                            for scene in blocks_manager.prompt_metadata['scenes']:
                                # CORRECCIÓN: slot_assigned corresponde al slot, y verificar que pertenece a la entidad actual
                                if scene.get('slot_assigned') == slot_match and scene.get('entity') == entity_dir:
                                    # Usar directamente frame_count del metadata si existe, sino calcular desde duration_seconds
                                    metadata_frames = scene.get('frame_count')
                                    if metadata_frames is None:
                                        metadata_duration = scene.get('duration_seconds', 2.0)
                                        metadata_frames = int(metadata_duration * 24)  # 24 FPS

                                    entity_controller.blocks[slot_match]['frame_count'] = metadata_frames
                                    entity_controller.blocks[slot_match]['fps'] = 24
                                    print(f"      ✅ Slot {slot_match}: {os.path.splitext(py_file)[0]} ({metadata_frames} frames desde metadata)")
                                    break
                        else:
                            print(f"      ✅ Slot {slot_match}: {os.path.splitext(py_file)[0]}")
                        loaded_count += 1
                    else:
                        print(f"      ❌ Error en slot {slot_match}: {py_file}")
                else:
                    print(f"      ⚠️ No se pudo determinar slot para: {py_file}")

            print(f"    📊 Animaciones cargadas: {loaded_count}/{len(py_files)}")

            # Guardar entidad configurada (preservando estado de carga)
            existing_entity = blocks_manager.entities.get(entity_dir, {})

            # PRESERVAR ESTADO DEL CONTROLLER SI LA ESTRUCTURA YA ESTÁ CARGADA
            try:
                if existing_entity.get('is_loaded', False):
                    prev_controller = existing_entity.get('controller')
                    # Adoptar player_parts si existen
                    if prev_controller and hasattr(prev_controller, 'player_parts'):
                        prev_parts = prev_controller.player_parts
                        if isinstance(prev_parts, dict) and len([o for o in prev_parts.values() if o is not None]) > 0:
                            entity_controller.player_parts = prev_parts.copy()
                            entity_controller.is_loaded = True
                            # Usar archivo .blend real previamente cargado si existe
                            if existing_entity.get('blend_file'):
                                entity_controller.blend_file = existing_entity.get('blend_file')
                            print(f"    🔄 Partes preservadas para {entity_dir}: {len([k for k,v in entity_controller.player_parts.items() if v is not None])} encontradas")
                        else:
                            # Re-detectar desde escena en caso de que no haya partes válidas
                            resolved = entity_controller.find_entity_parts()
                            print(f"    🔍 Re-detección de partes para {entity_dir}: {'OK' if resolved else 'sin resultados'}")
                    else:
                        resolved = entity_controller.find_entity_parts()
                        print(f"    🔍 Re-detección de partes para {entity_dir}: {'OK' if resolved else 'sin resultados'}")
            except Exception as e:
                print(f"    ⚠️ Error preservando/re-detectando partes para {entity_dir}: {e}")

            blocks_manager.entities[entity_dir] = {
                'name': entity_dir,
                'type': entity_config.get('tipo', 'unknown'),
                'blend_file': existing_entity.get('blend_file', entity_config.get('estructura_blend_requerida', '')),
                'suggested_blend_file': entity_config.get('estructura_blend_requerida', ''),
                'assigned_slots': entity_config.get('slots_asignados', []),
                'transform_offset': entity_config.get('transform_global', {}),
                'description': entity_config.get('descripcion', ''),
                'is_loaded': existing_entity.get('is_loaded', False),
                'scene_objects': existing_entity.get('scene_objects', []),
                'controller': entity_controller
            }

            loaded_animations = len([b for b in entity_controller.blocks.values() if b['is_loaded']])
            print(f"    📊 Animaciones cargadas: {loaded_animations}")
            success_count += 1

        print(f"🎉 Estructura por entidades cargada: {success_count}/{len(entity_dirs)} entidades")
        return success_count > 0

    except Exception as e:
        print(f"❌ Error cargando estructura por entidades: {e}")
        import traceback
        traceback.print_exc()
        return False

def load_new_scenario_entity_structure(folder_path: str, scenario_dir: str, entity_dirs: list) -> bool:
    """Carga nueva estructura con carpeta ecenario/ separada de entidades"""
    try:
        # CORRECCIÓN: Usar importaciones absolutas
        import core_system
        blocks_manager = core_system.blocks_manager
        from entity_system import EntityController
        from translation_system import translate_entity_name, find_blend_file_with_translation

        print("🎬 CARGANDO NUEVA ESTRUCTURA: ESCENARIO + ENTIDADES")

        if not blocks_manager.prompt_metadata or 'entidades' not in blocks_manager.prompt_metadata:
            print("❌ Metadata no contiene información de entidades")
            return False

        entities_config = blocks_manager.prompt_metadata['entidades']
        success_count = 0

        # PRIMERO: Procesar carpeta ECENARIO
        scenario_path = os.path.join(folder_path, scenario_dir)
        if os.path.exists(scenario_path):
            print(f"🎭 Procesando carpeta ESCENARIO: {scenario_dir}")

            # Crear entidad especial para escenario (si no existe en metadata)
            if 'ecenario' not in entities_config:
                entities_config['ecenario'] = {
                    'tipo': 'scenario',
                    'descripcion': 'Escenario y mundo compartido',
                    'slots_asignados': []
                }

            # Crear EntityController para escenario
            scenario_controller = EntityController(
                name='ecenario',
                entity_type='scenario',
                blend_file=None  # El escenario no tiene .blend específico
            )

            # Cargar animaciones de escenario desde archivos slot_xxx_*.py
            py_files = [f for f in os.listdir(scenario_path) if f.endswith('.py') and f.startswith('slot_')]
            print(f"    🎬 Encontrados {len(py_files)} archivos de escenario: {py_files}")

            loaded_count = 0
            for py_file in py_files:
                filepath = os.path.join(scenario_path, py_file)

                # Extraer slot del nombre del archivo
                slot_match = extract_slot_from_filename(py_file)
                print(f"      🔍 Procesando escenario {py_file} → Slot {slot_match}")

                if slot_match:
                    success = scenario_controller.load_animation_block(slot_match, filepath)
                    if success:
                        # SINCRONIZAR CON METADATA: Buscar en scenes asignadas al escenario
                        if blocks_manager.prompt_metadata and 'scenes' in blocks_manager.prompt_metadata:
                            for scene in blocks_manager.prompt_metadata['scenes']:
                                # Buscar escenas asignadas al escenario
                                if scene.get('slot_assigned') == slot_match and scene.get('entity', '').lower() == 'ecenario':
                                    metadata_frames = scene.get('frame_count')
                                    if metadata_frames is None:
                                        metadata_duration = scene.get('duration_seconds', 2.0)
                                        metadata_frames = int(metadata_duration * 24)  # 24 FPS

                                    scenario_controller.blocks[slot_match]['frame_count'] = metadata_frames
                                    scenario_controller.blocks[slot_match]['fps'] = 24
                                    print(f"      ✅ Slot {slot_match}: {os.path.splitext(py_file)[0]} ({metadata_frames} frames desde metadata)")
                                    break
                        else:
                            print(f"      ✅ Slot {slot_match}: {os.path.splitext(py_file)[0]}")
                        loaded_count += 1
                    else:
                        print(f"      ❌ Error en slot {slot_match}: {py_file}")

            print(f"    📊 Animaciones de escenario cargadas: {loaded_count}/{len(py_files)}")

            # Guardar entidad escenario
            blocks_manager.entities['ecenario'] = {
                'name': 'ecenario',
                'type': 'scenario',
                'blend_file': None,
                'suggested_blend_file': None,
                'assigned_slots': [],
                'transform_offset': {},
                'description': 'Escenario y mundo compartido',
                'is_loaded': True,  # El escenario siempre está "cargado"
                'scene_objects': [],
                'controller': scenario_controller
            }

            success_count += 1
        else:
            print(f"⚠️ Carpeta de escenario no encontrada: {scenario_path}")

        # SEGUNDO: Procesar carpetas de ENTIDADES (filtrar solo entidades válidas)
        for entity_dir in entity_dirs:
            entity_path = os.path.join(folder_path, entity_dir)

            # Verificar que existe la carpeta
            if not os.path.exists(entity_path):
                print(f"⚠️ Carpeta de entidad no encontrada: {entity_dir}")
                continue

            # FILTRAR: Solo procesar directorios que tengan configuración en metadata
            entity_config = entities_config.get(entity_dir)
            if not entity_config:
                print(f"ℹ️ Carpeta '{entity_dir}' no es una entidad (sin configuración en metadata), omitiendo")
                continue

            print(f"  📦 Procesando entidad: {entity_dir}")

            # Crear EntityController para esta entidad
            entity_controller = EntityController(
                name=entity_dir,
                entity_type=entity_config.get('tipo', 'unknown'),
                blend_file=entity_config.get('estructura_blend_requerida', '')
            )

            # NUEVO: Detectar y cargar script object_importer.py para esta entidad
            object_importer_path = os.path.join(entity_path, 'object_importer.py')
            if os.path.exists(object_importer_path):
                try:
                    # Importar el módulo object_importer dinámicamente
                    spec = importlib.util.spec_from_file_location(f"object_importer_{entity_dir}", object_importer_path)
                    if spec and spec.loader:
                        importer_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(importer_module)

                        # Verificar que tenga la clase ObjectImporter
                        if hasattr(importer_module, 'ObjectImporter'):
                            importer_class = importer_module.ObjectImporter
                            entity_controller.object_importer = importer_class(entity_name=entity_dir)
                            print(f"    ✅ Script object_importer.py cargado para {entity_dir}")
                        else:
                            print(f"    ⚠️ object_importer.py encontrado pero sin clase ObjectImporter para {entity_dir}")
                    else:
                        print(f"    ❌ Error cargando spec para object_importer.py de {entity_dir}")
                except Exception as e:
                    print(f"    ❌ Error importando object_importer.py para {entity_dir}: {e}")
            else:
                print(f"    ℹ️ No se encontró object_importer.py para {entity_dir} (opcional)")

            # Cargar animaciones desde archivos slot_xxx_*.py
            py_files = [f for f in os.listdir(entity_path) if f.endswith('.py') and f.startswith('slot_')]
            print(f"    🎬 Encontrados {len(py_files)} archivos de animación: {py_files}")

            loaded_count = 0
            for py_file in py_files:
                filepath = os.path.join(entity_path, py_file)

                # Extraer slot del nombre del archivo
                slot_match = extract_slot_from_filename(py_file)
                print(f"      🔍 Procesando {py_file} → Slot {slot_match}")

                if slot_match:
                    success = entity_controller.load_animation_block(slot_match, filepath)
                    if success:
                        # SINCRONIZAR CON METADATA: Actualizar frame_count usando datos del metadata.json
                        if blocks_manager.prompt_metadata and 'scenes' in blocks_manager.prompt_metadata:
                            for scene in blocks_manager.prompt_metadata['scenes']:
                                # CORRECCIÓN: slot_assigned corresponde al slot, y verificar que pertenece a la entidad actual
                                if scene.get('slot_assigned') == slot_match and scene.get('entity') == entity_dir:
                                    # Usar directamente frame_count del metadata si existe, sino calcular desde duration_seconds
                                    metadata_frames = scene.get('frame_count')
                                    if metadata_frames is None:
                                        metadata_duration = scene.get('duration_seconds', 2.0)
                                        metadata_frames = int(metadata_duration * 24)  # 24 FPS

                                    entity_controller.blocks[slot_match]['frame_count'] = metadata_frames
                                    entity_controller.blocks[slot_match]['fps'] = 24
                                    print(f"      ✅ Slot {slot_match}: {os.path.splitext(py_file)[0]} ({metadata_frames} frames desde metadata)")
                                    break
                        else:
                            print(f"      ✅ Slot {slot_match}: {os.path.splitext(py_file)[0]}")
                        loaded_count += 1
                    else:
                        print(f"      ❌ Error en slot {slot_match}: {py_file}")
                else:
                    print(f"      ⚠️ No se pudo determinar slot para: {py_file}")

            print(f"    📊 Animaciones cargadas: {loaded_count}/{len(py_files)}")

            # Guardar entidad configurada (preservando estado de carga)
            existing_entity = blocks_manager.entities.get(entity_dir, {})

            # PRESERVAR ESTADO DEL CONTROLLER SI LA ESTRUCTURA YA ESTÁ CARGADA
            try:
                if existing_entity.get('is_loaded', False):
                    prev_controller = existing_entity.get('controller')
                    # Adoptar player_parts si existen
                    if prev_controller and hasattr(prev_controller, 'player_parts'):
                        prev_parts = prev_controller.player_parts
                        if isinstance(prev_parts, dict) and len([o for o in prev_parts.values() if o is not None]) > 0:
                            entity_controller.player_parts = prev_parts.copy()
                            entity_controller.is_loaded = True
                            # Usar archivo .blend real previamente cargado si existe
                            if existing_entity.get('blend_file'):
                                entity_controller.blend_file = existing_entity.get('blend_file')
                            print(f"    🔄 Partes preservadas para {entity_dir}: {len([k for k,v in entity_controller.player_parts.items() if v is not None])} encontradas")
                        else:
                            # Re-detectar desde escena en caso de que no haya partes válidas
                            resolved = entity_controller.find_entity_parts()
                            print(f"    🔍 Re-detección de partes para {entity_dir}: {'OK' if resolved else 'sin resultados'}")
                    else:
                        resolved = entity_controller.find_entity_parts()
                        print(f"    🔍 Re-detección de partes para {entity_dir}: {'OK' if resolved else 'sin resultados'}")
            except Exception as e:
                print(f"    ⚠️ Error preservando/re-detectando partes para {entity_dir}: {e}")

            blocks_manager.entities[entity_dir] = {
                'name': entity_dir,
                'type': entity_config.get('tipo', 'unknown'),
                'blend_file': existing_entity.get('blend_file', entity_config.get('estructura_blend_requerida', '')),
                'suggested_blend_file': entity_config.get('estructura_blend_requerida', ''),
                'assigned_slots': entity_config.get('slots_asignados', []),
                'transform_offset': entity_config.get('transform_global', {}),
                'description': entity_config.get('descripcion', ''),
                'is_loaded': existing_entity.get('is_loaded', False),
                'scene_objects': existing_entity.get('scene_objects', []),
                'controller': entity_controller
            }

            loaded_animations = len([b for b in entity_controller.blocks.values() if b['is_loaded']])
            print(f"    📊 Animaciones cargadas: {loaded_animations}")
            success_count += 1

        total_entities = 1 + len(entity_dirs)  # escenario + entidades
        print(f"🎉 Nueva estructura cargada: {success_count}/{total_entities} entidades (1 escenario + {len(entity_dirs)} personajes)")
        return success_count > 0

    except Exception as e:
        print(f"❌ Error cargando nueva estructura escenario/entidades: {e}")
        import traceback
        traceback.print_exc()
        return False

def load_flat_structure(folder_path: str) -> bool:
    """Carga estructura antigua de archivos planos (compatibilidad hacia atrás)"""
    try:
        from .core_system import blocks_manager

        print("📄 CARGANDO ESTRUCTURA DE ARCHIVOS PLANOS (compatibilidad):")

        # Crear entidades desde metadata (SIN cargar .blend automáticamente)
        success = create_entities_from_metadata()
        if success:
            # Cargar y distribuir archivos de animación
            load_animations_from_folder(folder_path)
            print("✅ Estructura plana cargada (modo compatibilidad)")
            return True
        else:
            print("❌ Error creando entidades desde metadata")
            return False

    except Exception as e:
        print(f"❌ Error cargando estructura plana: {e}")
        return False

def create_entities_from_metadata() -> bool:
    """Crea todas las entidades definidas en metadata.json (SIN cargar .blend automáticamente)"""
    # CORRECCIÓN: Usar importaciones absolutas
    import core_system
    blocks_manager = core_system.blocks_manager
    from entity_system import EntityController
    from translation_system import translate_entity_name, find_blend_file_with_translation

    if not blocks_manager.prompt_metadata or 'entidades' not in blocks_manager.prompt_metadata:
        print("❌ Metadata no contiene información de entidades")
        return False

    entities_config = blocks_manager.prompt_metadata['entidades']
    print(f"🎭 CREANDO {len(entities_config)} ENTIDADES:")

    success_count = 0
    for entity_name, entity_config in entities_config.items():
        print(f"   📦 Entidad: {entity_name} ({entity_config.get('tipo', 'unknown')})")

        # Crear entidad (sin cargar .blend)
        if create_entity(entity_name, entity_config):
            success_count += 1
            print(f"   ✅ {entity_name} creada (pendiente cargar .blend)")
        else:
            print(f"   ❌ Error creando {entity_name}")

    print(f"📊 Entidades creadas: {success_count}/{len(entities_config)}")
    print(f"💡 Carga manual de .blend requerida en cada columna")
    return success_count > 0

def create_entity(entity_name: str, entity_config: dict) -> bool:
    """Crea una entidad específica desde su configuración con sistema de traducción"""
    try:
        # CORRECCIÓN: Usar importaciones absolutas
        import core_system
        blocks_manager = core_system.blocks_manager
        from entity_system import EntityController
        from translation_system import translate_entity_name, find_blend_file_with_translation

        # Sistema de traducción inteligente para archivos .blend
        blend_file = entity_config.get('blend_file', '')
        suggested_translation = entity_config.get('nombre_traduccion', '')

        # Si no hay blend_file definido, intentar encontrar automáticamente
        resolved_blend_file = ""
        if blend_file:
            # Usar el blend_file especificado en metadata
            if not os.path.isabs(blend_file):
                estructura_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "estructura_lista", blend_file)
                if os.path.exists(estructura_path):
                    resolved_blend_file = estructura_path
                else:
                    print(f"⚠️ Archivo .blend especificado no encontrado: {blend_file}")
        else:
            # Intentar encontrar automáticamente con traducción
            print(f"🔍 Buscando archivo .blend automáticamente para: {entity_name}")
            resolved_blend_file = find_blend_file_with_translation(entity_name)

            if resolved_blend_file:
                print(f"✅ Archivo encontrado automáticamente: {os.path.basename(resolved_blend_file)}")
            else:
                print(f"⚠️ No se encontró archivo .blend para {entity_name} (carga manual requerida)")

        # Si hay traducción sugerida en metadata, usarla
        if suggested_translation and not resolved_blend_file:
            print(f"💡 Usando traducción sugerida: {suggested_translation}")
            resolved_blend_file = find_blend_file_with_translation(suggested_translation)

        # Crear EntityController para esta entidad
        entity_controller = EntityController(
            name=entity_name,
            entity_type=entity_config.get('tipo', 'unknown'),
            blend_file=resolved_blend_file if resolved_blend_file else None
        )

        # Inicializar indicadores visuales para esta entidad
        initialize_entity_slot_indicators(entity_name)

        # Guardar configuración de entidad (preservando estado de carga si ya estaba en escena)
        existing_entity = blocks_manager.entities.get(entity_name, {})
        blocks_manager.entities[entity_name] = {
            'name': entity_name,
            'type': entity_config.get('tipo', 'unknown'),
            'blend_file': resolved_blend_file if resolved_blend_file else existing_entity.get('blend_file'),
            'suggested_blend_file': blend_file,  # Archivo original en metadata
            'translation_used': suggested_translation or translate_entity_name(entity_name),
            'assigned_slots': entity_config.get('slots_asignados', []),
            'transform_offset': entity_config.get('transform_global', {}),
            'description': entity_config.get('descripcion', ''),
            'is_loaded': existing_entity.get('is_loaded', False),  # conservar si ya estaba cargada
            'scene_objects': existing_entity.get('scene_objects', []),  # conservar objetos en escena
            'controller': entity_controller  # EntityController para manejar animaciones
        }

        status = "✅ Archivo encontrado" if resolved_blend_file else "⚠️ Carga manual requerida"
        print(f"✅ Entidad {entity_name} creada ({status})")
        return True

    except Exception as e:
        print(f"❌ Error creando entidad {entity_name}: {e}")
        return False

def load_animations_from_folder(folder_path: str):
    """Carga animaciones desde una carpeta (modo compatibilidad)"""
    # CORRECCIÓN: Usar importaciones absolutas
    import core_system
    blocks_manager = core_system.blocks_manager

    py_files = [f for f in os.listdir(folder_path) if f.endswith('.py') and f.startswith('slot_')]
    print(f"📁 Encontrados {len(py_files)} archivos de animación")

    loaded_count = 0
    for py_file in py_files:
        filepath = os.path.join(folder_path, py_file)

        # Extraer slot del nombre del archivo
        slot_match = extract_slot_from_filename(py_file)
        if slot_match and slot_match <= blocks_manager.max_slots:
            if load_animation_block(slot_match, filepath):
                loaded_count += 1

    print(f"📊 Animaciones cargadas: {loaded_count}/{len(py_files)}")

def extract_slot_from_filename(filename: str) -> int:
    """Extrae el número de slot del nombre del archivo"""
    import re
    match = re.search(r'slot_(\d+)', filename, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def process_dynamic_objects_for_prompt():
    """Procesa objetos dinámicos para el prompt actual"""
    # CORRECCIÓN: Usar importaciones absolutas
    import core_system
    blocks_manager = core_system.blocks_manager

    if not blocks_manager.dynamic_objects_enabled or not blocks_manager.prompt_metadata:
        return

    try:
        # Procesar objetos dinámicos según metadata
        if 'objetos_dinamicos' in blocks_manager.prompt_metadata:
            dynamic_config = blocks_manager.prompt_metadata['objetos_dinamicos']
            print(f"🎭 Procesando {len(dynamic_config)} configuraciones de objetos dinámicos")

            for entity_name, objects_config in dynamic_config.items():
                if entity_name in blocks_manager.entities:
                    # Importar objetos dinámicos para esta entidad
                    imported_objects = blocks_manager.dynamic_objects_importer.import_objects_for_entity(
                        entity_name, objects_config
                    )
                    blocks_manager.imported_dynamic_objects[entity_name] = imported_objects
                    print(f"   ✅ {len(imported_objects)} objetos dinámicos importados para {entity_name}")
    except Exception as e:
        print(f"⚠️ Error procesando objetos dinámicos: {e}")

# ============================================================================
# REGISTRO DEL MÓDULO
# ============================================================================

def register():
    """Registra las funciones de utilidad"""
    print("✅ Utilidades registradas correctamente")

def unregister():
    """Desregistra las funciones de utilidad"""
    print("✅ Utilidades desregistradas correctamente")