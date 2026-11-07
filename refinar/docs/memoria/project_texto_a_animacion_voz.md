---
name: project-texto-a-animacion-voz
description: "Sistema paralelo texto -> voz clonada -> rostro en \"de texto a animacion +voz\"; motor F5, juez WavLM, lecciones del 4 nov 2026"
metadata:
  node_type: memory
  type: project
  originSessionId: f8eb2c67-dfce-48ed-9ecd-44655aec23de
  modified: 2026-11-04T15:32:20.263Z
---

Sistema en `de texto a animacion +voz/` (texto_a_animacion.py, tts_f5.py, prosodia_palabras.py, config.json). No toca voz_a_voz ni estudio_audio_expresion (solo los usa).

- Voz base: F5-TTS Spanish (env_f5) con referencias del usuario en `referencias_usuario/<emocion>.wav` + textos.json exactos. Alfred SIN RVC (RVC bajaba el parecido 0.974->0.941); Jerry con RVC.
- Juez de tomas: Whisper (texto) + WavLM parecido con la voz real. Coincide con el oido del usuario: aprobada ~0.97, acento argentino 0.943, robotica 0.82-0.89.
- Lecciones: forzar duracion (fix_duration) = robotico; empalmar referencias cortas = cortado; recortar pausas internas = sin fluidez; referencias cortas (<10 s) = acento ajeno (argentino); Chatterbox latam = acento chileno; edge-tts = robotico.
- "Jerry" se escribe "Yeri" para F5 (6/6 correcto en experimento); pegar o empalmar el "Jerry" grabado del usuario lo empeoro (0/6).

**Why:** el usuario rechaza resultados mediocres y exige investigar/experimentar antes de entregar.
**How to apply:** medir con el juez varias configuraciones antes de enviar; solo enviar la mejor. Pendiente: arreglar Jerry (RVC sobre F5). Relacionado: [[feedback-obedecer-breve]].

Skill `texto-a-animacion-voz` (proyecto y global, 2026-11-05) integra este sistema al flujo de animacion; regla añadida en CLAUDE.md.
