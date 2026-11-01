"""Junta las vista.png de una carpeta en una sola imagen, para revisar los cortes de un vistazo. Se ejecuta con Python normal (Pillow).

python -I hoja_contacto.py carpeta salida.png [texto_que_debe_tener_la_ruta]
"""
import math
import os
import sys

from PIL import Image, ImageDraw

base, salida = sys.argv[1], sys.argv[2]
filtro = sys.argv[3] if len(sys.argv) > 3 else ""
fotos = []
for raiz, dirs, files in os.walk(base):
    dirs.sort()
    if "vista.png" in files and filtro in raiz.replace(os.sep, "/"):
        fotos.append(os.path.join(raiz, "vista.png"))
if not fotos:
    sys.exit("No hay fotos en " + base)
C = min(14, max(6, math.ceil(math.sqrt(len(fotos)))))
W, H = 1800 // C, 1400 // C
hoja = Image.new("RGB", (W * C, H * math.ceil(len(fotos) / C)))
for i, p in enumerate(fotos):
    im = Image.open(p).convert("RGB").resize((W, H))
    ImageDraw.Draw(im).text((3, 3), os.path.basename(os.path.dirname(p)), fill=(255, 255, 0))
    hoja.paste(im, ((i % C) * W, (i // C) * H))
hoja.save(salida)
print(len(fotos), "fotos en", salida)
