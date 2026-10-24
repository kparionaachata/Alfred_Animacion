---
name: addon-tunel-alfred
description: Panel "10 Tunel (cavar)" del Alfred Animation Studio: dado inicio y final crea el tunel + animacion de Alfred (pala/pico) + caras del mundo
metadata:
  type: project
---

2026-10-10: `alfred/refinar/alfred_animation_studio/tunel.py` + `tunel_ops.py` (panel 10, `scene.alfst_tunel`, ops `alfst.tunel_crear/quitar/cursor`). Automatiza lo hecho a mano en la parte 8 (ver [[parte-8-base-frame-751]]): ruta recta, rayos para celdas solidas, poses portables de pala (`pala_pozo`) y pico (ciclo del hacha), tapas/caras/cascaron de tierra y piedra, final abierto, anclas en el guion. `quitar` restaura las caras del mundo.

**Why:** el usuario pidio que todo fuera automatico y conectado al flujo del estudio.
**How to apply:** probar cargando el paquete con `importlib` (`alfst_test`) y `register()`; trabajar en `capitulos/capitulo_4/base_parte_8_trabajo.blend` (copia de `respaldo/base_parte_8_ORIGINAL_sin_tunel.blend`, que no se abre en vivo porque el usuario guarda encima). Nunca escanear miles de rayos en la sesion viva; la geometria se calcula antes de poner claves y excluye mallas con rig (un primer intento borro caras de Alfred).

**Actualizacion (2026-10-10):** v2.3.0 instalada en `AppData/Roaming/Blender Foundation/Blender/5.2/scripts/addons/alfred_animation_studio` (sincronizada desde la fuente `refinar/alfred_animation_studio`, que es la mas nueva; la fuente manda) y `refinar/alfred_animation_studio.zip` rehecho. Tras cambiar `tunel.py`, copiar a la instalada y al zip. Cambios clave: bloques centrados (el cubo de bloques_dinamicos parte de la base), solo pico, rellenar aire, saltos con z entera, suela +0.0145.
