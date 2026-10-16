# -*- coding: utf-8 -*-
"""Add-on para INSTALAR (Editar > Preferencias > Complementos > Instalar desde disco... > este archivo).
Solo carga el panel real desde capitulo_4/automatizacion/panel_cadena.py: los cambios en esa carpeta se usan sin reinstalar."""
bl_info = {"name": "Cadena: reconstruir en segundo plano", "author": "Alfred_Animacion", "version": (1, 0, 0), "blender": (4, 2, 0),
           "location": "Visor 3D > barra lateral (N) > Cadena", "description": "Reconstruye la cadena de scripts de cada parte sin bloquear Blender, con respaldo y chequeos",
           "category": "Animation"}
import sys, importlib

AUTO = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\automatizacion"


def register():
    if AUTO not in sys.path: sys.path.insert(0, AUTO)
    import panel_cadena; importlib.reload(panel_cadena); panel_cadena.register()


def unregister():
    import panel_cadena; panel_cadena.unregister()
