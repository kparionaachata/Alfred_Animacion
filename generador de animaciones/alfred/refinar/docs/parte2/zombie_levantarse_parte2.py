"""Parte 2 - LEVANTARSE ORGANICO de los zombies tras el empujon de Jerry (pedido de Kebyn). Lo importa `compose_zombies_parte2.py`.
Antes: la subida era una bisagra rigida (Hips X -90 -> 0 con smoothstep, 26-36 f, con los pies deslizando) y todos los huesos volvian a la pose base a la vez.
Ahora la subida (RISE_F + RISE_EXTRA frames, tomados del tiempo tendido; la duracion total del empujon NO cambia) tiene fases con retardos entre huesos:
  1) ESFUERZO (u 0-0.25): la cabeza se levanta primero (cuello), el torso se enrosca (columna con flexion), los brazos empujan el suelo, las rodillas se recogen; el cuerpo apenas se incorpora.
  2) SENTARSE (u 0.1-0.45): el torso se incorpora hasta ~60 % (lam 0.62) con la columna enroscada y una torsion lateral (cada zombie hacia un lado).
  3) PAUSA / APOYO (u 0.4-0.52): se queda sentado un instante, apoyado en los brazos.
  4) LEVANTARSE (u 0.5-0.9): pivota sobre los pies (rodillas flexionadas -> se extienden), el torso se desenrosca, los brazos caen balanceandose; se pasa un poco de la vertical hacia delante (lam -0.07).
  5) TAMBALEO (u 0.9-1): vuelve a la vertical con un ligero rebote de cabeza y brazos.
`compose_zombies_parte2.py` ademas corrige, con las tablas medidas en Blender (`levantarse_correccion.json`, ver `medir_levantarse.py`), la altura de la cadera (nada atraviesa el suelo y el cuerpo sube al empujar con los brazos)
y el desplazamiento horizontal de la cadera (los pies quedan PLANTADOS mientras el cuerpo pivota sobre ellos, sin deslizar).
"""
import math

RISE_EXTRA = 14                                                                   # frames que la subida le quita al tiempo tendido (FREEZE no cambia)


def ss(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def lam_rise(u):
    """lam = Hips X / -90 (1 tendido, 0 de pie); pasa un poco de la vertical (negativo = inclinado hacia delante) y vuelve."""
    return 1.0 - 0.38 * ss((u - 0.08) / 0.34) - 0.69 * ss((u - 0.50) / 0.40) + 0.07 * ss((u - 0.90) / 0.10)


def rise_extra(short, u, n, fv):
    """rotacion adicional (rad, XYZ) del hueso `short` en el instante u de la subida (n = numero de zombie; fv = variante de caida del zombie)."""
    side = 1.0 if n % 2 == 0 else -1.0                                            # cada zombie se incorpora hacia un lado distinto
    vig = 0.85 + (0.07 * n) % 0.30                                                    # vigor distinto por zombie
    curl = ss((u - 0.04) / 0.30) * (1.0 - ss((u - 0.55) / 0.35))                    # columna enroscada: sube con el sentarse y se desenrosca al levantarse
    lead = ss((u - 0.00) / 0.16) * (1.0 - ss((u - 0.40) / 0.30))                    # la cabeza se adelanta
    after = ss((u - 0.62) / 0.25) * (1.0 - ss((u - 0.92) / 0.08))                   # rebote de cabeza/brazos al ponerse de pie
    push = ss((u - 0.05) / 0.15) * (1.0 - ss((u - 0.46) / 0.20))                    # brazos apoyados empujando el suelo
    squat = ss((u - 0.30) / 0.20) * (1.0 - ss((u - 0.62) / 0.28))                   # rodillas flexionadas mientras pivota sobre los pies
    d = [0.0, 0.0, 0.0]
    if short == "Spine": d[0] += 0.30 * vig * curl; d[2] += 0.10 * side * curl
    elif short == "Spine1": d[0] += 0.32 * vig * curl; d[2] += 0.14 * side * curl
    elif short == "Spine2": d[0] += 0.28 * vig * curl; d[2] += 0.10 * side * curl; d[0] -= 0.10 * after
    elif short == "Neck": d[0] += 0.55 * lead - 0.12 * after; d[2] += 0.30 * side * lead
    elif short == "RightUpArm": d[2] += 0.55 * push; d[0] += 0.10 * math.sin(u * 9.0 + n) * push
    elif short == "LeftUpArm": d[2] -= 0.55 * push; d[0] += 0.10 * math.sin(u * 9.0 + n + 1.7) * push
    elif short in ("Rightelbow", "Leftelbow"): d[2] += (-1.0 if short[0] == "R" else 1.0) * (0.35 * push + 0.20 * after)
    elif short in ("RightUpLeg", "LeftUpLeg"): d[0] += -0.55 * squat
    elif short in ("Rightknee", "Leftknee"): d[0] += 0.85 * squat
    elif short == "Hips": d[2] += 0.12 * side * curl * (1.0 - ss((u - 0.5) / 0.3))
    return d
