---
name: lanzamientos-mas-lentos
description: "Video bonobos (30 oct): cada vuelo de objeto lanzado se alargo +20 frames con un remapeo global de tiempo; scripts bonobos_madera_* quedan desfasados"
metadata:
  node_type: memory
  type: project
  originSessionId: 652ab5d2-c4b2-402d-87db-bd00c559cad5
  modified: 2026-10-30T18:30:56.101Z
---

El 30 oct el usuario pidio "20 frames mas" a cada lanzamiento (palos, pollo, rata, silex, manzana, serpiente) entre Alfred y los monos. Se hizo sobre la escena viva con un remapeo global de tiempo (todas las acciones, handles y la tira de sonido `pop_item`): cada vuelo (suelta -> impacto) dura +20 frames; los vuelos solapados reparten rampas resueltas por minimos cuadrados. La escena paso de 1119 a 1339 frames. Los parametros quedaron en `scene['lanz_rampas']` (JSON con los vuelos V y las rampas a) para poder invertirlo.

**Why:** los lanzamientos se veian demasiado rapidos (T_VUELO 14 en el bloque 3).

**How to apply:** los scripts `bonobos_madera_*.py` y `bonobos_madera_bloque3_p.py` siguen en la escala anterior (retime 0.8, sin los +20): no regenerar encima de la escena viva sin deshacer antes el remapeo con `lanz_rampas`. Relacionado: [[feedback_movimientos_rapidos]].
