# Automatización de la cadena de cada parte

Tres herramientas que trabajan juntas:

1. **Una sola orden para reconstruir, solo desde el paso que cambió.** La lista de pasos de cada parte está en `cadenas/<archivo>.json`, por ejemplo `cadenas/base_parte_10.json`.
2. **Se reconstruye en segundo plano.** Un Blender sin ventana hace el trabajo y tu Blender no se bloquea. Antes se guarda un respaldo automático. Al terminar, el resultado se pone en el archivo y se vuelve a abrir.
3. **Chequeos automáticos.** Después de cada reconstrucción se escribe un informe con errores y avisos, cada uno con su frame.

## Cómo se usa

### Desde Blender (panel)
- **Cargarlo una vez:** *Editar > Preferencias > Complementos > Instalar desde disco…* y elige `addon_cadena.py`. Luego actívalo.
- **Usarlo:** visor 3D > barra lateral (tecla N) > pestaña **Cadena**.
  - **Automático:** reconstruye desde el primer paso que cambió. Si tocaste la escena a mano, reconstruye todo.
  - **Completo:** todos los pasos.
  - **Desde un paso…:** eliges el paso.
  - **Chequear al terminar** (casilla): desactívala para iterar rápido. Los chequeos tardan ~45 s.
  - **Solo chequear:** revisa la escena tal como está, sin guardar ni tocar el archivo.
  - Los botones **Informe, Log, Cadena y Respaldos** abren cada cosa con su programa.

### Desde la consola (con Blender cerrado o con el archivo ya guardado)
```
reconstruir.bat base_parte_10.blend            (automático)
reconstruir.bat base_parte_10.blend completo
reconstruir.bat base_parte_10.blend jerry_rio  (desde ese paso)
reconstruir.bat base_parte_10.blend chequeos
reconstruir.bat base_parte_10.blend auto rapido   (sin chequeos al final)
```

## Tiempos medidos (parte 10)
| Caso | Tiempo |
|---|---|
| Nada cambió | instantáneo ("la cadena ya está al día") |
| Cambió una voz o un paso posterior | ~1 min con chequeos, ~20 s sin chequeos (desde el checkpoint) |
| Cambió el script del arrastre, o la escena se tocó a mano | ~5 min (todo, arrastre ~3.5 min) |
| Primera vez en un archivo | siempre completo |

Una reconstrucción parcial deja exactamente la misma escena que una completa (comprobado con la huella).

## Qué se guarda y dónde
| Qué | Dónde |
|---|---|
| Respaldos (los 4 más nuevos de cada archivo; `respaldos_max` en la cadena) | `capitulo_4/respaldos_auto/` |
| Informe de chequeos | `automatizacion/informes/<archivo>_ultimo.txt` |
| Log, estado y checkpoints | `automatizacion/estado/<archivo>/` |
| Copias de audios y caras de las voces (no dependen de Descargas) | `automatizacion/entradas/<archivo>/` |

## Cómo decide desde dónde reconstruir
- Cada paso tiene una **huella**: su definición en el .json y el contenido de sus archivos (script, audio, cara y `depende_de`). Si cambias un paso, se rehacen ese paso y todos los siguientes.
- La escena también tiene una huella: objetos, claves, mallas, materiales, tiras y propiedades. No depende del frame en que estés.
  - Si la escena no se tocó a mano desde la última reconstrucción, se abre el **checkpoint** guardado después del último paso que no cambió y se sigue desde ahí.
  - Si se tocó, se rehace todo desde el paso 0.
- Los checkpoints son copias completas del .blend (~1.4 GB cada una). Por eso solo se guardan después de los pasos marcados con `"checkpoint": true`.

## Tipos de paso
| tipo | campos |
|---|---|
| `script` | `archivo` (se ejecuta con exec), `globales` opcional, `depende_de` opcional |
| `voz_rapida` | `inicio` (expresión con `T` = tiempos de la escena, p.ej. `"T['T_ARR0'] + 4"`), `audio`, `script` (cara), `tag`, `modo`, `efecto`, `vol` |
| `borrar_props` | `props`: propiedades de la escena a borrar |
| `python` | `codigo` corto |

**Reglas para los scripts:**
- Cada paso debe poder **repetirse** sin acumular. Por ejemplo, que borre sus propias tiras o claves antes de ponerlas, como hacen los de la parte 10.
- **La cámara la maneja solo el usuario:** ningún paso la anima, la mueve ni le borra claves.
- Al repetirse, un paso **no debe borrar lo que no anima él**: focos, océano, música… Ver `YA_LIMPIA` en `jerry_arrastra_alfred_parte10.py`.
- Los rayos que buscan el suelo no deben caer justo en la arista entre bloques, porque a veces la atraviesan. Desplázalos unos milímetros, como hace `piso_xy`.

## Chequeos (sección `chequeos` de la cadena)
- **saltos:** un hueso, la raíz o un objeto vigilado se mueve en 1 frame mucho más que en sus vecinos. Por ejemplo, Jerry que salta.
- **giros:** un hueso da una vuelta brusca, como una voltereta de ángulos.
- **relevos:** un objeto se oculta y otro de nombre parecido aparece. Por ejemplo, la flecha en vuelo pasa a ser la flecha clavada. Deben estar en el mismo sitio.
- **pegados:** objetos que deben ir en el cuerpo de un personaje, como las flechas clavadas.
- **penetracion:** mallas de dos personajes que se atraviesan fuera de los tramos `permitido`.
- **suelo:** vértices de un personaje metidos en el suelo o en las paredes.
- **distancias:** contactos que deben llegar (`max_m`) o separaciones mínimas (`min_m`) en frames dados. Por ejemplo, el sombrero en cada golpe.
- **audio:** archivos que faltan, tiras duplicadas, voces del mismo personaje encimadas y tiras fuera del rango.

## Para una parte nueva
Copia `cadenas/plantilla.json` como `cadenas/base_parte_11.json` y escribe los pasos. Los audios y caras van en `entradas/base_parte_11/`.
