# -*- coding: utf-8 -*-
"""ESPECTADORES POR GRUPOS: activa / desactiva la presencia de cada grupo de espectadores del ring
(ribbits, guardianes ribbit, cerdos, vacas, pollos) para reproducir y analizar cada grupo por separado.
- Ocultar un grupo apaga sus objetos en el visor (y opcionalmente en el render): no se evaluan, la reproduccion va mas fluida.
- Cada personaje se lleva su slab (slab_<nombre>) y todas sus mallas hijas.
- El estado original de cada objeto se guarda al ocultarlo y se restaura al mostrarlo (las mallas auxiliares que ya
  estaban ocultas siguen ocultas).
- Los luchadores (guard_ribbit_1 y alfred) nunca se tocan. No mueve nada ni pone claves: solo visibilidad."""
bl_info = {"name": "Espectadores por grupos (ring)", "author": "Alfred_Animacion", "version": (1, 0, 0), "blender": (4, 2, 0),
           "location": "Visor 3D > barra lateral (N) > Espectadores",
           "description": "Mostrar / ocultar ribbits, guardianes, cerdos, vacas y pollos del ring por separado", "category": "Animation"}

import bpy, re
from bpy.props import BoolProperty, EnumProperty

COLECCION = "espectadores_ring"
VALLA = "valla_ring_lucha"
LUCHADORES = {"guard_ribbit_1", "alfred"}
MARGEN = 3.0                                              # un guardian a menos de esto de la valla cuenta como espectador
CLAVE = "_esp_grupo_prev"                                 # (hide_viewport, hide_render) antes de ocultarlo

GRUPOS = [  # (id, etiqueta, icono, patron del nombre de la raiz)
    ("ribbits", "Ribbits", 'OUTLINER_OB_ARMATURE', re.compile(r"^ribbit_\w+_ring$")),
    ("guardianes", "Guardianes ribbit", 'MOD_ARMATURE', re.compile(r"^guard_ribbit_\d+$")),
    ("cerdos", "Cerdos", 'MONKEY', re.compile(r"^cerdo\d*_ring$")),
    ("vacas", "Vacas", 'MONKEY', re.compile(r"^vaca\d*_ring$")),
    ("pollos", "Pollos", 'MONKEY', re.compile(r"^pollo\d*_ring$")),
]


# ------------------------------------------------------------------ quien es de cada grupo
def _cerca_del_ring(o):
    v = bpy.data.objects.get(VALLA)
    if v is None: return True
    from mathutils import Vector
    bb = [v.matrix_world @ Vector(c) for c in v.bound_box]; p = o.matrix_world.translation
    return (min(q.x for q in bb) - MARGEN <= p.x <= max(q.x for q in bb) + MARGEN and
            min(q.y for q in bb) - MARGEN <= p.y <= max(q.y for q in bb) + MARGEN)


def raices(sc, gid):
    patron = next(g[3] for g in GRUPOS if g[0] == gid); col = bpy.data.collections.get(COLECCION); out = []
    for o in sc.objects:
        if o.parent is not None or o.name in LUCHADORES or not patron.match(o.name): continue
        if (col and col in o.users_collection) or _cerca_del_ring(o): out.append(o)
    return out


def objetos(sc, gid):
    """raices del grupo + todos sus hijos + su slab"""
    out = []
    for r in raices(sc, gid):
        out += [r] + list(r.children_recursive)
        sl = bpy.data.objects.get("slab_" + r.name)
        if sl: out += [sl] + list(sl.children_recursive)
    return out


# ------------------------------------------------------------------ mostrar / ocultar
def poner(sc, gid, visible):
    render = sc.esp_grupos_render
    for o in objetos(sc, gid):
        if not visible:
            if CLAVE not in o: o[CLAVE] = [int(o.hide_viewport), int(o.hide_render)]
            o.hide_viewport = True
            if render: o.hide_render = True
        elif CLAVE in o:
            hv, hr = o[CLAVE]; o.hide_viewport = bool(hv); o.hide_render = bool(hr); del o[CLAVE]


# ------------------------------------------------------------------ personajes principales (los luchadores)
PRINCIPALES = [("alfred", "Alfred"), ("guard_ribbit_1", "Contrincante (guard_ribbit_1)")]


def objs_de(nombre):
    r = bpy.data.objects.get(nombre)
    return [r] + list(r.children_recursive) if r else []


def poner_objs(sc, objs, visible):
    render = sc.esp_grupos_render
    for o in objs:
        if not visible:
            if CLAVE not in o: o[CLAVE] = [int(o.hide_viewport), int(o.hide_render)]
            o.hide_viewport = True
            if render: o.hide_render = True
        elif CLAVE in o:
            hv, hr = o[CLAVE]; o.hide_viewport = bool(hv); o.hide_render = bool(hr); del o[CLAVE]
        elif o.hide_viewport and CLAVE_FOCO in o:
            o.hide_viewport = False                                   # oculto por el foco: se pide verlo, se muestra


def principal_visible(nombre):
    r = bpy.data.objects.get(nombre)
    return bool(r) and not r.hide_viewport


def _prop_principal(nombre):
    def get(self): return principal_visible(nombre)
    def set(self, v): poner_objs(self, objs_de(nombre), v)
    return BoolProperty(name=nombre, description="Mostrar / ocultar este personaje principal", get=get, set=set)


class ESP_OT_principales(bpy.types.Operator):
    bl_idname = "espectadores.principales"; bl_label = "Principales"; bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Muestra u oculta a los dos personajes principales (Alfred y el contrincante)"
    visible: BoolProperty(default=False)

    def execute(self, ctx):
        for n, _e in PRINCIPALES: poner_objs(ctx.scene, objs_de(n), self.visible)
        return {'FINISHED'}


class ESP_PT_principales(bpy.types.Panel):
    bl_label = "Personajes principales"; bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = "Espectadores"

    def draw(self, ctx):
        sc = ctx.scene; L = self.layout
        for n, etiqueta in PRINCIPALES:
            fila = L.row(); fila.enabled = n in bpy.data.objects; vis = principal_visible(n)
            fila.prop(sc, "esp_pp_" + n, text=etiqueta, icon='HIDE_OFF' if vis else 'HIDE_ON', toggle=True)
        fila = L.row(align=True)
        fila.operator("espectadores.principales", text="Mostrar ambos", icon='HIDE_OFF').visible = True
        fila.operator("espectadores.principales", text="Ocultar ambos", icon='HIDE_ON').visible = False


# ------------------------------------------------------------------ cuadrilatero (coleccion ring_lucha: valla + antorcha del centro)
COL_RING = "ring_lucha"


def objs_ring():
    c = bpy.data.collections.get(COL_RING)
    return list(c.all_objects) if c else []


def ring_visible():
    return any(not o.hide_viewport for o in objs_ring() if o.type == 'MESH')


def _prop_ring():
    def get(self): return ring_visible()
    def set(self, v): poner_objs(self, objs_ring(), v)
    return BoolProperty(name="Cuadrilatero", description="Mostrar / ocultar el cuadrilatero (valla y antorcha del centro)", get=get, set=set)


class ESP_PT_ring(bpy.types.Panel):
    bl_label = "Cuadrilatero"; bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = "Espectadores"

    def draw(self, ctx):
        fila = self.layout.row(); fila.enabled = bool(objs_ring()); vis = ring_visible()
        fila.prop(ctx.scene, "esp_ring", text="Cuadrilatero (valla y antorcha)", icon='HIDE_OFF' if vis else 'HIDE_ON', toggle=True)


def es_visible(sc, gid):
    rs = raices(sc, gid)
    return any(not r.hide_viewport for r in rs) if rs else True


def _prop(gid):
    def get(self): return es_visible(self, gid)
    def set(self, v): poner(self, gid, v)
    return BoolProperty(name=gid, description="Mostrar / ocultar este grupo de espectadores", get=get, set=set)


class ESP_OT_solo(bpy.types.Operator):
    bl_idname = "espectadores.solo"; bl_label = "Solo"; bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Deja visible solo este grupo de espectadores (los demas se ocultan)"
    grupo: EnumProperty(items=[(g[0], g[1], "") for g in GRUPOS])

    def execute(self, ctx):
        for g in GRUPOS: poner(ctx.scene, g[0], g[0] == self.grupo)
        return {'FINISHED'}


class ESP_OT_todos(bpy.types.Operator):
    bl_idname = "espectadores.todos"; bl_label = "Todos"; bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Muestra u oculta todos los grupos de espectadores"
    visible: BoolProperty(default=True)

    def execute(self, ctx):
        for g in GRUPOS: poner(ctx.scene, g[0], self.visible)
        return {'FINISHED'}


class ESP_OT_seleccionar(bpy.types.Operator):
    bl_idname = "espectadores.seleccionar"; bl_label = "Seleccionar"; bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Selecciona las raices de este grupo (para verlas en el outliner o encuadrarlas)"
    grupo: EnumProperty(items=[(g[0], g[1], "") for g in GRUPOS])

    def execute(self, ctx):
        for o in ctx.view_layer.objects: o.select_set(False)
        rs = [r for r in raices(ctx.scene, self.grupo) if r.visible_get()]
        for r in rs: r.select_set(True)
        if rs: ctx.view_layer.objects.active = rs[0]
        self.report({'INFO'}, "%d seleccionados" % len(rs))
        return {'FINISHED'}


class ESP_PT_panel(bpy.types.Panel):
    bl_label = "Espectadores del ring"; bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = "Espectadores"

    def draw(self, ctx):
        sc = ctx.scene; L = self.layout
        for gid, etiqueta, icono, _p in GRUPOS:
            n = len(raices(sc, gid)); vis = es_visible(sc, gid)
            fila = L.row(align=True); fila.enabled = n > 0
            fila.prop(sc, "esp_" + gid, text="%s (%d)" % (etiqueta, n), icon='HIDE_OFF' if vis else 'HIDE_ON', toggle=True)
            fila.operator("espectadores.solo", text="", icon='SOLO_ON').grupo = gid
            fila.operator("espectadores.seleccionar", text="", icon='RESTRICT_SELECT_OFF').grupo = gid
        fila = L.row(align=True)
        fila.operator("espectadores.todos", text="Mostrar todos", icon='HIDE_OFF').visible = True
        fila.operator("espectadores.todos", text="Ocultar todos", icon='HIDE_ON').visible = False
        L.prop(sc, "esp_grupos_render")


# ------------------------------------------------------------------ FOCO: ocultar todo menos un personaje (para no cargar la CPU)
CLAVE_FOCO = "_foco_prev"


def foco_activo(sc): return any(CLAVE_FOCO in o for o in sc.objects)


def poner_foco(sc, raiz_nombre):
    raiz = bpy.data.objects.get(raiz_nombre)
    if raiz is None: return 0
    deja = {raiz} | set(raiz.children_recursive); n = 0
    for o in sc.objects:
        if o in deja or o.type in {'CAMERA', 'LIGHT'} or CLAVE_FOCO in o: continue      # camara y luces no se tocan
        o[CLAVE_FOCO] = int(o.hide_viewport); o.hide_viewport = True; n += 1
    return n


def quitar_foco(sc):
    n = 0
    for o in sc.objects:
        if CLAVE_FOCO in o:
            if CLAVE not in o: o.hide_viewport = bool(o[CLAVE_FOCO])      # lo que se oculto aparte (grupos/principales) sigue oculto
            del o[CLAVE_FOCO]; n += 1
    return n


class ESP_OT_foco(bpy.types.Operator):
    bl_idname = "espectadores.foco"; bl_label = "Foco"; bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Oculta en el visor todo menos el personaje elegido (no se evalua: la CPU queda libre). Otra vez = restaurar"
    raiz: bpy.props.StringProperty(default="alfred")

    def execute(self, ctx):
        if foco_activo(ctx.scene): self.report({'INFO'}, "Restaurados %d objetos" % quitar_foco(ctx.scene))
        else: self.report({'INFO'}, "Ocultos %d objetos" % poner_foco(ctx.scene, self.raiz))
        return {'FINISHED'}


RIVAL = "guard_ribbit_1"


def objs_rival():
    r = bpy.data.objects.get(RIVAL)
    return [r] + list(r.children_recursive) if r else []


def rival_visible(): return any(not o.hide_viewport for o in objs_rival())


class ESP_OT_foco_rival(bpy.types.Operator):
    bl_idname = "espectadores.foco_rival"; bl_label = "Contrincante"; bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Con el foco activo: muestra u oculta al contrincante (guard_ribbit_1) junto a Alfred"

    def execute(self, ctx):
        mostrar = not rival_visible()
        for o in objs_rival():
            if mostrar:
                if CLAVE_FOCO not in o: o[CLAVE_FOCO] = int(o.hide_viewport)      # al quitar el foco vuelve a como estaba
                o.hide_viewport = False
            elif CLAVE_FOCO in o: o.hide_viewport = True
        self.report({'INFO'}, "Contrincante %s" % ("visible" if mostrar else "oculto"))
        return {'FINISHED'}


class ESP_PT_foco(bpy.types.Panel):
    bl_label = "Foco (solo un personaje)"; bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = "Espectadores"

    def draw(self, ctx):
        act = foco_activo(ctx.scene)
        self.layout.operator("espectadores.foco", text="Mostrar todo otra vez" if act else "Solo Alfred (ocultar el resto)",
                             icon='HIDE_OFF' if act else 'SOLO_ON', depress=act).raiz = "alfred"
        fila = self.layout.row(); fila.enabled = act and bool(objs_rival()); vis = rival_visible()
        fila.operator("espectadores.foco_rival", text="Mostrar contrincante (%s)" % RIVAL, icon='HIDE_OFF' if vis else 'HIDE_ON', depress=vis)


# ------------------------------------------------------------------ entorno (todo lo que no es publico, luchadores ni cuadrilatero)
PATRULLA = ["guard_ribbit_16", "guard_ribbit_17", "guard_ribbit_18", "guard_ribbit_19"]


def objs_patrulla():
    out = []
    for n in PATRULLA: out += objs_de(n)
    return out


def patrulla_visible():
    return any(not o.hide_viewport for o in objs_patrulla())


def _prop_patrulla():
    def get(self): return patrulla_visible()
    def set(self, v): poner_objs(self, objs_patrulla(), v)
    return BoolProperty(name="Patrulla", description="Mostrar / ocultar los guardianes que patrullan", get=get, set=set)


class ESP_PT_patrulla(bpy.types.Panel):
    bl_label = "Guardianes de patrulla"; bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = "Espectadores"

    def draw(self, ctx):
        fila = self.layout.row(); fila.enabled = bool(objs_patrulla()); vis = patrulla_visible()
        fila.prop(ctx.scene, "esp_patrulla", text="Patrulla (%d guardianes)" % sum(1 for n in PATRULLA if n in bpy.data.objects),
                  icon='HIDE_OFF' if vis else 'HIDE_ON', toggle=True)


# ------------------------------------------------------------------ Jerry (raiz `jerry` + sus hijos + el sombrero suelto)
JERRY = "jerry"; JERRY_EXTRA = ["sombrero_jerry_libre"]


def objs_jerry():
    return objs_de(JERRY) + [bpy.data.objects[n] for n in JERRY_EXTRA if n in bpy.data.objects]


def jerry_visible():
    r = bpy.data.objects.get(JERRY)
    return bool(r) and not r.hide_viewport


def _mutear_visibilidad(objs, mute):
    """el sombrero tiene claves de visibilidad: mientras Jerry esta oculto se silencian para que no lo vuelvan a mostrar"""
    for o in objs:
        ad = o.animation_data
        if not (ad and ad.action): continue
        for capa in ad.action.layers:
            for tira in capa.strips:
                for cb in tira.channelbags:
                    for fc in cb.fcurves:
                        if fc.data_path in ("hide_viewport", "hide_render"): fc.mute = mute


def poner_jerry(sc, visible):
    objs = objs_jerry()
    if visible:
        poner_objs(sc, objs, True); _mutear_visibilidad(objs, False)
    else:
        _mutear_visibilidad(objs, True); poner_objs(sc, objs, False)


def _prop_jerry():
    def get(self): return jerry_visible()
    def set(self, v): poner_jerry(self, v)
    return BoolProperty(name="Jerry", description="Mostrar / ocultar a Jerry (con su sombrero)", get=get, set=set)


class ESP_PT_jerry(bpy.types.Panel):
    bl_label = "Jerry"; bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = "Espectadores"

    def draw(self, ctx):
        fila = self.layout.row(); fila.enabled = JERRY in bpy.data.objects; vis = jerry_visible()
        fila.prop(ctx.scene, "esp_jerry", text="Jerry", icon='HIDE_OFF' if vis else 'HIDE_ON', toggle=True)


def objs_entorno(sc):
    fuera = set(objs_ring()) | set(objs_patrulla()) | set(objs_jerry())          # Jerry no es entorno
    for g in GRUPOS: fuera.update(objetos(sc, g[0]))
    for n, _e in PRINCIPALES: fuera.update(objs_de(n))
    return [o for o in sc.objects if o not in fuera and o.type not in {'CAMERA', 'LIGHT'}]


def entorno_visible(sc):
    return any(not o.hide_viewport for o in objs_entorno(sc) if o.type == 'MESH')


def _prop_entorno():
    def get(self): return entorno_visible(self)
    def set(self, v): poner_objs(self, objs_entorno(self), v)
    return BoolProperty(name="Entorno", description="Mostrar / ocultar el entorno (terreno, arboles, casas, fogatas...)", get=get, set=set)


class ESP_OT_escena_final(bpy.types.Operator):
    bl_idname = "espectadores.escena_final"; bl_label = "Escena final"; bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Muestra TODO como queda la escena final: entorno, cuadrilatero, luchadores y todo el publico (quita el foco)"

    def execute(self, ctx):
        sc = ctx.scene
        for g in GRUPOS: poner(sc, g[0], True)
        for n, _e in PRINCIPALES: poner_objs(sc, objs_de(n), True)
        poner_objs(sc, objs_ring(), True); poner_objs(sc, objs_entorno(sc), True); poner_objs(sc, objs_patrulla(), True)
        poner_jerry(sc, True)
        quitar_foco(sc)
        self.report({'INFO'}, "Escena final visible")
        return {'FINISHED'}


class ESP_PT_entorno(bpy.types.Panel):
    bl_label = "Entorno y escena final"; bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = "Espectadores"

    def draw(self, ctx):
        sc = ctx.scene; vis = entorno_visible(sc)
        self.layout.prop(sc, "esp_entorno", text="Entorno (terreno, arboles, casas...)", icon='HIDE_OFF' if vis else 'HIDE_ON', toggle=True)
        self.layout.operator("espectadores.escena_final", text="Ver escena final (mostrar todo)", icon='SCENE_DATA')


CLASES = (ESP_OT_solo, ESP_OT_todos, ESP_OT_seleccionar, ESP_PT_panel, ESP_OT_foco, ESP_OT_foco_rival, ESP_PT_foco, ESP_OT_principales, ESP_PT_principales, ESP_PT_ring, ESP_OT_escena_final, ESP_PT_entorno, ESP_PT_patrulla, ESP_PT_jerry)


def register():
    for c in CLASES: bpy.utils.register_class(c)
    bpy.types.Scene.esp_grupos_render = BoolProperty(name="Ocultar tambien en el render", default=True,
                                                    description="Al ocultar un grupo, tampoco sale en el render")
    for g in GRUPOS: setattr(bpy.types.Scene, "esp_" + g[0], _prop(g[0]))
    for n, _e in PRINCIPALES: setattr(bpy.types.Scene, "esp_pp_" + n, _prop_principal(n))
    bpy.types.Scene.esp_ring = _prop_ring()
    bpy.types.Scene.esp_entorno = _prop_entorno()
    bpy.types.Scene.esp_patrulla = _prop_patrulla()
    bpy.types.Scene.esp_jerry = _prop_jerry()


def unregister():
    for n in ["esp_" + g[0] for g in GRUPOS] + ["esp_pp_" + n for n, _e in PRINCIPALES] + ["esp_ring", "esp_entorno", "esp_patrulla", "esp_jerry", "esp_grupos_render"]:
        if hasattr(bpy.types.Scene, n): delattr(bpy.types.Scene, n)
    for c in reversed(CLASES):
        if c.is_registered: bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
