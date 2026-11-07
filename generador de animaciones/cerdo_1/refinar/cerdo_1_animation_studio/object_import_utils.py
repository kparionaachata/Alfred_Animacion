#!/usr/bin/env python3
"""
object_import_utils.py - Lógica reutilizable para importar objetos (armas, escudos, etc.)
desde archivos .blend ubicados en objetos/vanilla/<nombre_objeto>/<nombre_objeto>.blend

Basado en el sistema usado en slot_002_sacar_escudo.py y slot_003_sacar_espada.py
para Alfred_Animacion. Pensado para ser importado por los distintos slots:

    from object_import_utils import import_object_from_blend, set_visibility_keyframes, parent_to_bone

Compatible con simple_animation_blocks_manager.py
"""

import bpy
from .blender_compat import get_fcurves
import os
import re


# ============================================================
# REGLA_SUFIJO_NUMERICO_ANTICOLISION
# ============================================================
#
# Filtro que se aplica a TODO objeto (arma, escudo, comida, etc.) recien
# traido de un .blend, ANTES de linkearlo a una collection de la escena
# (o sea, antes de que aparezca en el Outliner).
#
# Motivo: si la historia pide importar el mismo objeto mas de una vez
# (o dos personajes distintos importan el mismo .blend, ej. la misma
# espada para Cerdo_1 y para Jerry), los nombres de sus Objects, su
# Mesh/Armature data y sus Bones colisionarian con los ya existentes en
# la escena si no se renombran primero. Este filtro les agrega un
# sufijo numerico dinamico ("_1", "_2", "_3"...) eligiendo siempre el
# primer numero libre, de forma que nunca pisa nombres ya presentes.
#
# IMPORTANTE: solo toca los objetos recien importados (nunca el resto
# de la escena) -- importar un objeto jamas debe renombrar el rig de
# Cerdo_1/Jerry/Guard Ribbit ni nada que ya estuviera en la escena.

def _nombre_base_sin_sufijo(nombre):
    """Si `nombre` ya termina en '_<numero>' (ej. de una importacion anterior
    de este mismo objeto), devuelve el nombre SIN ese sufijo -- evita
    encadenar sufijos tipo 'espada_1_2_3' si el mismo objeto se re-filtra
    mas de una vez."""
    m = re.match(r"^(.*)_\d+$", nombre)
    return m.group(1) if m else nombre


def _siguiente_numero_libre(nombre_base, nombres_existentes):
    """Primer entero >= 1 tal que '{nombre_base}_{n}' no esta en
    `nombres_existentes`."""
    n = 1
    while f"{nombre_base}_{n}" in nombres_existentes:
        n += 1
    return n


def aplicar_sufijo_numerico_anticolision(objetos_importados):
    """
    FILTRO DE IMPORTACION -- REGLA_SUFIJO_NUMERICO_ANTICOLISION.

    Debe llamarse INMEDIATAMENTE despues de traer los objetos de un
    .blend (resultado de `bpy.data.libraries.load(..., link=False)` /
    `data_to.objects`) y ANTES de linkearlos a una collection de la
    escena -- o sea, antes de que aparezcan en el Outliner.

    Renombra, para cada objeto MESH o ARMATURE importado:
      - El nombre del propio Object.
      - El nombre de su Mesh/Armature data (solo si no la comparte con
        otro objeto, `users == 1`).
      - Si es ARMATURE: cada Bone dentro de ella, con EL MISMO numero
        que el objeto -- asi es trivial ver a que importacion pertenece
        cada bone con solo mirar el nombre (ej. objeto "espada_2",
        bones "hilt_espada_2", "hoja_espada_2", ...).

    Args:
        objetos_importados: lista/iterable de bpy.types.Object recien
            importados, todavia sin linkear a ninguna collection.

    Returns:
        dict {nombre_original: nombre_nuevo} de los objetos MESH/ARMATURE
        procesados.
    """
    mapa_renombrado = {}

    # Snapshot de nombres YA existentes en la escena antes de renombrar,
    # para no elegir un numero que choque con algo que ya estaba ahi.
    nombres_objetos_existentes   = {o.name for o in bpy.data.objects}
    nombres_mallas_existentes    = {m.name for m in bpy.data.meshes}
    nombres_armaduras_existentes = {a.name for a in bpy.data.armatures}

    for obj in objetos_importados:
        if obj is None or obj.type not in ('MESH', 'ARMATURE'):
            continue

        nombre_original = obj.name
        base = _nombre_base_sin_sufijo(nombre_original)
        n = _siguiente_numero_libre(base, nombres_objetos_existentes)
        nuevo_nombre = f"{base}_{n}"

        print(f"[FILTRO IMPORT] Objeto: '{nombre_original}' -> '{nuevo_nombre}'")
        obj.name = nuevo_nombre
        nombres_objetos_existentes.add(nuevo_nombre)
        mapa_renombrado[nombre_original] = nuevo_nombre

        if obj.type == 'MESH' and obj.data and obj.data.users == 1:
            base_malla = _nombre_base_sin_sufijo(obj.data.name)
            n_malla = _siguiente_numero_libre(base_malla, nombres_mallas_existentes)
            nuevo_nombre_malla = f"{base_malla}_{n_malla}"
            print(f"  - Malla: '{obj.data.name}' -> '{nuevo_nombre_malla}'")
            obj.data.name = nuevo_nombre_malla
            nombres_mallas_existentes.add(nuevo_nombre_malla)

        if obj.type == 'ARMATURE' and obj.data:
            if obj.data.users == 1:
                base_arm = _nombre_base_sin_sufijo(obj.data.name)
                n_arm = _siguiente_numero_libre(base_arm, nombres_armaduras_existentes)
                nuevo_nombre_arm = f"{base_arm}_{n_arm}"
                print(f"  - Armadura: '{obj.data.name}' -> '{nuevo_nombre_arm}'")
                obj.data.name = nuevo_nombre_arm
                nombres_armaduras_existentes.add(nuevo_nombre_arm)

            if obj.data.bones:
                for bone in obj.data.bones:
                    nombre_bone_original = bone.name
                    base_bone = _nombre_base_sin_sufijo(nombre_bone_original)
                    nuevo_nombre_bone = f"{base_bone}_{n}"
                    print(f"  - Bone: '{nombre_bone_original}' -> '{nuevo_nombre_bone}'")
                    bone.name = nuevo_nombre_bone

    return mapa_renombrado


def get_objetos_base_path(file_dunder: str, levels_up: int = 4) -> str:
    """
    Calcula la ruta base 'objetos' a partir de la ubicación del slot.

    levels_up: cuántos niveles de directorio subir desde el archivo del slot
               hasta llegar a la carpeta raíz del proyecto (Alfred_Animacion).
               Por defecto 4, igual que en slot_002 y slot_003.
    """
    path = os.path.abspath(file_dunder)
    for _ in range(levels_up):
        path = os.path.dirname(path)
    return os.path.join(path, 'objetos')


def get_objetos_base_path_from_anchor(anchor_dir: str, levels_up: int = 4) -> str:
    """
    Igual que get_objetos_base_path, pero a partir de un directorio ancla
    (en vez de un archivo). Util para ejecutar la importacion de objetos
    directamente en la escena en vivo (ej. boton CONCATENAR), donde no
    existe un archivo de slot exportado.

    anchor_dir: directorio desde el cual subir 'levels_up' niveles
                (ej. scene.cerdo_1_st.anim_dir, que por defecto esta 4
                niveles debajo de Alfred_Animacion).
    """
    path = os.path.abspath(anchor_dir)
    for _ in range(levels_up):
        path = os.path.dirname(path)
    return os.path.join(path, 'objetos')


def resolve_object_folder_path(base_path: str, object_folder: str) -> str:
    """
    Resuelve la carpeta del objeto dentro de 'objetos/'.

    object_folder puede ser:
      - una ruta relativa con subcarpetas, ej. 'vanilla/shield', 'jerry/espada_madera'
      - solo el nombre de la carpeta del objeto, ej. 'shield' (formato legado)

    Para compatibilidad con configuraciones antiguas (donde object_folder
    era solo 'shield' y se asumia dentro de objetos/vanilla/), si
    objetos/<object_folder> no existe pero objetos/vanilla/<object_folder>
    si, se usa esta ultima.
    """
    object_folder = (object_folder or "").strip().replace("\\", "/")
    direct = os.path.join(base_path, *object_folder.split("/"))
    if os.path.isdir(direct):
        return direct

    legacy = os.path.join(base_path, "vanilla", *object_folder.split("/"))
    if os.path.isdir(legacy):
        return legacy

    # Ninguna existe: devolver la ruta directa (el llamador reportara el error)
    return direct


def get_bloques_dinamicos_path_from_anchor(anchor_dir: str, levels_up: int = 4) -> str:
    """
    Igual que get_objetos_base_path_from_anchor, pero para la carpeta
    'bloques_dinamicos' -- HERMANA de 'objetos/', directamente bajo la
    raiz del proyecto (ej. .../Alfred_Animacion/bloques_dinamicos/), NO
    anidada dentro de 'objetos/'. Ahi viven props con partes en
    movimiento/luz propia que no son "objetos sostenibles" (armas,
    escudos) sino elementos que se plantan en el recorrido -- ej.
    antorcha_1.blend.
    """
    path = os.path.abspath(anchor_dir)
    for _ in range(levels_up):
        path = os.path.dirname(path)
    return os.path.join(path, 'bloques_dinamicos')


# ============================================================
# IMPORTACION DE BLOQUES DINAMICOS (ej. antorchas) — libreria
# COMPLETA (todas las collections/objetos del .blend, jerarquia de
# parentesco intacta) + renombrado secuencial GLOBAL
# ============================================================
#
# A diferencia de import_object_from_blend_path() (que solo trae UN
# objeto suelto nombrado), un bloque dinamico como antorcha_1.blend es
# un Empty raiz ("antorcha_1") con luz + mallas PARENTEADAS a el (ver
# antorcha_1.json: coleccion 'Spawner Exclude > torch.1'). Traer solo
# el Empty sin sus hijos dejaria la antorcha sin llama ni luz. La logica
# de carga (bpy.data.libraries.load trayendo TODAS las collections y
# objetos, igual que blend_importer.py/BLEND_OT_import_file) es la
# correcta aca -- no filtra por nombre.
#
# Cada colocacion REIMPORTA el mismo .blend fuente (nunca se modifica) y
# renombra TODO lo recien traido (objetos, mallas, armatures, huesos,
# colecciones, materiales) con la MISMA logica de remplazar_sufijo.py:
# reemplaza el sufijo numerico final ('_1', tal como vienen nombrados
# los datablocks en el .blend fuente) por '_N', el primer N libre en la
# escena -- a diferencia de aplicar_sufijo_numerico_anticolision() (que
# asigna un numero INDEPENDIENTE por objeto), aca TODOS los datablocks
# de una misma importacion comparten el MISMO numero N (antorcha_1,
# antorcha_2, antorcha_3...), para que sea trivial ver a que antorcha
# pertenece cada pieza con solo mirar el nombre.

def _bloque_siguiente_sufijo(base_name: str, existing_names: set) -> int:
    """Primer entero >= 1 tal que '{base_name}_{n}' no esta en
    existing_names (ej. si 'antorcha_1' ya esta en escena, devuelve 2)."""
    n = 1
    while f"{base_name}_{n}" in existing_names:
        n += 1
    return n


def _bloque_renombrar_sufijo(nombre: str, suffix_from: str, suffix_to: str) -> str:
    """Identico a rename() de remplazar_sufijo.py: reemplaza suffix_from
    SOLO si esta al final del nombre (no toca ocurrencias en el medio)."""
    pattern = re.escape(suffix_from) + r"$"
    return re.sub(pattern, suffix_to, nombre)


def import_bloque_dinamico_full(blend_path: str, target_location, base_name: str = None):
    """
    Importa un .blend COMPLETO (todas sus collections y objetos, con
    jerarquia de parentesco intacta) en target_location, renombrando
    secuencialmente TODO lo recien traido (ver docstring de arriba).

    Parámetros:
        blend_path:      ruta al .blend (ej. bloques_dinamicos/antorcha_1.blend)
        target_location: (x, y, z) donde debe quedar el objeto raiz principal
                          (mismo punto que 'torch_dest' / points[1] del tramo
                          colocar_antorcha)
        base_name:        nombre base para detectar el sufijo '_1' fuente Y
                          para elegir el objeto ANCLA de posicionamiento (ver
                          abajo). Por defecto, nombre del archivo sin
                          extension (ej. 'antorcha_1').

    Posicionamiento: usa como ANCLA el objeto raiz cuyo nombre (ya
    renombrado) coincide con '{base_name_sin_sufijo}_{N}' (ej.
    'antorcha_2'), NO el promedio de todos los objetos raiz como hace
    blend_importer.py -- antorcha_1.blend trae ademas mallas sueltas de
    otras variantes (humo generico, malla de referencia
    "torch_flame_noImport") sin parentesco a la antorcha, que arruinarian
    el promedio si se las contara. Si no se encuentra el ancla esperado
    (.blend con otra estructura), hace fallback al primer EMPTY raiz y,
    si tampoco hay, al primer objeto raiz.

    Retorna: (objeto_ancla_o_None, dict {nombre_original: nombre_nuevo})
    """
    from mathutils import Vector

    if not os.path.exists(blend_path):
        print(f"   ⚠️ Archivo no encontrado: {blend_path}")
        return None, {}

    if base_name is None:
        base_name = os.path.splitext(os.path.basename(blend_path))[0]

    with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
        data_to.collections = list(data_from.collections)
        data_to.objects      = list(data_from.objects)

    imported_objects     = [o for o in data_to.objects if o is not None]
    imported_collections = [c for c in data_to.collections if c is not None]

    if not imported_objects and not imported_collections:
        print(f"   ⚠️ {os.path.basename(blend_path)} no contiene nada para importar")
        return None, {}

    # ── Renombrado secuencial GLOBAL, ANTES de linkear a la escena (o
    #    sea, antes de que aparezca en el Outliner) ─────────────────────
    existing_obj_names = {o.name for o in bpy.data.objects}
    n           = _bloque_siguiente_sufijo(base_name, existing_obj_names)
    suffix_from = "_1"
    suffix_to   = f"_{n}"
    mapa_renombrado = {}

    imported_meshes    = {o.data for o in imported_objects if o.type == 'MESH' and o.data}
    imported_armatures = {o.data for o in imported_objects if o.type == 'ARMATURE' and o.data}
    imported_materials = set()
    for o in imported_objects:
        if o.type == 'MESH' and o.data:
            for m in o.data.materials:
                if m is not None:
                    imported_materials.add(m)

    for obj in imported_objects:
        old, new = obj.name, _bloque_renombrar_sufijo(obj.name, suffix_from, suffix_to)
        if new != old:
            obj.name = new
            mapa_renombrado[old] = new

    for coll in imported_collections:
        old, new = coll.name, _bloque_renombrar_sufijo(coll.name, suffix_from, suffix_to)
        if new != old:
            coll.name = new
            mapa_renombrado[old] = new

    for mesh in imported_meshes:
        old, new = mesh.name, _bloque_renombrar_sufijo(mesh.name, suffix_from, suffix_to)
        if new != old:
            mesh.name = new
            mapa_renombrado[old] = new

    for arm in imported_armatures:
        old, new = arm.name, _bloque_renombrar_sufijo(arm.name, suffix_from, suffix_to)
        if new != old:
            arm.name = new
            mapa_renombrado[old] = new
        for bone in arm.bones:
            old_b, new_b = bone.name, _bloque_renombrar_sufijo(bone.name, suffix_from, suffix_to)
            if new_b != old_b:
                bone.name = new_b
                mapa_renombrado[old_b] = new_b

    for mat in imported_materials:
        old, new = mat.name, _bloque_renombrar_sufijo(mat.name, suffix_from, suffix_to)
        if new != old:
            mat.name = new
            mapa_renombrado[old] = new

    print(f"[BLOQUE_DINAMICO] '{os.path.basename(blend_path)}' -> sufijo "
          f"'{suffix_from}'->'{suffix_to}' ({len(mapa_renombrado)} datablocks renombrados)")

    # ── Linkear a la escena (recien AHORA aparece en el Outliner) ──────
    scene_coll = bpy.context.scene.collection
    for coll in imported_collections:
        if coll.name not in scene_coll.children:
            scene_coll.children.link(coll)

    imported_names = {o.name for o in imported_objects}
    for obj in imported_objects:
        en_coleccion = any(obj.name in coll.objects for coll in imported_collections)
        if not en_coleccion and obj.name not in scene_coll.objects:
            scene_coll.objects.link(obj)

    bpy.context.view_layer.update()

    # ── Posicionar en target_location, usando el ancla (ver docstring) ─
    root_objects = [o for o in imported_objects
                    if o.parent is None or o.parent.name not in imported_names]

    ancla_name  = _bloque_renombrar_sufijo(base_name, suffix_from, suffix_to)
    root_anchor = next((o for o in root_objects if o.name == ancla_name), None)
    if root_anchor is None:
        root_anchor = (next((o for o in root_objects if o.type == 'EMPTY'), None)
                        or (root_objects[0] if root_objects else None))

    if root_anchor is not None and root_objects:
        offset = Vector(target_location) - root_anchor.matrix_world.translation
        for obj in root_objects:
            obj.location = obj.location + offset

    bpy.context.view_layer.update()

    print(f"   ✅ Bloque dinamico importado: {len(imported_objects)} objetos, "
          f"{len(imported_collections)} colecciones, ancla="
          f"'{root_anchor.name if root_anchor else None}' -> "
          f"{tuple(round(c, 3) for c in target_location)}")

    return root_anchor, mapa_renombrado


def list_objects_in_blend(blend_path: str, only_meshes: bool = True):
    """
    Lista los nombres de los objetos disponibles dentro de un .blend SIN
    importarlos (solo lectura de metadatos via bpy.data.libraries.load).

    Util para que el usuario, tras elegir un .blend en el explorador de
    archivos, pueda ver/seleccionar el nombre exacto del objeto a importar.

    Parámetros:
        blend_path:  ruta al archivo .blend
        only_meshes: parametro reservado para futura distincion por tipo
                     (bpy.data.libraries.load no expone el tipo en preview,
                     por lo que actualmente se devuelven todos los nombres).

    Retorna: lista de nombres de objetos (puede estar vacia si el archivo
    no existe, no tiene objetos, o no se pudo leer).
    """
    if not os.path.exists(blend_path):
        return []

    try:
        with bpy.data.libraries.load(blend_path, link=False) as (data_from, _data_to):
            names = list(data_from.objects)
    except Exception as e:
        print(f"   ⚠️ No se pudo leer {blend_path}: {e}")
        return []

    return names


def import_object_from_blend_path(blend_path: str, object_name: str):
    """
    Importa un objeto (mesh) desde una ruta .blend ya resuelta, sin
    necesidad de __file__. Util para la ejecucion en escena en vivo
    (CONCATENAR), donde la ruta base se calcula a partir de un directorio
    ancla en vez de un archivo de slot.

    Retorna el objeto importado y enlazado a la escena, o None si falló.
    """
    if not os.path.exists(blend_path):
        print(f"   ⚠️ Archivo no encontrado: {blend_path}")
        return None

    print(f"   📦 Importando '{object_name}' desde {blend_path}")

    imported_obj = None
    # Guardar nombres existentes antes de importar para detectar el nuevo objeto
    _existing_names = set(o.name for o in bpy.data.objects)

    with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
        data_to.objects = [name for name in data_from.objects if name == object_name]
    # Fuera del with: data_to.objects contiene los objetos reales (ya cargados en bpy.data)

    # ── Filtro anticolision (REGLA_SUFIJO_NUMERICO_ANTICOLISION) ──────────
    # Se aplica AQUI porque los objetos ya existen en bpy.data pero todavia
    # NO estan linkeados a ninguna collection -- o sea, todavia no aparecen
    # en el Outliner. Les agrega un sufijo "_N" (numero libre) a Object,
    # Mesh/Armature data y Bones, para que si la misma espada/escudo/comida
    # se importa mas de una vez en la escena, nunca colisionen los nombres.
    aplicar_sufijo_numerico_anticolision([o for o in data_to.objects if o is not None])

    for obj in data_to.objects:
        if obj is not None:
            target_collection = bpy.context.collection
            if target_collection is None:
                target_collection = bpy.context.scene.collection
            if obj.name not in target_collection.objects:
                target_collection.objects.link(obj)
            imported_obj = obj
            print(f"   ✅ Objeto importado: {imported_obj.name}")
            break

    if imported_obj is None:
        print(f"   ⚠️ No se encontró el objeto '{object_name}' dentro de {os.path.basename(blend_path)}")

    return imported_obj


def import_object_from_blend(file_dunder: str, object_folder: str, blend_filename: str,
                               object_name: str, levels_up: int = 4):
    """
    Importa un objeto (mesh) desde un archivo .blend ubicado en
    objetos/vanilla/<object_folder>/<blend_filename>.

    Parámetros:
        file_dunder:    pasar __file__ del slot que llama esta función
        object_folder:  nombre de la carpeta dentro de objetos/vanilla (ej: 'shield', 'stone_sword')
        blend_filename: nombre del archivo .blend (ej: 'shield.blend', 'stone_sword.blend')
        object_name:    nombre exacto del objeto dentro del .blend a importar (ej: 'shield', 'stone_sword')
        levels_up:      niveles de directorio a subir desde el slot hasta la raíz del proyecto

    Retorna:
        El objeto importado y enlazado a la escena, o None si falló (incluyendo
        el caso fallback de crear un objeto procedural simple).
    """
    base_path = get_objetos_base_path(file_dunder, levels_up)
    object_dir = resolve_object_folder_path(base_path, object_folder)
    blend_path = os.path.join(object_dir, blend_filename)
    return import_object_from_blend_path(blend_path, object_name)


def create_procedural_fallback(name: str, kind: str = 'plane',
                                location=(0, 0, 0), scale=(1.0, 1.0, 1.0)):
    """
    Crea un objeto procedural simple como fallback cuando el .blend no existe
    o el objeto no se encontró dentro de él.

    kind: 'plane' o 'cylinder'
    """
    if kind == 'cylinder':
        bpy.ops.mesh.primitive_cylinder_add(radius=0.02, depth=1.0, location=location)
    else:
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=location)

    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale

    if kind == 'plane':
        solidify_mod = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
        solidify_mod.thickness = 0.05

    print(f"   🔧 Objeto procedural '{name}' creado como fallback")
    return obj


def ensure_material(obj, material_name: str, base_color=(0.8, 0.8, 0.9, 1.0),
                     metallic: float = 1.0, roughness: float = None,
                     specular: float = None):
    """
    Asegura que el objeto tenga al menos un material. Si no tiene ninguno,
    crea uno nuevo con los parámetros dados (Principled BSDF).
    """
    if obj.data.materials:
        return

    material = bpy.data.materials.new(name=material_name)
    material.use_nodes = True
    principled = material.node_tree.nodes["Principled BSDF"]
    principled.inputs['Base Color'].default_value = base_color
    principled.inputs['Metallic'].default_value = metallic

    if roughness is not None:
        principled.inputs['Roughness'].default_value = roughness

    if specular is not None and 'Specular IOR Level' in principled.inputs:
        principled.inputs['Specular IOR Level'].default_value = specular

    obj.data.materials.append(material)
    print(f"   🎨 Material '{material_name}' aplicado a '{obj.name}'")


def set_visibility_keyframes(obj, frame: int, visible: bool):
    """
    Inserta keyframes de hide_viewport / hide_render en el frame dado,
    según si el objeto debe ser visible o no a partir de ese frame.
    """
    obj.hide_viewport = not visible
    obj.hide_render = not visible
    obj.keyframe_insert(data_path="hide_viewport", frame=frame)
    obj.keyframe_insert(data_path="hide_render", frame=frame)


def hide_until_frame(obj, appear_frame: int):
    """
    Oculta el objeto desde el frame anterior a appear_frame, y lo hace
    visible exactamente en appear_frame. Útil para objetos que aparecen
    a mitad de la animación (ej: la espada en slot_003).
    """
    hide_frame = max(1, appear_frame - 1)
    set_visibility_keyframes(obj, hide_frame, visible=False)
    set_visibility_keyframes(obj, appear_frame, visible=True)


def find_armature_and_bone(armature_name: str, bone_name_contains=('bend',), exact_bone_name=None):
    """
    Busca un armature por nombre y, dentro de él, un pose bone cuyo nombre
    contenga alguno de los substrings dados (en minúsculas) o que coincida
    exactamente con exact_bone_name.

    Retorna: (armature_obj, pose_bone) — cualquiera puede ser None si no se encuentra.
    """
    armature_obj = None
    target_bone = None

    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and obj.name == armature_name:
            armature_obj = obj
            if obj.pose and obj.pose.bones:
                if exact_bone_name:
                    target_bone = obj.pose.bones.get(exact_bone_name)
                if target_bone is None and bone_name_contains:
                    for bone in obj.pose.bones:
                        bone_lower = bone.name.lower()
                        if any(sub in bone_lower for sub in bone_name_contains):
                            target_bone = bone
                            break
            break

    return armature_obj, target_bone


def parent_to_bone(obj, armature_name: str, bone_name_contains=('bend',), exact_bone_name=None):
    """
    Parentea 'obj' al pose bone correcto del armature indicado. Si no se
    encuentra un bone específico, hace fallback a parentear al armature
    completo (parent_type='OBJECT').

    matrix_parent_inverse se deja como IDENTIDAD a proposito: de esta forma
    obj.location / obj.rotation_euler / obj.scale quedan como un offset
    LOCAL relativo al espacio del bone (o del armature en el fallback),
    que es lo que representan los campos "Posicion / Rotacion / Escala"
    del panel de Importacion de Objetos. Esto tambien hace que el objeto
    siga correctamente al bone durante la animacion.
    """
    armature_obj, target_bone = find_armature_and_bone(
        armature_name, bone_name_contains=bone_name_contains, exact_bone_name=exact_bone_name
    )

    import mathutils

    if target_bone:
        obj.parent = target_bone.id_data
        obj.parent_bone = target_bone.name
        obj.parent_type = 'BONE'
        obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
        print(f"   🔗 '{obj.name}' parentado al bone '{target_bone.name}' de '{armature_name}'")
    elif armature_obj:
        obj.parent = armature_obj
        obj.parent_type = 'OBJECT'
        obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
        print(f"   🔗 '{obj.name}' parentado al armature '{armature_name}' (fallback)")
    else:
        print(f"   ⚠️ No se encontró armature '{armature_name}' para parentear '{obj.name}'")

    return armature_obj, target_bone


def apply_transform(obj, location=None, rotation_euler=None, scale=None):
    """
    Aplica location / rotation_euler / scale a un objeto si se proporcionan.
    Útil para correcciones ergonómicas (posición, rotación, escala validadas).
    """
    if location is not None:
        obj.location = location
    if rotation_euler is not None:
        obj.rotation_euler = rotation_euler
    if scale is not None:
        obj.scale = scale



# ============================================================
# SISTEMA DE TRANSICIONES CARTOON PROFESIONALES
# ============================================================

def _ensure_action(obj):
    """Asegura que el objeto tenga un action de animación activo."""
    if obj.animation_data is None:
        obj.animation_data_create()
    if obj.animation_data.action is None:
        action = bpy.data.actions.new(name=f"{obj.name}_anim")
        obj.animation_data.action = action
    return obj.animation_data.action


def _set_fcurve_interpolation(action, data_path, index=0, interp='BEZIER', easing='AUTO',
                               back=None, period=None, amplitude=None):
    """Configura la interpolación de todos los keyframes de una fcurve."""
    for fc in get_fcurves(action):
        if fc.data_path == data_path and fc.array_index == index:
            for kp in fc.keyframe_points:
                kp.interpolation = interp
                if hasattr(kp, 'easing'):
                    kp.easing = easing
                if back is not None and hasattr(kp, 'back'):
                    kp.back = back
                if period is not None and hasattr(kp, 'period'):
                    kp.period = period
                if amplitude is not None and hasattr(kp, 'amplitude'):
                    kp.amplitude = amplitude


def _kf_scale(obj, frame, sx, sy, sz):
    obj.scale = (sx, sy, sz)
    obj.keyframe_insert(data_path="scale", frame=frame)


def _kf_loc_offset(obj, frame, dx, dy, dz):
    """Inserta keyframe de location sumando offset a la location base del objeto."""
    base = obj.location.copy()
    obj.location = (base.x + dx, base.y + dy, base.z + dz)
    obj.keyframe_insert(data_path="location", frame=frame)
    obj.location = base


def _kf_loc_abs(obj, frame, x, y, z):
    obj.location = (x, y, z)
    obj.keyframe_insert(data_path="location", frame=frame)


def _kf_rot_z(obj, frame, rz):
    import math
    obj.rotation_euler = (obj.rotation_euler.x, obj.rotation_euler.y, rz)
    obj.keyframe_insert(data_path="rotation_euler", frame=frame, index=2)


def _ensure_alpha_material(obj):
    """
    Asegura que el material del objeto tenga un nodo de transparencia Alpha
    conectado para poder animar fade in/out. Usa BLEND o HASHED.
    """
    import bpy
    if not obj.data or not hasattr(obj.data, 'materials'):
        return False
    if not obj.data.materials:
        return False
    mat = obj.data.materials[0]
    if mat is None:
        return False
    mat.use_nodes = True
    mat.blend_method = 'BLEND'
    nt = mat.node_tree
    nodes = nt.nodes
    # Buscar Principled BSDF
    principled = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if principled is None:
        return False
    # Asegurar que Alpha esté en 1.0 inicialmente
    if principled.inputs['Alpha'].default_value < 0.01:
        principled.inputs['Alpha'].default_value = 1.0
    return True


def apply_transition_in(obj, item, base_scale, base_loc):
    """
    Aplica la transición de ENTRADA (aparición) del objeto.
    item.transition_in: tipo de transición
    item.transition_in_duration: duración en frames
    base_scale: escala final deseada (float uniforme)
    base_loc: location final deseada (tuple x,y,z)
    """
    import math
    t_type = getattr(item, 'transition_in', 'NONE')
    dur    = getattr(item, 'transition_in_duration', 8)
    f0     = item.frame_start        # frame donde inicia la transición
    f1     = item.frame_start + dur  # frame donde termina (objeto en estado final)
    s      = base_scale
    action = _ensure_action(obj)

    if t_type == 'NONE':
        return  # Sin transición — ya se puso hide_until_frame

    # --- Restaurar estado final al llegar f1 ---
    # (garantiza que después de la transición el objeto quede correcto)
    obj.scale = (s, s, s)
    obj.keyframe_insert(data_path="scale", frame=f1)
    obj.location = base_loc
    obj.keyframe_insert(data_path="location", frame=f1)

    if t_type == 'SCALE_POP':
        # Frame inicio: escala 0
        _kf_scale(obj, f0, 0.001, 0.001, 0.001)
        # Overshoot al 80%: escala 1.25
        f_over = f0 + int(dur * 0.6)
        _kf_scale(obj, f_over, s * 1.25, s * 1.25, s * 1.25)
        # Final: escala normal
        _kf_scale(obj, f1, s, s, s)
        for idx in range(3):
            _set_fcurve_interpolation(action, "scale", idx, 'BACK', 'AUTO', back=1.8)

    elif t_type == 'SCALE_BOUNCE':
        # Empieza pequeño desde arriba
        _kf_scale(obj, f0, 0.001, 0.001, 0.001)
        _kf_loc_offset(obj, f0, 0, 0, s * 1.5)
        # Aterriza con squash
        f_land = f0 + int(dur * 0.65)
        _kf_scale(obj, f_land, s * 1.3, s * 1.3, s * 0.6)
        _kf_loc_abs(obj, f_land, base_loc[0], base_loc[1], base_loc[2])
        # Bounce pequeño
        f_bounce = f0 + int(dur * 0.82)
        _kf_scale(obj, f_bounce, s * 0.9, s * 0.9, s * 1.15)
        # Final
        _kf_scale(obj, f1, s, s, s)
        _kf_loc_abs(obj, f1, base_loc[0], base_loc[1], base_loc[2])

    elif t_type == 'SCALE_SQUASH':
        # Aplastado horizontal → estira → normal
        _kf_scale(obj, f0, s * 2.0, s * 2.0, 0.001)
        f_stretch = f0 + int(dur * 0.5)
        _kf_scale(obj, f_stretch, s * 0.7, s * 0.7, s * 1.4)
        _kf_scale(obj, f1, s, s, s)
        for idx in range(3):
            _set_fcurve_interpolation(action, "scale", idx, 'ELASTIC', 'EASE_OUT')

    elif t_type == 'FADE_IN':
        ok = _ensure_alpha_material(obj)
        if ok and obj.data.materials:
            mat = obj.data.materials[0]
            principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if principled:
                inp = principled.inputs['Alpha']
                inp.default_value = 0.0
                inp.keyframe_insert("default_value", frame=f0)
                inp.default_value = 1.0
                inp.keyframe_insert("default_value", frame=f1)

    elif t_type == 'SLIDE_UP':
        _kf_loc_offset(obj, f0, 0, 0, -s * 2.0)
        _kf_loc_abs(obj, f1, base_loc[0], base_loc[1], base_loc[2])
        _set_fcurve_interpolation(action, "location", 2, 'BACK', 'EASE_OUT', back=1.5)

    elif t_type == 'SLIDE_DOWN':
        _kf_loc_offset(obj, f0, 0, 0, s * 2.0)
        _kf_loc_abs(obj, f1, base_loc[0], base_loc[1], base_loc[2])
        _set_fcurve_interpolation(action, "location", 2, 'BACK', 'EASE_OUT', back=1.5)

    elif t_type == 'SPIN_IN':
        import math
        _kf_scale(obj, f0, 0.001, 0.001, 0.001)
        _kf_rot_z(obj, f0, obj.rotation_euler.z + math.radians(360))
        _kf_scale(obj, f1, s, s, s)
        _kf_rot_z(obj, f1, obj.rotation_euler.z)
        for idx in range(3):
            _set_fcurve_interpolation(action, "scale", idx, 'BACK', 'EASE_OUT', back=1.4)
        _set_fcurve_interpolation(action, "rotation_euler", 2, 'CUBIC', 'EASE_OUT')

    elif t_type == 'IRIS_WIPE':
        # Crece desde 0 con exponencial — simula iris de cámara clásica
        _kf_scale(obj, f0, 0.001, 0.001, 0.001)
        f_mid = f0 + int(dur * 0.4)
        _kf_scale(obj, f_mid, s * 0.3, s * 0.3, s * 0.3)
        _kf_scale(obj, f1, s, s, s)
        for idx in range(3):
            _set_fcurve_interpolation(action, "scale", idx, 'EXPO', 'EASE_OUT')

    elif t_type == 'SWING_IN':
        import math
        base_rz = obj.rotation_euler.z
        # Columpia desde el lado, amortiguado
        _kf_scale(obj, f0, s, s, s)
        _kf_rot_z(obj, f0, base_rz + math.radians(45))
        f_over = f0 + int(dur * 0.6)
        _kf_rot_z(obj, f_over, base_rz - math.radians(8))
        _kf_rot_z(obj, f1, base_rz)
        _set_fcurve_interpolation(action, "rotation_euler", 2, 'ELASTIC', 'EASE_OUT')


def apply_transition_out(obj, item, base_scale, base_loc):
    """
    Aplica la transición de SALIDA (desaparición) del objeto.
    """
    import math
    t_type = getattr(item, 'transition_out', 'NONE')
    dur    = getattr(item, 'transition_out_duration', 8)
    f0     = item.frame_end - dur   # frame donde inicia la transición de salida
    f1     = item.frame_end         # frame donde el objeto queda oculto
    s      = base_scale
    action = _ensure_action(obj)

    if t_type == 'NONE':
        return

    # Estado inicial al comienzo de la transición de salida (objeto visible normal)
    obj.scale = (s, s, s)
    obj.keyframe_insert(data_path="scale", frame=f0)
    obj.location = base_loc
    obj.keyframe_insert(data_path="location", frame=f0)

    if t_type == 'SCALE_SHRINK':
        # Squash brevísimo antes de encoger
        f_squash = f0 + int(dur * 0.3)
        _kf_scale(obj, f_squash, s * 1.15, s * 1.15, s * 0.8)
        _kf_scale(obj, f1, 0.001, 0.001, 0.001)
        for idx in range(3):
            _set_fcurve_interpolation(action, "scale", idx, 'BACK', 'EASE_IN', back=1.6)

    elif t_type == 'SCALE_BOUNCE':
        # Salta hacia arriba antes de encoger
        f_jump = f0 + int(dur * 0.4)
        _kf_loc_offset(obj, f_jump, 0, 0, s * 0.8)
        _kf_scale(obj, f_jump, s * 0.9, s * 0.9, s * 1.1)
        _kf_loc_abs(obj, f1, base_loc[0], base_loc[1], base_loc[2])
        _kf_scale(obj, f1, 0.001, 0.001, 0.001)

    elif t_type == 'FADE_OUT':
        ok = _ensure_alpha_material(obj)
        if ok and obj.data.materials:
            mat = obj.data.materials[0]
            principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if principled:
                inp = principled.inputs['Alpha']
                inp.default_value = 1.0
                inp.keyframe_insert("default_value", frame=f0)
                inp.default_value = 0.0
                inp.keyframe_insert("default_value", frame=f1)

    elif t_type == 'SLIDE_UP':
        _kf_loc_abs(obj, f0, base_loc[0], base_loc[1], base_loc[2])
        _kf_loc_offset(obj, f1, 0, 0, s * 2.0)
        _set_fcurve_interpolation(action, "location", 2, 'BACK', 'EASE_IN', back=1.5)

    elif t_type == 'SLIDE_DOWN':
        _kf_loc_abs(obj, f0, base_loc[0], base_loc[1], base_loc[2])
        _kf_loc_offset(obj, f1, 0, 0, -s * 2.0)
        _set_fcurve_interpolation(action, "location", 2, 'BACK', 'EASE_IN', back=1.5)

    elif t_type == 'SPIN_OUT':
        _kf_scale(obj, f0, s, s, s)
        _kf_rot_z(obj, f0, obj.rotation_euler.z)
        _kf_scale(obj, f1, 0.001, 0.001, 0.001)
        _kf_rot_z(obj, f1, obj.rotation_euler.z - math.radians(360))
        for idx in range(3):
            _set_fcurve_interpolation(action, "scale", idx, 'BACK', 'EASE_IN', back=1.4)

    elif t_type == 'SWING_OUT':
        base_rz = obj.rotation_euler.z
        _kf_rot_z(obj, f0, base_rz)
        _kf_rot_z(obj, f1, base_rz - math.radians(60))
        _set_fcurve_interpolation(action, "rotation_euler", 2, 'BACK', 'EASE_IN', back=1.2)

    elif t_type == 'SQUASH_OUT':
        _kf_scale(obj, f0, s, s, s)
        f_squash = f0 + int(dur * 0.5)
        _kf_scale(obj, f_squash, s * 1.5, s * 1.5, s * 0.1)
        _kf_scale(obj, f1, 0.001, 0.001, 0.001)



def run_object_imports_live(scene, anchor_dir=None, segment_idx=None):
    """
    Ejecuta la importacion de todos los objetos activos definidos en
    scene.cerdo_1_st.object_imports directamente sobre la escena en vivo de Blender.

    Replica EXACTAMENTE la logica probada de _import_shield_at_frame /
    _import_sword_at_frame (slot_002_sacar_escudo.py / slot_003_sacar_espada.py):

        1. Si ya existe un objeto importado de una corrida anterior, se elimina
           (igual que slot_002, que siempre parte de cero).
        2. Importar el .blend (con fallback procedural si no existe el archivo
           o el objeto no se encuentra dentro de el).
        3. Asegurar material si el objeto no tiene ninguno (fallback procedural).
        4. Visibilidad: oculto hasta frame_start, visible desde frame_start
           hasta frame_end, oculto despues de frame_end.
        5. Buscar el armature y el bone (por nombre exacto o que contenga
           'bend') y parentear con parent_type='BONE', SIN tocar
           matrix_parent_inverse (igual que el slot original: queda en
           identidad por defecto al recien crear/parentear el objeto).
        6. Aplicar location / rotation_euler / scale tal cual estan
           configurados en el panel (offset local relativo al bone).

    Parámetros:
        scene:       bpy.types.Scene actual (debe tener scene.cerdo_1_st.object_imports)
        anchor_dir:  directorio ancla desde el cual subir 'levels_up' niveles
                      para llegar a la raiz del proyecto (Alfred_Animacion).
                      Si no se provee, se usa bpy.path.abspath(scene.cerdo_1_st.anim_dir).
        segment_idx: si se provee (int >= 0), solo se procesan los items con
                      item.segment_idx == segment_idx O item.segment_idx == -1
                      (los items con -1 son "globales" y se ejecutan siempre).
                      Si es None, se procesan TODOS los items (comportamiento
                      del CONCATENAR global).

    Retorna:
        (n_imported, n_skipped, errors) — contadores y lista de mensajes de error/advertencia.
    """
    import mathutils

    st = getattr(scene, 'cerdo_1_st', None)
    oi = getattr(st, 'object_imports', None) if st else None

    print("\n" + "=" * 60)
    print("[OBJ_IMPORTS] run_object_imports_live() llamado")
    print(f"[OBJ_IMPORTS] st={'OK' if st else 'None'}  oi={'OK' if oi else 'None'}  segment_idx={segment_idx}")

    if oi is None or not oi.enabled:
        print(f"[OBJ_IMPORTS] ABORTADO: oi.enabled = {getattr(oi, 'enabled', 'N/A')}")
        print("=" * 60 + "\n")
        return 0, 0, []

    if anchor_dir is None:
        anchor_dir = bpy.path.abspath(st.anim_dir) if st.anim_dir else bpy.path.abspath('//')

    print(f"[OBJ_IMPORTS] anchor_dir = {anchor_dir}")
    print(f"[OBJ_IMPORTS] total items en lista = {len(oi.items)}")

    n_imported = 0
    n_skipped  = 0
    errors     = []

    for idx, item in enumerate(oi.items):
        print(f"\n[OBJ_IMPORTS] --- Item #{idx}: '{item.label}' ---")
        print(f"[OBJ_IMPORTS]   enabled         = {item.enabled}")
        print(f"[OBJ_IMPORTS]   segment_idx     = {item.segment_idx}")
        print(f"[OBJ_IMPORTS]   object_folder   = '{item.object_folder}'")
        print(f"[OBJ_IMPORTS]   blend_filename  = '{item.blend_filename}'")
        print(f"[OBJ_IMPORTS]   object_name     = '{item.object_name}'")
        print(f"[OBJ_IMPORTS]   levels_up       = {item.levels_up}")
        print(f"[OBJ_IMPORTS]   frame_start     = {item.frame_start}")
        print(f"[OBJ_IMPORTS]   frame_end       = {item.frame_end}")
        print(f"[OBJ_IMPORTS]   parent_armature = '{item.parent_armature}'")
        print(f"[OBJ_IMPORTS]   parent_bone     = '{item.parent_bone}'")
        print(f"[OBJ_IMPORTS]   loc  = ({item.loc_x}, {item.loc_y}, {item.loc_z})")
        print(f"[OBJ_IMPORTS]   rot  = ({item.rot_x}, {item.rot_y}, {item.rot_z})")
        print(f"[OBJ_IMPORTS]   scale_uniform   = {item.scale_uniform}")
        print(f"[OBJ_IMPORTS]   imported_object_name = '{item.imported_object_name}'")

        if not item.enabled:
            print(f"[OBJ_IMPORTS]   -> SALTADO (item.enabled = False)")
            n_skipped += 1
            continue

        if segment_idx is not None and item.segment_idx != -1 and item.segment_idx != segment_idx:
            print(f"[OBJ_IMPORTS]   -> SALTADO (item.segment_idx={item.segment_idx} != "
                  f"segment_idx={segment_idx} y != -1)")
            n_skipped += 1
            continue

        try:
            # ── 1. Eliminar objeto de una corrida anterior (empezar de cero) ──
            print(f"[OBJ_IMPORTS]   [1] Verificando objeto previo...")
            if item.imported_object_name:
                old_obj = bpy.data.objects.get(item.imported_object_name)
                if old_obj is not None:
                    print(f"[OBJ_IMPORTS]       Eliminando objeto previo '{old_obj.name}'")
                    old_mesh = old_obj.data
                    bpy.data.objects.remove(old_obj, do_unlink=True)
                    if old_mesh is not None and old_mesh.users == 0:
                        bpy.data.meshes.remove(old_mesh)
                item.imported_object_name = ""

            # ── 2. Importar el .blend (con fallback procedural) ───────────────
            base_path  = get_objetos_base_path_from_anchor(anchor_dir, item.levels_up)
            object_dir = resolve_object_folder_path(base_path, item.object_folder)
            blend_path = os.path.join(object_dir, item.blend_filename)
            print(f"[OBJ_IMPORTS]   [2] base_path  = {base_path}")
            print(f"[OBJ_IMPORTS]   [2] object_dir = {object_dir}")
            print(f"[OBJ_IMPORTS]   [2] blend_path = {blend_path}")
            print(f"[OBJ_IMPORTS]   [2] existe?    = {os.path.exists(blend_path)}")

            obj = None
            if not os.path.exists(blend_path):
                print(f"   ⚠️ Archivo {item.blend_filename} no encontrado en {blend_path}, "
                      f"creando objeto procedural...")
            else:
                obj = import_object_from_blend_path(blend_path, item.object_name)
                print(f"[OBJ_IMPORTS]   [2] objeto importado = {obj.name if obj else None}")
                if obj is None:
                    print(f"   ⚠️ No se pudo importar '{item.object_name}', creando procedural...")

            if obj is None:
                print(f"   ⚠️ '{item.object_name}' no importado — se omite")
                errors.append(f"No se pudo importar '{item.object_name}' desde {blend_path}")
                continue

            # ── 3. Material si no tiene ninguno ────────────────────────────────
            if not obj.data.materials:
                ensure_material(
                    obj,
                    material_name=f"{item.object_name or item.label}_material",
                    base_color=(0.1, 0.1, 0.15, 1.0),
                    metallic=0.9,
                    roughness=0.2,
                    specular=0.5,
                )

            # ── 4. Visibilidad por rango de frames ─────────────────────────────
            print(f"[OBJ_IMPORTS]   [4] Visibilidad: aparece frame {item.frame_start}, "
                  f"desaparece frame {item.frame_end}")
            hide_until_frame(obj, appear_frame=item.frame_start)
            set_visibility_keyframes(obj, item.frame_end, visible=False)
            print(f"[OBJ_IMPORTS]   [4] hide_viewport keyframes insertados: "
                  f"{[ (kp.co.x, kp.co.y) for fc in (get_fcurves(obj.animation_data) if obj.animation_data and obj.animation_data.action else []) if fc.data_path=='hide_viewport' for kp in fc.keyframe_points ]}")

            # ── 4b. Transiciones cartoon ───────────────────────────────────
            _base_scale = item.scale_uniform
            _base_loc   = (item.loc_x, item.loc_y, item.loc_z)
            _t_in  = getattr(item, 'transition_in',  'NONE')
            _t_out = getattr(item, 'transition_out', 'NONE')
            print(f"[OBJ_IMPORTS]   [4b] transition_in='{_t_in}'  transition_out='{_t_out}'")
            if _t_in  != 'NONE':
                apply_transition_in(obj, item, _base_scale, _base_loc)
                print(f"[OBJ_IMPORTS]   [4b] transición entrada aplicada")
            if _t_out != 'NONE':
                apply_transition_out(obj, item, _base_scale, _base_loc)
                print(f"[OBJ_IMPORTS]   [4b] transición salida aplicada")

            # ── 5. Parentar al bone correcto del rig ───────────────────────────
            arm  = (item.parent_armature or '').strip()
            bone = (item.parent_bone or '').strip()
            print(f"[OBJ_IMPORTS]   [5] arm='{arm}' bone='{bone}'")

            armature_obj = None
            target_bone  = None

            all_armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']

            if arm:
                for o in all_armatures:
                    if o.name == arm:
                        armature_obj = o
                        break
                if armature_obj is None:
                    print(f"[OBJ_IMPORTS]   [5] ⚠️ armature '{arm}' NO encontrado en bpy.data.objects "
                          f"(armatures disponibles: {[o.name for o in all_armatures]})")

            # Fallback: si el nombre configurado no existe (o esta vacio) y la
            # escena tiene un unico armature, usarlo automaticamente. Cerdo_1
            # tiene un solo armature ("Armature") — esto evita que un nombre
            # incorrecto (ej. "left_arm") deje el objeto sin parentear.
            if armature_obj is None and len(all_armatures) == 1:
                armature_obj = all_armatures[0]
                print(f"[OBJ_IMPORTS]   [5] ⚙️ usando unico armature de la escena: '{armature_obj.name}' "
                      f"(configurado: '{arm}')")

            if armature_obj is not None:
                arm = armature_obj.name
                print(f"[OBJ_IMPORTS]   [5] armature '{arm}' encontrado, "
                      f"pose.bones={len(armature_obj.pose.bones) if armature_obj.pose else 0}")
                if armature_obj.pose and armature_obj.pose.bones:
                    if bone:
                        target_bone = armature_obj.pose.bones.get(bone)
                        print(f"[OBJ_IMPORTS]   [5] busqueda exacta '{bone}' -> "
                              f"{target_bone.name if target_bone else None}")
                    if target_bone is None:
                        for pb in armature_obj.pose.bones:
                            if 'bend' in pb.name.lower():
                                target_bone = pb
                                break
                        print(f"[OBJ_IMPORTS]   [5] busqueda 'bend' -> "
                              f"{target_bone.name if target_bone else None}")

            if target_bone:
                obj.parent = target_bone.id_data
                obj.parent_bone = target_bone.name
                obj.parent_type = 'BONE'
                obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
                print(f"   🔗 '{obj.name}' parentado al bone '{target_bone.name}' de '{arm}'")
            elif armature_obj:
                obj.parent = armature_obj
                obj.parent_type = 'OBJECT'
                obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
                print(f"   🔗 '{obj.name}' parentado al armature '{arm}' (fallback)")
            elif arm:
                print(f"   ⚠️ No se encontró armature '{arm}' para parentear '{obj.name}'")
            else:
                print(f"[OBJ_IMPORTS]   [5] parent_armature vacio, NO se parentea")

            print(f"[OBJ_IMPORTS]   [5] resultado: obj.parent={obj.parent.name if obj.parent else None}, "
                  f"parent_type={obj.parent_type}, parent_bone='{obj.parent_bone}'")

            # ── 6. Posicion / rotacion / escala (offset local relativo al bone) ─
            print(f"[OBJ_IMPORTS]   [6] Aplicando transform: "
                  f"loc=({item.loc_x},{item.loc_y},{item.loc_z}) "
                  f"rot=({item.rot_x},{item.rot_y},{item.rot_z}) "
                  f"scale={item.scale_uniform}")
            obj.location = (item.loc_x, item.loc_y, item.loc_z)
            obj.rotation_euler = (item.rot_x, item.rot_y, item.rot_z)
            obj.scale = (item.scale_uniform, item.scale_uniform, item.scale_uniform)
            print(f"[OBJ_IMPORTS]   [6] resultado: obj.location={tuple(obj.location)}, "
                  f"obj.rotation_euler={tuple(obj.rotation_euler)}, obj.scale={tuple(obj.scale)}")

            item.imported_object_name = obj.name

            print(f"  ✅ Objeto '{item.label}' importado (frames {item.frame_start}→{item.frame_end})")
            n_imported += 1

        except Exception as e_item:
            import traceback
            tb = traceback.format_exc()
            print(f"[OBJ_IMPORTS]   ❌ EXCEPCION en item '{item.label}':")
            print(tb)
            errors.append(f"Objeto '{item.label}': {e_item}")
            n_skipped += 1

    print(f"\n[OBJ_IMPORTS] RESULTADO: imported={n_imported} skipped={n_skipped} errors={errors}")
    print("=" * 60 + "\n")
    return n_imported, n_skipped, errors


# ============================================================
# EJEMPLO DE USO (equivalente a _import_shield_at_frame / _import_sword_at_frame)
# ============================================================
#
# from object_import_utils import (
#     import_object_from_blend, create_procedural_fallback, ensure_material,
#     set_visibility_keyframes, hide_until_frame, parent_to_bone, apply_transform
# )
#
# def _import_shield_at_frame(frame: int):
#     shield_obj = import_object_from_blend(
#         file_dunder=__file__,
#         object_folder='shield',
#         blend_filename='shield.blend',
#         object_name='shield',
#     )
#
#     if shield_obj is None:
#         shield_obj = create_procedural_fallback(
#             name='shield', kind='plane', scale=(0.8, 1.2, 0.1)
#         )
#
#     ensure_material(
#         shield_obj, material_name='shield_material',
#         base_color=(0.1, 0.1, 0.15, 1.0), metallic=0.9, roughness=0.2, specular=0.5
#     )
#
#     set_visibility_keyframes(shield_obj, frame, visible=True)
#
#     parent_to_bone(shield_obj, armature_name='left_arm', bone_name_contains=('bend', 'left_arm.003'))
#
#     apply_transform(
#         shield_obj,
#         location=(0, -0.14, -0.05),
#         rotation_euler=(-1.5708, 0, 4.7124),
#         scale=(1.2, 1.2, 1.2),
#     )
#
#     return shield_obj
#
#
# def _import_sword_at_frame(frame: int):
#     sword_obj = import_object_from_blend(
#         file_dunder=__file__,
#         object_folder='stone_sword',
#         blend_filename='stone_sword.blend',
#         object_name='stone_sword',
#     )
#
#     if sword_obj is None:
#         sword_obj = create_procedural_fallback(
#             name='sword', kind='cylinder', scale=(0.8, 0.8, 0.8)
#         )
#     else:
#         sword_obj.scale = (0.8, 0.8, 0.8)
#
#     ensure_material(
#         sword_obj, material_name='sword_material',
#         base_color=(0.8, 0.8, 0.9, 1.0), metallic=1.0
#     )
#
#     # Oculto hasta su frame de aparición (ej: 219), visible desde ahí
#     hide_until_frame(sword_obj, appear_frame=frame)
#
#     parent_to_bone(sword_obj, armature_name='right_arm', bone_name_contains=('bend', 'right_arm.003'))
#
#     apply_transform(
#         sword_obj,
#         location=(-0.4, 0.05, 0.03),
#         rotation_euler=(math.radians(2), math.radians(-0.3), math.radians(135)),
#         scale=(0.9, 0.9, 0.9),
#     )
#
#     return sword_obj
