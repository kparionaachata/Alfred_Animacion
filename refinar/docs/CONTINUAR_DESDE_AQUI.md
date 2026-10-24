# Continuar desde aqui (estado al 2026-10-24)

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
