---
name: jerry-desplazamiento-a-b
description: Cuando haya que desplazar a Jerry (el perro, cuadrupedo) de un punto A a un punto B (o por una ruta de varios puntos) en Blender, elegir SIEMPRE la animacion preestablecida segun la diferencia de Z - caminar (Z igual), saltar subir (Z positivo) o saltar bajar (Z negativo) - del jerry_animation_studio. No inventar poses de caminata ni de salto.
---

# Desplazar a Jerry de A a B con las animaciones preestablecidas

Fuente unica: `C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\jerry\refinar\jerry_animation_studio\`
(`generate_slots_jerry.py` = detector, agrupador, caminar y wrappers de salto; `jump_motion.py` = tiempos, trayectoria y ciclos de los saltos).
Es la version de Jerry de la skill `alfred-desplazamiento-a-b` (misma logica, rig cuadrupedo).

## Regla de eleccion (por cada par de puntos consecutivos A -> B)

Comparar Z con `round(z, 4)` (igual que `detect_movement_type`; Alfred usa 2 decimales):

| Condicion | Animacion | Funcion del estudio |
|---|---|---|
| XYZ identicos | **Parada** (quieto, pose IDLE) | `generate_parada` |
| zB == zA (XY distintos) | **Caminar** | `generate_caminar` |
| zB > zA (Z positivo, sube) | **Saltar subir** | `generate_saltar_subir` (ciclo DogJumpCycle, 15 f) |
| zB < zA (Z negativo, baja) | **Saltar bajar** | `generate_saltar_bajar` (base QuadrupedWalkPlainCycle, 24 f) |
| punto marcado `tipo_segmento='SALTAR'` | salto segun dz: subir / bajar / `saltar_horizontal` si dz = 0 | |

- Nunca caminar de A a B si hay diferencia de Z: siempre salto. Nunca saltar si Z es igual (salvo marca SALTAR).
- Rutas de varios puntos: `group_segments` agrupa los puntos consecutivos de tipo `caminar` en un solo slot; cada subida o bajada es su propio tramo de exactamente 2 puntos.
- Cualquier cambio de Z (aunque sea 0.001) produce un salto: redondear la Z de los puntos antes si se quiere caminar.

## Como se usa

1. Lista de puntos `{'index': i, 'coordinates': {'x':..,'y':..,'z':..}, 'tipo_segmento': 'AUTO'}` (1 bloque = 1 m, Z hacia arriba).
2. Clasificar con la tabla (o llamar a `detect_movement_type` / `group_segments`).
3. Generar con el estudio, no a mano. Firmas reales:
   - `generate_caminar(slot, frame_ini, puntos, hoy, prev_rz, root_rot=(0,0,-90), walk_style='NORMAL', frames_por_bloque=32)`
   - `generate_saltar_subir(slot, frame_ini, puntos, hoy, prev_rz, root_rot=(0,0,-90), fps=24.0)`
   - `generate_saltar_bajar(...)` y `generate_saltar_horizontal(...)` con los mismos argumentos que subir
   - `generate_parada(slot, frame_ini, puntos, hoy, root_rot, frames_parada=None, observar=False)`
   Devuelven el codigo de la animacion y el frame final; ejecutarlo sobre el rig y encadenar con `frame_final + 1` como inicio del siguiente tramo. `prev_rz` = rotacion Z con la que terminó el tramo anterior (para no girar de golpe).
4. Estilos de caminata (`WALK_STYLE_PARAMS`): `NORMAL` (por defecto), `LENTO`, `HERIDO`, `RAPIDO`, `CORRER`, `CORRER_2`. Con 32 f/bloque: NORMAL ≈ 0.75 m/s, CORRER ≈ 1.7 m/s, CORRER_2 ≈ 2.5 m/s. Para mover mas rapido usar un estilo, no acortar `frames_por_bloque` a mano.
5. Rig: empty raiz `jerry`, armature `Dog_001_rig`, ojos `ojo_*_jerry`. Cuadrupedo: no usar poses/huesos de Alfred.
6. Orientacion: el root rota hacia el sentido de marcha; en el salto, durante la preparacion.

## Duraciones del salto (adaptativas, jump_timing)

Reparto preparacion / vuelo / aterrizaje (frames, total = suma + 1):

| Salto | prep | vuelo | aterr | total |
|---|---|---|---|---|
| subir dz=1 | 2 | 9 | 3 | 15 |
| subir dz=2 | 2 | 13 | 3 | 19 |
| bajar dz=-1 | 4 | 14 | 5 | 24 |
| bajar dz=-3 | 4 | 25 | 5 | 35 |
| horizontal 3 m | 2 | 7 | 3 | 13 |

El arco es una Bezier cuyo apice es max(zA, zB) + max(0.8, 1.4·dz, 0.45·distancia_XY).

## Fisica (combinar con la skill `inercia-accion-reaccion`)

Defectos medidos (30 oct): el vuelo de los saltos de subida y horizontal es ~5-6 veces mas rapido que la gravedad real (subir 1 m: 9 f vs ~20 f fisicos; horizontal: 7 f vs ~18 f); la bajada va ~2 veces mas rapida (14 f vs ~20 f). Sin compresion de patas al aterrizar ni impulso al despegar reforzado. Al pulir: respetar el tipo elegido y los puntos A y B, y corregir tiempo de vuelo (altura = g·T²/8, g = 0.01703 m/f²), compresion de patas/columna al aterrizar segun la velocidad de impacto, impulso previo al despegue y anticipacion en el giro. No cambiar los frames de inicio/fin del tramo.

## Recursos

Objetos, sonidos y bloques: skill `recursos-animacion`.

## Verificacion

- [ ] Cada tramo tiene el tipo que corresponde a su dz (caminar / subir / bajar).
- [ ] Jerry llega exactamente a B (XYZ) y el siguiente tramo arranca ahi.
- [ ] Ninguna pose T/rest en ningun frame; revisar con hoja de contacto en despegue, vuelo y aterrizaje.
- [ ] Sin saltos de pose (pop) en el empalme entre tramos.
- [ ] Las firmas de arriba se leyeron del codigo y no se probaron en Blender: si una llamada falla, releer `generate_slots_jerry.py`.

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
