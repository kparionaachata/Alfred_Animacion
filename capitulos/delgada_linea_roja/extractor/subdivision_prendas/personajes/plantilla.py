"""Plantilla de configuracion de paso4_subdividir.py. Copiala con el nombre del personaje y rellenala con lo que diga paso3_inspeccionar.py.

Ejemplo completo y real: black_watch_soldier.py. Deja vacio lo que no uses. Las rutas de CON_TROZOS y PINTADAS son relativas a la carpeta de salida.
"""


# Corta una malla compartida por varias prendas. Recibe las u, v y z de CADA CARA y devuelve el nombre de su prenda.
def zona_ejemplo(u, v, z):
    return "falda" if max(z) < 1.1 else "camisa"


# prenda: (mallas enteras, (malla a cortar, zona) o None, prefijos de los objetos de detalle 3D)
PRENDAS = {
    "camisa": ((), ("torsos", zona_ejemplo), ("det_torsos_",)),
    "falda": ((), ("torsos", zona_ejemplo), ()),
    "gorro": (("hats",), None, ()),
}


# Reparte las piezas CONECTADAS de una prenda. Recibe los limites de la pieza y devuelve el nombre de su detalle.
def zona_camisa(u0, u1, v0, v1, y1, z1):
    return "mangas" if u0 >= .6 else "cuerpo"


# prenda: {detalle: (malla a cortar, zona) o texto que aparece en el nombre de sus objetos}
DETALLES = {
    "camisa": {"cuerpo": ("camisa", zona_camisa), "mangas": ("camisa", zona_camisa), "botones": "_boton_"},
}

# Archivos cuyas piezas conectadas son limpias (paso6_auditar.py): cada pieza va a su .blend, con lado D (x > 0) o I.
CON_TROZOS = ("falda", "camisa/detalles/mangas")


# Detalles solo pintados en una malla: la malla se corta por el contorno del dibujo.
# Recibe matrices de la textura: x, y en pixeles (fila 0 arriba) y r, g, b, lum entre 0 y 1. Devuelve zonas en orden de prioridad y el nombre de lo que sobra.
def zonas_ejemplo(x, y, r, g, b, lum):
    galon = (y >= 100) & (y <= 120) & (lum > .5)
    return [("galon", galon)], "tela"


PINTADAS = {
    "camisa/detalles/mangas/detalles/mangas_D_01": zonas_ejemplo,
}
