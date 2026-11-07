import bpy, math
from mathutils import Vector
sc=bpy.context.scene; al=bpy.data.objects["Armature"]; pb=al.pose.bones; p=bpy.data.objects["stone_shovel"]
deg=lambda e:[round(math.degrees(x),3) for x in e]
# valores actuales (sin re-evaluar el frame)
r={"frame":sc.frame_current,"modo":bpy.context.mode,"activo":bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
   "huesos_sel":[b.name for b in pb if getattr(b,"select",False)]}
r["bones"]={b.name:{"rot":deg(b.rotation_euler),"loc":[round(x,4) for x in b.location]} for b in pb if b.name.endswith("_alfred")}
r["pala"]={"loc":[round(x,5) for x in p.location],"rot":deg(p.rotation_euler),"scale":[round(x,3) for x in p.scale],"cons":[(c.name,c.type,getattr(c,'subtarget',''),round(c.influence,3)) for c in p.constraints],"parent":p.parent.name if p.parent else None,"parent_bone":p.parent_bone}
# diferencia con lo animado en este frame
act=al.animation_data.action
dif={}
if act:
    cb=act.layers[0].strips[0].channelbag(al.animation_data.action_slot)
    for b in pb:
        for i in range(3):
            fc=cb.fcurves.find('pose.bones["%s"].rotation_euler'%b.name,index=i)
            if fc:
                v=fc.evaluate(sc.frame_current)
                if abs(v-b.rotation_euler[i])>1e-3: dif.setdefault(b.name,[]).append((i,round(math.degrees(v),2),round(math.degrees(b.rotation_euler[i]),2)))
r["cambiado_respecto_animacion"]=dif
pa=p.animation_data.action if p.animation_data else None
r["pala_animada"]=bool(pa)
r["mano_izq_tail"]=[round(x,3) for x in al.matrix_world@pb["Leftelbow_alfred"].tail]
r["mano_der_tail"]=[round(x,3) for x in al.matrix_world@pb["Rightelbow_alfred"].tail]
r["pala_mundo"]=[round(x,3) for x in p.matrix_world.translation]
result=r
