#!/usr/bin/env python3
"""
rotation_mode_fix.py
Script para convertir automáticamente todos los objetos y bones de Quaternion (W X Y Z)
a Euler XYZ en Blender.

Este script corrige el problema donde las animaciones no se visualizan porque los
objetos están en modo Quaternion en lugar de Euler XYZ.

Uso:
1. Abrir Blender con el proyecto
2. Ejecutar este script desde el Text Editor de Blender
3. O ejecutar desde la consola de Python: exec(open("rotation_mode_fix.py").read())

El script:
- Convierte todos los objetos (meshes, armatures, etc.) a modo Euler XYZ
- Convierte todos los pose bones de armatures a modo Euler XYZ
- Preserva las rotaciones actuales convirtiéndolas correctamente
- Funciona de forma global en toda la escena
"""

import bpy
import mathutils

def convert_object_rotation_mode(obj):
    """Convierte un objeto individual de Quaternion a Euler XYZ"""
    try:
        # Solo procesar si el objeto tiene rotación
        if hasattr(obj, 'rotation_mode'):
            current_mode = obj.rotation_mode

            if current_mode == 'QUATERNION':
                print(f"🔄 Convirtiendo objeto: {obj.name} (QUATERNION → XYZ)")

                # Obtener la rotación actual en Quaternion
                current_quat = obj.rotation_quaternion.copy()

                # Convertir a Euler XYZ
                euler_rotation = current_quat.to_euler('XYZ')

                # Cambiar el modo de rotación
                obj.rotation_mode = 'XYZ'

                # Aplicar la rotación convertida
                obj.rotation_euler = euler_rotation

                print(f"✅ Objeto {obj.name} convertido exitosamente")
                return True
            else:
                print(f"ℹ️ Objeto {obj.name} ya está en modo {current_mode}")
                return False

    except Exception as e:
        print(f"❌ Error convirtiendo objeto {obj.name}: {e}")
        return False

def convert_armature_bones(armature):
    """Convierte todos los pose bones de un armature a Euler XYZ"""
    try:
        if not armature or armature.type != 'ARMATURE':
            return False

        print(f"🔄 Procesando armature: {armature.name}")

        # Asegurar que esté en pose mode
        was_in_pose_mode = False
        if armature.mode != 'POSE':
            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='POSE')
            was_in_pose_mode = True

        bones_converted = 0

        # Procesar cada pose bone
        for pose_bone in armature.pose.bones:
            try:
                current_mode = pose_bone.rotation_mode

                if current_mode == 'QUATERNION':
                    print(f"  🔄 Convirtiendo bone: {pose_bone.name} (QUATERNION → XYZ)")

                    # Obtener la rotación actual en Quaternion
                    current_quat = pose_bone.rotation_quaternion.copy()

                    # Convertir a Euler XYZ
                    euler_rotation = current_quat.to_euler('XYZ')

                    # Cambiar el modo de rotación
                    pose_bone.rotation_mode = 'XYZ'

                    # Aplicar la rotación convertida
                    pose_bone.rotation_euler = euler_rotation

                    bones_converted += 1
                    print(f"  ✅ Bone {pose_bone.name} convertido")

                else:
                    print(f"  ℹ️ Bone {pose_bone.name} ya está en modo {current_mode}")

            except Exception as e:
                print(f"  ❌ Error convirtiendo bone {pose_bone.name}: {e}")

        # Restaurar el modo anterior si es necesario
        if not was_in_pose_mode and armature.mode == 'POSE':
            bpy.ops.object.mode_set(mode='OBJECT')

        print(f"✅ Armature {armature.name}: {bones_converted} bones convertidos")
        return bones_converted > 0

    except Exception as e:
        print(f"❌ Error procesando armature {armature.name}: {e}")
        return False

def fix_all_rotation_modes():
    """Función principal que convierte todos los objetos y bones de la escena"""
    print("=" * 60)
    print("🔧 ROTATION MODE FIX - Convirtiendo a Euler XYZ")
    print("=" * 60)

    objects_converted = 0
    armatures_processed = 0
    bones_converted_total = 0

    # Procesar todos los objetos de la escena
    for obj in bpy.data.objects:
        try:
            # Convertir objetos individuales
            if convert_object_rotation_mode(obj):
                objects_converted += 1

            # Procesar armatures
            if obj.type == 'ARMATURE':
                bones_converted = convert_armature_bones(obj)
                if bones_converted:
                    armatures_processed += 1
                    bones_converted_total += bones_converted

        except Exception as e:
            print(f"❌ Error procesando objeto {obj.name}: {e}")

    # Reporte final
    print("\n" + "=" * 60)
    print("📊 REPORTE FINAL:")
    print(f"  📦 Objetos convertidos: {objects_converted}")
    print(f"  🦴 Armatures procesadas: {armatures_processed}")
    print(f"  🦴 Bones convertidos: {bones_converted_total}")
    print("=" * 60)

    if objects_converted > 0 or bones_converted_total > 0:
        print("✅ Conversión completada exitosamente")
        print("🎯 Las animaciones ahora deberían visualizarse correctamente")
        print("\n💡 RECUERDA:")
        print("   • Guarda el archivo (.blend) después de la conversión")
        print("   • Las animaciones ahora funcionarán con rotaciones Euler XYZ")
    else:
        print("ℹ️ No se encontraron objetos o bones en modo Quaternion")
        print("🎯 Todos los objetos ya están en modo Euler XYZ")

    return objects_converted, armatures_processed, bones_converted_total

def check_scene_rotation_modes():
    """Verifica qué objetos están en modo Quaternion"""
    print("\n🔍 VERIFICACIÓN DE MODOS DE ROTACIÓN:")
    print("-" * 50)

    quaternion_objects = []
    quaternion_bones = []

    # Verificar objetos
    for obj in bpy.data.objects:
        if hasattr(obj, 'rotation_mode') and obj.rotation_mode == 'QUATERNION':
            quaternion_objects.append(obj.name)
            print(f"📦 Objeto QUATERNION: {obj.name}")

    # Verificar bones en armatures
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and obj.pose:
            for pose_bone in obj.pose.bones:
                if pose_bone.rotation_mode == 'QUATERNION':
                    quaternion_bones.append(f"{obj.name}.{pose_bone.name}")
                    print(f"🦴 Bone QUATERNION: {obj.name}.{pose_bone.name}")

    if not quaternion_objects and not quaternion_bones:
        print("✅ No se encontraron objetos o bones en modo Quaternion")
        return False
    else:
        print(f"\n⚠️ Encontrados: {len(quaternion_objects)} objetos, {len(quaternion_bones)} bones")
        return True

# Función principal para ejecutar desde Blender
def main():
    """Función principal del script"""
    print("🚀 INICIANDO ROTATION MODE FIX")
    print("Script para convertir Quaternion → Euler XYZ")
    print("Versión: 1.0")
    print("-" * 50)

    # Verificar escena primero
    has_quaternion = check_scene_rotation_modes()

    if has_quaternion:
        print("\n🔧 Iniciando conversión...")
        objects_converted, armatures_processed, bones_converted_total = fix_all_rotation_modes()

        # Forzar actualización de la escena
        bpy.context.view_layer.update()
        print("\n🔄 Escena actualizada")

    else:
        print("\n✅ No es necesario hacer conversiones")
        print("🎯 Todos los objetos ya están en modo Euler XYZ")

    print("\n" + "=" * 60)
    print("🎉 PROCESO COMPLETADO")
    print("=" * 60)

# Ejecutar automáticamente si se corre el script
if __name__ == "__main__":
    main()

# Función para ejecutar desde la consola de Blender
def run_rotation_fix():
    """Alias para ejecutar desde la consola de Blender"""
    main()

print("\n" + "=" * 60)
print("🎯 ROTATION MODE FIX CARGADO")
print("=" * 60)
print("📋 INSTRUCCIONES DE USO:")
print("1. Ejecutar en Blender: exec(open('rotation_mode_fix.py').read())")
print("2. O usar la función: run_rotation_fix()")
print("3. Guardar el archivo .blend después de la conversión")
print("=" * 60)