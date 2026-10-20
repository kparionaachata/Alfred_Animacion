# Variador de música instrumental

Sistema local e independiente de `voz_a_voz`. Recibe una pista instrumental de
10 segundos a 10 minutos y crea de 1 a 4 reinterpretaciones mediante ACE-Step
1.5. La pista original nunca se sobrescribe.

## Abrir

1. Ejecuta `Abrir Variador de Musica.cmd`.
2. Carga un WAV, MP3, FLAC, OGG, OPUS, M4A o AAC.
3. Describe la instrumentación o el ambiente deseado.
4. Ajusta la fidelidad: 0.2 transforma mucho; 0.95 conserva mucho.
5. Elige de 1 a 4 variaciones y pulsa **Generar variaciones**.

La interfaz queda en `http://127.0.0.1:6973` y el motor privado en
`http://127.0.0.1:6974`. La primera generación descarga y carga los modelos, por
lo que tarda bastante más que las siguientes.

## Aprendizaje

Una canción de tres minutos sirve como **condicionamiento**, no como un conjunto
de entrenamiento. Después de cada lote se puede puntuar un resultado. El sistema
aprende qué descripción y grado de fidelidad reciben 4 o 5 estrellas y los
propone con **Aplicar lo aprendido**.

El entrenamiento profundo LoRA queda fuera de esta instalación porque la RTX
3050 tiene 6 GB de VRAM y ACE-Step documenta 16 GB como mínimo para entrenamiento.
Presentarlo como entrenamiento local funcional en esta máquina sería incorrecto.

## Carpetas

- `entradas/`: copias preservadas de las pistas cargadas.
- `resultados/<lote>/`: WAV generados.
- `historial/`: parámetros, semillas y rutas de cada lote.
- `aprendizaje/calificaciones.jsonl`: elecciones del usuario.
- `motor.*.log` y `estudio.*.log`: diagnóstico.

## Privacidad y derechos

Todo se procesa localmente. Usa música propia, licenciada o para la que tengas
permiso de crear obras derivadas. El modelo está configurado siempre como
instrumental (`[Instrumental]`) y añade instrucciones explícitas de no generar voz.

## Motor

- ACE-Step 1.5, modelo turbo, modo `cover`.
- 48 kHz estéreo, salida WAV.
- Descarga del modelo y del DiT a RAM activada para la RTX 3050 de 6 GB.
- El planificador LLM se desactiva para ahorrar VRAM; el modo cover no lo necesita.
