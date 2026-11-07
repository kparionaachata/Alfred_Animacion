import bpy
sc=bpy.context.scene; c=sc.cycles; r=sc.render
d={}
for p in ("preview_samples","samples","use_preview_denoising","preview_denoiser","preview_denoising_upscale_quality","preview_denoising_input_passes","use_preview_adaptive_sampling","preview_adaptive_threshold","max_bounces","diffuse_bounces","glossy_bounces","transmission_bounces","volume_bounces","transparent_max_bounces","use_fast_gi","caustics_reflective","caustics_refractive","blur_glossy","texture_limit","use_light_tree","volume_step_rate","volume_preview_step_rate"):
    d[p]=getattr(c,p,None)
d["simplify"]=(r.use_simplify, r.simplify_subdivision, getattr(c,"texture_limit",None))
d["res"]=(r.resolution_x,r.resolution_y,r.resolution_percentage)
d["dlss"]={k:str(getattr(sc.dlss_render,k)) for k in dir(sc.dlss_render) if not k.startswith(("_","bl_","rna"))} if hasattr(sc,"dlss_render") else None
d["vis_objs"]=sum(1 for o in sc.objects if not o.hide_render)
d["particles"]=sum(len([m for m in o.modifiers if m.type=="PARTICLE_SYSTEM"]) for o in sc.objects if not o.hide_render)
d["volumes"]=[o.name for o in sc.objects if o.type=="VOLUME" and not o.hide_render][:5]
w=sc.world
d["world"]=(w.name if w else None)
print("CFG",d)
