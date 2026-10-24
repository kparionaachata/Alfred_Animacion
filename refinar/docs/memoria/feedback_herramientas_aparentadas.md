---
name: herramientas-aparentadas-espalda-alfred
description: Herramientas/armas de Alfred van aparentadas al hueso Spine1_alfred (como alfred.blend); al sacar/guardar hay anim de brazo atras + aparentar/desaparentar (Child Of con influencia keyed)
metadata:
  node_type: memory
  type: feedback
  originSessionId: 8fcd90fa-7269-48e9-8b7f-24c25e8d8caa
  modified: 2026-10-08T17:22:18.256Z
---

Las herramientas y armas de Alfred van emparentadas al hueso `Spine1_alfred` de la espalda (alfred.blend: parent_type BONE, parent inverse identidad; `stone_axe` pegada a la malla del torso ~0.002, `wooden_pickaxe` 0.039, `wooden_axe` 0.107). Cada vez que Alfred saca o guarda una en la espalda: animar el brazo hacia atras y aparentar/desaparentar la malla (mano <-> espalda) para que se mueva en sincronia con el personaje.

**Why:** el usuario lo exigio (2026-10-08) tras ver herramientas flotando lejos de la espalda y siguiendo claves horneadas en vez del personaje.
**How to apply:** usar 2 constraints Child Of por herramienta (`Espalda` -> Spine1_alfred, `Mano` -> Rightelbow_alfred) con la influencia keyed (constante) y el basis relativo; `docs/acciones/alfred_herramientas_aparentadas.py` y `rel_espalda_alfred_blend.json` (alfred/refinar). No hornear matrices de mundo para herramientas que viajan con Alfred. Ver [[project_parte5_base]] para el origen de la escena.

**Actualizacion 2026-10-08 (regla repetida por el usuario):** al USAR una herramienta se aparenta al hueso que la usa (hacha -> `Rightelbow_alfred`, nunca claves de matriz por frame): Child Of `Mano` con `basis` CONSTANTE (agarre rigido, `acciones/agarre_hacha_alfred.json`); al guardarla se desaparenta y vuelve a `Espalda` en el frame en que el brazo llega atras. Sin mezclas "volando". Gotcha: `stone_axe.rotation_mode` debe ser `QUATERNION` (las claves de basis son cuaterniones; en XYZ se ignoran). Pendiente: mesa de crafteo f569-662 aun con basis por frame. Animacion del brazo del usuario guardada en `acciones/animacion_brazo_derecho_espalda.json` (borro los .py de Descargas).
**Valores del hacha en uso (usuario, 2026-10-08):** basis Child Of `Mano`: loc (0.17911, 0.43506, 0.043194), quat WXYZ (0.925, -0.015, -0.126, -0.356), escala 0.6 — usar siempre estos al empuñar `stone_axe`.
