# -*- coding: utf-8 -*-
"""alfred_cueva_5E.blend: mientras la criatura trepa, cada vez que una mano o un pie se agarra a la pared (o al techo) se desprenden trocitos de piedra que caen (gravedad, rebotan hacia fuera de la superficie
y se detienen al chocar con la caverna), mas un estallido grande en el impacto del aterrizaje. Cubitos reutilizados de un grupo (objetos pcl_trepa_NNN, material de caverna_stone) con claves de posicion y escala.
Requiere ejecutados antes: stalker_trepa_base.py, stalker_trepa_pared.py, stalker_trepa_ruta.py, y planear/preparar_plan/trayecto (P, bv).
Uso: emitir(bv, P)  (borra los pcl_trepa_* anteriores y los rehace)"""
import bpy, math, random
from mathutils import Vector

G = Vector((0, 0, -9.8))
POOL = 110
PREFIJO = "pcl_trepa_"


def _material():
    o = bpy.data.objects.get("caverna_stone")
    return o.material_slots[0].material if o and o.material_slots else None


def _pool():
    for o in [o for o in bpy.data.objects if o.name.startswith(PREFIJO)]:
        bpy.data.objects.remove(o)
    me = bpy.data.meshes.get("pcl_trepa_cubo")
    if me is None:
        me = bpy.data.meshes.new("pcl_trepa_cubo")
        v = [(x, y, z) for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5)]
        f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        me.from_pydata(v, [], f)
        me.update()
        mat = _material()
        if mat:
            me.materials.append(mat)
    col = bpy.context.scene.collection
    obs = []
    for i in range(POOL):
        o = bpy.data.objects.new("%s%03d" % (PREFIJO, i), me)
        col.objects.link(o)
        o.scale = (0, 0, 0)
        o.keyframe_insert("scale", frame=1)
        obs.append(o)
    return obs


def _vida(bv, p0, v0, fr0, vmax):
    """puntos de la trayectoria cada 2 frames hasta chocar con la caverna o agotar la vida: [(frame, pos)]"""
    pts = [(fr0, p0.copy())]
    p = p0.copy()
    for k in range(1, vmax // 2 + 1):
        t = 2 * k / 24.0
        q = p0 + v0 * t + 0.5 * G * t * t
        d = q - p
        L = d.length
        if L > 1e-6:
            r = bv.ray_cast(p, d / L, L)
            if r[0] is not None:
                pts.append((fr0 + 2 * k, r[0]))
                break
        pts.append((fr0 + 2 * k, q.copy()))
        p = q
    return pts


def emitir(bv, P, semilla=7):
    rng = random.Random(semilla)
    obs = _pool()
    libre = [0] * POOL                                    # frame desde el que cada cubito esta libre
    eventos = []
    # agarres de la trepada
    for n in NEUTRO:
        m = 1
        while True:
            td = F_L1 - BETA_T * T_TREPA + FASE[n] * T_TREPA + m * T_TREPA
            if td > P["f_llega"]:
                break
            if td > F_L1:
                a, pit, yaw, roll = cuerpo(bv, P, int(td))
                nrm = R_de(pit, yaw, roll) @ Vector((0, 0, 1))
                eventos.append((int(td), _plantas_trepa(P, bv, n, m), nrm, 3 + rng.randint(0, 2), 0.14 if n[0] == "H" else 0.11))
            m += 1
    # impacto del aterrizaje (manos y pies en el muro)
    for n in NEUTRO:
        eventos.append((F_J1, P["hit_mano"][n] if n[0] == "H" else P["plant0"][n], Vector((0, -1, 0)), 7, 0.22))
    eventos.sort(key=lambda e: e[0])
    n_p = 0
    sin_hueco = 0
    for fr, pos, nrm, cuantas, tam in eventos:
        for _ in range(cuantas):
            idx = next((i for i in range(POOL) if libre[i] <= fr - 2), None)
            if idx is None:
                sin_hueco += 1
                continue
            tang = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
            tang -= nrm * tang.dot(nrm)
            v0 = nrm * rng.uniform(0.4, 1.4) + tang * rng.uniform(0.3, 1.1)
            if fr == F_J1:
                v0 = nrm * rng.uniform(1.0, 3.0) + tang * rng.uniform(0.8, 2.2)
            p0 = pos + nrm * 0.05 + tang * 0.12
            s = tam * rng.uniform(0.5, 1.2)
            vida = rng.randint(30, 50)
            pts = _vida(bv, p0, v0, fr, vida)
            o = obs[idx]
            o.rotation_mode = 'XYZ'
            r0 = Vector((rng.uniform(0, 6.28), rng.uniform(0, 6.28), rng.uniform(0, 6.28)))
            w = Vector((rng.uniform(-6, 6), rng.uniform(-6, 6), rng.uniform(-6, 6)))
            o.location = pts[0][1]
            o.scale = (0, 0, 0)
            o.keyframe_insert("scale", frame=fr - 1)
            o.scale = (s, s, s)
            o.keyframe_insert("scale", frame=fr)
            for (f_, q) in pts:
                o.location = q
                o.rotation_euler = r0 + w * ((f_ - fr) / 24.0)
                o.keyframe_insert("location", frame=f_)
                o.keyframe_insert("rotation_euler", frame=f_)
            fin = pts[-1][0]
            o.scale = (s * 0.5, s * 0.5, s * 0.5)
            o.keyframe_insert("scale", frame=fin)
            o.scale = (0, 0, 0)
            o.keyframe_insert("scale", frame=fin + 1)
            libre[idx] = fin + 2
            n_p += 1
    return {"eventos": len(eventos), "particulas": n_p, "sin_hueco": sin_hueco}
