"""Run this file in Blender's Text Editor to update the existing solar material.

Does not save the blend, rebuild the orbit, or change camera / solar animation.
"""
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
result = bpy.ops.hdri.repair_solar_face()
print('HDRI solar texture repair:', result, 'Source:', source)
