# Subdivisión de prendas

Parte un personaje de `biblioteca_personajes/` en prendas, detalles y piezas. Cada una queda en su carpeta con un `.blend` (esqueleto, pesos, material y texturas empaquetadas) y una `vista.png`. El `.blend` original no se guarda.

```
<personaje>/prendas/<prenda>/<prenda>.blend
                    <prenda>/detalles/<detalle>/<detalle>.blend
                    <prenda>/detalles/<detalle>/detalles/<pieza>/<pieza>.blend
                    .../<pieza>/detalles/<zona>/<zona>.blend
```

Usa Blender 5.3 Beta (`blender-5.3...` en `Program Files/Blender Foundation`). Con otra versión, define `BLENDER` antes de ejecutar `flujo.sh`.

## Flujo

| Paso | Herramienta | Qué hace | Dónde corre |
|---|---|---|---|
| 1 | `paso1_detalles_3d.py` | Convierte en mallas los detalles pintados y modela las hombreras | Dentro de Blender, en el personaje abierto |
| 2 | `paso2_ropa_foto.py` | Pone tela y cuero fotografiados en los materiales | Dentro de Blender, en el personaje abierto |
| 3 | `paso3_inspeccionar.py` | Lista las piezas de cada malla y dibuja sus UV sobre la textura | Sin ventana |
| - | `personajes/<personaje>.py` | Configuración escrita a mano con lo visto en el paso 3 | - |
| 4 | `paso4_subdividir.py` | Genera todos los `.blend` y las fotos | Sin ventana |
| 5 | `paso5_comprobar.py` | Comprueba archivos, áreas y deformación en pose | Sin ventana |
| 6 | `paso6_auditar.py` | Busca archivos que aún tienen piezas sin separar | Sin ventana |
| - | `hoja_contacto.py` | Junta las fotos en una imagen para revisarlas | Python normal |

`flujo.sh` ejecuta 4, 5, 6 y la hoja seguidos.

### Textura de cine y desgaste de batalla (pasos 7 y 8)

| Paso | Herramienta | Qué hace | Dónde corre |
|---|---|---|---|
| 7 | `paso7_textura_cine.py` | Rehace una cinta en anillo y teje su textura hilo a hilo (35 s y unos 23 MB) | Dentro de Blender, o llamado por el paso 8 |
| 8 | `paso8_cine_lote.py` | Aplica material y desgaste a todos los detalles finales (unos 3 s y 2 MB por pieza) | Sin ventana |
| 9 | `paso9_montar_cine.py` | Monta los detalles sobre el esqueleto en un archivo nuevo; el original no se guarda | Sin ventana |
| 10 | `paso10_relieve_3d.py` | Suaviza las mallas del juego, levanta en 3D lo pintado y rehace las texturas borrosas | Sin ventana |
| 11 | `paso11_persona.py` | Separa la persona en detalles (piel por zonas, ojos, manos y cada tipo de pelo), con un `.blend` y una foto por detalle | Sin ventana |

```bash
blender -b personaje.blend --factory-startup --python paso8_cine_lote.py -- personajes/mi_personaje.py
blender -b personaje.blend --factory-startup --python paso9_montar_cine.py -- personajes/mi_personaje.py salida.blend
blender -b salida.blend --factory-startup --python paso10_relieve_3d.py -- personajes/mi_personaje.py personaje.blend salida_relieve.blend
```

- **Persona (pasos 10 y 11):** `crear_rostro` usa la malla base y las deformaciones de MPFB guardadas en `mpfb_datos` (CC0). El paso 11 deja cada detalle en `<personaje>/persona/<detalle>/`. Las zonas de piel conservan las normales de la cabeza entera.
- **Mallas suaves (paso 10):** `RELIEVE` nombra las mallas que se sueldan y subdividen, cada una con sus zonas y materiales. `SUAVES_RUTAS` y `SUAVES_NOMBRES` suavizan piezas sueltas. Asi desaparecen las aristas de carton y las normales del juego, que causaban parches de luz.
- **Relieve (paso 10):** cada pieza de `RELIEVE` dice que zona de la textura se levanta y a que altura. `respeta_borde` hace que baje antes del borde de la malla, para zonas que llegan hasta el. `QUITAR` lista lo que sale. Las cajas y alturas son de ese personaje: otro necesita las suyas.
- **Texturas (paso 10):** `pintar` redibuja a alta resolucion lo que el juego tenia borroso. En el Black Watch, los cuadros de las medias y el tartan. `forma` cambia la malla ya suavizada, como los pliegues del kilt. `extra` crea prendas nuevas sobre la malla, como las polainas, y `FINAL` lista funciones que corren al acabar, como el bonete de pelo y el sporran. `RECETAS_NUEVAS` ajusta el desgaste de cada material.
- **Salida:** `<personaje>/prendas_cine`, con la misma estructura. `prendas/` no se toca.
- **Recetas:** la lista `CINE` de la configuración asigna a cada detalle `sarga`, `pano`, `tartan`, `galon`, `ante`, `cuero`, `metal`, `pluma` o `anillo`. Una pieza sin receta se avisa con `SIN_RECETA` y no se genera.
- **Caras visibles:** cada cara lanza rayos contra el personaje completo en pose T. Las que quedan tapadas no reciben desgaste.
- **Desgaste continuo:** barro, hollín y manchas se calculan con la posición real en el cuerpo, así que continúan de una pieza a otra.
- **Filtro para probar:** añade la carpeta de salida y una lista de textos de ruta separados por comas.
- **Reglas de material:** el `Sheen Tint` debe ir conectado al color (en blanco, la tela se ve gris) y `Falloff` debe ser bajo (con el valor del grupo, el rojo se lava). En Cycles, las mallas de pocas caras necesitan `shadow_terminator_offset` para no dibujar sombras en punta.

## Cómo hacerlo con otro personaje

**1. Preparar el personaje (opcional).** Abre su `.blend` en Blender y, en la consola de Python, ejecuta:

```python
exec(open(r"...\subdivision_prendas\paso1_detalles_3d.py", encoding="utf-8").read())
exec(open(r"...\subdivision_prendas\paso2_ropa_foto.py", encoding="utf-8").read())
```

Guarda el archivo si te gusta el resultado. Estos dos scripts solo están probados en el Black Watch soldado: revisa `hombreras()` y `pesos_de_manga()` del paso 1 y `REPETIR` y `mascara()` del paso 2, porque usan nombres de malla y zonas de textura de ese personaje.

**2. Inspeccionar.**

```bash
blender -b personaje.blend --factory-startup --python paso3_inspeccionar.py -- carpeta_de_inspeccion
```

Anota las piezas que imprime y abre los `<malla>_uv.png`. La rejilla azul marca cada 50 píxeles de textura; úsala para medir las zonas.

**3. Configurar.** Copia `personajes/plantilla.py` con el nombre del personaje y rellena, en este orden:

- `PRENDAS`: qué mallas forman cada prenda. Una malla compartida se corta por caras con una función de zona.
- `DETALLES`: cómo se reparten las piezas conectadas de cada prenda, o qué objetos 3D le tocan según su nombre.
- `CON_TROZOS` y `PINTADAS`: déjalos vacíos la primera vez.

**4. Generar y revisar.**

```bash
bash flujo.sh personaje.blend personajes/mi_personaje.py
```

Revisa la salida:

- Debe terminar en `TOTAL ... MAL 0`.
- `VARIAS` indica archivos con piezas sin separar: añade a `CON_TROZOS` los que tengan piezas limpias.
- Abre `prendas/hoja.png` y busca detalles que sigan pintados en una sola malla.

**5. Cortar lo pintado.** Ejecuta el paso 3 sobre la pieza (su `.blend`), mide en el `_uv.png`, escribe una función de zonas y añádela a `PINTADAS`.

**6. Repetir solo lo nuevo.** La cuarta variable de `flujo.sh` elige las etapas (`prendas,detalles,piezas,trozos,pintadas`). Cada etapa lee lo que dejó la anterior:

```bash
bash flujo.sh personaje.blend personajes/mi_personaje.py "" trozos,pintadas
```

Antes de repetir `trozos` o `pintadas`, borra a mano la carpeta `detalles` de esas piezas si cambiaste de nombres: el script sobrescribe, pero no borra lo que ya no genera.

## Reglas aprendidas

- **Lados con la misma UV:** izquierda y derecha comparten textura, así que hay que separar por pieza conectada en 3D, nunca por isla de UV. `D` es x positivo. En piezas centrales la letra no significa nada.
- **Umbrales de UV con margen:** los valores impresos están redondeados. Un 0.69 puede ser 0.685.
- **Comprobar la pieza suelta:** un detalle puede verse bien puesto en la prenda y ser una esquirla al aislarlo. Por eso cada archivo lleva foto propia.
- **Esquirlas:** si `paso6_auditar.py` da cientos de trozos de pocas caras, no los separes. Con unos 25 MB por archivo, los 5.600 trozos del Black Watch necesitarían unos 140 GB.
- **Grupos de vértices:** sus nombres viven en la malla, no en el objeto. Al cambiar `o.data` hay que crearlos de nuevo en el mismo orden (`malla_cortada`).
- **Límite de ruta:** Windows no abre rutas de más de 260 caracteres, y el motor se detiene con un error a los 255. Si ocurre, pasa una carpeta de salida más corta o acorta los nombres.

## Pruebas hechas (31 oct 2026)

- **Black Watch soldado, desde cero:** `flujo.sh` tardó unos 13 minutos y dio los mismos 338 archivos, con áreas y desvíos iguales a los de `prendas/` y `MAL 0`.
- **Highland Foot soldado, con la configuración del Black Watch:** generó 129 archivos con `MAL 0`, pero el puño es distinto y las `presilla_N` salieron mal cortadas. `MAL 0` no valida los cortes: hay que mirar la hoja de fotos.
- **Cosaco soldado:** el paso 3 y `plantilla.py` sin editar funcionaron de principio a fin, con avisos por lo que ese personaje no tiene.
- **Sin probar en otro personaje:** los pasos 1 y 2.

## Limitaciones

- **Sin automatizar:** la configuración se escribe a mano para cada personaje, porque cada uno tiene su textura y sus UV. Solo pueden compartirla personajes con el mismo modelo y la misma textura; compruébalo siempre con la hoja de fotos.
- **Corte de lo pintado:** da láminas sin grosor sobre la superficie de la prenda. Los bordes siguen una textura de baja resolución y pueden quedar irregulares.
- **Relieve del paso 1:** botones, cordones, ligas, hebillas y ribete salen como esquirlas con púas. Solo las hombreras están modeladas como piezas limpias.
- **Peso en disco:** el Black Watch soldado ocupa 8.2 GB en 338 archivos, porque cada `.blend` lleva sus propias texturas.
- **Materiales:** se ven en Blender; no pasan a `.glb`.
- **Animación:** el paso 5 prueba una pose con todos los huesos girados, no clips de animación.
