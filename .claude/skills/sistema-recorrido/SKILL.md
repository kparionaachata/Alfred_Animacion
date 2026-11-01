---
name: sistema-recorrido
description: Sistema de captura de recorrido (Paso 1 "trazar recorrido") que usan TODOS los personajes del proyecto (Alfred, Jerry, rat_1, chicken_1 y los futuros) - formato del JSON de puntos, reglas de 1 bloque (recto, diagonal, subir/bajar), clasificacion caminar/saltar subir/saltar bajar/parada, agrupacion en slots y flujo hasta generar y encadenar las animaciones. Usar SIEMPRE que haya que crear, leer, validar o ejecutar un recorrido de cualquier personaje.
---

# Sistema de recorrido (comun a todos los personajes)

Cada personaje tiene su `<personaje>_animation_studio` (`generador de animaciones\<personaje>\refinar\<personaje>_animation_studio\`) con el mismo esqueleto: `path_recorder.py` (Paso 1: grabar, previsualizar, exportar) + `generate_slots*.py` (clasifica, agrupa y genera los `slot_NNN_*.py`). La eleccion de animacion y los detalles de cada rig estan en la skill del personaje (`alfred-`, `jerry-`, `rat1-`, `chicken1-desplazamiento-a-b`); esta skill es la parte comun. Los tiempos fisicos y reacciones: `inercia-accion-reaccion`. Objetos, sonidos y bloques: `recursos-animacion`.

## 1. Como se captura (Paso 1)

1. Se activa la grabacion, se entra en modo EDIT sobre el terreno y se selecciona UNA cara por clic. Un handler (`depsgraph_update_post`) guarda el centro global de la cara (`calc_center_median` @ `matrix_world`), su textura y su `face_index`, y la deselecciona (se puede repetir la misma cara).
2. Cada punto lleva un desplegable `tipo_segmento` (`AUTO` por defecto; `PARADA`, `SALTAR` o acciones puntuales segun el personaje), frames de parada, animacion importada, orientacion guardada y estilo de caminata por tramo.
3. `_expand_points_with_paradas` duplica el punto detras de cada `PARADA` (dos puntos iguales = parada; se ignora si el tramo real no es plano).
4. "Reproducir recorrido" = vista previa; "Exportar recorrido (slots)" / "Generar slots (InScene)" = genera y encadena los slots.

## 2. Formato del recorrido (JSON)

Ejemplo real: `ejemplo_recorrido.json` (en la carpeta de cualquiera de las skills de desplazamiento).

```
{"path_name": "recorded_path",
 "key_points": [{"index": 1, "coordinates": {"x": -59.5, "y": 32.5, "z": 13.0}, "texture": "stone", "face_index": "75430"}, ...]}
```
`tipo_segmento` / `tipo_marcado` solo aparece en puntos PARADA, SALTAR o accion puntual. Coordenadas = centro de la cara (X, Y en `.5`, Z = altura de la cara superior, entera); 1 bloque = 1 m, Z hacia arriba.

## 3. Reglas de los puntos (OBLIGATORIO)

- El punto de partida puede tener cualquier decimal (5.5, 6, 9; o -77.439, 33.16, 12 si el personaje ya esta puesto) y se conserva TAL CUAL. Nunca redondear ni ajustar a la cuadricula.
- Cada paso es de exactamente 1 bloque:
  - Recto: ±1 en X **o** en Y (6.5, 6, 9 tras 5.5, 6, 9).
  - Diagonal: ±1 en X **y** ±1 en Y (1.41 m), misma Z.
  - Subir / bajar: Z ±1 junto con ±1 en un eje hacia delante (-54.5, 27.5, 13 → -54.5, 26.5, 12).
- Un trayecto largo A→B es una cadena de puntos a 1 bloque (5.5 → 6.5 → 7.5 → 8.5); nada de pasos de varios metros.
- Si faltan puntos, preguntarlos al usuario; nunca inventarlos.

## 4. Clasificacion y agrupacion (identica en todos los estudios)

Por cada par consecutivo (`detect_movement_type`; DEBE coincidir con `_detect_move` del recorder y con la estimacion de frames):

| Condicion | Tipo |
|---|---|
| XYZ iguales | `parada` |
| Z igual | `caminar` |
| Z sube | `saltar_subir` |
| Z baja | `saltar_bajar` |
| marcas `SALTAR` / acciones puntuales | override evaluado ANTES que la Z (segun personaje) |

`group_segments`: los pares consecutivos de `caminar` forman UN slot (rectos y diagonales mezclados); `saltar_subir`, `saltar_bajar` y `parada` son tramos de exactamente 2 puntos (el ultimo punto de un caminar es el primero del salto siguiente); `SALTAR` de 3 puntos solo en chicken_1.

Tolerancia de Z por personaje (no mezclar): Alfred `round(z,2)`, Jerry `round(z,4)`, rat_1 `round(z,2)`, chicken_1 Z cruda con `EPSILON_Z = 1e-3`.

Ejemplo (`ejemplo_recorrido.json`, 27 puntos, 26 pasos: 13 rectos, 10 diagonales, 3 bajadas): caminar 1-15, bajar 15→16, caminar 16-19, bajar 19→20, caminar 20-26, bajar 26→27 = 6 slots.

## 5. Flujo para ejecutar un recorrido

1. Validar los puntos: pasos de 1 bloque, decimales del inicio intactos, sin marcas inesperadas.
2. Clasificar y agrupar con `detect_movement_type` / `group_segments` del estudio del personaje (no reescribirlos).
3. Generar cada slot con su `generate_*` (firmas en la skill del personaje) y ejecutarlo sobre el rig; el siguiente arranca en `frame_final + 1`. Rotacion de partida = la del personaje (`prev_rz` / `root_rot`).
4. Prohibido desplazar con keyframes de root o huesos hechos a mano.
5. Verificar: pasa por todos los puntos, llega al ultimo con los mismos decimales, mira hacia el siguiente punto en cada tramo, sin pose T/rest, sin saltos de pose (pop) en los empalmes (hoja de contacto en despegues y aterrizajes).

## 6. Personajes que usan el sistema

| Personaje | Estudio | Rig | Notas |
|---|---|---|---|
| Alfred | `alfred\refinar\alfred_animation_studio` | `Armature` + empty `alfred` | biped, mocap Mixamo; ademas puntos de encuentro, interacciones y suavizado de empalmes |
| Jerry | `jerry\refinar\jerry_animation_studio` | empty `jerry`, `Dog_001_rig` | cuadrupedo; saltos adaptativos (`jump_motion.py`) |
| rat_1 | `rat_1\refinar\rat_1_animation_studio` | empty `rat_1`, `body1_1` | cuadrupedo procedural; subir 18 f, bajar 20 f; acciones PARARSE_DOS_PATAS/OLFATEAR/ESCARBAR/ROER |
| chicken_1 | `chicken_1\refinar\chicken_1_animation_studio` | empty `chicken_1`, `Armature_chicken_1` | keyframes capturados; caminar 40 f por paso, subir 40 f, bajar 33 f, `SALTAR` de 3 puntos; acciones PICOTEAR/ACICALARSE/ALETEAR/RASCAR |

## 7. Personaje nuevo

Debe copiar el esqueleto del estudio (recorder + generador con `detect_movement_type`, `group_segments`, `generate_caminar`, `generate_saltar_subir`, `generate_saltar_bajar`, `generate_parada`), usar las animaciones base del propio personaje (no las de otro rig) y tener su skill `<personaje>-desplazamiento-a-b`, que remite a esta. Anotarlo en la tabla del punto 6 y en `CLAUDE.md`.

## 8. Escala, visibilidad y verificacion en escena (todos los personajes)

- La escala del personaje vive SOLO en su empty raiz (chicken_1 = 1.0 confirmado, igual que su archivo base; alfred = 1.0; rat_1 estaba a 0.6 en la pelicula sin confirmar, su base es 1.0). Armature y mallas quedan en 1. Los slots generados nunca ponen keyframes de escala: fijarla una vez y no animarla. Los archivos de `refinar/estructura/` pueden tener otra escala o ser copia de otro personaje (la de rat_1 es de Alfred): NO usarlos como referencia; medir la escena.
- La raiz se anima con `location` y `rotation_euler` (keys cada 2 frames al caminar, rebote Z +-0.03, rotacion X/Y = 0, solo Z cambia el rumbo) y con `hide_viewport` / `hide_render` (1 hasta el frame de aparicion, 0 despues). Un slot que arranca tarde deja al personaje invisible antes.
- Antes de decir que algo esta mal o de preguntar al usuario: MEDIR (Blender o headless sobre una copia): escala del empty, visibilidad por frame, rot X/Y, `minZ_malla - Z_root` (<0 hundido, >0 flota) y velocidad en m/s. El archivo guardado en disco puede diferir de la escena viva (otros frames de aparicion): comparar con la escena viva si Blender esta conectado.
- Tras vuelos, golpes o caidas, la rotacion X/Y final debe ser multiplo de 360 y el personaje apoyado en el suelo (`inercia-accion-reaccion`).

## Limites conocidos

Leido a fondo: grabacion, expansion de paradas, clasificacion y agrupacion, generadores de caminar/saltar de Jerry, rat_1 y chicken_1. NO leido a fondo: la vista previa (`PreviewPath`), los puntos de encuentro y las interacciones de Alfred. Las firmas de `generate_*` no se probaron en Blender.
