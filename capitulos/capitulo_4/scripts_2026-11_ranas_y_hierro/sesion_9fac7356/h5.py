import bpy
sc=bpy.context.scene; ed=sc.sequence_editor
n="VozSync_alfred_sale_del_hoyo"
if n in ed.strips_all: ed.strips.remove(ed.strips_all[n])
s=ed.strips.new_sound(n, r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\voces_alfred\alfred_frase_6.mp3", 26, 625)
s["duck_todos"]=False
exec(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\ducking_voces.py", encoding="utf-8").read(), {"__name__": "x", "DUCK": 0.56})
result={"strip":(s.frame_final_start,s.frame_final_end,s.channel)}
