# Estudio de animación del cerdo (cerdo_1) — portado desde el estudio de Alfred

Fecha: 2026-10-13. `cerdo_1_animation_studio/` es el estudio completo de Alfred adaptado al cerdo. Se registra **junto al de Alfred** sin choques:

| | Alfred | Cerdo |
|---|---|---|
| Propiedades de escena | `alfst`, `alfred_segs`, `alfred_path`, `alfst_bloques`, `alfst_tunel` | `cerdo_1_st`, `cerdo_1_segs`, `cerdo_1_path`, `cerdo_1_st_bloques`, `cerdo_1_st_tunel` |
| Operadores | `alfst.*`, `alfredpr.*`, `alfredseg.*` | `cerdo_1_st.*`, `cerdo_1pr.*`, `cerdo_1seg.*` |
| Pestaña | Alfred Studio | Cerdo 1 Studio |

## Cómo se generó (repetible)
`python portar_cerdo_1.py` (en esta carpeta). Siempre parte de la copia original de Alfred guardada en `_respaldo_copia_alfred/`, así que se puede volver a correr sin acumular cambios. Hace lo siguiente:

1. **Identidad.** Renombra clases, operadores, propiedades y archivos con el generador del proyecto (`creador_de_addon/generate_character_addon_v2.py`):
   - `generate_slots_alfred.py` → `generate_slots_cerdo_1.py`
   - `motor_alfred.py` → `motor_cerdo_1.py`

   La carpeta del proyecto `Alfred_Animacion` se protege y no se renombra.
2. **Rig del cerdo:**
   - raíz `cerdo_1`, armadura `pig.arma_cerdo_1`;
   - mallas `pig.Body/Head/Leg-FL/FR/BL/BR_cerdo_1`;
   - 16 huesos en `BONES_LISTA`. No incluye los 4 `Leg:*:IK`, que ya no controlan nada.
3. **Mapa anatómico** de las referencias a huesos de Alfred:
   | Alfred | Cerdo |
   |---|---|
   | brazos | patas delanteras (`Leg:FL/FR` + `:Bend`) |
   | piernas | patas traseras (`Leg:BL/BR` + `:Bend`) |
   | Hips | `Body` |
   | Spine | `Body:Bend` |
   | Neck / face | `Head` |
4. **Locomoción de cuatro patas** (en lugar de la de dos piernas). Ejes medidos en el rig: el cerdo mira a +Y; en las patas, X = adelante/atrás.
   - **Caminar y correr** (los 5 estilos: normal, lento, rápido, correr, herido):
     - las patas van en pares diagonales, FL + BR y FR + BL;
     - la parte baja de cada pata se dobla mientras va por el aire;
     - el cuerpo rueda y cabecea en cada paso, y al correr se inclina hacia delante;
     - en "herido", las patas derechas van débiles.
   - **Saltar subiendo, bajando y en horizontal:** poses propias de cuatro patas.
   - **Parado:** las patas delanteras rectas (el estudio de Alfred las ponía a 90°, como brazos).
   - **Dirección al encadenar tramos:** el tramo siguiente arranca con la dirección del **último paso**. Antes, en un camino en L, el salto empezaba mirando en diagonal y giraba de golpe; ese defecto también está en el estudio de Alfred.
5. **Tipos de tramo:** solo Caminar (auto), Saltar y Parada. Las acciones de Alfred quedan ocultas: cortar madera, antorcha, mesa, pared, levantarse, arrodillarse, conversar, golpe y resbalarse.

## Probado (Blender 5.2, en segundo plano, con `estructura_lista/cerdo_1.blend`)
- Se registra y se desregistra junto al add-on de Alfred, sin choques.
- **Reproducir recorrido:**
  - camina por un recorrido en L (gira de +Y a +X);
  - sube un bloque saltando y baja otro;
  - corre;
  - las patas van en diagonal (±30° al caminar, ±50° al correr).
- **Exportar:** escribe los slots `.py` (`slot_001_cerdo_1_caminar.py`, `slot_002_cerdo_1_saltar_bajar.py`…).
- **Paso 3:** Dividir segmentos crea un segmento por tramo, y Concatenar termina bien.
- Los paneles se dibujan sin errores.

## Pendiente / a tener en cuenta
- **Ojos:**
  - el cerdo no tiene mallas de ojos como Alfred (tiene los huesos `Eye-L/R` y la forma `Blink` en la cabeza);
  - el sistema de ojos y parpadeos del estudio no hace nada con el cerdo;
  - se puede conectar a `Blink` si hace falta.
- **Paneles con acciones de dos piernas:** Túnel (cavar), Movimiento por tramos (`motor_cerdo_1`) y los clips de Mixamo usan animaciones de dos piernas: con el cerdo no se ven bien.
- **Carpetas de datos copiadas de Alfred:** `poses/`, `configuraciones/`, `animaciones/`, `docs/`… en `refinar/` tienen datos de Alfred. Las poses de Alfred no sirven para el cerdo.
- **Biblioteca de clips:** la carpeta `codigos de animacion/cerdo_1` todavía no existe.

## Paso 1: las 3 animaciones básicas sobre bloques de 1 m³ (2026-10-13)
Para cualquier personaje, el recorrido debe tener **caminar, saltar subir y saltar bajar** (bloques de 1 m³). En el cerdo:

- **Cómo se elige la animación:** se detecta sola por la altura de los puntos (misma altura = caminar, un bloque más alto = saltar subir, un bloque más bajo = saltar bajar). El panel la muestra en cada punto ("Caminar", "Saltar subir (1 bloque)", "Saltar bajar (1 bloque)").
- **El cerdo es LARGO:** desde su origen, el hocico está 0.988 m adelante y las ancas 0.492 m atrás, y no cabe en una celda. Por eso:
  - **subir:** se detiene con el hocico a 6 cm del bloque, salta hacia arriba (~1.15 m) y después avanza encima; el hocico nunca entra en el bloque;
  - **bajar:** avanza hasta que las ancas pasan el borde y recién ahí cae; aterriza un poco más adelante del centro de la celda;
  - **caminar y saltar:** en cada frame se mide la esquina más baja real de las 4 pezuñas, y el cuerpo sube lo justo para que no se hundan en el bloque.
- **Medidas del cuerpo:** son constantes del personaje (`CUERPO_FRENTE`, `CUERPO_ATRAS`, `PEZUNAS` en `jump_motion.py` y en `generate_slots_cerdo_1.py`). Para otro personaje se cambian esas medidas.
- **Prueba con bloques reales:** suelo + escalón de 2 bloques; recorrido caminar → subir → caminar encima → bajar → caminar.
  - Las pezuñas quedan a 5 mm sobre el bloque al caminar, que es la altura de reposo del modelo.
  - Subir, estar encima y bajar: sin cruces con el bloque.
  - Solo en los 1–2 frames de transición entre tramos (la mezcla suave de poses del estudio) se hunde hasta 1.4 cm.
