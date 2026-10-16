# -*- coding: utf-8 -*-
"""MICROFONO DE CAMARA: la camara de la escena es el microfono.
Para cada tira de sonido del VSE que pertenece a una ENTIDAD (personaje, mob, objeto):
  1. DISTANCIA: el volumen sigue la ley del inverso de la distancia (cada vez que la distancia se duplica, -6 dB),
     con la distancia REAL entre la camara (su ruta animada, frame a frame) y la cabeza de la entidad.
  2. PANEO: suena a la izquierda o a la derecha segun donde esta la entidad respecto a la camara.
  (El efecto Doppler se quito a pedido del usuario: los sonidos suenan con su audio original, sin copias procesadas.)
Flujo: (1) ANALIZAR RUTA DE LA CAMARA -> ver donde estara la camara y a que distancia queda cada entidad;
       (2) APLICAR MICROFONO -> volumen + paneo en todas las tiras con dueno;  (3) QUITAR -> todo como estaba.
Se compone con el ducking y con cualquier clave de volumen previa (las multiplica). Repetible y sin acumular.
La camara la maneja el usuario: este add-on SOLO la lee, nunca la mueve ni le pone claves."""
bl_info = {"name": "Microfono de camara (distancia y paneo)", "author": "Alfred_Animacion", "version": (1, 1, 0), "blender": (4, 2, 0),
           "location": "Editor de video (VSE) y Visor 3D > barra lateral (N) > Microfono",
           "description": "La camara es el microfono: volumen por distancia y paneo de los sonidos de cada entidad", "category": "Sequencer"}

import bpy, math, os, json, hashlib, time
from bpy.props import FloatProperty, IntProperty, BoolProperty, StringProperty, PointerProperty

ALIAS = {"pollo": "chicken_1", "chicken": "chicken_1", "creeper": "creeper_1", "cerdo": "cerdo_1", "grass_step_armature": "alfred", "cuerpo_a.002": "alfred"}
HUESOS_CABEZA = ("head", "cabeza", "face", "scull", "skull", "neck")


# ------------------------------------------------------------------ entidades
def entidades(sc):
    """raices de personajes: empties sin padre con una armadura hija (alfred, jerry, cerdo_1, creeper_1, chicken_1...)"""
    out = {}
    for o in sc.objects:
        if o.parent is None and o.type == 'EMPTY':
            arm = next((c for c in o.children_recursive if c.type == 'ARMATURE'), None)
            if arm: out[o.name] = arm
    return out


def emisor_de_tira(s, ents):
    """objeto (raiz) dueno de la tira: propiedad `mic_emisor` o por el nombre de la tira; None = sin dueno (musica, narrador...)"""
    if s.get("mic_emisor"): return s["mic_emisor"] if s["mic_emisor"] in bpy.data.objects else None
    n = s.name.lower()
    for k, v in ALIAS.items():
        if k in n and v in ents: return v
    for r in sorted(ents, key=len, reverse=True):
        base = r.lower().rstrip("_0123456789") or r.lower()
        if r.lower() in n or (len(base) >= 4 and base in n): return r
    return None


def punto_emisor(nombre, ents):
    """posicion del sonido: la cabeza de la entidad (hueso cabeza de su armadura), si no su origen + 1 m"""
    o = bpy.data.objects.get(nombre)
    if o is None: return None
    arm = ents.get(nombre)
    if arm:
        pb = next((p for p in arm.pose.bones if any(h in p.name.lower() for h in HUESOS_CABEZA)), None)
        if pb: return arm.matrix_world @ pb.head
    if o.type == 'EMPTY':                                                    # raiz sin armadura: el sonido sale un poco por encima de su origen
        from mathutils import Vector
        return o.matrix_world.translation + Vector((0, 0, 1.0))
    return o.matrix_world.translation.copy()                                 # un objeto (flecha, item...): desde el mismo objeto


def tiras_sonido(sc):
    ed = sc.sequence_editor
    return [s for s in ed.strips_all if s.type == 'SOUND'] if ed else []


# ------------------------------------------------------------------ muestreo de la camara y de las entidades
def muestrear(sc, frames, nombres, ents):
    """{f: (pos_camara, derecha_camara, {nombre: pos})} evaluando la escena frame a frame (NLA, restricciones, marcadores de camara)"""
    f0 = sc.frame_current; out = {}
    for f in frames:
        sc.frame_set(f)
        cam = sc.camera
        if cam is None: continue
        M = cam.matrix_world
        out[f] = (M.translation.copy(), (M.to_3x3() @ __import__("mathutils").Vector((1, 0, 0))).normalized(), {n: punto_emisor(n, ents) for n in nombres})
    sc.frame_set(f0)
    return out


# ------------------------------------------------------------------ curvas de volumen / paneo
def curva(sc, ruta, crear=False):
    ad = sc.animation_data
    if ad is None or ad.action is None:
        if not crear: return None
        ad = sc.animation_data_create()
        if ad.action is None: ad.action = bpy.data.actions.new("SceneAction")
    for l in ad.action.layers:
        for st in l.strips:
            for cb in st.channelbags:
                for fc in cb.fcurves:
                    if fc.data_path == ruta: return fc
    if not crear: return None
    return ad.action.fcurve_ensure_for_datablock(sc, ruta, index=0)


def quitar_curva(sc, ruta):
    ad = sc.animation_data
    if ad is None or ad.action is None: return
    for l in ad.action.layers:
        for st in l.strips:
            for cb in st.channelbags:
                for fc in [f for f in cb.fcurves if f.data_path == ruta]: cb.fcurves.remove(fc)


def claves(fc):
    return [[round(k.co.x, 3), round(k.co.y, 6)] for k in fc.keyframe_points] if fc else []


def firma(lista):
    return hashlib.md5(json.dumps(lista).encode()).hexdigest()


def evaluar(lista, f, base):
    if not lista: return base
    if f <= lista[0][0]: return lista[0][1]
    if f >= lista[-1][0]: return lista[-1][1]
    for (a, va), (b, vb) in zip(lista, lista[1:]):
        if a <= f <= b: return va + (vb - va) * (f - a) / (b - a) if b > a else vb
    return base


def poner_claves(sc, ruta, pares, interp='LINEAR'):
    quitar_curva(sc, ruta)
    fc = curva(sc, ruta, crear=True); kp = fc.keyframe_points; kp.add(len(pares))
    co = []
    for f, v in pares: co += [float(f), float(v)]
    kp.foreach_set("co", co)
    for k in kp: k.interpolation = interp
    fc.update(); return fc


# ------------------------------------------------------------------ estado original de cada tira (para repetir sin acumular)
def original(sc, s):
    """estado ANTES del microfono: si nadie toco la tira desde la ultima aplicacion se usa lo guardado; si cambio (p.ej. se rehizo el ducking), lo actual"""
    rv = 'sequence_editor.strips_all["%s"].volume' % s.name; rp = 'sequence_editor.strips_all["%s"].pan' % s.name
    vol_now = claves(curva(sc, rv)); pan_now = claves(curva(sc, rp))
    if s.get("mic_firma") and s["mic_firma"] == firma([vol_now, pan_now]):        # (solo las claves: el valor suelto lo recalcula Blender desde ellas)
        return json.loads(s["mic_original"])
    o = {"vol_claves": vol_now, "vol": float(s.volume), "pan_claves": pan_now, "pan": float(s.pan),
         "sonido": s.sound.filepath if s.sound else "", "mono": bool(s.sound.use_mono) if s.sound else False}
    if s.get("mic_sonido_original"): o["sonido"] = s["mic_sonido_original"]
    if s.get("mic_mono_original") is not None: o["mono"] = bool(s["mic_mono_original"])
    return o


def restaurar(sc, s):
    if not s.get("mic_original"): return False
    o = json.loads(s["mic_original"]); rv = 'sequence_editor.strips_all["%s"].volume' % s.name; rp = 'sequence_editor.strips_all["%s"].pan' % s.name
    quitar_curva(sc, rv); quitar_curva(sc, rp); s.volume = o["vol"]; s.pan = o["pan"]
    if o["vol_claves"]: poner_claves(sc, rv, o["vol_claves"])
    if o["pan_claves"]: poner_claves(sc, rp, o["pan_claves"])
    if s.sound and o.get("sonido") and bpy.path.abspath(s.sound.filepath) != bpy.path.abspath(o["sonido"]):
        s.sound = bpy.data.sounds.load(o["sonido"], check_existing=True)
    if s.sound and "mic_mono_original" in s.sound.keys(): s.sound.use_mono = bool(s.sound["mic_mono_original"])
    for k in ("mic_original", "mic_firma", "mic_sonido_original", "mic_mono_original", "mic_info"):
        if k in s: del s[k]
    return True


# ------------------------------------------------------------------ propiedades
class MIC_Props(bpy.types.PropertyGroup):
    dist_ref: FloatProperty(name="Distancia de referencia (m)", default=3.0, min=0.1, description="A esta distancia o menos el sonido va a su volumen normal")
    caida: FloatProperty(name="Caida", default=1.0, min=0.1, max=3.0, description="1 = fisico: -6 dB cada vez que la distancia se duplica")
    minimo: FloatProperty(name="Volumen minimo", default=0.05, min=0.0, max=1.0, description="Lo mas bajo que puede quedar un sonido lejano (0.05 = -26 dB)")
    paneo: BoolProperty(name="Paneo izquierda/derecha", default=True)
    ancho_paneo: FloatProperty(name="Ancho del paneo", default=0.8, min=0.0, max=1.0)
    paso: IntProperty(name="Muestrear cada (frames)", default=2, min=1, max=12)
    informe: StringProperty(default="")


# ------------------------------------------------------------------ operadores
class MIC_OT_analizar(bpy.types.Operator):
    bl_idname = "microfono.analizar"; bl_label = "1. Analizar ruta de la camara"
    bl_description = "Recorre la escena para ver donde estara la camara (el microfono) y a que distancia queda cada entidad con sonidos. Dibuja la ruta de la camara"

    def execute(self, context):
        sc = context.scene; p = sc.microfono
        if sc.camera is None: self.report({'ERROR'}, "La escena no tiene camara activa"); return {'CANCELLED'}
        ents = entidades(sc); T = tiras_sonido(sc)
        duenos = {}
        for s in T:
            e = emisor_de_tira(s, ents)
            duenos.setdefault(e or "(sin dueno)", []).append(s)
        con = [e for e in duenos if e != "(sin dueno)"]
        frames = list(range(sc.frame_start, sc.frame_end + 1, max(p.paso * 2, 1)))
        M = muestrear(sc, frames, con, ents)
        cams = [M[f][0] for f in frames if f in M]
        mueve = max(((a - cams[0]).length for a in cams), default=0.0)
        L = ["Camara '%s': %s (se desplaza hasta %.1f m)" % (sc.camera.name, "SE MUEVE" if mueve > 0.05 else "quieta", mueve)]
        for e in con:
            ds = [(M[f][2][e] - M[f][0]).length for f in frames if f in M and M[f][2].get(e) is not None]
            if ds:
                g = lambda d: max(p.minimo, min(1.0, (p.dist_ref / max(d, 1e-3)) ** p.caida))
                L.append("%s: %d tiras; distancia %.1f-%.1f m -> %.0f a %.0f dB" % (e, len(duenos[e]), min(ds), max(ds), 20 * math.log10(g(max(ds))), 20 * math.log10(g(min(ds)))))
        if "(sin dueno)" in duenos: L.append("Sin dueno (no se tocan): %d tiras (%s...)" % (len(duenos["(sin dueno)"]), ", ".join(s.name for s in duenos["(sin dueno)"][:3])))
        # ruta de la camara como curva (solo para verla; no se renderiza)
        cu = bpy.data.curves.get("ruta_camara_microfono") or bpy.data.curves.new("ruta_camara_microfono", 'CURVE')
        cu.splines.clear(); sp = cu.splines.new('POLY'); sp.points.add(len(cams) - 1)
        for i, c in enumerate(cams): sp.points[i].co = (c.x, c.y, c.z, 1.0)
        cu.dimensions = '3D'; cu.bevel_depth = 0.0                      # linea fina: un tubo tapaba la vista de la camara
        ob = bpy.data.objects.get("ruta_camara_microfono") or bpy.data.objects.new("ruta_camara_microfono", cu)
        if ob.name not in sc.collection.objects: sc.collection.objects.link(ob)
        ob.hide_render = True; ob.hide_select = True; ob.visible_camera = False; ob.display_type = 'WIRE'
        p.informe = "\n".join(L); self.report({'INFO'}, L[0]); print("[Microfono]\n" + p.informe)
        return {'FINISHED'}


class MIC_OT_aplicar(bpy.types.Operator):
    bl_idname = "microfono.aplicar"; bl_label = "2. Aplicar microfono"
    bl_description = "Volumen por distancia a la camara y paneo en todas las tiras de sonido con dueno (repetible)"

    def execute(self, context):
        t0 = time.time(); sc = context.scene; p = sc.microfono; fps = sc.render.fps / sc.render.fps_base
        if sc.camera is None: self.report({'ERROR'}, "La escena no tiene camara activa"); return {'CANCELLED'}
        ents = entidades(sc); T = [(s, emisor_de_tira(s, ents)) for s in tiras_sonido(sc)]; T = [(s, e) for s, e in T if e]
        if not T: self.report({'WARNING'}, "Ninguna tira tiene dueno"); return {'CANCELLED'}
        frames = set()
        for s, e in T:
            a, b = int(s.frame_final_start), int(s.frame_final_end)
            frames.update(range(a, b + 1, p.paso)); frames.update((a, b))
        M = muestrear(sc, sorted(frames), sorted({e for s, e in T}), ents)
        for s, e in T:                                                                   # mono original de cada SONIDO (varias tiras pueden compartir el mismo archivo)
            if s.sound and "mic_mono_original" not in s.sound.keys(): s.sound["mic_mono_original"] = bool(s.sound.use_mono)
        res = []
        for s, e in T:
            o = original(sc, s)
            a, b = int(s.frame_final_start), int(s.frame_final_end)
            fr = sorted(f for f in frames if a <= f <= b and f in M and M[f][2].get(e) is not None)
            if not fr: continue
            d = {f: (M[f][2][e] - M[f][0]).length for f in fr}
            gan = {f: max(p.minimo, min(1.0, (p.dist_ref / max(d[f], 1e-3)) ** p.caida)) for f in fr}
            rv = 'sequence_editor.strips_all["%s"].volume' % s.name; rp = 'sequence_editor.strips_all["%s"].pan' % s.name
            poner_claves(sc, rv, [(f, evaluar(o["vol_claves"], f, o["vol"]) * gan[f]) for f in fr])
            if p.paneo and s.sound:
                s.sound.use_mono = True                                                  # el paneo del VSE solo actua sobre sonido mono
                pan = {f: max(-1.0, min(1.0, (M[f][2][e] - M[f][0]).normalized().dot(M[f][1]) * p.ancho_paneo)) for f in fr}
                poner_claves(sc, rp, [(f, evaluar(o["pan_claves"], f, o["pan"]) + pan[f]) for f in fr])
            info = {"emisor": e, "d_min": round(min(d.values()), 2), "d_max": round(max(d.values()), 2), "db_min": round(20 * math.log10(min(gan.values())), 1)}
            if s.sound and o.get("sonido") and bpy.path.abspath(s.sound.filepath) != bpy.path.abspath(o["sonido"]):
                mono = s.sound.use_mono                                                  # si tenia una copia procesada (Doppler de antes): vuelve al audio ORIGINAL
                s.sound = bpy.data.sounds.load(o["sonido"], check_existing=True); s.sound.use_mono = mono
            if "mic_sonido_original" in s: del s["mic_sonido_original"]
            s["mic_mono_original"] = o.get("mono", False)
            s["mic_original"] = json.dumps(o)
            s["mic_firma"] = firma([claves(curva(sc, rv)), claves(curva(sc, rp))])
            s["mic_info"] = json.dumps(info); res.append((s.name, info))
        p.informe = "Microfono aplicado a %d tiras en %.0f s" % (len(res), time.time() - t0)
        self.report({'INFO'}, p.informe); print("[Microfono] " + p.informe)
        for n, i in res[:40]: print("   %-36s %s" % (n, i))
        return {'FINISHED'}


class MIC_OT_quitar(bpy.types.Operator):
    bl_idname = "microfono.quitar"; bl_label = "Quitar microfono"; bl_description = "Deja todas las tiras como estaban antes de aplicar el microfono"

    def execute(self, context):
        n = sum(1 for s in tiras_sonido(context.scene) if restaurar(context.scene, s))
        context.scene.microfono.informe = "Microfono quitado de %d tiras" % n; self.report({'INFO'}, context.scene.microfono.informe); return {'FINISHED'}


class MIC_OT_asignar(bpy.types.Operator):
    bl_idname = "microfono.asignar"; bl_label = "Dueno = objeto activo"; bl_description = "Las tiras seleccionadas suenan desde el objeto activo (su raiz)"

    def execute(self, context):
        o = context.active_object
        if o is None: self.report({'ERROR'}, "No hay objeto activo"); return {'CANCELLED'}
        while o.parent: o = o.parent
        ed = context.scene.sequence_editor; n = 0
        for s in (ed.strips_all if ed else []):
            if s.select and s.type == 'SOUND': s["mic_emisor"] = o.name; n += 1
        self.report({'INFO'}, "%d tiras suenan desde %s" % (n, o.name)); return {'FINISHED'}


def dibujar(self, context):
    L = self.layout; p = context.scene.microfono
    cam = context.scene.camera
    L.label(text="Microfono: %s" % (cam.name if cam else "SIN CAMARA"), icon='OUTLINER_OB_CAMERA' if cam else 'ERROR')
    L.operator("microfono.analizar", icon='CON_FOLLOWPATH')
    col = L.column(align=True)
    for k in ("dist_ref", "caida", "minimo", "paso"): col.prop(p, k)
    row = L.row(align=True); row.prop(p, "paneo"); r2 = row.row(); r2.active = p.paneo; r2.prop(p, "ancho_paneo", text="Ancho")
    L.operator("microfono.aplicar", icon='SPEAKER')
    row = L.row(align=True); row.operator("microfono.quitar", icon='LOOP_BACK'); row.operator("microfono.asignar", icon='OBJECT_DATA')
    if p.informe:
        box = L.box()
        for l in p.informe.splitlines()[:12]: box.label(text=l[:90])


class MIC_PT_vse(bpy.types.Panel):
    bl_label = "Microfono de camara"; bl_space_type = 'SEQUENCE_EDITOR'; bl_region_type = 'UI'; bl_category = "Microfono"
    draw = dibujar


class MIC_PT_3d(bpy.types.Panel):
    bl_label = "Microfono de camara"; bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = "Microfono"
    draw = dibujar


CLASES = (MIC_Props, MIC_OT_analizar, MIC_OT_aplicar, MIC_OT_quitar, MIC_OT_asignar, MIC_PT_vse, MIC_PT_3d)


def register():
    for c in CLASES:
        try: bpy.utils.unregister_class(getattr(bpy.types, c.__name__))
        except Exception: pass
        bpy.utils.register_class(c)
    bpy.types.Scene.microfono = PointerProperty(type=MIC_Props)


def unregister():
    for c in reversed(CLASES):
        try: bpy.utils.unregister_class(c)
        except Exception: pass
    if hasattr(bpy.types.Scene, "microfono"): del bpy.types.Scene.microfono
