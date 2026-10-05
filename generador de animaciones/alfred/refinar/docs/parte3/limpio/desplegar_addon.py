# -*- coding: utf-8 -*-
"""Despliega el add-on: respalda lo instalado (y el zip anterior) en refinar/cambios/, copia los .py de la fuente al add-on instalado de Blender 5.2 y reconstruye alfred_animation_studio.zip.
Uso:  python desplegar_addon.py [--sin-respaldo]"""
import os
import shutil
import sys
import time
import zipfile

R = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"
SRC = os.path.join(R, "alfred_animation_studio")
INST = os.path.join(os.environ["APPDATA"], "Blender Foundation", "Blender", "5.2", "scripts", "addons", "alfred_animation_studio")
cam = os.path.join(R, "cambios"); os.makedirs(cam, exist_ok=True); sello = time.strftime("%Y%m%d_%H%M")


def zipdir(carpeta, destino):
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(carpeta)):
            if f.endswith(".py"): z.write(os.path.join(carpeta, f), "alfred_animation_studio/" + f)


def leer(p):
    with open(p, "rb") as f: return f.read()


if "--sin-respaldo" not in sys.argv:
    zipdir(INST, os.path.join(cam, "alfred_animation_studio_instalado_antes_%s.zip" % sello)); shutil.copyfile(os.path.join(R, "alfred_animation_studio.zip"), os.path.join(cam, "alfred_animation_studio_zip_antes_%s.zip" % sello))
os.makedirs(INST, exist_ok=True); n = 0
for f in sorted(os.listdir(SRC)):
    if f.endswith(".py"): shutil.copyfile(os.path.join(SRC, f), os.path.join(INST, f)); n += 1
zipdir(SRC, os.path.join(R, "alfred_animation_studio.zip"))
dif = [f for f in os.listdir(SRC) if f.endswith(".py") and leer(os.path.join(SRC, f)) != leer(os.path.join(INST, f))]
with zipfile.ZipFile(os.path.join(R, "alfred_animation_studio.zip")) as z: nz = len(z.namelist())
print("copiados %d modulos al add-on instalado; zip con %d archivos; difieren fuente/instalado: %s" % (n, nz, dif))
