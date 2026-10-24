---
name: voces-ducking-suave
description: Las voces de Alfred solo bajan unos pocos dB los sonidos del juego (no los tapan del todo)
metadata:
  type: feedback
---

Las voces de los personajes mandan sobre los sonidos del juego, pero SOLO bajandolos unos pocos decibeles (x0.56 = -5 dB), no al minimo: Kebyn necesita seguir oyendo las acciones y los sonidos de las entidades mientras Alfred habla (2026-10-07, corrige el -20 dB inicial).

**Why:** el ducking a x0.10 casi borraba pasos, golpes y voces de zombies durante los dialogos.
**How to apply:** `alfred/refinar/docs/acciones/ducking_voces.py` (variable `DUCK`, por omision 0.56); se aplica solo al final de `aplicar_secuencia.py` y `aplicar_sonidos_directo.py`. Ver [[sonido-camara-dentro-fuera]].
