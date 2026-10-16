#!/usr/bin/env python3
"""
ui_panels.py - Paneles de interfaz de usuario del sistema multi-entidad
Contiene ANIMBLOCKS_PT_MainPanel y funciones relacionadas con UI
"""

import bpy
import os
from bpy.types import Panel, Operator

# ============================================================================
# OPERADORES DE UI
# ============================================================================

def _try_import_eye_props():
    """Importa alfred_eye_props de forma segura."""
    try:
        import alfred_eye_props
        return alfred_eye_props
    except ImportError:
        return None


def get_light_options(self, context):
    """Genera opciones dinámicas para el menú desplegable de luces"""
    import os

    # Obtener la ruta de la carpeta de luces
    addon_dir = os.path.dirname(os.path.dirname(__file__))
    lights_dir = os.path.join(addon_dir, "light_placement_tool", "luces")

    options = []
    if os.path.exists(lights_dir):
        json_files = [f for f in os.listdir(lights_dir) if f.endswith('.json')]
        for light_file in sorted(json_files):
            light_name = light_file.replace('.json', '')
            display_name = light_name.replace('_', ' ').title()
            options.append((light_name, display_name, f"Seleccionar {display_name}"))

    return options if options else [("none", "No hay luces disponibles", "")]


class ANIMBLOCKS_OT_ApplySingleLight(Operator):
    """Aplica (crea) una luz específica inmediatamente"""
    bl_idname = "simple_animblocks.apply_single_light"
    bl_label = "Aplicar Luz"
    bl_options = {'REGISTER', 'UNDO'}

    light_name: bpy.props.StringProperty(name="Light Name", default="")

    def execute(self, context):
        import os
        import json
        import bpy

        # Obtener la ruta del archivo JSON específico
        addon_dir = os.path.dirname(os.path.dirname(__file__))
        lights_dir = os.path.join(addon_dir, "light_placement_tool", "luces")
        json_path = os.path.join(lights_dir, f"{self.light_name}.json")

        if not os.path.exists(json_path):
            self.report({'ERROR'}, f"Archivo no encontrado: {self.light_name}.json")
            return {'CANCELLED'}

        # Crear colección para luces si no existe
        lights_collection = None
        for coll in bpy.data.collections:
            if coll.name == "Luces_Generadas":
                lights_collection = coll
                break

        if not lights_collection:
            lights_collection = bpy.data.collections.new("Luces_Generadas")
            bpy.context.scene.collection.children.link(lights_collection)

        try:
            # Leer coordenadas del archivo JSON
            with open(json_path, 'r') as f:
                coordinates = json.load(f)

            if not coordinates:
                self.report({'WARNING'}, f"No hay coordenadas en {self.light_name}.json")
                return {'CANCELLED'}

            # Obtener propiedades de luz
            light_props = self.get_light_properties(self.light_name)

            # Crear luces
            created_count = 0
            for i, coord in enumerate(coordinates):
                bpy.ops.object.light_add(type='POINT', location=coord)
                light_object = bpy.context.active_object

                light_object.name = f"{self.light_name}_{i+1}"
                light_data = light_object.data
                light_data.energy = light_props['energy']
                light_data.shadow_soft_size = light_props['shadow_size']
                light_data.color = light_props['color']

                # Mover a colección
                for coll in light_object.users_collection:
                    coll.objects.unlink(light_object)
                lights_collection.objects.link(light_object)

                created_count += 1

            light_display = self.light_name.replace('_', ' ').title()
            self.report({'INFO'}, f"💡 Creadas {created_count} luces: {light_display}")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error creando luces: {str(e)}")
            return {'CANCELLED'}

    def get_light_properties(self, light_name):
        """Retorna propiedades de luz según el tipo"""
        default_props = {
            'energy': 500.0,
            'shadow_size': 3.0,
            'color': (1, 0.8, 0.5)
        }

        light_configs = {
            'torch': {'energy': 800.0, 'shadow_size': 2.0, 'color': (1, 0.6, 0.2)},
            'lantern': {'energy': 1000.0, 'shadow_size': 1.5, 'color': (1, 0.8, 0.6)},
            'campfire_log_lit': {'energy': 1200.0, 'shadow_size': 4.0, 'color': (1, 0.4, 0.1)},
            'lava_flow': {'energy': 600.0, 'shadow_size': 3.5, 'color': (1, 0.3, 0.0)},
            'lava_still': {'energy': 500.0, 'shadow_size': 3.0, 'color': (1, 0.2, 0.0)},
            'glow_lichen': {'energy': 300.0, 'shadow_size': 1.0, 'color': (0.8, 1, 0.6)},
            'sea_pickle': {'energy': 400.0, 'shadow_size': 1.5, 'color': (0.6, 1, 0.8)},
            'furnace_front': {'energy': 700.0, 'shadow_size': 2.5, 'color': (1, 0.5, 0.3)},
            'spore_blossom': {'energy': 350.0, 'shadow_size': 2.0, 'color': (0.7, 0.9, 1)},
            'cave_vines_lit': {'energy': 250.0, 'shadow_size': 1.0, 'color': (0.5, 1, 0.4)},
            'amethyst_cluster': {'energy': 450.0, 'shadow_size': 2.0, 'color': (0.8, 0.6, 1)},
            'magma': {'energy': 550.0, 'shadow_size': 3.0, 'color': (1, 0.3, 0.1)}
        }

        return light_configs.get(light_name, default_props)

class ANIMBLOCKS_OT_RefreshLightSelection(Operator):
    """Refresca la lista de luces disponibles"""
    bl_idname = "simple_animblocks.refresh_light_selection"
    bl_label = "Refresh Light List"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Forzar actualización de la UI
        if hasattr(context.scene, 'light_selected_items'):
            # Limpiar selección actual para forzar refresh
            context.scene.light_selected_items = ""
        return {'FINISHED'}

class ANIMBLOCKS_OT_ResetLights(Operator):
    """Elimina todas las luces creadas en la colección 'Luces_Generadas'"""
    bl_idname = "simple_animblocks.reset_lights"
    bl_label = "Reset Lights"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import bpy

        # Buscar la colección de luces generadas
        lights_collection = None
        for coll in bpy.data.collections:
            if coll.name == "Luces_Generadas":
                lights_collection = coll
                break

        if not lights_collection:
            self.report({'WARNING'}, "No se encontró la colección 'Luces_Generadas'")
            return {'FINISHED'}

        # Contar luces antes de eliminar
        initial_count = len(lights_collection.objects)

        if initial_count == 0:
            self.report({'INFO'}, "No hay luces para eliminar")
            return {'FINISHED'}

        # Eliminar todas las luces de la colección
        lights_to_remove = []
        for obj in lights_collection.objects:
            if obj.type == 'LIGHT':
                lights_to_remove.append(obj)

        # Eliminar los objetos
        for light_obj in lights_to_remove:
            # Remover de la colección primero
            lights_collection.objects.unlink(light_obj)
            # Luego eliminar el objeto completamente
            bpy.data.objects.remove(light_obj)

        # Verificar si la colección quedó vacía y eliminarla si es necesario
        if len(lights_collection.objects) == 0:
            # Remover la colección de la escena
            for scene in bpy.data.scenes:
                if lights_collection.name in scene.collection.children:
                    scene.collection.children.unlink(lights_collection)
            # Eliminar la colección completamente
            bpy.data.collections.remove(lights_collection)

        self.report({'INFO'}, f"🗑️ Eliminadas {len(lights_to_remove)} luces. Colección limpiada.")
        return {'FINISHED'}


class ANIMBLOCKS_OT_LoadStructure(Operator):
    """Carga una estructura .blend para una entidad específica"""
    bl_idname = "simple_animblocks.load_entity_structure"
    bl_label = "Cargar Estructura"
    bl_options = {'REGISTER', 'UNDO'}

    entity_name: bpy.props.StringProperty(name="Entidad", default="")
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        # CORRECCIÓN: Usar importaciones absolutas
        import core_system
        blocks_manager = core_system.blocks_manager

        if not self.entity_name:
            self.report({'ERROR'}, "Nombre de entidad no especificado")
            return {'CANCELLED'}

        if not self.filepath:
            self.report({'ERROR'}, "Archivo no especificado")
            return {'CANCELLED'}

        # Cargar la estructura
        success = self.load_entity_structure(self.entity_name, self.filepath)
        if success:
            self.report({'INFO'}, f"Estructura '{os.path.basename(self.filepath)}' cargada para '{self.entity_name}'")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, f"Error cargando estructura para '{self.entity_name}'")
            return {'CANCELLED'}

    def load_entity_structure(self, entity_name: str, filepath: str) -> bool:
        """Carga una estructura .blend para una entidad específica"""
        try:
            # CORRECCIÓN: Usar importaciones absolutas
            import core_system
            blocks_manager = core_system.blocks_manager

            print(f"🏗️ CARGANDO ESTRUCTURA para {entity_name}: {os.path.basename(filepath)}")

            # Verificar que la entidad existe
            if entity_name not in blocks_manager.entities:
                print(f"❌ Entidad {entity_name} no encontrada en configuración")
                return False

            entity_data = blocks_manager.entities[entity_name]

            # Cargar el archivo .blend
            with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
                # Importar objetos
                data_to.objects = [obj for obj in data_from.objects]

                # Importar colecciones si existen
                if hasattr(data_from, 'collections'):
                    data_to.collections = [coll for coll in data_from.collections]

            # Agregar objetos a la escena
            imported_object_names = []
            for obj in data_to.objects:
                if obj is not None:
                    try:
                        bpy.context.scene.collection.objects.link(obj)
                        imported_object_names.append(obj.name)
                        print(f"   ✅ Importado: {obj.name}")
                    except RuntimeError as e:
                        # Objeto ya existe en la escena
                        print(f"   ⚠️ Ya existe: {obj.name} ({e})")
                        continue

            # Agregar colecciones si existen
            for coll in data_to.collections:
                if coll is not None:
                    try:
                        bpy.context.scene.collection.children.link(coll)
                        print(f"   ✅ Colección importada: {coll.name}")
                    except RuntimeError:
                        print(f"   ⚠️ Colección ya existe: {coll.name}")

            # Marcar la entidad como cargada
            entity_data['is_loaded'] = True
            entity_data['blend_file'] = self.filepath
            entity_data['scene_objects'] = imported_object_names  # Guardar nombres de objetos

            # Buscar partes del cuerpo de esta entidad
            entity_controller = entity_data.get('controller')
            if entity_controller:
                entity_controller.find_entity_parts()

            # Configurar escena (mantener configuración actual)
            scene = bpy.context.scene
            # NO resetear frame_start/frame_current para no interferir con otras entidades

            filename = os.path.basename(filepath)
            imported_count = len(imported_object_names)
            self.report({'INFO'}, f"Estructura '{filename}' importada para '{entity_name}' ({imported_count} objetos)")
            print(f"✅ ESTRUCTURA IMPORTADA: {filename} para entidad '{entity_name}'")
            print(f"📦 Objetos importados: {imported_count}")
            print(f"🎭 Partes encontradas: {len(entity_controller.player_parts) if entity_controller else 0}")

            # Mostrar resumen de traducciones aplicadas
            if hasattr(self, 'translation_used') and self.translation_used and self.translation_used != entity_name:
                print(f"🔄 Sistema de traducción: '{entity_name}' → '{self.translation_used}' → {filename}")

            return True

        except Exception as e:
            self.report({'ERROR'}, f"Error cargando estructura: {str(e)}")
            print(f"❌ Error cargando estructura para {entity_name}: {e}")
            return False

    def invoke(self, context, event):
        """Modificar invoke para sugerir archivo basado en traducción"""
        try:
            # CORRECCIÓN: Usar importaciones absolutas
            import core_system
            blocks_manager = core_system.blocks_manager
            from translation_system import translate_entity_name, find_blend_file_with_translation

            if self.entity_name:
                if self.entity_name in blocks_manager.entities:
                    entity_data = blocks_manager.entities[self.entity_name]
                    translation_used = entity_data.get('translation_used', '')

                    # Intentar encontrar archivo automáticamente para pre-seleccionarlo
                    if translation_used:
                        suggested_file = find_blend_file_with_translation(translation_used)
                        if suggested_file:
                            self.filepath = suggested_file
                            print(f"💡 Archivo sugerido encontrado: {os.path.basename(suggested_file)}")

            # Asegurar que siempre retorne el set correcto
            result = context.window_manager.fileselect_add(self)
            if result is None:
                return {'RUNNING_MODAL'}
            return result

        except Exception as e:
            print(f"❌ Error en invoke de LoadEntityStructure: {e}")
            return {'CANCELLED'}

class ANIMBLOCKS_OT_LoadAnimationBlock(Operator):
    """Carga un bloque de animación en un slot específico"""
    bl_idname = "simple_animblocks.load_animation_block"
    bl_label = "Cargar Bloque de Animación"
    bl_options = {'REGISTER', 'UNDO'}

    slot: bpy.props.IntProperty(name="Slot", default=1)
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        # CORRECCIÓN: Usar importaciones absolutas
        import core_system
        blocks_manager = core_system.blocks_manager

        if not self.filepath:
            self.report({'ERROR'}, "Archivo no seleccionado")
            return {'CANCELLED'}

        # Cargar el bloque
        success = blocks_manager.load_animation_block(self.slot, self.filepath)
        if success:
            filename = os.path.basename(self.filepath)
            self.report({'INFO'}, f"Bloque '{filename}' cargado en slot {self.slot}")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, f"Error cargando bloque en slot {self.slot}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# ============================================================================
# PANEL PRINCIPAL
# ============================================================================

class ANIMBLOCKS_PT_MainPanel(Panel):
    bl_label = "Multi-Entity Animation Blocks Manager"
    bl_idname = "ANIMBLOCKS_PT_multi_entity_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Animation Blocks'

    def get_blocks_manager_safe(self):
        """Obtiene el manager de bloques de forma segura con fallbacks"""
        try:
            # Intentar importar desde core_system
            import core_system
            if hasattr(core_system, 'blocks_manager'):
                return core_system.blocks_manager
        except (ImportError, AttributeError):
            pass

        try:
            # Intentar importar directamente
            from core_system import SimpleAnimationBlocksManager
            return SimpleAnimationBlocksManager()
        except ImportError:
            pass

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
                self.selected_slots = {}  # Para slots seleccionados en secuencia

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

        return DummyManager()

    def draw(self, context):
        layout = self.layout

        # Obtener manager con sistema de importación corregido
        blocks_manager = self.get_blocks_manager_safe()

        # CONTROLES GENERALES - Parte superior
        controls_box = layout.box()
        controls_box.label(text="🎮 CONTROLES GENERALES", icon='SETTINGS')

        # Fila de botones principales
        main_controls_row = controls_box.row(align=True)
        main_controls_row.scale_y = 1.2

        # Botón Reset - limpia todo desde cargar carpeta
        reset_op = main_controls_row.operator("simple_animblocks.reset_all", text="🔄 Reset", icon='TRASH')
        restart_op = main_controls_row.operator("simple_animblocks.stop_playback", text="⏮️ Reiniciar", icon='LOOP_BACK')


        # CONTROLES DE ANIMACIÓN RELATIVA - DESACTIVADOS TEMPORALMENTE
        # Esta sección se muestra solo cuando es necesario activar el sistema de animación relativa
        # if blocks_manager.entities:
        #     relative_box = layout.box()
        #     relative_box.label(text="🔄 ANIMACIÓN RELATIVA", icon='ORIENTATION_VIEW')
        #
        #     # Estado de orientaciones
        #     orientation_row = relative_box.row()
        #     if context.scene.base_orientations_captured:
        #         orientation_row.label(text="📐 Orientaciones: ✅ Capturadas", icon='CHECKMARK')
        #     else:
        #         orientation_row.label(text="📐 Orientaciones: ❌ Pendientes", icon='ERROR')
        #
        #     # Controles de orientación
        #     orientation_controls = relative_box.row(align=True)
        #     orientation_controls.scale_y = 1.1
        #
        #     # Botón para capturar orientaciones
        #     capture_op = orientation_controls.operator("simple_animblocks.capture_base_orientations",
        #                                              text="📐 Capturar Base", icon='ORIENTATION_GIMBAL')
        #     capture_op = orientation_controls.operator("simple_animblocks.toggle_narrative_mode",
        #                                              text="🎭 Narrativa" if context.scene.narrative_mode_enabled else "🎯 Coherente",
        #                                              icon='SEQUENCE')
        #
        #     # Información del modo actual
        #     mode_info = relative_box.box()
        #     if context.scene.narrative_mode_enabled:
        #         mode_info.label(text="🎭 MODO NARRATIVA: Expresividad sobre coherencia", icon='SEQUENCE')
        #         mode_info.label(text="• Movimientos más amplios y expresivos", icon='INFO')
        #     else:
        #         mode_info.label(text="🎯 MODO COHERENTE: Coherencia visual prioritaria", icon='ORIENTATION_VIEW')
        #         mode_info.label(text="• Movimientos precisos y consistentes", icon='INFO')

        # Carga masiva desde carpeta Prompt
        box = layout.box()

        # Mostrar información del prompt actual si existe
        if blocks_manager.current_prompt_folder and blocks_manager.prompt_metadata:
            import os
            prompt_name = os.path.basename(blocks_manager.current_prompt_folder)
            box.label(text=f"📁 Prompt actual: {prompt_name}", icon='FILE_FOLDER')

            # Calcular duración DINÁMICA basada en timeline COMPARTIDO
            max_entity_frames = 0  # Máximo frames por entidad (no suma total)
            total_loaded_blocks = 0
            active_entities = 0
            entity_frame_counts = []  # Para mostrar detalle por entidad

            # Recorrer todas las entidades y sus bloques cargados
            for entity_name, entity_data in blocks_manager.entities.items():
                entity_controller = entity_data.get('controller')
                if entity_controller:
                    # Contar bloques cargados en esta entidad
                    loaded_blocks = [block for block in entity_controller.blocks.values() if block.get('is_loaded', False)]
                    if loaded_blocks:
                        active_entities += 1
                        entity_frames = sum(block.get('frame_count', 0) for block in loaded_blocks)
                        entity_frame_counts.append((entity_name, entity_frames))
                        max_entity_frames = max(max_entity_frames, entity_frames)  # Timeline compartido = máximo
                        total_loaded_blocks += len(loaded_blocks)

            # Usar el máximo de frames como duración total (timeline compartido)
            total_loaded_frames = max_entity_frames

            # Obtener FPS del prompt actual
            config_global = blocks_manager.prompt_metadata.get('configuracion_global', {}) if blocks_manager.prompt_metadata else {}
            fps = config_global.get('fps', 24) if config_global else 24

            # Calcular duración basada en frames realmente cargados
            if total_loaded_frames > 0 and fps > 0:
                total_duration_seconds = total_loaded_frames / fps
                minutes = int(total_duration_seconds // 60)
                seconds = int(total_duration_seconds % 60)

                # Mostrar duración calculada dinámicamente
                duration_text = f"⏱️ Duración calculada: {minutes}:{seconds:02d} min ({total_loaded_frames} frames @ {fps}fps)"
                box.label(text=duration_text, icon='TIME')

                # Información adicional sobre timeline compartido
                timeline_info = f"🎬 Bloques activos: {total_loaded_blocks} | 🎭 Entidades: {active_entities}"
                box.label(text=timeline_info, icon='ACTION')

                # Mostrar detalle de frames por entidad (timeline compartido)
                if entity_frame_counts:
                    entities_detail = " | ".join([f"{name}: {frames}f" for name, frames in entity_frame_counts])
                    box.label(text=f"📊 Frames por entidad: {entities_detail}", icon='TIME')
                    box.label(text=f"🎯 Timeline compartido: {max_entity_frames} frames máximo", icon='SCENE_DATA')

            else:
                # Fallback: usar metadata del prompt si no hay bloques cargados
                prompt_info = blocks_manager.prompt_metadata.get('prompt_info', {}) if blocks_manager.prompt_metadata else {}
                total_frames = prompt_info.get('total_duration_target', 0) if prompt_info else 0

                if total_frames > 0 and fps > 0:
                    total_duration_seconds = total_frames / fps
                    minutes = int(total_duration_seconds // 60)
                    seconds = int(total_duration_seconds % 60)
                    duration_text = f"⏱️ Duración estimada: {minutes}:{seconds:02d} min ({total_frames} frames @ {fps}fps)"
                    box.label(text=duration_text, icon='TIME')
                    box.label(text="💡 Carga animaciones para cálculo preciso", icon='INFO')
                else:
                    box.label(text="⚠️ No se pudo calcular duración", icon='ERROR')
                    box.label(text="💡 Carga un prompt y animaciones", icon='HELP')
        else:
            # Mostrar estado cuando no hay prompt cargado
            box.label(text="💡 No hay prompt cargado", icon='INFO')
            box.label(text="Usa 'Cargar Carpeta Prompt' para cargar un prompt", icon='HELP')

            # Mostrar entidades configuradas
            if (blocks_manager.prompt_metadata and
                'entidades' in blocks_manager.prompt_metadata and
                isinstance(blocks_manager.prompt_metadata['entidades'], dict)):
                entities_config = blocks_manager.prompt_metadata['entidades']
                entities_info = box.box()
                entities_info.label(text=f"🎭 Entidades configuradas: {len(entities_config)}", icon='ARMATURE_DATA')

                loaded_entities = blocks_manager.get_loaded_entities()
                if loaded_entities:
                    entities_info.label(text=f"✅ Estructuras cargadas: {len(loaded_entities)}", icon='CHECKMARK')
                else:
                    entities_info.label(text="💡 Carga estructuras manualmente en cada columna", icon='INFO')

                for entity_name, entity_config in entities_config.items():
                    entity_row = entities_info.row()
                    entity_type = entity_config.get('tipo', 'unknown')
                    is_loaded = entity_name in loaded_entities
                    status_icon = 'CHECKMARK' if is_loaded else 'RADIOBUT_OFF'
                    entity_row.label(text=f"{'✅' if is_loaded else '⭕'} {entity_name} ({entity_type})", icon=status_icon)

        box.operator("simple_animblocks.load_prompt_folder", text="Cargar Carpeta Prompt", icon='FILEBROWSER')
        box.operator("simple_animblocks.extract_data", text="Extraer Datos", icon='EXPORT')

        # Información del flujo de trabajo - REMOVIDO PARA INTERFAZ MÁS LIMPIA

        # ENTIDADES EN COLUMNAS (solo si hay entidades cargadas)
        if blocks_manager.entities:
            self.draw_entities_columns(context, layout, blocks_manager)

    def draw_entities_columns(self, context, layout, manager):
        """Dibuja las entidades en columnas separadas con separación escenario/entidades"""
        if not manager.entities:
            return

        # Contenedor principal para columnas
        main_box = layout.box()
        main_box.label(text="🎭 ESCENARIO Y ENTIDADES", icon='MODIFIER')

        # Crear una fila para las columnas
        row = main_box.row()

        # SEPARAR ESCENARIO DE ENTIDADES
        scenario_entities = []
        character_entities = []

        for entity_name, entity_data in manager.entities.items():
            entity_type = entity_data.get('type', '').lower()
            if entity_type == 'scenario' or entity_name.lower() == 'ecenario':
                scenario_entities.append(entity_name)
            else:
                character_entities.append(entity_name)

        # Inicializar num_entities para evitar error de variable no definida
        num_entities = len(character_entities)

        # MOSTRAR ESCENARIO PRIMERO (si existe)
        if scenario_entities:
            scenario_box = layout.box()
            scenario_box.label(text="🎬 ESCENARIO", icon='WORLD')

            scenario_row = scenario_box.row()
            scenario_col = scenario_row.column()

            for scenario_name in scenario_entities:
                self.draw_entity_column(context, scenario_col, scenario_name, manager.entities[scenario_name], manager)

        # MOSTRAR ENTIDADES DE PERSONAJES
        if character_entities:
            # Contenedor para entidades de personajes
            characters_box = layout.box()
            characters_box.label(text="🎭 ENTIDADES DE PERSONAJES", icon='ARMATURE_DATA')

            # ORGANIZAR ENTIDADES EN FILAS PARA MEJOR USO DEL ESPACIO
            num_entities = len(character_entities)
            entities_per_row = min(3, num_entities)  # Máximo 3 entidades por fila

            for i, entity_name in enumerate(character_entities):
                if i % entities_per_row == 0:
                    # Crear nueva fila
                    if i > 0:
                        # Separador visual entre filas
                        characters_box.separator()
                    entity_row = characters_box.row()

                # Crear columna para esta entidad
                entity_col = entity_row.column()
                # Dibujar entidad en su columna
                self.draw_entity_column(context, entity_col, entity_name, manager.entities[entity_name], manager)

        # CONTROLES GLOBALES MULTI-ENTIDAD
        if num_entities > 1:
            global_box = layout.box()
            global_box.label(text="🎬 CONTROLES MULTI-ENTIDAD", icon='PLAY')

            # Botón para reproducir todas las entidades simultáneamente
            play_all_row = global_box.row(align=True)
            play_all_op = play_all_row.operator("simple_animblocks.play_multi_entity", text="🎭 Reproducir Todas las Entidades", icon='PLAY')
            play_all_row.scale_y = 1.5

            # Información de timeline compartido - CALCULADO DINÁMICAMENTE
            # Calcular entidades activas y máximo de frames
            active_entities_in_panel = []
            max_frames = 0
            for name, entity_data in manager.entities.items():
                entity_controller = entity_data.get('controller')
                if entity_controller and len([b for b in entity_controller.blocks.values() if b['is_loaded']]) > 0:
                    active_entities_in_panel.append(name)
                    entity_frames = sum(block['frame_count'] for block in entity_controller.blocks.values() if block['is_loaded'])
                    max_frames = max(max_frames, entity_frames)

            total_frames = max_frames if max_frames > 0 else 360
            fps = manager.prompt_metadata.get('configuracion_global', {}).get('fps', 24) if manager.prompt_metadata else 24
            duration = total_frames / fps

            timeline_info = global_box.box()
            timeline_info.label(text=f"⏱️ Timeline Calculado: 1-{total_frames} frames ({duration:.1f}s)", icon='TIME')
            timeline_info.label(text=f"🎯 Máximo entre {len(active_entities_in_panel)} entidades activas", icon='SCENE_DATA')
            timeline_info.label(text=f"🎬 FPS: {fps} | 📊 Frames totales: {total_frames}", icon='SETTINGS')

    def draw_entity_column(self, context, layout, entity_name, entity_data, manager):
        """Dibuja una columna para una entidad específica con su propio sistema BLOQUES DE ANIMACIÓN"""
        # Header de la entidad
        entity_box = layout.box()
        header_row = entity_box.row()

        # Icono según tipo de entidad
        entity_type = entity_data.get('type', 'unknown')
        icon = self.get_entity_icon(entity_type)

        # MANEJO ESPECIAL PARA ESCENARIO
        is_scenario = entity_type.lower() == 'scenario' or entity_name.lower() == 'ecenario'

        if is_scenario:
            # ESCENARIO: Siempre está "cargado" (no necesita .blend)
            header_row.label(text=f"{entity_name} (Escenario)", icon=icon)
            header_row.label(text="", icon='CHECKMARK')

            # Información especial para escenario
            scenario_row = entity_box.row()
            scenario_row.label(text="🎬 Escenario compartido", icon='WORLD')
            scenario_row = entity_box.row()
            scenario_row.label(text="No requiere estructura .blend", icon='INFO')
        else:
            # ENTIDAD NORMAL: Estado de carga de estructura
            is_loaded = entity_data.get('is_loaded', False)
            status_icon = 'CHECKMARK' if is_loaded else 'RADIOBUT_OFF'

            header_row.label(text=f"{entity_name} ({entity_type})", icon=icon)
            header_row.label(text="", icon=status_icon)

            # Información de carga de estructura
            structure_row = entity_box.row()
            if is_loaded:
                structure_row.label(text="Estructura: ✅ Cargada", icon='FILE_BLEND')
            else:
                structure_row.label(text="Estructura: ❌ Pendiente", icon='FILE_BLEND')

            # Botones para cargar/limpiar estructura
            structure_buttons_row = entity_box.row(align=True)
            structure_buttons_row.scale_y = 1.1

            # Botón para cargar estructura
            load_structure_op = structure_buttons_row.operator("simple_animblocks.load_entity_structure", text="Cargar Estructura", icon='FILE_BLEND')
            load_structure_op.entity_name = entity_name

            # Botón para actualizar entidad (solo si hay prompt cargado)
            if manager.current_prompt_folder:
                refresh_op = structure_buttons_row.operator("simple_animblocks.refresh_entity", text="Actualizar", icon='FILE_REFRESH')
                refresh_op.entity_name = entity_name

            # Botón para limpiar estructura (solo si está cargada)
            if is_loaded:
                clear_structure_op = structure_buttons_row.operator("simple_animblocks.clear_entity_structure", text="Limpiar", icon='X')
                clear_structure_op.entity_name = entity_name

        # Información de animaciones
        entity_controller = entity_data.get('controller')
        if entity_controller:
            loaded_count = len([b for b in entity_controller.blocks.values() if b['is_loaded']])
            total_slots = entity_controller.max_slots if entity_controller.max_slots is not None else len(entity_controller.blocks)

            anim_row = entity_box.row()
            anim_row.label(text=f"Animaciones: {loaded_count}/{total_slots}", icon='ACTION')

            # Botón de concatenar para esta entidad
            if loaded_count > 0:
                concat_row = entity_box.row(align=True)
                concat_op = concat_row.operator("simple_animblocks.concatenate_entity", text="🔗 Concatenar", icon='SETTINGS')
                concat_op.entity_name = entity_name
                concat_row.scale_y = 1.2
                
                # Botón para limpiar selecciones de esta entidad
                if hasattr(manager, 'selected_slots') and manager.selected_slots.get(entity_name, {}):
                    clear_row = entity_box.row(align=True)
                    clear_op = clear_row.operator("simple_animblocks.clear_all_selections", text="🧹 Limpiar Selecciones", icon='X')
                    clear_op.entity_name = entity_name
                    
                    # Mostrar contador de seleccionados
                    selected_count = len([s for s in manager.selected_slots.get(entity_name, {}).values() if s])
                    if selected_count > 0:
                        info_row = entity_box.row()
                        info_row.label(text=f"📌 {selected_count} slot(s) seleccionado(s) para concatenar", icon='INFO')

            # 🎬 BLOQUES DE ANIMACIÓN por entidad (sistema individual)
            if loaded_count > 0:
                # Sección BLOQUES DE ANIMACIÓN para esta entidad
                blocks_box = entity_box.box()
                blocks_box.label(text=f"🎬 BLOQUES DE ANIMACIÓN - {entity_name}", icon='SEQUENCE')

                # Información de secuencia para esta entidad
                sequence = entity_controller.get_loaded_blocks_sequence()
                if sequence:
                    seq_info = blocks_box.box()
                    seq_info.label(text=f"Secuencia: {len(sequence)} bloques")
                    total_frames = sum(block['frame_count'] for block in sequence)
                    seq_info.label(text=f"Total: {total_frames} frames")

                # Mostrar slots de la entidad con sistema de evaluación
                slots_container = blocks_box.box()

                # Mostrar TODOS los slots disponibles sin límite de visualización
                for slot_num in sorted(entity_controller.blocks.keys()):
                    block = entity_controller.blocks[slot_num]
                    if block['is_loaded']:
                        # Slot individual con evaluación ⭐
                        slot_box = slots_container.box()

                        # INDICADOR VISUAL: Color diferente si el slot está activo durante reproducción
                        # Asegurar que los indicadores existen para esta entidad
                        if entity_name not in manager.active_entity_slot_indicators:
                            manager.initialize_entity_slot_indicators(entity_name)
                        is_active = manager.active_entity_slot_indicators.get(entity_name, {}).get(slot_num, False)

                        # Header del slot
                        slot_header = slot_box.row()
                        if is_active:
                            # Slot ACTIVO - Color verde/azul para resaltar
                            slot_header.alert = True  # Hace que el row tenga color de alerta
                            slot_header.label(text=f"🎬 SLOT {slot_num} - ACTIVO", icon='PLAY')
                        else:
                            slot_header.label(text=f"Slot {slot_num}: {block['name']}", icon='FILE_TEXT')
                            slot_header.label(text=f"{block['frame_count']}f", icon='TIME')

                        # Indicador de selección para secuencia
                        if not hasattr(manager, 'selected_slots'):
                            manager.selected_slots = {}
                        if entity_name not in manager.selected_slots:
                            manager.selected_slots[entity_name] = {}
                        is_selected = manager.selected_slots.get(entity_name, {}).get(slot_num, False)

                        # Mostrar estado de selección
                        if is_selected:
                            selected_row = slot_box.row()
                            selected_row.label(text="✅ Seleccionado para secuencia", icon='CHECKBOX_HLT')

                        # Sistema de calificación y comentarios removidos por solicitud del usuario

                        # Controles del slot - Botón toggle seleccionar
                        controls_row = slot_box.row(align=True)
                        if is_selected:
                            toggle_op = controls_row.operator("simple_animblocks.toggle_slot_selection", text=f"❌ Quitar (Slot {slot_num})", icon='CHECKBOX_HLT')
                        else:
                            toggle_op = controls_row.operator("simple_animblocks.toggle_slot_selection", text=f"✅ Seleccionar (Slot {slot_num})", icon='CHECKBOX_DEHLT')
                        toggle_op.entity_name = entity_name
                        toggle_op.slot = slot_num

                        # Panel de ojos editable (solo para alfred)
                        if entity_name.lower() == "alfred":
                            eye_mod = _try_import_eye_props()
                            filepath = block.get('file_path', '')
                            slot_key = f"{entity_name}::{slot_num}"

                            if eye_mod is not None and filepath and os.path.isfile(filepath):
                                # Solo lectura durante draw - nunca escribir aqui
                                cfg = eye_mod._get_eye_config(context, slot_key)

                                if cfg is not None and cfg.loaded:
                                    # ── Panel de ojos editable ──────────────────
                                    eye_mod.draw_eye_editor(slot_box, cfg, slot_key, filepath)

                                    # Botón Crear / Recrear Shape Keys
                                    eye_row = slot_box.row()
                                    eye_row.scale_y = 1.3
                                    eye_op = eye_row.operator(
                                        "simple_animblocks.rebuild_eye_shape_keys_slot",
                                        text="Crear / Recrear Shape Keys",
                                        icon='SCULPTMODE_HLT',
                                    )
                                    eye_op.entity_name = entity_name
                                    eye_op.slot = slot_num

                                    # Botón CONCATENAR_2 (Ojos)
                                    concat2_row = slot_box.row()
                                    concat2_row.scale_y = 1.5
                                    concat2_op = concat2_row.operator(
                                        "simple_animblocks.concatenate_eyes",
                                        text="▶  CONCATENAR_2  (Ojos)",
                                        icon='HIDE_OFF',
                                    )
                                    concat2_op.entity_name = entity_name
                                    concat2_op.slot = slot_num
                                else:
                                    # Verificar si el .py tiene datos de ojos antes de mostrar boton
                                    has_eye = eye_mod._file_has_eye_data(filepath)
                                    if has_eye:
                                        load_row = slot_box.row()
                                        load_row.scale_y = 1.3
                                        load_op = load_row.operator(
                                            "alfeyecap2.load_config",
                                            text="👁  Cargar config de ojos",
                                            icon='HIDE_OFF',
                                        )
                                        load_op.slot_key = slot_key
                                        load_op.filepath = filepath

                                        # Botones de accion igualmente disponibles
                                        eye_row = slot_box.row()
                                        eye_op = eye_row.operator(
                                            "simple_animblocks.rebuild_eye_shape_keys_slot",
                                            text="Crear / Recrear Shape Keys",
                                            icon='SCULPTMODE_HLT',
                                        )
                                        eye_op.entity_name = entity_name
                                        eye_op.slot = slot_num

                                        concat2_row = slot_box.row()
                                        concat2_row.scale_y = 1.5
                                        concat2_op = concat2_row.operator(
                                            "simple_animblocks.concatenate_eyes",
                                            text="▶  CONCATENAR_2  (Ojos)",
                                            icon='HIDE_OFF',
                                        )
                                        concat2_op.entity_name = entity_name
                                        concat2_op.slot = slot_num
                                    # Si no tiene datos de ojos no se muestra nada

                # Información adicional si hay slots cargados
                if loaded_count > 0:
                    # Calcular frames totales para esta entidad
                    total_frames = sum(block['frame_count'] for block in entity_controller.blocks.values() if block['is_loaded'])
                    final_info = blocks_box.row()
                    final_info.label(text=f"📊 Total entidad: {total_frames} frames", icon='TIME')
        else:
            entity_box.label(text="Controller no disponible", icon='ERROR')

    def get_entity_icon(self, entity_type):
        """Retorna el icono apropiado para el tipo de entidad"""
        icon_map = {
            'scenario': 'WORLD',
            'player': 'USER',
            'hostile': 'GHOST_ENABLED',
            'passive': 'ARMATURE_DATA',
            'custom': 'BLANK1'
        }
        return icon_map.get(entity_type, 'BLANK1')

# ============================================================================
# PANEL DEDICADO PARA CREACIÓN DE LUCES
# ============================================================================

class ANIMBLOCKS_PT_LightCreatorPanel(Panel):
    bl_label = "Light Creator"
    bl_idname = "ANIMBLOCKS_PT_light_creator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Light Creator'

    def draw(self, context):
        layout = self.layout

        # CONTROLES PRINCIPALES
        controls_box = layout.box()
        controls_row = controls_box.row(align=True)
        controls_row.scale_y = 1.2

        # Botón Reset - limpia todas las luces creadas
        reset_op = controls_row.operator("simple_animblocks.reset_lights", text="🗑️ Reset", icon='TRASH')
        controls_row.separator()
        controls_row.label(text="💡 Sistema de Creación de Luces", icon='LIGHT')

        # Descripción
        desc_box = layout.box()
        desc_row = desc_box.row()
        desc_row.label(text="Crea luces basadas en fuentes de luz de Minecraft", icon='INFO')
        desc_row = desc_box.row()
        desc_row.label(text="Cada botón '⚡ Aplicar' crea luces inmediatamente", icon='PLAY')

        # SECCIÓN PRINCIPAL DE LUCES
        main_lights_box = layout.box()
        main_lights_box.label(text="🔥 Fuentes de Luz Disponibles", icon='LIGHT')

        # Verificar si existe la carpeta de luces
        import os
        addon_dir = os.path.dirname(os.path.dirname(__file__))
        lights_dir = os.path.join(addon_dir, "light_placement_tool", "luces")

        if os.path.exists(lights_dir):
            json_files = [f for f in os.listdir(lights_dir) if f.endswith('.json')]
            if json_files:
                # Información general
                info_box = main_lights_box.box()
                info_row = info_box.row()
                info_row.label(text=f"📁 Total de fuentes: {len(json_files)}", icon='FILE_TEXT')
                info_row = info_box.row()
                info_row.label(text="🗂️ Luces organizadas por tipo de bloque", icon='FILE_TEXT')

                # Lista de luces organizada
                lights_list_box = main_lights_box.box()

                # Categorizar luces por tipo
                torch_lights = []
                block_lights = []
                natural_lights = []
                other_lights = []

                for light_file in sorted(json_files):
                    light_name = light_file.replace('.json', '').lower()
                    if 'torch' in light_name:
                        torch_lights.append(light_file)
                    elif any(word in light_name for word in ['furnace', 'campfire', 'lantern', 'sea_pickle']):
                        block_lights.append(light_file)
                    elif any(word in light_name for word in ['glow_lichen', 'cave_vines', 'spore_blossom', 'amethyst']):
                        natural_lights.append(light_file)
                    else:
                        other_lights.append(light_file)

                # Función helper para crear sección de luces
                def draw_light_section(title, light_files, icon):
                    if light_files:
                        section_box = lights_list_box.box()
                        section_row = section_box.row()
                        section_row.label(text=f"{icon} {title} ({len(light_files)})", icon='TRIA_RIGHT')

                        # Grid para los botones
                        lights_grid = section_box.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True)

                        for light_file in sorted(light_files):
                            light_name = light_file.replace('.json', '')
                            display_name = light_name.replace('_', ' ').title()

                            # Contenedor para cada luz
                            light_container = lights_grid.box()
                            light_row = light_container.row(align=True)

                            # Icono y nombre
                            light_row.label(text=display_name, icon='LIGHT')

                            # Botón Aplicar
                            apply_op = light_row.operator("simple_animblocks.apply_single_light",
                                                        text="⚡ Aplicar", icon='PLAY')
                            apply_op.light_name = light_name

                # Dibujar secciones organizadas
                draw_light_section("Antorchas y Luminarias", torch_lights, "🔥")
                draw_light_section("Bloques Luminosos", block_lights, "🟫")
                draw_light_section("Elementos Naturales", natural_lights, "🌿")
                draw_light_section("Otros", other_lights, "❓")

                # Información adicional
                help_box = main_lights_box.box()
                help_row = help_box.row()
                help_row.label(text="💡 Consejos:", icon='HELP')
                help_row = help_box.row()
                help_row.label(text="• Las luces se crean en la colección 'Luces_Generadas'", icon='GROUP')
                help_row = help_box.row()
                help_row.label(text="• Cada fuente tiene propiedades físicas específicas", icon='SETTINGS')
                help_row = help_box.row()
                help_row.label(text="• Las coordenadas provienen de archivos JSON", icon='FILE')

                # Botón para refrescar
                refresh_row = main_lights_box.row(align=True)
                refresh_op = refresh_row.operator("simple_animblocks.refresh_light_selection",
                                                text="🔄 Refrescar Lista de Luces", icon='FILE_REFRESH')
                refresh_row.scale_y = 1.2

            else:
                main_lights_box.label(text="⚠️ No se encontraron archivos de luces", icon='ERROR')
                main_lights_box.label(text="Verifica que existan archivos .json en light_placement_tool/luces/", icon='INFO')
        else:
            main_lights_box.label(text="⚠️ Carpeta de luces no encontrada", icon='ERROR')
            main_lights_box.label(text="Ruta esperada: light_placement_tool/luces/", icon='FOLDER_REDIRECT')

        # SECCIÓN DE ESTADÍSTICAS
        stats_box = layout.box()
        stats_box.label(text="📊 Información del Sistema", icon='INFO')

        # Estadísticas de luces creadas (si hay colección)
        lights_collection = None
        for coll in bpy.data.collections:
            if coll.name == "Luces_Generadas":
                lights_collection = coll
                break

        if lights_collection:
            total_lights = len(lights_collection.objects)
            stats_box.label(text=f"✅ Luces creadas: {total_lights}", icon='CHECKMARK')
            stats_box.label(text=f"📁 Colección: '{lights_collection.name}'", icon='GROUP')
        else:
            stats_box.label(text="ℹ️ No hay luces creadas aún", icon='INFO')
            stats_box.label(text="Las luces aparecerán aquí al crearlas", icon='LIGHT')

# ============================================================================
# REGISTRO DEL MÓDULO
# ============================================================================

def register():
    """Registra los paneles y operadores de UI"""
    try:
        bpy.utils.register_class(ANIMBLOCKS_OT_ApplySingleLight)
        bpy.utils.register_class(ANIMBLOCKS_OT_RefreshLightSelection)
        bpy.utils.register_class(ANIMBLOCKS_OT_ResetLights)
        bpy.utils.register_class(ANIMBLOCKS_OT_LoadStructure)
        bpy.utils.register_class(ANIMBLOCKS_OT_LoadAnimationBlock)
        bpy.utils.register_class(ANIMBLOCKS_PT_MainPanel)
        bpy.utils.register_class(ANIMBLOCKS_PT_LightCreatorPanel)
        print("✅ Paneles de UI registrados correctamente")
    except Exception as e:
        print(f"❌ Error registrando paneles de UI: {e}")

def unregister():
    """Desregistra los paneles y operadores de UI"""
    try:
        bpy.utils.unregister_class(ANIMBLOCKS_PT_LightCreatorPanel)
        bpy.utils.unregister_class(ANIMBLOCKS_PT_MainPanel)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_LoadAnimationBlock)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_LoadStructure)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_RefreshLightSelection)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_ResetLights)
        bpy.utils.unregister_class(ANIMBLOCKS_OT_ApplySingleLight)
        print("✅ Paneles de UI desregistrados correctamente")
    except Exception as e:
        print(f"❌ Error desregistrando paneles de UI: {e}")