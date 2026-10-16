#!/usr/bin/env python3
"""
core_system.py - Sistema central del Multi-Entity Animation Blocks Manager
Contiene la clase principal SimpleAnimationBlocksManager y configuración base
"""

import bpy
import os
import json
import datetime
import importlib.util
import math
import mathutils
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, IntProperty, BoolProperty, CollectionProperty
from bpy.types import PropertyGroup, Panel, Operator, UIList

# ============================================================================
# SISTEMA DE OBJETOS DINÁMICOS - INTEGRACIÓN
# ============================================================================

# Importar módulos del sistema de objetos dinámicos
try:
    from dynamic_object_importer import DynamicObjectImporter
    from narrative_object_parser import NarrativeObjectParser
    DYNAMIC_OBJECTS_AVAILABLE = True
    print("✅ Sistema de objetos dinámicos disponible")
except ImportError as e:
    print(f"⚠️ Sistema de objetos dinámicos no disponible: {e}")
    DYNAMIC_OBJECTS_AVAILABLE = False
    DynamicObjectImporter = None
    NarrativeObjectParser = None

# ============================================================================
# SISTEMA DE ORGANIZACIÓN AUTOMÁTICA DE FEEDBACK IA
# ============================================================================

# Importar sistema de organización de feedback
try:
    from Extractor_de_datos.feedback_organizer_system import FeedbackOrganizerSystem
    FEEDBACK_ORGANIZER_AVAILABLE = True
    print("✅ Sistema de organización de feedback disponible")
except ImportError as e:
    print(f"⚠️ Sistema de organización de feedback no disponible: {e}")
    FEEDBACK_ORGANIZER_AVAILABLE = False
    FeedbackOrganizerSystem = None

# Configuración del addon
bl_info = {
    "name": "Multi-Entity Animation Blocks Manager",
    "author": "Sistema Multi-Entidad Avanzado",
    "version": (2, 1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Animation Blocks",
    "description": "Gestor multi-entidad con carga automática desde carpetas Prompt_X",
    "category": "Animation",
}

# ============================================================================
# CLASES BASE DEL SISTEMA
# ============================================================================

class AnimationSequenceSettings(PropertyGroup):
    auto_set_timeline: BoolProperty(name="Timeline Automático", default=True)
    frame_gap: IntProperty(name="Gap entre Bloques", default=0, min=0)

class AnimationBlock(PropertyGroup):
    name: StringProperty(name="Nombre", default="")
    file_path: StringProperty(name="Archivo", default="", subtype="FILE_PATH")
    frame_count: IntProperty(name="Frames", default=0, min=0)
    is_loaded: BoolProperty(name="Cargado", default=False)
    order: IntProperty(name="Orden", default=0)
    description: StringProperty(name="Descripción", default="")
    fps: IntProperty(name="FPS", default=24, min=1)
    rating: IntProperty(name="Calificación", default=0, min=0, max=10, description="Calificación de 1-10 estrellas")
    feedback: StringProperty(name="Comentarios", default="", description="Comentarios sobre qué mejorar")

class EntityManager(PropertyGroup):
    """Gestor para una entidad específica (alfred, creeper, vaca, etc.)"""
    entity_name: StringProperty(name="Nombre Entidad", default="")
    entity_type: StringProperty(name="Tipo", default="")  # player, hostile, passive
    blend_file: StringProperty(name="Archivo .blend", default="", subtype="FILE_PATH")
    is_loaded: BoolProperty(name="Entidad Cargada", default=False)
    assigned_slots: StringProperty(name="Slots Asignados", default="")  # "1,2,3"
    transform_offset: StringProperty(name="Offset Transform", default="0,0,0;0,0,0;1.0")  # location;rotation;scale
    description: StringProperty(name="Descripción", default="")


# ============================================================================
# CLASE PRINCIPAL DEL SISTEMA
# ============================================================================

class SimpleAnimationBlocksManager:
    def __init__(self):
        self.blocks = {}  # Mantenido por compatibilidad, pero ahora usamos entidades
        self.current_structure = None
        self.max_slots = 50  # Para compatibilidad
        self.player_parts = {}  # Para compatibilidad
        self.loop_enabled = False
        self.sequence_frame_ranges = {}
        self.active_slot_indicators = {}

        # SISTEMA MULTI-ENTIDAD PRINCIPAL
        self.entities = {}  # Diccionario de EntityController por nombre
        self.current_prompt_folder = None
        self.prompt_metadata = None
        self.shared_timeline = True
        self.max_entities = 8

        # INDICADORES VISUALES POR ENTIDAD
        self.active_entity_slot_indicators = {}  # {entity_name: {slot: bool}}

        # NUEVO: Sistema de animación relativa
        self.orientation_detector = None  # CharacterOrientationDetector - Se inicializa en entity_system.py
        self.relative_engine = None  # Se inicializa en relative_animation.py
        self.narrative_mode = False  # Modo narrativa vs coherencia visual

        # NUEVO: Sistema específico para Alfred
        self.alfred_hybrid_system_enabled = True  # Habilitar sistema híbrido para Alfred
        self.alfred_templates_path = os.path.join(os.path.dirname(__file__), "acciones")
        self.alfred_auto_regenerate = True  # Regeneración automática para animaciones fallidas

        # Inicializar sistema de validación post-generación
        try:
            from post_generation_validator import integrate_validator_with_animation_manager
            self.post_generation_validator = integrate_validator_with_animation_manager(self)
            print("✅ Sistema de validación post-generación inicializado")
        except ImportError:
            print("⚠️ Sistema de validación post-generación no disponible")
            self.post_generation_validator = None

        # NUEVO: Sistema de objetos dinámicos
        self.dynamic_objects_enabled = DYNAMIC_OBJECTS_AVAILABLE
        self.dynamic_objects_importer = None
        self.dynamic_objects_parser = None
        self.imported_dynamic_objects = {}  # {entity_name: [object_names]}

        if self.dynamic_objects_enabled:
            try:
                self.dynamic_objects_importer = DynamicObjectImporter()
                self.dynamic_objects_parser = NarrativeObjectParser()
                print("✅ Sistema de objetos dinámicos inicializado")
            except Exception as e:
                print(f"❌ Error inicializando sistema de objetos dinámicos: {e}")
                self.dynamic_objects_enabled = False

        # NUEVO: Sistema de organización de feedback IA
        self.feedback_organizer = None
        self.feedback_organizer_enabled = FEEDBACK_ORGANIZER_AVAILABLE

        if self.feedback_organizer_enabled and FeedbackOrganizerSystem:
            try:
                self.feedback_organizer = FeedbackOrganizerSystem()
                print("✅ Sistema de organización de feedback inicializado")
            except Exception as e:
                print(f"❌ Error inicializando sistema de organización de feedback: {e}")
                self.feedback_organizer_enabled = False

        self.initialize_slots()  # Para compatibilidad
        self.find_player_parts()  # Para compatibilidad
        self.initialize_slot_indicators()

    def find_player_parts(self):
        """Encuentra todas las partes del jugador en la escena (soporte para sufijos _alfred)"""
        # Inicializar diccionario de partes del jugador
        self.player_parts = {
            'body': None,
            'head': None,
            'left_arm': None,
            'right_arm': None,
            'left_leg': None,
            'right_leg': None
        }

        # Buscar el objeto padre "alfred" (prioridad) o "player" (fallback)
        player_parent = None
        for obj in bpy.data.objects:
            obj_name_lower = obj.name.lower()
            if obj_name_lower == 'alfred' and len(obj.children) > 0:
                player_parent = obj
                print(f"🎯 Encontrado root principal 'alfred': {obj.name}")
                break
            elif obj_name_lower == 'player' and len(obj.children) > 0:
                player_parent = obj
                print(f"⚠️ Usando root alternativo 'player': {obj.name}")
                # No break aquí, continuar buscando por si hay un "alfred"

        if player_parent:
            print(f"🎭 Encontrado objeto padre: {player_parent.name}")
            # Buscar en los hijos del objeto player/alfred
            for child in player_parent.children:
                part_name = child.name.lower()
                # Primero buscar partes con sufijo _alfred
                for base_part in self.player_parts.keys():
                    if part_name == f"{base_part}_alfred":
                        self.player_parts[base_part] = child
                        print(f"   ✅ {child.name} → {base_part} (_alfred)")
                        break
                else:
                    # Si no encontró _alfred, buscar nombre exacto
                    if part_name in self.player_parts:
                        self.player_parts[part_name] = child
                        print(f"   ✅ {child.name}")
        else:
            # Método de búsqueda alternativo si no hay padre "alfred"/"player"
            print("🔍 Buscando partes del jugador (método alternativo con soporte _alfred)...")

            # Primero intentar encontrar el root "alfred" si existe
            alfred_root = None
            for obj in bpy.data.objects:
                if obj.name.lower() == 'alfred':
                    alfred_root = obj
                    print(f"🎯 Encontrado root 'alfred' en búsqueda alternativa: {obj.name}")
                    break

            if alfred_root:
                # Si encontramos root "alfred", buscar sus hijos
                for child in alfred_root.children:
                    part_name = child.name.lower()
                    # Buscar partes con sufijo _alfred
                    for base_part in self.player_parts.keys():
                        if part_name == f"{base_part}_alfred":
                            self.player_parts[base_part] = child
                            print(f"   ✅ {child.name} → {base_part} (_alfred)")
                            break
                    else:
                        # Si no encontró _alfred, buscar nombre exacto
                        if part_name in self.player_parts:
                            self.player_parts[part_name] = child
                            print(f"   ✅ {child.name}")
            else:
                # Búsqueda completamente alternativa
                for obj in bpy.data.objects:
                    part_name = obj.name.lower()
                    # Primero buscar partes con sufijo _alfred
                    for base_part in self.player_parts.keys():
                        if part_name == f"{base_part}_alfred":
                            self.player_parts[base_part] = obj
                            print(f"   ✅ {obj.name} → {base_part} (_alfred)")
                            break
                    else:
                        # Si no encontró _alfred, buscar nombre exacto
                        if part_name in self.player_parts:
                            self.player_parts[part_name] = obj
                            print(f"   ✅ {obj.name}")

        # Verificar qué partes se encontraron
        found_parts = [name for name, obj in self.player_parts.items() if obj is not None]
        missing_parts = [name for name, obj in self.player_parts.items() if obj is None]
        print(f"📊 Partes encontradas: {found_parts}")
        if missing_parts:
            print(f"⚠️ Partes faltantes: {missing_parts}")

        return len(found_parts) > 0

    def initialize_slots(self):
        for i in range(1, self.max_slots + 1):
            self.blocks[i] = {
                'name': '', 'file_path': '', 'frame_count': 0, 'is_loaded': False,
                'order': i, 'description': '', 'fps': 24, 'rating': 0, 'feedback': ''
            }

    def initialize_slot_indicators(self):
        """Inicializa indicadores visuales para cada slot"""
        for i in range(1, self.max_slots + 1):
            self.active_slot_indicators[i] = False  # False = no activo, True = activo

    def initialize_entity_slot_indicators(self, entity_name: str):
        """Inicializa indicadores visuales para una entidad específica"""
        if entity_name not in self.active_entity_slot_indicators:
            self.active_entity_slot_indicators[entity_name] = {}
            # Inicializar slots 1-20 para esta entidad
            for slot in range(1, 21):  # 20 slots por entidad
                self.active_entity_slot_indicators[entity_name][slot] = False

    def get_loaded_entities(self):
        """Retorna lista de entidades cargadas"""
        return [name for name, entity in self.entities.items() if entity.get('is_loaded', False)]

    def calculate_total_frames(self):
        """Calcula el total de frames de todos los bloques cargados"""
        total = 0
        for block in self.blocks.values():
            if block['is_loaded']:
                total += block['frame_count']
        return total

    def get_loaded_blocks_sequence(self):
        """Retorna lista de bloques cargados para compatibilidad"""
        sequence = []
        for slot in range(1, self.max_slots + 1):
            if self.blocks[slot]['is_loaded']:
                block_data = self.blocks[slot].copy()
                block_data['slot'] = slot
                sequence.append(block_data)
        return sequence

# ============================================================================
# FUNCIONES GLOBALES
# ============================================================================

def get_blocks_manager():
    """Retorna la instancia global del manager"""
    global blocks_manager
    if 'blocks_manager' not in globals():
        blocks_manager = SimpleAnimationBlocksManager()
    return blocks_manager

# ============================================================================
# REGISTRO DEL MÓDULO
# ============================================================================

def register():
    """Registra las clases base del sistema"""
    try:
        bpy.utils.register_class(AnimationSequenceSettings)
        bpy.utils.register_class(AnimationBlock)
        bpy.utils.register_class(EntityManager)

        # Propiedades para sistema multi-entidad
        bpy.types.Scene.multi_entity_entities = bpy.props.CollectionProperty(type=EntityManager)

        # Propiedades para selección de luces (usando string para mayor compatibilidad)
        bpy.types.Scene.light_selected_items = bpy.props.StringProperty(
            name="Luces Seleccionadas",
            default="",
            description="Lista de luces seleccionadas separadas por comas"
        )

        # Propiedad para controlar el panel desplegable de luces
        bpy.types.Scene.show_lights_panel = bpy.props.BoolProperty(
            name="Mostrar Panel de Luces",
            default=False,
            description="Mostrar/ocultar el panel de creación de luces"
        )

        print("✅ Sistema central registrado correctamente")

        # Registrar propiedades editables de ojos para alfred
        try:
            import alfred_eye_props
            alfred_eye_props.register()
            print("✅ alfred_eye_props registrado")
        except Exception as e:
            print(f"⚠️ alfred_eye_props no disponible: {e}")

    except Exception as e:
        print(f"❌ Error registrando sistema central: {e}")

def unregister():
    """Desregistra las clases base del sistema"""
    try:
        if hasattr(bpy.types.Scene, 'multi_entity_entities'):
            del bpy.types.Scene.multi_entity_entities
        if hasattr(bpy.types.Scene, 'light_selected_items'):
            del bpy.types.Scene.light_selected_items
        if hasattr(bpy.types.Scene, 'show_lights_panel'):
            del bpy.types.Scene.show_lights_panel

        bpy.utils.unregister_class(EntityManager)
        bpy.utils.unregister_class(AnimationBlock)
        bpy.utils.unregister_class(AnimationSequenceSettings)

        print("✅ Sistema central desregistrado correctamente")

        # Desregistrar propiedades editables de ojos
        try:
            import alfred_eye_props
            alfred_eye_props.unregister()
        except Exception:
            pass

    except Exception as e:
        print(f"❌ Error desregistrando sistema central: {e}")

# Inicializar instancia global
blocks_manager = SimpleAnimationBlocksManager()