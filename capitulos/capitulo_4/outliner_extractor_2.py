#!/usr/bin/env python3
"""
outliner_extractor_universal.py

Script UNIVERSAL para extraer información COMPLETA del Outliner de Blender.
Funciona con cualquier archivo .blend, capturando TODAS las collections y objetos.
Incluye conexión automática a la carpeta de Extractor_de_datos correspondiente a la entidad.

INTEGRACIÓN COMPLETA CON SISTEMA MULTI-ENTIDAD:
- ✅ Accede al AnimationBlocksManager para obtener estado actual
- ✅ Lee Prompt_X cargado actualmente
- ✅ Conoce entidades activas y su metadata
- ✅ Proporciona contexto completo para IA
"""

import bpy
import json
import os
import math
import sys
import re
from datetime import datetime

def get_bone_hierarchy(armature_obj):
    """Extrae jerarquía completa de bones"""
    if not armature_obj.data or not armature_obj.data.bones:
        return []

    def build_bone_tree(bone, level=0):
        bone_info = {
            'name': bone.name,
            'level': level,
            'connected': bone.use_connect,
            'length': round(bone.length, 6),
            'head': [round(bone.head.x, 6), round(bone.head.y, 6), round(bone.head.z, 6)],
            'tail': [round(bone.tail.x, 6), round(bone.tail.y, 6), round(bone.tail.z, 6)],
            'children': []
        }

        for other_bone in armature_obj.data.bones:
            if other_bone.parent == bone:
                child_info = build_bone_tree(other_bone, level + 1)
                bone_info['children'].append(child_info)

        return bone_info

    root_bones = []
    for bone in armature_obj.data.bones:
        if not bone.parent:
            root_tree = build_bone_tree(bone, 0)
            root_bones.append(root_tree)

    return root_bones

def get_object_info(obj):
    """Obtiene información detallada de cualquier objeto"""
    info = {
        'name': obj.name,
        'type': obj.type,
        'visible': not obj.hide_viewport,
        'hide_render': obj.hide_render,
        'selectable': not obj.hide_select,
        'location': [round(obj.location.x, 6), round(obj.location.y, 6), round(obj.location.z, 6)],
        'rotation_euler': [round(obj.rotation_euler.x, 6), round(obj.rotation_euler.y, 6), round(obj.rotation_euler.z, 6)],
        'scale': [round(obj.scale.x, 6), round(obj.scale.y, 6), round(obj.scale.z, 6)],
        'parent': obj.parent.name if obj.parent else None
    }

    # Información específica por tipo
    if obj.type == 'ARMATURE' and obj.data:
        info['bones_count'] = len(obj.data.bones)
        info['pose_bones_count'] = len(obj.pose.bones) if obj.pose else 0
        info['bone_hierarchy'] = get_bone_hierarchy(obj)

    elif obj.type == 'MESH' and obj.data:
        info['vertices'] = len(obj.data.vertices)
        info['edges'] = len(obj.data.edges)
        info['faces'] = len(obj.data.polygons)
        info['materials'] = [mat.name for mat in obj.data.materials if mat]
        info['modifiers'] = [{'name': mod.name, 'type': mod.type} for mod in obj.modifiers]
        
        # Detectar armature vinculado
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE' and mod.object:
                info['armature_link'] = mod.object.name

    elif obj.type == 'EMPTY':
        info['empty_display_type'] = obj.empty_display_type
        info['empty_display_size'] = obj.empty_display_size

    elif obj.type == 'CAMERA':
        info['lens'] = obj.data.lens if obj.data else None
        info['clip_start'] = obj.data.clip_start if obj.data else None
        info['clip_end'] = obj.data.clip_end if obj.data else None

    elif obj.type == 'LIGHT':
        info['light_type'] = obj.data.type if obj.data else None
        info['energy'] = obj.data.energy if obj.data else None

    elif obj.type == 'CURVE':
        info['curve_type'] = obj.data.dimensions if obj.data else None

    return info

def get_all_collections_recursive(collection, level=0, processed=None):
    """Obtiene TODAS las collections recursivamente, incluso sub-collections"""
    if processed is None:
        processed = set()
    
    # Evitar procesar la misma collection dos veces
    if collection.name in processed:
        return None
    
    processed.add(collection.name)
    
    collection_info = {
        'name': collection.name,
        'type': 'COLLECTION',
        'level': level,
        'hide_viewport': collection.hide_viewport,
        'hide_render': collection.hide_render,
        'objects': [],
        'children': []
    }

    # Obtener TODOS los objetos en esta collection
    for obj in collection.objects:
        obj_info = get_object_info(obj)
        obj_info['collection'] = collection.name
        collection_info['objects'].append(obj_info)

    # Procesar sub-collections recursivamente
    for child in collection.children:
        child_info = get_all_collections_recursive(child, level + 1, processed)
        if child_info:
            collection_info['children'].append(child_info)

    return collection_info

def extract_all_collections():
    """Extrae TODAS las collections del archivo .blend completo"""
    all_collections = {}
    
    # 1. Collections de la escena activa
    if bpy.context.scene.collection:
        scene_coll = get_all_collections_recursive(bpy.context.scene.collection)
        all_collections['scene_collection'] = scene_coll
    
    # 2. TODAS las collections en bpy.data.collections (incluso no vinculadas)
    orphan_collections = []
    processed_names = set()
    
    if 'scene_collection' in all_collections:
        def mark_processed(coll_info):
            processed_names.add(coll_info['name'])
            for child in coll_info.get('children', []):
                mark_processed(child)
        mark_processed(all_collections['scene_collection'])
    
    # Buscar collections huérfanas (no vinculadas a la escena principal)
    for collection in bpy.data.collections:
        if collection.name not in processed_names:
            orphan_info = get_all_collections_recursive(collection, level=0)
            if orphan_info:
                orphan_collections.append(orphan_info)
    
    if orphan_collections:
        all_collections['orphan_collections'] = orphan_collections
    
    # 3. Todas las escenas disponibles
    all_scenes = []
    for scene in bpy.data.scenes:
        scene_info = {
            'name': scene.name,
            'is_current': scene == bpy.context.scene,
            'frame_start': scene.frame_start,
            'frame_end': scene.frame_end,
            'fps': scene.render.fps,
            'collection': get_all_collections_recursive(scene.collection) if scene.collection else None
        }
        all_scenes.append(scene_info)
    
    all_collections['all_scenes'] = all_scenes
    
    return all_collections

def analyze_all_relationships():
    """Analiza TODAS las relaciones entre objetos"""
    relationships = {
        'armatures': [],
        'meshes': [],
        'mesh_to_armature': [],
        'parent_child': [],
        'collections_count': len(bpy.data.collections),
        'objects_count': len(bpy.data.objects)
    }

    # Todos los armatures
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            relationships['armatures'].append({
                'name': obj.name,
                'bones_count': len(obj.data.bones) if obj.data else 0
            })

    # Todos los meshes y sus relaciones
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            mesh_info = {
                'name': obj.name,
                'vertices': len(obj.data.vertices) if obj.data else 0,
                'armature': None,
                'parent': obj.parent.name if obj.parent else None
            }
            
            # Buscar armature vinculado
            for mod in obj.modifiers:
                if mod.type == 'ARMATURE' and mod.object:
                    mesh_info['armature'] = mod.object.name
                    relationships['mesh_to_armature'].append({
                        'mesh': obj.name,
                        'armature': mod.object.name
                    })
            
            relationships['meshes'].append(mesh_info)

    # Relaciones padre-hijo
    for obj in bpy.data.objects:
        if obj.parent:
            relationships['parent_child'].append({
                'child': obj.name,
                'parent': obj.parent.name,
                'child_type': obj.type,
                'parent_type': obj.parent.type
            })

    return relationships

def extract_system_context_old():
    """
    Extrae información del contexto del sistema Multi-Entidad.
    Detecta automáticamente las entidades cargadas y establece conexión con sus carpetas en Extractor_de_datos.
    """
    # Obtener la ruta del archivo actual
    blend_file_path = bpy.data.filepath
    if not blend_file_path:
        return {"status": "error", "message": "Archivo no guardado"}

    # Obtener el nombre del archivo sin extensión
    blend_file_name = os.path.basename(blend_file_path)
    entity_name = os.path.splitext(blend_file_name)[0]

    # Detectar entidades cargadas basadas en armatures y collections
    loaded_entities = []

    # Buscar entidades por armatures
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            # Extraer nombre de entidad del nombre del armature
            # Patrones comunes: "Armature_Chicken", "Chicken_Armature", "Chicken_Rig", etc.
            armature_name = obj.name.lower()
            entity_match = None

            # Buscar patrones comunes de nombres de entidades
            entity_patterns = [
                r'armature[_\s]*(.*)',  # Armature_Chicken
                r'(.*)[_\s]*armature',  # Chicken_Armature
                r'(.*)[_\s]*rig',       # Chicken_Rig
                r'rig[_\s]*(.*)',       # Rig_Chicken
            ]

            for pattern in entity_patterns:
                match = re.search(pattern, armature_name)
                if match:
                    entity_match = match.group(1).strip()
                    break

            # Si no se encontró un patrón, usar el nombre completo
            if not entity_match:
                entity_match = armature_name

            # Verificar si ya existe esta entidad en la lista
            if entity_match and not any(e.get('name', '').lower() == entity_match for e in loaded_entities):
                loaded_entities.append({
                    "name": entity_match,
                    "source": "armature",
                    "armature_name": obj.name,
                    "bone_count": len(obj.data.bones) if obj.data else 0
                })

    # Buscar entidades por nombres de collections
    for collection in bpy.data.collections:
        collection_name = collection.name.lower()
        # Ignorar collections comunes que no son entidades
        if any(x in collection_name for x in ['camera', 'light', 'lamp', 'scene', 'world', 'environment']):
            continue

        # Verificar si ya existe esta entidad en la lista
        if not any(e.get('name', '').lower() == collection_name for e in loaded_entities):
            loaded_entities.append({
                "name": collection_name,
                "source": "collection",
                "collection_name": collection.name,
                "object_count": len(collection.objects)
            })

    # Buscar la carpeta Extractor_de_datos
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    extractor_dir = os.path.join(project_dir, "Extractor_de_datos")

    # Verificar si existe la carpeta
    extractor_exists = os.path.exists(extractor_dir) and os.path.isdir(extractor_dir)

    # Conectar entidades con sus carpetas en Extractor_de_datos
    if extractor_exists:
        for entity in loaded_entities:
            entity_name = entity.get('name', '').lower()
            # Buscar carpetas de entidad en Extractor_de_datos
            entity_folders = []

            # Listar directorios en Extractor_de_datos
            for item in os.listdir(extractor_dir):
                item_path = os.path.join(extractor_dir, item)
                if os.path.isdir(item_path):
                    # Verificar si el nombre de la carpeta contiene el nombre de la entidad
                    if entity_name in item.lower():
                        entity_folders.append({
                            "folder_name": item,
                            "path": item_path,
                            "files": [f for f in os.listdir(item_path) if os.path.isfile(os.path.join(item_path, f))]
                        })

            # Agregar información de carpetas encontradas
            entity["extractor_folders"] = entity_folders

    # Construir el contexto del sistema
    context_info = {
        "loaded_entities": loaded_entities,
        "extractor_data_path": extractor_dir if extractor_exists else None,
        "extractor_data_exists": extractor_exists,
        "current_file": blend_file_path,
        "current_entity": entity_name
    }

    return context_info

def extract_complete_outliner():
    """Extrae jerarquía COMPLETA del Outliner - VERSIÓN ULTRA COMPLETA CON CONTEXTO IA"""

    # Información detallada de todas las collections
    all_collections_detailed = {}
    for collection in bpy.data.collections:
        coll_info = {
            'name': collection.name,
            'objects_count': len(collection.objects),
            'children_count': len(collection.children),
            'hide_viewport': collection.hide_viewport,
            'hide_render': collection.hide_render,
            'all_objects': [obj.name for obj in collection.all_objects],
            'children_names': [child.name for child in collection.children],
            'users': collection.users,  # Número de escenas que usan esta collection
            'is_master_collection': collection == bpy.context.scene.collection
        }
        all_collections_detailed[collection.name] = coll_info

    # NUEVO: Extraer información del contexto del sistema Multi-Entidad
    context_info = extract_system_context()

    hierarchy = {
        'timestamp': datetime.now().isoformat(),
        'blender_version': bpy.app.version_string,
        'file_path': bpy.data.filepath or 'Unsaved',
        'file_name': os.path.basename(bpy.data.filepath) if bpy.data.filepath else 'Unsaved',
        'current_scene': bpy.context.scene.name,

        # NUEVO: Información del contexto del sistema (carpeta cargada + estructuras)
        'system_context': context_info,

        # Jerarquía completa
        'collections': extract_all_collections(),

        # TODAS las collections con información detallada
        'all_collections_detailed': all_collections_detailed,

        # Análisis de relaciones
        'relationships': analyze_all_relationships(),

        # Información de escenas
        'scenes_info': {
            'total_scenes': len(bpy.data.scenes),
            'current_scene': bpy.context.scene.name,
            'all_scenes': [{
                'name': scene.name,
                'is_active': scene == bpy.context.scene,
                'objects_count': len(scene.objects),
                'frame_start': scene.frame_start,
                'frame_end': scene.frame_end,
                'fps': scene.render.fps,
                'resolution_x': scene.render.resolution_x,
                'resolution_y': scene.render.resolution_y
            } for scene in bpy.data.scenes]
        },

        # Información de datos globales
        'global_data': {
            'total_materials': len(bpy.data.materials),
            'total_textures': len(bpy.data.textures),
            'total_images': len(bpy.data.images),
            'total_worlds': len(bpy.data.worlds),
            'total_fonts': len(bpy.data.fonts),
            'total_curves': len(bpy.data.curves),
            'total_metaballs': len(bpy.data.metaballs),
            'total_lattices': len(bpy.data.lattices),
            'total_masks': len(bpy.data.masks),
            'total_movieclips': len(bpy.data.movieclips),
            'total_sounds': len(bpy.data.sounds),
            'total_speakers': len(bpy.data.speakers),
            'total_texts': len(bpy.data.texts),
            'total_hair_curves': len(bpy.data.hair_curves),
            'total_pointclouds': len(bpy.data.pointclouds),
            'total_volumes': len(bpy.data.volumes)
        },

        # Estadísticas globales expandidas
        'statistics': {
            'total_collections': len(bpy.data.collections),
            'total_objects': len(bpy.data.objects),
            'total_meshes': len([o for o in bpy.data.objects if o.type == 'MESH']),
            'total_armatures': len([o for o in bpy.data.objects if o.type == 'ARMATURE']),
            'total_empties': len([o for o in bpy.data.objects if o.type == 'EMPTY']),
            'total_cameras': len([o for o in bpy.data.objects if o.type == 'CAMERA']),
            'total_lights': len([o for o in bpy.data.objects if o.type == 'LIGHT']),
            'total_curves': len([o for o in bpy.data.objects if o.type == 'CURVE']),
            'total_surfaces': len([o for o in bpy.data.objects if o.type == 'SURFACE']),
            'total_metaballs': len([o for o in bpy.data.objects if o.type == 'META']),
            'total_text_objects': len([o for o in bpy.data.objects if o.type == 'FONT']),
            'total_speakers': len([o for o in bpy.data.objects if o.type == 'SPEAKER']),
            'total_lattices': len([o for o in bpy.data.objects if o.type == 'LATTICE']),
            'total_grease_pencils': len([o for o in bpy.data.objects if o.type == 'GPENCIL']),
            'total_volumes': len([o for o in bpy.data.objects if o.type == 'VOLUME']),
            'total_lightprobes': len([o for o in bpy.data.objects if o.type == 'LIGHT_PROBE']),

            # Información adicional
            'objects_by_collection': {coll.name: len(coll.objects) for coll in bpy.data.collections},
            'collections_hierarchy': {coll.name: [child.name for child in coll.children] for coll in bpy.data.collections},
            'orphan_collections': [coll.name for coll in bpy.data.collections if coll.users == 0],
            'master_collections': [coll.name for coll in bpy.data.collections if coll == bpy.context.scene.collection]
        }
    }

    return hierarchy

def extract_system_context():
    """Extrae información del contexto del sistema Multi-Entidad para la IA"""
    context = {
        'loaded_prompt': None,
        'loaded_structures': {},
        'system_info': {
            'addon_version': '2.1.1',
            'system_type': 'Multi-Entity Animation Blocks Manager',
            'extraction_type': 'Proyecto Independent'
        }
    }

    try:
        # PRIMERO: Intentar acceder al manager del sistema Multi-Entidad para obtener el prompt ACTUALMENTE CARGADO
        # Esto es más preciso que la detección automática por fecha de modificación
        manager = None
        try:
            # Intentar importar y acceder al manager global
            # Primero intentar importación directa
            try:
                from simple_animation_blocks_manager import get_blocks_manager
            except ImportError:
                # Si falla, intentar con path relativo
                script_dir = os.path.dirname(os.path.abspath(__file__))
                if script_dir not in sys.path:
                    sys.path.append(script_dir)
                from simple_animation_blocks_manager import get_blocks_manager

            manager = get_blocks_manager()
            print(f"✅ Manager obtenido: {manager}")
        except Exception as e:
            print(f"⚠️ No se pudo importar manager: {e}")
            # Intentar acceder al manager desde bpy.context si existe
            try:
                if hasattr(bpy.context, 'scene') and hasattr(bpy.context.scene, 'multi_entity_manager'):
                    manager = bpy.context.scene.multi_entity_manager
                    print(f"✅ Manager obtenido desde bpy.context: {manager}")
            except:
                pass

        if manager:
            # Obtener prompt actual del manager
            if hasattr(manager, 'current_prompt_folder') and manager.current_prompt_folder:
                prompt_path = manager.current_prompt_folder
                if os.path.exists(prompt_path):
                    folder_name = os.path.basename(prompt_path)
                    context['loaded_prompt'] = {
                        'folder_name': folder_name,
                        'full_path': prompt_path,
                        'folder_type': 'Prompt_X',
                        'has_metadata': os.path.exists(os.path.join(prompt_path, 'metadata.json')),
                        'last_modified': os.path.getmtime(prompt_path),
                        'source': 'manager_current_loaded'  # Indicar que viene del manager actual
                    }
                    print(f"✅ PROMPT DETECTADO DESDE MANAGER: {folder_name}")

            # Extraer información de entidades cargadas desde el manager
            if hasattr(manager, 'entities') and manager.entities:
                print(f"📦 Manager tiene {len(manager.entities)} entidades")
                for entity_name, entity_data in manager.entities.items():
                    print(f"  🔍 Procesando entidad: {entity_name}")

                    # Obtener información del blend_file
                    blend_file = entity_data.get('blend_file', '')
                    if not blend_file:
                        # Intentar con suggested_blend_file
                        blend_file = entity_data.get('suggested_blend_file', '')

                    # Si no hay blend_file específico, intentar encontrar automáticamente
                    if not blend_file:
                        blend_file = find_blend_file_with_translation(entity_name) or f'{entity_name}.blend'

                    # Construir path completo si es relativo
                    blend_path = blend_file
                    if blend_file and not os.path.isabs(blend_file):
                        # Buscar en estructura_lista
                        estructura_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'estructura_lista', blend_file)
                        if os.path.exists(estructura_path):
                            blend_path = estructura_path
                        else:
                            # Buscar con traducción
                            translated_blend = find_blend_file_with_translation(entity_name)
                            if translated_blend:
                                blend_path = translated_blend

                    context['loaded_structures'][entity_name] = {
                        'blend_file': os.path.basename(blend_file) if blend_file else f'{entity_name}.blend',
                        'blend_path': blend_path,
                        'is_loaded': entity_data.get('is_loaded', False),
                        'assigned_slots': entity_data.get('assigned_slots', []),
                        'description': entity_data.get('description', ''),
                        'entity_type': entity_data.get('type', 'unknown'),
                        'translation_used': entity_data.get('translation_used', ''),
                        'data_folder_project_path': os.path.join(os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'Extractor_de_datos', entity_name),
                        'data_folder_full_path': os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Extractor_de_datos', entity_name),
                        'data_folder_exists': os.path.isdir(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Extractor_de_datos', entity_name))
                    }
                    print(f"    ✅ {entity_name}: {os.path.basename(blend_path) if blend_path else 'no encontrado'}")
            else:
                print("⚠️ Manager no tiene entidades o no está inicializado")
        else:
            print("⚠️ No se pudo acceder al manager del sistema Multi-Entidad")

        # Si no se pudo obtener del manager, intentar acceder a propiedades de escena
        if not context['loaded_structures'] and hasattr(bpy.context, 'scene') and hasattr(bpy.context.scene, 'multi_entity_entities'):
            print("🔄 Fallback: Usando propiedades de escena")
            entities = bpy.context.scene.multi_entity_entities
            for entity_item in entities:
                entity_name = entity_item.entity_name
                if entity_name:
                    context['loaded_structures'][entity_name] = {
                        'blend_file': entity_item.blend_file or f'{entity_name}.blend',
                        'blend_path': entity_item.blend_file or f'estructura_lista/{entity_name}.blend',
                        'is_loaded': entity_item.is_loaded,
                        'assigned_slots': entity_item.assigned_slots,
                        'description': entity_item.description,
                        'data_folder_project_path': os.path.join('Extractor_de_datos', entity_name),
                        'data_folder_full_path': os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Extractor_de_datos', entity_name),
                        'data_folder_exists': os.path.isdir(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Extractor_de_datos', entity_name))
                    }

        # SEGUNDO: Si no se pudo obtener del manager O no está disponible, usar detección automática por fecha de modificación
        # (este es el método principal cuando el addon no está cargado en la interfaz)
        if not context['loaded_prompt']:
            # Obtener directorio del proyecto desde el archivo actual
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_dir = os.path.dirname(script_dir)  # Subir un nivel desde Proyecto/
            animacion_dir = os.path.join(project_dir, 'animacion')

            if os.path.exists(animacion_dir):
                # Buscar todas las carpetas Prompt_XXX y ordenar por fecha de modificación
                prompt_folders = []
                for item in os.listdir(animacion_dir):
                    item_path = os.path.join(animacion_dir, item)
                    if os.path.isdir(item_path) and item.startswith('Prompt_'):
                        # Verificar si tiene metadata.json
                        metadata_path = os.path.join(item_path, 'metadata.json')
                        if os.path.exists(metadata_path):
                            # Obtener tiempo de modificación
                            mod_time = os.path.getmtime(item_path)
                            prompt_folders.append((item, item_path, mod_time))

                # Ordenar por tiempo de modificación (más reciente primero)
                prompt_folders.sort(key=lambda x: x[2], reverse=True)

                # Tomar la carpeta más reciente como la actual
                if prompt_folders:
                    folder_name, folder_path, mod_time = prompt_folders[0]
                    context['loaded_prompt'] = {
                        'folder_name': folder_name,
                        'full_path': folder_path,
                        'folder_type': 'Prompt_X',
                        'has_metadata': True,
                        'last_modified': mod_time,
                        'source': 'automatic_detection'  # Indicar que es detección automática
                    }
                    print(f"✅ PROMPT DETECTADO POR FECHA (automático): {folder_name}")

                    # Cargar metadata para obtener información de entidades
                    try:
                        metadata_path = os.path.join(folder_path, 'metadata.json')
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)

                        # Crear estructuras desde metadata
                        if 'entidades' in metadata:
                            entities_config = metadata['entidades']
                            for entity_name, entity_config in entities_config.items():
                                # Buscar archivo blend automáticamente
                                blend_file = find_blend_file_with_translation(entity_name)
                                blend_path = blend_file if blend_file else None

                                context['loaded_structures'][entity_name] = {
                                    'blend_file': os.path.basename(blend_file) if blend_file else f'{entity_name}.blend',
                                    'blend_path': blend_path,
                                    'is_loaded': False,  # En modo background, asumimos no cargado
                                    'assigned_slots': entity_config.get('slots_asignados', []),
                                    'description': entity_config.get('descripcion', ''),
                                    'entity_type': entity_config.get('tipo', 'unknown'),
                                    'translation_used': translate_entity_name(entity_name),
                                    'data_folder_project_path': os.path.join(os.path.basename(project_dir), 'Extractor_de_datos', entity_name),
                                    'data_folder_full_path': os.path.join(project_dir, 'Extractor_de_datos', entity_name),
                                    'data_folder_exists': os.path.isdir(os.path.join(project_dir, 'Extractor_de_datos', entity_name))
                                }
                                print(f"    📦 Entidad desde metadata: {entity_name} ({entity_config.get('tipo', 'unknown')})")
                    except Exception as metadata_e:
                        print(f"⚠️ Error cargando metadata: {metadata_e}")

        # Si no hay prompt detectado, marcar como desconocido
        if not context['loaded_prompt']:
            context['loaded_prompt'] = {
                'folder_name': 'unknown',
                'full_path': 'unknown',
                'folder_type': 'none_detected',
                'note': 'No se pudo detectar carpeta Prompt_X cargada'
            }

        # Analizar partes disponibles por entidad (si hay entidades cargadas)
        for entity_name, entity_info in context['loaded_structures'].items():
            if entity_info.get('is_loaded'):
                # Detectar dinámicamente las partes disponibles analizando objetos en escena
                available_parts = []
                expected_parts = []

                # Buscar todos los objetos mesh que pertenecen a esta entidad
                entity_objects = [obj for obj in bpy.data.objects
                                if obj.type == 'MESH' and entity_name.lower() in obj.name.lower()]

                # Extraer nombres de partes de los objetos encontrados
                for obj in entity_objects:
                    obj_name_lower = obj.name.lower()
                    # Remover el nombre de la entidad para obtener el nombre de la parte
                    part_name = obj_name_lower.replace(entity_name.lower(), '').strip()
                    # Limpiar prefijos comunes
                    part_name = part_name.lstrip('._- ')
                    if part_name and part_name not in expected_parts:
                        expected_parts.append(part_name)

                # Si aún no hay partes, agregar las encontradas directamente
                if not expected_parts:
                    for obj in entity_objects[:5]:  # Limitar a primeras 5 para evitar spam
                        part_name = obj.name.lower().replace(entity_name.lower(), '').strip('._- ')
                        if part_name:
                            expected_parts.append(part_name)

                # Verificar qué partes están disponibles
                for part in expected_parts:
                    found = any(part.lower() in obj.name.lower() for obj in entity_objects)
                    if found:
                        available_parts.append(part)
                    else:
                        # Buscar con matching más flexible
                        found_flexible = any(part.lower() in obj.name.lower() for obj in bpy.data.objects)
                        if found_flexible:
                            available_parts.append(part)

                # Calcular partes faltantes (solo si tenemos partes esperadas)
                missing_parts = []
                if expected_parts:
                    for part in expected_parts:
                        if part not in available_parts:
                            missing_parts.append(part)

                entity_info['available_parts'] = available_parts
                entity_info['missing_parts'] = missing_parts
                entity_info['expected_parts'] = expected_parts

                # Contar objetos totales de esta entidad
                entity_objects = [obj for obj in bpy.data.objects if entity_name.lower() in obj.name.lower()]
                entity_info['total_objects'] = len(entity_objects)

                # Buscar armature principal
                armatures = [obj for obj in entity_objects if obj.type == 'ARMATURE']
                if armatures:
                    entity_info['armature_name'] = armatures[0].name
                    entity_info['bone_count'] = len(armatures[0].data.bones) if armatures[0].data else 0

                    # Resolver carpeta de datos en Extractor_de_datos de forma robusta
                    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    data_root = os.path.join(project_root, 'Extractor_de_datos')
                    root_name = os.path.basename(project_root)

                    # Candidatos: nombre de entidad y nombre base del .blend asociado
                    entity_base_from_blend = os.path.splitext(os.path.basename(entity_info.get('blend_file', '')))[0]
                    candidates = []
                    for cand in [entity_name, entity_base_from_blend]:
                        if cand:
                            candidates.append(cand.lower())

                    matched_folder = None
                    if os.path.isdir(data_root):
                        for cand in candidates:
                            path_candidate = os.path.join(data_root, cand)
                            if os.path.isdir(path_candidate):
                                matched_folder = cand
                                break

                        # Fallback: búsqueda por coincidencia parcial en subcarpetas
                        if not matched_folder:
                            try:
                                for name in os.listdir(data_root):
                                    if os.path.isdir(os.path.join(data_root, name)) and (
                                         name.lower() == entity_name.lower() or (
                                             entity_base_from_blend and entity_base_from_blend.lower() in name.lower()
                                         )
                                     ):
                                         matched_folder = name
                                         break
                            except Exception:
                                pass

                    if matched_folder:
                        rel_project_path = os.path.join(root_name, 'Extractor_de_datos', matched_folder)
                        abs_path = os.path.join(data_root, matched_folder)
                        entity_info['data_folder_project_path'] = rel_project_path
                        entity_info['data_folder_full_path'] = abs_path
                        entity_info['data_folder_exists'] = True
                    else:
                        entity_info['data_folder_project_path'] = os.path.join(root_name, 'Extractor_de_datos', entity_name)
                        entity_info['data_folder_full_path'] = os.path.join(data_root, entity_name)
                        entity_info['data_folder_exists'] = os.path.isdir(entity_info['data_folder_full_path'])

    except Exception as e:
        # Si hay error accediendo al contexto, marcar como no disponible
        context['system_context_error'] = str(e)
        context['note'] = 'Información del sistema Multi-Entidad no disponible en este contexto'

    return context

def get_expected_parts_for_entity(entity_name):
    """
    DEPRECATED: Esta función ya no se usa.
    Las partes esperadas ahora se detectan dinámicamente de los objetos en escena.
    Se mantiene por compatibilidad pero retorna lista vacía.
    """
    return []

def save_outliner_data():
    """Guarda los datos completos del Outliner en JSON"""
    # Para el flujo independiente del Proyecto, guardar siempre en la carpeta Proyecto
    script_dir = os.path.dirname(os.path.abspath(__file__))
    proyecto_dir = os.path.dirname(script_dir) if os.path.basename(script_dir) == 'Proyecto' else script_dir

    # Si estamos en Proyecto, usar esa carpeta
    if os.path.basename(proyecto_dir) == 'Proyecto':
        output_dir = proyecto_dir
    else:
        # Fallback al directorio del script
        output_dir = script_dir

    output_file = os.path.join(output_dir, 'outliner_data.json')

    data = extract_complete_outliner()

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*100}")
    print(f"✅ DATOS COMPLETOS GUARDADOS EN: {output_file}")
    print(f"{'='*100}")
    print(f"📁 Archivo: {data['file_name']}")
    print(f"🎬 Escena actual: {data['current_scene']}")
    print(f"📊 Collections totales: {data['statistics']['total_collections']}")
    print(f"📦 Objetos totales: {data['statistics']['total_objects']}")
    print(f"🦴 Armatures: {data['statistics']['total_armatures']}")
    print(f"🔷 Meshes: {data['statistics']['total_meshes']}")
    print(f"🕐 Timestamp: {data['timestamp']}")

    # NUEVO: Mostrar información del contexto del sistema
    if 'system_context' in data:
        context = data['system_context']
        print(f"\n{'='*100}")
        print(f"📊 INFORMACIÓN DEL CONTEXTO DEL SISTEMA MULTI-ENTIDAD")
        print(f"{'='*100}")
        
        # Mostrar entidades cargadas
        if 'loaded_entities' in context and context['loaded_entities']:
            print(f"🔍 Entidades detectadas: {len(context['loaded_entities'])}")
            for i, entity in enumerate(context['loaded_entities'], 1):
                print(f"  {i}. {entity.get('name', 'Desconocido')} ({entity.get('source', 'desconocido')})")
                
                # Mostrar conexión con Extractor_de_datos
                if 'extractor_folders' in entity and entity['extractor_folders']:
                    print(f"     ✅ Conectado a Extractor_de_datos: {len(entity['extractor_folders'])} carpeta(s)")
                    for folder in entity['extractor_folders']:
                        print(f"        - {folder.get('folder_name', 'Desconocido')} ({len(folder.get('files', []))} archivos)")
                else:
                    print(f"     ❌ No se encontró carpeta en Extractor_de_datos")
        else:
            print(f"❌ No se detectaron entidades en el archivo")
            
        # Mostrar información de la carpeta Extractor_de_datos
        if context.get('extractor_data_exists'):
            print(f"\n✅ Carpeta Extractor_de_datos encontrada: {context.get('extractor_data_path', 'Desconocido')}")
        else:
            print(f"\n❌ No se encontró la carpeta Extractor_de_datos")
            
        print(f"{'='*100}")
        
    # Si no hay información del contexto del sistema
    else:
        print(f"\n❌ No se pudo extraer información del contexto del sistema")
        
    print(f"{'='*100}\n")

    print(f"{'='*100}\n")

    return output_file

def print_complete_summary():
    """Imprime resumen visual ULTRA COMPLETO del Outliner"""

    data = extract_complete_outliner()

    print("\n" + "="*120)
    print("📋 ANÁLISIS ULTRA COMPLETO DEL OUTLINER - VERSIÓN MAXIMA")
    print("="*120)
    print(f"📁 Archivo: {data['file_name']}")
    print(f"📂 Ruta: {data['file_path']}")
    print(f"🎬 Escena activa: {data['current_scene']}")
    print(f"🔧 Blender: {data['blender_version']}")
    print(f"🕐 Extraído: {data['timestamp']}")

    print("\n" + "-"*120)
    print("📊 ESTADÍSTICAS ULTRA COMPLETAS")
    print("-"*120)
    stats = data['statistics']
    global_data = data['global_data']
    scenes_info = data['scenes_info']

    print(f"📂 Collections: {stats['total_collections']}")
    print(f"📦 Objetos totales: {stats['total_objects']}")
    print(f"🦴 Armatures: {stats['total_armatures']}")
    print(f"🔷 Meshes: {stats['total_meshes']}")
    print(f"🎯 Empties: {stats['total_empties']}")
    print(f"📷 Cámaras: {stats['total_cameras']}")
    print(f"💡 Luces: {stats['total_lights']}")
    print(f"〰️ Curves: {stats['total_curves']}")
    print(f"🌐 Surfaces: {stats['total_surfaces']}")
    print(f"⚫ Metaballs: {stats['total_metaballs']}")
    print(f"📝 Text Objects: {stats['total_text_objects']}")
    print(f"🔊 Speakers: {stats['total_speakers']}")
    print(f"🔗 Lattices: {stats['total_lattices']}")
    print(f"✏️ Grease Pencils: {stats['total_grease_pencils']}")
    print(f"📦 Volumes: {stats['total_volumes']}")
    print(f"💡 Light Probes: {stats['total_lightprobes']}")

    print(f"\n🎨 Materiales: {global_data['total_materials']}")
    print(f"🖼️ Texturas: {global_data['total_textures']}")
    print(f"🖼️ Imágenes: {global_data['total_images']}")
    print(f"🌍 Mundos: {global_data['total_worlds']}")
    print(f"🔤 Fuentes: {global_data['total_fonts']}")
    print(f"🎬 Clips de video: {global_data['total_movieclips']}")
    print(f"🔊 Sonidos: {global_data['total_sounds']}")

    print(f"\n🎭 Escenas totales: {scenes_info['total_scenes']}")
    print(f"📊 Máscaras: {global_data['total_masks']}")
    print(f"💇 Curvas de cabello: {global_data['total_hair_curves']}")
    print(f"☁️ Nubes de puntos: {global_data['total_pointclouds']}")
    print(f"📄 Textos: {global_data['total_texts']}")
    
    def print_collection_tree(coll, indent=0):
        """Imprime árbol de collections recursivamente"""
        prefix = "  " * indent
        icon = "📁" if coll['type'] == 'COLLECTION' else "📦"
        obj_count = len(coll.get('objects', []))
        child_count = len(coll.get('children', []))
        
        visibility = "👁️" if not coll.get('hide_viewport', False) else "🙈"
        
        print(f"{prefix}{icon} {visibility} {coll['name']} ({obj_count} objs, {child_count} subcols)")
        
        # Objetos en esta collection
        for obj in coll.get('objects', []):
            obj_prefix = "  " * (indent + 1)
            obj_icon = {"ARMATURE": "🦴", "MESH": "🔷", "EMPTY": "🎯", 
                       "CAMERA": "📷", "LIGHT": "💡", "CURVE": "〰️"}.get(obj['type'], "📦")
            obj_vis = "👁️" if obj['visible'] else "🙈"
            
            extra = ""
            if obj['type'] == 'ARMATURE':
                extra = f" [{obj.get('bones_count', 0)} bones]"
            elif obj['type'] == 'MESH':
                extra = f" [{obj.get('vertices', 0)} verts]"
                if 'armature_link' in obj:
                    extra += f" → 🦴{obj['armature_link']}"
            
            print(f"{obj_prefix}{obj_icon} {obj_vis} {obj['name']}{extra}")
        
        # Sub-collections recursivamente
        for child in coll.get('children', []):
            print_collection_tree(child, indent + 1)
    
    print("\n" + "-"*100)
    print("🌳 JERARQUÍA DE COLLECTIONS")
    print("-"*100)
    
    collections = data['collections']
    
    # Scene Collection
    if 'scene_collection' in collections:
        print(f"\n🎬 SCENE COLLECTION ({data['current_scene']}):")
        print_collection_tree(collections['scene_collection'])
    
    # Orphan Collections
    if 'orphan_collections' in collections:
        print(f"\n⚠️ COLLECTIONS HUÉRFANAS (no vinculadas a escena principal): {len(collections['orphan_collections'])}")
        for orphan in collections['orphan_collections']:
            print_collection_tree(orphan)
    
    # Información detallada de collections
    print("\n" + "-"*120)
    print("📂 INFORMACIÓN DETALLADA DE COLLECTIONS")
    print("-"*120)
    all_collections_detailed = data.get('all_collections_detailed', {})
    for coll_name, coll_info in all_collections_detailed.items():
        status = "👑 MASTER" if coll_info.get('is_master_collection') else "🧪 ORPHAN" if coll_info.get('users', 0) == 0 else "✅ ACTIVE"
        visibility = "👁️ VISIBLE" if not coll_info.get('hide_viewport') else "🙈 HIDDEN"
        print(f"  📁 {coll_name}: {status} | {visibility} | {coll_info['objects_count']} objs | {coll_info['children_count']} children | Users: {coll_info.get('users', 0)}")

    # Todas las escenas
    if 'all_scenes' in collections and len(collections['all_scenes']) > 1:
        print(f"\n🎭 OTRAS ESCENAS DISPONIBLES:")
        for scene in collections['all_scenes']:
            if not scene['is_current']:
                print(f"  🎬 {scene['name']} (frames: {scene['frame_start']}-{scene['frame_end']}, {scene['resolution_x']}x{scene['resolution_y']})")

    # Relaciones expandidas
    print("\n" + "-"*120)
    print("🔗 RELACIONES COMPLETAS")
    print("-"*120)
    relationships = data['relationships']

    # Mesh to Armature
    if relationships['mesh_to_armature']:
        print("🔷 MESH → ARMATURE:")
        for rel in relationships['mesh_to_armature']:
            print(f"  🔷 {rel['mesh']} → 🦴 {rel['armature']}")
    else:
        print("🔷 MESH → ARMATURE: No hay relaciones")

    # Parent-Child
    if relationships['parent_child']:
        print("\n👨‍👩‍👧‍👦 PARENT-CHILD RELATIONSHIPS:")
        for rel in relationships['parent_child']:
            print(f"  {rel['child']} ({rel['child_type']}) → {rel['parent']} ({rel['parent_type']})")

    # Collections hierarchy
    print("\n🌳 COLLECTIONS HIERARCHY:")
    coll_hierarchy = stats.get('collections_hierarchy', {})
    for parent, children in coll_hierarchy.items():
        if children:
            print(f"  📁 {parent} → {', '.join(children)}")

    # Orphan collections
    orphan_cols = stats.get('orphan_collections', [])
    if orphan_cols:
        print(f"\n⚠️ COLLECTIONS HUÉRFANAS: {', '.join(orphan_cols)}")

    print("\n" + "="*120)
    print("✅ ANÁLISIS ULTRA COMPLETO FINALIZADO")
    print("="*120 + "\n")

if __name__ == "__main__":
    import sys

    # Si se pasa un archivo como argumento, abrirlo primero
    if len(sys.argv) > 1:
        blend_file = sys.argv[1]
        print(f"\n🔍 ANALIZANDO ARCHIVO: {blend_file}")

        # Verificar que no sea un argumento de Blender
        if not blend_file.startswith('--'):
            # Abrir el archivo .blend
            bpy.ops.wm.open_mainfile(filepath=blend_file)
            print(f"✅ Archivo {os.path.basename(blend_file)} abierto correctamente")
        else:
            print(f"⚠️ Ignorando argumento de Blender: {blend_file}")

    print("\n🔍 EJECUTANDO EXTRACCIÓN UNIVERSAL DEL OUTLINER...")
    save_outliner_data()
    print_complete_summary()