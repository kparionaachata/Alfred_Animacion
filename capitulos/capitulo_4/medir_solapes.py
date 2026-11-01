# -*- coding: utf-8 -*-
"""Mide cuanto se hunde la criatura en la caverna: para cada frame pedido evalua las mallas del personaje (muestra de vertices) y las articulaciones y cuenta los puntos
DENTRO del solido de la caverna (BVH de caverna_*, normales hacia el aire): prof = max profundidad. Uso: exec(ruta_stalker_pico.py); exec(este); medir([frames])"""
import bpy
from mathutils import Vector

MALLAS = ("Mesh_0_1", "Mesh_1", "Mesh_2_1", "Mesh_3_1", "stalker_fx_boca", "stalker_fx_rojos_pecho")


def _dentro(bvh, p):
    r = bvh.find_nearest(p)
    if r[0] is None:
        return 0.0
    v = p - r[0]
    return max(0.0, -v.dot(r[1])) if v.length < 3 else 0.0


def medir(frames, paso=6, detalle=False):
    sc = bpy.context.scene
    O = bpy.data.objects
    dg0 = bpy.context.evaluated_depsgraph_get()
    cav = bpy.app.driver_namespace["ruta_bvh"][0]
    out = {}
    for fr in frames:
        sc.frame_set(fr)
        dg = bpy.context.evaluated_depsgraph_get()
        n = tot = 0
        prof = 0.0
        quien = {}
        for nm in MALLAS:
            o = O[nm]
            e = o.evaluated_get(dg)
            m = e.to_mesh()
            W = o.matrix_world
            vg = {g.index: g.name for g in o.vertex_groups}
            for v in [m.vertices[i] for i in range(0, len(m.vertices), paso)]:
                tot += 1
                d = _dentro(cav, W @ v.co)
                if d > 0.03:
                    n += 1
                    prof = max(prof, d)
                    if detalle and o.data.vertices[v.index].groups:
                        g = max(o.data.vertices[v.index].groups, key=lambda g: g.weight)
                        quien[vg.get(g.group)] = quien.get(vg.get(g.group), 0) + 1
            e.to_mesh_clear()
        out[fr] = (n, tot, round(prof, 2), sorted(quien.items(), key=lambda x: -x[1])[:5] if detalle else None)
    return out
