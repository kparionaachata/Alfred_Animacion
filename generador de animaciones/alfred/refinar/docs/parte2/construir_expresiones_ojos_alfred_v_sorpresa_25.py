"""Se ejecuta DENTRO de Blender (exec). Regenera los shape keys de expresion de los ojos de Alfred con el MISMO sistema del add-on (`alfred_animation_studio.eye_system._eye_compute_vertex`:
Zona Superior/Inferior, Inv V, Curva cuadratica, intensidades 0.18) para que, con la INTENSIDAD FIJA en 0.06 (valor del shape key), cada expresion se lea bien:

  Feliz    : Zona INFERIOR + Inv V   -> arco hacia arriba en el borde inferior = ojos sonrientes (^)
  Triste   : Zona INFERIOR + Inv V   -> bordes inferiores caidos y redondeados (ojos de cachorro)  [Feliz con otro signo: mismo set, signo contrario]
  Enojado  : Zona SUPERIOR + Inv H   -> esquinas internas BAJAS (ceno, determinacion). Medido: SIN Inv H el add-on da las esquinas internas ALTAS en los ojos de Alfred (el eje x local
             de la malla del ojo esta invertido), por eso se usa Inv H para que el nombre coincida con el gesto
  Sospecha : Zona SUPERIOR + Inv H   -> esquinas internas ALTAS (preocupacion / duda / miedo)
Las tres que no tienen intensidad propia en el add-on (Cansado, Cerrado, Sorpresa) llevan sus formulas del add-on multiplicadas para que el valor 0.06 produzca el efecto util:
  Cansado  : Zona SUPERIOR, comprime la mitad superior un 45 %    (parpado caido)
  Cerrado  : ambas zonas, comprime un 30 % hacia el centro         (ojos entrecerrados)
  Sorpresa : Zona SUPERIOR, expande la mitad superior un 25 %      (ojos mas altos)
`Closed` (parpadeo) no se toca. Ojo derecho con espejo horizontal, como hace el add-on (is_right_eye=True).
Uso (en Blender):  exec(open(r"<ruta>/construir_expresiones_ojos_alfred.py", encoding="utf-8").read())
"""
import bpy, sys, importlib
from types import SimpleNamespace

es = sys.modules.get("alfred_animation_studio.eye_system") or importlib.import_module("alfred_animation_studio.eye_system")
VALOR = 0.06                                                  # intensidad (valor del shape key) con la que se anima
I = 0.18                                                      # intensidad de geometria de Feliz/Triste/Enojo/Sospecha (la de la lista de intervalos)
SET = {                                                       # expresion -> (zona, inv_v, inv_h)
    "feliz": ("LOWER", True, False), "triste": ("LOWER", True, False), "enojado": ("UPPER", False, True), "sospecha": ("UPPER", False, True),
}
EXTRA = {"cansado": 0.45, "cerrado": 0.30, "sorpresa": 0.25}   # fraccion de la altura que mueve el efecto cuando el shape key vale VALOR
OJOS = (("L", "ojo_izquierdo_alfred"), ("R", "ojo_derecho_alfred"))


def _bounds(bas):
    xs = [c.x for c in bas]; ys = [c.y for c in bas]; zs = [c.z for c in bas]
    return {"cx": (max(xs) + min(xs)) / 2, "cy": (max(ys) + min(ys)) / 2, "cz": (max(zs) + min(zs)) / 2, "rx": max(xs) - min(xs), "ry": max(ys) - min(ys), "rz": max(zs) - min(zs)}


def construir():
    for side, nombre in OJOS:
        e = bpy.data.objects[nombre]; me = e.data
        bas = [v.co.copy() for v in me.vertices]; b = _bounds(bas); h, v, _ = es._eye_detect_axes(e)
        for k in ("Feliz", "Triste", "Enojado", "Sospecha", "Cansado", "Cerrado", "Sorpresa"):
            old = me.shape_keys.key_blocks.get(k)
            if old: e.shape_key_remove(old)
        for expr in ("feliz", "triste", "enojado", "sospecha"):
            zona, inv, inv_h = SET[expr]
            S = SimpleNamespace(invert_vertical=inv, invert_horizontal=inv_h, affect_zone=zona, curve_mode="QUADRATIC", swap_axes=False,
                                intensity_feliz=I, intensity_triste=I, intensity_enojado=I, intensity_sospecha=I, subdivide_cuts=3)
            sk = e.shape_key_add(name=expr.capitalize(), from_mix=False); sk.slider_min = -2.0; sk.slider_max = 2.0; sk.value = 0.0
            # "Triste" = "Feliz" con el signo del add-on invertido para la misma zona/inversion: se usa la formula propia de cada una
            for i, o in enumerate(bas): sk.data[i].co = es._eye_compute_vertex(o, h, v, b, expr, S, mirror_h=(side == "R"))
        for expr, frac in EXTRA.items():
            sk = e.shape_key_add(name=expr.capitalize(), from_mix=False); sk.slider_min = -2.0; sk.slider_max = 2.0; sk.value = 0.0
            k = frac / VALOR
            for i, o in enumerate(bas):
                vv = getattr(o, v); cv = {"x": b["cx"], "y": b["cy"], "z": b["cz"]}[v]; rv = {"x": b["rx"], "y": b["ry"], "z": b["rz"]}[v]
                vf = (vv - cv) / (rv / 2) if rv > 0 else 0.0
                if expr == "cansado": off = -(vv - cv) * k * max(vf, 0.0)
                elif expr == "sorpresa": off = (vv - cv) * k * max(vf, 0.0)
                else: off = -(vv - cv) * k * abs(vf) * 0 - (vv - cv) * k
                n = o.copy(); setattr(n, v, vv + off); sk.data[i].co = n
    print("expresiones de los ojos de Alfred reconstruidas con el sistema del add-on (valor de animacion", VALOR, ")")


construir()
