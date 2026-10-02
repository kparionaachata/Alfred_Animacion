# Cómo agregar nuevas animaciones de acción al sistema de recorrido (Path Recorder)

**Para:** cualquier IA (Claude u otra) que reciba el pedido de agregar una o
**varias** animaciones nuevas seleccionables en el recorrido de
`alfred_animation_studio` (o de cualquier `<personaje>_animation_studio`
portado con el mismo toolkit), siguiendo el mismo patrón que
`colocar_antorcha`, `golpe_estomago_1`, `arrodillarse_1`, `resbalarse_1`.

**TL;DR (léase primero):** desde 2026-08-27 este proceso está
**automatizado**. Si vas a agregar N animaciones, NO edites los archivos a
mano — usá `tools/agregar_animacion.py` (sección 2). La Sección 3 (proceso
manual, archivo por archivo) queda como referencia/fallback para cuando el
script no aplica (addon portado que todavía no tiene los marcadores
`AUTOGEN`, un caso raro que no encaja en el patrón de 2 puntos, o para
entender/depurar qué hace el script por dentro).

**Qué es "el sistema de recorrido":** el addon de Blender tiene un modo
"Path Recorder" (Paso 1) donde el usuario graba una lista de coordenadas
(`key_points`) por las que el personaje camina. Cada punto tiene un
`tipo_segmento` (Auto / Parada / Colocar antorcha / Golpe estómago / ...)
seleccionable en un dropdown. El addon convierte esa lista en una secuencia
de "slots" (archivos `.py` o acciones NLA) que animan al personaje: caminar,
saltar, pararse, o ejecutar una acción puntual en un lugar (el patrón que
cubre esta guía).

---

## 1. Arquitectura (resumen — necesario para entender qué hace el script)

### 1.1 Los archivos que siempre cambian juntos

| Archivo | Rol |
|---|---|
| `path_recorder.py` | UI del Paso 1, el enum `tipo_segmento`, la detección de movimiento en vivo (`_detect_move`), el agrupador de segmentos (`_group_segments`), la estimación de frames (`calcular_estimacion_geometrica`), y los DOS loops que invocan a los generadores (preview "Reproducir recorrido" y export "Generar Slots"). |
| `generate_slots_alfred.py` | Los generadores reales: `detect_movement_type()` y `group_segments()` (gemelos de los de arriba, deben dar el MISMO resultado), y una función `generate_<tipo>()` por cada tipo de segmento. |
| `panels.py` | Dibuja el ícono de cada punto en la lista del Paso 1, y el label de cada segmento en la estimación del Paso 2. |
| `config_ops.py` | Guarda/carga `configuracion.json`. **Ya es genérico** (ver 1.4) — no necesita tocarse al agregar un tipo nuevo. |

**Regla de oro:** todo lo que cambie en `path_recorder.py` (`_detect_move`,
`_group_segments`) tiene que tener su espejo EXACTO en
`generate_slots_alfred.py` (`detect_movement_type`, `group_segments`). El
script de la sección 2 mantiene esto sincronizado automáticamente porque
parchea ambos archivos con los mismos datos en la misma corrida.

### 1.2 Cómo se clasifica cada punto (`tipo_segmento`)

Cada punto tiene un `tipo_segmento`, por default `"AUTO"` (se infiere de la
geometría). El usuario puede forzar un override desde el dropdown
(`COLOCAR_ANTORCHA`, `GOLPE_ESTOMAGO_1`, `ARRODILLARSE_1`, `RESBALARSE_1`,
...), que tiene prioridad sobre la geometría y define un segmento especial
que abarca **ese punto y el siguiente** (dos coordenadas reales, sin
duplicar — a diferencia de `PARADA`, que sí usa un punto duplicado).

### 1.3 Por qué el root NO camina dentro del propio segmento especial

El personaje ya llegó caminando a `key_points[i]`. Durante el slot del
override, el root queda **fijo** en `key_points[i]`. Quien lo hace caminar
hasta `key_points[i+1]` es el segmento `caminar` que `_group_segments()` /
`group_segments()` fusionan automáticamente justo después, con los MISMOS
2 puntos como arranque. `key_points[i+1]` solo sirve, dentro del override,
para **orientar** al personaje antes de ejecutar la acción.

### 1.4 `config_ops.py` ya es genérico — no hace falta tocarlo

Guardar/cargar `configuracion.json` persiste **cualquier** valor de
`tipo_segmento_raw` que no sea `"AUTO"` tal cual (ver comentario "FIX
2026-08-24" en `config_ops.py`), sin depender de una lista fija de
overrides conocidos. Un tipo nuevo (agregado por el script o a mano)
funciona automáticamente con save/load de config — **no es necesario
agregar nada en `config_ops.py`**.

---

## 2. Proceso automatizado (usar esto salvo excepción)

### 2.1 Marcadores `AUTOGEN`

Los 3 archivos que hace falta tocar tienen 10 marcadores estables
(comentarios `# === AUTOGEN:<NOMBRE> ===`) en cada uno de los puntos de
inserción del patrón:

| Archivo | Marcador | Qué se inserta ahí |
|---|---|---|
| `generate_slots_alfred.py` | `DETECT_OVERRIDES` | `if p_current.get('tipo_segmento') == 'TIPO': return 'tipo'` |
| `generate_slots_alfred.py` | `KEYFRAME_DATA_BLOCKS` | `TOTAL_FRAMES_<TIPO>` + `<TIPO>_KEYFRAME_DATA = {...}` |
| `generate_slots_alfred.py` | `GENERATOR_FUNCTIONS` | `def generate_<tipo>(...)` completa |
| `path_recorder.py` | `ENUM_ITEMS` | item del `EnumProperty` (dropdown) |
| `path_recorder.py` | `DETECT_OVERRIDES` | override en `_detect_move()` |
| `path_recorder.py` | `ESTIMATION_BRANCHES` | rama en `calcular_estimacion_geometrica()` |
| `path_recorder.py` | `PREVIEW_LOOP_BRANCHES` | rama en el loop de "Reproducir recorrido" |
| `path_recorder.py` | `EXPORT_LOOP_BRANCHES` | rama en el loop de "Generar Slots" |
| `panels.py` | `PANEL_ICONS_PASO1` | ícono en la lista de puntos (Paso 1) |
| `panels.py` | `PANEL_LABELS_PASO2` | label en la estimación de segmentos (Paso 2) |

Además, 4 tuplas de una sola línea (`_ACCION_OVERRIDES` en los dos
archivos, y el `elif move_type/move in (...)` en los dos archivos) se
actualizan por patrón de texto (regex), sin necesitar marcador — el script
detecta si el tipo ya está para no duplicar.

Si estás portando este toolkit a un `<personaje>_animation_studio` que
todavía no tiene estos marcadores, agregalos una sola vez copiando la
ubicación exacta desde `alfred_animation_studio` (son solo comentarios, no
alteran el comportamiento existente).

### 2.2 Correr el script

Ubicación: `alfred_animation_studio/tools/agregar_animacion.py`. No
requiere `bpy` ni Blender abierto.

**Paso 0 — conseguir el/los archivo(s) fuente.** Cada animación nueva
necesita un `.py` con los datos de la animación (exportado de Mixamo u
otra fuente), en cualquiera de estos dos formatos — el script detecta cuál
es solo:

- **Denso:** ya trae `KEYFRAME_DATA = {...}` con 1 entrada por frame por
  hueso (como los `golpe_estomago_1.py` / `levantarse_1.py` originales).
- **Disperso:** trae `POSE_INICIO` / `POSE_ACCION` / `POSE_FIN` +
  `BONES_LISTA` + `TOTAL_FRAMES` + su propia `_build_bone_functions()`
  (como `resbalarse_1.py`). El script hornea (bake) 1 valor por frame
  corriendo esa misma función del archivo fuente — no hace falta
  convertir nada a mano.

**Paso 1 — escribir el spec** (un JSON con una animación o una lista de
N animaciones a agregar en la misma corrida):

```json
[
  {
    "tipo": "empujar_1",
    "nombre_visible": "Empujar",
    "descripcion": "El personaje se detiene en este punto y empuja un objeto (Mixamo, 14 huesos). Abarca este punto y el siguiente (coordenadas reales, sin duplicar)",
    "icono": "MOD_PHYSICS",
    "fuente": "empujar_1.py",
    "root_rot": [0, 0, -90]
  },
  {
    "tipo": "saludar_1",
    "nombre_visible": "Saludar",
    "icono": "ARMATURE_DATA",
    "fuente": "saludar_1.py"
  }
]
```

Campos: `tipo` y `nombre_visible` y `fuente` son obligatorios;
`descripcion`, `icono` (default `"ARMATURE_DATA"`), `root_rot` (default
`[0,0,-90]`) y `numero_enum` (default: autoasignado) son opcionales.
`TIPO` (mayúsculas, para el enum) se deriva solo de `tipo`.

**Paso 2 — correr:**

```bash
python3 tools/agregar_animacion.py \
    --addon-dir /ruta/a/alfred_animation_studio \
    --spec mis_animaciones.json
```

Agregar `--dry-run` para validar sin escribir nada a disco. El script:

1. Hornea/extrae el `KEYFRAME_DATA` de cada `fuente`.
2. Parchea `generate_slots_alfred.py`, `path_recorder.py` y `panels.py`
   **en memoria** (nunca toca disco todavía).
3. Valida sintaxis (`ast.parse`) de los 3 resultados.
4. Si algo falla, **no escribe nada** — el addon queda intacto y se
   imprime el error.
5. Si todo valida, escribe los 3 archivos.
6. Es **idempotente**: si un `tipo` ya existe en el enum, ese item del
   spec se saltea con un aviso (no duplica nada) — se puede volver a
   correr sin miedo, incluso con specs que mezclan tipos nuevos y ya
   agregados.

**Paso 3 — revisar y empaquetar.** Revisar el diff generado (git diff o
comparar contra el zip anterior) y volver a empaquetar el addon (`.zip`)
para entregarlo.

### 2.3 Validación adicional recomendada (sin Blender)

Después de correr el script, además de que el propio script ya valida
sintaxis, conviene simular `group_segments()` con **dos overrides en
secuencia** (el tipo nuevo + otro cualquiera, con solo "Caminar" en medio)
para confirmar que ninguno desaparece de la lista de segmentos generados
(ver el bug histórico en la sección 4). El script `agregar_animacion.py`
no corre esta simulación por sí solo — hacerlo a mano una vez por lote es
barato:

```python
import sys, types, importlib.util
sys.modules['bpy'] = types.ModuleType('bpy')
spec = importlib.util.spec_from_file_location("gen", "generate_slots_alfred.py")
gen = importlib.util.module_from_spec(spec); spec.loader.exec_module(gen)

key_points = [
    {'tipo_segmento': 'TU_TIPO_1', 'coordinates': {'x':0,'y':0,'z':0}},
    {'tipo_segmento': 'AUTO',      'coordinates': {'x':2,'y':0,'z':0}},
    {'tipo_segmento': 'TU_TIPO_2', 'coordinates': {'x':2,'y':0,'z':0}},
    {'tipo_segmento': 'AUTO',      'coordinates': {'x':4,'y':0,'z':0}},
]
segs = gen.group_segments(key_points)
print([s['type'] for s in segs])  # ambos tipos deben aparecer
```

---

## 3. Proceso manual (referencia / fallback)

Usar solo si el addon no tiene los marcadores `AUTOGEN` todavía, o si se
necesita depurar/entender exactamente qué genera el script.

### Paso 0 — Los 14 huesos estándar del rig

```
Hips_alfred, Spine_alfred, Spine1_alfred, Spine2_alfred, Neck_alfred,
face_alfred, RightUpArm_alfred, Rightelbow_alfred, LeftUpArm_alfred,
Leftelbow_alfred, RightUpLeg_alfred, Rightknee_alfred, LeftUpLeg_alfred,
Leftknee_alfred
```

### Paso 1 — `path_recorder.py`: enum, override, tupla de fusión

En el `EnumProperty` de `tipo_segmento`, agregar:

```python
("TU_NUEVO_TIPO", "Nombre visible",
 "Descripcion. Abarca este punto y el siguiente (coordenadas reales, sin duplicar)",
 "ICONO_DE_BLENDER", numero_unico),
```

En `_detect_move()`:

```python
if getattr(p0, "tipo_segmento", "AUTO") == "TU_NUEVO_TIPO":
    return "tu_nuevo_tipo"
```

En `_ACCION_OVERRIDES` y en el `elif move in (...)` de `_group_segments()`,
agregar `"TU_NUEVO_TIPO"` / `"tu_nuevo_tipo"` a las tuplas existentes.
**Crítico:** la rama de fusión debe terminar con `i = j` (NO `i = j + 1`)
— ver sección 4.

### Paso 2 — `generate_slots_alfred.py`: espejo + generador

Mismos 3 cambios que el Paso 1 (override en `detect_movement_type()`,
tupla en `_ACCION_OVERRIDES`, tupla en `group_segments()`), más una
función `generate_tu_nuevo_tipo(slot_index, start_frame, points, today,
root_rot=(0,0,-90))` copiada de `generate_resbalarse_1()` (la plantilla
más simple y más reciente) cambiando nombres de constantes/función y
pegando tu `KEYFRAME_DATA`.

### Paso 3 — `path_recorder.py`: los dos loops + estimación

En el loop de preview y en el de export, agregar:

```python
elif move_type == "tu_nuevo_tipo":
    code, end_frame = gen.generate_tu_nuevo_tipo(
        slot_index, current_frame, points, today, _cur_rot)
```

(en el de export, además `fname = f"slot_{slot_index:03d}_alfred_tu_nuevo_tipo.py"`)

En `calcular_estimacion_geometrica()`:

```python
elif seg_type == "tu_nuevo_tipo":
    from .generate_slots_alfred import TOTAL_FRAMES_TU_NUEVO_TIPO as _TFX
    slots.append({"slot": i + 1, "tipo": "tu_nuevo_tipo",
                   "label": "tu_nuevo_tipo", "frames_estimados": _TFX})
```

### Paso 4 — `panels.py`: ícono y label

```python
elif pt.tipo_segmento == "TU_NUEVO_TIPO":
    row_pt.label(text="", icon="TU_ICONO")
```

```python
elif _s["tipo"] == "tu_nuevo_tipo":
    row_seg.label(text=f"  Segmento {_s['slot']}: tu_nuevo_tipo ({_s['frames_estimados']} f)",
                  icon="TU_ICONO")
```

### Paso 5 — validar

1. Sintaxis: `python3 -c "import ast; ast.parse(open('archivo.py').read())"`
   en cada archivo tocado.
2. Simulación de `group_segments` con dos overrides en secuencia (ver
   2.3).
3. `generate_tu_nuevo_tipo(...)` ejecutada fuera de Blender (sin `bpy`
   real, con un stub) — el `code` devuelto debe parsear con `ast.parse()`
   y contener `ROOT_LOCATION_DATA = {`, `KEYFRAME_DATA = {`,
   `TOTAL_FRAMES = <tu numero>` y `def execute_animation`.

---

## 4. Bug histórico a tener en cuenta (por qué `i = j`, no `i = j + 1`)

La primera versión de la rama de fusión (`colocar_antorcha` original) hacía
`i = j + 1` al final, en vez de `i = j`. Eso saltaba exactamente el punto
donde termina el caminar fusionado — que es también el punto donde debe
empezar el SIGUIENTE segmento especial. Síntoma: con dos overrides en
secuencia (con solo "Caminar" en medio), el segundo quedaba absorbido
como simple punto de paso del caminar del primero y su animación nunca se
generaba. Con un solo override el bug era invisible.

`tools/agregar_animacion.py` no puede introducir este bug de nuevo porque
no reescribe la lógica de fusión — solo agrega el nombre del tipo nuevo a
tuplas ya existentes que mantienen el `i = j` correcto. Aun así, correr la
simulación de la sección 2.3 después de agregar un tipo nuevo es la forma
más barata de confirmar que sigue así.

---

## 5. Resumen ultra-corto

- [ ] Conseguir el/los `.py` fuente de la(s) animación(es) nueva(s).
- [ ] Armar el spec JSON (uno o varios items).
- [ ] `python3 tools/agregar_animacion.py --addon-dir ... --spec ... --dry-run`
      para validar, después sin `--dry-run` para aplicar.
- [ ] Simular `group_segments()` con el tipo nuevo + otro override en
      secuencia (sección 2.3) — ningún override debe desaparecer.
- [ ] Revisar el diff y volver a empaquetar el addon.
- [ ] (Solo si no hay marcadores `AUTOGEN` en el addon) seguir el proceso
      manual de la sección 3, y de paso agregar los marcadores para que
      la próxima vez sea automática.
