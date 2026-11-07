# -*- coding: utf-8 -*-
"""
camara_guion.py -- Cerdo_1 Animation Studio: CAMARA del guion 2.0 (fase 5 del plan `docs/PLAN_PARTE3_AL_FLUJO.md`). Sustituye a `parte3/camara_final_parte3.py`.

Seccion `camara` (lista de entradas, todas con `objeto`; los tiempos aceptan anclas)
  {tipo: "claves", objeto, canal, claves: [[t, x, y, z] | [t, valor]...], interp, nota}
        la animacion YA HECHA de un canal de la camara / foco (la camara profesional de la parte 3, f1-683: una clave por frame):  canal = location (3 valores) | lens | dof.aperture_fstop (1 valor)
        se capturan de la escena (`capturar_claves`) y se vuelven a escribir tal cual (`aplicar_camara`) en el rango de la primera a la ultima clave
  {tipo: "movimiento", objeto, desde, hasta, destino: [x, y, z], interp, nota}      (el tipo por omision)
        desde `desde` el objeto se mueve de donde esta (su valor en desde-1) a `destino` en `hasta`; todo lo que habia de `desde` en adelante se sustituye. interp = BEZIER (suave) | LINEAR | CONSTANT (corte)
`aplicar_camara` escribe por la API de fcurves en la accion donde ya estan las claves del objeto (nunca crea una accion que tape otra) y es repetible.
"""
import copy

import bpy

try:
    from . import guion_v2 as gv
    from .claves_util import escritor_de, fcurves
except Exception:                                                                      # fuera del paquete (exec por ruta)
    import importlib.util as _ilu
    import os as _os

    def _cargar(n):
        sp = _ilu.spec_from_file_location(n, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), n + ".py")); m = _ilu.module_from_spec(sp); sp.loader.exec_module(m); return m
    gv = _cargar("guion_v2"); _cu = _cargar("claves_util"); escritor_de, fcurves = _cu.escritor_de, _cu.fcurves

INTERP = {"smooth": "BEZIER", "bezier": "BEZIER", "linear": "LINEAR", "constant": "CONSTANT", "ease_in": "BEZIER", "ease_out": "BEZIER"}


def _bloque(ob, canal):
    """(datablock, [(ruta, indice)]) de un canal: location es del objeto; lens / dof.* son de los datos de la camara."""
    if canal.startswith("data."): canal = canal[5:]                                          # los portables escriben `data.lens` / `data.dof.aperture_fstop` (ruta desde el objeto)
    if canal == "location": return ob, [("location", i) for i in range(3)]
    if ob.type != 'CAMERA': raise ValueError("%s no es una camara: no tiene el canal %r" % (ob.name, canal))
    return ob.data, [(canal, 0)]


def _refrescar(context, obs):
    for idb in obs:
        ad = idb.animation_data
        if ad and ad.nla_tracks: ad.use_nla = False; ad.use_nla = True
        if hasattr(idb, "update_tag"): idb.update_tag()
    context.scene.frame_set(context.scene.frame_current); context.view_layer.update()


def aplicar_camara(context, data):
    """escribe las claves y movimientos de `camara` en la escena. -> {"claves": n, "movimientos": n, "objetos": [...]}"""
    d = gv.desplegar(gv.migrar(data)); ents = d.get("camara") or []; tocados = []; nc = nm = 0
    for c in [e for e in ents if e.get("tipo") == "claves"]:
        ob = bpy.data.objects[c["objeto"]]; idb, rutas = _bloque(ob, c["canal"]); rows = c["claves"]
        w = escritor_de(idb, rutas[0][0], rutas[0][1], int(rows[0][0]))
        for ruta, i in rutas: w.limpiar(ruta, i, rows[0][0], rows[-1][0])
        for row in rows:
            for j, (ruta, i) in enumerate(rutas): w.poner(ruta, i, int(row[0]), float(row[1 + j]), INTERP.get(c.get("interp", "smooth")))
        w.cerrar(); tocados.append(idb); nc += 1
    movs = {}
    for c in ents:
        if c.get("tipo", "movimiento") == "movimiento": movs.setdefault(c["objeto"], []).append(c)
    for nombre, lst in movs.items():
        ob = bpy.data.objects[nombre]; lst.sort(key=lambda m: m["desde"]); w = escritor_de(ob, "location", 0, lst[0]["desde"])
        for i in range(3): w.limpiar("location", i, lst[0]["desde"], None)
        for m in lst:
            interp = INTERP.get(m.get("interp", "smooth"))
            hold = [w.evaluar("location", i, m["desde"] - 1) if w.existe("location", i) and w.fc[("location", i)].keyframe_points else ob.location[i] for i in range(3)]
            for i in range(3): w.poner("location", i, int(m["desde"]), hold[i], interp if interp in ("LINEAR", "CONSTANT") else None); w.poner("location", i, int(m["hasta"]), float(m["destino"][i]), interp)       # la interpolacion de una clave rige el tramo que SIGUE: el corte / lineal va en la clave de partida
            w.aplicar()
            nm += 1
        w.cerrar(); tocados.append(ob)
    _refrescar(context, tocados)
    return {"claves": nc, "movimientos": nm, "objetos": sorted({e["objeto"] for e in ents})}


def capturar_claves(context, objeto, canal, f0, f1, id=None, interp="smooth"):
    """entrada `claves` con las claves del canal en [f0, f1] tal como estan en la escena."""
    ob = bpy.data.objects[objeto]; idb, rutas = _bloque(ob, canal); ad = idb.animation_data
    if not (ad and ad.action): raise ValueError("%s no tiene animacion en %s" % (objeto, canal))
    fcs = {(f.data_path, f.array_index): f for f in fcurves(ad.action)}
    marcos = sorted({int(round(p.co[0])) for r in rutas for p in fcs[r].keyframe_points if f0 <= p.co[0] <= f1})
    return {"tipo": "claves", "objeto": objeto, "canal": canal, "interp": interp, "claves": [[f] + [round(fcs[r].evaluate(f), 6) for r in rutas] for f in marcos], "id": id or "cam_%s_%s" % (objeto, canal.replace(".", "_"))}


def capturar_movimiento(context, objeto, desde, hasta, id=None, interp="smooth", nota=""):
    """entrada `movimiento` cuyo destino es la ubicacion ACTUAL del objeto (se coloca la camara / el foco a mano y se captura)."""
    ob = bpy.data.objects[objeto]; loc = ob.matrix_world.to_translation() if ob.parent else ob.location
    e = {"tipo": "movimiento", "objeto": objeto, "desde": desde, "hasta": hasta, "destino": [round(c, 4) for c in loc], "interp": interp}
    if nota: e["nota"] = nota
    if id: e["id"] = id
    return e
