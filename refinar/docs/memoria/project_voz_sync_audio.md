---
name: voz-sync-audio-y-estudio-expresion
description: Add-on Alfred Voz Sync (voz+emocion -> cabeza/mandibula) y la app estudio_audio_expresion (Whisper + emocion aprendida); etiquetas aprobadas por el usuario
metadata:
  node_type: memory
  type: project
  originSessionId: bc5111ce-f461-4c43-8762-8518fd54bd30
  modified: 2026-10-03T11:36:47.484Z
---

Dos sistemas de audio conviven en el proyecto (oct 2026):

- **Add-on `capitulos/capitulo_4/alfred_voz_sync/`** (mio, v1.2, zip al lado): lee `audios/alfred|jerry/*.mp3`, mueve mandibula (Jerry) y cabeza (ambos) con el volumen y pone la emocion como capa NLA aditiva; contexto opcional en `<audio>.emocion.json` (texto, emocion, segmentos, palabras). Flujo del usuario: sube mp3, me dice archivo + frame de inicio, yo sincronizo en Blender.
- **App del usuario `estudio_audio_expresion/`** (Gradio en 127.0.0.1:6972): Whisper Base local + prosodia (librosa) + memoria de ejemplos aprobados; solo genera expresion de OJOS de Alfred (shape key `Audio_procedural`). Emociones: alegria, tristeza, enojo, sorpresa, cansancio, duda, neutral.

**Etiquetas aprobadas por el usuario (verdad de terreno):** `audios/alfred/fdfdfdfff.mp3` = "Y ahora, ¿que hacemos?" -> DUDA. "Record (online-voice-recorder (mp3cut.net).mp3" = "Oye, no me vengas con tonterias" (Whisper Base lo oyo "no me venga junto en terias") -> ENOJO.

**Why:** el usuario quiere que la emocion salga de entender palabras + tono; yo no oigo audio, asi que la transcripcion y las etiquetas aprobadas son la fuente.
**How to apply:** al sincronizar un audio, buscar su etiqueta en `estudio_audio_expresion/aprendizaje/aprobaciones.jsonl` o en plan.json antes de adivinar; falta la emocion DUDA en el add-on (la app la tiene, el add-on no). Reiniciar la app tras editar su codigo (el servidor guarda la version vieja en memoria).

**Update 2026-10-03:** Jerry's reply = `audios/jerry/dsdsdsdaa.wav` ("Bueno, me echare a dormir hasta manana", app labeled it `duda`, probably really sueno) + `Downloads/animacion_jerry.py` (app's destructive face script). Add-on v1.5 imports such scripts WITHOUT executing them (`herramientas/importar_script_jerry.py` -> `.cara.json` tipo jerry) and plays them as additive layers; placed at f87 (speech f114-158, right after Alfred's f50-100).

**Camara parte 3 (2026-10-04):** `docs/parte3/camara_parte3.py` hornea la camara de `base_parte_3.blend` por fases (elegir/hornear/validar) a partir de `camara_muestras.json` (cara de cada personaje y tramos de habla por voz): primeros planos de quien habla, cortes en pausas del dialogo si el giro > 38 grados, empuje lento, DOF. Rehacerlo si cambian voces o animacion (resamplear la cara por frame). La sala es 2x2 m: camara dentro, lente = k x distancia para que la cabeza ocupe ~60 % de la altura.

**Gotcha NLA (2026-10-04):** las pistas `VozBase_*` (REPLACE+HOLD) deben ir DEBAJO de todas las `VozSync_*` o la de un audio posterior borra la capa aditiva de los anteriores (los ojos solo funcionaban en el ultimo audio). Ya corregido en el add-on (`sostener_estaticos` con `nla_tracks.new(prev=...)`). La oscilacion del habla de Alfred (`habla` en `<audio>.cara.json`, de `importar_script_alfred.py`) va en los objetos de los ojos; la cabeza se filtra (`suavizar_cabeza` = 2 frames) para que no vibre.

**Parte 6 (2026-10-08):** voces sin el add-on (la escena viva no usa NLA VozSync): `alfred/refinar/docs/acciones/voz_alfred_golpes.py` (quejido de Alfred en f165/f207, tira `VozGolpe_*`, sin ojos porque duerme) y `jerry/refinar/docs/voz_jerry_despierta.py` (voz+cara de la app sumadas a la animacion existente desde f120, tiras `VozJerry_despierta_*`). Regla del usuario: la voz por ENCIMA en dB (volumen de tira 3.0 si la grabacion es baja) y los sonidos de la animacion solapados a la MITAD: tira con `duck_todos` + `ducking_voces.py` (DUCK 0.5). No ejecutar `animacion_jerry.py` de la app en la escena viva (borra claves de ojos).
