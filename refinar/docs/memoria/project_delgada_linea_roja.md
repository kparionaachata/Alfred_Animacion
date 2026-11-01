---
name: delgada-linea-roja
description: "Video realista de 5 min de la Delgada Linea Roja (cuadro de Gibb): materiales, extractor de Napoleon Total War y que falta"
metadata:
  node_type: memory
  type: project
  originSessionId: ecf146ce-27a6-4bbb-8414-6c2cac17a01b
  modified: 2026-10-31T07:31:28.458Z
---

Pedido (30 oct 2026): video en Blender de la batalla de la Delgada Linea Roja, estilo realista como el cuadro de Robert Gibb, solo soldados (sin Alfred/Jerry), 5 minutos. El cielo lo pone el usuario con su HDRI. El usuario pidio ir por pasos: NO empezar guion, escena, camaras, sonido ni render hasta que lo ordene.

Carpeta `capitulos/delgada_linea_roja/`: `materiales/` (descargas libres, CREDITOS.json), `Nueva carpeta/` (juego Napoleon: Total War, 23 GB, solo lectura), `extractor/` (`ntw_lib.py`, `exportar_personajes.py`, `comprobar_glb.py`, `ver_glb.py`), `personajes_napoleon/` (32 .glb con esqueleto y texturas, LEEME.txt).

**Formato descifrado del juego:** variant_part_mesh = 4 LOD, el primero es el de mas detalle; vertice de 40 bytes con 2 huesos y posicion relativa a cada hueso (por eso hace falta una pose para reconstruir); penachos y equipo rigidos de 64 bytes. El rojo de la casaca NO esta en la textura: sale de colour_mask, los tintes del cuadro van en UNIDADES.
**Gotcha:** el importador glTF de Blender crea un objeto auxiliar `Icosphere` de 42 vertices; no es el personaje.
**Efectos y mecanicas (31 oct):** `efectos_y_mecanicas/` (LEEME.txt) con 2036 clips en glb, armas, efectos (crear_efecto.py), sonidos y tablas; generado con `extractor/exportar_mecanicas.py`; la tabla de columnas viene de rpfm-schemas (schema_nap.ron, variable NTW_SCHEMA).
**Biblioteca (31 oct):** `biblioteca_personajes/` (LEEME.txt): un .blend por personaje en pose T, sin armas (el usuario las pidio aparte), `armas/<arma>/` y `equipo/`. Regenerar con `extractor/generar_todo.sh`. Personajes, clips y armas comparten como reposo la pose T del juego (animations/reference/tpose.anim, horse_base.anim).
**GLB compatibles:** huesos con traslacion y rotacion (no matriz), tangentes y texturas potencia de 2, arreglo el colapso en el visor 3D de Windows (confirmado por el usuario). Rugosidad sacada del canal G de gloss_map y normales suavizadas para quitar el brillo de la tela. Validar con gltf-validator (npm). Las armas van siempre aparte de los personajes: `armas_napoleon/` (.glb) y `biblioteca_personajes/armas/` (.blend).
**Gotchas:** mosquete en Weapon1, sable en Weapon2, lanza en Weapon3 (el juego aparca los que no usa). Clips a 20 fps; avance en Hips; c_sab_*/c_lan_* no avanzan, el jinete debe seguir al caballo. La herramienta rea no se uso: solo analiza programas, no datos ya descifrados. Texturas de terreno/vegetacion en materiales/.

**Why:** retomar sin volver a descifrar los formatos.
**How to apply:** volver a generar con `python -I exportar_personajes.py`. Modelos con copyright de Creative Assembly/SEGA. Ver [[obey-and-be-brief]].
