#!/usr/bin/env python3
"""
dynamic_objects.py - Sistema de objetos dinámicos del Multi-Entity Animation Blocks Manager
Contiene integración con DynamicObjectImporter y NarrativeObjectParser
"""

# ============================================================================
# INTEGRACIÓN CON SISTEMA DE OBJETOS DINÁMICOS
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
# FUNCIONES DE SOPORTE PARA OBJETOS DINÁMICOS
# ============================================================================

def initialize_dynamic_objects():
    """Inicializa el sistema de objetos dinámicos"""
    from .core_system import blocks_manager

    if DYNAMIC_OBJECTS_AVAILABLE:
        try:
            blocks_manager.dynamic_objects_importer = DynamicObjectImporter()
            blocks_manager.dynamic_objects_parser = NarrativeObjectParser()
            blocks_manager.dynamic_objects_enabled = True
            print("✅ Sistema de objetos dinámicos inicializado")
        except Exception as e:
            print(f"❌ Error inicializando sistema de objetos dinámicos: {e}")
            blocks_manager.dynamic_objects_enabled = False
    else:
        blocks_manager.dynamic_objects_enabled = False
        print("⚠️ Sistema de objetos dinámicos no disponible")

def process_dynamic_objects_for_entity(entity_name: str, objects_config: dict):
    """Procesa objetos dinámicos para una entidad específica"""
    from .core_system import blocks_manager

    if not blocks_manager.dynamic_objects_enabled:
        return []

    try:
        if blocks_manager.dynamic_objects_importer:
            imported_objects = blocks_manager.dynamic_objects_importer.import_objects_for_entity(
                entity_name, objects_config
            )
            blocks_manager.imported_dynamic_objects[entity_name] = imported_objects
            print(f"✅ {len(imported_objects)} objetos dinámicos importados para {entity_name}")
            return imported_objects
        else:
            print(f"⚠️ Importer no disponible para {entity_name}")
            return []
    except Exception as e:
        print(f"❌ Error procesando objetos dinámicos para {entity_name}: {e}")
        return []

def get_dynamic_objects_for_entity(entity_name: str):
    """Retorna los objetos dinámicos importados para una entidad"""
    from .core_system import blocks_manager
    return blocks_manager.imported_dynamic_objects.get(entity_name, [])

def clear_dynamic_objects_for_entity(entity_name: str):
    """Limpia los objetos dinámicos de una entidad"""
    from .core_system import blocks_manager

    if entity_name in blocks_manager.imported_dynamic_objects:
        # Remover objetos de la escena
        for obj_name in blocks_manager.imported_dynamic_objects[entity_name]:
            if obj_name in bpy.data.objects:
                bpy.data.objects.remove(bpy.data.objects[obj_name])

        # Limpiar registro
        del blocks_manager.imported_dynamic_objects[entity_name]
        print(f"🗑️ Objetos dinámicos limpiados para {entity_name}")

# ============================================================================
# REGISTRO DEL MÓDULO
# ============================================================================

def register():
    """Registra el sistema de objetos dinámicos"""
    initialize_dynamic_objects()
    print("✅ Sistema de objetos dinámicos registrado correctamente")

def unregister():
    """Desregistra el sistema de objetos dinámicos"""
    from .core_system import blocks_manager

    # Limpiar todos los objetos dinámicos importados
    for entity_name in list(blocks_manager.imported_dynamic_objects.keys()):
        clear_dynamic_objects_for_entity(entity_name)

    blocks_manager.dynamic_objects_importer = None
    blocks_manager.dynamic_objects_parser = None
    blocks_manager.dynamic_objects_enabled = False
    blocks_manager.imported_dynamic_objects.clear()

    print("✅ Sistema de objetos dinámicos desregistrado correctamente")