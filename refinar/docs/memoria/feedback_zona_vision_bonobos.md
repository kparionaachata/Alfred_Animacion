---
name: zona-vision-bonobos
description: "Video bonobos tala - Alfred debe ir a la zona (-72.5, 30.5|32.5, 12) cada vez que es golpeado, mira que pasa o lanza algo a los monos"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 652ab5d2-c4b2-402d-87db-bd00c559cad5
  modified: 2026-10-30T14:56:48.169Z
---

En el video bonobos, siempre que Alfred reciba golpes de los monos, observe o QUIERA LANZAR/devolver algo a los monos, tiene que desplazarse antes a la zona marcada por el usuario: (-72.5, 32.5, 12.0) o (-72.5, 30.5, 12.0) (zona circulada donde convergen las lineas de los monos; desde ahi los ve bien).

**Why:** el usuario lo ordeno el 30 oct con dos capturas (coordenadas #1 y #2 y vista aerea con el circulo rojo).

**How to apply:** en cualquier escena nueva donde Alfred lance algo a los monos, primero caminar ahi (skill alfred-desplazamiento-a-b) y lanzar desde ese punto. Bloque 3 ya hecho asi con PH=(-72.5,32.5,12) en `bonobos_madera_bloque3_p.py`. Ver [[feedback_monos_bloqueados]] (los monos se desbloquean solo si la orden pide animarlos).
