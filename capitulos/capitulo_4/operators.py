#!/usr/bin/env python3
"""
operators.py - Operadores del sistema Multi-Entity Animation Blocks Manager
Contiene todos los operadores de Blender para el sistema
"""

import bpy
import os
import json
import datetime
import importlib.util
from pathlib import Path
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, IntProperty, BoolProperty, CollectionProperty
from bpy.types import Operator

# ============================================================================
# OPERADORES PRINCIPALES
# ============================================================================

class ANIMBLOCKS_OT_LoadPromptFolder(Operator, ImportHelper):
    """Carga una carpeta Prompt_X completa con metadata.json"""
    bl_idname = "simple_animblocks.load_prompt_folder"
    bl_label = "Cargar Carpeta Prompt"
    bl_options = {'REGISTER', 'UNDO'}

    directory: StringProperty(subtype="DIR_PATH")

    def execute(self, context):
        # CORRECCIÓN COMPLETA: Usar la función load_prompt_folder de utilities.py
        # que tiene toda la lógica implementada correctamente
        try:
            from utilities import load_prompt_folder
            success = load_prompt_folder(self.directory)
        except ImportError as e:
            # Fallback si utilities no está disponible
            print(f"⚠️ utilities.load_prompt_folder no disponible: {e}, usando fallback")
            try:
                import core_system
                blocks_manager = core_system.blocks_manager
                # CORRECCIÓN: Usar la función de utilities en lugar del método del manager
                from utilities import load_prompt_folder
                success = load_prompt_folder(self.directory)
            except (ImportError, AttributeError) as e2:
                print(f"❌ No se pudo acceder al manager de bloques: {e2}")
                # Último fallback: intentar usar la función directamente
                try:
                    from utilities import load_prompt_folder
                    success = load_prompt_folder(self.directory)
                except Exception as e3:
                    print(f"❌ Error crítico en carga de prompt: {e3}")
                    success = False

        # CORRECCIÓN: Asegurar que blocks_manager esté definido para el return
        if 'blocks_manager' not in locals():
            import core_system
            blocks_manager = core_system.blocks_manager

        print(f"DEBUG: Operador ejecutado con directory: '{self.directory}'")
        print(f"DEBUG: Tipo de directory: {type(self.directory)}")
        print(f"DEBUG: Longitud de directory: {len(self.directory) if self.directory else 0}")

        # Validar que directory no sea None, vacío, o no exista
        if self.directory is None:
            print("DEBUG: directory es None")
            self.report({'ERROR'}, "No se seleccionó ninguna carpeta")
            return {'CANCELLED'}

        if self.directory.strip() == "":
            print("DEBUG: directory es string vacío")
            self.report({'ERROR'}, "No se seleccionó ninguna carpeta")
            return {'CANCELLED'}

        if not os.path.exists(self.directory):
            print(f"DEBUG: directory no existe: '{self.directory}'")
            self.report({'ERROR'}, f"Carpeta no existe: '{self.directory}'")
            return {'CANCELLED'}

        print(f"DEBUG: Carpeta válida, llamando load_prompt_folder con: '{self.directory}'")

        # Usar la función de utilities directamente (ya que el manager no tiene el método)
        from utilities import load_prompt_folder
        success = load_prompt_folder(self.directory)

        if success:
            folder_name = os.path.basename(os.path.normpath(self.directory)) if self.directory else "desconocida"
            # Intentar obtener entidades cargadas si el manager está disponible
            try:
                import core_system
                loaded_entities = len(core_system.blocks_manager.get_loaded_entities())
            except:
                loaded_entities = 0
            self.report({'INFO'}, f"Prompt '{folder_name}' cargado: {loaded_entities} entidades")
            print(f"SUCCESS: Prompt '{folder_name}' cargado exitosamente")
            return {'FINISHED'}
        else:
            folder_name = os.path.basename(os.path.normpath(self.directory)) if self.directory else "desconocida"
            print(f"ERROR: Falló la carga del prompt '{folder_name}'")
            self.report({'ERROR'}, f"Error cargando prompt '{folder_name}'")
            return {'CANCELLED'}

    def invoke(self, context, event):
        # Configurar el directorio inicial en la carpeta animacion
        script_dir = os.path.dirname(os.path.abspath(__file__))
        animacion_dir = os.path.join(script_dir, "..", "animacion")

        if os.path.exists(animacion_dir):
            self.directory = animacion_dir
        else:
            self.directory = script_dir

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class ANIMBLOCKS_OT_ExtractData(Operator):
    """Extrae datos del sistema para análisis IA"""
    bl_idname = "simple_animblocks.extract_data"
    bl_label = "Extraer Datos"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            # Fallback: crear manager básico si no está disponible
            try:
                from core_system import SimpleAnimationBlocksManager
                blocks_manager = SimpleAnimationBlocksManager()
            except ImportError:
                # Último fallback: crear un manager vacío
                class DummyManager:
                    def __init__(self):
                        self.entities = {}
                        self.current_prompt_folder = None
                        self.prompt_metadata = None
                        self.shared_timeline = True
                        self.max_entities = 8
                        self.active_entity_slot_indicators = {}
                        self.sequence_frame_ranges = {}
                        self.active_slot_indicators = {}
                        self.loop_enabled = False
                        self.max_slots = 50
                        self.player_parts = {}
                        self.current_structure = None

                    def get_loaded_entities(self):
                        return []

                    def initialize_entity_slot_indicators(self, entity_name):
                        if entity_name not in self.active_entity_slot_indicators:
                            self.active_entity_slot_indicators[entity_name] = {}
                            for slot in range(1, 21):
                                self.active_entity_slot_indicators[entity_name][slot] = False

                    def initialize_slots(self):
                        pass

                    def find_player_parts(self):
                        pass

                    def initialize_slot_indicators(self):
                        for i in range(1, self.max_slots + 1):
                            self.active_slot_indicators[i] = False

                    def load_prompt_folder(self, folder_path):
                        """Método dummy para load_prompt_folder"""
                        print(f"DummyManager: Intentando cargar carpeta {folder_path}")
                        return False

                blocks_manager = DummyManager()

        try:
            # Importar y usar outliner_extractor_2.py (versión independiente del Proyecto)
            import sys
            import os

            # Ruta al outliner_extractor_2.py (versión específica del Proyecto)
            outliner_path = os.path.join(os.path.dirname(__file__), "outliner_extractor_2.py")

            if not os.path.exists(outliner_path):
                self.report({'ERROR'}, f"Archivo outliner_extractor.py no encontrado: {outliner_path}")
                return {'CANCELLED'}

            # Importar el módulo dinámicamente
            spec = importlib.util.spec_from_file_location("outliner_extractor", outliner_path)
            if spec and spec.loader:
                outliner_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(outliner_module)

                # Ejecutar la extracción completa del outliner
                output_file = outliner_module.save_outliner_data()

                # Mostrar resumen en consola
                outliner_module.print_complete_summary()

                self.report({'INFO'}, f"Outliner extraído: {os.path.basename(output_file)}")
                print(f"✅ OUTLINER EXTRAÍDO EXITOSAMENTE: {output_file}")
                print("🎯 El archivo JSON contiene toda la estructura del .blend cargado")
                print("🤖 La IA ahora puede analizar la jerarquía completa para crear/editar animaciones")

                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Error cargando módulo outliner_extractor")
                return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error extrayendo outliner: {str(e)}")
            print(f"❌ Error en extracción del outliner: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

class ANIMBLOCKS_OT_Update(Operator):
    """Actualiza y recarga el sistema de bloques de animación"""
    bl_idname = "simple_animblocks.update"
    bl_label = "Actualizar"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            # Fallback: crear manager básico si no está disponible
            try:
                from core_system import SimpleAnimationBlocksManager
                blocks_manager = SimpleAnimationBlocksManager()
            except ImportError:
                # Último fallback: crear un manager vacío
                class DummyManager:
                    def __init__(self):
                        self.entities = {}
                        self.current_prompt_folder = None
                        self.prompt_metadata = None
                        self.shared_timeline = True
                        self.max_entities = 8
                        self.active_entity_slot_indicators = {}
                        self.sequence_frame_ranges = {}
                        self.active_slot_indicators = {}
                        self.loop_enabled = False
                        self.max_slots = 50
                        self.player_parts = {}
                        self.current_structure = None

                    def get_loaded_entities(self):
                        return []

                    def initialize_entity_slot_indicators(self, entity_name):
                        if entity_name not in self.active_entity_slot_indicators:
                            self.active_entity_slot_indicators[entity_name] = {}
                            for slot in range(1, 21):
                                self.active_entity_slot_indicators[entity_name][slot] = False

                    def initialize_slots(self):
                        pass

                    def find_player_parts(self):
                        pass

                    def initialize_slot_indicators(self):
                        for i in range(1, self.max_slots + 1):
                            self.active_slot_indicators[i] = False

                blocks_manager = DummyManager()

        # Actualizar partes del cuerpo
        blocks_manager.find_player_parts()

        # Reinicializar indicadores
        blocks_manager.initialize_slot_indicators()
        for entity_name in blocks_manager.entities:
            blocks_manager.initialize_entity_slot_indicators(entity_name)

        # Limpiar rangos de frames
        blocks_manager.sequence_frame_ranges = {}

        self.report({'INFO'}, "Sistema de bloques de animación actualizado")
        print("🔄 SISTEMA ACTUALIZADO: Partes del cuerpo y indicadores reinicializados")
        return {'FINISHED'}

class ANIMBLOCKS_OT_ResetAll(Operator):
    """Limpia completamente el outliner y resetea el estado del manager"""
    bl_idname = "simple_animblocks.reset_all"
    bl_label = "Resetear TODO"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        print("\n\u26a0\ufe0f ALERTA: Se ha llamado a ANIMBLOCKS_OT_ResetAll. Esto limpiar\u00e1 toda la escena.")
        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            # Fallback: crear manager básico si no está disponible
            try:
                from core_system import SimpleAnimationBlocksManager
                blocks_manager = SimpleAnimationBlocksManager()
            except ImportError:
                # Último fallback: crear un manager vacío
                class DummyManager:
                    def __init__(self):
                        self.entities = {}
                        self.current_prompt_folder = None
                        self.prompt_metadata = None
                        self.shared_timeline = True
                        self.max_entities = 8
                        self.active_entity_slot_indicators = {}
                        self.sequence_frame_ranges = {}
                        self.active_slot_indicators = {}
                        self.loop_enabled = False
                        self.max_slots = 50
                        self.player_parts = {}
                        self.current_structure = None

                    def get_loaded_entities(self):
                        return []

                    def initialize_entity_slot_indicators(self, entity_name):
                        if entity_name not in self.active_entity_slot_indicators:
                            self.active_entity_slot_indicators[entity_name] = {}
                            for slot in range(1, 21):
                                self.active_entity_slot_indicators[entity_name][slot] = False

                    def initialize_slots(self):
                        pass

                    def find_player_parts(self):
                        pass

                    def initialize_slot_indicators(self):
                        for i in range(1, self.max_slots + 1):
                            self.active_slot_indicators[i] = False

                blocks_manager = DummyManager()

        # 1. LIMPIAR EL OUTLINER COMPLETAMENTE
        print("🧹 LIMPIANDO OUTLINER COMPLETO...")
        try:
            # Limpiar todas las colecciones excepto la escena principal
            scene_collections = list(bpy.context.scene.collection.children)
            for coll in scene_collections:
                try:
                    bpy.context.scene.collection.children.unlink(coll)
                    print(f"   ✅ Colección removida: {coll.name}")
                except Exception as e:
                    print(f"   ⚠️ Error removiendo colección {coll.name}: {e}")

            # Limpiar todos los objetos de la escena principal
            objects_to_remove = []
            for obj in bpy.context.scene.collection.objects:
                # Solo remover objetos que no sean la cámara y luz por defecto
                if obj.type not in ['CAMERA', 'LIGHT']:
                    objects_to_remove.append(obj)

            for obj in objects_to_remove:
                try:
                    bpy.data.objects.remove(obj, do_unlink=True)
                    print(f"   ✅ Objeto removido: {obj.name} ({obj.type})")
                except Exception as e:
                    print(f"   ⚠️ Error removiendo objeto {obj.name}: {e}")

            # Limpiar actions no utilizadas — EXCEPTO las de los addons de personajes
            # (GRB7, GRB8, Alfred, Jerry) para no cruzar flujos de animacion.
            _PROTECTED_ACTION_PREFIXES = (
                "main_guard_ribbit_", "shield_guard_ribbit_", "spear_guard_ribbit_",
                "alfred", "jerry",
            )
            actions_to_remove = []
            for action in bpy.data.actions:
                # Nunca tocar actions de los addons de personajes
                _aname_lower = action.name.lower()
                if any(_aname_lower.startswith(p) for p in _PROTECTED_ACTION_PREFIXES):
                    continue
                # Verificar si la action esta siendo usada por algun objeto
                used = False
                for obj in bpy.data.objects:
                    if obj.animation_data and obj.animation_data.action == action:
                        used = True
                        break
                if not used:
                    actions_to_remove.append(action)

            for action in actions_to_remove:
                try:
                    bpy.data.actions.remove(action)
                    print(f"   ✅ Action removida: {action.name}")
                except Exception as e:
                    print(f"   ⚠️ Error removiendo action {action.name}: {e}")

            print("✅ OUTLINER COMPLETAMENTE LIMPIO")

        except Exception as e:
            print(f"❌ Error limpiando outliner: {e}")
            self.report({'WARNING'}, f"Error limpiando outliner: {str(e)}")

        # 2. Limpiar todo el sistema de bloques de animación
        print("🔄 RESETEANDO SISTEMA DE BLOQUES...")
        blocks_manager.entities = {}
        blocks_manager.current_prompt_folder = None
        blocks_manager.prompt_metadata = None
        blocks_manager.player_parts = {}
        blocks_manager.sequence_frame_ranges = {}
        blocks_manager.active_slot_indicators = {}
        blocks_manager.active_entity_slot_indicators = {}

        # Reinicializar slots
        blocks_manager.initialize_slots()

        # Resetear timeline
        scene = context.scene
        scene.frame_current = 1
        scene.frame_set(1)

        # Limpiar handlers de animación si existen
        try:
            handlers_to_remove = []
            for handler in bpy.app.handlers.frame_change_post:
                if hasattr(handler, '__name__') and 'animblocks' in handler.__name__.lower():
                    handlers_to_remove.append(handler)

            for handler in handlers_to_remove:
                bpy.app.handlers.frame_change_post.remove(handler)
                print("🗑️ Handler de animación removido")
        except:
            pass

        self.report({'INFO'}, "Sistema completamente reseteado y outliner limpiado")
        print("🔄 SISTEMA COMPLETAMENTE RESETEADO Y OUTLINER LIMPIO")
        return {'FINISHED'}

class ANIMBLOCKS_OT_StopPlayback(Operator):
    """Detiene la reproducción y limpia indicadores"""
    bl_idname = "simple_animblocks.stop_playback"
    bl_label = "Detener Reproducción"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            # Fallback: crear manager básico si no está disponible
            try:
                from core_system import SimpleAnimationBlocksManager
                blocks_manager = SimpleAnimationBlocksManager()
            except ImportError:
                # Último fallback: crear un manager vacío
                class DummyManager:
                    def __init__(self):
                        self.entities = {}
                        self.current_prompt_folder = None
                        self.prompt_metadata = None
                        self.shared_timeline = True
                        self.max_entities = 8
                        self.active_entity_slot_indicators = {}
                        self.sequence_frame_ranges = {}
                        self.active_slot_indicators = {}
                        self.loop_enabled = False
                        self.max_slots = 50
                        self.player_parts = {}
                        self.current_structure = None

                    def get_loaded_entities(self):
                        return []

                    def initialize_entity_slot_indicators(self, entity_name):
                        if entity_name not in self.active_entity_slot_indicators:
                            self.active_entity_slot_indicators[entity_name] = {}
                            for slot in range(1, 21):
                                self.active_entity_slot_indicators[entity_name][slot] = False

                    def initialize_slots(self):
                        pass

                    def find_player_parts(self):
                        pass

                    def initialize_slot_indicators(self):
                        for i in range(1, self.max_slots + 1):
                            self.active_slot_indicators[i] = False

                    def load_prompt_folder(self, folder_path):
                        """Método dummy para load_prompt_folder"""
                        print(f"DummyManager: Intentando cargar carpeta {folder_path}")
                        return False

                blocks_manager = DummyManager()

        # Detener reproducción si está activa
        if bpy.context.screen.is_animation_playing:
            bpy.ops.screen.animation_cancel(restore_frame=False)
            print("⏹️ Reproducción detenida")

        # Limpiar indicadores visuales
        blocks_manager.sequence_frame_ranges = {}
        for slot in blocks_manager.active_slot_indicators:
            blocks_manager.active_slot_indicators[slot] = False

        # Limpiar indicadores por entidad
        for entity_name in blocks_manager.active_entity_slot_indicators:
            for slot in blocks_manager.active_entity_slot_indicators[entity_name]:
                blocks_manager.active_entity_slot_indicators[entity_name][slot] = False

        # Remover handlers de indicadores visuales (si existe el método)
        try:
            if hasattr(blocks_manager, 'unregister_visual_indicators_handler'):
                blocks_manager.unregister_visual_indicators_handler()
        except AttributeError:
            print("⚠️ Método unregister_visual_indicators_handler no disponible (funcionalidad opcional)")

        # Resetear al frame inicial
        scene = context.scene
        scene.frame_current = 1
        scene.frame_set(1)

        self.report({'INFO'}, "Reproducción detenida e indicadores limpiados")
        print("🧹 Indicadores visuales limpiados")
        return {'FINISHED'}

class ANIMBLOCKS_OT_ConcatenateEntity(Operator):
    """Concatena y reproduce las animaciones de una entidad específica"""
    bl_idname = "simple_animblocks.concatenate_entity"
    bl_label = "Concatenar Entidad"
    bl_options = {'REGISTER', 'UNDO'}

    entity_name: StringProperty(name="Entidad", default="")

    def execute(self, context):
        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            # Fallback: crear manager básico si no está disponible
            try:
                from core_system import SimpleAnimationBlocksManager
                blocks_manager = SimpleAnimationBlocksManager()
            except ImportError:
                # Último fallback: crear un manager vacío
                class DummyManager:
                    def __init__(self):
                        self.entities = {}
                        self.current_prompt_folder = None
                        self.prompt_metadata = None
                        self.shared_timeline = True
                        self.max_entities = 8
                        self.active_entity_slot_indicators = {}
                        self.sequence_frame_ranges = {}
                        self.active_slot_indicators = {}
                        self.loop_enabled = False
                        self.max_slots = 50
                        self.player_parts = {}
                        self.current_structure = None

                    def get_loaded_entities(self):
                        return []

                    def initialize_entity_slot_indicators(self, entity_name):
                        if entity_name not in self.active_entity_slot_indicators:
                            self.active_entity_slot_indicators[entity_name] = {}
                            for slot in range(1, 21):
                                self.active_entity_slot_indicators[entity_name][slot] = False

                    def initialize_slots(self):
                        pass

                    def find_player_parts(self):
                        pass

                    def initialize_slot_indicators(self):
                        for i in range(1, self.max_slots + 1):
                            self.active_slot_indicators[i] = False

                    def load_prompt_folder(self, folder_path):
                        """Método dummy para load_prompt_folder"""
                        print(f"DummyManager: Intentando cargar carpeta {folder_path}")
                        return False

                blocks_manager = DummyManager()

        if not self.entity_name or self.entity_name not in blocks_manager.entities:
            self.report({'ERROR'}, f"Entidad '{self.entity_name}' no encontrada")
            return {'CANCELLED'}

        entity_data = blocks_manager.entities[self.entity_name]
        entity_controller = entity_data.get('controller')
        if not entity_controller:
            self.report({'ERROR'}, f"Controller no encontrado para entidad '{self.entity_name}'")
            return {'CANCELLED'}

        # Importar animation_engine UNA SOLA VEZ antes del loop (optimización de rendimiento)
        animation_engine_path = os.path.join(os.path.dirname(__file__), "animation_engine.py")
        spec = importlib.util.spec_from_file_location("animation_engine", animation_engine_path)
        if spec and spec.loader:
            animation_engine_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(animation_engine_module)
            execute_animation_block = animation_engine_module.execute_animation_block
            print("ℹ️ Animation engine cargado una sola vez (optimizado)")
        else:
            print("❌ Error creando spec para animation_engine")
            return {'CANCELLED'}

        # Obtener la secuencia de bloques cargados
        sequence = entity_controller.get_loaded_blocks_sequence()

        # FILTRO: Si hay slots seleccionados, usar solo esos; si no, usar todos
        if hasattr(blocks_manager, 'selected_slots') and blocks_manager.selected_slots:
            selected_for_entity = blocks_manager.selected_slots.get(self.entity_name, {})
            if selected_for_entity:
                # Filtrar la secuencia para solo incluir slots seleccionados
                original_count = len(sequence)
                sequence = [block for block in sequence if selected_for_entity.get(block['slot'], False)]
                print(f"🎯 Slots seleccionados para '{self.entity_name}': {original_count} → {len(sequence)}")
                print(f"   Slots: {[block['slot'] for block in sequence]}")
            else:
                print(f"ℹ️ No hay slots seleccionados para '{self.entity_name}' - usando todos los slots")
        else:
            print(f"ℹ️ Sistema de selección no disponible - usando todos los slots")

        if not sequence:
            # Debugging: mostrar qué animaciones están disponibles
            all_blocks = entity_controller.blocks
            loaded_blocks = [slot for slot, block in all_blocks.items() if block['is_loaded']]
            total_blocks = len([slot for slot, block in all_blocks.items() if block['is_loaded'] or block['name']])

            debug_msg = f"No hay animaciones cargadas para '{self.entity_name}'"
            if loaded_blocks:
                debug_msg += f" (Slots cargados: {loaded_blocks})"
            else:
                debug_msg += f" (0/{total_blocks} slots con animaciones)"

            print(f"🎭 DEBUG: {debug_msg}")
            print(f"📊 Estado de slots para {self.entity_name}:")
            for slot in range(1, min(11, entity_controller.max_slots + 1)):  # Mostrar primeros 10 slots
                block = all_blocks[slot]
                status = "✅" if block['is_loaded'] else "❌"
                print(f"   Slot {slot}: {status} {block['name'] or 'vacío'}")

            self.report({'WARNING'}, debug_msg)
            return {'CANCELLED'}

        print(f"🎭 CONCATENANDO ENTIDAD: {self.entity_name}")
        print(f"📦 Animaciones: {len(sequence)}")

        # LIMPIAR PISTAS DE AUDIO EXISTENTES ANTES DE EJECUTAR ANIMACIONES
        # Para evitar acumulación de pistas de audio cuando se actualiza y concatena
        # NOTA: Solo limpiar audio en reproducción multi-entidad, NO en concatenaciones individuales
        # para preservar audio de otras entidades
        print("ℹ️ Concatenación individual: Preservando pistas de audio existentes de otras entidades")
        # No limpiamos audio en concatenaciones individuales para evitar afectar otras entidades

        # CALCULAR timeline RELATIVO para esta entidad (SIN MODIFICAR escena global)
        total_frames = sum(block['frame_count'] for block in sequence)
        print(f"⏱️ Timeline calculado para {self.entity_name}: {total_frames} frames totales")

        # Cachear armature y root al inicio para evitar búsquedas repetitivas
        # Buscar armature generico del sistema Animation Blocks.
        # IMPORTANTE: ignorar armatures que pertenecen a los addons de personajes
        # (GRB7, GRB8, Alfred, Jerry) para no cruzar flujos.
        _STUDIO_ADDON_PREFIXES = (
            "main_guard_ribbit_", "shield_guard_ribbit_", "spear_guard_ribbit_",
            "alfred", "jerry",
        )
        armature = None
        _candidate = bpy.data.objects.get("Armature")
        if _candidate and _candidate.type == "ARMATURE":
            _name_lower = _candidate.name.lower()
            if not any(_name_lower.startswith(p) for p in _STUDIO_ADDON_PREFIXES):
                armature = _candidate
        entity_root = None
        for obj in bpy.data.objects:
            if obj.name == self.entity_name and obj.type == 'EMPTY':
                entity_root = obj
                break
        
        # Asegurar modo POSE una sola vez
        if armature and armature.type == 'ARMATURE':
            if armature.mode != 'POSE':
                bpy.context.view_layer.objects.active = armature
                bpy.ops.object.mode_set(mode='POSE')
            print("ℹ️ Modo POSE configurado una vez (optimizado)")

        # Ejecutar secuencia de la entidad con timeline RELATIVO
        success_count = 0
        current_frame = 1  # Timeline relativo empezando en 1 para esta entidad

        # ⚠️ NO modificar timeline global de la escena
        print(f"⏱️ Timeline RELATIVO para '{self.entity_name}': 1-{total_frames} frames (escena global intacta)")

        for i, block in enumerate(sequence):
            print(f"🎯 Ejecutando {block['name']} (frames {current_frame}-{current_frame + block['frame_count'] - 1})")

            # Ejecutar la animación usando la lógica del manager
            block_start = current_frame
            block_end = current_frame + block['frame_count'] - 1

            # Usar los player_parts específicos de esta entidad
            entity_player_parts = entity_controller.player_parts

            # Verificar que tengamos las partes necesarias según el tipo de entidad
            entity_type = entity_data.get('type', 'unknown')
            required_parts = []

            # Determinar qué partes buscar según el tipo de entidad
            if entity_type in ['wolf_with_dog_skin', 'wolf', 'dog', 'cat']:
                # Entidades de tipo gato/perro: patas específicas
                required_parts = ['body', 'head', 'tail', 'leg4', 'leg4.001', 'leg4.002', 'leg4.003']
            elif entity_type in ['player', 'human', 'villager', 'skeleton']:
                # Entidades humanas: brazos y piernas estándar
                required_parts = ['body', 'head', 'left_arm', 'right_arm', 'left_leg', 'right_leg']
            elif entity_type == 'creature_flink':
                # Flink: criatura especial con partes terminadas en "_flink"
                required_parts = ['body_flink', 'head_flink', 'eyes_flink', 'body2_flink', 'body3_flink', 'body4_flink', 'body5_flink']
            elif entity_type == 'creature_guard_ribbit':
                # Guard Ribbit: sistema multi-armature con escudo y lanza
                # Solo requiere 'main'/'body' que son el armature Object principal
                required_parts = ['main', 'body']
            elif entity_type == 'creature_zombie':
                # Zombie: criatura especial con rig avanzado - requiere al menos las partes principales
                # pero permite muchas más partes del rig complejo (119 bones, múltiples meshes)
                required_parts = ['body_zombie', 'head_zombie']  # Solo partes críticas mínimas
                # Opcionalmente verificar que tenga al menos algunos brazos/piernas si están disponibles
                optional_parts = ['left_arm_zombie', 'right_arm_zombie', 'left_leg_zombie', 'right_leg_zombie']
                available_optional = [part for part in optional_parts if part in entity_player_parts and entity_player_parts[part] is not None]
                if available_optional:
                    print(f"  📋 Partes opcionales zombie disponibles: {available_optional}")
            else:
                # Fallback: buscar cualquier parte disponible
                required_parts = ['body', 'head']

            # Verificar partes específicas del tipo de entidad (incluyendo sufijos específicos)
            missing_parts = []
            for part in required_parts:
                # Buscar parte exacta primero
                found = part in entity_player_parts and entity_player_parts[part] is not None
                if found:
                    # Verificar que el objeto aun existe en la escena
                    # NOTA: obj.name in bpy.data.objects siempre es True si el objeto existe;
                    # usar identidad de objeto (is) para confirmar que es el mismo objeto.
                    obj = entity_player_parts[part]
                    if hasattr(obj, 'name') and bpy.data.objects.get(obj.name) is obj:
                        found = True
                    else:
                        found = False
                        # Limpiar referencia invalida o a objeto equivocado
                        entity_player_parts[part] = None

                if not found:
                    # Para entidades con sufijos específicos, no buscar sufijos adicionales
                    # ya que required_parts ya incluye los sufijos correctos
                    missing_parts.append(part)

            if missing_parts:
                print(f"❌ Partes faltantes para '{self.entity_name}' ({entity_type}): {missing_parts}")
                print(f"💡 Partes requeridas para {entity_type}: {required_parts}")
                print(f"🔍 Partes encontradas: {list(entity_player_parts.keys())}")

                # Intentar re-detectar partes si faltan algunas críticas
                print(f"🔄 Re-detectando partes faltantes para '{self.entity_name}'...")
                entity_controller.find_entity_parts()

                # Re-verificar después de re-detección usando las partes que realmente se encontraron
                # EN LUGAR de required_parts, usar las partes que el sistema encontró
                found_parts_after_redetection = [name for name, obj in entity_controller.player_parts.items() if obj is not None]

                if not found_parts_after_redetection:
                    print(f"❌ Re-detección fallida: no se encontraron partes para '{self.entity_name}'")
                    print("💡 Asegúrate de que la estructura esté cargada y las partes nombradas correctamente")
                    continue
                else:
                    print(f"✅ Partes re-detectadas exitosamente para '{self.entity_name}': {found_parts_after_redetection}")
                    # Actualizar entity_player_parts con las partes re-detectadas
                    entity_player_parts = entity_controller.player_parts

                    # CRÍTICO: Actualizar required_parts para usar las partes que realmente existen
                    # En lugar de requerir partes específicas del tipo, usar las que se encontraron
                    required_parts = found_parts_after_redetection
                    print(f"🔄 Actualizando partes requeridas a: {required_parts}")

            # Mostrar partes encontradas
            found_parts = [name for name, obj in entity_player_parts.items() if obj is not None]
            print(f"✅ Partes encontradas para '{self.entity_name}' ({entity_type}): {len(found_parts)}")
            print(f"🎯 Partes requeridas: {required_parts}")

            # Ejecutar la animación con los player_parts específicos de esta entidad
            # Ya no necesitamos importar animation_engine en cada iteración ✓
            success = execute_animation_block(block, block_start, block_end, entity_player_parts)

            if success:
                success_count += 1
                print(f"✅ Slot {block['slot']} completado: {block['name']}")
            else:
                print(f"❌ Error en slot {block['slot']}: {block['name']}")

            current_frame = block_end + 1

        if success_count > 0:
            # Asegurar que los indicadores están inicializados para esta entidad
            if self.entity_name not in blocks_manager.active_entity_slot_indicators:
                blocks_manager.initialize_entity_slot_indicators(self.entity_name)

            # ⚠️ NO actualizar indicadores visuales globales durante concatenación individual
            # Los indicadores solo se actualizan durante reproducción multi-entidad
            print(f"ℹ️ Indicadores visuales no modificados (concatenación individual)")

            self.report({'INFO'}, f"Entidad '{self.entity_name}' concatenada: {success_count}/{len(sequence)} animaciones")
            print(f"✅ ENTIDAD '{self.entity_name}' CONCATENADA: {success_count}/{len(sequence)} animaciones exitosas")
            print(f"🔒 Timeline global de escena PRESERVADO - sin interferencia con otras entidades")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, f"Error concatenando '{self.entity_name}' - 0 animaciones ejecutadas")
            return {'CANCELLED'}

class ANIMBLOCKS_OT_PlayMultiEntity(Operator):
    """Reproduce todas las entidades simultáneamente"""
    bl_idname = "simple_animblocks.play_multi_entity"
    bl_label = "Reproducir Multi-Entidad"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            # Fallback: crear manager básico si no está disponible
            try:
                from core_system import SimpleAnimationBlocksManager
                blocks_manager = SimpleAnimationBlocksManager()
            except ImportError:
                # Último fallback: crear un manager vacío
                class DummyManager:
                    def __init__(self):
                        self.entities = {}
                        self.current_prompt_folder = None
                        self.prompt_metadata = None
                        self.shared_timeline = True
                        self.max_entities = 8
                        self.active_entity_slot_indicators = {}
                        self.sequence_frame_ranges = {}
                        self.active_slot_indicators = {}
                        self.loop_enabled = False
                        self.max_slots = 50
                        self.player_parts = {}
                        self.current_structure = None

                    def get_loaded_entities(self):
                        return []

                    def initialize_entity_slot_indicators(self, entity_name):
                        if entity_name not in self.active_entity_slot_indicators:
                            self.active_entity_slot_indicators[entity_name] = {}
                            for slot in range(1, 21):
                                self.active_entity_slot_indicators[entity_name][slot] = False

                    def initialize_slots(self):
                        pass

                    def find_player_parts(self):
                        pass

                    def initialize_slot_indicators(self):
                        for i in range(1, self.max_slots + 1):
                            self.active_slot_indicators[i] = False

                    def load_prompt_folder(self, folder_path):
                        """Método dummy para load_prompt_folder"""
                        print(f"DummyManager: Intentando cargar carpeta {folder_path}")
                        return False

                blocks_manager = DummyManager()

        if not blocks_manager.entities:
            self.report({'WARNING'}, "No hay entidades para reproducir")
            return {'CANCELLED'}

        active_entities = []
        for name, entity_data in blocks_manager.entities.items():
            entity_controller = entity_data.get('controller')
            if entity_controller and len([b for b in entity_controller.blocks.values() if b['is_loaded']]) > 0:
                active_entities.append(name)

        if not active_entities:
            self.report({'WARNING'}, "No hay entidades con animaciones cargadas")
            return {'CANCELLED'}

        # Asegurar que todas las entidades activas tienen indicadores inicializados
        for entity_name in active_entities:
            if entity_name not in blocks_manager.active_entity_slot_indicators:
                blocks_manager.initialize_entity_slot_indicators(entity_name)

        # REGISTRAR HANDLER PARA INDICADORES VISUALES EN TIEMPO REAL (si existe el método)
        try:
            if hasattr(blocks_manager, 'register_visual_indicators_handler'):
                blocks_manager.register_visual_indicators_handler()
        except AttributeError:
            print("⚠️ Método register_visual_indicators_handler no disponible (funcionalidad opcional)")

        print(f"🎭 REPRODUCIENDO MULTI-ENTIDAD: {len(active_entities)} entidades activas")
        print(f"🎬 Entidades: {', '.join(active_entities)}")

        # Importar animation_engine UNA SOLA VEZ antes del loop (optimización de rendimiento)
        animation_engine_path = os.path.join(os.path.dirname(__file__), "animation_engine.py")
        spec = importlib.util.spec_from_file_location("animation_engine", animation_engine_path)
        if spec and spec.loader:
            animation_engine_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(animation_engine_module)
            execute_animation_block = animation_engine_module.execute_animation_block
            print("ℹ️ Animation engine cargado una sola vez (optimizado)")
        else:
            print("❌ Error creando spec para animation_engine")
            return {'CANCELLED'}

        # LIMPIAR rangos de frames anteriores
        for entity_name in active_entities:
            # Get the manager to access entities (works whether called on manager or operator)
            blocks_manager = blocks_manager  # This line seems redundant but keeps the reference
            entity_data = blocks_manager.entities[entity_name]
            entity_controller = entity_data.get('controller')
            if entity_controller:
                entity_controller.slot_frame_ranges.clear()

        # ⚠️ Configurar timeline compartido SOLO para multi-entidad - NO AFECTA concatenaciones individuales
        scene = context.scene

        # Calcular el máximo de frames entre entidades activas
        max_frames = 0
        for entity_name in active_entities:
            entity_data = blocks_manager.entities[entity_name]
            entity_controller = entity_data.get('controller')
            if entity_controller:
                entity_frames = sum(block['frame_count'] for block in entity_controller.blocks.values() if block['is_loaded'])
                max_frames = max(max_frames, entity_frames)

        total_frames = max_frames if max_frames > 0 else 360  # Fallback si no hay frames
        fps = blocks_manager.prompt_metadata.get('configuracion_global', {}).get('fps', 24) if blocks_manager.prompt_metadata else 24

        # ⚠️ SOLO modificar timeline si estamos en modo multi-entidad completo
        # Las concatenaciones individuales NO modifican el timeline global
        scene.frame_start = 1
        scene.frame_end = total_frames
        scene.frame_current = 1
        scene.render.fps = fps

        print(f"⏱️ Timeline compartido configurado: 1-{total_frames} frames ({total_frames/fps:.1f}s)")
        print(f"ℹ️ Este timeline solo afecta la reproducción multi-entidad, no las concatenaciones individuales")

        # Ejecutar todas las entidades en paralelo
        success_count = 0
        total_animations = 0

        for entity_name in active_entities:
            entity_data = blocks_manager.entities[entity_name]
            entity_controller = entity_data.get('controller')
            if entity_controller:
                sequence = entity_controller.get_loaded_blocks_sequence()
                
                # FILTRO: Si hay slots seleccionados para esta entidad, usar solo esos
                if hasattr(blocks_manager, 'selected_slots') and blocks_manager.selected_slots:
                    selected_for_entity = blocks_manager.selected_slots.get(entity_name, {})
                    if selected_for_entity:
                        # Filtrar la secuencia para solo incluir slots seleccionados
                        original_count = len(sequence)
                        sequence = [block for block in sequence if selected_for_entity.get(block['slot'], False)]
                        print(f"🎯 Slots seleccionados para '{entity_name}': {original_count} → {len(sequence)}")
                        print(f"   Slots: {[block['slot'] for block in sequence]}")
                    else:
                        print(f"ℹ️ No hay slots seleccionados para '{entity_name}' - usando todos")
                
                entity_player_parts = entity_controller.player_parts

                if sequence:
                    print(f"🎬 Ejecutando {entity_name}: {len(sequence)} animaciones")
                    total_animations += len(sequence)

                    # Ejecutar cada animación de esta entidad (cada entidad tiene su propio timeline relativo)
                    entity_current_frame = 1
            
                    # Ejecutar cada animación de esta entidad
                    entity_success_count = 0
                    for block in sequence:
                        block_start = entity_current_frame
                        block_end = entity_current_frame + block['frame_count'] - 1

                        # ALMACENAR EL RANGO DE FRAMES PARA ESTE SLOT
                        slot_num = block['slot']
                        entity_controller.slot_frame_ranges[slot_num] = {
                            'start_frame': block_start,
                            'end_frame': block_end,
                            'frame_count': block['frame_count'],
                            'name': block['name']
                        }

                        print(f"  🎯 {entity_name} - {block['name']}: frames {block_start}-{block_end}")

                        # Verificar player_parts
                        found_parts = [name for name, obj in entity_player_parts.items() if obj is not None]
                        if len(found_parts) == 0:
                            print(f"  ❌ No se encontraron partes para {entity_name}")
                            continue

                        # Ejecutar animación
                        # Ya no necesitamos importar animation_engine en cada iteración ✓
                        success = execute_animation_block(block, block_start, block_end, entity_player_parts)
                        if success:
                            entity_success_count += 1
                            print(f"  ✅ {entity_name} - {block['name']} completado")
                        else:
                            print(f"  ❌ Error en {entity_name} - {block['name']}")

                        entity_current_frame = block_end + 1

                    if entity_success_count > 0:
                        success_count += 1
                        print(f"  📊 {entity_name}: {entity_success_count}/{len(sequence)} animaciones exitosas")

        if success_count > 0:
            # ACTUALIZAR INDICADORES INICIALES
            blocks_manager.update_visual_indicators(bpy.context.scene.frame_current)

            # Forzar actualización de la interfaz para mostrar indicadores iniciales
            if hasattr(bpy.context, 'screen'):
                bpy.context.screen.areas.update()

            self.report({'INFO'}, f"Multi-entidad ejecutada: {success_count} entidades, {total_animations} animaciones totales")
            print(f"✅ MULTI-ENTIDAD EJECUTADA: {success_count}/{len(active_entities)} entidades activas")
            print(f"🎬 Total de animaciones ejecutadas: {total_animations}")
            print(f"👁️ Indicadores visuales ACTIVADOS")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Error en reproducción multi-entidad")
            return {'CANCELLED'}

# ============================================================================
# OPERADORES ADICIONALES
# ============================================================================

class ANIMBLOCKS_OT_DiagnoseJerry(Operator):
    """Diagnóstico completo del sistema Jerry para Prompt_002"""
    bl_idname = "simple_animblocks.diagnose_jerry"
    bl_label = "Diagnosticar Jerry"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        self.diagnose_jerry_system()
        return {'FINISHED'}

    def diagnose_jerry_system(self):
        """Diagnóstico completo del sistema Jerry"""
        print("\n🐕 DIAGNÓSTICO DEL SISTEMA JERRY - Prompt_002")
        print("="*70)

        # 1. Verificar estructura Jerry.blend
        jerry_blend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "estructura_lista", "jerry.blend")
        print(f"📁 Archivo Jerry.blend: {os.path.basename(jerry_blend_path)}")
        exists = os.path.exists(jerry_blend_path)
        print(f"   {'✅' if exists else '❌'} Existe: {exists}")

        if not exists:
            print("   🚨 ERROR: Jerry.blend no encontrado - las animaciones fallarán")
            return

        # 2. Verificar objetos Jerry en escena
        print("\n🎭 OBJETOS JERRY EN ESCENA:")
        jerry_objects = []
        for obj in bpy.data.objects:
            if 'jerry' in obj.name.lower():
                jerry_objects.append(obj)
                print(f"   • {obj.name} ({obj.type})")

        if not jerry_objects:
            print("   ❌ No hay objetos Jerry en escena")
            print("   💡 SOLUCIÓN: Carga la estructura Jerry.blend primero")
            return

        # 3. Buscar partes del cuerpo como esperan los scripts
        print("\n🔍 BUSCANDO PARTES DEL CUERPO:")

        # Mapeo de partes esperadas por los scripts
        expected_parts = {
            'body': ['body', 'jerry.body'],
            'head': ['head', 'jerry.head'],
            'tail': ['tail', 'jerry.tail'],
            'mane': ['mane', 'jerry.mane'],
            'leggings': ['leggings', 'jerry.leggings'],
            'leg4': ['leg4', 'jerry.leg4'],  # Front left
            'leg4.001': ['leg4.001', 'jerry.leg4.001'],  # Front right
            'leg4.002': ['leg4.002', 'jerry.leg4.002'],  # Back left
            'leg4.003': ['leg4.003', 'jerry.leg4.003'],  # Back right
            'boca superior': ['boca superior', 'mouth_upper'],
            'boca inferior': ['boca inferior', 'mouth_lower'],
            'ojos': ['ojos', 'eyes'],
            'oreja 1': ['oreja 1', 'ear_left'],
            'oreja2': ['oreja2', 'ear_right']
        }

        found_parts = {}
        missing_parts = []

        for part_name, possible_names in expected_parts.items():
            found = False
            for possible_name in possible_names:
                for obj in bpy.data.objects:
                    if obj.name.lower() == possible_name.lower():
                        found_parts[part_name] = obj
                        print(f"   ✅ {part_name}: {obj.name}")
                        found = True
                        break
                if found:
                    break

            if not found:
                missing_parts.append(part_name)
                print(f"   ❌ {part_name}: NO ENCONTRADO")

        # 4. Verificar partes críticas
        critical_parts = ['body', 'head', 'tail', 'leg4', 'leg4.001', 'leg4.002', 'leg4.003']
        critical_found = [p for p in critical_parts if p in found_parts]
        critical_missing = [p for p in critical_parts if p not in found_parts]

        print("\n🎯 PARTES CRÍTICAS:")
        print(f"   ✅ Encontradas: {len(critical_found)}/7")
        if critical_missing:
            print(f"   ❌ Faltantes: {critical_missing}")
            print("   🚨 ERROR: Las animaciones NO funcionarán")

        # 5. Verificar archivos de animación
        print("\n📁 ARCHIVOS DE ANIMACIÓN:")
        jerry_anim_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "animacion", "Prompt_002", "jerry")
        if os.path.exists(jerry_anim_dir):
            py_files = [f for f in os.listdir(jerry_anim_dir) if f.endswith('.py')]
            print(f"   ✅ Directorio existe: {len(py_files)} archivos .py")
            for py_file in py_files:
                print(f"      • {py_file}")
        else:
            print(f"   ❌ Directorio no existe: {jerry_anim_dir}")

        # 6. Resultado final
        print("\n🏁 RESULTADO:")
        if len(critical_found) == 7:
            print("   ✅ SISTEMA JERRY LISTO PARA ANIMACIONES")
            print("   🎬 Las concatenaciones deberían funcionar")
        else:
            print("   ❌ PROBLEMAS CRÍTICOS DETECTADOS")
            print("   📋 SOLUCIONES:")
            print("      1. Cargar Jerry.blend en la escena")
            print("      2. Verificar nombres de objetos")
            print("      3. Asegurar que todas las partes críticas existan")

        print("="*70)

class ANIMBLOCKS_OT_ToggleNarrativeMode(Operator):
    """Alterna entre modo coherencia visual y modo narrativa expresiva"""
    bl_idname = "simple_animblocks.toggle_narrative_mode"
    bl_label = "Alternar Modo Narrativa"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            # Fallback: crear manager básico si no está disponible
            try:
                from core_system import SimpleAnimationBlocksManager
                blocks_manager = SimpleAnimationBlocksManager()
            except ImportError:
                # Último fallback: crear un manager vacío
                class DummyManager:
                    def __init__(self):
                        self.entities = {}
                        self.current_prompt_folder = None
                        self.prompt_metadata = None
                        self.shared_timeline = True
                        self.max_entities = 8
                        self.active_entity_slot_indicators = {}
                        self.sequence_frame_ranges = {}
                        self.active_slot_indicators = {}
                        self.loop_enabled = False
                        self.max_slots = 50
                        self.player_parts = {}
                        self.current_structure = None

                    def get_loaded_entities(self):
                        return []

                    def initialize_entity_slot_indicators(self, entity_name):
                        if entity_name not in self.active_entity_slot_indicators:
                            self.active_entity_slot_indicators[entity_name] = {}
                            for slot in range(1, 21):
                                self.active_entity_slot_indicators[entity_name][slot] = False

                    def initialize_slots(self):
                        pass

                    def find_player_parts(self):
                        pass

                    def initialize_slot_indicators(self):
                        for i in range(1, self.max_slots + 1):
                            self.active_slot_indicators[i] = False

                blocks_manager = DummyManager()

        new_mode = blocks_manager.toggle_narrative_mode()
        context.scene.narrative_mode_enabled = new_mode

        mode_name = "🎭 NARRATIVA" if new_mode else "🎯 COHERENCIA VISUAL"
        self.report({'INFO'}, f"Modo cambiado a: {mode_name}")
        return {'FINISHED'}

class ANIMBLOCKS_OT_CaptureBaseOrientations(Operator):
    """Captura las orientaciones base de todas las entidades para animaciones relativas"""
    bl_idname = "simple_animblocks.capture_base_orientations"
    bl_label = "Capturar Orientaciones Base"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            # Fallback: crear manager básico si no está disponible
            try:
                from core_system import SimpleAnimationBlocksManager
                blocks_manager = SimpleAnimationBlocksManager()
            except ImportError:
                # Último fallback: crear un manager vacío
                class DummyManager:
                    def __init__(self):
                        self.entities = {}
                        self.current_prompt_folder = None
                        self.prompt_metadata = None
                        self.shared_timeline = True
                        self.max_entities = 8
                        self.active_entity_slot_indicators = {}
                        self.sequence_frame_ranges = {}
                        self.active_slot_indicators = {}
                        self.loop_enabled = False
                        self.max_slots = 50
                        self.player_parts = {}
                        self.current_structure = None

                    def get_loaded_entities(self):
                        return []

                    def initialize_entity_slot_indicators(self, entity_name):
                        if entity_name not in self.active_entity_slot_indicators:
                            self.active_entity_slot_indicators[entity_name] = {}
                            for slot in range(1, 21):
                                self.active_entity_slot_indicators[entity_name][slot] = False

                    def initialize_slots(self):
                        pass

                    def find_player_parts(self):
                        pass

                    def initialize_slot_indicators(self):
                        for i in range(1, self.max_slots + 1):
                            self.active_slot_indicators[i] = False

                    def load_prompt_folder(self, folder_path):
                        """Método dummy para load_prompt_folder"""
                        print(f"DummyManager: Intentando cargar carpeta {folder_path}")
                        return False

                    def get_loaded_blocks_sequence(self):
                        """Método dummy para get_loaded_blocks_sequence"""
                        return []

                    def capture_all_base_orientations(self):
                        """Método dummy para capture_all_base_orientations"""
                        return False

                    def toggle_narrative_mode(self):
                        """Método dummy para toggle_narrative_mode"""
                        return False

                    def unregister_visual_indicators_handler(self):
                        """Método dummy para unregister_visual_indicators_handler"""
                        pass

                    def update_visual_indicators(self, frame):
                        """Método dummy para update_visual_indicators"""
                        pass

                    def register_visual_indicators_handler(self):
                        """Método dummy para register_visual_indicators_handler"""
                        pass

                blocks_manager = DummyManager()

        if not blocks_manager.entities:
            self.report({'WARNING'}, "No hay entidades para capturar orientaciones")
            return {'CANCELLED'}

        success = blocks_manager.capture_all_base_orientations()
        if success:
            context.scene.base_orientations_captured = True
            context.scene.relative_animation_enabled = True
            self.report({'INFO'}, "Orientaciones base capturadas exitosamente")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Error capturando orientaciones base")
            return {'CANCELLED'}

class ANIMBLOCKS_OT_ExportSequence(Operator):
    """Exporta la secuencia completa como archivo Python"""
    bl_idname = "simple_animblocks.export_sequence"
    bl_label = "Exportar Secuencia"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.py", options={'HIDDEN'})

    def execute(self, context):
        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            # Fallback: crear manager básico si no está disponible
            try:
                from core_system import SimpleAnimationBlocksManager
                blocks_manager = SimpleAnimationBlocksManager()
            except ImportError:
                # Último fallback: crear un manager vacío
                class DummyManager:
                    def __init__(self):
                        self.entities = {}
                        self.current_prompt_folder = None
                        self.prompt_metadata = None
                        self.shared_timeline = True
                        self.max_entities = 8
                        self.active_entity_slot_indicators = {}
                        self.sequence_frame_ranges = {}
                        self.active_slot_indicators = {}
                        self.loop_enabled = False
                        self.max_slots = 50
                        self.player_parts = {}
                        self.current_structure = None

                    def get_loaded_entities(self):
                        return []

                    def initialize_entity_slot_indicators(self, entity_name):
                        if entity_name not in self.active_entity_slot_indicators:
                            self.active_entity_slot_indicators[entity_name] = {}
                            for slot in range(1, 21):
                                self.active_entity_slot_indicators[entity_name][slot] = False

                    def initialize_slots(self):
                        pass

                    def find_player_parts(self):
                        pass

                    def initialize_slot_indicators(self):
                        for i in range(1, self.max_slots + 1):
                            self.active_slot_indicators[i] = False

                blocks_manager = DummyManager()
        sequence = blocks_manager.get_loaded_blocks_sequence()

        if not sequence:
            self.report({'WARNING'}, "No hay bloques para exportar")
            return {'CANCELLED'}

        # Generar el archivo de animación concatenada
        success = self.export_sequence_to_file(sequence, self.filepath)
        if success:
            filename = os.path.basename(self.filepath)
            self.report({'INFO'}, f"Secuencia exportada: {filename}")
            print(f"✅ SECUENCIA EXPORTADA: {self.filepath}")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Error exportando secuencia")
            return {'CANCELLED'}

    def invoke(self, context, event):
        # Nombre por defecto basado en los bloques
        from .core_system import blocks_manager
        sequence = blocks_manager.get_loaded_blocks_sequence()
        if sequence:
            block_names = [block['name'][:10] for block in sequence[:3]]  # Primeros 3 nombres
            default_name = "_".join(block_names) + "_sequence.py"
        else:
            default_name = "sequence_export.py"

        self.filepath = default_name
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def export_sequence_to_file(self, sequence, filepath):
        """Exporta la secuencia completa como un archivo .py"""
        try:
            from .core_system import blocks_manager

            # Calcular información de la secuencia
            total_frames = blocks_manager.calculate_total_frames()
            total_duration = total_frames / 24.0  # 24 FPS

            # Recopilar todos los keyframes de las actions compartidas
            keyframes_data = self.collect_sequence_keyframes()

            # NUEVO: Recopilar información de orientación relativa si existe
            orientation_data = self.collect_orientation_data(sequence)

            # Generar código Python
            code = self.generate_sequence_code(sequence, total_frames, total_duration, keyframes_data, orientation_data)

            # Escribir archivo
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)

            print(f"📝 Archivo generado: {filepath}")
            print(f"🎬 Frames totales: {total_frames}")
            print(f"⏱️ Duración: {total_duration:.2f}s")

            return True

        except Exception as e:
            print(f"❌ Error exportando secuencia: {e}")
            import traceback
            traceback.print_exc()
            return False

    def collect_sequence_keyframes(self):
        """Recopila todos los keyframes de las actions compartidas"""
        keyframes_data = {}

        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE' and obj.animation_data and obj.animation_data.action:
                action = obj.animation_data.action
                obj_keyframes = {}

                for fcurve in action.fcurves:
                    data_path = fcurve.data_path
                    if data_path not in obj_keyframes:
                        obj_keyframes[data_path] = []

                    for keyframe in fcurve.keyframe_points:
                        frame = int(keyframe.co.x)
                        value = keyframe.co.y
                        obj_keyframes[data_path].append((frame, value))

                if obj_keyframes:
                    keyframes_data[obj.name] = obj_keyframes

        return keyframes_data

    def generate_sequence_code(self, sequence, total_frames, total_duration, keyframes_data, orientation_data=None):
        """Genera el código Python para la animación concatenada"""
        import datetime

        # Información de los bloques originales
        block_info = []
        for block in sequence:
            block_info.append(f"    '{block['name']}': {{'frames': {block['frame_count']}, 'fps': {block['fps']}}}")

        blocks_info_str = ",\n".join(block_info)

        # Información de orientación si existe
        orientation_info = ""
        if orientation_data:
            orientation_info = f"\n# Información de orientación relativa\nORIENTATION_DATA = {orientation_data}\n"

        code = f'''#!/usr/bin/env python3
"""
Animación Secuencia Concatenada - Exportada desde Simple Animation Blocks Manager
Bloques originales concatenados en una sola animación
Fecha: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

import bpy
import math

# Información de la animación concatenada
ANIMATION_INFO = {{
    'name': 'sequence_concatenated',
    'description': 'Animación concatenada desde múltiples bloques - exportada automáticamente',
    'frame_count': {total_frames},
    'fps': 24,
    'duration_seconds': {total_duration:.2f},
    'original_blocks': {{
{blocks_info_str}
    }}
}}{orientation_info}
'''

        # Agregar código para insertar todos los keyframes recopilados
        code += self.generate_keyframes_code(keyframes_data)

        code += f'''
def execute_animation(player_parts, start_frame=1, end_frame={total_frames}):
    """
    Animación concatenada - reproduce todos los bloques en secuencia
    Compatible con simple_animation_player.py
    """
    print(f"SEQUENCE: Ejecutando animación concatenada: {{ANIMATION_INFO['name']}}")
    print(f"INFO: Frames: {{start_frame}} - {{end_frame}} ({{end_frame - start_frame + 1}} frames)")
    print(f"ORIGINAL: {{len(ANIMATION_INFO['original_blocks'])}} bloques concatenados")

    # Obtener referencias a los armatures desde player_parts
    body_armature = player_parts.get('body')
    head_armature = player_parts.get('head')
    left_arm_armature = player_parts.get('left_arm')
    right_arm_armature = player_parts.get('right_arm')
    left_leg_armature = player_parts.get('left_leg')
    right_leg_armature = player_parts.get('right_leg')

    # Verificar armatures
    required_armatures = [body_armature, head_armature, left_arm_armature, right_arm_armature, left_leg_armature, right_leg_armature]
    if not all(required_armatures):
        missing = []
        names = ['body', 'head', 'left_arm', 'right_arm', 'left_leg', 'right_leg']
        for i, arm in enumerate(required_armatures):
            if not arm:
                missing.append(names[i])
        print(f"ERROR: Armatures faltantes: {{missing}}")
        return False

    # Crear actions para la animación concatenada
    animation_name = f"concatenated_sequence_{{start_frame}}_{{end_frame}}"
    for armature in [body_armature, head_armature, left_arm_armature, right_arm_armature, left_leg_armature, right_leg_armature]:
        if armature:
            if not armature.animation_data:
                armature.animation_data_create()
            if not armature.animation_data.action:
                action = bpy.data.actions.new(name=f"{{armature.name}}_{{animation_name}}")
                armature.animation_data.action = action

    print("ACTIONS: Creadas actions compartidas para animación concatenada")

    # KEYFRAMES CONCATENADOS - Insertados automáticamente desde las actions originales
    print("KEYFRAMES: Insertando keyframes concatenados...")

    print(f"SUCCESS: Animación concatenada completada: {{end_frame - start_frame + 1}} frames")
    print(f"COMPOSED: {{len(ANIMATION_INFO['original_blocks'])}} bloques originales")
    return True

# Información adicional
if __name__ == "__main__":
    print("SEQUENCE: Animación Concatenada Exportada")
    print(f"📁 Nombre: {{ANIMATION_INFO['name']}}")
    print(f"📝 Descripción: {{ANIMATION_INFO['description']}}")
    print(f"🎬 Frames: {{ANIMATION_INFO['frame_count']}}")
    print(f"⏱️ Duración: {{ANIMATION_INFO['duration_seconds']}}s")
    print(f"🧩 Bloques originales: {{len(ANIMATION_INFO['original_blocks'])}}")
    print("\\nSUCCESS: Compatible con Simple Animation Player")
'''

        return code

    def generate_keyframes_code(self, keyframes_data):
        """Genera código Python para insertar todos los keyframes"""
        code_lines = []
        code_lines.append("    # Insertar keyframes recopilados de las actions originales")
        code_lines.append("    print(\"KEYFRAMES: Insertando keyframes concatenados...\")")
        code_lines.append("")

        for obj_name, obj_keyframes in keyframes_data.items():
            code_lines.append(f"    # Keyframes para {obj_name}")
            if obj_name.lower().endswith('_armature'):
                armature_var = obj_name.lower().replace('_armature', '_armature')
            else:
                armature_var = obj_name.lower() + '_armature'

            for data_path, keyframes in obj_keyframes.items():
                if 'pose.bones' in data_path:
                    # Es un keyframe de pose bone
                    bone_name = data_path.split('["')[1].split('"]')[0]
                    for frame, value in keyframes:
                        if len(keyframes) > 1 and keyframes.index((frame, value)) > 0:
                            prev_frame, prev_value = keyframes[keyframes.index((frame, value)) - 1]
                            if abs(value - prev_value) > 0.001:  # Solo si cambió significativamente
                                code_lines.append(f"    set_bone_rotation_internal({armature_var}, '{bone_name}', ({value}, 0, 0), {frame})")
                else:
                    # Es un keyframe de objeto regular
                    for frame, value in keyframes:
                        if data_path == 'location':
                            if len(keyframes) > 1 and keyframes.index((frame, value)) > 0:
                                prev_frame, prev_value = keyframes[keyframes.index((frame, value)) - 1]
                                if abs(value - prev_value) > 0.001:
                                    code_lines.append(f"    set_keyframe({armature_var}, {frame}, location=({armature_var}.location.x, {value}, {armature_var}.location.z))")
                        elif data_path == 'rotation_euler':
                            if len(keyframes) > 1 and keyframes.index((frame, value)) > 0:
                                prev_frame, prev_value = keyframes[keyframes.index((frame, value)) - 1]
                                if abs(value - prev_value) > 0.001:
                                    code_lines.append(f"    set_keyframe({armature_var}, {frame}, rotation=({value}, {armature_var}.rotation_euler.y, {armature_var}.rotation_euler.z))")

        code_lines.append("")
        code_lines.append("    print(f\"KEYFRAMES: Insertados keyframes para {{len(keyframes_data)}} objetos\")")
        code_lines.append("")

        return "\n".join(code_lines)

    def collect_orientation_data(self, sequence):
        """Recopila información de orientación relativa para la exportación"""
        orientation_data = {}
        from .core_system import blocks_manager

        for block in sequence:
            entity_name = block.get('entity_name')
            if entity_name and entity_name in blocks_manager.entities:
                entity_data = blocks_manager.entities[entity_name]
                entity_controller = entity_data.get('controller')
                if entity_controller and entity_controller.has_base_orientation():
                    orientation_data[entity_name] = {
                        'base_orientation': entity_controller.get_base_orientation(),
                        'adapted_blocks': [block['name']] if block.get('adapted_for_orientation') else []
                    }

        return orientation_data

# ============================================================================
# OPERADORES DE EVALUACIÓN
# ============================================================================

class ANIMBLOCKS_OT_SetRating(Operator):
    """Calificar una animación con estrellas"""
    bl_idname = "simple_animblocks.set_rating"
    bl_label = "Calificar Animación"
    bl_options = {'REGISTER', 'UNDO'}

    entity_name: StringProperty(name="Entidad", default="")
    slot: IntProperty(name="Slot", default=1, min=1)  # Sin límite máximo

    rating: IntProperty(name="Calificación", default=3, min=1, max=10, description="Calificación de 1-10 estrellas")

    def execute(self, context):
        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            # Fallback: crear manager básico si no está disponible
            try:
                from core_system import SimpleAnimationBlocksManager
                blocks_manager = SimpleAnimationBlocksManager()
            except ImportError:
                # Último fallback: crear un manager vacío
                class DummyManager:
                    def __init__(self):
                        self.entities = {}
                blocks_manager = DummyManager()

        if self.entity_name in blocks_manager.entities:
            entity_data = blocks_manager.entities[self.entity_name]
            entity_controller = entity_data.get('controller')
            if entity_controller and self.slot in entity_controller.blocks:
                entity_controller.blocks[self.slot]['rating'] = self.rating
                self.report({'INFO'}, f"Calificación {self.rating}⭐ asignada a {self.entity_name} slot {self.slot}")
                return {'FINISHED'}

        self.report({'ERROR'}, f"Entidad '{self.entity_name}' o slot {self.slot} no válido")
        return {'CANCELLED'}

    def invoke(self, context, event):
        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            try:
                from core_system import SimpleAnimationBlocksManager
                blocks_manager = SimpleAnimationBlocksManager()
            except ImportError:
                class DummyManager:
                    def __init__(self):
                        self.entities = {}
                blocks_manager = DummyManager()

        if self.entity_name in blocks_manager.entities:
            entity_data = blocks_manager.entities[self.entity_name]
            entity_controller = entity_data.get('controller')
            if entity_controller and self.slot in entity_controller.blocks:
                self.rating = entity_controller.blocks[self.slot]['rating'] or 3
        return context.window_manager.invoke_props_dialog(self)

class ANIMBLOCKS_OT_SetFeedback(Operator):
    """Agregar comentarios a una animación"""
    bl_idname = "simple_animblocks.set_feedback"
    bl_label = "Comentarios"
    bl_options = {'REGISTER', 'UNDO'}

    entity_name: StringProperty(name="Entidad", default="")
    slot: IntProperty(name="Slot", default=1, min=1)  # Sin límite máximo

    feedback: StringProperty(name="Comentarios", default="", description="Comentarios sobre qué mejorar")

    def execute(self, context):
        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            try:
                from core_system import SimpleAnimationBlocksManager
                blocks_manager = SimpleAnimationBlocksManager()
            except ImportError:
                class DummyManager:
                    def __init__(self):
                        self.entities = {}
                blocks_manager = DummyManager()

        if self.entity_name in blocks_manager.entities:
            entity_data = blocks_manager.entities[self.entity_name]
            entity_controller = entity_data.get('controller')
            if entity_controller and self.slot in entity_controller.blocks:
                entity_controller.blocks[self.slot]['feedback'] = self.feedback
                self.report({'INFO'}, f"Comentarios guardados en {self.entity_name} slot {self.slot}")
                return {'FINISHED'}

        self.report({'ERROR'}, f"Entidad '{self.entity_name}' o slot {self.slot} no válido")
        return {'CANCELLED'}

    def invoke(self, context, event):
        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            try:
                from core_system import SimpleAnimationBlocksManager
                blocks_manager = SimpleAnimationBlocksManager()
            except ImportError:
                class DummyManager:
                    def __init__(self):
                        self.entities = {}
                blocks_manager = DummyManager()

        if self.entity_name in blocks_manager.entities:
            entity_data = blocks_manager.entities[self.entity_name]
            entity_controller = entity_data.get('controller')
            if entity_controller and self.slot in entity_controller.blocks:
                self.feedback = entity_controller.blocks[self.slot]['feedback']
        return context.window_manager.invoke_props_dialog(self)

class ANIMBLOCKS_OT_ClearEntityStructure(Operator):
    """Limpia la estructura cargada de una entidad específica"""
    bl_idname = "simple_animblocks.clear_entity_structure"
    bl_label = "Limpiar Estructura"
    bl_options = {'REGISTER', 'UNDO'}

    entity_name: StringProperty(name="Entidad", default="")

    def execute(self, context):
        if not self.entity_name:
            self.report({'ERROR'}, "Nombre de entidad no especificado")
            return {'CANCELLED'}

        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            # Fallback: crear manager básico si no está disponible
            try:
                from core_system import SimpleAnimationBlocksManager
                blocks_manager = SimpleAnimationBlocksManager()
            except ImportError:
                class DummyManager:
                    def __init__(self):
                        self.entities = {}
                blocks_manager = DummyManager()

        if self.entity_name not in blocks_manager.entities:
            self.report({'ERROR'}, f"Entidad '{self.entity_name}' no encontrada")
            return {'CANCELLED'}

        try:
            print(f"🧹 LIMPIANDO ESTRUCTURA DE ENTIDAD: {self.entity_name}")

            entity_data = blocks_manager.entities[self.entity_name]

            # Limpiar objetos importados de la escena (usando nombres)
            scene_object_names = entity_data.get('scene_objects', [])
            if scene_object_names:
                print(f"  🗑️ Removiendo {len(scene_object_names)} objetos importados...")
                objects_removed = 0
                for obj_name in scene_object_names:
                    if obj_name in bpy.data.objects:
                        obj = bpy.data.objects[obj_name]
                        bpy.data.objects.remove(obj, do_unlink=True)
                        print(f"    ✅ Removido: {obj_name}")
                        objects_removed += 1
                print(f"  📊 Objetos removidos: {objects_removed}/{len(scene_object_names)}")
                scene_object_names.clear()

            # Limpiar partes del cuerpo encontradas
            entity_controller = entity_data.get('controller')
            if entity_controller:
                entity_controller.player_parts = {
                    'body': None, 'head': None, 'left_arm': None, 'right_arm': None,
                    'left_leg': None, 'right_leg': None
                }
                print("  ✅ Partes del cuerpo limpiadas")

            # Marcar entidad como no cargada
            entity_data['is_loaded'] = False
            entity_data['blend_file'] = ''
            entity_data['scene_objects'] = []  # Resetear lista de nombres de objetos

            self.report({'INFO'}, f"Estructura de '{self.entity_name}' limpiada - listo para recargar")
            print(f"✅ ESTRUCTURA DE '{self.entity_name}' LIMPIADA - listo para recargar")

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error limpiando estructura: {str(e)}")
            print(f"❌ Error limpiando estructura de {self.entity_name}: {e}")
            return {'CANCELLED'}

class ANIMBLOCKS_OT_ApplyScenario(Operator):
    """Aplicar los cambios del escenario a la escena de Blender"""
    bl_idname = "simple_animblocks.apply_scenario"
    bl_label = "Aplicar"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            # Fallback: crear manager básico si no está disponible
            try:
                from core_system import SimpleAnimationBlocksManager
                blocks_manager = SimpleAnimationBlocksManager()
            except ImportError:
                class DummyManager:
                    def __init__(self):
                        self.entities = {}
                        self.current_prompt_folder = None
                        self.prompt_metadata = None
                blocks_manager = DummyManager()

        # AUTOMÁTICAMENTE CARGAR CONFIGURACIÓN DEL SLOT PARA HDRI ANTES DE APLICAR ESCENARIO
        print("🔄 Cargando configuración automática del slot para HDRI...")
        try:
            from hdri_complete_system import load_slot_sky_configuration
            success = load_slot_sky_configuration()
            if success:
                print("✅ Configuración del slot cargada exitosamente para HDRI")
            else:
                print("⚠️ No se pudo cargar configuración del slot, usando configuración actual del panel HDRI")
        except ImportError as e:
            print(f"⚠️ Sistema HDRI no disponible: {e}")

        # Verificar que hay un prompt cargado
        if not blocks_manager.current_prompt_folder:
            self.report({'ERROR'}, "No hay ningún prompt cargado. Carga un prompt primero.")
            return {'CANCELLED'}

        # Construir la ruta a la carpeta ecena del prompt actual
        prompt_path = Path(blocks_manager.current_prompt_folder)
        ecena_folder = prompt_path / "ecena"

        if not ecena_folder.exists():
            self.report({'ERROR'}, f"Carpeta 'ecena' no encontrada en: {ecena_folder}")
            return {'CANCELLED'}

        # Buscar archivos de escenario (slots de escenario)
        scenario_files = list(ecena_folder.glob("slot_*.py"))
        if not scenario_files:
            self.report({'ERROR'}, f"No se encontraron archivos de escenario en: {ecena_folder}")
            return {'CANCELLED'}

        # Ejecutar todos los archivos de escenario encontrados
        executed_count = 0
        for scenario_file in sorted(scenario_files):
            try:
                print(f"🎭 EJECUTANDO ESCENARIO: {scenario_file.name}")

                # Leer el contenido del archivo
                with open(scenario_file, 'r', encoding='utf-8') as f:
                    scenario_code = f.read()

                # Crear un namespace local para ejecutar el código
                local_namespace = {
                    'bpy': bpy,
                    'math': __import__('math'),
                    'os': __import__('os'),
                    'json': __import__('json'),
                    'Path': __import__('pathlib').Path,
                }

                # Ejecutar el código del escenario
                exec(scenario_code, local_namespace)

                # Si tiene función execute_animation, ejecutarla
                if 'execute_animation' in local_namespace:
                    execute_func = local_namespace['execute_animation']
                    # Ejecutar con parámetros por defecto (escenario base)
                    result = execute_func({}, start_frame=1, end_frame=103)
                    if result:
                        print(f"✅ Escenario '{scenario_file.name}' ejecutado exitosamente")
                        executed_count += 1
                    else:
                        print(f"⚠️ Escenario '{scenario_file.name}' ejecutado con advertencias")
                        executed_count += 1
                else:
                    print(f"⚠️ Archivo '{scenario_file.name}' no tiene función execute_animation")
                    # Intentar ejecutar el código directamente si no hay función específica
                    executed_count += 1

            except Exception as e:
                print(f"❌ Error ejecutando escenario '{scenario_file.name}': {e}")
                import traceback
                traceback.print_exc()
                continue

        if executed_count > 0:
            self.report({'INFO'}, f"Escenario aplicado: {executed_count} archivo(s) ejecutado(s)")
            print(f"🎬 ESCENARIO COMPLETO APLICADO: {executed_count} archivo(s) procesado(s)")
            print("🌍 Mundo, cielo, agua y terreno configurados en la escena")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "No se pudo aplicar ningún escenario")
            return {'CANCELLED'}


class ANIMBLOCKS_OT_ToggleSlotSelection(Operator):
    """Alterna la selección de un slot para inclusión en la secuencia final"""
    bl_idname = "simple_animblocks.toggle_slot_selection"
    bl_label = "Seleccionar Slot"
    bl_options = {'REGISTER', 'UNDO'}

    entity_name: StringProperty(name="Entidad", default="")
    slot: IntProperty(name="Slot", default=1, min=1)  # Sin límite máximo - soporta cualquier número de slots

    def execute(self, context):
        print(f"🎯 ToggleSlotSelection: entity={self.entity_name}, slot={self.slot}")
        
        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            try:
                from core_system import SimpleAnimationBlocksManager
                blocks_manager = SimpleAnimationBlocksManager()
            except ImportError:
                class DummyManager:
                    def __init__(self):
                        self.entities = {}
                        self.selected_slots = {}  # {entity_name: {slot: bool}}
                blocks_manager = DummyManager()

        # Inicializar diccionario de seleccionados si no existe
        if not hasattr(blocks_manager, 'selected_slots'):
            blocks_manager.selected_slots = {}

        # Inicializar entidad si no existe
        if self.entity_name not in blocks_manager.selected_slots:
            blocks_manager.selected_slots[self.entity_name] = {}

        # Toggle el estado
        current_state = blocks_manager.selected_slots[self.entity_name].get(self.slot, False)
        new_state = not current_state
        blocks_manager.selected_slots[self.entity_name][self.slot] = new_state

        # DEBUG: Print current state
        print(f"   DEBUG: Slot {self.slot} toggled from {current_state} to {new_state}")
        print(f"   DEBUG: selected_slots now: {blocks_manager.selected_slots.get(self.entity_name, {})}")

        state_text = "seleccionado" if new_state else "deseleccionado"
        
        self.report({'INFO'}, f"Slot {self.slot} {state_text} para {self.entity_name}")
        print(f"🎯 Slot {self.entity_name}/{self.slot}: {'✅ Seleccionado' if new_state else '❌ Deseleccionado'}")
        return {'FINISHED'}


class ANIMBLOCKS_OT_ClearAllSelections(Operator):
    """Limpia todas las selecciones de slots para una entidad"""
    bl_idname = "simple_animblocks.clear_all_selections"
    bl_label = "Limpiar Selecciones"
    bl_options = {'REGISTER', 'UNDO'}

    entity_name: StringProperty(name="Entidad", default="")

    def execute(self, context):
        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            try:
                from core_system import SimpleAnimationBlocksManager
                blocks_manager = SimpleAnimationBlocksManager()
            except ImportError:
                class DummyManager:
                    def __init__(self):
                        self.selected_slots = {}
                blocks_manager = DummyManager()

        # Inicializar si no existe
        if not hasattr(blocks_manager, 'selected_slots'):
            blocks_manager.selected_slots = {}

        if self.entity_name:
            # Limpiar solo los slots de una entidad específica
            if self.entity_name in blocks_manager.selected_slots:
                count = len(blocks_manager.selected_slots[self.entity_name])
                blocks_manager.selected_slots[self.entity_name] = {}
                self.report({'INFO'}, f"Limpiadas {count} selecciones para {self.entity_name}")
                print(f"🧹 Selecciones limpiadas para {self.entity_name}: {count} slots")
            else:
                self.report({'INFO'}, f"No había selecciones para {self.entity_name}")
        else:
            # Limpiar todas las selecciones
            total = sum(len(v) for v in blocks_manager.selected_slots.values())
            blocks_manager.selected_slots = {}
            self.report({'INFO'}, f"Limpiadas {total} selecciones globales")
            print(f"🧹 Todas las selecciones limpiadas: {total} slots")
        
        return {'FINISHED'}


class ANIMBLOCKS_OT_ExportSlotData(Operator):
    """Exportar datos de evaluación de un slot con sistema avanzado de feedback IA"""
    bl_idname = "simple_animblocks.export_slot_data"
    bl_label = "Exportar Datos del Slot"
    bl_options = {'REGISTER', 'UNDO'}

    entity_name: StringProperty(name="Entidad", default="")
    slot: IntProperty(name="Slot", default=1, min=1)  # Sin límite máximo

    def execute(self, context):
        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            try:
                from core_system import SimpleAnimationBlocksManager
                blocks_manager = SimpleAnimationBlocksManager()
            except ImportError:
                class DummyManager:
                    def __init__(self):
                        self.entities = {}
                blocks_manager = DummyManager()

        # Validar entidad y slot
        if self.entity_name not in blocks_manager.entities:
            self.report({'ERROR'}, f"Entidad '{self.entity_name}' no encontrada")
            return {'CANCELLED'}

        entity_data = blocks_manager.entities[self.entity_name]
        entity_controller = entity_data.get('controller')
        if not entity_controller or self.slot not in entity_controller.blocks:
            self.report({'ERROR'}, f"Slot {self.slot} no válido para entidad '{self.entity_name}'")
            return {'CANCELLED'}

        block = entity_controller.blocks[self.slot]
        if not block['is_loaded']:
            self.report({'ERROR'}, f"Slot {self.slot} de '{self.entity_name}' está vacío")
            return {'CANCELLED'}

        # Usar el sistema avanzado de feedback
        try:
            # Importar desde el módulo feedback_system
            import feedback_system
            collect_slot_analysis_data = feedback_system.collect_slot_analysis_data
            export_enhanced_feedback_json = feedback_system.export_enhanced_feedback_json
            categorize_and_save_json = feedback_system.categorize_and_save_json

            # Recopilar datos completos del slot
            slot_data = collect_slot_analysis_data(blocks_manager, self.entity_name, self.slot)
            if "error" in slot_data:
                self.report({'ERROR'}, f"Error recopilando datos: {slot_data['error']}")
                return {'CANCELLED'}

            # Obtener rating y feedback del usuario
            user_rating = block['rating']
            user_feedback = block['feedback']

            # Exportar JSON enriquecido
            export_path = export_enhanced_feedback_json(slot_data, user_rating, user_feedback, blocks_manager)
            if not export_path:
                self.report({'ERROR'}, "Error exportando feedback enriquecido")
                return {'CANCELLED'}

            # Organizar automáticamente en jerarquía por calidad
            final_path = categorize_and_save_json(export_path, self.entity_name)

            filename = os.path.basename(final_path)
            self.report({'INFO'}, f"Feedback exportado y organizado: {filename}")
            print(f"✅ SISTEMA AVANZADO: Feedback exportado y jerarquizado: {final_path}")
            return {'FINISHED'}

        except ImportError as ie:
            # Fallback al sistema básico si feedback_system no está disponible
            print(f"⚠️ Sistema avanzado no disponible: {ie}, usando exportación básica")
        except Exception as e:
            # Fallback al sistema básico si hay cualquier otro error
            print(f"⚠️ Error en sistema avanzado: {e}, usando exportación básica")

            evaluation_data = {
                'entity_name': self.entity_name,
                'slot_number': self.slot,
                'animation_name': block['name'],
                'rating': block['rating'],
                'feedback': block['feedback'],
                'frame_count': block['frame_count'],
                'fps': block['fps'],
                'timestamp': str(datetime.datetime.now())
            }

            try:
                filename = f"{self.entity_name}_slot_{self.slot}_evaluation.json"
                filepath = os.path.join(os.path.dirname(bpy.data.filepath or os.getcwd()), filename)

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(evaluation_data, f, indent=2, ensure_ascii=False)

                self.report({'INFO'}, f"Datos básicos exportados: {filename}")
                print(f"✅ Datos de evaluación exportados (básico): {filepath}")
                return {'FINISHED'}

            except Exception as e:
                self.report({'ERROR'}, f"Error exportando datos básicos: {str(e)}")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error en exportación avanzada: {str(e)}")
            return {'CANCELLED'}

class ANIMBLOCKS_OT_RefreshEntity(Operator):
    """Recarga una entidad específica sin afectar a otras entidades"""
    bl_idname = "simple_animblocks.refresh_entity"
    bl_label = "Actualizar Entidad"
    bl_options = {'REGISTER', 'UNDO'}

    entity_name: StringProperty(name="Entidad", default="")

    def execute(self, context):
        # CORRECCIÓN: Usar importaciones absolutas
        import core_system
        blocks_manager = core_system.blocks_manager

        if not self.entity_name:
            self.report({'ERROR'}, "Nombre de entidad no especificado")
            return {'CANCELLED'}

        # Verificar que la entidad existe
        if self.entity_name not in blocks_manager.entities:
            self.report({'ERROR'}, f"Entidad '{self.entity_name}' no encontrada")
            return {'CANCELLED'}

        # Obtener la carpeta del prompt actual
        current_prompt_folder = blocks_manager.current_prompt_folder
        if not current_prompt_folder:
            self.report({'ERROR'}, "No hay prompt cargado actualmente")
            return {'CANCELLED'}

        # Construir la ruta de la carpeta específica de la entidad
        entity_folder = os.path.join(current_prompt_folder, self.entity_name)

        if not os.path.exists(entity_folder):
            self.report({'ERROR'}, f"Carpeta de entidad no encontrada: {entity_folder}")
            return {'CANCELLED'}

        # Recargar la entidad específica
        success = self.refresh_entity(self.entity_name, entity_folder, blocks_manager)

        if success:
            self.report({'INFO'}, f"Entidad '{self.entity_name}' actualizada desde {os.path.basename(entity_folder)}")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, f"Error actualizando entidad '{self.entity_name}'")
            return {'CANCELLED'}

    def refresh_entity(self, entity_name: str, entity_folder: str, blocks_manager) -> bool:
        """Recarga una entidad específica preservando el estado de otras entidades"""
        try:
            print(f"🔄 ACTUALIZANDO ENTIDAD: {entity_name} desde {os.path.basename(entity_folder)}")

            # Obtener el controller de la entidad
            entity_data = blocks_manager.entities[entity_name]
            entity_controller = entity_data.get('controller')

            if not entity_controller:
                print(f"❌ Controller no encontrado para entidad {entity_name}")
                return False

            # PRESERVAR ESTADO DE CARGA (is_loaded)
            was_loaded = entity_data.get('is_loaded', False)
            preserved_parts = None
            if was_loaded and entity_controller.player_parts:
                # Guardar las partes existentes si estaban cargadas
                preserved_parts = entity_controller.player_parts.copy()

            # Limpiar COMPLETAMENTE slots existentes de esta entidad (sin afectar otras entidades)
            loaded_slots_before = len([b for b in entity_controller.blocks.values() if b['is_loaded']])
            print(f"📊 Slots cargados antes: {loaded_slots_before}")

            # LIMPIAR COMPLETAMENTE el diccionario de blocks para esta entidad
            entity_controller.blocks.clear()
            print(f"🧹 Diccionario de blocks limpiado completamente para {entity_name}")

            # Buscar archivos de animación en la carpeta de la entidad
            py_files = [f for f in os.listdir(entity_folder) if f.endswith('.py') and f.startswith('slot_')]
            print(f"🎬 Encontrados {len(py_files)} archivos de animación: {py_files}")

            # RECONSTRUIR COMPLETAMENTE el diccionario de blocks desde cero
            loaded_count = 0
            for py_file in py_files:
                filepath = os.path.join(entity_folder, py_file)

                # Extraer slot del nombre del archivo
                slot_match = self.extract_slot_from_filename(py_file)
                print(f"      🔍 Procesando {py_file} → Slot {slot_match}")

                if slot_match:
                    # CREAR NUEVA ENTRADA en el diccionario limpio
                    entity_controller.blocks[slot_match] = {
                        'name': '', 'file_path': '', 'frame_count': 0, 'is_loaded': False,
                        'order': slot_match, 'description': '', 'fps': 24, 'rating': 0, 'feedback': ''
                    }

                    success = entity_controller.load_animation_block(slot_match, filepath)
                    if success:
                        # SINCRONIZAR CON METADATA GLOBAL: Actualizar frame_count usando datos del metadata.json
                        if blocks_manager.prompt_metadata and 'scenes' in blocks_manager.prompt_metadata:
                            for scene in blocks_manager.prompt_metadata['scenes']:
                                # Buscar escenas asignadas a esta entidad
                                if scene.get('slot_assigned') == slot_match and scene.get('entity') == entity_name:
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

            print(f"📊 Diccionario reconstruido: {len(entity_controller.blocks)} slots totales")

            # RESTAURAR PARTES PRESERVADAS si la entidad estaba cargada
            if preserved_parts and was_loaded:
                entity_controller.player_parts = preserved_parts
                entity_controller.is_loaded = True
                print(f"    🔄 Partes restauradas para {entity_name}: {len([k for k,v in preserved_parts.items() if v is not None])} encontradas")

            # Actualizar indicadores visuales para esta entidad
            if entity_name in blocks_manager.active_entity_slot_indicators:
                del blocks_manager.active_entity_slot_indicators[entity_name]
            blocks_manager.initialize_entity_slot_indicators(entity_name)

            print(f"✅ ENTIDAD ACTUALIZADA: {loaded_count} animaciones cargadas para {entity_name}")
            print(f"📁 Fuente: {os.path.basename(entity_folder)}")

            return True

        except Exception as e:
            print(f"❌ Error actualizando entidad {entity_name}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def extract_slot_from_filename(self, filename: str) -> int:
        """Extrae el número de slot del nombre del archivo"""
        import re
        match = re.search(r'slot_(\d+)', filename, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

# ============================================================================
# OPERADOR: CREAR / RECREAR SHAPE KEYS DE OJOS PARA UN SLOT
# Replica exactamente _build_expr_shape_keys() del slot .py exportado:
#  1. Restaura la geometría base desde EYE_BASE_MESH_DATA (snapshot exacto).
#  2. Recalcula los shape keys con los parámetros de EYE_SEQUENCE_DATA[global].
# ============================================================================


def _eye_apply_curve_op(factor, curve_mode):
    if curve_mode == "QUADRATIC": return factor ** 2
    if curve_mode == "CUBIC":     return factor ** 3
    return factor


def _eye_detect_axes_op(mesh_obj):
    """Detecta ejes h/v/depth por rango de coordenadas."""
    verts = [v.co for v in mesh_obj.data.vertices]
    if not verts:
        return "x", "z", "y"
    xs = [v.x for v in verts]; ys = [v.y for v in verts]; zs = [v.z for v in verts]
    ranges = {"x": max(xs)-min(xs), "y": max(ys)-min(ys), "z": max(zs)-min(zs)}
    sorted_r = sorted(ranges.items(), key=lambda i: i[1])
    return sorted_r[2][0], sorted_r[1][0], sorted_r[0][0]


def _eye_compute_vertex_op(orig_co, h_axis, v_axis, bounds, expression, cfg, mirror_h=False):
    """
    Desplaza un vértice según la expresión.
    cfg es un dict (igual que en el .py del slot: usa cfg.get(...)).
    """
    cx = bounds["cx"]; cy = bounds["cy"]; cz = bounds["cz"]
    rx = bounds["rx"]; ry = bounds["ry"]; rz = bounds["rz"]

    h_val = getattr(orig_co, h_axis)
    v_val = getattr(orig_co, v_axis)

    center_v = {"x": cx, "y": cy, "z": cz}[v_axis]
    range_v  = {"x": rx, "y": ry, "z": rz}[v_axis]
    center_h = {"x": cx, "y": cy, "z": cz}[h_axis]
    range_h  = {"x": rx, "y": ry, "z": rz}[h_axis]

    v_mult = -1 if cfg.get("invert_vertical",   True)  else 1
    h_mult = -1 if cfg.get("invert_horizontal", False) else 1

    v_factor = (v_val - center_v) / (range_v / 2) if range_v > 0 else 0
    h_factor = (h_val - center_h) / (range_h / 2) if range_h > 0 else 0

    if mirror_h:
        h_factor = -h_factor

    zone = cfg.get("affect_zone", "UPPER")
    if zone == "UPPER":
        if v_factor <= 0: return orig_co.copy()
        v_factor_norm = v_factor
    elif zone == "LOWER":
        if v_factor >= 0: return orig_co.copy()
        v_factor_norm = -v_factor
    else:
        v_factor_norm = abs(v_factor)

    offset = 0.0
    cm = cfg.get("curve_mode", "QUADRATIC")
    expr = expression.lower()

    if expr in ("feliz", "triste"):
        curve  = _eye_apply_curve_op(abs(h_factor), cm)
        intens = cfg.get("intensity_feliz", 0.18) if expr == "feliz" else cfg.get("intensity_triste", 0.18)
        sign   = 1 if expr == "feliz" else -1
        offset = sign * intens * curve * v_factor_norm * v_mult

    elif expr in ("sospecha", "enojado"):
        min_h  = center_h - range_h / 2
        h_norm = (h_val - min_h) / range_h if range_h > 0 else 0.5
        if mirror_h:
            h_norm = 1.0 - h_norm
        if expr == "sospecha":
            intens = cfg.get("intensity_sospecha", 0.18)
            offset = (intens * h_norm - intens / 2) * v_factor_norm * v_mult * h_mult
        else:
            intens = cfg.get("intensity_enojado", 0.18)
            offset = (-intens * h_norm + intens / 2) * v_factor_norm * v_mult * h_mult

    elif expr == "cerrado":
        offset = -(v_val - center_v) * 0.85
    elif expr == "cansado":
        offset = -(v_val - center_v) * 0.4 * v_factor_norm
    elif expr == "sorpresa":
        offset = (v_val - center_v) * 0.15 * v_factor_norm

    new_co = orig_co.copy()
    setattr(new_co, v_axis, v_val + offset)
    return new_co


def _build_eye_shape_keys_from_slot(eye_obj, cfg, base_verts, is_right):
    """
    Reconstruye los shape keys de un ojo replicando exactamente
    _build_expr_shape_keys() del .py interno del slot:
      1. Restaura geometría base desde base_verts (EYE_BASE_MESH_DATA snapshot).
      2. Recalcula todos los shape keys con los parámetros de cfg (dict global).
    """
    if not eye_obj or eye_obj.type != "MESH":
        return False, f"'{getattr(eye_obj,'name','?')}' no es malla"

    # ── 1. Restaurar geometría base exacta ───────────────────────────────
    if base_verts:
        if len(base_verts) != len(eye_obj.data.vertices):
            # Diferente nº de vértices: reconstruir desde cero
            if eye_obj.data.shape_keys:
                eye_obj.shape_key_clear()
            bpy.context.view_layer.objects.active = eye_obj
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.mesh.dissolve_limited()
            cuts = cfg.get("subdivide_cuts", 3)
            for _ in range(cuts):
                bpy.ops.mesh.subdivide(number_cuts=1)
            bpy.ops.object.mode_set(mode="OBJECT")

        if len(base_verts) == len(eye_obj.data.vertices):
            # Restaurar coordenadas exactas del snapshot exportado
            if eye_obj.data.shape_keys:
                eye_obj.shape_key_clear()
            for i, co in enumerate(base_verts):
                eye_obj.data.vertices[i].co.x = co[0]
                eye_obj.data.vertices[i].co.y = co[1]
                eye_obj.data.vertices[i].co.z = co[2]
            eye_obj.data.update()
        else:
            return False, (
                f"No se pudo igualar el conteo de vértices "
                f"(base={len(base_verts)} scene={len(eye_obj.data.vertices)})"
            )
    else:
        # Sin snapshot: subdividir solo si la malla es primitiva (≤12 verts)
        cuts = cfg.get("subdivide_cuts", 3)
        if cuts > 0 and len(eye_obj.data.vertices) <= 12:
            if eye_obj.data.shape_keys:
                eye_obj.shape_key_clear()
            bpy.context.view_layer.objects.active = eye_obj
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            for _ in range(cuts):
                bpy.ops.mesh.subdivide(number_cuts=1)
            bpy.ops.object.mode_set(mode="OBJECT")
        elif eye_obj.data.shape_keys:
            eye_obj.shape_key_clear()

    # ── 2. Construir shape keys ──────────────────────────────────────────
    eye_obj.shape_key_add(name="Basis", from_mix=False)
    mesh = eye_obj.data
    orig = [v.co.copy() for v in mesh.vertices]

    xs = [v.co.x for v in mesh.vertices]
    ys = [v.co.y for v in mesh.vertices]
    zs = [v.co.z for v in mesh.vertices]
    bounds = {
        "cx": (max(xs)+min(xs))/2, "cy": (max(ys)+min(ys))/2, "cz": (max(zs)+min(zs))/2,
        "rx": max(xs)-min(xs),     "ry": max(ys)-min(ys),     "rz": max(zs)-min(zs),
    }

    # Determinar ejes — prioridad: ejes serializados en el .py > detección automática
    side = "R" if is_right else "L"
    h_key = f"eye_{side}_h_axis"
    v_key = f"eye_{side}_v_axis"
    if cfg.get(h_key) and cfg.get(v_key):
        h_axis = cfg[h_key]
        v_axis = cfg[v_key]
    else:
        h_axis, v_axis, _ = _eye_detect_axes_op(eye_obj)

    if cfg.get("swap_axes", False):
        h_axis, v_axis = v_axis, h_axis

    print(f"[rebuild_eye] {eye_obj.name}: h={h_axis} v={v_axis} "
          f"is_right={is_right} verts={len(orig)} "
          f"zone={cfg.get('affect_zone','?')} invV={cfg.get('invert_vertical','?')}")

    for expr in ("feliz", "triste", "enojado", "sospecha", "cerrado", "cansado", "sorpresa"):
        sk = eye_obj.shape_key_add(name=expr.capitalize(), from_mix=False)
        sk.value = 0.0
        sk.slider_min = -2.0
        sk.slider_max = 2.0
        for i, o in enumerate(orig):
            sk.data[i].co = _eye_compute_vertex_op(
                o, h_axis, v_axis, bounds, expr, cfg, mirror_h=is_right
            )

    # Shape key Closed — cortina hacia el mínimo del eje vertical
    sk_cl = eye_obj.shape_key_add(name="Closed", from_mix=False)
    sk_cl.value = 0.0
    min_v = min(getattr(v.co, v_axis) for v in mesh.vertices)
    for i, v in enumerate(mesh.vertices):
        nc = v.co.copy()
        setattr(nc, v_axis, min_v)
        sk_cl.data[i].co = nc

    sk_count = len(mesh.shape_keys.key_blocks) if mesh.shape_keys else 0
    return True, (
        f"{eye_obj.name}: h={h_axis} v={v_axis} verts={len(orig)} "
        f"zone={cfg.get('affect_zone','?')} invV={cfg.get('invert_vertical','?')} "
        f"swap={cfg.get('swap_axes','?')} keys={sk_count}"
    )


def _load_slot_eye_data(filepath):
    """
    Importa el .py del slot y extrae:
      - cfg      : dict con EYE_SEQUENCE_DATA['global']
      - base_L   : lista de verts de EYE_BASE_MESH_DATA['eye_L'] (o None)
      - base_R   : lista de verts de EYE_BASE_MESH_DATA['eye_R'] (o None)
    Devuelve (cfg, base_L, base_R, msg) o (None, None, None, msg_error).
    """
    import importlib.util

    try:
        spec = importlib.util.spec_from_file_location("_slot_eye_tmp", filepath)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        return None, None, None, f"Error importando .py: {e}"

    eye_seq  = getattr(mod, "EYE_SEQUENCE_DATA",  None)
    eye_base = getattr(mod, "EYE_BASE_MESH_DATA", None)

    if not eye_seq or not isinstance(eye_seq, dict):
        return None, None, None, "El .py no contiene EYE_SEQUENCE_DATA"

    global_cfg = eye_seq.get("global", {})
    if not global_cfg.get("enabled", False):
        return None, None, None, "EYE_SEQUENCE_DATA.global.enabled = False"

    base_L = base_R = None
    if eye_base and isinstance(eye_base, dict):
        base_L = eye_base.get("eye_L")
        base_R = eye_base.get("eye_R")

    return global_cfg, base_L, base_R, "OK"


class ANIMBLOCKS_OT_RebuildEyeShapeKeysForSlot(Operator):
    """
    Crea / Recrea los Shape Keys de ojos para un slot concreto.

    Replica la función _build_expr_shape_keys() embebida en el .py exportado:
      1. Restaura la geometría EXACTA de los ojos desde EYE_BASE_MESH_DATA
         (snapshot capturado en el momento de exportar el slot).
      2. Recalcula todos los shape keys usando los parámetros guardados en
         EYE_SEQUENCE_DATA['global'] (affect_zone, invert_vertical, intensidades…).

    Ejecutar este botón ANTES de Concatenar garantiza que los cambios del
    panel "Setup de Shape Keys de ojos" se apliquen correctamente.
    """
    bl_idname = "simple_animblocks.rebuild_eye_shape_keys_slot"
    bl_label  = "Crear / Recrear Shape Keys"
    bl_description = (
        "Restaura la geometría exacta de los ojos y reconstruye sus Shape Keys "
        "con la configuración guardada en este slot. "
        "EJECUTAR ANTES DE CONCATENAR para que los cambios de 'Setup de Shape Keys' tengan efecto."
    )
    bl_options = {'REGISTER', 'UNDO'}

    entity_name: bpy.props.StringProperty(name="Entidad", default="")
    slot:        bpy.props.IntProperty(name="Slot", default=1, min=1)

    def execute(self, context):
        # ── Obtener el block del slot ─────────────────────────────────────
        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            self.report({'ERROR'}, "No se pudo acceder a core_system.blocks_manager")
            return {'CANCELLED'}

        if self.entity_name not in blocks_manager.entities:
            self.report({'ERROR'}, f"Entidad '{self.entity_name}' no encontrada")
            return {'CANCELLED'}

        entity_data      = blocks_manager.entities[self.entity_name]
        entity_controller = entity_data.get('controller')
        if not entity_controller or self.slot not in entity_controller.blocks:
            self.report({'ERROR'}, f"Slot {self.slot} no válido para '{self.entity_name}'")
            return {'CANCELLED'}

        block = entity_controller.blocks[self.slot]
        if not block.get('is_loaded'):
            self.report({'ERROR'}, f"Slot {self.slot} está vacío")
            return {'CANCELLED'}

        filepath = block.get('file_path', '')
        if not filepath or not os.path.isfile(filepath):
            self.report({'ERROR'},
                f"Archivo .py no encontrado para Slot {self.slot} — ruta: '{filepath}'")
            return {'CANCELLED'}

        # ── Verificar objetos de ojo ──────────────────────────────────────
        eye_L = bpy.data.objects.get("ojo_izquierdo_alfred")
        eye_R = bpy.data.objects.get("ojo_derecho_alfred")
        if not eye_L or not eye_R:
            self.report({'ERROR'},
                "No se encontraron 'ojo_izquierdo_alfred' y/o 'ojo_derecho_alfred' en la escena")
            return {'CANCELLED'}

        # ── Cargar datos desde el .py del slot ────────────────────────────
        cfg, base_L, base_R, msg = _load_slot_eye_data(filepath)
        if cfg is None:
            self.report({'WARNING'}, f"Slot {self.slot}: {msg}")
            return {'CANCELLED'}

        print(f"[rebuild_eye] Slot {self.slot} — cfg cargado: "
              f"zone={cfg.get('affect_zone')} invV={cfg.get('invert_vertical')} "
              f"swap={cfg.get('swap_axes')} base_L={'sí' if base_L else 'no'} "
              f"base_R={'sí' if base_R else 'no'}")

        # ── Reconstruir shape keys — mismo flujo que _build_expr_shape_keys ─
        errors = []

        ok_L, info_L = _build_eye_shape_keys_from_slot(eye_L, cfg, base_L, is_right=False)
        if not ok_L:
            errors.append(f"ojo_izquierdo: {info_L}")
        else:
            print(f"[rebuild_eye] ✅ L — {info_L}")

        ok_R, info_R = _build_eye_shape_keys_from_slot(eye_R, cfg, base_R, is_right=True)
        if not ok_R:
            errors.append(f"ojo_derecho: {info_R}")
        else:
            print(f"[rebuild_eye] ✅ R — {info_R}")

        if errors:
            self.report({'ERROR'}, " | ".join(errors))
            return {'CANCELLED'}

        slot_name = block.get('name', f'Slot {self.slot}')
        sk_count  = len(eye_L.data.shape_keys.key_blocks) if eye_L.data.shape_keys else 0
        self.report({'INFO'},
            f"✅ Shape Keys OK — Slot {self.slot} ({slot_name}) | "
            f"{sk_count} keys | zone={cfg.get('affect_zone')} "
            f"invV={cfg.get('invert_vertical')} swap={cfg.get('swap_axes')}")
        return {'FINISHED'}



# ============================================================================
# OPERADOR: CONCATENAR_2 (Ojos) — Recrear Shape Keys + Concatenar slot
# Ejecuta primero "Crear / Recrear Shape Keys" para aplicar la configuración
# del panel "Setup de Shape Keys de ojos" y luego concatena el slot completo
# (cuerpo + ojos) para que los cambios queden grabados en la animación.
# ============================================================================

class ANIMBLOCKS_OT_ConcatenateEyes(Operator):
    """
    CONCATENAR_2 (Ojos):
    1. Recrea los Shape Keys de los ojos con la configuración guardada en el
       slot (affect_zone, invert_vertical, intensidades, etc.).
    2. Concatena el slot completo para que esos cambios queden aplicados
       en la animación reproducida.
    """
    bl_idname  = "simple_animblocks.concatenate_eyes"
    bl_label   = "CONCATENAR_2 (Ojos)"
    bl_description = (
        "Recrea los Shape Keys de ojos con el Setup configurado y luego "
        "concatena SOLO este slot para que los cambios queden aplicados. "
        "Úsalo cuando la animación no tome en cuenta los cambios del "
        "panel 'Setup de Shape Keys de ojos'."
    )
    bl_options = {'REGISTER', 'UNDO'}

    entity_name: bpy.props.StringProperty(name="Entidad", default="")
    slot: bpy.props.IntProperty(name="Slot", default=1, min=1)

    def execute(self, context):
        # ── Paso 1: Recrear Shape Keys del slot ───────────────────────────
        result = bpy.ops.simple_animblocks.rebuild_eye_shape_keys_slot(
            entity_name=self.entity_name, slot=self.slot
        )
        if 'CANCELLED' in result:
            self.report({'ERROR'},
                f"CONCATENAR_2: falló la reconstrucción de Shape Keys para "
                f"Slot {self.slot} de '{self.entity_name}'. "
                f"Verifica que los objetos 'ojo_izquierdo_alfred' y "
                f"'ojo_derecho_alfred' estén en la escena y el slot esté cargado."
            )
            return {'CANCELLED'}

        print(f"[CONCATENAR_2] ✅ Shape Keys reconstruidos — Slot {self.slot} / '{self.entity_name}'")

        # ── Paso 2: Concatenar SOLO este slot en su posicion de timeline ──
        try:
            import core_system
            blocks_manager = core_system.blocks_manager
        except (ImportError, AttributeError):
            self.report({'ERROR'}, "No se pudo acceder a core_system.blocks_manager")
            return {'CANCELLED'}

        if self.entity_name not in blocks_manager.entities:
            self.report({'ERROR'}, f"Entidad '{self.entity_name}' no encontrada")
            return {'CANCELLED'}

        entity_data       = blocks_manager.entities[self.entity_name]
        entity_controller = entity_data.get('controller')
        if not entity_controller:
            self.report({'ERROR'}, f"Controller no encontrado para '{self.entity_name}'")
            return {'CANCELLED'}

        if self.slot not in entity_controller.blocks:
            self.report({'ERROR'}, f"Slot {self.slot} no existe en '{self.entity_name}'")
            return {'CANCELLED'}

        target_block = entity_controller.blocks[self.slot]
        if not target_block.get('is_loaded'):
            self.report({'ERROR'}, f"Slot {self.slot} no está cargado")
            return {'CANCELLED'}

        # Calcular el frame de inicio de este slot dentro de la timeline
        # sumando los frames de todos los slots anteriores (en orden)
        sequence = entity_controller.get_loaded_blocks_sequence()
        current_frame = 1
        block_start = None
        block_end   = None
        for block in sequence:
            if block['slot'] == self.slot:
                block_start = current_frame
                block_end   = current_frame + block['frame_count'] - 1
                break
            current_frame += block['frame_count']

        if block_start is None:
            self.report({'ERROR'},
                f"Slot {self.slot} no está en la secuencia activa de '{self.entity_name}'"
            )
            return {'CANCELLED'}

        # Cargar animation_engine
        animation_engine_path = os.path.join(os.path.dirname(__file__), "animation_engine.py")
        spec = importlib.util.spec_from_file_location("animation_engine", animation_engine_path)
        if not spec or not spec.loader:
            self.report({'ERROR'}, "No se pudo cargar animation_engine.py")
            return {'CANCELLED'}

        animation_engine_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(animation_engine_module)
        execute_animation_block = animation_engine_module.execute_animation_block

        entity_player_parts = entity_controller.player_parts
        print(
            f"[CONCATENAR_2] Ejecutando solo Slot {self.slot} "
            f"frames {block_start}-{block_end} de '{self.entity_name}'"
        )

        success = execute_animation_block(
            target_block, block_start, block_end, entity_player_parts
        )

        if not success:
            self.report({'ERROR'},
                f"CONCATENAR_2: la concatenación del Slot {self.slot} falló."
            )
            return {'CANCELLED'}

        self.report({'INFO'},
            f"✅ CONCATENAR_2 — Slot {self.slot} / '{self.entity_name}': "
            f"Shape Keys + frames {block_start}-{block_end} aplicados."
        )
        print(
            f"[CONCATENAR_2] ✅ Slot {self.slot} concatenado "
            f"(frames {block_start}-{block_end}) — sin tocar otros slots."
        )
        return {'FINISHED'}


# ============================================================================
# REGISTRO DEL MÓDULO
# ============================================================================

def register():
    """Registra todos los operadores"""
    try:
        bpy.utils.register_class(ANIMBLOCKS_OT_LoadPromptFolder)
        bpy.utils.register_class(ANIMBLOCKS_OT_ApplyScenario)
        bpy.utils.register_class(ANIMBLOCKS_OT_ExtractData)
        bpy.utils.register_class(ANIMBLOCKS_OT_StopPlayback)
        bpy.utils.register_class(ANIMBLOCKS_OT_ConcatenateEntity)
        bpy.utils.register_class(ANIMBLOCKS_OT_PlayMultiEntity)
        bpy.utils.register_class(ANIMBLOCKS_OT_DiagnoseJerry)
        bpy.utils.register_class(ANIMBLOCKS_OT_ToggleNarrativeMode)
        bpy.utils.register_class(ANIMBLOCKS_OT_CaptureBaseOrientations)
        bpy.utils.register_class(ANIMBLOCKS_OT_ExportSequence)
        # REGISTRAR OPERADORES PRINCIPALES
        bpy.utils.register_class(ANIMBLOCKS_OT_Update)
        bpy.utils.register_class(ANIMBLOCKS_OT_ResetAll)
        bpy.utils.register_class(ANIMBLOCKS_OT_RefreshEntity)

        # REGISTRAR OPERADORES DE EVALUACIÓN
        bpy.utils.register_class(ANIMBLOCKS_OT_ClearEntityStructure)
        bpy.utils.register_class(ANIMBLOCKS_OT_SetRating)
        bpy.utils.register_class(ANIMBLOCKS_OT_SetFeedback)
        bpy.utils.register_class(ANIMBLOCKS_OT_ExportSlotData)
        bpy.utils.register_class(ANIMBLOCKS_OT_ToggleSlotSelection)
        bpy.utils.register_class(ANIMBLOCKS_OT_ClearAllSelections)
        bpy.utils.register_class(ANIMBLOCKS_OT_RebuildEyeShapeKeysForSlot)
        bpy.utils.register_class(ANIMBLOCKS_OT_ConcatenateEyes)
        print("✅ Operadores registrados correctamente")
    except Exception as e:
        print(f"❌ Error registrando operadores: {e}")

def unregister():
    """Desregistra todos los operadores"""
    try:
        # DESREGISTRAR OPERADORES PRINCIPALES
        bpy.utils.unregister_class(ANIMBLOCKS_OT_ResetAll)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_Update)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_RefreshEntity)

        # DESREGISTRAR OPERADORES DE EVALUACIÓN PRIMERO
        bpy.utils.unregister_class(ANIMBLOCKS_OT_ExportSlotData)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_ToggleSlotSelection)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_ClearAllSelections)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_RebuildEyeShapeKeysForSlot)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_ConcatenateEyes)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_SetFeedback)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_SetRating)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_ClearEntityStructure)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_ExportSequence)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_CaptureBaseOrientations)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_ToggleNarrativeMode)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_DiagnoseJerry)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_PlayMultiEntity)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_ConcatenateEntity)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_StopPlayback)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_ApplyScenario)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_ExtractData)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_LoadPromptFolder)
        print("✅ Operadores desregistrados correctamente")
    except Exception as e:
        print(f"❌ Error desregistrando operadores: {e}")