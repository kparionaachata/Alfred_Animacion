@echo off
REM ============================================================
REM  renderizar_dlss.bat
REM  Renderiza la animacion con DLSS (add-on DLSS Render) por comando.
REM  Solo se ve esta consola, con una linea por frame guardado: Blender se
REM  lanza OCULTO (sin ventana ni icono en la barra de tareas), pone la escena a
REM  punto, lanza "Render Animation" y se cierra al acabar. (El denoiser DLSS
REM  solo existe en el viewport, por eso Blender no puede ir en modo -b.)
REM  Para parar: Ctrl+C aqui y luego detener_dlss.bat, o solo detener_dlss.bat.
REM  Los frames salen como PNG: ejecuta unir_video.bat al terminar.
REM  Solo usa la RTX 3050. No guarda el .blend. Registro: render_dlss_log.txt
REM ============================================================

set "BLEND_FILE=C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\base_tarde con las ranas_1.blend"
set "BLENDER_EXE=C:\Program Files\Blender Foundation\blender-5.3.0-beta+v53.9eaa3f289688-windows.amd64-release\blender.exe"
set "SCRIPT=C:\Users\user\Desktop\Alfred_Animacion\renderizado\dlss_render_por_comando.py"
set "LOG=C:\Users\user\Desktop\Alfred_Animacion\renderizado\render_dlss_log.txt"

set "DLSS_OUT=C:\Users\user\Desktop\Alfred_Animacion\renderizado\render"
set DLSS_START=1
set DLSS_END=990
REM Calidad: DRAFT (8 muestras), BALANCED (24), HIGH (64) o CUSTOM (usa DLSS_MUESTRAS).
REM CUSTOM con 4 muestras: ~2,5 s por frame, frame exacto (probado en 30 frames). Con 3 o menos muestras el viewport
REM puede devolver el frame anterior; con 24 (BALANCED) tarda ~4-6 s por frame.
set DLSS_CALIDAD=CUSTOM
set DLSS_MUESTRAS=4
REM Escalado DLSS: vacio = el de la escena, o NONE, QUALITY, BALANCED, PERFORMANCE, ULTRA_PERFORMANCE.
REM La escena ahora guarda QUALITY (~5,5 s por frame); con BALANCED volvia a ~1,6-2,5 s por frame.
set DLSS_UPSCALE=BALANCED

echo ============================================================
echo  Iniciando render DLSS: frames %DLSS_START% a %DLSS_END%  (calidad %DLSS_CALIDAD%)
echo  Salida: %DLSS_OUT%\frame_####.png
echo  Dispositivo: SOLO RTX 3050 (OptiX)
echo ============================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dlss_lanzar.ps1"

echo.
echo ============================================================
echo  Render finalizado (o interrumpido). Revisa la carpeta:
echo  %DLSS_OUT%
echo ============================================================
pause
