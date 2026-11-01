---
name: bloque-roto-drop
description: Cuando en una animacion se rompe un bloque (madera/tronco, piedra, tierra, mena, hojas, cualquier material) picando, talando o excavando, el bloque se vuelve un item pequeno que cae, gira y flota como en Minecraft, y luego es absorbido por el personaje que lo rompio. Aplicar SIEMPRE que Alfred (u otro personaje) rompa un bloque con pico, hacha, pala o a mano.
---

# Bloque roto -> item que gira y flota -> absorbido por quien lo rompio (como en Minecraft)

Se aplica SIEMPRE, con cualquier personaje y cualquier material. Combinar con `inercia-accion-reaccion` (caida con gravedad real), `recursos-animacion` (usar el bloque de `bloques_dinamicos`, no un cubo inventado: `bloque_de_roble`, `bloque_de_stone`, `mena_de_hierro`...) y la skill del personaje.

## Secuencia completa

1. **Rotura** (frame f_r = golpe final, con las grietas 0-9 ya completas): ocultar el bloque original (keys constantes de `hide_viewport` + `hide_render`) y soltar las astillas/particulas del material (en `arboles_talables.py` ya existe `_astillas`). Sonido de rotura segun el material (`sonidos`).
2. **Item**: copia del mismo bloque (misma malla y material) con **escala 0.25 en todos los ejes**, en el centro del bloque roto. Visible desde f_r. Un item por bloque roto (arbol de 4 troncos = 4 items).
3. **Salto de aparicion**: empujon pequeno al azar: velocidad horizontal ~+-0.03 m/frame en X e Y y salto vertical de ~0.2 m (vz inicial = sqrt(2*g_f*0.2) = 0.083 m/frame, `g_f = 9.81/24^2 = 0.017031 m/f^2`). Cae, se posa sin rebote apreciable y se frena por friccion. Nunca atraviesa el suelo.
4. **Flotar y girar** (desde que se posa hasta que lo absorben):
   - Giro en Z continuo de **1 rad/s = 2.39 grados/frame** (una vuelta cada ~151 f), LINEAR, sin frenarse; fase inicial al azar por item.
   - Flotacion: `z = z_suelo + 0.1 + 0.1*sin(2*pi*t/75 + fase)` m (entre 0 y 0.2 m sobre el suelo, periodo ~3.14 s = ~75 f), keys cada 6-8 f con interpolacion suave.
5. **Absorcion por el personaje que lo rompio**:
   - Solo lo absorbe quien lo rompio (o a quien se asigne el item); no se espera a que el item toque al personaje.
   - Retardo minimo desde la rotura: 10 ticks = **12 frames** (el item aun no se puede recoger).
   - Se dispara cuando el personaje esta a **< 1 m** (horizontal) del item y el item ya esta posado y flotando; si el personaje sigue talando/picando y no se acerca, el item sigue girando hasta que se acerque.
   - Animacion de absorcion: en **~5 frames** el item viaja en linea recta (ease-in) hasta el pecho del personaje (hueso del torso: `Spine1_alfred` en Alfred; punto medio del cuerpo en otros), mientras su escala baja de 0.25 a 0; al llegar se oculta (keys `hide_viewport` + `hide_render`). Sin rotar bruscamente: conserva su giro durante el vuelo.
   - Sonido de recoger item (`sonidos`, sonido de "pop" de Minecraft) en el frame en que llega al personaje; los items recogidos en el mismo frame suenan una sola vez.
   - Si el personaje tiene inventario/objeto en mano en la escena, la absorcion no cambia su pose ni agrega animacion al personaje.

## Reglas

- Nunca dejar el bloque grande y el item a la vez; nunca dejar el item quieto sin girar; nunca dejarlo flotando para siempre si el personaje que lo rompio esta en la escena: debe terminar absorbido.
- La escala 0.25 es del item, no del personaje ni de su empty.
- Verificar con hoja de contacto: bloque oculto en f_r, item visible desde f_r a 0.25, aterriza sin atravesar el suelo, gira 2.39 grados/frame y sube/baja 0-0.2 m, empieza a volar al personaje solo cuando hay < 1 m y han pasado >= 12 f, llega a su pecho, desaparece y suena una vez.
