# -*- coding: utf-8 -*-
"""Renderiza la animacion con DLSS desde la linea de comandos (lo lanza renderizar_dlss.bat).

El add-on DLSS Render necesita una ventana de Blender con un 3D Viewport (el denoiser DLSS solo existe en el viewport),
asi que Blender se abre con interfaz, este script configura la escena, pulsa por ti "Render Animation" y, cuando el
render termina (o falla), cierra Blender. No guarda el .blend.
Configuracion por variables de entorno (las pone el .bat): DLSS_START, DLSS_END, DLSS_OUT, DLSS_CALIDAD, DLSS_MUESTRAS."""
import bpy, os, sys, time, traceback

START = int(os.environ.get("DLSS_START", "1"))
END = int(os.environ.get("DLSS_END", "729"))
OUT = os.environ.get("DLSS_OUT", r"C:\Users\user\Desktop\Alfred_Animacion\renderizado\render")
CALIDAD = os.environ.get("DLSS_CALIDAD", "BALANCED").upper()      # DRAFT, BALANCED, HIGH o CUSTOM
MUESTRAS = int(os.environ.get("DLSS_MUESTRAS", "24"))              # solo con CUSTOM
PREFIJO = "frame_"
ADDON = "bl_ext.user_default.dlss_render"
estado = {"fase": "espera", "t0": time.time(), "intentos": 0}


def salir(codigo, texto):
    print("DLSS_CMD:", texto, flush=True)
    estado["fase"] = "fin"
    bpy.app.timers.register(lambda: (bpy.ops.wm.quit_blender(), None)[1], first_interval=1.0)
    estado["codigo"] = codigo


def hay_viewport(win):
    return any(a.type == "VIEW_3D" for a in win.screen.areas)


RAIZ = r"C:\Users\user\Desktop\Alfred_Animacion"


def reparar_texturas():
    """Algunas texturas del .blend apuntan a ...\\Temp\\AppData\\ecenarios\\... (ruta de otra sesion) y no existen:
    se reenlazan a la carpeta ecenarios del proyecto (por la ruta desde 'ecenarios', o por el nombre del archivo)."""
    por_nombre = {}
    base = os.path.join(RAIZ, "ecenarios")
    for d, _, fs in os.walk(base):
        for f in fs:
            por_nombre.setdefault(f.lower(), os.path.join(d, f))
    arreglo = faltan = 0
    for im in bpy.data.images:
        if im.source != "FILE" or not im.filepath or im.packed_file:
            continue
        ab = bpy.path.abspath(im.filepath)
        if os.path.exists(ab):
            continue
        partes = os.path.normpath(ab).split(os.sep)
        nuevo = None
        if "ecenarios" in partes:
            cand = os.path.join(base, *partes[partes.index("ecenarios") + 1:])
            if os.path.exists(cand):
                nuevo = cand
        if nuevo is None:
            nuevo = por_nombre.get(os.path.basename(ab).lower())
        if nuevo:
            im.filepath = nuevo
            im.reload()
            arreglo += 1
        else:
            faltan += 1
            print("DLSS_CMD: textura sin encontrar:", im.name, ab, flush=True)
    print(f"DLSS_CMD: texturas reenlazadas: {arreglo}, sin encontrar: {faltan}", flush=True)


def configurar():
    reparar_texturas()
    sc = bpy.context.scene
    r = sc.render
    r.engine = "CYCLES"
    sc.cycles.device = "GPU"
    r.resolution_x, r.resolution_y, r.resolution_percentage = 1920, 1080, 100
    r.use_border = False
    sc.frame_start, sc.frame_end, sc.frame_step = START, END, max(1, int(os.environ.get("DLSS_STEP", "1")))
    os.makedirs(OUT, exist_ok=True)
    r.filepath = os.path.join(OUT, PREFIJO)
    if hasattr(r.image_settings, "media_type"):          # Blender 5.x: si la escena sale como video (FFMPEG), pasar a imagen
        r.image_settings.media_type = "IMAGE"
    r.image_settings.file_format = "PNG"
    r.image_settings.compression = int(os.environ.get("DLSS_COMPRESION", "15"))     # 0 = guarda mas rapido (archivos mas grandes)
    print("DLSS_CMD: PNG", r.image_settings.color_depth, "bits, compresion", r.image_settings.compression, flush=True)
    # solo la RTX 3050
    p = bpy.context.preferences.addons["cycles"].preferences
    p.compute_device_type = "OPTIX"
    p.get_devices()
    for d in p.devices:
        d.use = d.type != "CPU" and "3050" in d.name
    print("DLSS_CMD: dispositivos:", [(d.name, d.use) for d in p.devices], flush=True)
    up = os.environ.get("DLSS_UPSCALE", "").upper()            # NONE, QUALITY, BALANCED, PERFORMANCE, ULTRA_PERFORMANCE (vacio = el de la escena)
    if up:
        sc.cycles.preview_denoising_upscale_quality = up
    print("DLSS_CMD: upscale:", sc.cycles.preview_denoising_upscale_quality, flush=True)
    s = sc.dlss_render
    s.quality = CALIDAD
    if CALIDAD == "CUSTOM":
        s.samples = MUESTRAS


def lanzar():
    """Timer: espera a que la ventana este lista y arranca el render."""
    try:
        wm = bpy.context.window_manager
        if estado["fase"] == "fin":
            return None
        if estado["fase"] == "espera":
            if not wm.windows or time.time() - estado["t0"] < 4.0:
                return 0.5
            win = wm.windows[0]
            if not hay_viewport(win):
                # el espacio de trabajo guardado no tiene 3D Viewport: busca uno que si
                for ws in bpy.data.workspaces:
                    if any(a.type == "VIEW_3D" for s in ws.screens for a in s.areas):
                        win.workspace = ws
                        break
                estado["intentos"] += 1
                if estado["intentos"] > 10 or not hay_viewport(win):
                    if estado["intentos"] > 10:
                        salir(2, "No hay ningun 3D Viewport en la ventana.")
                    return 0.5
            if ADDON not in bpy.context.preferences.addons:
                salir(3, "El add-on DLSS Render no esta activado.")
                return None
            configurar()
            win = wm.windows[0]
            with bpy.context.temp_override(window=win, screen=win.screen):
                res = bpy.ops.render.dlss_render("EXEC_DEFAULT", animation=True)
            print("DLSS_CMD: operador ->", res, flush=True)
            if "RUNNING_MODAL" not in res:
                salir(4, "El render DLSS no pudo empezar (ver el mensaje de arriba).")
                return None
            estado["fase"] = "render"
            from importlib import import_module
            estado["modulo"] = import_module(ADDON + ".render")
            return 1.0
        if estado["fase"] == "render":
            m = estado["modulo"]
            if m.ACTIVE is None:
                salir(0, "Render terminado.")
                return None
            return 2.0
    except Exception:
        traceback.print_exc()
        salir(1, "Error en el script.")
    return None


bpy.app.timers.register(lanzar, first_interval=1.0)
