---
name: trepa-pared-5e
description: "alfred_cueva_5E.blend: criatura salta al muro, trepa y llega bajo Alfred (f1-729); geometria del acantilado/plataforma y gotchas"
metadata:
  node_type: memory
  type: project
  originSessionId: f2dc8c8c-28c2-4950-8dad-f7d558faab3c
  modified: 2026-10-27T22:36:30.409Z
---

2026-10-27: `alfred_cueva_5E.blend` (base = f1011 de la 5D, `crear_base_cueva_5E.py`, camara tambien fija). Animacion de the_stalker_1 hecha en Python: `stalker_trepa_base.py` (FK/IK propias), `stalker_trepa_pared.py` (carrera, impulso f1-24, salto f46-66, aterrizaje, modular), `stalker_trepa_ruta.py` (muro -> esquina -> techo; fija F_FIN=729). Se ejecutan los 3 en un mismo ns: planear, preparar_plan, trayecto, resolver, escribir. Poses base en `poses5D.json`.

Geometria: acantilado vertical y=91.3 (z 12-63); a z=64-65 hay una plataforma (bloques sueltos `bloque_*`, tunel de la salida) que sobresale hasta y=83.3; Alfred (0.56, 84.07, 65.55) esta ENCIMA de la punta. La criatura acaba colgada del techo (cara inferior) justo debajo de el, no encima.

**Gotchas:** las mallas `bloque_*` tienen las normales hacia dentro (invertir orden de vertices en el BVH o la penalizacion de IK falla); los `caverna_*` solo tienen caras expuestas (rayos +Y desde dentro de roca dan falsos golpes); la vista 3D se queda congelada tras clip_end pequeno: usar render Workbench con camara temporal (`foto`) para ver.
**Why:** el usuario pidio que llegue a la coordenada de Alfred.
**How to apply:** si pide subir a la plataforma, falta envolver la punta (pitch 180->0) y ruta sobre la cara superior.
