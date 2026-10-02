# Tablero de tareas compartido (Claude = maestro, Codex/ChatGPT = esclavo)

**Actualizado: 2026-09-30 por Claude.** Lee ESTE archivo completo antes de tocar nada. Lo que diga aqui sustituye a versiones anteriores del tablero
(los parametros de E1 de la primera version —estilos LENTO/BRAZO_ABAJO/ESPASMOS, aterrizajes lejanos, retrasos 85/120/155— estan SUPERADOS).
Contexto general: `FLUJO_DE_TRABAJO.md`, `FLUJOS_MANUAL_E_IA.md`, bitacora viva `GUIA_ANIMACION_ALFRED.md` (mas detalle tecnico).

## 1. Reglas y protocolo
1. **Claude = MAESTRO**: planifica, define criterios, es el UNICO que toca la escena de Blender y verifica; declara "listo para revisar". **Codex = ESCLAVO**: ejecuta encargos cerrados sobre archivos, sin Blender ni MCP (ni `blender_ejecutar.py`), sin editar el codigo del add-on de Alfred.
2. Estados de un encargo: `LIBRE` -> `EN CURSO` (Codex lo toma) -> `ENTREGADO` (+ resumen de 3 lineas y como probarlo) -> el maestro marca `ACEPTADO` o `REHACER` con la lista de fallos. Solo lo ACEPTADO cuenta como hecho.
3. Trabajar SOLO dentro de las rutas de salida del encargo; no ampliar alcance ni cambiar el diseno. Encargos pequenos y autocontenidos: leer solo las "Entradas".
4. Nada se declara "aprobado": el usuario revisa en Blender. No sobrescribir guiones del usuario ni la carpeta de otra IA; respaldar antes de tocar datos.
5. **NUNCA activar `zombie_N_animation_studio`** (copias mal renombradas que registran `ZMB1ST_*`/`scene.zmb1st` y rompen zombie_1).
6. Blender: turnos. Escena tomada por: **Claude** (frame 1, zombies 1-5 importados con la version actual). Codex no la toca.

## 2. ESTADO ACTUAL (fuente de verdad)
Escena `capitulos/capitulo_4/base.blend`, frames 1-860. Personajes animados: Alfred, Jerry, zombie_1..5 (todo sin aprobar por el usuario).
- Artefactos: `generador de animaciones/zombie_N/refinar/animaciones_ia/zombie_N_camina_acantilado/` (`.animacion.json`, `manifest.json`, `.py`).
- **zombie_1**: ruta del usuario/IA original; ZOMBIE_ASIM; cae hacia f546 sobre la piedra en (-114.8,-117.5). Entrada INMUTABLE.
- **zombie_2** (hecho por Claude a mano, sin script): NORMAL, sin balanceo, retraso 45 frames (cae ~f591), aterriza en el agua en (-118.4,-119.0), luego baja 1.6 m al sur para no pisar a los caidos. Entrada INMUTABLE para Codex.
- **zombie_3, 4, 5** (pipeline en `docs/datos_zombies/`, ver seccion 4): todos caminata NORMAL (frente, brazos al frente, espalda recta) con fase distinta (6/13/3), retrasos 97/120/155, esperan en el BORDE del alcantilado y caen desde ahi:

| | borde (x,y) | cae (f) | aterriza (x,y) | destino final f860 | inicio marcha final |
|---|---|---|---|---|---|
| zombie_3 | (-112.0,-116.7) | 650 | (-112.5,-118.9) | (-109.6,-118.6) | f780 |
| zombie_4 | (-115.6,-116.7) | 673 | (-116.6,-119.2) | (-113.0,-121.7) | f800 |
| zombie_5 | (-113.4,-116.7) | 708 | (-114.4,-119.1) | (-111.4,-120.0) | f830 |

Otros actores (no tocar): Alfred espera en (-115.4,-119.75) hasta ~f650 y nada al este por y=-120.3 (0.058 m/f); Jerry en (-112.5,-119.5) hasta ~f630 y nada por y=-119.2 (0.062 m/f); zombie_1 sale del agua hacia f680-700 y va por y~-120.2.

## 3. QUE HACER BIEN / QUE NO HACER (errores ya cometidos y corregidos)
**Datos del terreno (medidos por raycast)**
- Cima del alcantilado: tierra z=13 hasta y=-116.9 (x -117.5..-109.5). Debajo, un saliente de piedra z=8 hasta y~-118.3 y luego el agua (superficie 7.89, lecho z 7; 6 al sur; y limite sur ~-122). NO usar la vieja regla "piedra en x[-117,-114], y[-118,-117]": es incompleta.
- Arboles/troncos: `docs/datos_zombies/arboles_puntos.json` (195 puntos a <0.6 m de tronco u hojas, paso 0.5). La grilla vieja de 22 celdas NO incluia los troncos (`Oak_Log`, `Spruce_Log`). Medir siempre con rayos HORIZONTALES a la altura del cuerpo.
**Reglas de animacion**
1. **Si cambias x,y del root, vuelve a orientarlo** (`orientar_al_avanzar.py`): si no, el zombie camina de lado. Convencion del rig: delante = (-sin rz, cos rz), `rz = atan2(-vx, vy)`; giro maximo 0.09 rad/frame.
2. **La caida debe salir del borde real**: esperar en y~-116.7 y salir hacia delante ANTES de perder altura (avance horizontal = fraccion de caida elevada a 0.55) para librar el bloque de tierra y el saliente de piedra. Cae "como trapo mojado", sin salto. Penetracion maxima aceptable medida por raycast: <=0.25 m.
3. **No caer lejos**: aterrizar a 1.5-3 m del borde, no a 5-8 m. No caer cerca de Alfred (<1 m) ni sobre Jerry.
4. **Distancias**: antes de fijar un aterrizaje o carril, medir contra las trayectorias reales de Jerry, Alfred y los demas zombies por frame (rejilla de candidatos). Objetivo >=1.2 m entre pares (minimos actuales: z1-z3 1.1, z3-Alfred 1.26, z3-Jerry 1.4). El canal es estrecho (y -118.3..-122): si no hay hueco, cambiar el TIEMPO de la caida en vez del lugar.
5. **Caminata NORMAL sin balanceo**: el balanceo lateral sale de `Hips.location.x` (ZOMBIE_ASIM lo heredaba). Anular `Hips.location` y fijar el cuello a la media en marcha. Cada zombie con fase de ciclo distinta (no sincronizar) y cadencia/retraso propios.
6. **Ojos rojos siempre**: `brillo_ojos` en el JSON (emision constante para camara) y, desde 2026-09-30, `ai_export._brillo` fija tambien `diffuse_color` (rojo en vista solida). Visibilidad siempre 0 y `Closed`=0.
7. Editar SOLO listas de longitud N (860); las escalares se convierten a lista antes de editar. Renombrado de sufijos `_zombie_2`->`_zombie_N`, salvo `Neck_zombie_1.001` que se llama asi en todos.
8. Tras cambiar un JSON hay que regenerar el `.py` y reimportar (`ai_export._plantilla_py`, `ai_export.importar(nombre, personaje=ai_export.zombie(n))`): lo hace el maestro en Blender.
9. Perdidas de tiempo evitables: `execute_blender_code` largo bloquea Blender (usar timers); cancelar la reproduccion antes de medir/capturar; `python` de Windows no entiende rutas de Git Bash (`/tmp`, `/c/...`): usar rutas de Windows dentro de Python.

## 4. Pipeline vigente de zombie_3..5 (solo Python estandar, sin bpy; desde `generador de animaciones`)
1. `python alfred/refinar/docs/datos_zombies/derivar_zombie.py` — deriva de `z2_antes_estilos.animacion.json` + `estilos_zombie2.json` (NORMAL con fase por zombie, retraso, carril, caida, orientacion inicial). Imprime FALLOS: son de reglas antiguas (>=4.5 m a Alfred, >=3 m entre aterrizajes, hueco entre caidas >=35); NO los "corrijas" moviendo los aterrizajes lejos. Los criterios vigentes son los de la seccion 3.
2. `python alfred/refinar/docs/datos_zombies/rutas_sin_arboles.py 3 4 5` — reemplaza la aproximacion por una ruta A* sin arboles hasta el BORDE (tabla EDGE) y hace la caida desde el borde. Respalda `<nombre>.antes_arboles.json` (borrarlo antes de regenerar con `derivar_zombie.py`, si no parte de una version vieja).
3. `python alfred/refinar/docs/datos_zombies/orientar_al_avanzar.py 3 4 5` — orienta el root; respalda `<nombre>.antes_rumbo.json` (parte siempre de el).
Los tres scripts son idempotentes si se borran los respaldos `.antes_*.json` al regenerar desde cero.

## 5. ENCARGOS
- **E1 — zombie_3..5**: ACEPTADO (version actual, con las correcciones del maestro). Codex NO debe rehacerlo ni regenerarlo salvo nuevo encargo.
- **E2 — Renombrar bien los add-ons `zombie_2..5_animation_studio`** (clases `ZMB2ST_*`..., `scene.zmb2st`..., que no choquen con zombie_1): LIBRE. Esclavo: hacerlo sobre COPIAS en `zombie_N/refinar/zombie_N_animation_studio_renombrado/`, sin tocar los originales ni el add-on de Alfred/zombie_1, y sin instalarlos ni activarlos en Blender. Aceptacion: `grep` sin `ZMB1ST`/`zmb1st` en cada copia y todas las clases/propiedades con su propio prefijo unico; `python -m py_compile` de cada archivo.
- **E3 — `verificar_ia.py`** (comprobador): LIBRE. Debe leer los `.animacion.json` de zombie_1..5 y comprobar: longitudes N, saltos de hueso (>0.35 rad/frame fuera de la ventana de caida), paso del root (<0.5 m/f), distancias entre pares (>=1.0 m), rumbo vs velocidad (desvio <34 grados donde hay avance >0.03 m/f), distancia a puntos de arbol (`arboles_puntos.json`), `brillo_ojos` presente. Salida: informe legible. Entradas: seccion 3.
- **E4 (idea, sin abrir)**: separar a zombie_2 y zombie_3 al inicio (0.76 m en f21) y a zombie_4/5 (1.1 m en f1).

## 6. Pendiente de revision del usuario / limitaciones conocidas
- Nada esta aprobado; el usuario revisa en el visor. Reportes mas recientes del usuario: caminaban de lado (corregido), atravesaban arboles (corregido), caian lejos (corregido), atravesaban tierra al caer (corregido), zombie_3 sobre Jerry (corregido).
- Distancias minimas aun justas: z1-z2 1.09 (f846), z1-z3 1.1 (f728), z2-z3 0.76 (f21), z4-z5 1.1 (f1); zombie_2 roza una copa de hojas al caer (f586).
- Saltos de pierna ~0.3-0.38 rad/frame al retomar la marcha tras levantarse (zombie_5 f~780).

## 7. Registro (nuevo; el anterior esta en `TABLERO_HISTORIAL.md` si existe)
- 2026-09-29 Codex: E1 entregado y reentregado (derivar_zombie.py y JSON de zombie_3..5); ver secciones 4-5.
- 2026-09-29/30 Claude (maestro): E1 ACEPTADO tras correcciones propias: NORMAL para 3-5, rutas sin arboles, orientacion, aterrizajes cerca del borde, caida desde el borde real, ojos rojos en vista solida, zombie_3 reubicado por Jerry (retraso 97, aterrizaje (-112.5,-118.9)).
- (anadir aqui una linea por tarea: fecha, dueno, resultado)

## 8. Conexion con Blender (solo el maestro, salvo que se cambie el turno)
Add-on MCP v1.0.3, socket `localhost:9876` (`{"type":"execute","code":...,"strict_json":true}` terminado en NUL). Cliente de terminal: `docs/blender_ejecutar.py` (el codigo debe hacer `import bpy` y dejar `result = {...}`). Codex no lo usa mientras rija el protocolo maestro/esclavo.

## Regla de animacion (usuario, 2026-09-30)
Transiciones expresivas (sustos, risas, golpes, reacciones) -> **Elastic In-Out** (`ELASTIC_IN_OUT`; en scripts `ela()/epulse()` de `docs/parte2/compose_parte2.py`). Suaves (caminar, respirar, descansar) -> smoothstep. Ver GUIA_ANIMACION_ALFRED.md.
