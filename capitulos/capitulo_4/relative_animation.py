#!/usr/bin/env python3
"""
relative_animation.py - Sistema de animación relativa y detección de orientación
Contiene CharacterOrientationDetector y RelativeAnimationEngine
"""

import bpy
import os
import json
import datetime
import math
import mathutils

# ============================================================================
# SISTEMA DE ANIMACIÓN RELATIVA - DETECCIÓN DE ORIENTACIÓN
# ============================================================================

class CharacterOrientationDetector:
    """Detecta y almacena la orientación base de cualquier personaje"""

    def __init__(self):
        self.base_states = {}  # {entity_name: base_state}

    def capture_base_state(self, entity_name: str) -> dict:
        """Captura el estado base completo del personaje en tiempo=0"""
        try:
            print(f"📐 CAPTURANDO ESTADO BASE para {entity_name}")

            base_state = {
                'timestamp': datetime.datetime.now().isoformat(),
                'entity_name': entity_name,
                'position': None,
                'rotation': None,
                'forward_vector': None,
                'right_vector': None,
                'up_vector': None,
                'facing_angle': 0.0,
                'armature_object': None
            }

            # Buscar el armature principal de la entidad
            armature_obj = self._find_entity_armature(entity_name)
            if not armature_obj:
                print(f"⚠️ No se encontró armature para {entity_name}")
                return None

            base_state['armature_object'] = armature_obj.name

            # Capturar posición y rotación
            base_state['position'] = list(armature_obj.location)
            base_state['rotation'] = list(armature_obj.rotation_euler)

            # Calcular vectores de orientación
            base_state['forward_vector'] = self.calculate_forward_vector(armature_obj)
            base_state['right_vector'] = self.calculate_right_vector(armature_obj)
            base_state['up_vector'] = self.calculate_up_vector(armature_obj)
            base_state['facing_angle'] = self.get_facing_angle(armature_obj)

            # Almacenar estado base
            self.base_states[entity_name] = base_state

            print(f"✅ Estado base capturado: ángulo {base_state['facing_angle']:.1f}°, posición {base_state['position']}")
            return base_state

        except Exception as e:
            print(f"❌ Error capturando estado base para {entity_name}: {e}")
            return None

    def calculate_forward_vector(self, armature) -> list:
        """Calcula el vector forward basado en la rotación del armature"""
        rotation_matrix = armature.rotation_euler.to_matrix()
        # En Blender, forward es -Z por defecto
        default_forward = mathutils.Vector((0, 0, -1))
        forward = rotation_matrix @ default_forward
        return list(forward)

    def calculate_right_vector(self, armature) -> list:
        """Calcula el vector right basado en la rotación del armature"""
        rotation_matrix = armature.rotation_euler.to_matrix()
        # En Blender, right es +X por defecto
        default_right = mathutils.Vector((1, 0, 0))
        right = rotation_matrix @ default_right
        return list(right)

    def calculate_up_vector(self, armature) -> list:
        """Calcula el vector up basado en la rotación del armature"""
        rotation_matrix = armature.rotation_euler.to_matrix()
        # En Blender, up es +Z por defecto
        default_up = mathutils.Vector((0, 0, 1))
        up = rotation_matrix @ default_up
        return list(up)

    def get_facing_angle(self, armature) -> float:
        """Calcula el ángulo de orientación en grados"""
        # El ángulo Y (alrededor del eje Z) determina la dirección de facing
        angle_rad = armature.rotation_euler.z
        angle_deg = math.degrees(angle_rad)
        # Normalizar a 0-360 grados
        angle_deg = angle_deg % 360
        return angle_deg

    def _find_entity_armature(self, entity_name: str):
        """Encuentra el armature principal de una entidad"""
        # Buscar por nombre de entidad
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                obj_name = obj.name.lower()
                entity_lower = entity_name.lower()

                # Coincidencia directa
                if entity_lower in obj_name:
                    return obj

                # Coincidencia con prefijo
                if obj_name.startswith(entity_lower):
                    return obj

        # Si no se encuentra, buscar cualquier armature que pueda pertenecer a la entidad
        from .core_system import blocks_manager
        if entity_name in blocks_manager.entities:
            entity_data = blocks_manager.entities[entity_name]
            scene_objects = entity_data.get('scene_objects', [])
            for obj_name in scene_objects:
                if obj_name in bpy.data.objects:
                    obj = bpy.data.objects[obj_name]
                    if obj.type == 'ARMATURE':
                        return obj

        return None

    def get_base_state(self, entity_name: str) -> dict:
        """Retorna el estado base de una entidad"""
        return self.base_states.get(entity_name)

class RelativeAnimationEngine:
    """Motor de animación relativa que adapta movimientos según orientación base"""

    def __init__(self, orientation_detector):
        self.orientation_detector = orientation_detector
        self.narrative_mode = False  # True = narrativa sobre coherencia visual

    def adapt_animation_to_orientation(self, animation_block: dict, entity_name: str, start_frame: int, end_frame: int) -> dict:
        """Adapta la animación según la orientación base del personaje"""
        try:
            base_state = self.orientation_detector.get_base_state(entity_name)
            if not base_state:
                print(f"⚠️ No hay estado base para {entity_name}, usando animación sin adaptación")
                return animation_block

            print(f"🔄 Adaptando animación '{animation_block['name']}' para {entity_name} (ángulo base: {base_state['facing_angle']:.1f}°)")

            # Crear copia adaptada del bloque
            adapted_block = animation_block.copy()

            # Marcar que fue adaptada
            adapted_block['adapted_for_orientation'] = True
            adapted_block['base_orientation_used'] = base_state['facing_angle']
            adapted_block['original_animation'] = animation_block['name']

            # Aplicar transformaciones narrativas si está activado el modo narrativa
            if self.narrative_mode:
                adapted_block = self.apply_narrative_transforms(base_state, adapted_block)

            # Validación específica para Alfred si es necesario
            if entity_name.lower() == 'alfred' and self.alfred_hybrid_system_enabled:
                adapted_block = self.ensure_alfred_hybrid_compliance(adapted_block)

            return adapted_block

        except Exception as e:
            print(f"❌ Error adaptando animación para {entity_name}: {e}")
            return animation_block

    def apply_narrative_transforms(self, base_state: dict, animation_data: dict) -> dict:
        """Aplica transformaciones narrativas (movimientos expresivos)"""
        if not self.narrative_mode:
            return animation_data

        print("🎭 Aplicando transformaciones narrativas - expresividad sobre coherencia")

        # Crear copia para modificar
        transformed = animation_data.copy()

        # Aplicar transformaciones narrativas:
        # - Movimientos más amplios para expresividad
        # - Orientaciones arbitrarias para narrativa
        # - Velocidades variables para dramatismo

        # Ejemplo: Amplificar movimientos
        if 'frame_count' in transformed:
            # Pequeño aumento en duración para movimientos más expresivos
            transformed['frame_count'] = int(transformed['frame_count'] * 1.1)

        # Marcar como narrativa
        transformed['narrative_transforms_applied'] = True

        return transformed

    def validate_alfred_hybrid_system(self, animation_code: str) -> bool:
        """Valida sistema híbrido obligatorio para Alfred"""
        import re
        required_patterns = [
            r"body_pos\.y = forward_movement\s*# OVERRIDE ABSOLUTO",
            r"head_pos\.y = forward_movement\s*# OVERRIDE ABSOLUTO",
            r"left_arm_pos\.y = forward_movement\s*# OVERRIDE ABSOLUTO",
            r"right_arm_pos\.y = forward_movement\s*# OVERRIDE ABSOLUTO",
            r"left_leg_pos\.y = forward_movement\s*# OVERRIDE ABSOLUTO",
            r"right_leg_pos\.y = forward_movement\s*# OVERRIDE ABSOLUTO",
            r"global_offset.*forward_movement",
            r"initial_positions.*body.*head.*arm.*leg"
        ]

        for pattern in required_patterns:
            if not re.search(pattern, animation_code, re.MULTILINE | re.DOTALL):
                return False
        return True

    def ensure_alfred_hybrid_compliance(self, animation_block):
        """Asegura que el bloque de animación cumpla con el sistema híbrido de Alfred"""
        # Si el bloque ya tiene código, validarlo
        if 'code' in animation_block and animation_block['code']:
            if not self.validate_alfred_hybrid_system(animation_block['code']):
                print(f"⚠️ Animación para Alfred no cumple con sistema híbrido, aplicando correcciones")
                animation_block = self.apply_alfred_hybrid_fixes(animation_block)

        # Marcar el bloque como compatible con sistema híbrido
        animation_block['alfred_hybrid_compatible'] = True
        return animation_block

    def apply_alfred_hybrid_fixes(self, animation_block):
        """Aplica correcciones al código para hacerlo compatible con sistema híbrido de Alfred"""
        # Obtener el código actual
        code = animation_block.get('code', '')

        # Verificar si ya tiene los patrones necesarios
        if not "# OVERRIDE ABSOLUTO" in code:
            # Buscar sección donde se manipulan las posiciones
            import re
            position_section = re.search(r'(# .*posiciones.*\n.*\n)', code, re.IGNORECASE | re.MULTILINE)

            if position_section:
                # Insertar código de override absoluto
                hybrid_code = """
    # OVERRIDE ABSOLUTO OBLIGATORIO PARA ALFRED
    body_pos.y = forward_movement      # OVERRIDE ABSOLUTO
    head_pos.y = forward_movement      # OVERRIDE ABSOLUTO
    left_arm_pos.y = forward_movement  # OVERRIDE ABSOLUTO
    right_arm_pos.y = forward_movement # OVERRIDE ABSOLUTO
    left_leg_pos.y = forward_movement  # OVERRIDE ABSOLUTO
    right_leg_pos.y = forward_movement # OVERRIDE ABSOLUTO

    # Almacenar posiciones iniciales
    initial_positions = {
        'body': body_armature.location.copy(),
        'head': head_armature.location.copy(),
        'left_arm': left_arm_armature.location.copy(),
        'right_arm': right_arm_armature.location.copy(),
        'left_leg': left_leg_armature.location.copy(),
        'right_leg': right_leg_armature.location.copy()
    }
"""
                # Insertar después de la sección de posiciones
                insert_pos = position_section.end()
                code = code[:insert_pos] + hybrid_code + code[insert_pos:]

                # Actualizar el código en el bloque
                animation_block['code'] = code
                print("✅ Código actualizado con sistema híbrido para Alfred")

        return animation_block

    def calculate_relative_movement(self, base_forward: mathutils.Vector, animation_movement: dict) -> dict:
        """Calcula movimiento relativo a la orientación base"""
        # Esta función calcula cómo debe transformarse el movimiento
        # basado en la orientación del personaje

        relative_movement = animation_movement.copy()

        # Aplicar rotación relativa
        if 'rotation_offset' in animation_movement:
            # Ajustar rotación según orientación base
            base_angle = math.atan2(base_forward.y, base_forward.x)
            relative_movement['adjusted_rotation'] = animation_movement['rotation_offset'] + math.degrees(base_angle)

        return relative_movement

# ============================================================================
# FUNCIONES DE SOPORTE
# ============================================================================

def show_translation_examples():
    """Muestra ejemplos de traducciones disponibles para debugging"""
    from .translation_system import show_translation_examples as _show_translation_examples
    return _show_translation_examples()

# ============================================================================
# REGISTRO DEL MÓDULO
# ============================================================================

def register():
    """Registra el sistema de animación relativa"""
    print("✅ Sistema de animación relativa registrado correctamente")

def unregister():
    """Desregistra el sistema de animación relativa"""
    print("✅ Sistema de animación relativa desregistrado correctamente")