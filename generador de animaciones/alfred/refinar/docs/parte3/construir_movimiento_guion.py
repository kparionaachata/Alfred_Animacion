# -*- coding: utf-8 -*-
"""Agrega la seccion `movimiento` a `configuraciones/guion_alfred_parte3.json`: los filtros organicos del estudio y los tramos de Alfred que YA se migraron al motor (`motor_alfred.py`), con sus parametros
(valores de `sentarse_en_refugio.py` v76). Cada tramo nuevo se agrega aqui o en `crear_tramo` y se aprueba por separado. Repetible (reemplaza los tramos con el mismo id y deja .bak).
Uso:  python construir_movimiento_guion.py"""
import importlib.util
import os

REFINAR = r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar"
GUION = os.path.join(REFINAR, "configuraciones", "guion_alfred_parte3.json")
sp = importlib.util.spec_from_file_location("guion_v2", os.path.join(REFINAR, "alfred_animation_studio", "guion_v2.py")); gv = importlib.util.module_from_spec(sp); sp.loader.exec_module(gv)
d = gv.cargar(GUION)

# anclas nuevas (frames confirmados con la referencia: la aproximacion termina en f29, la referencia de sentarse en f52 y el lanzamiento de herramientas empieza en f191)
d["anclas"].update({"ref_sentar": 30, "sentado": 52, "lanza_herramientas": 191, "nuca": 341})

mov = d.setdefault("movimiento", {})
mov["referencia_numerica"] = "docs/parte3/datos_guion/base_referencia_alfred.json"
mov["yaw_base_deg"] = -720.0                                                                       # giro acumulado de la parte 2 (TH = -4 pi): el yaw del root se escribe como -720 + yaw
mov["organico"] = {"breathing_amplitude": 0.020, "breathing_speed": 0.010, "breathing_phase": 1.97, "head_sway_amplitude": 0.023, "head_sway_speed": 0.079, "head_sway_seed": 693, "micro_scale_amplitude": 0.010,
                   "secondary_motion_lag": 3.9, "secondary_motion_damping": 0.51, "smooth_passes": 3, "smooth_factor": 0.63, "origen": "segmento 0 de alfred_animation_studio (ver docs/GUIA_ANIMACION_ALFRED.md)"}

PARAMS_SENTADO = {
    "referencia_sentado": "docs/parte3/ref_sentarse_cansado_alfred.json", "t_ref0": 30, "slow": 0.16, "t_mira": 150, "cuello_x_factor": 0.3,
    "aproximacion": {"t_inicio": 3, "dur": 23.0, "ciclo": 11.5, "piernas": 15, "rodillas": 16, "brazos": 7, "spine_z": 3, "spine2_z": 2, "hips_z": 2.2, "cuello_y": 28, "cuello_y_dur": 20.0,
                     "ruido": [["Spine_alfred", 1.0, 0.5], ["Spine2_alfred", 3.0, 0.6], ["Neck_alfred", 4.0, 0.8]], "ruido_fade": [20, 9.5]},
    "reposo": {"alive_dur": 10.0, "ruido": [["Spine_alfred", 1.0, 0.8], ["Spine1_alfred", 2.0, 0.7], ["Spine2_alfred", 3.0, 0.9]], "ruido_z": 0.6, "cuello_x": [4.0, 1.4], "cuello_z": [6.0, 1.0],
               "respira": [["Spine2_alfred", 1.4, 96.0, 0.0], ["Spine_alfred", 0.8, 96.0, 0.5], ["Spine1_alfred", 0.6, 96.0, 0.2]], "mira": [[0, 0], [16, 0], [34, 44], [66, 46], [84, 0]], "mira_x": 4.0, "mira_x_ini": 20,
               "mira_x_fin": 80, "cae": [[0, 0], [100, 0], [160, 14]], "cae_z": 0.4, "suspiro_dt": 44, "suspiro_ancho": 7.0, "suspiro_amp": 3.0, "brazo_i": [7.0, 1.2], "codo_i": [10.0, 1.6]},
    "root": {"t_inicio": 3, "dur": 23.0, "yaw": 90.0, "rebase": 2.0, "rebase_ini": 20, "rebase_dur": 9.5, "x0": -95.5, "dx": 0.2, "y0": -108.5, "dy": -0.09, "z": 14.0}}

PARAMS_S03 = {"base_de": "S01_sentarse",
              "lean": [["Spine_alfred", 24.0], ["Spine1_alfred", 18.0], ["Spine2_alfred", 10.0]], "t_lean_sube": 190, "t_lean_tope": 204, "t_lean_baja": 270, "lean_baja_dur": 12,
              "tiempos": {"alcanza": 9, "sostiene": 2, "lanza": 12, "vuelve": 12},
              "agarres": [{"objeto": "wooden_pickaxe", "lado": "Right", "t_toma": 206, "delta": [-19, 0, -42, 0]}, {"objeto": "wooden_axe", "lado": "Left", "t_toma": 224, "delta": [-2, 0, 57, -11]},
                          {"objeto": "stone_axe", "lado": "Right", "t_toma": 242, "delta": [-26, 0, -48, 0]}],
              "estudio": {"u": [28.5284, 198.1061, 62.0369], "e": [-16.873, 18.6165, -107.9791], "loc": [0.006603, 0.096746, -0.086079]},
              "suelta": {"Right": [[0.13206, -0.67532, -0.68619, 0.23592], [0.63634, 0.77141, 0.0, 0.0]], "Left": [[0.13706, -0.65673, 0.63297, -0.38636], [0.63742, 0.77051, 0.0, 0.0]]}}

TRAMOS = [
    {"id": "S01_sentarse", "nombre": "Acercarse al rincon y sentarse (referencia sentado_cansado_alfred)", "tipo": "sentado_cansado", "inicio": 1, "fin": "sentado", "estado": "sin aprobar", "params": PARAMS_SENTADO,
     "nota": "f1-29: de pie -> pose inicial de la referencia, giro +90 y 4 pasitos; f30-52: se sienta (la referencia x0.16)"},
    {"id": "S02_descansa", "nombre": "Sentado: respira, mira la antorcha, se le cierra la cabeza de sueno", "tipo": "sentado_cansado", "inicio": "sentado+1", "fin": "lanza_herramientas-1", "estado": "sin aprobar", "usa": "S01_sentarse",
     "nota": "f53-190; el filtro de respiracion, el ruido organico, la mirada a la antorcha (f166-234 del guion antiguo) y la cabeza que cae"},
    {"id": "S03_lanza_herramientas", "nombre": "Se inclina, arranca el pico y las hachas que lleva en la espalda y las lanza delante de el", "tipo": "lanza_herramientas", "inicio": "lanza_herramientas", "fin": "nuca-1", "estado": "sin aprobar", "params": PARAMS_S03,
     "nota": "f191-340: inclinacion del torso (f190-282), brazos por cuaterniones (alcanza 9 f, sostiene 2, lanza 12 con Elastic 30 %, vuelve 12) en f206 (pico, derecha), f224 (hacha de madera, izquierda) y f242 (hacha de piedra, derecha); luego reposo con respiracion hasta la nuca"}]
# ------------------------------------------------------------------------------------------------------------------ S03-S14: tipo `cuerpo` (todo el resto del cuerpo de Alfred); los parametros viven en S03 y los demas tramos los usan (`usa`)
import json
_sp = importlib.util.spec_from_file_location("construir_cuerpo_guion", os.path.join(REFINAR, "docs", "parte3", "construir_cuerpo_guion.py")); cc = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(cc)
d["anclas"].update({"sit_ini": 434, "rodillas": 502, "craftea": 628, "levanta": 843, "fin_corte": 1062})
TRAMOS = [t for t in TRAMOS if not t["id"].startswith("S03")]
TRAMOS.append({"id": "S03_lanza_herramientas", "nombre": "Se inclina, arranca el pico y las hachas que lleva en la espalda y las lanza delante de el", "tipo": "cuerpo", "inicio": "lanza_herramientas", "fin": "nuca-1", "estado": "sin aprobar", "params": cc.parametros_cuerpo(),
               "nota": "f191-340; PARAMETROS DE TODO EL CUERPO (S03-S14): torso, brazos por cuaterniones o por tabla de poses, rodillas, giros, root; los demas tramos los usan (`usa`)"})
for tid, nombre, ini, fin, nota in [
        ("S04_manos_nuca", "Manos detras de la cabeza, apoyado contra el muro, mira a Jerry", "nuca", "sit_ini-1", "f341-433: sube los brazos a la nuca (24 f), se acomoda y contesta mirando a Jerry"),
        ("S05_barrido", "'Espera, tengo una idea': barre las herramientas sobre Jerry", "sit_ini", "rodillas-1", "f434-501: brazos caidos, se inclina 48 grados y da 3 manotazos con la izquierda (f450, 463, 476)"),
        ("S06_rodillas_antorcha", "Se pone de rodillas y coloca la segunda antorcha", "rodillas", "mesa_aparece-1", "f502-562: sentado -> de rodillas (14 f), saca la antorcha de la espalda y la pone en el muro oeste"),
        ("S07_mesa_crafteo", "Saca y coloca la mesa de crafteo; trae sticks y un bloque de piedra", "mesa_aparece", "craftea-1", "f563-627: mesa (aparece f563, golpe f574), sticks con la derecha (f571-583) y piedra con la izquierda (f585-612)"),
        ("S08_craftea_pala", "Pone los materiales en la mesa y craftea la pala de piedra", "craftea", "tablon_1", "f628-712: avanza de rodillas, piedra y sticks en la rejilla, aparece la pala (f672), la coge y la guarda"),
        ("S09_tablones_slabs", "Tres tablones en la mesa, seis slabs; guarda uno y barre los cinco sobre Jerry", "tablon_1+1", "levanta-1", "f713-842: tablones (f712-765), slabs (f776), guarda uno (f791-803) y barre cinco (f816-826)"),
        ("S10_levanta_cava", "Se levanta, saca la pala y cava el bloque de debajo", "levanta", "cae_pozo-1", "f843-911: se pone de pie, la pala sale de la espalda (f865) y da paladas (f873-908)"),
        ("S11_pozo_guarda_pala", "Cae al pozo, absorbe la tierra, guarda la pala y gira +90", "cae_pozo", "hacha_toma-1", "f912-983: la tapa de pasto desaparece, baja 1 en Z, absorbe la tierra (f938), guarda la pala y gira (f946-962)"),
        ("S12_toma_hacha", "Coge el hacha de piedra y gira otros +90", "hacha_toma", "corta_inicio-1", "f984-1015: coge el hacha (f984), la mantiene y gira (f996-1012)"),
        ("S13_corta_bloque", "Corta el bloque de madera: golpe por el codo con el torso hacia atras", "corta_inicio", "rompe_bloque", "f1016-1062: 4 hachazos (f1026, 1038, 1050, 1062) con valores exactos en el impacto"),
        ("S14_guarda_asoma", "Guarda el hacha, retrocede, habla y se asoma a mirar", "rompe_bloque+1", 1160, "f1063-1160: hacha a la espalda, retrocede a x -95.7, 'Que estara pasando afuera?' y mira de izquierda a derecha")]:
    TRAMOS.append({"id": tid, "nombre": nombre, "tipo": "cuerpo", "inicio": ini, "fin": fin, "estado": "sin aprobar", "usa": "S03_lanza_herramientas", "nota": nota})
mov["ajuste_hips"] = [[round(v, 7) for v in r_] for r_ in json.load(open(os.path.join(REFINAR, "docs", "parte3", "datos_guion", "base_referencia_alfred.json"), encoding="utf-8"))["ajuste_hips"]]      # contacto con el suelo (HYK / KZ del generador)
mov["referencia_de_pruebas"] = "docs/parte3/datos_guion/base_referencia_alfred.json"; mov["referencia_numerica"] = None                      # el guion ya no depende de la referencia: queda como oraculo de las pruebas
previos = {t["id"]: t for t in mov.get("tramos", [])}
for t in TRAMOS:                                                                                  # la aprobacion es del usuario: si el tramo ya estaba aprobado, se conserva
    p_ = previos.get(t["id"])
    if p_ and p_.get("estado") == "aprobado": t["estado"] = "aprobado"; t["aprobado_por"] = p_.get("aprobado_por"); t["aprobado_el"] = p_.get("aprobado_el")
mov["tramos"] = [t for t in mov.get("tramos", []) if t["id"] not in {x["id"] for x in TRAMOS}] + TRAMOS
mov["tramos"].sort(key=lambda t: gv.frame_de(t["inicio"], gv.resolver_anclas(d)))

r = gv.validar(d, os.path.dirname(os.path.dirname(os.path.dirname(REFINAR))))
for e in r["errores"]: print("ERROR ", e)
for a in r["avisos"]: print("aviso ", a)
if not r["errores"]:
    gv.guardar(d, GUION, sobrescribir=True); print("guion guardado | tramos:", [(t["id"], gv.frame_de(t["inicio"], gv.resolver_anclas(d)), gv.frame_de(t["fin"], gv.resolver_anclas(d))) for t in mov["tramos"]])
