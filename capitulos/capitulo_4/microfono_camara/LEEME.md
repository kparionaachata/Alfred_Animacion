# Micrófono de cámara (distancia y paneo)

La **cámara de la escena es el micrófono**. Cada sonido de una entidad (personaje, mob…) se escucha según dónde esté esa entidad respecto a la cámara, frame a frame, siguiendo la ruta animada de la cámara. El add-on solo **lee** la cámara: nunca la mueve ni le pone claves.

| Efecto | Qué hace |
|---|---|
| Distancia | Ley del inverso de la distancia: a la distancia de referencia o menos, volumen normal; cada vez que la distancia se duplica, **-6 dB**; nunca baja del volumen mínimo. |
| Paneo | Suena a la izquierda o a la derecha según dónde esté la entidad respecto a la cámara (pone el sonido en mono para que el paneo actúe). |

## Uso
**Instalar:** Preferencias > Complementos > Instalar desde disco… > `microfono_camara.zip`. También se carga solo desde la cadena de la parte 11.

Panel **Micrófono** en la barra lateral (N) del editor de video y del visor 3D:
1. **Analizar ruta de la cámara**:
   - dice si la cámara se mueve;
   - muestra a qué distancia queda cada entidad y cuántos dB pierde;
   - dibuja la ruta de la cámara (`ruta_camara_microfono`, no se renderiza).

   **Hazlo antes de colocar sonidos:** así sabes dónde estará el micrófono.
2. **Aplicar micrófono**: pone volumen + paneo en todas las tiras de sonido con dueño. Repetible, sin acumular. Se combina con el ducking y con cualquier clave de volumen anterior, porque las multiplica.
3. **Quitar micrófono**: deja todo exactamente como estaba (comprobado).

**Dueño de cada tira:** se deduce del nombre (`SND_p11_cerdo_oink` → `cerdo_1`; `VozJerry…` → `jerry`; `…alfred…` → `alfred`; `pollo/chicken` → `chicken_1`; `creeper` → `creeper_1`). Para otro caso, selecciona las tiras y pulsa **Dueño = objeto activo**. Las tiras sin dueño (música, narrador) no se tocan.

El sonido sale de la **cabeza** de la entidad (el hueso Head/face/neck/scull de su armadura).

## Orden en el flujo
1. Animación.
2. Sonidos y voces.
3. Ducking.
4. **Micrófono**: siempre al final, y otra vez si se vuelven a colocar sonidos.

En la cadena de la parte 11 ya es el último paso.

> El efecto Doppler se quitó a pedido del usuario (2026-10-14): los sonidos usan su audio original; ya no hay `cache_doppler/`.
