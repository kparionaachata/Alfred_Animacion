# -*- coding: utf-8 -*-
"""Parametros del tipo de tramo `cuerpo` (S03-S14 de Alfred: lanzar herramientas, manos en la nuca, barrido, de rodillas, mesa de crafteo, craftear, tablones y slabs, levantarse y cavar, hacha, corte, asomarse): las tablas del
generador (`sentarse_en_refugio.py`, exportadas a `datos_guion/tablas_cuerpo.json` por `limpio/exportar_tablas.py`) con los nombres y las convenciones del guion (los tiempos llevan prefijo `t_`; las listas de tiempos, `tt_`).
Se usa desde `construir_movimiento_guion.py` y desde `limpio/explorar_tramo.py`."""
import json
import os

R = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"


def tablas():
    with open(os.path.join(R, "docs", "parte3", "datos_guion", "tablas_cuerpo.json"), encoding="utf-8") as f: return json.load(f)


def parametros_cuerpo(T=None):
    T = T or tablas()
    return {
        "base_de": "S01_sentarse",
        "lean": T["LEAN"], "t_lean_sube": T["LEAN_UP"], "t_lean_tope": T["LEAN_TOP"], "t_lean_baja": T["LEAN_DOWN"], "lean_baja_dur": 12,
        "tiempos": {"alcanza": T["REACH_D"], "sostiene": T["HOLD_D"], "lanza": T["SWING_D"], "vuelve": T["BACK_D"]},
        "agarres": [{"objeto": n, "lado": s, "t_toma": gf, "delta": list(dl)} for n, s, gf, dl in T["THROWS"]],
        "estudio": {"u": T["STUDIO_U"], "e": T["STUDIO_E"], "loc": T["STUDIO_LOC"]}, "suelta": T["REL_Q"],
        "nuca": {"t_ini": T["NUCA0"], "dur": T["NUCA_D"], "q": T["NUCA_Q"]},
        "sit": {"t_ini": T["SIT_T"][0], "t_fin": T["SIT_T"][1], "q": T["SIT_Q"]},
        "barrido": {"tt_claves": T["CLR_KEYS"], "q": T["CLR_Q"], "sw": T["CLR_SW"], "inclinacion": T["CLR_T"], "reparto": T["CLR_LEANW"], "tt_inclinacion": T["CLR_LEAN"]},
        "rodillas": {"t_ini": T["KN0"], "t_fin": T["KN1"], "pierna": T["KN_LEG"], "hips_y": T["KN_HIPY"], "x": T["KN_X"], "tt_inclina": T["KN_LEAN"], "tt_cuello": T["KN_NECK"], "tt_mirada": T["KN_LOOKY"]},
        "de_pie": {"t_ini": T["ASTAND0"], "dur": T["ASTAND_D"], "x": T["STAND_X"], "y": T["STAND_Y"]},
        "giro": {"t_ini1": T["ROT0"], "dur1": T["ROT_D"], "t_ini2": T["ROT2_0"], "dur2": T["ROT2_D"]},
        "brazos": {"poses": T["MESA_E"], "tt_tbk": T["TBK"], "tt_pre_r": T["TBK_PRE_R"], "tt_pre_l": T["TBK_PRE_L"], "tt_x_right": T["TBK_X"]["Right"], "tt_x_left": T["TBK_X"]["Left"]},
        "root": {"antorcha": {"t_ini": 533, "t_fin": 548, "dur": 12, "dx": T["TORCH_DX"]}, "scoot": {"t_ini": T["SCOOT0"], "dur": T["SCOOT_D"], "dx": T["SCOOT_DX"]},
                 "corte": {"t_avance": 1017, "avance_dur": 4, "avance": 0.19, "t_retroceso": 1062, "retroceso_dur": 12, "retroceso": -0.49}, "pozo": {"t_ini": T["FALL0"], "dur": T["FALL_D"], "baja": 1.0}}}
