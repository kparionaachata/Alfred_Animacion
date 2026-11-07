# Lo llama renderizar_dlss.bat: lanza Blender oculto con el script DLSS y muestra en la consola una linea por frame guardado.
$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force $env:DLSS_OUT | Out-Null

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Ventanas {
    delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc p, IntPtr l);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
    // oculta toda ventana visible del proceso; devuelve cuantas ha ocultado
    public static int Ocultar(uint pidBuscado) {
        int n = 0;
        EnumWindows((h, l) => {
            uint pid; GetWindowThreadProcessId(h, out pid);
            if (pid == pidBuscado && IsWindowVisible(h)) {
                SetWindowPos(h, IntPtr.Zero, -32000, -32000, 0, 0, 0x0001 | 0x0004 | 0x0010);   // fuera de pantalla, sin cambiar tamano
                ShowWindow(h, 0);                                                                  // SW_HIDE
                n++;
            }
            return true;
        }, IntPtr.Zero);
        return n;
    }
}
"@

function Nuevos {
    Get-ChildItem $script:out -Filter 'frame_*.png' -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -ge $script:t0 -and -not $script:vistos.ContainsKey($_.Name) } | Sort-Object Name
}

function Informa($f) {
    # espera a que el PNG termine de escribirse
    for ($i = 0; $i -lt 20; $i++) {
        try { $s = [IO.File]::Open($f.FullName, 'Open', 'Read', 'None'); $s.Close(); break } catch { Start-Sleep -Milliseconds 250 }
    }
    $script:vistos[$f.Name] = $true
    $script:n++
    $ahora = Get-Date
    $dt = ($ahora - $script:tPrev).TotalSeconds
    $script:tPrev = $ahora
    Write-Host ("Saved: '{0}'  [{1}/{2}]  {3:HH:mm:ss}  ({4:N1} s)" -f $f.FullName, $script:n, $script:total, $ahora, $dt)
}

# Lanza Blender oculto con el script DLSS (la configuracion va en variables de entorno) y cuenta los PNG que aparecen en $salida
function Correr-Blender($salida, $totalFrames) {
    $script:out = $salida
    $script:total = $totalFrames
    $script:vistos = @{}
    $script:n = 0
    # pantalla completa: asi el viewport mide 1920x1080 y cada frame se renderiza de una sola vez (sin teselas)
    $a = @('--window-fullscreen', ('"' + $env:BLEND_FILE + '"'), '--python', ('"' + $env:SCRIPT + '"'))
    $p = Start-Process -FilePath $env:BLENDER_EXE -ArgumentList $a -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $env:LOG -RedirectStandardError ($env:LOG + '.err')
    $null = $p.Handle          # sin esto PowerShell no puede leer el codigo de salida
    $script:t0 = $p.StartTime
    $script:tPrev = Get-Date
    $ultimaBusqueda = Get-Date
    Write-Host "Blender arrancando (oculto)..."
    while (-not $p.WaitForExit(150)) {
        [void][Ventanas]::Ocultar([uint32]$p.Id)       # el splash y la ventana principal se ocultan en cuanto aparecen
        if (((Get-Date) - $ultimaBusqueda).TotalSeconds -ge 1.5) {
            $ultimaBusqueda = Get-Date
            foreach ($f in Nuevos) { Informa $f }
        }
    }
    foreach ($f in Nuevos) { Informa $f }
    Write-Host ""
    Write-Host ("Blender termino (codigo {0}). Frames guardados: {1} de {2}" -f $p.ExitCode, $script:n, $totalFrames)
    if ($script:n -lt $totalFrames) {
        Write-Host "Faltan frames. Ultimas lineas relevantes del registro:"
        Get-Content $env:LOG -ErrorAction SilentlyContinue | Select-String 'DLSS_CMD|Traceback|Error:|DLSS Render' |
            Where-Object { $_ -notmatch 'NGX|HIPEW' } | Select-Object -Last 8 | ForEach-Object { Write-Host "  $_" }
    }
    return $script:n
}

$ini = [int]$env:DLSS_START
$fin = [int]$env:DLSS_END
$paso = if ($env:DLSS_STEP) { [int]$env:DLSS_STEP } else { 1 }
$out = $env:DLSS_OUT
$totalFase1 = [math]::Floor(($fin - $ini) / $paso) + 1

$n = Correr-Blender $out $totalFase1
