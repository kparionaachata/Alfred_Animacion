import bpy, time
sc=bpy.context.scene
ts=[]
for f in (100,101,102,500,501,900,901):
    t=time.perf_counter(); sc.frame_set(f); ts.append((f,round(time.perf_counter()-t,3)))
dl=None
for k in ("dlss","dlss_render","dlss_settings"):
    if hasattr(sc,k): dl=k
props={}
for p in dir(sc):
    if "dlss" in p.lower(): props[p]=str(getattr(sc,p))
result={"frame_set_s":ts,"props":props,"cycles_dlss":{p:str(getattr(sc.cycles,p)) for p in dir(sc.cycles) if "dlss" in p.lower() or "denois" in p.lower() or "upscal" in p.lower()}}
