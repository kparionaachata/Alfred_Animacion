# Add-ons y scripts de sincronizacion (audio + animacion) - capitulo 4

Raiz: `C:\Users\user\Desktop\Alfred_Animacion\`. Escena de trabajo: `capitulos\capitulo_4\alfred_cueva_2.blend` (el usuario aun NO la ha guardado; respaldo: `alfred_cueva_2_respaldo_antes_superficies.blend`). Blender 5.2.1 via MCP (`execute_blender_code`; los hornos largos dan timeout a ~120 s pero terminan: comprobar con las propiedades personalizadas). Reglas del usuario: obedecer, respuestas breves, no marcar animaciones como aprobadas.

## Add-ons (carpeta `capitulos\capitulo_4\`)
| Add-on | Ruta | Funcion |
|---|---|---|
| Alfred Sonidos | `alfred_sonidos\__init__.py` (+README) | Pone sonidos de Minecraft como tiras `SND_<evento>_<frame>` en el editor de secuencias (`sc.mcsnd`, `colocar`, `rutas_de`, `indice`). Biblioteca: `Alfred_Animacion\sonidos\` (sounds.json). Etiqueta `mcsnd_origen` para borrar/regenerar por grupo. |
| Alfred Voz Sync | `alfred_voz_sync\__init__.py` (+README, `herramientas\`) | Voz/emocion/lipsync de los personajes. |
| Alfred Agua | `alfred_agua\__init__.py` (+README, zip) | Cascadas/agua de Minecraft (nivel 7, -1 por bloque, textura water_flow/still por frames). Ejemplo: celda (-49,-19). |
| Alfred Efectos | `alfred_efectos\__init__.py` (+README, zip) | Efectos de escena. |
| Recorridos | `recorrido\blender_path_bloques.py` (trazar sobre caras superiores de bloques, exporta .json), `blender_path_visual.py` | Genera rutas (`jerry_ruta_a.json`). |

## Scripts de animacion (se ejecutan con `exec(open(ruta,encoding="utf8").read())`)
Orden cronologico en la escena:
1. `alfred_cae_estalagmita.py` - Alfred pica, cae y se desliza (frames 1-242). Props en el empty `alfred`: f_imp, f_aterriza, f_tumba, f_fin.
   Sonidos: `alfred_cae_estalagmita_sonidos.py` (`sonorizar()`).
2. `alfred_levantarse.py` - se levanta (inicio 370, termina 552). Usa `animacion_alfred_levantarse_3.py` (Mixamo). Empty fijo; el hueso Hips compensa (`construir()` -> `hornear(info,datos)`). Prop `alfred["f_levanta"]`.
3. `alfred_coloca_antorcha.py` - agacha y planta la antorcha `antorcha_1_colocada` en (-44.5,-15.5,-9.0): mezcla 553-557, slot 558-587, antorcha aparece en 573. Datos: `animacion_alfred_colocar_antorcha.py`. `hornear()`. Props `alfred["f_antorcha"]`, `["f_antorcha_fin"]`.
4. `jerry_baja_agua.py` - toda la secuencia de Jerry: trote al borde (f_parada 370), salto F_BAJA=378, columna de agua, rebote, salida, secado, trote rapido por `jerry_ruta_a.json` hacia Alfred, lanza el balde (rebota a su derecha). `construir()` -> `hornear(info,datos)`; guarda `jerry["jerry_agua"]` (JSON con todos los frames).
   Constantes de sincronizacion: `F_BAJA`, `ESPERA_BORDE`, `DEMORA_RUTA`, `V_RUTA`, `CICLO_RUTA`, `F_ALFRED_DE_PIE=552`, `V_TROTE`. Regla: Jerry debe llegar a su ultimo punto DESPUES de f_antorcha_fin (587).
5. `sonidos_jerry_agua_levantarse.py` - `sonorizar()` agua, Jerry (sin pasos, por orden del usuario), Alfred levantandose, colocar antorcha. LEE `jerry["jerry_agua"]`, `alfred["f_levanta"]`, `alfred["f_antorcha"]`: re-ejecutarlo SIEMPRE tras rehornear Jerry o Alfred.
6. Otros: `hueco_agua_49_19.py` (hueco y cascada), `cueva_extremos_a_superficie.py`.

## Estado actual de tiempos (Jerry)
f_ini -49 (ya trota en el frame 1), f_parada 98, f_baja 106 (F_BAJA), f_choque 193, f_aterriza 210, f_borde 211, f_seco 253, f_ruta_ini 326, f_lanza 375, f_rel 383, f_golpe 386, f_fin 491 (antes todo 272 frames despues; la voz de Jerry de f659 y sus capas NLA siguen en su sitio; al rehornear guardar y restaurar las pistas NLA del rig). Agua cae del 80 al 180 (antes 150-250).

## Gotchas
- Mantener Alfred/Jerry/cubo/herramientas/antorcha dentro de la coleccion `luz_entrada_receptores` (light linking de `luz_entrada_cueva`); si no, se ven oscuros. Esa coleccion NO esta en la view layer: enlazar los objetos tambien a la Scene Collection.
- Bloques: `bloque_<tipo>_<i>_<j>_<k>`, origen abajo-centro, cara superior z=k+1. El bloque diorita (-45,-15) tiene k=-10 (top z=-9).
- Alfred: nunca mover el empty `alfred` en el levantarse/antorcha (el usuario lo exige); el desplazamiento va en Hips.
- Pase de Python: usar rutas con `/` o `r""` en parches; no borrar bloques de funciones con `index('# ====')`.

## Cambios del 21 de octubre (Alfred tirado 30 frames)
Alfred queda boca abajo solo del 242 al 272: se levanta 272-454, antorcha 455-489, se soba la espalda 490-702. Todo lo posterior se adelanto 98 frames (escena 1-871):
voz de Alfred "alfred_f368" en 270, Jerry "que te he dicho" 390 (justo despues de lanzar el balde en 383; su mirada a Alfred desde 389), Alfred "nada, no me ha dicho nada" 442 (mientras termina de ponerse de pie), Jerry "que raro... una arana" 652 (pata al menton 646-703, giro de alerta 697-713, pose de alerta),
Alfred mira la arana 702-712, la arana aparece 692, salta 704, en la cara 716 (impacto en Alfred), Alfred corre en circulos desde 726 (ovalo en (-47.9,-15.75)).
Jerry baja por el agua desde 106 (en el suelo 210) y lanza el balde en 383 (golpe 386, mientras Alfred se levanta). Agua 80-180. La camara y el foco de la conversacion (claves 349-710) NO se movieron.
Scripts (constantes ya actualizadas): alfred_levantarse.py, alfred_coloca_antorcha.py, jerry_baja_agua.py, jerry_responde_pensando.py, alfred_mira_arana.py, arana_salta_cara.py, alfred_corre_circulos.py.
Orden si se regenera: ... jerry_responde_pensando -> alfred_mira_arana -> alfred_corre_circulos -> arana_salta_cara (la arana sigue a la cara ya animada).
Despues (dialogo seguido, sin silencios; escena 1-701): Jerry "que te he dicho" 390-438, Alfred "nada, no me ha dicho nada" 442-478 (aun levantandose), Jerry "que raro... una arana" 482-547
(pata al menton 476-533, giro/alerta 527-543), Alfred mira la arana 532-542, arana aparece 522, salta 534, en la cara 546, Alfred corre desde 556. Lo de arriba con 652/692/716/726 quedo reemplazado.
Choque (alfred_choca_estalagmita.py): ultima vuelta, se desvia en 672 hacia la estalagmita (-48.47,-14.5), choca en 675 (arana aplastada entre la estalagmita y su cara, alfred["f_choque"]),
rebota, gira y cae de espaldas hacia el oeste (suelo en 696, alfred["f_suelo"]); escena 1-730. Orden: alfred_corre_circulos -> alfred_choca_estalagmita -> arana_salta_cara -> jerry_mira_carrera -> sonidos_arana_carrera.
Antorcha (alfred_antorcha_levantandose.py, sustituye a alfred_coloca_antorcha.py): Alfred la planta con el brazo derecho mientras se levanta, aun de rodillas (alcanza 290, planta 302, suelta 316; IK por frame en la capa Alfred_antorcha_levantandose). Se quito el agachado viejo (455-489) de la accion base; sobarse la espalda empieza en 455 con fundido de 8 frames. Voz tapada de Alfred al correr: alfred_corre_arana_tapado.wav en 558, volumen 3.

## The Stalker en el tunel (alfred_cueva_5.blend)
- Personaje: empty `the_stalker_1` (hijo `torso_1` armature de 133 huesos, 11 mallas, luces `stalker_fx_luz_*`). Mide 1 x 3 m; el tunel x -99..-98, z -18..-16 (1 x 2), avanza hacia +Y hacia la camara `Camera.001` (y = -82.5).
- `capitulos/capitulo_4/stalker_tunel_gatear.py` -> `exec(...)`; `aplicar()`: reescribe el andar de los 14 huesos del cuerpo y la posicion Y del empty (cuadros 1-261): agachado, torso inclinado, cabeza/cara/pecho hacia la camara, manos aferradas a las paredes (IK de 2 huesos con la mano fija en el mundo mientras tira), piernas empujando, todo asimetrico. Respaldos: acciones `*.respaldo_caminar`. Los tentaculos no se tocan.
- Luz `stalker_luz_cara` (hija del hueso head_1, light linking solo a la coleccion `stalker_receptores`) para ver cara, dientes y pecho sin iluminar el tunel.
- Cambio de ritmo: ahora avanza desde el cuadro 1 a ~1.4 m/s (antes arrancaba en el 85 a ~3 m/s) y llega junto a la camara hacia el 240.
- Agarres del Stalker (`superficie()` en `stalker_tunel_gatear.py`): cuadros 1-80 ambas manos a las paredes (alto 0.9-1.75 m); 80-145 el brazo izquierdo al suelo; 145-210 el derecho al techo; luego vuelve a las paredes. La mandibula inferior (`neck_front_1`) sigue a la cabeza (se traslada con `location` ademas de rotar).

## Alfred picando carbon en el tunel (clon `alfred_carbon`)
- `capitulos/capitulo_4/alfred_pica_carbon.py`: `crear_clon()` duplica el rig (`alfred_carbon`, `Armature_carbon`, mallas, ojos, `stone_pickaxe_carbon`; entran en `luz_entrada_receptores`), `hornear()` (frames 1-261, un golpe cada 18: 18, 36 ... 252), `sonorizar()` (block.stone.break por golpe, origen `alfred_carbon`).
- Esta de pie en (-98.5, -41.5, -18.0) mirando a +X, golpeando la veta `bloque_coal_ore_-98_-42_-18/-17` (cara de la pared en x = -98). Reutiliza el solucionador de poses de `alfred_cae_estalagmita.py` (se ejecuta con ARM/ROOT cambiados).
- `alfred_pica_carbon.py` ahora parte de `generador de animaciones/alfred/refinar/poses/preparado para picar.json` (pose exacta en los frames sin golpe; manos delante a la altura de la cintura), levanta el pico delante y golpea la pared; un golpe cada 22 frames (22, 44 ... 242). Ciclo: `fase_c(f)` 0 = preparado, 1 = pico levantado, 2 = impacto.
