---
name: rat1-desplazamiento-a-b
description: Cuando haya que desplazar a rat_1 (la rata, cuadrupedo) de un punto A a un punto B (o por una ruta de varios puntos) en Blender, elegir SIEMPRE la animacion preestablecida segun la diferencia de Z - caminar (Z igual), saltar subir (Z positivo) o saltar bajar (Z negativo) - del rat_1_animation_studio. No inventar poses de caminata ni de salto.
---

# Desplazar a rat_1 de A a B con las animaciones preestablecidas

Fuente unica: `C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\rat_1\refinar\rat_1_animation_studio\`
(`generate_slots_rat_1.py` = detector, agrupador, caminar, saltos y acciones; `path_recorder.py` = "Paso 1 trazar recorrido"). Misma logica que `alfred-desplazamiento-a-b` y `jerry-desplazamiento-a-b`, con rig cuadrupedo y 100 % procedural (sin mocap).

## Regla de eleccion (por cada par de puntos consecutivos A -> B)

Comparar con `round(v, 2)` (igual que `detect_movement_type`):

| Condicion | Animacion | Funcion |
|---|---|---|
| XYZ identicos y punto marcado PARADA | **Parada** | `generate_parada` |
| XYZ identicos sin marca | caminar (en el sitio) | `generate_caminar` |
| zB == zA (XY distintos) | **Caminar** | `generate_caminar` |
| zB > zA (Z positivo, sube) | **Saltar subir** | `generate_saltar_subir` (18 f fijos) |
| zB < zA (Z negativo, baja) | **Saltar bajar** | `generate_saltar_bajar` (20 f fijos) |

- Nunca caminar de A a B si hay diferencia de Z: siempre salto. Nunca saltar si Z es igual.
- `group_segments`: los puntos consecutivos de tipo caminar forman UN solo slot; cada subida o bajada es un tramo de exactamente 2 puntos.
- Overrides por `tipo_segmento` del punto de partida (se evaluan ANTES que la Z): `PARARSE_DOS_PATAS`, `OLFATEAR`, `ESCARBAR`, `ROER` (acciones puntuales con la rata fija en el punto; el tramo hasta el siguiente punto se camina despues). No son desplazamientos: usarlas solo si el guion las pide (`generate_pararse_dos_patas`, `generate_olfatear`, ... y `generate_idle`).
- En rat_1 NO existe `SALTAR` ni `saltar_horizontal`: un salto en plano no tiene preset; no inventarlo.

## Como se usa

1. Lista de puntos `{'index': i, 'coordinates': {'x':..,'y':..,'z':..}, 'tipo_segmento': 'AUTO'}` (1 bloque = 1 m, Z hacia arriba).
2. Clasificar con la tabla (o `detect_movement_type` / `group_segments`).
3. Generar con el estudio, no a mano. Firmas reales (devuelven `(codigo, frame_final)`):
   - `generate_caminar(slot_index, frame_start, points, today, root_rot, walk_style="NORMAL")`
   - `generate_saltar_subir(slot_index, frame_start, points, today, root_rot)`
   - `generate_saltar_bajar(slot_index, frame_start, points, today, root_rot)`
   - `generate_parada(slot_index, frame_start, points, today, root_rot, frames_parada=60)`
   Ejecutar el codigo (define `execute_animation()` y la llama) y encadenar con `frame_final + 1` como inicio del siguiente tramo. `root_rot` = (rx, ry, rz) en grados; el rumbo real sale de los puntos.
4. Rig: empty raiz `rat_1`, armature `body1_1` (22 huesos: patas `leftArm_1/rightArm_1/leftHand_1/rightHand_1/leftThigh_1/rightThigh_1/leftFoot_1/rightFoot_1`, columna `body1_1/body2_1`, `neck_1/head_1`, cola `tail1_1/tail2_1`). Los huesos faciales no se tocan.
5. Caminar: trote diagonal, ciclo de 14 f (NORMAL), base 24 f/m = 1 m/s; n_frames se redondea a medio ciclo para empalmar sin pop. Estilos `NORMAL`, `LENTO`, `HERIDO`, `RAPIDO`, `CORRER`.
   - **Ojo, inconsistencia del estudio:** el generador hace `frames/m = 24 * speed_mult` (LENTO 0.6 = mas rapido, CORRER 2.2 = mas lento) y la estimacion de `path_recorder.py` divide. Comprobar la velocidad real del tramo generado antes de fiarse del nombre del estilo; no "arreglarlo" sin que se pida.
6. Saltos: el root sigue P0->P1 con smoothstep + arco `4·H·s·(1-s)`; subir H = max(0.6·|dz|, 0.35·dXY, 0.25); bajar H = max(0.3·|dz|, 0.3·dXY, 0.2). Giro hacia el rumbo del salto en 8 f (curva S) desde el rumbo heredado del tramo anterior. Poses: agazapado → despegue → vuelo plegado → patas delanteras al aterrizar (subir); extension → impacto → compresion → asentado (bajar).

## Fisica (combinar con la skill `inercia-accion-reaccion`)

Duracion fija sin importar la altura: un salto de 3 m dura lo mismo que uno de 0.5 m. Para altura dz y arco con apice A sobre el punto mas alto, el vuelo fisico es ~(√(2·h1/g)+√(2·h2/g)) con g = 0.01703 m/f² (p. ej. subir 1 m ≈ 15 f, bajar 1 m ≈ 11 f de vuelo). Al pulir: respetar el tipo elegido y los puntos A y B, escalar la duracion con la altura (altura = g·T²/8), reforzar la compresion al aterrizar segun la velocidad de impacto y la anticipacion del giro; no cambiar frames de inicio/fin del tramo.

## Recursos

Objetos, sonidos y bloques: skill `recursos-animacion`.

## Verificacion

- [ ] Cada tramo tiene el tipo que corresponde a su dz (caminar / subir / bajar).
- [ ] La rata llega exactamente a B (XYZ) y el siguiente tramo arranca ahi.
- [ ] Ninguna pose de reposo/T en ningun frame; hoja de contacto en agazapado, vuelo y aterrizaje.
- [ ] Sin saltos de pose (pop) en el empalme entre tramos.
- [ ] Las firmas se leyeron del codigo y no se probaron en Blender: si una llamada falla, releer `generate_slots_rat_1.py`.

## Recorrido: formato y reglas de los puntos (OBLIGATORIO)

Claude NO crea el recorrido a mano ni pone keyframes de root/huesos para desplazar: arma los puntos y los pasa por el sistema del estudio (`detect_movement_type` → `group_segments` → `generate_*`). Si faltan puntos, los pide al usuario; nunca los inventa ni los redondea.

- **Formato** (el mismo que exporta el Paso 1; ejemplo real en `ejemplo_recorrido.json` de esta carpeta): `{"path_name": "recorded_path", "key_points": [{"index": 1, "coordinates": {"x": -59.5, "y": 32.5, "z": 13.0}, "texture": "stone", "face_index": "75430"}, ...]}`. Los marcadores `tipo_segmento` / `tipo_marcado` solo aparecen si el punto es PARADA, SALTAR o accion puntual; sin marca = AUTO.
- **Coordenadas = centro de la cara del bloque** (X e Y en `.5` en el ejemplo, Z = altura de la cara superior, entera). El punto de partida puede tener cualquier decimal (p. ej. 5.5, 6, 9; o X -77.439, Y 33.16, Z 12 si el personaje ya esta puesto) y se conserva TAL CUAL.
- **Cada paso es de exactamente 1 bloque**, nunca mas:
  - Avanzar / retroceder: ±1 en X **o** en Y (el otro eje y la Z no cambian). Ej. (5.5, 6, 9) → (6.5, 6, 9).
  - Diagonal: ±1 en X **y** ±1 en Y a la vez (1.41 m), misma Z. Ej. (-59.5, 32.5, 13) → (-58.5, 33.5, 13).
  - Subir / bajar: Z ±1 junto con ±1 en un eje (X o Y) hacia delante. Ej. (-54.5, 27.5, 13) → (-54.5, 26.5, 12) = saltar bajar.
- Trayecto largo de A a B = cadena de puntos a 1 bloque uno de otro, con los decimales del inicio intactos (5.5 → 6.5 → 7.5 → 8.5). No saltarse puntos ni dejar pasos de varios metros.
- Los puntos consecutivos con Z igual (rectos y diagonales mezclados) forman UN solo slot de caminar; cada cambio de Z es su propio tramo de 2 puntos.
- El ejemplo (`ejemplo_recorrido.json`, 27 puntos, 26 pasos) da: caminar 1-15 (14 pasos: rectos y diagonales), saltar bajar 15→16, caminar 16-19, saltar bajar 19→20, caminar 20-26, saltar bajar 26→27 = 6 slots.
- Verificar al final: el personaje pasa por todos los puntos, llega a B con los mismos decimales y la rotacion Z de cada tramo mira hacia el siguiente punto.

## Escala, jerarquia y estado en escena (MEDIDO en `base_tarde con las ranas.blend`, 30 oct)

- Jerarquia: empty `rat_1` (raiz que se mueve) > armature `body1_1` (22 huesos, loc Z 0.256) > malla `Mesh_0_1`. Armature y malla con escala 1.
- **La escala vive SOLO en el empty `rat_1`. En la pelicula esta a 0.6 (SIN CONFIRMAR por el usuario); la base `estructura_lista/rat_1.blend` es 1.0, igual que el pollo (corregido a 1.0 el 30 oct): preguntar o medir antes de usar 0.6.** Malla sin escalar = 0.438 (X) x 2.054 (Y, largo) x 0.447 (Z, alto) -> con 0.6 mide 0.26 x 1.23 x 0.27 m; el cuerpo mira hacia +Y local. Referencia: Alfred mide ~2.05 m de alto.
- Los slots generados NUNCA ponen keyframes de escala: solo `location` y `rotation_euler` del empty y los huesos. No animar ni cambiar la escala; fijarla una vez en el empty.
- Visibilidad: el empty tiene `hide_viewport` y `hide_render` con keyframes (1 hasta el frame de aparicion, 0 despues; en el guardado, aparece en f634). Si el slot arranca tarde, el personaje no se ve antes.
- Caminar medido (f634-760): rot X/Y = 0, solo rot Z (rumbo); loc Z oscila +-0.03 (rebote), keys cada 2 frames, ~0.7 m/s; la base de la malla toca el suelo (minZ - rootZ = 0.0).
- La carpeta `rat_1/refinar/estructura/` trae `alfred.blend`/`alfred.json` (copia del toolkit de Alfred): NO sirve para medir la rata; usar `estructura_lista/rat_1.blend` (empty escala 1.0, sin escalar).

## Diagnostico rapido (antes de preguntar al usuario que esta mal)

Medir, no preguntar: con Blender (o headless sobre una copia) leer en el empty: escala (debe ser 0.6), `hide_viewport/hide_render` en cada frame del guion, rot X/Y (deben ser 0 salvo vuelo/caida) y `minZ_malla - Z_root` (debe ser ~0: <0 = hundido, >0 = flotando). Caso real del 30 oct: tras el golpe la rata gira y termina con rot (884, 379, 632) grados y minZ = -0.5 (hundida e inclinada): al aterrizar, rot X/Y deben quedar en multiplo de 360 y la base apoyada en el suelo (`inercia-accion-reaccion`).
