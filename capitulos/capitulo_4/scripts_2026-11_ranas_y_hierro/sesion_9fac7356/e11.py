import bpy, math
from mathutils import Vector
sc=bpy.context.scene; r=sc.render
FRAMES=[680,850]
DIR=r"C:\Users\user\AppData\Local\Temp\claude\d0772e74e53e6fa2\9fac7356-8ced-4d1a-a12c-3247350383c7\scratchpad"
al=bpy.data.objects["Armature"]
old=(r.engine,r.resolution_x,r.resolution_y,r.resolution_percentage,r.filepath,sc.camera, r.image_settings.file_format if hasattr(r.image_settings,'file_format') else None)
cd=bpy.data.cameras.new("_tmpcam_e"); cam=bpy.data.objects.new("_tmpcam_e",cd); sc.collection.objects.link(cam); sc.camera=cam
out=[]
try:
    r.engine="BLENDER_EEVEE" if "BLENDER_EEVEE" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else "BLENDER_EEVEE_NEXT"
    try: sc.eevee.taa_render_samples=4
    except Exception: pass
    r.resolution_x=r.resolution_y=320; r.resolution_percentage=100
    for f in FRAMES:
        sc.frame_set(f)
        F=al.matrix_world@al.pose.bones["face_alfred"].matrix; h=F.translation; fz=F.to_3x3().col[2].normalized()
        cam.location=h+fz*0.9; cam.rotation_euler=(h-cam.location).to_track_quat('-Z','Y').to_euler(); cd.lens=60
        bpy.ops.render.render()
        p=DIR+"/eevee_%d.png"%f; bpy.data.images["Render Result"].save_render(p); out.append(p)
finally:
    r.engine,r.resolution_x,r.resolution_y,r.resolution_percentage,r.filepath,sc.camera=old[:6]
    bpy.data.objects.remove(cam); bpy.data.cameras.remove(cd)
result={"out":out,"engine_restaurado":r.engine}
