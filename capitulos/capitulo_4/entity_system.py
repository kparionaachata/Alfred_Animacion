#!/usr/bin/env python3
"""
entity_system.py - Sistema de gestiÃ³n de entidades del Multi-Entity Animation Blocks Manager
Contiene EntityController y funciones relacionadas con entidades
"""

import bpy
import os
import json
import datetime
import importlib.util
import math
import mathutils

# ============================================================================
# SISTEMA DE ENTIDADES
# ============================================================================

class CharacterOrientationDetector:
    """Detector de orientaciÃ³n de personajes para animaciones relativas"""

    def __init__(self):
        self.detected_orientations = {}

    def capture_base_state(self, entity_name: str) -> dict:
        """Captura el estado base completo del personaje en tiempo=0"""
        try:
            print(f"ðŸ“ DETECTOR: Capturando estado base para {entity_name}")

            # Buscar el root del personaje
            root_empty = None
            for obj in bpy.data.objects:
                if obj.type == 'EMPTY' and obj.name.lower() == entity_name.lower():
                    root_empty = obj
                    break

            if not root_empty:
                print(f"âš ï¸ No se encontrÃ³ empty root para {entity_name}")
                return None

            # Capturar orientaciÃ³n base
            base_state = {
                'entity_name': entity_name,
                'root_location': list(root_empty.location),
                'root_rotation': list(root_empty.rotation_euler),
                'facing_angle': root_empty.rotation_euler.z,  # Ãngulo Z como direcciÃ³n de facing
                'timestamp': datetime.datetime.now().isoformat()
            }

            self.detected_orientations[entity_name] = base_state
            print(f"âœ… Estado base capturado: facing_angle={base_state['facing_angle']:.3f}")
            return base_state

        except Exception as e:
            print(f"âŒ Error capturando estado base: {e}")
            return None

class EntityController:
    """Gestiona una entidad especÃ­fica con sus animaciones"""
    def __init__(self, name, entity_type, blend_file=None):
        self.name = name
        self.entity_type = entity_type  # player, hostile, passive
        self.blend_file = blend_file
        self.is_loaded = False
        self.blocks = {}  # Slots de animaciÃ³n para esta entidad (dinÃ¡micos, sin lÃ­mite)
        self.max_slots = None  # Sin lÃ­mite de slots por entidad
        self.player_parts = {}  # Partes del cuerpo especÃ­ficas de esta entidad
        self.transform_offset = {'location': [0,0,0], 'rotation': [0,0,0], 'scale': 1.0}
        self.slot_frame_ranges = {}  # Almacena los rangos de frames para cada slot durante reproducciÃ³n

        # NUEVO: Sistema de orientaciÃ³n relativa
        self.base_orientation = None  # Estado base capturado
        self.orientation_captured = False  # Si se capturÃ³ la orientaciÃ³n base

        # NUEVO: Sistema de objetos dinÃ¡micos
        self.object_importer = None  # Instancia de ObjectImporter para esta entidad

        # No inicializar slots vacÃ­os - se crean dinÃ¡micamente

    def initialize_entity_slots(self):
        """Ya no inicializa slots vacÃ­os - se crean dinÃ¡micamente cuando se necesitan"""
        # Los slots se crean dinÃ¡micamente en load_animation_block()
        pass

    def load_animation_block(self, slot: int, animation_file: str) -> bool:
        """Carga una animaciÃ³n en un slot especÃ­fico de esta entidad (slots ilimitados)"""
        try:
            print(f"    ðŸŽ¬ Cargando animaciÃ³n en {self.name} slot {slot}: {os.path.basename(animation_file)}")

            # Crear slot dinÃ¡micamente si no existe (sin lÃ­mite)
            if slot not in self.blocks:
                self.blocks[slot] = {
                    'name': '', 'file_path': '', 'frame_count': 0, 'is_loaded': False,
                    'description': '', 'fps': 24, 'rating': 0, 'feedback': '', 'execute_function': None
                }
                print(f"    ðŸ†• Slot {slot} creado dinÃ¡micamente para {self.name}")

            # Validar archivo
            validation = self.validate_animation_file(animation_file)
            if not validation["valid"]:
                print(f"    âŒ Archivo invÃ¡lido: {validation['error']}")
                return False

            # IMPORTAR EL MÃ“DULO Y OBTENER LA FUNCIÃ“N execute_animation
            try:
                # Crear un nombre Ãºnico para el mÃ³dulo basado en el archivo
                module_name = f"animation_slot_{slot}_{self.name}_{os.path.basename(animation_file).replace('.', '_')}"

                # Importar el mÃ³dulo dinÃ¡micamente
                spec = importlib.util.spec_from_file_location(module_name, animation_file)
                if spec and spec.loader:
                    animation_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(animation_module)

                    # Buscar la funciÃ³n execute_animation
                    execute_func = None
                    for attr_name in dir(animation_module):
                        if attr_name.startswith('execute_') and callable(getattr(animation_module, attr_name)):
                            execute_func = getattr(animation_module, attr_name)
                            print(f"    ðŸ“‹ FunciÃ³n encontrada: {attr_name}")
                            break

                    if not execute_func:
                        print(f"    âŒ No se encontrÃ³ funciÃ³n execute_* en {os.path.basename(animation_file)}")
                        return False

                else:
                    print(f"    âŒ Error cargando spec para {os.path.basename(animation_file)}")
                    return False

            except Exception as import_e:
                print(f"    âŒ Error importando mÃ³dulo de animaciÃ³n: {import_e}")
                return False

            # Actualizar bloque con la funciÃ³n importada
            self.blocks[slot].update({
                'name': validation['name'],
                'file_path': animation_file,
                'frame_count': validation['frame_count'],
                'is_loaded': True,
                'description': validation['description'],
                'fps': validation['fps'],
                'execute_function': execute_func  # â† FUNCIÃ“N IMPORTADA
            })

            print(f"    âœ… AnimaciÃ³n '{validation['name']}' cargada en {self.name} slot {slot} ({validation['frame_count']} frames)")
            print(f"    ðŸŽ¯ FunciÃ³n execute_animation asignada correctamente")
            return True

        except Exception as e:
            print(f"    âŒ Error cargando animaciÃ³n en {self.name}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def validate_animation_file(self, filepath: str) -> dict:
        """Valida un archivo de animaciÃ³n - SOLO TEXTO, sin importar mÃ³dulos"""
        try:
            print(f"      ðŸ” Validando archivo: {os.path.basename(filepath)}")

            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Buscar funciÃ³n execute_ (solo patrÃ³n de texto)
            import re
            execute_functions = re.findall(r'def (execute_\w+)\(', content)
            print(f"      ðŸ“‹ Funciones execute_ encontradas: {execute_functions}")

            if not execute_functions:
                return {"valid": False, "error": "No contiene funciÃ³n execute_*"}

            # Extraer informaciÃ³n bÃ¡sica
            result = {
                "valid": True,
                "name": os.path.splitext(os.path.basename(filepath))[0],
                "frame_count": 48,  # Default - serÃ¡ sobrescrito por metadata
                "fps": 24,
                "description": "AnimaciÃ³n cargada"
            }

            # Intentar extraer informaciÃ³n del ANIMATION_INFO si existe
            info_match = None
            if "ANIMATION_INFO =" in content:
                try:
                    # Buscar el diccionario ANIMATION_INFO
                    info_match = re.search(r'ANIMATION_INFO\s*=\s*\{(.*?)\}', content, re.DOTALL)
                    if info_match:
                        print(f"      âœ… ANIMATION_INFO encontrado en {os.path.basename(filepath)}")
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
                    print(f"      âš ï¸ Error parseando ANIMATION_INFO: {info_e}")

            # Extraer frame_count de execute_animation/execute_slot_* si no hay ANIMATION_INFO
            # Solo usar si tiene parámetros start_frame y end_frame
            execute_match = re.search(r'def (execute_(?:animation|slot_\d+))\([^)]*start_frame=(\d+)[^)]*end_frame=(\d+)', content)
            has_params = execute_match is not None and execute_match.group(2) is not None and execute_match.group(3) is not None
            
            if has_params and not info_match:
                func_name = execute_match.group(1)
                start_frame = int(execute_match.group(2))
                end_frame = int(execute_match.group(3))
                calculated_frames = end_frame - start_frame + 1
                result['frame_count'] = calculated_frames
                print(f"      âœ… Frames calculados de {func_name}: {calculated_frames} ({start_frame}-{end_frame})")
            elif not info_match:
                # FALLBACK: Extraer frames del docstring del archivo
                docstring_match = re.search(r'# Frames:\s*(\d+)\s*-\s*(\d+)', content)
                if docstring_match:
                    start_frame = int(docstring_match.group(1))
                    end_frame = int(docstring_match.group(2))
                    calculated_frames = end_frame - start_frame + 1
                    result['frame_count'] = calculated_frames
                    print(f"      âœ… Frames extraÃ­dos del docstring: {calculated_frames} ({start_frame}-{end_frame})")
                else:
                    # Ãšltimo fallback: buscar en scene.frame_set si hay frame_end configurado
                    scene_end_match = re.search(r'scene\.frame_end\s*=\s*(\d+)', content)
                    if scene_end_match:
                        end_frame = int(scene_end_match.group(1))
                        result['frame_count'] = end_frame  # Asumiendo frame_start = 1
                        print(f"      âœ… Frames extraÃ­dos de scene.frame_end: {end_frame}")

            print(f"      âœ… Archivo vÃ¡lido: {result['name']} ({result['frame_count']} frames)")
            return result

        except Exception as e:
            print(f"      âŒ Error validando archivo: {e}")
            return {"valid": False, "error": str(e)}

    def get_loaded_blocks_sequence(self):
        """Retorna lista de bloques cargados para esta entidad (sin lÃ­mite de slots)"""
        sequence = []
        # Iterar sobre todos los slots existentes (sin lÃ­mite)
        for slot in sorted(self.blocks.keys()):
            if self.blocks[slot]['is_loaded']:
                block_data = self.blocks[slot].copy()
                block_data['slot'] = slot
                block_data['entity_name'] = self.name
                sequence.append(block_data)
        return sequence

    # ============================================================================
    # NUEVO: SISTEMA DE ORIENTACIÃ“N RELATIVA
    # ============================================================================

    def capture_base_orientation(self) -> bool:
        """Captura la orientaciÃ³n base del personaje para animaciones relativas"""
        try:
            print(f"ðŸ“ CAPTURANDO ORIENTACIÃ“N BASE para {self.name}")

            # Usar el detector global
            manager = get_blocks_manager()
            if not hasattr(manager, 'orientation_detector') or manager.orientation_detector is None:
                manager.orientation_detector = CharacterOrientationDetector()

            base_state = manager.orientation_detector.capture_base_state(self.name)
            if base_state:
                self.base_orientation = base_state
                self.orientation_captured = True
                print(f"âœ… OrientaciÃ³n base capturada: {base_state['facing_angle']:.1f}Â°")
                return True
            else:
                print(f"âŒ Error capturando orientaciÃ³n base para {self.name}")
                return False

        except Exception as e:
            print(f"âŒ Error en capture_base_orientation: {e}")
            return False

    def get_base_orientation(self):
        """Retorna la orientaciÃ³n base capturada"""
        return self.base_orientation if self.base_orientation else {}

    def has_base_orientation(self) -> bool:
        """Verifica si tiene orientaciÃ³n base capturada"""
        return self.orientation_captured and self.base_orientation is not None

    def reset_base_orientation(self):
        """Resetea la orientaciÃ³n base"""
        self.base_orientation = None
        self.orientation_captured = False
        print(f"ðŸ”„ OrientaciÃ³n base reseteada para {self.name}")

    def find_entity_parts(self):
        """Encuentra las partes del cuerpo de esta entidad en la escena con bÃºsqueda inteligente"""
        entity_prefix = self.name.lower()
        entity_type = self.entity_type.lower()

        # MANEJO ESPECIAL PARA ESCENARIO: No tiene partes del cuerpo
        if entity_type == 'scenario' or self.name.lower() == 'ecenario':
            print(f"ðŸŽ¬ Entidad ESCENARIO '{self.name}': No requiere partes del cuerpo especÃ­ficas")
            self.player_parts = {}  # Escenario no tiene partes del cuerpo
            self.is_loaded = True  # El escenario siempre estÃ¡ "cargado"
            return True

        # BUSCAR ROOT ESPECÃFICO DE LA ENTIDAD
        entity_root = None
        for obj in bpy.data.objects:
            if obj.name.lower() == entity_prefix and len(obj.children) > 0:
                entity_root = obj
                print(f"ðŸŽ¯ Encontrado root especÃ­fico '{entity_prefix}': {obj.name}")
                # ASIGNAR EL ROOT EMPTY COMO 'main' SI ES UN EMPTY OBJECT
                if obj.type == 'EMPTY' and self.player_parts.get('main') is None:
                    self.player_parts['main'] = obj
                    print(f"  âœ… Asignado root Empty como 'main': {obj.name}")
                break

        # BUSCAR EMPTY OBJECT PARA 'main' SI NO SE ASIGNÓ
        if self.player_parts.get('main') is None:
            print(f"  🔍 Buscando Empty para 'main' (entity_prefix: {entity_prefix})...")
            # Buscar Empty con nombre similar al entity_prefix
            for obj in bpy.data.objects:
                if obj.type == 'EMPTY':
                    obj_name_lower = obj.name.lower()
                    print(f"    Checking Empty: {obj.name}")
                    # Exact match primero
                    if obj_name_lower == entity_prefix:
                        self.player_parts['main'] = obj
                        print(f"  ✅ Asignado Empty exacto como 'main': {obj.name}")
                        break
                    # Luego buscar que contenga el nombre sin prefijos
                    elif entity_prefix.replace('main_', '') in obj_name_lower:
                        self.player_parts['main'] = obj
                        print(f"  ✅ Asignado Empty (removiendo 'main_') como 'main': {obj.name}")
                        break
                    # Finalmente cualquier Empty que pueda estar relacionado
                    elif 'guitar' in obj_name_lower and 'ribbit' in obj_name_lower:
                        self.player_parts['main'] = obj
                        print(f"  ✅ Asignado Empty fallback como 'main': {obj.name}")
                        break
            if self.player_parts.get('main') is None:
                print(f"  ❌ No se encontró Empty para 'main'")

        # Si no encontrÃ³ root especÃ­fico, buscar root legacy para compatibilidad
        if not entity_root:
            if entity_prefix == 'alfred':
                for obj in bpy.data.objects:
                    if obj.name.lower() == 'alfred' and len(obj.children) > 0:
                        entity_root = obj
                        print(f"ðŸŽ¯ Encontrado root legacy 'alfred': {obj.name}")
                        # ASIGNAR EL ROOT EMPTY COMO 'main' SI ES UN EMPTY OBJECT
                        if obj.type == 'EMPTY' and self.player_parts.get('main') is None:
                            self.player_parts['main'] = obj
                            print(f"  âœ… Asignado root legacy Empty como 'main': {obj.name}")
                        break
            elif entity_prefix == 'flink':
                for obj in bpy.data.objects:
                    if obj.name.lower() == 'flink' and len(obj.children) > 0:
                        entity_root = obj
                        print(f"ðŸŽ¯ Encontrado root 'flink': {obj.name}")
                        # ASIGNAR EL ROOT EMPTY COMO 'main' SI ES UN EMPTY OBJECT
                        if obj.type == 'EMPTY' and self.player_parts.get('main') is None:
                            self.player_parts['main'] = obj
                            print(f"  âœ… Asignado root flink Empty como 'main': {obj.name}")
                        break
            elif entity_type in ['player', 'character']:
                for obj in bpy.data.objects:
                    if obj.name.lower() == 'player' and len(obj.children) > 0:
                        entity_root = obj
                        print(f"âš ï¸ Usando root alternativo 'player': {obj.name}")
                        # ASIGNAR EL ROOT EMPTY COMO 'main' SI ES UN EMPTY OBJECT
                        if obj.type == 'EMPTY' and self.player_parts.get('main') is None:
                            self.player_parts['main'] = obj
                            print(f"  âœ… Asignado root alternativo Empty como 'main': {obj.name}")
                        break

        # ADICIONAL: Si no tenemos 'main' asignado, buscar cualquier Empty que pueda ser el root
        if self.player_parts.get('main') is None:
            for obj in bpy.data.objects:
                if obj.type == 'EMPTY':
                    obj_name_lower = obj.name.lower()
                    # Buscar Empty que contenga el nombre de la entidad
                    if entity_prefix in obj_name_lower or obj_name_lower in entity_prefix:
                        self.player_parts['main'] = obj
                        print(f"  âœ… Asignado Empty encontrado como 'main': {obj.name}")
                        break
                    # Fallback específico para casos como main_guitar_ribbit -> guitar_ribbit
                    elif entity_prefix.startswith('main_') and entity_prefix[5:] in obj_name_lower:
                        self.player_parts['main'] = obj
                        print(f"  âœ… Asignado Empty (removiendo 'main_') como 'main': {obj.name}")
                        break

        # CORRECCIÓN DE TIPO DE ENTIDAD ANTES DE INICIALIZACIÓN
        # Para entidades que se identifican por nombre, corregir el tipo automáticamente
        if self.name.lower() == 'ribbit':
            entity_type = 'creature_ribbit'
            self.entity_type = 'creature_ribbit'
        elif self.name.lower() in ['guard_ribbit_1', 'guard_ribbit_2', 'guard_ribbit_3', 'guard_ribbit_4', 'guard_ribbit_5', 'guard_ribbit_6', 'guard_ribbit_7', 'guard_ribbit_8', 'guard_ribbit_9']:
            entity_type = 'creature_guard_ribbit'
            self.entity_type = 'creature_guard_ribbit'
        elif self.name.lower() == 'bass_ribbit':
            entity_type = 'creature_bass_ribbit'
            self.entity_type = 'creature_bass_ribbit'
        elif self.name.lower() == 'flink':
            entity_type = 'creature_flink'
            self.entity_type = 'creature_flink'
        elif self.name.lower() == 'zombie':
            entity_type = 'creature_zombie'
            self.entity_type = 'creature_zombie'
        elif self.name.lower() == 'enderdragon':
            entity_type = 'creature_enderdragon'
            self.entity_type = 'creature_enderdragon'
        elif self.name.lower() == 'chicken':
            entity_type = 'chicken'  # Usar 'chicken' no 'creature_chicken'
            self.entity_type = 'chicken'

        # INICIALIZAR PARTES SEGÃšN TIPO DE ENTIDAD
        if entity_type in ['wolf_with_dog_skin', 'wolf', 'dog']:
            # Jerry y entidades similares: partes especÃ­ficas del lobo/perro - TODOS los bones del Dog_001_rig
            self.player_parts = {
                # Partes principales
                'body': None, 'head': None, 'tail': None, 'mane': None, 'leggings': None,
                'leg4': None, 'leg4.001': None, 'leg4.002': None, 'leg4.003': None,
                'boca superior': None, 'boca inferior': None, 'ojos': None,
                'oreja 1': None, 'oreja2': None,
                # TODOS los bones del Dog_001_rig armature
                'spine.004': None, 'spine.003': None, 'spine.002': None, 'spine.001': None, 'spine': None,
                'spine.005': None, 'spine.006': None, 'spine.007': None, 'spine.008': None, 'spine.009': None, 'spine.010': None,
                'scull': None, 'face': None, 'nose': None, 'nose.001': None,
                'lip.T.L': None, 'lip.T.L.001': None, 'jaw': None, 'chin': None,
                'ear.L.002': None, 'ear.R.002': None, 'lip.T.R': None, 'lip.T.R.001': None,
                'forehead.L.002': None, 'jaw.L.001': None, 'cheek.B.L.001': None, 'brow.T.L.001': None,
                'forehead.R.002': None, 'jaw.R.001': None, 'cheek.B.R.001': None, 'brow.T.R.001': None,
                'cheek.T.L.001': None, 'cheek.T.R.001': None, 'teeth.B': None, 'tongue': None, 'tongue.001': None, 'tongue.002': None,
                'front_shoulder.L': None, 'front_thigh.L': None, 'front_shin.L': None, 'front_foot.L': None, 'front_toe.L': None,
                'front_shoulder.R': None, 'front_thigh.R': None, 'front_shin.R': None, 'front_foot.R': None, 'front_toe.R': None,
                'front_shoulder.L.001': None, 'front_shoulder.R.001': None, 'no_bone_001': None,
                'shoulder.L': None, 'shoulder.L.001': None, 'shoulder.R': None, 'shoulder.R.001': None,
                'thigh.L': None, 'shin.L': None, 'foot.L': None, 'toe.L': None,
                'thigh.R': None, 'shin.R': None, 'foot.R': None, 'toe.R': None
            }
        elif entity_type == 'creeper' or self.name.lower() == 'creeper':
            # Creeper: partes especÃ­ficas del creeper
            self.player_parts = {
                'mane': None, 'leggings': None, 'body': None, 'leg4': None, 'leg4.001': None,
                'leg4.002': None, 'leg4.003': None, 'tail': None, 'head': None,
                'boca inferior': None, 'boca superior': None, 'oreja 1': None, 'oreja2': None,
                'ceja 1': None, 'cejas2': None, 'ojos': None
            }
        elif entity_type == 'chicken' or self.name.lower() == 'chicken':
            # Pollo: partes específicas del pollo según chicken_outliner_data.json (34 huesos)
            self.player_parts = {
                # Armature principal
                'armature_name': 'Armature_chicken',
                'Armature_chicken': None,
                # Meshes
                'Body_chicken': None,
                'Head_chicken': None,
                'Head2_chicken': None,
                'Eyes_chicken': None,
                'BeakTop_chicken': None,
                'BeakBottom_chicken': None,
                'WingL_chicken': None,
                'WingR_chicken': None,
                'LegL_chicken': None,
                'LegL.001_chicken': None,
                # === TODOS LOS 34 HUESOS ===
                # Nivel 0 (Roots)
                'Root_M_chicken': None,
                'Knee.Right_chicken': None,
                'Knee.Left_chicken': None,
                # Nivel 1
                'Hip_R_chicken': None,
                'Spine1_M_chicken': None,
                'Hip_L_chicken': None,
                'no_bone_05_chicken': None,
                'no_bone_04_chicken': None,
                'no_bone_02_chicken': None,
                'no_bone_03_chicken': None,
                # Nivel 2
                'Knee_R_chicken': None,
                'Chest_M_chicken': None,
                'no_bone_01_chicken': None,
                'Knee_L_chicken': None,
                # Nivel 3
                'Knee_R_end_chicken': None,
                'Neck_M_chicken': None,
                'Scapula_R_chicken': None,
                'Scapula_L_chicken': None,
                # Nivel 4
                'Head_M_chicken': None,
                'Shoulder_R_chicken': None,
                'Shoulder_L_chicken': None,
                # Nivel 5
                'Jaw_M_chicken': None,
                'Elbow_R_chicken': None,
                'Elbow_L_chicken': None,
                # Nivel 6
                'Jaw_top_chicken': None,
                'Jaw_bot_chicken': None,
                'Elbow_R_end_chicken': None,
                'Elbow_L_end_chicken': None,
                # Otros bones
                'no_bone_06_chicken': None,
                # End bones de tobillos
                'Ankle_R_chicken': None,
                'Ankle_L_chicken': None,
                'Ankle_R_end_chicken': None,
                'Ankle_L_end_chicken': None,
            }
        elif self.name.lower() == 'flink' or entity_type == 'creature_flink':
            # Flink: criatura de Minecraft con bones terminados en "_flink"
            self.player_parts = {
                'body_flink': None, 'head_flink': None, 'eyes_flink': None,
                'body2_flink': None, 'body3_flink': None, 'body4_flink': None, 'body5_flink': None
            }
        elif self.name.lower() == 'ribbit' or entity_type == 'creature_ribbit':
            # Ribbit: criatura de Minecraft
            self.player_parts = {
                'main': None, 'body': None, 'left_arm': None, 'right_arm': None,
                'left_leg': None, 'right_leg': None
            }
        elif self.name.lower() == 'ribbit_2' or entity_type == 'creature_ribbit':
            # Ribbit_2: variante de criatura de Minecraft
            self.player_parts = {
                'main': None, 'body': None, 'left_arm': None, 'right_arm': None,
                'left_leg': None, 'right_leg': None
            }
        elif self.name.lower() == 'ribbit_3' or entity_type == 'creature_ribbit':
            # Ribbit_3: tercera variante de criatura de Minecraft
            self.player_parts = {
                'main': None, 'body': None, 'left_arm': None, 'right_arm': None,
                'left_leg': None, 'right_leg': None
            }
        elif self.name.lower() == 'ribbit_4' or entity_type == 'creature_ribbit':
            # Ribbit_4: cuarta variante de criatura de Minecraft
            self.player_parts = {
                'main': None, 'body': None, 'left_arm': None, 'right_arm': None,
                'left_leg': None, 'right_leg': None
            }
        elif self.name.lower() == 'ribbit_5' or entity_type == 'creature_ribbit':
            # Ribbit_5: quinta variante de criatura de Minecraft
            self.player_parts = {
                'main': None, 'body': None, 'left_arm': None, 'right_arm': None,
                'left_leg': None, 'right_leg': None
            }
        elif self.name.lower() == 'ribbit_6' or entity_type == 'creature_ribbit':
            # Ribbit_6: sexta variante de criatura de Minecraft
            self.player_parts = {
                'main': None, 'body': None, 'left_arm': None, 'right_arm': None,
                'left_leg': None, 'right_leg': None
            }
        elif self.name.lower() == 'ribbit_7' or entity_type == 'creature_ribbit':
            # Ribbit_7: séptima variante de criatura de Minecraft
            self.player_parts = {
                'main': None, 'body': None, 'left_arm': None, 'right_arm': None,
                'left_leg': None, 'right_leg': None
            }
        elif self.name.lower() == 'ribbit_8' or entity_type == 'creature_ribbit':
            # Ribbit_8: octava variante de criatura de Minecraft
            self.player_parts = {
                'main': None, 'body': None, 'left_arm': None, 'right_arm': None,
                'left_leg': None, 'right_leg': None
            }
        elif self.name.lower() in ['guard_ribbit_1', 'guard_ribbit_2', 'guard_ribbit_3', 'guard_ribbit_4', 'guard_ribbit_5', 'guard_ribbit_6', 'guard_ribbit_7', 'guard_ribbit_8', 'guard_ribbit_9'] or entity_type == 'creature_guard_ribbit':
            # Guard Ribbit_1: guardia con armadura completa - sistema multi-armature avanzado
            self.player_parts = {
                # Armature principal (6 huesos)
                'main': None, 'body': None, 'left_arm': None, 'right_arm': None,
                'left_leg': None, 'right_leg': None,
                # Armature adicional - escudo (1 hueso)
                'shield': None,
                # Armature adicional - lanza (1 hueso)
                'spear': None
            }
        elif self.name.lower() == 'bass_ribbit' or entity_type == 'creature_bass_ribbit':
            # Bass Ribbit: variante de ribbit con parte especial de bajo
            self.player_parts = {
                'main': None, 'body': None, 'left_arm': None, 'right_arm': None,
                'left_leg': None, 'right_leg': None, 'bass': None  # Parte especial
            }
        elif self.name.lower() == 'zombie' or entity_type == 'creature_zombie':
            # Zombie: criatura de Minecraft con rig avanzado - TODAS las partes del armature y meshes
            # Inicializar con todas las partes conocidas del zombie (basado en zombie_outliner_data.json)
            self.player_parts = {
                # Partes principales del cuerpo
                'body_zombie': None, 'head_zombie': None, 'left_arm_zombie': None, 'right_arm_zombie': None,
                'left_leg_zombie': None, 'right_leg_zombie': None,
                # Partes adicionales del cuerpo
                'Body_zombie': None, 'Body.003_zombie': None, 'Head_zombie': None, 'Head.002_zombie': None,
                'Head.001_zombie': None, 'Arm.Left_zombie': None, 'Arm.Left.001_zombie': None,
                'Arm.Left.002_zombie': None, 'Arm.Left.003_zombie': None,
                # Partes de dedos y extremidades
                'Cube.004_zombie': None, 'Cube.005_zombie': None, 'Cube.006_zombie': None,
                'Cube.007_zombie': None, 'Cube.008_zombie': None, 'Cube.009_zombie': None,
                'Cube.010_zombie': None, 'Cube.011_zombie': None, 'Cube.012_zombie': None,
                'Cube.013_zombie': None, 'Cube.014_zombie': None, 'Cube.015_zombie': None,
                'Cube.016_zombie': None, 'Cube.017_zombie': None, 'Cube.018_zombie': None,
                'Cube.027_zombie': None,
                # El armature principal con todos sus bones
                'Zombie.arma_zombie': None
            }
        elif self.name.lower() == 'enderdragon' or entity_type == 'creature_enderdragon':
            # Enderdragon: criatura de Minecraft con rig complejo - partes especÃ­ficas del dragÃ³n
            self.player_parts = {
                'main': None,  # Armature principal
                'body': None, 'head': None,
                'left_arm': None, 'right_arm': None,
                'left_leg': None, 'right_leg': None,
                # Partes especÃ­ficas del personaje
                'mainenderdragon_enderdragon': None,
                'ik-foot:front.renderdragon_enderdragon': None,
                'ik-front-pole.renderdragon_enderdragon': None,
                'ik-foot:front.lenderdragon_enderdragon': None,
                'ik-front-pole.lenderdragon_enderdragon': None,
                'ik-foot:back.renderdragon_enderdragon': None,
                'ik-lower:back.renderdragon_enderdragon': None,
                'ik-foot:back.lenderdragon_enderdragon': None,
                'ik-lower:back.lenderdragon_enderdragon': None,
                'body.mainenderdragon_enderdragon': None,
                'body.middleenderdragon_enderdragon': None,
                'chestenderdragon_enderdragon': None,
                'ik-neckenderdragon_enderdragon': None,
                'headenderdragon_enderdragon': None,
                'eyetracking:leftenderdragon_enderdragon': None,
                'eyetracking:rightenderdragon_enderdragon': None,
                'mouth:upperenderdragon_enderdragon': None,
                'mouth:lowerenderdragon_enderdragon': None,
                'eye:leftenderdragon_enderdragon': None,
                'eyetrackingenderdragon_enderdragon': None,
                'eye:rightenderdragon_enderdragon': None,
                'neckenderdragon_enderdragon': None,
                'neck.001enderdragon_enderdragon': None,
                'neck.002enderdragon_enderdragon': None,
                'neck.003enderdragon_enderdragon': None,
                'neck.004enderdragon_enderdragon': None,
                'leg:front:upper:rightenderdragon_enderdragon': None,
                'leg:front:lower:rightenderdragon_enderdragon': None,
                'foot:front.renderdragon_enderdragon': None,
                'leg:front:upper:leftenderdragon_enderdragon': None,
                'leg:front:lower:leftenderdragon_enderdragon': None,
                'foot:front.lenderdragon_enderdragon': None,
                'wing:rightenderdragon_enderdragon': None,
                'wing:right:tipenderdragon_enderdragon': None,
                'wing:leftenderdragon_enderdragon': None,
                'wing:left:tipenderdragon_enderdragon': None,
                'leg:back:upper:leftenderdragon_enderdragon': None,
                'leg:back:lower:leftenderdragon_enderdragon': None,
                'foot:back.lenderdragon_enderdragon': None,
                'leg:back:upper:rightenderdragon_enderdragon': None,
                'leg:back:lower:rightenderdragon_enderdragon': None,
                'foot:back.renderdragon_enderdragon': None,
                'tail_enderdragon': None,
                'tail.001enderdragon_enderdragon': None,
                'tail.002enderdragon_enderdragon': None,
                'tail.003enderdragon_enderdragon': None,
                'tail.004enderdragon_enderdragon': None,
                'tail.005enderdragon_enderdragon': None,
                'tail.006enderdragon_enderdragon': None,
                'tail.007enderdragon_enderdragon': None,
                'tail.008enderdragon_enderdragon': None,
                'tail.009enderdragon_enderdragon': None,
                'tail.010enderdragon_enderdragon': None,
                'tail.011enderdragon_enderdragon': None,
            }
        else:
            # Entidades genÃ©ricas (alfred, etc.)
            self.player_parts = {
                'body': None, 'head': None, 'left_arm': None, 'right_arm': None,
                'left_leg': None, 'right_leg': None
            }


        print(f"ðŸ” Buscando partes para entidad '{self.name}' (tipo: {entity_type})")

        # BÃšSQUEDA INTELIGENTE: mÃºltiples estrategias
        found_any = False

        # Estrategia 1: Si tenemos root especÃ­fico, buscar en sus hijos primero
        if entity_root:
            print(f"ðŸŽ­ Buscando en hijos del root '{entity_root.name}'...")
            for child in entity_root.children:
                child_name = child.name.lower()
                # Buscar partes con sufijo especÃ­fico de entidad (ej: "body_jerry")
                for part in self.player_parts.keys():
                    if child_name == f"{part}_{entity_prefix}":
                        self.player_parts[part] = child
                        print(f"  âœ… Encontrado en root ({entity_prefix}): {child.name} â†’ {part}")
                        found_any = True
                        break
                else:
                    # Si no encontrÃ³ sufijo especÃ­fico, buscar nombre exacto
                    if child_name in self.player_parts:
                        self.player_parts[child_name] = child
                        print(f"  âœ… Encontrado en root (exacto): {child.name}")
                        found_any = True

        # MANEJO ESPECIAL PARA RIBBIT: Criatura con bones terminados en "_ribbit"
        if entity_prefix == 'ribbit':
            print(f"ðŸ¸ Ribbit (con sufijo _ribbit): Buscando armatures con bones _ribbit...")
            # Buscar el armature principal
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'ribbit.001_ribbit':
                    self.player_parts['main'] = obj
                    print(f"  âœ… Armature Ribbit encontrado: {obj.name} â†’ main")
                    found_any = True
                    # Buscar los huesos dentro del armature y mapearlos correctamente
                    ribbit_bone_mapping = {
                        'ribbit_ribbit': 'main',  # Ya asignado arriba
                        'body_ribbit': 'body',
                        'left_arm_ribbit': 'left_arm',
                        'right_arm_ribbit': 'right_arm',
                        'left_leg_ribbit': 'left_leg',
                        'right_leg_ribbit': 'right_leg'
                    }

                    for bone in obj.data.bones:
                        bone_name = bone.name.lower()
                        if bone_name in ribbit_bone_mapping:
                            part_key = ribbit_bone_mapping[bone_name]
                            if part_key in self.player_parts and self.player_parts[part_key] is None:
                                self.player_parts[part_key] = bone
                                print(f"    âœ… Hueso Ribbit mapeado: {bone.name} â†’ {part_key}")
                    break

        # MANEJO ESPECIAL PARA RIBBIT_2: Criatura con bones terminados en "_ribbit_2"
        if entity_prefix == 'ribbit_2':
            print(f"ðŸ¸ Ribbit_2 (con sufijo _ribbit_2): Buscando armatures con bones _ribbit_2...")
            # Buscar el armature principal
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'ribbit.001_ribbit_2':
                    self.player_parts['main'] = obj
                    print(f"  âœ… Armature Ribbit_2 encontrado: {obj.name} â†’ main")
                    found_any = True
                    # Buscar los huesos dentro del armature y mapearlos correctamente
                    ribbit_2_bone_mapping = {
                        'ribbit_ribbit_2': 'main',  # Ya asignado arriba
                        'body_ribbit_2': 'body',
                        'left_arm_ribbit_2': 'left_arm',
                        'right_arm_ribbit_2': 'right_arm',
                        'left_leg_ribbit_2': 'left_leg',
                        'right_leg_ribbit_2': 'right_leg'
                    }

                    for bone in obj.data.bones:
                        bone_name = bone.name.lower()
                        if bone_name in ribbit_2_bone_mapping:
                            part_key = ribbit_2_bone_mapping[bone_name]
                            if part_key in self.player_parts and self.player_parts[part_key] is None:
                                self.player_parts[part_key] = bone
                                print(f"    âœ… Hueso Ribbit_2 mapeado: {bone.name} â†’ {part_key}")
                    break

        # MANEJO ESPECIAL PARA RIBBIT_3: Criatura con bones terminados en "_ribbit_3"
        if entity_prefix == 'ribbit_3':
            print(f"ðŸ¸ Ribbit_3 (con sufijo _ribbit_3): Buscando armatures con bones _ribbit_3...")
            # Buscar el armature principal
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'ribbit.001_ribbit_3':
                    self.player_parts['main'] = obj
                    print(f"  âœ… Armature Ribbit_3 encontrado: {obj.name} â†’ main")
                    found_any = True
                    # Buscar los huesos dentro del armature y mapearlos correctamente
                    ribbit_3_bone_mapping = {
                        'ribbit_ribbit_3': 'main',  # Ya asignado arriba
                        'body_ribbit_3': 'body',
                        'left_arm_ribbit_3': 'left_arm',
                        'right_arm_ribbit_3': 'right_arm',
                        'left_leg_ribbit_3': 'left_leg',
                        'right_leg_ribbit_3': 'right_leg'
                    }

                    for bone in obj.data.bones:
                        bone_name = bone.name.lower()
                        if bone_name in ribbit_3_bone_mapping:
                            part_key = ribbit_3_bone_mapping[bone_name]
                            if part_key in self.player_parts and self.player_parts[part_key] is None:
                                self.player_parts[part_key] = bone
                                print(f"    âœ… Hueso Ribbit_3 mapeado: {bone.name} â†’ {part_key}")
                    break

        # MANEJO ESPECIAL PARA RIBBIT_4: Criatura con bones terminados en "_ribbit_4"
        if entity_prefix == 'ribbit_4':
            print(f"ðŸ¸ Ribbit_4 (con sufijo _ribbit_4): Buscando armatures con bones _ribbit_4...")
            # Buscar el armature principal
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'ribbit.001_ribbit_4':
                    self.player_parts['main'] = obj
                    print(f"  âœ… Armature Ribbit_4 encontrado: {obj.name} â†’ main")
                    found_any = True
                    # Buscar los huesos dentro del armature y mapearlos correctamente
                    ribbit_4_bone_mapping = {
                        'ribbit_ribbit_4': 'main',  # Ya asignado arriba
                        'body_ribbit_4': 'body',
                        'left_arm_ribbit_4': 'left_arm',
                        'right_arm_ribbit_4': 'right_arm',
                        'left_leg_ribbit_4': 'left_leg',
                        'right_leg_ribbit_4': 'right_leg'
                    }

                    for bone in obj.data.bones:
                        bone_name = bone.name.lower()
                        if bone_name in ribbit_4_bone_mapping:
                            part_key = ribbit_4_bone_mapping[bone_name]
                            if part_key in self.player_parts and self.player_parts[part_key] is None:
                                self.player_parts[part_key] = bone
                                print(f"    âœ… Hueso Ribbit_4 mapeado: {bone.name} â†’ {part_key}")
                    break

        # MANEJO ESPECIAL PARA RIBBIT_5: Criatura con bones terminados en "_ribbit_5"
        if entity_prefix == 'ribbit_5':
            print(f"ðŸ¸ Ribbit_5 (con sufijo _ribbit_5): Buscando armatures con bones _ribbit_5...")
            # Buscar el armature principal
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'ribbit.001_ribbit_5':
                    self.player_parts['main'] = obj
                    print(f"  âœ… Armature Ribbit_5 encontrado: {obj.name} â†’ main")
                    found_any = True
                    # Buscar los huesos dentro del armature y mapearlos correctamente
                    ribbit_5_bone_mapping = {
                        'ribbit_ribbit_5': 'main',  # Ya asignado arriba
                        'body_ribbit_5': 'body',
                        'left_arm_ribbit_5': 'left_arm',
                        'right_arm_ribbit_5': 'right_arm',
                        'left_leg_ribbit_5': 'left_leg',
                        'right_leg_ribbit_5': 'right_leg'
                    }

                    for bone in obj.data.bones:
                        bone_name = bone.name.lower()
                        if bone_name in ribbit_5_bone_mapping:
                            part_key = ribbit_5_bone_mapping[bone_name]
                            if part_key in self.player_parts and self.player_parts[part_key] is None:
                                self.player_parts[part_key] = bone
                                print(f"    âœ… Hueso Ribbit_5 mapeado: {bone.name} â†’ {part_key}")
                    break

        # MANEJO ESPECIAL PARA RIBBIT_6: Criatura con bones terminados en "_ribbit_6"
        if entity_prefix == 'ribbit_6':
            print(f"ðŸ¸ Ribbit_6 (con sufijo _ribbit_6): Buscando armatures con bones _ribbit_6...")
            # Buscar el armature principal
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'ribbit.001_ribbit_6':
                    self.player_parts['main'] = obj
                    print(f"  âœ… Armature Ribbit_6 encontrado: {obj.name} â†’ main")
                    found_any = True
                    # Buscar los huesos dentro del armature y mapearlos correctamente
                    ribbit_6_bone_mapping = {
                        'ribbit_ribbit_6': 'main',  # Ya asignado arriba
                        'body_ribbit_6': 'body',
                        'left_arm_ribbit_6': 'left_arm',
                        'right_arm_ribbit_6': 'right_arm',
                        'left_leg_ribbit_6': 'left_leg',
                        'right_leg_ribbit_6': 'right_leg'
                    }

                    for bone in obj.data.bones:
                        bone_name = bone.name.lower()
                        if bone_name in ribbit_6_bone_mapping:
                            part_key = ribbit_6_bone_mapping[bone_name]
                            if part_key in self.player_parts and self.player_parts[part_key] is None:
                                self.player_parts[part_key] = bone
                                print(f"    âœ… Hueso Ribbit_6 mapeado: {bone.name} â†’ {part_key}")
                    break

        # MANEJO ESPECIAL PARA RIBBIT_7: Criatura con bones terminados en "_ribbit_7"
        if entity_prefix == 'ribbit_7':
            print(f"ðŸ¸ Ribbit_7 (con sufijo _ribbit_7): Buscando armatures con bones _ribbit_7...")
            # Buscar el armature principal
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'ribbit.001_ribbit_7':
                    self.player_parts['main'] = obj
                    print(f"  âœ… Armature Ribbit_7 encontrado: {obj.name} â†’ main")
                    found_any = True
                    # Buscar los huesos dentro del armature y mapearlos correctamente
                    ribbit_7_bone_mapping = {
                        'ribbit_ribbit_7': 'main',  # Ya asignado arriba
                        'body_ribbit_7': 'body',
                        'left_arm_ribbit_7': 'left_arm',
                        'right_arm_ribbit_7': 'right_arm',
                        'left_leg_ribbit_7': 'left_leg',
                        'right_leg_ribbit_7': 'right_leg'
                    }

                    for bone in obj.data.bones:
                        bone_name = bone.name.lower()
                        if bone_name in ribbit_7_bone_mapping:
                            part_key = ribbit_7_bone_mapping[bone_name]
                            if part_key in self.player_parts and self.player_parts[part_key] is None:
                                self.player_parts[part_key] = bone
                                print(f"    âœ… Hueso Ribbit_7 mapeado: {bone.name} â†’ {part_key}")
                    break

        # MANEJO ESPECIAL PARA RIBBIT_8: Criatura con bones terminados en "_ribbit_8"
        if entity_prefix == 'ribbit_8':
            print(f"ðŸ¸ Ribbit_8 (con sufijo _ribbit_8): Buscando armatures con bones _ribbit_8...")
            # Buscar el armature principal
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'ribbit.001_ribbit_8':
                    self.player_parts['main'] = obj
                    print(f"  âœ… Armature Ribbit_8 encontrado: {obj.name} â†’ main")
                    found_any = True
                    # Buscar los huesos dentro del armature y mapearlos correctamente
                    ribbit_8_bone_mapping = {
                        'ribbit_ribbit_8': 'main',  # Ya asignado arriba
                        'body_ribbit_8': 'body',
                        'left_arm_ribbit_8': 'left_arm',
                        'right_arm_ribbit_8': 'right_arm',
                        'left_leg_ribbit_8': 'left_leg',
                        'right_leg_ribbit_8': 'right_leg'
                    }

                    for bone in obj.data.bones:
                        bone_name = bone.name.lower()
                        if bone_name in ribbit_8_bone_mapping:
                            part_key = ribbit_8_bone_mapping[bone_name]
                            if part_key in self.player_parts and self.player_parts[part_key] is None:
                                self.player_parts[part_key] = bone
                                print(f"    âœ… Hueso Ribbit_8 mapeado: {bone.name} â†’ {part_key}")
                    break

        # MANEJO ESPECIAL PARA GUARD_RIBBIT_1: Guardia con armadura completa - sistema multi-armature
        if entity_prefix == 'guard_ribbit_1':
            print(f"ðŸŠ” Guard Ribbit_1 (sistema multi-armature): Buscando armatures main, shield y spear con sufijos _guard_ribbit_1...")
            # Buscar armature principal
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'main_guard_ribbit_1':
                    self.player_parts['main'] = obj
                    print(f"  âœ… Armature Main Guard Ribbit encontrado: {obj.name} â†’ main")
                    found_any = True
                    # Buscar los huesos dentro del armature principal y mapearlos
                    guard_main_bone_mapping = {
                        'main_guard_ribbit_1': 'main',  # Root
                        'body_guard_ribbit_1': 'body',
                        'left_arm_guard_ribbit_1': 'left_arm',
                        'right_arm_guard_ribbit_1': 'right_arm',
                        'left_leg_guard_ribbit_1': 'left_leg',
                        'right_leg_guard_ribbit_1': 'right_leg'
                    }

                    for bone in obj.data.bones:
                        bone_name = bone.name.lower()
                        if bone_name in guard_main_bone_mapping:
                            part_key = guard_main_bone_mapping[bone_name]
                            if part_key in self.player_parts and self.player_parts[part_key] is None:
                                self.player_parts[part_key] = bone
                                print(f"    âœ… Hueso Main mapeado: {bone.name} â†’ {part_key}")

            # Buscar armature del escudo
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'shield_guard_ribbit_1':
                    self.player_parts['shield'] = obj
                    print(f"  âœ… Armature Shield encontrado: {obj.name} â†’ shield")
                    found_any = True
                    # Mapear hueso del escudo
                    for bone in obj.data.bones:
                        if bone.name.lower() == 'shield_guard_ribbit_1':
                            self.player_parts['shield'] = bone
                            print(f"    âœ… Hueso Shield mapeado: {bone.name} â†’ shield")
                            break

            # Buscar armature de la lanza
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'spear_guard_ribbit_1':
                    self.player_parts['spear'] = obj
                    print(f"  âœ… Armature Spear encontrado: {obj.name} â†’ spear")
                    found_any = True
                    # Mapear hueso de la lanza
                    for bone in obj.data.bones:
                        if bone.name.lower() == 'spear_guard_ribbit_1':
                            self.player_parts['spear'] = bone
                            print(f"    âœ… Hueso Spear mapeado: {bone.name} â†’ spear")
                            break

        # MANEJO ESPECIAL PARA GUARD_RIBBIT_2: Guardia con armadura completa - sistema multi-armature
        if entity_prefix == 'guard_ribbit_2':
            print(f"ðŸŠ” Guard Ribbit_2 (sistema multi-armature): Buscando armatures main, shield y spear con sufijos _guard_ribbit_2...")
            # Buscar armature principal
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'main_guard_ribbit_2':
                    self.player_parts['main'] = obj
                    print(f"  âœ… Armature Main Guard Ribbit_2 encontrado: {obj.name} â†’ main")
                    found_any = True
                    # Buscar los huesos dentro del armature principal y mapearlos
                    guard_main_bone_mapping = {
                        'main_guard_ribbit_2': 'main',  # Root
                        'body_guard_ribbit_2': 'body',
                        'left_arm_guard_ribbit_2': 'left_arm',
                        'right_arm_guard_ribbit_2': 'right_arm',
                        'left_leg_guard_ribbit_2': 'left_leg',
                        'right_leg_guard_ribbit_2': 'right_leg'
                    }

                    for bone in obj.data.bones:
                        bone_name = bone.name.lower()
                        if bone_name in guard_main_bone_mapping:
                            part_key = guard_main_bone_mapping[bone_name]
                            if part_key in self.player_parts and self.player_parts[part_key] is None:
                                self.player_parts[part_key] = bone
                                print(f"    âœ… Hueso Main mapeado: {bone.name} â†’ {part_key}")

            # Buscar armature del escudo
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'shield_guard_ribbit_2':
                    self.player_parts['shield'] = obj
                    print(f"  âœ… Armature Shield encontrado: {obj.name} â†’ shield")
                    found_any = True
                    # Mapear hueso del escudo
                    for bone in obj.data.bones:
                        if bone.name.lower() == 'shield_guard_ribbit_2':
                            self.player_parts['shield'] = bone
                            print(f"    âœ… Hueso Shield mapeado: {bone.name} â†’ shield")
                            break

            # Buscar armature de la lanza
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'spear_guard_ribbit_2':
                    self.player_parts['spear'] = obj
                    print(f"  âœ… Armature Spear encontrado: {obj.name} â†’ spear")
                    found_any = True
                    # Mapear hueso de la lanza
                    for bone in obj.data.bones:
                        if bone.name.lower() == 'spear_guard_ribbit_2':
                            self.player_parts['spear'] = bone
                            print(f"    âœ… Hueso Spear mapeado: {bone.name} â†’ spear")
                            break

        # MANEJO ESPECIAL PARA GUARD_RIBBIT_3: Guardia con armadura completa - sistema multi-armature
        if entity_prefix == 'guard_ribbit_3':
            print(f"ðŸŠ” Guard Ribbit_3 (sistema multi-armature): Buscando armatures main, shield y spear con sufijos _guard_ribbit_3...")
            # Buscar armature principal
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'main_guard_ribbit_3':
                    self.player_parts['main'] = obj
                    print(f"  âœ… Armature Main Guard Ribbit_3 encontrado: {obj.name} â†’ main")
                    found_any = True
                    # Buscar los huesos dentro del armature principal y mapearlos
                    guard_main_bone_mapping = {
                        'main_guard_ribbit_3': 'main',  # Root
                        'body_guard_ribbit_3': 'body',
                        'left_arm_guard_ribbit_3': 'left_arm',
                        'right_arm_guard_ribbit_3': 'right_arm',
                        'left_leg_guard_ribbit_3': 'left_leg',
                        'right_leg_guard_ribbit_3': 'right_leg'
                    }

                    for bone in obj.data.bones:
                        bone_name = bone.name.lower()
                        if bone_name in guard_main_bone_mapping:
                            part_key = guard_main_bone_mapping[bone_name]
                            if part_key in self.player_parts and self.player_parts[part_key] is None:
                                self.player_parts[part_key] = bone
                                print(f"    âœ… Hueso Main mapeado: {bone.name} â†’ {part_key}")

            # Buscar armature del escudo
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'shield_guard_ribbit_3':
                    self.player_parts['shield'] = obj
                    print(f"  âœ… Armature Shield encontrado: {obj.name} â†’ shield")
                    found_any = True
                    # Mapear hueso del escudo
                    for bone in obj.data.bones:
                        if bone.name.lower() == 'shield_guard_ribbit_3':
                            self.player_parts['shield'] = bone
                            print(f"    âœ… Hueso Shield mapeado: {bone.name} â†’ shield")
                            break

            # Buscar armature de la lanza
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'spear_guard_ribbit_3':
                    self.player_parts['spear'] = obj
                    print(f"  âœ… Armature Spear encontrado: {obj.name} â†’ spear")
                    found_any = True
                    # Mapear hueso de la lanza
                    for bone in obj.data.bones:
                        if bone.name.lower() == 'spear_guard_ribbit_3':
                            self.player_parts['spear'] = bone
                            print(f"    âœ… Hueso Spear mapeado: {bone.name} â†’ spear")
                            break

        # MANEJO ESPECIAL PARA GUARD_RIBBIT_4: Guardia con armadura completa - sistema multi-armature
        if entity_prefix == 'guard_ribbit_4':
            print(f"ðŸŠ” Guard Ribbit_4 (sistema multi-armature): Buscando armatures main, shield y spear con sufijos _guard_ribbit_4...")
            # Buscar armature principal
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'main_guard_ribbit_4':
                    self.player_parts['main'] = obj
                    print(f"  âœ… Armature Main Guard Ribbit_4 encontrado: {obj.name} â†’ main")
                    found_any = True
                    # Buscar los huesos dentro del armature principal y mapearlos
                    guard_main_bone_mapping = {
                        'main_guard_ribbit_4': 'main',  # Root
                        'body_guard_ribbit_4': 'body',
                        'left_arm_guard_ribbit_4': 'left_arm',
                        'right_arm_guard_ribbit_4': 'right_arm',
                        'left_leg_guard_ribbit_4': 'left_leg',
                        'right_leg_guard_ribbit_4': 'right_leg'
                    }

                    for bone in obj.data.bones:
                        bone_name = bone.name.lower()
                        if bone_name in guard_main_bone_mapping:
                            part_key = guard_main_bone_mapping[bone_name]
                            if part_key in self.player_parts and self.player_parts[part_key] is None:
                                self.player_parts[part_key] = bone
                                print(f"    âœ… Hueso Main mapeado: {bone.name} â†’ {part_key}")

            # Buscar armature del escudo
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'shield_guard_ribbit_4':
                    self.player_parts['shield'] = obj
                    print(f"  âœ… Armature Shield encontrado: {obj.name} â†’ shield")
                    found_any = True
                    # Mapear hueso del escudo
                    for bone in obj.data.bones:
                        if bone.name.lower() == 'shield_guard_ribbit_4':
                            self.player_parts['shield'] = bone
                            print(f"    âœ… Hueso Shield mapeado: {bone.name} â†’ shield")
                            break

            # Buscar armature de la lanza
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'spear_guard_ribbit_4':
                    self.player_parts['spear'] = obj
                    print(f"  âœ… Armature Spear encontrado: {obj.name} â†’ spear")
                    found_any = True
                    # Mapear hueso de la lanza
                    for bone in obj.data.bones:
                        if bone.name.lower() == 'spear_guard_ribbit_4':
                            self.player_parts['spear'] = bone
                            print(f"    âœ… Hueso Spear mapeado: {bone.name} â†’ spear")
                            break

        # MANEJO ESPECIAL PARA GUARD_RIBBIT_5: Guardia con armadura completa - sistema multi-armature
        if entity_prefix == 'guard_ribbit_5':
            print(f"ðŸŠ” Guard Ribbit_5 (sistema multi-armature): Buscando armatures main, shield y spear con sufijos _guard_ribbit_5...")
            # Buscar armature principal
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'main_guard_ribbit_5':
                    self.player_parts['main'] = obj
                    print(f"  âœ… Armature Main Guard Ribbit_5 encontrado: {obj.name} â†’ main")
                    found_any = True
                    # Buscar los huesos dentro del armature principal y mapearlos
                    guard_main_bone_mapping = {
                        'main_guard_ribbit_5': 'main',  # Root
                        'body_guard_ribbit_5': 'body',
                        'left_arm_guard_ribbit_5': 'left_arm',
                        'right_arm_guard_ribbit_5': 'right_arm',
                        'left_leg_guard_ribbit_5': 'left_leg',
                        'right_leg_guard_ribbit_5': 'right_leg'
                    }

                    for bone in obj.data.bones:
                        bone_name = bone.name.lower()
                        if bone_name in guard_main_bone_mapping:
                            part_key = guard_main_bone_mapping[bone_name]
                            if part_key in self.player_parts and self.player_parts[part_key] is None:
                                self.player_parts[part_key] = bone
                                print(f"    âœ… Hueso Main mapeado: {bone.name} â†’ {part_key}")

            # Buscar armature del escudo
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'shield_guard_ribbit_5':
                    self.player_parts['shield'] = obj
                    print(f"  âœ… Armature Shield encontrado: {obj.name} â†’ shield")
                    found_any = True
                    # Mapear hueso del escudo
                    for bone in obj.data.bones:
                        if bone.name.lower() == 'shield_guard_ribbit_5':
                            self.player_parts['shield'] = bone
                            print(f"    âœ… Hueso Shield mapeado: {bone.name} â†’ shield")
                            break

            # Buscar armature de la lanza
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'spear_guard_ribbit_5':
                    self.player_parts['spear'] = obj
                    print(f"  âœ… Armature Spear encontrado: {obj.name} â†’ spear")
                    found_any = True
                    # Mapear hueso de la lanza
                    for bone in obj.data.bones:
                        if bone.name.lower() == 'spear_guard_ribbit_5':
                            self.player_parts['spear'] = bone
                            print(f"    âœ… Hueso Spear mapeado: {bone.name} â†’ spear")
                            break

        # MANEJO ESPECIAL PARA GUARD_RIBBIT_6: Guardia con armadura completa - sistema multi-armature
        if entity_prefix == 'guard_ribbit_6':
            print(f"ðŸŠ” Guard Ribbit_6 (sistema multi-armature): Buscando armatures main, shield y spear con sufijos _guard_ribbit_6...")
            # Buscar armature principal
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'main_guard_ribbit_6':
                    self.player_parts['main'] = obj
                    print(f"  âœ… Armature Main Guard Ribbit_6 encontrado: {obj.name} â†’ main")
                    found_any = True
                    # Buscar los huesos dentro del armature principal y mapearlos
                    guard_main_bone_mapping = {
                        'main_guard_ribbit_6': 'main',  # Root
                        'body_guard_ribbit_6': 'body',
                        'left_arm_guard_ribbit_6': 'left_arm',
                        'right_arm_guard_ribbit_6': 'right_arm',
                        'left_leg_guard_ribbit_6': 'left_leg',
                        'right_leg_guard_ribbit_6': 'right_leg'
                    }

                    for bone in obj.data.bones:
                        bone_name = bone.name.lower()
                        if bone_name in guard_main_bone_mapping:
                            part_key = guard_main_bone_mapping[bone_name]
                            if part_key in self.player_parts and self.player_parts[part_key] is None:
                                self.player_parts[part_key] = bone
                                print(f"    âœ… Hueso Main mapeado: {bone.name} â†’ {part_key}")

            # Buscar armature del escudo
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'shield_guard_ribbit_6':
                    self.player_parts['shield'] = obj
                    print(f"  âœ… Armature Shield encontrado: {obj.name} â†’ shield")
                    found_any = True
                    # Mapear hueso del escudo
                    for bone in obj.data.bones:
                        if bone.name.lower() == 'shield_guard_ribbit_6':
                            self.player_parts['shield'] = bone
                            print(f"    âœ… Hueso Shield mapeado: {bone.name} â†’ shield")
                            break

            # Buscar armature de la lanza
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'spear_guard_ribbit_6':
                    self.player_parts['spear'] = obj
                    print(f"  âœ… Armature Spear encontrado: {obj.name} â†’ spear")
                    found_any = True
                    # Mapear hueso de la lanza
                    for bone in obj.data.bones:
                        if bone.name.lower() == 'spear_guard_ribbit_6':
                            self.player_parts['spear'] = bone
                            print(f"    âœ… Hueso Spear mapeado: {bone.name} â†’ spear")
                            break

        # MANEJO ESPECIAL PARA GUARD_RIBBIT_7: Guardia con armadura completa - sistema multi-armature
        if entity_prefix == 'guard_ribbit_7':
            print(f"\u0001F6E1 Guard Ribbit_7 (sistema multi-armature): Buscando armatures main, shield y spear con sufijos _guard_ribbit_7...")
            # Buscar armature principal
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'main_guard_ribbit_7':
                    # IMPORTANTE: 'main' y 'body' deben ser el Object armature (no un Bone).
                    # El slot hace: armature = player_parts.get('body') y luego armature.type != 'ARMATURE'
                    # Si body es un Bone en lugar de un Object, lanza AttributeError: 'Bone' has no attribute 'type'
                    self.player_parts['main'] = obj
                    self.player_parts['body'] = obj   # body = armature Object principal
                    print(f"  \u2705 Armature Main Guard Ribbit_7 encontrado: {obj.name} -> main / body")
                    found_any = True
                    # Mapear solo huesos de extremidades (NO sobreescribir 'main' ni 'body' con Bone)
                    guard_main_bone_mapping = {
                        'left_arm_guard_ribbit_7': 'left_arm',
                        'right_arm_guard_ribbit_7': 'right_arm',
                        'left_leg_guard_ribbit_7': 'left_leg',
                        'right_leg_guard_ribbit_7': 'right_leg'
                    }
                    for bone in obj.data.bones:
                        bone_name = bone.name.lower()
                        if bone_name in guard_main_bone_mapping:
                            part_key = guard_main_bone_mapping[bone_name]
                            if part_key in self.player_parts and self.player_parts[part_key] is None:
                                self.player_parts[part_key] = bone
                                print(f"    \u2705 Hueso Main mapeado: {bone.name} -> {part_key}")

            # Buscar armature del escudo - guardar el Object (NO sobreescribir con Bone)
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'shield_guard_ribbit_7':
                    self.player_parts['shield'] = obj   # Object armature, no Bone
                    print(f"  \u2705 Armature Shield encontrado: {obj.name} -> shield")
                    found_any = True
                    break

            # Buscar armature de la lanza - guardar el Object (NO sobreescribir con Bone)
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'spear_guard_ribbit_7':
                    self.player_parts['spear'] = obj    # Object armature, no Bone
                    print(f"  \u2705 Armature Spear encontrado: {obj.name} -> spear")
                    found_any = True
                    break

        # MANEJO ESPECIAL PARA GUARD_RIBBIT_8: Guardia con armadura completa - sistema multi-armature
        if entity_prefix == 'guard_ribbit_8':
            print(f"\u0001F6E1 Guard Ribbit_8 (sistema multi-armature): Buscando armatures main, shield y spear con sufijos _guard_ribbit_8...")
            # Buscar armature principal
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'main_guard_ribbit_8':
                    # IMPORTANTE: 'main' y 'body' deben ser el Object armature (no un Bone).
                    # Ver fix guard_ribbit_7 - mismo patron: NO sobreescribir con Bone.
                    self.player_parts['main'] = obj
                    self.player_parts['body'] = obj   # body = armature Object principal
                    print(f"  \u2705 Armature Main Guard Ribbit_8 encontrado: {obj.name} -> main / body")
                    found_any = True
                    # Mapear solo huesos de extremidades (NO 'main' ni 'body' con Bone)
                    guard_main_bone_mapping = {
                        'left_arm_guard_ribbit_8': 'left_arm',
                        'right_arm_guard_ribbit_8': 'right_arm',
                        'left_leg_guard_ribbit_8': 'left_leg',
                        'right_leg_guard_ribbit_8': 'right_leg'
                    }
                    for bone in obj.data.bones:
                        bone_name = bone.name.lower()
                        if bone_name in guard_main_bone_mapping:
                            part_key = guard_main_bone_mapping[bone_name]
                            if part_key in self.player_parts and self.player_parts[part_key] is None:
                                self.player_parts[part_key] = bone
                                print(f"    \u2705 Hueso Main mapeado: {bone.name} -> {part_key}")

            # Buscar armature del escudo - guardar el Object (NO sobreescribir con Bone)
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'shield_guard_ribbit_8':
                    self.player_parts['shield'] = obj   # Object armature, no Bone
                    print(f"  \u2705 Armature Shield encontrado: {obj.name} -> shield")
                    found_any = True
                    break

            # Buscar armature de la lanza - guardar el Object (NO sobreescribir con Bone)
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'spear_guard_ribbit_8':
                    self.player_parts['spear'] = obj    # Object armature, no Bone
                    print(f"  \u2705 Armature Spear encontrado: {obj.name} -> spear")
                    found_any = True
                    break

        if entity_prefix == 'guard_ribbit_9':
            print(f"🛡️ Guard Ribbit_9 (sistema multi-armature): Buscando armatures main, shield y spear con sufijos _guard_ribbit_9...")
            # Buscar armature principal
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'main_guard_ribbit_9':
                    self.player_parts['main'] = obj
                    self.player_parts['body'] = obj
                    print(f"  ✅ Armature Main Guard Ribbit_9 encontrado: {obj.name} -> main / body")
                    found_any = True
                    guard_main_bone_mapping = {
                        'left_arm_guard_ribbit_9': 'left_arm',
                        'right_arm_guard_ribbit_9': 'right_arm',
                        'left_leg_guard_ribbit_9': 'left_leg',
                        'right_leg_guard_ribbit_9': 'right_leg'
                    }
                    for bone in obj.data.bones:
                        bone_name = bone.name.lower()
                        if bone_name in guard_main_bone_mapping:
                            part_key = guard_main_bone_mapping[bone_name]
                            if part_key in self.player_parts and self.player_parts[part_key] is None:
                                self.player_parts[part_key] = bone
                                print(f"    ✅ Hueso Main mapeado: {bone.name} -> {part_key}")

            # Buscar armature del escudo
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'shield_guard_ribbit_9':
                    self.player_parts['shield'] = obj
                    print(f"  ✅ Armature Shield encontrado: {obj.name} -> shield")
                    found_any = True
                    break

            # Buscar armature de la lanza
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'spear_guard_ribbit_9':
                    self.player_parts['spear'] = obj
                    print(f"  ✅ Armature Spear encontrado: {obj.name} -> spear")
                    found_any = True
                    break

        # MANEJO ESPECIAL PARA BASS_RIBBIT: Criatura con bones terminados en "_bass_ribbit"
        if entity_prefix == 'bass_ribbit':
            print(f"ðŸ¸ðŸŽ¸ Bass Ribbit (con sufijo _bass_ribbit): Buscando armatures con bones _bass_ribbit...")
            # Buscar el armature principal
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and obj.name.lower() == 'main_bass_ribbit':
                    self.player_parts['main'] = obj
                    print(f"  âœ… Armature Bass Ribbit encontrado: {obj.name} â†’ main")
                    found_any = True
                    # Buscar los huesos dentro del armature y mapearlos correctamente
                    bass_ribbit_bone_mapping = {
                        'main_bass_ribbit': 'main',  # Root bone
                        'body_bass_ribbit': 'body',
                        'left_arm_bass_ribbit': 'left_arm',
                        'right_arm_bass_ribbit': 'right_arm',
                        'left_leg_bass_ribbit': 'left_leg',
                        'right_leg_bass_ribbit': 'right_leg',
                        'bass_bass_ribbit': 'bass'  # Parte especial
                    }

                    for bone in obj.data.bones:
                        bone_name = bone.name.lower()
                        if bone_name in bass_ribbit_bone_mapping:
                            part_key = bass_ribbit_bone_mapping[bone_name]
                            if part_key in self.player_parts and self.player_parts[part_key] is None:
                                self.player_parts[part_key] = bone
                                print(f"    âœ… Hueso Bass Ribbit mapeado: {bone.name} â†’ {part_key}")
                    break

        # MANEJO ESPECIAL PARA ZOMBIE: Criatura con rig avanzado - buscar TODAS las partes
        if entity_prefix == 'zombie':
            print(f"ðŸ§Ÿ Zombie (rig avanzado): Buscando TODAS las partes del zombie...")

            # 1. Buscar el armature principal (con mÃºltiples nombres posibles para compatibilidad)
            armature_names = ['Zombie.arma_zombie', 'Zombie.arma', 'zombie.arma_zombie', 'zombie.arma']
            for armature_name in armature_names:
                for obj in bpy.data.objects:
                    if obj.type == 'ARMATURE' and obj.name.lower() == armature_name.lower():
                        self.player_parts['Zombie.arma_zombie'] = obj
                        print(f"  âœ… Armature Zombie encontrado: {obj.name} (buscado como: {armature_name})")
                        found_any = True
                        break
                if found_any:
                    break

            # 2. Buscar TODOS los meshes con sufijo "_zombie" automÃ¡ticamente
            zombie_meshes_found = 0
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and obj.name.lower().endswith('_zombie'):
                    # Usar el nombre exacto del objeto como key
                    part_key = obj.name
                    if part_key in self.player_parts and self.player_parts[part_key] is None:
                        self.player_parts[part_key] = obj
                        print(f"  âœ… Mesh Zombie encontrado: {obj.name}")
                        zombie_meshes_found += 1
                        found_any = True

            print(f"  ðŸ“Š Total meshes zombie encontrados: {zombie_meshes_found}")

            # 3. Mapear nombres legacy para compatibilidad
            zombie_mesh_mapping = {
                'body_zombie': ['Body_zombie', 'Body.003_zombie'],
                'head_zombie': ['Head_zombie', 'Head.002_zombie'],
                'left_arm_zombie': ['Arm.Left_zombie', 'Arm.Left.001_zombie'],
                'right_arm_zombie': ['Arm.Left.002_zombie', 'Arm.Left.003_zombie'],
                'left_leg_zombie': ['Cube.013_zombie', 'Cube.015_zombie'],
                'right_leg_zombie': ['Cube.014_zombie', 'Cube.027_zombie']
            }

            for part_key, possible_names in zombie_mesh_mapping.items():
                if part_key in self.player_parts and self.player_parts[part_key] is None:
                    for possible_name in possible_names:
                        for obj in bpy.data.objects:
                            if obj.type == 'MESH' and obj.name.lower() == possible_name.lower():
                                self.player_parts[part_key] = obj
                                print(f"  âœ… Mesh Zombie mapeado: {obj.name} â†’ {part_key}")
                                found_any = True
                                break
                        if self.player_parts[part_key]:
                            break

        # MANEJO ESPECIAL PARA CHICKEN: Criatura con rig Mixamo - buscar TODAS las partes
        if entity_prefix == 'chicken':
            print(f"🐔 Chicken (rig Mixamo): Buscando TODAS las partes del pollo...")

            # 1. Buscar el armature principal con sufijo _chicken
            armature_names = ['Armature_chicken', 'armature_chicken', 'ChickenArmature']
            for armature_name in armature_names:
                for obj in bpy.data.objects:
                    if obj.type == 'ARMATURE' and obj.name.lower() == armature_name.lower():
                        self.player_parts['Armature_chicken'] = obj
                        print(f"  ✅ Armature Chicken encontrado: {obj.name}")
                        found_any = True
                        break
                if found_any:
                    break

            # 2. Buscar TODOS los meshes con sufijo "_chicken" automáticamente
            chicken_meshes_found = 0
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and obj.name.lower().endswith('_chicken'):
                    # Usar el nombre exacto del objeto como key
                    part_key = obj.name
                    if part_key in self.player_parts and self.player_parts[part_key] is None:
                        self.player_parts[part_key] = obj
                        print(f"  ✅ Mesh Chicken encontrado: {obj.name}")
                        chicken_meshes_found += 1
                        found_any = True

            print(f"  📊 Total meshes chicken encontrados: {chicken_meshes_found}")

        # Estrategia 2: Buscar por sufijo especÃ­fico de entidad en toda la escena
        if not found_any:
            print(f"ðŸ”„ Buscando sufijos '_{entity_prefix}' en toda la escena...")
            for obj in bpy.data.objects:
                obj_name = obj.name.lower()
                for part in self.player_parts.keys():
                    if obj_name == f"{part}_{entity_prefix}":
                        self.player_parts[part] = obj
                        print(f"  âœ… Encontrado por sufijo _{entity_prefix}: {obj.name} â†’ {part}")
                        found_any = True
                        break

        # Estrategia 3: BÃºsqueda especÃ­fica para entidades con sufijos legacy
        if not found_any:
            if self.name.lower() == 'alfred':
                print(f"  ðŸ”„ Probando bÃºsqueda legacy _alfred para {self.name}...")
                for obj in bpy.data.objects:
                    obj_name = obj.name.lower()
                    for part in self.player_parts.keys():
                        if obj_name == f"{part}_alfred":
                            self.player_parts[part] = obj
                            print(f"  âœ… Encontrado legacy _alfred: {obj.name} â†’ {part}")
                            found_any = True
                            break
            elif self.name.lower() == 'flink':
                print(f"  ðŸ”„ Probando bÃºsqueda especÃ­fica para {self.name}...")
                for obj in bpy.data.objects:
                    obj_name = obj.name.lower()
                    for part in self.player_parts.keys():
                        # Para flink: arms/legs sin sufijo, body/head con _flink
                        if part in ['left_arm', 'right_arm', 'left_leg', 'right_leg'] and obj_name == part:
                            if self.player_parts[part] is None:
                                self.player_parts[part] = obj
                                print(f"  âœ… Encontrado flink (arm/leg sin sufijo): {obj.name} â†’ {part}")
                                found_any = True
                        elif obj_name == f"{part}_flink":
                            if self.player_parts[part] is None:
                                self.player_parts[part] = obj
                                print(f"  âœ… Encontrado flink (_flink): {obj.name} â†’ {part}")
                                found_any = True
            elif self.name.lower() == 'zombie':
                print(f"  ðŸ”„ BÃºsqueda especÃ­fica zombie ya realizada arriba (rig avanzado)")
                # La bÃºsqueda especÃ­fica del zombie ya se hizo arriba con lÃ³gica avanzada
                pass

        # Estrategia 1.5: Buscar objetos con sufijo "_alfred" (despuÃ©s del rename)
        if not found_any and entity_type in ['player', 'character']:
            print(f"  ðŸ”„ Probando bÃºsqueda con sufijo '_alfred' para {entity_type}...")
            for obj in bpy.data.objects:
                obj_name = obj.name.lower()
                for part in self.player_parts.keys():
                    # Buscar objetos que terminen con "_{part}_alfred"
                    if obj_name.endswith(f"_{part}_alfred"):
                        self.player_parts[part] = obj
                        print(f"  âœ… Encontrado con '_alfred': {obj.name} â†’ {part}")
                        found_any = True
                        break
                if found_any:
                    break

        # Estrategia 2: Buscar partes especÃ­ficas segÃºn tipo de entidad
        # Mapeo de bÃºsqueda especÃ­fico para cada tipo de entidad (siempre definido para evitar UnboundLocalError)
        search_mappings = {
                'alfred': {
                    'main': ['Hips_alfred', 'Armature_alfred', 'alfred.main', 'main'],
                    'body': ['Spine_alfred', 'Spine1_alfred', 'Spine2_alfred', 'alfred.body', 'body'],
                    'head': ['Neck_alfred', 'face_alfred', 'alfred.head', 'head'],
                    'left_arm': ['LeftUpArm_alfred', 'Leftelbow_alfred', 'alfred.left_arm', 'left_arm'],
                    'right_arm': ['RightUpArm_alfred', 'Rightelbow_alfred', 'alfred.right_arm', 'right_arm'],
                    'left_leg': ['LeftUpLeg_alfred', 'Leftknee_alfred', 'alfred.left_leg', 'left_leg'],
                    'right_leg': ['RightUpLeg_alfred', 'Rightknee_alfred', 'alfred.right_leg', 'right_leg']
                },
                'player': {
                    'body': ['body_flink', 'body_alfred', 'body', 'flink.body', 'alfred.body'],
                    'head': ['head_flink', 'head_alfred', 'head', 'flink.head', 'alfred.head'],
                    'left_arm': ['left_arm', 'left_arm_alfred', 'left_arm_flink', 'flink.left_arm', 'alfred.left_arm'],
                    'right_arm': ['right_arm', 'right_arm_alfred', 'right_arm_flink', 'flink.right_arm', 'alfred.right_arm'],
                    'left_leg': ['left_leg', 'left_leg_alfred', 'left_leg_flink', 'flink.left_leg', 'alfred.left_leg'],
                    'right_leg': ['right_leg', 'right_leg_alfred', 'right_leg_flink', 'flink.right_leg', 'alfred.right_leg']
                },
                'wolf_with_dog_skin': {
                # Objetos principales
                'body': {'type': 'OBJECT', 'name': 'Dog_001_rig'},
                'main': {'type': 'OBJECT', 'name': 'jerry'},
                # Mapeo de nombres legacy a bones del Dog_001_rig
                'head': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'scull'},
                'tail': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'spine.005'},
                'mane': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'spine.008'},
                'leggings': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'spine.006'},
                'leg4': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'front_shoulder.L'},
                'leg4.001': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'front_shoulder.R'},
                'leg4.002': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'shoulder.L'},
                'leg4.003': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'shoulder.R'},
                'boca superior': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'lip.T.L'},
                'boca inferior': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'jaw'},
                'ojos': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'face'},
                'oreja 1': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'ear.L.002'},
                'oreja2': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'ear.R.002'},
                # Bones existentes
                'sombrero': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'sombrero'},
                'scull': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'scull'},
                'spine_6': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'spine_6'},
                'tail_1': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'tail_1'},
                'spine_3': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'spine_3'},
                'shoulder.L': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'shoulder.L'},
                'shoulder.R': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'shoulder.R'},
                'front_shoulder.L': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'front_shoulder.L'},
                'front_shoulder.R': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'front_shoulder.R'},
                # NUEVOS bones agregados del Dog_001_rig
                'spine.004': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'spine.004'},
                'spine.003': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'spine.003'},
                'spine.002': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'spine.002'},
                'spine.001': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'spine.001'},
                'spine': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'spine'},
                'spine.005': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'spine.005'},
                'spine.006': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'spine.006'},
                'spine.007': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'spine.007'},
                'spine.008': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'spine.008'},
                'spine.009': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'spine.009'},
                'spine.010': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'spine.010'},
                'face': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'face'},
                'nose': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'nose'},
                'nose.001': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'nose.001'},
                'lip.T.L': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'lip.T.L'},
                'lip.T.L.001': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'lip.T.L.001'},
                'jaw': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'jaw'},
                'chin': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'chin'},
                'ear.L.002': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'ear.L.002'},
                'ear.R.002': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'ear.R.002'},
                'lip.T.R': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'lip.T.R'},
                'lip.T.R.001': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'lip.T.R.001'},
                'forehead.L.002': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'forehead.L.002'},
                'jaw.L.001': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'jaw.L.001'},
                'cheek.B.L.001': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'cheek.B.L.001'},
                'brow.T.L.001': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'brow.T.L.001'},
                'forehead.R.002': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'forehead.R.002'},
                'jaw.R.001': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'jaw.R.001'},
                'cheek.B.R.001': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'cheek.B.R.001'},
                'brow.T.R.001': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'brow.T.R.001'},
                'cheek.T.L.001': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'cheek.T.L.001'},
                'cheek.T.R.001': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'cheek.T.R.001'},
                'teeth.B': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'teeth.B'},
                'tongue': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'tongue'},
                'tongue.001': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'tongue.001'},
                'tongue.002': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'tongue.002'},
                'front_thigh.L': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'front_thigh.L'},
                'front_shin.L': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'front_shin.L'},
                'front_foot.L': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'front_foot.L'},
                'front_toe.L': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'front_toe.L'},
                'front_thigh.R': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'front_thigh.R'},
                'front_shin.R': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'front_shin.R'},
                'front_foot.R': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'front_foot.R'},
                'front_toe.R': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'front_toe.R'},
                'front_shoulder.L.001': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'front_shoulder.L.001'},
                'front_shoulder.R.001': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'front_shoulder.R.001'},
                'no_bone_001': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'no_bone_001'},
                'shoulder.L.001': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'shoulder.L.001'},
                'shoulder.R.001': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'shoulder.R.001'},
                'thigh.L': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'thigh.L'},
                'shin.L': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'shin.L'},
                'foot.L': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'foot.L'},
                'toe.L': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'toe.L'},
                'thigh.R': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'thigh.R'},
                'shin.R': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'shin.R'},
                'foot.R': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'foot.R'},
                'toe.R': {'type': 'BONE', 'armature': 'Dog_001_rig', 'name': 'toe.R'}
            },
                'creature_ribbit': {
                    'main': ['main_ribbit', 'ribbit.main', 'main', 'ribbit_ribbit'],
                    'body': ['body_ribbit', 'ribbit.body', 'body'],
                    'left_arm': ['left_arm_ribbit', 'ribbit.left_arm', 'left_arm'],
                    'right_arm': ['right_arm_ribbit', 'ribbit.right_arm', 'right_arm'],
                    'left_leg': ['left_leg_ribbit', 'ribbit.left_leg', 'left_leg'],
                    'right_leg': ['right_leg_ribbit', 'ribbit.right_leg', 'right_leg']
                },
                'creature_bass_ribbit': {
                    'main': ['main_bass_ribbit', 'bass_ribbit.main', 'main', 'main_bass_ribbit'],
                    'body': ['body_bass_ribbit', 'bass_ribbit.body', 'body'],
                    'left_arm': ['left_arm_bass_ribbit', 'bass_ribbit.left_arm', 'left_arm'],
                    'right_arm': ['right_arm_bass_ribbit', 'bass_ribbit.right_arm', 'right_arm'],
                    'left_leg': ['left_leg_bass_ribbit', 'bass_ribbit.left_leg', 'left_leg'],
                    'right_leg': ['right_leg_bass_ribbit', 'bass_ribbit.right_leg', 'right_leg'],
                    'bass': ['bass_bass_ribbit', 'bass_ribbit.bass', 'bass']
                },
                'creeper': {
                    'mane': ['mane', 'creeper.mane'],
                    'leggings': ['leggings', 'creeper.leggings'],
                    'body': ['body', 'creeper.body'],
                    'leg4': ['leg4', 'creeper.leg4', 'front_left_leg'],
                    'leg4.001': ['leg4.001', 'creeper.leg4.001', 'front_right_leg'],
                    'leg4.002': ['leg4.002', 'creeper.leg4.002', 'back_left_leg'],
                    'leg4.003': ['leg4.003', 'creeper.leg4.003', 'back_right_leg'],
                    'tail': ['tail', 'creeper.tail'],
                    'head': ['head', 'creeper.head'],
                    'boca inferior': ['boca inferior', 'mouth_lower'],
                    'boca superior': ['boca superior', 'mouth_upper'],
                    'oreja 1': ['oreja 1', 'ear_left'],
                    'oreja2': ['oreja2', 'ear_right'],
                    'ceja 1': ['ceja 1', 'eyebrow_left'],
                    'cejas2': ['cejas2', 'eyebrow_right'],
                    'ojos': ['ojos', 'eyes']
                },
                'chicken': {
                    # Armature
                    'Armature_chicken': ['Armature_chicken', 'armature_chicken', 'chicken_armature'],
                    'armature_name': ['Armature_chicken'],
                    # Meshes
                    'Body_chicken': ['Body_chicken', 'body_chicken'],
                    'Head_chicken': ['Head_chicken', 'head_chicken'],
                    'Head2_chicken': ['Head2_chicken', 'head2_chicken'],
                    'Eyes_chicken': ['Eyes_chicken', 'eyes_chicken'],
                    'BeakTop_chicken': ['BeakTop_chicken', 'beaktop_chicken', 'BeakTop'],
                    'BeakBottom_chicken': ['BeakBottom_chicken', 'beakbottom_chicken', 'BeakBottom'],
                    'WingL_chicken': ['WingL_chicken', 'wingl_chicken', 'WingL'],
                    'WingR_chicken': ['WingR_chicken', 'wingr_chicken', 'WingR'],
                    'LegL_chicken': ['LegL_chicken', 'legl_chicken', 'LegL'],
                    'LegL.001_chicken': ['LegL.001_chicken', 'legl.001_chicken', 'LegL.001'],
                    # === TODOS LOS 34 HUESOS ===
                    # Root bones (nivel 0)
                    'Root_M_chicken': ['Root_M_chicken', 'root_m_chicken', 'Root_M'],
                    'Knee.Right_chicken': ['Knee.Right_chicken', 'knee.right_chicken', 'Knee.Right', 'Knee_Right_chicken'],
                    'Knee.Left_chicken': ['Knee.Left_chicken', 'knee.left_chicken', 'Knee.Left', 'Knee_Left_chicken'],
                    # Nivel 1
                    'Hip_R_chicken': ['Hip_R_chicken', 'hip_r_chicken', 'Hip_R'],
                    'Spine1_M_chicken': ['Spine1_M_chicken', 'spine1_m_chicken', 'Spine1_M'],
                    'Hip_L_chicken': ['Hip_L_chicken', 'hip_l_chicken', 'Hip_L'],
                    'no_bone_05_chicken': ['no_bone_05_chicken', 'nobone_05_chicken', 'no_bone_05'],
                    'no_bone_04_chicken': ['no_bone_04_chicken', 'nobone_04_chicken', 'no_bone_04'],
                    'no_bone_02_chicken': ['no_bone_02_chicken', 'nobone_02_chicken', 'no_bone_02'],
                    'no_bone_03_chicken': ['no_bone_03_chicken', 'nobone_03_chicken', 'no_bone_03'],
                    # Nivel 2
                    'Knee_R_chicken': ['Knee_R_chicken', 'knee_r_chicken', 'Knee_R'],
                    'Chest_M_chicken': ['Chest_M_chicken', 'chest_m_chicken', 'Chest_M'],
                    'no_bone_01_chicken': ['no_bone_01_chicken', 'nobone_01_chicken', 'no_bone_01'],
                    'Knee_L_chicken': ['Knee_L_chicken', 'knee_l_chicken', 'Knee_L'],
                    # Nivel 3
                    'Knee_R_end_chicken': ['Knee_R_end_chicken', 'knee_r_end_chicken', 'Knee_R_end'],
                    'Neck_M_chicken': ['Neck_M_chicken', 'neck_m_chicken', 'Neck_M'],
                    'Scapula_R_chicken': ['Scapula_R_chicken', 'scapula_r_chicken', 'Scapula_R'],
                    'Scapula_L_chicken': ['Scapula_L_chicken', 'scapula_l_chicken', 'Scapula_L'],
                    # Nivel 4
                    'Head_M_chicken': ['Head_M_chicken', 'head_m_chicken', 'Head_M'],
                    'Shoulder_R_chicken': ['Shoulder_R_chicken', 'shoulder_r_chicken', 'Shoulder_R'],
                    'Shoulder_L_chicken': ['Shoulder_L_chicken', 'shoulder_l_chicken', 'Shoulder_L'],
                    # Nivel 5
                    'Jaw_M_chicken': ['Jaw_M_chicken', 'jaw_m_chicken', 'Jaw_M'],
                    'Elbow_R_chicken': ['Elbow_R_chicken', 'elbow_r_chicken', 'Elbow_R'],
                    'Elbow_L_chicken': ['Elbow_L_chicken', 'elbow_l_chicken', 'Elbow_L'],
                    # Nivel 6
                    'Jaw_top_chicken': ['Jaw_top_chicken', 'jaw_top_chicken', 'Jaw_top'],
                    'Jaw_bot_chicken': ['Jaw_bot_chicken', 'jaw_bot_chicken', 'Jaw_bot'],
                    'Elbow_R_end_chicken': ['Elbow_R_end_chicken', 'elbow_r_end_chicken', 'Elbow_R_end'],
                    'Elbow_L_end_chicken': ['Elbow_L_end_chicken', 'elbow_l_end_chicken', 'Elbow_L_end'],
                    # Otros bones
                    'no_bone_06_chicken': ['no_bone_06_chicken', 'nobone_06_chicken', 'no_bone_06'],
                    # Tobillos
                    'Ankle_R_chicken': ['Ankle_R_chicken', 'ankle_r_chicken', 'Ankle_R'],
                    'Ankle_L_chicken': ['Ankle_L_chicken', 'ankle_l_chicken', 'Ankle_L'],
                    'Ankle_R_end_chicken': ['Ankle_R_end_chicken', 'ankle_r_end_chicken', 'Ankle_R_end'],
                    'Ankle_L_end_chicken': ['Ankle_L_end_chicken', 'ankle_l_end_chicken', 'Ankle_L_end'],
                    # Fin de la lista de huesos
                },
                'creature_zombie': {
                    # Partes principales
                    'body_zombie': ['Body_zombie', 'Body.003_zombie', 'body_zombie', 'zombie.body'],
                    'head_zombie': ['Head_zombie', 'Head.002_zombie', 'head_zombie', 'zombie.head'],
                    'left_arm_zombie': ['Arm.Left_zombie', 'Arm.Left.001_zombie', 'left_arm_zombie', 'zombie.left_arm'],
                    'right_arm_zombie': ['Arm.Left.002_zombie', 'Arm.Left.003_zombie', 'right_arm_zombie', 'zombie.right_arm'],
                    'left_leg_zombie': ['Cube.013_zombie', 'Cube.015_zombie', 'left_leg_zombie', 'zombie.left_leg'],
                    'right_leg_zombie': ['Cube.014_zombie', 'Cube.027_zombie', 'right_leg_zombie', 'zombie.right_leg'],
                    # Partes adicionales del rig avanzado
                    'Body_zombie': ['Body_zombie'], 'Body.003_zombie': ['Body.003_zombie'],
                    'Head_zombie': ['Head_zombie'], 'Head.002_zombie': ['Head.002_zombie'], 'Head.001_zombie': ['Head.001_zombie'],
                    'Arm.Left_zombie': ['Arm.Left_zombie'], 'Arm.Left.001_zombie': ['Arm.Left.001_zombie'],
                    'Arm.Left.002_zombie': ['Arm.Left.002_zombie'], 'Arm.Left.003_zombie': ['Arm.Left.003_zombie'],
                    # Partes de dedos y extremidades
                    'Cube.004_zombie': ['Cube.004_zombie'], 'Cube.005_zombie': ['Cube.005_zombie'], 'Cube.006_zombie': ['Cube.006_zombie'],
                    'Cube.007_zombie': ['Cube.007_zombie'], 'Cube.008_zombie': ['Cube.008_zombie'], 'Cube.009_zombie': ['Cube.009_zombie'],
                    'Cube.010_zombie': ['Cube.010_zombie'], 'Cube.011_zombie': ['Cube.011_zombie'], 'Cube.012_zombie': ['Cube.012_zombie'],
                    'Cube.013_zombie': ['Cube.013_zombie'], 'Cube.014_zombie': ['Cube.014_zombie'], 'Cube.015_zombie': ['Cube.015_zombie'],
                    'Cube.016_zombie': ['Cube.016_zombie'], 'Cube.017_zombie': ['Cube.017_zombie'], 'Cube.018_zombie': ['Cube.018_zombie'],
                    'Cube.027_zombie': ['Cube.027_zombie'],
                    # Armature principal (mÃºltiples nombres para compatibilidad)
                    'Zombie.arma_zombie': ['Zombie.arma_zombie', 'Zombie.arma', 'zombie.arma_zombie', 'zombie.arma']
                },
                'creature_enderdragon': {
                    # Parte principal (EMPTY root para movimiento)
                    'main': ['Ender_dragon', 'ender_dragon', 'main_enderdragon', 'enderdragon.main'],

                    # Armature principal
                    'body': ['Enderdragon.arma_Ender_dragon', 'body_enderdragon', 'enderdragon.body'],

                    # Partes estÃ¡ndar (si existen)
                    'head': ['head_enderdragon', 'enderdragon.head', 'head'],
                    'left_arm': ['left_arm_enderdragon', 'enderdragon.left_arm', 'left_arm'],
                    'right_arm': ['right_arm_enderdragon', 'enderdragon.right_arm', 'right_arm'],
                    'left_leg': ['left_leg_enderdragon', 'enderdragon.left_leg', 'left_leg'],
                    'right_leg': ['right_leg_enderdragon', 'enderdragon.right_leg', 'right_leg'],

                    # PARTES ESPECÃFICAS DEL PERSONAJE
                    'mainenderdragon_enderdragon': ['mainenderdragon_enderdragon_enderdragon', 'enderdragon.mainenderdragon_enderdragon', 'mainenderdragon_enderdragon'],
                    'ik-foot:front.renderdragon_enderdragon': ['ik-foot:front.renderdragon_enderdragon_enderdragon', 'enderdragon.ik-foot:front.renderdragon_enderdragon', 'ik-foot:front.renderdragon_enderdragon'],
                    'ik-front-pole.renderdragon_enderdragon': ['ik-front-pole.renderdragon_enderdragon_enderdragon', 'enderdragon.ik-front-pole.renderdragon_enderdragon', 'ik-front-pole.renderdragon_enderdragon'],
                    'ik-foot:front.lenderdragon_enderdragon': ['ik-foot:front.lenderdragon_enderdragon_enderdragon', 'enderdragon.ik-foot:front.lenderdragon_enderdragon', 'ik-foot:front.lenderdragon_enderdragon'],
                    'ik-front-pole.lenderdragon_enderdragon': ['ik-front-pole.lenderdragon_enderdragon_enderdragon', 'enderdragon.ik-front-pole.lenderdragon_enderdragon', 'ik-front-pole.lenderdragon_enderdragon'],
                    'ik-foot:back.renderdragon_enderdragon': ['ik-foot:back.renderdragon_enderdragon_enderdragon', 'enderdragon.ik-foot:back.renderdragon_enderdragon', 'ik-foot:back.renderdragon_enderdragon'],
                    'ik-lower:back.renderdragon_enderdragon': ['ik-lower:back.renderdragon_enderdragon_enderdragon', 'enderdragon.ik-lower:back.renderdragon_enderdragon', 'ik-lower:back.renderdragon_enderdragon'],
                    'ik-foot:back.lenderdragon_enderdragon': ['ik-foot:back.lenderdragon_enderdragon_enderdragon', 'enderdragon.ik-foot:back.lenderdragon_enderdragon', 'ik-foot:back.lenderdragon_enderdragon'],
                    'ik-lower:back.lenderdragon_enderdragon': ['ik-lower:back.lenderdragon_enderdragon_enderdragon', 'enderdragon.ik-lower:back.lenderdragon_enderdragon', 'ik-lower:back.lenderdragon_enderdragon'],
                    'body.mainenderdragon_enderdragon': ['body.mainenderdragon_enderdragon_enderdragon', 'enderdragon.body.mainenderdragon_enderdragon', 'body.mainenderdragon_enderdragon'],
                    'body.middleenderdragon_enderdragon': ['body.middleenderdragon_enderdragon_enderdragon', 'enderdragon.body.middleenderdragon_enderdragon', 'body.middleenderdragon_enderdragon'],
                    'chestenderdragon_enderdragon': ['chestenderdragon_enderdragon_enderdragon', 'enderdragon.chestenderdragon_enderdragon', 'chestenderdragon_enderdragon'],
                    'ik-neckenderdragon_enderdragon': ['ik-neckenderdragon_enderdragon_enderdragon', 'enderdragon.ik-neckenderdragon_enderdragon', 'ik-neckenderdragon_enderdragon'],
                    'headenderdragon_enderdragon': ['headenderdragon_enderdragon_enderdragon', 'enderdragon.headenderdragon_enderdragon', 'headenderdragon_enderdragon'],
                    'eyetracking:leftenderdragon_enderdragon': ['eyetracking:leftenderdragon_enderdragon_enderdragon', 'enderdragon.eyetracking:leftenderdragon_enderdragon', 'eyetracking:leftenderdragon_enderdragon'],
                    'eyetracking:rightenderdragon_enderdragon': ['eyetracking:rightenderdragon_enderdragon_enderdragon', 'enderdragon.eyetracking:rightenderdragon_enderdragon', 'eyetracking:rightenderdragon_enderdragon'],
                    'mouth:upperenderdragon_enderdragon': ['mouth:upperenderdragon_enderdragon_enderdragon', 'enderdragon.mouth:upperenderdragon_enderdragon', 'mouth:upperenderdragon_enderdragon'],
                    'mouth:lowerenderdragon_enderdragon': ['mouth:lowerenderdragon_enderdragon_enderdragon', 'enderdragon.mouth:lowerenderdragon_enderdragon', 'mouth:lowerenderdragon_enderdragon'],
                    'eye:leftenderdragon_enderdragon': ['eye:leftenderdragon_enderdragon_enderdragon', 'enderdragon.eye:leftenderdragon_enderdragon', 'eye:leftenderdragon_enderdragon'],
                    'eyetrackingenderdragon_enderdragon': ['eyetrackingenderdragon_enderdragon_enderdragon', 'enderdragon.eyetrackingenderdragon_enderdragon', 'eyetrackingenderdragon_enderdragon'],
                    'eye:rightenderdragon_enderdragon': ['eye:rightenderdragon_enderdragon_enderdragon', 'enderdragon.eye:rightenderdragon_enderdragon', 'eye:rightenderdragon_enderdragon'],
                    'neckenderdragon_enderdragon': ['neckenderdragon_enderdragon_enderdragon', 'enderdragon.neckenderdragon_enderdragon', 'neckenderdragon_enderdragon'],
                    'neck.001enderdragon_enderdragon': ['neck.001enderdragon_enderdragon_enderdragon', 'enderdragon.neck.001enderdragon_enderdragon', 'neck.001enderdragon_enderdragon'],
                    'neck.002enderdragon_enderdragon': ['neck.002enderdragon_enderdragon_enderdragon', 'enderdragon.neck.002enderdragon_enderdragon', 'neck.002enderdragon_enderdragon'],
                    'neck.003enderdragon_enderdragon': ['neck.003enderdragon_enderdragon_enderdragon', 'enderdragon.neck.003enderdragon_enderdragon', 'neck.003enderdragon_enderdragon'],
                    'neck.004enderdragon_enderdragon': ['neck.004enderdragon_enderdragon_enderdragon', 'enderdragon.neck.004enderdragon_enderdragon', 'neck.004enderdragon_enderdragon'],
                    'leg:front:upper:rightenderdragon_enderdragon': ['leg:front:upper:rightenderdragon_enderdragon_enderdragon', 'enderdragon.leg:front:upper:rightenderdragon_enderdragon', 'leg:front:upper:rightenderdragon_enderdragon'],
                    'leg:front:lower:rightenderdragon_enderdragon': ['leg:front:lower:rightenderdragon_enderdragon_enderdragon', 'enderdragon.leg:front:lower:rightenderdragon_enderdragon', 'leg:front:lower:rightenderdragon_enderdragon'],
                    'foot:front.renderdragon_enderdragon': ['foot:front.renderdragon_enderdragon_enderdragon', 'enderdragon.foot:front.renderdragon_enderdragon', 'foot:front.renderdragon_enderdragon'],
                    'leg:front:upper:leftenderdragon_enderdragon': ['leg:front:upper:leftenderdragon_enderdragon_enderdragon', 'enderdragon.leg:front:upper:leftenderdragon_enderdragon', 'leg:front:upper:leftenderdragon_enderdragon'],
                    'leg:front:lower:leftenderdragon_enderdragon': ['leg:front:lower:leftenderdragon_enderdragon_enderdragon', 'enderdragon.leg:front:lower:leftenderdragon_enderdragon', 'leg:front:lower:leftenderdragon_enderdragon'],
                    'foot:front.lenderdragon_enderdragon': ['foot:front.lenderdragon_enderdragon_enderdragon', 'enderdragon.foot:front.lenderdragon_enderdragon', 'foot:front.lenderdragon_enderdragon'],
                    'wing:rightenderdragon_enderdragon': ['wing:rightenderdragon_enderdragon_enderdragon', 'enderdragon.wing:rightenderdragon_enderdragon', 'wing:rightenderdragon_enderdragon'],
                    'wing:right:tipenderdragon_enderdragon': ['wing:right:tipenderdragon_enderdragon_enderdragon', 'enderdragon.wing:right:tipenderdragon_enderdragon', 'wing:right:tipenderdragon_enderdragon'],
                    'wing:leftenderdragon_enderdragon': ['wing:leftenderdragon_enderdragon_enderdragon', 'enderdragon.wing:leftenderdragon_enderdragon', 'wing:leftenderdragon_enderdragon'],
                    'wing:left:tipenderdragon_enderdragon': ['wing:left:tipenderdragon_enderdragon_enderdragon', 'enderdragon.wing:left:tipenderdragon_enderdragon', 'wing:left:tipenderdragon_enderdragon'],
                    'leg:back:upper:leftenderdragon_enderdragon': ['leg:back:upper:leftenderdragon_enderdragon_enderdragon', 'enderdragon.leg:back:upper:leftenderdragon_enderdragon', 'leg:back:upper:leftenderdragon_enderdragon'],
                    'leg:back:lower:leftenderdragon_enderdragon': ['leg:back:lower:leftenderdragon_enderdragon_enderdragon', 'enderdragon.leg:back:lower:leftenderdragon_enderdragon', 'leg:back:lower:leftenderdragon_enderdragon'],
                    'foot:back.lenderdragon_enderdragon': ['foot:back.lenderdragon_enderdragon_enderdragon', 'enderdragon.foot:back.lenderdragon_enderdragon', 'foot:back.lenderdragon_enderdragon'],
                    'leg:back:upper:rightenderdragon_enderdragon': ['leg:back:upper:rightenderdragon_enderdragon_enderdragon', 'enderdragon.leg:back:upper:rightenderdragon_enderdragon', 'leg:back:upper:rightenderdragon_enderdragon'],
                    'leg:back:lower:rightenderdragon_enderdragon': ['leg:back:lower:rightenderdragon_enderdragon_enderdragon', 'enderdragon.leg:back:lower:rightenderdragon_enderdragon', 'leg:back:lower:rightenderdragon_enderdragon'],
                    'foot:back.renderdragon_enderdragon': ['foot:back.renderdragon_enderdragon_enderdragon', 'enderdragon.foot:back.renderdragon_enderdragon', 'foot:back.renderdragon_enderdragon'],
                    'tail_enderdragon': ['tail_enderdragon_enderdragon', 'enderdragon.tail_enderdragon', 'tail_enderdragon'],
                    'tail.001enderdragon_enderdragon': ['tail.001enderdragon_enderdragon_enderdragon', 'enderdragon.tail.001enderdragon_enderdragon', 'tail.001enderdragon_enderdragon'],
                    'tail.002enderdragon_enderdragon': ['tail.002enderdragon_enderdragon_enderdragon', 'enderdragon.tail.002enderdragon_enderdragon', 'tail.002enderdragon_enderdragon'],
                    'tail.003enderdragon_enderdragon': ['tail.003enderdragon_enderdragon_enderdragon', 'enderdragon.tail.003enderdragon_enderdragon', 'tail.003enderdragon_enderdragon'],
                    'tail.004enderdragon_enderdragon': ['tail.004enderdragon_enderdragon_enderdragon', 'enderdragon.tail.004enderdragon_enderdragon', 'tail.004enderdragon_enderdragon'],
                    'tail.005enderdragon_enderdragon': ['tail.005enderdragon_enderdragon_enderdragon', 'enderdragon.tail.005enderdragon_enderdragon', 'tail.005enderdragon_enderdragon'],
                    'tail.006enderdragon_enderdragon': ['tail.006enderdragon_enderdragon_enderdragon', 'enderdragon.tail.006enderdragon_enderdragon', 'tail.006enderdragon_enderdragon'],
                    'tail.007enderdragon_enderdragon': ['tail.007enderdragon_enderdragon_enderdragon', 'enderdragon.tail.007enderdragon_enderdragon', 'tail.007enderdragon_enderdragon'],
                    'tail.008enderdragon_enderdragon': ['tail.008enderdragon_enderdragon_enderdragon', 'enderdragon.tail.008enderdragon_enderdragon', 'tail.008enderdragon_enderdragon'],
                    'tail.009enderdragon_enderdragon': ['tail.009enderdragon_enderdragon_enderdragon', 'enderdragon.tail.009enderdragon_enderdragon', 'tail.009enderdragon_enderdragon'],
                    'tail.010enderdragon_enderdragon': ['tail.010enderdragon_enderdragon_enderdragon', 'enderdragon.tail.010enderdragon_enderdragon', 'tail.010enderdragon_enderdragon'],
                    'tail.011enderdragon_enderdragon': ['tail.011enderdragon_enderdragon_enderdragon', 'enderdragon.tail.011enderdragon_enderdragon', 'tail.011enderdragon_enderdragon'],
                },
            }

            # Usar mapeo especÃ­fico si existe, sino bÃºsqueda genÃ©rica
        if entity_type in search_mappings:
            mapping = search_mappings[entity_type]
            print(f"  â„¹ï¸ Usando configuraciÃ³n especÃ­fica para '{entity_type}'...")
            for part, part_config in mapping.items():
                # No sobreescribir si ya se encontrÃ³ en una estrategia anterior
                if self.player_parts.get(part) and self.player_parts[part] is not None:
                    continue

                found_obj = None
                
                # Manejar la nueva estructura de diccionario para la configuraciÃ³n (ej: wolf_with_dog_skin)
                if isinstance(part_config, dict) and 'type' in part_config:
                    if part_config['type'] == 'OBJECT':
                        found_obj = bpy.data.objects.get(part_config['name'])
                        if found_obj:
                            print(f"    âœ… Encontrado [OBJECT] '{found_obj.name}' para '{part}'")
                    
                    elif part_config['type'] == 'BONE':
                        armature_obj = bpy.data.objects.get(part_config['armature'])
                        if armature_obj and armature_obj.type == 'ARMATURE':
                            bone = armature_obj.pose.bones.get(part_config['name'])
                            if bone:
                                found_obj = bone
                                print(f"    âœ… Encontrado [BONE] '{bone.name}' en armature '{armature_obj.name}' para '{part}'")
                
                # Manejar la estructura antigua (lista de nombres) para compatibilidad
                elif isinstance(part_config, list):
                    for possible_name in part_config:
                        for obj in bpy.data.objects:
                            if obj.name.lower() == possible_name.lower():
                                found_obj = obj
                                print(f"  âœ… Encontrado especÃ­fico ({entity_type}): {obj.name} â†’ {part}")
                                break
                        if found_obj:
                            break
                
                if found_obj:
                    self.player_parts[part] = found_obj
                    found_any = True
            else:
                # BÃºsqueda genÃ©rica para otros tipos
                for obj in bpy.data.objects:
                    obj_name = obj.name.lower()
                    for part in self.player_parts.keys():
                        # Priorizar sufijos especÃ­ficos de entidad (ej: "_jerry", "_flink")
                        if obj_name == f"{part}_{entity_prefix}":
                            if self.player_parts[part] is None:
                                self.player_parts[part] = obj
                                print(f"  âœ… Encontrado especÃ­fico ({entity_prefix}): {obj.name} â†’ {part}")
                                found_any = True
                        # Para flink, priorizar nombres sin sufijo para arms/legs
                        elif entity_prefix == 'flink' and part in ['left_arm', 'right_arm', 'left_leg', 'right_leg'] and obj_name == part:
                            if self.player_parts[part] is None:
                                self.player_parts[part] = obj
                                print(f"  âœ… Encontrado flink (sin sufijo): {obj.name} â†’ {part}")
                                found_any = True
                        # Fallback para flink usando _flink
                        elif entity_prefix == 'flink' and obj_name == f"{part}_flink":
                            if self.player_parts[part] is None:
                                self.player_parts[part] = obj
                                print(f"  âœ… Encontrado flink (_flink): {obj.name} â†’ {part}")
                                found_any = True
                        # Para zombie, usar sufijo _zombie
                        elif entity_prefix == 'zombie' and obj_name == f"{part}_zombie":
                            if self.player_parts[part] is None:
                                self.player_parts[part] = obj
                                print(f"  âœ… Encontrado zombie (_zombie): {obj.name} â†’ {part}")
                                found_any = True
                        # Fallback para legacy _alfred
                        elif entity_type in ['player', 'character'] and obj_name == f"{part}_alfred":
                            if self.player_parts[part] is None:
                                self.player_parts[part] = obj
                                print(f"  âœ… Encontrado legacy (_alfred): {obj.name} â†’ {part}")
                                found_any = True
                        # BÃºsqueda genÃ©rica final
                        elif (obj_name == part or obj_name.endswith(f"_{part}")) and self.player_parts[part] is None:
                            self.player_parts[part] = obj
                            print(f"  âœ… Encontrado genÃ©rico: {obj.name} â†’ {part}")
                            found_any = True

        # Estrategia 3: Mapeo especial para variaciones de nombres comunes
        if not found_any:
            print(f"  ðŸ”„ Probando mapeo especial de nombres para {entity_prefix}...")
            name_mappings = {
                'enderdragon': {
                    'Ender_dragon': 'main',  # Root empty object
                    'enderdragon': 'main',  # Alternative lowercase
                    'Enderdragon.arma_Ender_dragon': 'body',  # Main armature
                }
            }

            if entity_prefix in name_mappings:
                mapping = name_mappings[entity_prefix]
                for obj in bpy.data.objects:
                    obj_name = obj.name
                    if obj_name in mapping:
                        part_key = mapping[obj_name]
                        if part_key in self.player_parts and self.player_parts[part_key] is None:
                            self.player_parts[part_key] = obj
                            print(f"  âœ… Mapeo especial: {obj.name} â†’ {part_key}")
                            found_any = True

            # ADICIONAL: Crear alias para compatibilidad con animaciones existentes
            # Si la animaciÃ³n busca 'enderdragon' pero tenemos 'Ender_dragon', crear un alias
            if entity_prefix == 'enderdragon':
                # Buscar si existe el objeto root con nombre alternativo
                root_candidates = ['Ender_dragon', 'enderdragon']
                found_root = None
                for candidate in root_candidates:
                    for obj in bpy.data.objects:
                        if obj.name == candidate and obj.type == 'EMPTY':
                            found_root = obj
                            break
                    if found_root:
                        break

                if found_root and found_root.name != 'enderdragon':
                    # Crear un objeto temporal con el nombre que espera la animaciÃ³n
                    temp_root = bpy.data.objects.new('enderdragon', None)
                    temp_root.empty_display_type = 'PLAIN_AXES'
                    temp_root.empty_display_size = 1.0
                    # Copiar transformaciÃ³n del root original
                    temp_root.location = found_root.location
                    temp_root.rotation_euler = found_root.rotation_euler
                    temp_root.scale = found_root.scale
                    # Establecer como hijo del root original para mantener jerarquÃ­a
                    temp_root.parent = found_root
                    # Agregar a la escena
                    bpy.context.scene.collection.objects.link(temp_root)
                    print(f"  âœ… Alias creado: '{temp_root.name}' â†’ apunta a '{found_root.name}'")
                    # Mapear el alias como main
                    self.player_parts['main'] = temp_root

          # Estrategia 4: Buscar por tipo de objeto (ultimo recurso)
        if not found_any:
            print(f"  Advertencia: No encontrado especifico, probando por tipo...")
            entity_name_lower = self.name.lower()
            matched_armature = None
            for obj in bpy.data.objects:
                if obj.type == 'ARMATURE' and entity_name_lower in obj.name.lower():
                    matched_armature = obj
                    break
            if matched_armature is None and self.player_parts.get('main') is not None:
                root_obj = self.player_parts['main']
                for obj in bpy.data.objects:
                    if obj.type == 'ARMATURE' and obj.parent == root_obj:
                        matched_armature = obj
                        break
            if matched_armature is None:
                all_armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
                if len(all_armatures) == 1:
                    matched_armature = all_armatures[0]
                    print(f"  Unico armature, asignando: {matched_armature.name}")
                else:
                    print(f"  ERROR Estrategia 4: {len(all_armatures)} armatures, "
                          f"ninguno coincide con '{entity_name_lower}'. No se asigna body.")
            if matched_armature is not None and self.player_parts.get('body') is None:
                self.player_parts['body'] = matched_armature
                print(f"  OK Asignado armature filtrado por entidad: {matched_armature.name} -> body")
                found_any = True

# Verificar resultados
        found_parts = [name for name, obj in self.player_parts.items() if obj is not None]
        missing_parts = [name for name, obj in self.player_parts.items() if obj is None]

        print(f"ðŸŽ­ {self.name}: {len(found_parts)} partes encontradas: {found_parts}")
        if missing_parts:
            print(f"âš ï¸ Partes faltantes: {missing_parts}")

        # Mostrar todos los objetos disponibles para debugging
        if not found_any:
            print("ðŸ” OBJETOS DISPONIBLES EN ESCENA:")
            for obj in bpy.data.objects:
                if obj.type in ['ARMATURE', 'MESH']:
                    print(f"   â€¢ {obj.name} ({obj.type})")

        return len(found_parts) > 0

# ============================================================================
# FUNCIONES DE SOPORTE PARA ENTIDADES
# ============================================================================

def get_blocks_manager():
    """Retorna la instancia global del manager"""
    from .core_system import blocks_manager
    return blocks_manager

# ============================================================================
# FUNCIONES DE SOPORTE PARA ENTIDADES
# ============================================================================

def get_blocks_manager():
    """Retorna la instancia global del manager"""
    from .core_system import blocks_manager
    return blocks_manager

# ============================================================================
# REGISTRO DEL MÃ“DULO
# ============================================================================
# ============================================================================
# REGISTRO DEL MÓDULO
# ============================================================================



def register():
    """Registra las clases del sistema de entidades"""
    print("✅ Sistema de entidades registrado correctamente")

def unregister():
    """Desregistra las clases del sistema de entidades"""
    print("✅ Sistema de entidades desregistrado correctamente")