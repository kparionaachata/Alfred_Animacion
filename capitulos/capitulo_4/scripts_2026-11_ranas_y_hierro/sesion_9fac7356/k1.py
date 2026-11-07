import bpy
sc=bpy.context.scene
anim=[]
for o in bpy.data.objects:
    ad=o.animation_data
    if ad and (ad.action or ad.nla_tracks): anim.append((o.name, ad.action.name if ad.action else None, len(ad.nla_tracks)))
sk=[k.user.name for k in bpy.data.shape_keys if k.animation_data and k.animation_data.action]
ed=sc.sequence_editor
result={"frame_actual":sc.frame_current,"rango":(sc.frame_start,sc.frame_end),"objetos_animados":len(anim),"ejemplos":anim[:25],"shape_keys_animadas":sk[:10],"sonidos":len([s for s in ed.strips_all]) if ed else 0,"markers":[(m.name,m.frame) for m in sc.timeline_markers]}
