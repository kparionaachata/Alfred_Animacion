# Como se trabaja en este sistema (guia para cualquier IA)

Leer esto primero. Luego `FLUJOS_MANUAL_E_IA.md` (reglas de convivencia) y `GUIA_ANIMACION_ALFRED.md` (bitacora viva con
valores del rig y del historial). Las instrucciones actuales del usuario prevalecen sobre estas guias.

## 1. Que es
Un add-on de Blender por personaje (`alfred_animation_studio`, `jerry_animation_studio`, ...; mismo kit portado) para animar
personajes de Minecraft sobre un escenario importado con Mineways. El usuario lo usa a mano; las IA lo usan en paralelo.
Codigo de Alfred: `generador de animaciones/alfred/refinar/alfred_animation_studio/`.

Preparacion (una vez): escenario (Mineways -> OBJ -> superficies separadas) y, por personaje, 4 animaciones base
(caminar, parado, saltar_subir, saltar_bajar). Trabajo por animacion (se repite): recorrido -> segmentos -> poses/filtros/ojos
-> concatenar -> guardar.

## 2. Los dos flujos (no se mezclan)
| | MANUAL | IA |
|---|---|---|
| Quien | el usuario, en los paneles | una IA (varias a la vez) |
| Guarda | guion `.json` en `refinar/configuraciones/` (receta editable) | resultado completo en `refinar/animaciones_ia/<nombre>/` |
| Depende del guion | si | no (opcional; nunca cuello de botella) |

Una tarea de animacion dada a una IA usa el flujo IA. Nunca sobrescribir guiones del usuario ni carpetas de otra IA.

## 3. Conceptos del motor
- **Recorrido (Pasos 1-2):** puntos de coordenada (centro de una cara del escenario) con `tipo_segmento`
  (AUTO, PARADA, SALTAR, acciones puntuales...). AUTO se decide por la geometria: mismo Z = caminar, Z distinto = salto.
  Una PARADA solo se admite en un punto cuyo tramo siguiente sea caminar. Estilos de caminata: NORMAL, LENTO, HERIDO, RAPIDO, CORRER.
  `alfredpr.preview_path` hornea la **animacion base (Capa 1)** como pistas NLA `slot_NNN_*`.
- **Segmentos (Paso 3):** `alfredseg.autosplit_from_config` crea un segmento por tramo. Cada uno tiene `action_poses`
  (secuencia de poses con duracion e interpolacion), bloqueo de huesos, filtros organicos, parpadeos y expresiones de ojos.
- **Poses:** `.json` en `refinar/poses/` (formato ALFST_OT_ExtractPose). Guardan huesos y la clave `root`: posicion y rotacion
  **ABSOLUTAS (mundo)** del Empty raiz. Las poses se *inyectan* sobre la base; los huesos bloqueados conservan la base.
- **Concatenar:** `alfredseg.concatenate_all` regenera la base y hornea las poses. Reglas que hay que conocer:
  - El primer waypoint de un segmento es su **primera pose** y el ultimo su **ultima**; cada pose es un waypoint en la mitad de su
    ventana. La interpolacion que llega a una pose usa el `interp_type` de esa pose.
  - Con `manual_start` en la primera pose, el hueco inicial usa la base capturada (mezcla suave). Ver `ai_api.seg_bordes`.
  - Root libre = poses mandan el root (`filter_main_bone` falso); bloqueado = manda la base.
  - Al terminar arranca la reproduccion: cancelarla antes de medir o capturar.
  - Cargar una config dispara CONCATENAR_2 (ojos) automaticamente.
- **Ojos:** meshes `ojo_izquierdo_<p>` / `ojo_derecho_<p>` con escala (X ancho, Z alto; neutro 1.555 / 3.55, Y fijo), shape keys
  (`Closed`, Feliz, Triste, Enojado, Sospecha, Cansado, Sorpresa, sueno) y expresiones por intervalo en cada segmento. El sistema
  solo pone claves en intervalos que usan una shape key: entre dos usos lejanos **interpola** (ej. `Closed` se cerraba en un salto).
  Retocar con `ai_api.ojos_fijar`.

## 4. Rig de Alfred (verificado)
Empty `alfred` en el pie; `Armature` con 22 huesos; cadera a 0.873 sobre el root; alto 2.03; Alfred mira a -Y con rotZ=180.
Ejes locales (Euler XYZ, grados; delante/derecha/izquierda desde Alfred):
- `Hips`: X+ inclina TODO el cuerpo hacia adelante (boca abajo con X=90); Z rueda sobre el eje adelante (Z negativo rueda a su izquierda); Y+ gira a la izquierda.
- `Spine/Spine1/Spine2`: X+ adelante, Y+ gira a la izquierda, Z+ inclina a la derecha. `Neck`: X- mira arriba, X+ abajo, Y+ izquierda.
- Brazos (reposo X=90): abduccion = X = 90 - a; adelante: derecho Y+, izquierdo Y-. Codo: derecho flexiona con Z-, izquierdo con Z+.
- Piernas: X+ adelante; rodilla flexiona con X negativo.
Un giro con Euler XYZ no se "deshace" si el angulo final se mantiene (ej. rodar hasta Z=-360 y seguir con Z=-360).

## 5. Como hacer una animacion (flujo IA)
1. Leer `GUIA_ANIMACION_ALFRED.md` y confirmar el personaje y el `.blend` activos. Respaldo: `bpy.ops.wm.save_as_mainfile(copy=True)`.
2. Medir el terreno (raycast `scene.ray_cast` desde arriba y desde la superficie del agua): alturas de suelo, lecho, agua; no suponer.
3. Recorrido: `ai_api.guion_recorrido` (tipos, estilos, puntos) en un guion **nuevo**; `guion_aplicar`; `bpy.ops.alfredpr.preview_path()`;
   `bpy.ops.alfredseg.autosplit_from_config()`.
4. Poses: `ai_api.pose_huesos` + `crear_pose(nombre, huesos, root_pos=, root_rot_deg=)`. Root con `root_por_suelo` (cuerpo apoyado)
   o `root_por_cadera` (trayectorias en el aire, p. ej. una parabola con un waypoint cada ~6 frames). Nombres nuevos `ia_<nombre>_*`.
5. Segmentos: `seg_poner_poses`, `seg_bloquear`, `seg_bordes`; ojos en `expr_intervals` (suma de duraciones = frames del segmento);
   `validar_guion`; `guion_aplicar_segmentos`; `concatenar` (o `bpy.ops.alfredseg.concatenate_all()`).
6. Retoques posteriores: `ojos_fijar`; pruebas con `medir`, `chequear_frames`, `ver_pose`, `encuadrar` (capturas).
7. Guardar: `ai_export.exportar("<nombre>", agente=, guion_fuente=, suavizar_en=[frames de union], ventana=8)` ->
   `animaciones_ia/<nombre>/{.animacion.json, .py, manifest.json}`. Otro personaje: `personaje=JERRY` (o un dict propio).
   Reproducir: `ai_export.importar("<nombre>")` o ejecutar el `.py` (crea pistas `IA_<nombre>__*`).
8. Registrar el trabajo en `GUIA_ANIMACION_ALFRED.md`. No declarar "aprobada" una animacion sin confirmacion del usuario.

Uso dentro de Blender: `from alfred_animation_studio import ai_api, ai_export`. La copia instalada esta en
`%APPDATA%\Blender Foundation\Blender\5.2\scripts\addons\<personaje>_animation_studio\`: al editar la fuente hay que copiarla alli
(o reinstalar con `start_animation_studio.bat`).

## 6. Mapa de archivos
- `alfred_animation_studio/`: `properties.py` (datos), `panels.py` (UI), `path_recorder.py` (recorrido, base), `operators_segments.py`
  (segmentos, concatenar todo), `operators_anim.py` (motor que hornea poses), `config_ops.py` (guardar/cargar guion),
  `generate_slots_alfred.py` (animaciones base), `pose_utils.py`, `interpolation.py`, `eye_system.py`, `blender_compat.py`,
  **`ai_api.py`** (crear/editar/verificar) y **`ai_export.py`** (salida del flujo IA). Los dos ultimos son aditivos.
- Datos: `poses/`, `configuraciones/`, `animaciones/` (slots .py), `animaciones_ia/`, `docs/`.

## 7. Trampas conocidas
- `bpy.ops` desde Blender por MCP: `execute_blender_code` no comparte variables entre comprensiones (usar bucles); `result` debe ser dict.
- Playback se reactiva solo tras `concatenate_all`: `screen.animation_cancel(restore_frame=False)` y comprobar `is_animation_playing`.
- Capturas de vista: usar vista local + colores aleatorios + huesos visibles; el agua es opaca en vista solida; las capturas solo
  funcionan con la ventana de Blender en su tamano actual.
- `keyframe_points.insert` puede no insertar en curvas horneadas de Blender 5.2: usar `add(1)` y asignar `co`.
- El cargador de config perdia las PARADA en Blender 5.2 (corregido en `config_ops.py`; `ai_api.guion_aplicar` lo repite por si el add-on instalado es viejo).
- Importar un guion no reinicia el estado de los ojos: volver a concatenar despues de cambiar `expr_intervals`.
- Otro personaje (Jerry) usa el kit portado con nombres propios (`jerrypr.*`, `scene.jerry_path`, `Dog_001_rig`, root `jerry`); su
  `preview_path` sobrescribe su recorrido y el rango de frames: guardar y restaurar el del usuario.
- El flujo IA no exporta props importados/lanzados ni invisibilidad de mallas salvo `extras` declarados en el personaje.

## 8. Reglas del usuario
Trabajo manual y sin depender de IA, salvo lo que se le pida. Cambios visibles y con feedback rapido. No sobrescribir su trabajo.
Todo lo de documentacion va en `refinar/docs/`. Sin aprobacion explicita, una animacion es una primera version.
