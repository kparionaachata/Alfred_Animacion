---
name: biblioteca-animaciones-alfred
description: "Catalogo de codigos de animacion\\alfred (164 archivos): formatos, API execute_animation, familias y objetos para reciclar animaciones de Alfred"
metadata:
  node_type: memory
  type: reference
  originSessionId: 22c3d667-c653-48cb-ab35-244ae3a40749
  modified: 2026-10-29T17:48:39.332Z
---

Carpeta `C:\Users\user\Desktop\Alfred_Animacion\codigos de animacion\alfred` (leida 2026-10-29). Rig comun: armature con hueso `Hips_alfred` (22 huesos: Hips, Spine, Spine1, Spine2, Neck, face, L/R UpArm, L/R elbow, L/R UpLeg, L/R knee, no_bone_01..08) + root = empty padre `alfred`; Alfred mira a +Y local; fps 24; rotation_mode XYZ.

**Formatos / API**
- Moderno `PAYLOAD` (113 archivos; `LEEME_parte2/6/7/cueva3.md`): `execute_animation(start_frame=<frame original>, origen='actual'|'escena')`. 'actual' = parte de donde esta Alfred ahora (root relativo); 'escena' = posicion absoluta original. Incluye huesos + root + objetos (`PAYLOAD['objetos']`, tipos 'aparentado' Child Of al hueso o mundo relativo al root) que se anaden solos desde `objetos/*.blend` si faltan. Sin voz/ojos/parpadeo/audio; ya llevan filtros organicos. Estado "sin aprobar". Un .py por tramo: `NN_nombre_<escena>_alfred.py`.
- Mixamo `KEYFRAME_DATA` (37, prefijo `slot_001_`, ene-feb 2026): `execute_animation(player_parts, start_frame=1, end_frame=N)`; 14 huesos euler, busca `Armature` y root `alfred`. Algunos 22 huesos (slot_001_alfred_5, correr, gesto_sentarse).
- Catalogo (PAYLOAD con bones/root/eyes/geometry, 22 huesos): `execute_animation(player_parts=None, start_frame=1, end_frame=None)`; `catalogo_alfred_exportado.json` los indexa (100style Elated/Depressed, neuronales 'Generada' correr/saltar/camina triste, gestos aprobados asentir/negar/curiosidad/reverencia, 6 emotecraft en `emotecraft_pendientes/` firma `(start_frame=1,end_frame=None,preserve_pose=False)` pending_review).
- Otros: sentarse/sentado_tirar_herramientas (13 huesos, `execute_animation(start_frame, yaw_deg, location)`), llevar_brazo(s)_espalda (4 huesos, solo brazo), parado_manos_cintura (pose), slot_1_caminar_llanura_animated (procedural), sentado_cansado (144f).

**Contenido por escena (frames)**: parte2 nadar/escalera/refugio (ruta_2A), parte5 empuja_zombie_bebe_con_palo, parte6 dormido_en_pozo/mira_alerta/se_levanta/rompe_mesa/salta_fosa/talla_puerta/huye_creeper, parte7 corre/tobillo/pollo/creeper/cojea, ruta_I susto tras arbol, ruta_K cama (dormir/girar/caer/sentarse, 23 tramos), ruta_M acantilado/salto/nada crol (13), ranas2 boxeo/combate vs rana (21 tramos: guardia, orbita, jab, patadas, combos), cueva3 picar hierro/lanzar/caer (10), ruta_4A craftea pala, slot_001 base Mixamo (caminar_1/2/6, correr, saltar_*, nadar, caidas, levantarse, arrodillarse, arrastrarse, lanzar, recoger, mirar, saludo, parado_1/2, cojear, boxeo, sorpresa...).
Objetos (`objetos/`): herramientas_espalda_*.blend, herramientas_madera/piedra, mesa_de_crafteo, cama_ruta_K, pollo, refugio_parte2, mineria_cueva3, crafteo_pala, stick_parte5, bloques_puerta.
Exportadores: `generador de animaciones/alfred/refinar/docs/acciones/exportar_animaciones_alfred_*.py`.
Alfred del rig importable: `estructura_lista\alfred.blend` (objetos alfred, Armature, Mesh_*_alfred, ojos, herramientas).
