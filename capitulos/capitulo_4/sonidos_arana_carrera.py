# -*- coding: utf-8 -*-
"""Sonidos de Minecraft de la arana (aparece, salta, cae en la cara de Alfred y chilla/escarba mientras sigue pegada), de Alfred corriendo
en circulos sobre piedra (un paso por cada apoyo de pie, detectado de la animacion), del giro de Alfred y del giro de alerta de Jerry.
Usa el add-on Alfred Sonidos (tiras SND_, etiqueta mcsnd_origen = ORIGEN; se borran y se rehacen). Uso: exec(open(ruta).read()); sonorizar()
Frames: arana_salta_cara.py (F_APARECE, F_SALTA, F_CARA), alfred_corre_circulos.py (F_INI), alfred_mira_arana.py, jerry_responde_pensando.py (GIRO_INI).
"""
import bpy, importlib.util, sys, random
from mathutils import Vector

ADDON = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_sonidos\__init__.py"
ORIGEN = "arana_carrera"
F_APARECE, F_AGACHA, F_SALTA, F_CARA = 522, 528, 534, 546
F_GIRO_ALFRED = 532                    # Alfred voltea a mirar la arana (532-542)
F_GIRO_JERRY = 527                     # Jerry voltea en alerta (527-543)
F_CORRE = 556
PIES = ("Rightknee_alfred", "Leftknee_alfred")      # la cola del hueso de la rodilla es el pie


def cargar_addon():
    m = sys.modules.get("alfred_sonidos_local")
    if m is None:
        spec = importlib.util.spec_from_file_location("alfred_sonidos_local", ADDON)
        m = importlib.util.module_from_spec(spec); sys.modules["alfred_sonidos_local"] = m
        spec.loader.exec_module(m); m.register()
    return m


PERIODO = 14                           # alfred_corre_circulos.PERIODO: 2 apoyos por ciclo


def apoyos(f0, f1):
    """apoyos de la carrera de alfred_corre_circulos: el pie toca el suelo cuando la pierna llega adelante (sin(fase) = 1),
    derecho en t = PERIODO/4 y el izquierdo medio ciclo despues -> un paso cada PERIODO/2 frames."""
    out = []; t = PERIODO / 4.0
    while f0 + t <= f1:
        out.append(int(round(f0 + t))); t += PERIODO / 2.0
    return out


def sonorizar():
    m = cargar_addon(); sc = bpy.context.scene; p = sc.mcsnd; m.indice(p, forzar=True)
    ed = sc.sequence_editor or sc.sequence_editor_create()
    for t in [t for t in m._strips(ed) if t.name.startswith(m.PREFIJO) and t.get("mcsnd_origen") == ORIGEN]: m._strips(ed).remove(t)
    rng = m.rng_de(p); puestos = []; fin = sc.frame_end; f_act = sc.frame_current

    def poner(evento, frame, vol=1.0, grupo="golpes"):
        rutas = m.rutas_de(p, evento)
        if not rutas: print("sin sonido:", evento); return
        t = m.colocar(bpy.context, p, rutas, int(frame), grupo, evento.replace(".", "_"), vol, 0, rng)
        if t: t["mcsnd_origen"] = ORIGEN; puestos.append((t.name, int(frame)))

    # --- arana: aparece, se agacha y salta, cae en la cara
    poner("entity.spider.ambient", F_APARECE, 0.9, "voces")
    for f in (F_APARECE + 2, F_APARECE + 4):
        poner("entity.spider.step", f, 0.5, "pasos")
    poner("entity.spider.step", F_AGACHA, 0.6, "pasos")
    poner("entity.spider.ambient", F_SALTA, 1.0, "voces")
    poner("entity.player.attack.knockback", F_CARA, 0.9, "golpes")          # golpe sordo contra la cara (sin entity.player.hurt)
    poner("entity.spider.step", F_CARA + 1, 0.8, "pasos")                   # las patas se cierran sobre la cabeza
    poner("entity.spider.step", F_CARA + 5, 0.6, "pasos")
    # --- mientras sigue pegada: chillidos cada ~1.5 s (sin pasos repetidos de la arana, pedido del usuario), hasta el choque
    emp = bpy.data.objects["alfred"]; f_choque = int(emp.get("f_choque", fin)); f_suelo = int(emp.get("f_suelo", 0))
    r = random.Random(7)
    f = F_CARA + 20
    while f < min(fin, f_choque) - 4:
        poner("entity.spider.ambient", f, 0.7, "voces"); f += r.randint(30, 42)
    # --- choque contra la estalagmita (alfred_choca_estalagmita.py): golpe en la piedra, la arana aplastada, Alfred cae de espaldas
    if f_choque < fin:
        poner("block.pointed_dripstone.hit" if m.rutas_de(p, "block.pointed_dripstone.hit") else "block.stone.hit", f_choque, 1.0, "golpes")
        poner("entity.player.attack.knockback", f_choque, 0.9, "golpes")
        poner("entity.spider.death", f_choque + 1, 1.0, "voces")
        poner("entity.slime.squish", f_choque + 1, 0.8, "golpes")
        for k in (3, 6): poner("block.stone.step", f_choque + k, 0.5, "pasos")       # trastabilla hacia atras
    if f_suelo:
        poner("entity.player.big_fall" if m.rutas_de(p, "entity.player.big_fall") else "entity.generic.big_fall", f_suelo, 1.0, "golpes")
        poner("block.stone.fall", f_suelo + 1, 0.8, "golpes")
    # --- giros sobre la piedra: Jerry en alerta y Alfred al voltear
    for f in (F_GIRO_JERRY + 2, F_GIRO_JERRY + 9): poner("block.stone.step", f, 0.45, "pasos")
    for f in (F_GIRO_ALFRED + 3, F_GIRO_ALFRED + 8): poner("block.stone.step", f, 0.55, "pasos")
    # --- Alfred corre sobre piedra: un paso por apoyo
    pasos = apoyos(F_CORRE, min(fin, int(bpy.data.objects["alfred"].get("f_choque", fin)) - 1))
    for f in pasos: poner("block.stone.step", f, 0.65, "pasos")
    sc.frame_set(f_act)
    return {"tiras": len(puestos), "pasos_alfred": len(pasos), "primeros_pasos": pasos[:6]}
