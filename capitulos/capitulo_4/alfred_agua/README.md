# Alfred Agua

Pone **agua de Minecraft** en la escena: cascadas por un hueco y agua que se reparte por el suelo, desde el frame que se pida. Esta hecho para que la IA aprenda a colocar agua con una llamada;
el ejemplo es la cascada de la cueva de Alfred (hueco de la celda (-49, -19), agua desde el frame 150, 100 frames en caer).
Panel: Vista 3D > barra lateral (N) > **Agua MC**. Guion del ejemplo original: `capitulos/capitulo_4/hueco_agua_49_19.py`.

## Reglas de Minecraft que usa
| que | como |
|---|---|
| columna que cae | cubo completo de 1x1 que crece de arriba hacia abajo en `duracion` frames; textura `water_flow.png` (32 cuadros de 32x32), una tira por metro |
| agua en el suelo | nivel 7 donde cae la columna, **un nivel menos por bloque**, solo sobre suelo firme; altura = 0.875 * nivel / 7; textura `water_still.png` |
| borde sin suelo | el agua cae en vertical (cubo completo, textura de flujo) hasta el siguiente suelo y **reinicia en nivel 7** donde aterriza |
| tiempo | un bloque cada 5 ticks = **6 frames** (`tick`); cada cuadro de textura dura 2.4 frames (`cuadro`) |
| color | las texturas son grises: se tienen con **#4573FF** (`color`), opacidad 0.85 (`alfa`), brillo propio 0.1 (`emision`) y ganancia 1.2 (`ganancia`) |
Con poco brillo propio la luz de la escena decide: la cara que mira a la pared sale mas oscura que la que mira a la luz. Si el agua queda muy oscura se sube `ganancia` o `emision`.

## Como lee el mundo
Los bloques sueltos `bloque_<tipo>_<i>_<j>_<k>` de la coleccion `cueva_bloques` (`coleccion_bloques=` para otra). La celda (i, j, k) ocupa x i..i+1, y j..j+1, z k..k+1.
`agua.analizar((i, j))` dice que bloques hay en esa columna, que paredes tiene y cual es el suelo (k del aire que queda sobre el primer bloque hacia abajo).

## Uso (IA)
```python
import importlib.util, sys
spec = importlib.util.spec_from_file_location("alfred_agua_local", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_agua\__init__.py")
agua = importlib.util.module_from_spec(spec); sys.modules["alfred_agua_local"] = agua; spec.loader.exec_module(agua); agua.register()

agua.analizar((-49, -19))                                   # decidir antes de poner
agua.cascada(celda=(-49, -19), z_superficie=8, frame=150, duracion=100, abrir_hueco=True)   # el ejemplo (abrir_hueco quita el techo y levanta las paredes)
agua.derramar(en=(-30.5, -10.5, -9.0), frame=200)           # reparto por el suelo desde un punto (como vaciar un cubo)
agua.estado(); agua.quitar("cascada_-49_-19"); agua.quitar()
agua.plan_aplicar([{"tipo": "cascada", "celda": [-49, -19], "frame": 150, "duracion": 100}])
agua.plan_guardar("agua_plan.json")
```
Opciones de ambas: `color`, `alfa`, `emision`, `ganancia`, `rugosidad`, `cuadro`, `tick`, `radio` (nivel inicial, 7), `receptores` (coleccion de luz con light linking a la que se anade el agua; por defecto `luz_entrada_receptores`, `""` = ninguna), `id` (para rehacer sin duplicar).
`cascada(..., k_suelo=...)` si el suelo no se detecta; `abrir_hueco=True` usa `k_techo` (-2) y `k_tope` (7) para la chimenea.
Todo vive en la coleccion `agua_mc` (un objeto por tick y tipo, asi se ve como se va extendiendo) con la propiedad `agua_id`; el registro esta en `scene["agua_registro"]`.

## Pruebas
Blender 5.2.1 en segundo plano con un mundo de bloques de prueba (suelo con escalon, techo, hueco): analiza, abre el hueco, pone cascada + derrame, guarda / aplica planes y renderiza (el agua se ve azul con la textura y las alturas por nivel). El panel no se ha probado con la interfaz abierta; la cascada real de la cueva de Alfred se hizo antes con `hueco_agua_49_19.py`, con el mismo reparto.
