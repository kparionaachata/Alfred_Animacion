---
name: video-bonobos-tala
description: "Video \"Alfred tala arboles, los bonobos le lanzan cosas\" en base_tarde con las ranas.blend: guion, scripts bonobos_madera_*.py y como regenerar"
metadata:
  node_type: memory
  type: project
  originSessionId: 22c3d667-c653-48cb-ab35-244ae3a40749
  modified: 2026-10-29T18:44:24.070Z
---

Guion del usuario (2026-10-29): al acercarse la noche Alfred va a talar arboles; en las copas hay familias de bonobos que le lanzan objetos de los arboles (manzana, palo, panal, cacao, bayas; de objetos/vanilla); Alfred los amenaza, sigue talando y les devuelve lo del suelo (pedernal, rata_1, pollo); los bonobos saltan de copa en copa; al final le lanzan snake_plains que se le clava en un brazo; Alfred levanta el puno y se desmaya lentamente.

Escena viva: `capitulos/capitulo_4/base_tarde con las ranas.blend` (NO guardada por mi). Alfred en (-74.5,32.5,12) -> arbol 1 (-79,33), arbol 2 (-78.5,30); copas: z25 en x-81..-77,y31..35; z23 anillo; z21 en x-80..-75,y37..41 (T3).
Scripts en `capitulos/capitulo_4/`: `bonobos_madera_lib.py` (apuntar=FK por direccion; OJO: fijar pb.scale=(1,1,1) o se deforman los brazos), `_alfred.py` (poses y guion de Alfred; frames en scene['bm_G']), `_bonobos.py`, `_escena.py` (clones de bonobos A1-A7,B1-B3 en coleccion bonobos_madera), `_main.py` (`armar()`, ~2 min: el MCP da timeout pero Blender termina; comprobar scene['bm_listo']), `_camaras.py` (`armar_camaras()`, camaras bm_cam_* + marcadores), `_foto.py` (hoja de contacto Workbench). Duracion 1-1533 f (24 fps).
**Gotchas:** el rig de Alfred importado esta en T-pose: las poses se dan con apuntar(), no con los clips de la biblioteca (que se vieron raros); no usar viewport render con la escena completa sin camara despejada (sale negro); PIL no existe dentro de Blender (juntar hojas con python del sistema).
**Pendiente / no verificado:** orientacion de rata y pollo, colmillos de la serpiente, sonido, clima de noche, pulido de poses.
Ver [[biblioteca-animaciones-alfred]].

**Caminar por defecto de Alfred (decision del usuario, 2026-10-29):** la animacion `Alfred camina por terreno llano` = `codigos de animacion/alfred/slot_1_caminar_llanura_animated.py` (ciclo 24.75 f, 1 m por paso, brazos X=90deg + swing, codos Z, ubica los brazos con location). En `bonobos_madera_alfred.py` esta implementada como `pose_caminar()`/`caminar()` importando ese modulo; usarla siempre que Alfred camine (no los clips slot_001_caminar_*).

**Cortar madera (decision del usuario, 2026-10-29):** usar `codigos de animacion/alfred/01_pica_el_bloque_de_hierro_cueva3_alfred.py` (golpes en f12/28/44/60 del clip, 1 cada 16 f; = Downloads/pica el bloque de hierro.py) cambiando SOLO el pico de piedra por `stone_axe`. En `bonobos_madera_alfred.py`: `tala(f0,pos,yaw,golpes,parcial)` reproduce huesos+root del clip y keyea el hacha con la transformacion de mundo del pico (`stone_pickaxe` es tipo 'mundo', item plano) @ `_cfix_hacha()`; el Child Of 'Mano' del hacha baja a influencia 0 durante el clip. Resultado ~1447 f (con caminar llano + esta tala); los frames fijos de los bonobos ahora cuelgan de G.

**Bonobos dispersos (2026-10-29):** los monos ya no estan en la copa grande (las hojas tapaban la vista); estan en copas con linea de vista limpia a Alfred, calculada con rayos (ray_cast iterando para saltar los objetos propios: el primer hit de un bonobo ocultaba las hojas de detras). Casas: A1 (-76.5,37.5,21) A2 (-88.5,34.5,21) A3 (-73.5,20.5,18) A4 (-88.5,36.5,23) A5 (-74.5,36.5,18) A6 (-84.5,23.5,18) A7 (-71.5,19.5,20, lanza la serpiente) B1 (-70.5,21.5,18) B2 (-72.5,22.5,18) B3 (-84.5,36.5,19); en scene['bm_homes']. Validos para C1 y C2 tambien: (-88.5,34.5..36.5), (-76.5,36.5..37.5), (-73.5..-70.5,18..22), (-66.5,42.5,21). Lanzamiento nuevo `lanza_bonobo(..., pos)`: mira, gira el torso, apunta segun distancia/altura, saltito; vigilancia aleatoria entre acciones; `desenrollar()` evita giros de 360. Para render con marcadores de camara hay que quitar m.camera temporalmente (foto.hoja lo hace).

## Arboles talables (30 oct)
Los robles T1 (celda -80,32) y T2 (-78,29) que talla Alfred se sacaron de las mallas del mundo (Oak_Log/Oak_Leaves, respaldo `<nombre>_orig_arboles`) y se rehicieron con bloques (`bloques_dinamicos/bloque_de_roble.blend` + cubo con material `oak_leaves`) en la coleccion `arboles_talables`. `capitulos/capitulo_4/arboles_talables.py` -> `talar_arboles()` (idempotente, lee `scene['bm_G']`): grietas destroy_stage por hachazo, astillas con gravedad, T1 se rompe en el 5o hachazo (f545) y cae (pendulo, rebote); T2 solo se agrieta. Si cambian los frames de los hachazos de Alfred hay que volver a ejecutar `talar_arboles()`. Gotcha: `view_layer.update()` antes de `matrix_world.inverted()` al emparentar.

## Hacha en la mano y arboles (30 oct, tarde)
- Arboles NO caen (Minecraft): al romperse T1 queda el tronco de arriba y las hojas en su sitio. Ruptura progresiva continua destroy_stage 0-9 (`_progreso`/`_grietas` en arboles_talables.py; cubo de grieta con UV 0..1 explicitos, si no la textura sale mal).
- Hacha: la malla del antebrazo acaba 0.33 antes que la cola del hueso Rightelbow_alfred; la mano real = `HACHA_MANO` (0.04,0.35,0) en espacio del hueso; punto de agarre del mango `HACHA_AGARRE`; `ajustar_agarre_hacha()` al final de armar(). Alfred se planta en C1=(-77.44,33.16), C2=(-76.84,30.39).
- armar() ahora limpia las claves del hacha (`animation_data_clear`): las viejas de corridas anteriores se mezclaban. Despues de armar: re-silenciar monos (mute+lock fcurves de bonobo_*) y `talar_arboles()`.
- Previsualizar con render EEVEE propio: guardar/restaurar engine, media_type, hide_render en try/finally (el estado original: engine CYCLES, res 360 en el .blend).
- Skill sistema-recorrido aplicada (30 oct): los caminares son cadenas de puntos a 1 bloque con `caminar_ruta` (valida pasos y Z igual). A0=(-74.5,32.5) -> C1=(-77.5,32.5) (tronco 1) -> RS=(-76.5,32.5) -> C2=(-75.5,29.5) (tronco 2, cara este, yaw 90). Los hachazos de T2 pasaron a f983/f999.
- Grietas con el color de la madera (marron oscuro de corteza via ColorRamp, material `arb_grieta_m_N`).
