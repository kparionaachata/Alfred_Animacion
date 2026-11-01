# Reglas fijas del proyecto Alfred_Animacion

- Al desplazar a Alfred de un punto A a un punto B: usar SIEMPRE la skill `alfred-desplazamiento-a-b` (Z igual = caminar, Z positivo = saltar subir, Z negativo = saltar bajar, con las animaciones del `alfred_animation_studio`). No inventar caminatas ni saltos.
- Al desplazar a Jerry de A a B: usar SIEMPRE la skill `jerry-desplazamiento-a-b` (misma regla de Z, con el `jerry_animation_studio`).
- Al desplazar a rat_1 (la rata) de A a B: usar SIEMPRE la skill `rat1-desplazamiento-a-b` (misma regla de Z, con el `rat_1_animation_studio`).
- Al desplazar a chicken_1 (el pollo) de A a B: usar SIEMPRE la skill `chicken1-desplazamiento-a-b` (misma regla de Z, con el `chicken_1_animation_studio` y sus animaciones base capturadas).
- Para CUALQUIER recorrido o desplazamiento de personajes (formato de puntos, pasos de 1 bloque, clasificacion en slots): usar la skill `sistema-recorrido` (comun a todos los personajes presentes y futuros).
- En TODA animacion con objetos que se mueven, se lanzan, golpean o caen, o con personajes que reciben o dan impactos: aplicar la skill `inercia-accion-reaccion` (gravedad real, inercia, reaccion en el frame exacto del impacto, rebotes).
- Las skills estan en `.claude/skills/` (y en `~/.claude/skills/`); leerlas completas antes de animar.
- Alfred con una herramienta o arma en la MANO DERECHA (hacha, pico, espada...): aplicar SIEMPRE la skill `herramienta-mano-derecha` (Child Of a `Rightelbow_alfred` con ubicacion, rotacion y escala fijas).
- Objetos, sonidos y bloques 3D para animar a cualquier personaje: buscarlos primero segun la skill `recursos-animacion` (objetos en `objetos/vanilla`, sonidos en `sonidos`, bloques en `bloques_dinamicos`).
- Cada vez que un personaje rompa un bloque (madera, piedra, tierra, menas...) picando, talando o excavando: aplicar SIEMPRE la skill `bloque-roto-drop` (el bloque se oculta, aparece un item de escala 0.25 que cae, gira y flota como en Minecraft, y luego lo absorbe el personaje que lo rompio).
- Todo objeto que un personaje lance hacia otro personaje: el que lanza debe mirar a su objetivo (mover la cabeza y dirigir la mirada); aplicar SIEMPRE la skill `lanzador-mira-objetivo`.

# Retomar el trabajo con otra cuenta
- Alfred y Jerry: leer `refinar/docs/CONTINUAR_DESDE_AQUI.md` y las reglas en `refinar/docs/memoria/`.
- Proyecto en paralelo, La Delgada Linea Roja (soldados, sin Alfred ni Jerry): leer `capitulos/delgada_linea_roja/CONTINUAR_AQUI.md`.
