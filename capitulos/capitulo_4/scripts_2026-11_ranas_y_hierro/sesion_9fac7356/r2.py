import bpy
im=bpy.context.scene.render.image_settings
result={"media_type":getattr(im,"media_type",None),"formato":im.file_format,"opciones":[e.identifier for e in im.bl_rna.properties["media_type"].enum_items] if hasattr(im,"media_type") else None}
