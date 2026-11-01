# -*- coding: utf-8 -*-
"""Importa y coloca los personajes y objetos de la escena 'bonobos' (base_tarde con las ranas.blend): bonobos adultos/bebes (clones del rig mejorado),
rata, pollo, serpiente y los objetos que se lanzan. Idempotente: si un objeto bm_* / bonobo_* ya existe, no lo vuelve a crear."""
import bpy, math
from mathutils import Vector, Matrix

PROY = r"C:\Users\user\Desktop\Alfred_Animacion"
VAN = PROY + r"\objetos\vanilla"
COL = 'bonobos_madera'

# nombre -> (tipo, posicion de la copa (x,y,z), yaw hacia Alfred)  ; Alfred queda al este (+X)
BONOBOS = {   # (tipo, casa): puntos de las copas con vista despejada a Alfred (comprobado con rayos, ver bonobos_madera_main.SPOTS)
    'bonobo_A1': ('a', (-76.5, 37.5, 21.0)),
    'bonobo_A2': ('a', (-88.5, 34.5, 21.0)),
    'bonobo_A3': ('a', (-73.5, 20.5, 18.0)),
    'bonobo_A4': ('a', (-88.5, 36.5, 23.0)),
    'bonobo_A5': ('a', (-74.5, 36.5, 18.0)),
    'bonobo_A6': ('a', (-84.5, 23.5, 18.0)),
    'bonobo_B1': ('b', (-70.5, 21.5, 18.0)),
    'bonobo_B2': ('b', (-72.5, 22.5, 18.0)),
}
CASA_A7 = (-71.5, 19.5, 20.0)
CASA_B3 = (-84.5, 36.5, 19.0)


def coleccion():
    c = bpy.data.collections.get(COL) or bpy.data.collections.new(COL)
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c


def traer(ruta, nombres=None):
    """append de objetos (link=False) sin enlazarlos a la escena; devuelve la lista de objetos nuevos"""
    antes = set(bpy.data.objects)
    with bpy.data.libraries.load(ruta, link=False) as (s, d):
        d.objects = [n for n in s.objects if (nombres is None or n in nombres)]
    return [o for o in d.objects if o]


def clonar(raiz, nuevo, col):
    objs = [raiz] + raiz.children_recursive
    mapa = {}
    for o in objs:
        n = o.copy()
        mapa[o] = n
        col.objects.link(n)
    for o, n in mapa.items():
        n.parent = mapa.get(o.parent)
        n.matrix_parent_inverse = o.matrix_parent_inverse.copy()
        for m in n.modifiers:
            if m.type == 'ARMATURE' and m.object in mapa:
                m.object = mapa[m.object]
    mapa[raiz].name = nuevo
    return mapa[raiz]


def preparar_bonobos():
    col = coleccion()
    plantillas = {}
    for tipo, f, nombre, final in (('a', PROY + r"\estructura_lista\bonobo_adulto.blend", 'bonobo_adulto_1', 'bonobo_A7'),
                                   ('b', PROY + r"\estructura_lista\bonobo_bebe.blend", 'bonobo_bebe', 'bonobo_B3')):
        r = bpy.data.objects.get(final) or bpy.data.objects.get(nombre)
        if r is None:
            objs = traer(f)
            for o in objs:
                col.objects.link(o)
            r = bpy.data.objects[nombre]
        plantillas[tipo] = r
    res = {}
    for nm, (tipo, pos) in BONOBOS.items():
        r = bpy.data.objects.get(nm)
        if r is None:
            r = clonar(plantillas[tipo], nm, col)
        r.location = pos
        r.rotation_euler = (0, 0, math.radians(-90))        # mira al este (+X), hacia Alfred
        res[nm] = r
    # las plantillas se esconden bajo tierra (el primer bonobo adulto/bebe son las plantillas)
    for t, r in plantillas.items():
        r.location = CASA_A7 if t == 'a' else CASA_B3
        r.rotation_euler = (0, 0, math.radians(-90))
        r.name = 'bonobo_A7' if t == 'a' else 'bonobo_B3'
        res[r.name] = r
    return res


def rig_de(raiz):
    return [o for o in raiz.children if o.type == 'ARMATURE'][0]


def sufijo(rig):
    for b in rig.data.bones:
        if b.name.startswith('head_'):
            return b.name[5:]
    raise KeyError('head_')


def objeto_item(nombre, carpeta, escala=1.0):
    """copia de un item de vanilla (p.ej. 'apple') con nombre bm_<nombre>_<n>; devuelve el objeto"""
    base = bpy.data.objects.get('bm_tpl_' + nombre)
    if base is None:
        objs = traer(VAN + '\\%s\\%s.blend' % (carpeta, carpeta), [nombre])
        o = objs[0]
        o.name = 'bm_tpl_' + nombre
        o.hide_render = True; o.hide_viewport = True
        coleccion().objects.link(o)
        base = o
    n = base.copy()
    n.data = base.data
    n.hide_render = False; n.hide_viewport = False
    k = 1
    while 'bm_%s_%d' % (nombre, k) in bpy.data.objects:
        k += 1
    n.name = 'bm_%s_%d' % (nombre, k)
    coleccion().objects.link(n)
    n.scale = (escala, escala, escala)
    return n
