import bpy
s=bpy.context.scene.sequence_editor.strips_all["VozSync_alfred_tapado_en_el_hoyo"]
v0=s.volume; s.volume=v0*2
result={"antes":v0,"ahora":s.volume}
