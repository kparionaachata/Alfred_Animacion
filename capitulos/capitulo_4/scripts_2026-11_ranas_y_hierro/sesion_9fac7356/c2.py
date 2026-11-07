import bpy, sys, importlib, json
sys.path.insert(0, r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\cerdo_1\refinar")
gs = importlib.import_module("cerdo_1_animation_studio.generate_slots_cerdo_1")
kp=json.load(open(r"C:\Users\user\Desktop\recorrido.json"))["key_points"]
result={"segs":[(s["type"],[(c["coordinates"]["x"],c["coordinates"]["y"],c["coordinates"]["z"]) for c in s["points"]]) for s in gs.group_segments(kp)]}
