# -*- coding: utf-8 -*-
"""
tunel.py -- Cerdo_1 Animation Studio: TUNEL AUTOMATICO. Das la coordenada de INICIO y la FINAL y Cerdo_1 cava / pica un tunel recto entre las dos.

QUE HACE (todo automatico, repetible con `quitar`):
  1. RUTA: camino de celdas (bloques de 1 m, 4-conectado) de inicio a final; la raiz baja/sube en linea recta entre las dos z. El corredor mide `alto` bloques desde el piso.
  2. SOLIDEZ: con rayos decide que celdas del corredor son roca (el mundo son mallas por tipo de bloque con SOLO las caras expuestas) y cuales ya son aire / cueva (solo se camina).
  3. ANIMACION DE CERDO_1 con las poses portables que ya existen (`refinar/poses`): saca la pala de la espalda (`pala_pozo` f855-879), PALADA (ciclo f893-906, impacto cada 14 f) para tierra,
     y PICAR = la animacion de usar el hacha (`golpea_rompe_madera` ciclo f1026-1037, 12 f) con el PICO en lugar del hacha, para piedra; cada golpe rompe hasta 2 celdas y despues avanza 1 bloque.
     Una herramienta por paso (pico si hay piedra); guardar = brazo a la espalda (`pala_pozo` f945-959). Herramientas con `Child Of` Espalda / Mano (convencion del estudio).
  4. GEOMETRIA: romper un bloque = copiar sus caras expuestas a objetos `tunel_tapa_*` (visibles hasta el golpe) y BORRARLAS de la malla original; caras nuevas `tunel_cara_*` de los
     bloques vecinos (paredes, piso, techo; tierra o piedra) que aparecen en el golpe; y un CASCARON de tierra / piedra donde la cueva no tiene piso, paredes ni techo (aire) para que
     parezca cavado. El final (ultimas celdas) queda ABIERTO hacia la cueva (sin tapon). Todo con claves CONSTANT de `hide_viewport` / `hide_render` (coleccion `tunel`).
  5. GUION: anclas `tunel_inicio` / `tunel_fin` en el guion de la escena (si existe).
Pensado para el rig de Cerdo_1 (`armature` con `Body_cerdo_1`, raiz = su padre) y el mundo de Minecraft del proyecto. Sin dependencias fuera de bpy / mathutils / numpy.
"""
import json
import math
import os

import bpy
import bmesh
import numpy as np
from mathutils import Euler, Matrix, Vector

REFINAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))             # .../cerdo_1/refinar
if not os.path.isdir(os.path.join(REFINAR, "poses")):                                   # instalado en `scripts/addons`: se usa la ruta del proyecto (constants.py)
    try:
        from .constants import DEFAULT_POSES_DIR
        REFINAR = os.path.dirname(DEFAULT_POSES_DIR)
    except Exception: pass
COL = "tunel"
SUELA = 0.0145                                                                   # m que se sube la cadera (Hips loc Y) para que las suelas apoyen justo sobre el piso
DIRS = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
ss = lambda t: 0.0 if t <= 0 else (1.0 if t >= 1 else t * t * (3 - 2 * t))
PIEDRAS = {"Stone", "Andesite", "Coal_Ore", "Iron_Ore", "Copper_Ore", "Lapis_Lazuli_Ore", "Cobblestone", "Mossy_Cobblestone", "Diorite", "Granite", "Deepslate"}


# ============================================================================================================================ poses y agarres
class Biblioteca:
    """poses por frame de las animaciones portables que se reutilizan (se leen una vez)"""
    def __init__(self):
        def cargar(carpeta, pref, a, b):
            out = {}
            for f in range(a, b + 1):
                p = json.load(open(os.path.join(REFINAR, "poses", carpeta, "%s%d.json" % (pref, f)), encoding="utf-8"))["poses"][0]
                out[f] = {n: tuple(v["local_space"]["rotation_euler_deg"][k] for k in "xyz") + tuple(v["local_space"]["location"][k] for k in "xyz") + tuple(v["local_space"]["scale"][k] for k in "xyz") for n, v in p["bones"].items()}
            return out
        self.PA = cargar("pala_pozo_f843_983", "pala_pozo_f", 843, 983)
        self.HA = cargar("golpea_rompe_madera_f1016_1063", "golpea_rompe_madera_f", 1016, 1063)
        self.bones = list(self.PA[843].keys())
        for _pl in (self.PA, self.HA):                                         # las suelas de Cerdo_1 quedan 1.4 cm POR DEBAJO de la raiz: se sube la cadera para que no se solapen con la cara superior del piso (z-fighting)
            for _f, _pose in _pl.items():
                v = list(_pose["Body_cerdo_1"]); v[4] += SUELA; _pose["Body_cerdo_1"] = tuple(v)
        gp = os.path.join(REFINAR, "configuraciones", "guiones")
        cp = json.load(open(os.path.join(gp, "configuracion_portable_pala_pozo_f843_983.json"), encoding="utf-8"))["objetos"][0]
        ch = json.load(open(os.path.join(gp, "configuracion_portable_golpea_rompe_madera_f1016_1063.json"), encoding="utf-8"))["objetos"][0]
        self.rab = json.load(open(os.path.join(REFINAR, "docs", "acciones", "rel_espalda_cerdo_1_blend.json"), encoding="utf-8"))["herramientas"]
        M4 = lambda v: Matrix([v[0:4], v[4:8], v[8:12], v[12:16]])
        self.M4 = M4
        self.grip_pala = M4(cp["agarres"]["cavar"]["matriz"]); self.alto = M4(ch["agarres"]["alto"]["matriz"]); self.impacto = M4(ch["agarres"]["impacto"]["matriz"])
        self.reposo = dict(self.PA[855]); self.listo = self.PA[879]                          # reposo = DE PIE con los brazos caidos (PA[843] es la pose ARRODILLADA del inicio de la animacion de la pala: rodillas -89 grados)
        ex = os.path.join(REFINAR, "poses", "tunel_extra")
        d7 = json.load(open(os.path.join(ex, "toma_pico_talla_puerta.json"), encoding="utf-8")); d8 = json.load(open(os.path.join(ex, "guarda_caminando_sale.json"), encoding="utf-8"))
        def _p(d, a, b):
            out = []
            for pose in d["poses"][a:b]:
                q = {n: tuple(v) for n, v in pose.items()}; v = list(q["Body_cerdo_1"]); v[4] += SUELA; q["Body_cerdo_1"] = tuple(v); out.append(q)
            return out
        self.toma = _p(d7, 0, 40); self.toma_agarre = 23                            # `animacion_cerdo_1 (7)`: saca el hacha de la espalda con la animacion del brazo del usuario (agarra en el frame 23)
        self.guarda = _p(d8, 0, 37); self.guarda_suelta = 24
        self.camina = _p(d8, 64, 84); self.camina_pasos = 17                              # CICLO DE CAMINAR DEL ESTUDIO (20 f, ~1.15 m por ciclo): 17 f por bloque                        # `animacion_cerdo_1 (8)`: guarda el hacha en la espalda CAMINANDO (la suelta en el frame 24)
        for _k in ("Leg:BR:Bend_cerdo_1", "Leg:BL:Bend_cerdo_1"):
            _v = list(self.reposo[_k]); _v[0] = 0.0; self.reposo[_k] = tuple(_v)
        self.salto = {"sube": self._leer_salto("slot_002_saltar_subir.py"), "baja": self._leer_salto("slot_003_saltar_bajar.py")}

    @staticmethod
    def _leer_salto(archivo):
        """huesos por frame (radianes) de `generadores_de_recorrido/slots_historia_cerdo_1_desde_1/<archivo>` (animaciones de SALTAR SUBIR / SALTAR BAJAR de Cerdo_1, KEYFRAME_DATA)"""
        import ast as _ast
        ruta = os.path.join(os.path.dirname(REFINAR), "generadores_de_recorrido", "slots_historia_cerdo_1_desde_1", archivo)
        txt = open(ruta, encoding="utf-8").read(); i = txt.index("KEYFRAME_DATA = {"); j = txt.index("{", i); d = 0
        for k in range(j, len(txt)):
            if txt[k] == "{": d += 1
            elif txt[k] == "}":
                d -= 1
                if d == 0: break
        K = _ast.literal_eval(txt[j:k + 1]); fr = sorted(next(iter(K.values())).keys())
        return [{b: K[b][f] for b in K} for f in fr]

    def pala_ciclo(self, c): return self.PA[893 + (c % 14)]
    def pico_ciclo(self, c): return self.HA[1026 + (c % 12)]


def _mezcla(p, q, t): return {n: tuple(a + (b - a) * t for a, b in zip(p[n], q[n])) for n in p}
def _con_escala(m, s):
    l, q, _ = m.decompose(); return Matrix.Translation(l) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((s, s, s, 1))
def _mixM(A, B, t):
    la, qa, sa = A.decompose(); lb, qb, sb = B.decompose()
    return Matrix.Translation(la.lerp(lb, t)) @ qa.slerp(qb, t).to_matrix().to_4x4() @ Matrix.Diagonal(tuple(sa.lerp(sb, t)) + (1,))


# ============================================================================================================================ escena
def rig_cerdo_1():
    arm = next((o for o in bpy.data.objects if o.type == "ARMATURE" and "Body_cerdo_1" in o.pose.bones), None)
    if arm is None: raise RuntimeError("No se encontro el armature de Cerdo_1 (con el hueso Body_cerdo_1)")
    return arm.parent or arm, arm


def celda_de(p): return (int(math.floor(p[0])), int(math.floor(p[1])), int(math.floor(round(p[2], 6))))


class Mundo:
    """consultas sobre el terreno (rayos) ANTES de editar las mallas"""
    def __init__(self, sc, ignorar):
        self.sc = sc; self.dg = bpy.context.evaluated_depsgraph_get(); self.ignorar = set(ignorar); self.cache = {}; self.cache_dir = {}
        self.stone = [o for o in bpy.data.objects if o.type == "MESH" and o.name in PIEDRAS]
    def solida(self, c):
        """celda roca (6 rayos: la primera superficie en cada direccion es una cara DE ESPALDA)"""
        if c in self.cache: return self.cache[c]
        p = Vector((c[0] + .5, c[1] + .5, c[2] + .5)); n = 0.0
        for d in DIRS:
            dv = Vector(d); ok, loc, nor, idx, ob, mat = self.sc.ray_cast(self.dg, p, dv, distance=40)
            if ok and nor.dot(dv) > 0: n += 1
            elif not ok: n += 0.3
        self.cache[c] = n >= 4; return self.cache[c]
    def solido_hacia(self, fc, d):
        """el vecino al otro lado de la cara compartida es roca? (rayo desde la cara: sin impacto o cara de frente = aire)"""
        k = (round(fc[0] * 2), round(fc[1] * 2), round(fc[2] * 2), d)
        if k not in self.cache_dir:
            dv = Vector(d); ok, loc, nor, idx, ob, mat = self.sc.ray_cast(self.dg, Vector(fc) + dv * 0.01, dv, distance=60)
            self.cache_dir[k] = bool(ok and nor.dot(dv) > 0)
        return self.cache_dir[k]
    def preparar_piedra(self, caja):
        """vertices (mundo) de las mallas de piedra dentro de `caja` = (xmin, xmax, ymin, ymax, zmin, zmax), para clasificar las celdas"""
        pts = []
        for o in self.stone:
            n = len(o.data.vertices)
            if n == 0: continue
            co = np.empty(n * 3); o.data.vertices.foreach_get("co", co); co = co.reshape(n, 3); M = np.array(o.matrix_world); w = co @ M[:3, :3].T + M[:3, 3]
            ok = (w[:, 0] >= caja[0]) & (w[:, 0] <= caja[1]) & (w[:, 1] >= caja[2]) & (w[:, 1] <= caja[3]) & (w[:, 2] >= caja[4]) & (w[:, 2] <= caja[5]); pts.append(w[ok])
        self.sv = np.concatenate(pts) if pts else np.zeros((0, 3))
    def piedra(self, c):
        if not hasattr(self, "sv") or len(self.sv) == 0: return False
        p = np.array([c[0] + .5, c[1] + .5, c[2] + .5]); return int((np.linalg.norm(self.sv - p, axis=1) < 0.9).sum()) >= 3


def hacer_tipo(cfg, mundo):
    """tipo de bloque de una celda: piedra real del mundo, o por PROFUNDIDAD (cuanto mas se baja mas piedra; abajo solo piedra)"""
    z_ini, z_fin = cfg.get("z_ini"), cfg.get("z_fin")
    def prof(c):
        if z_ini is None or z_fin is None or z_ini == z_fin: return cfg["pct_piedra"]
        return max(0.0, min(1.0, (z_ini - c[2]) / float(z_ini - z_fin)))
    def tipo(c):
        h = ((c[0] * 73856093) ^ (c[1] * 19349663) ^ (c[2] * 83492791) ^ (cfg["semilla"] * 2654435761)) & 0xFFFFFF
        return "piedra" if (mundo.piedra(c) or (h / float(0x1000000)) < prof(c) or prof(c) >= 0.999) else "tierra"
    return tipo


# ============================================================================================================================ ruta
def construir_ruta(ini, fin):
    """celdas 4-conectadas de `ini` a `fin` (x, y enteros) repartiendo los pasos de x e y; z de la raiz lineal. Devuelve (lista de celdas (cx, cy), z de la raiz por celda)."""
    ax, ay = int(math.floor(ini[0])), int(math.floor(ini[1])); bx, by = int(math.floor(fin[0])), int(math.floor(fin[1]))
    cel = [(ax, ay)]; x, y = ax, ay
    while (x, y) != (bx, by):
        rx, ry = bx - x, by - y
        if abs(rx) * 1.0 >= abs(ry) * 1.0 and rx != 0 and (ry == 0 or abs(rx) / max(1, abs(bx - ax)) >= abs(ry) / max(1, abs(by - ay))): x += 1 if rx > 0 else -1
        elif ry != 0: y += 1 if ry > 0 else -1
        else: x += 1 if rx > 0 else -1
        cel.append((x, y))
    n = len(cel) - 1
    zs = [int(round(ini[2] + (fin[2] - ini[2]) * (i / n if n else 0))) for i in range(n + 1)]       # la z solo cambia de 1 m en 1 m (con la animacion de saltar subir / bajar), nunca valores como 6.36
    return cel, zs


# ============================================================================================================================ animacion
class Linea:
    """linea de tiempo de Cerdo_1 (misma logica que las pruebas de la parte 8)"""
    def __init__(self, bib, cfg):
        self.b = bib; self.cfg = cfg; self.TL = {}; self.EVENTOS = []; self.ACC = []; self.LLEG = {}
        self.fase = 0; self.cur = cfg["frame_ini"]; self.ult = {"pose": bib.reposo, "x": 0, "y": 0, "rz": 90.0, "z": 0.0}
    def poner(self, pose, x, y, rz, z=None):
        z = self.ult["z"] if z is None else z
        self.TL[self.cur] = dict(pose=pose, x=x, y=y, rz=rz, z=z); self.ult.update(pose=pose, x=x, y=y, rz=rz, z=z); self.cur += 1
    def secuencia(self, seq, x, y, rz, z=None, mezcla_in=3):
        p0 = self.ult["pose"]
        for i, p in enumerate(seq): self.poner(_mezcla(p0, p, ss((i + 1) / (mezcla_in + 1))) if i < mezcla_in else p, x, y, rz, z)
    def quedarse(self, n, pose, x, y, rz, z=None): self.secuencia([pose] * n, x, y, rz, z, mezcla_in=min(4, n))
    @staticmethod
    def piernas(base, fase, amp):
        p = dict(base); a = 24.0 * amp; s = math.sin(fase); c = math.cos(fase)
        def sumar(n, dx):
            v = list(p[n]); v[0] += dx; p[n] = tuple(v)
        sumar("Leg:BR_cerdo_1", a * s); sumar("Leg:BL_cerdo_1", -a * s); sumar("Leg:BR:Bend_cerdo_1", -max(0.0, -c) * 28 * amp); sumar("Leg:BL:Bend_cerdo_1", -max(0.0, c) * 28 * amp)
        return p
    PIERNAS = ("Leg:BR_cerdo_1", "Leg:BL_cerdo_1", "Leg:BR:Bend_cerdo_1", "Leg:BL:Bend_cerdo_1")
    TRONCO = ("Leg:FR_cerdo_1", "Leg:FL_cerdo_1", "Leg:FR:Bend_cerdo_1", "Leg:FL:Bend_cerdo_1", "Body_cerdo_1", "Body:Bend_cerdo_1", "Body:Bend_cerdo_1", "Body:Bend_cerdo_1")
    def caminar(self, a, b, rz, nf=None, pose=None):
        """camina de `a` a `b` con el CICLO DE CAMINAR DEL ESTUDIO (el de `animacion_cerdo_1 (8)`); con una herramienta en las manos solo mueve las piernas, sin ella tambien brazos y tronco"""
        nf = nf or self.b.camina_pasos; con_herr = pose is not None and pose is not self.b.reposo; pose = pose or self.b.reposo; p0 = self.ult["pose"]; rz0 = self.ult["rz"]; cyc = self.b.camina
        for i in range(nf):
            u = (i + 1) / nf; amp = min(1.0, (i + 1) / 3.0, (nf - i) / 3.0 + 0.15); base = _mezcla(p0, pose, ss(min(1.0, (i + 1) / 4.0))); c = cyc[(self.fase + i) % len(cyc)]; q = dict(base)
            for bn in (self.PIERNAS if con_herr else self.PIERNAS + self.TRONCO):
                v = list(base[bn])
                for k in range(3): v[k] = base[bn][k] + (c[bn][k] - base[bn][k]) * amp
                q[bn] = tuple(v)
            dz = (rz - rz0 + 180.0) % 360.0 - 180.0
            self.poner(q, a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, rz0 + dz * ss(min(1.0, u * 1.5)), a[2] + (b[2] - a[2]) * u)
        self.fase = (self.fase + nf) % len(cyc)
    def saltar(self, a, b, rz, tipo):
        """un salto de 1 m hacia delante y 1 m arriba / abajo con las animaciones de Cerdo_1 `saltar_subir` (25 f, root suave) / `saltar_bajar` (35 f, trayecto en 22 f y recuperacion)"""
        datos = self.b.salto[tipo]; nf = len(datos); p0 = self.ult["pose"]; rz0 = self.ult["rz"]; dz = (rz - rz0 + 180.0) % 360.0 - 180.0
        base = self.b.reposo
        for i in range(nf):
            u = (i / 24.0) if tipo == "sube" else min(1.0, i / 21.0)
            if tipo == "sube": ez = ss(min(1.0, u / 0.35)); ex = ss(max(0.0, (u - 0.15) / 0.85))      # sube hasta el borde del escalon ANTES de cruzar la linea de la celda
            else: ex = ss(min(1.0, u / 0.8)); ez = ss(max(0.0, (u - 0.55) / 0.45))                     # avanza hasta librar el borde del piso y DESPUES cae
            pose = dict(base)
            for bn, (rx, ry, rzz) in datos[i].items():
                if bn in pose: v = list(pose[bn]); v[0], v[1], v[2] = math.degrees(rx), math.degrees(ry), math.degrees(rzz); pose[bn] = tuple(v)
            if i < 3: pose = _mezcla(p0, pose, ss((i + 1) / 4.0))
            self.poner(pose, a[0] + (b[0] - a[0]) * ex, a[1] + (b[1] - a[1]) * ex, rz0 + dz * ss(min(1.0, (i + 1) / 8.0)), a[2] + (b[2] - a[2]) * ez)
    def tomar(self, herr, x, y, rz, z):
        t0 = self.cur; self.secuencia(self.b.toma, x, y, rz, z, mezcla_in=4); self.ACC.append((t0 + self.b.toma_agarre, herr, "toma"))
    BRAZOS = ("Leg:FR_cerdo_1", "Leg:FL_cerdo_1", "Leg:FR:Bend_cerdo_1", "Leg:FL:Bend_cerdo_1")
    def guardar_caminando(self, herr, a, b, rz, ng=20, nf=9):
        """guarda la herramienta en la espalda (BRAZOS de animacion_cerdo_1 (8), comprimidos a `ng` f) mientras camina RAPIDO de la celda `a` a la `b` en `nf` f
        (ciclo de caminar del estudio al doble de ritmo); cadera / columna / cuello en reposo (sin balanceo); despues queda de pie (nunca arrodillado)"""
        g = self.b.guarda; n = len(g); t0 = self.cur; p0 = self.ult["pose"]; rz0 = self.ult["rz"]; dz = (rz - rz0 + 180.0) % 360.0 - 180.0
        cyc = self.b.camina; nc = len(cyc); rep = self.b.reposo; nf = 0 if tuple(a) == tuple(b) else nf; piernas = {bn: p0[bn] for bn in self.PIERNAS}
        for i in range(ng):
            s_ = i * (n - 1) / (ng - 1); k0 = int(s_); k1 = min(n - 1, k0 + 1); ga = _mezcla(g[k0], g[k1], s_ - k0)
            pose = dict(rep)
            for bn in self.BRAZOS: pose[bn] = ga[bn]
            if i < 3: pose = _mezcla(p0, pose, ss((i + 1) / 4.0))
            if i < nf:                                                                          # camina rapido: 1 bloque en `nf` f, desplazamiento lineal, piernas del ciclo de caminar a doble ritmo
                u = (i + 1) / nf; amp = min(1.0, (i + 1) / 2.0, (nf - i) / 2.0 + 0.15); c = cyc[(self.fase + 2 * i) % nc]
                for bn in self.PIERNAS: pose[bn] = tuple(pose[bn][k] + (c[bn][k] - pose[bn][k]) * amp for k in range(len(pose[bn])))
                piernas = {bn: pose[bn] for bn in self.PIERNAS}
            else:                                                                               # ya llego: termina de guardar la herramienta de pie, piernas al reposo
                u = 1.0; t = ss(min(1.0, (i - nf + 1) / 3.0))
                for bn in self.PIERNAS: pose[bn] = tuple(x + (y - x) * t for x, y in zip(piernas[bn], rep[bn]))
            self.poner(pose, a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, rz0 + dz * ss(min(1.0, u * 2)), a[2] + (b[2] - a[2]) * u)
        if nf: self.fase = (self.fase + 2 * nf) % nc
        self.ACC.append((t0 + round(self.b.guarda_suelta * (ng - 1) / (n - 1)), herr, "guarda"))
        g_fin = dict(self.ult["pose"])                                                          # parte de la ultima pose PUESTA (piernas ya en reposo)
        self.secuencia([_mezcla(g_fin, rep, ss((i + 1) / 6.0)) for i in range(6)], b[0], b[1], rz, b[2], mezcla_in=0)
    def guardar(self, herr, x, y, rz, z):
        t0 = self.cur; self.secuencia([self.b.PA[f] for f in range(945, 960)], x, y, rz, z, mezcla_in=3); self.ACC.append((t0 + 11, herr, "guarda"))
        self.secuencia([_mezcla(self.b.PA[959], self.b.reposo, ss((i + 1) / 10.0)) for i in range(10)], x, y, rz, z, mezcla_in=0)


def animar(bib, cfg, ruta, zs, corredor, mundo):
    """corredor: por indice de celda de la ruta, lista de celdas solidas a cavar ya filtradas; devuelve la Linea"""
    L = Linea(bib, cfg); n = len(ruta) - 1; ini = ruta[0]
    cx = lambda i: (ruta[i][0] + 0.5, ruta[i][1] + 0.5, zs[i])
    rz_dir = lambda a, b: math.degrees(math.atan2(-(b[0] - a[0]), (b[1] - a[1])))
    d0 = rz_dir(ruta[0], ruta[1]) if n else 90.0
    L.ult.update(x=cx(0)[0], y=cx(0)[1], z=zs[0], rz=d0)
    L.quedarse(cfg["espera"], bib.reposo, cx(0)[0], cx(0)[1], d0, zs[0])
    herr = None; ultimo = None
    for i in range(n):
        L.LLEG[i] = L.cur; a = cx(i); b = cx(i + 1); rz = rz_dir(ruta[i], ruta[i + 1]); nuevos = corredor[i + 1]
        if nuevos:
            th = "pico" if (cfg.get("solo_pico") or any(cfg["_tipo"](c) == "piedra" for c in nuevos)) else (herr or "pala")
            tierra_ = [c for c in nuevos if cfg["_tipo"](c) != "piedra"]; piedra_ = [c for c in nuevos if cfg["_tipo"](c) == "piedra"]          # la tierra se rompe de 1 golpe, la piedra de 3
            trabajos = [([c], 1) for c in tierra_] + [([c], 3) for c in piedra_]                  # UN bloque a la vez (nunca dos en simultaneo)
            for grp, ngol in trabajos:
                if herr != th:
                    if herr is not None: L.guardar(herr, a[0], a[1], rz, a[2])
                    L.tomar(th, a[0], a[1], rz, a[2]); herr = th; ultimo = None
                    if th == "pico": L.secuencia([_mezcla(bib.listo, bib.HA[1022], ss((j + 1) / 7.0)) for j in range(7)], a[0], a[1], rz, a[2], mezcla_in=0)
                nf, imp = (14, 6) if herr == "pala" else (12, 4); ciclo = bib.pala_ciclo if herr == "pala" else bib.pico_ciclo; golpes = []
                for g_ in range(ngol):
                    t0 = L.cur; L.secuencia([ciclo(8 + j) for j in range(nf)], a[0], a[1], rz, a[2], mezcla_in=(0 if ultimo == (herr, i) else 5)); ultimo = (herr, i); golpes.append(t0 + imp)
                L.EVENTOS.append((golpes[-1], grp, golpes[:-1]))
        if i == n - 1 and herr is not None and zs[i + 1] == zs[i]: L.guardar_caminando(herr, a, b, rz); herr = None        # termino de romper: guarda la herramienta caminando hacia la ultima celda
        elif zs[i + 1] != zs[i]: L.saltar(a, b, rz, "sube" if zs[i + 1] > zs[i] else "baja")                  # subir / bajar 1 m = saltar (animaciones de Cerdo_1)
        else: L.caminar(a, b, rz, None, pose=(bib.listo if herr == "pala" else (bib.HA[1022] if herr == "pico" else bib.reposo)))
        ultimo = None
    if herr is not None: L.guardar_caminando(herr, cx(n), cx(n), L.ult["rz"])
    L.quedarse(cfg["espera"], bib.reposo, cx(n)[0], cx(n)[1], L.ult["rz"], zs[n])
    return L


# ============================================================================================================================ claves rapidas
def accion(obj, nombre, canales, grupos=None, interp="LINEAR"):
    if obj.animation_data is None: obj.animation_data_create()
    ant = obj.animation_data.action; obj.animation_data.action = None
    if ant is not None and ant.users == 0 and ant.name.startswith("tunel_"): bpy.data.actions.remove(ant)
    a = bpy.data.actions.new(nombre); slot = a.slots.new(id_type='OBJECT', name=obj.name); strip = a.layers.new("Capa").strips.new(type='KEYFRAME'); cb = strip.channelbag(slot, ensure=True)
    for (dp, i), pts in canales.items():
        g = (grupos or {}).get(dp); fc = cb.fcurves.new(dp, index=i, group_name=g) if g else cb.fcurves.new(dp, index=i)
        fc.keyframe_points.add(len(pts)); fc.keyframe_points.foreach_set("co", [v for p in pts for v in p])
        for kp in fc.keyframe_points: kp.interpolation = interp
        fc.update()
    obj.animation_data.action = a; obj.animation_data.action_slot = slot
    return a


PROYECTO = os.path.normpath(os.path.join(REFINAR, os.pardir, os.pardir, os.pardir))                 # .../Alfred_Animacion


def asegurar_herramienta(nombre, base="wooden_pickaxe", textura="stone_pickaxe.png"):
    """si el objeto `nombre` no esta en la escena (p. ej. `stone_pickaxe`), lo crea como copia de `base` (misma malla y orientacion) con la textura `textura` de MCprep (pico de piedra)"""
    if nombre in bpy.data.objects: return bpy.data.objects[nombre]
    src = bpy.data.objects.get(base)
    if src is None: raise RuntimeError("No existe %r ni %r en la escena" % (nombre, base))
    ob = src.copy(); ob.data = src.data.copy(); ob.name = nombre; ob.data.name = nombre
    for c in list(ob.constraints): ob.constraints.remove(c)
    if ob.animation_data: ob.animation_data_clear()
    bpy.context.scene.collection.objects.link(ob)
    ruta = os.path.join(PROYECTO, "MCprep_addon", "MCprep_resources", "resourcepacks", "mcprep_default", "assets", "minecraft", "textures", "item", textura)
    if os.path.exists(ruta) and src.data.materials and src.data.materials[0]:
        mat = src.data.materials[0].copy(); mat.name = nombre + "_material"; img = bpy.data.images.load(ruta, check_existing=True)
        if mat.node_tree:
            for n in mat.node_tree.nodes:
                if n.type == "TEX_IMAGE": n.image = img; n.interpolation = "Closest"
        ob.data.materials[0] = mat
    return ob


def aplicar_linea(L, bib, cfg, ROOT, ARM):
    vl = bpy.context.view_layer; TL = L.TL; ts = sorted(TL)
    sh = bpy.data.objects[cfg["pala"]]; pk = asegurar_herramienta(cfg["pico"])
    for o in (sh, pk):
        if "tunel_rel_espalda" not in o: o["tunel_rel_espalda"] = [v for r in o.matrix_basis for v in r] if o is sh else [v for r in bib.M4(bib.rab["wooden_pickaxe"]["matriz"]) for v in r]
        for c in list(o.constraints): o.constraints.remove(c)
        if o.animation_data and o.animation_data.action: o.animation_data.action = None
        o.rotation_mode = 'QUATERNION'
        for nom, hueso in (("Espalda", "Body:Bend_cerdo_1"), ("Mano", "Leg:FR:Bend_cerdo_1")):
            c = o.constraints.new('CHILD_OF'); c.name = nom; c.target = ARM; c.subtarget = hueso; c.inverse_matrix = Matrix.Identity(4); c.influence = 1.0 if nom == "Espalda" else 0.0
    REL = {"pala": Matrix([sh["tunel_rel_espalda"][0:4], sh["tunel_rel_espalda"][4:8], sh["tunel_rel_espalda"][8:12], sh["tunel_rel_espalda"][12:16]]),
           "pico": Matrix([pk["tunel_rel_espalda"][0:4], pk["tunel_rel_espalda"][4:8], pk["tunel_rel_espalda"][8:12], pk["tunel_rel_espalda"][12:16]])}
    esc = cfg["escala_mano"]; GP = _con_escala(bib.grip_pala, esc)
    UP = pk.get("tunel_grip_pico_usuario")
    GRIP_PICO = Matrix([UP[0:4], UP[4:8], UP[8:12], UP[12:16]]) if UP else (Matrix.Translation((0.060342, 0.30122, 0.18047)) @ Euler((math.radians(-200.13), math.radians(22.563), math.radians(-100.72)), 'XYZ').to_matrix().to_4x4() @ Matrix.Diagonal((0.7, 0.7, 0.7, 1)))
    def grip(herr, pose):
        if herr == "pala": return GP
        return GRIP_PICO                                                                     # forma de SOSTENER EL PICO elegida por el usuario (relativa a Leg:FR:Bend_cerdo_1), fija en todo el picado
        t = max(0.0, min(1.0, (pose["Leg:FR:Bend_cerdo_1"][0] + 43.0) / 73.0)); la, qa, _ = bib.alto.decompose(); li, qi, _ = bib.impacto.decompose()
        return Matrix.Translation(la.lerp(li, t)) @ qa.slerp(qi, t).to_matrix().to_4x4() @ Matrix.Diagonal((esc, esc, esc, 1))
    def mats(t):
        d = TL[t]; ROOT.location = (d["x"], d["y"], d["z"]); ROOT.rotation_euler = (0, 0, math.radians(d["rz"]))
        for n, v in d["pose"].items():
            pb = ARM.pose.bones[n]; pb.rotation_mode = 'XYZ'; pb.rotation_euler = tuple(math.radians(a) for a in v[0:3]); pb.location = v[3:6]; pb.scale = v[6:9]
        vl.update(); return (ARM.matrix_world @ ARM.pose.bones["Leg:FR:Bend_cerdo_1"].matrix).copy(), (ARM.matrix_world @ ARM.pose.bones["Body:Bend_cerdo_1"].matrix).copy()
    M_ = {}
    for (tacc, herr, tipo) in L.ACC:
        for t in range(tacc - 4, tacc + 5):
            if t in TL and t not in M_: M_[t] = mats(t)
    B = {"pala": {ts[0]: REL["pala"]}, "pico": {ts[0]: REL["pico"]}}
    for (tacc, herr, tipo) in L.ACC:
        if tipo == "toma":
            hand, sp1 = M_[tacc]; B0 = hand.inverted() @ (sp1 @ REL[herr]); B[herr][tacc - 1] = REL[herr]; B[herr][tacc] = B0
            for i in range(1, 5): B[herr][tacc + i] = _mixM(B0, grip(herr, TL[tacc + i]["pose"]), i / 4.0)
        else:
            for i in range(4, -1, -1):
                t = tacc - i; hand, sp1 = M_[t]; Bb = hand.inverted() @ (sp1 @ REL[herr]); B[herr][t] = _mixM(grip(herr, TL[t]["pose"]), Bb, (4 - i) / 4.0)
            B[herr][tacc + 1] = REL[herr]
    for herr, o in (("pala", sh), ("pico", pk)):
        cambios = sorted((t, tp) for (t, h, tp) in L.ACC if h == herr)
        for i in range(0, len(cambios) - 1, 2):
            for t in range(cambios[i][0] + 5, cambios[i + 1][0] - 4): B[herr].setdefault(t, grip(herr, TL[t]["pose"]))
    # claves de Cerdo_1
    accion(ROOT, "tunel_cerdo_1_root", {("location", ax): [(t, (TL[t]["x"], TL[t]["y"], TL[t]["z"])[ax]) for t in ts] for ax in range(3)} | {("rotation_euler", 2): [(t, math.radians(TL[t]["rz"])) for t in ts]})
    can = {}
    for n in bib.bones:
        for j, (dp, ax) in enumerate([("rotation_euler", 0), ("rotation_euler", 1), ("rotation_euler", 2), ("location", 0), ("location", 1), ("location", 2), ("scale", 0), ("scale", 1), ("scale", 2)]):
            can[('pose.bones["%s"].%s' % (n, dp), ax)] = [(t, (math.radians(TL[t]["pose"][n][j]) if dp == "rotation_euler" else TL[t]["pose"][n][j])) for t in ts]
    for pb in ARM.pose.bones: pb.rotation_mode = 'XYZ'
    accion(ARM, "tunel_cerdo_1_armature", can, grupos={k[0]: k[0].split('"')[1] for k in can})
    for herr, o in (("pala", sh), ("pico", pk)):
        tf = sorted(B[herr]); can = {}
        for ax in range(3): can[("location", ax)] = [(t, B[herr][t].to_translation()[ax]) for t in tf]; can[("scale", ax)] = [(t, B[herr][t].to_scale()[ax]) for t in tf]
        for ax in range(4): can[("rotation_quaternion", ax)] = [(t, B[herr][t].to_quaternion()[ax]) for t in tf]
        ie = [(ts[0], 1.0)]; im = [(ts[0], 0.0)]
        for (t, h, tp) in sorted(L.ACC):
            if h != herr: continue
            if tp == "toma": ie += [(t - 1, 1.0), (t, 0.0)]; im += [(t - 1, 0.0), (t, 1.0)]
            else: ie += [(t, 0.0), (t + 1, 1.0)]; im += [(t, 1.0), (t + 1, 0.0)]
        can[('constraints["Espalda"].influence', 0)] = sorted(set(ie)); can[('constraints["Mano"].influence', 0)] = sorted(set(im))
        a = accion(o, "tunel_%s" % herr, can)
        for fc in a.layers[0].strips[0].channelbags[0].fcurves:
            if "influence" in fc.data_path:
                for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'


# ============================================================================================================================ geometria
def _romper_claves(tC, base, previos=()):
    """romper un bloque (animacion_cerdo_1 (7), `refugio_bloque_06`): CADA golpe previo lo hace temblar ~1 cm y lo agrieta (escala .97 tras el 1.º, .94 tras el 2.º); en el golpe final se encoge en 3 f (.857 -> .533 -> .159) y desaparece"""
    off = [(0.002, 0.01, 0.005), (0.002, -0.006, -0.003), (-0.003, 0.003, -0.001), (0.0, 0.0, 0.0)]
    golpes = [h for h in previos] + [tC]; esc = [0.97, 0.94]
    loc = {ax: [(golpes[0] - 5, base[ax])] for ax in range(3)}
    sca = [(1, 1.0)]
    for n_, h in enumerate(golpes):
        ini = h - 3 if n_ == len(golpes) - 1 else h                                         # el golpe final tiembla 3 f ANTES de romperse; los previos desde el impacto
        for ax in range(3):
            loc[ax] += [(ini + k, base[ax] + off[k][ax]) for k in range(4)]
        if n_ < len(golpes) - 1: sca.append((h, 1.0 if n_ == 0 else esc[n_ - 1])); sca.append((h + 1, esc[min(n_, 1)]))
        else: sca += [(tC - 1, esc[min(len(previos), 2) - 1] if previos else 0.97), (tC, 0.857), (tC + 1, 0.533), (tC + 2, 0.159)]
    ex = {}
    for ax in range(3):
        ex[("location", ax)] = loc[ax] + [(tC + 3, base[ax])]; ex[("scale", ax)] = sca
    return ex


def _vis(o, t_on, t_off, extras=None):
    pts = [(1, 1.0 if t_on > 1 else 0.0)]
    if t_on > 1: pts.append((t_on, 0.0))
    if t_off < 10 ** 5: pts.append((t_off, 1.0))
    o.hide_viewport = pts[0][1] > 0.5; o.hide_render = pts[0][1] > 0.5
    if o.animation_data is None: o.animation_data_create()
    a = bpy.data.actions.new("tunel_vis_" + o.name); slot = a.slots.new(id_type='OBJECT', name=o.name); cb = a.layers.new("Capa").strips.new(type='KEYFRAME').channelbag(slot, ensure=True)
    for dp in ("hide_viewport", "hide_render"):
        fc = cb.fcurves.new(dp, index=0); fc.keyframe_points.add(len(pts)); fc.keyframe_points.foreach_set("co", [v for p in pts for v in p])
        for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
        fc.update()
    for (dp, i), ps in (extras or {}).items():
        ps = sorted(set(ps)); fc = cb.fcurves.new(dp, index=i); fc.keyframe_points.add(len(ps)); fc.keyframe_points.foreach_set("co", [v for q in ps for v in q])
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
        fc.update()
    o.animation_data.action = a; o.animation_data.action_slot = slot


def _cuadrado(fc, n):
    ax = [i for i in range(3) if n[i] != 0][0]; o1, o2 = [i for i in range(3) if i != ax]; pts = []
    for s1, s2 in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        v = [fc[0], fc[1], fc[2]]; v[o1] += .5 * s1; v[o2] += .5 * s2; pts.append(Vector(v))
    if (pts[1] - pts[0]).cross(pts[2] - pts[1]).dot(Vector(n)) < 0: pts.reverse()
    return pts


BLOQUES_DIR = os.path.normpath(os.path.join(REFINAR, os.pardir, os.pardir, os.pardir, "bloques_dinamicos"))     # .../Alfred_Animacion/bloques_dinamicos
BLOQUE_ARCHIVO = {"tierra": ("bloque_de_tierra.blend", "dirt"), "piedra": ("bloque_de_stone.blend", "stone")}


def malla_bloque(tipo, carpeta=None):
    """malla del BLOQUE ENTERO (cubo de 1 m con sus 6 caras / materiales) de `bloques_dinamicos/bloque_de_tierra.blend` o `bloque_de_stone.blend`; se importa una vez y se comparte"""
    nom = "tunel_bloque_" + tipo
    if nom in bpy.data.meshes: return bpy.data.meshes[nom]
    arch, obn = BLOQUE_ARCHIVO[tipo]; ruta = os.path.join(carpeta or BLOQUES_DIR, arch)
    if not os.path.exists(ruta): raise RuntimeError("No existe %s" % ruta)
    with bpy.data.libraries.load(ruta, link=False) as (src, dst):
        if obn not in src.objects: raise RuntimeError("%s no tiene el objeto %r" % (arch, obn))
        dst.objects = [obn]
    ob = dst.objects[0]; me = ob.data; me.name = nom; me.use_fake_user = True
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    c = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2))
    me.transform(Matrix.Translation(-c))                                                   # el cubo del archivo parte de la BASE (z 0..1): se centra para que el origen sea el CENTRO del bloque
    bpy.data.objects.remove(ob, do_unlink=True)
    return me


def geometria(sc, cfg, mundo, eventos, corr_celdas, llegadas, ruta, rellenos=()):
    """pone los BLOQUES del tunel (sin superficies sueltas): tapas de las celdas cavadas (copias de sus caras originales), bloques de tierra / piedra para lo que se descubre, el cascaron y borra del mundo
    las caras que sustituyen / se rompen"""
    T = {}; HITS = {}
    for f, cs, hs in eventos:
        for c in cs: T[tuple(c)] = f; HITS[tuple(c)] = list(hs)
    if not T: return {"tapas": 0, "bloques": 0, "objetos": 0}
    xs = [c[0] for c in T]; ys = [c[1] for c in T]; zs_ = [c[2] for c in T]
    BOX = (min(xs) - 1.6, max(xs) + 2.6, min(ys) - 1.6, max(ys) + 2.6, min(zs_) - 1.6, max(zs_) + 2.6)
    ign = set(mundo.ignorar); INDEX = {}; PCL = []; PNL = []; POL = []
    def indexar(o):
        me = o.data; n = len(me.polygons)
        if n == 0: return
        c = np.empty(n * 3); nr = np.empty(n * 3); me.polygons.foreach_get("center", c); me.polygons.foreach_get("normal", nr); c = c.reshape(n, 3); nr = nr.reshape(n, 3)
        M = np.array(o.matrix_world); cw = c @ M[:3, :3].T + M[:3, 3]; nw = nr @ M[:3, :3].T; nw /= np.maximum(np.linalg.norm(nw, axis=1, keepdims=True), 1e-9)
        ok = np.where((cw[:, 0] >= BOX[0]) & (cw[:, 0] <= BOX[1]) & (cw[:, 1] >= BOX[2]) & (cw[:, 1] <= BOX[3]) & (cw[:, 2] >= BOX[4]) & (cw[:, 2] <= BOX[5]))[0]
        for i in ok: INDEX.setdefault((int(round(cw[i, 0] * 2)), int(round(cw[i, 1] * 2)), int(round(cw[i, 2] * 2))), []).append((o, int(i), nw[i].copy()))
        PCL.append(cw[ok]); PNL.append(nw[ok]); POL.extend((o, int(i)) for i in ok)
    for o in bpy.data.objects:
        if o.type != "MESH" or o.name in ign or o.name.startswith(("tunel_", "techo_tierra")): continue
        if o.parent is not None and o.parent.type == "ARMATURE": continue                      # personajes y herramientas (mallas con rig): NUNCA se tocan
        if any(m.type == "ARMATURE" for m in o.modifiers) or len(o.vertex_groups) > 0: continue
        bb = [o.matrix_world @ Vector(v) for v in o.bound_box]
        if max(b.x for b in bb) < BOX[0] or min(b.x for b in bb) > BOX[1] or max(b.y for b in bb) < BOX[2] or min(b.y for b in bb) > BOX[3] or max(b.z for b in bb) < BOX[4] or min(b.z for b in bb) > BOX[5]: continue
        indexar(o)
    PC = np.concatenate(PCL) if PCL else np.zeros((0, 3)); PN = np.concatenate(PNL) if PNL else np.zeros((0, 3))
    def en_plano(cell, e, tol=0.02):
        """TODAS las caras del mundo (cualquier orientacion, tamano o centro) que tocan la cara `e` de la celda: en su mismo plano (+-`tol`) y con el centro dentro del cuadrado de esa cara"""
        a = [i for i in range(3) if e[i] != 0][0]; u, v = [i for i in range(3) if i != a]
        fc = (cell[0] + .5 + .5 * e[0], cell[1] + .5 + .5 * e[1], cell[2] + .5 + .5 * e[2])
        if not len(PC): return []
        m = (np.abs(PN[:, a]) > 0.9) & (np.abs(PC[:, a] - fc[a]) < tol) & (np.abs(PC[:, u] - fc[u]) < 0.5 + 1e-3) & (np.abs(PC[:, v] - fc[v]) < 0.5 + 1e-3)
        return [POL[j] for j in np.where(m)[0]]
    malla = {"tierra": malla_bloque("tierra", cfg.get("bloques_dir")), "piedra": malla_bloque("piedra", cfg.get("bloques_dir"))}
    tipo = cfg["_tipo"]
    def key(fc): return (int(round(fc[0] * 2)), int(round(fc[1] * 2)), int(round(fc[2] * 2)))
    def caras_de(cell, e):                                                                  # caras originales del mundo en el lado `e` de la celda (con normal hacia fuera)
        fc = (cell[0] + .5 + .5 * e[0], cell[1] + .5 + .5 * e[1], cell[2] + .5 + .5 * e[2])
        return [(o, i) for (o, i, nw) in INDEX.get(key(fc), []) if nw[0] * e[0] + nw[1] * e[1] + nw[2] * e[2] > 0.9]
    celda_de = {}
    cubiertas = {}                                                                          # t_off -> caras originales de celdas cavadas (se copian a `tapa` y se borran)
    reemplazo = []                                                                          # caras originales de bloques que pasan a ser un bloque entero (se copian ocultas para poder deshacer)
    BL = {}                                                                                 # celda -> [tipo, t_on, t_off]
    fin_ruta = ruta[-cfg["final_abierto"]:] if cfg["final_abierto"] else []; dir_final = (0, 0)
    if len(ruta) > 1: dir_final = (ruta[-1][0] - ruta[-2][0], ruta[-1][1] - ruta[-2][1])
    ult_celdas = {c for c in T if (c[0], c[1]) in set(fin_ruta)}
    zona_final = cfg.get("_zona_final", set())
    def bloque(cell, tp, t_on, t_off):
        if (cell[0], cell[1]) in zona_final: return                                          # tramo final: no se generan bloques
        if cell in BL: BL[cell][1] = min(BL[cell][1], t_on); BL[cell][2] = max(BL[cell][2], t_off)
        else: BL[cell] = [tp, t_on, t_off]
    import random as _random
    rng_r = _random.Random(cfg["semilla"] + 1); relleno = set(map(tuple, rellenos))
    for C in sorted(relleno):                                                                 # celdas de aire del corredor: bloque entero desde el inicio hasta que Cerdo_1 lo pica
        if C in T: bloque(C, tipo(C), 1, T[C])
    for C, tC in T.items():
        if C in relleno: continue
        if any(caras_de(C, e) for e in DIRS): bloque(C, tipo(C), 1, tC)                       # bloque REAL del mundo que se pica: pasa a ser un BLOQUE ENTERO (sus caras expuestas se quitan), no una superficie suelta
        for d in DIRS:
            propias = caras_de(C, d); N = (C[0] + d[0], C[1] + d[1], C[2] + d[2])
            if propias:
                cubiertas.setdefault(tC, []).extend(propias)
                for (o_, i_) in propias: celda_de[(id(o_), i_)] = C
            elif C in ult_celdas and (d[0], d[1]) == dir_final: continue                    # fondo abierto hacia la cueva
            elif N in T:
                if T[N] < tC and not any(caras_de(C, e) for e in DIRS): bloque(C, tipo(C), T[N], tC)     # (si C ya tiene caras expuestas propias se omite: se solaparian con las suyas hasta el golpe)                                  # C queda al descubierto cuando se rompe N y se rompe despues
            else:
                fc = (C[0] + .5 + .5 * d[0], C[1] + .5 + .5 * d[1], C[2] + .5 + .5 * d[2])
                if mundo.solido_hacia(fc, d): bloque(N, tipo(N), 1, 10 ** 6)                  # vecino de roca: pasa a ser un bloque entero (visible desde el inicio, tapado por la roca hasta que se rompe C)
    borrando = {(id(o), i) for lst in cubiertas.values() for (o, i) in lst}                 # caras del mundo que se van a quitar (no cuentan como existentes)
    def ocupada(cell):                                                                      # la celda ya es un bloque del mundo? (tiene una cara expuesta propia hacia fuera en algun lado)
        return any((id(o), i) not in borrando for e in DIRS for (o, i) in caras_de(cell, e))
    # cascaron de bloques enteros donde el corredor no tiene piso / paredes / techo
    if cfg["cascaron"]:
        import random
        rng = random.Random(cfg["semilla"]); cset = set(corr_celdas); n_ent = cfg["entrada_sin_cascaron"]; idx_de = {(r[0], r[1]): i for i, r in enumerate(ruta)}
        for C in corr_celdas:
            i = idx_de.get((C[0], C[1]), 0)
            if i < n_ent: continue
            t_on = max(2, llegadas.get(max(0, i - cfg["adelanto"]), 2))
            for d in DIRS:
                N = (C[0] + d[0], C[1] + d[1], C[2] + d[2])
                if N in cset or N in BL or N in T: continue
                if i >= len(ruta) - cfg["final_abierto"] and (d[0], d[1]) == dir_final: continue
                fc = (C[0] + .5 + .5 * d[0], C[1] + .5 + .5 * d[1], C[2] + .5 + .5 * d[2])
                if mundo.solido_hacia(fc, d): continue                                      # ya es roca
                if ocupada(N): continue                                                     # ya hay un bloque del mundo ahi: no se pone otro encima
                bloque(N, tipo(N), t_on, 10 ** 6)
    # los bloques que sustituyen roca / terreno existente: sus caras originales expuestas se quitan (el bloque entero las reemplaza)
    for cell, (tp, t_on, t_off) in BL.items():
        if cell in T: continue
        for e in DIRS:
            for (o, i) in caras_de(cell, e): reemplazo.append((o, i))
    # las superficies del mundo que quedan PEGADAS a un bloque del tunel (caras del bloque vecino que miran a la celda del bloque) se eliminan para que no se solapen con las del bloque:
    #  - bloque permanente (cascaron, roca vecina): se borran definitivamente (copia oculta solo para `quitar`);
    #  - bloque que Cerdo_1 rompe (relleno de aire): se mueven a un objeto que APARECE cuando el bloque desaparece (asi la pared sigue ahi al romperlo)
    reaparecen = {}
    for cell, (tp, t_on, t_off) in BL.items():
        for e in DIRS:
            fc = (cell[0] + .5 + .5 * e[0], cell[1] + .5 + .5 * e[1], cell[2] + .5 + .5 * e[2])
            facs = [(o, i) for (o, i) in en_plano(cell, e) if (id(o), i) not in borrando]
            if not facs: continue
            if cell in T: reaparecen.setdefault(T[cell] + 3, []).extend(facs)
            else: reemplazo.extend(facs)
    col = bpy.data.collections.get(COL) or bpy.data.collections.new(COL)
    if col.name not in [c.name for c in sc.collection.children]: sc.collection.children.link(col)
    n_obj = 0; BORRAR = {}
    for cell, (tp, t_on, t_off) in sorted(BL.items(), key=lambda kv: (kv[1][1], kv[0])):
        ob = bpy.data.objects.new("tunel_bloque_%s_%d_%d_%d" % (tp, cell[0], cell[1], cell[2]), malla[tp]); ob.location = (cell[0] + 0.5, cell[1] + 0.5, cell[2] + 0.5)
        col.objects.link(ob)
        if cell in T: _vis(ob, t_on, T[cell] + 3, _romper_claves(T[cell], ob.location, HITS.get(cell, ())))                       # celda cavada: tiembla y se rompe
        else: _vis(ob, t_on, t_off)
        n_obj += 1
    def copiar(lista, nombre, t_on, t_off, por_celda=False):
        por = {}
        for o, i in {(id(o), i): (o, i) for o, i in lista}.values(): por.setdefault((o, celda_de.get((id(o), i)) if por_celda else None), set()).add(i)
        for (o, cell), idx in por.items():
            origen = Vector((cell[0] + .5, cell[1] + .5, cell[2] + .5)) if cell else Vector((0.0, 0.0, 0.0))
            me = o.data; mw = o.matrix_world; uvd = me.uv_layers[0].data if me.uv_layers else None; bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
            for i in sorted(idx):
                p = me.polygons[i]
                try: f = bm.faces.new([bm.verts.new(mw @ me.vertices[vi].co - origen) for vi in p.vertices])
                except ValueError: continue
                f.material_index = p.material_index
                if uvd:
                    for l, li in zip(f.loops, p.loop_indices): l[uvl].uv = uvd[li].uv
            mc = bpy.data.meshes.new("tunel_tapa_m"); bm.to_mesh(mc); bm.free()
            for m in me.materials: mc.materials.append(m)
            ob = bpy.data.objects.new("tunel_tapa_%s_%s" % (o.name, nombre), mc); ob["tunel_origen"] = o.name; ob["tunel_base"] = [origen.x, origen.y, origen.z]; ob.location = origen; col.objects.link(ob)
            if cell is not None and cell in T: _vis(ob, t_on, T[cell] + 3, _romper_claves(T[cell], origen, HITS.get(cell, ())))
            else: _vis(ob, t_on, t_off)
            BORRAR.setdefault(o, set()).update(idx)
    vistas = set(borrando)                                                                  # cada cara del mundo va a UNA sola copia (si no, `quitar` la devolveria dos veces)
    for k_ in sorted(reaparecen):
        reaparecen[k_] = [x for x in {(id(o_), i_): (o_, i_) for o_, i_ in reaparecen[k_]}.values() if (id(x[0]), x[1]) not in vistas]
        vistas.update((id(o_), i_) for o_, i_ in reaparecen[k_])
    reemplazo[:] = [x for x in {(id(o_), i_): (o_, i_) for o_, i_ in reemplazo}.values() if (id(x[0]), x[1]) not in vistas]
    cav = [x for lista in cubiertas.values() for x in lista]
    if cav: copiar(cav, "cavadas", 10 ** 6, 10 ** 7); n_obj += 1                                 # caras originales de las celdas cavadas: las reemplaza el bloque entero; se quitan del mundo (copia oculta solo para `quitar`)
    for t_ap, lista in sorted(reaparecen.items()): copiar(lista, "pared_%d" % t_ap, t_ap, 10 ** 6); n_obj += 1
    if reemplazo: copiar(reemplazo, "sustituidas", 10 ** 6, 10 ** 7); n_obj += 1                # caras del mundo que sustituye / tapa un bloque: se quitan (copia oculta solo para `quitar`)
    # lo que suelta cada bloque roto, COMO EN MINECRAFT: el mini bloque (escala .25) CAE al SUELO del tunel (rebota un poco y queda girando), y cuando Cerdo_1 esta a menos de 1.5 m lo ABSORBE:
    # vuela a su pecho encogiendose (animacion_cerdo_1 (8), `drop_tablon`) y desaparece
    pos_a = cfg.get("_pos_cerdo_1"); piso = cfg.get("_piso")
    if pos_a is not None:
        for cell, tC in sorted(T.items(), key=lambda kv: kv[1]):
            tp = tipo(cell); ob = bpy.data.objects.new("tunel_item_%d_%d_%d" % cell, malla[tp]); ob.scale = (0.25, 0.25, 0.25); col.objects.link(ob)
            h_ = ((cell[0] * 73856093) ^ (cell[1] * 19349663) ^ (cell[2] * 83492791)) & 0xFFFF
            cx_ = cell[0] + .5 + ((h_ & 0xFF) / 255.0 - 0.5) * 0.3; cy_ = cell[1] + .5 + (((h_ >> 8) & 0xFF) / 255.0 - 0.5) * 0.3
            z0 = cell[2] + .5; zf = (piso(cell) if piso else cell[2]) + 0.125; hh = max(0.0, z0 - zf); fall = max(4, int(round(5.5 * math.sqrt(max(hh, 0.3)))))
            land = tC + fall
            ex = {("location", 0): [], ("location", 1): [], ("location", 2): [], ("scale", 0): [], ("scale", 1): [], ("scale", 2): []}
            for k in sorted({0, max(1, fall // 3), max(2, 2 * fall // 3), fall}):               # caida (cuadratica) hasta el suelo del tunel
                z = z0 - (z0 - zf) * (k / float(fall)) ** 2
                for ax, v in enumerate((cx_, cy_, z)): ex[("location", ax)].append((tC + k, v))
            for k, dz in ((2, 0.1), (4, 0.0)):                                                  # rebote pequeno
                for ax, v in enumerate((cx_, cy_, zf + dz)): ex[("location", ax)].append((land + k, v))
            t_pick = land + 6
            for f_ in range(land + 6, land + 96):                                               # lo recoge cuando Cerdo_1 esta cerca
                pa = pos_a(f_)
                if math.hypot(pa[0] - cx_, pa[1] - cy_) < 1.5 and abs(pa[2] - (zf - 0.125)) < 1.5: t_pick = f_; break
            ax_, ay_, az_ = pos_a(t_pick + 6); az_ += 1.1
            for k in (2, 4, 6):                                                                  # vuela al pecho de Cerdo_1 encogiendose
                u = ss(k / 6.0)
                for ax, (v0, v1) in enumerate(((cx_, ax_), (cy_, ay_), (zf, az_))): ex[("location", ax)].append((t_pick + k, v0 + (v1 - v0) * u))
            for ax in range(3): ex[("scale", ax)] = [(tC, 0.25), (t_pick, 0.25), (t_pick + 2, 0.25 * (1 - ss(2 / 6.0))), (t_pick + 4, 0.25 * (1 - ss(4 / 6.0))), (t_pick + 6, 0.0)]
            ex[("rotation_euler", 2)] = [(tC, 0.0), (t_pick + 6, 2 * math.pi * (t_pick + 6 - tC) / 15.0)]
            _vis(ob, tC, t_pick + 7, ex); n_obj += 1
    borradas = 0
    for o, idx in BORRAR.items():
        me = o.data; b2 = bmesh.new(); b2.from_mesh(me); b2.faces.ensure_lookup_table()
        bmesh.ops.delete(b2, geom=[b2.faces[i] for i in sorted(idx)], context='FACES_ONLY'); b2.to_mesh(me); b2.free(); me.update(); borradas += len(idx)
    return {"tapas": sum(len(v) for v in cubiertas.values()), "bloques": len(BL), "objetos": n_obj, "borradas": borradas, "diag": {"cubiertas": sum(len(v) for v in cubiertas.values()), "reemplazo": len(reemplazo), "reaparecen": sum(len(v) for v in reaparecen.values()), "PC": int(len(PC)), "BL": len(BL)}, "_BL": dict(BL)}


def colisiones(L, BL, eventos_t, solidas, alto):
    """cuenta los frames en que el cuerpo de Cerdo_1 (pies y cabeza sobre la columna de la raiz) esta dentro de un bloque: bloque del tunel visible en ese frame o roca todavia sin picar"""
    malos = []
    for f in sorted(L.TL):
        d = L.TL[f]; cx_, cy_ = int(math.floor(d["x"])), int(math.floor(d["y"])); z0 = int(math.floor(d["z"] + 0.01)); z1 = int(math.floor(d["z"] + 1.9))
        for z in range(z0, z1 + 1):
            c = (cx_, cy_, z)
            if c in BL and BL[c][1] <= f < BL[c][2]: malos.append((f, c, "bloque")); break
            if c in solidas and eventos_t.get(c, 10 ** 9) > f: malos.append((f, c, "roca")); break
    return {"frames": len(malos), "primeros": malos[:8]}


def quitar(sc):
    """deshace el tunel: devuelve a las mallas originales las caras borradas, quita los objetos `tunel_*` y las acciones `tunel_*`"""
    col = bpy.data.collections.get(COL); n_rest = 0
    if col:
        for ob in list(col.objects):
            if ob.name.startswith("tunel_tapa_") and ob.get("tunel_origen") in bpy.data.objects:
                src = bpy.data.objects[ob["tunel_origen"]]; inv = src.matrix_world.inverted(); me = src.data
                bm = bmesh.new(); bm.from_mesh(me); uvl = bm.loops.layers.uv.verify() if me.uv_layers else None; sm = ob.data
                uvd = sm.uv_layers[0].data if sm.uv_layers else None
                for p in sm.polygons:
                    try: f = bm.faces.new([bm.verts.new(inv @ (Matrix.Translation(Vector(ob.get("tunel_base", (0.0, 0.0, 0.0)))) @ sm.vertices[vi].co)) for vi in p.vertices])
                    except ValueError: continue
                    f.material_index = p.material_index
                    if uvl and uvd:
                        for l, li in zip(f.loops, p.loop_indices): l[uvl].uv = uvd[li].uv
                    n_rest += 1
                bm.to_mesh(me); bm.free(); me.update()
        for ob in list(col.objects):
            me = ob.data; bpy.data.objects.remove(ob, do_unlink=True)
            if me and me.users == 0: bpy.data.meshes.remove(me)
        bpy.data.collections.remove(col)
    for o in bpy.data.objects:                                                     # soltar las acciones `tunel_*` de Cerdo_1, de las herramientas y de lo que sea
        if o.animation_data and o.animation_data.action and o.animation_data.action.name.startswith("tunel_"): o.animation_data.action = None
    for a in list(bpy.data.actions):
        if a.name.startswith("tunel_") and a.users == 0: bpy.data.actions.remove(a)
    try:
        ROOT, ARM = rig_cerdo_1()
        for o in (ROOT, ARM):
            if o.animation_data and o.animation_data.action and o.animation_data.action.name.startswith("tunel_"): o.animation_data.action = None
    except RuntimeError: pass
    for a in list(bpy.data.actions):
        if a.name.startswith("tunel_") and a.users == 0: bpy.data.actions.remove(a)
    return n_rest


# ============================================================================================================================ principal
CFG_DEFECTO = dict(final_sin_bloques=0, solo_pico=True, rellenar_aire=True, bloques_dir=None, frame_ini=1, alto=3, espera=14, pala="stone_shovel", pico="stone_pickaxe", escala_mano=0.7, cascaron=True, semilla=3, pct_piedra=0.5, final_abierto=2,
                   entrada_sin_cascaron=1, adelanto=4, ignorar=("Short_Grass", "Fern", "Large_Fern", "Birch_Leaves", "Oak_Leaves", "Spruce_Leaves", "Allium", "Dandelion", "Azure_Bluet", "Poppy",
                                                                "Seagrass", "Brown_Mushroom", "Glow_Lichen", "Stationary_Water"))


def crear(context, inicio, final, **kw):
    """Crea el tunel de `inicio` a `final` (coordenadas de mundo, z = piso) con Cerdo_1 cavando. Devuelve un resumen."""
    sc = context.scene; cfg = dict(CFG_DEFECTO); cfg.update(kw)
    if bpy.data.collections.get(COL): quitar(sc)
    ROOT, ARM = rig_cerdo_1(); bib = Biblioteca(); mundo = Mundo(sc, cfg["ignorar"])
    ruta, zs = construir_ruta(inicio, final); n = len(ruta) - 1
    cfg['z_ini'], cfg['z_fin'] = zs[0], zs[-1]
    cfg["_tipo"] = hacer_tipo(cfg, mundo)
    K = max(0, int(cfg["final_sin_bloques"]))                                              # al llegar al final del recorrido NO se generan mas bloques (solo se rompen los que hay delante)
    cfg["_zona_final"] = {(r_[0] + dx, r_[1] + dy) for r_ in ruta[-K:] for dx in (-1, 0, 1) for dy in (-1, 0, 1)} if K else set()
    xs_ = [r[0] for r in ruta]; ys_ = [r[1] for r in ruta]; mundo.preparar_piedra((min(xs_) - 3, max(xs_) + 4, min(ys_) - 3, max(ys_) + 4, min(zs) - 3, max(zs) + cfg['alto'] + 3))
    if n < 1: raise RuntimeError("El inicio y el final estan en la misma celda")
    corredor_por_i = []; corr_celdas = []
    for i, (cx_, cy_) in enumerate(ruta):
        zf = int(math.floor(zs[i] + 0.001)); zmax = max(zs[j] for j in (i - 1, i, i + 1) if 0 <= j <= n)                  # junto a un escalon el corredor sube hasta la altura del vecino (cabeza libre en el salto)
        celdas = [(cx_, cy_, z) for z in range(zf, int(math.floor(zmax + 0.001)) + cfg["alto"])]; corr_celdas += celdas
        corredor_por_i.append([c for c in celdas if i > 0 and ((cfg["rellenar_aire"] and (c[0], c[1]) not in cfg["_zona_final"]) or mundo.solida(c))])
    rellenos = [c for lst in corredor_por_i for c in lst if not mundo.solida(c) and (c[0], c[1]) not in cfg["_zona_final"]]            # celdas de aire del corredor: se rellenan con bloques para que Cerdo_1 siempre tenga bloques delante
    L = animar(bib, cfg, ruta, zs, corredor_por_i, mundo)
    fmax = max(L.TL); piso_ = {(r_[0], r_[1]): zs[i_] for i_, r_ in enumerate(ruta)}
    cfg["_piso"] = lambda c: piso_.get((c[0], c[1]), c[2])                                  # nivel del piso del tunel en esa columna (donde caen los bloques rotos)
    cfg["_pos_cerdo_1"] = lambda f: (L.TL[min(f, fmax)]["x"], L.TL[min(f, fmax)]["y"], L.TL[min(f, fmax)]["z"])
    ev = [(e[0], [list(c) for c in e[1]], list(e[2])) for e in L.EVENTOS]
    llegadas = {i: f for i, f in L.LLEG.items()}
    g = geometria(sc, cfg, mundo, [(f, [tuple(c) for c in cs], hs) for f, cs, hs in ev], corr_celdas, llegadas, ruta, rellenos)      # primero la geometria (con la escena sin tocar), luego las claves
    aplicar_linea(L, bib, cfg, ROOT, ARM)
    fin = L.cur - 1; sc.frame_end = max(sc.frame_end, fin)
    g["colisiones"] = colisiones(L, g.get("_BL", {}), eventos_t=dict((tuple(c), f) for f, cs, hs in ev for c in cs), solidas=set(c for c in corr_celdas if mundo.solida(c)), alto=cfg["alto"])
    g.pop("_BL", None)
    try:
        from . import audio_import as ai, guion_v2 as gv
        gu = ai.guion_de_escena(sc)
        if gu is not None:
            gu.setdefault("anclas", {})["tunel_inicio"] = cfg["frame_ini"]; gu["anclas"]["tunel_fin"] = fin; ai.guardar_en_escena(sc, gu)
    except Exception: pass
    sc["cerdo_1_st_tunel_ultimo"] = json.dumps({"inicio": list(inicio), "final": list(final), "frame_ini": cfg["frame_ini"], "frame_fin": fin, "golpes": len(ev), "celdas": len(ruta)})
    sc.frame_set(cfg["frame_ini"])
    return {"frame_fin": fin, "golpes": len(ev), "celdas_ruta": len(ruta), "celdas_cavadas": sum(len(c) for c in corredor_por_i), **g}


# ============================================================================================================================ capas ajenas al terreno
def _ocultar_ajenos():
    """oculta mientras se crea el tunel los objetos que NO son terreno real pero estan pegados a el (p. ej. `techo_tierra_bajo_pasto`: caras de tierra bajo el pasto,
    vistas desde dentro de la roca), para que no engañen a los rayos que deciden que celdas son roca"""
    ocu = [o for o in bpy.data.objects if o.name.startswith("techo_tierra") and not o.hide_viewport]
    for o in ocu: o.hide_viewport = True
    return ocu


_crear_base = crear


def crear(context, inicio, final, **kw):
    ocu = _ocultar_ajenos()
    try: return _crear_base(context, inicio, final, **kw)
    finally:
        for o in ocu: o.hide_viewport = False
