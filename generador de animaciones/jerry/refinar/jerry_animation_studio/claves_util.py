# -*- coding: utf-8 -*-
"""
claves_util.py -- Jerry Animation Studio: escritura de claves por la API de fcurves, comun a `motor_alfred` (huesos), `camara_guion` (camara / foco / lente) y futuros modulos.

POR QUE no `keyframe_insert`: si el objeto tiene pistas NLA (Voz Sync deja la accion del personaje como pista `Base_*`), `keyframe_insert` crea una accion ACTIVA nueva que tapa toda la animacion del NLA. Aqui las claves se
escriben en la accion donde ya estan (`accion_destino`), sin crear nada que tape otra cosa. Necesita bpy solo para tipos que recibe (no lo importa).
"""


def fcurves(act):
    try: return list(act.fcurves)
    except AttributeError:                                                                  # Blender 5: accion -> capa -> tira -> channelbag -> fcurves
        return [fc for l in act.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


def accion_destino(ob, ruta0, idx0, frame):
    """la accion donde escribir las claves de `ob`: la activa; si no hay (Voz Sync la paso al NLA como pista `Base_*`) la de esa pista; si tampoco, se crea con una clave. NUNCA se crea una accion activa
    nueva encima de un NLA con animacion (taparia todo lo que no se toca)."""
    ad = ob.animation_data or ob.animation_data_create()
    if ad.action: return ad.action
    for t in ad.nla_tracks:
        if t.name.startswith("Base") and t.strips and t.strips[0].action: return t.strips[0].action
    if ad.nla_tracks and any(t.strips for t in ad.nla_tracks): raise RuntimeError("%s tiene pistas NLA pero ninguna `Base_*`: no se sabe donde escribir (no se crea una accion que las tape)" % ob.name)
    try: ob.keyframe_insert(ruta0, index=idx0, frame=frame)
    except TypeError: ob.keyframe_insert(ruta0, frame=frame)                              # propiedad que no es un vector (lens, apertura...): no admite `index`
    return ob.animation_data.action


def slot_de(idb, act):
    """el slot (Blender 5) con que `idb` usa `act`: el de su animation_data o el de la tira NLA que la tiene; None si no hay slots."""
    ad = idb.animation_data
    if ad is None: return None
    if ad.action == act: return getattr(ad, "action_slot", None)
    for t in ad.nla_tracks:
        for s in t.strips:
            if s.action == act: return getattr(s, "action_slot", None)
    return None


def escritor_de(idb, ruta0, idx0, frame):
    """Escritor para las claves de `idb` (objeto o datos): la accion donde ya estan (`accion_destino`) y SU slot (en Blender 5 una accion puede traer curvas de varios datablocks en slots distintos: una
    curva creada en el slot equivocado existe pero no anima nada)."""
    act = accion_destino(idb, ruta0, idx0, frame); return Escritor(act, slot_de(idb, act))


class Escritor:
    """escribe claves en una accion con la API de fcurves (rapido, sin tocar la accion activa del objeto).

    IMPORTANTE (error real, 2026-10-05): `keyframe_points.add()` REASIGNA el arreglo de claves; cualquier referencia a una clave guardada antes (`p`) queda colgando y escribir por ella corrompe OTRAS claves de la curva.
    Por eso `poner` solo ANOTA (frame -> valor) y `aplicar` / `cerrar` escribe todo de golpe: primero los valores de las claves que ya existen (por indice, releyendo la curva), luego UN solo `add(n)` y se rellenan
    las nuevas sin guardar ninguna referencia."""

    def __init__(self, act, slot=None):
        self.act = act; self.slot = slot; self.pend = {}; self.tocadas = set()
        if slot is not None and hasattr(act, "layers"):                                     # solo las curvas del slot de este datablock
            self.fc = {}
            for l in act.layers:
                for s in l.strips:
                    cb = s.channelbag(slot)
                    if cb is not None:
                        for f in cb.fcurves: self.fc[(f.data_path, f.array_index)] = f
        else: self.fc = {(f.data_path, f.array_index): f for f in fcurves(act)}

    def _curva(self, ruta, idx):
        fc = self.fc.get((ruta, idx))
        if fc is None:
            if self.slot is not None and hasattr(self.act, "layers"): cb = self.act.layers[0].strips[0].channelbag(self.slot, ensure=True)
            else: cb = next(cb for l in self.act.layers for s in l.strips for cb in s.channelbags)
            fc = cb.fcurves.new(ruta, index=idx); self.fc[(ruta, idx)] = fc
        return fc

    def poner(self, ruta, idx, frame, valor, interp=None):
        self._curva(ruta, idx); self.pend.setdefault((ruta, idx), {})[int(frame)] = (float(valor), interp)

    def existe(self, ruta, idx):
        return (ruta, idx) in self.fc

    def aplicar(self):
        """escribe lo anotado (ver arriba)."""
        for (ruta, idx), datos in self.pend.items():
            fc = self.fc[(ruta, idx)]; kp = fc.keyframe_points; ya = {int(round(kp[i].co[0])): i for i in range(len(kp))}; nuevos = []
            for fr, (v, interp) in datos.items():
                if fr in ya:
                    kp[ya[fr]].co[1] = v
                    if interp: kp[ya[fr]].interpolation = interp
                else: nuevos.append((fr, v, interp))
            if nuevos:
                n0 = len(kp); kp.add(len(nuevos))
                for j, (fr, v, interp) in enumerate(nuevos):
                    p = kp[n0 + j]; p.co = (fr, v); p.interpolation = interp or 'BEZIER'; p.handle_left_type = p.handle_right_type = 'AUTO_CLAMPED'
            fc.update(); self.tocadas.add((ruta, idx))
        self.pend.clear()

    def limpiar(self, ruta, idx, f0=None, f1=None):
        """quita las claves de la curva con frame en [f0, f1] (None = sin limite). -> cuantas."""
        self.aplicar()
        if (ruta, idx) not in self.fc: return 0
        fc = self.fc[(ruta, idx)]; n = 0
        for i in range(len(fc.keyframe_points) - 1, -1, -1):
            f = fc.keyframe_points[i].co[0]
            if (f0 is None or f >= f0 - 1e-6) and (f1 is None or f <= f1 + 1e-6): fc.keyframe_points.remove(fc.keyframe_points[i]); n += 1
        self.tocadas.add((ruta, idx)); return n

    def evaluar(self, ruta, idx, frame):
        """valor de la curva en `frame` (la ultima clave se mantiene)."""
        self.aplicar(); fc = self.fc[(ruta, idx)]; fc.update(); return fc.evaluate(frame)

    def cerrar(self):
        self.aplicar()
        for k in self.tocadas: self.fc[k].update()
