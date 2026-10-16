"""Run in Blender's Text Editor to add lighting rays to the existing sun."""
import bpy
import importlib.util
import sys
from pathlib import Path

source = Path(r'C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\hdri_complete_system.py')
spec = importlib.util.spec_from_file_location('hdri_complete_system', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.register()
sys.modules['hdri_complete_system'] = module
bpy.context.scene.hdri_tester_props.solar_rays_enabled = True
result = bpy.ops.hdri.apply_solar_rays()
print('Rayos solares:', result)
