import bpy
ng=bpy.data.node_groups["Pasto_aplastado"]; N=ng.nodes; L=ng.links
sep=next(n for n in N if n.bl_idname=="ShaderNodeSeparateXYZ"); cmb=next(n for n in N if n.bl_idname=="ShaderNodeCombineXYZ")
# destino de la salida de separar (la resta alto = pos - z_base) y origen de la entrada de combinar (dz)
dest=[l.to_socket for l in L if l.from_node==sep]
orig=[l.from_socket for l in L if l.to_node==cmb]
for l in [l for l in L if l.from_node==sep or l.to_node==cmb]: L.remove(l)
for s in dest: L.new(sep.outputs["Y"], s)
for s in orig: L.new(s, cmb.inputs["Y"])
result={"sep_out":[l.from_socket.name for l in L if l.from_node==sep],"cmb_in":[l.to_socket.name for l in L if l.to_node==cmb]}
