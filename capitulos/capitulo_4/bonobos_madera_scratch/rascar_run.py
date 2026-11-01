
import bpy, math, random, time
from mathutils import Vector
R={'P':P}
exec(open(P+r"\rascar.py",encoding='utf-8').read(),R)
SC=bpy.context.scene
mono,suf=R['mono'],R['suf']
fcs=R['ns']['fcs']

def mirar(rig,S,base_head,t0,yaw_deg,up):
    pb=rig.pose.bones['head'+S]
    hd=(pb.tail-pb.head).normalized()
    Rz=Vector(hd); 
    import mathutils
    m=mathutils.Matrix.Rotation(math.radians(yaw_deg),3,'Z')
    d2=(m@hd); d2.z+=up; d2.normalize()
    def key(f): pb.keyframe_insert('rotation_euler',frame=f,group=pb.name)
    pb.rotation_euler=base_head; bpy.context.view_layer.update(); key(t0)
    R['apuntar'](rig,'head'+S,d2); key(t0+8); key(t0+8+rng_hold[0])
    pb.rotation_euler=base_head; bpy.context.view_layer.update(); key(t0+16+rng_hold[0])
    return t0+16+rng_hold[0]

def run(i,intervals,seed):
    global rng_hold
    rng=random.Random(seed+i)
    raiz,rig=mono(i); S=suf(rig)
    total=0
    for a,b in intervals:
        if b-a<46: continue
        a2,b2=a+6,b-4
        SC.frame_set(a2); bpy.context.view_layer.update()
        base={}
        for side in ('left','right'):
            for h in ('arm','forearm','hand'):
                base[side+h]=tuple(rig.pose.bones[side+h+S].rotation_euler)
        base_head=tuple(rig.pose.bones['head'+S].rotation_euler)
        # limpiar claves de brazos y cabeza en el intervalo
        ac=rig.animation_data.action
        for c in fcs(ac):
            if 'pose.bones' in c.data_path:
                n=c.data_path.split('"')[1]
                if any(n==s+h+S for s in ('left','right') for h in ('arm','forearm','hand')) or n=='head'+S:
                    if c.data_path.endswith('rotation_euler'):
                        for k in reversed(list(c.keyframe_points)):
                            if a2-0.5<=k.co[0]<=b2+0.5: c.keyframe_points.remove(k)
        pts=R['surf'](rig); tg=R['targets'](pts,S,rig)
        # claves base en los extremos (mantener pose)
        for f in (a2,b2):
            for side in ('left','right'):
                for h in ('arm','forearm','hand'):
                    pbn=rig.pose.bones[side+h+S]; pbn.rotation_euler=base[side+h]; pbn.keyframe_insert('rotation_euler',frame=f,group=pbn.name)
            hb=rig.pose.bones['head'+S]; hb.rotation_euler=base_head; hb.keyframe_insert('rotation_euler',frame=f,group=hb.name)
        f=a2+rng.randint(4,14)
        menu=['head','head','ear','chest','chest','belly','butt','butt','look']
        while f+44<b2:
            kind=rng.choice(menu)
            if kind=='look':
                rng_hold=[rng.randint(6,14)]
                f=mirar(rig,S,base_head,f,rng.choice((-1,1))*rng.uniform(25,45),rng.uniform(0.0,0.25))
            else:
                side=rng.choice(('left','right')); sx=1 if side=='left' else -1
                T=tg[kind](sx)
                amp=Vector((0,0.6,0.8)) if kind in('head','ear') else Vector((0,0,1))
                f=R['scratch'](rig,S,side,T,base,f,rng.randint(3,6),amp,tg)
            total+=1
            f+=rng.randint(8,26)
    return total
