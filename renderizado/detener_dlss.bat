@echo off
REM Para el render DLSS oculto (cierra el blender.exe lanzado por renderizar_dlss.bat). Los frames ya guardados se conservan.
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='blender.exe'\" | Where-Object { $_.CommandLine -like '*dlss_render_por_comando.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('Detenido blender.exe PID '+$_.ProcessId) }"
pause
