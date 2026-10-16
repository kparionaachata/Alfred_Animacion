import bpy  
import sys  
import os  
import importlib.util  
  
# Agregar directorio actual al path de Python  
current_dir = os.path.dirname(os.path.abspath(__file__))  
if current_dir not in sys.path:  
    sys.path.insert(0, current_dir)  
    print(f"? Directorio agregado al path: {{current_dir}}")  
  
# Cargar addons autom ticamente usando importlib  
try:  
    # Cargar el m¢dulo usando importlib para evitar problemas de importaci¢n  
    spec = importlib.util.spec_from_file_location("simple_animation_blocks_manager", os.path.join(current_dir, "__init__.py"))  
    if spec and spec.loader:  
        simple_animation_blocks_manager = importlib.util.module_from_spec(spec)  
        sys.modules["simple_animation_blocks_manager"] = simple_animation_blocks_manager  
        spec.loader.exec_module(simple_animation_blocks_manager)  
  
        # Registrar el sistema  
        simple_animation_blocks_manager.register()  
  
        print("="*70)  
        print("?? SISTEMA MULTI-ENTIDAD MODULAR CARGADO EN BLENDER 4.5")  
        print("Multi-Entity Animation Blocks Manager v2.1.1 (Arquitectura Modular)")  
        print("="*70)  
        print("\\n? SISTEMAS LISTOS PARA USAR")  
        print("Panel disponible en sidebar (N):")  
        print("   'Animation Blocks' - Sistema Multi-Entidad")  
    else:  
        print("? ERROR: No se pudo crear el spec para el m¢dulo")  
  
except Exception as e:  
    print(f"? ERROR cargando addons: {{e}}")  
    import traceback  
    traceback.print_exc() 
