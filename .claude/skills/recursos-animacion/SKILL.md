---
name: recursos-animacion
description: Donde estan los recursos para animar CUALQUIER personaje en este proyecto - objetos (pan, stick, papel, libro, manzana, herramientas...), sonidos (pasos, golpes, comer, ambiente, mobs) y bloques 3D (piedra, madera, tierra, oro, menas, antorchas, mesas...). Consultar SIEMPRE antes de crear un objeto, sonido o bloque desde cero o de pedir que se lo busquen.
---

# Recursos del proyecto para animaciones

Antes de modelar, sintetizar o pedir un recurso, buscarlo aqui. Todo es reutilizable por cualquier personaje (Alfred, Jerry, mobs...).

## 1. Objetos (items) - `C:\Users\user\Desktop\Alfred_Animacion\objetos\vanilla`

- ~600 carpetas, una por objeto: `objetos\vanilla\<nombre>\<nombre>.blend` (+ `<nombre>_outliner_data.json`). Nombres en ingles de Minecraft: `bread`, `apple`, `stick`, `paper`, `book`, `writable_book`, `written_book`, `feather`, `flint`, `honeycomb`, `cocoa_beans`, `sweet_berries`, `arrow`, `*_boat`, `*_door`, `*_sign`, `*_pottery_sherd`, `armor_stand`...
- Algunos traen rig (p.ej. `arrow.rig`) o variantes (`stick`, `stick_2`, `book.001`).
- Para comer pan, lanzar un stick, escribir en papel, etc.: usar el objeto de aqui y animarlo (Child Of al hueso de la mano mientras se sostiene, o keys de mundo al soltarlo).
- Buscar: listar la carpeta o `Glob` con parte del nombre. Si falta el objeto, avisar y NO inventarlo sin preguntar.
- Traerlo a la escena con `append`/`link` de Blender (el proyecto ya tiene helpers: `traer()` y `objeto_item()` en `capitulos/capitulo_4/bonobos_madera_escena.py`, que copian el item y lo nombran `bm_<nombre>_<n>`).

## 2. Sonidos - `C:\Users\user\Desktop\Alfred_Animacion\sonidos`

- `sonidos\vanilla\<categoria>\...` con las categorias de Minecraft: `ambient`, `block`, `damage`, `dig`, `enchant`, `entity`, `event`, `fire`, `fireworks`, `item`, `liquid`, `minecart`...
- `sonidos\sounds.json`: indice evento -> lista de sonidos (`name`, `volume`, `weight` para variar). Usarlo para elegir sonido y volumen reales de cada evento (pasos, golpes, items...).
- Paquetes de mobs/mods: `Monke Madness 1.13.2`, `SimplySnakes-Fabric-26.2-1.0.2`, `THE UNDEAD REVAMPED`, `The Man From The Fog`, `Zoo__Wild_Animals_Rebuilt__ZAWA`, `insects_recrafted_1100`, `palomas`, `ribbits`.
- `sonidos\algoritmos\` (Java, con `README.md`): logica de sonidos de bloques y pasos segun superficie.
- Reglas del proyecto: ver tambien las notas de memoria sobre sonido (volumen segun distancia a camara, dentro/fuera del refugio, ducking suave de las voces).

## 3. Bloques 3D - `C:\Users\user\Desktop\Alfred_Animacion\bloques_dinamicos`

- ~100 `.blend` planos, nombres en espanol: `bloque_de_stone`, `bloque_de_roble`, `bloque_de_tablones_de_roble`, `bloque_de_tierra`, `piedra`, `tierra`, `arena`, `grava`, `cobblestone`, `andesita`, `diorita`, `granito`, `obsidiana`, `pizarra_profunda`, `mena_de_<mineral>` (hierro, oro, cobre, carbon, diamante, esmeralda, lapislazuli, redstone, + `_de_pizarra_profunda`), `bloque_de_<mineral>_en_bruto`, `bloque_de_amatista`, `estalactita_*`/`estalagmita_*`, `antorcha_1`, `torch*`, `soul_torch`, `lantern*`, `campfire*`, `fogata_*`, `fire`, `chest`, `chest_double`, `furnace_front_on`, `mesa_de_crafteo_1`, `enchanting_table`, `spawner`, `telarana`, `valla de roble`, `slab_de_tablones_de_roble`...
- Algunos tienen `.json` con su configuracion (`antorcha_1.json`, `mesa_de_crafteo_1.json`, `fogata_3.json`, `arco_1.json`). Ignorar los `.blend1` (respaldos).
- Para construir suelos, paredes, minas o mesas: usar estos bloques, no cubos con materiales nuevos.

## Como proceder

1. Identificar que objeto/sonido/bloque pide la animacion.
2. Buscarlo en la carpeta correspondiente (nombre exacto con `ls`/`Glob`).
3. Reutilizarlo; si no existe algo equivalente, decirlo y proponer alternativa antes de crearlo.
4. Anotar en el guion de la animacion que recurso se uso y de que ruta.
