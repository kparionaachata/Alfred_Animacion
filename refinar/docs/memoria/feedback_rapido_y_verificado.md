---
name: feedback_rapido_y_verificado
description: "No iterar a ciegas durante mucho tiempo; aplicar lo pedido, verificar en imagen y reportar enseguida"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 93ef65a7-e5c0-4f1e-ac65-91c8b9f7c4e7
  modified: 2026-11-07T05:47:13.707Z
---

El usuario se enojo mucho (2026-11-06/07, pala y carbones) cuando pase minutos re-ejecutando una IK frame a frame y probando parametros sin avisar ("estas minando bitcoin?", "no vuelvas a darme mierdas", interrumpio y pidio cancelar).

**Why:** cada vuelta tardaba minutos, el resultado seguia mal (mano atravesando el cuerpo, piernas deformadas por IK sin polo, manos solapadas) y el usuario no veia avances.
**How to apply:**
- Si el usuario da valores de huesos/objetos (capturas del panel), usarlos TAL CUAL en los frames que dice; no reinterpretarlos ni "mejorarlos".
- Una pasada, verificar (medida + render de cerca del gesto) y reportar; si algo no cuadra, decirlo y proponer opciones en vez de seguir probando.
- Nunca IK en piernas sin polo (deforma la malla); no mover la cadera para alcanzar algo si los pies se quedan: dar un paso.
- Herramienta larga (pala ~0.8 m): primero comprobar que cabe entre el personaje y el objetivo; si no, que el personaje se aparte.
- Mensajes cortos. Relacionado: [[feedback_obedecer_breve]], [[feedback_herramienta_mano_derecha]].
