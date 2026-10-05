"""Parte 3 - SONIDOS de la historia (pedido de Kebyn). AUTOMATICO: lo hace el add-on `alfred_sonidos` (v1.3+), este script solo lo llama (sin frames escritos a mano).
Se ejecuta DENTRO de Blender (exec) sobre base_parte_3.blend. "Todo" rehace las tiras automaticas SND_ (mcsnd_auto) de toda la escena; para sonorizar solo lo que se anadio al final usar modo="NUEVO".
Los sonidos van a los canales 10+ (las voces de Voz Sync, en 1-4) y quedan por debajo de la voz mas baja de la escena (pico -8 dB, medio -3 dB). Tarda ~35 s.
Version anterior de este archivo (frames fijos): ver GUIA_ANIMACION_ALFRED.md, "sonidos del refugio".
"""
import bpy, sys, importlib.util
sc = bpy.context.scene
m = sys.modules.get("alfred_sonidos")
if m is None:
    ruta = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py"
    spec = importlib.util.spec_from_file_location("alfred_sonidos", ruta); m = importlib.util.module_from_spec(spec); sys.modules["alfred_sonidos"] = m; spec.loader.exec_module(m); m.register()
if not sc.mcsnd.items: bpy.ops.mcsnd.indexar()
sc.mcsnd.semilla = 7
bpy.ops.mcsnd.sonorizar(modo="TODO")
