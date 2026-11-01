# -*- coding: utf-8 -*-
"""
preparar_escena.py -- Alfred Animation Studio: crea en la escena los OBJETOS que el guion necesita y que el generador (`sentarse_en_refugio.py`) creaba a mano (fase 6 del plan).

Para una escena limpia (`base_parte_3.blend`): importa la pala de piedra, el item de tierra, el item de tablon, y prepara el pozo (la tapa de pasto sacada del suelo + la caja abierta de tierra). Todo es IDEMPOTENTE:
si el objeto ya existe no se toca. Lee del guion:
  objetos[*]   {nombre, blend (relativo a la raiz del proyecto), fuente_objeto}          -> objeto importado a la coleccion `objetos_mano` (sin padre)
  mundo[*]     crear_pozo     {tapa, objeto (pozo), celda: [x, y, z_superior], suelo: "a.001", tierra: {fuente_blend, fuente_objeto, nombre}}
               aparecer_item  {objeto, copia_de | fuente_blend + fuente_objeto}     -> el item (copia de un bloque de la escena, o importado de un .blend)
"""
import os

import bpy

try:
    from . import guion_v2 as gv
except Exception:
    import importlib.util as _ilu
    _sp = _ilu.spec_from_file_location("guion_v2", os.path.join(os.path.dirname(os.path.abspath(__file__)), "guion_v2.py")); gv = _ilu.module_from_spec(_sp); _sp.loader.exec_module(gv)

RAIZ = os.environ.get("ALFRED_RAIZ", r"C:\Users\user\Desktop\Alfred_Animacion")


def coleccion(sc, nombre):
    c = bpy.data.collections.get(nombre) or bpy.data.collections.new(nombre)
    if c.name not in sc.collection.children: sc.collection.children.link(c)
    return c


def _a_coleccion(ob, col):
    for c in list(ob.users_collection): c.objects.unlink(ob)
    col.objects.link(ob)


def _importar(blend, nombre, extra=None):
    ruta = blend if os.path.isabs(blend) else os.path.join(RAIZ, blend)
    if not os.path.isfile(ruta): raise FileNotFoundError(ruta)
    with bpy.data.libraries.load(ruta, link=False) as (src, dst):
        if nombre not in src.objects: raise KeyError("%s no tiene el objeto %r (tiene %s)" % (os.path.basename(ruta), nombre, list(src.objects)[:6]))
        dst.objects = [nombre] + [e for e in extra or [] if e in src.objects]
    return dst.objects[0]


def _tapa_y_pozo(sc, col, m, tierra):
    import bmesh
    cx, cy, cz = m["celda"]; r = {}
    if bpy.data.objects.get(m["tapa"]) is None:                                          # se saca del suelo el unico quad de la cara superior de la casilla (su copia exacta queda en la tapa)
        suelo = bpy.data.objects[m.get("suelo", "a.001")]; bm = bmesh.new(); bm.from_mesh(suelo.data); mw = suelo.matrix_world; uvl = bm.loops.layers.uv.active
        fc = [f for f in bm.faces if len(f.verts) == 4 and abs((mw @ f.calc_center_median()).x - cx) < 0.01 and abs((mw @ f.calc_center_median()).y - cy) < 0.01 and abs((mw @ f.calc_center_median()).z - cz) < 0.01]
        if not fc: bm.free(); raise ValueError("no hay un quad de %s en la casilla (%s, %s, %s)" % (suelo.name, cx, cy, cz))
        fc = fc[0]; me = bpy.data.meshes.new(m["tapa"]); vs = [mw @ v.co for v in fc.verts]; uv = [l[uvl].uv.copy() for l in fc.loops] if uvl else None
        me.from_pydata([tuple(v) for v in vs], [], [(0, 1, 2, 3)]); me.update(); mi = fc.material_index
        for mat in suelo.data.materials: me.materials.append(mat)
        me.polygons[0].material_index = mi
        if uv:
            uvm = me.uv_layers.new(name="UVMap")
            for i, l in enumerate(me.loops): uvm.data[l.index].uv = uv[i]
        tapa = bpy.data.objects.new(m["tapa"], me); tapa["quad_original_de_%s" % suelo.name.replace(".", "")] = "eliminado de %s (casilla x %s, y %s, cara superior z %s)" % (suelo.name, cx, cy, cz)
        bmesh.ops.delete(bm, geom=[fc], context='FACES'); bm.to_mesh(suelo.data); suelo.data.update(); bm.free(); r["tapa"] = "creada"
    else: tapa = bpy.data.objects[m["tapa"]]
    _a_coleccion(tapa, col)
    if bpy.data.objects.get(m["objeto"]) is None:                                         # el pozo: la caja de tierra abierta por arriba
        me = tierra.data.copy(); me.name = m["objeto"]; bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().z > 0.99], context='FACES'); bm.to_mesh(me); bm.free()
        pozo = bpy.data.objects.new(m["objeto"], me); r["pozo"] = "creado"
    else: pozo = bpy.data.objects[m["objeto"]]
    _a_coleccion(pozo, col); pozo.location = (cx, cy, cz - m.get("profundidad", 1.0)); pozo.rotation_euler = (0, 0, 0); pozo.scale = (1.0, 1.0, 1.0)
    return r


def preparar(context, guion):
    """crea lo que falte. -> {nombre: 'creado' | 'importado' | 'copiado' | 'ya existia'}"""
    sc = context.scene; d = gv.migrar(guion); res = {}; col_mano = coleccion(sc, "objetos_mano"); col_cavar = coleccion(sc, "cavar")
    for o in d.get("objetos") or []:                                                      # herramientas / objetos que vienen de un .blend (la pala); los que ya estan en la escena (hachas) no se tocan
        n = o["nombre"]
        ob0 = bpy.data.objects.get(n)
        if ob0 is not None:
            if o.get("espalda") and ob0.parent is not None:                                  # las herramientas de la espalda se animan sueltas: se desparentan sin moverlas
                mw = ob0.matrix_world.copy(); ob0.parent = None; ob0.matrix_world = mw; ob0.rotation_mode = 'QUATERNION'; res[n] = "desparentado"
            else: res[n] = "ya existia"
            continue
        col = coleccion(sc, o["coleccion"]) if o.get("coleccion") else col_mano
        if o.get("copia_de"):                                                              # copia de otro objeto (comparte malla): sticks, tablones, slabs
            ob = bpy.data.objects[o["copia_de"]].copy(); ob.name = n; _a_coleccion(ob, col); ob.parent = None; ob.rotation_mode = 'QUATERNION'; res[n] = "copiado"; continue
        if o.get("copia_jerarquia_de"):                                                    # antorcha 2: vacio + malla + llama + humo + luz (la luz con datos propios)
            raiz = bpy.data.objects[o["copia_jerarquia_de"]]; objs = [raiz] + list(raiz.children_recursive); mp = {}
            for x in objs:
                c = x.copy()
                if x.type == 'LIGHT': c.data = x.data.copy()
                c.name = n if x is raiz else x.name + "_a2"; mp[x] = c; col.objects.link(c)
            for x in objs:
                if x.parent: mp[x].parent = mp[x.parent]; mp[x].matrix_parent_inverse = x.matrix_parent_inverse.copy()
            mp[raiz].rotation_mode = 'QUATERNION'; res[n] = "copiado (jerarquia)"; continue
        if not o.get("blend"): raise KeyError("el objeto %r no esta en la escena y el guion no dice de que .blend importarlo (`blend`)" % n)
        ob = _importar(o["blend"], o.get("fuente_objeto", n), o.get("fuente_extra")); ob.name = n; ob.parent = None
        for x in [ob] + [bpy.data.objects[e] for e in o.get("fuente_extra") or [] if e in bpy.data.objects]: _a_coleccion(x, col)
        ob.rotation_mode = 'QUATERNION'; res[n] = "importado"
    mundo = d.get("mundo") or []
    for m in mundo:
        if m.get("accion") != "aparecer_item": continue
        n = m["objeto"]
        if bpy.data.objects.get(n) is not None: res[n] = "ya existia"; continue
        if m.get("copia_de"):
            src = bpy.data.objects[m["copia_de"]]; ob = src.copy(); ob.name = n; col_mano.objects.link(ob); res[n] = "copiado"
        elif m.get("fuente_blend"):
            ob = _importar(m["fuente_blend"], m.get("fuente_objeto", n)); ob.name = n; _a_coleccion(ob, col_cavar); res[n] = "importado"
        else: raise KeyError("el item %r no tiene `copia_de` ni `fuente_blend`" % n)
        ob.parent = None; ob.rotation_mode = 'XYZ'
    for m in mundo:
        if m.get("accion") != "crear_pozo": continue
        it = next((x for x in mundo if x.get("accion") == "aparecer_item" and x.get("fuente_blend") and x.get("pozo_de") == m["objeto"]), None) or next((x for x in mundo if x.get("accion") == "aparecer_item" and x.get("fuente_blend")), None)
        if it is None: raise KeyError("crear_pozo necesita un item de tierra con `fuente_blend` (la caja de tierra de la que sale el pozo)")
        for k, v in _tapa_y_pozo(sc, col_cavar, m, bpy.data.objects[it["objeto"]]).items(): res[m["tapa"] if k == "tapa" else m["objeto"]] = v
    return res
