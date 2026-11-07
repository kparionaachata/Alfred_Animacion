import bpy
p=bpy.data.objects["alfred"]
r={}
for t in p.animation_data.nla_tracks:
    if t.name in ("Salir_root","Slot_006_root","Rodar_root"):
        s=t.strips[0]; a=s.action
        fz=[c for l in a.layers for st in l.strips for cb in st.channelbags for c in cb.fcurves if c.data_path=="location" and c.array_index==2]
        ks=[(round(k.co.x),round(k.co.y,2)) for k in fz[0].keyframe_points] if fz else None
        r[t.name]=dict(action=a.name, users=a.users, nkeys=len(ks) if ks else 0, keys_600_820=[k for k in ks if 595<=k[0]<=820][::3] if ks else None)
result=r
