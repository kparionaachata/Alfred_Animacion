"""Parte 2 - EXPRESIONES DE LOS OJOS de Alfred, frames 1 a N (pedido de Kebyn): cada situacion de Alfred tiene su mirada (esperanza al nadar, curiosidad, preocupacion, duda, idea, insistencia,
miedo, panico, esfuerzo, golpe, inconsciencia, despertar aturdido, tos, susto, agotamiento, alivio al colocar la antorcha, concentracion al construir, sobresalto con cada empujon de Jerry y cada
zombie que llega, cautela, alivio final) + parpadeos naturales irregulares + micro-movimientos de la mirada.

Ojos de Alfred (medido en Blender, hoja de contacto): dos rectangulos blancos altos sobre cara negra. Shape keys (regenerados con construir_expresiones_ojos_alfred.py, sistema del add-on): Feliz (arco sonriente en el borde inferior), Triste (bordes inferiores caidos), Enojado (inclinados),
Sospecha (asimetrico inclinado), Cerrado (cuadrados pequenos), Cansado (parpado caido, mas bajos), Sorpresa (mas altos y anchos), Closed (linea fina = parpadeo / cerrados). Ademas escala (ancho/alto) y
location (mirada: desplazamiento lateral/vertical pequeno).
Ejecutar DESPUES de compose_refugio_parte2.py (usa sus constantes y jsons):  python alfred/refinar/docs/parte2/compose_ojos_alfred_parte2.py   (desde 'generador de animaciones')
Reescribe la seccion `ojos` de parte2_alfred_refugio.animacion.json (se puede repetir: sobreescribe todo).
"""
import json, math, os, random, sys

BASE = "generador de animaciones" if os.path.isdir("generador de animaciones") else "."
HERE = os.path.join(BASE, "alfred/refinar/docs/parte2")
sys.path.insert(0, HERE)
import compose_refugio_parte2 as CR                                   # K_ARR, TORCH_INS, N_TOTAL

KEYS = ["Feliz", "Triste", "Enojado", "Sospecha", "Cerrado", "Cansado", "Sorpresa", "Closed"]
SC0 = (1.555, 0.496, 3.55)                                            # escala POR DEFECTO de las mallas de los ojos (dada por Kebyn: ojo_izquierdo_alfred / ojo_derecho_alfred Scale 1.555, 0.496, 3.550)
LOC0 = {"ojo_izquierdo_alfred": (0.10665, 0.27046, 1.7008), "ojo_derecho_alfred": (-0.1053, 0.25633, 1.7004)}      # posicion por defecto (dada por Kebyn)
# Calibracion medida en Blender (render de la cara a 0.1/0.2/0.3/0.45): Triste ya es claro con 0.1-0.2 (con 0.3 aparecen muescas y con 0.45 espinas); Sospecha 0.1-0.2 es escepticismo, 0.3+ ya es ceno
# furioso en V; Enojado 0.2-0.3 es decision, 0.45 rabia; Feliz 0.2-0.3 (0.45 toca la diadema); Sorpresa 1.0 es sutil y el efecto fuerte viene de ensanchar (tope 0.30); Cansado/Cerrado se leen bien en todo el rango.
# (factor, tope) sobre el valor de cada estado de animo:
CAL = {"Triste": (0.45, 0.24), "Sospecha": (0.40, 0.22), "Enojado": (0.65, 0.30), "Feliz": (0.70, 0.32), "Cerrado": (1.0, 0.60)}
WIDE_MAX = 0.22
EXPR_INT = 0.06                                                      # intensidad de cada expresion cuando esta activa (rampa suave de entrada/salida segun el estado de animo)
LOC_SHIFT = 0.008                                                     # desplazamiento maximo de la mirada (unidades del rig)


def ss(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def ela(t):
    if t <= 0: return 0.0
    if t >= 1: return 1.0
    c5 = (2 * math.pi) / 4.5
    return -(2 ** (20 * t - 10) * math.sin((20 * t - 11.125) * c5)) / 2 if t < 0.5 else (2 ** (-20 * t + 10) * math.sin((20 * t - 11.125) * c5)) / 2 + 1


def pulse(k, a, b, fa=6.0, fb=6.0):
    return ss((k - a) / fa) * (1 - ss((k - b) / fb))


def epulse(k, a, b, fa=10.0, fb=14.0):
    return ela((k - a) / fa) * (1 - ela((k - b) / fb))


def main():
    ev = json.load(open(os.path.join(HERE, "eventos_alfred.json"), encoding="utf-8"))
    B = json.load(open(os.path.join(HERE, "refugio_bloques.json"), encoding="utf-8")); EM = json.load(open(os.path.join(HERE, "empujes_zombies.json"), encoding="utf-8"))["eventos"]
    T = json.load(open(os.path.join(HERE, "antorcha_parte2.json"), encoding="utf-8"))
    N = CR.N_TOTAL; KA, TI = CR.K_ARR, CR.TORCH_INS
    blocks = [b["frame"] for b in B["bloques"]]; hits = sorted(e["frame_golpe"] for e in EM.values()); llegan = sorted(e["llegada"] for e in EM.values()); last_block = max(blocks)
    K0 = KA + TI                                                       # fin del hueco de la antorcha (se corre todo lo posterior)
    KW, KSC, KC, KTOP = ev["k_levanta"], ev["k_reconoce_zombies"], ev["k_sube_otra_vez"], ev["k_llega_arriba"]
    kb, kn, ks, kT, kS, t1, t2 = ev["k_miran_atras"], ev["k_susto_fin"], ev["k_nado_frenetico"], ev["k_pie_escalera"], ev["k_resbala"], ev["k_golpe_caida"], ev["k_ultimo_escalon"]
    t_torch = T["frame_aparece"]; REST0 = K0; REST1 = CR.N0                     # descanso f1391-1461
    hit_alfred = ev["golpes"]                                          # frames de cada golpe de la caida rodando
    # ------------------------------------------------------------ estados de animo: (frame, {shape key: valor}, ensanchar ojos, mirada x (+ derecha), mirada z (+ arriba))
    # NEUTRO por defecto (todo a 0): las expresiones solo aparecen en su momento y vuelven a neutro (antes Enojado estaba activo el 53 % de los frames y daba cara de amargado todo el tiempo).
    Z = {}                                                                                                   # neutro
    M = [
        (1, Z, 0.0, 0.05, 0.12), (150, Z, 0.0, 0.10, 0.15), (205, {"Cansado": 0.25}, 0.0, 0.0, 0.10), (272, {"Cansado": 0.25}, 0.0, 0.0, 0.10),            # nada hacia el este: neutro y, al final, algo cansado
        (284, {"Sorpresa": 0.35, "Sospecha": 0.20}, 0.05, -0.25, 0.1), (306, {"Sorpresa": 0.20, "Triste": 0.15, "Sospecha": 0.15}, 0.0, -0.35, 0.0),             # Jerry avisa: mira a Jerry (a su izquierda)
        (322, {"Triste": 0.30, "Sospecha": 0.25}, 0.0, -0.35, -0.05), (350, {"Triste": 0.30, "Sospecha": 0.25}, 0.0, -0.30, -0.10),                          # escucha preocupado
        (362, {"Sospecha": 0.50, "Sorpresa": 0.12}, 0.03, 0.30, 0.15), (376, {"Sospecha": 0.50, "Sorpresa": 0.15}, 0.05, 0.60, 0.25), (390, {"Sospecha": 0.30}, 0.0, 0.55, 0.20),   # duda mirando el horizonte
        (400, {"Triste": 0.40, "Cansado": 0.30}, 0.0, -0.10, -0.15), (412, {"Triste": 0.40, "Cansado": 0.30}, 0.0, -0.15, -0.20),                          # encoge los hombros: resignado
        (420, {"Feliz": 0.30, "Sorpresa": 0.25}, 0.04, -0.65, 0.15), (436, {"Feliz": 0.40, "Sorpresa": 0.12}, 0.02, -0.70, 0.20), (444, Z, 0.0, -0.30, 0.0),     # idea: hacia el norte (su izquierda)
        (450, {"Enojado": 0.30}, 0.0, -0.25, 0.0), (468, {"Enojado": 0.30}, 0.0, -0.20, 0.0), (476, Z, 0.0, -0.40, 0.0),                                 # insiste, decidido (solo ~20 f)
        (480, {"Sorpresa": 0.45, "Sospecha": 0.20}, 0.08, -0.60, 0.0),                                                                               # algo detras...
        (kb + 8, {"Sorpresa": 0.95, "Sospecha": 0.30}, 0.30, 0.0, 0.0), (kn + 6, {"Sorpresa": 0.90, "Sospecha": 0.30, "Triste": 0.12}, 0.25, 0.0, 0.0),        # MIEDO: zombies cerca
        (ks + 20, {"Sorpresa": 0.65, "Sospecha": 0.30}, 0.10, 0.0, 0.05), (kT - 40, {"Sorpresa": 0.50, "Sospecha": 0.30}, 0.05, 0.0, 0.15),                   # nado frenetico: panico
        (kT + 20, {"Sorpresa": 0.30, "Sospecha": 0.25, "Enojado": 0.12}, 0.03, 0.0, 0.50), (kS - 14, {"Sorpresa": 0.32, "Sospecha": 0.25}, 0.03, 0.0, 0.45),  # sube los escalones saltando: urgencia
        (kS, {"Sorpresa": 0.90}, 0.30, 0.45, 0.20), (kS + 12, {"Sorpresa": 1.0}, 0.45, 0.30, 0.0),                                                           # resbala: ojos enormes
        (t1 - 2, {"Sorpresa": 0.70}, 0.15, 0.0, -0.3), (t1 + 4, {"Triste": 0.30}, 0.0, 0.0, -0.3), (KW - 4, {"Triste": 0.30}, 0.0, 0.0, -0.2),                # cae, queda inconsciente (Closed lo cierra)
        (KW + 14, {"Cansado": 0.40, "Triste": 0.30}, 0.0, 0.0, -0.45), (KW + 38, {"Cansado": 0.40, "Triste": 0.35, "Sospecha": 0.10}, 0.0, 0.1, -0.4),      # despierta aturdido, parpados pesados
        (KW + 58, {"Sospecha": 0.35, "Cansado": 0.30}, 0.0, 0.0, 0.0), (KW + 66, {"Sospecha": 0.35, "Sorpresa": 0.20}, 0.0, -0.4, 0.0),                    # desorientado: mira a los lados
        (KSC, {"Sorpresa": 1.0, "Sospecha": 0.30}, 0.38, 0.0, 0.0), (KSC + 24, {"Sorpresa": 0.95, "Sospecha": 0.30, "Triste": 0.15}, 0.30, 0.0, 0.0),      # ve a los zombies
        (KC + 12, {"Sorpresa": 0.55, "Sospecha": 0.30}, 0.08, 0.0, 0.40), (KTOP - 20, {"Sorpresa": 0.25, "Sospecha": 0.25, "Cansado": 0.30}, 0.02, 0.0, 0.50),  # vuelve a subir: miedo
        (KTOP + 12, {"Cansado": 0.30, "Triste": 0.30}, 0.0, 0.0, -0.35), (KA - 6, {"Cansado": 0.30, "Triste": 0.30}, 0.0, 0.0, -0.40),                     # camina agotado
        (KA + 10, {"Cansado": 0.25, "Feliz": 0.25}, 0.0, 0.0, -0.35),                                                                                        # llega: alivio y pone la antorcha
        (t_torch, {"Cansado": 0.20}, 0.0, 0.25, -0.85), (K0 - 4, {"Feliz": 0.30, "Cansado": 0.20}, 0.0, 0.2, -0.45),                                         # concentrado en el suelo, satisfecho
        (K0 + 6, {"Cansado": 0.30, "Sospecha": 0.25, "Triste": 0.15}, 0.0, 0.10, 0.35), (K0 + 28, {"Cansado": 0.30, "Sospecha": 0.25, "Triste": 0.18}, 0.0, 0.10, 0.30),   # Jerry le habla: lo mira
        (K0 + 42, {"Cansado": 0.40, "Cerrado": 0.30, "Triste": 0.22}, 0.0, 0.0, -0.60), (REST1 - 14, {"Cansado": 0.40, "Cerrado": 0.28, "Triste": 0.20}, 0.0, 0.0, -0.60),   # jadea inclinado
        (REST1 + 4, {"Sospecha": 0.35, "Cansado": 0.25}, 0.0, -0.2, 0.10), (REST1 + 36, {"Enojado": 0.30}, 0.0, 0.0, -0.10), (REST1 + 70, {"Enojado": 0.30}, 0.0, 0.0, -0.20),   # escucha el plan y se decide (~35 f)
        (REST1 + 90, {"Cansado": 0.25}, 0.0, 0.0, -0.20), (llegan[0] - 8, {"Cansado": 0.25}, 0.0, 0.0, -0.20),                                              # construye: neutro, algo cansado (el esfuerzo por bloque se suma abajo)
        (llegan[0] + 18, {"Sospecha": 0.35, "Triste": 0.22, "Sorpresa": 0.15}, 0.04, 0.2, 0.0),                                                               # los zombies llegan a los muros: cautela y miedo
        (last_block - 24, {"Sospecha": 0.38, "Triste": 0.28, "Sorpresa": 0.18}, 0.04, 0.0, 0.05), (last_block + 14, {"Cansado": 0.30, "Feliz": 0.20}, 0.0, 0.0, -0.1),   # cierra el ultimo bloque: tension que cede
        (last_block + 44, {"Feliz": 0.35, "Cansado": 0.25}, 0.0, 0.0, -0.05), (N, {"Feliz": 0.35, "Cansado": 0.25}, 0.0, 0.0, -0.05),                          # alivio: sellado y a salvo
    ]
    M.sort(key=lambda m: m[0])

    def mood(k):
        if k <= M[0][0]: a, b, u = M[0], M[0], 0.0
        elif k >= M[-1][0]: a, b, u = M[-1], M[-1], 0.0
        else:
            i = next(q for q in range(1, len(M)) if M[q][0] >= k); a, b = M[i - 1], M[i]; u = ss((k - a[0]) / float(b[0] - a[0]))
        vals = {key: a[1].get(key, 0.0) + (b[1].get(key, 0.0) - a[1].get(key, 0.0)) * u for key in KEYS}
        return vals, a[2] + (b[2] - a[2]) * u, a[3] + (b[3] - a[3]) * u, a[4] + (b[4] - a[4]) * u

    # ------------------------------------------------------------ pulsos de evento (sobresaltos elasticos) que se suman al estado de animo
    START = [(kb + 8, kn + 8, 0.0, 0.0), (KSC, KSC + 28, 0.0, 0.0)]                      # susto ya modelado en M; solo ensanchan los ojos con elasticidad
    def startle(k):                                                                      # sobresalto: sorpresa + ojos mas anchos (elastico)
        s = 0.0; wd = 0.0
        for k0, amp, wid in ([(h - 2, 0.45, 0.10) for h in hits] + [(x - 1, 0.40, 0.08) for x in llegan] + [(kb + 8, 0.0, 0.35), (kS, 0.0, 0.30), (KSC, 0.0, 0.35)]):
            f = epulse(k, k0, k0 + 20, 8.0, 12.0); s += amp * f; wd += wid * f
        return min(0.6, s), wd
    def effort(k):                                                                       # esfuerzo al colocar cada bloque: entrecierra los ojos y frunce un instante
        return sum(pulse(k, b - 7, b + 5, 4.0, 5.0) for b in blocks)

    # ------------------------------------------------------------ parpadeos: irregulares, mas frecuentes si esta cansado, ninguno en el miedo ni con los ojos cerrados
    rnd = random.Random(7); closed_spans = [(t1 + 1, KW + 6), (KW + 20, KW + 62)]
    B_ = []
    k = 12
    while k < N:
        tired = 0.0
        vals, _, _, _ = mood(k); tired = vals["Cansado"]; fear = vals["Sorpresa"]
        gap = rnd.randint(46, 150) * (1.0 - 0.35 * tired)
        k += int(gap)
        if any(a <= k <= b for a, b in closed_spans) or fear > 0.6 or (kb - 4 <= k <= kn + 12) or (KSC - 6 <= k <= KSC + 34): continue
        dur = 7 if tired < 0.5 else 10
        B_.append((k, dur))
        if rnd.random() < 0.18: B_.append((k + dur + 3, 6))                              # a veces parpadea dos veces
    # cierres deliberados (no son parpadeos): inconsciente, tos, jadeo, golpes, salpicaduras
    def closed_target(k):
        c = 0.0
        c = max(c, ss((k - (t1 + 2)) / 4.0) * (1 - ss((k - (KW + 2)) / 24.0)))                                         # cae y queda inconsciente; despierta abriendo despacio
        for kg in hit_alfred[1:]: c = max(c, 0.0)                                                                        # (cada golpe rodando: ya esta cerrado)
        c = max(c, 0.35 * (pulse(k, KW + 12, KW + 20, 3, 3) + pulse(k, KW + 26, KW + 31, 3, 3)))                         # aleteo al despertar
        c = max(c, pulse(k, KW + 38, KW + 49, 3.0, 5.0), pulse(k, KW + 52, KW + 63, 3.0, 5.0))                           # tos 1 y 2: aprieta los ojos
        for q, e0 in enumerate((K0 + 46, K0 + 58, K0 + 70)):                                                             # jadeo: cierra al exhalar
            c = max(c, 0.6 * pulse(k, e0 - 4, e0 + 10, 4.0, 7.0))
        c = max(c, 0.9 * pulse(k, t_torch + 6, t_torch + 12, 2.0, 3.0))                                                  # parpadeo largo de alivio al dejar la antorcha
        for sp in range(ks + 12, kT, 33): c = max(c, 0.85 * pulse(k, sp, sp + 4, 1.5, 2.0))                              # salpicaduras mientras nada frenetico
        c = max(c, 0.9 * pulse(k, last_block + 30, last_block + 46, 5.0, 8.0))                                           # alivio final: cierra despacio, respira
        return c

    def blink(k):
        v = 0.0
        for k0, d in B_:
            if k0 <= k < k0 + d:
                u = (k - k0) / float(d); v = max(v, ss(u / 0.3) if u < 0.3 else (1.0 if u < 0.45 else 1 - ss((u - 0.45) / 0.55)))
        return v

    # ------------------------------------------------------------ mirada: micro-movimientos (sacadas) + deriva lenta, con el rumbo de cada situacion
    sac = []; k = 5; rs = random.Random(11)
    while k < N:
        sac.append((k, rs.uniform(-0.22, 0.22), rs.uniform(-0.15, 0.15))); k += rs.randint(35, 120)
    def saccade(k):
        gx = gz = 0.0; prev = (0.0, 0.0)
        for i, (k0, x, z) in enumerate(sac):
            if k0 > k: break
            u = ss((k - k0) / 3.0); gx = prev[0] + (x - prev[0]) * u; gz = prev[1] + (z - prev[1]) * u; prev = (x, z)
        return gx, gz

    # ------------------------------------------------------------ series finales
    series = {key: [] for key in KEYS}; sx, sy, sz = [], [], []; lx, lz = [], []
    for k in range(1, N + 1):
        vals, wid, gx, gz = mood(k); s_, w_ = startle(k); ef = effort(k); cl = max(closed_target(k), blink(k))
        sx_, sz_ = saccade(k); sx_ *= 1.0 - 0.8 * vals["Sorpresa"]; sz_ *= 1.0 - 0.8 * vals["Sorpresa"]                  # con miedo la mirada se clava
        v = dict(vals)
        v["Sorpresa"] = min(1.0, v["Sorpresa"] + s_); pass                                                                       # el esfuerzo al colocar bloques ya NO suma Enojado/Cansado (con un bloque cada 12 f dejaba el ceno puesto todo el rato); solo entrecierra un poco por escala
        v["Closed"] = min(1.0, cl)
        noise = 0.03 * math.sin(k * 0.047) + 0.02 * math.sin(k * 0.113 + 1.7)                                              # leve vida en las expresiones
        for key in KEYS:
            if key == "Closed": continue
            v[key] = max(0.0, min(1.0, v[key] + (noise if v[key] > 0.15 else 0.0)))
        for key in KEYS:                                                                                    # intensidad de las expresiones FIJA en EXPR_INT (pedido de Kebyn: 0.06 como en la lista de intervalos del add-on); solo Closed (parpadeo/cierre) va de 0 a 1
            series[key].append(round(v[key] if key == "Closed" else EXPR_INT * ss(min(1.0, v[key] / 0.22)), 4))
        # ESCALA de las mallas de los ojos: la de por defecto SIEMPRE, y solo crece cuando hay SORPRESA (el resto de situaciones no la toca: ojos grandes taparian las demas expresiones)
        surp = series["Sorpresa"][-1] / EXPR_INT                                                           # exactamente la activacion de la expresion Sorpresa de este frame (0 = sin sorpresa = escala por defecto)
        wide = min(WIDE_MAX, wid + w_) * surp
        sx.append(round(SC0[0] * (1 + 0.33 * wide * 0.6), 4)); sy.append(SC0[1])
        sz.append(round(SC0[2] * (1 + 0.40 * wide), 4))
        lx.append(round((gx + sx_) * LOC_SHIFT, 5)); lz.append(round((gz + sz_) * LOC_SHIFT, 5))
    # ------------------------------------------------------------ escribir en el artefacto de Alfred
    path = os.path.join(BASE, "alfred/refinar/animaciones_ia/parte2_alfred_refugio/parte2_alfred_refugio.animacion.json")
    D = json.load(open(path, encoding="utf-8")); assert D["frame_fin"] == N, (D["frame_fin"], N)
    for on, o in D["ojos"].items():
        base_loc = list(LOC0[on])
        for key in KEYS: o["shape_keys"][key] = list(series[key])
        o["canales"]["scale"] = [list(sx), list(sy), list(sz)]
        o["canales"]["location"] = [[round(base_loc[0] + x, 5) for x in lx], [base_loc[1]] * N, [round(base_loc[2] + z, 5) for z in lz]]
        for hk in ("hide_viewport", "hide_render"): o["visibilidad"][hk] = [0.0] * N
    json.dump(D, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    parp = len(B_); print(f"ojos de Alfred: {N} f, {parp} parpadeos programados, estados de animo {len(M)}, sobresaltos en golpes {hits} y llegadas {llegan}")


if __name__ == "__main__":
    main()
