---
name: chicken1-desplazamiento-a-b
description: Cuando haya que desplazar a chicken_1 (el pollo, bipedo con alas) de un punto A a un punto B (o por una ruta de varios puntos) en Blender, usar SIEMPRE sus animaciones base por defecto del chicken_1_animation_studio - caminar (Z igual), saltar subir (Z positivo), saltar bajar (Z negativo) o saltar de 3 puntos - y nunca inventar caminatas, saltos ni aleteos nuevos.
---

# Desplazar a chicken_1 de A a B con sus animaciones base

Fuente unica: `C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\chicken_1\refinar\chicken_1_animation_studio\`
(`generate_slots.py` = detector, agrupador, generadores y los diccionarios de keyframes `KEYFRAMES_CAMINAR_CYCLE`, `KEYFRAMES_SALTAR_SUBIR`, `KEYFRAMES_SALTAR_BAJAR`; `path_recorder.py` = "Paso 1 trazar recorrido"; `slot_001_parado.py` = pose parado).
A diferencia de Jerry y rat_1 (procedurales), las poses del pollo son **capturas reales** de sus animaciones base: se reutilizan tal cual, solo se retemporizan. Nunca generar a mano poses de patas/alas para caminar o saltar. Ver tambien `alfred-desplazamiento-a-b`, `jerry-desplazamiento-a-b`, `rat1-desplazamiento-a-b`.

## Regla de eleccion (por cada par de puntos consecutivos A -> B)

Z cruda (sin redondeo), tolerancia `EPSILON_Z = 1e-3` (`detect_movement_type`):

| Condicion | Animacion | Funcion | Frames |
|---|---|---|---|
| XYZ exactamente iguales | **Parada** (pose rest) | `generate_parada` | `FRAMES_PARADA_DEFAULT` = 60 |
| abs(dz) <= 0.001 | **Caminar** | `generate_caminar` | 40 por par de puntos (+1) |
| dz > 0.001 (Z positivo) | **Saltar subir** | `generate_saltar_subir` | 40 |
| dz < -0.001 (Z negativo) | **Saltar bajar** | `generate_saltar_bajar` | 33 |
| 3 puntos con el primero marcado `tipo_marcado='SALTAR'` (despegue/pico/aterrizaje) | **Saltar** (un solo arco) | `generate_saltar` | 33 |

- Nunca caminar de A a B si hay diferencia de Z: siempre salto. Nunca saltar con Z igual, salvo el `SALTAR` de 3 puntos marcado a mano (para saltar un obstaculo en plano).
- `group_segments`: puntos consecutivos de caminar = UN solo slot (cada par = un ciclo completo); subir/bajar/parada = exactamente 2 puntos; saltar = 3 puntos.
- Acciones de campo (solo si el guion las pide, marcadas con `tipo_marcado`, root fijo): `PICOTEAR` 24 f, `ACICALARSE` 80 f, `ALETEAR` 64 f, `RASCAR` 72 f → `generate_picotear_1`, `generate_acicalarse_1`, `generate_aletear_1`, `generate_rascar_1`. No son desplazamientos.

## Como se usa

1. Lista de puntos `{'coordinates': {'x':..,'y':..,'z':..}, 'tipo_marcado': ...}` (1 bloque = 1 m, Z hacia arriba).
2. Clasificar con la tabla (o `detect_movement_type` / `group_segments`).
3. Generar con el estudio, no a mano. Firmas reales (devuelven el codigo del slot; fin = `start_frame + total_frames - 1`):
   - `generate_caminar(slot_index, start_frame, points, today, root_rot=(0,0,-90), walk_style=None)`
   - `generate_saltar_subir(slot_index, start_frame, points, today, root_rot=(0,0,-90))` y `generate_saltar_bajar(...)` igual
   - `generate_saltar(slot_index, start_frame, points, today, root_rot, altura_pico=1.0)`
   - `generate_parada(slot_index, start_frame, points, today, root_rot, frames_parada=None)`
   El codigo generado define `execute_animation(player_parts, start_frame=None, end_frame=None)`. Encadenar con `frame_final + 1` como inicio del siguiente slot.
4. Estilos de caminata (`walk_style`): `NORMAL` (ciclo capturado, 41 f), `LENTO` (55 f), `RAPIDO` (29 f), `PERSEGUIDO` (11 f, aleteo de panico y mirada atras sobre el ciclo base, con rebote vertical de 5 cm). `HERIDO` y `CORRER` NO existen: caen a NORMAL; no inventarlos.
5. Rig: empty raiz `chicken_1`, armature `Armature_chicken_1`, huesos `*_chicken_1` (Root_M, Spine1_M, Chest_M, Neck_M, Head_M, Jaw*, Scapula/Shoulder/Elbow R/L = alas, Hip/Knee/Ankle R/L = patas, Knee.Right/Left, no_bone_01..08). Usar `REST_BONES_CHICKEN_1` para la lista completa.
6. Orientacion: cada par de puntos fija su rumbo (`_SEGMENT_DIRECTIONS`) con suavizado; en el salto, desde el rumbo heredado hacia despegue→aterrizaje.

## Gotchas de velocidad y trayectoria

- **La caminata dura lo mismo sin importar la distancia**: cada par de puntos consume un ciclo de 40 f (NORMAL). Con pasos de 1 bloque (recto) = 0.6 m/s; la diagonal (1.41 m) va ~1.4 veces mas rapido en los mismos frames. Por eso los puntos DEBEN ir a 1 bloque (ver seccion Recorrido); nunca dejar tramos de varios metros entre dos puntos. Para ir mas rapido usar `RAPIDO`/`PERSEGUIDO`, no acortar frames a mano.
- Salto subir/bajar: arco H = max(1, 0.75·|dz| + 0.5, 0.5·dXY) sobre la recta con smoothstep; subir 40 f, bajar 33 f fijos (con dz = ±1: vuelo fisico ≈ 24 f, asi que van ~1.4-1.7 veces mas lentos que la gravedad real, aceptable en un pollo que aletea). `saltar` de 3 puntos: pico fijo 1 m y aleteo ×1.3.

## Fisica (combinar con la skill `inercia-accion-reaccion`)

Respetar el tipo elegido y los puntos A y B. Si se pide pulir: ajustar duracion del vuelo a la altura (altura = g·T²/8, g = 0.01703 m/f²), reforzar la compresion de patas al aterrizar segun la velocidad de impacto y la anticipacion del giro, sin cambiar los frames de inicio/fin del tramo ni reemplazar los keyframes capturados.

## Recursos

Objetos, sonidos y bloques: skill `recursos-animacion` (sonidos de pollo en `sonidos`).

## Verificacion

- [ ] Cada tramo tiene el tipo que corresponde a su dz (caminar / subir / bajar / saltar).
- [ ] El pollo llega exactamente a B (XYZ) y el siguiente slot arranca ahi.
- [ ] Ninguna pose de reposo/T en ningun frame del desplazamiento; hoja de contacto en despegue, vuelo y aterrizaje.
- [ ] Sin saltos de pose (pop) en el empalme entre slots.
- [ ] Las firmas se leyeron del codigo y no se probaron en Blender: si una llamada falla, releer `generate_slots.py`.

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

- Jerarquia: empty `chicken_1` (raiz que se mueve) > armature `Armature_chicken_1` (36 huesos) > 20 mallas (Body, Head, Head2, Beak top/bottom, Eyes, Wing L/R, Leg L / L.001, ojos, parpados, pupilas, cejas). Armature y mallas con escala 1 (salvo piezas finas: pico/Head2 Z 0.2/0.33, Eyes 0.031).
- **ESCALA CORRECTA = 1.0 (uniforme) en el empty `chicken_1`** (la del archivo base `chicken_1.blend`, confirmada por el usuario el 30 oct). El 0.7 que traia la pelicula era un error y se corrigio a 1.0. Medidas a escala 1: cuerpo 0.375 x 0.5 x 0.375, ~0.9 m de alto; mira hacia +Y local. Referencia: Alfred ~2.05 m.
- En `chicken_1/refinar/estructura/chicken_1.json` el empty y el armature aparecen con escala 0.1 y el armature con rot (90, 0, 180): es el archivo de estructura, NO la escena; en `estructura_lista/chicken_1.blend` la escala es 1.0. No copiar esos valores a la pelicula.
- Los slots generados NUNCA ponen keyframes de escala: solo `location` y `rotation_euler` del empty y los huesos. Fijar la escala una vez en el empty y no tocarla.
- Visibilidad: el empty tiene `hide_viewport` y `hide_render` con keyframes (1 hasta el frame de aparicion, 0 despues; en el guardado, aparece en f754).
- Caminar medido (f754-850, con escala 0.7 antiguo): rot X/Y = 0, solo rot Z (rumbo), loc Z oscila +-0.04, keys cada 2 frames, ~0.5 m/s; la base de la malla queda a ~0 del suelo (apoyado).

## Diagnostico rapido (antes de preguntar al usuario que esta mal)

Medir, no preguntar: con Blender (o headless sobre una copia) leer en el empty: escala (debe ser 1.0), `hide_viewport/hide_render` en cada frame del guion, rot X/Y (deben ser 0 salvo vuelo/caida) y `minZ_malla - Z_root` (debe ser ~0: <0 = hundido, >0 = flotando). Caso real del 30 oct: tras el golpe el pollo gira y termina con rot (867, 371, 619) grados y minZ = -0.54 (hundido e inclinado): al aterrizar, rot X/Y deben quedar en multiplo de 360 y la base apoyada en el suelo (`inercia-accion-reaccion`).
