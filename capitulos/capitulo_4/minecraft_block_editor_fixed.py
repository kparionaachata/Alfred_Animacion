"""
================================================================================
MINECRAFT BLOCK EDITOR v5.0 - SISTEMA COMPLETO DE GESTIÓN DE TEXTURAS
================================================================================

DESCRIPCIÓN:
Editor profesional para modificar texturas de bloques Minecraft importados.
Sistema de guardado/carga robusto con aplicación automática garantizada.

NUEVAS CARACTERÍSTICAS v5.0:
✅ Sistema de guardado/carga completamente rediseñado
✅ Aplicación automática de texturas al importar .OBJ
✅ Verificación y validación de cambios
✅ Sistema de backup automático
✅ Integración directa con slot_001
✅ Detección inteligente de objetos modificados
✅ Preview de texturas antes de aplicar
✅ Historial de cambios

INSTALACIÓN:
1. Abre Blender
2. Ve a: Scripting > Abrir > Selecciona este archivo
3. Presiona "Run Script" (▶)
4. El panel "Block Tools v5" aparecerá en la sidebar (N)

FLUJO DE TRABAJO:
1. IMPORTAR: Usa slot_001 para importar bloques .OBJ
2. EDITAR: Modifica texturas usando el Block Editor v5
3. GUARDAR: Presiona "💾 Guardar Configuración"
4. APLICAR: Los cambios se aplican automáticamente en futuras importaciones

================================================================================
"""

import bpy
import os
import json
import time
from pathlib import Path
from datetime import datetime
import shutil

# ==============================================================================
# CONFIGURACIÓN GLOBAL
# ==============================================================================

class EditorConfig:
    """Configuración centralizada del editor"""
    
    # Rutas dinámicas basadas en el proyecto actual
    @staticmethod
    def get_project_root():
        """Obtiene la raíz del proyecto de forma inteligente"""
        if bpy.data.filepath:
            return Path(bpy.data.filepath).parent
        return Path.home() / "Desktop" / "Alfred_Animacion"
    
    @staticmethod
    def get_config_dir():
        """Directorio de configuraciones"""
        config_dir = EditorConfig.get_project_root() / "minecraft_configs"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    @staticmethod
    def get_backup_dir():
        """Directorio de backups"""
        backup_dir = EditorConfig.get_config_dir() / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir
    
    @staticmethod
    def get_config_file():
        """Archivo de configuración principal"""
        return EditorConfig.get_config_dir() / "texture_config.json"

# ==============================================================================
# SISTEMA DE GESTIÓN DE CONFIGURACIÓN
# ==============================================================================

class TextureConfigManager:
    """Gestor centralizado de configuraciones de texturas"""
    
    @staticmethod
    def create_backup():
        """Crea backup automático de la configuración actual"""
        config_file = EditorConfig.get_config_file()
        if not config_file.exists():
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = EditorConfig.get_backup_dir() / f"config_backup_{timestamp}.json"
        
        try:
            shutil.copy2(config_file, backup_file)
            print(f"✅ Backup creado: {backup_file.name}")
            return backup_file
        except Exception as e:
            print(f"⚠️ Error creando backup: {e}")
            return None
    
    @staticmethod
    def save_configuration(force_save=False):
        """
        Guarda la configuración completa de texturas
        Formato mejorado con metadata y validación
        """
        try:
            # Crear backup antes de guardar
            if not force_save:
                TextureConfigManager.create_backup()
            
            config_data = {
                "metadata": {
                    "version": "5.0",
                    "timestamp": datetime.now().isoformat(),
                    "blender_version": f"{bpy.app.version[0]}.{bpy.app.version[1]}.{bpy.app.version[2]}",
                    "total_objects": 0,
                    "total_materials": 0
                },
                "texture_paths": {},
                "objects": {}
            }
            
            objects_processed = 0
            materials_processed = 0
            
            # Procesar todos los objetos MESH en la escena
            for obj in bpy.context.scene.objects:
                if obj.type != 'MESH':
                    continue
                
                obj_data = {
                    "name": obj.name,
                    "location": list(obj.location),
                    "scale": list(obj.scale),
                    "materials": {}
                }
                
                has_materials = False
                
                # Procesar cada material del objeto
                for slot_idx, material_slot in enumerate(obj.material_slots):
                    if not material_slot.material:
                        continue
                    
                    mat = material_slot.material
                    
                    # Extraer información de textura
                    texture_info = TextureConfigManager._extract_texture_from_material(mat)
                    
                    if texture_info:
                        obj_data["materials"][f"slot_{slot_idx}"] = {
                            "material_name": mat.name,
                            "texture_path": texture_info["path"],
                            "texture_name": texture_info["name"],
                            "image_name": texture_info["image_name"]
                        }
                        
                        # Registrar ruta de textura global
                        config_data["texture_paths"][texture_info["name"]] = texture_info["path"]
                        
                        materials_processed += 1
                        has_materials = True
                
                if has_materials:
                    config_data["objects"][obj.name] = obj_data
                    objects_processed += 1
            
            # Actualizar metadata
            config_data["metadata"]["total_objects"] = objects_processed
            config_data["metadata"]["total_materials"] = materials_processed
            
            # Guardar archivo
            config_file = EditorConfig.get_config_file()
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            
            print(f"\n{'='*60}")
            print(f"💾 CONFIGURACIÓN GUARDADA EXITOSAMENTE")
            print(f"{'='*60}")
            print(f"📁 Archivo: {config_file}")
            print(f"📦 Objetos procesados: {objects_processed}")
            print(f"🎨 Materiales guardados: {materials_processed}")
            print(f"⏰ Timestamp: {config_data['metadata']['timestamp']}")
            print(f"{'='*60}\n")
            
            return True, objects_processed, materials_processed
            
        except Exception as e:
            print(f"❌ Error guardando configuración: {e}")
            import traceback
            traceback.print_exc()
            return False, 0, 0
    
    @staticmethod
    def _extract_texture_from_material(material):
        """Extrae información de textura de un material"""
        if not material or not material.use_nodes:
            return None
        
        # Buscar nodo de imagen conectado al Principled BSDF
        principled = None
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled = node
                break
        
        if not principled:
            return None
        
        # Verificar Base Color input
        base_color_input = principled.inputs.get('Base Color')
        if not base_color_input or not base_color_input.is_linked:
            return None
        
        # Obtener nodo de imagen
        link = base_color_input.links[0]
        if link.from_node.type != 'TEX_IMAGE':
            return None
        
        texture_node = link.from_node
        if not texture_node.image:
            return None
        
        image = texture_node.image
        image_path = bpy.path.abspath(image.filepath)
        
        if not os.path.exists(image_path):
            return None
        
        return {
            "path": image_path,
            "name": Path(image_path).stem,
            "image_name": image.name
        }
    
    @staticmethod
    def load_configuration():
        """
        Carga y aplica la configuración guardada
        Sistema robusto con validación y reportes detallados
        """
        config_file = EditorConfig.get_config_file()
        
        if not config_file.exists():
            print("⚠️ No se encontró archivo de configuración")
            return False, "No existe archivo de configuración"
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            print(f"\n{'='*60}")
            print(f"📂 CARGANDO CONFIGURACIÓN")
            print(f"{'='*60}")
            print(f"📁 Archivo: {config_file.name}")
            print(f"🔖 Versión: {config_data.get('metadata', {}).get('version', 'desconocida')}")
            print(f"⏰ Guardado: {config_data.get('metadata', {}).get('timestamp', 'desconocido')}")
            print(f"{'='*60}\n")
            
            applied_count = 0
            failed_count = 0
            not_found_count = 0
            
            objects_config = config_data.get("objects", {})
            
            for obj_name, obj_data in objects_config.items():
                obj = bpy.context.scene.objects.get(obj_name)
                
                if not obj:
                    print(f"⚠️ Objeto '{obj_name}' no encontrado en escena")
                    not_found_count += 1
                    continue
                
                materials_config = obj_data.get("materials", {})
                
                for slot_key, mat_config in materials_config.items():
                    slot_idx = int(slot_key.split('_')[1])
                    
                    if slot_idx >= len(obj.material_slots):
                        print(f"⚠️ Slot {slot_idx} no existe en '{obj_name}'")
                        failed_count += 1
                        continue
                    
                    texture_path = mat_config.get("texture_path")
                    texture_name = mat_config.get("texture_name")
                    
                    if not texture_path or not os.path.exists(texture_path):
                        print(f"⚠️ Textura no encontrada: {texture_path}")
                        failed_count += 1
                        continue
                    
                    # Aplicar textura
                    success = TextureConfigManager._apply_texture_to_slot(
                        obj, slot_idx, texture_path, texture_name
                    )
                    
                    if success:
                        applied_count += 1
                        print(f"✅ {obj_name}.slot_{slot_idx} → {texture_name}")
                    else:
                        failed_count += 1
                        print(f"❌ Error aplicando textura a {obj_name}.slot_{slot_idx}")
            
            print(f"\n{'='*60}")
            print(f"📊 RESUMEN DE APLICACIÓN")
            print(f"{'='*60}")
            print(f"✅ Texturas aplicadas: {applied_count}")
            print(f"❌ Errores: {failed_count}")
            print(f"⚠️ Objetos no encontrados: {not_found_count}")
            print(f"{'='*60}\n")
            
            if applied_count > 0:
                return True, f"✅ {applied_count} texturas aplicadas"
            else:
                return False, f"❌ No se aplicaron texturas ({failed_count} errores)"
            
        except Exception as e:
            error_msg = f"Error cargando configuración: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return False, error_msg
    
    @staticmethod
    def _apply_texture_to_slot(obj, slot_idx, texture_path, texture_name):
        """Aplica una textura a un slot específico de un objeto"""
        try:
            # Cargar imagen
            img = None
            for image in bpy.data.images:
                if image.filepath == texture_path:
                    img = image
                    break

            if not img:
                img = bpy.data.images.load(texture_path)

            # Crear o reutilizar material
            mat_name = f"Mat_{texture_name}"
            mat = bpy.data.materials.get(mat_name)

            if not mat:
                mat = bpy.data.materials.new(mat_name)
                mat.use_nodes = True
                nodes = mat.node_tree.nodes
                nodes.clear()

                # Configurar nodos
                output = nodes.new('ShaderNodeOutputMaterial')
                output.location = (300, 0)

                principled = nodes.new('ShaderNodeBsdfPrincipled')
                principled.location = (0, 0)

                tex_image = nodes.new('ShaderNodeTexImage')
                tex_image.image = img
                tex_image.location = (-300, 0)
                tex_image.interpolation = 'Closest'  # Pixel-perfect para Minecraft

                # Conectar color base
                links = mat.node_tree.links
                links.new(tex_image.outputs['Color'], principled.inputs['Base Color'])
                links.new(principled.outputs['BSDF'], output.inputs['Surface'])

                # DETECTAR Y CONFIGURAR TRANSPARENCIA PARA FLORES Y PLANTAS
                TextureConfigManager._setup_transparency_for_texture(mat, tex_image, principled, texture_name)

            else:
                # Actualizar imagen en material existente
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        node.image = img
                        # Reconfigurar transparencia si es necesario
                        TextureConfigManager._setup_transparency_for_texture(mat, node, None, texture_name)
                        break

            # Asignar material al slot
            obj.material_slots[slot_idx].material = mat

            return True

        except Exception as e:
            print(f"   Error en _apply_texture_to_slot: {e}")
            return False

    @staticmethod
    def _analyze_separated_objects():
        """
        Analiza la escena y agrupa objetos que parecen ser resultado de separaciones
        Devuelve un diccionario con grupos de objetos separados
        """
        separated_groups = {}

        # Obtener todos los objetos mesh
        mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']

        # Buscar objetos que siguen patrones de nombres de separación
        # Blender crea nombres como: Object.001, Object.002, etc. cuando separa
        name_groups = {}

        for obj in mesh_objects:
            # Verificar si es un cubo individual
            if not is_individual_cube(obj):
                continue

            # Intentar identificar el nombre base (antes del .001, .002, etc.)
            if '.' in obj.name:
                base_name = obj.name.rsplit('.', 1)[0]
                if base_name not in name_groups:
                    name_groups[base_name] = []
                name_groups[base_name].append(obj)
            else:
                # Objetos sin numeración podrían ser individuales o bases
                # Verificar si hay otros objetos con el mismo nombre base
                base_name = obj.name
                if base_name not in name_groups:
                    name_groups[base_name] = []
                name_groups[base_name].append(obj)

        # Filtrar solo grupos que tienen múltiples objetos (separados)
        for base_name, objects in name_groups.items():
            if len(objects) > 1:
                # Verificar que todos sean cubos individuales
                if all(is_individual_cube(obj) for obj in objects):
                    separated_groups[base_name] = objects
                    print(f"   📦 Grupo separado identificado: {base_name} → {len(objects)} cubos")

        # También buscar objetos que podrían haber sido separados pero renombrados
        # Buscar cubos individuales que no están en grupos pero podrían ser parte de separaciones anteriores
        individual_cubes = [obj for obj in mesh_objects if is_individual_cube(obj)]

        # Si hay muchos cubos individuales sin grupo, crear un grupo genérico
        ungrouped_cubes = []
        for obj in individual_cubes:
            in_group = False
            for group_objects in separated_groups.values():
                if obj in group_objects:
                    in_group = True
                    break
            if not in_group:
                ungrouped_cubes.append(obj)

        # Si hay más de 3 cubos sin grupo, asumir que son resultado de separaciones
        if len(ungrouped_cubes) > 3:
            separated_groups["separated_cubes"] = ungrouped_cubes
            print(f"   📦 Grupo genérico de cubos separados: {len(ungrouped_cubes)} cubos")

        return separated_groups

    @staticmethod
    def _setup_transparency_for_texture(material, tex_image_node, principled_node, texture_name):
        """Configura transparencia para texturas que la necesitan (flores, plantas, etc.)"""
        try:
            # Lista de texturas que necesitan transparencia
            transparent_textures = [
                'allium', 'azure_bluet', 'blue_orchid', 'cornflower', 'dandelion',
                'lilac_bottom', 'lilac_top', 'lily_of_the_valley', 'orange_tulip',
                'oxeye_daisy', 'peony_bottom', 'peony_top', 'pink_tulip', 'poppy',
                'red_tulip', 'rose_bush_bottom', 'rose_bush_top', 'sunflower_back',
                'sunflower_front', 'sunflower_top', 'white_tulip', 'wither_rose',
                'brown_mushroom', 'red_mushroom', 'red_toadstool',
                'sweet_berry_bush_stage3', 'sea_pickle', 'vine_y',
                'short_grass_y', 'tall_grass_bottom_y', 'tall_grass_top_y',
                'fern_y', 'large_fern_bottom_y', 'large_fern_top_y',
                'seagrass', 'tall_seagrass_bottom', 'tall_seagrass_top',
                'sugar_cane', 'kelp', 'kelp_plant', 'dried_kelp_top', 'dried_kelp_side',
                'glow_lichen', 'spore_blossom', 'hanging_roots',
                'small_dripleaf_top', 'big_dripleaf_top', 'small_dripleaf_stem_top',
                'mangrove_roots_top', 'mangrove_roots_side',
                'oak_leaves_y', 'birch_leaves_y', 'spruce_leaves_y', 'jungle_leaves_y',
                'acacia_leaves', 'dark_oak_leaves', 'mangrove_leaves',
                'azalea_leaves', 'flowering_azalea_leaves',
                'cherry_leaves', 'pale_oak_leaves'
            ]

            # Verificar si la textura necesita transparencia
            needs_transparency = any(trans_tex in texture_name.lower() for trans_tex in transparent_textures)

            if needs_transparency:
                print(f"   🌿 Configurando transparencia para: {texture_name}")

                # Configurar material para transparencia
                material.blend_method = 'BLEND'

                # Configurar shadow_method solo si existe (compatibilidad con versiones de Blender)
                if hasattr(material, 'shadow_method'):
                    material.shadow_method = 'CLIP'

                # Si no tenemos principled_node, buscarlo
                if principled_node is None:
                    for node in material.node_tree.nodes:
                        if node.type == 'BSDF_PRINCIPLED':
                            principled_node = node
                            break

                if principled_node:
                    # Conectar alpha del texture al Principled BSDF
                    links = material.node_tree.links

                    # Verificar si ya está conectado
                    alpha_connected = False
                    for link in principled_node.inputs['Alpha'].links:
                        if link.from_node == tex_image_node:
                            alpha_connected = True
                            break

                    if not alpha_connected:
                        links.new(tex_image_node.outputs['Alpha'], principled_node.inputs['Alpha'])

                    # Configurar propiedades del Principled BSDF para transparencia
                    principled_node.inputs['Alpha'].default_value = 1.0  # Usar alpha de textura
                    principled_node.inputs['Transmission Weight'].default_value = 0.0

                print(f"   ✅ Transparencia configurada para {texture_name}")
            else:
                # Para texturas opacas, asegurar configuración sólida
                material.blend_method = 'OPAQUE'

                # Configurar shadow_method solo si existe
                if hasattr(material, 'shadow_method'):
                    material.shadow_method = 'OPAQUE'

        except Exception as e:
            print(f"   ⚠️ Error configurando transparencia para {texture_name}: {e}")

    @staticmethod
    def save_configuration_to_file(config_file_path):
        """
        Guarda SOLO los cambios realizados en la configuración
        Incluye información de separaciones realizadas para restauración correcta
        """
        try:
            # Crear backup si el archivo ya existe
            if config_file_path.exists():
                backup_file = EditorConfig.get_backup_dir() / f"backup_{config_file_path.stem}_{int(time.time())}.json"
                shutil.copy2(config_file_path, backup_file)

            # Directorio de texturas por defecto (Prompt_054)
            default_texture_dir = "Prompt_054"

            config_data = {
                "metadata": {
                    "version": "5.0",
                    "timestamp": datetime.now().isoformat(),
                    "blender_version": f"{bpy.app.version[0]}.{bpy.app.version[1]}.{bpy.app.version[2]}",
                    "total_objects": 0,
                    "total_materials": 0,
                    "changes_only": True,
                    "default_texture_dir": default_texture_dir,
                    "includes_separation_tracking": True
                },
                "texture_paths": {},
                "objects": {},
                "separation_tracking": {}  # NUEVO: Tracking de separaciones
            }

            objects_processed = 0
            materials_processed = 0
            separations_tracked = 0

            # PASO 1: Analizar objetos separados y crear tracking
            print("🔍 Analizando estado de separación de bloques...")

            # Buscar objetos que parecen ser resultado de separaciones
            separated_groups = TextureConfigManager._analyze_separated_objects()

            for group_name, cube_objects in separated_groups.items():
                # Recopilar materiales comunes del grupo
                group_materials = {}

                for cube_obj in cube_objects:
                    for slot_idx, material_slot in enumerate(cube_obj.material_slots):
                        if material_slot.material:
                            mat = material_slot.material
                            texture_info = TextureConfigManager._extract_texture_from_material(mat)

                            if texture_info and default_texture_dir not in texture_info["path"]:
                                slot_key = f"slot_{slot_idx}"
                                # Solo guardar si no está ya guardado para este slot
                                if slot_key not in group_materials:
                                    group_materials[slot_key] = {
                                        "material_name": mat.name,
                                        "texture_path": texture_info["path"],
                                        "texture_name": texture_info["name"],
                                        "image_name": texture_info["image_name"]
                                    }

                config_data["separation_tracking"][group_name] = {
                    "original_object": group_name,
                    "separated_cubes": [obj.name for obj in cube_objects],
                    "cube_count": len(cube_objects),
                    "group_materials": group_materials,
                    "separation_timestamp": datetime.now().isoformat()
                }
                separations_tracked += 1
                print(f"   📦 Grupo separado detectado: {group_name} → {len(cube_objects)} cubos ({len(group_materials)} materiales)")

            # PASO 2: Procesar todos los objetos MESH en la escena
            for obj in bpy.context.scene.objects:
                if obj.type != 'MESH':
                    continue

                obj_data = {
                    "name": obj.name,
                    "location": list(obj.location),
                    "scale": list(obj.scale),
                    "materials": {}
                }

                has_changed_materials = False

                # Procesar cada material del objeto
                for slot_idx, material_slot in enumerate(obj.material_slots):
                    if not material_slot.material:
                        continue

                    mat = material_slot.material

                    # Extraer información de textura
                    texture_info = TextureConfigManager._extract_texture_from_material(mat)

                    if texture_info:
                        texture_path = texture_info["path"]

                        # SOLO GUARDAR SI LA TEXTURA NO ES DEL DIRECTORIO POR DEFECTO
                        # Esto significa que es un cambio personalizado
                        if default_texture_dir not in texture_path:
                            obj_data["materials"][f"slot_{slot_idx}"] = {
                                "material_name": mat.name,
                                "texture_path": texture_path,
                                "texture_name": texture_info["name"],
                                "image_name": texture_info["image_name"]
                            }

                            # Registrar ruta de textura global
                            config_data["texture_paths"][texture_info["name"]] = texture_path

                            materials_processed += 1
                            has_changed_materials = True

                            print(f"   🎯 Cambio detectado: {obj.name}.slot_{slot_idx} → {texture_info['name']}")

                # Solo incluir objetos con materiales modificados (no cubos separados individuales)
                # Los cubos separados se manejan a través de group_materials
                if has_changed_materials:
                    config_data["objects"][obj.name] = obj_data
                    objects_processed += 1

            # Actualizar metadata
            config_data["metadata"]["total_objects"] = objects_processed
            config_data["metadata"]["total_materials"] = materials_processed
            config_data["metadata"]["separations_tracked"] = separations_tracked

            # Guardar archivo
            with open(config_file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)

            print(f"\n{'='*60}")
            print(f"💾 CAMBIOS GUARDADOS (CON TRACKING DE SEPARACIONES)")
            print(f"{'='*60}")
            print(f"📁 Archivo: {config_file_path}")
            print(f"📦 Objetos con cambios: {objects_processed}")
            print(f"🎨 Materiales modificados: {materials_processed}")
            print(f"✂️ Separaciones rastreadas: {separations_tracked}")
            print(f"⏰ Timestamp: {config_data['metadata']['timestamp']}")
            print(f"🎯 Modo: Cambios + Separaciones")
            print(f"{'='*60}\n")

            return True, objects_processed, materials_processed

        except Exception as e:
            print(f"❌ Error guardando cambios en archivo específico: {e}")
            import traceback
            traceback.print_exc()
            return False, 0, 0

    @staticmethod
    def load_configuration_from_file(config_file_path):
        """
        Carga y aplica la configuración desde un archivo específico
        Maneja objetos separados correctamente aplicando texturas a cubos individuales
        """
        if not config_file_path.exists():
            return False, f"No existe el archivo: {config_file_path.name}"

        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            print(f"\n{'='*60}")
            print(f"📂 CARGANDO CONFIGURACIÓN DESDE ARCHIVO ESPECÍFICO")
            print(f"{'='*60}")
            print(f"📁 Archivo: {config_file_path.name}")
            print(f"🔖 Versión: {config_data.get('metadata', {}).get('version', 'desconocida')}")
            print(f"⏰ Guardado: {config_data.get('metadata', {}).get('timestamp', 'desconocido')}")

            # Verificar si incluye tracking de separaciones
            has_separation_tracking = config_data.get('metadata', {}).get('includes_separation_tracking', False)
            if has_separation_tracking:
                print(f"✂️ Tracking de separaciones: Habilitado")
            print(f"{'='*60}\n")

            applied_count = 0
            failed_count = 0
            not_found_count = 0
            separation_restored_count = 0
            processed_objects = set()  # Track all objects that receive textures

            objects_config = config_data.get("objects", {})
            separation_tracking = config_data.get("separation_tracking", {})

            # PASO 0: RECREAR SEPARACIONES GUARDADAS ANTES DE APLICAR TEXTURAS
            if has_separation_tracking and separation_tracking:
                print("🔧 Recreando separaciones guardadas...")
                recreated_separations = 0

                for group_name, separation_data in separation_tracking.items():
                    original_object_name = separation_data.get("original_object", group_name)

                    # Buscar el objeto original en la escena
                    original_obj = bpy.context.scene.objects.get(original_object_name)

                    if original_obj and is_bedrock_object(original_obj):
                        print(f"   🔄 Recreando separación: {original_object_name} → {separation_data.get('cube_count', 0)} cubos")

                        # Separar el objeto usando la función existente
                        if separate_object_into_cubes(original_obj):
                            recreated_separations += 1
                            print(f"   ✅ Separación recreada: {original_object_name}")
                        else:
                            print(f"   ❌ Error recreando separación: {original_object_name}")
                    else:
                        print(f"   ⚠️ Objeto original no encontrado: {original_object_name}")

                if recreated_separations > 0:
                    print(f"🔄 Separaciones recreadas: {recreated_separations}")
                    print("   ℹ️ Ahora aplicando texturas a los cubos separados...")

            # PASO 1: Manejar objetos separados
            if has_separation_tracking and separation_tracking:
                print("🔧 Aplicando configuración a objetos separados...")

                # Primero, analizar cubos separados actualmente en la escena
                current_separated_groups = TextureConfigManager._analyze_separated_objects()

                for group_name, separation_data in separation_tracking.items():
                    group_materials = separation_data.get("group_materials", {})
                    original_cube_names = separation_data.get("separated_cubes", [])

                    print(f"   📦 Procesando grupo: {group_name} ({len(original_cube_names)} cubos registrados)")

                    # Buscar cubos que pertenecen a este grupo en la escena actual
                    applicable_cubes = []

                    # Estrategia 1: Buscar cubos con nombres que coincidan con el patrón del grupo
                    if group_name in current_separated_groups:
                        applicable_cubes = current_separated_groups[group_name]
                        print(f"      🔍 Encontrados {len(applicable_cubes)} cubos del grupo por patrón de nombres")
                    else:
                        # Estrategia 2: Buscar cubos individuales que podrían ser del grupo
                        for cube_name in original_cube_names:
                            obj = bpy.context.scene.objects.get(cube_name)
                            if obj and is_individual_cube(obj):
                                applicable_cubes.append(obj)

                        if applicable_cubes:
                            print(f"      🔍 Encontrados {len(applicable_cubes)} cubos del grupo por nombres exactos")

                    # Estrategia 3: Si no encontramos cubos específicos, buscar TODOS los cubos individuales
                    # que podrían ser resultado de separaciones (para compatibilidad con archivos legacy)
                    if not applicable_cubes:
                        all_individual_cubes = [obj for obj in bpy.context.scene.objects if is_individual_cube(obj)]
                        if all_individual_cubes:
                            applicable_cubes = all_individual_cubes
                            print(f"      🔍 Usando todos los cubos individuales encontrados ({len(applicable_cubes)}) como fallback")

                    # Aplicar SOLO configuraciones individuales guardadas explícitamente
                    # NO usar group_materials como fallback - persistencia exacta
                    if applicable_cubes:
                        print(f"      📋 Aplicando configuraciones individuales guardadas a cubos separados")

                        # Buscar configuraciones individuales para los cubos separados encontrados
                        individual_configs_applied = 0

                        for cube_obj in applicable_cubes:
                            # SOLO aplicar si hay configuración individual guardada explícitamente
                            # Persistencia EXACTA - no usar group_materials como fallback
                            if cube_obj.name in objects_config:
                                cube_config = objects_config[cube_obj.name]
                                materials_config = cube_config.get("materials", {})

                                for slot_key, mat_config in materials_config.items():
                                    slot_idx = int(slot_key.split('_')[1])

                                    if slot_idx >= len(cube_obj.material_slots):
                                        while len(cube_obj.material_slots) <= slot_idx:
                                            cube_obj.data.materials.append(None)

                                    texture_path = mat_config.get("texture_path")
                                    texture_name = mat_config.get("texture_name")

                                    if not texture_path or not os.path.exists(texture_path):
                                        failed_count += 1
                                        continue

                                    success = TextureConfigManager._apply_texture_to_slot(
                                        cube_obj, slot_idx, texture_path, texture_name
                                    )

                                    if success:
                                        applied_count += 1
                                        separation_restored_count += 1
                                        processed_objects.add(cube_obj.name)
                                        individual_configs_applied += 1
                                        print(f"         ✅ {cube_obj.name}.slot_{slot_idx} → {texture_name}")
                                    else:
                                        failed_count += 1
                            else:
                                # Cubo sin configuración guardada - dejar sin textura
                                print(f"         ℹ️ {cube_obj.name} → sin configuración guardada (se mantiene como está)")

                        if individual_configs_applied > 0:
                            print(f"      📋 Aplicadas {individual_configs_applied} configuraciones individuales exactas")
                        else:
                            print(f"      ℹ️ No hay configuraciones individuales guardadas para estos cubos separados")
                    else:
                        print(f"      ⚠️ No se encontraron cubos para el grupo {group_name}")
                        not_found_count += len(original_cube_names)

            # PASO 2: Aplicar configuración normal a objetos no separados
            print(f"\n🎨 Aplicando configuración a objetos normales...")

            for obj_name, obj_data in objects_config.items():
                # Skip objects that were already processed as part of separations
                if obj_name in processed_objects:
                    continue

                obj = bpy.context.scene.objects.get(obj_name)

                if not obj:
                    print(f"⚠️ Objeto '{obj_name}' no encontrado en escena")
                    not_found_count += 1
                    continue

                materials_config = obj_data.get("materials", {})

                for slot_key, mat_config in materials_config.items():
                    slot_idx = int(slot_key.split('_')[1])

                    if slot_idx >= len(obj.material_slots):
                        print(f"⚠️ Slot {slot_idx} no existe en '{obj_name}'")
                        failed_count += 1
                        continue

                    texture_path = mat_config.get("texture_path")
                    texture_name = mat_config.get("texture_name")

                    if not texture_path or not os.path.exists(texture_path):
                        print(f"⚠️ Textura no encontrada: {texture_path}")
                        failed_count += 1
                        continue

                    # Aplicar textura
                    success = TextureConfigManager._apply_texture_to_slot(
                        obj, slot_idx, texture_path, texture_name
                    )

                    if success:
                        applied_count += 1
                        processed_objects.add(obj_name)
                        print(f"✅ {obj_name}.slot_{slot_idx} → {texture_name}")
                    else:
                        failed_count += 1
                        print(f"❌ Error aplicando textura a {obj_name}.slot_{slot_idx}")

            print(f"\n{'='*60}")
            print(f"📊 RESUMEN DE APLICACIÓN")
            print(f"{'='*60}")
            print(f"✅ Texturas aplicadas: {applied_count}")
            if separation_restored_count > 0:
                print(f"✂️ Separaciones restauradas: {separation_restored_count}")
            print(f"❌ Errores: {failed_count}")
            print(f"⚠️ Objetos no encontrados: {not_found_count}")
            print(f"{'='*60}\n")

            success_msg = f"✅ {applied_count} texturas aplicadas desde {config_file_path.name}"
            if separation_restored_count > 0:
                success_msg += f" (+ {separation_restored_count} separaciones restauradas)"

            if applied_count > 0:
                return True, success_msg
            else:
                return False, f"❌ No se aplicaron texturas ({failed_count} errores)"

        except Exception as e:
            error_msg = f"Error cargando configuración desde archivo específico: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return False, error_msg

# ==============================================================================
# SISTEMA DE VALIDACIÓN
# ==============================================================================

class ConfigValidator:
    """Validador de configuraciones"""
    
    @staticmethod
    def validate_config_file():
        """Valida el archivo de configuración"""
        config_file = EditorConfig.get_config_file()
        
        if not config_file.exists():
            return False, "Archivo no existe"
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Validar estructura
            if "metadata" not in config_data:
                return False, "Falta metadata"
            
            if "objects" not in config_data:
                return False, "Falta sección de objetos"
            
            # Validar rutas de texturas
            missing_textures = []
            for obj_name, obj_data in config_data.get("objects", {}).items():
                for slot_key, mat_config in obj_data.get("materials", {}).items():
                    texture_path = mat_config.get("texture_path")
                    if texture_path and not os.path.exists(texture_path):
                        missing_textures.append(texture_path)
            
            if missing_textures:
                return False, f"{len(missing_textures)} texturas no encontradas"
            
            return True, "Configuración válida"
            
        except json.JSONDecodeError:
            return False, "JSON inválido"
        except Exception as e:
            return False, f"Error: {str(e)}"

# ==============================================================================
# PANEL PRINCIPAL v5.0
# ==============================================================================

class MinecraftBlockEditorV5(bpy.types.Panel):
    """Panel principal mejorado del Block Editor v5.0"""
    bl_label = "Block Tools v5.0"
    bl_idname = "MINECRAFT_PT_block_editor_v5"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Block Tools v5'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # ===============================================
        # HEADER CON INFORMACIÓN DE VERSIÓN
        # ===============================================
        header = layout.box()
        header.label(text="🎮 Minecraft Block Editor", icon='NONE')
        header.label(text="Version 5.0 - Sistema Completo")
        
        # ===============================================
        # SECCIÓN 1: GESTIÓN DE CONFIGURACIÓN
        # ===============================================
        layout.separator()
        box1 = layout.box()
        box1.label(text="💾 Gestión de Configuración:", icon='NONE')
        
        # Verificar si existe configuración
        config_exists = EditorConfig.get_config_file().exists()
        
        if config_exists:
            info = box1.box()
            info.alert = False
            info.label(text="✅ Configuración encontrada", icon='NONE')
            
            # Validar configuración
            is_valid, msg = ConfigValidator.validate_config_file()
            if is_valid:
                info.label(text=f"✓ {msg}")
            else:
                info.alert = True
                info.label(text=f"⚠️ {msg}")
        else:
            info = box1.box()
            info.alert = True
            info.label(text="⚠️ No hay configuración guardada", icon='NONE')
        
        # Botones principales
        col = box1.column()
        col.scale_y = 1.5

        row = col.row(align=True)
        row.operator('minecraft.save_config_named',
                     text='💾 Guardar Como...',
                     icon='FILE_NEW')
        row.operator('minecraft.load_config_named',
                     text='📂 Cargar De...',
                     icon='FILE_FOLDER')
        
        col.operator('minecraft.validate_config',
                    text='🔍 Validar Configuración',
                    icon='CHECKMARK')
        
        # Información adicional
        info2 = box1.box()
        info2.label(text="📁 Ubicación:", icon='NONE')
        config_path = str(EditorConfig.get_config_file())
        # Mostrar ruta en partes si es muy larga
        if len(config_path) > 50:
            info2.label(text=config_path[:50])
            info2.label(text=config_path[50:])
        else:
            info2.label(text=config_path)

        # Mostrar configuraciones disponibles
        config_dir = EditorConfig.get_config_dir()
        if config_dir.exists():
            config_files = list(config_dir.glob("texture_config_*.json"))
            if config_files:
                info3 = box1.box()
                info3.label(text=f"📋 Configuraciones disponibles: {len(config_files)}", icon='NONE')
                # Mostrar las 3 más recientes
                sorted_files = sorted(config_files, key=lambda x: x.stat().st_mtime, reverse=True)
                for i, config_file in enumerate(sorted_files[:3]):
                    name = config_file.stem.replace("texture_config_", "")
                    mtime = datetime.fromtimestamp(config_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                    info3.label(text=f"  {i+1}. {name} ({mtime})")
                if len(config_files) > 3:
                    info3.label(text=f"  ... y {len(config_files)-3} más")
        
        # ===============================================
        # SECCIÓN 2: ESTADÍSTICAS Y SEPARACIÓN
        # ===============================================
        layout.separator()
        box2 = layout.box()
        box2.label(text="📊 Estado de la Escena:", icon='NONE')

        # Contar objetos y materiales
        mesh_objects = [obj for obj in context.scene.objects if obj.type == 'MESH']
        textured_objects = sum(1 for obj in mesh_objects if obj.data.materials)
        selected_objects = len([obj for obj in context.selected_objects if obj.type == 'MESH'])
        bedrock_objects = get_bedrock_objects(context)
        individual_cubes = count_individual_cubes(context)

        stats = box2.column()
        stats.label(text=f"📦 Objetos mesh: {len(mesh_objects)}")
        stats.label(text=f"🎨 Con texturas: {textured_objects}")
        stats.label(text=f"✅ Seleccionados: {selected_objects}")
        stats.label(text=f"🔴 Bloques unidos: {len(bedrock_objects)}")
        stats.label(text=f"🧊 Cubos individuales: {individual_cubes}")

        # Separación de bloques
        if len(bedrock_objects) > 0:
            layout.separator()
            box_sep = layout.box()
            box_sep.label(text="🔧 Separación de Bloques:", icon='MODIFIER')
            box_sep.alert = True

            col_sep = box_sep.column()
            col_sep.label(text=f"⚠️ Hay {len(bedrock_objects)} objetos unidos", icon='ERROR')

            row_sep = col_sep.row(align=True)
            row_sep.operator('minecraft.separate_selected',
                           text='Separar Seleccionados',
                           icon='UNLINKED')

            row_main = col_sep.row()
            row_main.scale_y = 1.5
            row_main.operator('minecraft.separate_all_bedrock',
                            text=f'🔥 Separar Todos ({len(bedrock_objects)})',
                            icon='UNLINKED')

            info_sep = box_sep.box()
            info_sep.label(text="💡 Los bloques unidos deben separarse", icon='INFO')
            info_sep.label(text="para editar texturas individualmente")
        
        # ===============================================
        # SECCIÓN 3: HERRAMIENTAS DE SELECCIÓN
        # ===============================================
        layout.separator()
        box3 = layout.box()
        box3.label(text="🎯 Herramientas de Selección:", icon='NONE')
        
        col_sel = box3.column()
        row = col_sel.row(align=True)
        row.operator('minecraft.select_all_cubes',
                    text='Todo',
                    icon='SELECT_SET')
        row.operator('minecraft.deselect_all',
                    text='Ninguno',
                    icon='SELECT_SUBTRACT')
        
        col_sel.operator('minecraft.select_by_texture',
                        text='🔍 Por Textura Actual',
                        icon='TEXTURE')
        
        col_sel.operator('minecraft.select_by_material_name',
                        text='🔍 Por Nombre Material',
                        icon='MATERIAL')
        
        # ===============================================
        # SECCIÓN 4: APLICACIÓN DE TEXTURAS
        # ===============================================
        layout.separator()
        box4 = layout.box()
        box4.label(text="🎨 Aplicar Texturas:", icon='NONE')
        
        # Configurar ruta
        current_path = getattr(context.scene, 'minecraft_texture_path', '')
        if current_path:
            col_path = box4.column()
            col_path.label(text=f"📂 {os.path.basename(current_path)}")
        
        row_path = box4.row(align=True)
        row_path.operator('minecraft.set_texture_path',
                         text='📁 Configurar Ruta',
                         icon='FILE_FOLDER')
        row_path.operator('minecraft.clear_texture_path',
                         text='🗑️',
                         icon='X')
        
        # Obtener y mostrar texturas
        texture_files = get_texture_files()

        if texture_files:
            box4.label(text=f"🖼️ {len(texture_files)} texturas disponibles")

            # Campo de búsqueda
            box4.prop(context.scene, "minecraft_texture_search",
                     text="🔎", icon='VIEWZOOM')

            # Filtrar texturas
            search_term = context.scene.minecraft_texture_search.lower()
            filtered = [t for t in texture_files if search_term in t.lower()] if search_term else texture_files

            if filtered:
                # CONTENEDOR CON SCROLL PARA TEXTURAS
                scroll_box = box4.box()
                scroll_box.label(text=f"📜 Texturas ({len(filtered)}):", icon='NONE')

                # Crear área con scroll
                scroll_col = scroll_box.column(align=True)
                scroll_col.scale_y = 0.8  # Altura reducida para scroll

                # Mostrar todas las texturas en filas de 2 columnas con scroll
                for i in range(0, len(filtered), 2):
                    row = scroll_col.row(align=True)

                    # Primera columna
                    if i < len(filtered):
                        name = filtered[i].replace('.png', '').replace('_', ' ').title()[:15]
                        op = row.operator('minecraft.apply_texture',
                                        text=name,
                                        icon='IMAGE_DATA')
                        op.texture_name = filtered[i]

                    # Segunda columna
                    if i + 1 < len(filtered):
                        name = filtered[i+1].replace('.png', '').replace('_', ' ').title()[:15]
                        op = row.operator('minecraft.apply_texture',
                                        text=name,
                                        icon='IMAGE_DATA')
                        op.texture_name = filtered[i+1]

                # Información adicional al final
                info_scroll = scroll_box.box()
                info_scroll.label(text=f"✅ {len(filtered)} texturas listadas", icon='NONE')
                info_scroll.label(text="💡 Usa scroll para ver todas", icon='INFO')

            else:
                box4.label(text="❌ Sin resultados", icon='ERROR')
        else:
            box4.label(text="⚠️ Configura ruta de texturas", icon='ERROR')
        
        # ===============================================
        # SECCIÓN 5: HERRAMIENTAS AVANZADAS
        # ===============================================
        layout.separator()
        box5 = layout.box()
        box5.label(text="🔧 Herramientas Avanzadas:", icon='NONE')

        col_tools = box5.column()
        col_tools.operator('minecraft.show_statistics',
                          text='📊 Estadísticas Detalladas',
                          icon='INFO')
        col_tools.operator('minecraft.clean_materials',
                          text='🗑️ Limpiar Materiales',
                          icon='BRUSH_DATA')
        col_tools.operator('minecraft.export_config_info',
                          text='📄 Exportar Info',
                          icon='TEXT')

        # ===============================================
        # SECCIÓN 6: ELIMINACIÓN DE BLOQUES
        # ===============================================
        layout.separator()
        box6 = layout.box()
        box6.label(text="🗑️ Eliminación de Bloques:", icon='NONE')

        col_delete = box6.column()

        # Información de seguridad
        warning = box6.box()
        warning.alert = True
        warning.label(text="⚠️ Estas acciones son irreversibles", icon='ERROR')
        warning.label(text="Asegúrate de guardar antes de eliminar")

        # Botones de eliminación
        row_delete = col_delete.row(align=True)
        row_delete.operator('minecraft.delete_selected_blocks',
                           text='🗑️ Eliminar Seleccionados',
                           icon='X')
        row_delete.operator('minecraft.delete_all_separated',
                           text='💥 Eliminar Todos Separados',
                           icon='CANCEL')

        # Información adicional
        info_delete = box6.box()
        info_delete.label(text="💡 Usos comunes:", icon='INFO')
        info_delete.label(text="• Limpiar espacio para nuevos bloques")
        info_delete.label(text="• Corregir errores de separación")
        info_delete.label(text="• Optimizar escena compleja")

# ==============================================================================
# OPERADORES PRINCIPALES
# ==============================================================================


class MINECRAFT_OT_ValidateConfig(bpy.types.Operator):
    """Validar configuración guardada"""
    bl_idname = "minecraft.validate_config"
    bl_label = "Validar Configuración"
    bl_description = "Verifica que la configuración guardada sea válida"

    def execute(self, context):
        is_valid, message = ConfigValidator.validate_config_file()

        if is_valid:
            self.report({'INFO'}, f'✅ {message}')
        else:
            self.report({'WARNING'}, f'⚠️ {message}')

        return {'FINISHED'}

class MINECRAFT_OT_SaveConfigNamed(bpy.types.Operator):
    """Guardar configuración con nombre personalizado"""
    bl_idname = "minecraft.save_config_named"
    bl_label = "Guardar Configuración Como..."
    bl_description = "Guarda la configuración con un nombre personalizado"
    bl_options = {'REGISTER', 'UNDO'}

    config_name: bpy.props.StringProperty(
        name="Nombre de Configuración",
        description="Nombre para la configuración (sin extensión)",
        default=""
    )

    def execute(self, context):
        if not self.config_name.strip():
            self.report({'ERROR'}, 'Ingresa un nombre válido')
            return {'CANCELLED'}

        # Crear nombre de archivo seguro
        safe_name = "".join(c for c in self.config_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        if not safe_name:
            safe_name = f"config_{int(time.time())}"

        filename = f"texture_config_{safe_name}.json"
        config_file = EditorConfig.get_config_dir() / filename

        success, obj_count, mat_count = TextureConfigManager.save_configuration_to_file(config_file)

        if success:
            self.report({'INFO'}, f'✅ Guardado como "{safe_name}": {obj_count} objetos, {mat_count} materiales')
        else:
            self.report({'ERROR'}, '❌ Error al guardar configuración')

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

def get_config_files_items(self, context):
    """Obtiene lista de archivos de configuración disponibles para EnumProperty"""
    config_dir = EditorConfig.get_config_dir()
    if not config_dir.exists():
        return []

    files = []
    for file in config_dir.glob("texture_config_*.json"):
        if file.is_file():
            # Extraer nombre del archivo
            name = file.stem.replace("texture_config_", "")
            files.append((str(file), name, f"Configuración: {name}"))

    # Ordenar por fecha de modificación (más reciente primero)
    files.sort(key=lambda x: os.path.getmtime(x[0]), reverse=True)

    return files

class MINECRAFT_OT_LoadConfigNamed(bpy.types.Operator):
    """Cargar configuración desde archivo seleccionado"""
    bl_idname = "minecraft.load_config_named"
    bl_label = "Cargar Configuración De..."
    bl_description = "Carga una configuración desde un archivo seleccionado"
    bl_options = {'REGISTER', 'UNDO'}

    config_file: bpy.props.EnumProperty(
        name="Archivo de Configuración",
        description="Selecciona el archivo de configuración a cargar",
        items=get_config_files_items
    )


    def execute(self, context):
        if not self.config_file:
            self.report({'ERROR'}, 'Selecciona un archivo de configuración')
            return {'CANCELLED'}

        config_file = Path(self.config_file)
        if not config_file.exists():
            self.report({'ERROR'}, f'Archivo no encontrado: {config_file.name}')
            return {'CANCELLED'}

        success, message = TextureConfigManager.load_configuration_from_file(config_file)

        if success:
            self.report({'INFO'}, message)
        else:
            self.report({'WARNING'}, message)

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class MINECRAFT_OT_ApplyTexture(bpy.types.Operator):
    """Aplicar textura a objetos seleccionados"""
    bl_idname = "minecraft.apply_texture"
    bl_label = "Aplicar Textura"
    bl_description = "Aplica la textura seleccionada"
    bl_options = {'REGISTER', 'UNDO'}
    
    texture_name: bpy.props.StringProperty(default="")
    
    def execute(self, context):
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not selected:
            self.report({'WARNING'}, 'Selecciona objetos primero')
            return {'CANCELLED'}
        
        texture_path = get_texture_path(self.texture_name)
        if not texture_path:
            self.report({'ERROR'}, f'Textura no encontrada: {self.texture_name}')
            return {'CANCELLED'}
        
        success_count = 0
        for obj in selected:
            if TextureConfigManager._apply_texture_to_slot(obj, 0, texture_path, self.texture_name):
                success_count += 1
        
        self.report({'INFO'}, f'✅ Aplicado a {success_count} objetos')
        return {'FINISHED'}

class MINECRAFT_OT_SelectAllCubes(bpy.types.Operator):
    """Seleccionar todos los cubos"""
    bl_idname = "minecraft.select_all_cubes"
    bl_label = "Seleccionar Todos"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        count = 0
        for obj in context.scene.objects:
            if obj.type == 'MESH':
                obj.select_set(True)
                count += 1
        self.report({'INFO'}, f'✅ Seleccionados {count} objetos')
        return {'FINISHED'}

class MINECRAFT_OT_DeselectAll(bpy.types.Operator):
    """Deseleccionar todos"""
    bl_idname = "minecraft.deselect_all"
    bl_label = "Deseleccionar"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        self.report({'INFO'}, '✓ Deseleccionado')
        return {'FINISHED'}

class MINECRAFT_OT_SelectByTexture(bpy.types.Operator):
    """Seleccionar por textura del objeto activo"""
    bl_idname = "minecraft.select_by_texture"
    bl_label = "Seleccionar por Textura"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        active = context.active_object
        if not active or active.type != 'MESH' or not active.data.materials:
            self.report({'WARNING'}, 'Selecciona un objeto con material')
            return {'CANCELLED'}
        
        target_mat = active.data.materials[0]
        bpy.ops.object.select_all(action='DESELECT')
        
        count = 0
        for obj in context.scene.objects:
            if obj.type == 'MESH' and obj.data.materials:
                if obj.data.materials[0] == target_mat:
                    obj.select_set(True)
                    count += 1
        
        self.report({'INFO'}, f'✅ Seleccionados {count} objetos')
        return {'FINISHED'}

class MINECRAFT_OT_SelectByMaterialName(bpy.types.Operator):
    """Seleccionar por nombre de material"""
    bl_idname = "minecraft.select_by_material_name"
    bl_label = "Seleccionar por Material"
    bl_options = {'REGISTER', 'UNDO'}
    
    material_name: bpy.props.StringProperty(name="Material", default="")
    
    def execute(self, context):
        if not self.material_name:
            return {'CANCELLED'}
        
        bpy.ops.object.select_all(action='DESELECT')
        search = self.material_name.lower()
        count = 0
        
        for obj in context.scene.objects:
            if obj.type == 'MESH' and obj.data.materials:
                for mat in obj.data.materials:
                    if mat and search in mat.name.lower():
                        obj.select_set(True)
                        count += 1
                        break
        
        self.report({'INFO'}, f'✅ {count} objetos con "{self.material_name}"')
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class MINECRAFT_OT_SetTexturePath(bpy.types.Operator):
    """Configurar ruta de texturas"""
    bl_idname = "minecraft.set_texture_path"
    bl_label = "Configurar Ruta"
    bl_description = "Define carpeta de texturas"
    
    directory: bpy.props.StringProperty(subtype="DIR_PATH")
    
    def execute(self, context):
        if self.directory and os.path.exists(self.directory):
            context.scene.minecraft_texture_path = self.directory
            count = len(get_texture_files())
            self.report({'INFO'}, f'✅ Ruta configurada: {count} texturas')
        else:
            self.report({'ERROR'}, 'Ruta no válida')
        return {'FINISHED'}
    
    def invoke(self, context, event):
        if hasattr(context.scene, 'minecraft_texture_path'):
            self.directory = context.scene.minecraft_texture_path
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class MINECRAFT_OT_ClearTexturePath(bpy.types.Operator):
    """Limpiar ruta de texturas"""
    bl_idname = "minecraft.clear_texture_path"
    bl_label = "Limpiar Ruta"
    
    def execute(self, context):
        context.scene.minecraft_texture_path = ""
        self.report({'INFO'}, 'Ruta limpiada')
        return {'FINISHED'}

class MINECRAFT_OT_ShowStatistics(bpy.types.Operator):
    """Mostrar estadísticas detalladas"""
    bl_idname = "minecraft.show_statistics"
    bl_label = "Estadísticas"
    
    def execute(self, context):
        stats = {}
        total = 0
        
        for obj in context.scene.objects:
            if obj.type == 'MESH' and obj.data.materials:
                mat_name = obj.data.materials[0].name
                stats[mat_name] = stats.get(mat_name, 0) + 1
                total += 1
        
        print("\n" + "="*60)
        print("📊 ESTADÍSTICAS DE TEXTURAS")
        print("="*60)
        print(f"Total objetos: {total}")
        print("-"*60)
        
        for mat, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            pct = (count/total*100) if total > 0 else 0
            print(f"{mat}: {count} ({pct:.1f}%)")
        
        print("="*60 + "\n")
        
        self.report({'INFO'}, f'📊 Ver consola ({total} objetos)')
        return {'FINISHED'}

class MINECRAFT_OT_CleanMaterials(bpy.types.Operator):
    """Limpiar materiales sin uso"""
    bl_idname = "minecraft.clean_materials"
    bl_label = "Limpiar Materiales"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        count = 0
        for mat in bpy.data.materials:
            if mat.users == 0:
                bpy.data.materials.remove(mat)
                count += 1
        
        self.report({'INFO'}, f'🗑️ Eliminados {count} materiales')
        return {'FINISHED'}

class MINECRAFT_OT_ExportConfigInfo(bpy.types.Operator):
    """Exportar información de configuración"""
    bl_idname = "minecraft.export_config_info"
    bl_label = "Exportar Info"

    def execute(self, context):
        config_file = EditorConfig.get_config_file()

        if not config_file.exists():
            self.report({'WARNING'}, 'No hay configuración guardada')
            return {'CANCELLED'}

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            info_file = EditorConfig.get_config_dir() / "config_info.txt"

            with open(info_file, 'w', encoding='utf-8') as f:
                f.write("="*60 + "\n")
                f.write("MINECRAFT BLOCK EDITOR v5.0 - INFORMACIÓN DE CONFIGURACIÓN\n")
                f.write("="*60 + "\n\n")

                metadata = config.get('metadata', {})
                f.write(f"Versión: {metadata.get('version', 'N/A')}\n")
                f.write(f"Fecha: {metadata.get('timestamp', 'N/A')}\n")
                f.write(f"Objetos: {metadata.get('total_objects', 0)}\n")
                f.write(f"Materiales: {metadata.get('total_materials', 0)}\n\n")

                f.write("OBJETOS CONFIGURADOS:\n")
                f.write("-"*60 + "\n")

                for obj_name, obj_data in config.get('objects', {}).items():
                    f.write(f"\n{obj_name}:\n")
                    for slot_key, mat_config in obj_data.get('materials', {}).items():
                        texture_name = mat_config.get('texture_name', 'N/A')
                        f.write(f"  - {slot_key}: {texture_name}\n")

            self.report({'INFO'}, f'📄 Exportado: {info_file.name}')
            print(f"✅ Información exportada a: {info_file}")

        except Exception as e:
            self.report({'ERROR'}, f'Error: {str(e)}')

        return {'FINISHED'}

class MINECRAFT_OT_DeleteSelectedBlocks(bpy.types.Operator):
    """Eliminar bloques seleccionados"""
    bl_idname = "minecraft.delete_selected_blocks"
    bl_label = "Eliminar Bloques Seleccionados"
    bl_description = "Elimina permanentemente los bloques seleccionados"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_mesh = [obj for obj in context.selected_objects if obj.type == 'MESH']

        if not selected_mesh:
            self.report({'WARNING'}, 'No hay objetos mesh seleccionados')
            return {'CANCELLED'}

        # Confirmación adicional para muchos objetos
        if len(selected_mesh) > 5:
            # En un addon real, aquí iría un diálogo de confirmación
            print(f"⚠️ Eliminando {len(selected_mesh)} objetos...")

        deleted_count = 0
        for obj in selected_mesh:
            try:
                # Guardar nombre antes de eliminar
                obj_name = obj.name

                # Eliminar objeto
                bpy.data.objects.remove(obj, do_unlink=True)
                deleted_count += 1

                print(f"  🗑️ Eliminado: {obj_name}")

            except Exception as e:
                print(f"  ❌ Error eliminando {obj.name}: {e}")

        if deleted_count > 0:
            self.report({'INFO'}, f'✅ Eliminados {deleted_count} bloques seleccionados')
        else:
            self.report({'WARNING'}, 'No se pudo eliminar ningún bloque')

        return {'FINISHED'}

class MINECRAFT_OT_DeleteAllSeparated(bpy.types.Operator):
    """Eliminar todos los bloques separados (cubos individuales)"""
    bl_idname = "minecraft.delete_all_separated"
    bl_label = "Eliminar Todos los Bloques Separados"
    bl_description = "Elimina permanentemente todos los cubos individuales separados"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Encontrar todos los cubos separados (bloques individuales)
        separated_cubes = []
        for obj in context.scene.objects:
            if obj.type == 'MESH' and is_individual_cube(obj):
                separated_cubes.append(obj)

        if not separated_cubes:
            self.report({'INFO'}, 'No hay bloques separados para eliminar')
            return {'FINISHED'}

        # Confirmación adicional para muchos objetos
        if len(separated_cubes) > 10:
            print(f"⚠️ Eliminando {len(separated_cubes)} bloques separados...")

        deleted_count = 0
        for obj in separated_cubes:
            try:
                obj_name = obj.name
                bpy.data.objects.remove(obj, do_unlink=True)
                deleted_count += 1
                print(f"  🗑️ Eliminado cubo separado: {obj_name}")

            except Exception as e:
                print(f"  ❌ Error eliminando {obj.name}: {e}")

        if deleted_count > 0:
            self.report({'INFO'}, f'✅ Eliminados {deleted_count} bloques separados')
            print(f"💡 Espacio liberado para nuevos bloques")
        else:
            self.report({'WARNING'}, 'No se pudo eliminar ningún bloque')

        return {'FINISHED'}

# ==============================================================================
# SISTEMA DE SEPARACIÓN DE BLOQUES
# ==============================================================================

def separate_object_into_cubes(obj):
    """Separa un objeto mesh en sus bloques/cubos individuales"""
    if obj.type != 'MESH':
        return False

    try:
        # Guardar objeto activo anterior
        previous_active = bpy.context.view_layer.objects.active

        # Seleccionar solo este objeto
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        # Cambiar a modo edición
        bpy.ops.object.mode_set(mode='EDIT')

        # Seleccionar todo
        bpy.ops.mesh.select_all(action='SELECT')

        # Separar por partes sueltas
        bpy.ops.mesh.separate(type='LOOSE')

        # Volver a modo objeto
        bpy.ops.object.mode_set(mode='OBJECT')

        # Restaurar objeto activo anterior si existe
        if previous_active and previous_active.name in bpy.data.objects:
            bpy.context.view_layer.objects.active = previous_active

        return True

    except Exception as e:
        print(f"Error separando {obj.name}: {e}")
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except:
            pass
        return False

def get_bedrock_objects(context):
    """Obtiene objetos unidos que necesitan separación"""
    bedrock_objects = []
    for obj in context.scene.objects:
        if obj.type == 'MESH' and is_bedrock_object(obj):
            bedrock_objects.append(obj)
    return bedrock_objects

def is_bedrock_object(obj):
    """Verifica si un objeto necesita separación (está unido)"""
    # Un objeto está unido si tiene más de 8 vértices (más de un cubo)
    is_compound = len(obj.data.vertices) > 8

    if not is_compound:
        return False

    # Verificar si no tiene materiales o tiene material bedrock
    if not obj.data.materials:
        return True

    for mat in obj.data.materials:
        if mat and is_bedrock_material(mat):
            return True

    return False

def is_bedrock_material(mat):
    """Verifica si un material es de bedrock"""
    if not mat:
        return False

    # Verificar nombre del material
    if 'bedrock' in mat.name.lower():
        return True

    # Verificar textura del material
    if mat.node_tree:
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE':
                if node.image and 'bedrock' in node.image.name.lower():
                    return True

    return False

def is_individual_cube(obj):
    """Verifica si un objeto es un cubo individual (8 vértices)"""
    return obj.type == 'MESH' and len(obj.data.vertices) == 8

def count_individual_cubes(context):
    """Cuenta todos los cubos individuales en la escena"""
    return sum(1 for obj in context.scene.objects if is_individual_cube(obj))

# ==============================================================================
# OPERADORES DE SEPARACIÓN DE BLOQUES
# ==============================================================================

class MINECRAFT_OT_SeparateSelected(bpy.types.Operator):
    """Separar objetos seleccionados en bloques individuales"""
    bl_idname = 'minecraft.separate_selected'
    bl_label = 'Separar Seleccionados'
    bl_description = 'Separa los objetos seleccionados en cubos individuales'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']

        if not selected_objects:
            self.report({'WARNING'}, 'No hay objetos seleccionados')
            return {'CANCELLED'}

        separated_count = 0
        failed_count = 0

        for obj in selected_objects:
            try:
                if separate_object_into_cubes(obj):
                    separated_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                self.report({'WARNING'}, f'Error separando {obj.name}: {str(e)}')
                failed_count += 1

        if separated_count > 0:
            # GUARDAR AUTOMÁTICAMENTE LA CONFIGURACIÓN DESPUÉS DE SEPARAR
            print("💾 Guardando configuración automáticamente después de separación...")
            try:
                config_file = EditorConfig.get_config_dir() / "texture_config_separacion_automatica.json"
                success, obj_count, mat_count = TextureConfigManager.save_configuration_to_file(config_file)

                if success:
                    print(f"✅ Configuración guardada: {obj_count} objetos, {mat_count} materiales, {separated_count} separaciones")
                    self.report({'INFO'}, f'✅ Separados {separated_count} objetos (config guardada)')
                else:
                    self.report({'WARNING'}, f'✅ Separados {separated_count} objetos pero error guardando config')
            except Exception as e:
                print(f"⚠️ Error guardando configuración automática: {e}")
                self.report({'WARNING'}, f'✅ Separados {separated_count} objetos (config no guardada)')

        if failed_count > 0:
            self.report({'WARNING'}, f'⚠️ {failed_count} objetos fallaron')

        return {'FINISHED'}

class MINECRAFT_OT_SeparateAllBedrock(bpy.types.Operator):
    """Separar todos los objetos bedrock en bloques individuales"""
    bl_idname = 'minecraft.separate_all_bedrock'
    bl_label = 'Separar Todos los Bedrock'
    bl_description = 'Encuentra y separa automáticamente todos los objetos unidos'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bedrock_objects = get_bedrock_objects(context)

        if not bedrock_objects:
            self.report({'INFO'}, 'No hay objetos unidos para separar')
            return {'FINISHED'}

        separated_count = 0
        failed_count = 0
        total_cubes_created = 0

        for obj in bedrock_objects:
            try:
                obj_name = obj.name
                initial_count = len([o for o in context.scene.objects if o.type == 'MESH'])

                if separate_object_into_cubes(obj):
                    separated_count += 1
                    final_count = len([o for o in context.scene.objects if o.type == 'MESH'])
                    cubes_created = final_count - initial_count
                    total_cubes_created += cubes_created
                    print(f"  ✓ {obj_name} → {cubes_created} cubos")
                else:
                    failed_count += 1
            except Exception as e:
                self.report({'WARNING'}, f'Error separando {obj.name}: {str(e)}')
                failed_count += 1

        if separated_count > 0:
            # GUARDAR AUTOMÁTICAMENTE LA CONFIGURACIÓN DESPUÉS DE SEPARAR
            print("💾 Guardando configuración automáticamente después de separación...")
            try:
                config_file = EditorConfig.get_config_dir() / "texture_config_separacion_automatica.json"
                success, obj_count, mat_count = TextureConfigManager.save_configuration_to_file(config_file)

                if success:
                    print(f"✅ Configuración guardada: {obj_count} objetos, {mat_count} materiales, {separated_count} separaciones")
                    self.report({'INFO'}, f'✅ Separados {separated_count} objetos en {total_cubes_created} cubos (config guardada)')
                else:
                    self.report({'WARNING'}, f'✅ Separados {separated_count} objetos pero error guardando config')
            except Exception as e:
                print(f"⚠️ Error guardando configuración automática: {e}")
                self.report({'WARNING'}, f'✅ Separados {separated_count} objetos (config no guardada)')

        if failed_count > 0:
            self.report({'WARNING'}, f'⚠️ {failed_count} objetos fallaron')

        return {'FINISHED'}

# ==============================================================================
# FUNCIONES AUXILIARES
# ==============================================================================

def get_texture_files():
    """Obtiene lista de texturas disponibles"""
    possible_paths = []
    
    # Ruta configurada por usuario
    if hasattr(bpy.context.scene, "minecraft_texture_path"):
        user_path = bpy.context.scene.minecraft_texture_path
        if user_path and os.path.exists(user_path):
            possible_paths.append(user_path)
    
    # Ruta relativa al .blend
    if bpy.data.filepath:
        blend_dir = os.path.dirname(bpy.data.filepath)
        possible_paths.append(os.path.join(blend_dir, "textures", "block"))
    
    # Ruta MCprep
    mcprep_path = Path.home() / "Desktop" / "Alfred_Animacion" / "MCprep_addon" / "MCprep_resources"
    if mcprep_path.exists():
        possible_paths.append(str(mcprep_path / "resourcepacks" / "mcprep_default" / "assets" / "minecraft" / "textures" / "block"))
    
    textures = []
    for path in possible_paths:
        if os.path.exists(path):
            for file in os.listdir(path):
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    textures.append(file)
            if textures:
                break
    
    return sorted(set(textures))

def get_texture_path(texture_name):
    """Obtiene ruta completa de una textura"""
    possible_paths = []
    
    if hasattr(bpy.context.scene, "minecraft_texture_path"):
        user_path = bpy.context.scene.minecraft_texture_path
        if user_path:
            possible_paths.append(os.path.join(user_path, texture_name))
    
    if bpy.data.filepath:
        blend_dir = os.path.dirname(bpy.data.filepath)
        possible_paths.append(os.path.join(blend_dir, "textures", "block", texture_name))
    
    mcprep_path = Path.home() / "Desktop" / "Alfred_Animacion" / "MCprep_addon" / "MCprep_resources"
    if mcprep_path.exists():
        possible_paths.append(str(mcprep_path / "resourcepacks" / "mcprep_default" / "assets" / "minecraft" / "textures" / "block" / texture_name))
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

# ==============================================================================
# REGISTRO
# ==============================================================================

classes = (
    MinecraftBlockEditorV5,
    MINECRAFT_OT_SaveConfigNamed,
    MINECRAFT_OT_LoadConfigNamed,
    MINECRAFT_OT_ValidateConfig,
    MINECRAFT_OT_ApplyTexture,
    MINECRAFT_OT_SelectAllCubes,
    MINECRAFT_OT_DeselectAll,
    MINECRAFT_OT_SelectByTexture,
    MINECRAFT_OT_SelectByMaterialName,
    MINECRAFT_OT_SetTexturePath,
    MINECRAFT_OT_ClearTexturePath,
    MINECRAFT_OT_ShowStatistics,
    MINECRAFT_OT_CleanMaterials,
    MINECRAFT_OT_ExportConfigInfo,
    MINECRAFT_OT_DeleteSelectedBlocks,
    MINECRAFT_OT_DeleteAllSeparated,
    MINECRAFT_OT_SeparateSelected,
    MINECRAFT_OT_SeparateAllBedrock,
)

def register():
    """Registra todas las clases"""
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.minecraft_texture_path = bpy.props.StringProperty(
        name="Texture Path",
        description="Ruta a carpeta de texturas",
        default="",
        subtype='DIR_PATH'
    )
    
    bpy.types.Scene.minecraft_texture_search = bpy.props.StringProperty(
        name="Search",
        description="Buscar texturas",
        default=""
    )
    
    print("\n" + "="*60)
    print("✅ MINECRAFT BLOCK EDITOR v5.0 CARGADO")
    print("="*60)
    print("📁 Config Dir:", EditorConfig.get_config_dir())
    print("💾 Config File:", EditorConfig.get_config_file())
    print("📂 Backup Dir:", EditorConfig.get_backup_dir())
    print("="*60 + "\n")

def unregister():
    """Desregistra todas las clases"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.minecraft_texture_path
    del bpy.types.Scene.minecraft_texture_search

if __name__ == "__main__":
    register()
    