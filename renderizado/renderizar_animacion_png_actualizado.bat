@echo off
REM ============================================================
REM  renderizar_animacion.bat
REM  Renderiza la animacion completa por linea de comandos usando
REM  la configuracion vista en tus capturas (Cycles + OptiX,
REM  1920x1080 al 100%, 24fps, frames 1-990, Blender 5.3).
REM
REM  IMPORTANTE: se fuerza salida como secuencia PNG en vez de
REM  FFmpeg Video, para poder retomar el render si se cuelga a
REM  mitad de camino (ver conversacion anterior). Al final puedes
REM  unir los PNG en un video.
REM
REM  GPU-ONLY: se fuerza Cycles a usar SOLO la RTX 3050 (OptiX).
REM  Se desactivan explicitamente la CPU y cualquier otra GPU
REM  (ej. T400), sin importar lo que tengas guardado en el .blend
REM  o en las preferencias de Blender.
REM ============================================================

REM ---------- Archivo .blend a renderizar ----------
set "BLEND_FILE=C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\base_tarde con las ranas_1.blend"
REM -------------------------------------------------------------------

set "BLENDER_EXE=C:\Program Files\Blender Foundation\blender-5.3.0-beta+v53.9eaa3f289688-windows.amd64-release\blender.exe"
set "OUTPUT_DIR=C:\Users\user\Desktop\Alfred_Animacion\renderizado\render"
set OUTPUT_PREFIX=frame_
set FRAME_START=420
set FRAME_END=990

REM ---------- Script Python temporal: fuerza GPU-only (OptiX) ----------
set "GPU_SCRIPT=%TEMP%\forzar_gpu_render.py"

(
echo import bpy
echo # Forzar siempre la resolucion de salida de los PNG
echo bpy.context.scene.render.resolution_x = 1920
echo bpy.context.scene.render.resolution_y = 1080
echo bpy.context.scene.render.resolution_percentage = 100
echo # Blender 5.x: la escena sale como video ^(FFMPEG^); hay que pasar a imagen antes de elegir PNG
echo im = bpy.context.scene.render.image_settings
echo if hasattr^(im, 'media_type'^): im.media_type = 'IMAGE'
echo im.file_format = 'PNG'
echo prefs = bpy.context.preferences.addons['cycles'].preferences
echo prefs.compute_device_type = 'OPTIX'
echo prefs.get_devices^(^)
echo for d in prefs.devices:
echo     if d.type == 'CPU':
echo         d.use = False
echo     else:
echo         d.use = ^('3050' in d.name^)
echo bpy.context.scene.cycles.device = 'GPU'
echo print^("=== Dispositivos de render ==="^)
echo for d in prefs.devices:
echo     print^("  ", d.name, d.type, "-> use =", d.use^)
) > "%GPU_SCRIPT%"

echo ============================================================
echo  Iniciando render: frames %FRAME_START% a %FRAME_END%
echo  Salida: %OUTPUT_DIR%\%OUTPUT_PREFIX%
echo  Dispositivo: SOLO RTX 3050 (OptiX, CPU y otras GPU desactivadas)
echo ============================================================
echo.

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

"%BLENDER_EXE%" -b "%BLEND_FILE%" ^
    --python "%GPU_SCRIPT%" ^
    -o "%OUTPUT_DIR%\%OUTPUT_PREFIX%" ^
    -x 1 ^
    -s %FRAME_START% ^
    -e %FRAME_END% ^
    -a

del "%GPU_SCRIPT%" >nul 2>&1

echo.
echo ============================================================
echo  Render finalizado (o interrumpido). Revisa la carpeta:
echo  %OUTPUT_DIR%
echo ============================================================
pause
