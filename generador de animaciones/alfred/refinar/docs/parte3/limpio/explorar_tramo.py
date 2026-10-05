# Explora el tipo `cuerpo`: genera TODO el cuerpo (f191-N) con los parametros de las tablas y lo compara con la referencia. Se ejecuta en Blender (necesita mathutils).
import importlib.util, json, math, os, sys
R = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"
A = R + r"\alfred_animation_studio"


def cargar(n, ruta=None):
    sp = importlib.util.spec_from_file_location(n, ruta or os.path.join(A, n + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


gv = cargar("guion_v2"); ma = cargar("motor_alfred"); cc = cargar("construir_cuerpo_guion", R + r"\docs\parte3\construir_cuerpo_guion.py")
d = gv.cargar(R + r"\configuraciones\guion_alfred_parte3.json"); ref = ma.cargar_referencia(d["movimiento"]["referencia_numerica"]); org = ma.organico_de(d["movimiento"]); N = ref["N"]
P = cc.parametros_cuerpo(); por_id = {t["id"]: t["params"] for t in ma.tramos_de(gv.desplegar(d))}
ctx = ma.prep_cuerpo(P, org, N, N, por_id, gv.desplegar(d)); malos = []
for k in range(191, N + 1):
    r, l = ma.raw_cuerpo(k, P, org, N, ctx); m = 0.0; mb = None
    for b in r:
        e = max(ma._dang(r[b][q] - ref["raw"]["rot"][b][k - 1][q]) for q in range(3))
        if e > m: m, mb = e, b
    for b in l:
        e = max(abs(l[b][q] - ref["raw"]["loc"][b][k - 1][q]) for q in range(3))
        if e > m: m, mb = e, b
    root = ma.root_cuerpo(k, P, ctx); er = max(abs(root[q] - ref["root"][k - 1][q]) for q in range(4))
    if m > 1e-5 or er > 1e-5: malos.append((k, round(math.degrees(m), 4), mb, round(er, 6)))
print("desajustes:", len(malos), "| primeros:", malos[:10])
if malos:
    por_b = {}
    for k, e, b, er in malos: por_b.setdefault(b, []).append(k)
    print({b: (len(v), v[0], v[-1]) for b, v in por_b.items()})
