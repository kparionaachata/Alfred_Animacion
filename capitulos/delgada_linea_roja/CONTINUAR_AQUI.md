# La Delgada Linea Roja: continuar desde aqui (estado al 2026-11-01)

Proyecto en paralelo al de Alfred y Jerry, y sin relacion con su historia. Leer esto antes de tocar nada.

## De que se trata

Video realista de unos 5 minutos en Blender sobre la batalla de la Delgada Linea Roja (Balaclava, guerra de Crimea, 1854), siguiendo el cuadro de Robert Gibb *The Thin Red Line*. Solo soldados: ni Alfred ni Jerry.

**Se avanza por pasos y solo lo que el usuario ordena.** Todavia NO se empieza guion, escena, camaras, sonido ni render del video. El cielo lo pone el usuario con su HDRI. Las armas van siempre aparte de los personajes.

**Etapa actual:** dejar un soldado Highlander (`britain_inf_elite_british_black_watch.soldier`) realista como heroe. Luego vendran los demas y una version ligera para las filas.

## Ultimo estado

- **Archivo de trabajo:** `biblioteca_personajes/highlanders/britain_inf_elite_british_black_watch.soldier/ejemplo_19.blend`. Los `ejemplo_N` son versiones sucesivas: nunca se pisan y el `.blend` original del personaje no se toca (md5 `ffacf08790722106124f69e355684e83`).
- **Persona separada:** `.../persona/<detalle>/<detalle>.blend` con `vista.png` (22 detalles; `persona/hoja.png` los muestra todos).
- **Ultima orden cumplida:** cerrar el hueco entre nuca, oreja y bonete.
- **Pendiente sin ordenar:** la ropa nueva de los ejemplos todavia no esta subdividida en carpetas como la persona. Preguntar antes de hacerlo.

## Que hay y que no hay en el repositorio

En Git solo estan los scripts, las guias y `extractor/subdivision_prendas/mpfb_datos`. Lo demas vive en el PC del usuario, en `C:\Users\user\Desktop\Alfred_Animacion\capitulos\delgada_linea_roja\`:

| Carpeta | Contenido | Por que no se sube |
|---|---|---|
| `Nueva carpeta/` | Juego Napoleon: Total War (23 GB, solo lectura) | Copyright de Creative Assembly/SEGA |
| `biblioteca_personajes/` | Personajes `.blend`, `prendas/`, `prendas_cine/`, `persona/`, `ejemplo_*.blend` (12 GB) | Peso y modelos del juego |
| `personajes_napoleon/`, `armas_napoleon/`, `efectos_y_mecanicas/` | Exportados del juego | Peso y copyright |
| `materiales/` | Texturas libres (710 MB) | Peso |
| `poliigon-addon-blender/` | Add-on de Poliigon; solo se usa su grupo de nodos `Poliigon_Fabric_Falloff` | Repositorio ajeno |

**Si la otra cuenta trabaja en el mismo PC, tiene todo.** En otro PC hay que copiar esa carpeta aparte; con solo clonar no se puede abrir ni regenerar nada. El repositorio es **publico**: nunca subir modelos del juego ni claves.

## Como regenerar el soldado

Blender 5.3 Beta (`C:\Program Files\Blender Foundation\blender-5.3...`), sin ventana. Los scripts estan en `extractor/subdivision_prendas/`; su guia completa es `LEEME.md`. El personaje se configura en `personajes/black_watch_soldier.py`, que ya contiene casi todo lo hecho a mano.

```bash
# P = carpeta del personaje, C = personajes/black_watch_soldier.py
blender -b "$P/personaje.blend" --factory-startup --python paso8_cine_lote.py -- "$C"                  # prendas/ -> prendas_cine/ (18 min)
blender -b "$P/personaje.blend" --factory-startup --python paso9_montar_cine.py -- "$C" "$P/ejemplo_1.blend"
blender -b "$P/ejemplo_1.blend" --factory-startup --python paso10_relieve_3d.py -- "$C" "$P/personaje.blend" "$P/ejemplo_N.blend"   # unos 3 min
blender -b "$P/ejemplo_N.blend" --factory-startup --python paso11_persona.py -- "$P/persona"
```

Para cambiar el soldado se edita la configuracion y se vuelve a lanzar el paso 10 con un `ejemplo_N` nuevo. Siempre parte de `ejemplo_1.blend`. Por eso los ejemplos anteriores ya no se reproducen con el codigo actual.

**Funciones de la configuracion:** `pintar_legs` (medias a dados y tartan), `plisar_kilt`, `crear_polainas`, `crear_bonete`, `crear_sporran`, `crear_doblez_media`, `crear_bandas`, `crear_hombros`, `crear_rostro`, y las listas `QUITAR`, `RELIEVE`, `RECETAS_NUEVAS`, `FINAL`.

## El soldado segun las referencias del usuario

Sus referencias son el cuadro de Gibb (manda sobre lo demas) y fotos coloreadas de veteranos de Crimea. Lo decidido con ellas, para no repetirlo:

- **Bonete:** masa alta de pelo negro fino, **no plumas** (lo corrigio el usuario), con una caida a un lado, banda a dados del cuadro y plumero blanco.
- **Persona:** **hombres mayores y curtidos**, barba tupida rojiza. Cabeza de MPFB, datos CC0 en `mpfb_datos`, leidos sin instalar el add-on.
- **Casaca:** galones, botones y faldones son **geometria real sacada de la textura**, nunca pintados ("tiene que notarse el alto relieve"). Mallas subdivididas: nada de aristas de carton.
- **Bandas:** solo una es blanca, de cuero, con insignia de laton; la otra es una **faja roja de otra tela**.
- **Hombros:** rollo blanco, tirilla con dos cordones y vivo en la sisa. Sin el ala ni los flecos del juego.
- **Kilt:** lana mate sin brillo, tartan oscuro azul y verde, tablas modeladas.
- **Sporran:** pegado a la cintura, colgador blanco en V, pelo oscuro y seis borlas claras.
- **Medias:** dados rojos y blancos, con doblez arriba y **borla roja colgante** (no moño).
- **Polainas:** lona blanca que tapa casi todo el zapato; solo asoman puntera y suela. Sin cantimplora.
- **Contexto:** es una batalla: desgaste, barro y suciedad, solo en las caras visibles.

## Fallos que el usuario todavia no ha visto resueltos

- **Ojos:** es lo que mas delata el 3D, con la mirada fija.
- **Faja roja:** pequenas grietas negras y borde irregular en la cadera; causa sin localizar. Sus pliegues casi no se notan.
- **Piezas de `persona/`:** bordes dentados y zonas por posicion, no por anatomia. El relieve de arrugas se proyecta tambien detras de la cabeza.
- **Sporran:** borlas separadas de lado, remate como una bala; correas que no llegan a un cinturon visible.
- **Cintura:** hueco con franjas a los lados, bajo el borde de la casaca.
- **Peso:** solo sirve de primer plano. Las filas necesitan una version ligera.
- **Sin comprobar:** animacion real. Casi todo se reviso en Cycles con una pose de prueba, no en el viewport del usuario.

## Como trabajar con este usuario

- Responder en espanol, breve. Hacer solo lo ordenado. No avisar de guardar.
- **Trabajar sin ventana y en un `ejemplo_N` nuevo.** No tocar su Blender abierto sin pedirlo. El MCP de Blender da timeout en operaciones largas.
- Mostrar siempre fotos y decir con franqueza lo que aun falla. Sus capturas marcan en rojo lo que hay que corregir: suelen ser del viewport.
- Comparar contra las referencias antes de entregar. Si manda una referencia, ella manda.
- Pegar en el chat una imagen sin texto suele ser la siguiente correccion.
- **Inventos a evitar:** no pintar lo que debe ser 3D, no dejar colores saturados de "recien salido del sastre".

## Herramientas externas probadas

- **Higgsfield:** la API (clave `HF_KEY` en `.env.local`, ignorado por Git, nunca en el repositorio) solo tiene imagen y video: de sus 91 modelos ninguno es 3D. Los modelos 3D estan en el conector de Claude, cuya cuenta tenia 0,82 creditos; una prueba cuesta de 17,75 a 52,75. No se genero nada.
- **Repositorios de rostros evaluados:** MPFB2 (el usado), CharMorph, FLAME add-on, ICT-FaceKit, HRN, NextFace, DECA, Deep3DFaceRecon, 3DDFA_V2. Revisar sus licencias antes de usar otro.

## Formato del juego (para no volver a descifrarlo)

Ver `refinar/docs/memoria/project_delgada_linea_roja.md` en la raiz del repositorio: formato de mallas, tintes por unidad, huesos de armas y como regenerar con `extractor/generar_todo.sh`. Modelos con copyright de Creative Assembly/SEGA.

## Sesiones de Claude

El chat de esta etapa no esta en `chats/` a proposito: contiene una clave pegada. Este archivo lo sustituye.
