---
name: herramienta-mano-derecha
description: Valores fijos de ubicacion/rotacion/escala de cualquier herramienta o arma en la mano derecha de Alfred (Child Of Rightelbow_alfred)
metadata:
  node_type: memory
  type: feedback
---

Toda herramienta o arma que Alfred lleve en la MANO DERECHA debe tener (transformacion local del objeto con Child Of 'Mano' al hueso `Rightelbow_alfred`): Location (0.21937, 0.32673, -0.001575) m, Rotation XYZ Euler (7.9831°, 17.876°, -56.916°), Scale 0.82 (captura del usuario del stone_axe, 30 oct).

**Why:** el usuario coloco el hacha bien en la mano a mano y quiere ese mismo agarre para cualquier herramienta/arma en la derecha.

**How to apply:** constante `HERR_MANO_DER` en `capitulos/capitulo_4/bonobos_madera_alfred.py` (HACHA_LOC/ROT/ESC); al tallar, el punto del sprite que cae en la mano (`HACHA_AGARRE`) sale de esa misma pose. Ver [[project_video_bonobos_tala]].

**Reglas aprendidas (30 oct):** los valores solo valen cuando la tiene en la mano; los hachazos son otra animacion (el hacha sigue el pico del clip, cabeza al tronco); nunca invertida (con el brazo levantado se gira sobre la mano para que la cabeza apunte arriba); no regenerar todo para cambiar valores. Detalle en la skill `herramienta-mano-derecha`.
