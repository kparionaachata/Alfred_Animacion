# -*- coding: utf-8 -*-
"""RING: las dos VACAS espectadoras alientan a su luchador.
Pose base = la que dejo el usuario en vaca_ring (pezuna delantera izquierda en la barra, la derecha arriba), para las dos.
Encima, animacion propia de cada una (cuaterniones: base @ giro local) + reacciones a la pelea:
- vaca_ring (guardian): agita la pata derecha en circulos, sacude la cabeza, rebota.
- vaca2_ring (Alfred): golpea el aire con la pata (bombeo), cabecea rapido.
El pecho solo rebota hacia atras (hacia adelante entra en la valla). Repetible."""
import bpy, math, random
from mathutils import Euler, Quaternion

PUB = {"__name__": "pub"}
exec(open("C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/ring/publico_ribbits.py", encoding="utf-8").read(), PUB)
FIN = PUB["FIN"]; ss = PUB["ss"]

# pose de referencia del usuario (vaca_ring): hueso -> (location, rotation_quaternion)
REF = {"Chest": ((0, 0, 0), (0.9763, 0, 0, 0.2164)),
       "Leg:U:F:R": ((0.1157, -0.2481, 0), (0.6807, 0.676, 0.0022, 0.2846)),
       "Leg:L:F:R": ((0, 0, 0), (0.8547, 0.0311, -0.1692, 0.4895)),
       "Leg:U:F:L": ((0.0583, -0.5648, -0.2512), (0.8523, -0.0726, 0.0767, -0.5123)),
       "Leg:L:F:L": ((0, 0, 0), (0.9619, 0.0251, -0.2421, 0.1247)),
       "Head": ((0, 0, 0), (0.8351, 0.0915, -0.0575, -0.5394)),
       "Leg:U:B:R": ((0, 0, 0), (0.9526, 0, 0, -0.3043)),
       "Leg:U:B:L": ((0, 0, 0), (0.9526, 0, 0, -0.3043)),
       "Body": ((0, 0, 0), (1, 0, 0, 0)),
       "Leg:L:B:R": ((0, 0, 0), (1, 0, 0, 0)),
       "Leg:L:B:L": ((0, 0, 0), (1, 0, 0, 0))}

VACAS = [dict(nombre="vaca_ring", luchador="guard_ribbit_1", estilo="agita", per=15, fase=1.1, amp=1.0),
         dict(nombre="vaca2_ring", luchador="alfred", estilo="bombea", per=11, fase=3.0, amp=1.1)]


def modo_de(c, f):
    """tramos de 70-150 frames con un modo cada uno (no se repite el mismo dos veces seguidas); devuelve (modo, avance 0..1)"""
    if "tramos" not in c:
        rng = random.Random(c["nombre"] + "_tramos"); t = 1; tr = []; ultimo = None
        while t <= FIN:
            n = rng.randint(70, 150); m = rng.choice([x for x in ("rafaga", "descansa", "golpes") if x != ultimo])
            tr.append((t, t + n, m)); ultimo = m; t += n
        c["tramos"] = tr
    for a, b, m in c["tramos"]:
        if a <= f < b: return m, (f - a) / float(b - a)
    return "descansa", 0.0


def deltas(c, f, wc, wd):
    """giros locales en grados (x, y, z) sumados a la pose base"""
    ph = 2 * math.pi * f / c["per"] + c["fase"]; a = c["amp"]; d = {}
    d["Chest"] = (3 * abs(math.sin(ph)) * a + 4 * wc + 5 * wd, 0, 0)                   # solo hacia atras (+)
    d["Body"] = (0, 0, 3 * math.sin(ph * 0.5))
    if c["estilo"] == "agita":
        d["Leg:U:F:R"] = (20 * math.sin(ph) * a * (1 + 0.5 * wc), 0, 15 * math.cos(ph) * a)
        d["Leg:L:F:R"] = (18 * math.sin(ph + 0.9), 0, 0)
        d["Head"] = (8 * math.sin(ph * 0.5) - 10 * wc + 14 * wd, 0, 10 * math.sin(ph * 0.25))
    else:
        # sin repetir: el ritmo se acelera y frena, y alterna rafagas de bombeo, descansos y golpes sueltos
        ph = 2 * math.pi * f / c["per"] + c["fase"] + 1.6 * math.sin(2 * math.pi * f / 131.0) + 0.9 * math.sin(2 * math.pi * f / 53.0)
        bomba = max(0.0, math.sin(ph)) ** 2
        fuerza = a * (0.55 + 0.45 * math.sin(2 * math.pi * f / 97.0 + 0.7)) * (1 + 0.5 * wc)

        def valor(modo, u):
            if modo == "rafaga": return 28 * bomba * fuerza, 6 * math.sin(ph * 0.5), 22 * bomba
            if modo == "descansa": return 6 + 5 * math.sin(2 * math.pi * f / 47.0), 8 * math.sin(2 * math.pi * f / 61.0), 8.0
            g = max(0.0, math.sin(math.pi * min(1.0, (u * 3.0) % 1.0 * 2.2))) ** 3     # golpes sueltos: uno cada tanto, seco
            return 32 * g * fuerza, 3 * math.sin(ph * 0.3), 26 * g
        modo, u = modo_de(c, f); x, z, dob = valor(modo, u)
        tr = next(t for t in c["tramos"] if t[0] <= f < t[1]) if any(t[0] <= f < t[1] for t in c["tramos"]) else None
        if tr and f - tr[0] < 10 and tr[0] > 1:                                   # transicion suave desde el modo anterior
            mp, up = modo_de(c, tr[0] - 1); xp, zp, dp = valor(mp, up); k = ss((f - tr[0]) / 10.0)
            x, z, dob = xp + (x - xp) * k, zp + (z - zp) * k, dp + (dob - dp) * k
        d["Leg:U:F:R"] = (x + 10 * wc, 0, z)
        d["Leg:L:F:R"] = (dob, 0, 0)
        d["Head"] = (3 * math.sin(2 * math.pi * f / 37.0) - 8 * wc + 10 * wd, 0, 5 * math.sin(2 * math.pi * f / 190.0))   # poca oscilacion, lenta
    d["Leg:U:F:L"] = (2 * math.sin(ph * 0.5), 0, 0)
    d["Leg:U:B:R"] = (3 * math.sin(ph * 0.5), 0, 0)
    d["Leg:U:B:L"] = (-3 * math.sin(ph * 0.5), 0, 0)
    return d


def claves(obj, nombre, canales):
    obj.animation_data_create()
    viejo = bpy.data.actions.get(nombre)
    if viejo: bpy.data.actions.remove(viejo)
    act = bpy.data.actions.new(nombre); obj.animation_data.action = act
    for path, cl in canales.items():
        for i in range(len(cl[0][1])):
            fc = act.fcurve_ensure_for_datablock(obj, path, index=i); fc.keyframe_points.add(len(cl))
            fc.keyframe_points.foreach_set("co", [x for f, v in cl for x in (f, v[i])]); fc.update()
    return act


def construir():
    ev = PUB["eventos"](); out = {}
    for c in VACAS:
        r = bpy.data.objects[c["nombre"]]
        arm = next(x for x in r.children_recursive if x.type == 'ARMATURE' and len(x.pose.bones) > 3 and "extras" not in x.name)
        rr = random.Random(c["nombre"])
        fr = dict(nombre=c["nombre"], luchador=c["luchador"], seed=rr.randint(0, 10 ** 6), prob=0.9, retraso=rr.randint(2, 6),
                  dur=rr.randint(18, 28), salto=0.0)
        cel, des, _sal = PUB["capas_evento"](fr, ev)
        if c["nombre"] == "vaca2_ring":
            out[c["nombre"]] = construir_vaca2(c, arm, cel, des); continue
        canales = {}; prev = {}
        for h in REF:
            arm.pose.bones[h].rotation_mode = 'QUATERNION'
            canales['pose.bones["%s"].rotation_quaternion' % h] = []; canales['pose.bones["%s"].location' % h] = []
        for f in range(1, FIN + 1):
            wc = cel.get(f, 0.0); wd = des.get(f, 0.0); d = deltas(c, f, wc, wd)
            for h, (lo, q0) in REF.items():
                dd = d.get(h, (0, 0, 0))
                q = Quaternion(q0) @ Euler([math.radians(v) for v in dd]).to_quaternion()
                if h in prev and prev[h].dot(q) < 0: q.negate()                       # continuidad
                prev[h] = q
                canales['pose.bones["%s"].rotation_quaternion' % h].append((f, tuple(q)))
                canales['pose.bones["%s"].location' % h].append((f, tuple(lo)))
        claves(arm, c["nombre"] + "_anima", canales)
        out[c["nombre"]] = dict(celebra_s=round(sum(1 for v in cel.values() if v > 0.5) / 24, 1), desanima_s=round(sum(1 for v in des.values() if v > 0.5) / 24, 1))
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    return out


# ------------------------------------------------------------------ vaca2_ring: organica (resortes, retrasos) y golpes a la barra
HIT = ((-60, -102, -60), (-40, 0, 0))          # giro extra (hombro, codo) que deja la pezuna derecha sobre la barra (medido)
TRAMOS_V2 = [(1, 100, "golpes"), (100, 190, "descansa"), (190, 262, "golpea_valla"), (262, 340, "rafaga"), (340, 430, "descansa"),
             (430, 520, "golpea_valla"), (520, 600, "golpes"), (600, 690, "rafaga"), (690, FIN + 1, "descansa")]


def construir_vaca2(c, arm, cel, des):
    rng = random.Random("vaca2_golpes"); hits = []
    for a, b, m in TRAMOS_V2:
        if m == "golpea_valla":
            t = a + 8
            while t < b - 14:
                d = rng.randint(14, 22); hits.append((t, d)); t += d + rng.randint(0, 7)
    en_tramo = lambda f: next((m for a, b, m in TRAMOS_V2 if a <= f < b), "descansa")

    def h_de(f):                                                                # 0 = pata arriba, 1 = pezuna en la barra
        for t0, d in hits:
            u = f - t0
            if 0 <= u < d:
                baja = int(d * 0.45)
                if u < baja: return ss(u / float(baja)) ** 1.6                    # cae acelerando
                if u < baja + 2: return 1.0                                       # impacto
                return 1.0 - 0.85 * ss((u - baja - 2) / float(d - baja - 2))      # rebota hacia arriba
        return 0.15 if en_tramo(f) == "golpea_valla" else 0.0
    contactos = [t0 + int(d * 0.45) for t0, d in hits]

    def impacto(f, retraso=0):
        return sum(math.exp(-(f - retraso - tc) / 4.0) for tc in contactos if f - retraso >= tc and f - retraso - tc < 20)
    qhit_u = Quaternion(REF["Leg:U:F:R"][1]) @ Euler([math.radians(v) for v in HIT[0]]).to_quaternion()
    qhit_l = Quaternion(REF["Leg:L:F:R"][1]) @ Euler([math.radians(v) for v in HIT[1]]).to_quaternion()
    estado = {}; canales = {}
    for h in REF:
        arm.pose.bones[h].rotation_mode = 'QUATERNION'
        canales['pose.bones["%s"].rotation_quaternion' % h] = []; canales['pose.bones["%s"].location' % h] = []
    for f in range(1, FIN + 1):
        wc = cel.get(f, 0.0); wd = des.get(f, 0.0); modo = en_tramo(f)
        cc = dict(c); cc["tramos"] = TRAMOS_V2
        d = deltas(cc, f, wc, wd) if modo != "golpea_valla" else deltas(dict(cc, tramos=[(1, FIN + 1, "descansa")]), f, 0.0, wd)
        hh = h_de(f); imp = impacto(f); imp_cab = impacto(f, 3)
        # secundarios: el pecho recibe el golpe, la cabeza acompana con retraso, el cuerpo sigue el ritmo
        d["Chest"] = (d["Chest"][0] + 3.5 * imp, 0, 2 * math.sin(2 * math.pi * f / 83.0))
        d["Head"] = (d["Head"][0] + 7 * imp_cab, 0, d["Head"][2] - 4 * imp_cab)
        d["Body"] = (0, 0, d["Body"][2] + 2 * math.sin(2 * math.pi * f / 71.0 + 1.3))
        for h, (lo, q0) in REF.items():
            dd = d.get(h, (0, 0, 0)); q = Quaternion(q0) @ Euler([math.radians(v) for v in dd]).to_quaternion()
            if h == "Leg:U:F:R": q = q.slerp(qhit_u, hh)
            if h == "Leg:L:F:R": q = q.slerp(qhit_l, hh)
            # resorte: nada salta de golpe (la pata cuando cae va mas firme para que el golpe sea seco)
            k = 0.85 if (h.startswith("Leg:") and hh > 0.2) else (0.45 if h.startswith("Leg:") else 0.28)
            if h in estado:
                q_prev = estado[h]
                if q_prev.dot(q) < 0: q.negate()
                q = q_prev.slerp(q, k)
            estado[h] = q.copy()
            canales['pose.bones["%s"].rotation_quaternion' % h].append((f, tuple(q)))
            canales['pose.bones["%s"].location' % h].append((f, tuple(lo)))
    claves(arm, c["nombre"] + "_anima", canales)
    return dict(golpes_a_la_barra=len(hits), contactos=contactos)
