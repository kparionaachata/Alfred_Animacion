# -*- coding: utf-8 -*-
"""
interpolation.py — Alfred Animation Studio v1.8
Implementacion de todas las curvas de interpolacion profesional.
"""
import math

# ─── CURVAS BASICAS ──────────────────────────────────────────
def _interp_linear(t):           return t
def _interp_smooth(t):           return t * t * (3 - 2 * t)
def _interp_ease_in_quad(t):     return t * t
def _interp_ease_out_quad(t):    return 1 - (1 - t) ** 2
def _interp_ease_in_out_quad(t):
    return 2*t*t if t < 0.5 else 1 - (-2*t+2)**2 / 2

def _interp_ease_in_cubic(t):    return t * t * t
def _interp_ease_out_cubic(t):   return 1 - (1 - t) ** 3
def _interp_ease_in_out_cubic(t):
    return 4*t*t*t if t < 0.5 else 1 - (-2*t+2)**3 / 2

def _interp_ease_in_quart(t):    return t ** 4
def _interp_ease_out_quart(t):   return 1 - (1 - t) ** 4
def _interp_ease_in_out_quart(t):
    return 8*t**4 if t < 0.5 else 1 - (-2*t+2)**4 / 2

def _interp_ease_in_expo(t):
    return 0.0 if t == 0 else 2 ** (10*t - 10)
def _interp_ease_out_expo(t):
    return 1.0 if t == 1 else 1 - 2 ** (-10*t)
def _interp_ease_in_out_expo(t):
    if t == 0: return 0.0
    if t == 1: return 1.0
    return (2**(20*t-10))/2 if t < 0.5 else (2-2**(-20*t+10))/2

def _interp_ease_in_sine(t):     return 1 - math.cos(t * math.pi / 2)
def _interp_ease_out_sine(t):    return math.sin(t * math.pi / 2)
def _interp_ease_in_out_sine(t): return -(math.cos(math.pi * t) - 1) / 2

def _interp_ease_in_circ(t):
    return 1 - math.sqrt(max(0, 1 - t * t))
def _interp_ease_out_circ(t):
    return math.sqrt(max(0, 1 - (t - 1) ** 2))
def _interp_ease_in_out_circ(t):
    if t < 0.5:
        return (1 - math.sqrt(max(0, 1 - (2*t)**2))) / 2
    return (math.sqrt(max(0, 1 - (-2*t+2)**2)) + 1) / 2

# ─── BOUNCE ──────────────────────────────────────────────────
def _bounce_out_raw(t):
    n1, d1 = 7.5625, 2.75
    if t < 1/d1:   return n1 * t * t
    elif t < 2/d1: t -= 1.5/d1;   return n1*t*t + 0.75
    elif t < 2.5/d1: t -= 2.25/d1; return n1*t*t + 0.9375
    else:           t -= 2.625/d1; return n1*t*t + 0.984375
def _interp_bounce(t):    return _bounce_out_raw(t)
def _interp_bounce_in(t): return 1 - _bounce_out_raw(1 - t)

# ─── ELASTIC ─────────────────────────────────────────────────
def _interp_elastic(t):
    if t == 0: return 0.0
    if t == 1: return 1.0
    c4 = (2 * math.pi) / 3
    return -(2**(10*t-10)) * math.sin((t*10-10.75)*c4)
def _interp_elastic_in(t):
    if t == 0: return 0.0
    if t == 1: return 1.0
    c4 = (2 * math.pi) / 3
    return 2**(10*t-10) * math.sin((t*10-10.75)*c4)
def _interp_elastic_in_out(t):
    if t == 0: return 0.0
    if t == 1: return 1.0
    c5 = (2 * math.pi) / 4.5
    if t < 0.5:
        return -(2**(20*t-10) * math.sin((20*t-11.125)*c5)) / 2
    return (2**(-20*t+10) * math.sin((20*t-11.125)*c5)) / 2 + 1

# ─── SPRING ──────────────────────────────────────────────────
def _interp_spring(t):
    if t == 0: return 0.0
    if t == 1: return 1.0
    decay = 6.0; freq = 35.0; amp = 1.0
    return 1 - math.exp(-decay*t) * math.cos(freq*t) * amp
def _interp_spring_heavy(t):
    if t == 0: return 0.0
    if t == 1: return 1.0
    return 1 - math.exp(-5.0*t) * math.cos(20.0*t)
def _interp_spring_light(t):
    if t == 0: return 0.0
    if t == 1: return 1.0
    return 1 - math.exp(-4.0*t) * math.cos(50.0*t)

# ─── PRINCIPIOS DISNEY ──────────────────────────────────────
def _interp_anticipation(t):
    overshoot = 0.15
    if t < 0.2:
        return -overshoot * math.sin(t / 0.2 * math.pi)
    return _interp_ease_out_cubic((t - 0.2) / 0.8)
def _interp_anticipation_strong(t):
    overshoot = 0.35
    if t < 0.25:
        return -overshoot * math.sin(t / 0.25 * math.pi)
    return _interp_ease_out_cubic((t - 0.25) / 0.75)
def _interp_overshoot(t):
    if t < 0.85:
        return _interp_ease_in_out_cubic(t / 0.85) * 1.15
    return 1.15 - 0.15 * (t - 0.85) / 0.15
def _interp_overshoot_strong(t):
    if t < 0.8:
        return _interp_ease_in_cubic(t / 0.8) * 1.35
    return 1.35 - 0.35 * (t - 0.8) / 0.2
def _interp_ease_in_back(t):
    c1 = 1.70158; c3 = c1 + 1
    return c3*t*t*t - c1*t*t
def _interp_ease_out_back(t):
    c1 = 1.70158; c3 = c1 + 1
    return 1 + c3*(t-1)**3 + c1*(t-1)**2
def _interp_ease_in_out_back(t):
    c1 = 1.70158; c2 = c1 * 1.525
    if t < 0.5:
        return ((2*t)**2 * ((c2+1)*2*t - c2)) / 2
    return ((2*t-2)**2 * ((c2+1)*(2*t-2) + c2) + 2) / 2
def _interp_follow_through(t):
    if t < 0.7:
        return _interp_ease_in_out_cubic(t / 0.7)
    elif t < 0.85:
        return 1.0 + 0.08 * math.sin((t-0.7)/0.15 * math.pi)
    return 1.0 + 0.08 * math.sin((t-0.7)/0.15 * math.pi) * (1-(t-0.85)/0.15)
def _interp_squash_stretch(t):
    if t < 0.05:   return _interp_ease_in_cubic(t / 0.05) * 0.05
    elif t < 0.7:  return 0.05 + _interp_ease_out_expo((t-0.05)/0.65) * 0.95
    return 1.0 + 0.04 * math.sin((t-0.7)/0.3 * math.pi * 2) * (1-(t-0.7)/0.3)

# ─── ESPECIALES ──────────────────────────────────────────────
def _interp_stepped(t):          return 0.0 if t < 1.0 else 1.0
def _interp_hold_then_go(t):
    hold = 0.6
    return 0.0 if t < hold else _interp_ease_out_cubic((t-hold)/(1-hold))
def _interp_slow_in_fast_out(t): return _interp_ease_in_out_quad(t) if t < 0.5 else _interp_ease_out_expo(t)
def _interp_fast_in_slow_out(t): return _interp_ease_in_expo(t) if t < 0.5 else _interp_ease_in_out_quad(t)

# ─── DISPATCHER ─────────────────────────────────────────────
_CURVE_MAP = {
    "LINEAR":           _interp_linear,
    "SMOOTH":           _interp_smooth,
    "EASE_IN_QUAD":     _interp_ease_in_quad,
    "EASE_OUT_QUAD":    _interp_ease_out_quad,
    "EASE_IN_OUT_QUAD": _interp_ease_in_out_quad,
    "EASE_IN_CUBIC":    _interp_ease_in_cubic,
    "EASE_OUT_CUBIC":   _interp_ease_out_cubic,
    "EASE_IN_OUT_CUB":  _interp_ease_in_out_cubic,
    "EASE_IN_QUART":    _interp_ease_in_quart,
    "EASE_OUT_QUART":   _interp_ease_out_quart,
    "EASE_IN_OUT_QRT":  _interp_ease_in_out_quart,
    "EASE_IN_EXPO":     _interp_ease_in_expo,
    "EASE_OUT_EXPO":    _interp_ease_out_expo,
    "EASE_IN_OUT_EXP":  _interp_ease_in_out_expo,
    "EASE_IN_SINE":     _interp_ease_in_sine,
    "EASE_OUT_SINE":    _interp_ease_out_sine,
    "EASE_IN_OUT_SIN":  _interp_ease_in_out_sine,
    "EASE_IN_CIRC":     _interp_ease_in_circ,
    "EASE_OUT_CIRC":    _interp_ease_out_circ,
    "EASE_IN_OUT_CIR":  _interp_ease_in_out_circ,
    "BOUNCE":           _interp_bounce,
    "BOUNCE_IN":        _interp_bounce_in,
    "ELASTIC":          _interp_elastic,
    "ELASTIC_IN":       _interp_elastic_in,
    "ELASTIC_IN_OUT":   _interp_elastic_in_out,
    "SPRING":           _interp_spring,
    "SPRING_HEAVY":     _interp_spring_heavy,
    "SPRING_LIGHT":     _interp_spring_light,
    "ANTICIPATION":     _interp_anticipation,
    "ANTICIPATION_STR": _interp_anticipation_strong,
    "OVERSHOOT":        _interp_overshoot,
    "OVERSHOOT_STR":    _interp_overshoot_strong,
    "FOLLOW_THROUGH":   _interp_follow_through,
    "SQUASH_STRETCH":   _interp_squash_stretch,
    "STEPPED":          _interp_stepped,
    "HOLD_THEN_GO":     _interp_hold_then_go,
    "SLOW_IN_FAST_OUT": _interp_slow_in_fast_out,
    "FAST_IN_SLOW_OUT": _interp_fast_in_slow_out,
    "EASE_IN_BACK":     _interp_ease_in_back,
    "EASE_OUT_BACK":    _interp_ease_out_back,
    "EASE_IN_OUT_BCK":  _interp_ease_in_out_back,
}

def apply_interp(t, interp_type):
    fn = _CURVE_MAP.get(interp_type, _interp_smooth)
    # IMPORTANTE: NO clampear la salida — curvas como BOUNCE, ELASTIC, SPRING,
    # ANTICIPATION, OVERSHOOT, FOLLOW_THROUGH y SQUASH_STRETCH intencionalmente
    # producen valores fuera de [0,1] para lograr su efecto visual.
    # Solo clampear la entrada t para evitar evaluacion fuera de dominio.
    return fn(max(0.0, min(1.0, t)))
