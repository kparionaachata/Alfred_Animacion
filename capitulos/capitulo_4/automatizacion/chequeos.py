# -*- coding: utf-8 -*-
"""CHEQUEOS AUTOMATICOS de una animacion (dentro de Blender). Recorre los frames y busca los errores tipicos:
  - SALTOS: un hueso, la raiz de un personaje o un objeto vigilado se mueve de golpe mucho mas que en los frames vecinos (p.ej. Jerry que salta en f562);
  - GIROS bruscos de huesos (volteretas por angulos que dan la vuelta);
  - RELEVOS: cuando un objeto se oculta y otro se muestra en su lugar (flecha en vuelo -> flecha clavada, sombrero puesto -> sombrero en la pata), que esten en el mismo sitio;
  - PEGADOS: objetos que deben ir pegados a un personaje (flechas clavadas) y quedan lejos de su cuerpo;
  - PENETRACION entre personajes (mallas que se solapan) fuera de los tramos permitidos (mordidas, golpes);
  - SUELO: vertices de los personajes hundidos en el suelo o en las paredes;
  - DISTANCIAS pedidas: contactos que deben llegar (el sombrero a la cabeza) o separaciones minimas;
  - AUDIO: archivos que faltan, tiras duplicadas, voces del mismo personaje encimadas, tiras fuera del rango.
La configuracion va en la seccion "chequeos" del .json de la cadena. Las expresiones de frames usan T = los tiempos de la escena (p.ej. "T['GOLPES_S'][0]")."""
import bpy, bmesh, math, os, fnmatch, time
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def _ev(x, T):
    return eval(str(x), {"T": T, "int": int, "round": round, "min": min, "max": max, "range": range, "list": list})


def _lista_frames(x, T):
    v = _ev(x, T)
    return [int(a) for a in v] if isinstance(v, (list, tuple, range)) else [int(v)]


def _coinciden(nombre, patrones):
    return any(fnmatch.fnmatchcase(nombre, p) for p in patrones)


class Personaje:
    def __init__(self, nombre, c):
        self.nombre = nombre
        self.arm = bpy.data.objects.get(c.get("armadura", ""))
        self.raiz = bpy.data.objects.get(c.get("raiz", "")) or (self.arm.parent if self.arm else None)
        pat = c.get("mallas", [])
        self.mallas = [o for o in bpy.data.objects if o.type == 'MESH' and _coinciden(o.name, pat)]

    def malla(self, dg):
        """vertices deformados del personaje (en el mundo, numpy) + su BVH (todo en C: rapido)"""
        bm = bmesh.new(); V = []
        for o in self.mallas:
            if o.hide_render or not o.visible_get(): continue                    # (visible_get del objeto evaluado siempre da False)
            e = o.evaluated_get(dg); me = e.to_mesh()
            if len(me.vertices):
                me.transform(e.matrix_world)
                co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); V.append(co.reshape(-1, 3)); bm.from_mesh(me)
            e.to_mesh_clear()
        if not V: bm.free(); return None, None
        t = BVHTree.FromBMesh(bm); bm.free()
        return np.concatenate(V), t


def _bvh(V, Tr):
    return BVHTree.FromPolygons([tuple(v) for v in V.tolist()], Tr.tolist(), all_triangles=True)


class Informe:
    def __init__(self): self.items = []; self.ok = []; self.info = []

    def add(self, nivel, tipo, sujeto, f, texto, valor=0.0, grupo=None):
        self.items.append([nivel, tipo, sujeto, int(f), texto, float(valor), grupo or sujeto])

    def agrupar(self):
        """frames seguidos (o casi) del mismo problema y del mismo personaje -> UNA linea (el peor caso + cuantos huesos/objetos)"""
        g = {}
        for nivel, tipo, suj, f, txt, val, gr in sorted(self.items, key=lambda x: (x[1], x[6], x[3])):
            k = (tipo, gr, nivel); L = g.setdefault(k, [])
            if L and f - L[-1]["hasta"] <= 3:
                L[-1]["hasta"] = max(L[-1]["hasta"], f); L[-1]["sujetos"].add(suj)
                if val > L[-1]["valor"]: L[-1].update(valor=val, texto=txt, frame=f)
            else: L.append(dict(nivel=nivel, tipo=tipo, sujeto=gr, desde=f, hasta=f, frame=f, texto=txt, valor=val, sujetos={suj}))
        out = [x for L in g.values() for x in L]
        for x in out:
            n = len(x.pop("sujetos"))
            if n > 1: x["texto"] += " (y %d huesos/objetos mas de %s)" % (n - 1, x["sujeto"])
        return sorted(out, key=lambda x: (0 if x["nivel"] == "error" else 1, -x["valor"]))


def _grupo(nombre):
    return nombre.split(":")[0].replace("raiz ", "") if not nombre.startswith("obj ") else nombre


def _rapido(c, f):
    """tramo donde los movimientos rapidos son a proposito (cachetadas, caidas, golpes): ahi solo se avisa de errores"""
    return any(a <= f <= b for a, b in c.get("_rapidos", []))


def _saltos(nombre, P, vis, inf, c, es_obj=False):
    """P: (n,3) posiciones por frame. Un SALTO = la velocidad de un frame es mucho mayor que la normal de sus vecinos."""
    if len(P) < 4: return
    v = np.linalg.norm(np.diff(P, axis=0), axis=1)                       # v[i]: de frames[i] a frames[i+1]
    umb = c.get("umbral_m", 0.08); tele = c.get("teleport_m", 0.6); k = c.get("factor", 5.0); w = 6
    for i in range(len(v)):
        if vis is not None and not (vis[i] and vis[i + 1]): continue
        if v[i] < umb: continue
        vec = np.concatenate([v[max(0, i - w):i], v[i + 1:i + 1 + w]])
        normal = float(np.median(vec)) if len(vec) else 0.0
        r = v[i] / max(normal, 0.004)
        f = c["_f0"] + i + 1; gr = _grupo(nombre)
        if v[i] >= tele and r >= 3: inf.add("error", "salto", nombre, f, "%s se teletransporta %.2f m en 1 frame (%.0fx lo normal)" % (nombre, v[i], r), v[i], gr)
        elif r >= k:
            if _rapido(c, f): continue                                         # tramo a proposito rapido: solo cuentan los teletransportes
            nivel = "error" if (v[i] > 0.2 and r >= 3 * k) else "aviso"
            if nivel == "aviso" and v[i] * r < c.get("puntaje_aviso", 1.5): continue   # pasos de un ciclo de caminar, etc.
            inf.add(nivel, "salto", nombre, f, "%s se mueve %.2f m en 1 frame (%.0fx lo normal de sus vecinos)" % (nombre, v[i], r), v[i], gr)


def _giros(nombre, Q, inf, c):
    """Q: (n,4) cuaterniones locales de un hueso. Velocidad angular de golpe mucho mayor que la de sus vecinos (volteretas)."""
    if len(Q) < 4: return
    d = np.abs(np.sum(Q[1:] * Q[:-1], axis=1)).clip(0, 1); ang = np.degrees(2 * np.arccos(d))
    umb = c.get("umbral_grados", 40.0); k = c.get("factor", 5.0); w = 6
    for i in range(len(ang)):
        if ang[i] < umb: continue
        vec = np.concatenate([ang[max(0, i - w):i], ang[i + 1:i + 1 + w]]); normal = float(np.median(vec)) if len(vec) else 0.0
        r = ang[i] / max(normal, 0.5)
        f = c["_f0"] + i + 1; nivel = "error" if ang[i] > 90 else "aviso"
        if r >= k and not _rapido(c, f):
            inf.add(nivel, "giro", nombre, f, "el hueso %s gira %.0f grados en 1 frame (%.0fx lo normal)" % (nombre, ang[i], r), ang[i], _grupo(nombre))


def _centro(o, dg):
    e = o.evaluated_get(dg); bb = [e.matrix_world @ Vector(p) for p in e.bound_box]
    return sum(bb, Vector()) / 8.0, max((bb[0] - bb[6]).length, 0.01)


def _visible(o):
    return not (o.hide_render or o.hide_viewport)


def _suelo(sc, dg, p, ignorar, alto):
    """z del suelo bajo p (rayo hacia abajo desde p.z+alto, saltando lo que se ignora); None si no hay nada"""
    o_ = Vector((p[0], p[1], p[2] + alto)); dist = alto + 3.0
    for _ in range(10):
        ok, loc, n, i, ob, m = sc.ray_cast(dg, o_, Vector((0, 0, -1)), distance=dist)
        if not ok: return None
        if ignorar(ob.original if hasattr(ob, "original") else ob):
            dist -= (o_ - loc).length + 0.001; o_ = loc - Vector((0, 0, 0.001))
            if dist <= 0: return None
            continue
        return loc.z
    return None


def _audio(sc, inf, c, rango):
    ed = sc.sequence_editor
    if not ed: return 0
    S = [s for s in ed.strips_all if s.type == 'SOUND']
    vistos = {}
    for s in S:
        ruta = bpy.path.abspath(s.sound.filepath) if s.sound else ""
        if not ruta or not os.path.isfile(ruta): inf.add("error", "audio", s.name, s.frame_final_start, "la tira %s usa un archivo que NO existe: %s" % (s.name, ruta or "(vacio)"), 1)
        k = (os.path.normcase(ruta), int(s.frame_final_start))
        if k in vistos and not s.mute: inf.add("error", "audio", s.name, s.frame_final_start, "tira DUPLICADA: %s y %s suenan el mismo archivo en el mismo frame" % (vistos[k], s.name), 1)
        vistos[k] = s.name
        if s.frame_final_end < rango[0] or s.frame_final_start > rango[1]: inf.add("aviso", "audio", s.name, s.frame_final_start, "la tira %s queda fuera del rango f%d-%d" % (s.name, rango[0], rango[1]), 0)
    for pj, pre in c.get("voces", {}).items():                            # dos voces del mismo personaje a la vez
        V = sorted((s for s in S if s.name.startswith(pre) and not s.mute), key=lambda s: s.frame_final_start)
        for a, b in zip(V, V[1:]):
            tag_a = a.get("tag", a.name.rsplit("_", 2)[0]); tag_b = b.get("tag", b.name.rsplit("_", 2)[0])
            if b.frame_final_start < a.frame_final_end - 1 and tag_a != tag_b:
                inf.add("aviso", "audio", pj, b.frame_final_start, "dos voces de %s se enciman: %s y %s (f%d-%d)" % (pj, a.name, b.name, b.frame_final_start, a.frame_final_end), a.frame_final_end - b.frame_final_start)
    return len(S)


def ejecutar(cfg, T, frame_inicial=None):
    """-> dict(items agrupados, ok, info, texto). `cfg` = seccion "chequeos" del .json."""
    import time
    t0 = time.time(); sc = bpy.context.scene; vl = bpy.context.view_layer; inf = Informe()
    r = cfg.get("rango", [sc.frame_start, sc.frame_end]); F0, F1 = int(_ev(r[0], T)), int(_ev(r[1], T))
    PJ = {n: Personaje(n, c) for n, c in cfg.get("personajes", {}).items()}
    vig_pat = cfg.get("vigilados", []); VIG = [o for o in bpy.data.objects if _coinciden(o.name, vig_pat)]
    rap = [(int(_ev(p["desde"], T)), int(_ev(p["hasta"], T))) for p in cfg.get("tramos_rapidos", [])]
    cs = dict(cfg.get("saltos", {})); cs["_f0"] = F0; cs["_rapidos"] = rap; cg = dict(cfg.get("giros", {})); cg["_f0"] = F0; cg["_rapidos"] = rap
    pen = cfg.get("penetracion", {}); suelo = cfg.get("suelo", {}); dists = cfg.get("distancias", []); peg = cfg.get("pegados", {})
    cada = int(cfg.get("cada", 2))
    perm = [(int(_ev(p["desde"], T)), int(_ev(p["hasta"], T)), p.get("motivo", "")) for p in pen.get("permitido", [])]
    ign_pre = tuple(suelo.get("ignorar_prefijos", [])); ign_suf = tuple(suelo.get("ignorar_sufijos", []))
    mallas_pj = {o.name for p in PJ.values() for o in p.mallas}; vig_n = {o.name for o in VIG}

    def ignorar(o):
        return (o.type != 'MESH' or o.name in mallas_pj or o.name in vig_n or o.name.startswith(ign_pre) or o.name.endswith(ign_suf)
                or (o.parent is not None and o.parent.type == 'ARMATURE'))
    dist_f = {}
    for d in dists:
        for f in _lista_frames(d["frames"], T): dist_f.setdefault(f, []).append(d)
    tt = {"frames": 0.0, "mallas": 0.0, "penetracion": 0.0, "suelo": 0.0, "distancias": 0.0}; _t = time.time
    pos = {}; rot = {}; visd = {}; nfr = 0; casts = 0; cob = {"penetracion": 0, "suelo": 0, "pegados": 0, "distancias": 0}
    for f in range(F0, F1 + 1):
        t_ = _t(); sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); nfr += 1
        for p in PJ.values():                                               # raiz y huesos (posiciones en el mundo, giros locales)
            if p.raiz: pos.setdefault("raiz " + p.nombre, []).append(tuple(p.raiz.matrix_world.translation))
            if p.arm:
                W = p.arm.matrix_world
                for pb in p.arm.pose.bones:
                    pos.setdefault("%s:%s" % (p.nombre, pb.name), []).append(tuple(W @ pb.head))
                    rot.setdefault("%s:%s" % (p.nombre, pb.name), []).append(tuple(pb.matrix_basis.to_quaternion()))
        cent = {}
        for o in VIG:
            c_, tam = _centro(o, dg); cent[o.name] = (c_, tam); pos.setdefault("obj " + o.name, []).append(tuple(c_)); visd.setdefault(o.name, []).append(_visible(o))
        # ---- relevos: un vigilado se oculta y otro de nombre parecido aparece en su lugar ----
        if f > F0:
            ocultos = [n for n in visd if visd[n][-2] and not visd[n][-1]]; nuevos = [n for n in visd if not visd[n][-2] and visd[n][-1]]
            for a in ocultos:
                for b in nuevos:
                    if not (a.startswith(b) or b.startswith(a)): continue
                    A1 = Vector(pos["obj " + a][-2]); A0 = Vector(pos["obj " + a][-3]) if len(pos["obj " + a]) > 2 else A1
                    B_ = Vector(pos["obj " + b][-1]); pred = A1 + (A1 - A0)            # donde estaria el que se oculta si siguiera (los ocultos no se evaluan)
                    d_ = min((B_ - A1).length, (B_ - pred).length)
                    lim = max(0.15, 0.5 * min(cent[a][1], cent[b][1]))
                    if d_ > lim: inf.add("error", "relevo", "%s->%s" % (a, b), f, "%s se cambia por %s pero estan a %.2f m (deberian coincidir)" % (a, b, d_), d_)
                    else: inf.ok.append("relevo %s -> %s en f%d: %.3f m" % (a, b, f, d_))
        malla = (f - F0) % cada == 0 or f in dist_f; tt["frames"] += _t() - t_
        if not malla: continue
        t_ = _t(); VV = {n: p.malla(dg) for n, p in PJ.items()}
        BV = {n: v[1] for n, v in VV.items()}; tt["mallas"] += _t() - t_
        # ---- penetracion entre personajes ----
        if (f - F0) % cada == 0:
            t_ = _t()
            for a, b in pen.get("pares", []):
                if BV.get(a) is None or BV.get(b) is None: continue
                n_ = len(BV[a].overlap(BV[b])); cob["penetracion"] += 1
                if n_ >= pen.get("min_pares", 4):
                    ok_ = [m for (x, y, m) in perm if x <= f <= y]
                    if not ok_: inf.add("aviso", "penetracion", "%s-%s" % (a, b), f, "las mallas de %s y %s se atraviesan (%d triangulos cruzados)" % (a, b, n_), n_)
            tt["penetracion"] += _t() - t_; t_ = _t()
            # ---- suelo ----
            for n in (suelo.get("personajes", []) if (f - F0) % int(suelo.get("cada", 4)) == 0 else []):
                V, _ = VV.get(n, (None, None))
                if V is None: continue
                cob["suelo"] += 1; zmin = V[:, 2].min(); cand = V[V[:, 2] < zmin + suelo.get("franja_m", 0.12)]
                if len(cand) > suelo.get("muestras", 16): cand = cand[np.linspace(0, len(cand) - 1, suelo.get("muestras", 16)).astype(int)]
                peor = 0.0; peor_p = None
                for p in cand:
                    z = _suelo(sc, dg, p, ignorar, suelo.get("alto_m", 0.35)); casts += 1
                    if z is not None and z - p[2] > peor: peor = z - p[2]; peor_p = p
                if peor > suelo.get("umbral_m", 0.05):
                    inf.add("aviso" if peor < 0.15 else "error", "suelo", n, f, "%s esta %.0f cm metido en el suelo/pared (en x %.2f y %.2f)" % (n, peor * 100, peor_p[0], peor_p[1]), peor)
            tt["suelo"] += _t() - t_
            # ---- pegados ----
            for patron, pj in peg.items():
                if BV.get(pj) is None: continue
                for o in VIG:
                    if not fnmatch.fnmatchcase(o.name, patron) or not _visible(o): continue
                    c_, tam = cent[o.name]; hit = BV[pj].find_nearest(c_); cob["pegados"] += 1
                    if hit[0] is not None and hit[3] > max(0.4, tam):
                        inf.add("error", "pegado", o.name, f, "%s deberia ir pegado a %s pero esta a %.2f m de su cuerpo" % (o.name, pj, hit[3]), hit[3])
        # ---- distancias pedidas (contactos / separaciones) ----
        t_ = _t()
        for d in dist_f.get(f, []):
            A = d["a"]; B = d["b"]
            def puntos(x):
                if x in PJ: return VV[x][0]
                o = bpy.data.objects.get(x)
                if o is None: return None
                e = o.evaluated_get(dg); me = e.data
                co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
                M = np.array(e.matrix_world, dtype=np.float64); return co @ M[:3, :3].T + M[:3, 3]
            def arbol(x):
                if x in PJ: return BV[x]
                o = bpy.data.objects.get(x)
                if o is None: return None
                e = o.evaluated_get(dg); me = e.data; me.calc_loop_triangles()
                t = np.empty(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get("vertices", t)
                return _bvh(puntos(x), t.reshape(-1, 3))
            PA = puntos(A); TB = arbol(B); cob["distancias"] += 1
            if PA is None or TB is None: inf.add("error", "distancia", d.get("nombre", A), f, "no encuentro %s o %s" % (A, B), 0); continue
            paso = max(1, len(PA) // 4000)
            dm = min((h[3] for h in (TB.find_nearest(Vector(p)) for p in PA[::paso]) if h[0] is not None), default=1e9)
            nom = d.get("nombre", "%s-%s" % (A, B))
            if "max_m" in d and dm > d["max_m"]: inf.add("error", "distancia", nom, f, "%s: %s NO llega a %s (queda a %.1f cm, maximo %.1f)" % (nom, A, B, dm * 100, d["max_m"] * 100), dm)
            elif "min_m" in d and dm < d["min_m"]: inf.add("error", "distancia", nom, f, "%s: %s esta demasiado cerca de %s (%.1f cm, minimo %.1f)" % (nom, A, B, dm * 100, d["min_m"] * 100), d["min_m"] - dm)
            else: inf.ok.append("%s (f%d): %.1f cm" % (nom, f, dm * 100))
        tt["distancias"] += _t() - t_
    # ---- analisis de las series ----
    for k, P in pos.items():
        vis = visd.get(k[4:]) if k.startswith("obj ") else None
        _saltos(k, np.array(P), vis, inf, cs)
    for k, Q in rot.items(): _giros(k, np.array(Q), inf, cg)
    n_aud = _audio(sc, inf, cfg.get("audio", {}), (F0, F1))
    if frame_inicial is not None: sc.frame_set(frame_inicial)
    G = inf.agrupar(); max_l = int(cfg.get("max_lineas", 25))
    E = [g for g in G if g["nivel"] == "error"]; A_ = [g for g in G if g["nivel"] == "aviso"]
    L = ["CHEQUEOS f%d-%d  (%d frames, %d personajes, %d objetos vigilados, %d tiras de audio, %.0f s)" % (F0, F1, nfr, len(PJ), len(VIG), n_aud, time.time() - t0),
         "RESULTADO: %s" % ("OK, sin problemas" if not G else "%d errores, %d avisos" % (len(E), len(A_)))]
    def linea(g):
        fr = "f%d" % g["desde"] if g["desde"] == g["hasta"] else "f%d-%d (peor f%d)" % (g["desde"], g["hasta"], g["frame"])
        return "  - [%s] %s" % (fr, g["texto"])
    if E: L += ["", "ERRORES:"] + [linea(g) for g in E[:max_l]] + (["  ... y %d mas" % (len(E) - max_l)] if len(E) > max_l else [])
    if A_: L += ["", "AVISOS (revisar):"] + [linea(g) for g in A_[:max_l]] + (["  ... y %d mas" % (len(A_) - max_l)] if len(A_) > max_l else [])
    if inf.ok: L += ["", "COMPROBADO OK:"] + ["  - " + x for x in inf.ok[:max_l]]
    L += ["", "REVISADO: saltos y giros en %d frames; %s" % (nfr, ", ".join("%s %d" % (k, v) for k, v in cob.items())),
          "TIEMPOS: " + ", ".join("%s %.0f s" % (k, v) for k, v in tt.items())]
    return dict(errores=len(E), avisos=len(A_), grupos=G, ok=inf.ok, texto="\n".join(L))
