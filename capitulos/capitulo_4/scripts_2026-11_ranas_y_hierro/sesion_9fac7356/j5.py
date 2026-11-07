import sys, importlib, json, re
sys.path.insert(0, r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\jerry\refinar")
gs = importlib.import_module("jerry_animation_studio.generate_slots_jerry")
kp = json.load(open(r"C:\Users\user\Desktop\recorrido_1.json"))["key_points"]
seg=[s for s in gs.group_segments(kp) if s["type"]=="caminar"][0]
r={}
for st in ("NORMAL","RAPIDO","CORRER"):
    res=gs.generate_caminar(70,1000,[dict(c) for c in seg["points"]],"x",180,(0,0,180),walk_style=st)
    code=res[0] if isinstance(res,tuple) else res
    m=re.search(r"END_FRAME\s*=\s*(\d+)",code); r[st]=(int(m.group(1))-1000+1 if m else None, res[1] if isinstance(res,tuple) else None)
result=r
