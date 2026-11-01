---
name: monos-bloqueados-solo-alfred
description: "Video bonobos/tala: animaciones de los monos BLOQUEADAS (no tocar); trabajar solo Alfred y su interaccion con objetos"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 22c3d667-c653-48cb-ab35-244ae3a40749
  modified: 2026-10-30T05:06:52.555Z
---

El usuario (30 oct) pidio bloquear las animaciones de los bonobos en el video "Alfred tala arboles y los bonobos le tiran cosas": no cambiar bonobos_madera_bonobos.py ni el codigo de monos de bonobos_madera_main.py; enfocarse solo en la animacion completa de Alfred y su interaccion con los objetos (hacha, objetos que recoge y lanza, objetos que recibe).

**Why:** ya los dejo como queria (ritmo rapido de monos) y no quiere que se re-toquen.

**How to apply:** los monos dependen de los frames-evento de G (impactos, soltar, etc.) que genera bonobos_madera_alfred.py; al cambiar la duracion de un tramo de Alfred se desplazan los monos. Mantener los frames de G estables o avisar. Ver [[project_video_bonobos_tala]].
