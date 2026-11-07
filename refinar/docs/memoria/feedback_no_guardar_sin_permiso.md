---
name: feedback-no-guardar-sin-permiso
description: Nunca guardar el .blend (ni copias con save_as_mainfile copy=True para hornear) sin autorizacion explicita del usuario
metadata:
  node_type: memory
  type: feedback
  originSessionId: 8e82a5cf-5d90-4d65-ac01-fa6ec5963909
  modified: 2026-11-06T18:28:34.571Z
---

No guardar nunca sin autorizacion: ni el archivo del usuario ni copias (save_as_mainfile(copy=True)) para hornear en segundo plano.

**Why:** el usuario se enfado mucho (6 nov 2026) al ver guardados que no habia autorizado, aunque eran copias en el scratchpad para los horneados headless de la tela.

**How to apply:** si hace falta recalcular la fisica (horneado headless que necesita una copia guardada), pedir permiso antes de guardar la copia. Complementa [[feedback-no-pedir-guardar]] (no recordarle que guarde su archivo).
