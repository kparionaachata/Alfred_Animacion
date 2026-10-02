# Guía para integrar nuevos segmentos especiales (tipo "Colocar antorcha")

> Dirigida a cualquier IA/dev que tenga que agregar un segmento nuevo al
> addon Alfred Animation Studio siguiendo el mismo patrón que ya usan
> `COLOCAR_ANTORCHA`, `COLOCAR_MESA_CRAFTEO` y `GOLPE_ESTOMAGO_1`.
> Objetivo: que la integración de un segmento nuevo (ej. "Colocar cofre",
> "Tocar campana", "Sentarse") sea un ejercicio de **copiar el patrón y
> renombrar**, no de re-descubrir la arquitectura desde cero.

---

## 0. Vocabulario mínimo

- **Recorrido**: lista de `ALFREDPathPoint` que el usuario arma
  seleccionando faces del escenario en modo EDIT (Paso 1 del panel).
- **Segmento / tramo**: sub-animación autocontenida (caminar, salto,
  parada, colocar_antorcha...) que ocupa un rango de frames contiguo.
- **Slot**: el `.py` generado para UN segmento (`slot_NNN_<tipo>.py`),
  con `execute_animation()` embebido.
- **Override manual**: el usuario elige el tipo de segmento a mano desde
  un dropdown en el Paso 1, en vez de que el sistema lo infiera de la
  geometría (caminar/subir/bajar).
- **Punto "de destino"**: en los segmentos que colocan un objeto,
  `points[1]` es la coordenada real donde debe terminar plantado el
  objeto (NO es un punto duplicado — es la siguiente coordenada real del
  recorrido, salvo el caso especial de la sección 8).

---

## 1. Los dos sub-patrones que ya existen

Antes de tocar código, decidí a cuál de los dos se parece tu segmento
nuevo:

| Sub-patrón | Ejemplos | Root del personaje | ¿Coloca un objeto externo? |
|---|---|---|---|
| **A. Colocar objeto** | `colocar_antorcha`, `colocar_mesa_de_crafteo` | Fijo en `points[0]` todo el slot | Sí — vía el Sistema de Lanzar/Recoger/Mantener Objetos (`seg.throws`) |
| **B. Animación pura** | `golpe_estomago_1` | Fijo en `points[0]` todo el slot | No — solo reproduce una animación importada (Mixamo u otra) sobre el rig |

Si tu segmento nuevo coloca/aparece un objeto en escena → seguí el
sub-patrón A completo (todas las secciones de abajo). Si es solo una
animación corporal sin objeto → sub-patrón B (te salteás la sección 7 y
las partes de "destino"/`throws` de las secciones 5 y 9).

Ambos comparten **exactamente** la misma arquitectura de detección,
agrupamiento y generación — solo cambian: la pose (keyframes), la
duración fija en frames, y si hay o no objeto que registrar.

---

## 2. Mapa de archivos (qué toca cada uno)

```
path_recorder.py          Paso 1 (UI grabación) + _detect_move() + _group_segments()
                           + _expand_points_with_paradas() + calcular_estimacion_geometrica()
generate_slots_alfred.py  detect_movement_type() + group_segments() (duplicado en Python puro,
                           sin bpy — usado por operators_segments.py) + generate_<tipo>() +
                           KEYFRAMES_<TIPO> + constantes TOTAL_FRAMES_<TIPO>/MID_FRAME_<TIPO>
panels.py                 Dropdown del Paso 1 (tipo_segmento) + fila de icono +
                           panel "Estimación de segmentos" del Paso 2
operators_segments.py     ALFREDSEG_OT_AutoSplitFromConfig: auto-registro del AlfredThrowItem
                           cuando el tramo trae destino de objeto (torch_dest/table_dest-like)
operators_anim.py         apply_throw_item() / reproducción real del throw (objeto genérico,
                           no necesita cambios si ya seguís el patrón de object_folder
                           'bloques_dinamicos')
object_import_utils.py    import_bloque_dinamico_full() + aplicar_sufijo_numerico_anticolision()
                           (genérico, no necesita cambios — reutilizás lo que ya existe)
```

**Regla de oro repetida en TODO el código como comentario**: la lógica
de detección/agrupamiento vive **duplicada intencionalmente en 3
lugares** que deben coincidir siempre:

1. `_detect_move()` — `path_recorder.py`
2. `detect_movement_type()` — `generate_slots_alfred.py`
3. `_resolver_tipo_segmento_auto()` — `config_ops.py` (mismo criterio,
   usado al recalcular tipos al cargar una config guardada)

Y el agrupamiento en 2 lugares que deben coincidir:

1. `_group_segments()` — `path_recorder.py`
2. `group_segments()` — `generate_slots_alfred.py`

Si tocás uno, tocá el otro. El comentario `# Debe coincidir con...` en
el código apunta siempre al gemelo.

---

## 3. Paso a paso para agregar un segmento nuevo

Usá `COLOCAR_MESA_CRAFTEO` como plantilla de copiar/pegar/renombrar en
todos los pasos. Nombrar tu tipo nuevo en dos formatos consistentes:

- **Enum interno** (mayúsculas, snake_case): `MI_SEGMENTO_NUEVO`
- **String de tipo de segmento** (minúsculas, snake_case): `mi_segmento_nuevo`

### 3.1 — Enum del dropdown (Paso 1)

Archivo: `path_recorder.py`, clase `ALFREDPathPoint`, propiedad
`tipo_segmento` (línea ~82).

Agregar un item nuevo al `EnumProperty.items`:

```python
("MI_SEGMENTO_NUEVO", "Mi segmento nuevo",
 "Descripción corta de qué hace el personaje en este tramo. Abarca "
 "este punto y el siguiente (coordenadas reales, sin duplicar)",
 "ICONO_DE_BLENDER", 5),  # el numero al final debe ser unico y creciente
```

Elegí un ícono de Blender que represente la acción (`OUTLINER_OB_LIGHT`
para props tipo antorcha, `OUTLINER_OB_MESH` para props tipo mueble,
`ARMATURE_DATA` para animaciones puras sin objeto — o buscá otro que
encaje).

### 3.2 — Override en los 3 detectores (deben coincidir)

**`path_recorder.py` → `_detect_move(p0, p1)`** (línea ~708): agregar,
junto a los otros overrides, ANTES de la comparación geométrica:

```python
if getattr(p0, "tipo_segmento", "AUTO") == "MI_SEGMENTO_NUEVO":
    return "mi_segmento_nuevo"
```

**`generate_slots_alfred.py` → `detect_movement_type(p_current, p_next)`**
(línea ~1500): mismo override, mismo orden relativo:

```python
if p_current.get('tipo_segmento') == 'MI_SEGMENTO_NUEVO':
    return 'mi_segmento_nuevo'
```

**`config_ops.py` → `_resolver_tipo_segmento_auto()`**: replicar el
mismo criterio si esa función tiene su propia copia de la cadena de
overrides (revisar el archivo — a veces solo maneja PARADA; si no toca
overrides de "colocar_X", no hace falta editarla).

⚠️ **El override SIEMPRE va antes de la comparación de coordenadas.**
Así el segmento funciona sin importar si `points[0]`/`points[1]` son
iguales o distintos, y sin importar si el tramo real sería
caminar/subir/bajar.

### 3.3 — Agrupamiento (deben coincidir)

**`path_recorder.py` → `_group_segments()`** (línea ~835) y
**`generate_slots_alfred.py` → `group_segments()`** (línea ~1575):
agregar tu string nuevo a la tupla de tipos que comparten rama:

```python
elif move in ("colocar_antorcha", "golpe_estomago_1", "colocar_mesa_de_crafteo", "mi_segmento_nuevo"):
```

No hace falta tocar nada más de esa rama — ya incluye:
- el segmento del tipo nuevo con `points=[pts[i], pts[i+1]]`
- el chequeo de "misma coordenada" (ver sección 8 — CRÍTICO no saltarlo)
- la fusión con el caminar real que sigue, para que el walk-cycle no
  tenga un pop de piernas al reanudar (ver comentario largo en esa
  rama sobre el bug "piernas no abren bien en el 2do ciclo")

### 3.4 — Constantes de duración y frame de aparición

Archivo: `generate_slots_alfred.py`, junto a las constantes existentes
(línea ~2915-2960):

```python
TOTAL_FRAMES_MI_SEGMENTO_NUEVO = <N>          # duración fija del slot
MID_FRAME_MI_SEGMENTO_NUEVO = <M>             # frame donde ocurre "el momento clave"
                                               # (agacharse/soltar objeto/pegar golpe)
```

Si tu segmento vuelve a la pose de pie al final (como antorcha/mesa),
`TOTAL_FRAMES = M + RETURN_TO_PARADO_FRAMES` (constante ya existente,
mismo patrón). Si es una animación importada de duración fija completa
(como `golpe_estomago_1`, 100 frames de Mixamo), simplemente hardcodeá
el total.

### 3.5 — Keyframes (la pose)

Dos caminos, elegí el que corresponda:

**(a) Pose capturada a mano** (patrón antorcha/mesa): capturás una pose
intermedia (ej. "agachado colocando X") como `.json` de pose local-space
(mismo formato que `inclinado_colocando_antorcha.json`), y armás:

```python
KEYFRAMES_MI_SEGMENTO_NUEVO = {
    'Hips_alfred': {0: (...), 1: (...), ..., M: (...)},
    # ... los 14 huesos animables, frame 0 = POSE_PARADO, frame M = pose capturada
}
```

Y un builder que agrega el tramo de vuelta a parado interpolado en
smoothstep (copiar `_build_colocar_antorcha_keyframes()` renombrando):

```python
def _build_mi_segmento_nuevo_keyframes(walk_style_next=None):
    result = {}
    for bone, frames in KEYFRAMES_MI_SEGMENTO_NUEVO.items():
        bone_frames = dict(frames)
        start_val = frames[MID_FRAME_MI_SEGMENTO_NUEVO]
        end_val   = frames[0]
        for j in range(1, RETURN_TO_PARADO_FRAMES + 1):
            rel_frame = MID_FRAME_MI_SEGMENTO_NUEVO + j
            tt = _smoothstep_meta(j / RETURN_TO_PARADO_FRAMES)
            bone_frames[rel_frame] = tuple(
                start_val[k] + (end_val[k] - start_val[k]) * tt
                for k in range(3)
            )
        result[bone] = bone_frames
    return result
```

**(b) Animación importada completa** (patrón golpe_estomago_1): los
keyframes vienen de un archivo externo (Mixamo, etc.) ya convertido al
mismo formato `bone -> {frame: (x,y,z)}` en radianes, sin necesidad del
builder de "vuelta a parado" si la animación ya termina en una pose
neutral por sí sola.

### 3.6 — La función generadora `generate_<tipo>()`

Copiar `generate_colocar_mesa_crafteo()` (o `generate_golpe_estomago_1()`
si es sub-patrón B) completa y renombrar. Piezas que SIEMPRE hay que
mantener:

- `ROOT_LOCATION_DATA` **fijo** en `points[0]` (`{start_frame: p0, end_frame: p0}`)
  — el personaje NO camina hacia `points[1]` en este slot; ese
  desplazamiento lo hace el tramo "caminar" que `group_segments()`
  fusiona automáticamente después (sección 3.3).
- `ROOT_ROTATION_DATA` orientado hacia `points[1]` vía
  `_compute_direction_angle(p0, p1)` — el personaje gira para encarar
  el destino antes de actuar, aunque no se mueva.
- Si tu segmento coloca un objeto: usar
  `_compute_object_placement_target(p0, p1, root_rot)` (ver sección 8)
  para calcular el destino real del objeto — **nunca uses `points[1]`
  a pelo**, porque puede coincidir con `points[0]` en casos límite
  (punto reutilizado para otra cosa, ej. una Parada final).
- El nombre de la variable de destino y de frame de aparición debe
  seguir la convención `<OBJETO>_TARGET_COORDS` / `<OBJETO>_APPEAR_FRAME`
  (ej. `TORCH_TARGET_COORDS`/`TORCH_APPEAR_FRAME`,
  `TABLE_TARGET_COORDS`/`TABLE_APPEAR_FRAME`) — de ahí lo lee
  `operators_segments.py` en el paso 3.9.

### 3.7 — Router en `path_recorder.py` (reproducción en vivo / export)

Buscar los dos lugares donde el código despacha por `move_type`
(uno para "Reproducir recorrido" ~línea 2258, otro para exportar
`.py` sueltos ~línea 2856) y agregar tu rama:

```python
elif move_type == "mi_segmento_nuevo":
    code, end_frame = gen.generate_mi_segmento_nuevo(
        slot_index, current_frame, points, today, _cur_rot,
        walk_style_next=_walk_style_next)
```

### 3.8 — `calcular_estimacion_geometrica()` (path_recorder.py, ~línea 1064)

Agregar una rama para que el panel del Paso 2 pueda estimar
frames/destino ANTES de dividir en Paso 3:

```python
elif seg_type == "mi_segmento_nuevo":
    from .generate_slots_alfred import TOTAL_FRAMES_MI_SEGMENTO_NUEVO as _TFMSN
    slots.append({"slot": i + 1, "tipo": "mi_segmento_nuevo",
                   "label": "mi_segmento_nuevo",
                   "frames_estimados": _TFMSN})
    # si coloca objeto, agregar también "mi_dest": {"x":.., "y":.., "z":..}
    # calculado igual que _dest_mesa = seg_pts[1].coords (o con el mismo
    # helper de "adelante del personaje" si aplica, ver seccion 8)
```

### 3.9 — Auto-registro del objeto (solo sub-patrón A)

Archivo `operators_segments.py`, función `ALFREDSEG_OT_AutoSplitFromConfig`
(~línea 2077 y 2137 para los ejemplos existentes). Copiar el bloque
`if tipo == "colocar_mesa_de_crafteo":` completo y adaptar:

```python
if tipo == "mi_segmento_nuevo":
    _mi_dest = tramo.get("mi_dest")
    if _mi_dest is None:
        errores.append(f"Tramo {i} (mi_segmento_nuevo): sin coordenada de destino...")
    else:
        from .generate_slots_alfred import MID_FRAME_MI_SEGMENTO_NUEVO as _MFMSN
        _appear_frame = fs + _MFMSN
        seg.throws.enabled = True
        _titem = seg.throws.items.add()
        _titem.label          = f"Mi objeto (tramo {i:02d})"
        _titem.enabled        = True
        _titem.mode           = 'THROW'
        _titem.object_folder  = 'bloques_dinamicos'
        _titem.blend_filename = 'mi_objeto_1.blend'
        _titem.object_name    = 'mi_objeto_1'
        _titem.levels_up      = 4
        _titem.parent_armature = arm_obj.name
        _titem.parent_bone     = "Rightelbow_alfred"
        _titem.frame_start    = _appear_frame
        _titem.frame_end      = _appear_frame   # igual a frame_start = sin arco de vuelo
        _titem.target_armature = arm_obj.name
        _titem.target_bone     = "Rightelbow_alfred"
        _titem.dest_x = _mi_dest["x"]
        _titem.dest_y = _mi_dest["y"]
        _titem.dest_z = _mi_dest["z"]
        _titem.easing_global = 'EASE_OUT'
        _titem.transition_in  = 'NONE'
        _titem.transition_out = 'NONE'   # se queda plantado, no desaparece
```

El `.blend` fuente (`mi_objeto_1.blend`) tiene que existir en
`bloques_dinamicos/mi_objeto_1/` con un Empty raíz del mismo nombre —
la importación/renombrado secuencial anticolisión (para si el mismo
recorrido coloca el objeto más de una vez) ya la resuelve
`import_bloque_dinamico_full()` + `aplicar_sufijo_numerico_anticolision()`
en `object_import_utils.py` (**genérico, no tocar**), y la reproducción
del throw la maneja `apply_throw_item()` en `operators_anim.py`
(**genérico, no tocar** — solo revisar que `object_folder ==
'bloques_dinamicos'` fuerce reimportación siempre, línea ~1344, así
cada instancia colocada es un objeto nuevo en vez de reutilizar uno
existente).

### 3.10 — Panel del Paso 1 (icono junto al dropdown)

`panels.py`, dentro del bloque que dibuja cada punto de
"Coordenadas seleccionadas" (~línea 1657-1666):

```python
elif pt.tipo_segmento == "MI_SEGMENTO_NUEVO":
    row_pt.label(text="", icon="ICONO_ELEGIDO")
```

### 3.11 — Panel del Paso 2 ("Estimación de segmentos")

`panels.py`, dentro del `elif _fuente_est == "estimacion_geometrica":`
(~línea 1791-1813). **Este paso se olvida fácil — ver sección 9, es
exactamente el bug que ya pasó con `golpe_estomago_1`.**

```python
elif _s["tipo"] == "mi_segmento_nuevo":
    row_seg.label(
        text=f"  Segmento {_s['slot']}: mi segmento nuevo ({_s['frames_estimados']} f)",
        icon="ICONO_ELEGIDO",
    )
```

Tiene que ir **antes** del `else:  # parada` final de esa cadena —
cualquier tipo sin rama propia cae ahí y se muestra mal etiquetado como
"parada".

---

## 4. Checklist final (copiar/pegar y tildar)

```
[ ] 3.1  Enum item en ALFREDPathPoint.tipo_segmento           (path_recorder.py)
[ ] 3.2a Override en _detect_move()                            (path_recorder.py)
[ ] 3.2b Override en detect_movement_type()                    (generate_slots_alfred.py)
[ ] 3.2c Override en _resolver_tipo_segmento_auto() si aplica  (config_ops.py)
[ ] 3.3a Tipo agregado a la tupla en _group_segments()          (path_recorder.py)
[ ] 3.3b Tipo agregado a la tupla en group_segments()           (generate_slots_alfred.py)
[ ] 3.4  TOTAL_FRAMES_<TIPO> / MID_FRAME_<TIPO>                 (generate_slots_alfred.py)
[ ] 3.5  KEYFRAMES_<TIPO> + builder _build_<tipo>_keyframes()   (generate_slots_alfred.py)
[ ] 3.6  generate_<tipo>() completa                             (generate_slots_alfred.py)
[ ] 3.7a Rama en el router de "Reproducir recorrido"             (path_recorder.py, ~2258)
[ ] 3.7b Rama en el router de "Exportar recorrido"               (path_recorder.py, ~2856)
[ ] 3.8  Rama en calcular_estimacion_geometrica()                (path_recorder.py)
[ ] 3.9  Auto-registro de throws (solo si coloca objeto)         (operators_segments.py)
[ ] 3.10 Icono en el panel del Paso 1                            (panels.py)
[ ] 3.11 Rama en el panel "Estimación de segmentos" del Paso 2   (panels.py)  ← fácil de olvidar
```

---

## 5. Gotchas ya encontrados (leer ANTES de tocar código)

Estos son bugs reales que ya se dieron en este mismo sistema al agregar
segmentos nuevos — evitalos de entrada.

### 5.1 — El destino del objeto puede coincidir con el punto de partida

`points[1]` en teoría es siempre "la siguiente coordenada real", pero
en la práctica el usuario puede reutilizar la misma face dos veces
(por ejemplo para además marcar ese punto como Parada final del
recorrido). Cuando eso pasa, `points[0] == points[1]` y el objeto
quedaría plantado literalmente encima del personaje en vez de
"adelante".

**Solución ya implementada**: `_compute_object_placement_target(p0, p1, root_rot)`
en `generate_slots_alfred.py` (~línea 2962). Si los puntos son iguales
(redondeando a 2 decimales), calcula un punto sintético
`OBJECT_PLACEMENT_FORWARD_STEP` unidades adelante en la dirección hacia
la que el personaje está orientado. Si son distintos, devuelve
`points[1]` sin cambios. **Usar siempre esta función en vez de leer
`points[1]` directo** en cualquier generador nuevo que coloque un
objeto.

⚠️ Ojo con la convención de rotación de este rig: NO es la inversa
"ingenua" de atan2. Comprobado empíricamente contra
`_compute_direction_angle()` (la función ya usada y confiable en todo
el proyecto): `rz=-90` → personaje mirando hacia `+X`, `rz=90` → `-X`,
`rz=0` → `+Y`, `rz=180` → `-Y`. La fórmula correcta para ir de ángulo a
vector es `dx = -sin(rz)`, `dy = cos(rz)` (con el signo de `dx`
invertido respecto de lo que uno esperaría de un atan2 directo). Si
necesitás replicar este cálculo en otro lado, no lo reinventes — llamá
a `_compute_object_placement_target()`.

### 5.2 — Tolerancia de comparación de coordenadas: SIEMPRE 2 decimales

Las coordenadas que llegan de la selección de faces en el viewport
arrastran ruido de punto flotante y ruido geométrico real de la malla
del escenario (hasta ~0.01 en casos reales). Toda comparación
"¿son el mismo punto?" en este sistema usa `round(coord, 2)` — la
MISMA precisión que el panel le muestra al usuario en la lista
"Coordenadas seleccionadas". Si dos puntos se ven iguales en la lista,
tienen que clasificarse como el mismo punto en el código también. No
uses comparación exacta (`==`) ni 4 decimales — ya se probó
insuficiente dos veces.

### 5.3 — El tramo de "alcance" (caminar) hacia el destino es condicional

Cuando `points[i]` y `points[i+1]` (del segmento colocar_X) tienen la
misma coordenada, NO hay que generar el tramo "caminar" de alcance que
normalmente sigue al segmento — no hay distancia real que recorrer, y
generarlo igual produce un walk-cycle completo de distancia cero
(caminar "en el lugar", visualmente y auditivamente un segmento de más
que no debería existir). Este chequeo YA está en la rama compartida de
`_group_segments()`/`group_segments()` (sección 3.3) — si copiás esa
rama tal cual para agregar tu tipo nuevo a la tupla, lo heredás gratis.
No dupliques esta lógica a mano en otro lugar.

### 5.4 — El override de tipo_segmento se lee del punto ACTUAL, no del siguiente

`detect_movement_type(p_current, p_next)` / `_detect_move(p0, p1)` solo
miran `tipo_segmento` de `p_current`/`p0` — nunca de `p_next`/`p1`. Esto
significa que un punto solo "activa" su propio segmento especial cuando
le toca ser el punto de PARTIDA de una transición, no cuando es el
punto de llegada de la anterior. Si tu segmento nuevo necesita
comportarse distinto según el punto siguiente, vas a necesitar lógica
extra — no asumas que "estar marcado" alcanza en todos los casos, sobre
todo si tu punto es el ÚLTIMO de una cadena de "caminar" fusionada (ver
sección 3.3: el bucle de fusión SÍ vuelve a evaluar cada punto como
`p_current` en la siguiente vuelta del `while` exterior, así que esto
funciona correctamente siempre que sigas el patrón — es solo algo a
tener presente si escribís agrupamiento nuevo desde cero).

### 5.5 — Todo elif de "tipo de segmento" en los paneles necesita SU PROPIA rama

`panels.py` tiene dos listas separadas de `if/elif` por tipo de
segmento (Paso 1: ícono junto al dropdown; Paso 2: fila de la
estimación). **Cualquier tipo sin rama propia cae silenciosamente en el
`else` genérico, que asume "parada"** y lo etiqueta mal sin lanzar
ningún error — el bug pasa desapercibido hasta que alguien lo nota
visualmente en el panel. Si agregás un tipo nuevo, buscá TODOS los
`elif _s["tipo"] ==` / `elif pt.tipo_segmento ==` del archivo y
agregá tu rama en cada lista, no solo en la que "parece" relevante.

---

## 6. Cómo verificar rápido que la integración quedó bien (sin abrir Blender)

`_group_segments()`/`group_segments()` son funciones puras (no
dependen de `bpy` para la lógica de clasificación en sí, solo
`_group_segments()` recibe objetos `ALFREDPathPoint` reales). Se puede
simular con diccionarios simples para validar la secuencia de
segmentos antes de probar en Blender:

```python
# Pegar una copia standalone de detect_movement_type()/group_segments()
# (sin el import bpy) y correr con datos de prueba tipo:
pts = [
    {'coordinates': {'x': -2.5, 'y': -23.5, 'z': 9.0}, 'tipo_segmento': 'MI_SEGMENTO_NUEVO'},
    {'coordinates': {'x': -2.5, 'y': -23.5, 'z': 9.0}, 'tipo_segmento': 'PARADA'},
    {'coordinates': {'x': -2.5, 'y': -23.5, 'z': 9.0}, 'tipo_segmento': 'AUTO'},  # stub de la parada
]
segs = group_segments(pts)
for s in segs: print(s['type'], len(s['points']))
# Esperado: mi_segmento_nuevo (2 pts), parada (2 pts) -- SIN caminar de por medio
```

Esto detecta de entrada el error más común (sección 5.3/5.5) sin
necesitar levantar Blender.
