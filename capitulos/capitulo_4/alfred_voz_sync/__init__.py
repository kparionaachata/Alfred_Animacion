"""Alfred Voz Sync - sincroniza la voz de Alfred o Jerry con el movimiento del personaje y le da la EMOCION de lo que dice.

Biblioteca de audios: carpeta `C:\\Users\\user\\Desktop\\Alfred_Animacion\\audios` con una subcarpeta por personaje (`alfred`, `jerry`; se aceptan subcarpetas dentro de ellas).
El panel lista los audios del personaje elegido (con su duracion) y cada uno tiene su propio frame de inicio. Para cada audio el add-on:
  1. VOZ: mide frame a frame la INTENSIDAD (volumen RMS) y la DURACION. Jerry: la mandibula (`jaw_bot`) se abre con cada silaba y se cierra en los silencios; la cabeza (`scull`, `scull_1`)
     cabecea con los acentos y se mueve mientras habla. Alfred (sin mandibula): solo la cabeza (`Neck_alfred` + un poco de `Spine2_alfred`).
  2. EMOCION: decide que emocion expresa el audio (enojo, alegria, tristeza, sueno, miedo, sorpresa o neutro) y la reparte durante TODA la duracion del audio como una capa de animacion:
     postura de cabeza y torso, temblor, respiracion, ojos de Alfred (shape keys), cejas / orejas / cola de Jerry. La emocion se decide, por orden, con: lo que elijas en el panel; el archivo
     `<audio>.emocion.json` junto al mp3 (texto, emocion, intensidad y segmentos: ahi se anota el CONTEXTO y las PALABRAS entendidas); el texto (palabras clave); y, si no hay nada de eso, una
     estimacion acustica (volumen, tono, variacion del tono, ritmo, brillo, pausas).
Todo se crea como pistas NLA ADITIVAS (`VozSync_<PERSONAJE>_<audio>`, y una por cada ojo de Alfred) que se SUMAN a la animacion que el personaje ya tenga (si corre, sigue corriendo), asi no se pierde
nada. Se puede quitar con "Quitar".

Panel: Vista 3D > barra lateral (N) > pestana "Voz Sync".
"""
bl_info = {
    "name": "Alfred Voz Sync",
    "author": "Kebyn",
    "version": (1, 2, 0),
    "blender": (4, 4, 0),
    "location": "Vista 3D > barra lateral (N) > Voz Sync",
    "description": "Sincroniza voz (duracion e intensidad) y emocion del audio con la cabeza, la mandibula y el cuerpo de Alfred y Jerry, en capas aditivas",
    "category": "Animation",
}

import json
import math
import os
import re
import unicodedata

import bpy
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup, UIList

PREFIJO_PISTA = "VozSync_"
CARPETA_AUDIOS = r"C:\Users\user\Desktop\Alfred_Animacion\audios"
EXTENSIONES = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac", ".opus", ".wma"}
EMOCIONES = ("NEUTRO", "ENOJO", "ALEGRIA", "TRISTEZA", "SUENO", "MIEDO", "SORPRESA", "DUDA")
PYTHON_ESTUDIO = r"C:\Users\user\Desktop\Alfred_Animacion\voz_a_voz\Applio\env\Scripts\python.exe"          # Python de la app estudio_audio_expresion (librosa, torch, transformers, Whisper)

# Huesos y amplitudes por personaje (grados con "Intensidad de la cabeza" = 1). Convencion de ambos rigs (comprobada en Blender): en el cuello/craneo X+ = cabecear hacia abajo, Z = girar, Y = inclinar.
# `torso` = (hueso, factor) para inclinar el torso hacia ADELANTE `lean` grados (Alfred: Spine* X+ inclina adelante; Jerry: spine_5/6 X- inclina adelante); `resp` = hueso de la respiracion.
PERSONAJES = {
    "JERRY": {
        "etiqueta": "Jerry", "subcarpeta": "jerry", "hueso_clave": "jaw_bot", "rig_por_defecto": "Dog_001_rig",
        "cabeza": [("scull", 1.0), ("scull_1", 0.35)], "mandibula": "jaw_bot",
        "pitch": 9.0, "yaw": 11.0, "roll": 5.0,
        "torso": [("spine_6", -0.5), ("spine_5", -0.5)], "resp": ("spine_5", -1.0),
        "orejas": [("ear.R", 1.0), ("ear.L", 1.0)], "cola": [("tail_1", 1.0, 1.0, 0.0), ("tail_2", 0.6, 0.8, -0.6), ("tail_3", 0.4, 0.6, -1.2)],
        "cejas": ("sejas_1_jerry", "sejas_2_jerry"),
        "ojos_obj": ["ojo_izquierdo_jerry", "ojo_derecho_jerry", "pupila_izquierda_jerry", "pupila_derecha_jerry"], "ojos_claves": ["Closed"],
    },
    "ALFRED": {
        "etiqueta": "Alfred", "subcarpeta": "alfred", "hueso_clave": "Neck_alfred", "rig_por_defecto": "a",
        "cabeza": [("Neck_alfred", 1.0), ("Spine2_alfred", 0.25)], "mandibula": None,
        "pitch": 8.0, "yaw": 10.0, "roll": 4.0,
        "torso": [("Spine_alfred", 0.4), ("Spine1_alfred", 0.35), ("Spine2_alfred", 0.25)], "resp": ("Spine1_alfred", 1.0),
        "orejas": [], "cola": [], "cejas": None,
        "ojos_obj": ["ojo_izquierdo_alfred", "ojo_derecho_alfred"], "ojos_claves": ["Feliz", "Triste", "Enojado", "Sospecha", "Cansado", "Cerrado", "Sorpresa", "Closed"],
    },
}

# Perfil de cada emocion (se suman ponderados por su peso en el tiempo). pitch/roll: postura fija de la cabeza (grados; pitch+ = baja la cabeza); nod/giro/incl/mand: multiplicadores de los movimientos
# que salen de la voz; balanceo=(grados, Hz) vaiven de la cabeza mientras habla; temblor=(grados, Hz); lean: torso hacia adelante (grados); resp=(grados, Hz) respiracion; ojos: shape keys de los ojos
# (convencion del proyecto: 0.06 = expresion completa); ceja: pose de cejas de Jerry (estudio); orejas: grados (+ = atras/abajo); cola=(bajar grados +, meneo grados, Hz); sag: cabeceo de sueno (grados).
PERFILES = {
    "NEUTRO": {},
    "ENOJO": dict(pitch=8.0, roll=0.0, nod=1.6, giro=0.45, incl=0.4, mand=1.3, balanceo=(0.0, 0.0), temblor=(0.9, 11.0), lean=8.0, resp=(1.6, 0.9), ojos={"Enojado": 0.06, "Sospecha": 0.015}, ceja="enojado", orejas=25.0, cola=(14.0, 0.0, 0.0), sag=0.0),
    "ALEGRIA": dict(pitch=-6.0, roll=0.0, nod=1.25, giro=1.5, incl=1.5, mand=1.15, balanceo=(2.5, 1.2), temblor=(0.0, 0.0), lean=-3.0, resp=(1.0, 0.7), ojos={"Feliz": 0.06}, ceja=None, orejas=-15.0, cola=(-18.0, 22.0, 3.5), sag=0.0),
    "TRISTEZA": dict(pitch=14.0, roll=4.0, nod=0.4, giro=0.35, incl=0.4, mand=0.7, balanceo=(0.0, 0.0), temblor=(0.25, 6.0), lean=10.0, resp=(2.0, 0.3), ojos={"Triste": 0.06, "Cansado": 0.02}, ceja="triste", orejas=30.0, cola=(35.0, 0.0, 0.0), sag=0.0),
    "SUENO": dict(pitch=10.0, roll=3.0, nod=0.3, giro=0.3, incl=0.3, mand=0.6, balanceo=(0.0, 0.0), temblor=(0.0, 0.0), lean=6.0, resp=(2.5, 0.25), ojos={"Cansado": 0.06, "Closed": 0.5}, ceja=None, orejas=20.0, cola=(25.0, 0.0, 0.0), sag=14.0),
    "MIEDO": dict(pitch=-8.0, roll=2.0, nod=0.7, giro=0.9, incl=1.2, mand=1.0, balanceo=(0.0, 0.0), temblor=(1.5, 16.0), lean=-6.0, resp=(2.0, 1.6), ojos={"Sorpresa": 0.06, "Sospecha": 0.03}, ceja="triste", orejas=35.0, cola=(45.0, 0.0, 0.0), sag=0.0),
    "DUDA": dict(pitch=-2.0, roll=7.0, nod=0.6, giro=0.8, incl=1.2, mand=0.9, balanceo=(1.5, 0.4), temblor=(0.0, 0.0), lean=-2.0, resp=(0.9, 0.6), ojos={"Sospecha": 0.05, "Triste": 0.015}, ceja="duda", orejas=-8.0, cola=(4.0, 3.0, 0.8), sag=0.0),
    "SORPRESA": dict(pitch=-10.0, roll=0.0, nod=0.8, giro=0.6, incl=0.6, mand=1.2, balanceo=(0.0, 0.0), temblor=(0.4, 14.0), lean=-5.0, resp=(1.2, 1.0), ojos={"Sorpresa": 0.06}, ceja="sorprendido", orejas=-20.0, cola=(-10.0, 8.0, 2.0), sag=0.0),
}

# Poses de cejas de Jerry (estudio de Jerry, `_EMOTION_POSES`): rotacion Euler XYZ (rad) y localizacion local; posicion base capturada de cada ceja.
CEJAS_POSES = {
    "enojado": {"sejas_1_jerry": ((0.018057, 0.032724, 0.466682), (0.00746, -0.011135, 0.000709)), "sejas_2_jerry": ((0.059813, -0.027015, -0.463214), (0.020687, -0.018262, 0.005866))},
    "triste": {"sejas_1_jerry": ((0.002696, -0.051839, -0.649442), (0.008732, -0.027737, 0.001994)), "sejas_2_jerry": ((-0.04654, 0.063158, 0.5541), (0.020013, -0.031002, 0.003717))},
    "duda": {"sejas_1_jerry": ((-0.002724, -0.014304, -0.180244), (0.016415, -0.030631, 0.001622)), "sejas_2_jerry": ((-0.020113, 0.020089, 0.198146), (0.01384, 0.000266, 0.000305))},      # 'levanta_la_ceja_izquierda' del estudio
    "sorprendido": {"sejas_1_jerry": ((0.001155, -0.049993, -0.613817), (0.019916, -0.009849, -0.000639)), "sejas_2_jerry": ((-0.047893, 0.064076, 0.570414), (0.010334, -0.010014, 0.000792))},
}

# Palabras clave (sin tildes, minusculas) para estimar la emocion del TEXTO cuando no hay anotacion de contexto.
LEXICO = {
    "ENOJO": ["odio", "maldit", "idiota", "estupid", "callate", "furios", "rabia", "enojad", "enfadad", "basta", "largo de", "imbecil", "cabron", "mierda", "te voy a", "como te atreves", "harto"],
    "ALEGRIA": ["feliz", "alegr", "genial", "excelente", "jaja", "jeje", "gracias", "fantastic", "yupi", "divertid", "te amo", "bravo", "lo logramos", "buenisimo", "increible!", "hurra", "si!"],
    "TRISTEZA": ["triste", "llor", "perdon", "lo siento", "pena", "adios", "extrano", "muert", "perdi", "ya no", "nunca mas", "solo estoy", "duele"],
    "SUENO": ["sueno", "dormir", "cansad", "bostez", "zzz", "agotad", "descans", "mmm", "que flojera", "buenas noches"],
    "MIEDO": ["miedo", "ayuda", "socorro", "cuidado", "corre", "corran", "peligro", "monstruo", "zombi", "aaah", "aahh", "asust", "no me", "por favor no", "van a"],
    "DUDA": ["no se", "tal vez", "quizas", "sera que", "que hacemos", "y ahora", "por que", "como hacemos", "no estoy seguro", "?"],
    "SORPRESA": ["wow", "vaya", "no puede ser", "en serio", "sorpresa", "oh!", "que?!", "no lo", "de repente", "mira eso"],
}


# ------------------------------------------------------------------------------------------------------------------------------------ audio / senal
def cargar_audio(ruta):
    """(muestras mono float32, frecuencia de muestreo) con el modulo `aud` de Blender (wav, mp3, ogg, flac...)."""
    import aud
    import numpy as np
    snd = aud.Sound(bpy.path.abspath(ruta))
    rate, _canales = snd.specs
    datos = np.asarray(snd.data(), dtype=np.float32)
    if datos.ndim == 2: datos = datos.mean(axis=1)
    return datos, int(rate)


def duracion_audio(ruta):
    """segundos (sin decodificar todo el archivo), o 0.0 si no se puede leer."""
    try:
        import aud
        snd = aud.Sound(bpy.path.abspath(ruta)); rate, _c = snd.specs
        return float(snd.length) / float(rate)
    except Exception:
        return 0.0


def rms_por_frame(mono, rate, fps):
    """volumen RMS de cada frame (ventana de 2 frames centrada en el frame, para no perder silabas cortas)."""
    import numpy as np
    spf = rate / float(fps); n = int(math.ceil(len(mono) / spf))
    cs = np.concatenate(([0.0], np.cumsum(mono.astype(np.float64) ** 2)))
    i0 = np.clip(((np.arange(n) - 0.5) * spf).astype(np.int64), 0, len(mono)); i1 = np.clip(((np.arange(n) + 1.5) * spf).astype(np.int64), 0, len(mono))
    return np.sqrt((cs[i1] - cs[i0]) / np.maximum(1, i1 - i0))


def normalizar(rms, umbral, ganancia):
    """0..1: por debajo del umbral (fraccion del pico) es silencio; el pico (percentil 95) es 1; `ganancia` escala; curva suave (gamma 0.8)."""
    import numpy as np
    if len(rms) == 0 or float(rms.max()) <= 0.0: return np.zeros(len(rms))
    pico = float(np.percentile(rms, 95)) or float(rms.max()); thr = umbral * pico
    x = np.clip((rms - thr) / max(pico - thr, 1e-9), 0.0, 1.5)
    return np.clip((x ** 0.8) * ganancia, 0.0, 1.0)


def ela(t):
    """Elastic In-Out (misma curva que `ELASTIC_IN_OUT` de interpolation.py del add-on Alfred Animation Studio y que `ela()` de compose_parte2.py): 0 -> 1 con doble tension elastica (sobreoscila ~10 %)."""
    if t <= 0: return 0.0
    if t >= 1: return 1.0
    c5 = (2 * math.pi) / 4.5
    if t < 0.5: return -(2 ** (20 * t - 10) * math.sin((20 * t - 11.125) * c5)) / 2
    return (2 ** (-20 * t + 10) * math.sin((20 * t - 11.125) * c5)) / 2 + 1


def ela_vec(u):
    import numpy as np
    return np.array([ela(float(v)) for v in np.asarray(u, dtype=float)])


def ela_entre(xs, ys, n):
    """serie de n valores que pasa por los puntos (xs, ys) con Elastic In-Out entre cada par de keyframes (como la interpolacion ELASTIC / EASE_IN_OUT de Blender); fuera de los puntos mantiene el primer / ultimo valor."""
    import numpy as np
    out = np.full(n, float(ys[0])); ux, uy = [], []
    for x_, y_ in zip(xs, ys):
        if ux and x_ <= ux[-1]: uy[-1] = y_ if x_ == ux[-1] else uy[-1]; continue
        ux.append(float(x_)); uy.append(float(y_))
    t = np.arange(n, dtype=float)
    out[t >= ux[-1]] = uy[-1]
    for k in range(len(ux) - 1):
        sel = (t >= ux[k]) & (t < ux[k + 1])
        if sel.any(): out[sel] = uy[k] + (uy[k + 1] - uy[k]) * ela_vec((t[sel] - ux[k]) / (ux[k + 1] - ux[k]))
    return out


def suavizar(x, ataque, liberacion):
    """filtro de un polo con constantes distintas al subir (ataque) y al bajar (liberacion), en frames."""
    import numpy as np
    a = 1.0 - math.exp(-1.0 / max(ataque, 0.05)); r = 1.0 - math.exp(-1.0 / max(liberacion, 0.05)); y = np.zeros(len(x)); v = 0.0
    for i, t in enumerate(x):
        v += (t - v) * (a if t > v else r); y[i] = v
    return y


def senales(x, fps, semilla, props, palabras=None, lead=0, elastico=False):
    """de la envolvente normalizada x (0..1 por frame) saca: apertura de mandibula, cabeceo, giro e inclinacion (todo 0..1 / -1..1, antes de multiplicar por las amplitudes).
    `palabras` = [(t0, t1)] en segundos desde el inicio del audio (si el contexto las trae): cada palabra empieza con un cabeceo ademas de los acentos detectados en el volumen."""
    import numpy as np
    n = len(x); t = np.arange(n) / float(fps); rs = np.random.RandomState(semilla)
    mandibula = suavizar(x, 0.7, 1.8)                                              # la mandibula sigue cada silaba: abre rapido, cierra un poco mas lento
    rapida = suavizar(x, 1.0, 3.0); habla = suavizar(x, 4.0 * props.suavidad, 14.0 * props.suavidad)       # habla = intensidad lenta (el cuerpo/cabeza se "activan" mientras habla)
    nod = np.zeros(n + 40); ultimo = -99
    for i in range(3, n):                                                          # acentos: subida rapida de la envolvente -> cabeceo amortiguado
        d = rapida[i] - rapida[i - 3]
        if d > 0.22 and rapida[i] > 0.3 and i - ultimo > 6:
            amp = min(1.0, d * 2.0 + 0.2) * (0.5 + 0.5 * rapida[i]); ultimo = i
            for j in range(30): nod[i + j] += amp * (ela(j / 6.0) * (1.0 - ela((j - 6) / 10.0)) if elastico else math.sin(math.pi * j / 10.0) * math.exp(-j / 9.0))
    for t0, t1 in (palabras or []):                                                # cada palabra conocida: cabeceo en su inicio REAL (Whisper da tiempos aproximados: se ancla a la primera subida de energia de su ventana)
        a0 = max(0, int(round(t0 * fps)) + lead - 4); a1 = min(n, int(round(t1 * fps)) + lead + 2)
        if a1 <= a0: continue
        ven = x[a0:a1]; sobre = np.nonzero(ven > 0.25)[0]
        if len(sobre) == 0: continue                                               # palabra sin voz en su ventana: no se mueve
        i = a0 + int(sobre[0])
        if i - ultimo > 4:
            amp = 0.35 + 0.65 * float(ven.max()); ultimo = i
            for j in range(30): nod[i + j] += 0.7 * amp * (ela(j / 6.0) * (1.0 - ela((j - 6) / 10.0)) if elastico else math.sin(math.pi * j / 10.0) * math.exp(-j / 9.0))
    nod = nod[:n]
    ph = rs.uniform(0, 2 * math.pi, 8)
    giro = habla * (0.65 * np.sin(2 * math.pi * 0.23 * t + ph[0]) + 0.35 * np.sin(2 * math.pi * 0.51 * t + ph[1]))
    incl = habla * (0.6 * np.sin(2 * math.pi * 0.31 * t + ph[2]) + 0.4 * np.sin(2 * math.pi * 0.77 * t + ph[3]))
    cabeceo = nod + 0.35 * (rapida - habla) - 0.25 * habla * (0.5 + 0.5 * np.sin(2 * math.pi * 0.19 * t + ph[4]))     # cabeceo con los acentos; levanta un poco el menton mientras habla
    return {"mandibula": mandibula, "cabeceo": cabeceo, "giro": giro, "inclinacion": incl, "habla": habla, "fases": ph}


# ------------------------------------------------------------------------------------------------------------------------------------ emocion: deteccion
def _sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def emocion_por_texto(texto):
    """(emocion, intensidad 0..1.5) a partir del texto, o (None, 0). Cuenta palabras clave; los '!' y las MAYUSCULAS suben la intensidad."""
    if not texto or not texto.strip(): return None, 0.0
    t = _sin_tildes(texto); cuentas = {e: sum(t.count(w) for w in ws) for e, ws in LEXICO.items()}
    mejor = max(cuentas, key=cuentas.get)
    if cuentas[mejor] == 0: return None, 0.0
    exclam = texto.count("!") + texto.count("¡"); mayus = sum(1 for c in texto if c.isupper()) / max(1, sum(1 for c in texto if c.isalpha()))
    return mejor, min(1.5, 0.7 + 0.15 * cuentas[mejor] + 0.1 * min(exclam, 4) + 0.5 * (mayus > 0.5))


def caracteristicas(mono, rate):
    """rasgos acusticos de la voz: nivel (dBFS de los frames con voz), tono F0 (mediana Hz) y su variacion (semitonos), ritmo (silabas/s), brillo (centroide Hz) y proporcion de pausas."""
    import numpy as np
    n = len(mono); hop = max(1, int(0.010 * rate)); fl = int(0.030 * rate)
    if n < fl * 3: return None
    idx = np.arange(0, n - fl, hop); win = np.hanning(fl).astype(np.float32); freqs = np.fft.rfftfreq(fl, 1.0 / rate)
    sq = mono.astype(np.float64) ** 2; cs = np.concatenate(([0.0], np.cumsum(sq))); rms = np.sqrt((cs[idx + fl] - cs[idx]) / fl)
    pico = float(np.percentile(rms, 95))
    if pico <= 1e-5: return None
    voz = rms > 0.15 * pico; lo = max(2, int(rate / 400.0)); hi = int(rate / 70.0); nfft = 1 << int(math.ceil(math.log2(fl * 2)))
    f0s = []; cens = []
    for k in np.nonzero(voz)[0]:
        fr = mono[idx[k]:idx[k] + fl] * win; sp = np.abs(np.fft.rfft(fr)); cens.append(float((sp * freqs).sum() / max(sp.sum(), 1e-9)))
        ac = np.fft.irfft(np.abs(np.fft.rfft(fr, nfft)) ** 2)[:hi + 1]
        if ac[0] > 1e-9 and hi > lo:
            j = int(np.argmax(ac[lo:hi])) + lo
            if ac[j] / ac[0] > 0.4: f0s.append(rate / float(j))
    sm = suavizar(rms / pico, 3.0, 3.0)
    picos = [i for i in range(1, len(sm) - 1) if sm[i] > 0.35 and sm[i] >= sm[i - 1] and sm[i] > sm[i + 1]]; sil = []; ult = -99
    for i in picos:
        if i - ult > 12: sil.append(i); ult = i
    voz_idx = np.nonzero(voz)[0]; dur = max(0.3, (voz_idx[-1] - voz_idx[0]) * hop / rate) if len(voz_idx) else 0.3
    f0s = np.asarray(f0s); f0m = float(np.median(f0s)) if len(f0s) >= 5 else 0.0
    f0v = float(np.std(12.0 * np.log2(f0s / f0m))) if len(f0s) >= 5 else 0.0
    return {"nivel": float(20.0 * math.log10(float(rms[voz].mean()) + 1e-9)), "f0": f0m, "f0_var": f0v, "ritmo": len(sil) / dur if dur > 0.6 else 3.5,
            "brillo": float(np.mean(cens)) if cens else 1000.0, "pausas": float(1.0 - voz.mean())}


def emocion_acustica(c):
    """(emocion, intensidad, descripcion) estimadas SOLO con rasgos acusticos (aproximado: el audio no dice el significado de las palabras)."""
    if not c: return "NEUTRO", 0.0, "audio demasiado corto"
    a_nivel = (c["nivel"] + 24.0) / 8.0; a_ritmo = (c["ritmo"] - 3.5) / 2.0; a_var = (c["f0_var"] - 2.5) / 2.0; a_bril = (c["brillo"] - 1200.0) / 800.0
    exc = 0.35 * a_nivel + 0.25 * a_ritmo + 0.25 * a_var + 0.15 * a_bril
    d = f"excitacion {exc:+.2f} (nivel {c['nivel']:.0f} dBFS, tono {c['f0']:.0f} Hz +-{c['f0_var']:.1f} st, {c['ritmo']:.1f} sil/s, brillo {c['brillo']:.0f} Hz)"
    if exc < -0.6: return ("SUENO" if (c["ritmo"] < 2.2 and c["f0_var"] < 1.5) else "TRISTEZA"), min(1.5, 0.6 + abs(exc) * 0.5), d
    if exc > 0.6:
        if a_nivel < 0.0: return "MIEDO", min(1.5, 0.6 + exc * 0.4), d
        if a_bril > 0.3 and c["f0_var"] < 3.5: return "ENOJO", min(1.5, 0.6 + exc * 0.4), d
        return "ALEGRIA", min(1.5, 0.6 + exc * 0.4), d
    return "NEUTRO", 0.0, d


def ruta_meta(ruta):
    return os.path.splitext(bpy.path.abspath(ruta))[0] + ".emocion.json"


def leer_meta(ruta):
    """contexto del audio: `<audio>.emocion.json` = {texto, emocion, intensidad, segmentos:[{desde, hasta, emocion, intensidad}], palabras:[{t0, t1, w}]} (tiempos en segundos desde el inicio del audio)."""
    try:
        with open(ruta_meta(ruta), encoding="utf-8") as f: return json.load(f)
    except Exception:
        return {}


def resolver_emocion(p, clip, mono, rate, dur):
    """(plan, fuente, palabras): plan = [(t0, t1, emocion, intensidad)] en segundos desde el inicio del audio."""
    k = p.intensidad_emocion; meta = leer_meta(clip.ruta); palabras = [(float(w["t0"]), float(w["t1"])) for w in meta.get("palabras", []) if "t0" in w and "t1" in w]
    if p.emocion != "AUTO": return [(0.0, dur, p.emocion, k)], "panel", palabras
    if meta.get("segmentos"):
        plan = [(float(s.get("desde", 0.0)), float(s.get("hasta", dur)), str(s.get("emocion", "NEUTRO")).upper(), float(s.get("intensidad", 1.0)) * k) for s in meta["segmentos"]]
        return plan, "contexto (.emocion.json: segmentos)", palabras
    if meta.get("emocion"): return [(0.0, dur, str(meta["emocion"]).upper(), float(meta.get("intensidad", 1.0)) * k)], "contexto (.emocion.json)", palabras
    e, inten = emocion_por_texto(meta.get("texto", ""))
    if e: return [(0.0, dur, e, inten * k)], "texto (palabras clave)", palabras
    e, inten, d = emocion_acustica(caracteristicas(mono, rate))
    return [(0.0, dur, e, inten * k)], "estimacion acustica: " + d, palabras


# ------------------------------------------------------------------------------------------------------------------------------------ emocion: capa de animacion
def capa_emocional(cfg, plan, S, n, lead, fps, base_cejas, base_ojos, escala_pose, elastico=False, dur=None):
    """Devuelve (canales_rig, canales_ojos): canales_rig = {(ruta_datos, indice, grupo): serie}, canales_ojos = {objeto: {(ruta_datos, 0, grupo): serie}}. Todo ADITIVO.
    Los pesos de cada emocion en el tiempo salen del plan (suavizados), asi una frase puede pasar de enojo a tristeza sin saltos."""
    import numpy as np
    D2R = math.pi / 180.0; t = np.arange(n) / float(fps); ph = S["fases"]; habla = S["habla"]; w = {}
    idx = np.arange(n, dtype=float)

    def pesos(el):
        W = {}
        for (t0, t1, emo, inten) in plan:
            if emo not in PERFILES or emo == "NEUTRO" or inten <= 0: continue
            a = W.setdefault(emo, np.zeros(n))
            if el:                                                                   # entrada y salida (y cruces entre segmentos) con Elastic In-Out: 14 frames, sobreoscila ~10 %, termina EXACTAMENTE en 0
                ultimo = dur is None or t1 >= dur - 0.05; ia = lead + t0 * fps - (10 if t0 <= 0.05 else 7); ib = lead + t1 * fps - (0 if ultimo else 7)
                a += inten * ela_vec((idx - ia) / 14.0) * (1.0 - ela_vec((idx - ib) / 14.0))
            else:
                i0 = max(0, min(n, lead + int(round(t0 * fps)) - 2)); i1 = max(i0, min(n, lead + int(round(t1 * fps)) + 1)); a[i0:i1] = np.maximum(a[i0:i1], inten)
        if not el:
            for emo in W: W[emo] = suavizar(W[emo], 5.0, 7.0)
        if W:
            total = sum(W.values()); esc = np.where(total > 1.6, 1.6 / np.maximum(total, 1e-9), 1.0)
            for emo in W: W[emo] = W[emo] * esc
        return W

    w = pesos(elastico); wc = pesos(False) if elastico else w                        # w: torso, ojos, orejas, cola, cejas (Elastic In-Out si se pide); wc: HUESOS DE LA CABEZA y mandibula, siempre transicion suave (pedido de Kebyn)
    if not w: return {}, {}, w, {}
    zero = np.zeros(n)

    def ganancia(clave, W=None):
        g = np.ones(n)
        for emo, a in (W or w).items(): g = g + a * (PERFILES[emo].get(clave, 1.0) - 1.0)
        return np.clip(g, 0.0, 3.0)

    def suma(clave, W=None):
        s = np.zeros(n)
        for emo, a in (W or w).items(): s = s + a * PERFILES[emo].get(clave, 0.0)
        return s

    def oscila(clave, fase, mod=None, W=None):
        s = np.zeros(n)
        for emo, a in (W or w).items():
            amp, hz = PERFILES[emo].get(clave, (0.0, 0.0))
            if amp: s = s + a * amp * np.sin(2 * math.pi * hz * t + fase) * (1.0 if mod is None else mod)
        return s

    sag = np.zeros(n)
    if "SUENO" in wc:
        per = 3.6; fase = (t / per) % 1.0; saw = np.where(fase < 0.85, fase / 0.85, (1.0 - fase) / 0.15); sag = wc["SUENO"] * PERFILES["SUENO"]["sag"] * suavizar(saw, 1.5, 1.5)
    g_nod, g_giro, g_incl, g_mand = ganancia("nod", wc), ganancia("giro", wc), ganancia("incl", wc), ganancia("mand", wc)
    out = {}

    def acum(ruta, idx, grupo, serie_rad):
        k = (ruta, idx, grupo); out[k] = out.get(k, zero) + serie_rad

    pitch_extra = suma("pitch", wc) + sag + oscila("temblor", ph[5], None, wc)             # cabeza: pesos suaves
    roll_extra = suma("roll", wc) + oscila("balanceo", ph[6], 0.3 + 0.7 * habla, wc) + 0.5 * oscila("temblor", ph[7], None, wc)
    yaw_extra = 0.8 * oscila("temblor", ph[0], None, wc)
    for hueso, share in cfg["cabeza"]:
        r = f'pose.bones["{hueso}"].rotation_euler'
        acum(r, 0, hueso, pitch_extra * share * D2R)                                    # postura y temblor; el cabeceo de la voz va en la capa de voz (multiplicado por g_nod)
        acum(r, 1, hueso, roll_extra * share * D2R)
        acum(r, 2, hueso, yaw_extra * share * D2R)
    lean = suma("lean"); resp = oscila("resp", ph[1])
    for hueso, f in cfg["torso"]:
        acum(f'pose.bones["{hueso}"].rotation_euler', 0, hueso, lean * f * D2R)
    if cfg["resp"]: acum(f'pose.bones["{cfg["resp"][0]}"].rotation_euler', 0, cfg["resp"][0], resp * cfg["resp"][1] * D2R)
    orejas = suma("orejas")
    for hueso, f in cfg["orejas"]: acum(f'pose.bones["{hueso}"].rotation_euler', 0, hueso, orejas * f * D2R)
    bajar = np.zeros(n)
    for emo, a in w.items(): bajar = bajar + a * PERFILES[emo].get("cola", (0.0, 0.0, 0.0))[0]
    for hueso, f_bajar, f_meneo, lag in cfg["cola"]:
        acum(f'pose.bones["{hueso}"].rotation_euler', 0, hueso, bajar * f_bajar * D2R)
        mene = np.zeros(n)
        for emo, a in w.items():
            c = PERFILES[emo].get("cola", (0.0, 0.0, 0.0))
            if c[1]: mene = mene + a * c[1] * np.sin(2 * math.pi * c[2] * t + lag + ph[3])
        acum(f'pose.bones["{hueso}"].rotation_euler', 2, hueso, mene * f_meneo * D2R)
    if cfg["cejas"] and base_cejas:                                                  # cejas de Jerry: de la pose que tengan en el frame de inicio a la pose de la emocion
        for emo, a in w.items():
            pose = CEJAS_POSES.get(PERFILES[emo].get("ceja") or "")
            if not pose: continue
            for hueso in cfg["cejas"]:
                rot, loc = pose[hueso]; b_rot, b_loc = base_cejas[hueso]
                for i in range(3):
                    acum(f'pose.bones["{hueso}"].rotation_euler', i, hueso, a * (rot[i] - b_rot[i]))
                    acum(f'pose.bones["{hueso}"].location', i, hueso, a * (loc[i] - b_loc[i]))
    ojos = {}
    if base_ojos:                                                                      # ojos: cada shape key va hacia el valor de la emocion (el resto hacia 0) respecto al valor que tenia en el frame de inicio
        for obj, base in base_ojos.items():
            serie = {}
            for nombre in cfg["ojos_claves"]:
                s = np.zeros(n)
                for emo, a in w.items(): s = s + a * (PERFILES[emo].get("ojos", {}).get(nombre, 0.0) * escala_pose - base.get(nombre, 0.0))
                serie[(f'key_blocks["{nombre}"].value', 0, nombre)] = s
            ojos[obj] = serie
    return out, ojos, w, {"mand": g_mand, "nod": g_nod, "giro": g_giro, "incl": g_incl}


# ------------------------------------------------------------------------------------------------------------------------------------ propiedades
def _cambio_personaje(self, context):
    try: bpy.ops.voz_sync.refrescar()
    except Exception: pass


class VozClip(PropertyGroup):
    nombre: StringProperty(name="Audio")
    ruta: StringProperty(name="Ruta", subtype='FILE_PATH')
    duracion: FloatProperty(name="Duracion (s)", default=0.0)
    inicio: IntProperty(name="Inicio", default=1, min=-100000, description="Frame de la escena en que empieza este audio")


class VozSyncProps(PropertyGroup):
    carpeta: StringProperty(name="Carpeta de audios", subtype='DIR_PATH', default=CARPETA_AUDIOS, description="Carpeta con una subcarpeta por personaje (alfred, jerry)")
    personaje: EnumProperty(name="Personaje", items=[("JERRY", "Jerry", "Mandibula y cabeza"), ("ALFRED", "Alfred", "Solo cabeza")], description="Quien habla", update=_cambio_personaje)
    rig: PointerProperty(name="Armature", type=bpy.types.Object, poll=lambda self, o: o.type == 'ARMATURE', description="Armature del personaje (vacio = buscarlo automaticamente)")
    clips: CollectionProperty(type=VozClip)
    clip_activo: IntProperty(default=0)
    emocion: EnumProperty(name="Emocion", items=[("AUTO", "Automatica", "Contexto (.emocion.json) > texto > estimacion acustica"), ("NEUTRO", "Neutro", "Solo voz, sin capa emocional"), ("ENOJO", "Enojo", ""),
                                                  ("ALEGRIA", "Alegria", ""), ("TRISTEZA", "Tristeza", ""), ("SUENO", "Sueno / cansancio", ""), ("MIEDO", "Miedo", ""), ("SORPRESA", "Sorpresa", ""), ("DUDA", "Duda", "")], description="Emocion que expresa el audio")
    intensidad_emocion: FloatProperty(name="Intensidad de la emocion", default=1.0, min=0.0, max=2.0, description="Multiplica la emocion (0 = ninguna)")
    ganancia: FloatProperty(name="Ganancia", default=1.0, min=0.1, max=4.0, description="Multiplica la intensidad medida (sube si el audio es muy bajo)")
    umbral: FloatProperty(name="Umbral de silencio", default=0.08, min=0.0, max=0.6, description="Fraccion del volumen pico por debajo de la cual se considera silencio (la boca se cierra y la cabeza descansa)")
    apertura: FloatProperty(name="Apertura de mandibula", default=25.0, min=0.0, max=60.0, description="Grados maximos de apertura de la mandibula de Jerry con el volumen pico")
    intensidad_cabeza: FloatProperty(name="Intensidad de la cabeza", default=1.0, min=0.0, max=3.0, description="Multiplica todos los movimientos de cabeza (0 = solo mandibula)")
    cabeceo: FloatProperty(name="Cabeceo (acentos)", default=1.0, min=0.0, max=3.0)
    giro: FloatProperty(name="Giro", default=1.0, min=0.0, max=3.0)
    inclinacion: FloatProperty(name="Inclinacion", default=1.0, min=0.0, max=3.0)
    suavidad: FloatProperty(name="Suavidad de la cabeza", default=1.0, min=0.3, max=3.0, description="Mas alto = la cabeza reacciona mas lento a la intensidad")
    cola: IntProperty(name="Salida suave (frames)", default=16, min=0, max=120, description="Frames despues del final del audio en que todo vuelve a la animacion original (evita un salto al terminar)")
    suavizar_cabeza: FloatProperty(name="Suavizar cabeza (frames)", default=2.0, min=0.0, max=8.0, description="Filtro pasa-bajos (gaussiano) sobre los huesos de la CABEZA (cuello, craneo, hocico, cejas): quita la vibracion de cuadro a cuadro que viene de la envolvente del audio. La mandibula y las MALLAS DE LOS OJOS no se filtran: ahi va la oscilacion del habla. 0 = sin filtro")
    anticipo: IntProperty(name="Anticipo (frames)", default=6, min=0, max=48, description="Frames antes del inicio del audio en que la emocion (postura, ojos) empieza a entrar")
    semilla: IntProperty(name="Semilla", default=1, min=0, description="Cambia el patron de giros/inclinaciones")
    empujar_accion: BoolProperty(name="Empujar la accion activa al NLA si tapa la voz", default=True, description="Una accion activa del personaje va por encima del NLA y anularia la voz; si anima la cabeza/mandibula/ojos se pasa a una pista NLA (como Push Down) sin cambiar la animacion")
    agregar_audio: BoolProperty(name="Agregar el audio al editor de secuencias", default=True, description="Pone el audio en el VSE en su frame de inicio para oirlo al reproducir")
    ajustar_rango: BoolProperty(name="Ampliar el rango de la escena si hace falta", default=False)
    cara_activa: BoolProperty(name="Animacion facial de la herramienta (Alfred)", default=True, description="Si existe `<audio>.cara.json` (lo crea la herramienta de analisis), anima los ojos de Alfred con la expresion generada por la app estudio_audio_expresion, como capa aditiva")
    python_estudio: StringProperty(name="Python de la herramienta", subtype='FILE_PATH', default=PYTHON_ESTUDIO, description="Python con librosa, torch y transformers (el de la app estudio_audio_expresion)")
    neutro_limpio: BoolProperty(name="Ojos de Alfred: neutro limpio", default=True, description="Las expresiones de los ojos (Feliz, Triste, Cansado...) que no tienen animacion de base se dejan en 0: el neutro es la cara sin expresion, sin muescas ni arcos sobrantes, tambien fuera de la animacion facial")
    auto_analizar: BoolProperty(name="Analizar con Whisper si falta el contexto", default=True, description="Si el audio no tiene `<audio>.emocion.json` (o, siendo Alfred con emocion, `<audio>.cara.json`), ejecuta la herramienta de analisis antes de sincronizar")
    elastico_alfred: BoolProperty(name="Alfred: transiciones Elastic In-Out", default=True, description="Los movimientos de Alfred (torso, entrada y salida de la emocion, cambios de emocion y fases de la animacion facial de los ojos) usan la transicion Elastic In-Out del proyecto. Los huesos de la cabeza (cuello, cabeceos) NO la usan: siempre transicion suave")
    info: StringProperty(name="Info", default="")
    info2: StringProperty(name="Emocion detectada", default="")


# ------------------------------------------------------------------------------------------------------------------------------------ utilidades
def _strips(ed):
    """coleccion de strips del editor de secuencias (`strips` en Blender 4.4+, `sequences` antes)."""
    return ed.strips if hasattr(ed, "strips") else ed.sequences


def carpeta_personaje(props, crear=False):
    base = bpy.path.abspath(props.carpeta or CARPETA_AUDIOS); sub = PERSONAJES[props.personaje]["subcarpeta"]
    if os.path.isdir(base):
        for d in os.listdir(base):                                                  # acepta mayusculas/minusculas distintas (Jerry, jerry...)
            if d.lower() == sub and os.path.isdir(os.path.join(base, d)): return os.path.join(base, d)
    ruta = os.path.join(base, sub)
    if crear:
        try: os.makedirs(ruta, exist_ok=True)
        except OSError: pass
    return ruta


def nombre_seguro(nombre):
    return re.sub(r"[^0-9A-Za-z_\-]+", "_", os.path.splitext(nombre)[0]).strip("_") or "audio"


def buscar_rig(props):
    cfg = PERSONAJES[props.personaje]
    if props.rig and cfg["hueso_clave"] in props.rig.pose.bones: return props.rig
    o = bpy.data.objects.get(cfg["rig_por_defecto"])
    if o and o.type == 'ARMATURE' and cfg["hueso_clave"] in o.pose.bones: return o
    for o in bpy.data.objects:
        if o.type == 'ARMATURE' and cfg["hueso_clave"] in o.pose.bones: return o
    return None


def claves_ojos(cfg):
    """{objeto: Key (shape keys)} de los ojos del personaje que existen en la escena."""
    out = {}
    for n in cfg["ojos_obj"]:
        o = bpy.data.objects.get(n)
        if o and o.type == 'MESH' and o.data.shape_keys: out[n] = o.data.shape_keys
    return out


def clip_activo(props):
    return props.clips[props.clip_activo] if 0 <= props.clip_activo < len(props.clips) else None


def analizar(props, scene, ruta):
    mono, rate = cargar_audio(ruta); fps = scene.render.fps / scene.render.fps_base
    rms = rms_por_frame(mono, rate, fps); x = normalizar(rms, props.umbral, props.ganancia)
    return mono, rate, fps, rms, x


def nombre_pista(personaje, clip):
    return f"{PREFIJO_PISTA}{personaje}_{nombre_seguro(clip.nombre)}"


def duenos_anim(p, rig):
    """[(idblock, AnimData)] donde viven las pistas de este personaje: el rig y las shape keys de sus ojos."""
    cfg = PERSONAJES[p.personaje]; res = []
    if rig and rig.animation_data: res.append((rig, rig.animation_data))
    for k in claves_ojos(cfg).values():
        if k.animation_data: res.append((k, k.animation_data))
    for n in cfg["ojos_obj"]:
        o = bpy.data.objects.get(n)
        if o and o.animation_data: res.append((o, o.animation_data))
    return res


def _fijar(idblock, ruta, idx, v):
    """escribe v en la propiedad `ruta`[idx] del idblock (sin lanzar si no existe)."""
    try:
        if "." in ruta: base, prop = ruta.rsplit(".", 1); tgt = idblock.path_resolve(base)
        else: tgt, prop = idblock, ruta
        cur = getattr(tgt, prop)
        if hasattr(cur, "__len__"): cur[idx] = v
        else: setattr(tgt, prop, v)
    except Exception: pass


def _leer(idblock, ruta, idx):
    try:
        if "." in ruta: base, prop = ruta.rsplit(".", 1); tgt = idblock.path_resolve(base)
        else: tgt, prop = idblock, ruta
        cur = getattr(tgt, prop)
        return float(cur[idx]) if hasattr(cur, "__len__") else float(cur)
    except Exception:
        return None


def nombre_base(nombre):
    return nombre.replace(PREFIJO_PISTA, "VozBase_", 1)


def quitar_pista(p, rig, nombre, prefijo=False):
    """quita la pista NLA `nombre` (o todas las que empiecen por `nombre` si `prefijo`) del rig y de los ojos, con sus acciones; las pistas `VozBase_*` (valores estaticos que sostenian los
    canales sin animacion de base) se quitan devolviendo a la propiedad su valor original."""
    n = 0; base = nombre_base(nombre)
    for idb, ad in duenos_anim(p, rig):
        resto = [t_ for t_ in ad.nla_tracks if t_.name.startswith(PREFIJO_PISTA) and not (t_.name == nombre or (prefijo and t_.name.startswith(nombre)))]          # otras voces que siguen en pie
        for tr in list(ad.nla_tracks):
            es_base = tr.name == base or (prefijo and tr.name.startswith(base))
            if es_base and resto: continue                                                                  # el valor sostenido lo siguen usando las demas voces
            if tr.name == nombre or es_base or (prefijo and tr.name.startswith(nombre)):
                for st in list(tr.strips):
                    a = st.action
                    if es_base and a:
                        try:
                            from bpy_extras import anim_utils
                            cb = anim_utils.action_get_channelbag_for_slot(a, st.action_slot)
                            for fc in cb.fcurves: _fijar(idb, fc.data_path, fc.array_index, fc.keyframe_points[0].co[1])
                        except Exception: pass
                    tr.strips.remove(st)
                    if a and a.users == 0: bpy.data.actions.remove(a)
                ad.nla_tracks.remove(tr); n += 1
        if not any(t_.name.startswith(PREFIJO_PISTA) for t_ in ad.nla_tracks):                              # ya no queda ninguna voz: se sueltan tambien los valores sostenidos que sobraron
            for tr in list(ad.nla_tracks):
                if not tr.name.startswith("VozBase_"): continue
                for st in list(tr.strips):
                    a = st.action
                    try:
                        from bpy_extras import anim_utils
                        for fc in anim_utils.action_get_channelbag_for_slot(a, st.action_slot).fcurves: _fijar(idb, fc.data_path, fc.array_index, fc.keyframe_points[0].co[1])
                    except Exception: pass
                    tr.strips.remove(st)
                    if a and a.users == 0: bpy.data.actions.remove(a)
                ad.nla_tracks.remove(tr); n += 1
    return n


def con_base(ad):
    """{(ruta, indice)} de los canales que ya anima la accion activa o alguna pista NLA que NO sea de voz (la base sobre la que se suma la capa)."""
    from bpy_extras import anim_utils
    cs = set(); acts = [(ad.action, getattr(ad, "action_slot", None))] if ad.action else []
    for tr in ad.nla_tracks:
        if tr.name.startswith(PREFIJO_PISTA) or tr.name.startswith("VozBase_"): continue
        for st in tr.strips: acts.append((st.action, getattr(st, "action_slot", None)))
    for a, sl in acts:
        try:
            for fc in anim_utils.action_get_channelbag_for_slot(a, sl).fcurves: cs.add((fc.data_path, fc.array_index))
        except Exception: pass
    return cs


def canales_sostenidos(ad):
    """{(ruta, indice)} que ya sostiene alguna pista VozBase_ de `ad`."""
    from bpy_extras import anim_utils
    cs = set()
    for tr in ad.nla_tracks:
        if not tr.name.startswith("VozBase_"): continue
        for st in tr.strips:
            try:
                for fc in anim_utils.action_get_channelbag_for_slot(st.action, st.action_slot).fcurves: cs.add((fc.data_path, fc.array_index))
            except Exception: pass
    return cs


def sostener_estaticos(nombre, idb, id_type, ad, canales, frame):
    """para los canales de `canales` que NO tienen animacion de base, crea una pista REPLACE (HOLD) con su valor estatico actual: el NLA suma las capas aditivas sobre el valor por defecto (0), no sobre el
    valor fijo de la propiedad, y sin esto el canal cambiaria tambien fuera del audio."""
    ya = canales_sostenidos(ad); base_ = con_base(ad); faltan = {k for k in canales if (k[0], k[1]) not in base_ and (k[0], k[1]) not in ya}; vals = {}          # los ya sostenidos por la pista de otro audio no se repiten
    for (ruta, idx, grupo) in faltan:
        v = _leer(idb, ruta, idx)
        if v is not None: vals[(ruta, idx, grupo)] = v
    if not vals: return 0
    act = bpy.data.actions.new(nombre); slot = act.slots.new(id_type=id_type, name=idb.name)
    layer = act.layers.new("Base"); strip = layer.strips.new(type='KEYFRAME'); cb = strip.channelbag(slot, ensure=True)
    for (ruta, idx, grupo), v in vals.items():
        fc = cb.fcurves.new(ruta, index=idx, group_name=grupo); fc.keyframe_points.add(1); fc.keyframe_points.foreach_set("co", [0.0, float(v)]); fc.update()
    pistas = list(ad.nla_tracks); i_sync = next((i for i, t_ in enumerate(pistas) if t_.name.startswith(PREFIJO_PISTA)), None)
    tr = ad.nla_tracks.new(prev=pistas[i_sync - 1]) if (i_sync is not None and i_sync > 0) else ad.nla_tracks.new()                  # DEBAJO de todas las capas de voz: si no, la pista REPLACE (HOLD) de un audio posterior tapa la capa aditiva de los anteriores
    tr.name = nombre; st = tr.strips.new(act.name, int(frame), act)
    try: st.action_slot = slot
    except Exception: pass
    st.blend_type = 'REPLACE'; st.extrapolation = 'HOLD'
    return len(vals)


def quitar_audio_vse(scene, nombre, prefijo=False):
    if scene.sequence_editor:
        col = _strips(scene.sequence_editor)
        for s in [s for s in col if s.name == nombre or s.name.startswith(nombre + ".") or (prefijo and s.name.startswith(nombre))]: col.remove(s)


def accion_activa_toca(ad, rutas):
    """True si la accion ACTIVA anima alguna de las `rutas` de datos (una accion activa va por encima del NLA y taparia la voz)."""
    act = ad.action
    if act is None: return False
    try:
        from bpy_extras import anim_utils
        cb = anim_utils.action_get_channelbag_for_slot(act, ad.action_slot)
        return any(fc.data_path in rutas for fc in cb.fcurves)
    except Exception:
        return True


def empujar_accion(ad):
    """equivale a "Push Down": la accion activa pasa a una pista NLA (REPLACE, mantiene la pose fuera de su rango) y la capa de voz se suma encima."""
    act = ad.action; slot = getattr(ad, "action_slot", None)
    tr = ad.nla_tracks.new(); tr.name = "Base_" + act.name
    st = tr.strips.new(act.name, int(act.frame_range[0]), act)
    try:
        if slot is not None: st.action_slot = slot
    except Exception: pass
    st.blend_type = 'REPLACE'; st.extrapolation = 'HOLD'; ad.action = None


def crear_accion(nombre, idblock, id_type, canales):
    """accion con una keyframe LINEAL por frame para cada (ruta_de_datos, indice, grupo) de `canales` = {...: [(frame, valor), ...]}."""
    act = bpy.data.actions.new(nombre); slot = act.slots.new(id_type=id_type, name=idblock.name)
    layer = act.layers.new("Voz"); strip = layer.strips.new(type='KEYFRAME'); cb = strip.channelbag(slot, ensure=True)
    for (ruta, idx, grupo), pts in canales.items():
        fc = cb.fcurves.new(ruta, index=idx, group_name=grupo)
        fc.keyframe_points.add(len(pts)); flat = []
        for f, v in pts: flat += [float(f), float(v)]
        fc.keyframe_points.foreach_set("co", flat)
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
        fc.update()
    return act, slot


def pista_aditiva(ad, nombre, act, slot, inicio):
    tr = ad.nla_tracks.new(); tr.name = nombre; st = tr.strips.new(act.name, inicio, act)
    try: st.action_slot = slot
    except Exception: pass
    st.blend_type = 'ADD'; st.extrapolation = 'NOTHING'; st.influence = 1.0; st.use_animated_influence = False
    return tr


def leer_cara(ruta):
    """`<audio>.cara.json` (lo crea herramientas/analizar_audio.py con la geometria de ojos de la app estudio_audio_expresion) o None."""
    try:
        with open(os.path.splitext(bpy.path.abspath(ruta))[0] + ".cara.json", encoding="utf-8") as f: return json.load(f)
    except Exception:
        return None


def filtro_gauss(serie, sigma):
    """filtro gaussiano de `sigma` frames (bordes repetidos): quita la vibracion de cuadro a cuadro y deja los movimientos lentos."""
    import numpy as np
    a = np.asarray(serie, dtype=float)
    if sigma <= 0.0 or a.ndim != 1 or len(a) < 3: return a
    r = max(1, int(round(3 * sigma))); k = np.exp(-0.5 * (np.arange(-r, r + 1) / float(sigma)) ** 2); k /= k.sum()
    return np.convolve(np.pad(a, (r, r), mode="edge"), k, mode="valid")


def pchip(xs, ys, n):
    """interpolacion cubica monotona (sin sobreimpulsos) de los puntos (xs, ys) evaluada en 0..n-1; fuera de los puntos mantiene el primer / ultimo valor."""
    import numpy as np
    ux, uy = [], []
    for x_, y_ in zip(xs, ys):
        if ux and x_ <= ux[-1]: uy[-1] = y_ if x_ == ux[-1] else uy[-1]; continue
        ux.append(float(x_)); uy.append(float(y_))
    t = np.arange(n, dtype=float); out = np.full(n, uy[0]); m = len(ux)
    if m == 1: return out
    h = np.diff(ux); d = np.diff(uy) / h; sl = np.zeros(m)
    for k in range(1, m - 1):
        if d[k - 1] * d[k] > 0:
            w1 = 2 * h[k] + h[k - 1]; w2 = h[k] + 2 * h[k - 1]; sl[k] = (w1 + w2) / (w1 / d[k - 1] + w2 / d[k])
    out[t >= ux[-1]] = uy[-1]
    for k in range(m - 1):
        sel = (t >= ux[k]) & (t < ux[k + 1])
        if not sel.any(): continue
        u = (t[sel] - ux[k]) / h[k]; h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
        out[sel] = h00 * uy[k] + h10 * h[k] * sl[k] + h01 * uy[k + 1] + h11 * h[k] * sl[k + 1]
    return out


def crear_clave_cara(obj, nombre, coords):
    """shape key `nombre` del ojo con la geometria generada (absoluta, igual que `Audio_procedural` de la app). False si la topologia no coincide."""
    me = obj.data
    if len(me.vertices) != len(coords): return False
    if not me.shape_keys: obj.shape_key_add(name="Basis", from_mix=False)
    viejo = me.shape_keys.key_blocks.get(nombre)
    if viejo: obj.shape_key_remove(viejo)
    kb = obj.shape_key_add(name=nombre, from_mix=False); kb.slider_min = -2.0; kb.slider_max = 2.0
    kb.data.foreach_set("co", [c for v in coords for c in v]); kb.value = 0.0
    return True


def quitar_claves_cara(p, nombre=None):
    """quita las shape keys `Voz_*` de los ojos (la de `nombre`, o todas si nombre es None)."""
    cfg = PERSONAJES[p.personaje]; n = 0
    for on in cfg["ojos_obj"]:
        o = bpy.data.objects.get(on)
        if o and o.type == 'MESH' and o.data.shape_keys:
            for kb in list(o.data.shape_keys.key_blocks):
                if kb.name.startswith("Voz_") and (nombre is None or kb.name == nombre): o.shape_key_remove(kb); n += 1
    return n


def capa_cara(cara, nombre_clave, n, lead, n_audio, base_ojos, base_tf, claves_expr, elastico=False):
    """animacion facial de la app estudio_audio_expresion (mismas fases, pesos, retardo entre ojos y parametros que su `animacion_alfred.py`) como capas ADITIVAS:
    valor de la shape key generada, las demas expresiones hacia 0 mientras dura, y desplazamiento / escala / giro de cada ojo. Devuelve ({ojo: canales de la Key}, {ojo: canales del objeto})."""
    import numpy as np
    par = cara["parametros"]; fases = cara["fases"]; END = max(2, n_audio); ojos_key = {}; ojos_obj = {}
    for idx, obj in enumerate(cara["coordenadas"]):
        delay = idx * max(1, int(END * 0.025)); amt = 1.0 if idx == 0 else 0.86; xs = []; w_ = []; ph_ = []; usados = set()
        for ph, w in fases:
            fr = min(END, max(1, 1 + int(round((END - 1) * ph)) + (delay if 0.15 < ph < 0.86 else 0)))
            if fr in usados and fr != END: fr = min(END, fr + 1)
            usados.add(fr); xs.append(lead + fr - 1); w_.append(w); ph_.append(ph)
        w_ = np.array(w_); bt = base_tf[obj]; side = 1.0 if bt["loc"][0] > 0 else -1.0       # lado por la posicion LOCAL del ojo (la app lo calcula con el mundo, en su escena esta en el origen)
        curva = (lambda vals: ela_entre(xs, vals, n)) if elastico else (lambda vals: pchip(xs, vals, n))      # Elastic In-Out entre fases (Alfred) o cubica suave (como la app)
        kd = {(f'key_blocks["{nombre_clave}"].value', 0, nombre_clave): curva(par["shape_value"] * w_ * amt)}
        cero = np.clip(curva(np.clip(w_, 0.0, 1.0)), 0.0, 1.0)
        for nm in claves_expr: kd[(f'key_blocks["{nm}"].value', 0, nm)] = -base_ojos.get(obj, {}).get(nm, 0.0) * cero
        if cara.get("parpadeos"):                                                                      # parpadeo del script de la app (BLINK_CENTERS: 0 -> 1 -> 0 en centro -2 / centro / centro +2), en el ojo Closed
            parp = np.zeros(n)
            for c_, v_ in cara["parpadeos"]:
                for df_, k_ in ((-1, 0.5), (0, 1.0), (1, 0.5)):
                    i_ = lead + int(c_) + df_ - 1
                    if 0 <= i_ < n: parp[i_] = max(parp[i_], float(v_) * k_)
            kd[('key_blocks["Closed"].value', 0, "Closed")] = parp
        ojos_key[obj] = kd
        vert = curva(par["vertical"] * w_ * np.array([1.0 if q < 0.60 else 0.65 for q in ph_])); rot = curva(side * par["rotation"] * w_ * (1.0 if idx == 0 else -0.72))
        fx = 1.0 + curva((par["scale_x"] - 1.0) * w_ * amt); fz = 1.0 + curva((par["scale_z"] - 1.0) * w_ * amt); fy = np.ones(n); hb = cara.get("habla")
        if hb:                                                                                         # OSCILACION DEL HABLA del script de la app (pulso vertical, squash / stretch y giro de ataque): va en las MALLAS DE LOS OJOS, no en la cabeza
            spv = np.zeros(n)
            for k_, lv in hb["curva"]:
                i_ = lead + int(k_) - 1
                if 0 <= i_ < n: spv[i_] = float(lv)
            ks_ = np.arange(n, dtype=float) - lead + 1.0; ata = np.maximum(0.0, spv - np.concatenate(([0.0], spv[:-1]))); onda = np.sin(ks_ * 1.34 + idx * 0.16); estira = onda * spv
            vert = vert + hb["vertical"] * spv * onda * amt
            fx = fx * (1.0 + hb["scale_x"] * spv - 0.040 * estira); fz = fz * (1.0 + hb["scale_z"] * spv + 0.065 * estira + 0.025 * ata); fy = fy * (1.0 - 0.025 * spv)
            rot = rot + side * hb["attack_rotation"] * ata * amt
        ojos_obj[obj] = {("location", 0, "Transform"): curva(side * par["lateral"] * w_ * (1.0 if idx == 0 else -0.55)), ("location", 2, "Transform"): vert,
                         ("scale", 0, "Transform"): bt["scale"][0] * (fx - 1.0), ("scale", 2, "Transform"): bt["scale"][2] * (fz - 1.0), ("rotation_euler", 1, "Transform"): rot}
        if hb: ojos_obj[obj][("scale", 1, "Transform")] = bt["scale"][1] * (fy - 1.0)
    return ojos_key, ojos_obj


def ejecutar_herramienta(p, clip, emocion=None):
    """ejecuta herramientas/analizar_audio.py con el Python de la app estudio_audio_expresion. Devuelve (ok, lineas_o_error)."""
    import subprocess
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "herramientas", "analizar_audio.py"); py = bpy.path.abspath(p.python_estudio)
    if not os.path.isfile(py) or not os.path.isfile(script): return False, f"Falta el Python de la herramienta o el script ({py})"
    cmd = [py, script, bpy.path.abspath(clip.ruta)] + (["--emocion", emocion] if emocion and emocion != "AUTO" else [])
    try: r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as e: return False, f"No se pudo ejecutar la herramienta: {e}"
    lineas = [l for l in r.stdout.splitlines() if l.startswith(("emocion:", "cara:"))]
    if r.returncode or not lineas: return False, "La herramienta fallo: " + (r.stderr.strip().splitlines() or ["sin salida"])[-1]
    return True, " || ".join(lineas)


def limpiar_neutro(cfg, ks):
    """pone en 0 las expresiones de los ojos (no `Closed`, que es el parpadeo) que NINGUNA animacion de base controla: asi el neutro es la cara sin expresion. Devuelve cuantas cambio."""
    n = 0
    for obj, key in ks.items():
        base = con_base(key.animation_data) if key.animation_data else set()
        for nm in cfg["ojos_claves"]:
            if nm == "Closed" or nm not in key.key_blocks or (f'key_blocks["{nm}"].value', 0) in base: continue
            if abs(key.key_blocks[nm].value) > 1e-6: key.key_blocks[nm].value = 0.0; n += 1
    return n


def asegurar_ojos_jerry(cara):
    """crea en las mallas de los ojos de Jerry las shape keys de expresion (Feliz, Triste, Enojado, Sospecha, Cerrado, Cansado, Sorpresa, Closed) con el MISMO codigo del add-on Jerry Animation Studio
    (`eye_system.build_expression_shape_keys`: subdivide la malla y crea las claves) y con las intensidades del script de la app; si ya existen no hace nada. Devuelve cuantos ojos creo."""
    import importlib
    import sys
    ruta = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\jerry\refinar"
    if ruta not in sys.path: sys.path.insert(0, ruta)
    es = importlib.import_module("jerry_animation_studio.eye_system")

    class Ajustes:
        subdivide_cuts = 3; curve_mode = "QUADRATIC"; affect_zone = "UPPER"; swap_axes = False; invert_vertical = False; invert_horizontal = False
    for k_, v_ in cara.get("Settings", {}).items(): setattr(Ajustes, k_, v_)
    vl = bpy.context.view_layer; activo = vl.objects.active; sel0 = [o for o in vl.objects if o.select_get()]; n = 0
    try:
        for nombre in ("ojo_izquierdo_jerry", "ojo_derecho_jerry"):
            ob = bpy.data.objects.get(nombre)
            if ob and ob.type == 'MESH' and not (ob.data.shape_keys and "Sospecha" in ob.data.shape_keys.key_blocks):
                es.build_expression_shape_keys(ob, Ajustes()); n += 1
    finally:
        for o in vl.objects: o.select_set(False)
        for o in sel0: o.select_set(True)
        vl.objects.active = activo
    return n


def capa_cara_jerry(cara, n, lead, base_tf):
    """animacion facial de Jerry de la app (`animacion_jerry.py`: mandibula, hocico, cabeza, cejas, ojos, pupilas y parpadeo) como capas ADITIVAS. El frame k del script cae en el indice lead + k - 1.
    Devuelve (canales del rig, {ojo: canales de la Key}, {ojo: canales del objeto})."""
    import numpy as np
    D2R = math.pi / 180.0; END = int(cara["END_FRAME"]); fases = cara["phase_data"]; comp = cara["COMPONENTS"]; amp = float(cara["AMPLITUDE"]); emo = str(cara["GENERATED_EMOTION"]).lower()
    sp = np.zeros(n)
    for k_, lv in cara["SPEECH_CURVE"]:
        i = lead + int(k_) - 1
        if 0 <= i < n: sp[i] = float(lv)
    ks = np.arange(n, dtype=float) - lead + 1.0                                        # frame del script en cada indice (<= 0 antes del audio)
    ataque = np.maximum(0.0, sp - np.concatenate(([0.0], sp[:-1]))); rig = {}

    def r(h, idx, serie): rig[(f'pose.bones["{h}"].rotation_euler', idx, h)] = serie

    def loc(h, idx, serie): rig[(f'pose.bones["{h}"].location', idx, h)] = serie
    r("jaw_bot", 0, -25.0 * D2R * np.clip(sp, 0.0, 1.0)); r("jaw_bot", 2, 0.45 * D2R * sp * np.sin(ks * 0.73))                                # mandibula: 0 a -25 grados segun la envolvente de la app
    r("jaw_top", 0, -3.0 * D2R * sp); r("jaw_top", 1, 1.0 * D2R * ataque); r("jaw_top", 2, 0.45 * D2R * sp * np.sin(ks * 0.61))                  # hocico superior (nariz)
    for b, seguir in (("scull", 1.0), ("scull_1", 0.55)):
        r(b, 0, 1.15 * D2R * sp * seguir); r(b, 1, 0.55 * D2R * sp * np.sin(ks * 0.19) * seguir)                                            # seguimiento organico de la cabeza
    pos = (ks - 1.0) / max(1, END - 1); w = np.interp(pos, [q[0] for q in fases], [q[1] for q in fases], left=0.0, right=0.0)
    mix = np.clip(w * float(cara.get("BROW_POSE_STRENGTH", 1.0)), 0.0, 1.0)
    for bi, b in enumerate(("sejas_1_jerry", "sejas_2_jerry")):                                                                          # cejas: de la base a la pose (la base de la app -> la pose actual de la escena)
        base = cara["BROW_BASE"][b]; pose = cara["BROW_POSE"][b]; lado = 1.0 if bi == 0 else -1.0; osc = 2.2 * D2R * np.sin(ks * 0.27 + bi * 0.24)
        for a in range(3):
            serie = (pose["euler"][a] - base["euler"][a]) * mix
            if a == 2: serie = serie + lado * osc * np.maximum(w, sp)
            if a == 0: serie = serie + 1.6 * D2R * sp * (1.0 if bi == 0 else 0.86)
            r(b, a, serie); loc(b, a, (pose["loc"][a] - base["loc"][a]) * mix)
    parp = np.zeros(n)
    for f_, v_ in cara.get("parpadeos", []):
        i = lead + int(f_) - 1
        if 0 <= i < n: parp[i] = max(parp[i], float(v_))
    ojos_key = {}; ojos_obj = {}
    for idx, on in enumerate(("ojo_izquierdo_jerry", "ojo_derecho_jerry")):
        delay = idx * max(1, int(END * 0.025)); asim = 1.0 if idx == 0 else 0.88; xs = []; ws = []
        for ph, wt in fases:
            fr = min(END, max(1, 1 + int(round((END - 1) * ph)) + (delay if 0.15 < ph < 0.86 else 0))); xs.append(lead + fr - 1); ws.append(wt)
        ws = np.array(ws); bt = base_tf[on]; curva = lambda vals: pchip(xs, vals, n)
        kd = {(f'key_blocks["{nm}"].value', 0, nm): curva(amp * cw * ws * asim) for nm, cw in comp}
        kd[('key_blocks["Closed"].value', 0, "Closed")] = parp
        ojos_key[on] = kd
        ojos_obj[on] = {("scale", 0, "Transform"): curva(bt["scale"][0] * (float(cara["EYE_SCALE"]) - 1.0) * ws * asim), ("scale", 2, "Transform"): curva(bt["scale"][2] * (float(cara["EYE_SCALE"]) - 1.0) * ws * 0.55),
                        ("location", 2, "Transform"): curva(0.0025 * ws * (1.0 if idx == 0 else 0.72))}
        spl = np.convolve(sp, [0.25, 0.5, 0.25], mode="same"); onda = np.sin(ks * 1.34 + idx * 0.16); estira = onda * spl; ata_ = np.maximum(0.0, spl - np.concatenate(([0.0], spl[:-1])))      # pulso del habla en las MALLAS DE LOS OJOS (como Alfred: vertical + squash / stretch)
        ojos_obj[on][("location", 2, "Transform")] = ojos_obj[on][("location", 2, "Transform")] + 0.0018 * spl * onda * asim
        ojos_obj[on][("scale", 0, "Transform")] = ojos_obj[on][("scale", 0, "Transform")] + bt["scale"][0] * (0.06 * spl - 0.025 * estira)
        ojos_obj[on][("scale", 2, "Transform")] = ojos_obj[on][("scale", 2, "Transform")] + bt["scale"][2] * (0.10 * spl + 0.04 * estira + 0.015 * ata_)
        ojos_obj[on][("scale", 1, "Transform")] = bt["scale"][1] * (-0.015 * spl)
    for pi, pn in enumerate(("pupila_izquierda_jerry", "pupila_derecha_jerry")):
        xs = [lead + min(END, max(1, 1 + int(round((END - 1) * ph)))) - 1 for ph, _ in fases]; ws = np.array([q[1] for q in fases]); lado = 1.0 if pi == 0 else -1.0; sentido = -1.0 if emo == "enojo" else 1.0
        d = float(cara["PUPIL_SHIFT"])
        ojos_obj[pn] = {("location", 0, "Transform"): pchip(xs, lado * d * ws * sentido, n), ("location", 2, "Transform"): pchip(xs, d * 0.25 * ws, n)}
        ojos_key[pn] = {('key_blocks["Closed"].value', 0, "Closed"): parp}
    return rig, ojos_key, ojos_obj


def sincronizar_clip(context, clip):
    """crea (o reemplaza) las pistas NLA de voz + emocion de `clip`. Devuelve (ok, mensaje)."""
    import numpy as np
    sc = context.scene; p = sc.voz_sync; cfg = PERSONAJES[p.personaje]
    if not os.path.isfile(bpy.path.abspath(clip.ruta)): return False, f"No existe el archivo {clip.ruta}"
    rig = buscar_rig(p)
    if rig is None: return False, f"No encuentro la armature de {cfg['etiqueta']} (hueso {cfg['hueso_clave']})"
    faltan = [h for h, _ in cfg["cabeza"] if h not in rig.pose.bones] + ([cfg["mandibula"]] if cfg["mandibula"] and cfg["mandibula"] not in rig.pose.bones else [])
    if faltan: return False, f"Faltan huesos en {rig.name}: {faltan}"
    aviso = ""
    if p.auto_analizar:
        meta0 = leer_meta(clip.ruta); falta = not meta0 or (p.personaje == "ALFRED" and meta0.get("emocion", "NEUTRO") != "NEUTRO" and leer_cara(clip.ruta) is None and p.cara_activa)
        if falta:
            ok_h, msg_h = ejecutar_herramienta(p, clip, p.emocion)
            aviso = " | analisis automatico: " + msg_h.split(" || ")[0][:80] if ok_h else " | NO se pudo analizar (" + msg_h[:80] + ")"
    try: mono, rate, fps, rms, x = analizar(p, sc, clip.ruta)
    except Exception as e: return False, f"No se pudo leer el audio: {e}"
    elastico = bool(p.elastico_alfred and p.personaje == "ALFRED")
    n_audio = len(x); dur = n_audio / fps; lead = max(int(p.anticipo), 10) if elastico else int(p.anticipo); tail = max(int(p.cola), 16) if elastico else int(p.cola); n = lead + n_audio + tail
    plan, fuente, palabras = resolver_emocion(p, clip, mono, rate, dur)
    x = np.concatenate([np.zeros(lead), x, np.zeros(tail)])
    S = senales(x, fps, p.semilla, p, palabras, lead, False); D2R = math.pi / 180.0; f0 = clip.inicio; fs = f0 - lead; k = p.intensidad_cabeza   # fs = frame de inicio del strip
    t_ = np.clip((np.arange(n) - (lead + n_audio - 1)) / float(max(1, tail)), 0.0, 1.0); fade = 1.0 - t_ * t_ * (3.0 - 2.0 * t_)          # todo vuelve a la animacion original tras el audio
    # estado de partida (cejas y ojos en el frame de inicio, SIN nuestras pistas) para que la capa emocional lleve de lo que hay a la emocion
    nombre = nombre_pista(p.personaje, clip); quitar_pista(p, rig, nombre); nombre_clave = ("Voz_" + nombre_seguro(clip.nombre))[:56]; quitar_claves_cara(p, nombre_clave)
    cara_all = leer_cara(clip.ruta) if p.cara_activa else None
    cara = cara_all if (p.personaje == "ALFRED" and cara_all and cara_all.get("tipo", "alfred") != "jerry") else None
    cara_j = cara_all if (p.personaje == "JERRY" and cara_all and cara_all.get("tipo") == "jerry") else None
    creados_j = asegurar_ojos_jerry(cara_j) if cara_j else 0
    frame0 = sc.frame_current; sc.frame_set(f0); base_cejas = None; base_ojos = {}; base_tf = {}
    if cfg["cejas"] and not cara_j and all(h in rig.pose.bones for h in cfg["cejas"]):
        base_cejas = {h: (tuple(rig.pose.bones[h].rotation_euler), tuple(rig.pose.bones[h].location)) for h in cfg["cejas"]}
    ks = claves_ojos(cfg)
    limpiados = limpiar_neutro(cfg, ks) if (p.neutro_limpio and p.personaje == "ALFRED") else 0
    for obj, key in ks.items(): base_ojos[obj] = {nm: key.key_blocks[nm].value for nm in cfg["ojos_claves"] if nm in key.key_blocks}
    if cara_j:
        for on in cfg["ojos_obj"]:
            ob = bpy.data.objects.get(on)
            if ob: base_tf[on] = {"loc": tuple(ob.location), "scale": tuple(ob.scale)}
    ok_cara = False
    if cara:
        ok_cara = all(o in ks and crear_clave_cara(bpy.data.objects[o], nombre_clave, cara["coordenadas"][o]) for o in cara["coordenadas"])
        for o in cara["coordenadas"]:
            ob = bpy.data.objects.get(o)
            if ob: base_tf[o] = {"loc": tuple(ob.location), "scale": tuple(ob.scale)}
        if not ok_cara: quitar_claves_cara(p, nombre_clave)
    sc.frame_set(frame0)
    capa, ojos, w, gan = capa_emocional(cfg, plan, S, n, lead, fps, base_cejas, None if ok_cara else base_ojos, 1.0, elastico, dur)
    ojos_obj = {}
    cj_rig = {}
    if cara_j:
        cj_rig, ojos, ojos_obj = capa_cara_jerry(cara_j, n, lead, base_tf)
    if ok_cara: ojos, ojos_obj = capa_cara(cara, nombre_clave, n, lead, n_audio, base_ojos, base_tf, [k_ for k_ in cfg["ojos_claves"] if k_ != "Closed"], elastico)
    g = gan if gan else {"mand": 1.0, "nod": 1.0, "giro": 1.0, "incl": 1.0}
    canales = {}
    def suma(ruta, idx, grupo, serie):
        canales[(ruta, idx, grupo)] = canales.get((ruta, idx, grupo), 0.0) + serie
    for hueso, share in cfg["cabeza"]:
        r = f'pose.bones["{hueso}"].rotation_euler'
        suma(r, 0, hueso, S["cabeceo"] * g["nod"] * cfg["pitch"] * p.cabeceo * k * share * D2R)
        suma(r, 1, hueso, S["inclinacion"] * g["incl"] * cfg["roll"] * p.inclinacion * k * share * D2R)
        suma(r, 2, hueso, S["giro"] * g["giro"] * cfg["yaw"] * p.giro * k * share * D2R)
    if cfg["mandibula"] and not cara_j: suma(f'pose.bones["{cfg["mandibula"]}"].rotation_euler', 0, cfg["mandibula"], -np.clip(S["mandibula"] * g["mand"], 0.0, 1.3) * p.apertura * D2R)       # X negativa = abrir (comprobado en el rig de Jerry)
    for clave, serie in capa.items(): suma(clave[0], clave[1], clave[2], serie)
    for clave, serie in cj_rig.items(): suma(clave[0], clave[1], clave[2], serie)                          # cara de Jerry de la app (mandibula, hocico, cabeza, cejas)
    if p.suavizar_cabeza > 0:                                                                               # la cabeza NO vibra: filtro pasa-bajos en cuello / craneo / hocico / cejas (la mandibula y los ojos conservan la oscilacion del habla)
        suaves = {h for h, _ in cfg["cabeza"]} | ({"jaw_top", "sejas_1_jerry", "sejas_2_jerry"} if cara_j else set())
        for kk in list(canales):
            if kk[2] in suaves and hasattr(canales[kk], "__len__"): canales[kk] = filtro_gauss(canales[kk], p.suavizar_cabeza)
    # desvanecer todo al final y pasar a listas de (frame, valor)
    canales_rig = {kk: [(fs + i, float(v[i] * fade[i] if hasattr(v, "__len__") else 0.0)) for i in range(n)] for kk, v in canales.items()}
    ad = rig.animation_data or rig.animation_data_create(); pushed = []
    rutas_rig = {kk[0] for kk in canales_rig}
    if p.empujar_accion and accion_activa_toca(ad, rutas_rig): pushed.append(ad.action.name); empujar_accion(ad)
    mantenidos = sostener_estaticos(nombre_base(nombre), rig, 'OBJECT', ad, canales_rig, sc.frame_start)
    act, slot = crear_accion(nombre, rig, 'OBJECT', canales_rig); pista_aditiva(ad, nombre, act, slot, fs)
    for obj, serie in ojos.items():
        key = ks[obj]; ada = key.animation_data or key.animation_data_create(); cks = {kk: [(fs + i, float(v[i] * fade[i])) for i in range(n)] for kk, v in serie.items()}
        if p.empujar_accion and accion_activa_toca(ada, {kk[0] for kk in cks}): pushed.append(ada.action.name); empujar_accion(ada)
        mantenidos += sostener_estaticos(nombre_base(nombre), key, 'KEY', ada, cks, sc.frame_start)
        a2, s2 = crear_accion(nombre, key, 'KEY', cks); pista_aditiva(ada, nombre, a2, s2, fs)
    for on, serie in ojos_obj.items():
        ob = bpy.data.objects[on]; ado = ob.animation_data or ob.animation_data_create(); cks = {kk: [(fs + i, float(v[i])) for i in range(n)] for kk, v in serie.items()}
        if p.empujar_accion and accion_activa_toca(ado, {kk[0] for kk in cks}): pushed.append(ado.action.name); empujar_accion(ado)
        mantenidos += sostener_estaticos(nombre_base(nombre), ob, 'OBJECT', ado, cks, sc.frame_start)
        a3, s3 = crear_accion(nombre, ob, 'OBJECT', cks); pista_aditiva(ado, nombre, a3, s3, fs)
    for _idb, ad_ in duenos_anim(p, rig): ad_.use_nla = False; ad_.use_nla = True
    rig.update_tag(); sc.frame_set(sc.frame_current)          # reconstruye las relaciones de animacion (sin esto el NLA a veces no evalua los canales nuevos)
    quitar_audio_vse(sc, nombre)
    extra = ""
    if p.agregar_audio:
        ed = sc.sequence_editor or sc.sequence_editor_create(); canal = 1 + len(_strips(ed))
        try: _strips(ed).new_sound(nombre, bpy.path.abspath(clip.ruta), min(canal, 128), f0)
        except Exception as e: extra += f" (no pude agregar el audio al VSE: {e})"
    if p.ajustar_rango and fs + n - 1 > sc.frame_end: sc.frame_end = fs + n - 1
    emo_txt = ", ".join(f"{e} x{float(a.max()):.2f}" for e, a in w.items()) or "NEUTRO (solo voz)"
    if elastico: emo_txt += " | Elastic In-Out en torso y ojos (NO en los huesos de la cabeza)"
    if cara_j: emo_txt += f" | cara de Jerry de la app ({cara_j.get('fuente', '')}): mandibula, hocico, cabeza, cejas, ojos {[c_[0] for c_ in cara_j['COMPONENTS']]}, pupilas y parpadeo" + (f" ({creados_j} ojos con shape keys nuevas)" if creados_j else "")
    if limpiados: emo_txt += f" | neutro limpio: {limpiados} expresiones sobrantes de los ojos puestas a 0"
    emo_txt += aviso
    if ok_cara: emo_txt += " | cara: " + "+".join(f"{c['expression']} {c['weight']:.2f}" for c in cara.get("componentes", [])) + f" (intensidad {cara.get('intensidad', 0):.2f}, clave {nombre_clave})"
    elif cara: emo_txt += " | cara NO aplicada (la topologia de los ojos no coincide)"
    return True, f"{cfg['etiqueta']}: '{clip.nombre}' {n_audio} frames de audio (f{f0}-f{f0 + n_audio - 1}; capa f{fs}-f{fs + n - 1}) | emocion: {emo_txt} [{fuente}]" + (f" | acciones activas pasadas al NLA: {pushed}" if pushed else "") + (f" | {mantenidos} canales sin base sostenidos" if mantenidos else "") + extra


# ------------------------------------------------------------------------------------------------------------------------------------ operadores
class VOZ_OT_refrescar(Operator):
    bl_idname = "voz_sync.refrescar"; bl_label = "Actualizar lista"; bl_description = "Lee los audios de la subcarpeta del personaje (se crean las carpetas si faltan)"

    def execute(self, context):
        p = context.scene.voz_sync; carpeta = carpeta_personaje(p, crear=True); previos = {c.ruta: c.inicio for c in p.clips}; archivos = []
        for raiz, _dirs, files in os.walk(carpeta):
            for f in files:
                if os.path.splitext(f)[1].lower() in EXTENSIONES: archivos.append(os.path.join(raiz, f))
        p.clips.clear()
        for ruta in sorted(archivos):
            c = p.clips.add(); c.nombre = os.path.relpath(ruta, carpeta).replace("\\", "/"); c.ruta = ruta; c.duracion = duracion_audio(ruta); c.inicio = previos.get(ruta, context.scene.frame_current)
        p.clip_activo = min(p.clip_activo, max(0, len(p.clips) - 1)); p.info = f"{len(p.clips)} audio(s) en {carpeta}"; p.info2 = ""
        return {'FINISHED'}


class VOZ_OT_abrir_carpeta(Operator):
    bl_idname = "voz_sync.abrir_carpeta"; bl_label = "Abrir carpeta"; bl_description = "Abre la carpeta de audios del personaje en el explorador"

    def execute(self, context):
        bpy.ops.wm.path_open(filepath=carpeta_personaje(context.scene.voz_sync, crear=True)); return {'FINISHED'}


class VOZ_OT_analizar(Operator):
    bl_idname = "voz_sync.analizar"; bl_label = "Analizar"; bl_description = "Mide duracion, volumen, frames con voz y la emocion que se aplicaria al audio elegido (no cambia la escena)"

    def execute(self, context):
        p = context.scene.voz_sync; c = clip_activo(p)
        if c is None: self.report({'ERROR'}, "No hay audio elegido: pon archivos en la carpeta del personaje y pulsa Actualizar"); return {'CANCELLED'}
        try: mono, rate, fps, rms, x = analizar(p, context.scene, c.ruta)
        except Exception as e: self.report({'ERROR'}, f"No se pudo leer el audio: {e}"); return {'CANCELLED'}
        voz = int((x > 0.05).sum()); plan, fuente, palabras = resolver_emocion(p, c, mono, rate, len(x) / fps)
        p.info = f"{c.nombre}: {len(mono) / rate:.2f} s = {len(x)} frames a {fps:g} fps | con voz: {voz} frames ({100.0 * voz / max(1, len(x)):.0f} %) | pico RMS {float(rms.max()):.3f}"
        p.info2 = "Emocion: " + "; ".join(f"{e} {i:.2f} ({a:.1f}-{b:.1f}s)" for a, b, e, i in plan) + f" [{fuente}]" + (f" | {len(palabras)} palabras anotadas" if palabras else "")
        self.report({'INFO'}, p.info + " || " + p.info2); return {'FINISHED'}


class VOZ_OT_analizar_whisper(Operator):
    bl_idname = "voz_sync.analizar_whisper"; bl_label = "Analizar con Whisper"
    bl_description = "Ejecuta la herramienta de la app estudio_audio_expresion: transcribe (Whisper Base local, con tiempo por palabra), mide la prosodia, usa tus ejemplos aprobados para decidir la emocion y escribe `<audio>.emocion.json` y `<audio>.cara.json` junto al audio"

    def execute(self, context):
        p = context.scene.voz_sync; c = clip_activo(p)
        if c is None: self.report({'ERROR'}, "No hay audio elegido"); return {'CANCELLED'}
        ok, msg = ejecutar_herramienta(p, c, p.emocion)
        if not ok: self.report({'ERROR'}, msg); return {'CANCELLED'}
        p.info2 = msg; self.report({'INFO'}, msg); return {'FINISHED'}


class VOZ_OT_guardar_emocion(Operator):
    bl_idname = "voz_sync.guardar_emocion"; bl_label = "Guardar contexto"; bl_description = "Escribe/actualiza `<audio>.emocion.json` junto al mp3 con la emocion que se aplicaria (editable: texto, segmentos, palabras)"

    def execute(self, context):
        p = context.scene.voz_sync; c = clip_activo(p)
        if c is None: return {'CANCELLED'}
        try: mono, rate, fps, rms, x = analizar(p, context.scene, c.ruta)
        except Exception as e: self.report({'ERROR'}, f"No se pudo leer el audio: {e}"); return {'CANCELLED'}
        meta = leer_meta(c.ruta); plan, fuente, _pal = resolver_emocion(p, c, mono, rate, len(x) / fps)
        if not meta.get("emocion") and not meta.get("segmentos"):
            meta["emocion"] = plan[0][2] if plan else "NEUTRO"; meta["intensidad"] = round(plan[0][3], 2) if plan else 0.0
        meta.setdefault("texto", ""); meta["_nota"] = "tiempos en segundos desde el inicio del audio; emociones: " + ", ".join(EMOCIONES)
        with open(ruta_meta(c.ruta), "w", encoding="utf-8") as f: json.dump(meta, f, ensure_ascii=False, indent=2)
        self.report({'INFO'}, f"Guardado {ruta_meta(c.ruta)}"); return {'FINISHED'}


class VOZ_OT_aplicar(Operator):
    bl_idname = "voz_sync.aplicar"; bl_label = "Sincronizar"; bl_description = "Crea la animacion de voz y emocion del audio elegido, en pistas NLA aditivas"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        p = context.scene.voz_sync; c = clip_activo(p)
        if c is None: self.report({'ERROR'}, "No hay audio elegido: pon archivos en la carpeta del personaje y pulsa Actualizar"); return {'CANCELLED'}
        ok, msg = sincronizar_clip(context, c); p.info = msg; self.report({'INFO'} if ok else {'ERROR'}, msg); return {'FINISHED'} if ok else {'CANCELLED'}


class VOZ_OT_aplicar_todos(Operator):
    bl_idname = "voz_sync.aplicar_todos"; bl_label = "Sincronizar todos"; bl_description = "Sincroniza todos los audios de la lista, cada uno en su frame de inicio"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        p = context.scene.voz_sync; bien = 0; errores = []
        for c in p.clips:
            ok, msg = sincronizar_clip(context, c)
            if ok: bien += 1
            else: errores.append(msg)
        p.info = f"{bien}/{len(p.clips)} audios sincronizados" + (f" | error: {errores[0]}" if errores else "")
        self.report({'INFO'} if not errores else {'WARNING'}, p.info); return {'FINISHED'}


class VOZ_OT_quitar(Operator):
    bl_idname = "voz_sync.quitar"; bl_label = "Quitar"; bl_description = "Borra las pistas NLA y acciones del audio elegido (y su audio del VSE)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        sc = context.scene; p = sc.voz_sync; c = clip_activo(p); rig = buscar_rig(p)
        if c is None: return {'CANCELLED'}
        nombre = nombre_pista(p.personaje, c); n = quitar_pista(p, rig, nombre); quitar_audio_vse(sc, nombre); quitar_claves_cara(p, ("Voz_" + nombre_seguro(c.nombre))[:56]); p.info = ""
        self.report({'INFO'}, f"Quitadas {n} pista(s)"); return {'FINISHED'}


class VOZ_OT_quitar_todos(Operator):
    bl_idname = "voz_sync.quitar_todos"; bl_label = "Quitar todos"; bl_description = "Borra todas las pistas de voz de este personaje (y sus audios del VSE)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        sc = context.scene; p = sc.voz_sync; rig = buscar_rig(p); pref = f"{PREFIJO_PISTA}{p.personaje}_"
        n = quitar_pista(p, rig, pref, prefijo=True); quitar_audio_vse(sc, pref, prefijo=True); quitar_claves_cara(p); p.info = ""
        self.report({'INFO'}, f"Quitadas {n} pista(s)"); return {'FINISHED'}


class VOZ_UL_clips(UIList):
    bl_idname = "VOZ_UL_clips"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=True); r.label(text=item.nombre, icon='SOUND'); r.label(text=f"{item.duracion:.1f} s"); r.prop(item, "inicio", text="f")


class VOZ_PT_panel(Panel):
    bl_label = "Voz Sync"; bl_idname = "VOZ_PT_panel"; bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = "Voz Sync"

    def draw(self, context):
        l = self.layout; p = context.scene.voz_sync; cfg = PERSONAJES[p.personaje]
        l.prop(p, "personaje", expand=True); l.prop(p, "rig"); l.prop(p, "carpeta")
        r = l.row(align=True); r.operator("voz_sync.refrescar", icon='FILE_REFRESH'); r.operator("voz_sync.abrir_carpeta", icon='FILE_FOLDER')
        l.label(text=f"Audios de {cfg['etiqueta']} ({cfg['subcarpeta']}/):")
        if not p.clips: l.label(text="Sin audios: copia archivos a esa carpeta y pulsa Actualizar", icon='INFO')
        l.template_list("VOZ_UL_clips", "", p, "clips", p, "clip_activo", rows=4)
        r = l.row(align=True); r.operator("voz_sync.analizar", icon='VIEWZOOM'); r.operator("voz_sync.aplicar", icon='PLAY_SOUND'); r.operator("voz_sync.quitar", icon='X')
        r = l.row(align=True); r.operator("voz_sync.aplicar_todos", icon='SEQ_STRIP_DUPLICATE'); r.operator("voz_sync.quitar_todos", icon='TRASH')
        if p.info: l.label(text=p.info, icon='INFO')
        if p.info2: l.label(text=p.info2, icon='LIGHT')
        b = l.box(); b.label(text="Emocion (capa sobre la animacion existente)"); b.prop(p, "emocion"); b.prop(p, "intensidad_emocion"); b.operator("voz_sync.analizar_whisper", icon='OUTLINER_OB_SPEAKER'); b.operator("voz_sync.guardar_emocion", icon='TEXT'); b.prop(p, "anticipo")
        b.prop(p, "auto_analizar")
        if p.personaje == "ALFRED": b.prop(p, "elastico_alfred")
        if p.personaje == "ALFRED": b.prop(p, "cara_activa"); b.prop(p, "neutro_limpio")
        b = l.box(); b.label(text="Intensidad del audio"); b.prop(p, "ganancia"); b.prop(p, "umbral")
        b = l.box(); b.label(text="Movimiento de la voz")
        if cfg["mandibula"]: b.prop(p, "apertura")
        b.prop(p, "intensidad_cabeza"); r = b.row(align=True); r.prop(p, "cabeceo"); r.prop(p, "giro"); r.prop(p, "inclinacion"); b.prop(p, "suavidad"); b.prop(p, "suavizar_cabeza"); b.prop(p, "cola"); b.prop(p, "semilla")
        l.prop(p, "agregar_audio"); l.prop(p, "ajustar_rango"); l.prop(p, "empujar_accion")


CLASES = (VozClip, VozSyncProps, VOZ_OT_refrescar, VOZ_OT_abrir_carpeta, VOZ_OT_analizar, VOZ_OT_analizar_whisper, VOZ_OT_guardar_emocion, VOZ_OT_aplicar, VOZ_OT_aplicar_todos, VOZ_OT_quitar, VOZ_OT_quitar_todos, VOZ_UL_clips, VOZ_PT_panel)


def _llenar_lista():
    """llena la lista de audios del personaje elegido (al activar el add-on y al abrir un .blend)."""
    try:
        sc = bpy.context.scene
        if sc and hasattr(sc, "voz_sync") and not sc.voz_sync.clips: bpy.ops.voz_sync.refrescar()
    except Exception: pass
    return None


def _al_abrir(*_a):
    bpy.app.timers.register(_llenar_lista, first_interval=0.5)


def register():
    for c in CLASES: bpy.utils.register_class(c)
    bpy.types.Scene.voz_sync = PointerProperty(type=VozSyncProps)
    if _al_abrir not in bpy.app.handlers.load_post: bpy.app.handlers.load_post.append(_al_abrir)
    bpy.app.timers.register(_llenar_lista, first_interval=0.5)


def unregister():
    if _al_abrir in bpy.app.handlers.load_post: bpy.app.handlers.load_post.remove(_al_abrir)
    del bpy.types.Scene.voz_sync
    for c in reversed(CLASES): bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
