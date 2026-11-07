# Continuar desde aqui (actualizado el 2026-11-07)

## NOVEDADES 2026-11-01 -> 2026-11-07 (LEER PRIMERO: punto exacto donde se quedo)
- **Al retomar con otra cuenta:** los mismos pasos de siempre (ver la seccion siguiente): `git pull`, copiar `.claude/skills/*` a `~/.claude/skills/`, copiar `refinar/docs/memoria/*.md` a la memoria de Claude de la cuenta nueva (incluye las memorias nuevas `reference_dos_blender_puertos.md`, `feedback_rapido_y_verificado.md`, `project_ranas_y_hierro_2026-11.md`), instalar los add-ons de `generador de animaciones/{alfred,jerry,rat_1,chicken_1,cerdo_1}/refinar/<personaje>_animation_studio/`. Los .blend siguen fuera del repo.
- **Dos Blender a la vez:** el de trabajo va con el add-on MCP en el **puerto 9877** (Auto Start apagado: el usuario lo arranca). Cliente directo: `capitulos/capitulo_4/scripts_2026-11_ranas_y_hierro/b9877.py` (`python -I b9877.py script.py`, el script deja un dict en `result`). Tambien se creo la entrada MCP de usuario `blender_9877` (hay que crearla de nuevo en la otra cuenta: `claude mcp add -s user blender_9877 -e BLENDER_MCP_PORT=9877 -- "<carpeta de la extension Blender>\.venv\Scriptslender-mcp.exe"`).
- **Forma de trabajar (muy importante, el usuario se enojo):** usar los valores que da en capturas TAL CUAL, una pasada, verificar con medida + render de cerca y reportar corto. Nada de iterar minutos a ciegas. Ver `memoria/feedback_rapido_y_verificado.md`.

### 1. `capitulos/capitulo_4/base_tarde con las ranas_1.blend` (1-990, 24 fps) - casi terminado, sin aprobar
- Dialogo Alfred/Jerry con voces y rostros (`voces_alfred/`, `voces_jerry/`; pistas `VozSync_*`, ducking -5 dB con `ducking_voces.py`, DUCK=0.56). Alfred mira a Jerry cuando le habla. Ultimas voces: Alfred tapado en el hoyo 548-615 (vol 12, filtro ffmpeg), Jerry "no me parece muy comodo" 625-653, Alfred frase 6 tapada 640-706 y libre 706-808, frase 7 780-849, frase 8 897-970.
- Crafteo de la pala; Alfred cava y se queda en el fondo del hoyo 500-700 (remapeo global +90 frames desde f610, guardado en `scene["remap_hoyo"]`), trepa ~717-770 con los insectos, se sacude, cae ~885 y forcejea en el suelo (pistas `Alfred_forcejea_suelo`, `Alfred_toca_suelo`, `Alfred_picoteado`), ojos de dolor (shape key `Dolor` en `ojo_*_alfred`). Cabeza/capucha rigida (pesos corregidos; respaldo `alfred_cabeza_pesos_respaldo.json`).
- Pollo de relleno (`chicken_1`) + `chicken_2`/`chicken_3`: corren (PERSEGUIDO), saltan sobre Alfred, picotean con aleteo ADD encima, rebotan con fisica, plumas (`plumas_pollos`), cacareos desesperados (`sonidos_pollos_desesperados/`). Insectos que se quedan pegados a Alfred (`insectos_quedan.py`).
- Cerdo `cerdo_1` con `recorrido_cerdo_extendido.json`, pasos y grunidos. Pasto que se aplasta (modificador GN `Pasto_aplastado`; las mallas de pasto estan rotadas 90 grados en X: la vertical es la Y local).
- Jerry: se echa (pose de biblioteca `hechado_boca_abajo_mirar_adelante` + spine_1 y Z del empty que dio el usuario) mirando el hoyo, sigue a Alfred con la mirada (`Jerry_sigue_alfred`), camina 790-911, se sienta y niega con la cabeza 935-980; filtros organicos en toda la animacion; parpadeos arreglados (forma `Closed` de los ojos rehecha + pupilas).
- Scripts (orden de dependencias): `scripts_2026-11_ranas_y_hierro/sesion_9fac7356/` (`pollos_alfred.py` -> `pollos_aleteo_encima.py` -> `alfred_suelo_pollos_rebotan.py` -> `pollos_alfred_reaccion_sonidos.py` -> `pollos_desesperados.py` -> `insectos_quedan.py` -> `plumas_pollos.py`; Jerry: `jerry_se_acerca_resignado.py`, `jerry_organicos_toda.py`, `jerry_echado_mira_hoyo.py`, `jerry_sigue_alfred.py`; render: `renderizado/renderizar_dlss.bat`). Los datos de los pollos viven en `bpy.app.driver_namespace["_pollos_alfred_logs"]` (se pierden al reiniciar Blender: reconstruirlos desde las pistas `Slot_*` como en la sesion 93ef65a7).

### 2. `capitulos/capitulo_4/alfred_buscando_hierro.blend` (1-135) - EN CURSO, NO aprobado
- El f440 original se congelo como f1 (sin animaciones ni sonidos previos), se borraron los carbones del suelo y se pusieron 3 carbones en el hueco del combustible del `horno`.
- Alfred empuja los carbones con la pala (`stone_shovel`, Child Of `Mano` en influencia 0: la pala va en el mundo) usando las dos manos; brazo derecho en la pose de empuje del usuario (RightUpArm 451.118/122.901/406.415, Rightelbow 64.422/-21.81/-92.722), torso girado para apuntar a cada carbon. Despues descansa con la pala en la mano derecha (RightUpArm 58.2956/-8.5636/-19.6531, Rightelbow -6.6013/16.83/-38.8683, pala con los valores de la skill) y se seca el sudor con la izquierda. Se recorto para que el f16 sea el f1 (contactos en 15/42/68, descanso 75-135).
- **Pendiente/defectos conocidos:** en el empuje la punta de la pala quedaba ~10 cm por debajo del piso del hueco (z -9.938) y la mano izquierda se separa del mango hasta ~13 cm en el empuje del 1er carbon. El usuario no lo dio por bueno: preguntarle antes de tocarlo.
- Scripts: `scripts_2026-11_ranas_y_hierro/sesion_9fac7356/` (`alfred_pala_dos_manos.py`, `empuje_pose_usuario.py`, `descanso_sudor.py`, `brazo_der_sostiene.py`, `recorte16.py`, `fijar_f440_como_f1.py`).

### 3. Render
- `renderizado/renderizar_dlss.bat` (DLSS por comando, 1-990 de las ranas, upscale BALANCED ~1.6-2.5 s/frame) y `unir_video.bat`. Se quito todo lo de RIFE/render hibrido. `renderizar_animacion_png_actualizado.bat` = Cycles normal (corregido para Blender 5.3: pasar la salida de video a imagen antes de PNG).
- Chats de esta etapa: `chats/LEEME.md` (seccion 2026-11-01 a 2026-11-07); la sesion principal de Alfred/Jerry es `chat_2026-11-05_9fac7356` y su continuacion `chat_2026-11-07_93ef65a7`.

---

## NOVEDADES 2026-10-24 -> 2026-11-01 (leer primero)
- **Al retomar con otra cuenta:** (1) `git pull`; (2) copiar `.claude/skills/*` del repositorio a `~/.claude/skills/` (CLAUDE.md las exige: desplazamiento A->B de Alfred/Jerry/rat_1/chicken_1, sistema-recorrido, inercia-accion-reaccion, herramienta-mano-derecha, bloque-roto-drop, lanzador-mira-objetivo, recursos-animacion); (3) copiar `refinar/docs/memoria/*.md` a la carpeta de memoria de Claude de esa cuenta (reglas del usuario); (4) instalar los add-ons desde `generador de animaciones/{alfred,jerry,rat_1,chicken_1}/refinar/<personaje>_animation_studio/` (solo texto: .py/.json); (5) los .blend, audios e imagenes NO estan en el repositorio: hay que copiarlos aparte (carpeta del proyecto en el otro PC).
- **Capitulo 4, cuevas 5B-5E:** scripts nuevos en `capitulos/capitulo_4/` (`crear_cueva_5B/5C/5D.py`, `crear_base_cueva_5E.py`, `stalker_*.py` incl. trepa de pared, `slimes_caverna.py`, `criaturas_caverna.py`, `zombies_cruzan_camino.py`, camaras `camara_*`, flashback `flashback_*.py`). Detalle en `refinar/docs/memoria/project_trepa_pared_5E.md` y los chats de 10-25 a 10-28.
- **Video "Alfred tala arboles y los bonobos le lanzan cosas"** (escena `capitulos/capitulo_4/base_tarde con las ranas.blend`, 24 fps, 1-1453): guion y gotchas en `refinar/docs/memoria/project_video_bonobos_tala.md`; scripts `bonobos_madera_*.py`, `arboles_talables.py`; scripts de trabajo de la ultima sesion (lanzar objetos con trayectoria real, monos que se rascan/miran, cuello de Alfred que mira a los monos, hueco de animaciones) en `capitulos/capitulo_4/bonobos_madera_scratch/` (`lanzar.py`, `hueco.py`, `rascar.py`, `rascar_run.py`, `mirada_alfred.py`, `intercambio.py`...). Los lanzamientos llevan +20 frames por un remapeo global (ver `project_lanzamientos_mas_lentos.md`). Mordida de la serpiente: el mouth de `snake_plains` sigue al antebrazo izquierdo de Alfred desde f1218 (claves enteras de `location` y mandibulas en `mesh_root_snake_plains`).
- **`base_tarde con las ranas_1.blend`** (2026-11-01, no esta en el repo): estado del ultimo frame (f1453) como frame 1, sin animaciones, SIN Alfred, monos, pollo, serpiente, rata ni props de la historia (colección `bonobos_madera`), arboles devueltos a superficies del mundo (`Oak_Log`/`Oak_Leaves` originales); solo quedan las ranas, fogatas, antorchas, mundo y camara. Se hizo en segundo plano con una copia de `alfred/refinar/docs/parte10/crear_base_parte_10.py` (mismo metodo que las bases anteriores).
- **Reglas nuevas del usuario** (ver `refinar/docs/memoria/`): movimientos rapidos (nada lento), fisica real en todo objeto lanzado/golpeado, el que lanza mira al objetivo, Alfred mira hacia arriba a los monos al interactuar, herramienta en mano derecha con transformacion fija, bloque roto = item que gira y se absorbe, no tocar los monos cuando se pide solo Alfred, no pedir guardar ni responder avisos automaticos.
- Chats completos de esta etapa: ver `chats/LEEME.md` (seccion 2026-10-24 a 2026-11-01).

---

## Estado detallado al 2026-10-24 (cueva_5A)

> Esta guia es de Alfred y Jerry. El proyecto en paralelo, La Delgada Linea Roja, tiene la suya: `capitulos/delgada_linea_roja/CONTINUAR_AQUI.md`.

Leer esto primero al retomar el proyecto con otra cuenta de Claude. Despues: `refinar/docs/addons_sincronizacion_audio_animacion.md`
(detalle del capitulo 4 en cueva_2 / cueva_5) y `refinar/docs/memoria/` (preferencias y reglas del usuario, copia de la memoria de Claude).
Chats completos en `chats/` (zip con el .jsonl, sin imagenes); el de esta etapa: `chats/chat_2026-10-24_f52e92f4.zip`.

## Como se trabaja
- Raiz: `C:\Users\user\Desktop\Alfred_Animacion\`. Blender 5.2.1 abierto por el usuario y controlado por el MCP de Blender
  (`execute_blender_code`). Los .blend, audios e imagenes NO estan en el repositorio (solo scripts .py/.json/.md/.txt).
- Cada animacion es un script en `capitulos/capitulo_4/` que se ejecuta en la escena abierta:
  `ns={}; exec(open(ruta, encoding="utf8").read(), ns); ns["construir"]()`. Son repetibles (borran lo que crearon antes).
- Los hornos largos dan "timeout" del MCP (~120 s) pero TERMINAN: guardar el resultado en un texto de Blender
  (`bpy.data.texts["res_..."]`) y leerlo despues.
- Reglas del usuario (importantes): obedecer, respuestas cortas y en espanol, no hacer trabajo no pedido, NO marcar animaciones
  como aprobadas, NO tocar las mallas de los ojos salvo que lo pida, NO mover la camara, trabajar SOBRE el archivo que el usuario
  nombra (nunca copias), pedir autorizacion antes de abrir/bloquear Blender, sustos/risas/golpes con ELASTIC_IN_OUT.
- Utilidades comunes: `alfred_cae_estalagmita.py` (Rig por direcciones de hueso de Alfred: `Rig`, `pose_torso`, `piernas`,
  `resolver_con_brazos` con IK, `matriz_pico`, `poner_matriz`, `ORDEN`, `L_ANTEBRAZO`), `efecto_romper_bloque.py`
  (`romper(bloque, golpes, contacto)`: grietas destroy_stage y particulas), add-on `alfred_sonidos` (sonidos del juego como tiras
  `SND_*` con etiqueta `mcsnd_origen`; `scene.use_audio=True` = silenciado), `ojos_alfred_desde_script.py` y
  `jerry_responde_pensando.py` (aplican los scripts de voz/ojos de la app `estudio_audio_expresion` como capas NLA).
- Bloques: `bloque_<tipo>_<i>_<j>_<k>`, cubo 1x1x1 con origen abajo-centro. OJO: en `alfred_cueva_5A.blend` el tunel fue movido
  y los nombres ya NO coinciden con la posicion (usar `matrix_world`).

## Escenas y lo hecho en esta etapa (sesion f52e92f4)
### alfred_cueva_4.blend (capitulo 4)
- `jerry_pica_carbon.py`: Jerry pica 2 bloques de carbon con `jerry_pico` en la boca (agarre REL_PICO relativo a jaw_top, mandibulas
  JAW_TOP/JAW_BOT dadas por el usuario), 4 golpes en diagonal, patas en V, tira el pico, va al carbon, mira a Alfred, dice
  "Alfred, piensa rapido" (`jerry_piensa_rapido.py`, voces en `voces_piensa_rapido/`), lo lanza como un disco.
- `alfred_mete_carbon_horno.py`: Alfred mete carbones al horno; levanta la cabeza (pose `alfred_parado_mirando_pose.json` + cuello
  buscando), recibe el carbon en la cara, choca con la estalagmita, suelta los carbones y queda sentado
  (`alfred_sentado_despues_golpe_pose.json`).
- `alfred_aturdido_jerry_piensa.py`: ojos de Alfred cerrados 80 frames; Jerry pata a la cabeza (`jerry_pata_cabeza_pose.json`) y
  dice "creo que me pase" (sin el "Uy").
- `alfred_se_levanta.py`: se levanta despacio diciendo "Ay, pero que pendejo que eres" (`voces_alfred/`).
### alfred_cueva_5.blend
- `tunel_cueva5.py`: tunel 1x2 picado desde (-98.5,-26.5,-11) hacia -Y, baja 7 bloques en escalera y sigue recto (58 bloques),
  vetas de carbon/cobre, 10 diorita, antorchas de pared enterradas, hueco final 1x3.
- `stalker_arana_tunel.py`: el Stalker sale de la oscuridad (60 frames apagado), se contorsiona como Samara (El Aro) y avanza
  30 bloques como arana erguido apagando antorchas. (Otra sesion hizo despues `stalker_tunel_gatear.py`.)
### estructura_lista/the_stalker_1.blend (personaje)
- Un solo armature `torso_1` con huesos de nombre humano (root, spine, chest, neck, head, jaw, thigh/shin, upper_arm/forearm,
  finger_1..3/thumb .L/.R, neck_front).
- `estructura_lista/stalker_aspecto.py`: aspecto (placas oscuras, vetas rojas, ojos que brillan solo por su malla, pecho reventado
  en elipse asimetrica con paredes-tentaculo animadas (`chest_tent_*`), corazon = luz roja que late (~70 lpm), puntos rojos que
  parpadean cada uno a su ritmo (la mitad en el pecho), franjas rojas de la textura que brillan, dientes con hueso propio
  `tooth_up_*`/`tooth_low_*`, dedos con huesos `tent_*` (quietos)).
### alfred_cueva_5A.blend (ULTIMA ESCENA DE TRABAJO)
- Caverna 200x200x90 SOLO superficies: `caverna_superficies.py` (coleccion `caverna_superficies`; CENTRO alineado a la rejilla del
  tunel (-0.0471, 0.3381, 0.0157); 2 lagos de lava con luz desde la superficie hacia arriba; 4 cascadas de lava en cubos con bloque
  fuente hundido + diagonal, alturas distintas, brillo/luz distintos por cascada; luces de area sin rebotes para que el techo y el
  centro queden oscuros; `CONEXIONES` abre la salida del tunel en (0.5, 82.5, 66)).
- Add-on reutilizable: `generador_cavernas_superficies.py` (View3D > N > "Cavernas": tamano, semilla, pilares, puntas, lagos,
  cascadas, brillos, camara, Generar/Borrar). Aun NO tiene la opcion de abrir conexion con un tunel.
- `alfred_mira_caverna.py` (Alfred, 30% mas rapido con `VELOCIDAD=0.7`): pica 2 bloques del tapon (4 golpes c/u, 1-86), camina
  normal con el pico en la mano derecha (87-145, ciclo `alfred_caminar_6_realistic.py`), pone una antorcha en la cara del bloque
  (-0.55, 84.34) a Z 67.1656 (146-180, `antorcha_alfred_salida`), mira la caverna y se sorprende (180-247), se arrodilla con
  `alfred_arrodillarse_1_mixamo.py` (253-287). Hombros con offsets de `alfred_parado_2_mixamo.py`, piernas abiertas de
  `alfred_parado_manos_cintura.py`. El techo de 2 celdas del tunel se subio a 3 m.
- Sonidos de Alfred (picar, pasos, antorcha, rodillas): etiqueta `mcsnd_origen="alfred_salida"`.
- `jerry_llega_salida.py`: desde el frame 180 Jerry llega por el tunel con `jerry_pico` en la boca (ciclo `jerry_caminar_rapido.py`),
  hasta su sitio (-0.549, 84.775) y deja el pico delante (suelto en 306). OJO: su parte trasera queda dentro de la roca.
- The Stalker parado (sin caminar) en (42.45, -53.16, 6.02) desde el frame 1, brillando desde el frame 1.
- Antorchas del tunel encendidas siempre (se quito el apagado del Stalker) + 3 nuevas `antorcha_tunel5_salida_*`.

## Pendiente / ideas que quedaron abiertas
- Sonidos de Jerry en `alfred_cueva_5A` (pasos, soltar el pico) no puestos.
- Jerry en `alfred_cueva_5A`: la parte trasera atraviesa la roca (ofrecido adelantarlo o abrir hueco).
- Alfred: al poner la antorcha la mano queda ~25 cm corta (ofrecido un paso hacia el bloque).
- Add-on de cavernas: falta la opcion "abrir conexion con tunel".
- El mundo antiguo del origen (`minecraft_world_ecenario_2`) queda dentro de la caverna (se ve en render).
- Nada esta aprobado por el usuario: todo sigue "pendiente de aprobacion".
