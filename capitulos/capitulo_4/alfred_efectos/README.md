# Alfred Efectos

Sincroniza los efectos de `C:\Users\user\Desktop\Alfred_Animacion\efectos` (47 `.blend`, ~2 GB) con la animacion. Pensado para que la IA lo use con **una llamada por efecto** (o un plan de varios) sin tocar los `.blend` de los efectos.
Panel: Vista 3D > barra lateral (N) > **Efectos MC**. Se puede usar tambien solo por Python (ver abajo).

## Que hay en la carpeta `efectos` (analizado)
| tipo | archivos | como es por dentro |
|---|---|---|
| **sprites** (34) | `Angry`, `Big_smoke`, `Cherry`, `Critical`, `Damage`, `Drip`, `Effect`, `Enchanted`, `Explosion`, `Flame`, `Flash`, `Generic`, `Glint`, `Glitter`, `Glow`, `Goldheart`, `Heart`, `Lava`, `Nautilus`, `Note`, `Sculk_charge`, `Sculk_charge_pop`, `Sculk_soul`, `Sga`, `Shriek`, `Sonic_boom`, `Soul_fire`, `Soul`, `Spark`, `Spell`, `Splash`, `Sweep`, `Vibration` (`*_frame.blend`), `burbuja`, `charco_de_agua` | UNA particula de Minecraft: un EMPTY que instancia una coleccion de laminas planas (una por cuadro). Cada lamina se ve un frame con llaves `hide_viewport`/`hide_render`. Duran de 1 a 26 frames (Explosion 16, Sga 26, Critical 1). Una lamina sola no es un efecto: hay que emitir varias |
| **tnt** (2) | `TNT_slow_explode_frame_1` (103 frames), `TNT_instant_explode_1` (12) | bloque que se deforma + explosiones (copias de `Explosion_frame`) + humo con sistemas de particulas |
| **clima** (6) | `Rain`, `Snow`, `Ash`, `Spores`, `Firefly`, `Leafy_Wind` | un plano con el modificador de nodos *Camera Weather Nodes* + un EMPTY "origin" (el seguidor) |
| **clima por particulas** (2) | `Rain_1`, `Snow_1` | plano de 40x40 m con 11272 gotas / 8060 copos |
| **modelo** (1) | `trueno` | 9 rayos 3D (glTF) |
Todos los `.blend` traen ademas las mismas colecciones de relleno (hojas, gotas, copos, humo generico). Las texturas apuntan a la carpeta de MCprep de Blender 4.5, que ya no existe: el addon las vuelve a enlazar solo con `MCprep_addon/.../textures` del proyecto.

## Como funciona
1. `cargar(efecto)` trae la plantilla (una sola vez) oculta en la coleccion `FX_biblioteca`.
2. `colocar(...)` **clona** el efecto en el frame pedido: copia los objetos y mueve (y estira) todas las llaves, asi cada efecto empieza donde quieres y dura lo que quieres (`vida`). La primera lamina aparece justo en el frame pedido (se comprobo con Explosion, Cherry y Critical).
3. Para particulas "sueltas" se emiten varias copias (`cantidad`) con un **patron** (`radial`, `sube`, `cae`, `explota`, `cono`, `ninguno`): salida con velocidad + gravedad, escala que aparece y se apaga, y una restriccion *Track To* que las gira hacia la camara.
4. Todo lo creado lleva el prefijo `FX_`, la propiedad `fx_id` y vive en `FX_efectos/FX_<id>`; `quitar()` lo borra por completo (objetos, colecciones, acciones). El registro queda en `scene["fx_registro"]`.

## Uso por Python (IA)
```python
import importlib.util, sys
spec = importlib.util.spec_from_file_location("alfred_efectos_local", r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\alfred_efectos\__init__.py")
fx = importlib.util.module_from_spec(spec); sys.modules["alfred_efectos_local"] = fx; spec.loader.exec_module(fx); fx.register()

fx.catalogo()                 # [{id, etiqueta, tipo, etiquetas, patron, vida, escala, nota, archivo}]
fx.buscar("golpe")            # por palabra: golpe, humo, fuego, magia, curar, agua, polvo, explosion, lluvia...

fx.colocar("Critical_frame", 58, en="alfred:Rightelbow_alfred:tail", patron="radial", cantidad=8)   # en el hueso, frame 58
fx.colocar("Generic_frame", 210, en=(-44.6, -13.5, -9.5), patron="radial", cantidad=14, vida=16, escala=1.2)
fx.colocar("Explosion_frame", 120, en="bloque_techo_pozo", escala=3)
fx.colocar("Heart_frame", 40, en="jerry", desplazar=(0, 0, 2), patron="sube", cantidad=4, seguir=True)
fx.colocar("Rain", 1, hasta=240)                      # clima: sigue a la camara (nodos) entre dos frames
fx.colocar("trueno", 90, en=(10, 30, 0), hasta=100)   # parpadea como un rayo
fx.colocar("TNT_instant_explode_1", 150, en=(0, 0, 0))

fx.plan_aplicar([{"id": "golpe_1", "efecto": "Critical_frame", "frame": 58, "en": "alfred", "cantidad": 8}, ...])   # varios de una vez (idempotente)
fx.plan_guardar("efectos_plan.json"); fx.plan_cargar("efectos_plan.json")
fx.estado(); fx.quitar("golpe_1"); fx.quitar(); fx.quitar(origen="auto")
```
`en`: `(x, y, z)` | `"Objeto"` | `"Objeto:Hueso"` (cabeza) | `"Objeto:Hueso:tail"` | `"cursor"` | `{"objeto":..,"hueso":..,"punto":"tail","desplazar":[..]}`. `desplazar=(dx,dy,dz)` mueve en el mundo. `seguir=True` hornea la posicion del objeto mientras dura el efecto.
Opciones de `colocar`: `cantidad`, `patron`, `vida` (frames de cada particula), `escala`, `vel` (m/s), `grav` (m/s2, + cae), `dispersion` (m), `retraso` (frames al azar entre particulas), `direccion` (para `cono`), `hasta` (clima / trueno), `semilla`, `camara=False` (sin mirar a la camara), `id`. En el clima por nodos se pueden pasar `densidad`, `semilla`, `tiempo`, `extension` o el nombre de cualquier entrada del modificador.

## Sincronizar solo
* `fx.eventos(f0, f1)`: mira la animacion (objetos animados, visibles, que no sean del addon) y devuelve `impacto` / `impacto_fuerte` (baja rapido y rebota o se frena), `lanzamiento` (acelera de golpe), `aparece` / `desaparece` (llaves de `hide_*` o de escala a 0), con frame, objeto, posicion y fuerza.
* `fx.sugerir(f0, f1)`: propone un plan segun la tabla `REGLAS` (impacto -> polvo; impacto fuerte -> polvo + chispas criticas; aparece -> destellos; desaparece / rompe -> humo...). `fx.aplicar_sugerencias()` lo pone (origen `auto`, se rehace sin duplicar). Las reglas se cambian con `efectos/reglas_usuario.json`: `{"impacto": [["Generic_frame","radial",10,1.0,14]]}` (efecto, patron, cantidad, escala, vida).
* `fx.desde_sonidos(en=...)`: lee las tiras `SND_*` del add-on **Alfred Sonidos** y pone el efecto que le toca en el frame de cada una (`block.*.break` -> polvo + humo, `big_fall` -> polvo, `attack.crit` -> chispas, `hurt` -> dano, `explode` -> explosion, `anvil` / `chain` -> chispas...). Asi sonido y efecto quedan en el mismo frame.

## Notas
* Los efectos son hojas 2D con textura de Minecraft; se ven en Eevee y Cycles. Cada particula clonada son 1-26 objetos: para rafagas grandes bajar `cantidad`.
* El **TNT** y los sprites compuestos se clonan enteros (con sus sistemas de particulas); el clima por nodos usa la camara activa como seguidor.
* Probado en Blender 5.2.1 en segundo plano: los 46 efectos del catalogo se colocan sin error (`Rain_1_sin_plano` se omite, es igual que `Rain_1`); tiempos de aparicion exactos en Explosion, Cherry y Critical; render de prueba de sprites, explosion, lluvia por nodos y trueno. El panel de la interfaz no se ha probado con Blender abierto.
