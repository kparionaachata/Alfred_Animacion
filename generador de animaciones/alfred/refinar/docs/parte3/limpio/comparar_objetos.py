# -*- coding: utf-8 -*-
"""Compara lo que el motor de objetos calcula desde el guion con lo que hay en la escena guardada (resultado del generador).
  blender --background base_parte_3.blend --python comparar_objetos.py"""
import importlib.util, json, os, sys, time
import bpy
R = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"; A = R + r"\alfred_animation_studio"


def cargar(n):
    sp = importlib.util.spec_from_file_location(n, os.path.join(A, n + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


gv = cargar("guion_v2"); om = cargar("objetos_mundo"); d = gv.cargar(R + r"\configuraciones\guion_alfred_parte3.json")
t0 = time.time(); res = om.calcular(bpy.context, d); print("calculado en %.0f s" % (time.time() - t0))
c = om.comparar(res, tol_cm=2.0, tol_deg=2.0)
for n, v in c.items(): print("%-18s %s" % (n, json.dumps(v)))
import math
print("--- rangos con diferencia > 2 cm / 2 grados")
for n, est in res["objetos"].items():
    malos = []
    for k, s in sorted(est.items()):
        v = res["vivos"].get(k, {}).get(n)
        if v is None or (s.e < 0.002 and v.e < 0.002): continue
        dl = (s.loc - v.loc).length * 100; da = math.degrees(2 * math.acos(min(1.0, abs(s.q.dot(v.q)))))
        if dl > 2 or da > 2: malos.append((k, round(dl, 1), round(da, 1)))
    if malos:
        rg = []; ini = prev = malos[0][0]
        for k, _, _ in malos[1:]:
            if k != prev + 1: rg.append((ini, prev)); ini = k
            prev = k
        rg.append((ini, prev)); print(n, "frames:", rg[:12], "| peor:", max(malos, key=lambda x: x[1]))
        for a, b in rg: print("    %d-%d: %.1f cm / %.1f grados" % (a, b, max(m[1] for m in malos if a <= m[0] <= b), max(m[2] for m in malos if a <= m[0] <= b)))
