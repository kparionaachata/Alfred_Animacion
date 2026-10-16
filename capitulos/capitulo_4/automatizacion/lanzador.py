# -*- coding: utf-8 -*-
"""LANZADOR de reconstrucciones EN SEGUNDO PLANO (sin bpy: lo usa el panel de Blender y tambien la consola).
    python lanzador.py <archivo.blend> [auto|completo|<n>|<id del paso>|chequeos] [rapido]  (o reconstruir.bat)
    `rapido` = sin chequeos al final (para iterar rapido; los chequeos se pueden correr despues con `chequeos`)
 1. RESPALDO: copia el .blend a capitulo_4/respaldos_auto/ (se guardan los ultimos `respaldos_max` de cada archivo);
 2. decide si hace falta: si el archivo es exactamente el que dejo la ultima reconstruccion y ningun paso cambio -> no hace nada;
    si solo cambiaron pasos de mas adelante -> abre directamente el checkpoint y sigue desde ahi;
 3. lanza `blender -b ... --python cadena_runner.py` (Blender sin ventana) y guarda el log en automatizacion/estado/<archivo>/log.txt;
 4. si todo salio bien, pone el resultado EN LUGAR del .blend original (renombrado atomico: nunca queda un archivo a medias).
Desde la consola, Blender NO debe tener abierto ese archivo con cambios sin guardar (para eso esta el panel)."""
import os, sys, json, subprocess, time

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path: sys.path.insert(0, AQUI)
import cadena_comun as cc

BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
RUNNER = os.path.join(AQUI, "cadena_runner.py")


def preparar(blend, modo="auto", blender=None, origen=None, chequear=True):
    """-> plan {cmd, tmp, resultado, log, blend, modo}  o  {nada: True, texto} si no hay nada que hacer.
    `origen`: archivo a abrir en lugar del real (copia de la sesion viva, solo para 'chequeos')."""
    blend = os.path.abspath(blend); cfgp = cc.ruta_config(blend)
    if not os.path.isfile(cfgp): raise FileNotFoundError("No hay cadena para %s.\nCrea %s (copia cadenas/plantilla.json)." % (os.path.basename(blend), cfgp))
    d = cc.dir_estado(blend); res = os.path.join(d, "resultado.json"); log = os.path.join(d, "log.txt")
    tmp = os.path.splitext(blend)[0] + "__reconstruido_tmp.blend"
    abrir = origen or blend; extra = []; nota = ""
    if modo == "chequeos":
        extra = ["--solo-chequeos"]
    else:
        cfg = cc.cargar_config(cfgp); hs = cc.huellas_pasos(cfg); est = cc.leer_estado(blend)
        mismo = bool(est.get("huella_resultado")) and est.get("archivo_resultado") == cc.firma_archivo(blend)
        if modo == "auto" and mismo:                                         # el archivo no se toco desde la ultima reconstruccion
            k, cp = cc.decidir(est, hs, True, "auto")
            if k >= len(hs): return {"nada": True, "texto": "La cadena ya esta al dia: no cambio ningun paso ni la escena."}
            if cp: abrir = cp; extra = ["--abierto-en", str(k)]; nota = "desde el paso %d (%s), abriendo su checkpoint" % (k, cfg["pasos"][k]["id"])
            else: extra = ["--escena-igual", "--desde", "completo" if k == 0 else str(k)]
        else:
            extra = ["--desde", modo]
    cmd = [blender or BLENDER, "-b", abrir, "--python-exit-code", "1", "--python", RUNNER, "--", "--blend", blend, "--config", cfgp, "--resultado", res] + extra
    if modo != "chequeos": cmd += ["--salida", tmp] + ([] if chequear else ["--sin-chequeos"])
    return {"cmd": cmd, "tmp": tmp, "resultado": res, "log": log, "blend": blend, "modo": modo, "nota": nota}


def lanzar(plan):
    for p in (plan["resultado"], plan.get("tmp")):
        if p and os.path.isfile(p): os.remove(p)
    flags = 0x08000000 if os.name == "nt" else 0                         # CREATE_NO_WINDOW: sin ventana de consola
    f = open(plan["log"], "w", encoding="utf-8", errors="replace")
    f.write("[lanzador] %s\n[lanzador] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), " ".join('"%s"' % c if " " in c else c for c in plan["cmd"]))); f.flush()
    return subprocess.Popen(plan["cmd"], stdout=f, stderr=subprocess.STDOUT, creationflags=flags)


def ultimo_paso(plan):
    """la ultima linea '[cadena] ...' del log (para mostrar el progreso)"""
    try:
        with open(plan["log"], encoding="utf-8", errors="replace") as f: L = [l.strip() for l in f if l.startswith("[cadena]") and "RESULTADO" not in l]
        return L[-1][9:] if L else "abriendo el archivo..."
    except OSError: return ""


def terminar(plan, reemplazar=True):
    """lee el resultado; si salio bien pone el .blend reconstruido en lugar del original. -> dict R (+ 'reemplazado')"""
    try:
        with open(plan["resultado"], encoding="utf-8") as f: R = json.load(f)
    except Exception:
        cola = ""
        try:
            with open(plan["log"], encoding="utf-8", errors="replace") as f: cola = "".join(f.readlines()[-25:])
        except OSError: pass
        R = {"ok": False, "error": "Blender termino sin dejar resultado. Final del log:\n" + cola}
    R["reemplazado"] = False; blend = plan["blend"]; tmp = plan.get("tmp")
    if plan.get("borrar") and os.path.isfile(plan["borrar"]):                # copia temporal de la escena viva (solo chequeos)
        try: os.remove(plan["borrar"])
        except OSError: pass
    if R.get("ok") and plan["modo"] != "chequeos":
        est = cc.leer_estado(blend)
        if R.get("sin_cambios"):
            est["archivo_resultado"] = cc.firma_archivo(blend); cc.guardar_estado(blend, est)
        elif tmp and os.path.isfile(tmp):
            if reemplazar:
                os.replace(tmp, blend); R["reemplazado"] = True
                est["archivo_resultado"] = cc.firma_archivo(blend); cc.guardar_estado(blend, est)
            else:
                otro = os.path.splitext(blend)[0] + "_reconstruido.blend"; os.replace(tmp, otro); R["guardado_en"] = otro
    elif tmp and os.path.isfile(tmp):
        os.remove(tmp)
    return R


def resumen(R):
    L = []
    if not R.get("ok"): return "ERROR\n" + R.get("error", "?")
    if R.get("sin_cambios"): return "La cadena ya estaba al dia: no se reconstruyo nada."
    if R.get("modo") == "solo_chequeos": return R.get("informe", "")
    if R.get("motivo"): L.append("Desde el paso %s: %s" % (R.get("desde"), R["motivo"]))
    elif R.get("checkpoint") or R.get("desde"): L.append("Desde el paso %s (los anteriores no cambiaron)" % R.get("desde"))
    for p in R.get("pasos", []): L.append("  %-20s %6.1f s %s" % (p["id"], p["segundos"], p.get("nota", "")))
    L.append("Total %.0f s%s" % (R.get("segundos", 0), "" if not R.get("seg_guardar") else " (guardar %.0f s, chequeos %.0f s)" % (R["seg_guardar"], R.get("seg_chequeos", 0))))
    if R.get("reemplazado"): L.append("Resultado puesto en " + R.get("blend", ""))
    if R.get("guardado_en"): L.append("La escena cambio durante la reconstruccion: el resultado quedo en " + R["guardado_en"])
    if R.get("informe"): L += ["", R["informe"]]
    return "\n".join(L)


def main():
    if len(sys.argv) < 2: print(__doc__); return 2
    blend = os.path.abspath(sys.argv[1]); modo = sys.argv[2] if len(sys.argv) > 2 else "auto"; chequear = "rapido" not in sys.argv[3:]
    if modo != "chequeos":
        cfg = cc.cargar_config(cc.ruta_config(blend)) if os.path.isfile(cc.ruta_config(blend)) else {}
        plan = preparar(blend, modo, chequear=chequear)
        if plan.get("nada"): print(plan["texto"]); return 0
        print("[lanzador] respaldo..."); r = cc.respaldar(blend, cfg.get("respaldos_max", 4)); print("[lanzador] respaldo en", r)
    else:
        plan = preparar(blend, modo)
    if plan.get("nota"): print("[lanzador]", plan["nota"])
    t = time.time(); pr = lanzar(plan); ult = ""
    while pr.poll() is None:
        time.sleep(2); u = ultimo_paso(plan)
        if u != ult: print("[%4.0f s] %s" % (time.time() - t, u)); ult = u
    R = terminar(plan); print(); print(resumen(R)); print("\nLog:", plan["log"]); print("Informe:", cc.ruta_informe(blend))
    return 0 if R.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
