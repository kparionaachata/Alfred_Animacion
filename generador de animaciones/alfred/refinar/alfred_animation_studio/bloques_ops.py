# -*- coding: utf-8 -*-
"""
bloques_ops.py -- Alfred Animation Studio: panel "11  Bloques (suelo / pared)". La logica esta en `bloques.py`.

  alfst.bloques_suelo       rellena el suelo de la cueva desde el punto de INICIO (cursor 3D encima del piso), con montones irregulares
  alfst.bloques_pared       tapa lo que sigue mas alla de un suelo del estudio (columnas en el borde + filas escalonadas hacia dentro)
  alfst.bloques_caja        llena una caja entre la esquina A y la B (solida, hueca = pared / cascaron, con borde superior irregular)
  alfst.bloques_reemplazar  cambia un tipo de bloque por otro en una coleccion, o pone bloques ENCIMA de los de un tipo (tapar)
  alfst.bloques_quitar      borra una coleccion de bloques (devuelve las caras del mundo si era un suelo)
  alfst.bloques_cursor      copia el cursor 3D al inicio / esquina A / esquina B / zona libre
Los bloques salen de `bloques_dinamicos` (solo los cubicos). Todas las operaciones crean una coleccion repetible (si existe, se rehace).
"""
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup

from . import bloques as bq

_cache = []
def _items(self, context):
    _cache.clear(); _cache.extend((n, n, "") for n in bq.lista_bloques()); return _cache or [("", "(sin bloques)", "")]
def _items_ninguno(self, context):
    return [("", "(ninguno)", "")] + _items(self, context)
def _cols(self, context):
    return [(c.name, c.name, c.get("alfst_bloques", "")) for c in bpy.data.collections if "alfst_bloques" in c] or [("", "(sin colecciones)", "")]


class AlfredBloquesSettings(PropertyGroup):
    modo: EnumProperty(name="Modo", items=[("suelo", "Suelo", "Rellenar el suelo de una cueva"), ("pared", "Pared", "Tapar mas alla de un suelo"),
                                           ("caja", "Caja", "Caja / pared entre dos esquinas"), ("reemplazar", "Reemplazar", "Cambiar o tapar un tipo de bloque")], default="suelo")
    coleccion: StringProperty(name="Coleccion", default="bloques_suelo", description="Coleccion que se crea (si existe se rehace)")
    principal: EnumProperty(name="Bloque", items=_items)
    sec1: EnumProperty(name="Secundario 1", items=_items_ninguno)
    p1: FloatProperty(name="% sec. 1", default=0.06, min=0.0, max=1.0)
    sec2: EnumProperty(name="Secundario 2", items=_items_ninguno)
    p2: FloatProperty(name="% sec. 2", default=0.03, min=0.0, max=1.0)
    semilla: IntProperty(name="Semilla", default=21)
    # suelo
    inicio: FloatVectorProperty(name="Inicio", size=3, subtype='XYZ', precision=2, description="Punto sobre el piso de la cueva (z = nivel del piso)")
    radio: FloatProperty(name="Radio", default=20.0, min=1.0, max=80.0)
    alto_max: IntProperty(name="Alto de montones", default=2, min=0, max=6)
    densidad: FloatProperty(name="Densidad de montones", default=0.5, min=0.0, max=1.0)
    libre: FloatVectorProperty(name="Zona libre", size=3, subtype='XYZ', precision=2, description="Otro punto que queda plano (ademas del inicio)")
    usar_libre: BoolProperty(name="Usar zona libre", default=False)
    radio_libre: FloatProperty(name="Radio libre", default=2.5, min=0.0, max=10.0)
    retirar: BoolProperty(name="Retirar caras del piso", default=True, description="Quita las caras planas del mundo bajo los bloques (evita parpadeo); se devuelven al quitar")
    # pared
    suelo_base: EnumProperty(name="Suelo", items=_cols)
    alto_pared: IntProperty(name="Alto maximo", default=16, min=1, max=64)
    filas: IntProperty(name="Filas irregulares", default=4, min=0, max=8)
    # caja
    esq_a: FloatVectorProperty(name="Esquina A", size=3, subtype='XYZ', precision=2)
    esq_b: FloatVectorProperty(name="Esquina B", size=3, subtype='XYZ', precision=2)
    hueca: BoolProperty(name="Hueca (solo cascaron)", default=False)
    irregular: FloatProperty(name="Irregularidad arriba", default=0.0, min=0.0, max=0.95)
    # reemplazar
    col_obj: EnumProperty(name="En", items=_cols)
    tipo_de: EnumProperty(name="Tipo", items=_items)
    tipo_a: EnumProperty(name="Por / encima", items=_items)
    porcentaje: FloatProperty(name="% de bloques", default=1.0, min=0.0, max=1.0)
    encima: BoolProperty(name="Poner ENCIMA (tapar)", default=False)
    alto_encima: IntProperty(name="Alto encima", default=1, min=1, max=4)


def _mezcla(s):
    return bq.Mezcla(s.principal, s.sec1, s.p1, s.sec2, s.p2, s.semilla)


class ALFST_OT_BloquesSuelo(Operator):
    bl_idname = "alfst.bloques_suelo"; bl_label = "Rellenar suelo"; bl_options = {"REGISTER", "UNDO"}
    bl_description = "Rellena el suelo de la cueva desde el punto de inicio (relleno por vecinos con aire encima) con montones irregulares"

    def execute(self, context):
        s = context.scene.alfst_bloques
        try: r = bq.suelo(context.scene, s.coleccion, _mezcla(s), tuple(s.inicio), s.radio, s.alto_max, s.densidad, [tuple(s.libre)] if s.usar_libre else [], s.radio_libre, s.retirar, s.semilla)
        except Exception as e: self.report({"ERROR"}, "Suelo: %s" % e); return {"CANCELLED"}
        self.report({"INFO"}, "Suelo '%s': %d celdas, %d bloques, %d caras retiradas" % (s.coleccion, r["celdas"], r["bloques"], r["caras"])); return {"FINISHED"}


class ALFST_OT_BloquesPared(Operator):
    bl_idname = "alfst.bloques_pared"; bl_label = "Tapar con pared"; bl_options = {"REGISTER", "UNDO"}
    bl_description = "Columnas en el borde del suelo elegido (hasta el techo) y filas escalonadas hacia dentro para que no parezca un muro plano"

    def execute(self, context):
        s = context.scene.alfst_bloques
        try: r = bq.pared(context.scene, s.coleccion, _mezcla(s), s.suelo_base, s.alto_pared, s.filas, s.semilla, [tuple(s.libre)] if s.usar_libre else [], s.radio_libre)
        except Exception as e: self.report({"ERROR"}, "Pared: %s" % e); return {"CANCELLED"}
        self.report({"INFO"}, "Pared '%s': %d columnas de borde, %d bloques" % (s.coleccion, r["borde"], r["bloques"])); return {"FINISHED"}


class ALFST_OT_BloquesCaja(Operator):
    bl_idname = "alfst.bloques_caja"; bl_label = "Llenar caja"; bl_options = {"REGISTER", "UNDO"}
    bl_description = "Llena con bloques la caja entre la esquina A y la B (una pared es una caja de 1 de grosor)"

    def execute(self, context):
        s = context.scene.alfst_bloques
        try: r = bq.caja(context.scene, s.coleccion, _mezcla(s), tuple(s.esq_a), tuple(s.esq_b), s.hueca, s.irregular, s.semilla)
        except Exception as e: self.report({"ERROR"}, "Caja: %s" % e); return {"CANCELLED"}
        self.report({"INFO"}, "Caja '%s': %d bloques" % (s.coleccion, r["bloques"])); return {"FINISHED"}


class ALFST_OT_BloquesReemplazar(Operator):
    bl_idname = "alfst.bloques_reemplazar"; bl_label = "Reemplazar / tapar"; bl_options = {"REGISTER", "UNDO"}
    bl_description = "Cambia los bloques de un tipo por otro en la coleccion, o pone bloques encima de ellos"

    def execute(self, context):
        s = context.scene.alfst_bloques
        try: r = bq.reemplazar(context.scene, s.col_obj, s.tipo_de, s.tipo_a, s.porcentaje, s.encima, s.alto_encima, s.semilla)
        except Exception as e: self.report({"ERROR"}, "Reemplazar: %s" % e); return {"CANCELLED"}
        self.report({"INFO"}, "Reemplazar: %s" % r); return {"FINISHED"}


class ALFST_OT_BloquesQuitar(Operator):
    bl_idname = "alfst.bloques_quitar"; bl_label = "Quitar coleccion"; bl_options = {"REGISTER", "UNDO"}
    bl_description = "Borra la coleccion de bloques indicada (y devuelve las caras del mundo si era un suelo)"

    def execute(self, context):
        s = context.scene.alfst_bloques; n = bq.quitar(context.scene, s.coleccion)
        self.report({"INFO"}, "'%s' quitada (%d caras devueltas)" % (s.coleccion, n)); return {"FINISHED"}


class ALFST_OT_BloquesCursor(Operator):
    bl_idname = "alfst.bloques_cursor"; bl_label = "Cursor 3D"; bl_options = {"REGISTER"}
    bl_description = "Copia la posicion del cursor 3D al campo indicado"
    destino: EnumProperty(items=[("inicio", "Inicio", ""), ("esq_a", "Esquina A", ""), ("esq_b", "Esquina B", ""), ("libre", "Zona libre", "")])

    def execute(self, context):
        setattr(context.scene.alfst_bloques, self.destino, tuple(context.scene.cursor.location)); return {"FINISHED"}


class ALFST_PT_Bloques(Panel):
    bl_label = "11  Bloques (suelo / pared)"; bl_idname = "ALFST_PT_bloques"
    bl_space_type = "VIEW_3D"; bl_region_type = "UI"; bl_category = "Alfred Studio"; bl_parent_id = "ALFST_PT_main"; bl_options = {"DEFAULT_CLOSED"}

    def _vec(self, lay, s, prop, dest):
        r = lay.row(align=True); r.prop(s, prop); r.operator("alfst.bloques_cursor", text="", icon="CURSOR").destino = dest

    def draw(self, context):
        lay = self.layout; s = context.scene.alfst_bloques
        lay.row().prop(s, "modo", expand=True)
        if s.modo != "reemplazar":
            b = lay.box(); b.label(text="Bloques (bloques_dinamicos)", icon="MESH_CUBE"); b.prop(s, "principal")
            r = b.row(align=True); r.prop(s, "sec1", text=""); r.prop(s, "p1", text="%")
            r = b.row(align=True); r.prop(s, "sec2", text=""); r.prop(s, "p2", text="%")
            lay.prop(s, "coleccion")
        if s.modo == "suelo":
            c = lay.column(align=True); self._vec(c, s, "inicio", "inicio"); c.prop(s, "radio"); c.prop(s, "alto_max"); c.prop(s, "densidad", slider=True); c.prop(s, "retirar")
            c = lay.column(align=True); c.prop(s, "usar_libre")
            if s.usar_libre: self._vec(c, s, "libre", "libre")
            c.prop(s, "radio_libre")
            op = "alfst.bloques_suelo"; ic = "MOD_BUILD"
        elif s.modo == "pared":
            c = lay.column(align=True); c.prop(s, "suelo_base"); c.prop(s, "alto_pared"); c.prop(s, "filas"); c.prop(s, "usar_libre")
            if s.usar_libre: self._vec(c, s, "libre", "libre"); c.prop(s, "radio_libre")
            op = "alfst.bloques_pared"; ic = "MOD_BUILD"
        elif s.modo == "caja":
            c = lay.column(align=True); self._vec(c, s, "esq_a", "esq_a"); self._vec(c, s, "esq_b", "esq_b"); c.prop(s, "hueca"); c.prop(s, "irregular", slider=True)
            op = "alfst.bloques_caja"; ic = "CUBE"
        else:
            c = lay.column(align=True); c.prop(s, "col_obj"); c.prop(s, "tipo_de"); c.prop(s, "tipo_a"); c.prop(s, "porcentaje", slider=True); c.prop(s, "encima")
            if s.encima: c.prop(s, "alto_encima")
            op = "alfst.bloques_reemplazar"; ic = "FILE_REFRESH"
        lay.prop(s, "semilla")
        r = lay.row(align=True); r.scale_y = 1.3; r.operator(op, icon=ic)
        if s.modo != "reemplazar": r.operator("alfst.bloques_quitar", icon="TRASH")


clases = (AlfredBloquesSettings, ALFST_OT_BloquesSuelo, ALFST_OT_BloquesPared, ALFST_OT_BloquesCaja, ALFST_OT_BloquesReemplazar, ALFST_OT_BloquesQuitar,
          ALFST_OT_BloquesCursor, ALFST_PT_Bloques)


def register_bloques():
    for c in clases:
        try: bpy.utils.unregister_class(c)
        except RuntimeError: pass
        bpy.utils.register_class(c)
    bpy.types.Scene.alfst_bloques = PointerProperty(type=AlfredBloquesSettings)


def unregister_bloques():
    for c in reversed(clases):
        try: bpy.utils.unregister_class(c)
        except RuntimeError: pass
    if hasattr(bpy.types.Scene, "alfst_bloques"): del bpy.types.Scene.alfst_bloques
