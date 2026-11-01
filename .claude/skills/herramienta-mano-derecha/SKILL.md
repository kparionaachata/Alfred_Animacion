---
name: herramienta-mano-derecha
description: Posicion fija (ubicacion, rotacion y escala) de CUALQUIER herramienta o arma que Alfred lleve en la MANO DERECHA (hacha, pico, espada, antorcha, etc.) en Blender, mas las reglas para que NUNCA quede invertida (cabeza hacia abajo) ni afecte a otras animaciones. Usar SIEMPRE que Alfred sostenga, saque, use o lleve un objeto en la mano derecha.
---

# Herramienta o arma en la mano derecha de Alfred

Valores fijados por el usuario (captura del `stone_axe` bien colocado en la mano, 30 oct). Aplican a cualquier herramienta o arma en la derecha.

| Campo | Valor (espacio local del hueso) |
|---|---|
| Constraint | `Child Of` llamado `Mano`, target `Armature`, subtarget `Rightelbow_alfred`, influencia 1.0, matriz inversa LIMPIA (identidad), espacios WORLD/WORLD |
| Location | X 0.21937, Y 0.32673, Z -0.001575 m |
| Rotation (XYZ Euler) | X 7.9831, Y 17.876, Z -56.916 grados |
| Scale | 0.82, 0.82, 0.82 |

```python
import math
obj = bpy.data.objects['stone_axe']           # o la herramienta/arma que sea
obj.rotation_mode = 'XYZ'
obj.constraints['Mano'].influence = 1.0       # Child Of a Rightelbow_alfred
obj.location = (0.21937, 0.32673, -0.001575)
obj.rotation_euler = [math.radians(d) for d in (7.9831, 17.876, -56.916)]
obj.scale = (0.82, 0.82, 0.82)
```

En el proyecto: constante `HERR_MANO_DER` en `capitulos/capitulo_4/bonobos_madera_alfred.py`. Punto del sprite que cae en la mano: `Lfix^-1 @ (0.04, 0.35, 0)` en espacio del hueso (la malla del antebrazo acaba en y=0.37; la cola del hueso esta 0.33 mas alla, NO usarla como mano).

## Reglas (aprendidas con errores; cumplirlas SIEMPRE)

1. **Solo cuando la tiene en la mano.** Los valores aplican mientras Alfred sostiene o lleva la herramienta. NO tocar otras animaciones ni otros objetos. Los hachazos (talar/picar) son otra animacion: ahi la herramienta sigue el movimiento del clip (pico del clip, mango hacia Alfred, cabeza hacia el bloque) con el punto de la mano en el mango; no aplanarlos a los valores fijos.
2. **Nunca invertida.** La herramienta no puede verse con la cabeza hacia abajo ni con la cabeza hacia Alfred y el mango hacia el objetivo. Comprobar en cada frame que la tiene: direccion mango->cabeza en mundo (`(M@cabeza)-(M@mango)`; hacha de piedra: mango (-0.34,-0.41,0), cabeza (0.17,0.2,0) en coords del sprite) y su componente Z. Con los valores fijos, si el brazo esta levantado (antebrazo hacia arriba) la cabeza puede quedar horizontal o hacia abajo (Z < 0.1): en esos frames girar la herramienta SOBRE el punto de la mano (sin soltarla) hasta que la cabeza apunte hacia arriba (Z ~0.6), con peso suave (smoothstep entre Z=0.1 y Z=-0.2), y llevarlo a claves locales (sigue el Child Of, influencia 1.0). En los frames con Z >= 0.1 quedan los valores fijos intactos.
3. **No regenerar toda la animacion para cambiar valores.** Cambiar valores = editar las claves del objeto en la escena viva (rotation/location/scale e influencia). `armar()` o regenerar guiones enteros solo si el usuario lo pide. Ejecutar solo lo ordenado.
4. **Al soltarla o caer:** congelar la transformacion de mundo en el frame anterior, influencia 0 y caida con la skill `inercia-accion-reaccion`. Si la orientacion en la mano fue corregida (regla 2), arrancar la caida desde esa orientacion y fundir la diferencia en ~10 frames (rotacion sobre el punto de la mano, no interpolar la traslacion por separado) para que no haya salto.
5. Escala distinta si el modelo es otro: mantener ubicacion y rotacion y avisar antes de cambiarla.
6. Si con la pose fija la cabeza no llega al objetivo (p. ej. ~0.35 m antes del tronco), no tocar los valores: acercar a Alfred segun `sistema-recorrido` (puntos a 1 bloque) o avisar al usuario.

## Verificacion (antes de dar por terminado)

- [ ] Child Of en `Rightelbow_alfred`, influencia 1.0 mientras la lleva, inversa limpia.
- [ ] En los frames "en la mano": Location/Rotation/Scale = tabla, salvo los frames corregidos por la regla 2.
- [ ] Componente Z de mango->cabeza >= 0.1 en todos los frames en la mano; ningun frame invertido (revisar caminar, amenaza, gestos con el brazo levantado, antes y despues de talar).
- [ ] Hachazos intactos (cabeza hacia el bloque en el golpe); otras animaciones sin cambios.
- [ ] Sin salto de pose al empezar/terminar un hachazo ni al empezar la caida (comparar frames contiguos).
- [ ] Hoja de contacto en reposo, caminando, con el brazo levantado y al golpear.
