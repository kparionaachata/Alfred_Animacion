
import bpy, math, random, time
from mathutils import Vector
ns={}
exec(open(P+r"\lanzar.py",encoding='utf-8').read(),ns)
mono,suf,apuntar=ns['mono'],ns['suf'],ns['apuntar']
SC=bpy.context.scene

def surf(rig):
    bpy.context.view_layer.update()
    ms=[o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
    dg=bpy.context.evaluated_depsgraph_get(); inv=rig.matrix_world.inverted(); pts=[]
    for m in ms:
        e=m.evaluated_get(dg); me=e.to_mesh(); mw=e.matrix_world
        pts+=[inv@(mw@v.co) for v in me.vertices]; e.to_mesh_clear()
    return pts

def targets(pts, S, rig):
    pb=rig.pose.bones
    hh=pb['head'+S]; hc=(hh.head+hh.tail)/2
    top=max(p.z for p in pts if abs(p.x)<0.25 and abs(p.y-hc.y)<0.3)
    ty=[p.y for p in pts if abs(p.x)<0.25 and p.z>top-0.05 and abs(p.y-hc.y)<0.3]
    ytop=sum(ty)/len(ty)
    def fr(zc,hw=0.2,tol=0.05):
        c=[p.y for p in pts if abs(p.x)<hw and abs(p.z-zc)<tol]
        return (max(c),min(c)) if c else (0.2,-0.4)
    ch=pb['cube_r1'+S]; zc=(ch.head.z+ch.tail.z)/2
    bd=pb['body'+S]; zb=bd.head.z*0.5+bd.tail.z*0.5
    return dict(
        head=lambda sx: Vector((sx*0.13,ytop,top-0.03)),
        ear=lambda sx: Vector((sx*0.22,hc.y-0.02,hc.z+0.02)),
        chest=lambda sx: Vector((sx*0.10,fr(zc)[0]+0.01,zc)),
        belly=lambda sx: Vector((sx*0.10,fr(zb)[0]+0.01,zb)),
        butt=lambda sx: Vector((sx*0.13,fr(bd.head.z-0.06,0.3)[1]-0.01,bd.head.z-0.06)),
        )

def ik(J0,T,L1,L2,sx):
    d=T-J0; dist=d.length
    dist=min(max(dist,abs(L1-L2)+1e-3),L1+L2-1e-3)
    u=d.normalized()
    a=(dist*dist+L1*L1-L2*L2)/(2*dist); h=math.sqrt(max(L1*L1-a*a,1e-6))
    pole=Vector((sx*0.7,-0.5,-0.4)); pole=(pole-u*pole.dot(u)).normalized()
    E=J0+u*a+pole*h
    Tn=J0+u*dist
    return (E-J0).normalized(),(Tn-E).normalized()

def set_arm(rig,S,side,d1,d2):
    apuntar(rig,side+'arm'+S,d1); apuntar(rig,side+'forearm'+S,d2); apuntar(rig,side+'hand'+S,d2)

def key_arm(rig,S,side,f):
    for h in ('arm','forearm','hand'):
        pb=rig.pose.bones[side+h+S]; pb.keyframe_insert('rotation_euler',frame=f,group=pb.name)

def scratch(rig,S,side,T,base,t0,reps,amp_dir,tg):
    sx=1 if side=='left' else -1
    pb=rig.pose.bones
    J0=pb[side+'arm'+S].head.copy()
    L1=(pb[side+'arm'+S].tail-pb[side+'arm'+S].head).length
    L2=(pb[side+'forearm'+S].tail-pb[side+'forearm'+S].head).length+0.12
    def put(f,Tpos):
        if Tpos is None:
            for h in ('arm','forearm','hand'):
                pb[side+h+S].rotation_euler=base[side+h]
            bpy.context.view_layer.update()
        else:
            d1,d2=ik(J0,Tpos,L1,L2,sx); set_arm(rig,S,side,d1,d2)
        key_arm(rig,S,side,f)
    put(t0,None)
    put(t0+7,T)
    f=t0+7
    for k in range(reps*2):
        f+=2
        put(f,T+amp_dir*(0.05 if k%2==0 else -0.05))
    f+=2; put(f,T)
    f+=5; put(f,None)
    return f
