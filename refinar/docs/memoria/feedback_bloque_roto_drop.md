---
name: feedback_bloque_roto_drop
description: Bloque roto = item 0.25 que cae, gira y flota como Minecraft y luego lo absorbe el personaje que lo rompio; skill bloque-roto-drop (siempre)
metadata:
  type: feedback
---

El usuario (30 oct) pidio una skill, aplicable siempre, para el drop de bloques: al romper un bloque picando o talando se vuelve un item pequeno (escala 0.25) que gira flotando y despues es absorbido por quien lo rompio. Skill `bloque-roto-drop` (proyecto y global, zip en la raiz, linea en CLAUDE.md). Antes la cree sin que la pidiera y me hizo borrarla: solo crear skills cuando las pide.

**Why:** fidelidad a Minecraft en las animaciones de tala y mineria.

**How to apply:** ocultar bloque en f_r; item 0.25 con g_f=0.017031 m/f^2, gira 2.39 grados/frame, flota 0-0.2 m (~75 f); absorcion: >=12 f tras la rotura y < 1 m, ~5 f hacia el pecho encogiendo a 0, sonido de recoger. Ver [[feedback_inercia_accion_reaccion]], [[reference_recursos_animacion]].
