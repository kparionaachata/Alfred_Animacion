# -*- coding: utf-8 -*-
"""alfred_cueva_3.blend: Alfred, de pie en (-67.5,-17.5,-12.0), pica con su pico de piedra la veta de hierro (bloque_iron_ore_-68_-19_-12,
justo delante de el, hacia -Y). Al 5.o golpe el bloque se rompe: saltan trocitos de la veta y cae el hierro en bruto (objetos/vanilla/raw_iron),
que rebota y queda flotando y girando como un objeto soltado en Minecraft. Alfred se endereza con el pico listo.
Usa la mecanica de minado de alfred_cae_estalagmita.py (Rig, IK de brazos, matriz del pico; mismas reacciones a cada golpe).
Uso (Blender):  exec(open(r"...\\alfred_pica_hierro.py", encoding="utf8").read()); construir()      (repetible)
"""
import bpy, math, random
from mathutils import Vector, Matrix, Quaternion

BASE = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_cae_estalagmita.py"
PIE = Vector((-67.5, -17.5, -11.95))             # donde esta de pie (+5 cm: la suela real queda en -12) (cara de arriba del bloque de andesita)
VETA = "bloque_iron_ore_-68_-19_-12"             # celda (-68,-19,-12): de y -19 a -18, z -12 a -11
RAW_BLEND = r"C:\Users\user\Desktop\Alfred_Animacion\objetos\vanilla\raw_iron\raw_iron.blend"
GOLPES = [12, 28, 44, 60, 76]                    # 5 golpes; el ultimo rompe la veta
F_ROMPE = GOLPES[-1]
F_FIN = 140
TAM_ITEM = 0.32                                   # tamano del hierro en bruto soltado (m)
N_TROZOS = 10
ORIGEN = "pica_hierro"
ESC_PICO = 0.8
PARAMS = dict(th0=-0.10, cab0=-0.15, th1=0.30, cab1=-0.05, b0=-30, b1=100, xg=-0.08, yg=1.20, x0=0.40, y0=0.30, z0=1.50, mano_i=0.28, phi=30)   # golpe en diagonal (hombro derecho -> abajo a la izquierda), medido con BVH
R180 = Quaternion((0, 0, 1), math.pi)             # mira a -Y (hacia la veta)


def _base():
    ns = {"__name__": "base_mina"}
    exec(open(BASE, encoding="utf8").read(), ns)
    return ns


def construir():
    B = _base(); sc = bpy.context.scene; obj = bpy.data.objects
    rig = B["Rig"](); D = B["D"]; lerp = B["lerp"]; vlerp = B["vlerp"]; suave = B["suave"]
    veta = obj[VETA]

    # golpe con AMBAS manos y pico a escala ESC_PICO: la mano izquierda va mas abajo en el mango; al levantar el pico el cuerpo y la cabeza se
    # balancean hacia atras (th0, cab0) para que los brazos pasen por delante de la cabeza sin cruzar las mallas; al golpear se inclina adelante
    P = dict(PARAMS)
    k = ESC_PICO / 0.6
    PUNTA_D, PUNTA_E = B["PUNTA_D"] * k, B["PUNTA_E"] * k

    def estado(s):
        th = lerp(P["th0"], P["th1"], s); tg = lerp(0.20, 0.40, s); cab = lerp(P["cab0"], P["cab1"], s)
        dirs = B["pose_torso"](th, cabeza=cab); dirs.update(B["piernas"](0.10, tg, -tg))
        _, colas, _ = B["resolver_con_brazos"](rig, dirs, aplicar=False)
        piso = min(colas["Rightknee_alfred"].z, colas["Leftknee_alfred"].z) + B["SUELO_PIE"]
        yf = (colas["Rightknee_alfred"].y + colas["Leftknee_alfred"].y) / 2
        b = lerp(D(P["b0"]), D(P["b1"]), s)
        fi = D(P.get("phi", 0.0))                         # plano del golpe inclinado: de arriba a la derecha a abajo a la izquierda (diagonal)
        d = Vector((math.cos(b) * math.sin(fi), math.sin(b), math.cos(b) * math.cos(fi)))
        e = Vector((-math.sin(b) * math.sin(fi), math.cos(b), -math.sin(b) * math.cos(fi)))
        T = Vector((P["xg"], yf + P["yg"], piso + 0.955))   # la punta toca la cara de arriba de la veta
        G1 = T - d * PUNTA_D - e * PUNTA_E; G0 = Vector((P["x0"], yf + P["y0"], piso + P["z0"]))
        G = vlerp(G0, G1, s)
        return dict(th=th, cab=cab, lado=0.0, sep=0.10, cad=tg, rod=-tg, Gd=G, Gi=G - d * P["mano_i"], d=d, yf=yf, piso=piso)

    def aplicar(st):
        dirs = B["pose_torso"](st["th"], st["cab"], st["lado"]); dirs.update(B["piernas"](st["sep"], st["cad"], st["rod"]))
        pose, colas, info = B["resolver_con_brazos"](rig, dirs, Vector(st["Gd"]), Vector(st["Gi"]), polo_d=(1, -0.4, -0.3), polo_i=(-1, -0.4, -0.3))
        return pose, colas, info, B["norm"](st["d"])

    def matriz_pico(G, d):
        d = B["norm"](d); lado = Vector((1, 0, 0)) if abs(d.x) < 0.9 else Vector((0, 1, 0)); e = B["norm"](d.cross(lado))
        R = B["base_item"](B["PICO_EJE"], d, d.cross(e))
        return Matrix.LocRotScale(Vector(G) - R @ (ESC_PICO * B["PICO_AGARRE"]), R.to_quaternion(), Vector((ESC_PICO,) * 3))

    def s_de(f):
        if f > F_ROMPE:                                                   # se endereza con el pico listo
            u = (f - F_ROMPE - 3) / 12.0
            return 1.0 if u <= 0 else lerp(1.0, 0.35, suave(u))
        for g in GOLPES:
            gp = g - 16
            if gp <= f <= g:
                if f < gp + 6: return 1.0 - suave((f - gp) / 6.0)
                if f < g - 4: return 0.0
                u = (f - (g - 4)) / 4.0; return u * u
        return 0.0

    arm = obj["Armature"]; emp = obj["alfred"]; pico = obj["stone_pickaxe"]
    for o in (arm, emp, pico):
        if o.animation_data: o.animation_data_clear()
    emp.rotation_mode = 'QUATERNION'; pico.rotation_mode = 'QUATERNION'
    for n in B["ORDEN"]: arm.pose.bones[n].rotation_mode = 'XYZ'
    for f in range(1, F_FIN + 1):
        st = estado(s_de(f))
        kg = min([f - g for g in GOLPES if f > g] or [99])                 # rebote del pico y del cuerpo tras cada golpe (accion y reaccion)
        if kg < 10 and f <= F_ROMPE + 2:
            r = math.exp(-(kg - 1) / 2.5) * math.cos(0.9 * (kg - 1))
            st["th"] -= 0.10 * r; st["Gd"] = Vector(st["Gd"]) + Vector((0, -0.03 * r, 0.06 * r))
        _, colas, info, d = aplicar(st)
        loc = PIE - R180 @ Vector((0, st["yf"], st["piso"]))
        emp.location = loc; emp.rotation_quaternion = R180
        emp.keyframe_insert("location", frame=f); emp.keyframe_insert("rotation_quaternion", frame=f)
        arm.pose.bones["Hips_alfred"].location = (0, 0, 0); arm.pose.bones["Hips_alfred"].keyframe_insert("location", frame=f)
        for n in B["ORDEN"]: arm.pose.bones[n].keyframe_insert("rotation_euler", frame=f)
        Mw = B["matriz_mundo"](loc, R180, matriz_pico(info["mano_d"], d))
        B["poner_matriz"](pico, Mw)
        for dp in ("location", "rotation_quaternion", "scale"): pico.keyframe_insert(dp, frame=f)
    # --- la veta se rompe
    if veta.animation_data: veta.animation_data_clear()
    for f, v in ((1, False), (F_ROMPE, True)):
        veta.hide_viewport = v; veta.hide_render = v
        veta.keyframe_insert("hide_viewport", frame=f); veta.keyframe_insert("hide_render", frame=f)
    centro = veta.matrix_world.translation + Vector((0, 0, 0.5))
    rec = bpy.data.collections.get("luz_entrada_receptores")
    rnd = random.Random(11); g = 9.8 / 24 / 24
    for i in range(N_TROZOS):                                             # trocitos de la veta
        n = "trozo_hierro_%02d" % i
        if obj.get(n): bpy.data.objects.remove(obj[n], do_unlink=True)
        t = bpy.data.objects.new(n, veta.data); bpy.data.collections["cueva_bloques"].objects.link(t)
        if rec: rec.objects.link(t)
        esc = rnd.uniform(0.07, 0.13); t.scale = (esc,) * 3
        p = centro + Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3)))
        v = Vector((rnd.uniform(-1.2, 1.2), rnd.uniform(-1.2, 1.2), rnd.uniform(1.5, 3.0))) / 24
        giro = Vector((rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4)))
        vida = rnd.randint(14, 22)
        for k in range(0, vida + 1):
            q = p + v * k + Vector((0, 0, -0.5 * g * k * k))
            q.z = max(q.z, -12.0)
            t.location = q; t.rotation_euler = giro * k
            t.keyframe_insert("location", frame=F_ROMPE + k); t.keyframe_insert("rotation_euler", frame=F_ROMPE + k)
        for f, hv in ((1, True), (F_ROMPE, False), (F_ROMPE + vida + 1, True)):
            t.hide_viewport = hv; t.hide_render = hv
            t.keyframe_insert("hide_viewport", frame=f); t.keyframe_insert("hide_render", frame=f)
    # --- hierro en bruto: salta, rebota y queda flotando y girando
    it = obj.get("raw_iron_soltado")
    if it is None:
        with bpy.data.libraries.load(RAW_BLEND, link=False) as (src, dst): dst.objects = ["raw_iron"]
        it = dst.objects[0]; it.name = "raw_iron_soltado"; bpy.data.collections["cueva_bloques"].objects.link(it)
        if rec: rec.objects.link(it)
    if it.animation_data: it.animation_data_clear()
    it.parent = None; it.rotation_mode = 'XYZ'
    dims = max(it.dimensions) / max(it.scale) if max(it.scale) > 0 else 1.0
    s_it = TAM_ITEM / dims if dims > 0 else 1.0
    z_suelo = -12.0 + TAM_ITEM * 0.5 + 0.08
    p = centro.copy(); v = Vector((0.25, -0.25, 3.2)) / 24; z = p.z; vz = v.z; xy = p.to_2d(); vxy = v.to_2d(); rebotes = 0
    for k in range(0, F_FIN - F_ROMPE + 1):
        f = F_ROMPE + k
        if rebotes < 2:
            z += vz; vz -= g; xy += vxy
            if z <= z_suelo: z = z_suelo; vz = -vz * 0.35; vxy *= 0.5; rebotes += 1
        else:
            z = z_suelo + 0.06 * math.sin(2 * math.pi * k / 48.0)          # flota subiendo y bajando
        it.location = (xy.x, xy.y, z); it.rotation_euler = (0, 0, 2 * math.pi * k / 72.0); it.scale = (s_it,) * 3
        for dp in ("location", "rotation_euler", "scale"): it.keyframe_insert(dp, frame=f)
    for f, hv in ((1, True), (F_ROMPE, False)):
        it.hide_viewport = hv; it.hide_render = hv
        it.keyframe_insert("hide_viewport", frame=f); it.keyframe_insert("hide_render", frame=f)
    for o in [it, veta] + [obj["trozo_hierro_%02d" % i] for i in range(N_TROZOS)]:
        for lay in o.animation_data.action.layers:
            for s in lay.strips:
                for cb in s.channelbags:
                    for fc in cb.fcurves:
                        if fc.data_path.startswith("hide"):
                            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
    sc.frame_start, sc.frame_end = 1, F_FIN
    sonidos()
    sc.frame_set(GOLPES[0])
    return {"golpes": GOLPES, "rompe": F_ROMPE, "fin": F_FIN}


def sonidos():
    import importlib.util, sys
    m = sys.modules.get("alfred_sonidos_local")
    if m is None:
        spec = importlib.util.spec_from_file_location("alfred_sonidos_local", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py")
        m = importlib.util.module_from_spec(spec); sys.modules["alfred_sonidos_local"] = m; spec.loader.exec_module(m); m.register()
    sc = bpy.context.scene; p = sc.mcsnd; m.indice(p, forzar=True); ed = sc.sequence_editor or sc.sequence_editor_create()
    for t in [t for t in m._strips(ed) if t.name.startswith(m.PREFIJO) and t.get("mcsnd_origen") == ORIGEN]: m._strips(ed).remove(t)
    rng = m.rng_de(p)
    def poner(ev, f, vol, grupo):
        r = m.rutas_de(p, ev)
        if not r: print("sin sonido:", ev); return
        t = m.colocar(bpy.context, p, r, int(f), grupo, ev.replace(".", "_"), vol, 0, rng)
        if t: t["mcsnd_origen"] = ORIGEN
    for g in GOLPES:
        poner("entity.player.attack.nodamage" if m.rutas_de(p, "entity.player.attack.nodamage") else "entity.player.attack.weak", g - 4, 0.45, "golpes")   # el pico corta el aire
    for g in GOLPES[:-1]: poner("block.stone.hit", g, 0.8, "golpes")
    poner("block.stone.break", F_ROMPE, 1.0, "golpes")
    for k in (6, 9, 13): poner("block.stone.step", F_ROMPE + k, 0.3, "pasos")          # trocitos que caen
    it = bpy.data.objects.get("raw_iron_soltado")                                     # rebotes del hierro en bruto
    if it and it.animation_data and it.animation_data.action:
        zs = {}
        for lay in it.animation_data.action.layers:
            for s in lay.strips:
                for cb in s.channelbags:
                    for fc in cb.fcurves:
                        if fc.data_path == "location" and fc.array_index == 2: zs = {int(kp.co[0]): kp.co[1] for kp in fc.keyframe_points}
        fr = sorted(zs)
        for a, b, c in zip(fr, fr[1:], fr[2:]):
            if F_ROMPE < b < F_ROMPE + 30 and zs[b] < zs[a] and zs[b] <= zs[c] and zs[b] < min(zs.values()) + 0.02:
                poner("block.stone.hit", b, 0.35, "golpes")
