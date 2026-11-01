# -*- coding: utf-8 -*-
"""
objetos_mundo.py -- Jerry Animation Studio: OBJETOS y MUNDO del guion 2.0 (fase 3 del plan `docs/PLAN_PARTE3_AL_FLUJO.md`).

Lee las secciones `objetos` y `mundo` del guion (`guion_v2.py`) y anima los objetos de la escena por FRAME segun una linea de tiempo de eventos, sin keyframes escritos a mano: el guion guarda la receta y esto la hornea.

OBJETO (seccion `objetos`)
  {id, nombre, armature, hueso, escala_mano, escala_espalda,
   inicial:  {loc, rot|quat, escala, visible}           estado antes del primer evento (si falta: el que tiene el objeto en el frame 1)
   agarres:  {nombre: {matriz: [16]}                    matriz del objeto RELATIVA al hueso de la mano (se captura de una posicion de mundo: `capturar_agarre` / `agarre_desde_mundo`)
                    | {mezcla: {a, b, segun: {hueso, eje, de, a}}}}      mezcla de dos agarres segun un angulo de un hueso (ej. el codo: brazo en alto -> impacto)
   espalda:  {hueso, matriz: [16]}                      su sitio en la espalda, relativo a un hueso (`capturar_espalda`)
   eventos:  [{tipo, t, ...}]}
  TIPOS DE EVENTO (t = frame de inicio; todos los frames ya resueltos por `guion_v2.desplegar`)
   aparece   {en: {loc, rot, escala}, pop: {curva: elastica|suave, dur}}      el objeto sale de la nada en un sitio (escala 0 -> escala)
   toma      {hasta, agarre}        pasa de donde esta (espalda, mesa, suelo...) a la mano en t..hasta (suavizado) y la sigue
   mantiene  {agarre, mezcla}       cambia de agarre (en `mezcla` frames) sin soltarlo
   guarda    {hasta}                de la mano a su sitio de la espalda en t..hasta (escala mano -> espalda) y se queda pegado al hueso
   lanza | rebota | cae_sobre
             {vuelo, a: {loc, rot|quat, escala}, giro: {eje, de, a}, arco: {g | altura}}   vuelo de `vuelo` frames desde donde esta hasta `a` (parabola del CENTRO del objeto, como en el juego); `rebota`
                    es otro tramo seguido (contra un muro); `cae_sobre` ademas deja el objeto PEGADO al hueso de otro personaje:
                    {sobre: {armature, hueso, reposo: {loc, rot|quat, escala}}} (el reposo es su transformacion de mundo al caer; se calcula el agarre al hueso en ese frame)
   absorbe   {hasta, hacia: {armature, hueso}}      el objeto vuela hacia el pecho encogiendose (t..hasta) y se oculta
   en_mano   {agarre, pop: {dur, escala}}           el objeto sale en la mano (escala 0 -> `escala` en `dur` frames) y la sigue (sacado del inventario)
   asienta   {dur, vivo, en: {loc, rot|quat, escala}, squash: {desde, amp, tau, periodo, dur}}      desde donde esta en `t` (congelado) hasta `en` en `dur` frames (suave); `squash` = rebote corto de la escala al asentarse
   encoge    {dur}                                  la escala va a 0 en `dur` frames desde t (desaparece)
   bezier    {hasta, puntos: [P0, PC, H], rot0: [x, y, z], escala}      curva cuadratica de P0 a H pasando cerca de PC: el giro `rot0` se deshace y la escala crece (u^3) hasta `escala`
   En lanza | rebota | cae_sobre: `a.centro` = punto de llegada del CENTRO del objeto (en vez de `loc`, el origen); `arco.ref: "origen"` = el arco se calcula con el origen; `giro.curva: "suave"` = el giro sigue ss(u);
   el estado final incluye el giro final (`giro.a`).
   oculta | muestra                                   visibilidad desde t
MUNDO (seccion `mundo`)
   ocultar / mostrar {objeto | objetos | coleccion, t}            visibilidad (constante)
   luz               {objeto, energia, claves: [[t, factor]]}     la energia de todas las luces del objeto (y sus hijos) = energia x factor en cada clave (la luz de la antorcha solo existe desde que se saca)
   crear_pozo        {objeto: pozo, tapa, t}                      se quita la tapa de pasto en t (el pozo ya esta debajo; `preparar_pozo` lo crea si falta)
   aparecer_item     {objeto, t, en: [x, y, z] (centro), escala, sube, sube_dur, bob, bob_f, giro_vueltas_30f, absorbe_en, absorbe_dur, absorbido_por: {armature, hueso}, copia_de | fuente_blend+fuente_objeto}
                     el bloque roto sale como item pequeno: flota, gira, y es absorbido por el personaje (mecanica de Minecraft)
   mover             {objeto, t, hasta, destino: [x, y, z]}
Todo se calcula en memoria (`calcular`) y se compara con lo que hay en la escena (`comparar`) antes de hornear (`aplicar`).
"""
import math
import os

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

try:
    from . import guion_v2 as gv
except Exception:                                                                      # exec por ruta (pruebas)
    import importlib.util as _ilu
    import os as _os
    _sp = _ilu.spec_from_file_location("guion_v2", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "guion_v2.py")); gv = _ilu.module_from_spec(_sp); _sp.loader.exec_module(gv)

G = 9.8
FPS = 24.0


def _ruta_blend_portable(ruta):
    """Resuelve un asset del guion relativo a la raiz Alfred_Animacion."""
    if not ruta:
        return ""
    if os.path.isabs(ruta):
        return os.path.normpath(ruta)
    raices = [os.environ.get("ALFRED_RAIZ", r"C:\Users\user\Desktop\Alfred_Animacion")]
    if bpy.data.filepath:
        actual = os.path.dirname(os.path.abspath(bpy.data.filepath))
        while actual and os.path.dirname(actual) != actual:
            if os.path.basename(actual).lower() == "alfred_animacion":
                raices.append(actual)
                break
            actual = os.path.dirname(actual)
    raices.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
    for raiz in raices:
        candidata = os.path.normpath(os.path.join(raiz, ruta))
        if os.path.isfile(candidata):
            return candidata
    return os.path.normpath(os.path.join(raices[0], ruta))


def _asegurar_objeto_portable(cfg):
    """Importa la jerarquia declarada por un objeto de guion si aun no existe.

    Campos opcionales del JSON:
      blend / fuente_blend: .blend absoluto o relativo a Alfred_Animacion
      fuente_objeto: nombre del objeto raiz dentro del .blend
      fuente_extra: objetos adicionales de la jerarquia (luces, llamas, humo...)

    Esto permite que una configuracion de guion se reproduzca en un .blend
    limpio sin exigir que el prop ya haya sido importado manualmente.
    """
    nombre = cfg.get("nombre")
    if nombre and bpy.data.objects.get(nombre) is not None:
        return bpy.data.objects[nombre]
    ruta = _ruta_blend_portable(cfg.get("blend") or cfg.get("fuente_blend"))
    if not ruta:
        return None
    if not os.path.isfile(ruta):
        raise FileNotFoundError("%s: no existe el asset portable %r" % (nombre, ruta))
    raiz_fuente = cfg.get("fuente_objeto") or nombre
    pedidos = []
    for n in [raiz_fuente] + list(cfg.get("fuente_extra") or []):
        if n and n not in pedidos:
            pedidos.append(n)
    with bpy.data.libraries.load(ruta, link=False) as (src, dst):
        faltan = [n for n in pedidos if n not in src.objects]
        if faltan:
            raise KeyError("%s: objetos ausentes en %s: %s" % (nombre, ruta, ", ".join(faltan)))
        dst.objects = pedidos
    coleccion = getattr(bpy.context, "collection", None)
    if coleccion is None:
        coleccion = bpy.context.scene.collection
    for ob in dst.objects:
        if ob is not None and not ob.users_collection:
            coleccion.objects.link(ob)
    raiz = bpy.data.objects.get(raiz_fuente)
    if raiz is None:
        raise RuntimeError("%s: no se pudo importar el objeto raiz %r" % (nombre, raiz_fuente))
    if nombre and raiz.name != nombre and bpy.data.objects.get(nombre) is None:
        raiz.name = nombre
    print("[objetos_mundo] asset portable importado: %s (%d objetos)" % (ruta, len([o for o in dst.objects if o])))
    return raiz


def asegurar_portables_al_cargar(data):
    """Importa de inmediato los assets portatiles declarados por un JSON.

    La carga de una configuracion debe dejar visibles sus props aun antes de
    pulsar Concatenar. Las acciones incluidas en el .blend portable conservan
    ademas la transicion original mientras el horneado del guion se ejecuta.
    """
    importados = []
    for cfg in data.get("objetos") or []:
        nombre = cfg.get("nombre")
        if nombre and bpy.data.objects.get(nombre) is None and (cfg.get("blend") or cfg.get("fuente_blend")):
            _asegurar_objeto_portable(cfg)
            importados.append(nombre)
    for cfg in data.get("mundo") or []:
        nombre = cfg.get("objeto")
        if nombre and bpy.data.objects.get(nombre) is None and cfg.get("fuente_blend"):
            _asegurar_objeto_portable({
                "nombre": nombre,
                "blend": cfg.get("fuente_blend"),
                "fuente_objeto": cfg.get("fuente_objeto") or nombre,
                "fuente_extra": cfg.get("fuente_extra") or [],
            })
            importados.append(nombre)
    return importados


def ss(t):
    t = min(max(t, 0.0), 1.0); return t * t * (3 - 2 * t)


def ela(u):
    """Elastic In-Out (la misma formula que el add-on y la parte 2)."""
    if u <= 0.0: return 0.0
    if u >= 1.0: return 1.0
    c5 = 2 * math.pi / 4.5
    if u < 0.5: return -(2 ** (20 * u - 10) * math.sin((20 * u - 11.125) * c5)) / 2
    return (2 ** (-20 * u + 10) * math.sin((20 * u - 11.125) * c5)) / 2 + 1


def M16(l):
    return Matrix([list(l[i:i + 4]) for i in range(0, 16, 4)])


def mat16(M):
    return [round(float(M[i][j]), 6) for i in range(4) for j in range(4)]


def quat_de(d):
    """{rot: [x, y, z] grados | quat: [w, x, y, z]} -> Quaternion."""
    if d is None: return Quaternion((1, 0, 0, 0))
    if "quat" in d: return Quaternion(d["quat"]).normalized()
    return Euler([math.radians(a) for a in d.get("rot", (0, 0, 0))], 'XYZ').to_quaternion()


class Est:
    """estado de un objeto en un frame: origen, rotacion, escala uniforme, visible."""
    __slots__ = ("loc", "q", "e", "vis")

    def __init__(self, loc, q, e, vis=True):
        self.loc = Vector(loc); self.q = Quaternion(q).normalized(); self.e = float(e); self.vis = vis

    def copia(self, **kw):
        n = Est(self.loc, self.q, self.e, self.vis)
        for k, v in kw.items(): setattr(n, k, v)
        return n


def mezcla(a, b, u):
    q1 = b.q.copy()
    if a.q.dot(q1) < 0: q1.negate()
    return Est(a.loc.lerp(b.loc, u), a.q.slerp(q1, u).normalized(), a.e + (b.e - a.e) * u, b.vis)


def est_de_matriz(M, e, vis=True):
    return Est(M.to_translation(), M.to_quaternion().normalized(), e, vis)


def mat_de_est(s):
    return Matrix.LocRotScale(s.loc, s.q, Vector((1, 1, 1)))


# ------------------------------------------------------------------------------------------------------------------------------------------- rig / muestras
def rig(nombre, hueso=None):
    """objeto armature por nombre; si no existe (los rigs a veces se renombran) el que tenga ese hueso."""
    o = bpy.data.objects.get(nombre) if nombre else None
    if o is not None and o.type == 'ARMATURE' and (hueso is None or hueso in o.pose.bones): return o
    for o in bpy.data.objects:
        if o.type == 'ARMATURE' and hueso and hueso in o.pose.bones: return o
    raise KeyError("no encuentro la armature %r (hueso %r)" % (nombre, hueso))


def hueso_M(a, b):
    ob = rig(a, b); return ob.matrix_world @ ob.pose.bones[b].matrix


def capturar_agarre(obj, armature, hueso):
    """agarre = matriz del objeto RELATIVA al hueso, en el frame actual (se coloca el objeto a mano, se captura)."""
    return mat16(hueso_M(armature, hueso).inverted() @ obj.matrix_world.normalized())             # sin la escala del objeto: la escala va aparte (escala_mano / escala_espalda)


def agarre_desde_mundo(armature, hueso, frame, loc, rot=None, quat=None):
    """agarre a partir de una transformacion de MUNDO (valores de Blender dados por el usuario) y del frame en que se dio: relativo al hueso en ese frame."""
    sc = bpy.context.scene; f0 = sc.frame_current
    try: sc.frame_set(int(frame)); bpy.context.view_layer.update(); Mh = hueso_M(armature, hueso)
    finally: sc.frame_set(f0)
    return mat16(Mh.inverted() @ Matrix.LocRotScale(Vector(loc), quat_de({"rot": rot} if quat is None else {"quat": quat}), Vector((1, 1, 1))))


def capturar_espalda(obj, hueso="spine_3", armature="Dog_001_rig", frame=1):
    """su sitio en la espalda: matriz del objeto relativa al hueso en `frame` (el objeto debe estar colocado en ese frame)."""
    sc = bpy.context.scene; f0 = sc.frame_current
    try: sc.frame_set(int(frame)); bpy.context.view_layer.update(); return {"hueso": hueso, "matriz": mat16(hueso_M(armature, hueso).inverted() @ obj.matrix_world.normalized())}
    finally: sc.frame_set(f0)


class Muestras:
    """matrices de huesos (y rotaciones de algunos) en cada frame, evaluadas una sola vez (frame_set), y el estado VIVO de objetos de la escena (para comparar)."""

    def __init__(self, context, frames, huesos, rots=(), vivos=()):
        self.sc = context.scene; self.frames = sorted(set(int(f) for f in frames)); self.huesos = set(huesos); self.rots = set(rots); self.vivos = list(vivos); self.M = {}; self.R = {}; self.V = {}

    def _uno(self, k):
        self.sc.frame_set(k); bpy.context.view_layer.update()
        self.M[k] = {(a, b): hueso_M(a, b) for a, b in self.huesos}
        self.R[k] = {(a, b, ax): math.degrees(rig(a, b).pose.bones[b].rotation_euler[ax]) for a, b, ax in self.rots}
        self.V[k] = {}
        for n in self.vivos:
            o = bpy.data.objects[n]; mw = o.matrix_world; self.V[k][n] = Est(mw.to_translation(), mw.to_quaternion(), mw.to_scale().x, not (o.hide_viewport or o.hide_get()))

    def llenar(self):
        f0 = self.sc.frame_current
        try:
            for k in self.frames: self._uno(k)
        finally: self.sc.frame_set(f0)
        return self

    def _asegurar(self, k):
        """muestra bajo demanda un frame que no estaba en la lista (un evento puede pedir el hueso en el frame en que empieza)."""
        if k not in self.M:
            f0 = self.sc.frame_current
            try: self._uno(k)
            finally: self.sc.frame_set(f0)

    def mat(self, k, a, b):
        self._asegurar(k); d = self.M.get(k)
        if d is None or (a, b) not in d: raise KeyError("sin muestra del hueso %s/%s en f%s" % (a, b, k))
        return d[(a, b)]

    def rot(self, k, a, b, ax):
        self._asegurar(k); return self.R[k][(a, b, ax)]


def centro_local(ob):
    """centro del bbox del objeto en coordenadas locales (el vuelo se calcula sobre el CENTRO, como en el juego)."""
    return sum((Vector(c) for c in ob.bound_box), Vector()) / 8.0 if ob is not None and ob.type == 'MESH' else Vector((0, 0, 0))


# ------------------------------------------------------------------------------------------------------------------------------------------- motor de un objeto
class Motor:
    def __init__(self, cfg, mu, ob=None, vivo1=None):
        self.cfg = cfg; self.mu = mu; self.ob = ob; self.arm = cfg.get("armature", "Dog_001_rig"); self.hueso = cfg.get("hueso", "front_foot.R"); self.cl = centro_local(ob)
        self.e_mano = float(cfg.get("escala_mano", 1.0)); self.e_esp = float(cfg.get("escala_espalda", self.e_mano))
        ini = cfg.get("inicial")
        if ini: self.s0 = Est(ini.get("loc", (0, 0, 0)), quat_de(ini), ini.get("escala", self.e_mano), ini.get("visible", True))
        elif vivo1 is not None: self.s0 = vivo1.copia()
        else: raise ValueError("%s: falta `inicial` (y no hay estado vivo)" % cfg.get("nombre"))

    def mano_M(self, k, nombre):
        ag = (self.cfg.get("agarres") or {}).get(nombre)
        if ag is None: raise KeyError("%s: agarre %r no definido" % (self.cfg.get("nombre"), nombre))
        if "matriz" in ag: return self.mu.mat(k, self.arm, self.hueso) @ M16(ag["matriz"])
        if "de_espalda_en" in ag:                                                         # agarre = lo que hace falta para que en ese frame la mano tenga el objeto EXACTAMENTE donde esta en la espalda (sin salto)
            f = int(ag["de_espalda_en"]); rel = self.mu.mat(f, self.arm, self.hueso).inverted() @ self.espalda_M(f); return self.mu.mat(k, self.arm, self.hueso) @ rel
        m = ag["mezcla"]; sg = m["segun"]; v = self.mu.rot(k, sg.get("armature", self.arm), sg["hueso"], sg.get("eje", 0)); gs = min(max((v - sg["de"]) / float(sg["a"] - sg["de"]), 0.0), 1.0)
        A, B = self.mano_M(k, m["a"]), self.mano_M(k, m["b"]); sa, sb = est_de_matriz(A, 1.0), est_de_matriz(B, 1.0); s = mezcla(sa, sb, gs); return mat_de_est(s)

    def espalda_M(self, k):
        esp = self.cfg.get("espalda")
        if not esp: raise KeyError("%s: falta `espalda`" % self.cfg.get("nombre"))
        return self.mu.mat(k, esp.get("armature", self.arm), esp["hueso"]) @ M16(esp["matriz"])

    def construir(self):
        evs = sorted(self.cfg.get("eventos") or [], key=lambda e: e["t"]); prev = (lambda k: self.s0.copia())
        if evs and evs[0]["tipo"] == "aparece": self.s0.vis = False
        for ev in evs: prev = self._evento(ev, prev)
        self.fn = prev; self.t0 = evs[0]["t"] if evs else 1
        return self

    # un evento = una funcion k -> Est que continua a la anterior (`prev`)
    def _evento(self, ev, prev):
        t = int(ev["t"]); tipo = ev["tipo"]; cfg = self.cfg
        if tipo == "aparece":
            en = ev.get("en") or {}; q = quat_de(en); loc = Vector(en.get("loc", self.s0.loc)); e = float(en.get("escala", self.e_mano)); pop = ev.get("pop") or {"curva": "suave", "dur": 3}; d = float(pop.get("dur", 3))

            def f(k):
                if k < t: return prev(k)
                u = (k - t) / d
                return Est(loc, q, max(0.001, e * (ela(u) if pop.get("curva") == "elastica" else ss(u))) if k > t else 0.001, True)
            return f
        if tipo == "coloca":                                                                 # lo pone en un sitio absoluto (puente mientras el tramo que lo mueve no esta migrado)
            en = ev["en"]; q = quat_de(en); loc = Vector(en["loc"]); e = float(en.get("escala", self.e_mano))

            def f(k):
                p = prev(k)
                return p if k < t else Est(loc, q, e, en.get("visible", True))
            return f
        if tipo in ("toma", "mantiene", "guarda"):
            hasta = int(ev.get("hasta", t)); dur = float(max(1, (hasta - t) if tipo != "mantiene" else ev.get("mezcla", 0)))
            if tipo == "mantiene" and not ev.get("mezcla"): dur = 0
            ag = ev.get("agarre"); e_dest = float(ev.get("escala", self.e_esp)) if tipo == "guarda" else float(ev.get("escala", self.e_mano))

            def f(k):
                p = prev(k)
                if k < t: return p
                u = ss((k - t) / dur) if dur else 1.0
                dest = est_de_matriz(self.espalda_M(k) if tipo == "guarda" else self.mano_M(k, ag), e_dest)
                return mezcla(p, dest, u)
            return f
        if tipo in ("lanza", "rebota", "cae_sobre"):
            T = float(ev["vuelo"]); S0 = prev(t)
            if tipo == "cae_sobre":
                so = ev["sobre"]; rep = so["reposo"]; a_, b_ = so.get("armature", "Dog_001_rig"), so["hueso"]
            else: rep = ev["a"]
            gi = ev.get("giro"); eje = Vector(gi.get("eje", (0, 1, 0))).normalized() if gi else None
            arco = ev.get("arco") or {"g": G}; cl = Vector((0, 0, 0)) if arco.get("ref") == "origen" else self.cl
            q1 = quat_de(rep); e1 = float(rep.get("escala", S0.e)); tl = t + int(T); qfin = (Quaternion(eje, math.radians(gi.get("a", 0))) @ q1) if gi else q1          # el giro termina en `giro.a`

            def centro(loc, q, e): return loc + q.to_matrix() @ (cl * e)
            if "centro" in rep: c1 = Vector(rep["centro"]); l1 = c1 - qfin.to_matrix() @ (cl * e1)
            else: l1 = Vector(rep["loc"]); c1 = centro(l1, qfin, e1)
            c0 = centro(S0.loc, S0.q, S0.e); TT = T / FPS; vz = (c1.z - c0.z + 0.5 * arco.get("g", G) * TT * TT) / TT if "altura" not in arco else 0.0
            rel = None
            if tipo == "cae_sobre": rel = self.mu.mat(tl, a_, b_).inverted() @ Matrix.LocRotScale(l1, qfin, Vector((1, 1, 1)))

            def f(k):
                if k < t: return prev(k)
                if k >= tl:
                    if rel is not None:
                        M = self.mu.mat(k, a_, b_) @ rel; return est_de_matriz(M, e1)
                    return Est(l1, qfin, e1, True)
                u = (k - t) / T; tt = u * TT; c = c0.lerp(c1, u)
                c.z = c0.z + (c1.z - c0.z) * u + 4 * arco["altura"] * u * (1 - u) if "altura" in arco else c0.z + vz * tt - 0.5 * arco.get("g", G) * tt * tt
                qb = S0.q.slerp(q1 if S0.q.dot(q1) >= 0 else -q1, ss(u))
                if gi:
                    ug = ss(u) if gi.get("curva") == "suave" else u; q = Quaternion(eje, math.radians(gi.get("de", 0) + (gi.get("a", 0) - gi.get("de", 0)) * ug)) @ qb
                else: q = qb
                e = S0.e + (e1 - S0.e) * u
                return Est(c - q.to_matrix() @ (cl * e), q, e, True)
            return f
        if tipo == "en_mano":
            ag = ev["agarre"]; pop = ev.get("pop") or {}; d = float(pop.get("dur", 3)); es = float(pop.get("escala", self.e_mano))

            def f(k):
                if k < t: return prev(k)
                return est_de_matriz(self.mano_M(k, ag), max(0.001, ss((k - t) / d)) * es)
            return f
        if tipo == "asienta":
            en = ev["en"]; dur = float(ev.get("dur", 4)); dest = Est(en["loc"], quat_de(en), en.get("escala", self.e_mano), True); sq = ev.get("squash"); cache = {}

            def f(k):
                if k < t: return prev(k)
                if not ev.get("vivo") and "p0" not in cache: cache["p0"] = prev(t)
                s_ = mezcla(prev(k) if ev.get("vivo") else cache["p0"], dest, ss((k - t) / dur))             # `vivo`: parte de lo que hace el evento anterior en CADA frame (la mano sigue moviendose); si no, de lo congelado en t
                if sq:
                    d = k - (t + int(dur)) - int(sq.get("desde", 0))
                    if 0 <= d < sq.get("dur", 8): s_ = s_.copia(e=s_.e * (1.0 - math.exp(-d / sq.get("tau", 2.0)) * math.sin(math.pi * d / sq.get("periodo", 3.0)) * sq.get("amp", 0.04)))
                return s_
            return f
        if tipo == "encoge":
            dur = float(ev.get("dur", 2))

            def f(k):
                p = prev(k)
                return p if k <= t else p.copia(e=max(0.001, p.e * (1 - ss((k - t) / dur))))
            return f
        if tipo == "bezier":
            hasta = int(ev["hasta"]); P0, PC, H = [Vector(v) for v in ev["puntos"]]; r0 = [math.radians(a) for a in ev.get("rot0", (0, 0, 0))]; es = float(ev.get("escala", self.e_mano))

            def f(k):
                if k < t: return prev(k)
                if k >= hasta: return Est(H, Quaternion((1, 0, 0, 0)), es, True)
                u = (k - t) / float(hasta - t); e = ss(u); a = P0 * (1 - e) ** 2 + PC * 2 * e * (1 - e) + H * e * e
                return Est(a, Euler([x * (1 - e) for x in r0], 'XYZ').to_quaternion(), max(0.001, u ** 3 * es), True)
            return f
        if tipo == "absorbe":
            hasta = int(ev["hasta"]); hz = ev["hacia"]; D = float(max(1, hasta - t)); cl = self.cl

            def f(k):
                p = prev(k)
                if k < t: return p
                a = ss((k - t) / D); c = p.loc + p.q.to_matrix() @ (cl * p.e); tg = self.mu.mat(k, hz.get("armature", "Dog_001_rig"), hz["hueso"]).to_translation()
                e = p.e * (1 - a); cn = c.lerp(tg, a); return Est(cn - p.q.to_matrix() @ (cl * e), p.q, e, k < hasta)
            return f
        if tipo in ("oculta", "muestra"):
            vis = tipo == "muestra"

            def f(k):
                p = prev(k); return p.copia(vis=vis) if k >= t else p
            return f
        raise ValueError("evento desconocido: %r" % tipo)

    def estado(self, k):
        return self.fn(k)


# ------------------------------------------------------------------------------------------------------------------------------------------- mundo: items que salen de un bloque
def estado_item(a, mu, k, cl=None):
    """`mundo.aparecer_item` en el frame k (formulas de la parte 3): -> (loc, euler z, escala, visible-por-escala)."""
    t = int(a["t"]); u = k - t; en = Vector(a["en"]); e = float(a.get("escala", 0.25)); sube = float(a.get("sube", 0.3)); sd = float(a.get("sube_dur", 8)); bob = float(a.get("bob", 0.03)); bf = float(a.get("bob_f", 0.45))
    abs_t = int(a["absorbe_en"]); abs_d = float(a.get("absorbe_dur", 8)); vis = t <= k < abs_t + abs_d; sc = e * ss(u / 3.0)
    c = Vector((en.x, en.y, en.z + sube * ss(u / sd) + bob * math.sin(max(0, u - sd) * bf)))
    if k >= abs_t:
        ar = a["absorbido_por"]; al = ss((k - abs_t) / abs_d); c = c.lerp(mu.mat(k, ar.get("armature", "Dog_001_rig"), ar["hueso"]).to_translation(), al); sc *= (1 - al)
    if not vis: return Vector((en.x, en.y, en.z - 0.1)), 0.0, 0.001, False
    return c - Vector((0, 0, sc * 0.5)), 2 * math.pi * float(a.get("giro_vueltas_30f", 2)) * max(0, u) / 30.0, max(0.001, sc), True


# ------------------------------------------------------------------------------------------------------------------------------------------- calcular / comparar / aplicar
def _huesos_necesarios(d):
    hs, rs = set(), set()
    for o in d.get("objetos") or []:
        a = o.get("armature", "Dog_001_rig"); hs.add((a, o.get("hueso", "front_foot.R")))
        if o.get("espalda"): hs.add((o["espalda"].get("armature", "Dog_001_rig"), o["espalda"]["hueso"]))
        for g in (o.get("agarres") or {}).values():
            if "mezcla" in g: sg = g["mezcla"]["segun"]; rs.add((sg.get("armature", a), sg["hueso"], sg.get("eje", 0)))
        for e in o.get("eventos") or []:
            for k in ("hacia",):
                if k in e: hs.add((e[k].get("armature", "Dog_001_rig"), e[k]["hueso"]))
            if "sobre" in e: hs.add((e["sobre"].get("armature", "Dog_001_rig"), e["sobre"]["hueso"]))
    for m in d.get("mundo") or []:
        if m.get("accion") == "aparecer_item": hs.add((m["absorbido_por"].get("armature", "Dog_001_rig"), m["absorbido_por"]["hueso"]))
    return hs, rs


def _frames_objeto(o, N):
    ts = [e["t"] for e in o.get("eventos") or []]
    return range(max(1, min(ts) - 3) if ts else 1, N + 1)


def calcular(context, data, objetos=None, frames=None, vivos=(), N=None):
    """-> {"objetos": {nombre: {k: Est}}, "items": {nombre: {k: (loc, rotz, escala, vis)}}, "visib": {nombre: {k: bool}}, "vivos": {k: {nombre: Est}}}. No toca la escena (salvo evaluar frames)."""
    d = gv.desplegar(gv.migrar(data)); N = N or int((d.get("meta") or {}).get("frame_fin") or context.scene.frame_end)
    obs = [o for o in d.get("objetos") or [] if objetos is None or o["nombre"] in objetos]; mun = [m for m in d.get("mundo") or [] if m.get("accion") == "aparecer_item" and (objetos is None or m["objeto"] in objetos)]
    for o in obs:
        if bpy.data.objects.get(o["nombre"]) is None:
            _asegurar_objeto_portable(o)
    # Cualquier objeto de mundo puede viajar dentro de un asset portable. Esto
    # incluye no solo `aparecer_item`, sino bloques usados por `ocultar` o
    # `mostrar`, que deben existir antes de aplicar su visibilidad.
    for m in d.get("mundo") or []:
        nombre = m.get("objeto")
        if nombre and bpy.data.objects.get(nombre) is None and m.get("fuente_blend"):
            _asegurar_objeto_portable({
                "nombre": nombre,
                "blend": m.get("fuente_blend"),
                "fuente_objeto": m.get("fuente_objeto") or nombre,
                "fuente_extra": m.get("fuente_extra") or [],
            })
    hs, rs = _huesos_necesarios({"objetos": obs, "mundo": mun}); fr = set()
    for o in obs: fr |= set(_frames_objeto(o, N)) | {1} | {int(g["de_espalda_en"]) for g in (o.get("agarres") or {}).values() if "de_espalda_en" in g}                                      # f1 = estado inicial: sin esta clave un objeto recien importado se queda donde llego del .blend hasta su primer evento
    for m in mun: fr |= {1} | set(range(max(1, m["t"] - 3), N + 1))
    if frames is not None: fr = set(frames)
    vv = set(vivos) | {o["nombre"] for o in obs} | {m["objeto"] for m in mun}
    mu = Muestras(context, fr | {1}, hs, rs, vv).llenar(); res = {"objetos": {}, "items": {}, "vivos": mu.V, "muestras": mu}
    for o in obs:
        ob = bpy.data.objects.get(o["nombre"]); mo = Motor(o, mu, ob, mu.V[1].get(o["nombre"]) if 1 in mu.V else None).construir()
        t0 = min(e["t"] for e in o["eventos"]) - 3 if o.get("eventos") else 1
        res["objetos"][o["nombre"]] = {k: mo.estado(k) for k in sorted(fr) if k >= t0 or k == 1}
    for m in mun: res["items"][m["objeto"]] = {k: estado_item(m, mu, k) for k in sorted(fr) if k >= m["t"] - 3 or k == 1}
    return res


def comparar(res, tol_cm=2.0, tol_deg=2.0, rangos=None):
    """compara lo calculado con el estado vivo de la escena: -> {nombre: {"loc_cm", "ang_deg", "escala", "vis_distintos", "n", "peor_frame"}}."""
    out = {}
    for n, est in res["objetos"].items():
        pl = pa = pe = 0.0; nv = 0; peor = None; cnt = 0
        for k, s in est.items():
            v = res["vivos"].get(k, {}).get(n)
            if v is None or (rangos and n in rangos and not (rangos[n][0] <= k <= rangos[n][1])): continue
            cnt += 1; dl = (s.loc - v.loc).length * 100.0; da = math.degrees(2 * math.acos(min(1.0, abs(s.q.dot(v.q)))))
            if s.e > 0.002 or v.e > 0.002:
                pe = max(pe, abs(s.e - v.e))
                if dl > pl: pl, peor = dl, k
                pa = max(pa, da)
            if s.vis != v.vis and v.e > 0.002: nv += 1
        out[n] = {"loc_cm": round(pl, 3), "ang_deg": round(pa, 3), "escala": round(pe, 4), "vis_distintos": nv, "n": cnt, "peor_frame": peor, "ok": pl <= tol_cm and pa <= tol_deg and nv == 0}
    for n, est in res["items"].items():
        pl = pe = 0.0; cnt = 0
        for k, (loc, rz, sc, vis) in est.items():
            v = res["vivos"].get(k, {}).get(n)
            if v is None: continue
            if sc <= 0.002 and v.e <= 0.002: continue                          # oculto por escala en los dos: no importa donde este
            cnt += 1; pl = max(pl, (loc - v.loc).length * 100.0); pe = max(pe, abs(sc - v.e))
        out[n] = {"loc_cm": round(pl, 3), "escala": round(pe, 4), "n": cnt, "ok": pl <= tol_cm and pe < 0.01}
    return out


def aplicar_rango(context, res, f0, f1, objetos=None):
    """escribe SOLO los frames f0..f1 de lo calculado en la accion que cada objeto ya tiene (por la API de fcurves, sin tocar los demas frames): para migrar un tramo sin perder lo que el generador hizo despues.
    Los cuaterniones siguen el signo de la clave anterior (sin saltos de interpolacion). -> numero de objetos."""
    try: from .claves_util import escritor_de
    except Exception:
        import importlib.util as _u
        import os as _o
        sp = _u.spec_from_file_location("claves_util", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "claves_util.py")); cu = _u.module_from_spec(sp); sp.loader.exec_module(cu); escritor_de = cu.escritor_de
    n = 0
    for nombre, est in res["objetos"].items():
        if objetos and nombre not in objetos: continue
        ob = bpy.data.objects[nombre]; w = escritor_de(ob, "location", 0, f0); ks = [k for k in sorted(est) if f0 <= k <= f1]
        if not ks: continue
        prev = None
        if w.existe("rotation_quaternion", 0) and f0 > 1:                                          # signo de la clave anterior al rango
            w.aplicar(); prev = Quaternion([w.fc[("rotation_quaternion", i)].evaluate(f0 - 1) for i in range(4)])
        for k in ks:
            s_ = est[k]; q = s_.q.copy()
            if prev is not None and q.dot(prev) < 0: q.negate()
            prev = q
            for i in range(3): w.poner("location", i, k, s_.loc[i]); w.poner("scale", i, k, s_.e)
            for i in range(4): w.poner("rotation_quaternion", i, k, q[i])
        w.cerrar(); ad = ob.animation_data
        if ad and ad.nla_tracks: ad.use_nla = False; ad.use_nla = True
        ob.update_tag(); n += 1
    context.scene.frame_set(context.scene.frame_current); context.view_layer.update()
    return n


def aplicar(context, res, data=None):
    """hornea lo calculado: keyframes por frame de ubicacion, rotacion (cuaternion) y escala + claves de visibilidad. Devuelve cuantos objetos se animaron."""
    n_ob = 0
    for nombre, est in res["objetos"].items():
        ob = bpy.data.objects[nombre]
        if ob.animation_data: ob.animation_data_clear()
        ob.rotation_mode = 'QUATERNION'; prev = None; vis_prev = None
        for k in sorted(est):
            s = est[k]; q = s.q.copy()
            if prev is not None and q.dot(prev) < 0: q.negate()
            prev = q; ob.location = s.loc; ob.rotation_quaternion = q; ob.scale = (s.e, s.e, s.e)
            for dp in ("location", "rotation_quaternion", "scale"): ob.keyframe_insert(dp, frame=k)
            if s.vis != vis_prev:
                ob.hide_viewport = not s.vis; ob.hide_render = not s.vis; ob.keyframe_insert("hide_viewport", frame=k); ob.keyframe_insert("hide_render", frame=k); vis_prev = s.vis
        n_ob += 1
    for nombre, est in res["items"].items():
        ob = bpy.data.objects[nombre]
        if ob.animation_data: ob.animation_data_clear()
        ob.rotation_mode = 'XYZ'
        for k in sorted(est):
            loc, rz, sc, vis = est[k]; ob.location = loc; ob.rotation_euler = (0, 0, rz); ob.scale = (sc, sc, sc)
            for dp in ("location", "rotation_euler", "scale"): ob.keyframe_insert(dp, frame=k)
        n_ob += 1
    return n_ob


def aplicar_mundo_luces(context, data):
    """`mundo.luz`: claves de energia de las luces de un objeto (y sus hijos). -> nombres de las luces animadas."""
    d = gv.desplegar(gv.migrar(data)); hechas = []
    for m in d.get("mundo") or []:
        if m.get("accion") != "luz": continue
        raiz = bpy.data.objects[m["objeto"]]
        for o in [raiz] + list(raiz.children_recursive):
            if o.type != 'LIGHT': continue
            if o.data.animation_data: o.data.animation_data_clear()
            for f, fac in m["claves"]: o.data.energy = float(m["energia"]) * float(fac); o.data.keyframe_insert("energy", frame=int(f))
            hechas.append(o.name)
    return hechas


def aplicar_mundo_visibilidad(context, data):
    """`mundo.ocultar / mostrar / crear_pozo`: claves de visibilidad (constantes) de objetos o colecciones."""
    d = gv.desplegar(gv.migrar(data)); N = int((d.get("meta") or {}).get("frame_fin") or context.scene.frame_end); cambios = {}
    for m in sorted(d.get("mundo") or [], key=lambda m: m.get("t", 0)):
        ac = m.get("accion")
        if ac not in ("ocultar", "mostrar", "crear_pozo"): continue
        nombres = [m["tapa"]] if ac == "crear_pozo" else (m.get("objetos") or ([m["objeto"]] if m.get("objeto") else []))
        if m.get("coleccion"): nombres += [o.name for o in bpy.data.collections[m["coleccion"]].all_objects]
        for n in nombres: cambios.setdefault(n, []).append((int(m["t"]), ac != "mostrar"))
    for n, lst in cambios.items():
        ob = bpy.data.objects[n]
        if ob.animation_data: ob.animation_data_clear()
        oculto = not lst[0][1]; claves = [(1, oculto)]                      # antes de la primera accion esta como NO la deja la accion
        for t, nuevo in lst: claves += [(t - 1, oculto), (t, nuevo)]; oculto = nuevo
        claves.append((N, oculto))
        for f, h in claves:
            ob.hide_viewport = h; ob.hide_render = h; ob.keyframe_insert("hide_viewport", frame=f); ob.keyframe_insert("hide_render", frame=f)
    return sorted(cambios) + ["luz:" + n for n in aplicar_mundo_luces(context, data)]
