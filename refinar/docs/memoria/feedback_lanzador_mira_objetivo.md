---
name: feedback_lanzador_mira_objetivo
description: El personaje que lanza un objeto a otro mueve la cabeza y dirige la mirada al objetivo; skill lanzador-mira-objetivo (siempre)
metadata:
  type: feedback
---

El usuario (30 oct) pidio una skill, aplicable siempre: todo objeto lanzado hacia otro personaje exige que el lanzador mire a su objetivo (cabeza y mirada). Skill `lanzador-mira-objetivo` (proyecto y global, zip en la raiz, linea en CLAUDE.md).

**Why:** que los lanzamientos se vean naturales y con intencion.

**How to apply:** yaw/pitch calculados desde posiciones reales cabeza->objetivo; giro 8-12 f antes de la anticipacion, bloqueado hasta ~6 f tras soltar, sigue el impacto 10-20 f y vuelve suave; si pasa de ~70 grados gira tambien el torso. Ver [[feedback_inercia_accion_reaccion]], [[feedback_monos_bloqueados]].
