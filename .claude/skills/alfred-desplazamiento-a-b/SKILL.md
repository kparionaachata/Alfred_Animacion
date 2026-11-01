---
name: alfred-desplazamiento-a-b
description: Cuando haya que desplazar a Alfred de un punto A a un punto B (o por una ruta de varios puntos) en Blender, elegir SIEMPRE la animacion preestablecida segun la diferencia de Z - caminar (Z igual), saltar subir (Z positivo) o saltar bajar (Z negativo) - del sistema 1 de recorrido del alfred_animation_studio. No inventar poses de caminata ni de salto.
---

# Desplazar a Alfred de A a B con las animaciones preestablecidas

Fuente unica: `C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\alfred_animation_studio\`
(`generate_slots_alfred.py` = detector, caminar y claves de los saltos; `jump_motion.py` = tiempos y trayectoria de los saltos).

## Regla de eleccion (por cada par de puntos consecutivos A -> B)

Comparar Z redondeada a 2 decimales (`round(z, 2)`, igual que `detect_movement_type`):

| Condicion | Animacion | Tipo del estudio |
|---|---|---|
| zB == zA (y XY distintos) | **Caminar** | `caminar` (`generate_caminar`) |
| zB > zA (Z positivo, sube) | **Saltar subir** | `saltar_subir` (`generate_saltar_subir`, claves `KEYFRAMES_SALTAR_SUBIR`, 18 f base) |
| zB < zA (Z negativo, baja) | **Saltar bajar** | `saltar_bajar` (`generate_saltar_bajar`, claves `KEYFRAMES_SALTAR_BAJAR`, 35 f base) |
| mismo punto (XYZ iguales) | caminar en el sitio, o `parada` si se marca asi | |
| salto en plano, marcado como SALTAR | `saltar_horizontal` | |

- Nunca caminar de A a B si hay diferencia de Z: siempre salto. Nunca saltar si Z es igual.
- Rutas de varios puntos: separar en tramos; los consecutivos con Z igual se agrupan en un solo `caminar`; cada subida o bajada es su propio tramo de exactamente 2 puntos (`_group_segments_legacy`).
- Un cambio de Z da un salto aunque sea pequeno (tolerancia solo 0.01).

## Como se usa

1. Armar la lista de puntos `{'index': i, 'coordinates': {'x':..,'y':..,'z':..}}` (1 bloque = 1 m, Z hacia arriba).
2. Clasificar cada tramo con la tabla de arriba (o llamar a `detect_movement_type` / `group_segments` del estudio).
3. Generar con el estudio, no a mano: `generate_caminar(slot, frame_ini, puntos, hoy, root_rot, walk_style)`, `generate_saltar_subir(...)`, `generate_saltar_bajar(...)`; devuelven `(codigo, frame_final)`. Ejecutar el codigo y su `execute_animation` sobre el rig (`Armature` + empty `alfred`) y encadenar con `frame_final + 1` como inicio del siguiente tramo.
4. Estilos de caminata: `NORMAL` (1.93 m/s, ciclo 20 f), `LENTO`, `HERIDO`, `RAPIDO`, `CORRER` (`WALK_STYLE_PARAMS`). Por defecto NORMAL.
5. La caminata ya publicada es `codigos de animacion/alfred/slot_1_caminar_llanura_animated.py`; los clips sueltos de salto estan en la misma carpeta (`slot_001_saltar_subir_*`, `slot_001_saltar_abajo_*`). Usar la misma logica de eleccion.
6. Orientacion: el root rota hacia el sentido de marcha (en el salto, durante la preparacion; en el caminar, suavizado en 12 f).

## Fisica (combinar con la skill `inercia-accion-reaccion`)

El estudio tiene defectos conocidos (analizados 30 oct): los saltos de subida y el horizontal van ~3-4 veces mas rapidos que la gravedad real; no hay impulso de piernas al despegar ni amortiguacion al aterrizar; el giro de 90 grados se hace en 3-5 frames; el caminar arranca/frena en seco y puede patinar. Al usar estas animaciones, cuando se pida pulir: respetar la eleccion de tipo, pero corregir tiempos de vuelo (altura = g*T^2/8), anadir compresion de cadera/rodillas al aterrizar segun la velocidad de impacto, impulso previo al despegar y anticipacion en el giro, sin cambiar los puntos A y B ni los frames de inicio/fin del tramo.

## Verificacion

- [ ] Cada tramo tiene el tipo que corresponde a su dz (caminar / subir / bajar).
- [ ] Alfred llega exactamente a B (XYZ) y el siguiente tramo arranca en ese punto.
- [ ] Ninguna pose T en ningun frame; revisar con hoja de contacto en despegue, vuelo y aterrizaje.
- [ ] No hay saltos de pose (pop) en el empalme entre tramos.

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
