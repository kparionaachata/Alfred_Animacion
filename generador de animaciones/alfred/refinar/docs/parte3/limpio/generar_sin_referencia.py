# -*- coding: utf-8 -*-
"""Genera TODO Alfred desde el guion SIN referencia numerica y lo compara con la referencia congelada (oraculo). Necesita mathutils:
  blender.exe --background --factory-startup --python generar_sin_referencia.py"""
import importlib.util, os, sys
R = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"
A = R + r"\alfred_animation_studio"


def cargar(n):
    sp = importlib.util.spec_from_file_location(n, os.path.join(A, n + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


gv = cargar("guion_v2"); ma = cargar("motor_alfred")
d = gv.cargar(R + r"\configuraciones\guion_alfred_parte3.json")
assert not d["movimiento"].get("referencia_numerica")
ref = ma.cargar_referencia(d["movimiento"]["referencia_de_pruebas"])
res = ma.generar(d)
print("N", res["N"], "migrados", len(res["migrados"]))
c = ma.comparar(res, ref); print(c)
print("ajuste_hips igual:", all(abs(a - b) < 1e-6 for x, y in zip(res["ajuste_hips"], ref["ajuste_hips"]) for a, b in zip(x, y)))
