---
name: creeper-parte6
description: Creeper importado en la escena viva de la parte 6; camina creeper.json desde f1035 y se para mirando al este
metadata:
  node_type: memory
  type: project
---

2026-10-08: el usuario pidio que el creeper (estructura_lista/creeper_1.blend, studio `creeper_1_animation_studio`) camine `Desktop/creeper.json` desde f1035 y quede parado con la misma orientacion final que Alfred (-450) y Jerry (270) = mirando al este (rz -90). Hecho con `alfred/refinar/docs/acciones/creeper_camina_y_se_para.py`: append de 10 objetos (root empty `creeper_1`, armature `creeper.arma_creeper_1`), oculto hasta f1035, marcha del estudio (72 f, f1035-1106), parada con giro f1107-1118, pasos de pasto. Sin aprobar; sin guardar el .blend.

**Why:** cierre de la parte 6 (el creeper aparece al final).
**How to apply:** si pide explotar, el estudio tiene `explosion_runtime.py` (36 f carga + 16 efecto, assets/creeper_explosion.blend); no habilitar el add-on, copiar su formula como con Alfred/Jerry. Ver [[project_alfred_workflow]].
