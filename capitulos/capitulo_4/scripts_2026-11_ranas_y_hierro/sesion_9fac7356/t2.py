import bpy, time
sc=bpy.context.scene
sc.frame_set(1)
out=[]
for f in list(range(2,12))+list(range(800,810)):
    t=time.perf_counter(); sc.frame_set(f); out.append(round(time.perf_counter()-t,3))
print("TIEMPOS", out, "upscale", sc.cycles.preview_denoising_upscale_quality, "objs", len(bpy.data.objects), "acciones", len(bpy.data.actions))
