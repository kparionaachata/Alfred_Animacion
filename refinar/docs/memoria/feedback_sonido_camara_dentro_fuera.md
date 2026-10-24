---
name: sonido-camara-dentro-fuera
description: Regla de mezcla: sonidos de zombies/exterior bajan de volumen cuando la camara esta dentro del refugio
metadata:
  type: feedback
---

Los sonidos que vienen de afuera del refugio (pasos y voces de zombies, rasguños) se escuchan normal cuando la camara esta afuera y con menos decibelios (usé factor 0.30 ≈ -10.5 dB) cuando la camara esta adentro; la transicion sigue la posicion de Camera.001 (en la parte 5: f88-112).

**Why:** Kebyn lo pidio explicitamente al sonorizar los zombies de la parte 5 (2026-10-07).
**How to apply:** `alfred/refinar/docs/acciones/sonorizar_escena.py` (PARAMS: factor_dentro, x_pared=-94, paso_fuera...) calcula el volumen por frame; ajustar ahi. Para otras partes, cambiar la funcion `camara_x`. Ver [[project_sonidos_minecraft]].
