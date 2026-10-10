# -*- coding: utf-8 -*-
"""SONIDOS DE LA PARTE 5, SIN BLENDER (segundos): escribe los sonidos MANUALES (seccion `sonidos.manuales` del guion portable) de zombie_1..5 y de las acciones de Alfred (susto, lanzamiento del stick).
  python sonorizar_escena.py            (regenera todo; es repetible: reemplaza los sonidos anteriores de esta herramienta, marcados con grupo `parte5_auto`)
- PASOS de cada zombie (`mob/zombie/step1-5`): un paso por cada vez que una pierna llega adelante (maximo del giro X de RightUpLeg / LeftUpLeg en las poses por frame), solo mientras el zombie avanza.
- VOCES (`mob/zombie/say1-3`) a intervalos irregulares; zombie_1 ademas gruñe al empezar a arañar, rasca la madera (`mob/zombie/wood1-4`, 1 de cada 2 zarpazos) y se queja al recibir el stick (`mob/zombie/hurt1-2`, f268).
- ALFRED: cloth al levantar los brazos, paso atras (pasto), stick que sale de la espalda, silbido del lanzamiento (`entity/player/attack/sweep`), golpe en la cara, el stick cae en la madera, paso al frente.
- VOLUMEN SEGUN LA CAMARA: los sonidos de los ZOMBIES salen con `volumen_fuera` mientras la camara esta fuera del refugio y bajan a `volumen_fuera * factor_dentro` (0.30 = -10.5 dB) cuando esta dentro; la transicion sigue la posicion de la camara (la que dan los guiones de Alfred: f88-112 pasa del exterior al interior).
Parametros en PARAMS (arriba). Cada sonido guarda `camara: dentro %` para poder revisarlo."""
import glob
import json
import math
import os
import random

RAIZ = r"C:\Users\user\Desktop\Alfred_Animacion"; BASE = os.path.join(RAIZ, "generador de animaciones"); G = os.path.join(BASE, "alfred", "refinar", "configuraciones", "guiones"); ACC = os.path.join(BASE, "alfred", "refinar", "docs", "acciones")
PARAMS = {"paso_fuera": 0.55, "voz_fuera": 0.85, "rasca_fuera": 0.45, "factor_dentro": 0.30, "x_pared": -94.0, "transicion_m": 1.0, "hueco_pasos": 10, "voz_gap": (70, 140), "canal_paso": 40, "canal_voz": 50, "factor_gemidos": 0.5, "factor_madera": 0.5}
ID = "parte5_auto"


def ss(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


def camara_x(f):
    """x de Camera.001 en el frame f: fija en -91.623 hasta f88, pasa a -95.995 en f88-112 (smooth), luego fija."""
    return -91.623 + (-95.995 + 91.623) * ss((f - 88) / 24.0)


def dentro(f):
    """0 = camara fuera del refugio, 1 = dentro (transicion alrededor de la pared este, x = x_pared)"""
    return ss((PARAMS["x_pared"] + PARAMS["transicion_m"] / 2 - camara_x(f)) / PARAMS["transicion_m"])


def vol_zombie(base, f, rng):
    d = dentro(f); return round(base * (1 - d * (1 - PARAMS["factor_dentro"])) * (0.9 + 0.2 * rng.random()), 4), round(d * 100)


def poses(cfg):
    d = cfg["portable"]["poses_directory"]; out = {}
    for m in cfg["portable"]["pose_manifest"]:
        p = json.load(open(os.path.join(d, m["archivo"]), encoding="utf-8"))["poses"][0]; out[m["frame"]] = p
    return out


def pasos(pers, cfg, rng):
    P = poses(cfg); fr = sorted(P); res = []; ult = -999
    pierna = {l: [P[f]["bones"]["%sUpLeg_%s" % (l, pers)]["local_space"]["rotation_euler_rad"]["x"] for f in fr] for l in ("Right", "Left")}
    vel = [0.0] + [math.hypot(P[fr[i]]["root"]["location"]["x"] - P[fr[i - 1]]["root"]["location"]["x"], P[fr[i]]["root"]["location"]["y"] - P[fr[i - 1]]["root"]["location"]["y"]) for i in range(1, len(fr))]
    for l, s in pierna.items():
        for i in range(1, len(fr) - 1):
            if s[i] > s[i - 1] and s[i] >= s[i + 1] and s[i] > 0.3 and vel[i] > 0.012: res.append((fr[i], l))
    res.sort(); out = []
    for f, l in res:
        if f - ult < PARAMS["hueco_pasos"]: continue
        ult = f; v, dd = vol_zombie(PARAMS["paso_fuera"], f, rng)
        out.append({"etiqueta": "%s_paso_%s" % (pers, l.lower()), "archivo": "mob/zombie/step%d.ogg" % rng.randint(1, 5), "t": f, "volumen": v, "canal": PARAMS["canal_paso"] + int(pers[-1]), "grupo": ID, "camara": "dentro %d%%" % dd})
    return out


def voces(pers, desde, hasta, rng):
    out = []; f = desde + rng.randint(5, 40)
    while f < hasta:
        v, dd = vol_zombie(PARAMS["voz_fuera"], f, rng); out.append({"etiqueta": "%s_voz" % pers, "archivo": "mob/zombie/say%d.ogg" % rng.randint(1, 3), "t": f, "volumen": v, "canal": PARAMS["canal_voz"] + int(pers[-1]), "grupo": ID, "camara": "dentro %d%%" % dd})
        f += rng.randint(*PARAMS["voz_gap"])
    return out


def un(etq, arch, f, base, pers, rng, canal):
    v, dd = vol_zombie(base, f, rng); return {"etiqueta": etq, "archivo": arch, "t": f, "volumen": v, "canal": canal, "grupo": ID, "camara": "dentro %d%%" % dd}


def ajustar_gemidos_madera(S):
    """los gemidos de los zombies (`mob/zombie/say*`, `hurt*`) y los golpes a la madera (`wood`) suenan a la MITAD (PARAMS factor_gemidos / factor_madera)."""
    for m in S:
        a = m["archivo"].lower()
        if "mob/zombie/say" in a or "mob/zombie/hurt" in a: m["volumen"] = round(m["volumen"] * PARAMS["factor_gemidos"], 4)
        elif "wood" in a: m["volumen"] = round(m["volumen"] * PARAMS["factor_madera"], 4)
    return S


def zombies():
    for n in range(1, 6):
        pers = "zombie_%d" % n; f = glob.glob(os.path.join(G if False else os.path.join(BASE, pers, "refinar", "configuraciones", "guiones"), "configuracion_portable_%s_*.json" % pers))
        f = [x for x in f if "camina" in x or "rodea" in x][0]; cfg = json.load(open(f, encoding="utf-8")); rng = random.Random(1000 + n); fin = cfg["portable"]["frame_range"][1]
        S = pasos(pers, cfg, rng)
        if n == 1: S = [x for x in S if x["t"] <= 190 or x["t"] >= 262]                                                       # llega y se queda quieto en f193: sin pasos despues
        if n == 1:                                                                                        # zombie_1: camina f1-185, arana f201-292, recibe el stick en f256
            S += voces(pers, 1, 190, rng) + [un("zombie_1_gruni", "mob/zombie/say%d.ogg" % 2, 197, 1.0, pers, rng, 51), un("zombie_1_voz", "mob/zombie/say3.ogg", 240, PARAMS["voz_fuera"], pers, rng, 51),
                                              un("zombie_1_herido", "mob/zombie/hurt%d.ogg" % 1, 256, 1.0, pers, rng, 52), un("zombie_1_voz", "mob/zombie/say1.ogg", 266, PARAMS["voz_fuera"], pers, rng, 51)] + voces(pers, 275, fin, rng)
            S += [un("zombie_1_rasca", "mob/zombie/wood%d.ogg" % rng.randint(1, 4), 201 + 18 * k + 9, PARAMS["rasca_fuera"], pers, rng, 53) for k in range(0, 3)]
        else: S += voces(pers, 1, fin, rng)
        for s in S: s["id"] = "snd5_%s_%d" % (s["etiqueta"], s["t"])
        S.sort(key=lambda s: (s["t"], s["etiqueta"])); ajustar_gemidos_madera(S); cfg["sonidos"] = {"modo": "manual", "techo_voces": False, "manuales": S}
        cfg["sonidos"]["nota"] = "sonidos de %s generados por docs/acciones/sonorizar_escena.py (pasos por contacto de pierna, voces, volumen segun camara fuera/dentro del refugio)" % pers
        json.dump(cfg, open(f, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2); print("%s: %d sonidos (%d pasos) en %s" % (pers, len(S), sum(1 for s in S if "_paso_" in s["etiqueta"]), os.path.basename(f)))


def bebe():
    """zombie_baby_1 (corre al agujero): un paso por cada vez que una pierna llega adelante mientras corre (canales 46-48 en rotacion para que no se pisen) y voces al aparecer y durante la carrera; volumen segun la camara."""
    pers = "zombie_baby_1"; f = (glob.glob(os.path.join(BASE, pers, "refinar", "configuraciones", "guiones", "configuracion_portable_%s_corre_al_agujero_f1_*.json" % pers)) or [""])[0]
    if not os.path.exists(f): print("zombie_baby_1: no hay portable (correr_ruta.py)"); return
    cfg = json.load(open(f, encoding="utf-8")); rng = random.Random(1077); P = poses(cfg); fr = sorted(P); an = cfg["anclas"]; S = []; ult = -99; k = 0
    leg = {l: [P[x]["bones"]["%s_leg_%s" % (l, pers)]["local_space"]["rotation_euler_rad"]["x"] for x in fr] for l in ("right", "left")}
    vel = [0.0] + [math.hypot(P[fr[i]]["root"]["location"]["x"] - P[fr[i - 1]]["root"]["location"]["x"], P[fr[i]]["root"]["location"]["y"] - P[fr[i - 1]]["root"]["location"]["y"]) for i in range(1, len(fr))]
    for fnum, l in sorted((fr[i], l) for l, s_ in leg.items() for i in range(1, len(fr) - 1) if s_[i] > s_[i - 1] and s_[i] >= s_[i + 1] and s_[i] > 0.4 and vel[i] > 0.05):
        if fnum - ult < 3: continue
        ult = fnum; v, dd = vol_zombie(0.7, fnum, rng); S.append({"etiqueta": "%s_paso_%s" % (pers, l), "archivo": "mob/zombie/step%d.ogg" % rng.randint(1, 5), "t": fnum, "volumen": v, "canal": 46 + k % 3, "grupo": ID, "camara": "dentro %d%%" % dd}); k += 1
    for fv in (an["aparece"], an["aparece"] + 26, an["aparece"] + 50):
        v, dd = vol_zombie(0.85, fv, rng); S.append({"etiqueta": "%s_voz" % pers, "archivo": "mob/zombie/say%d.ogg" % rng.randint(1, 3), "t": fv, "volumen": v, "canal": 56, "grupo": ID, "camara": "dentro %d%%" % dd})
    CD = cfg.get("conducta")
    if CD:                                                                                                          # el bebe contra el slab: embestida, golpes de garra, manos, cabeza, saltos, pasos laterales, trepar, voces
        cnt = [0]
        def golpe(fr_, base, etq, arch=None):
            cnt[0] += 1; v, dd = vol_zombie(base, fr_, rng); S.append({"etiqueta": "%s_%s" % (pers, etq), "archivo": arch or "mob/zombie/wood%d.ogg" % rng.randint(1, 4), "t": int(fr_), "volumen": v, "canal": 57 + cnt[0] % 3, "grupo": ID, "camara": "dentro %d%%" % dd})
        def voz(fr_, base=0.9): v, dd = vol_zombie(base, fr_, rng); S.append({"etiqueta": "%s_voz" % pers, "archivo": "mob/zombie/say%d.ogg" % rng.randint(1, 3), "t": int(fr_), "volumen": v, "canal": 56, "grupo": ID, "camara": "dentro %d%%" % dd})
        voz(CD["desde"]); golpe(CD["impacto"], 1.0, "choca_slab")                                                    # se lanza y choca con el slab
        for g_ in CD["golpes_garra"]: golpe(g_, 0.6, "garra_golpe")
        for sg in CD["segmentos"]:
            a_, b_, t_ = sg["a"], sg["b"], sg["tipo"]
            if t_ == "manos":
                for g_ in range(a_ + 3, b_, 5): golpe(g_, 0.4, "manos_forcejeo")
            elif t_ == "cabeza": golpe(a_ + int((b_ - a_) * 0.45), 0.8, "cabeza_golpe"); voz(a_, 0.8)
            elif t_ == "saltar": golpe(a_ + int((b_ - a_) * 0.5), 0.55, "salto_golpe"); golpe(b_ - 1, 0.5, "salto_cae", "step/grass%d.ogg" % rng.randint(1, 6))
            elif t_ == "moverse":
                for g_ in range(a_ + 2, b_, 6): golpe(g_, 0.45, "paso_lateral", "mob/zombie/step%d.ogg" % rng.randint(1, 5))
            elif t_ == "embestir": golpe(a_ + int((b_ - a_) * 0.52), 1.0, "embiste_slab"); voz(a_ + int((b_ - a_) * 0.35), 0.9)
            elif t_ == "sacudir": voz(a_, 1.0)
            elif t_ == "agachar":
                for g_ in range(a_ + 3, b_, 7): golpe(g_, 0.4, "rasca_abajo")
            elif t_ == "trepar":
                for g_ in range(a_ + 3, b_, 8): golpe(g_, 0.55, "trepa_golpe")
                golpe(b_ - 1, 0.45, "trepa_cae", "step/grass%d.ogg" % rng.randint(1, 6))
        fq = CD["garras_desde"] + rng.randint(20, 40)
        while fq < cfg["portable"]["frame_range"][1]: voz(fq, 0.95); fq += rng.randint(28, 55)                          # gruñidos de rabia a intervalos irregulares
    for s_ in S: s_["id"] = "snd5_%s_%d" % (s_["etiqueta"], s_["t"])
    S.sort(key=lambda s_: (s_["t"], s_["etiqueta"])); ajustar_gemidos_madera(S); cfg["sonidos"] = {"modo": "manual", "techo_voces": False, "manuales": S, "nota": "sonidos de zombie_baby_1 generados por docs/acciones/sonorizar_escena.py"}
    json.dump(cfg, open(f, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2); print("zombie_baby_1: %d sonidos (%d pasos)" % (len(S), sum(1 for s_ in S if "_paso_" in s_["etiqueta"])))


def alfred():
    """sonidos de Alfred -> `sonidos` de las acciones `se_asusta_de_zombie_1` y `alfred_lanza_stick_a_zombie_1` (se pasan al portable al exportar)."""
    s1 = [{"etiqueta": "susto_ropa", "archivo": "step/cloth2.ogg", "t": 206, "volumen": 0.45, "canal": 22, "grupo": "objetos"}, {"etiqueta": "susto_paso_atras", "archivo": "step/grass3.ogg", "t": 214, "volumen": 0.35, "canal": 22, "grupo": "pasos"}]
    s2 = [{"etiqueta": "stick_sale_espalda", "archivo": "item/armor/equip_generic4.ogg", "t": 239, "volumen": 0.35, "canal": 22, "grupo": "objetos"}, {"etiqueta": "stick_lanza", "archivo": "entity/player/attack/sweep2.ogg", "t": 250, "volumen": 0.7, "canal": 22, "grupo": "objetos"},
          {"etiqueta": "stick_golpea_zombie", "archivo": "entity/player/attack/weak2.ogg", "t": 256, "volumen": 0.75, "canal": 23, "grupo": "objetos"}, {"etiqueta": "stick_cae_suelo", "archivo": "step/grass2.ogg", "t": 268, "volumen": 0.4, "canal": 22, "grupo": "objetos"}, {"etiqueta": "stick_rebote_suelo", "archivo": "step/grass4.ogg", "t": 273, "volumen": 0.2, "canal": 24, "grupo": "objetos"},
          {"etiqueta": "lanza_paso_adelante", "archivo": "step/grass5.ogg", "t": 252, "volumen": 0.35, "canal": 23, "grupo": "pasos"}]
    s3 = [{"etiqueta": "asoma2_ropa", "archivo": "step/cloth1.ogg", "t": 291, "volumen": 0.4, "canal": 22, "grupo": "objetos"}, {"etiqueta": "asoma2_paso", "archivo": "step/grass1.ogg", "t": 298, "volumen": 0.35, "canal": 23, "grupo": "pasos"}]
    s4 = [{"etiqueta": "retrocede_ropa", "archivo": "step/cloth3.ogg", "t": 414, "volumen": 0.5, "canal": 22, "grupo": "objetos"}, {"etiqueta": "retrocede_paso", "archivo": "step/grass4.ogg", "t": 418, "volumen": 0.45, "canal": 23, "grupo": "pasos"}]
    for carpeta, S in (("se_asusta_de_zombie_1", s1), ("alfred_lanza_stick_a_zombie_1", s2), ("se_asoma_otra_vez", s3), ("alfred_retrocede_asustado", s4)):
        p = os.path.join(ACC, carpeta, "accion.json"); a = json.load(open(p, encoding="utf-8")); a["sonidos"] = S
        json.dump(a, open(p, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2); print("alfred/%s: %d sonidos" % (carpeta, len(S)))


if __name__ == "__main__":
    zombies(); bebe(); alfred()
