# -*- coding: utf-8 -*-
"""
ai_export.py -- FLUJO IA: salida independiente de una animacion terminada.

Hay DOS flujos y no se mezclan (ver refinar/docs/FLUJOS_MANUAL_E_IA.md):

  FLUJO MANUAL  El usuario arma la secuencia en los paneles y la guarda como guion
                (.json en configuraciones/). El guion es la receta editable.

  FLUJO IA      Una IA (en paralelo al manual, y varias IA a la vez) crea la animacion y guarda
                el RESULTADO COMPLETO en su propia carpeta animaciones_ia/<nombre>/ :
                    <nombre>.animacion.json   datos horneados fotograma a fotograma
                    <nombre>.py               script autonomo (datos embebidos), no requiere el add-on
                    manifest.json             quien, cuando, rango, canales, fuente y limitaciones
                No lee ni escribe el guion del usuario ni scene.cerdo_1_st: el guion nunca es cuello de botella.

Cada animacion IA usa nombres propios (pistas/acciones "IA_<nombre>__*"), asi que varias IA pueden
trabajar sobre la misma escena sin pisarse, e importar/reimportar es idempotente.

Uso:
    from cerdo_1_animation_studio import ai_export
    ai_export.exportar("persecucion_zombie_agua", agente="claude", guion_fuente=None)
    ai_export.importar("persecucion_zombie_agua")          # o una ruta a <nombre>.animacion.json
"""
import bpy
import json
import math
import os
from datetime import datetime

from .constants import BONES_LISTA_FULL

CARPETA_IA = (
    r"C:\Users\user\Desktop\Alfred_Animacion"
    r"\generador de animaciones\cerdo_1\refinar\animaciones_ia"
)
FORMATO = "cerdo_1_ia_anim/1"
_ROOT = "cerdo_1"
_ARM = "pig.arma_cerdo_1"
_OJOS = ("ojo_izquierdo_cerdo_1", "ojo_derecho_cerdo_1")
_DEC = 5

# Personajes conocidos. `ojos` = objetos con transformaciones/shape keys animados; `extras` = props ajenos al rig
# que tambien se hornean (deben existir al hornear); `extras_fuente` = de que .blend importarlos si faltan al
# reproducir en otra escena: {nombre: {"blend": ruta, "objetos": [...], "raiz": nombre_del_empty_en_el_blend}}.
CERDO_1 = {"root": "cerdo_1", "armature": "pig.arma_cerdo_1", "ojos": ["ojo_izquierdo_cerdo_1", "ojo_derecho_cerdo_1"],
          "extras": [], "extras_fuente": {}, "todos_los_huesos": False, "carpeta": CARPETA_IA}
JERRY = {"root": "jerry", "armature": "Dog_001_rig",
         "ojos": ["ojo_izquierdo_jerry", "ojo_derecho_jerry", "pupila_izquierda_jerry", "pupila_derecha_jerry"],
         "extras": [], "extras_fuente": {}, "todos_los_huesos": True,
         "carpeta": r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\jerry\refinar\animaciones_ia"}

# Codigo que aplica los datos horneados. Es la unica fuente: se ejecuta desde importar() y se
# incrusta tal cual en el .py autonomo que genera exportar().
RUNTIME = r'''
import bpy

try:
    from bpy_extras import anim_utils as _anim_utils
except Exception:
    _anim_utils = None


def _fcurves(anim_data, id_owner):
    """FCurves de anim_data.action en Blender viejo y en 5.x (slot -> channelbag)."""
    action = anim_data.action
    if hasattr(action, "fcurves"):
        return action.fcurves
    slot = anim_data.action_slot
    if slot is None:
        if len(action.slots):
            slot = action.slots[0]
        else:
            slot = action.slots.new(id_type=id_owner.id_type, name=id_owner.name)
        anim_data.action_slot = slot
    return _anim_utils.action_ensure_channelbag_for_slot(action, slot).fcurves


def _canal(fcs, data_path, index, frames, valores, constante=False):
    fc = fcs.new(data_path=data_path, index=index)
    fc.keyframe_points.add(len(frames))
    co = []
    for f, v in zip(frames, valores):
        co.extend((float(f), float(v)))
    fc.keyframe_points.foreach_set("co", co)
    for kp in fc.keyframe_points:
        kp.interpolation = "CONSTANT" if constante else "LINEAR"
    fc.update()


def _expandir(c, n):
    return [c] * n if not isinstance(c, list) else c


def _pista(id_owner, nombre_pista, action, f0, f1):
    ad = id_owner.animation_data
    ad.action = None
    track = ad.nla_tracks.new()
    track.name = nombre_pista
    strip = track.strips.new(nombre_pista, int(f0), action)
    if hasattr(strip, "action_slot") and getattr(action, "slots", None):
        strip.action_slot = action.slots[0]
    strip.use_sync_length = False
    strip.action_frame_start = f0
    strip.action_frame_end = f1
    strip.frame_start = f0
    strip.frame_end = f1
    strip.extrapolation = "NOTHING"
    strip.blend_type = "REPLACE"
    ad.action = None


def _limpiar(id_owner, prefijo):
    ad = getattr(id_owner, "animation_data", None)
    if ad is None:
        return
    for t in list(ad.nla_tracks):
        if t.name.startswith(prefijo):
            ad.nla_tracks.remove(t)
    for a in list(bpy.data.actions):
        if a.name.startswith(prefijo) and a.users == 0:
            bpy.data.actions.remove(a)


def _conservar_base(id_owner, prefijo):
    """Si el objeto tiene una accion ACTIVA ajena (no una pista IA), pasarla a una pista NLA 'base' sostenida
    antes de escribir: la accion activa se evalua ENCIMA del NLA y asignar otra la desasigna (se perderia)."""
    ad = id_owner.animation_data
    if ad is None or ad.action is None or ad.action.name.startswith(prefijo):
        return
    act = ad.action
    ad.action = None
    tr = ad.nla_tracks.new(); tr.name = "Base_" + act.name[:40]
    f0 = int(act.frame_range[0])
    st = tr.strips.new(tr.name, f0, act)
    if hasattr(st, "action_slot") and getattr(act, "slots", None):
        try:
            st.action_slot = act.slots[0]
        except RuntimeError:
            pass      # slot de otro tipo de ID (ej. accion de shape keys creada con slot OBJECT)
    st.extrapolation = "HOLD_FORWARD"
    st.blend_type = "REPLACE"


def _escribir(id_owner, prefijo, parte, frames, canales, f0, f1):
    """canales: [(data_path, index, valores|constante, constante_bool)]"""
    if not canales:
        return 0
    if id_owner.animation_data is None:
        id_owner.animation_data_create()
    _conservar_base(id_owner, prefijo)
    nombre = f"{prefijo}{parte}"
    action = bpy.data.actions.new(nombre)
    id_owner.animation_data.action = action
    fcs = _fcurves(id_owner.animation_data, id_owner)
    n = 0
    for dp, idx, vals, const in canales:
        _canal(fcs, dp, idx, frames, _expandir(vals, len(frames)), const)
        n += 1
    _pista(id_owner, nombre, action, f0, f1)
    return n


def _asegurar_extras(data):
    """Importa los props (extras) que falten en la escena desde su .blend de origen."""
    for nombre, f in data.get("extras_fuente", {}).items():
        if nombre in bpy.data.objects:
            continue
        antes = set(bpy.data.objects.keys())
        with bpy.data.libraries.load(f["blend"], link=False) as (src, dst):
            dst.objects = [n for n in f["objetos"] if n in src.objects]
        nuevos = [o for o in bpy.data.objects if o.name not in antes]
        for o in nuevos:
            if not o.users_collection:
                bpy.context.scene.collection.objects.link(o)
            o.hide_viewport = False
            o.hide_render = False
        raiz = next((o for o in nuevos if o.name.split(".")[0] == f["raiz"] and o.type == "EMPTY"), None)
        if raiz is not None:
            raiz.name = nombre
        for o in nuevos:
            if o is not raiz and o.parent is None:
                bpy.data.objects.remove(o, do_unlink=True)


def _brillo(cfg):
    """Ojos que brillan SIEMPRE: emision constante para la camara (misma malla de nodos que el add-on del zombie)."""
    for n in cfg["objetos"]:
        o = bpy.data.objects.get(n)
        if o is None:
            continue
        for slot in o.material_slots:
            m = slot.material
            if m is None:
                continue
            m.use_nodes = True
            nt = m.node_tree
            em = nt.nodes.get("Zombie1EyeEmission") or nt.nodes.get("IA_ojo_emision")
            if em is None:
                out = next((x for x in nt.nodes if x.type == "OUTPUT_MATERIAL" and x.is_active_output), None) or nt.nodes.new("ShaderNodeOutputMaterial")
                mix = nt.nodes.new("ShaderNodeMixShader"); em = nt.nodes.new("ShaderNodeEmission"); em.name = "IA_ojo_emision"
                rays = nt.nodes.new("ShaderNodeLightPath"); dark = nt.nodes.new("ShaderNodeBsdfDiffuse")
                dark.inputs["Color"].default_value = (0, 0, 0, 1)
                nt.links.new(dark.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
                nt.links.new(rays.outputs["Is Camera Ray"], mix.inputs[0]); nt.links.new(mix.outputs[0], out.inputs["Surface"])
            for k in ("Color", "Strength"):
                try:
                    em.inputs[k].driver_remove("default_value")
                except Exception:
                    pass
            m.diffuse_color = (*cfg["color"], 1.0)   # tambien rojo en la vista solida/material
            em.inputs["Color"].default_value = (*cfg["color"], 1.0)
            em.inputs["Strength"].default_value = cfg.get("fuerza", 1.0)


def aplicar(data, frame_offset=0, root_name=None, armature_name=None):
    """Reconstruye la animacion horneada como pistas NLA propias (IA_<nombre>__*)."""
    _asegurar_extras(data)
    prefijo = f"IA_{data['nombre']}__"
    f0 = data["frame_inicio"] + frame_offset
    f1 = data["frame_fin"] + frame_offset
    frames = [f0 + i for i in range(data["frame_fin"] - data["frame_inicio"] + 1)]
    total = 0
    objs = bpy.data.objects

    root = objs.get(root_name or data["root"]["objeto"])
    arm = objs.get(armature_name or data["armature"]["objeto"])
    if root is not None:
        _limpiar(root, prefijo)
        ch = []
        for dp, ejes in data["root"]["canales"].items():
            for i, v in enumerate(ejes):
                ch.append((dp, i, v, False))
        total += _escribir(root, prefijo, "root", frames, ch, f0, f1)
    if arm is not None:
        for _b in data["armature"]["bones"]:
            _pb = arm.pose.bones.get(_b)
            if _pb is not None:
                _pb.rotation_mode = "XYZ"      # los datos horneados son Euler XYZ
        _limpiar(arm, prefijo)
        ch = []
        for dp, ejes in data["armature"].get("objeto_canales", {}).items():
            for i, v in enumerate(ejes):
                ch.append((dp, i, v, False))
        for bone, props in data["armature"]["bones"].items():
            for prop, ejes in props.items():
                for i, v in enumerate(ejes):
                    ch.append((f'pose.bones["{bone}"].{prop}', i, v, False))
        total += _escribir(arm, prefijo, "armature", frames, ch, f0, f1)
    for nombre_ojo, d in list(data.get("ojos", {}).items()) + list(data.get("extras", {}).items()):
        ojo = objs.get(nombre_ojo)
        if ojo is None:
            continue
        _limpiar(ojo, prefijo)
        ch = [(dp, i, v, False) for dp, ejes in d["canales"].items() for i, v in enumerate(ejes)]
        ch += [(dp, -1, v, True) for dp, v in d.get("visibilidad", {}).items()]
        ch = [(dp, (0 if i == -1 else i), v, c) for dp, i, v, c in ch]
        total += _escribir(ojo, prefijo, nombre_ojo, frames, ch, f0, f1)
        keys = getattr(getattr(ojo, "data", None), "shape_keys", None)
        if keys is not None and d.get("shape_keys"):
            _limpiar(keys, prefijo)
            ch = [(f'key_blocks["{k}"].value', 0, v, False) for k, v in d["shape_keys"].items()]
            total += _escribir(keys, prefijo, nombre_ojo + "_shapes", frames, ch, f0, f1)
    if data.get("brillo_ojos"):
        _brillo(data["brillo_ojos"])
    return total
'''


# ----------------------------------------------------------------------------- horneado

def _r(v):
    return round(float(v), _DEC)


def _comprimir(serie):
    """Lista de valores -> valor unico si es constante."""
    return serie[0] if all(abs(x - serie[0]) < 1e-6 for x in serie) else serie


_BAKE = {}


def _muestrear(f, arm, root, ojos, extras=(), todos=False):
    sc = bpy.context.scene
    sc.frame_set(f)
    fila = {"root": {"location": [_r(v) for v in root.location], "rotation_euler": [_r(v) for v in root.rotation_euler]},
            "bones": {}, "ojos": {}, "extras": {},
            "arm_obj": {"location": [_r(v) for v in arm.location], "rotation_euler": [_r(v) for v in arm.rotation_euler], "scale": [_r(v) for v in arm.scale]}}
    nombres = [pb.name for pb in arm.pose.bones] if todos else BONES_LISTA_FULL
    for b in nombres:
        pb = arm.pose.bones.get(b)
        if pb is None:
            continue
        rot = pb.rotation_euler if pb.rotation_mode not in ("QUATERNION", "AXIS_ANGLE") else pb.rotation_quaternion.to_euler("XYZ")
        fila["bones"][b] = {"rotation_euler": [_r(v) for v in rot], "location": [_r(v) for v in pb.location], "scale": [_r(v) for v in pb.scale]}
    for destino, lista in (("ojos", ojos), ("extras", extras)):
        for o in lista:
            keys = getattr(getattr(o, "data", None), "shape_keys", None)
            fila[destino][o.name] = {
                "location": [_r(v) for v in o.location], "rotation_euler": [_r(v) for v in o.rotation_euler], "scale": [_r(v) for v in o.scale],
                "hide_viewport": float(o.hide_viewport), "hide_render": float(o.hide_render),
                "shape_keys": {k.name: _r(k.value) for k in keys.key_blocks if k.name != "Basis"} if keys else {},
            }
    return fila


def _armar(nombre, filas, f0, f1, personaje=CERDO_1):
    def serie(getter):
        return _comprimir([getter(fl) for fl in filas])

    data = {
        "formato": FORMATO, "nombre": nombre, "fps": bpy.context.scene.render.fps,
        "frame_inicio": f0, "frame_fin": f1,
        "root": {"objeto": personaje["root"], "canales": {
            p: [serie(lambda fl, p=p, i=i: fl["root"][p][i]) for i in range(3)] for p in ("location", "rotation_euler")}},
        "armature": {"objeto": personaje["armature"], "bones": {},
                     "objeto_canales": {p: [serie(lambda fl, p=p, i=i: fl["arm_obj"][p][i]) for i in range(3)] for p in ("location", "rotation_euler", "scale")}},
        "ojos": {}, "extras": {}, "extras_fuente": personaje.get("extras_fuente", {}),
        "brillo_ojos": ({"objetos": list(personaje["ojos"]), **personaje["brillo_ojos"]} if personaje.get("brillo_ojos") else None),
    }
    for b in filas[0]["bones"]:
        data["armature"]["bones"][b] = {
            p: [serie(lambda fl, b=b, p=p, i=i: fl["bones"][b][p][i]) for i in range(3)] for p in ("rotation_euler", "location", "scale")}
    for destino in ("ojos", "extras"):
        for o in filas[0][destino]:
            data[destino][o] = {
                "canales": {p: [serie(lambda fl, o=o, p=p, i=i, dd=destino: fl[dd][o][p][i]) for i in range(3)] for p in ("location", "rotation_euler", "scale")},
                "visibilidad": {p: serie(lambda fl, o=o, p=p, dd=destino: fl[dd][o][p]) for p in ("hide_viewport", "hide_render")},
                "shape_keys": {k: serie(lambda fl, o=o, k=k, dd=destino: fl[dd][o]["shape_keys"][k]) for k in filas[0][destino][o]["shape_keys"]}}
    return data


def _ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _canales(fila):
    """(lista [x,y,z], es_rotacion) de root y huesos (los ojos no se suavizan)."""
    for k, v in fila["root"].items():
        yield v, k == "rotation_euler"
    for props in fila["bones"].values():
        for k, v in props.items():
            yield v, k == "rotation_euler"


def _dif(x, y, rot):
    d = y - x
    return (d + math.pi) % (2 * math.pi) - math.pi if rot else d


def suavizar(filas, f0, cortes, ventana=8):
    """
    Quita el salto en cada corte (frame donde empieza una animacion/tramo nuevo) repartiendolo con
    una curva suave: la mitad de la diferencia se corrige en `ventana` frames antes del corte y la
    otra mitad en `ventana` frames despues. Devuelve el salto maximo antes y despues (en unidades del canal).
    """
    def salto_max():
        m = 0.0
        for c in cortes:
            i = c - f0
            if 0 < i < len(filas):
                for (a, rot), (b, _) in zip(_canales(filas[i - 1]), _canales(filas[i])):
                    m = max(m, max(abs(_dif(x, y, rot)) for x, y in zip(a, b)))
        return round(m, 4)

    antes = salto_max()
    for c in cortes:
        i = c - f0
        if not 0 < i < len(filas):
            continue
        a_rows, b_rows = filas[i - 1], filas[i]
        saltos = [[_dif(x, y, rot) for x, y in zip(a, b)] for (a, rot), (b, _) in zip(_canales(a_rows), _canales(b_rows))]
        for k in range(ventana):
            w_post = 0.5 * (1 - _ease((k + 1) / (ventana + 1)))          # despues: de 0.5 a 0
            w_pre = 0.5 * (1 - _ease((k + 1) / (ventana + 1)))           # antes: de 0.5 a 0
            for j, fila_i in ((i + k, -w_post), (i - 1 - k, w_pre)):
                if 0 <= j < len(filas):
                    for (canal, _r), s in zip(_canales(filas[j]), saltos):
                        for e in range(3):
                            canal[e] = round(canal[e] + fila_i * s[e], _DEC)
    return {"salto_max_antes": antes, "salto_max_despues": salto_max()}


def zombie(n):
    """Personaje zombie_<n> (kit portado: root zombie_n, armature zombie_n_Armature, ojos ojo_*_zombie_n)."""
    return {"root": f"zombie_{n}", "armature": f"zombie_{n}_Armature",
            "ojos": [f"ojo_izquierdo_zombie_{n}", f"ojo_derecho_zombie_{n}"],
            "extras": [], "extras_fuente": {}, "todos_los_huesos": True,
            "brillo_ojos": {"color": [0.8, 0.015, 0.01], "fuerza": 1.0},
            "carpeta": rf"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\zombie_{n}\refinar\animaciones_ia"}


def hornear(nombre, frame_inicio=None, frame_fin=None, tanda=None, suavizar_en=None, ventana=8, personaje=CERDO_1, desfase=0, mantener_hasta=None):
    """
    Hornea la escena actual fotograma a fotograma. Con `tanda` (frames por llamada) devuelve
    {'listo': False, ...} hasta terminar: llamar de nuevo con los mismos argumentos.
    personaje: CERDO_1 (por defecto), JERRY, zombie(n) o un dict propio con la misma forma.
    mantener_hasta: repite la ultima pose hasta ese frame (el personaje se queda quieto al terminar en vez de volver a su pose base).
    desfase: desplaza TODA la animacion exportada esa cantidad de frames (puede ser negativo: un personaje que
    empieza antes del frame 1 de la escena). Los frames de `suavizar_en` y del rango van en frames de la escena.
    """
    sc = bpy.context.scene
    f0 = int(frame_inicio if frame_inicio is not None else sc.frame_start)
    f1 = int(frame_fin if frame_fin is not None else sc.frame_end)
    est = _BAKE.get(nombre)
    if est is None or est["f0"] != f0 or est["f1"] != f1:
        est = _BAKE[nombre] = {"f0": f0, "f1": f1, "sig": f0, "filas": [], "frame_original": sc.frame_current}
    arm = bpy.data.objects[personaje["armature"]]
    root = bpy.data.objects[personaje["root"]]
    ojos = [bpy.data.objects[n] for n in personaje["ojos"] if n in bpy.data.objects]
    extras = [bpy.data.objects[n] for n in personaje.get("extras", []) if n in bpy.data.objects]
    tope = f1 if tanda is None else min(f1, est["sig"] + tanda - 1)
    for f in range(est["sig"], tope + 1):
        est["filas"].append(_muestrear(f, arm, root, ojos, extras, personaje.get("todos_los_huesos", False)))
    est["sig"] = tope + 1
    if est["sig"] <= f1:
        return {"listo": False, "hecho": est["sig"] - f0, "total": f1 - f0 + 1}
    sc.frame_set(est["frame_original"])
    if mantener_hasta and mantener_hasta > f1:
        import copy
        for _ in range(mantener_hasta - f1):
            est["filas"].append(copy.deepcopy(est["filas"][-1]))
        f1 = int(mantener_hasta)
    info = suavizar(est["filas"], f0, suavizar_en, ventana) if suavizar_en else None
    data = _armar(nombre, est["filas"], f0, f1, personaje)
    if desfase:
        data["frame_inicio"] += desfase
        data["frame_fin"] += desfase
        data["desfase"] = desfase
    if info:
        data["suavizado"] = {"cortes": list(suavizar_en), "ventana": ventana, **info}
    del _BAKE[nombre]
    return {"listo": True, "data": data}


# ----------------------------------------------------------------------------- salida

def _carpeta(nombre, personaje=CERDO_1):
    return os.path.join(personaje["carpeta"], nombre)


def exportar(nombre, agente="ia", guion_fuente=None, notas="", frame_inicio=None, frame_fin=None, tanda=None,
             suavizar_en=None, ventana=8, personaje=CERDO_1, desfase=0, mantener_hasta=None):
    """
    Hornea y escribe <carpeta del personaje>/<nombre>/ (.animacion.json, .py autonomo, manifest.json).
    suavizar_en: frames donde empieza un tramo/animacion nuevo (ej. [83, 173, 179, 262]); en cada uno se
    reparte el salto entre `ventana` frames antes y despues.
    personaje: CERDO_1 (animaciones_ia de Cerdo_1) o JERRY (animaciones_ia de Jerry).
    """
    r = hornear(nombre, frame_inicio, frame_fin, tanda, suavizar_en, ventana, personaje, desfase, mantener_hasta)
    if not r["listo"]:
        return r
    data = r["data"]
    dirp = _carpeta(nombre, personaje)
    os.makedirs(dirp, exist_ok=True)
    fj = os.path.join(dirp, f"{nombre}.animacion.json")
    with open(fj, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    fp = os.path.join(dirp, f"{nombre}.py")
    with open(fp, "w", encoding="utf-8") as f:
        f.write(_plantilla_py(nombre, data))
    n_canales = sum(len(p) * 3 for p in data["armature"]["bones"].values()) + 6
    man = {
        "formato": FORMATO, "flujo": "IA", "nombre": nombre, "agente": agente,
        "creado": datetime.now().isoformat(timespec="seconds"), "blender": bpy.app.version_string,
        "fps": data["fps"], "frames": [data["frame_inicio"], data["frame_fin"]],
        "objetos": [data["root"]["objeto"], data["armature"]["objeto"], *data["ojos"].keys(), *data["extras"].keys()],
        "canales_armature_y_root": n_canales,
        "guion_fuente": guion_fuente, "notas": notas, "suavizado": data.get("suavizado"),
        "archivos": [os.path.basename(fj), os.path.basename(fp)],
        "aplicar": f"blender <personaje>.blend --python {nombre}.py   |   ai_export.importar('{nombre}', personaje=...)",
        "limitaciones": [
            "Solo incluye root, huesos, objetos de ojos y los `extras` listados en el personaje; no incluye otros props, invisibilidad de mallas ni objetos ajenos.",
            "Los extras que falten al reproducir se importan de `extras_fuente` (si esta definido).",
            "Fotograma a fotograma (interpolacion LINEAL): es un resultado final, no una receta editable.",
            "Las pistas se crean como IA_<nombre>__*; reimportar reemplaza solo esas pistas.",
        ],
    }
    with open(os.path.join(dirp, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
    return {"listo": True, "carpeta": dirp, "archivos": man["archivos"] + ["manifest.json"], "frames": man["frames"]}


def _plantilla_py(nombre, data):
    return (
        '# -*- coding: utf-8 -*-\n'
        f'"""\nAnimacion IA "{nombre}" -- script autonomo (FLUJO IA, ver FLUJOS_MANUAL_E_IA.md).\n'
        f'No requiere el add-on. Con el personaje en la escena (root "{data["root"]["objeto"]}" + armature "{data["armature"]["objeto"]}" + ojos):\n'
        f'    blender <personaje>.blend --python {nombre}.py      o  ejecutarlo desde el Text Editor.\n'
        f'Rango {data["frame_inicio"]}-{data["frame_fin"]} a {data["fps"]} fps. FRAME_OFFSET desplaza el inicio.\n"""\n'
        + RUNTIME +
        '\n\nFRAME_OFFSET = 0\nDATA = ' + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + '\n\n'
        'if __name__ == "__main__":\n'
        '    print("Canales escritos:", aplicar(DATA, FRAME_OFFSET))\n'
    )


def importar(origen, frame_offset=0, root_name=None, armature_name=None, personaje=CERDO_1):
    """Aplica una animacion IA (nombre de carpeta o ruta a .animacion.json) al personaje en la escena actual."""
    ruta = origen
    if not os.path.isfile(ruta):
        ruta = os.path.join(_carpeta(origen, personaje), f"{origen}.animacion.json")
    with open(ruta, "r", encoding="utf-8") as f:
        data = json.load(f)
    ns = {}
    exec(compile(RUNTIME, "<ai_export.RUNTIME>", "exec"), ns)
    n = ns["aplicar"](data, frame_offset, root_name, armature_name)
    return {"nombre": data["nombre"], "canales": n, "frames": [data["frame_inicio"] + frame_offset, data["frame_fin"] + frame_offset]}
