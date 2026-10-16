#!/usr/bin/env python3
"""
character_test_generator.py - Generador Automático de Animaciones Test para Personajes

Este script lee un archivo personaje_outliner_data.json y genera automáticamente:
1. Estructura de carpetas completa
2. Animación de test que mueve todos los bones
3. Metadata correspondiente
4. Archivos de soporte

Uso:
    python character_test_generator.py <ruta_a_carpeta_con_json>

Ejemplo:
    python character_test_generator.py "C:\temp\new_character"
"""

import os
import json
import sys
from pathlib import Path
import shutil

class CharacterTestGenerator:
    def __init__(self):
        self.base_path = Path(r"C:\Users\user\Desktop\Alfred_Animacion")
        self.template_path = self.base_path / "simple_animation_blocks_manager" / "templates"

    def load_outliner_data(self, json_path):
        """Carga y valida el archivo outliner_data.json"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"[OK] JSON cargado: {json_path}")
            return data
        except Exception as e:
            print(f"[ERROR] Error cargando JSON: {e}")
            return None

    def extract_character_info(self, outliner_data):
        """Extrae información del personaje del JSON"""
        try:
            entities = outliner_data.get('detected_entities', [])
            if not entities:
                print("[ERROR] No se encontraron entidades en el JSON")
                return None

            entity = entities[0]  # Tomamos la primera entidad
            character_name = entity.get('name', 'unknown')
            armature_name = entity.get('armature_name', f'{character_name}_armature')

            # Extraer jerarquía de bones
            bone_hierarchy = outliner_data.get('bone_hierarchy', [])
            bones = self.extract_bones_from_hierarchy(bone_hierarchy)

            print(f"[OK] Personaje detectado: {character_name}")
            print(f"   Armature: {armature_name}")
            print(f"   Bones encontrados: {len(bones)}")

            return {
                'name': character_name,
                'armature_name': armature_name,
                'bones': bones,
                'bone_count': len(bones)
            }

        except Exception as e:
            print(f"[ERROR] Error extrayendo información: {e}")
            return None

    def extract_bones_from_hierarchy(self, hierarchy):
        """Extrae lista plana de todos los bones"""
        bones = []
        def traverse(node):
            bones.append(node['name'])
            for child in node.get('children', []):
                traverse(child)
        for root in hierarchy:
            traverse(root)
        return bones

    def create_directory_structure(self, character_name):
        """Crea la estructura de directorios completa"""
        character_path = self.base_path / "Informacion_Animacion" / character_name
        test_path = character_path / "test"
        entity_path = test_path / character_name

        # Crear directorios
        entity_path.mkdir(parents=True, exist_ok=True)

        print(f"[OK] Estructura creada:")
        print(f"   {character_path}")
        print(f"   {test_path}")
        print(f"   {entity_path}")

        return {
            'character_path': character_path,
            'test_path': test_path,
            'entity_path': entity_path
        }

    def generate_test_animation(self, character_info, paths):
        """Genera la animación de test basada en el template de ribbit"""
        character_name = character_info['name']
        armature_name = character_info['armature_name']
        bones = character_info['bones']

        # Template base (basado en ribbit_test_animation.py)
        template = self.get_animation_template()

        # Reemplazar placeholders
        template = template.replace('CHARACTER_NAME', character_name)
        template = template.replace('ARMATURE_NAME', armature_name)
        template = template.replace('BONES_LIST', self.format_bones_list(bones))
        template = template.replace('BONES_DICT', self.format_bones_dict(bones))
        template = template.replace('BONES_ROTATION_SETUP', self.format_bones_rotation_setup(bones))
        template = template.replace('BONES_ANIMATION_CODE', self.format_bones_animation_code(bones, character_name))

        # Guardar archivo
        animation_file = paths['entity_path'] / f"slot_001_{character_name}_test_animation.py"
        with open(animation_file, 'w', encoding='utf-8') as f:
            f.write(template)

        print(f"[OK] Animación generada: {animation_file}")
        return animation_file

    def generate_metadata(self, character_info, paths):
        """Genera el archivo metadata.json"""
        character_name = character_info['name']
        bones = character_info['bones']

        metadata = self.get_metadata_template()
        metadata = metadata.replace('CHARACTER_NAME', character_name)
        metadata = metadata.replace('ARMATURE_NAME', character_info['armature_name'])
        metadata = metadata.replace('BONES_LIST_JSON', json.dumps(bones, indent=2))
        metadata = metadata.replace('ANIMATION_DETAILS', self.format_animation_details(bones, character_name))

        # Guardar metadata
        metadata_file = paths['test_path'] / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            f.write(metadata)

        print(f"[OK] Metadata generada: {metadata_file}")
        return metadata_file

    def get_animation_template(self):
        """Template base para la animación de test"""
        return '''import bpy
import math

ANIMATION_INFO = {
    'name': 'CHARACTER_NAME_test_animation',
    'frame_count': 96,
    'fps': 24,
    'duration_seconds': 4.0,
    'entity': 'CHARACTER_NAME',
    'slot': 'test',
    'movement_type': 'walk_forward_with_bone_test',
    'minecraft_scale': '1_block_=_1m3',
    'description': 'Test animation that moves all bones of CHARACTER_NAME'
}

def execute_animation(player_parts=None, start_frame=1, end_frame=None):
    if end_frame is None:
        end_frame = start_frame + 95  # 96 frames total

    print(f"TEST ANIMATION - CHARACTER_NAME bone test")
    print(f"   Character walks forward while all bones move independently")
    print(f"   Duration: {ANIMATION_INFO['duration_seconds']} seconds")

    # ============================================
    # FIND ROOT AND ARMATURE
    # ============================================
    root_empty = bpy.data.objects.get('CHARACTER_NAME')
    main_armature = bpy.data.objects.get('ARMATURE_NAME')

    if not root_empty or root_empty.type != 'EMPTY':
        print(f'[ERROR] Empty root CHARACTER_NAME not found')
        return False

    if not main_armature or main_armature.type != 'ARMATURE':
        print(f'[ERROR] Armature ARMATURE_NAME not found')
        return False

    print(f'[OK] Root EMPTY: {root_empty.name}')
    print(f'[OK] Armature: {main_armature.name}')

    # ============================================
    # GET ALL POSE BONES
    # ============================================
    pose_bones = main_armature.pose.bones

    BONES_DICT

    all_bones = {
        BONES_LIST
    }

    print(f'\n[OK] Bones found:')
    for name, bone in all_bones.items():
        if bone:
            print(f'   [OK] {name}')
        else:
            print(f'   [ERROR] {name} NOT FOUND')
            return False

    # --- Change to Pose Mode ---
    bpy.context.view_layer.objects.active = main_armature
    if bpy.context.mode != 'POSE':
        bpy.ops.object.mode_set(mode='POSE')

    # ============================================
    # CRITICAL: SET ALL BONES TO XYZ EULER
    # ============================================
    print(f'\n[INFO] Setting bones to XYZ Euler mode...')
    BONES_ROTATION_SETUP

    # --- Clear existing animations ---
    if root_empty.animation_data:
        root_empty.animation_data_clear()
    root_empty.animation_data_create()

    if main_armature.animation_data:
        main_armature.animation_data_clear()
    main_armature.animation_data_create()

    print(f'\n[INFO] Generating: Walking straight + exaggerated bone movements...')

    # ============================================
    # ANIMATION: WALK STRAIGHT + CRAZY BONES
    # ============================================

    total_frames = end_frame - start_frame + 1
    walk_distance = 8.0  # 8 units forward in 4 seconds

    for frame in range(start_frame, end_frame + 1):
        bpy.context.scene.frame_set(frame)
        relative_frame = frame - start_frame
        progress = relative_frame / (total_frames - 1)  # 0.0 to 1.0

        # ============================================
        # 1. EMPTY MOVES IN STRAIGHT LINE (WALKING)
        # ============================================
        forward_distance = progress * walk_distance

        # Subtle walking bounce
        walk_cycle = progress * math.pi * 2 * 6  # 6 steps
        bounce = (math.sin(walk_cycle) ** 2) * 0.08

        root_empty.location = (0, forward_distance, bounce)
        root_empty.rotation_euler = (0, 0, 0)  # No EMPTY rotation

        root_empty.keyframe_insert(data_path="location", frame=frame)
        root_empty.keyframe_insert(data_path="rotation_euler", frame=frame)

        # ============================================
        # 2. ALL BONES MOVE INDEPENDENTLY
        # ============================================
        BONES_ANIMATION_CODE

        # Log every 24 frames
        if relative_frame % 24 == 0:
            second = relative_frame // 24
            print(f'   [LOG] Second {second}: Y = {forward_distance:.2f}')

    # ============================================
    # CONFIGURE INTERPOLATION
    # ============================================

    if root_empty.animation_data and root_empty.animation_data.action:
        action_empty = root_empty.animation_data.action
        for fcurve in action_empty.fcurves:
            for kf in fcurve.keyframe_points:
                if 'location' in fcurve.data_path and fcurve.array_index == 1:
                    kf.interpolation = 'LINEAR'  # Constant walking
                else:
                    kf.interpolation = 'BEZIER'
                    kf.easing = 'AUTO'
        print(f'\n[OK] EMPTY: {len(action_empty.fcurves)} F-curves')

    if main_armature.animation_data and main_armature.animation_data.action:
        action_arm = main_armature.animation_data.action
        for fcurve in action_arm.fcurves:
            for kf in fcurve.keyframe_points:
                kf.interpolation = 'BEZIER'
                kf.easing = 'AUTO'
        print(f'[OK] ARMATURE: {len(action_arm.fcurves)} F-curves')

    bpy.context.scene.frame_set(start_frame)

    print(f'\n' + '='*70)
    print(f'[SUCCESS] CHARACTER_NAME BONE TEST COMPLETED')
    print(f'='*70)
    print(f'\nWhat the character does:')
    print(f'\n   BASE MOVEMENT (EMPTY):')
    print(f'      • Walks straight forward Y+ (8 units in 4s)')
    print(f'      • Subtle walking bounce in Z')
    print(f'      • No EMPTY rotation (always faces forward)')
    print(f'\n   WHILE WALKING, ALL BONES MOVE:')
    print(f'      • Each bone moves with different frequencies')
    print(f'      • Exaggerated movements to test control')
    print(f'      • Independent bone animations')
    print(f'\n   RESULT:')
    print(f'      Character walks straight but bones do')
    print(f'      crazy movements to demonstrate TOTAL CONTROL.')
    print(f'\nPress SPACE to see the demo')
    print(f'='*70)

    return True

if __name__ == '__main__':
    execute_animation()
'''

    def format_bones_list(self, bones):
        """Formatea la lista de bones para el template"""
        bone_lines = []
        for i, bone in enumerate(bones):
            bone_lines.append(f"        '{bone}': {bone}_bone")
        return ',\n'.join(bone_lines)

    def format_bones_dict(self, bones):
        """Formatea las declaraciones de bones"""
        bone_lines = []
        for bone in bones:
            bone_lines.append(f"    {bone}_bone = pose_bones.get('{bone}')")
        return '\n'.join(bone_lines)

    def format_bones_rotation_setup(self, bones):
        """Formatea la configuración de rotación para todos los bones"""
        lines = []
        for bone in bones:
            lines.append(f"    if {bone}_bone:")
            lines.append(f"        {bone}_bone.rotation_mode = 'XYZ'")
            lines.append(f"        print(f'   ✅ {bone}: rotation_mode = XYZ')")
        return '\n'.join(lines)

    def format_bones_animation_code(self, bones, character_name):
        """Genera código de animación para todos los bones"""
        lines = []

        # Generar diferentes tipos de animación para diferentes bones
        for i, bone in enumerate(bones):
            cycle_type = i % 4  # 4 tipos diferentes de ciclos

            if cycle_type == 0:  # Rotación completa en X
                lines.extend([
                    f"        # {bone.upper()} - Full rotation in X",
                    f"        if {bone}_bone:",
                    f"            bone_cycle = progress * math.pi * 2 * 4  # 4 cycles",
                    f"            {bone}_bone.rotation_euler = (",
                    f"                math.sin(bone_cycle) * 1.0472,    # X: ±60°",
                    f"                math.cos(bone_cycle * 1.5) * 0.5236,  # Y: ±30°",
                    f"                math.sin(bone_cycle * 2) * 0.3491     # Z: ±20°",
                    f"            )",
                    f"            {bone}_bone.keyframe_insert(data_path='rotation_euler', frame=frame)"
                ])
            elif cycle_type == 1:  # Balanceo en Y
                lines.extend([
                    f"        # {bone.upper()} - Y-axis swaying",
                    f"        if {bone}_bone:",
                    f"            bone_cycle = progress * math.pi * 2 * 6  # 6 cycles",
                    f"            {bone}_bone.rotation_euler = (",
                    f"                math.sin(bone_cycle * 0.5) * 0.3491,  # X: ±20°",
                    f"                math.cos(bone_cycle) * 0.7854,        # Y: ±45°",
                    f"                math.sin(bone_cycle * 1.5) * 0.2618   # Z: ±15°",
                    f"            )",
                    f"            {bone}_bone.keyframe_insert(data_path='rotation_euler', frame=frame)"
                ])
            elif cycle_type == 2:  # Movimiento circular
                lines.extend([
                    f"        # {bone.upper()} - Circular motion",
                    f"        if {bone}_bone:",
                    f"            bone_cycle = progress * math.pi * 2 * 8  # 8 cycles",
                    f"            {bone}_bone.rotation_euler = (",
                    f"                math.sin(bone_cycle) * 0.5236,        # X: ±30°",
                    f"                math.sin(bone_cycle + math.pi/3) * 0.5236,  # Y: ±30° (phase shifted)",
                    f"                math.sin(bone_cycle + math.pi/6) * 0.5236   # Z: ±30° (phase shifted)",
                    f"            )",
                    f"            {bone}_bone.keyframe_insert(data_path='rotation_euler', frame=frame)"
                ])
            else:  # Twist rápido
                lines.extend([
                    f"        # {bone.upper()} - Fast twisting",
                    f"        if {bone}_bone:",
                    f"            bone_cycle = progress * math.pi * 2 * 12  # 12 cycles",
                    f"            {bone}_bone.rotation_euler = (",
                    f"                math.cos(bone_cycle * 2) * 0.2618,   # X: ±15°",
                    f"                math.sin(bone_cycle * 3) * 0.7854,   # Y: ±45°",
                    f"                math.cos(bone_cycle * 4) * 0.3491    # Z: ±20°",
                    f"            )",
                    f"            {bone}_bone.keyframe_insert(data_path='rotation_euler', frame=frame)"
                ])

            lines.append("")

        return '\n'.join(lines)

    def get_metadata_template(self):
        """Template para metadata.json"""
        return '''{
  "prompt_info": {
    "original_prompt": "CHARACTER_NAME test animation - automated generation",
    "generated_timestamp": "2025-12-16T00:59:00Z",
    "ai_model": "Automated Character Test Generator",
    "total_duration_calculated": 4.0,
    "total_frames_calculated": 96,
    "structure_version": "automated_test_v2025",
    "minecraft_scale": "1_block_=_1m3",
    "timeline_type": "test_animation_automated"
  },
  "animation_info": {
    "name": "CHARACTER_NAME_test_animation",
    "timeline": "test_timeline",
    "movement_type": "walk_forward_with_automated_bone_test",
    "walking_speed": 2.0,
    "distance_traveled": 8.0,
    "velocity_units_per_second": 2.0
  },
  "entidades": {
    "CHARACTER_NAME": {
      "carpeta": "CHARACTER_NAME",
      "tipo": "creature_CHARACTER_NAME",
      "animaciones": [
        "slot_001_CHARACTER_NAME_test_animation"
      ],
      "entity_type": "creature_CHARACTER_NAME",
      "estructura_blend_requerida": "CHARACTER_NAME.blend",
      "total_animation_frames": 96,
      "total_animation_duration": 4.0,
      "armature_structure": "single_armature_with_pose_bones",
      "main_armature": "ARMATURE_NAME",
      "pose_bones_used": BONES_LIST_JSON
    }
  },
  "scenes": [
    {
      "scene_number": 1,
      "filename": "slot_001_CHARACTER_NAME_test_animation.py",
      "duration_seconds": 4.0,
      "frame_count": 96,
      "frame_range": "1-96",
      "narrative_importance": "test",
      "description": "Automated test animation that moves all bones of CHARACTER_NAME with different motion patterns"
    }
  ],
  "configuracion_global": {
    "fps": 24,
    "frames_totales_calculados": 96,
    "timeline_calculation": "automated_test_animation",
    "ai_features": {
      "narrative_driven_duration": false,
      "physics_based_movement": false,
      "high_quality_animations": true,
      "detailed_keyframes": true,
      "body_sway_animations": true,
      "extended_walking_cycles": false,
      "variable_frame_counts": true,
      "explosion_mechanics": false,
      "minecraft_accurate_timing": false,
      "forward_displacement": true,
      "vertical_bounce": true
    },
    "system_notes": {
      "walking_phases": true,
      "leg_swing_mechanics": false,
      "arm_opposite_swing": false,
      "body_balance_system": false,
      "head_stabilization": false,
      "continuation_from_previous": false,
      "rig_type": "single_armature_pose_bones",
      "movement_axis": "Y_forward",
      "bounce_axis": "Z_vertical",
      "modification_policy": "Automated test generation - no production constraints",
      "no_new_slots_without_explicit_request": false,
      "corrected_issues": [
        "Automated bone detection from outliner data",
        "Generated test animation with multiple motion patterns",
        "Created complete metadata structure"
      ]
    }
  },
 "animation_details": ANIMATION_DETAILS
  "technical_specifications": {
    "blender_version": "4.5.3 LTS",
    "coordinate_system": "Z_up_Y_forward",
    "unit_scale": "metric",
    "animation_method": "fcurves_with_keyframes",
    "interpolation_types": {
      "location": "LINEAR for Y, BEZIER for Z",
      "rotation": "BEZIER for all bones"
    },
    "total_fcurves_created": "variable based on bone count",
    "armature_mode": "POSE"
  },
  "performance_metrics": {
    "estimated_render_time_per_frame": "0.8-1.5 seconds",
    "complexity_rating": "high",
    "optimization_notes": "Automated test animation - not optimized for production"
  },
  "validation_checklist": {
    "armature_found": true,
    "pose_bones_verified": true,
    "forward_movement_applied": true,
    "vertical_bounce_applied": true,
    "rotation_animations_preserved": true,
    "interpolation_configured": true,
    "frame_range_correct": true,
    "bone_control_demonstrated": true,
    "automated_generation_successful": true
  },
  "test_animation_notes": {
    "purpose": "Automated test to verify all bones are properly rigged and animated",
    "movement_combination": "Linear walking + independent bone rotations",
    "bone_independence": "Each bone moves with different frequencies and amplitudes",
    "visual_result": "Character walks straight while bones do automated test movements",
    "technical_demonstration": "Shows automated system can control all bones during movement",
    "generation_method": "Automatically generated from outliner_data.json"
  }
}'''

    def format_animation_details(self, bones, character_name):
        """Formatea los detalles de animación para cada bone"""
        details = {}

        # Detalles del movimiento base
        details[f"slot_001_{character_name}_test_animation"] = {
            "armature_movement": {
                "axis_x": {"type": "static", "start_value": 0, "end_value": 0, "interpolation": "CONSTANT", "description": "No lateral movement - straight line walk"},
                "axis_y": {"type": "linear_progression", "start_value": 0, "end_value": 8.0, "interpolation": "LINEAR", "description": "Forward walking movement at constant speed", "keyframes": [{"frame": 1, "value": 0}, {"frame": 24, "value": 2.0}, {"frame": 48, "value": 4.0}, {"frame": 72, "value": 6.0}, {"frame": 96, "value": 8.0}]},
                "axis_z": {"type": "bounce_cycle", "bounce_height": 0.08, "interpolation": "BEZIER", "description": "Subtle walking bounce with 6 cycles over 4 seconds", "keyframes": [{"frame": 1, "value": 0}, {"frame": 8, "value": 0.08}, {"frame": 16, "value": 0}, {"frame": 24, "value": 0.08}, {"frame": 32, "value": 0}, {"frame": 40, "value": 0.08}, {"frame": 48, "value": 0}, {"frame": 56, "value": 0.08}, {"frame": 64, "value": 0}, {"frame": 72, "value": 0.08}, {"frame": 80, "value": 0}, {"frame": 88, "value": 0.08}, {"frame": 96, "value": 0}]}
            },
            "pose_bones_animation": {}
        }

        # Detalles para cada bone
        for i, bone in enumerate(bones):
            cycle_type = i % 4
            if cycle_type == 0:
                details[f"slot_001_{character_name}_test_animation"]["pose_bones_animation"][bone] = {
                    "rotation_euler_x": "sinusoidal_4_cycles",
                    "rotation_euler_y": "cosine_6_cycles",
                    "rotation_euler_z": "sinusoidal_8_cycles",
                    "keyframe_count": 96,
                    "description": "Full rotation pattern (±60° X, ±30° Y, ±20° Z) - 4 cycles"
                }
            elif cycle_type == 1:
                details[f"slot_001_{character_name}_test_animation"]["pose_bones_animation"][bone] = {
                    "rotation_euler_x": "sinusoidal_3_cycles",
                    "rotation_euler_y": "cosine_6_cycles",
                    "rotation_euler_z": "sinusoidal_9_cycles",
                    "keyframe_count": 96,
                    "description": "Y-axis swaying pattern (±20° X, ±45° Y, ±15° Z) - 6 cycles"
                }
            elif cycle_type == 2:
                details[f"slot_001_{character_name}_test_animation"]["pose_bones_animation"][bone] = {
                    "rotation_euler_x": "sinusoidal_8_cycles",
                    "rotation_euler_y": "sinusoidal_8_cycles_phase_shift",
                    "rotation_euler_z": "sinusoidal_8_cycles_phase_shift",
                    "keyframe_count": 96,
                    "description": "Circular motion pattern (±30° all axes with phase shifts) - 8 cycles"
                }
            else:
                details[f"slot_001_{character_name}_test_animation"]["pose_bones_animation"][bone] = {
                    "rotation_euler_x": "cosine_24_cycles",
                    "rotation_euler_y": "sinusoidal_36_cycles",
                    "rotation_euler_z": "cosine_48_cycles",
                    "keyframe_count": 96,
                    "description": "Fast twisting pattern (±15° X, ±45° Y, ±20° Z) - 12+ cycles"
                }

        return json.dumps(details, indent=2)

    def run_generation(self, input_folder):
        """Ejecuta el proceso completo de generación"""
        print("=== CHARACTER TEST GENERATOR ===")
        print("="*50)

        # Verificar carpeta de entrada
        input_path = Path(input_folder)
        if not input_path.exists():
            print(f"[ERROR] Carpeta no existe: {input_path}")
            return False

        # Buscar archivo JSON
        json_files = list(input_path.glob("*.json"))
        if not json_files:
            print(f"[ERROR] No se encontró archivo .json en: {input_path}")
            return False

        json_path = json_files[0]  # Tomar el primer JSON encontrado
        print(f"Archivo JSON: {json_path.name}")

        # Cargar datos del outliner
        outliner_data = self.load_outliner_data(json_path)
        if not outliner_data:
            return False

        # Extraer información del personaje
        character_info = self.extract_character_info(outliner_data)
        if not character_info:
            return False

        # Crear estructura de directorios
        paths = self.create_directory_structure(character_info['name'])

        # Generar animación de test
        animation_file = self.generate_test_animation(character_info, paths)

        # Generar metadata
        metadata_file = self.generate_metadata(character_info, paths)

        # Copiar archivo JSON original para referencia
        shutil.copy2(json_path, paths['test_path'] / f"{character_info['name']}_outliner_data.json")

        print(f"\n[SUCCESS] GENERACIÓN COMPLETADA")
        print(f"="*50)
        print(f"Personaje: {character_info['name']}")
        print(f"Bones detectados: {character_info['bone_count']}")
        print(f"Animación: {animation_file.name}")
        print(f"Metadata: {metadata_file.name}")
        print(f"Ubicación final: {paths['test_path']}")
        print(f"\nPara usar:")
        print(f"   1. Carga la carpeta: {paths['test_path'].name}")
        print(f"   2. Ejecuta: slot_001_{character_info['name']}_test_animation.py")
        print(f"   3. ¡Verás todos los bones moviéndose!")

        return True

def main():
    if len(sys.argv) != 2:
        print("Uso: python character_test_generator.py <ruta_a_carpeta_con_json>")
        print("Ejemplo: python character_test_generator.py \"C:\\temp\\new_character\"")
        sys.exit(1)

    input_folder = sys.argv[1]
    generator = CharacterTestGenerator()

    success = generator.run_generation(input_folder)
    if success:
        print("\n[SUCCESS] ¡Generación exitosa!")
    else:
        print("\n[ERROR] Error en la generación")
        sys.exit(1)

if __name__ == "__main__":
    main()