# -*- coding: utf-8 -*-
"""Parte 6: al romperse cada bloque de la puerta (`refugio_bloque_06` f796 y `refugio_bloque_07` f825) queda en el suelo un TABLON pequeno (el mismo bloque a escala 0.25, objetos `drop_tablon_1` / `drop_tablon_2`, material de tablones) que flota (sube y baja 3.5 cm, 32 f) y gira (360 grados cada 40 f).
Alfred, que empieza a caminar justo despues de terminar la puerta (f826, `caminar_estudio_alfred_y_jerry.py` con S_A=826), los ABSORBE al avanzar: cuando su pecho (`Spine1_alfred`) esta a <= 0.55 m (el de abajo) / 0.35 m (el de arriba) en el plano, el tablon vuela al pecho acelerando 6 f, se encoge y desaparece, con el `random/pop.ogg` (0.6) de la mesa.
Se ejecuta DENTRO de Blender con exec DESPUES de caminar_estudio_alfred_y_jerry.py (necesita la marcha de Alfred ya animada). Nunca `raise SystemExit`. Se puede repetir (borra las claves y sonidos de los tablones y los vuelve a hacer)."""
import bpy, math, os, traceback
from mathutils import Vector

try:
    sc = bpy.context.scene
    ss = lambda x: 0.0 if x <= 0 else (1.0 if x >= 1 else x * x * (3 - 2 * x))
    AA = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and "Hips_alfred" in o.pose.bones); pecho = AA.pose.bones["Spine1_alfred"]
    S = 0.25; ALT = 14.0 + 0.18 + 0.125; CENTRO = {"06": Vector((-96.5, -107.5, 14.5)), "07": Vector((-96.5, -107.5, 15.5))}
    cfg = [("drop_tablon_1", "refugio_bloque_06", 796, Vector((0.12, -0.12)), 0.55, "caer"), ("drop_tablon_2", "refugio_bloque_07", 825, Vector((-0.10, -0.05)), 0.35, "caer")]
    objs = []
    for nombre, bloque, f_sp, off, R, _ in cfg:
        src = bpy.data.objects[bloque]; o = bpy.data.objects.get(nombre)
        if o is None: o = bpy.data.objects.new(nombre, src.data); src.users_collection[0].objects.link(o)
        o.rotation_mode = 'XYZ'; o.hide_viewport = False; o.hide_render = False
        if o.animation_data and o.animation_data.action: bpy.data.actions.remove(o.animation_data.action)
        o.animation_data_create(); o.animation_data.action = bpy.data.actions.new(nombre + "_flota_y_se_absorbe"); objs.append(o)
    # ---- calcular el pecho de Alfred por frame (ya animado) ----
    FMAX = 900; CH = {}
    for f in range(795, FMAX):
        sc.frame_set(f); CH[f] = AA.matrix_world @ pecho.head
    def hover(f_sp, off, base_xy, f):                                                       # posicion del centro del tablon (sin absorcion)
        t = f - f_sp; xy = Vector(base_xy) + off * ss(t / 6.0)
        bob = 0.035 * math.sin(2 * math.pi * max(0, t - 8) / 32.0)
        return Vector((xy.x, xy.y, ALT + bob)), math.radians(360.0 * t / 40.0)
    ABS = []; prev_trig = 0
    for (nombre, bloque, f_sp, off, R, _), o in zip(cfg, objs):
        base = CENTRO[bloque[-2:]]; trig = None
        for f in range(max(f_sp + 8, prev_trig + 3), FMAX):
            p, _r = hover(f_sp, off, (base.x, base.y), f)
            if math.hypot(CH[f].x - p.x, CH[f].y - p.y) <= R: trig = f; break
        if trig is None: raise ValueError("Alfred no llega a absorber " + nombre)
        prev_trig = trig; ABS.append(trig); print(nombre, "aparece f", f_sp, "absorbido f", trig, "-> f", trig + 6)
        o.location = base; o.scale = (0, 0, 0)
        o.keyframe_insert("scale", frame=1); o.keyframe_insert("scale", frame=f_sp - 1)
        for f in range(f_sp, trig + 7):
            t = f - f_sp
            if t <= 8 and bloque.endswith("07"):                                            # el de arriba cae (gravedad) hasta el suelo
                u = min(1.0, t / 8.0); xy = Vector((base.x, base.y)) + off * ss(t / 6.0); z = base.z + (ALT - base.z) * u * u; p = Vector((xy.x, xy.y, z)); rz = math.radians(360.0 * t / 40.0)
            elif t <= 8: p, rz = hover(f_sp, off, (base.x, base.y), f); p.z = base.z + (ALT - base.z) * ss(t / 8.0)    # el de abajo salta un poco y se asienta
            else: p, rz = hover(f_sp, off, (base.x, base.y), f)
            esc = S
            if f > trig:                                                                    # absorcion: vuela al pecho acelerando y se encoge
                u = ((f - trig) / 6.0) ** 2; p0, _r = hover(f_sp, off, (base.x, base.y), trig); p0 = p0.copy(); p = p0.lerp(CH[f] + Vector((0, 0, -0.05)), min(1.0, u)); esc = S * (1 - min(1.0, u))
            o.location = p; o.rotation_euler = (0, 0, rz); o.scale = (esc, esc, esc)
            o.keyframe_insert("location", frame=f); o.keyframe_insert("rotation_euler", frame=f); o.keyframe_insert("scale", frame=f)
        o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=trig + 7)
        o.hide_viewport = False; o.hide_render = False; o.keyframe_insert("hide_viewport", frame=trig + 6); o.keyframe_insert("hide_render", frame=trig + 6)
        o.hide_viewport = True; o.hide_render = True; o.keyframe_insert("hide_viewport", frame=trig + 7); o.keyframe_insert("hide_render", frame=trig + 7)
        o.hide_viewport = False; o.hide_render = False; o.keyframe_insert("hide_viewport", frame=1); o.keyframe_insert("hide_render", frame=1)
        for fc in o.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT' if fc.data_path.startswith("hide") else 'LINEAR'
    # ---- sonidos ----
    ed = sc.sequence_editor; libre = max([s_.channel for s_ in ed.strips_all] + [30]) + 1
    for s_ in [s_ for s_ in ed.strips_all if str(s_.get("guion_id", "")).startswith("snd6_jerry_p_tablon_absorbido")]: ed.strips.remove(s_)
    for i, trig in enumerate(ABS):
        f = trig + 6; s_ = ed.strips.new_sound(f"SND_jerry_p_tablon_absorbido_{i + 1}_{f}", r"C:\Users\user\Desktop\Alfred_Animacion\sonidos\sounds\random\pop.ogg", libre + i, f)
        s_.volume = 0.6; s_["vol_base"] = 0.6; s_["mcsnd"] = "objetos"; s_["mcsnd_ev"] = "tablon_absorbido"; s_["guion_id"] = f"snd6_jerry_p_tablon_absorbido_{i + 1}"
    res = {}
    for f in (795, 796, 800, 826, 830, ABS[0] + 3, ABS[0] + 7, ABS[1] + 3, ABS[1] + 7):
        sc.frame_set(f); res[f] = {o.name: ([round(x, 2) for x in o.location], round(o.scale.x, 2), o.hide_viewport) for o in objs}
    sc.frame_set(120); print(res); print("LISTO")
except Exception:
    traceback.print_exc()
