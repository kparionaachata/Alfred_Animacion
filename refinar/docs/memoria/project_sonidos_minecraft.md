---
name: sonidos-minecraft-addon
description: "Add-on Alfred Sonidos y la carpeta sonidos/ de Minecraft (3855 ogg + sounds.json); como se usa para pasos, antorcha, impactos"
metadata:
  node_type: memory
  type: project
  originSessionId: 93e8129b-4209-416c-9fce-07d5d3cf9315
  modified: 2026-10-04T05:27:12.520Z
---

`C:\Users\user\Desktop\Alfred_Animacion\sonidos\` = sonidos originales de Minecraft (`sounds/` 3855 .ogg + `sounds.json` con 1642 eventos; `algoritmos/` doc Java; `ribbits/` mod ajeno). Add-on mio: `capitulos/capitulo_4/alfred_sonidos/` (v1.0.0, zip al lado, panel "Sonidos MC"): biblioteca de eventos, ~45 eventos del proyecto, pasos automaticos desde los pies, silbido/impacto de objetos lanzados, bucle de antorcha, mezcla WAV. Tiras `SND_<evento>_<frame>` en canales 10-40 (Voz Sync usa 2-3).

**v1.1.0 (2026-10-04) "como en el juego":** `resolver(ob)` reconoce cada objeto por nombre/padres/materiales/texturas (tablas `TIPOS_BLOQUE`, `ALIAS_MOB`; alfred=player, jerry/dog=wolf) -> eventos `block.<tipo>.*` / `entity.<mob>.*`; pasos de mobs con paso propio usan el suyo, Alfred la superficie bajo el pie (raycast; el suelo del refugio es pasto, objeto `a.001`); choques = superficie `fall` + material `hit`; aparecer/desaparecer = place/break. Los scripts `animacion/Prompt_*/alfred/slot_*caminar*.py` tienen su propio sistema viejo de pisadas (fase del ciclo, API rota en Blender 5.2), distinto de este.

**Why:** el usuario quiere sonorizar la escena segun lo que pasa sin buscar archivos a mano; yo no puedo oir, asi que la deteccion es por movimiento (z de la cola del hueso del pie, velocidad del objeto).
**How to apply:** para sonorizar, cargar el modulo desde su ruta con importlib (como Voz Sync), `bpy.ops.mcsnd.pasos/objetos/bucle/preset`; limitar el rango a donde camina; quitar con `mcsnd.quitar`. Sin pitch en Blender; no hay sonido de pico ni voz de Alfred. Relacionado: [[voz-sync-audio-y-estudio-expresion]].

**v1.3.0 (2026-10-04) automatico:** `bpy.ops.mcsnd.sonorizar(modo="TODO"|"NUEVO")` lee toda la animacion y pone pasos (solo tramos en que camina), contacto del cuerpo, silbido/choque de objetos y place/break, sin frames fijos; tope bajo las voces (v1.2, `techo_voces`: pico -8 dB, medio -3 dB vs la voz mas baja); "Solo lo nuevo" sigue desde `auto_hasta`. Tarda ~35 s en la parte 3 (si se llama por MCP junto con otras cosas puede dar timeout: llamarlo solo). `parte3/sonorizar_parte3.py` solo llama al operador.
