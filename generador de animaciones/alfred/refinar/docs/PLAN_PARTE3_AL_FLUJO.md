# Plan: llevar la animacion de Alfred (parte 3) al flujo del estudio y resumirla en un guion `.json`

Fecha: 2026-10-04. Estado: **Fases 0, 1, 2, 3, 5 y 6 HECHAS; Fase 4 EN CURSO: S01 y S02 migrados y APROBADOS, S03 migrado (sin aprobar); S04-S14 todavia salen de la referencia numerica** (modulo `alfred_animation_studio/guion_v2.py`, pruebas `pruebas/test_guion_v2.py`, guion inicial `configuraciones/alfred_parte3_guion_v2.json`); audio: `audio_import.py` + `audio_ops.py` (importar, sincronizar, panel 6) y pruebas `pruebas/test_audio_import.py`; objetos y mundo: `objetos_mundo.py` + `objetos_ops.py` (panel 7) y `pruebas/test_objetos_mundo.py`; Fase 4: `motor_alfred.py` + `movimiento_ops.py` (panel 8), referencia `datos_guion/base_referencia_alfred.json`, tramos S01 (f1-52) y S02 (f53-190); Fase 5: `sonidos_guion.py`, `camara_guion.py`, `claves_util.py`, `escena_ops.py` (panel 9) y `pruebas/test_escena_guion.py`; el resto del plan sigue pendiente de la aprobacion de Kebyn. Alcance de esta primera etapa: **solo Alfred**. Jerry, zombies y camara
quedan como "escena" que Alfred necesita (ver seccion 5); se migran en una etapa posterior con el mismo molde.

Objetivo final: un solo `guion_alfred_parte3.json` (receta editable, flujo MANUAL) que, cargado en el add-on, reconstruya TODO lo de Alfred: movimiento, poses, ojos,
objetos que saca / lanza / coloca, voces con su cara, sonidos y (como extension) la camara. Hoy eso lo hace `parte3/sentarse_en_refugio.py` (~1260 lineas, N=1160) +
scripts sueltos (Voz Sync, Sonidos MC, `camara_final_parte3.py`, `zombies_*`). El script actual **sigue siendo la referencia** hasta que cada tramo pase la comprobacion (seccion 4).

## 1. Que hay en el flujo y que falta (revision del codigo, `alfred_animation_studio` v1.9)

| Necesidad de la parte 3 | En el flujo hoy | Falta |
|---|---|---|
| Recorrido / segmentos con `action_poses` (poses con duracion e interpolacion), bloqueo de huesos, root libre o de la base | **Si** (Paso 3, `alfredseg.*`, `concatenate_all`) | Poses por *curvas* (inclinacion del torso, mirada del cuello, giros +90, "de pie" como peso) que yo hago por capas; solo hay poses discretas + osciladores |
| Tipos de segmento especiales | **Si**: CORTAR_MADERA x3, COLOCAR_ANTORCHA, COLOCAR_MESA_CRAFTEO, ARRODILLARSE_1, LEVANTARSE_1/2, CONVERSAR_1, GOLPE_ESTOMAGO_1, RESBALARSE_1, CREAR_PARED_NXN; `sentarse_1.py`, `slot_001_lanzar_objeto.py`, `slot_001_recojer.py` | Cavar, craftear en la mesa (rejilla con receta), guardar herramienta en la espalda, asomarse a mirar, girar +90 con pasitos |
| Filtros organicos (respiracion, balanceo, secundario, suavizado) | **Si** (`organic` por segmento y global) | Que el filtro respete los frames "exactos" (impactos) y se pueda excluir un hueso en un tramo |
| Ojos: expresiones por intervalo, parpadeo cortina | **Si** (`eye_sequence`, `expr_intervals`) | Que se combine sin pisarse con la capa de voz (hoy Voz Sync pone su propia capa aditiva en ojos / cuello) |
| Objetos: importar `.blend` y aparentarlos a un hueso (HOLD), lanzar / recoger con waypoints (THROW / CATCH), desaparecer mallas | **Si** (`object_imports`, `segments_throw`, `AlfredHideMeshSettings`) | Agarre **capturado del mundo** (matriz relativa a `Rightelbow_alfred` desde una posicion que el usuario da); salida / regreso a la espalda con el `rel_spine1` original; vuelo con rebote contra muro y caida sobre otro personaje (pegado a su hueso); aparecer con "pop" de escala; item que flota, gira y es **absorbido**; cambiar bloques del mundo (tapa de pasto oculta, pozo, bloque roto) |
| **Importar audios** | **No** | Todo: ver Fase 2 |
| **Sincronizar audio con ojos / cara / cuello** | **No** en el add-on. Existe el add-on aparte `alfred_voz_sync` (capas NLA `VozSync_*`, `.cara.json` / `.emocion.json`, `importar_script_alfred.py`, `analizar_audio.py`) | Integrarlo al guion: seccion `audio`, y que `concatenate_all` **no borre** (o vuelva a poner) las capas de voz |
| Sonidos de Minecraft (pasos, impactos, silbidos) | **No** en el add-on. Existe `alfred_sonidos` aparte (`colocar`, `sonorizar`, presets) | Seccion `sonidos` en el guion; reajuste automatico cuando se mueve el tiempo |
| Camara / foco | **No** | Seccion `camara` (claves de ubicacion, foco, lente) |
| IK / resolver poses de brazos para tocar objetos | **No** (solo `Extract/Import pose`) | `ik_brazos.py` como herramienta: "pose desde mano -> objetivo" y guardado como pose de la libreria |
| Tiempo relativo (insertar frames sin romper todo) | **No**: todo en frames absolutos | **Anclas**: eventos con `despues_de` / `desde` otro evento (ahora tengo que re-colocar sonidos y camara a mano cada vez que muevo la linea de tiempo) |
| Verificacion | `ai_api.medir`, `chequear_frames` | Comparacion automatica "guion vs script actual" (seccion 4) |

Lo que **no** conviene cambiar: el flujo manual (Pasos 1-3, `.json` en `configuraciones/`), la compatibilidad con guiones viejos (`version` 1.x se sigue leyendo) y la regla
"una animacion no esta aprobada sin tu confirmacion". Todo lo nuevo se agrega como secciones opcionales del `.json` y como modulos nuevos del add-on (sin reescribir lo existente).

## 2. Forma del guion nuevo (`version` 2.0, superset del actual)

Se conservan las claves actuales (`paso1_path`, `alfred_segs`, `organic`, `eye_sequence`, `object_imports`, `segments_throw`, ...) y se agregan:

```
anclas:      {nombre: frame}                       # puntos de referencia ("rompe_bloque": 1062); lo demas puede colgar de ellos
alfred_segs[i]:
   tipo:     "sentarse" | "lanzar_herramientas" | "craftear" | "cavar" | "cortar_madera" | "asomarse" | ...   # segmentos especiales (nuevos o ya existentes)
   inicio / fin: frame o  {ancla, delta}
   poses:    [{pose, duracion, interp, ...}]       # como hoy; poses nuevas con prefijo ia_parte3_ en poses/
   capas:    {inclinacion: [[frame, grados]...], cuello_y: [...], giro_yaw: [...], de_pie: [...]}   # curvas (nuevo)
   exactos:  {frames: [1026,1038,1050,1062], huesos: {...}}   # valores dados por el usuario que ningun filtro puede tocar (nuevo)
objetos:     [{nombre, blend, hueso, agarre(matriz relativa), espalda(rel_spine1), escala_mano, escala_espalda, eventos: [aparece|toma|guarda|lanza|rebota|absorbe|oculta ...]}]
mundo:       [{bloque, accion: "ocultar|crear_pozo|aparecer_item", frame/ancla}]            # cambios del escenario
audio:       [{archivo, inicio | ancla, emocion (opcional), texto (opcional), cara: ".cara.json", emocion_json}]   # voces (nuevo)
sonidos:     {modo: "auto", manuales: [{evento, frame | ancla, volumen}], techo_voces: true}
camara:      [{objeto, desde, hasta, destino:[x,y,z], interp}]  # incluye foco
```

Regla de oro: **el `.json` guarda decisiones (receta), no keyframes**; los keyframes se hornean al cargar. El resultado horneado se puede exportar aparte con `ai_export` (ya existe).

## 3. Orden de trabajo (cada fase termina con una comprobacion y una entrada en la guia; Alfred sigue "sin aprobar")

**Fase 0 — Linea base y red de seguridad** (1 sesion corta)
- Congelar la animacion actual como referencia: volcar por frame rotacion de los 22 huesos, root, escala, objetos de mano / espalda y claves de ojos en `parte3/base_referencia_alfred.json` (+ respaldo del `.py` y de los scripts auxiliares).
- Escribir `comparar_con_referencia()`: error maximo por hueso / root / objeto entre lo horneado por el flujo y la referencia. Criterio de paridad: hueso <= 1 grado, root <= 1 cm, objeto <= 2 cm (los **exactos** del usuario: 0).

**Fase 1 — Cimientos del guion v2**
- `guion_v2.py` (cargar / guardar / validar; lee v1; anclas -> frames absolutos; `exactos`).
- `capas` (curvas de torso, cuello, giro, de pie) aplicadas despues de las poses y antes del suavizado, con `exactos` por encima.
- Cargar un guion no debe dejar el escenario a medias: cada herramienta nueva es idempotente (re-ejecutable).

**Fase 2 — Herramientas de audio** (lo primero que pides; desbloquea 7 voces de Alfred y las de Jerry despues)
- `audio_import.py`: elegir un audio (+ opcional `animacion_alfred.py` de la app) -> copia a `audios/alfred/`, tiempos por palabra (`analizar_audio`), cara (`importar_script_alfred`), mapa emocion -> voz (incluye `curiosidad -> DUDA`, ya agregado), y lo registra en `audio[]` del guion con su inicio.
- Sincronizacion: llamar a Voz Sync (`aplicar_todos`) como paso final de "Cargar guion", **fijando `inicio` por clip** (hoy `refrescar` usa el frame actual: causa de un error real de hoy).
- Ojos / cara: definir quien manda en cada frame (voz o `expr_intervals`); la voz entra como capa aditiva y el segmento puede pedir "sin cara de voz".
- Panel "Audio" con lista, vista previa de la cara y boton "colocar en el frame actual / en el ancla".
- Comprobacion: las 7 voces de Alfred quedan en f50 / 206 / 358 / 430 / 632 / 664 / 1064 con la misma cara y cuello que ahora.

**Fase 3 — Objetos y mundo** (lo que pides: importar y tirar objetos)
- `agarre`: capturar la matriz relativa al hueso desde un objeto colocado a mano en una posicion de mundo (lo que hago hoy con `Rdig_` / `Rchop_` / `Rup_`).
- `espalda`: guardar el sitio de origen del objeto (`rel_spine1`) y volver a guardarlo en el mismo sitio.
- Tipos de evento de objeto que faltan: `aparece` (pop de escala), `absorbe` (flota, gira, se encoge hacia el pecho), `rebota` (muro) y `cae_sobre` (pegarse a un hueso de otro personaje), `mesa/rejilla` (celdas, recetas), `oculta`.
- `mundo`: bloque oculto / pozo / tapa de pasto / item que sale del bloque, como acciones del guion.
- Comprobacion: herramientas lanzadas, 6 slabs, pala, hacha, tierra, tablon: posiciones por frame <= 2 cm de la referencia.

**Fase 4 — Poses y movimiento de Alfred, en orden cronologico** (primero lo que ya existe en el flujo, despues lo que hay que crear)

| # | Tramo (frames aprox.) | Segmento del flujo | Estado |
|---|---|---|---|
| S01 | 1-60 acercarse y sentarse | `sentarse_1` + base | existe, ajustar |
| S02 | 60-190 sentado, duerme Jerry, mira antorcha | parado + filtros + cuello | existe |
| S03 | 190-270 lanza herramientas (pico, hachas) | `lanzar_objeto` (THROW) | existe, falta rebote / caida |
| S04 | 270-430 manos en la nuca, hablan | pose + voz f206 / f358 | pose nueva |
| S05 | 430-500 "Espera, tengo una idea", barre herramientas sobre Jerry | THROW + `cae_sobre` | nuevo evento |
| S06 | 502-548 de rodillas + antorcha en el muro | `arrodillarse_1` + `colocar_antorcha` | existe |
| S07 | 548-612 mesa de crafteo, sticks y piedra | `colocar_mesa_crafteo` + HOLD | existe + extension |
| S08 | 628-700 craftea la pala | `craftear` (rejilla / receta) | **nuevo** |
| S09 | 713-840 tablones, 6 slabs, barre 5 sobre Jerry | `craftear` + THROW | nuevo |
| S10 | 843-912 se levanta, saca pala, cava | `levantarse_1` + `cavar` | cavar **nuevo** |
| S11 | 912-962 cae al pozo, absorbe tierra, guarda pala y gira +90 | `absorbe` + `guarda_herramienta` + `giro` | nuevo |
| S12 | 984-1012 toma el hacha, gira +90 | HOLD + `giro` | nuevo |
| S13 | 1016-1062 corta el bloque (4 golpes, impacto exacto) | `cortar_madera` (**rehacer**: golpe por codo, torso atras, `exactos`) | mejorar |
| S14 | 1062-1160 guarda hacha, retrocede, habla, se asoma a mirar | `guarda_herramienta` + `asomarse` + voz f1064 | nuevo |

Por cada tramo: construir en el guion -> hornear con el flujo -> `comparar_con_referencia()` -> corregir -> anotar. Los tramos se aprueban uno a uno por ti (visualmente), no en bloque.

**Fase 5 — Sonidos y camara en el guion**
- `sonidos` (modo auto + manuales con ancla) y reajuste al mover tiempo; `camara` (claves de ubicacion / foco, incluidos los dos planos nuevos). Los zombies y su sonido quedan como script aparte hasta la etapa de personajes.

**Fase 6 — Guion final y cierre de Alfred**
- `guion_alfred_parte3.json` completo; cargar en escena limpia (`base_parte_3.blend`) y comprobar paridad de TODO el rango; export horneado opcional con `ai_export` para reproducir sin add-on.
- Documentar en `GUIA_ANIMACION_ALFRED.md` y en `FLUJO_DE_TRABAJO.md` (nuevas secciones del guion, herramientas de audio / objetos / sonidos / camara, limitaciones). Actualizar el add-on instalado en `%APPDATA%` (zip + `start_animation_studio.bat`).

**Etapa siguiente (no incluida):** Jerry (mismo molde con `jerry_animation_studio`; sus reacciones, voces y filtros), zombies y camara como personajes / actores del guion, y la escena de Jerry de la que Alfred depende hoy.

## 4. Como se comprueba (sin que tengas que revisar 1160 frames a mano)
1. `base_referencia_alfred.json` (Fase 0) = verdad numerica de hoy.
2. Cada fase corre `comparar_con_referencia()` y reporta frames y huesos fuera de tolerancia.
3. Capturas de frames clave (impactos, agarres, giros) y una lista corta para tu aprobacion visual por tramo.
4. Los valores que me diste (poses de BACK, agarre de pala / hacha, impacto, camara) se guardan como `exactos` y se verifican con tolerancia 0.

## 5. Dependencias de Alfred con otros personajes (en esta etapa se mantienen como estan)
- Jerry: sus huesos (`spine_3`) reciben herramientas y slabs lanzados; su voz, sus filtros y su reaccion siguen en `sentarse_en_refugio.py`.
- Zombies: `zombies_rondan_parte3.py` + `sonidos_zombies_parte3.py`.
- El guion de Alfred solo referencia estos objetos por nombre (`jerry:spine_3`), igual que hoy lo hace el script.

## 6. Riesgos y decisiones abiertas
- **Alcance del add-on instalado**: copiar los modulos nuevos a `%APPDATA%\...\alfred_animation_studio` y reinstalar; no rompe guiones v1.
- **Voz y filtros**: la capa de voz y los filtros organicos pueden duplicar movimiento de cabeza; hay que decidir la prioridad por segmento (propuesta: la voz manda en el cuello mientras habla).
- **Rendimiento**: hornear 1160 frames con IK / capas tarda; el guion se recorre por tramos (y se cachea la referencia).
- Decisiones para ti (abajo, en la respuesta): orden de las fases, si el tramo S13 se rehace como tipo nuevo, y si los sonidos / camara van dentro del guion de Alfred o en un guion de escena aparte.
