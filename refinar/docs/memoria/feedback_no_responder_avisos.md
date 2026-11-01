---
name: no-responder-avisos
description: No escribir mensajes al usuario por avisos automaticos de tareas/monitores; callar
metadata:
  node_type: memory
  type: feedback
  originSessionId: c6a6e7b4-4771-4c1c-8d93-6f565a693406
  modified: 2026-10-25T14:58:38.489Z
---

Ante notificaciones automaticas (task-notification, monitor terminado) no escribir texto al usuario.

**Why:** el usuario usa a Claude como herramienta; esos mensajes son ruido que no pidio.
**How to apply:** si no hay tarea pendiente, no responder nada o lo minimo; no comentar "es solo un aviso".
