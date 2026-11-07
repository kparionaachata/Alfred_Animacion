import bpy
ng=bpy.data.node_groups["Pasto_aplastado"]; N=ng.nodes; L=ng.links
sep=next(n for n in N if n.bl_idname=="ShaderNodeSeparateXYZ"); cmb=next(n for n in N if n.bl_idname=="ShaderNodeCombineXYZ")
# las mallas de pasto estan rotadas +90 en X: la vertical del mundo es la Y local
for l in list(L):
    if l.from_node==sep and l.from_socket.name=="Z":
        to=l.to_socket; L.remove(l); L.new(sep.outputs["Y"], to)
    if l.to_node==cmb and l.to_socket.name=="Z":
        fr=l.from_socket; L.remove(l); L.new(fr, cmb.inputs["Y"])
result={"links":[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in L if l.from_node in (sep,) or l.to_node in (cmb,)]}
