import bpy
result={n:([round(x,3) for x in bpy.data.objects[n].location],[round(x,3) for x in bpy.data.objects[n].rotation_euler],[round(x,3) for x in bpy.data.objects[n].scale], bpy.data.objects[n].parent.name if bpy.data.objects[n].parent else None) for n in ("Short_Grass","Tall_Grass","Fern")}
