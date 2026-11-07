import bpy, re
logs={}
for n in ("chicken_1","chicken_2","chicken_3"):
    o=bpy.data.objects[n]; L=[]
    for t in o.animation_data.nla_tracks:
        m=re.match(r"Slot_(\d+)", t.name)
        if not m or not t.strips: continue
        s=t.strips[0]; an=s.action.name.lower()
        tipo=next((k for k in ("saltar_bajar","saltar_subir","picotear","aletear","caminar","parada","saltar") if k in an), "?")
        if tipo=="parada": tipo="mirar"
        L.append((int(m.group(1)), tipo, int(s.frame_start), int(s.frame_end)))
    L.sort(); logs[n]=L
bpy.app.driver_namespace["_pollos_alfred_logs"]=logs
result={n:[x for x in L if x[2]>=850][:6] for n,L in logs.items()}
