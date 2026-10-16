# -*- coding: utf-8 -*-
"""EXPORTA las animaciones del POLLO (chicken_1) de la parte 7 (adaptado del exportador del creeper) (escena viva `base_parte_7.blend`) a archivos .py independientes en `codigos de animacion/creeper/`, uno por animacion.
Guarda, frame a frame, TODOS los canales animados (evaluando sus F-curves, sin cambiar de frame) del root `chicken_1` y de `Armature_chicken_1` (pose de sus 28 huesos).
Ejecutar en Blender con exec (rapido: no hace frame_set)."""
import bpy, os

DEST = r"C:\Users\user\Desktop\Alfred_Animacion\codigos de animacion\chicken"
R5 = lambda v: round(float(v), 5)
CREEPER = ["chicken_1", "Armature_chicken_1"] + [o.name for o in bpy.data.objects["chicken_1"].children_recursive if o.type == 'MESH']   # (el POLLO; se reusa el nombre de la lista)
MATS = []
POLLO = []
MODELOS = {"creeper": r"C:\Users\user\Desktop\Alfred_Animacion\estructura_lista\chicken_1.blend"}
ESCENAS = [
    ("salta_del_bloque_parte7", 1, 33, "salta desde el bloque al suelo (saltar_bajar)", False),
    ("camina_hasta_las_amapolas_parte7", 34, 140, "camina por su recorrido hasta las amapolas", False),
    ("picotea_dos_veces_parte7", 141, 188, "picotea el suelo dos veces junto a las amapolas", False),
    ("camina_parte7", 189, 241, "camina hasta el siguiente punto", False),
    ("picotea_tres_veces_parte7", 242, 313, "picotea el suelo tres veces", False),
    ("camina_hasta_su_ultimo_punto_parte7", 314, 410, "camina hasta su ultimo punto, junto a Alfred", False),
    ("picotea_indiferente_parte7", 411, 426, "picotea sin hacer caso a nada de lo que pasa", False),
    ("atrapado_y_lanzado_al_creeper_parte7", 427, 440, "Alfred lo agarra por el cuello (f427), cuelga de su mano, lo lanza (f437) y golpea la cara del creeper (f440)", False),
    ("rebota_y_se_estrella_contra_el_arbol_parte7", 441, 456, "rebota en la cara del creeper y vuela hasta estrellarse de espaldas contra el tronco del abedul", False),
    ("resbala_por_el_tronco_parte7", 457, 540, "pegado de espaldas al tronco, resbala hasta el suelo", False),
    ("cae_boca_abajo_y_rebota_parte7", 541, 575, "queda quieto, cae hacia delante boca abajo y rebota tres veces de la cintura para arriba", False),
    ("tumbado_inmovil_parte7", 576, 728, "queda tumbado boca abajo, inmovil, hasta el final", False),
]
def curvas(idb):
    ad = getattr(idb, "animation_data", None)
    if not ad or not ad.action: return []
    return [c for l in ad.action.layers for s in l.strips for b in s.channelbags for c in b.fcurves]

PLANTILLA = r'''# -*- coding: utf-8 -*-
"""
@@NOMBRE@@_chicken.py -- Pollo (chicken_1), parte 7, frames originales @@F0@@-@@F1@@ (@@N@@ f): @@TITULO@@.
Extraida de `base_parte_7.blend` (escena viva). Estado: sin aprobar.
Anima el root `chicken_1` y el armature `Armature_chicken_1` (28 huesos, rotacion y traslacion)@@EXTRA@@.
Uso en Blender (con el pollo en la escena; si falta se anade desde estructura_lista/chicken_1.blend):
    execute_animation()                      # frame original (@@F0@@), partiendo de donde esta el pollo AHORA
    execute_animation(start_frame=300)       # en otro frame
    execute_animation(origen='escena')       # posicion absoluta original de la parte 7
Reemplaza las acciones actuales de esos objetos.
"""
import bpy

PAYLOAD = @@PAYLOAD@@
ANIMATION_INFO = PAYLOAD['info']
FRAMES = ANIMATION_INFO['frames']
ORIGINAL_START = ANIMATION_INFO['frame_original']


def asegurar_modelos():
    """anade desde estructura_lista los modelos cuyos objetos falten"""
    for clave, (ruta, nombres) in PAYLOAD['modelos'].items():
        if all(n in bpy.data.objects for n in nombres): continue
        with bpy.data.libraries.load(ruta, link=False) as (src, dst): dst.objects = list(src.objects)
        col = bpy.data.collections.new(clave); bpy.context.scene.collection.children.link(col)
        for o in dst.objects:
            if o is not None: col.objects.link(o)
        faltan = [n for n in nombres if n not in bpy.data.objects]
        if faltan: raise ValueError('El modelo %s no trae: %s' % (ruta, ', '.join(faltan)))


def _poner(idb, d, i, v):
    """asigna el valor del canal (d, i) y dice si la propiedad es un arreglo"""
    import re
    m = re.match(r'^(.*)\["([^"]+)"\]$', d)
    if m and not d.endswith(']"]'):                                                          # propiedad personalizada: pose.bones["x"]["prop"]
        own = idb.path_resolve(m.group(1)) if m.group(1) else idb; own[m.group(2)] = v; return False
    base, _, attr = d.rpartition('.')
    own = idb.path_resolve(base) if base else idb; cur = getattr(own, attr)
    if hasattr(cur, '__len__') and not isinstance(cur, str): cur[i] = v; return True
    setattr(own, attr, bool(v) if isinstance(cur, bool) else v); return False


def _id(rec):
    return bpy.data.materials[rec['nombre']].node_tree if rec['tipo'] == 'material' else bpy.data.objects[rec['nombre']]


def execute_animation(start_frame=ORIGINAL_START, origen='actual'):
    from mathutils import Matrix, Euler, Vector
    asegurar_modelos(); sc = bpy.context.scene
    transf = {}                                                                              # roots que se re-ubican (origen='actual')
    for rn in PAYLOAD['roots']:
        ob = bpy.data.objects[rn]; can = {(d, i): v for d, i, v in PAYLOAD['ids'][rn]['canales']}
        val = lambda d, i, k: can[(d, i)][k] if (d, i) in can else getattr(ob, d)[i]
        M0 = Matrix.LocRotScale(Vector([val('location', i, 0) for i in range(3)]), Euler([val('rotation_euler', i, 0) for i in range(3)]).to_quaternion(), Vector((1, 1, 1)))
        transf[rn] = (ob.matrix_world.copy() @ M0.inverted()) if origen == 'actual' else Matrix.Identity(4)
    T = transf.get(PAYLOAD['roots'][0], Matrix.Identity(4)) if PAYLOAD['roots'] else Matrix.Identity(4)
    for key, rec in PAYLOAD['ids'].items():
        idb = _id(rec); idb.animation_data_create(); idb.animation_data.action = bpy.data.actions.new('Pollo_' + key + '_' + ANIMATION_INFO['name'])
        can = {(d, i): v for d, i, v in rec['canales']}
        if key in PAYLOAD['roots'] and origen == 'actual':                                  # ubicacion/rotacion del root relativas a su posicion actual
            prev = Euler(tuple(idb.rotation_euler))
            for k in range(FRAMES):
                g = lambda d, i: can[(d, i)][k] if (d, i) in can else getattr(idb, d)[i]
                M = T @ Matrix.LocRotScale(Vector([g('location', i) for i in range(3)]), Euler([g('rotation_euler', i) for i in range(3)]).to_quaternion(), Vector((1, 1, 1)))
                l, q, _s = M.decompose(); e = q.to_euler('XYZ', prev); prev = e
                for i in range(3): can.setdefault(('location', i), [None] * FRAMES)[k] = l[i]; can.setdefault(('rotation_euler', i), [None] * FRAMES)[k] = e[i]
        for (d, i), vals in can.items():
            for k, v in enumerate(vals):
                es_arr = _poner(idb, d, i, v)
                idb.keyframe_insert(d, index=i if es_arr else -1, frame=start_frame + k)
        for c in [c for l in idb.animation_data.action.layers for s in l.strips for b in s.channelbags for c in b.fcurves]:
            const = c.data_path.startswith('hide')
            for kp in c.keyframe_points: kp.interpolation = 'CONSTANT' if const else 'LINEAR'
    sc.render.fps = 24; sc.render.fps_base = 1
    sc.frame_start = min(sc.frame_start, int(start_frame)); sc.frame_end = max(sc.frame_end, int(start_frame + FRAMES - 1)); sc.frame_set(int(start_frame))
    return True


if __name__ == '__main__':
    execute_animation()
'''

os.makedirs(DEST, exist_ok=True)
for nombre, f0, f1, titulo, con_pollo in ESCENAS:
    fr = list(range(f0, f1 + 1)); ids = {}
    objs = CREEPER + (POLLO + [o.name for o in bpy.data.objects["chicken_1"].children_recursive if o.type == 'MESH'] if con_pollo else [])
    for n in objs:
        o = bpy.data.objects[n]; cs = curvas(o)
        if cs: ids[n] = {"tipo": "objeto", "nombre": n, "canales": [[c.data_path, c.array_index, [R5(c.evaluate(f)) for f in fr]] for c in cs]}
    for m in MATS:
        cs = curvas(bpy.data.materials[m].node_tree)
        if cs: ids["mat:" + m] = {"tipo": "material", "nombre": m, "canales": [[c.data_path, c.array_index, [R5(c.evaluate(f)) for f in fr]] for c in cs]}
    modelos = {"pollo": [MODELOS["creeper"], ["chicken_1", "Armature_chicken_1"]]}
    if con_pollo: modelos["pollo"] = [MODELOS["pollo"], ["chicken_1", "Armature_chicken_1"]]
    payload = {"info": {"name": nombre + "_chicken", "frames": len(fr), "fps": 24, "entity": "Chicken", "status": "sin aprobar", "fuente": "base_parte_7 (escena viva) f%d-%d" % (f0, f1),
                        "frame_original": f0, "descripcion": titulo, "objetos": (["chicken_1 (pollo que lo golpea)"] if con_pollo else [])},
               "roots": ["chicken_1"], "modelos": modelos, "ids": ids}
    txt = (PLANTILLA.replace("@@NOMBRE@@", nombre).replace("@@F0@@", str(f0)).replace("@@F1@@", str(f1)).replace("@@N@@", str(len(fr))).replace("@@TITULO@@", titulo)
           .replace("@@EXTRA@@", "").replace("@@PAYLOAD@@", repr(payload)))
    ruta = os.path.join(DEST, nombre + "_chicken.py"); open(ruta, "w", encoding="utf-8").write(txt)
    print("escrito", os.path.basename(ruta), "%d KB" % (os.path.getsize(ruta) // 1024), "ids:", len(ids))
print("LISTO")
