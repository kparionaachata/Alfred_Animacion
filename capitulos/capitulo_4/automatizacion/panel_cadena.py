# -*- coding: utf-8 -*-
"""PANEL "Cadena" (barra lateral del visor 3D, pestaña "Cadena"): reconstruir la animacion EN SEGUNDO PLANO sin bloquear Blender.
  Reconstruir:   guarda la escena (si tiene cambios) -> respaldo en respaldos_auto/ -> Blender sin ventana ejecuta la cadena (solo desde el paso que
                 cambio, si se puede) + chequeos -> pone el resultado en el archivo y lo vuelve a abrir aqui. Mientras tanto se puede seguir mirando.
  Solo chequear: corre los chequeos sobre la escena actual (sin guardar ni tocar el archivo).
Se carga con `addon_cadena.py` (instalable) o ejecutando este archivo. El estado queda en bpy.app.driver_namespace["cadena_estado"]."""
import bpy, os, sys, time, threading

AUTO = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\automatizacion"
if AUTO not in sys.path: sys.path.insert(0, AUTO)
import importlib
import cadena_comun as cc
import lanzador as lz
importlib.reload(cc); importlib.reload(lz)

E = bpy.app.driver_namespace.setdefault("cadena_estado", {})          # estado compartido (tambien lo lee Claude por MCP)
E.setdefault("fase", "libre")


def _redibujar():
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            if a.type == 'VIEW_3D': a.tag_redraw()


def _pasos(self, context):
    try:
        cfg = cc.cargar_config(cc.ruta_config(bpy.data.filepath))
        return [(str(i), "%d  %s" % (i, p["id"]), p.get("tipo", "")) for i, p in enumerate(cfg.get("pasos", []))] or [("0", "0", "")]
    except Exception: return [("0", "(sin cadena)", "")]


def _hilo(plan, respaldo_max):
    """en otro hilo (no toca bpy): respaldo + Blender en segundo plano"""
    try:
        if respaldo_max is not None:
            E["fase"] = "respaldo"; E["respaldo"] = cc.respaldar(plan["blend"], respaldo_max)
        E["fase"] = "corriendo"; E["t_blender"] = time.time(); pr = lz.lanzar(plan); E["proceso"] = pr; pr.wait()
        E["fase"] = "termino"
    except Exception as ex:
        E["fase"] = "termino"; E["error_hilo"] = str(ex)


def _vigilar():
    """timer en el hilo principal: muestra el progreso y, al terminar, pone el resultado y recarga la escena"""
    if E.get("fase") in ("respaldo", "corriendo"):
        if E.get("plan"): E["progreso"] = lz.ultimo_paso(E["plan"])
        _redibujar(); return 1.0
    if E.get("fase") != "termino": return None
    plan = E["plan"]; reemplazar = not bpy.data.is_dirty                  # si se cambio la escena mientras tanto, no se pisa
    R = lz.terminar(plan, reemplazar=reemplazar) if not E.get("error_hilo") else {"ok": False, "error": E["error_hilo"]}
    R.setdefault("blend", plan["blend"]); E["R"] = R; E["texto"] = lz.resumen(R); E["fase"] = "libre"; E["fin"] = time.time(); E.pop("proceso", None)
    print("[cadena]\n" + E["texto"])
    if R.get("reemplazado") and os.path.normcase(bpy.data.filepath) == os.path.normcase(plan["blend"]):
        try:
            win = bpy.context.window_manager.windows[0]
            with bpy.context.temp_override(window=win): bpy.ops.wm.revert_mainfile()
        except Exception as ex: E["texto"] += "\n(No se pudo recargar la escena: %s. Usa Archivo > Revertir.)" % ex
    _redibujar(); return None


class CADENA_OT_reconstruir(bpy.types.Operator):
    bl_idname = "cadena.reconstruir"; bl_label = "Reconstruir en segundo plano"
    bl_description = "Guarda, respalda y reconstruye la cadena de esta parte en un Blender sin ventana; al terminar recarga el resultado"
    modo: bpy.props.StringProperty(default="")                          # vacio = lo que diga el panel; o auto / completo / <n> / chequeos

    def execute(self, context):
        if E.get("fase") not in ("libre", None): self.report({'WARNING'}, "Ya hay una reconstruccion en marcha"); return {'CANCELLED'}
        blend = bpy.data.filepath
        if not blend: self.report({'ERROR'}, "Guarda primero el archivo .blend"); return {'CANCELLED'}
        sc = context.scene; modo = self.modo or (sc.cadena_modo if sc.cadena_modo != "desde" else sc.cadena_paso)
        try:
            if modo == "chequeos":
                origen = None
                if bpy.data.is_dirty:                                          # la escena actual tal cual, sin tocar el archivo
                    origen = os.path.join(cc.dir_estado(blend), "escena_viva_tmp.blend"); bpy.ops.wm.save_as_mainfile(filepath=origen, copy=True)
                plan = lz.preparar(blend, "chequeos", bpy.app.binary_path, origen); plan["borrar"] = origen; rmax = None
            else:
                if bpy.data.is_dirty: bpy.ops.wm.save_mainfile()               # el respaldo y la reconstruccion parten de lo que se ve
                plan = lz.preparar(blend, modo, bpy.app.binary_path, chequear=sc.cadena_chequear)
                if plan.get("nada"):
                    E.update(texto=plan["texto"], R={"ok": True, "sin_cambios": True}); self.report({'INFO'}, plan["texto"]); return {'FINISHED'}
                rmax = cc.cargar_config(cc.ruta_config(blend)).get("respaldos_max", 4)
        except Exception as ex:
            self.report({'ERROR'}, str(ex)); E["texto"] = "ERROR\n" + str(ex); return {'CANCELLED'}
        for k in ("R", "error_hilo", "respaldo", "progreso"): E.pop(k, None)
        E.update(plan=plan, fase="respaldo" if rmax is not None else "corriendo", inicio=time.time(), modo=modo, texto="")
        threading.Thread(target=_hilo, args=(plan, rmax), daemon=True).start()
        if not bpy.app.timers.is_registered(_vigilar): bpy.app.timers.register(_vigilar, first_interval=1.0)
        self.report({'INFO'}, "Reconstruccion lanzada" if modo != "chequeos" else "Chequeos lanzados"); return {'FINISHED'}


class CADENA_OT_cancelar(bpy.types.Operator):
    bl_idname = "cadena.cancelar"; bl_label = "Cancelar"; bl_description = "Detiene el Blender en segundo plano (el archivo no se toca)"

    def execute(self, context):
        pr = E.get("proceso")
        if pr and pr.poll() is None: pr.kill()
        return {'FINISHED'}


class CADENA_OT_abrir(bpy.types.Operator):
    bl_idname = "cadena.abrir"; bl_label = "Abrir"; bl_description = "Abre el informe, el log o la cadena (.json) con el programa de Windows"
    que: bpy.props.StringProperty(default="informe")

    def execute(self, context):
        b = bpy.data.filepath
        p = {"informe": cc.ruta_informe(b), "log": os.path.join(cc.dir_estado(b), "log.txt"), "cadena": cc.ruta_config(b),
             "respaldos": os.path.join(os.path.dirname(b), "respaldos_auto")}[self.que]
        if not os.path.exists(p): self.report({'WARNING'}, "No existe todavia: " + p); return {'CANCELLED'}
        os.startfile(p); return {'FINISHED'}


class CADENA_PT_panel(bpy.types.Panel):
    bl_label = "Cadena (reconstruir)"; bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = "Cadena"

    def draw(self, context):
        L = self.layout; sc = context.scene; b = bpy.data.filepath
        cfgp = cc.ruta_config(b) if b else ""
        if not b or not os.path.isfile(cfgp):
            L.label(text="Sin cadena para este archivo", icon='INFO')
            if b: L.label(text="Crea cadenas/%s.json" % cc.nombre_base(b))
            return
        try: n = len(cc.cargar_config(cfgp).get("pasos", []))
        except Exception as ex: L.label(text="Error en la cadena: %s" % ex, icon='ERROR'); return
        L.label(text="%s: %d pasos" % (cc.nombre_base(b), n), icon='SEQ_STRIP_DUPLICATE')
        fase = E.get("fase", "libre")
        if fase in ("respaldo", "corriendo"):
            box = L.box(); t = time.time() - E.get("inicio", time.time())
            box.label(text=("Respaldando el archivo..." if fase == "respaldo" else "Reconstruyendo...") + "  %d:%02d" % (t // 60, t % 60), icon='TIME')
            if E.get("progreso"): box.label(text=E["progreso"][:70])
            box.operator("cadena.cancelar", icon='CANCEL'); return
        L.prop(sc, "cadena_modo", text="")
        if sc.cadena_modo == "desde": L.prop(sc, "cadena_paso", text="Paso")
        L.prop(sc, "cadena_chequear")
        L.operator("cadena.reconstruir", icon='FILE_REFRESH')
        L.operator("cadena.reconstruir", text="Solo chequear", icon='VIEWZOOM').modo = "chequeos"
        R = E.get("R")
        if R is not None or E.get("texto"):
            box = L.box(); ok = R and R.get("ok")
            if R and R.get("errores") is not None:
                box.label(text="Chequeos: %d errores, %d avisos" % (R["errores"], R["avisos"]), icon='ERROR' if R["errores"] else ('INFO' if R["avisos"] else 'CHECKMARK'))
            elif not ok: box.label(text="Fallo la reconstruccion (mira el log)", icon='ERROR')
            for l in (E.get("texto") or "").splitlines()[:14]:
                if l.strip(): box.label(text=l[:80])
        row = L.row(align=True)
        for q, ic in (("informe", 'TEXT'), ("log", 'CONSOLE'), ("cadena", 'PREFERENCES'), ("respaldos", 'FILE_FOLDER')):
            row.operator("cadena.abrir", text=q.capitalize(), icon=ic).que = q


CLASES = (CADENA_OT_reconstruir, CADENA_OT_cancelar, CADENA_OT_abrir, CADENA_PT_panel)


def register():
    for c in CLASES:
        try: bpy.utils.unregister_class(getattr(bpy.types, c.__name__))
        except Exception: pass
        bpy.utils.register_class(c)
    bpy.types.Scene.cadena_modo = bpy.props.EnumProperty(name="Modo", items=[
        ("auto", "Automatico (solo lo que cambio)", "Reconstruye desde el primer paso que cambio; si la escena se toco a mano, todo"),
        ("completo", "Completo", "Todos los pasos desde el principio"),
        ("desde", "Desde un paso...", "Desde el paso elegido (usa el checkpoint anterior si existe)")], default="auto")
    bpy.types.Scene.cadena_paso = bpy.props.EnumProperty(name="Paso", items=_pasos)
    bpy.types.Scene.cadena_chequear = bpy.props.BoolProperty(name="Chequear al terminar", default=True,
                                                             description="Corre los chequeos automaticos despues de reconstruir (~1 min). Desactivalo para iterar rapido")


def unregister():
    for c in reversed(CLASES):
        try: bpy.utils.unregister_class(c)
        except Exception: pass
    for p in ("cadena_modo", "cadena_paso", "cadena_chequear"):
        if hasattr(bpy.types.Scene, p): delattr(bpy.types.Scene, p)


if __name__ in ("__main__", "__cadena_panel__"):
    register()
