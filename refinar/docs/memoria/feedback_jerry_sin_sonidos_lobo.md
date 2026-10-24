---
name: jerry-sin-sonidos-lobo
description: Jerry tiene voz propia; no usar sonidos mob/wolf; un solo sonido de lanzamiento por herramienta
metadata:
  node_type: memory
  type: feedback
  originSessionId: 8fcd90fa-7269-48e9-8b7f-24c25e8d8caa
  modified: 2026-10-08T12:14:29.902Z
---

No poner sonidos de lobo (`mob/wolf/*`) a Jerry: es un personaje con su propia voz (Voz Sync JERRY). Un solo sonido de lanzamiento por herramienta lanzada (el latigazo de la cola), no varios encadenados.

**Why:** el usuario pidio quitar el gemido de lobo del estiramiento ("es jerry, tiene su propia voz") y dejar un unico sonido de lanzamiento por herramienta (2026-10-08).
**How to apply:** al sonorizar Jerry usar solo sonidos de objetos/pasos/golpes de `sonidos/sounds/`; para sonidos de boca/voz de Jerry esperar audio suyo. Ver [[project_jerry_antorcha]] para el resto de su flujo; la escena viva de la parte 6 tiene su estiramiento f120-250 en `Jerry_despierta_estira_f120` (armature `a.002`).
