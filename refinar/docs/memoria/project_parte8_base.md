---
name: parte-8-base-frame-751
description: base_parte_8.blend = estado del frame 751 de la parte 7 (todos quietos) fijado como frame 1; como se hizo y gotchas
metadata:
  type: project
---

2026-10-10: `capitulos/capitulo_4/base_parte_8.blend` = frame **751** de `base_parte_7.blend` (guardado 10-09 18:50, ya con voces, parpadeos y distancia a camara) como frame 1, sin acciones/NLA ni tiras del VSE (144 quitadas). Elegi f751 y no f728 (fin de escena) porque Jerry sigue saltando/corriendo hasta f745 (en f728 esta en el aire); a f751 todos estan quietos: alfred (-109.48,-85.46,15.07) caido, jerry (-107.5,-80.5,15.0), creeper_1 (-108.5,-88.05,15.48), chicken_1 (-109.49,-82.46,16.01); camara Camera.001 en (-108.6,-92.5,17). Hecho headless (Blender 5.2, sin tocar el original) con `alfred/refinar/docs/parte8/crear_base_parte_8.py` (mismo metodo que [[parte-7-base-frame-1265]]); verificados 791 valores identicos a f1 y f400 vs f751 original. Rango de escena sigue 1-728; la propiedad `scene["distancia_camara"]` se conserva (ver [[distancia-camara-volumen]]).

**Gotcha:** el driver de `hide_*` de `creeper.head.sadb_creeper_1` llevaba `or frame<300` (oculta la cabeza antes de f300 de la parte 7): el script lo quita con regex, si no la cabeza del creeper salia oculta en f1.
**Why:** el usuario arranca la parte 8 donde terminó la 7.
**How to apply:** para la parte 9 repetir con la ultima base y el frame en que todos queden quietos; revisar drivers que dependan de `frame`.

**Parte 8 trabajo (2026-10-10, escena viva base_parte_8.blend sin guardar):** tunel de Alfred desde (-104.5,-69.5,9) hacia el oeste hasta la cueva natural (x -126..-120): scripts en `alfred/refinar/docs/parte8/` (`tunel_plan.json`, `tunel_alfred_parte8.py`, `tunel_geometria_parte8.py` [una sola vez: borra caras de a.001/Stone], `tunel_eventos.json`) y `jerry/refinar/docs/tunel_jerry_parte8.py`; f1-805. Pala = clip pala_pozo f893-906; pico = ciclo del hacha f1026-1037; piedra solo en (-120,-65,10-11). Orden: alfred -> geometria -> jerry. Mundo: mallas por tipo de bloque con solo caras expuestas; verificacion visual con renders en vacio (ocultar mundo y tunel; las claves de hide se pisan al renderizar: quitar la accion). Pendiente: camara, sonidos, voces, parpadeos/filtros de la parte 8.

**Etapa 2 (2026-10-10):** Alfred sigue hasta (-128.5,-67.5,9) (techo de galeria diagonal; ruta en `tunel2_ruta.json`, `aplicar(etapa2=True)`, fin f1284). Para regenerar TODO: `bpy.ops.wm.open_mainfile` de base_parte_8.blend, luego alfred -> geometria -> jerry (la geometria borra caras originales, no repetir). Lag de Blender: tenia una vista en Material Preview (pasada a Solido); NUNCA hacer escaneos de miles de `scene.ray_cast` en la sesion viva tras editar mallas (la colgo): usar Blender en segundo plano sobre una copia.

**VERSION FINAL (2026-10-10):** el recorrido anterior se borro; ahora `tunel_recto_parte8.py` (recto de (-106.5,-69.5,9) a (-131.5,-69.5,6), f1-770, solo Alfred). Regenerar: open_mainfile base_parte_8.blend -> exec tunel_recto_parte8.py + construir_recto() + _aplicar_tl(fin) -> tunel_geometria_parte8.py.

**Base limpia (2026-10-10):** el usuario guardo `base_parte_8.blend` CON un tunel anterior (caras originales ya borradas): para regenerar partir de `capitulos/capitulo_4/base_parte_8_limpia.blend`. Geometria con `SKIP_CARAS_X=-131, HULL_X=(-120,-130)` (cascaron de tierra/piedra en la cueva).

**Actualizacion:** la base para regenerar es `capitulos/capitulo_4/base_parte_8_sin_tunel.blend` (no guardar sobre ella; el usuario guarda sobre lo que tenga abierto y asi se ensucio `_limpia`). Geometria con `SKIP_CARAS_X=-131, HULL_X=(-120,-132)`.
