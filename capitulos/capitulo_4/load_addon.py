import bpy 
import sys 
import os 
 
# Configurar paths 
project_path = os.path.dirname(os.path.abspath(__file__)) 
sys.path.append(project_path) 
 
# Cargar addons automáticamente 
try: 
    # Agregar directorio actual al path de Python 
    import sys 
    import os 
    current_dir = os.path.dirname(os.path.abspath(__file__)) 
    if current_dir not in sys.path: 
        sys.path.insert(0, current_dir) 
        print(f"✅ Directorio agregado al path: {{current_dir}}") 
 
    # Registrar Multi-Entity Animation Blocks Manager 
    import simple_animation_blocks_manager 
    simple_animation_blocks_manager.register() 
 
    # Registrar Replay Mod Blender 
    try: 
        import replay_mod_blender 
        replay_mod_blender.register() 
        print("✅ Replay Mod Blender cargado") 
    except Exception as e: 
        print(f"⚠️ Replay Mod Blender no disponible: {{e}}") 
 
    # Registrar Blend Importer System 
    try: 
        import blend_importer 
        blend_importer.register() 
        print("✅ Blend Importer System cargado") 
    except Exception as e: 
        print(f"⚠️ Blend Importer no disponible: {{e}}") 
 
    print("="*70) 
    print("🎉 SISTEMA MULTI-ENTIDAD MODULAR CARGADO EN BLENDER 4.5") 
    print("Multi-Entity Animation Blocks Manager v2.1.1 (Arquitectura Modular)") 
    print("="*70) 
 
 
    print("CARACTERISTICAS ACTIVADAS:") 
    print("  🎭 Multi-entidad (alfred, creeper, wolf, chicken, etc.)") 
    print("  📦 Blend Importer System (importación avanzada .blend)") 
    print("  🎬 Replay Mod Blender (sistema de grabación cinematográfica)") 
    print("   Traducción automática Español→Inglés") 
    print("  ⭐ Sistema de calificación 1-10 estrellas") 
    print("  📤 Exportación inteligente para IA") 
    print("  🎬 Concatenación y timeline compartido") 
    print("  🎛️ Controles de animación avanzados") 
    print("  📦 Arquitectura modular (11 módulos especializados)") 
    print("  🔧 Sistema de entidades independiente") 
    print("  🎭 Sistema Multi-Entidad avanzado") 
    print("="*70) 
    print("\\n✅ SISTEMAS LISTOS PARA USAR") 
    print("Paneles disponibles en sidebar (N):") 
    print("  • 'Animation Blocks' - Sistema Multi-Entidad") 
    print("  • 'Replay' - Sistema de grabación cinematográfica") 
    print("  • 'Tool > Blend Importer' - Importador de archivos .blend") 
except Exception as e: 
    print(f"❌ ERROR cargando addons: {{e}}") 
    import traceback 
    traceback.print_exc() 
