"""Jerry se queda en el punto (-6.5,-5.5) de su recorrido (f238) en vez de llegar junto a Alfred y la mesa:
la caminata B termina en f238 (accion 184), espera ahi mirando a Alfred craftear (239-366) y recorre el ultimo
tramo original (accion 184-204) en 367-387 para empalmar con el Slot_016 de f388."""
import bpy

sc = bpy.context.scene
j = bpy.data.objects["jerry"]; rig = bpy.data.objects["Dog_001_rig"]
jt, rt = j.animation_data.nla_tracks, rig.animation_data.nla_tracks
CORTE, ESPERA0, C0 = 184, 239, 367          # accion donde se corta, inicio de la espera, inicio del ultimo tramo

# quitar la version anterior (giro ADD junto a la mesa)
for obj, n in ((j, "Jerry_mira_crafteo_root"), (rig, "Jerry_mira_crafteo_arm")):
    for t in list(obj.animation_data.nla_tracks):
        if t.name == n: obj.animation_data.nla_tracks.remove(t)
    a = n.lower()
    if a in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[a])
ed = sc.sequence_editor
for s in [s for s in ed.strips_all if s.name.startswith("SND_paso_jerry_mira_")]: ed.strips.remove(s)

for tr in (jt["Slot_014_root"], rt["Slot_014_arm"]):
    b = next(s for s in tr.strips if s.name.endswith("_B"))
    for s in [s for s in tr.strips if s.name.endswith("_C")]: tr.strips.remove(s)
    b.action_frame_end = CORTE                       # 164-238
    c = tr.strips.new(b.name[:-2] + "_C", C0, b.action)
    c.action_slot = b.action_slot
    c.action_frame_start = CORTE; c.action_frame_end = 204   # 367-387
    c.extrapolation = b.extrapolation = ("HOLD_FORWARD" if tr.name.endswith("_root") else "NOTHING")

pa = rt["Slot_015_parada_arm"].strips[0]
pa.frame_start_ui = ESPERA0
pa.action_frame_end = 205 + (C0 - 1 - ESPERA0)       # 239-366
pr = jt["Slot_015_parada_root"].strips[0]
pr.mute = True                                       # la raiz de la espera la pone jerry_mira_crafteo.py

# pasos: los del ultimo tramo (antes 239-258) pasan a 367-387
mov = [s for s in ed.strips_all if s.name.startswith("SND_paso_jerry_") and ESPERA0 <= s.frame_final_start <= 258]
for s in sorted(mov, key=lambda s: -s.frame_start): s.frame_start += (C0 - CORTE) - 54   # accion+54 -> accion+183
result = {"pasos_movidos": len(mov), "B": [(s.name, s.frame_start, s.frame_end) for s in jt["Slot_014_root"].strips],
          "parada_arm": (pa.frame_start, pa.frame_end)}
