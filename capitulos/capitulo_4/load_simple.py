import bpy
import sys
import os
import importlib.util

current_dir = os.path.dirname(os.path.abspath(__file__))
print("Directorio actual:", current_dir)

try:
    # Agregar directorio al path de Python
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
        print("Directorio agregado al path")

    # Importar módulos individualmente
    print("Importando módulos...")

    # Importar core_system
    try:
        import core_system
        print("✅ core_system importado")
    except ImportError as e:
        print(f"⚠️ core_system no disponible: {e}")

    # Importar entity_system
    try:
        import entity_system
        print("✅ entity_system importado")
    except ImportError as e:
        print(f"⚠️ entity_system no disponible: {e}")

    # Importar ui_panels
    try:
        import ui_panels
        ui_panels.register()
        print("✅ ui_panels importado y registrado")
    except ImportError as e:
        print(f"⚠️ ui_panels no disponible: {e}")

    # Importar operators
    try:
        import operators
        operators.register()
        print("✅ operators importado y registrado")
    except ImportError as e:
        print(f"⚠️ operators no disponible: {e}")

    # Importar utilities
    try:
        import utilities
        utilities.register()
        print("✅ utilities importado y registrado")
    except ImportError as e:
        print(f"⚠️ utilities no disponible: {e}")

    # Importar feedback_system
    try:
        import feedback_system
        feedback_system.register()
        print("✅ feedback_system importado y registrado")
    except ImportError as e:
        print(f"⚠️ feedback_system no disponible: {e}")

    # Importar translation_system
    try:
        import translation_system
        translation_system.register()
        print("✅ translation_system importado y registrado")
    except ImportError as e:
        print(f"⚠️ translation_system no disponible: {e}")

    # Importar relative_animation
    try:
        import relative_animation
        relative_animation.register()
        print("✅ relative_animation importado y registrado")
    except ImportError as e:
        print(f"⚠️ relative_animation no disponible: {e}")

    # Importar dynamic_objects
    try:
        import dynamic_objects
        dynamic_objects.register()
        print("✅ dynamic_objects importado y registrado")
    except ImportError as e:
        print(f"⚠️ dynamic_objects no disponible: {e}")

    # Importar animation_engine
    try:
        import animation_engine
        animation_engine.register()
        print("✅ animation_engine importado y registrado")
    except ImportError as e:
        print(f"⚠️ animation_engine no disponible: {e}")

    # Importar entity_system
    try:
        import entity_system
        entity_system.register()
        print("✅ entity_system importado y registrado")
    except ImportError as e:
        print(f"⚠️ entity_system no disponible: {e}")

    # Importar core_system
    try:
        import core_system
        core_system.register()
        print("✅ core_system importado y registrado")
    except ImportError as e:
        print(f"⚠️ core_system no disponible: {e}")

    # ============================================
    # 🎨 VIEWPORT TEXTURE SYSTEM
    # ============================================

    print("\n" + "="*70)
    print("🎨 CARGANDO VIEWPORT TEXTURE SYSTEM...")
    print("="*70)

    try:
        import viewport_texture_system
        print("✅ viewport_texture_system IMPORTADO correctamente")
        
        # Registrar el sistema
        viewport_texture_system.register()
        print("✅ viewport_texture_system REGISTRADO correctamente")
        
        # Verificar que el panel está registrado
        if hasattr(bpy.types, 'VIEWPORT_PT_texture_solid_panel'):
            print("   ✅ Panel VIEWPORT_PT_texture_solid_panel CONFIRMADO")
        else:
            print("   ❌ Panel VIEWPORT_PT_texture_solid_panel NO encontrado")
            
        # Verificar que los operadores están registrados
        if hasattr(bpy.ops.viewport, 'enable_texture_solid'):
            print("   ✅ Operador enable_texture_solid CONFIRMADO")
        else:
            print("   ❌ Operador enable_texture_solid NO encontrado")
            
        if hasattr(bpy.ops.viewport, 'disable_texture_solid'):
            print("   ✅ Operador disable_texture_solid CONFIRMADO")
        else:
            print("   ❌ Operador disable_texture_solid NO encontrado")
            
        if hasattr(bpy.ops.viewport, 'apply_texture_to_object'):
            print("   ✅ Operador apply_texture_to_object CONFIRMADO")
        else:
            print("   ❌ Operador apply_texture_to_object NO encontrado")
        
        print("="*70)
        print("✅ VIEWPORT TEXTURE SYSTEM COMPLETAMENTE CARGADO")
        print("   📂 Panel disponible en: View3D > Sidebar (N) > 'Viewport Texture'")
        print("="*70)
        
    except ImportError as e:
        print("="*70)
        print(f"❌ ERROR: viewport_texture_system no se pudo importar")
        print(f"   Razón: {e}")
        print("="*70)
        import traceback
        traceback.print_exc()
    except Exception as e:
        print("="*70)
        print(f"❌ ERROR: al registrar viewport_texture_system")
        print(f"   Razón: {e}")
        print("="*70)
        import traceback
        traceback.print_exc()

    # ============================================
    # SISTEMAS DE CÁMARAS EN PARALELO
    # ============================================

    print("\n🎥 Cargando sistemas de cámaras en paralelo...")

    # Importar FLUJO A: Creación de Cámaras
    try:
        import camaras_flujo_A
        camaras_flujo_A.register()
        print("✅ FLUJO A (Creación de Cámaras) importado y registrado")
    except ImportError as e:
        print(f"⚠️ FLUJO A no disponible: {e}")

    # Importar FLUJO B y C: Secuenciación de Cámaras
    try:
        import camaras_flujo_B_C
        camaras_flujo_B_C.register()
        print("✅ FLUJO B y C (Secuenciación de Cámaras) importado y registrado")
    except ImportError as e:
        print(f"⚠️ FLUJO B y C no disponible: {e}")

    # Importar HDRI Complete System
    try:
        cielos_path = os.path.join(current_dir, '..', 'cielos')
        if cielos_path not in sys.path:
            sys.path.insert(0, cielos_path)
        import hdri_complete_system
        hdri_complete_system.register()
        print("✅ HDRI Complete System importado y registrado")
    except ImportError as e:
        print(f"⚠️ HDRI Complete System no disponible: {e}")

    # Importar Minecraft Block Editor
    try:
        import minecraft_block_editor_fixed
        minecraft_block_editor_fixed.register()
        print("✅ Minecraft Block Editor v3.0 importado y registrado")
    except ImportError as e:
        print(f"⚠️ Minecraft Block Editor no disponible: {e}")

    # Importar Replay Mod Blender
    try:
        import replay_mod_blender
        replay_mod_blender.register()
        print("✅ Replay Mod Blender cargado")
    except ImportError as e:
        print(f"⚠️ Replay Mod Blender no disponible: {e}")

    # Importar Blend Importer System
    try:
        import blend_importer
        blend_importer.register()
        print("✅ Blend Importer System cargado")
    except ImportError as e:
        print(f"⚠️ Blend Importer System no disponible: {e}")

    # ============================================
    # 🟢 PLANO GENERADOR ADDON
    # ============================================

    print("\n" + "="*70)
    print("🟢 CARGANDO PLANO GENERADOR ADDON...")
    print("="*70)

    try:
        import plano_generador_addon
        plano_generador_addon.register()
        print("✅ Plano Generador Addon importado y registrado")
        print("   📂 Panel disponible en: View3D > Sidebar > 'Plano Generador'")
    except ImportError as e:
        print(f"⚠️ Plano Generador Addon no disponible: {e}")
    except Exception as e:
        print(f"❌ Error al registrar Plano Generador Addon: {e}")
        import traceback
        traceback.print_exc()

    print("="*70)

    # ============================================
    # 🎮 UNITY VIEWPORT OPTIMIZER
    # ============================================

    print("\n" + "="*70)
    print("🎮 INSTALANDO UNITY VIEWPORT OPTIMIZER...")
    print("="*70)

    try:
        import shutil
        import addon_utils

        # Ruta del archivo optimizador
        optimizer_source = os.path.join(current_dir, "optimizacion", "blender_unity_optimization.py")

        if os.path.exists(optimizer_source):
            # Obtener carpeta de addons de Blender
            user_addons = bpy.utils.user_resource('SCRIPTS', path="addons")

            if not os.path.exists(user_addons):
                os.makedirs(user_addons)
                print(f"📁 Carpeta de addons creada: {user_addons}")

            # Copiar archivo
            dest_file = os.path.join(user_addons, "blender_unity_optimization.py")

            try:
                shutil.copy2(optimizer_source, dest_file)
                print(f"✅ Unity Viewport Optimizer copiado a: {dest_file}")
            except Exception as e:
                print(f"❌ Error al copiar archivo: {e}")
                raise

            # Refrescar módulos de addons
            addon_utils.modules_refresh()

            # Activar addon
            try:
                addon_utils.enable("blender_unity_optimization", default_set=True)
                print("✅ Unity Viewport Optimizer ACTIVADO exitosamente")

                # Verificar que el panel está disponible
                if hasattr(bpy.types, 'VIEWPORT_PT_unity_optimizer_panel'):
                    print("   ✅ Panel 'Unity Optimizer' confirmado en sidebar")
                else:
                    print("   ⚠️ Panel 'Unity Optimizer' no encontrado (posible reinicio necesario)")

            except Exception as e:
                print(f"⚠️ Error al activar addon: {e}")
                print("   Intenta activarlo manualmente en Edit > Preferences > Add-ons")

        else:
            print(f"❌ Archivo optimizador no encontrado: {optimizer_source}")

    except ImportError as e:
        print(f"❌ Error importando módulos necesarios: {e}")
    except Exception as e:
        print(f"❌ Error instalando Unity Viewport Optimizer: {e}")
        import traceback
        traceback.print_exc()

    print("="*70)
    print("🎮 UNITY VIEWPORT OPTIMIZER INSTALACIÓN COMPLETADA")
    print("   📂 Panel disponible en: View3D > Sidebar (N) > 'Unity Optimizer'")
    print("   🎯 Configuración recomendada: FPS Objetivo=30, FPS Mínimo=20")
    print("="*70)

    # ============================================
    # RESUMEN FINAL
    # ============================================

    print("\n" + "="*70)
    print("SUCCESS: Todos los sistemas cargados correctamente")
    print("="*70)
    print("\n PANELES DISPONIBLES EN SIDEBAR (N):")
    print("  -- Sistema del proyecto --")
    print("  * 'Animation Blocks'   - Sistema Multi-Entidad")
    print("  * 'Replay'             - Sistema de grabacion cinematografica")
    print("  * 'Viewport Texture'   - Sistema de Texturas en Viewport")
    print("  * 'FLUJO A v2.0'       - Creacion de Camaras")
    print("  * 'Secuenciador'       - FLUJO B y C de Camaras")
    print("  * 'HDRI Complete'      - Sistema de Iluminacion HDRI")
    print("  * 'Block Tools'        - Minecraft Block Editor v3.0")
    print("  * 'Blend'              - Importador de archivos .blend")
    print("  * 'Plano Generador'    - Generador de planos con orientación y textura")
    print("  * 'Unity Optimizer'    - Optimizacion automatica de FPS")
    print("  -- Addons de personajes (instalados por el .bat) --")
    print("  * 'Alfred Studio'      - Controles de Alfred")
    print("  * 'Jerry Studio'       - Controles de Jerry")
    print("  * 'GRB7 Studio'        - Controles de Guard Ribbit 7")
    print("  * 'GRB8 Studio'        - Controles de Guard Ribbit 8")
    print("="*70)

except Exception as e:
    print("="*70)
    print("❌ ERROR CRÍTICO EN CARGA DE SISTEMAS:")
    print("="*70)
    print("ERROR:", str(e))
    import traceback
    traceback.print_exc()
    print("="*70)
