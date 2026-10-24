---
name: filtros-organicos-parpadeos-parte6
description: Alfred, Jerry y Creeper deben llevar los filtros organicos y parpadeos de sus estudios tambien en la escena viva de la parte 6
metadata:
  type: feedback
---

El usuario (2026-10-08) pidio aplicar a Alfred, Jerry y el Creeper "los filtros organicos, ademas de los parpadeos" que sus estudios traen: la parte 6 se construye con scripts en la escena viva y no pasa por CONCATENAR. Hecho con `alfred/refinar/docs/acciones/filtros_organicos_y_parpadeos.py` (valores por omision de cada estudio, deltas aditivos por frame en `organicos_delta.json`, parpadeos de 9 f cada 80-140 f).

**Why:** sin ellos las animaciones de la parte 6 se ven rigidas respecto a las partes 1-5.
**How to apply:** tras cambiar o regenerar animaciones de un personaje, volver a ejecutar ese script (resta lo anterior y vuelve a sumar). NO aplicar "suavizar fcurves" ni "secondary motion" del estudio sobre las claves de la parte 6 (borran giros rapidos y golpes). Cualquier animacion nueva de ojos debe esquivar las ventanas de parpadeo (editar `evitar_*` del script). Ver [[feedback_herramientas_aparentadas]].

**Parte 7 (2026-10-09):** pedido otra vez, para Alfred, Jerry, Creeper y Pollo (filtros) y Alfred+Jerry (parpadeos). Hecho con `alfred/refinar/docs/parte7/filtros_organicos_y_parpadeos_parte7.py` (deltas en `organicos_delta_parte7.json`; Alfred desde f131, Creeper desde f300, cola de Jerry solo tranquilo). Antes de regenerar la animacion de un personaje: ejecutarlo con `QUITAR = True`; despues, de nuevo normal.

**Parte 7 (2026-10-09):** cada script de voz borra los `Closed` de su rango -> huecos sin parpadeo. `alfred/refinar/docs/parte7/parpadeos_basicos_parte7.py` rellena huecos > 110 f (idempotente); correrlo SIEMPRE despues de los scripts de voz.
