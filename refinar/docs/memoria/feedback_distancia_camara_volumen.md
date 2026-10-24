---
name: distancia-camara-volumen
description: Parte 7: el volumen de voces y sonidos baja hasta 0.5 segun la distancia personaje-camara (distancia_camara.py, enganchado al ducking)
metadata:
  type: feedback
---

El usuario pidio (2026-10-09) "efecto Doppler" entre la camara y los personajes: al alejarse baja el volumen, **maximo 50 %**, para dar realismo. Implementado como atenuacion por distancia (sin pitch, el VSE no lo tiene): `alfred/refinar/docs/acciones/distancia_camara.py` (D_CERCA 4.0, D_LEJOS 12.5, MIN 0.5), activado con `scene["distancia_camara"]=True`.

**Why:** realismo del audio; la camara de la parte 7 esta quieta/lenta y los personajes van y vienen.
**How to apply:** `ducking_voces.py` ya lo llama al final, asi que cualquier script de voz/sonido que termine en el ducking reaplica la distancia. Si se re-sonoriza (sonorizar_parte7.py) o se cambian voces, basta con que corra el ducking. Para otras partes: poner la propiedad de escena y revisar el mapa de duenos/raices (`RAIZ`). Relacionado: [[voces-ducking-suave]], [[sonido-camara-dentro-fuera]].
