# -*- coding: utf-8 -*-
"""RUNNER de la cadena (se ejecuta DENTRO de Blender, normalmente en segundo plano):
    blender -b <archivo.blend> --python cadena_runner.py -- --blend <archivo real .blend> [--config cadena.json] [--salida resultado.blend]
            [--desde auto|completo|<n>|<id>] [--escena-igual] [--solo-chequeos] [--sin-chequeos] [--resultado resultado.json]
Hace:
 1. lee la cadena (`cadenas/<archivo>.json`) y calcula la huella de cada paso;
 2. decide DESDE QUE PASO reconstruir: si la escena no se toco a mano desde la ultima vez (huella de escena) y hay un checkpoint valido,
    lo abre y sigue desde ahi; si no, ejecuta todo desde el paso 0 (los pasos son repetibles);
 3. ejecuta los pasos (guarda un checkpoint despues de los que tienen "checkpoint": true);
 4. corre los CHEQUEOS automaticos y escribe el informe;
 5. guarda el resultado en --salida (el lanzador lo pone en lugar del original).
El resumen queda en --resultado (json) para el lanzador / el panel."""
import bpy, sys, os, json, time, traceback

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path: sys.path.insert(0, AQUI)
import importlib
import cadena_comun as cc
import huella_escena as he
import chequeos as chq
for m in (cc, he, chq): importlib.reload(m)


def _args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = {"desde": "auto"}; i = 0
    while i < len(a):
        k = a[i]
        if k in ("--config", "--salida", "--desde", "--resultado", "--blend", "--abierto-en"): o[k[2:].replace("-", "_")] = a[i + 1]; i += 2
        elif k in ("--solo-chequeos", "--sin-chequeos", "--escena-igual"): o[k[2:].replace("-", "_")] = True; i += 1
        else: i += 1
    return o


def _py(v):
    if hasattr(v, "to_dict"): return {k: _py(x) for k, x in v.to_dict().items()}
    if hasattr(v, "to_list"): return [_py(x) for x in v.to_list()]
    return v


def tiempos(cfg):
    return _py(bpy.context.scene.get(cfg.get("tiempos_prop", ""), {})) if cfg.get("tiempos_prop") else {}


def ejecutar_paso(p, cfg):
    t = p.get("tipo", "script")
    if t == "script":
        src = open(p["archivo"], encoding="utf-8").read(); g = {"__name__": "__cadena__", "__file__": p["archivo"]}; g.update(p.get("globales", {}))
        exec(compile(src, p["archivo"], "exec"), g)
    elif t == "voz_rapida":
        vr = importlib.import_module(p.get("modulo", "jerry_animation_studio.voz_rapida"))
        ini = int(eval(str(p["inicio"]), {"T": tiempos(cfg), "int": int, "round": round}))
        vr.aplicar(bpy.context, p["audio"], ini, p.get("script"), p.get("tag"), p.get("modo", "normal"), p.get("vol"), p.get("efecto", "ninguno"))
        return "inicio f%d" % ini
    elif t == "borrar_props":
        sc = bpy.context.scene
        for k in p["props"]:
            if k in sc: del sc[k]
    elif t == "python":
        exec(p["codigo"], {"bpy": bpy, "T": tiempos(cfg), "__name__": "__cadena__"})
    else:
        raise ValueError("tipo de paso desconocido: %r" % t)
    return ""


def main():
    A = _args(); BLEND = os.path.abspath(A["blend"]); R = {"ok": False, "blend": BLEND, "pasos": [], "t0": time.time()}
    salida_res = A.get("resultado")

    def escribir():
        R["segundos"] = round(time.time() - R["t0"], 1)
        if salida_res:
            with open(salida_res, "w", encoding="utf-8") as f: json.dump(R, f, indent=1, ensure_ascii=False)
        print("[cadena] RESULTADO " + json.dumps({k: v for k, v in R.items() if k != "informe"}, ensure_ascii=False)); sys.stdout.flush()
    try:
        cfg = cc.cargar_config(A.get("config") or cc.ruta_config(BLEND)); pasos = cfg.get("pasos", [])
        for p_ in cfg.get("rutas_python", []):
            if p_ not in sys.path: sys.path.insert(0, p_)
        hs = cc.huellas_pasos(cfg); est = cc.leer_estado(BLEND); frame0 = bpy.context.scene.frame_current
        # ---------- solo chequeos ----------
        if A.get("solo_chequeos"):
            r = chq.ejecutar(cfg.get("chequeos", {}), tiempos(cfg), frame0); R.update(ok=True, modo="solo_chequeos", errores=r["errores"], avisos=r["avisos"], informe=r["texto"])
            with open(cc.ruta_informe(BLEND), "w", encoding="utf-8") as f: f.write(r["texto"])
            print(r["texto"]); escribir(); return
        # ---------- desde donde ----------
        desde = A.get("desde", "auto")
        if desde not in ("auto", "completo"): desde = str(cc.indice_paso(cfg, desde))
        igual = True; motivo = ""
        if A.get("abierto_en") is not None:                                 # el lanzador ya abrio el checkpoint: el archivo abierto es el estado antes del paso k
            k, cp = int(A["abierto_en"]), None
        else:
            if desde != "completo" and not A.get("escena_igual"):
                H = he.huella(); igual = he.total(H) == est.get("huella_resultado")
                if not igual:
                    d, n = he.diferencias(est.get("huella_detalle"), H)
                    motivo = "primera vez" if not est.get("huella_resultado") else "la escena cambio a mano (%d datos: %s%s)" % (n, ", ".join(d[:6]), "..." if n > 6 else "")
            k, cp = cc.decidir(est, hs, igual, desde)
        R.update(desde=k, checkpoint=cp, motivo=motivo or ("completo pedido" if desde == "completo" else ""))
        if k >= len(pasos):
            R.update(ok=True, sin_cambios=True); print("[cadena] la cadena ya esta al dia: nada que reconstruir"); escribir(); return
        print("[cadena] %d pasos; se ejecutan desde el %d (%s)%s" % (len(pasos), k, pasos[k]["id"], " abriendo checkpoint " + os.path.basename(cp) if cp else ""))
        if motivo: print("[cadena] todo desde el principio: " + motivo)
        if cp: bpy.ops.wm.open_mainfile(filepath=cp)
        # los checkpoints de pasos que se rehacen ya no sirven
        viejos = est.get("pasos", [])[k:]; est["pasos"] = est.get("pasos", [])[:k]
        for e in viejos:
            c_ = e.get("checkpoint")
            if c_ and c_ != cp and os.path.isfile(c_):
                try: os.remove(c_)
                except OSError: pass
        est.pop("huella_resultado", None); cc.guardar_estado(BLEND, est)
        dir_cp = cc.dir_estado(BLEND)
        for i in range(k, len(pasos)):
            p = pasos[i]; t = time.time(); print("[cadena] paso %d/%d: %s ..." % (i, len(pasos) - 1, p["id"])); sys.stdout.flush()
            try: extra = ejecutar_paso(p, cfg)
            except Exception:
                R["pasos"].append({"id": p["id"], "ok": False, "segundos": round(time.time() - t, 1)}); R["error"] = "paso %d (%s):\n%s" % (i, p["id"], traceback.format_exc())
                print("[cadena] ERROR en el paso %s\n%s" % (p["id"], R["error"])); escribir(); return
            dt = round(time.time() - t, 1); e = {"id": p["id"], "huella": hs[i], "checkpoint": None}
            if p.get("checkpoint"):
                c_ = os.path.join(dir_cp, "cp_%02d_%s.blend" % (i, p["id"])); t2 = time.time()
                bpy.ops.wm.save_as_mainfile(filepath=c_, copy=True); e["checkpoint"] = c_; extra += " | checkpoint %.0f s" % (time.time() - t2)
            est["pasos"].append(e); cc.guardar_estado(BLEND, est)
            R["pasos"].append({"id": p["id"], "ok": True, "segundos": dt, "nota": extra}); print("[cadena]   ok %.1f s %s" % (dt, extra)); sys.stdout.flush()
        # ---------- chequeos ----------
        if not A.get("sin_chequeos") and cfg.get("chequeos"):
            t = time.time(); r = chq.ejecutar(cfg["chequeos"], tiempos(cfg), frame0)
            R.update(errores=r["errores"], avisos=r["avisos"], informe=r["texto"], seg_chequeos=round(time.time() - t, 1))
            with open(cc.ruta_informe(BLEND), "w", encoding="utf-8") as f: f.write(r["texto"])
            print(r["texto"])
        bpy.context.scene.frame_set(frame0)
        # ---------- huella final y guardar ----------
        H = he.huella(); est["huella_resultado"] = he.total(H); est["huella_detalle"] = H; est["fecha"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if A.get("salida"):
            t = time.time(); bpy.ops.wm.save_as_mainfile(filepath=A["salida"], copy=True); R["seg_guardar"] = round(time.time() - t, 1); R["salida"] = A["salida"]
        cc.guardar_estado(BLEND, est); R["ok"] = True
    except Exception:
        R["error"] = traceback.format_exc(); print("[cadena] ERROR\n" + R["error"])
    escribir()


main()
