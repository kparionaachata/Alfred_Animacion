---
name: cueva-alfred-jerry-capitulo4
description: "Estado al 2026-10-20 de alfred_cueva_2.blend (Alfred cae en la estalagmita, se levanta, pone antorcha; agua; Jerry baja y trota a Alfred) y regla de no usar Blender sin autorizacion"
metadata:
  node_type: memory
  type: project
  originSessionId: a6b878c7-038a-4857-8f52-879a8b502848
  modified: 2026-10-21T21:13:53.150Z
---

Ultimo trabajo (sesion 342257e2, 2026-10-20, subido en el commit 446fa0e/debc949): escena `capitulos/capitulo_4/alfred_cueva_2.blend` (el usuario no la habia guardado; respaldo `alfred_cueva_2_respaldo_antes_superficies.blend`). Doc de continuidad: `generador de animaciones/alfred/refinar/docs/addons_sincronizacion_audio_animacion.md` (orden de scripts, tiempos de Jerry, gotchas). Add-ons nuevos en capitulo_4: `alfred_agua/`, `alfred_efectos/`; recorridos sobre bloques: `recorrido/blender_path_bloques.py`.

Orden de scripts: alfred_cae_estalagmita (1-242) -> alfred_levantarse (370-552, empty fijo, compensa Hips) -> alfred_coloca_antorcha (553-587, antorcha en (-44.5,-15.5,-9)) -> jerry_baja_agua (borde f370, salta 378, trota a Alfred, balde f647, fin 763) -> sonidos_jerry_agua_levantarse (re-ejecutar tras rehornear). Agua de f150 a 250.

**Why:** el usuario sigue desde otra cuenta y necesita retomar sin perder contexto.
**How to apply:** el usuario escribio "bloquea el programa blender sin mis autorizacion": no usar herramientas de Blender salvo pedido explicito de esa tarea. No mover el empty `alfred` en levantarse/antorcha. Objetos nuevos iluminados deben ir a `luz_entrada_receptores`. Jerry sin pisadas. Ver [[obey-and-be-brief]].

**2026-10-21:** escena continuada en `alfred_cueva_3.blend` (araña, carrera en círculos, choque contra la estalagmita, Alfred cae de espaldas, f1-730). El usuario pidio dejar el f730 fijo como frame 1 EN ESE MISMO archivo (sin animaciones ni audios de personajes; camara y Foco_Conversacion intactos): se hizo en vivo con `crear_base_cueva_3.py` (sin la linea de guardar). NO crear copias de archivo cuando el usuario nombra un .blend: trabajar sobre ese (rechazo la copia `_base`, se borro). blender.exe en "C:/Program Files/Blender Foundation/Blender 5.2/" (el tool _for_cli no lo encuentra).
