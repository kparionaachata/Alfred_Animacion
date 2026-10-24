# -*- coding: utf-8 -*-
"""
slot_001_parado_2.py
Alfred parado_2 - Animación importada desde Mixamo
Compatible con Nueva estructura/alfred.blend
Sistema jerárquico con Mixamo rig

GENERADO AUTOMÁTICAMENTE desde: Armature|mixamo.com|Layer0
Frames originales: 1-30
Bones animados: 10
Fecha de generación: 2026-01-14 02:44:37
"""

import bpy

def _action_fcurves(action):
    """Devuelve curvas de acciones antiguas y de acciones por capas de Blender 5."""
    if action is None:
        return ()
    legacy = getattr(action, "fcurves", None)
    if legacy is not None:
        return legacy
    curves = []
    for layer in getattr(action, "layers", ()):
        for strip in getattr(layer, "strips", ()):
            for channelbag in getattr(strip, "channelbags", ()):
                curves.extend(channelbag.fcurves)
    return curves

import math

ANIMATION_INFO = {
    'name': 'slot_001_alfred_parado_2_mixamo',
    'frame_count': 30,
    'fps': 24,
    'duration_seconds': 1.25,
    'entity': 'Alfred',
    'slot': 1,
    'movement_type': 'parado_2_mixamo',
    'minecraft_scale': '1_block_=_1m3',
    'narrative_importance': 'ambient',
    'rig_type': 'mixamo_hierarchy',
    'source': 'mixamo_imported',
    'bones_animated': 10,
    'animation_type': 'idle'
}

# ✅ Datos de keyframes extraídos de Mixamo
KEYFRAME_DATA = {
    'LeftUpArm_alfred': {
        'rotation': {
            1: (1.570796, -0.000000, 0.000000),
            30: (1.570796, -0.000000, 0.000000),
        },
        'location': {
            1: (0.013552, 0.074613, -0.085881),
            30: (0.013552, 0.074613, -0.085881),
        }
    },
    'LeftUpLeg_alfred': {
        'rotation': {
            1: (0.000000, 0.000000, 0.000000),
            30: (0.000000, 0.000000, 0.000000),
        }
    },
    'Leftelbow_alfred': {
        'rotation': {
            1: (0.000000, 0.000000, 0.334451),
            30: (0.000000, 0.000000, 0.334451),
        }
    },
    'Leftknee_alfred': {
        'rotation': {
            1: (0.000000, 0.000000, 0.000000),
            30: (0.000000, 0.000000, 0.000000),
        }
    },
    'Neck_alfred': {
        'rotation': {
            1: (-0.000218, 0.009256, 0.000000),
            30: (-0.000218, 0.009256, 0.000000),
        }
    },
    'RightUpArm_alfred': {
        'rotation': {
            1: (1.570796, -0.000000, 0.000000),
            30: (1.570796, -0.000000, 0.000000),
        },
        'location': {
            1: (0.006604, 0.096746, -0.086079),
            30: (0.006604, 0.096746, -0.086079),
        }
    },
    'RightUpLeg_alfred': {
        'rotation': {
            1: (0.000000, 0.000000, 0.000000),
            30: (0.000000, 0.000000, 0.000000),
        }
    },
    'Rightelbow_alfred': {
        'rotation': {
            1: (0.000000, 0.000000, -0.822976),
            30: (0.000000, 0.000000, -0.822976),
        }
    },
    'Rightknee_alfred': {
        'rotation': {
            1: (-0.209440, 0.000000, 0.000000),
            30: (-0.209440, 0.000000, 0.000000),
        }
    },
    'Spine_alfred': {
        'rotation': {
            1: (0.000873, 0.000000, 0.000654),
            30: (0.000873, 0.000000, 0.000654),
        }
    },
}


def execute_animation(player_parts, start_frame=1, end_frame=30):
    """
    Slot 1: Animación de parado_2 de Alfred (Mixamo)
    Aplica keyframes extraídos de la animación original
    
    Total de bones animados: 10
    Nota: Animación convertida de Quaternion a Euler XYZ
    """
    
    # Buscar el armature principal
    armature = bpy.data.objects.get("Armature")
    
    if not armature:
        print("❌ Error: No se encontró el objeto 'Armature'")
        return False
    
    if armature.type != 'ARMATURE':
        print("❌ Error: El objeto 'Armature' no es un armature")
        return False
    
    # Asegurar que esté en pose mode
    if armature.mode != 'POSE':
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='POSE')
    
    print(f"✅ Armature encontrado: {armature.name}")
    print(f"📊 Aplicando animación a {len(KEYFRAME_DATA)} bones")
    
    # Buscar el root empty "alfred"
    alfred_root = None
    for obj in bpy.data.objects:
        if obj.name == 'alfred' and obj.type == 'EMPTY':
            alfred_root = obj
            break
    
    # ============================================
    # APLICAR KEYFRAMES DE BONES
    # ============================================
    
    bones_applied = 0
    bones_missing = []
    
    for bone_name, data in KEYFRAME_DATA.items():
        bone = armature.pose.bones.get(bone_name)
        if not bone:
            bones_missing.append(bone_name)
            continue

        # Aplicar rotaciones si existen
        if 'rotation' in data:
            # ✅ IMPORTANTE: Forzar modo EULER XYZ
            bone.rotation_mode = 'XYZ'

            for frame, rotation in data['rotation'].items():
                # Ajustar frame al rango del slot
                adjusted_frame = start_frame + (frame - 1)

                # Aplicar rotación euler
                bone.rotation_euler = rotation
                bone.keyframe_insert(data_path="rotation_euler", frame=adjusted_frame)

        # Aplicar ubicaciones si existen
        if 'location' in data:
            for frame, location in data['location'].items():
                # Ajustar frame al rango del slot
                adjusted_frame = start_frame + (frame - 1)

                # Aplicar ubicación
                bone.location = location
                bone.keyframe_insert(data_path="location", frame=adjusted_frame)

        bones_applied += 1
    
    if bones_missing:
        print(f"⚠️ Bones no encontrados en el rig: {len(bones_missing)}")
        for bone in bones_missing[:5]:  # Mostrar solo los primeros 5
            print(f"   - {bone}")
    
    print(f"✅ Keyframes aplicados a {bones_applied} bones")
    
    # ============================================
    # APLICAR KEYFRAMES DE ROOT LOCATION
    # ============================================
    
    if alfred_root and 'ROOT_LOCATION_DATA' in globals():
        keyframes_count = 0
        for frame, location in ROOT_LOCATION_DATA.items():
            adjusted_frame = start_frame + (frame - 1)
            
            alfred_root.location = location
            alfred_root.keyframe_insert(data_path="location", frame=adjusted_frame)
            keyframes_count += 1
        
        print(f"✅ Root location: {keyframes_count} keyframes")
    
    # ============================================
    # CONFIGURACIÓN DE INTERPOLACIÓN
    # ============================================
    
    if armature.animation_data and armature.animation_data.action:
        for fcurve in _action_fcurves(armature.animation_data.action):
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = 'BEZIER'
                keyframe.easing = 'AUTO'
    
    if alfred_root and alfred_root.animation_data and alfred_root.animation_data.action:
        for fcurve in _action_fcurves(alfred_root.animation_data.action):
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = 'BEZIER'
                keyframe.easing = 'AUTO'
    
    print("\n" + "=" * 60)
    print("✅ ANIMACIÓN DE PARADO_2 APLICADA!")
    print("=" * 60)
    print(f"   📊 Frames: {start_frame}-{end_frame} (1.25 segundos)")
    print(f"   🦴 Bones: {bones_applied} animados")
    print(f"   🎯 Sistema: Mixamo (Quaternion → Euler)")
    print(f"   ✨ Interpolación: BEZIER para suavidad")
    
    return True


def get_animation_metadata():
    """Retorna metadata de la animación para integración con el sistema"""
    return {
        'slot': 1,
        'type': 'parado_2_mixamo',
        'requires_previous_slot': False,
        'minecraft_equivalent': 'Player parado_2 animation (Mixamo rig)',
        'rig_type': 'mixamo_hierarchy',
        'source': 'mixamo_imported',
        'bones_count': 10,
        'animation_type': 'idle',
        'visual_effects': [
            'full_body_animation',
            'mixamo_keyframes',
            'procedural_interpolation'
        ]
    }


# Ejecutar si se corre directamente
if __name__ == "__main__":
    execute_animation(None, start_frame=1, end_frame=30)
