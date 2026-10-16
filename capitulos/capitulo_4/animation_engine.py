#!/usr/bin/env python3
"""
animation_engine.py - Motor de Animación del Simple Animation Blocks Manager
Contiene los operadores y la lógica para manipular los bloques de animación.
"""

import bpy
import os
import json
try:
    from .core_system import get_blocks_manager
except ImportError:
    # Fallback para importación dinámica
    def get_blocks_manager():
        return None

def execute_animation_block(block, start_frame, end_frame, player_parts):
    """
    Ejecuta un bloque de animación específico

    Args:
        block: Diccionario del bloque de animación con 'name', 'frame_count', etc.
        start_frame: Frame inicial para la animación
        end_frame: Frame final para la animación
        player_parts: Diccionario con las partes del cuerpo mapeadas

    Returns:
        bool: True si la ejecución fue exitosa
    """
    try:
        # Verificar que el bloque tiene la información necesaria
        if not block or 'name' not in block:
            print(f"❌ Bloque de animación inválido: {block}")
            return False

        print(f"🎬 Ejecutando bloque '{block['name']}' (frames {start_frame}-{end_frame})")

        # Verificar que tenemos las partes necesarias
        if not player_parts:
            print("❌ No se proporcionaron partes del cuerpo")
            return False

        # Obtener la función execute_animation del bloque
        execute_func = block.get('execute_function')
        if not execute_func:
            print(f"❌ No se encontró función execute_animation en el bloque '{block['name']}'")
            return False

        # Verificar que la función es callable
        if not callable(execute_func):
            print(f"❌ La función execute_animation no es ejecutable: {type(execute_func)}")
            return False

        # Ejecutar la animacion con los parametros correctos
        print(f"Llamando execute_animation con player_parts y frames {start_frame}-{end_frame}")

        # RESOLUCION DE BODY: si player_parts no tiene 'body' (o es None),
        # buscarlo en la escena usando el nombre de la entidad antes de llamar
        # al slot.  Esto evita que slots de Jerry caigan al fallback Dog_001_rig
        # cuando se ejecutan para Alfred u otra entidad.
        player_parts_resolved = dict(player_parts) if player_parts else {}
        if not player_parts_resolved.get('body'):
            entity_name = block.get('entity_name', '')
            resolved_body = None
            if entity_name:
                entity_lower = entity_name.lower()
                # 1) Buscar armature cuyo nombre contenga el nombre de la entidad
                for obj in bpy.data.objects:
                    if obj.type == 'ARMATURE' and entity_lower in obj.name.lower():
                        resolved_body = obj
                        break
                # 2) Si no, buscar armature hijo del root 'main' de la entidad
                if resolved_body is None:
                    root_obj = player_parts_resolved.get('main')
                    if root_obj:
                        for obj in bpy.data.objects:
                            if obj.type == 'ARMATURE' and obj.parent == root_obj:
                                resolved_body = obj
                                break
            # 3) Unico armature en escena (solo si hay exactamente uno)
            if resolved_body is None:
                all_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE']
                if len(all_arm) == 1:
                    resolved_body = all_arm[0]
            if resolved_body:
                print(f"  body resuelto para '{entity_name}': {resolved_body.name}")
                player_parts_resolved['body'] = resolved_body
            else:
                print(f"  Advertencia: no se pudo resolver 'body' para '{entity_name}'")

        # La funcion execute_animation espera (player_parts, start_frame, end_frame)
        result = execute_func(player_parts_resolved, start_frame, end_frame)

        if result:
            print(f"✅ Bloque '{block['name']}' ejecutado exitosamente")
            return True
        else:
            print(f"❌ Error en la ejecución del bloque '{block['name']}'")
            return False

    except Exception as e:
        print(f"❌ Error ejecutando bloque de animación '{block.get('name', 'unknown')}': {e}")
        import traceback
        traceback.print_exc()
        return False

class ANIMATION_OT_load_animation_block(bpy.types.Operator):
    """Carga un bloque de animación desde un archivo .py"""
    bl_idname = "animation.load_block"
    bl_label = "Load Animation Block"
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    slot: bpy.props.IntProperty()

    def execute(self, context):
        manager = get_blocks_manager()
        # Lógica para cargar el bloque de animación
        print(f"Cargando bloque desde {self.filepath} en el slot {self.slot}")
        return {'FINISHED'}

def register():
    """Registra las clases del motor de animación"""
    try:
        bpy.utils.register_class(ANIMATION_OT_load_animation_block)
        print("✅ Motor de animación registrado correctamente")
    except Exception as e:
        print(f"❌ Error registrando motor de animación: {e}")

def unregister():
    """Desregistra las clases del motor de animación"""
    try:
        bpy.utils.unregister_class(ANIMATION_OT_load_animation_block)
        print("✅ Motor de animación desregistrado correctamente")
    except Exception as e:
        print(f"❌ Error desregistrando motor de animación: {e}")