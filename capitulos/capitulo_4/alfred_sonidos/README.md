# Alfred Sonidos

Libreria de los sonidos originales de Minecraft (carpeta `C:\Users\user\Desktop\Alfred_Animacion\sonidos`: `sounds/` con 3855 .ogg y `sounds.json`, 1642 eventos con archivos)
para ponerlos en la escena segun lo que pasa. Panel: Vista 3D / Secuenciador > barra lateral (N) > **Sonidos MC**.

## Novedad v1.1: como en el juego
Cada objeto se reconoce por su nombre, el de su padre, sus materiales y sus texturas, y suena con los `.ogg` que le tocan en Minecraft:
- **Bloques** (`oak_planks` -> madera, `grass_block` -> pasto, `cobblestone` -> piedra...): colocar, romper, golpear, caer y paso (`block.<tipo>.*`, 112 tipos).
- **Mobs** (`zombie_1_Armature`, `Dog_001_rig` / `jerry` = lobo, `alfred` = jugador...): todos los eventos del mob (voz, herido, muerte, paso...).
- **Herramientas** (`wooden_axe`, `stone_axe`...): material -> madera, piedra, metal.
- **Pasos**: un mob con paso propio usa el suyo (`entity.zombie.step`, `entity.wolf.step`); Alfred y los demas usan la SUPERFICIE bajo el pie en ese frame (rayo hacia abajo, lee el bloque de abajo), volumen 0.5 como en el juego.
- **Choques**: la superficie de abajo (`fall`) + el material del objeto (`hit`).
- **Aparecer / desaparecer**: `place` / `break` segun el tipo del bloque (visibilidad o escala animadas).
- **Objeto activo**: el panel muestra que reconocio y da un boton por cada evento; **Analizar objetos** resume toda la escena.
La tabla de nombres -> tipo esta en `TIPOS_BLOQUE` y `ALIAS_MOB` (arriba en `__init__.py`); si un objeto no se reconoce, cambia su nombre o agrega la palabra.

## Novedad v1.2: por debajo de las voces
Cada sonido que se anade se limita para quedar por debajo de la voz MAS BAJA de la escena (tiras que no son `SND_`): su pico `margen_pico` dB (8) por debajo del pico de esa voz y su volumen medio `margen_rms` dB (3) por debajo del medio.
Los niveles se miden con `aud` sobre los archivos reales. Se desactiva con "Por debajo de las voces". Guion de la parte 3: `generador de animaciones/alfred/refinar/docs/parte3/sonorizar_parte3.py`.

## Novedad v1.3: automatico, segun avanza la historia
Caja **Sonorizar la historia** (arriba del panel): lee TODA la animacion y pone los sonidos sin frames escritos a mano.
- **Personajes** (armatures animados y visibles): pasos cuando CAMINAN, tramo a tramo (superficie bajo el pie, o el paso propio del mob), y el contacto del cuerpo con el suelo al sentarse / echarse / caer.
- **Objetos animados** reconocidos (herramientas, bloques; el material manda sobre el nombre): silbido al salir disparados (velocidad relativa al personaje mas cercano: una herramienta llevada en la espalda no suena), choque contra el suelo, colocar al aparecer y romper al desaparecer (en el primer frame en que empieza a encogerse).
- **Todo**: rehace las tiras automaticas (`mcsnd_auto`) de toda la escena (~35 s en la parte 3). **Solo lo nuevo**: sigue desde el ultimo frame sonorizado (*Sonorizado hasta*) hasta el final de la escena, asi se completa cuando la historia crece sin tocar lo anterior. **Reajustar volumenes**: vuelve a bajar todo por debajo de las voces actuales.
- **Vigilar** (apagado por defecto): cada 5 s sonoriza lo nuevo si el final de la escena crece y reajusta volumenes si se anaden o cambian voces.
Se desactiva cada tipo (pasos / cuerpo / objetos / aparecer) en la misma caja. Los sonidos manuales (biblioteca, eventos, bucle) no se tocan.

## Novedad v1.2: por debajo de las voces
1. **Biblioteca**: "Leer biblioteca" (se hace sola al abrir), busca un evento (`wolf howl`, `wood step`...) o cambia a "Archivos"; **Escuchar**; **Anadir al frame** (frame actual o propio). Variante 0 = al azar.
2. **Eventos del proyecto**: lista corta ya armada (pasos por superficie, antorcha, herramienta que cae, lanzar, Jerry ladra / jadea / suspira / se sacude, zombie, golpes, puertas...).
3. **Pasos automaticos**: elige el personaje (Alfred, Jerry o un zombie; los huesos de apoyo se detectan solos) y la superficie. Mira el movimiento de los pies en el rango y pone un paso en cada contacto.
   Ajustes: *umbral* (fraccion de lo que se levanta el pie), *levantamiento minimo*, *avance minimo*, *separacion*. Usa el rango donde camina (no dejes el sentado dentro del rango).
4. **Objetos lanzados**: selecciona los objetos (p. ej. `wooden_pickaxe`, `wooden_axe`, `stone_axe`); pone un silbido cuando salen disparados y un golpe cuando se frenan en seco cerca de su punto mas bajo.
5. **Bucle**: rellena un rango con un sonido repetido (antorcha / fuego / ambiente).
6. **En la escena**: quitar por tipo o todos (`SND_*`) y **Mezcla WAV** (todo el audio de la escena, voces incluidas).

Cada sonido es una tira de sonido `SND_<evento>_<frame>` (con propiedades `mcsnd`, `mcsnd_ev`); una fila de canales por tipo (pasos 10, antorcha 16, objetos 22, voces 28, golpes 34, ambiente 40; si dos se solapan sube al siguiente libre).
Los canales 2-3 son de Voz Sync. Se puede mover / recortar cada tira a mano. El volumen varia un poco al azar (*Variacion*).

## Personalizar
`presets_usuario.json` en la carpeta de sonidos redefine un evento del proyecto: `{"paso_madera": {"etiqueta": "..", "eventos": ["block.wood.step"], "grupo": "pasos", "vol": 0.9}}`.

## Limites
Blender no tiene tono (pitch) en las tiras de sonido: la variedad sale de las variantes de cada evento y del volumen. El sonido no es 3D (no hay parlantes).
Minecraft no tiene sonido de pico, ni voz de Alfred (bostezos, risas): eso viene de tus grabaciones.
