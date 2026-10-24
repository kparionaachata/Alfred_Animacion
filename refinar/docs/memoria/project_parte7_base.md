---
name: parte-7-base-frame-1265
description: base_parte_7_estatica.blend = end state (f1265) of part 6 baked static as frame 1; made headless on a copy because Blender auto mode blocks destructive edits in the live scene
metadata:
  node_type: memory
  type: project
  originSessionId: 8fcd90fa-7269-48e9-8b7f-24c25e8d8caa
  modified: 2026-10-09T11:33:41.841Z
---

2026-10-09: `capitulos/capitulo_4/base_parte_7_estatica.blend` = frame 1265 of part 6 as static frame 1, no actions/NLA, no VSE strips (241 removed), creeper head driver fixed (no `frame<1035`). Built headless on a copy of base_parte_7.blend by `alfred/refinar/docs/parte7/crear_base_parte_7.py` (same method as [[parte-2-base-frame-860]] and [[parte-5-base-frame-1236]]). Verified 721 values identical at f1 and f600 vs original f1265. Live session and base_parte_7.blend were NOT modified. Scene range still 1-1265.

**Why:** the user starts part 7 from where part 6 ended; the live-scene delete of actions/strips via the Blender MCP was blocked by the permission classifier ("Irreversible Local Destruction"), so the safe route is a copy + save-as.
**How to apply:** for future "bake state as frame 1" requests do it headless on a copy and save a new file; don't attempt bulk deletes in the live session. The user must open the _estatica file (or ask explicitly to apply it live).

**Parte 7 timeline (2026-10-09, escena viva base_parte_7.blend, sin guardar):** Jerry corre f1-151, Alfred aparece f131/corre/se tuerce el tobillo f182, se soba hasta f383; creeper camina desde f300, susto de Alfred f384-419, lanza el pollo f420-470 (golpe f440); pollo choca de espaldas con el tronco f456, cae boca abajo y se queda tumbado (z 15.88 de cadera de pie de Alfred, suelo del tronco z 16); Jerry regresa a f310 al punto (-107.5,-86.5,15), se sienta, ve al creeper f374, se tira boca abajo f382, f525 (cuando Alfred ya esta de pie) se sienta mirando al creeper y se para f558-567; Alfred se levanta cojeando f494-524. Orden de scripts Alfred/pollo: corre_tobillo -> ve_creeper -> tira_pollo -> pollo_atrapado -> se_levanta_cojeando; Jerry: jerry_recorrido_parte7 -> jerry_regresa_y_se_cubre_parte7. Gotcha: view_layer.update() con poses manuales se pisa si ya hay claves nuevas del mismo script; calcular todo antes de insertar claves.

**Update 2026-10-09 (cont.):** Alfred se cubre la cara f440-481 y levanta la cabeza f481-489 (alfred_tira_pollo_parte7.py, FIN 493), se levanta cojeando f494-524, se acerca cojeando al creeper f525-708 (alfred_se_acerca_cojeando_parte7.py); Jerry se para f558-567 y se acerca f568-686 (jerry_se_acerca_parte7.py). Los scripts posteriores se ejecutan despues de los anteriores (cada uno borra sus claves hacia delante).

**Update (cont. 2):** creeper convulsiona/brilla f668-721 (creeper_convulsion_parte7.py, pose tumbada rx 90); Alfred se asusta f671 y huye por alfred_2.json f681-711 (alfred_huye_parte7.py); Jerry brinca f671 y huye por jerry_2.json f679-745 (jerry_huye_parte7.py, salta en f717-731). Alfred y Jerry aproximacion: ambos miran siempre a LOOK=(-108.5,-89.7,15.5).

**Update 2026-10-10 (estado para retomar en otra cuenta):** la escena viva `base_parte_7.blend` lleva TODO sin guardar si el usuario no lo guardo. Hecho tras lo anterior: sonidos (`sonorizar_parte7.py`), filtros organicos + parpadeos (`filtros_organicos_y_parpadeos_parte7.py` y `parpadeos_basicos_parte7.py`, este SIEMPRE despues de las voces), voces Alfred (f136, f187, f386, f596 "Pues para eso que no.", f675 "Corre...!") y Jerry (f30, f274, f379, f526 con cara, `VozJerry_que_raro`), Jerry sin `scull` en el acercamiento + mira al creeper con `spine_2` (`jerry_sin_scull_acercamiento_parte7.py` -> `jerry_mira_creeper_parte7.py`), atenuacion por distancia a camara (`distancia_camara.py`, enganchada al ducking, ver [[distancia-camara-volumen]]). Cada cambio esta documentado en `alfred/refinar/docs/GUIA_ANIMACION_ALFRED.md` y `jerry/refinar/GUIA_ANIMACION_JERRY.md` (leer las ultimas entradas para ver el estado). Pendiente ofrecido: `scull` sigue rotando en f313-384 y f526-564 (Jerry); quitar `entity.player.hurt` de f182 si suena duplicado.
