import bpy
sc=bpy.context.scene; ed=sc.sequence_editor
V=r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\voces_alfred"
for n in ("VozSync_alfred_sale_del_hoyo","VozSync_alfred_frase6_tapada","VozSync_alfred_frase6_libre"):
    if n in ed.strips_all: ed.strips.remove(ed.strips_all[n])
INI, ROMPE = 640, 706           # la tapa se rompe en 706: desde ahi suena normal
a=ed.strips.new_sound("VozSync_alfred_frase6_tapada", V+r"\alfred_frase_6_tapado.wav", 26, INI)
b=ed.strips.new_sound("VozSync_alfred_frase6_libre", V+r"\alfred_frase_6.mp3", 27, INI)
fin=b.frame_final_end
a.frame_final_end=ROMPE; b.frame_final_start=ROMPE
tap=ed.strips_all.get("VozSync_alfred_tapado_en_el_hoyo")
a.volume=tap.volume if tap else 1.0; b.volume=1.0
for s in (a,b): s["duck_todos"]=False
exec(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\ducking_voces.py", encoding="utf-8").read(), {"__name__": "x", "DUCK": 0.56})
result={"tapada":(a.frame_final_start,a.frame_final_end,a.volume),"libre":(b.frame_final_start,b.frame_final_end,b.volume),"fin_audio":fin}
