# Dos flujos: MANUAL e IA

Alfred Animation Studio tiene **dos flujos independientes** que pueden trabajar en paralelo sobre la misma escena y
los mismos personajes. Otras IA recibiran tareas de animacion como esta: cada una usa el flujo IA y no toca el manual.

| | FLUJO MANUAL | FLUJO IA |
|---|---|---|
| Quien | El usuario, con los paneles del add-on | Una IA (varias a la vez), con `ai_api` + `ai_export` |
| Que se guarda | El **guion** `.json`: la receta editable de toda la secuencia | El **resultado completo**: animacion horneada `.json` + `.py` autonomo + `manifest.json` |
| Donde | `refinar/configuraciones/` | `refinar/animaciones_ia/<nombre>/` |
| Se edita luego | Si, cargando el guion en los paneles | No: es un resultado final (para cambiar algo se rehace y se reexporta) |
| Depende del guion | Si, es su fuente unica | **No**. El guion es opcional y nunca es cuello de botella |
| Requiere el add-on | Si | No para reproducir (el `.py` lleva los datos y el codigo) |

## Flujo manual (sin cambios)
Recorrido (Pasos 1-2) -> segmentos (Paso 3) -> poses/filtros/ojos -> `Concatenar segmentos` -> `Guardar configuracion`.
El `.json` de `configuraciones/` es el guion por personaje. Ninguna IA lo sobrescribe.

## Flujo IA
1. **Crear.** Con `ai_api` (dentro de Blender: `from alfred_animation_studio import ai_api`): poses con `crear_pose`,
   colocar el cuerpo con `root_por_suelo` / `root_por_cadera`, comprobar con `medir` y capturas. Puede apoyarse en el
   motor manual escribiendo un guion **nuevo** (puente: `guion_*`, `seg_*`, `concatenar`), o animar sin guion.
2. **Guardar el resultado completo.**
   `ai_export.exportar("<nombre>", agente="<quien>", guion_fuente=<ruta o None>, notas="...")` escribe:
   - `<nombre>.animacion.json`: root, 22 bones y ojos (transformaciones, shape keys, visibilidad) fotograma a fotograma.
   - `<nombre>.py`: script autonomo con los datos incrustados. Se ejecuta en Blender con Alfred en la escena.
   - `manifest.json`: agente, fecha, rango, fps, objetos, fuente, limitaciones.
3. **Reproducir en cualquier escena.** `ai_export.importar("<nombre>")` o ejecutar el `.py`. Crea pistas NLA propias
   `IA_<nombre>__*`; reimportar reemplaza solo esas pistas. `FRAME_OFFSET` en el `.py` (o `frame_offset=`) desplaza el inicio.

Verificado con `persecucion_zombie_agua`: el `.py` ejecutado en un Blender limpio sobre `estructura_lista/alfred.blend`
reproduce la escena con diferencia maxima de 8 mm en once cuadros.

## Otros personajes y props
`ai_export` no es solo de Alfred: el parametro `personaje=` acepta `ALFRED` (por defecto), `JERRY` o un dict propio
`{root, armature, ojos, extras, extras_fuente, todos_los_huesos, carpeta}`. `extras` son props que tambien se hornean
(ej. la antorcha de Jerry) y `extras_fuente` dice de que `.blend` importarlos si faltan al reproducir. Cada personaje
guarda en su propia carpeta `animaciones_ia/`. Ejemplo: `jerry/refinar/animaciones_ia/jerry_antorcha_salto_agua/`.
Tambien se hornea la transformacion del objeto armature (Jerry lo tiene con escala distinta segun donde se importe).

## Reglas para que varias IA no se pisen
- Un `<nombre>` unico por tarea (carpeta y pistas propias). Nunca escribir en la carpeta de otra animacion.
- No modificar ni sobrescribir guiones de `configuraciones/`. Si se usa el puente, guardar un guion **nuevo** (`*_ia_*.json`).
- La libreria `poses/` es compartida y solo se agrega: nombres nuevos, prefijo `ia_<nombre>_` en poses nuevas.
- No cambiar el codigo existente del add-on sin pedido expreso; lo nuevo va en `ai_api.py` / `ai_export.py`.
- Antes de tocar una escena abierta: respaldo (`save_as_mainfile(copy=True)`). Cancelar la reproduccion antes de capturar
  cuadros (`concatenar` la arranca al terminar).
- No marcar una animacion como aprobada sin confirmacion del usuario. Registrar cada trabajo en `GUIA_ANIMACION_ALFRED.md`.

## Limitaciones del flujo IA
No exporta props importados o lanzados, invisibilidad de mallas ni objetos ajenos a Alfred; es lineal por fotograma
(no editable por poses). Para esos casos se usa el flujo manual o se amplia `ai_export`.
