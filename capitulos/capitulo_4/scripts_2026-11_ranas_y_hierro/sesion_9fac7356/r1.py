import bpy
sc=bpy.context.scene
result={"archivo":bpy.data.filepath,"sucio":bpy.data.is_dirty,"inicio":sc.frame_start,"fin":sc.frame_end,"escena":sc.name}
