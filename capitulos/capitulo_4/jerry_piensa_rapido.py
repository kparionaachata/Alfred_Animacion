# -*- coding: utf-8 -*-
"""alfred_cueva_4.blend: antes de lanzar el carbon Jerry dice "Alfred!" y "piensa rapido" (scripts de la app animacion_jerry (23)/(24)).
Reutiliza jerry_responde_pensando.cara()/audio() (capas ADITIVAS de ojos, pupilas, parpadeo, mandibula, hocico, cabeza y cejas + tira del VSE)
sobre la animacion horneada de jerry_pica_carbon.py. Ademas pone los sonidos del juego de la escena (etiqueta mcsnd_origen = "jerry_lanza").
Uso: exec(open(ruta, encoding="utf8").read()); construir(f_voz, datos)      (f_voz y datos = lo que devuelve jerry_pica_carbon.construir())
"""
import bpy, sys, importlib.util

BASE = r"C:/Users/user/Desktop/Alfred_Animacion/capitulos/capitulo_4/"
VOCES = [  # (desfase desde f_voz, script de la app, audio, etiqueta)
    (1, BASE + "voces_piensa_rapido/animacion_jerry_alfred.py", r"C:/Users/user/Desktop/Alfred_Animacion/audios/jerry/jerry_alfred.wav", "VozJerry_alfred"),
    (16, BASE + "voces_piensa_rapido/animacion_jerry_piensa_rapido.py", r"C:/Users/user/Desktop/Alfred_Animacion/audios/jerry/jerry_piensa_rapido.wav", "VozJerry_piensa_rapido"),
]
ORIGEN = "jerry_lanza"


def _base_en_nla():
    """la accion horneada de Jerry pasa a una pista NLA de abajo, para que las capas aditivas de la voz se sumen encima"""
    ad = bpy.data.objects["Dog_001_rig"].animation_data; act = ad.action
    if act is None: return
    slot = ad.action_slot; ad.action = None
    tr = ad.nla_tracks.new(); tr.name = "Jerry_base"                 # jerry_pica_carbon borra las pistas: queda la primera (abajo)
    st = tr.strips.new("Jerry_base", int(act.frame_range[0]), act); st.blend_type = 'REPLACE'; st.extrapolation = 'HOLD'
    try: st.action_slot = slot
    except Exception: pass


OJOS_BASE = {   # valores reales de alfred_cueva_4.blend (con pistas NLA los canales sin pista vuelven a 0 y los ojos desaparecen)
    "ojo_izquierdo_jerry": ((-0.10573162, 0.70520961, 0.69979072), ("Feliz", "Triste", "Enojado", "Sospecha", "Cerrado", "Cansado", "Sorpresa", "Closed")),
    "ojo_derecho_jerry": ((0.10579580, 0.70477539, 0.70012289), ("Feliz", "Triste", "Enojado", "Sospecha", "Cerrado", "Cansado", "Sorpresa", "Closed")),
    "pupila_izquierda_jerry": ((0.09395468, 0.70372331, 0.68799782), ("Closed",)),
    "pupila_derecha_jerry": ((-0.09345061, 0.70350409, 0.68887675), ("Closed",)),
}


def _pista_base(idb, nombre, canales):
    ad = idb.animation_data or idb.animation_data_create()
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    vieja = bpy.data.actions.get(nombre)
    if vieja: bpy.data.actions.remove(vieja)
    act = bpy.data.actions.new(nombre); slot = act.slots.new(idb.id_type, idb.name)
    cb = act.layers.new("Layer").strips.new(type='KEYFRAME').channelbags.new(slot)
    for (ruta, i), v in canales.items(): cb.fcurves.new(ruta, index=i).keyframe_points.insert(1, v)
    tr = ad.nla_tracks.new(); tr.name = nombre
    st = tr.strips.new(nombre, 1, act); st.blend_type = 'REPLACE'; st.extrapolation = 'HOLD'
    try: st.action_slot = slot
    except Exception: pass


def _base_ojos():
    for n, (loc, formas) in OJOS_BASE.items():
        o = bpy.data.objects[n]
        _pista_base(o, "JerryOjos_base_" + n, {**{("location", i): loc[i] for i in range(3)}, **{("scale", i): 1.0 for i in range(3)}})
        _pista_base(o.data.shape_keys, "JerryOjos_base_formas_" + n, {(f'key_blocks["{k}"].value', 0): 0.0 for k in formas})


def _voces(f_voz):
    _base_en_nla(); _base_ojos(); hechas = []
    for d, script, audio, tag in VOCES:
        ns = {"__name__": "jerry_voz_" + tag}; exec(open(BASE + "jerry_responde_pensando.py", encoding="utf8").read(), ns)
        ns.update(F0=f_voz + d, SCRIPT_APP=script, AUDIO=audio, TAG=tag)
        ns["quitar"](); c = ns["constantes"](); ns["cara"](c); hechas.append((tag, ns["audio"]()))
    return hechas


def _sonidos(d):
    sc = bpy.context.scene; ed = sc.sequence_editor
    m = sys.modules.get("alfred_sonidos_local")
    if m is None:
        spec = importlib.util.spec_from_file_location("alfred_sonidos_local", BASE + "alfred_sonidos/__init__.py")
        m = importlib.util.module_from_spec(spec); sys.modules["alfred_sonidos_local"] = m; spec.loader.exec_module(m)
    p = sc.mcsnd; m.indice(p, forzar=True)
    for t in [t for t in ed.strips_all if t.get("mcsnd_origen") == ORIGEN]: ed.strips.remove(t)
    rng = m.rng_de(p); puestos = []
    def poner(ev, f, vol):
        r = m.rutas_de(p, ev)
        if r:
            t = m.colocar(bpy.context, p, r, int(f), "golpes", ev.replace(".", "_"), vol, 0, rng); t["mcsnd_origen"] = ORIGEN; puestos.append((ev, int(f)))
    poner("block.stone.fall", d["suelta_pico"] + 11, 0.9)              # el pico cae al suelo
    poner("entity.item.pickup", d["agarre"], 0.7)                       # coge el carbon con la boca
    poner("entity.player.attack.sweep", d["lanza"], 1.0)              # lo lanza como un disco: zumbido del giro
    poner("entity.player.attack.strong", d["impacto"], 1.0)             # le da en la cara
    poner("entity.player.hurt", d["impacto"] + 1, 1.0)
    poner("block.pointed_dripstone.hit", d["impacto"] + 6, 1.0)          # choca con la estalagmita
    poner("entity.player.attack.knockback", d["impacto"] + 6, 0.8)
    poner("entity.player.small_fall", d["impacto"] + 52, 0.8)           # termina de sentarse
    # cada carbon que rebota en el suelo
    sc.frame_set(d["fin"])
    for o in bpy.data.objects:
        if not o.name.startswith("coal_") or "suelto_-83_-12" in o.name or not o.visible_get(): continue   # solo los que acaban en el suelo
        fcz = None
        if o.animation_data and o.animation_data.action:
            for lay in o.animation_data.action.layers:
                for st in lay.strips:
                    for cb in st.channelbags: fcz = fcz or cb.fcurves.find("location", index=2)
        if fcz is None: continue
        f0 = d["impacto"]; zs = [(f, fcz.evaluate(f)) for f in range(f0, d["fin"] + 1)]; zmin = min(z for _, z in zs)
        n = 0
        for i in range(1, len(zs)):                                     # cada rebote: golpe seco, mas suave cuanto menos rapido cae
            if zs[i][1] <= zmin + 0.002 and zs[i - 1][1] > zmin + 0.002:
                vel = zs[i - 1][1] - zs[i][1] + (zs[i - 2][1] - zs[i - 1][1] if i > 1 else 0.0)
                vol = max(0.18, min(0.75, vel * 6.0)) * (0.8 ** n)
                poner("block.stone.hit" if n == 0 else "block.stone.step", zs[i][0], round(vol, 2)); n += 1
    return puestos


def construir(f_voz, datos):
    return {"voces": _voces(f_voz), "sonidos": _sonidos(datos)}
