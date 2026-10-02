# Historial resumido del tablero (2026-09-29/30) — NO usar como instrucciones

Version anterior del tablero, resumida al reescribirlo (las instrucciones vigentes estan en `TABLERO_TAREAS_IA.md`).

## E1 original (superado)
- Parametros pedidos a Codex: zombie_3 LENTO, retraso 85, aterrizaje (-123.0,-120.4); zombie_4 BRAZO_ABAJO, retraso 120, (-108.5,-120.6); zombie_5 ESPASMOS, retraso 155, (-118.6,-121.0). Aceptacion original: >=4.5 m a Alfred en la caida, >=3 m entre aterrizajes, caidas separadas >=35 frames.
- Formula de deformacion temporal: `tau(f)=f-S*ss((f-330)/160)*(1-ss((f-740)/110))`; peso de marcha `w_walk`: 1 hasta 440, rampa a 0 en 476, 0 hasta 660, rampa a 1 en 690.
- Entrada de Codex #1: JSON y `derivar_zombie.py` con validacion `E1_VALIDACION_OK`; aterrizajes ajustados: z3 (-123.55,-120.40), z5 (-117.70,-121.00).
- Revision del maestro #1: REHACER. zombie_2..5 estaban superpuestos (distancia 0.0 m) en f1-300 y f860. Se exigio velocidad de aproximacion distinta (0.94/0.90/0.86), carriles laterales (+0.7/-0.7/+1.2 desplazado), finales escalonados a <=0.085 m/f y distancias >=1.2-1.3 m.
- Reentrega de Codex: cumplia (minimos 1.30/1.24/1.32 m). Luego el maestro cambio el diseno por peticiones del usuario (ver tablero vigente).

## Cambios pedidos por el usuario despues (todos hechos por el maestro)
caminata NORMAL para 3-5; no atravesar arboles; caminar de frente (orientar al avanzar); no caer lejos; caer desde el borde sin atravesar tierra; ojos rojos siempre (tambien en vista solida); zombie_3 no debe caer sobre Jerry.
