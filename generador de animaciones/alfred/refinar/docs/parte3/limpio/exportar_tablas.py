# -*- coding: utf-8 -*-
"""Exporta las TABLAS del cuerpo de Alfred del generador (`sentarse_en_refugio.py`, espacio de nombres guardado por `volcar_referencia.py`) a `datos_guion/tablas_cuerpo.json`; el constructor del guion las pone en `movimiento`.
Se ejecuta en Blender (exec)."""
import json
import bpy

g = bpy.app.driver_namespace["gen_parte3"]
NOMBRES = ["NUCA0", "NUCA_D", "NUCA_Q", "SIT_Q", "SIT_T", "CLR_KEYS", "CLR_Q", "CLR_SW", "CLR_T", "CLR_LEANW", "CLR_LEAN", "KN0", "KN1", "KN_LEG", "KN_HIPY", "KN_X", "KN_LEAN", "KN_NECK", "KN_LOOKY", "MESA_E", "TBK", "TBK_X",
           "TBK_PRE_R", "TBK_PRE_L", "STUDIO_U", "STUDIO_E", "STUDIO_LOC", "SCOOT0", "SCOOT_D", "SCOOT_DX", "TORCH_DX", "ASTAND0", "ASTAND_D", "STAND_X", "STAND_Y", "FALL0", "FALL_D", "ROT0", "ROT_D", "ROT2_0", "ROT2_D", "N",
           "LEAN", "LEAN_UP", "LEAN_TOP", "LEAN_DOWN", "THROWS", "REL_Q", "REACH_D", "HOLD_D", "SWING_D", "BACK_D", "IMPACT_F"]
out = {}
for n in NOMBRES:
    if n not in g: print("FALTA", n); continue
    v = g[n]; out[n] = json.loads(json.dumps(v))
ruta = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\parte3\datos_guion\tablas_cuerpo.json"
json.dump(out, open(ruta, "w", encoding="utf-8"), separators=(",", ":"))
print("tablas:", len(out), "| tamano", len(json.dumps(out)), "bytes | faltan:", [n for n in NOMBRES if n not in out])
