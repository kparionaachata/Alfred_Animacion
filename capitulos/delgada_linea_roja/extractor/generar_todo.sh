#!/bin/sh
# Regenera personajes, clips y biblioteca y comprueba todo. Uso: sh generar_todo.sh carpeta_temporal
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
S="$1"
python -I exportar_personajes.py 2>/dev/null | tail -1
python -I exportar_mecanicas.py animaciones armas 2>/dev/null | tail -1 | cut -c1-200
"$B" -b --factory-startup --python comprobar_glb.py -- ../personajes_napoleon "$S/foto_c.png" 2>&1 | grep -E "^GLB MAL|^TOTAL|Traceback" | cut -c1-200
python -I exportar_biblioteca.py "$S/bib" 2>/dev/null | tail -1 | cut -c1-100
"$B" -b --factory-startup --python construir_biblioteca.py -- "$S/bib" 2>&1 | grep -E "^FIN|Traceback|Error:|faltan \[.+\]" | cut -c1-200
"$B" -b --factory-startup --python comprobar_biblioteca.py -- "$S/bib_fotos" 2>&1 | grep -E "^BIB MAL|^TOTAL|^CLIP|^FIN|Traceback|Error" | cut -c1-300
"$B" -b --factory-startup --python comprobar_mecanicas.py -- "$S/prueba_mec" --todos 2>&1 | grep -E "^GLB.*MAL|TOTAL_GLB|^FIN|Traceback|Error" | cut -c1-200
rm -rf ../efectos_y_mecanicas/__pycache__ ../efectos_y_mecanicas/efectos/__pycache__
find ../biblioteca_personajes -name "*.blend1" -delete
du -sh ../biblioteca_personajes ../biblioteca_personajes/armas ../efectos_y_mecanicas ../personajes_napoleon
ls ../biblioteca_personajes/armas | wc -l
echo TERMINADO
