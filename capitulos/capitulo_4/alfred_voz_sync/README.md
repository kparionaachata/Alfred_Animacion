# Alfred Voz Sync (add-on de Blender)

Sincroniza la **voz de Alfred o de Jerry** con su animacion y le da la **emocion** del audio, como **capas aditivas** sobre lo que el personaje ya tenga (si corre, sigue corriendo). Para Alfred ademas coloca la **animacion facial de los ojos** que genera la app `estudio_audio_expresion`.

* **Jerry**: mandibula (`jaw_bot`) con cada silaba; cabeza (`scull`, `scull_1`); segun la emocion: cejas (poses del estudio), orejas, cola, columna, ojos (`Closed`).
* **Alfred**: cabeza (`Neck_alfred` + `Spine2_alfred`), inclinacion y respiracion del torso y la **expresion facial generada** (shape key `Voz_<audio>` de cada ojo + desplazamiento, escala y giro de los ojos, con el retardo entre ojos de la app).

## Carpeta de audios

```
C:\Users\user\Desktop\Alfred_Animacion\audios\
    alfred\   <- voces de Alfred (mp3, wav, ogg, flac, m4a... ; se aceptan subcarpetas)
    jerry\    <- voces de Jerry
```

## Instalar
1. Blender: *Edit > Preferences > Add-ons > flecha de arriba a la derecha > Install from Disk...* y elige `alfred_voz_sync.zip` (esta misma carpeta) y activalo.
2. Panel: *Vista 3D > barra lateral (N) > pestana "Voz Sync"*.

## Flujo de trabajo
1. Copias el audio a `audios\alfred` o `audios\jerry`.
2. **Analizar con Whisper** (o la herramienta por linea de comandos): transcribe con Whisper Base local, mide la prosodia, usa los ejemplos que aprobaste en la app (`estudio_audio_expresion\aprendizaje`, solo se leen) y escribe junto al audio:
   * `<audio>.emocion.json`: texto, emocion, intensidad, confianza, puntajes y las palabras con su tiempo.
   * `<audio>.cara.json`: geometria de los ojos de Alfred (mezcla de las expresiones aprobadas de `catalogo_ojos`) y parametros de la animacion facial.
3. Eliges el **frame de inicio** del audio (campo `f` de la lista) y pulsas **Sincronizar**: voz + emocion + cara, y el audio en el editor de secuencias.
4. **Quitar** / **Quitar todos** devuelven al personaje a como estaba (los canales sin animacion de base recuperan su valor, se borran las shape keys `Voz_*`).

Herramienta por linea de comandos (Python de la app, con librosa / torch / transformers):
```
..\..\..\voz_a_voz\Applio\env\Scripts\python.exe herramientas\analizar_audio.py "C:\...\audios\alfred\fdfdfdfff.mp3" [--emocion duda] [--texto "texto corregido"] [--sin-cara]
```

## Emocion: como se decide (por orden)
1. Lo que elijas en el panel (**Emocion** distinta de *Automatica*) y su **Intensidad**.
2. **`<audio>.emocion.json`** (lo escribe la herramienta; tambien se puede editar a mano o crear con *Guardar contexto*):
   ```json
   { "texto": "Y ahora, ¿que hacemos?", "emocion": "DUDA", "intensidad": 1.25,
     "segmentos": [ {"desde": 0.0, "hasta": 1.2, "emocion": "DUDA", "intensidad": 1.0} ],
     "palabras": [ {"t0": 0.46, "t1": 1.12, "w": "ahora"} ] }
   ```
   `segmentos` permite cambiar de emocion dentro del audio (transicion suave). Cada palabra conocida provoca un cabeceo, anclado a la subida real de energia (Whisper da tiempos aproximados).
3. El **texto** (palabras clave en espanol) y 4. la **estimacion acustica** (aproximada: dice como suena, no que significa).

Emociones: NEUTRO, ENOJO, ALEGRIA, TRISTEZA, SUENO (cansancio), MIEDO, SORPRESA, DUDA. La app `estudio_audio_expresion` no tiene MIEDO; el add-on si.

## Que hace cada emocion (a intensidad 1)
| Emocion | Cabeza / torso | Ojos Alfred (sin `.cara.json`) | Jerry |
| --- | --- | --- | --- |
| ENOJO | cabeza +8 grados abajo, cabeceos secos, temblor 11 Hz, torso adelante | Enojado | cejas enojado, orejas atras, cola baja, mandibula x1.3 |
| ALEGRIA | cabeza arriba, vaiven, giros amplios | Feliz | orejas adelante, cola arriba menendose |
| TRISTEZA | cabeza +14 grados abajo, inclinada, encorvado | Triste + Cansado | cejas triste, orejas y cola caidas |
| SUENO | cabeza cae lento y sube de golpe cada ~3.6 s, respiracion lenta | Cansado + Closed 0.5 | ojos entrecerrados, orejas y cola bajas |
| MIEDO | cabeza atras, temblor 16 Hz, respiracion rapida | Sorpresa + Sospecha | cejas triste, orejas atras, cola entre las patas |
| SORPRESA | cabeza y torso atras | Sorpresa | cejas sorprendido, orejas y cola arriba |
| DUDA | cabeza ladeada (roll 7 grados) y ligeramente arriba, vaiven lento | Sospecha + Triste | una ceja alzada (estudio), orejas algo adelante |

## Cara de Jerry (script de la app)
La app de expresion facial genera para Jerry un `animacion_jerry.py` (mandibula `jaw_bot`, hocico `jaw_top`, cabeza `scull` / `scull_1`, cejas, ojos con shape keys de expresion, pupilas y parpadeo). Ese script es destructivo (borra la animacion de los ojos y keyframea valores absolutos desde f1), asi que NO se ejecuta: `herramientas/importar_script_jerry.py <audio> <animacion_jerry.py>` lo lee con `ast` y escribe `<audio>.cara.json` (tipo `jerry`) y `<audio>.emocion.json`. Al sincronizar, el add-on crea las shape keys de expresion en las mallas de los ojos de Jerry si faltan (con el codigo de `jerry_animation_studio/eye_system.py`: subdivide la malla y crea Feliz / Triste / Enojado / Sospecha / Cerrado / Cansado / Sorpresa / Closed) y reproduce exactamente esa animacion como capas ADITIVAS desde el frame de inicio del audio (el frame 1 del script = el frame de inicio). La mandibula usa la envolvente de la app (`SPEECH_CURVE`) en lugar de la medida por el add-on; la emocion del cuerpo (cabeza, orejas, cola) se suma encima.

## Ojos de Alfred: neutro limpio y analisis automatico
* **Neutro limpio** (activado por defecto): las expresiones de los ojos (Feliz, Triste, Enojado, Sospecha, Cansado, Cerrado, Sorpresa) que ninguna animacion controla se dejan en 0. Antes se conservaba cualquier valor suelto del archivo (p. ej. Feliz y Cansado a 0.06 en `base_parte_3.blend`), y fuera de la animacion facial los ojos volvian a ese "neutro" con la muesca en arco en el borde inferior. El parpadeo (`Closed`) no se toca.
* **Analizar con Whisper si falta el contexto** (activado): al sincronizar, si el audio no tiene `.emocion.json` (o, siendo Alfred con emocion, `.cara.json`) se ejecuta la herramienta primero; asi los ojos siempre reciben la animacion facial del audio y no solo el neutro.

## Transiciones Elastic In-Out (Alfred)
Regla del proyecto: los movimientos expresivos usan **Elastic In-Out** (la misma curva que `ELASTIC_IN_OUT` del add-on Alfred Animation Studio). Con *Alfred: transiciones Elastic In-Out* (activado) se aplica a: el **torso** (inclinacion y respiracion de la emocion), la entrada, la salida y los cambios entre emociones (14 frames, sobreoscila ~10 % y termina exactamente en 0) y las fases de la **animacion facial de los ojos** (forma generada, expresiones apagadas, desplazamiento / escala / giro). **NO se usa en los huesos de la cabeza** (`Neck_alfred` y la parte de cabeza de `Spine2_alfred`): sus cabeceos, giros, inclinacion y la entrada / salida de su postura usan siempre transiciones suaves. Jerry no la usa.

## Ajustes
*Ganancia*, *Umbral de silencio*, *Apertura de mandibula* (Jerry), *Intensidad de la cabeza*, *Cabeceo / Giro / Inclinacion*, *Suavidad*, *Salida suave*, *Anticipo*, *Semilla*, *Animacion facial de la herramienta (Alfred)*, *Python de la herramienta*.

Si el personaje (o sus ojos) tiene una **accion activa** que anima esos canales, esta iria por encima del NLA y taparia la capa: con *Empujar la accion activa al NLA* (activada) pasa a una pista NLA (Push Down), sin cambiar la animacion.
