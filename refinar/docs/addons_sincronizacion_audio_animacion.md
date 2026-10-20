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
f_ini 223, f_parada 370, f_baja 378, f_choque 465, f_aterriza 482, f_borde 483, f_seco 525 (seco ~585), f_ruta_ini 598, f_lanza 647, f_rel 655, f_golpe 658, f_fin 763. Agua cae del 150 al 250.

## Gotchas
- Mantener Alfred/Jerry/cubo/herramientas/antorcha dentro de la coleccion `luz_entrada_receptores` (light linking de `luz_entrada_cueva`); si no, se ven oscuros. Esa coleccion NO esta en la view layer: enlazar los objetos tambien a la Scene Collection.
- Bloques: `bloque_<tipo>_<i>_<j>_<k>`, origen abajo-centro, cara superior z=k+1. El bloque diorita (-45,-15) tiene k=-10 (top z=-9).
- Alfred: nunca mover el empty `alfred` en el levantarse/antorcha (el usuario lo exige); el desplazamiento va en Hips.
- Pase de Python: usar rutas con `/` o `r""` en parches; no borrar bloques de funciones con `index('# ====')`.
