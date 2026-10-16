import bpy

# Script para limpiar completamente el timeline en Blender
# y permitir cargar animaciones de más de 1500 frames

def limpiar_timeline():
    """Limpia todas las configuraciones del timeline y lo resetea"""
    
    scene = bpy.context.scene
    
    # 1. Resetear el frame actual
    scene.frame_current = 1
    
    # 2. Configurar nuevo rango de frames (ajusta según necesites)
    scene.frame_start = 1
    scene.frame_end = 2000  # Cambia este valor según tu necesidad
    
    # 3. Limpiar acciones y animaciones
    for obj in bpy.data.objects:
        # Limpiar animación del objeto
        obj.animation_data_clear()
    
    # 4. Limpiar todas las acciones no utilizadas
    for action in bpy.data.actions:
        if action.users == 0:
            bpy.data.actions.remove(action)
    
    # 5. Resetear el preview range si está activo
    scene.use_preview_range = False
    scene.frame_preview_start = 1
    scene.frame_preview_end = 250
    
    # 6. Limpiar markers del timeline
    scene.timeline_markers.clear()
    
    # 7. Actualizar la escena
    bpy.context.view_layer.update()
    
    print("="*50)
    print("Timeline limpiado exitosamente")
    print(f"Nuevo rango: {scene.frame_start} - {scene.frame_end}")
    print("="*50)

# Ejecutar la función
limpiar_timeline()

# Opcional: Si necesitas un rango específico diferente, descomenta y ajusta:
# bpy.context.scene.frame_end = 1500  # Tu duración específica

# VERSIÓN AGRESIVA (usa solo si lo anterior no funciona)
def limpiar_timeline_agresivo():
    """Limpieza más profunda del timeline"""
    
    # Remover TODAS las acciones
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action, do_unlink=True)
    
    # Limpiar NLA strips
    for obj in bpy.data.objects:
        if obj.animation_data:
            if obj.animation_data.nla_tracks:
                for track in obj.animation_data.nla_tracks:
                    obj.animation_data.nla_tracks.remove(track)
    
    # Resetear configuración de render también
    scene = bpy.context.scene
    scene.render.fps = 24
    scene.render.fps_base = 1.0
    
    print("Limpieza agresiva completada")

# Descomenta la siguiente línea si necesitas la limpieza agresiva:
# limpiar_timeline_agresivo()