# -*- coding: utf-8 -*-
"""Parte 11: Jerry, ya girado hacia Alfred despues de dejar el pescado, le pregunta "¿Voy a ir... tu no vas a comer?".
Audio: audios/jerry/jerry_voy_a_ir_tu_no_vas_a_comer.wav; cara: jerry_voy_a_ir_tu_no_vas_a_comer.cara_original.py (archivo del usuario).
Todo lo hace voz_jerry_comun.aplicar (boca, cabeza, cejas, ojos, pupilas, parpadeo, sumado a la accion de jerry_nada_pescado_parte11.py).
Volumen 1.3 (+30%, pedido del usuario). Repetible. Al final aplica el MICROFONO de camara."""
import bpy, os, importlib.util

BASE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\parte11"
AUDIO = r"C:\Users\user\Desktop\Alfred_Animacion\audios\jerry\jerry_voy_a_ir_tu_no_vas_a_comer.wav"
CARA = r"C:\Users\user\Desktop\Alfred_Animacion\audios\jerry\jerry_voy_a_ir_tu_no_vas_a_comer.cara_original.py"
NOMBRE = "VOZ_p11_jerry_voy_a_ir"; MARCA = "voz_jerry_voy_a_ir"
VOLUMEN = 1.3                               # +30% (pedido del usuario), antes del microfono
ESPERA = 6                                  # frames desde que termina de girar hasta que habla


def _comun():
    sp = importlib.util.spec_from_file_location("voz_jerry_comun", os.path.join(BASE, "voz_jerry_comun.py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


def construir(con_microfono=True):
    sc = bpy.context.scene; F0 = int(sc["p11_jerry"]["mira_alfred"]) + ESPERA
    F0, F1 = _comun().aplicar(AUDIO, CARA, NOMBRE, F0, MARCA, VOLUMEN, 31, con_microfono)
    sc["p11_voz_jerry"] = {"inicio": F0, "fin": F1}
    print("VOZ JERRY 'voy a ir':", F0, "-", F1)
    return F0


if __name__ in ("__main__", "x"):
    construir()
