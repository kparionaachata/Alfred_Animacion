---
name: inercia-accion-reaccion
description: Aplicar inercia, accion-reaccion y gravedad a TODA animacion de Blender que se genere en este proyecto (Alfred, Jerry, mobs, objetos lanzados, caidas, golpes, empujes). Usar siempre que se cree o modifique una animacion con objetos que se mueven, se lanzan, golpean o caen, o con personajes que reciben/dan impactos.
---

# Fisica en las animaciones (inercia, accion-reaccion, gravedad)

Toda animacion generada debe cumplir estos principios. Antes de dar una animacion por terminada, revisar la lista de verificacion del final.

## Principios

1. **Gravedad real**: g = 9.81 m/s2 = `9.81/24**2` m/frame2 a 24 fps. Un arco parabolico de T frames entre dos puntos tiene altura `g_f * T**2 / 8` (no inventar alturas). Las caidas ACELERAN (z = z0 - h*t^2), nunca a velocidad constante.
2. **Inercia**: un objeto en movimiento conserva su velocidad hasta que algo lo cambia. Tras un choque o una soltada sale con la velocidad que llevaba (reflejada o no), no se detiene en seco ni cae recto. Un objeto que falla sigue su trayectoria y cae mas alla. Los giros (velocidad angular) tambien se conservan y se amortiguan.
3. **Accion y reaccion**: si algo golpea a un personaje, el personaje reacciona EN EL MISMO FRAME del impacto (no 3 frames despues), con direccion igual a la del objeto e intensidad proporcional a masa x velocidad. El objeto tambien recibe reaccion (rebota con una restitucion segun material). Si el personaje lanza algo, el cuerpo hace contrapeso: carga atras, suelta, sigue adelante.
4. **Rebote elastico del cuerpo**: la reaccion no es una pose estatica. Perfil: golpe instantaneo (~45%), pico (100%) 2 frames despues, retorno con sobrepaso en sentido contrario (~-18%), asentamiento (~6%) y vuelta a la pose base.
5. **Cantidad de movimiento**: manzana/bayas ligeras = reaccion suave; palo/panal pesados = fuerte; si el golpe viene de arriba, las rodillas ceden (`hips_dz`) y la cabeza baja; el cuerpo se desliza un poco en la direccion del impacto y vuelve.
6. **Preparacion y seguimiento**: antes de un movimiento brusco hay anticipacion (carga contraria); despues, follow-through y asentamiento. Nada arranca ni para instantaneamente salvo en el impacto.
7. **Contacto**: al tocar el suelo los objetos rebotan perdiendo energia (restitucion y rozamiento, maximo 3 rebotes) y se quedan quietos con la rotacion amortiguada. Las cosas que cuelgan o se sostienen (hacha, serpiente) siguen el movimiento del hueso con retardo, no rigidas.

## Como se aplica en este proyecto

- **Objetos lanzados**: `capitulos/capitulo_4/bonobos_madera_fisica.py` -> `vuelo(obj, f0, p0, f1, p1, suelo=..., centro=..., choca=True/False)`; tabla `FISICA` (masa, restitucion contra Alfred y contra el suelo) por nombre de objeto; `velocidad_llegada()`. `suelo=None` = el objeto se queda pegado (serpiente).
- **Reaccion de Alfred**: `bonobos_madera_alfred.py` -> `reaccion(fi, v, masa, yaw, pos, peak, fin, dur, brazo=None)` con `golpe(lanzador, pos, z, f_imp, T)` y `velocidad_golpe()`; poses base `D_LISTO`, `D_CAB`, `D_HOM`, `D_BRAZO`, perfil `_PERFIL`.
- **Caidas**: simular con `G_F` por frame (ver la caida del hacha en `bonobos_madera_main.py`), con un rebote.
- Para otros personajes/escenas reutilizar la misma logica: velocidad de llegada -> reflexion con restitucion -> simulacion por frame -> keys por frame con interpolacion lineal.

## Lista de verificacion (revisar antes de entregar)

- [ ] Todo arco de vuelo usa gravedad real (no alturas arbitrarias); las caidas aceleran.
- [ ] Cada impacto sobre un personaje tiene reaccion en el frame exacto, en la direccion del objeto, proporcional a masa x velocidad, con rebote elastico y vuelta a la pose.
- [ ] Tras un choque el objeto sale con la inercia reflejada (restitucion segun material) y rebota/rueda hasta pararse.
- [ ] Lo que falla sigue de largo con su velocidad.
- [ ] Lanzar/golpear incluye anticipacion y seguimiento; ningun movimiento brusco arranca de golpe.
- [ ] Los frames-evento (impactos, soltadas) no se desplazan si hay otras animaciones sincronizadas con ellos (p.ej. los bonobos): la reaccion se ajusta DENTRO de la ventana existente.
- [ ] Verificar con fotogramas del instante del impacto y los siguientes (hoja de contacto), no solo la pose final.
- [ ] **Personajes que giran en el aire o ruedan tras un golpe (rata, pollo, etc.)**: la rotacion X/Y del empty raiz debe terminar en multiplo de 360 grados (cuerpo de pie) y la base de la malla apoyada en el suelo (`minZ_malla - Z_root` ~ 0). Fallo real del 30 oct: rata con rot final (884, 379, 632) y pollo (867, 371, 619) -> inclinados y hundidos 0.5 m. Medir al final del tramo, no solo durante el vuelo.
