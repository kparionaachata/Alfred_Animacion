# Guion 2.0 de Alfred Animation Studio

El **guion** es la receta editable de toda la animacion de un personaje (flujo MANUAL, `refinar/configuraciones/*.json`). La version **2.0** es un *superconjunto* del guion de siempre: no cambia ni quita nada de lo que el
add-on ya guarda (`paso1_path`, `alfred_segs`, `organic`, `eye_sequence`, `object_imports`, `segments_throw`...) y agrega secciones **opcionales**. Un guion 1.x se lee igual (se le agregan las secciones vacias), y un guion 2.0
cargado en el panel conserva sus secciones nuevas al volver a guardarse.

Guion de Alfred de la parte 3: `configuraciones/guion_alfred_parte3.json` (estado: **sin aprobar**). Plan completo y bitacora: `PLAN_PARTE3_AL_FLUJO.md`, `GUIA_ANIMACION_ALFRED.md`.

## 1. Tiempo y anclas
Un *tiempo* es un frame (`1062`) o una **ancla**: `{"ancla": "rompe_bloque", "delta": 8}` o el atajo `"rompe_bloque+8"` / `"rompe_bloque-3"` / `"rompe_bloque"`. Las anclas viven en `anclas` y pueden colgar de otras anclas
(sin ciclos). Insertar o quitar frames (`guion_v2.mover_tiempo(g, desde, delta)`) desplaza las anclas absolutas y todo lo que cuelga de ellas viaja con ellas; luego basta con volver a aplicar sonidos / camara / objetos.
Los parametros de un tramo de movimiento cuyo nombre empieza por `t_` son tiempos.

## 2. Secciones
| Seccion | Contenido | Herramienta |
|---|---|---|
| `meta` | nombre, personaje, fps, rango, fuente, estado, `migracion` (que tramos estan migrados y cuales no) | `guion_v2.py` |
| `anclas` | `{nombre: tiempo}` | `guion_v2.py` |
| `capas` | curvas de movimiento (inclinacion del torso, mirada del cuello...) `[{id, canal, puntos:[[t, v]], interp}]` | `guion_v2.py` (sin motor todavia) |
| `exactos` | valores dados por el usuario que NINGUN filtro puede tocar en esos frames (`frames`, `huesos`, `objetos`, `ventana`) | `motor_alfred.aplicar_exactos` |
| `objetos` | `{nombre, blend, armature, hueso, escala_mano, escala_espalda, inicial, agarres, espalda, eventos}` | `objetos_mundo.py`, `preparar_escena.py` |
| `mundo` | `ocultar`, `mostrar`, `crear_pozo`, `aparecer_item`, `mover` | `objetos_mundo.py`, `preparar_escena.py` |
| `audio` | voces: `{id, personaje, archivo, inicio, emocion, texto, cara, emocion_json, duracion_f}` | `audio_import.py` |
| `sonidos` | `{modo, manuales:[{id, etiqueta, grupo, archivo, t, volumen, canal, pan}]}` | `sonidos_guion.py` |
| `camara` | `claves` (animacion hecha de un canal) y `movimiento` (desde, hasta, destino) | `camara_guion.py` |
| `movimiento` | `referencia_numerica`, `yaw_base_deg`, `organico` (filtros del estudio), `tramos` | `motor_alfred.py` |

### Eventos de objeto (`objetos[*].eventos`)
`aparece`, `toma` (a la mano), `mantiene` (cambia de agarre), `guarda` (a la espalda), `lanza` / `rebota` / `cae_sobre` (vuelo parabolico; `cae_sobre` deja el objeto pegado a un hueso de OTRO personaje), `absorbe`, `oculta`, `muestra`.
Un **agarre** es la matriz del objeto relativa al hueso de la mano: se captura de una posicion (`alfst.obj_capturar_agarre`) o se calcula de valores de mundo y el frame en que se dieron (`objetos_mundo.agarre_desde_mundo`).

### Tramos de movimiento (`movimiento.tramos`)
`{id, nombre, tipo, inicio, fin, estado, usa, params}`. Migrados hoy: **S01_sentarse** (f1-52) y **S02_descansa** (f53-190), tipo `sentado_cansado` (aprobados), y **S03_lanza_herramientas** (f191-340), tipo `lanza_herramientas` (sin aprobar; usa cuaterniones de Blender). Los frames que ningun tramo cubre salen de la **referencia numerica**
(`docs/parte3/datos_guion/base_referencia_alfred.json`, la animacion congelada del generador): asi la animacion nunca queda a medias y cada tramo se migra, compara y aprueba por separado.

## 3. Herramientas del add-on (panel "Alfred Studio")
| Panel | Que hace |
|---|---|
| 5 Guardar / Importar configuracion | guarda / carga el guion (conserva las secciones 2.0) |
| 6 Audio (voces del guion) | importar un audio (copia, tiempos por palabra, cara de la app), poner su inicio, sincronizar con Voz Sync |
| 7 Objetos y mundo (guion) | capturar agarre / espalda, calcular, comparar y hornear objetos y mundo |
| 8 Movimiento (tramos) | comparar con la referencia, hornear y aprobar cada tramo |
| 9 Sonidos y camara (guion) | capturar / aplicar los sonidos manuales y la camara |
| 10 Reproducir guion completo | cargar un guion `.json` y reproducirlo entero en la escena (todos los pasos) |

Funciones sin Blender (para scripts y pruebas): `guion_v2` (`cargar`, `guardar`, `validar`, `desplegar`, `mover_tiempo`, `anclar`), `audio_import.importar`.

## 4. Flujo de trabajo
1. **Nueva escena limpia** -> abrir `base_parte_3.blend`, "Cargar guion (.json)" (panel 10) y "Reproducir guion". Orden interno: preparar objetos -> movimiento -> voces -> objetos y mundo -> sonidos -> camara.
2. **Cambiar el tiempo**: `mover_tiempo` (o mover anclas a mano en el `.json`) y volver a aplicar sonidos / camara / objetos / voces.
3. **Audio nuevo**: `audio_import.importar(origen, personaje, inicio, script_app=...)` o el boton "Importar audio..." (el inicio es OBLIGATORIO, nunca se usa el frame actual por omision).
4. **Un tramo de movimiento nuevo**: portar al motor (`motor_alfred.TIPOS`) la parte del generador que lo produce, llenar sus parametros en el guion, `comparar` (diferencia con la referencia <= 0.001 grados), `hornear`, revisar y **aprobar** (solo lo marca el usuario).
5. Despues de cada cambio: `python pruebas/test_*.py` (fuera de Blender) y `pruebas/test_objetos_mundo.py` / `test_escena_guion.py` (dentro de Blender), y la prueba en limpio `docs/parte3/limpio/probar_en_limpio.py`.

## 5. Reglas y trampas
* El `.json` guarda **decisiones** (receta), no keyframes; los keyframes se hornean al cargar. El resultado horneado se puede exportar aparte con `ai_export` (flujo IA).
* NUNCA guardes referencias a claves (`kp = fc.keyframe_points[i]`) y llames despues a `keyframe_points.add()`: reasigna el arreglo y escribir por la referencia vieja corrompe OTRAS claves. `claves_util.Escritor` anota y escribe de golpe.
* NUNCA `keyframe_insert` sobre un personaje con NLA: crea una accion activa nueva que tapa todo. Usar `claves_util.Escritor` (escribe en la accion de la pista `Base_*`).
* Concatenar segmentos y `preview_path` borran todas las pistas NLA del personaje (tambien las de voz): despues se vuelven a sincronizar (enganchado en concatenar y al cargar un guion).
* Los objetos que siguen al cuerpo (herramientas en la espalda) siguen la pose FINAL, voces incluidas: difieren hasta ~4 cm de los del generador, que no conoce las voces.
* Un guion nunca se sobrescribe sin `sobrescribir=True` (y deja `.bak`). Una animacion es una primera version hasta que el usuario la aprueba.
* Los archivos del add-on `__init__.py` y `operators_segments.py` usan saltos de linea CRLF: editarlos en binario.

## 6. Instalacion
Fuente: `refinar/alfred_animation_studio/`. Instalada (Blender 5.2): `%APPDATA%\Blender Foundation\Blender\5.2\scripts\addons\alfred_animation_studio\` (copia de los `.py` de la fuente). Distribucion: `refinar/alfred_animation_studio.zip`
(carpeta `alfred_animation_studio/` con los `.py`). Respaldo de lo anterior en `refinar/cambios/alfred_animation_studio_instalado_antes_*.zip`. `start_animation_studio.bat` apunta a Blender 4.5.
