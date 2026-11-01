#!/bin/bash
# Ejecuta los pasos 4, 5 y 6 y deja la hoja de fotos. La configuracion del personaje ya debe existir (ver LEEME.md).
#   bash flujo.sh personaje.blend personajes/config.py [carpeta_salida] [etapas]
set -e
AQUI="$(cd "$(dirname "$0")" && pwd)"
BLEND="$1"; CONFIG="$2"
SALIDA="${3:-$(dirname "$BLEND")/prendas}"
ETAPAS="${4:-prendas,detalles,piezas,trozos,pintadas}"
# los archivos estan guardados con la 5.3 Beta: una version anterior puede no abrirlos
B="${BLENDER:-$(ls -d "/c/Program Files/Blender Foundation/blender-5.3"*/blender.exe | head -1)}"
FILTRO='^(GUARDADO|AVISO|FIN|TOTAL|MAL|OK|VARIAS)|Error|Traceback'

"$B" -b "$BLEND" --factory-startup --python "$AQUI/paso4_subdividir.py" -- "$CONFIG" "$SALIDA" "$ETAPAS" 2>&1 | grep -E "$FILTRO"
"$B" -b --factory-startup --python "$AQUI/paso5_comprobar.py" -- "$SALIDA" 2>&1 | grep -E "$FILTRO"
"$B" -b --factory-startup --python "$AQUI/paso6_auditar.py" -- "$SALIDA" 2>&1 | grep -E "$FILTRO"
python -I "$AQUI/hoja_contacto.py" "$SALIDA" "$SALIDA/hoja.png"
du -sh "$SALIDA"
