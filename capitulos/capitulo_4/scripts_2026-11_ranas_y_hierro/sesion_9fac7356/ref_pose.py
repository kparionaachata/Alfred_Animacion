import math
REF = {  # pose que dejo el usuario (frame 103), grados / metros
 "Hips_alfred": ((0.733, -29.486, -0.026), (-0.0524, -0.0013, -0.1657)),
 "Spine_alfred": ((10.29, -0.125, 1.13), None), "Spine1_alfred": ((2.238, 0.11, -1.179), None), "Spine2_alfred": ((1.301, -0.033, 0.377), None),
 "Neck_alfred": ((10.89, -0.753, 0.701), None), "face_alfred": ((6.26, -3.575, 1.135), None),
 "RightUpArm_alfred": ((37.222, 25.327, -18.703), None), "Rightelbow_alfred": ((32.018, -15.995, -87.715), None),
 "LeftUpArm_alfred": ((77.373, -27.749, 17.38), None), "Leftelbow_alfred": ((39.634, 5.771, 98.758), None),
 "RightUpLeg_alfred": ((-0.902, -3.192, -23.082), None), "Rightknee_alfred": ((1.426, 15.009, 3.947), None),
 "LeftUpLeg_alfred": ((2.163, -0.031, 3.668), None), "Leftknee_alfred": ((-8.397, 1.162, -2.912), None)}
ROOT_RZ = 2.835
PALA_LOC = (0.3021, 0.48578, -0.02626); PALA_ROT = (-7.142, -21.913, 1.384)
def poner_ref(pb, root):
    for n, (r, l) in REF.items():
        b = pb[n]; b.rotation_mode = "XYZ"; b.rotation_euler = [math.radians(x) for x in r]
        if l is not None: b.location = l
    root.rotation_euler.z = ROOT_RZ
