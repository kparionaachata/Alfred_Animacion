---
name: lanzador-mira-objetivo
description: Cuando un personaje lanza un objeto hacia otro personaje (piedra, bola, hacha, carbon, flecha, comida, lo que sea), el que lanza debe MIRAR a su objetivo - mover la cabeza y dirigir la mirada hacia el objetivo antes, durante y despues del lanzamiento. Aplicar SIEMPRE que un personaje lance o arroje algo a otro personaje.
---

# El que lanza mira a su objetivo (cabeza + mirada)

Todo lanzamiento de un personaje hacia otro lleva SIEMPRE esta mirada, con cualquier personaje y objeto. Combinar con `inercia-accion-reaccion` (trayectoria y reaccion del que recibe), la skill del personaje que lanza y `recursos-animacion`.

## Que se anima

1. **Cabeza**: girar cuello y cabeza hacia el objetivo (yaw y pitch), no solo el cuerpo.
2. **Mirada**: si el personaje tiene ojos/pupilas (Alfred `ojo_izquierdo_alfred`/`ojo_derecho_alfred`, pollo `pupila_*_chicken_1`), desplazarlos hacia el objetivo; si no tiene, la cabeza basta.
3. **Cuerpo**: si el objetivo queda a mas de ~70 grados del frente, girar tambien el torso/raiz (`Spine*`, rot Z del empty) hacia el objetivo; la cabeza completa el resto. Cuello +-70 grados de yaw y +-35 de pitch como maximo.

## Calculo (siempre desde posiciones reales, nunca a ojo)

- Origen = posicion mundial de la cabeza del que lanza; destino = pecho/cabeza del objetivo (su posicion mundial EN ESE FRAME; si se mueve, recalcular por frame).
- `dx, dy, dz = destino - origen`; `yaw_mundo = atan2(dx, dy)` (o el eje frontal que use el rig), `pitch = atan2(dz, hypot(dx, dy))`.
- `yaw_local = yaw_mundo - rot_Z_del_personaje` (normalizado a -pi..pi). Los ejes locales de los huesos de cabeza dependen del rig: probar el signo con una pose de prueba y verificar que la cabeza queda apuntando al objetivo (hoja de contacto) antes de dar la animacion por buena.

## Tiempos

- **Antes**: empezar a girar la cabeza ~8-12 frames antes de armar el brazo; el objetivo ya esta mirado cuando arranca la anticipacion.
- **Durante**: cabeza bloqueada en el objetivo (siguiendolo si se mueve) desde la anticipacion hasta ~6 frames despues de soltar el objeto.
- **Despues**: seguir el objeto/el objetivo ~10-20 frames (ve el impacto) y volver suave a la pose anterior; sin movimiento brusco (interpolacion suave; ELASTIC_IN_OUT solo si el lanzamiento es expresivo).
- El giro de cabeza nunca cambia el frame de soltar el objeto ni los frames-evento ya sincronizados con otras animaciones.

## Reglas

- Siempre se mira al objetivo; nunca lanzar con la cabeza mirando a otro lado o al frente fijo.
- Se anima sobre huesos de cabeza/cuello del rig (Alfred: `Neck_alfred`, `face_alfred`; pollo: `Neck_M`, `Head_M`); no inventar huesos. En personajes bloqueados (p. ej. los monos del video de la tala) no tocar su animacion.
- Verificar con hoja de contacto: mira al objetivo en anticipacion, soltado e impacto; el giro de cabeza no atraviesa el cuerpo ni el hombro; vuelve a la pose sin saltos.
