#!/usr/bin/env python3
"""
__init__.py - Punto de entrada del sistema Multi-Entity Animation Blocks Manager
Importa y combina todos los módulos divididos para mantener compatibilidad
"""

# ============================================================================
# IMPORTACIONES PRINCIPALES
# ============================================================================

# Importar core_system primero para asegurar que las propiedades se registren antes del UI
try:
    from . import core_system
    print("✅ core_system importado correctamente")
except ImportError as e:
    print(f"❌ Error importando core_system: {e}")
    raise  # Propagar el error para debugging

try:
    from . import entity_system
    from . import animation_engine
    from . import ui_panels
    from . import operators
    from . import utilities
    from . import translation_system
    from . import relative_animation
    from . import dynamic_objects
    from . import feedback_system
    print("✅ Módulos principales importados correctamente")
except ImportError as e:
    print(f"❌ Error importando módulos principales: {e}")
    # Continuar sin algunos módulos opcionales
    pass

# ============================================================================
# IMPORTAR VIEWPORT_TEXTURE_SYSTEM - SIN TRY-EXCEPT PARA VER ERRORES
# ============================================================================

print("="*70)
print("🎨 CARGANDO VIEWPORT TEXTURE SYSTEM...")
print("="*70)

# IMPORTACIÓN DIRECTA - Sin capturar excepciones para ver errores reales
from . import viewport_texture_system
print("✅ viewport_texture_system importado correctamente")
print(f"   📋 Módulo: {viewport_texture_system}")
print(f"   📋 Clases: {viewport_texture_system.classes}")

print("="*70)


# ============================================================================
# FUNCIÓN DE REGISTRO
# ============================================================================

def register():
    """Registra todos los componentes del sistema"""
    
    print("\n" + "="*70)
    print("🚀 INICIANDO REGISTRO DE COMPONENTES")
    print("="*70)
    
    # ========================================================================
    # REGISTRAR VIEWPORT TEXTURE SYSTEM PRIMERO (es independiente)
    # ========================================================================
    
    print("\n🎨 REGISTRANDO VIEWPORT TEXTURE SYSTEM...")
    
    try:
        # Registro directo sin verificaciones innecesarias
        viewport_texture_system.register()
        print("✅ Viewport Texture System REGISTRADO EXITOSAMENTE")
        print("   📂 Panel disponible en: View3D > Sidebar (N) > 'Viewport Texture'")
        
        # Verificar que las clases están registradas
        import bpy
        if hasattr(bpy.types, 'VIEWPORT_PT_texture_solid_panel'):
            print("   ✅ Panel VIEWPORT_PT_texture_solid_panel confirmado")
        else:
            print("   ❌ Panel VIEWPORT_PT_texture_solid_panel NO encontrado")
            
        if hasattr(bpy.ops.viewport, 'enable_texture_solid'):
            print("   ✅ Operador enable_texture_solid confirmado")
        else:
            print("   ❌ Operador enable_texture_solid NO encontrado")
            
    except Exception as e:
        print(f"❌ ERROR CRÍTICO registrando viewport_texture_system:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Mensaje: {e}")
        import traceback
        traceback.print_exc()
        # NO capturar - dejar que el error se vea
        raise
    
    # ========================================================================
    # REGISTRAR COMPONENTES PRINCIPALES
    # ========================================================================
    
    try:
        print("\n🎭 REGISTRANDO COMPONENTES PRINCIPALES...")
        
        # Registrar componentes en orden de dependencia
        if 'core_system' in globals():
            core_system.register()
            print("   ✅ core_system")
        else:
            print("   ⚠️ core_system no disponible")

        if 'entity_system' in globals():
            entity_system.register()
            print("   ✅ entity_system")
        else:
            print("   ⚠️ entity_system no disponible")

        if 'animation_engine' in globals():
            animation_engine.register()
            print("   ✅ animation_engine")
        else:
            print("   ⚠️ animation_engine no disponible")

        if 'ui_panels' in globals():
            ui_panels.register()
            print("   ✅ ui_panels")
        else:
            print("   ⚠️ ui_panels no disponible")

        if 'operators' in globals():
            operators.register()
            print("   ✅ operators")
        else:
            print("   ⚠️ operators no disponible")

        if 'utilities' in globals():
            utilities.register()
            print("   ✅ utilities")
        else:
            print("   ⚠️ utilities no disponible")

        if 'translation_system' in globals():
            translation_system.register()
            print("   ✅ translation_system")
        else:
            print("   ⚠️ translation_system no disponible")

        if 'relative_animation' in globals():
            relative_animation.register()
            print("   ✅ relative_animation")
        else:
            print("   ⚠️ relative_animation no disponible")

        if 'dynamic_objects' in globals():
            dynamic_objects.register()
            print("   ✅ dynamic_objects")
        else:
            print("   ⚠️ dynamic_objects no disponible")

        if 'feedback_system' in globals():
            feedback_system.register()
            print("   ✅ feedback_system")
        else:
            print("   ⚠️ feedback_system no disponible")

        print("\n✅ Todos los componentes principales registrados")

    except Exception as e:
        print(f"❌ ERROR registrando componentes principales: {e}")
        import traceback
        traceback.print_exc()

    # ========================================================================
    # RESUMEN FINAL
    # ========================================================================
    
    print("\n" + "="*70)
    print("🎉 SISTEMA MULTI-ENTIDAD CARGADO EN BLENDER")
    print("Multi-Entity Animation Blocks Manager v2.1.1 (Módulos Divididos)")
    print("="*70)

    print("\n📋 CARACTERÍSTICAS ACTIVADAS:")
    print("  🎭 Multi-entidad (alfred, creeper, wolf, chicken, etc.)")
    print("  🌍 Traducción automática Español→Inglés")
    print("  ⭐ Sistema de calificación 1-10 estrellas")
    print("  📤 Exportación inteligente para IA")
    print("  🎬 Concatenación y timeline compartido")
    print("  🎛️ Controles de animación avanzados")
    print("  🎭 Sistema Multi-Entidad avanzado")
    print("  📦 Arquitectura modular para análisis")
    print("  🎨 Sistema de Texturas en Viewport")
    print("="*70)
    
    print("\n✅ SISTEMAS LISTOS PARA USAR")
    print("Paneles disponibles en sidebar (N):")
    print("  • 'Animation Blocks' - Sistema Multi-Entidad")
    print("  • 'Viewport Texture' - Sistema de Texturas Sólidas")
    print("="*70)


def unregister():
    """Desregistra todos los componentes del sistema"""
    
    print("\n" + "="*70)
    print("🔄 DESREGISTRANDO SISTEMA MULTI-ENTIDAD")
    print("="*70)
    
    try:
        # Desregistrar en orden inverso
        
        # Viewport Texture System primero
        try:
            viewport_texture_system.unregister()
            print("✅ viewport_texture_system desregistrado")
        except Exception as e:
            print(f"⚠️ Error desregistrando viewport_texture_system: {e}")

        # Resto de componentes
        try:
            feedback_system.unregister()
            print("✅ feedback_system desregistrado")
        except: pass
        
        try:
            dynamic_objects.unregister()
            print("✅ dynamic_objects desregistrado")
        except: pass
        
        try:
            relative_animation.unregister()
            print("✅ relative_animation desregistrado")
        except: pass
        
        try:
            translation_system.unregister()
            print("✅ translation_system desregistrado")
        except: pass
        
        try:
            utilities.unregister()
            print("✅ utilities desregistrado")
        except: pass
        
        try:
            operators.unregister()
            print("✅ operators desregistrado")
        except: pass
        
        try:
            ui_panels.unregister()
            print("✅ ui_panels desregistrado")
        except: pass
        
        try:
            animation_engine.unregister()
            print("✅ animation_engine desregistrado")
        except: pass
        
        try:
            entity_system.unregister()
            print("✅ entity_system desregistrado")
        except: pass
        
        try:
            core_system.unregister()
            print("✅ core_system desregistrado")
        except: pass

        print("="*70)
        print("✅ Sistema Multi-Entidad desregistrado correctamente")
        print("="*70)

    except Exception as e:
        print(f"❌ ERROR desregistrando sistema modular: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# EXPORTS Y METADATA
# ============================================================================

# Para compatibilidad con importaciones directas
__all__ = [
    'register',
    'unregister',
    'core_system',
    'entity_system',
    'animation_engine',
    'ui_panels',
    'operators',
    'utilities',
    'translation_system',
    'relative_animation',
    'dynamic_objects',
    'feedback_system',
    'viewport_texture_system'
]

# Información del addon (para compatibilidad con Blender)
bl_info = {
    "name": "Multi-Entity Animation Blocks Manager (Modular)",
    "author": "Sistema Multi-Entidad Modular",
    "version": (2, 1, 1),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Animation Blocks",
    "description": "Gestor multi-entidad modular con carga automática desde carpetas Prompt_X",
    "category": "Animation",
}

if __name__ == "__main__":
    register()
