---
name: texto-a-animacion-voz
description: Cuando un personaje (Alfred o Jerry) tenga que HABLAR en una animacion o haya un dialogo/guion de texto, generar SIEMPRE su voz clonada y la animacion del rostro sincronizada con el sistema "de texto a animacion +voz" (F5-TTS con la voz del usuario + RVC de Jerry + estudio_audio_expresion), y luego meter el audio y las claves del rostro en la escena en el frame correcto. No grabar ni inventar voces, no animar bocas/ojos a mano.
---

# Texto -> voz + rostro dentro del flujo de animacion

Sistema: `C:\Users\user\Desktop\Alfred_Animacion\de texto a animacion +voz\` (ver su `LEEME.md`).
Es un sistema PARALELO: no se modifica `voz_a_voz` ni `estudio_audio_expresion`; solo se usan.
GPU: siempre la RTX 3050 (`CUDA_VISIBLE_DEVICES=0`), nunca la T400.

## 1. Guion

Archivo `.txt` (UTF-8) en la carpeta del sistema, una linea por dialogo:
```
ALFRED [enojo]: No me vengas con tonterias, Jerry!
JERRY [sorpresa]: ¿En serio? ¡Genial! Por fin vamos a dormir.
```
- Emociones: neutral, enojo, alegria, tristeza, sorpresa, miedo, duda (sin grabacion propia usa la mas parecida, `emocion_parecida` en `config.json`).
- Emocion/enfasis por PALABRA solo donde la frase lo pida: `{enojo:no me vengas}` y `*palabra*` (`prosodia_palabras.py`).
- Escribir "Jerry" normal: el sistema lo cambia a "Yerrri" y refuerza la RR (`config.json` -> `pronunciacion`, `reforzar_rr`).

## 2. Generar (en segundo plano, tarda minutos)

```
cd "C:\Users\user\Desktop\Alfred_Animacion\de texto a animacion +voz"
..\voz_a_voz\Applio\env\Scripts\python.exe texto_a_animacion.py guion.txt --nombre <escena> --video
```
Una sola frase: `--texto "..." --personaje Alfred|Jerry --emocion <emocion> --nombre <escena>`.

Motor por defecto F5 (`env_f5`) con las grabaciones del usuario (`referencias_usuario\`): un juez elige la mejor de hasta 8 tomas (Whisper = texto correcto, WavLM = parecido a la voz del usuario, fluidez). Alfred va SIN RVC (es la voz del usuario); Jerry pasa por RVC `Jerry_100e_14100s.pth`.
No cambiar a edge-tts ni Chatterbox (robotico / acento chileno, rechazados por el usuario).

Resultado en `resultados\<escena>\`:
- `NN_personaje_frase\voz.wav`, `animacion_<personaje>.py` (rostro), `plan.json`, `voz_con_rostro.mp4` (vista previa).
- `dialogo.json`: frame_inicio/frame_fin de cada linea (24 fps, 10 frames entre dialogos).
- `dialogo_completo.wav`: todo el dialogo seguido.

Antes de meterlo en la escena: entregar al usuario el `voz_con_rostro.mp4` / `voz.wav` y esperar su visto bueno. Nunca dar la voz ni la animacion por aprobada.

## 3. Meter en la escena de Blender

Solo con autorizacion del usuario para tocar el `.blend`. Los `animacion_<personaje>.py` estan hechos para frame 1 y, al ejecutarse, BORRAN la animacion previa de los ojos/cejas/mandibula y cambian `frame_start/frame_end` de la escena. Por eso NO se ejecutan tal cual en una escena con animacion:

1. Elegir el frame de la escena donde empieza la frase (`F`) y el personaje (Alfred: `ojo_izquierdo_alfred`/`ojo_derecho_alfred`; Jerry: su rig con mandibula y `sejas_1_jerry`/`sejas_2_jerry`).
2. Guardar `frame_start`, `frame_end` y fps de la escena; ejecutar el script; restaurarlos despues.
3. Desplazar `F - 1` frames solo las claves que creo el script (las de los objetos/huesos del rostro de ese personaje) y, si el personaje ya tenia claves de rostro en ese tramo, quedarse con las nuevas solo dentro de `[F, F + duracion]` sin borrar las de fuera (copia de seguridad de las acciones antes de ejecutar).
4. Audio: añadir `voz.wav` como strip de sonido en el VSE en el frame `F` (canal libre, nombre `voz_<personaje>_NN`). Para un dialogo entero, usar los `frame_inicio` de `dialogo.json` + `F - 1`.
5. Despues de añadir voces, volver a aplicar las reglas de sonido del proyecto (ducking de voces -5 dB, distancia a camara) si la escena las tiene.
6. Verificar en el frame `F` y a mitad de la frase que el rostro se mueve con la voz (captura o render de vista previa) antes de entregarlo.

Combinar con las demas skills de la escena (desplazamientos, `inercia-accion-reaccion`, `lanzador-mira-objetivo`...): la voz y el rostro no sustituyen la animacion del cuerpo.

## Problemas conocidos

- Las transiciones entre palabras aun pueden sonar algo roboticas (F5 ~2.7-3.0 micro-cortes/s; el usuario 1.4-2.9). XTTS-v2 esta instalado (`env_xtts`, `tts_xtts.py`) pero requiere que el USUARIO acepte la licencia CPML (no comercial); no aceptarla por el.
- Jerry tras RVC: Whisper a veces oye mal alguna palabra ("Por fin" -> "Por no") aunque la base este bien; escuchar antes de descartar.
- Leer guiones/config con `utf-8-sig`; en PowerShell usar siempre `-Encoding utf8`.
