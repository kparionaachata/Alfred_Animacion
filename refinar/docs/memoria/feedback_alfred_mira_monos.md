---
name: feedback-alfred-mira-monos
description: Alfred sabe que hay monos en los arboles; cada vez que interactua con uno debe mirar hacia arriba (cuello apuntando a la cabeza del mono)
metadata:
  node_type: memory
  type: feedback
  originSessionId: 593282e0-289f-4704-9bd2-cafc9b5be57b
  modified: 2026-10-31T18:25:56.600Z
---

En el video de los bonobos Alfred no puede actuar "como si nada": sabe que hay monos en los arboles, por lo que cada vez que interactua con cualquiera (golpe del pollo, rata, lanzamiento, gesto con el puño) debe mirar hacia arriba al mono correspondiente (cabeza y cuello, no solo el cuerpo).

**Why:** el usuario lo pidio expresamente al animar el gesto con el puño tras el golpe del pollo y el susto por la rata (reducir tambien los frames de susto).

**How to apply:** resolver el cuello (`Neck_alfred` X/Y, cara = eje local Z de `face_alfred`) por Newton hacia la cabeza del mono por frame (pitch ±65°, yaw ±80°, mezcla de 6 frames entre objetivos); con el torso doblado (lanzamiento) el cuello no llega, empezar el rastreo cuando se recupere. Relacionado: [[feedback-lanzador-mira-objetivo]], [[feedback-inercia-accion-reaccion]].
