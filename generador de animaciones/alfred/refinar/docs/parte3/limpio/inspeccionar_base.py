import bpy, time
t0=time.time(); sc=bpy.context.scene
print("CARGADO", bpy.data.filepath, "frames", sc.frame_start, sc.frame_end, "t=%.0f s"%(time.time()-t0))
for n in ("stone_shovel","stone_axe","wooden_axe","wooden_pickaxe","tierra_item","tablon_item","lid_cesped_cavar","pozo_tierra","refugio_bloque_03","mesa_de_crafteo_1","a.001","Camera.001","Foco_Conversacion","Camera_FondoMarino","Armature","alfred","Dog_001_rig","jerry","zombie_1"):
    o=bpy.data.objects.get(n); print(" objeto",n,"-> existe" if o else "-> NO existe", ("anim:%s"%(o.animation_data.action.name if o.animation_data and o.animation_data.action else None)) if o else "")
A=[o for o in bpy.data.objects if o.type=='ARMATURE' and "Hips_alfred" in o.pose.bones]
for a in A: print(" rig alfred:",a.name,"accion",a.animation_data.action.name if a.animation_data and a.animation_data.action else None,"pistas NLA",[t.name for t in a.animation_data.nla_tracks] if a.animation_data else None)
ed=sc.sequence_editor; print(" tiras VSE:",len(ed.strips_all) if ed else 0)
print(" colecciones:",[c.name for c in bpy.data.collections][:30])
print(" acciones:",len(bpy.data.actions),[a.name for a in bpy.data.actions if 'Armature' in a.name or 'alfred' in a.name][:8])
