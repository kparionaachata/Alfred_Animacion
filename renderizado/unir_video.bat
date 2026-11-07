@echo off
REM ============================================================
REM  unir_video.bat
REM  Toma la secuencia de PNGs generada por renderizar_animacion.bat
REM  y la une en un unico archivo de video (MP4, H.264) usando ffmpeg.
REM
REM  REQUISITO: tener ffmpeg instalado.
REM  - Descarga: https://www.gyan.dev/ffmpeg/builds/ (build "essentials")
REM  - Descomprime, y copia la ruta completa a ffmpeg.exe abajo,
REM    O agrega la carpeta "bin" de ffmpeg a la variable de entorno PATH
REM    de Windows (asi puedes dejar FFMPEG_EXE=ffmpeg tal cual).
REM ============================================================

REM ---------- EDITA SI ES NECESARIO ----------
set "FFMPEG_EXE=ffmpeg"
REM Si no esta en el PATH, usa la ruta completa, ejemplo:
REM set "FFMPEG_EXE=C:\ffmpeg\bin\ffmpeg.exe"

set "INPUT_DIR=C:\Users\user\Desktop\Alfred_Animacion\renderizado\render"
set "OUTPUT_PREFIX=frame_"
set "OUTPUT_VIDEO=C:\Users\user\Desktop\Alfred_Animacion\renderizado\capitulo_4_final.mp4"
set FRAMERATE=24
set START_NUMBER=1
REM --------------------------------------------

echo ============================================================
echo  Uniendo secuencia de PNG en video...
echo  Origen: %INPUT_DIR%\%OUTPUT_PREFIX%%%04d.png
echo  Salida: %OUTPUT_VIDEO%
echo ============================================================
echo.

where %FFMPEG_EXE% >nul 2>nul
if errorlevel 1 (
    echo [ERROR] No se encontro ffmpeg. Instalalo o edita la ruta FFMPEG_EXE en este .bat.
    echo Descarga: https://www.gyan.dev/ffmpeg/builds/
    pause
    exit /b 1
)

%FFMPEG_EXE% -y -framerate %FRAMERATE% -start_number %START_NUMBER% ^
    -i "%INPUT_DIR%\%OUTPUT_PREFIX%%%04d.png" ^
    -c:v libx264 -pix_fmt yuv420p -crf 18 ^
    "%OUTPUT_VIDEO%"

echo.
if errorlevel 1 (
    echo ============================================================
    echo  Hubo un error al unir el video. Revisa el mensaje de ffmpeg arriba.
    echo  Causas comunes: numeracion de frames no consecutiva, algun
    echo  frame faltante en la secuencia, o ruta/prefijo incorrectos.
    echo ============================================================
) else (
    echo ============================================================
    echo  Video generado correctamente:
    echo  %OUTPUT_VIDEO%
    echo ============================================================
)
pause
