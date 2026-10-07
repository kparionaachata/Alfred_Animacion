# Acciones de Alfred (guiones reutilizables)

Cada accion es una carpeta con un `accion.json` (la receta, esquema `alfred_accion_v1`) y, si hace falta, su `LEEME`. La receta describe LO QUE PASA con parametros con nombre (objeto, mano, destino, tiempos,
cuerpo, sonidos); el ejecutor (un script de Blender) la convierte en animacion. Nada depende de que la animacion este guardada dentro de un `.blend`.

## Como se usa (humano o IA)
1. Copiar la carpeta de la accion y editar `accion.json` (los campos con "(*)" en su `nota` son los que se cambian).
2. En Blender, con la escena abierta y el add-on Alfred Animation Studio:
   `ns = {"__name__": "accion", "ACCION_JSON": r"<ruta>\accion.json"}; exec(open(r"<ruta>\colocar_objeto.py", encoding="utf-8").read(), ns)`
3. Revisar la escena. El ejecutor no guarda el `.blend`.

## Acciones
| Carpeta | Ejecutor | Que hace | Parametros que se cambian |
|---|---|---|---|
| `colocar_objeto_exterior/` | `colocar_objeto.py` | un personaje saca un objeto de su espalda con una mano y lo coloca en un sitio, inclinandose para llegar | `objeto` (antorcha, mesa de crafteo, bloque...), `destino`, `cuerpo`, `lado`, `tiempos`, `sonidos` |

## Convenciones del esquema
- Tiempos: frames absolutos de la escena (24 fps). En `sonidos` y eventos se pueden usar nombres de `tiempos` con desplazamiento (`"suelta+1"`).
- Coordenadas: metros de mundo de Blender (Z arriba). El suelo del refugio esta en z = 14.
- Huesos de Alfred: `Right|Left` + `UpArm_alfred` / `elbow_alfred`, `Spine_alfred`, `Spine1_alfred`, `Spine2_alfred`. Rotaciones Euler XYZ en grados.
- Objetos: o son una copia de otro objeto de la escena con sus hijos (`copia_jerarquia_de`) o se importan de un `.blend` (`blend` + `fuente_objeto`, ruta relativa a la raiz del proyecto).
- Sonidos: `archivo` es relativo a `sonidos/sounds` (biblioteca de Minecraft del proyecto).
- `estado`: "sin aprobar" hasta que el autor lo apruebe.

## Para crear una accion nueva
Describir primero la accion en palabras en `descripcion`, luego sacar los numeros de la escena (posiciones, poses de huesos, frames) y ponerlos en `parametros` / `tiempos`. Si la accion ya existe con otro objeto
o lugar, copiarla y cambiar solo esos parametros. Probar con el ejecutor y comparar con lo que se queria.

## Portables (lo que carga el flujo) y como se generan
El formato que se carga y concatena en el flujo Alfred Animation Studio, en cualquier otro .blend, es el PORTABLE (`alfred_portable_clip_v1`): `configuraciones/configuracion_portable_<accion>_f<a>_<b>.json` + una pose por frame en
`poses/<accion>_f<a>_<b>/` + los objetos en `objetos_portables/<accion>_portable.blend`. Es el formato principal; la receta (`accion.json`) es para que una IA entienda y adapte la accion.
`exportar_portable.py` genera el portable de un rango de la escena abierta (SPEC con nombre, f0, f1, objetos, anclas, sonidos...). Verificado: regenera las 77 poses de la antorcha identicas (0 diferencias) a las del portable existente.
Cada accion nueva se entrega como portable + receta.
