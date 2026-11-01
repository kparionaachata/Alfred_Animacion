---
name: sistema-recorrido
description: Skill sistema-recorrido - sistema de captura de recorrido comun a todos los personajes; pasos de 1 bloque (recto, diagonal, subir/bajar), JSON key_points, ejemplo en Desktop/recorrido.json
metadata:
  type: reference
---

Skill general `sistema-recorrido` (30 oct): Paso 1 de cada `<personaje>_animation_studio`. Puntos = centro de cara (x,y en .5, z entera); pasos de exactamente 1 bloque: recto ±1 en X o Y, diagonal ±1 en X e Y, subir/bajar Z ±1 con ±1 en un eje; el inicio puede tener cualquier decimal y se conserva. Claude no desplaza con keyframes a mano: usa detect_movement_type/group_segments/generate_*. Ejemplo: `Desktop/recorrido.json` (copia en cada skill). Ver [[feedback_alfred_desplazamiento_a_b]], [[feedback_jerry_desplazamiento_a_b]], [[feedback_rat1_desplazamiento_a_b]], [[feedback_chicken1_desplazamiento_a_b]].
