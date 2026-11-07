"""Reconstruye el fusil Pattern 1851 Minie (el arma de los Highlanders en Balaclava) con sus medidas reales.

blender -b --factory-startup --python reconstruir_p1851.py -- <carpeta_salida>
Salida: <carpeta>/pattern_1851_minie.blend, vista.png, detalle_llave.png, detalle_boca.png y piezas/<pieza>/<pieza>.blend + vista.png

Medidas (Wikipedia, rifleman.org.uk, College Hill Arsenal):
  largo total 55" (1,397 m), canon 39" (0,991 m), calibre .702" (17,8 mm), 4 estrias.
  Llave de percusion lateral con martillo de cuello de cisne, chimenea (nipple) sobre el rastrillo del canon.
  Canon sujeto a la caja de nogal por 3 pasadores (keys) con escudetes, no por abrazaderas.
  Guarniciones de laton: cantonera, guardamonte, puntera de la caja, 3 abrazaderas de baqueta y la contraplatina.
  Alza de escalera hasta 900 yardas; punto de mira de bloque y hoja, que es tambien el tope de la bayoneta.
  Baqueta de acero con cabeza de seta. Una anilla portafusil (guardamano). Bayoneta de cubo P1853 calada.
Ejes como el euro_musket01 del juego (para que use el mismo hueso Weapon1 y las mismas animaciones):
  +X hacia la boca, -Y hacia arriba, -Z del lado de la llave (lado derecho: fusil para diestros). El disparador queda donde estaba el del juego.
"""
import math, os, sys
import bpy, bmesh
import numpy as np
from mathutils import Euler, Vector, Matrix

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SALIDA = os.path.abspath(ARGS[0]) if ARGS else os.path.join(os.getcwd(), "pattern_1851_minie")
NOMBRE = "pattern_1851_minie"
for o in list(bpy.data.objects):bpy.data.objects.remove(o)
sc = bpy.context.scene

# ---------------------------------------------------------------- medidas (metros). Modelo: X boca, Z arriba, +Y lado de la llave
ZA = .0235                        # eje del canon (el del juego)
XB = .03                          # cara de la recamara
L_CANON, L_TOTAL = .991, 1.397
XM = XB + L_CANON                 # boca
XC = XM - L_TOTAL                 # talon de la culata
XN = XM - .075                    # fin de la caja: deja sitio al cubo de la bayoneta
R_ALMA = .0178 / 2
def r_canon(x):                   # radio exterior: refuerzo de la recamara y luego conico hasta la boca
    t = np.clip((x - XB) / L_CANON, 0, 1)
    return .0145 - .004 * t + .0008 * np.clip(1 - (x - XB) / .07, 0, 1)
# secciones de la caja: x, techo, suelo (respecto al eje), media anchura
CAJA = [(XC, -.030, -.150, .0215), (-.30, -.024, -.128, .0225), (-.22, -.017, -.100, .022), (-.16, -.012, -.074, .020),
        (-.12, -.010, -.058, .019), (-.08, -.006, -.054, .0205), (-.03, .004, -.056, .0245), (.06, .006, -.058, .0245),
        (.12, .004, -.050, .0225), (.20, .003, -.044, .021), (.45, .002, -.038, .0195), (.70, .002, -.034, .0185),
        (XN, .002, -.031, .017)]   # madera robusta como el fusil real: alrededor de la llave mide ~2.2 veces la platina; el guardamano envuelve la baqueta
CX = np.array([c[0] for c in CAJA])
def caja(x):return [np.interp(x, CX, [c[i] for c in CAJA]) for i in (1, 2, 3)]
Z_BAQ, R_BAQ = -.022, .0042       # baqueta bajo el canon (respecto al eje)

piezas = {}                       # nombre -> (malla bmesh, clase)
def nueva(nombre, clase):
    bm = bmesh.new(); piezas[nombre] = (bm, clase); return bm

# ---------------------------------------------------------------- utilidades de malla
def anillo(bm, x, cy, cz, ry, rz, n=24, e=2.0, giro=0.):
    vs = []
    for i in range(n):
        t = 2 * math.pi * i / n + giro; c, s = math.cos(t), math.sin(t)
        vs.append(bm.verts.new((x, cy + ry * math.copysign(abs(c) ** (2 / e), c), cz + rz * math.copysign(abs(s) ** (2 / e), s))))
    return vs
def puente(bm, a, b):
    n = len(a)
    for i in range(n):bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
def tapa(bm, a, invertir=False):bm.faces.new(a[::-1] if invertir else a)
def tubo(bm, xs, rs, cy=0., cz=0., n=24, cerrar=(True, True)):
    rings = [anillo(bm, x, cy, cz, r, r, n) for x, r in zip(xs, rs)]
    for a, b in zip(rings[:-1], rings[1:]):puente(bm, a, b)
    if cerrar[0]:tapa(bm, rings[0], True)
    if cerrar[1]:tapa(bm, rings[-1])
    return rings
def caja_simple(bm, lo, hi):
    r = bmesh.ops.create_cube(bm, size=1.)
    for v in r["verts"]:v.co = Vector([lo[i] + (v.co[i] + .5) * (hi[i] - lo[i]) for i in range(3)])
def extruir_perfil(bm, pts, y0, y1, plano="XZ"):
    """Poligono 2D (x,z) extruido en Y de y0 a y1 (o (x,y) en Z si plano XY)."""
    if plano == "XZ":a = [bm.verts.new((x, y0, z)) for x, z in pts]; b = [bm.verts.new((x, y1, z)) for x, z in pts]
    else:a = [bm.verts.new((x, y, y0)) for x, y in pts]; b = [bm.verts.new((x, y, y1)) for x, y in pts]
    puente(bm, a, b); tapa(bm, a, True); tapa(bm, b)
def tuberia(bm, pts, r, n=12, plano_y=None, ry=1., rz=1.):
    """Barra de seccion eliptica a lo largo de una polilinea 3D."""
    P = [Vector(p) for p in pts]; rings = []
    for i, p in enumerate(P):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        u = t.cross(Vector((0, 1, 0))) if abs(t.y) < .9 else t.cross(Vector((1, 0, 0)))
        u.normalize(); w = t.cross(u).normalized()
        rings.append([bm.verts.new(p + (u * math.cos(2 * math.pi * k / n) * rz + w * math.sin(2 * math.pi * k / n) * ry) * r) for k in range(n)])
    for a, b in zip(rings[:-1], rings[1:]):puente(bm, a, b)
    tapa(bm, rings[0], True); tapa(bm, rings[-1])
def tira(bm, xs, zf, wf, grosor):
    """Lamina continua que sigue la caja: zf(x) altura de la cara, wf(x) media anchura; grosor hacia fuera (+) o dentro (-)."""
    filas = []
    for x in xs:
        z, w = zf(x), wf(x)
        filas.append([bm.verts.new((x, -w, z)), bm.verts.new((x, w, z)), bm.verts.new((x, w, z + grosor)), bm.verts.new((x, -w, z + grosor))])
    for a_, b_ in zip(filas[:-1], filas[1:]):puente(bm, a_, b_)
    tapa(bm, filas[0], True); tapa(bm, filas[-1])
def curva(p0, p1, p2, p3, n=16):
    return [tuple((1 - t) ** 3 * np.array(p0) + 3 * (1 - t) ** 2 * t * np.array(p1) + 3 * (1 - t) * t * t * np.array(p2) + t ** 3 * np.array(p3)) for t in np.linspace(0, 1, n)]

# ---------------------------------------------------------------- caja de nogal
bm = nueva("caja_nogal", "madera")
xs = np.unique(np.r_[np.linspace(XC, XN, 90), CX])
rings = []
for x in xs:
    top, bot, hw = caja(x)
    rings.append(anillo(bm, x, 0., ZA + (top + bot) / 2, hw, (top - bot) / 2, 28, 2.7))
for a, b in zip(rings[:-1], rings[1:]):puente(bm, a, b)
tapa(bm, rings[0], True); tapa(bm, rings[-1])

# ---------------------------------------------------------------- canon con alma, rastrillo y chimenea
bm = nueva("canon", "hierro")
xs = np.linspace(XB, XM, 60); fuera = [anillo(bm, x, 0., ZA, r_canon(x), r_canon(x), 40) for x in xs]
for a, b in zip(fuera[:-1], fuera[1:]):puente(bm, a, b)
tapa(bm, fuera[0], True)
xi = [XM, XM - .12]; dentro = [anillo(bm, x, 0., ZA, R_ALMA, R_ALMA, 40) for x in xi]
puente(bm, fuera[-1], dentro[0])                    # corona de la boca
puente(bm, dentro[0], dentro[1]); tapa(bm, dentro[1], True)
bm = nueva("espiga_recamara", "hierro")             # cola del tapon de recamara sobre la garganta
top_w = lambda x: ZA + caja(x)[0]
tira(bm, np.linspace(XB - .1, XB, 24), lambda x: top_w(x) - .0008, lambda x: .0055 * min(1, (x - (XB - .1)) / .03 + .2), .0026)

# ---------------------------------------------------------------- llave de percusion (segun fotos de P1842/P1851 reales)
# platina larga de puntas redondeadas con filete grabado, embutida en un rebaje plano de la caja; martillo plano de
# cuello de cisne: cubo redondo con tornillo ranurado, cuello alto, espuela curvada hacia atras y nariz larga que
# baja a una cabeza en copa sobre la chimenea; la chimenea va en un rastrillo redondeado que sale del canon.
YP = .0212                                          # cara del rebaje de la llave
XN_, YN_ = XB + .016, .030                          # chimenea: x y lado
# martillo y disparador tomados del ejemplo del usuario (rifle.blend, Feldstutzer suizo de 1851, misma epoca y llave):
# se escalan al largo de este fusil, se espejan (alli la llave esta en -Y) y la cabeza se pone sobre nuestra chimenea
EJEMPLO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "biblioteca_personajes", "armas", "pattern_1851_minie", "rifle.blend")
with bpy.data.libraries.load(EJEMPLO, link=False) as (src_, dst_):dst_.objects = ["Cube.001", "swiss model 1851 feldstutzer rifle", "Cylinder"]
EJ = {o.name: o for o in dst_.objects}
_P = lambda o: [o.matrix_basis @ v.co for v in o.data.vertices]       # sin escena, matrix_world no esta calculada
_todo = _P(EJ["swiss model 1851 feldstutzer rifle"]) + _P(EJ["Cylinder"])
S_EJ = L_TOTAL / (max(p.x for p in _todo) - min(p.x for p in _todo))          # escala: mismo largo total
N0 = Vector((-7.371, -.0975, 10.119))                                          # chimenea del ejemplo (centro del martillo en Y)
GRUESO_EJ = 1.5                                                                # su martillo es delgado (5 mm): 8 mm como el real
def del_ejemplo(R, grueso=1.):
    d = R - N0;return Vector((XN_ + d.x * S_EJ, YN_ - d.y * S_EJ * grueso, ZA + .006 + d.z * S_EJ))
_mart = [del_ejemplo(p, GRUESO_EJ) for p in _P(EJ["Cube.001"])]
_cubo = [p for p, r in zip(_mart, _P(EJ["Cube.001"])) if r.z < 10.0]                # parte baja redonda = cubo del eje
_bx, _bz = [p.x for p in _cubo], [p.z for p in _cubo]
TX, TZ = (min(_bx) + max(_bx)) / 2, (min(_bz) + max(_bz)) / 2       # eje del martillo (tumbler) = centro del cubo redondo
R_CUBO = min(max(_bx) - min(_bx), max(_bz) - min(_bz)) / 2          # radio del cubo: el tornillo queda dentro, sin asomar
# martillo abatido: se gira sobre su eje hasta que la copa de la nariz cae justo encima de la chimenea y del fulminante
_xm = max(p.x for p in _mart); _nar = [p for p in _mart if p.x > _xm - .012]; _zn = min(p.z for p in _nar)
_fondo = [p for p in _nar if p.z < _zn + .0012]
_NX, _NZ = sum(p.x for p in _fondo) / len(_fondo), sum(p.z for p in _fondo) / len(_fondo)     # fondo de la nariz
def _gira(p, a):
    dx, dz = p.x - TX, p.z - TZ; return Vector((TX + dx * math.cos(a) - dz * math.sin(a), p.y, TZ + dx * math.sin(a) + dz * math.cos(a)))
Z_COPA = ZA + .011                                                 # fondo de la nariz abatida, sobre la chimenea
A_MART = min((a for a in np.linspace(-.6, .6, 4801) if abs(_gira(Vector((_NX, 0, _NZ)), a).z - Z_COPA) < 5e-5), key=abs)
_mart = [_gira(p, A_MART) for p in _mart]
XCH = _gira(Vector((_NX, 0, _NZ)), A_MART).x                      # la chimenea va justo debajo de la copa (su eje del martillo no llega mas adelante)
def perfil_platina(x0, x1, zc, hh, margen=0., n=40):
    """Contorno de la platina: bordes casi rectos y puntas redondeadas (la de delante algo mas aguda)."""
    pts = []
    for t in np.linspace(0, 1, n):                  # borde de arriba, de atras a delante
        e = (1 - abs(2 * t - 1) ** 6) ** (.5 if t < .5 else .7)
        pts.append((x0 - margen + (x1 - x0 + 2 * margen) * t, zc + (hh + margen) * e))
    for t in np.linspace(1, 0, n)[1:-1]:            # borde de abajo, algo abombado
        e = (1 - abs(2 * t - 1) ** 5) ** (.5 if t < .5 else .7)
        pts.append((x0 - margen + (x1 - x0 + 2 * margen) * t, zc - (hh * 1.08 + margen) * e))
    return pts
PX0, PX1, PZC, PHH = TX - .051, TX + .119, ZA - .021, .0165
bm = nueva("rebaje_llave", "madera")                # el plano de madera que rodea la platina
extruir_perfil(bm, [(x, z) for x, z in perfil_platina(PX0, PX1, PZC, PHH, .006)], .012, YP)
bm = nueva("platina", "hierro")
pts = perfil_platina(PX0, PX1, PZC, PHH)
a = [bm.verts.new((x, YP - .0004, z)) for x, z in pts]; b = [bm.verts.new((x, YP + .0038, z)) for x, z in pts]
puente(bm, a, b); tapa(bm, a, True); cara = bm.faces.new(b)
r = bmesh.ops.inset_region(bm, faces=[cara], thickness=.0016, depth=0.)                 # filete grabado del borde
r = bmesh.ops.inset_region(bm, faces=[cara], thickness=.0005, depth=-.00035)
r = bmesh.ops.inset_region(bm, faces=[cara], thickness=.0005, depth=.00035)
# rastrillo (bolster) como el de la foto: bloque de caras PLANAS, cara de fuera lisa y vertical, frente en forma de D
# (lobulo redondo abajo delante), lomo plano donde asienta la chimenea y una rampa concava hacia la recamara
bm = nueva("rastrillo", "hierro")
ZT = .0045                                                            # lomo plano (respecto al eje), base de la chimenea
ZB = -.0055                                                           # asienta sobre el borde de arriba de la platina
_lob = [(.007 + .005 * math.cos(t), -.0005 + .005 * math.sin(t)) for t in np.linspace(-math.pi / 2, math.pi / 2, 24)]
_ramp = [tuple((1 - t) ** 2 * np.array((-.004, ZT)) + 2 * (1 - t) * t * np.array((-.0045, -.003)) + t * t * np.array((-.012, ZB))) for t in np.linspace(0, 1, 14)]
_pr = [(-.012, ZB)] + _lob + _ramp[:-1]
_pr = [p for k, p in enumerate(_pr) if k == 0 or abs(p[0] - _pr[k - 1][0]) + abs(p[1] - _pr[k - 1][1]) > 1e-5]
extruir_perfil(bm, [(XCH + x, ZA + z) for x, z in _pr], .008, YN_ + .0052)
def _perfil_giro(bm, capas_zr, n, giro=0.):                     # solido de revolucion vertical sobre la chimenea
    capas = [[bm.verts.new((XCH + r_ * math.cos(2 * math.pi * k / n + giro), YN_ + r_ * math.sin(2 * math.pi * k / n + giro), z0)) for k in range(n)] for z0, r_ in capas_zr]
    for a_, b_ in zip(capas[:-1], capas[1:]):puente(bm, a_, b_)
    return capas
# chimenea: base de seis caras para la llave, cuello con collarin y cono hasta dentro del fulminante (como en la foto)
bm = nueva("chimenea", "hierro"); Z_TOPE = Z_COPA - .0009
c = _perfil_giro(bm, ((ZA + ZT - .0008, .0036), (ZA + ZT + .0014, .0036)), 6, math.pi / 6); tapa(bm, c[0], True); tapa(bm, c[-1])
c = _perfil_giro(bm, ((ZA + ZT + .0012, .0022), (ZA + ZT + .0016, .0022), (ZA + ZT + .0018, .0027), (ZA + ZT + .0024, .0027), (ZA + ZT + .0026, .0022),
                      (Z_TOPE - .0006, .0017), (Z_TOPE, .0015)), 16)
tapa(bm, c[0], True); tapa(bm, c[-1])
bm = nueva("fulminante", "cobre")                   # capsula de cobre con faldon, metida en la copa del martillo
c = _perfil_giro(bm, ((Z_COPA - .0046, .0024), (Z_COPA - .0046, .0027), (Z_COPA - .0004, .0026), (Z_COPA - .0003, .0021),
                      (Z_COPA - .0008, .0016), (Z_TOPE + .0001, .0015)), 16)
tapa(bm, c[0], True); tapa(bm, c[-1])
bm = nueva("copa_martillo", "hierro")               # copa hueca de la nariz que envuelve el fulminante al golpear
c = _perfil_giro(bm, ((Z_COPA + .0015, .0040), (Z_COPA - .0028, .0043), (Z_COPA - .0032, .0040), (Z_COPA - .0032, .0030),
                      (Z_COPA - .0002, .0029)), 20)
tapa(bm, c[0], True); tapa(bm, c[-1])
bm = nueva("martillo", "hierro")                    # el del ejemplo, en su sitio
bm.from_mesh(EJ["Cube.001"].data)
for v, p in zip(bm.verts, _mart):v.co = p
bmesh.ops.reverse_faces(bm, faces=bm.faces)          # el espejo invierte las caras
bm = nueva("cubo_martillo", "hierro")               # disco redondo del pie del martillo alrededor del tornillo (como en el original)
R_D = R_CUBO * 1.55; n = 40
c = [[bm.verts.new((TX + r_ * math.cos(2 * math.pi * k / n), y, TZ + r_ * math.sin(2 * math.pi * k / n))) for k in range(n)] for y, r_ in ((YP + .001, R_D), (YP + .0118, R_D), (YP + .0125, R_D * .96))]
for a_, b_ in zip(c[:-1], c[1:]):puente(bm, a_, b_)
tapa(bm, c[0], True); tapa(bm, c[-1])
tuberia(bm, [(TX + R_D * .8 * math.cos(t), YP + .0125, TZ + R_D * .8 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 49)], .00035, 8)   # aro grabado
bm = nueva("tornillo_martillo", "hierro")           # tornillo ranurado del eje, por fuera del martillo
n = 20; c = [[bm.verts.new((TX + r_ * math.cos(2 * math.pi * k / n), y, TZ + r_ * math.sin(2 * math.pi * k / n))) for k in range(n)] for y, r_ in ((YP + .0124, R_CUBO * .62), (YP + .0142, R_CUBO * .58), (YP + .0149, R_CUBO * .46))]
for a_, b_ in zip(c[:-1], c[1:]):puente(bm, a_, b_)
tapa(bm, c[0], True); tapa(bm, c[-1])
caja_simple(bm, (TX - R_CUBO * .47, YP + .0145, TZ - .0006), (TX + R_CUBO * .47, YP + .0155, TZ + .0006))    # ranura (relleno oscuro)
bm = nueva("tornillos_platina", "hierro")           # cabezas pequenas de los tornillos y pasadores
for dx, dz in ((-.04, .006), (-.039, -.006), (.03, .0), (.072, -.004), (.103, .0)):
    c = [[bm.verts.new((TX + dx + r_ * math.cos(2 * math.pi * k / 12), y, PZC + dz + r_ * math.sin(2 * math.pi * k / 12))) for k in range(12)] for y, r_ in ((YP + .0035, .0024), (YP + .0045, .0021), (YP + .005, .0012))]
    for a_, b_ in zip(c[:-1], c[1:]):puente(bm, a_, b_)
    tapa(bm, c[0], True); tapa(bm, c[-1])
bm = nueva("contraplatina", "laton")                # lado opuesto a la llave
CP = [(-.075, -.03), (-.06, -.016), (.0, -.013), (.055, -.016), (.07, -.025), (.05, -.034), (-.01, -.036), (-.06, -.035)]
extruir_perfil(bm, [(x, ZA + z) for x, z in CP], -YP - .0025, -YP + .001)

# ---------------------------------------------------------------- guardamonte, disparador y cantonera (laton)
bot_w = lambda x: ZA + caja(x)[1]
bm = nueva("guardamonte", "laton")
tira(bm, np.linspace(-.17, .13, 60), lambda x: bot_w(x) + .0008, lambda x: .0085 if -.07 < x < .04 else .0085 * (.55 + .45 * (1 - min(abs(x + .015) - .055, .1) / .1)), -.0032)
arco = curva((-.062, 0, bot_w(-.062) - .001), (-.072, 0, bot_w(-.03) - .068), (.046, 0, bot_w(.0) - .066), (.035, 0, bot_w(.035) - .001), 32)   # ovalo hondo: el gatillo queda dentro sin tocarlo
tuberia(bm, arco, .0032, 12, ry=.55, rz=1.7)
bm = nueva("disparador", "hierro")                  # hoja curva: baja, se abomba hacia atras y la punta vuelve adelante (cara del dedo concava)
xd = -.004; bd = bot_w(xd)
eje = curva((xd, 0, bd + .004), (xd - .010, 0, bd - .012), (xd - .008, 0, bd - .027), (xd + .007, 0, bd - .031), 28)
rings = []
for i, p in enumerate(eje):
    f = i / (len(eje) - 1); P = Vector(p)
    t = (Vector(eje[min(i + 1, len(eje) - 1)]) - Vector(eje[max(i - 1, 0)])).normalized()
    u = t.cross(Vector((0, 1, 0))).normalized()
    ex, ey = .0026 - .0010 * f, .0029 - .0007 * f            # grueso (en el plano) y media anchura (Y)
    rings.append([bm.verts.new(P + u * ex * math.copysign(abs(math.cos(a)) ** .6, math.cos(a)) + Vector((0, ey * math.copysign(abs(math.sin(a)) ** .6, math.sin(a)), 0))) for a in np.linspace(0, 2 * math.pi, 17)[:-1]])
for a_, b_ in zip(rings[:-1], rings[1:]):puente(bm, a_, b_)
tapa(bm, rings[0], True); tapa(bm, rings[-1])
bm = nueva("cantonera", "laton")
top, bot, hw = caja(XC)
a = anillo(bm, XC + .0005, 0., ZA + (top + bot) / 2, hw * 1.03, (top - bot) / 2 * 1.015, 28, 2.7)
b = anillo(bm, XC - .004, 0., ZA + (top + bot) / 2, hw * 1.03, (top - bot) / 2 * 1.015, 28, 2.7)
puente(bm, b, a); tapa(bm, a); tapa(bm, b, True)
tira(bm, np.linspace(XC - .002, XC + .085, 20), lambda x: ZA + caja(max(x, XC))[0] - .0008, lambda x: .008 * (1 - (x - XC) / .11), .0026)   # lengueta sobre el lomo

# ---------------------------------------------------------------- puntera, abrazaderas, baqueta y pasadores
bm = nueva("puntera", "laton")
xs = [XN - .028, XN - .002, XN + .001]
rr = []
for k, x in enumerate(xs):
    top, bot, hw = caja(min(x, XN)); f = 1.06 if k < 2 else .9
    rr.append(anillo(bm, x, 0., ZA + (top + bot) / 2, hw * f, (top - bot) / 2 * f, 28, 2.7))
puente(bm, rr[0], rr[1]); puente(bm, rr[1], rr[2]); tapa(bm, rr[0], True); tapa(bm, rr[2])
bm = nueva("abrazaderas_baqueta", "laton")
for x0, ln in ((.17, .055), (.36, .032), (.60, .032), (.84, .032)):
    tubo(bm, [x0, x0 + .004, x0 + ln - .004, x0 + ln], [.0062, .0068, .0068, .0062], cz=ZA + Z_BAQ, n=20, cerrar=(True, True))
bm = nueva("baqueta", "hierro")
tubo(bm, [-.06, XM - .03, XM - .028, XM - .02, XM - .014], [R_BAQ, R_BAQ, .0058, .0064, .0058], cz=ZA + Z_BAQ, n=16)
bm = nueva("escudetes_pasadores", "laton")
for x in (.33, .58, .80):
    for lado in (1, -1):
        top, bot, hw = caja(x)
        c = [[bm.verts.new((x + .0075 * math.cos(2 * math.pi * k / 16), lado * y, ZA - .006 + .0045 * math.sin(2 * math.pi * k / 16))) for k in range(16)] for y in (hw - .0005, hw + .0012)]
        puente(bm, c[0], c[1]); tapa(bm, c[0], lado > 0); tapa(bm, c[1], lado < 0)
bm = nueva("pasadores", "hierro")
for x in (.33, .58, .80):
    top, bot, hw = caja(x)
    caja_simple(bm, (x - .0035, -hw - .0016, ZA - .0075), (x + .0035, hw + .0016, ZA - .0045))

# ---------------------------------------------------------------- miras y anillas
bm = nueva("alza_escalera", "hierro")
xa = XB + .105; ra = float(r_canon(xa))
caja_simple(bm, (xa - .018, -.008, ZA + ra - .002), (xa + .018, .008, ZA + ra + .0035))          # base
for lado in (1, -1):caja_simple(bm, (xa - .018, lado * .0062 - .0012, ZA + ra + .0035), (xa + .006, lado * .0062 + .0012, ZA + ra + .0075))  # mejillas
caja_simple(bm, (xa - .072, -.0055, ZA + ra + .0042), (xa + .004, .0055, ZA + ra + .0062))      # hoja plegada
caja_simple(bm, (xa - .06, -.0068, ZA + ra + .0038), (xa - .05, .0068, ZA + ra + .0068))        # corredera
bm = nueva("punto_de_mira", "hierro")
xf = XM - .03; rf = float(r_canon(xf))
caja_simple(bm, (xf - .008, -.0045, ZA + rf - .002), (xf + .008, .0045, ZA + rf + .003))
extruir_perfil(bm, [(xf - .006, ZA + rf + .003), (xf + .004, ZA + rf + .003), (xf + .002, ZA + rf + .0068), (xf - .003, ZA + rf + .0068)], -.0008, .0008)
bm = nueva("anillas", "hierro")
for xc, zc in ((.60, ZA + caja(.60)[1] - .002),):                  # solo la del guardamano (la del guardamonte se quito)
    caja_simple(bm, (xc - .004, -.003, zc - .002), (xc + .004, .003, zc + .002))
    aro = [(xc + .015 * math.sin(t), 0, zc - .015 + .015 * math.cos(t)) for t in np.linspace(0, 2 * math.pi, 33)]
    tuberia(bm, aro, .0018, 8)

# ---------------------------------------------------------------- bayoneta de cubo Pattern 1853 (referencias del usuario)
# cubo de 3" con collar atras y ranura en Z (entra el punto de mira, que hace de teton), cuello que sale del frente del cubo,
# baja en codo y gira hacia delante, y hoja triangular de 17": cara plana arriba, dos caras con vaceo y arista abajo
def secciones(bm, xs, perfil):
    """Une secciones (y,z) en cada x: perfil(x) devuelve la lista de puntos de la seccion."""
    rings = [[bm.verts.new((x, y, z)) for y, z in perfil(x)] for x in xs]
    for a_, b_ in zip(rings[:-1], rings[1:]):puente(bm, a_, b_)
    tapa(bm, rings[0], True); tapa(bm, rings[-1])
bm = nueva("bayoneta", "hierro")
RB_I = float(r_canon(XM)) + .0004; RB_E = RB_I + .0021; XB0, XB1 = XM - .076, XM + .002
XS_ = np.r_[np.linspace(XB0, XB0 + .0045, 4), np.linspace(XB0 + .006, XB1, 37)]; NT = 48
A_FIN = math.radians(-55)                                             # el ultimo tramo de la ranura queda arriba (sobre el punto de mira)
def en_ranura(x, t):                                                  # ranura en Z: entra por atras, gira y sigue hacia delante
    t = (t - A_FIN + math.pi) % (2 * math.pi) - math.pi                # angulo medido desde el ultimo tramo
    a1 = math.radians(55); w = math.radians(13)
    if XB0 - 1 < x < XB0 + .026 and abs(t - a1) < w:return True       # entrada (desde el borde de atras)
    if XB0 + .020 < x < XB0 + .029 and -w < t < a1 + w:return True     # giro
    return XB0 + .020 < x < XM - .026 and abs(t) < w                   # tramo final hasta el punto de mira
radio_cubo = lambda x: RB_E + (.0012 if x < XB0 + .005 else 0)        # collar de atras
V = [[bm.verts.new((x, radio_cubo(x) * math.sin(2 * math.pi * k / NT + A_FIN), ZA + radio_cubo(x) * math.cos(2 * math.pi * k / NT + A_FIN))) for k in range(NT)] for x in XS_]
caras = []
for i_ in range(len(XS_) - 1):
    for k in range(NT):
        xm_ = (XS_[i_] + XS_[i_ + 1]) / 2; tm = 2 * math.pi * (k + .5) / NT + A_FIN
        if not en_ranura(xm_, tm):caras.append(bm.faces.new((V[i_][k], V[i_ + 1][k], V[i_ + 1][(k + 1) % NT], V[i_][(k + 1) % NT])))
bmesh.ops.solidify(bm, geom=caras, thickness=.0021)                   # pared del cubo hacia dentro
YB, ZBH = RB_E + .0165, ZA                                            # eje de la hoja, del lado de la llave
XC0 = XB1 - .007
cuello = curva((XC0, RB_E - .003, ZBH), (XC0, YB - .004, ZBH), (XC0 + .005, YB, ZBH), (XC0 + .024, YB, ZBH), 28)
rings = []                                                            # cuello grueso (seccion oval), marco fijo con Z arriba: sin giros en el codo
for i_, p_ in enumerate(cuello):
    P_ = Vector(p_); t_ = (Vector(cuello[min(i_ + 1, len(cuello) - 1)]) - Vector(cuello[max(i_ - 1, 0)])).normalized()
    u_ = t_.cross(Vector((0, 0, 1))).normalized(); r_ = .0074 - .0012 * i_ / (len(cuello) - 1)
    rings.append([bm.verts.new(P_ + u_ * r_ * math.cos(a_) + Vector((0, 0, r_ * .78 * math.sin(a_)))) for a_ in np.linspace(0, 2 * math.pi, 17)[:-1]])
for a_, b_ in zip(rings[:-1], rings[1:]):puente(bm, a_, b_)
tapa(bm, rings[0], True); tapa(bm, rings[-1])
XH0, XH1 = XC0 + .017, XC0 + .017 + .432
def hoja(x):
    t = (x - XH0) / (XH1 - XH0); w = .0112 * (1 - t) ** .75 + .0003; d = .0100 * (1 - t) ** .85 + .0003
    if t < .03:w *= 1.06                                              # hombro en la raiz
    v = .25 * min(1, (1 - t) * 3)                                     # vaceo de las caras, se pierde hacia la punta
    za, zr = ZBH + d * .35, ZBH - d * .65                             # cara plana arriba, arista abajo
    return [(YB - w, za), (YB + w, za), (YB + w * .5 * (1 - v), (za + zr) / 2 + d * v * .2), (YB, zr), (YB - w * .5 * (1 - v), (za + zr) / 2 + d * v * .2)]
secciones(bm, np.linspace(XH0, XH1, 36), hoja)

# ---------------------------------------------------------------- materiales
def material(c):
    m = bpy.data.materials.new(f"{NOMBRE}_{c}"); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links
    p = next(n for n in N if n.type == "BSDF_PRINCIPLED")
    def nodo(t, **k):
        n = N.new(t)
        for a, v in k.items():setattr(n, a, v)
        return n
    def poner(s, v):
        if isinstance(v, (int, float)):s.default_value = v
        elif isinstance(v, tuple):s.default_value = tuple(v) + ((1,) if len(v) == 3 else ())
        else:L.new(v, s)
    def mate(op, a, b=None, cl=False):
        n = nodo("ShaderNodeMath", operation=op, use_clamp=cl); poner(n.inputs[0], a)
        if b is not None:poner(n.inputs[1], b)
        return n.outputs[0]
    def rango(v, a, b, c_=0., d=1.):
        n = nodo("ShaderNodeMapRange", clamp=True, interpolation_type="SMOOTHSTEP"); poner(n.inputs[0], v)
        n.inputs[1].default_value, n.inputs[2].default_value, n.inputs[3].default_value, n.inputs[4].default_value = a, b, c_, d
        return n.outputs[0]
    def mezcla(f, a, b, tipo="MIX"):
        n = nodo("ShaderNodeMix", data_type="RGBA", blend_type=tipo, clamp_result=True); poner(n.inputs[0], f); poner(n.inputs[6], a); poner(n.inputs[7], b)
        return n.outputs[2]
    tc = nodo("ShaderNodeTexCoord").outputs["Object"]
    def ruido(esc, det=4., est=(1, 1, 1), dist=0., vec=None):
        mp = nodo("ShaderNodeMapping"); L.new(vec or tc, mp.inputs[0]); mp.inputs["Scale"].default_value = tuple(esc * k for k in est)
        n = nodo("ShaderNodeTexNoise"); L.new(mp.outputs[0], n.inputs["Vector"]); n.inputs["Detail"].default_value = det; n.inputs["Distortion"].default_value = dist
        n.inputs["Scale"].default_value = 1.; return n.outputs["Fac"]
    sucio = rango(ruido(14, 5), .52, .68); roce = rango(ruido(40, 4), .56, .7)
    ao = nodo("ShaderNodeAmbientOcclusion", samples=8); ao.inputs["Distance"].default_value = .01
    rincon = mate("SUBTRACT", 1., ao.outputs["AO"])             # grasa y hollin en los rincones
    if c == "madera":                                           # nogal aceitado: veta larga a lo largo del arma
        mp = nodo("ShaderNodeMapping"); L.new(tc, mp.inputs[0]); mp.inputs["Scale"].default_value = (3, 60, 60)
        dn = nodo("ShaderNodeTexNoise"); L.new(mp.outputs[0], dn.inputs["Vector"]); dn.inputs["Scale"].default_value = .8; dn.inputs["Detail"].default_value = 4
        vm = nodo("ShaderNodeVectorMath", operation="ADD"); L.new(mp.outputs[0], vm.inputs[0]); L.new(dn.outputs["Color"], vm.inputs[1])
        wv = nodo("ShaderNodeTexWave", wave_type="RINGS", rings_direction="X"); L.new(vm.outputs[0], wv.inputs["Vector"])
        wv.inputs["Scale"].default_value = .18; wv.inputs["Distortion"].default_value = 11; wv.inputs["Detail"].default_value = 8; wv.inputs["Detail Roughness"].default_value = .7
        veta = wv.outputs["Fac"]; poro = rango(ruido(1400, 2, (1, 7, 7)), .58, .72); mancha = ruido(25, 5, (.3, 1, 1))
        col = mezcla(mate("ADD", mate("MULTIPLY", rango(veta, .1, .95), .65), mate("MULTIPLY", mancha, .35)), (.045, .021, .010), (.14, .072, .030))
        col = mezcla(mate("MULTIPLY", poro, .55), col, (.025, .012, .006))
        col = mezcla(mate("MULTIPLY", roce, .45), col, (.21, .12, .06))          # aceite gastado donde se agarra
        col = mezcla(mate("MULTIPLY", mate("MAXIMUM", sucio, rincon), .6), col, (.02, .016, .012))
        rug = mate("ADD", .6, mate("ADD", mate("MULTIPLY", poro, .25), mate("MULTIPLY", sucio, .2)), True)   # aceite seco de campana: mate
        alto = mate("ADD", mate("MULTIPLY", veta, .25), mate("MULTIPLY", poro, -.7)); metal, dist = 0., .00025
    else:
        # arma en campana: metal mate y gastado, con polvo, barro y hollin de la polvora; sin oxido ni cardenillo (se limpia)
        base = {"hierro": (.085, .085, .09), "laton": (.30, .21, .08), "cobre": (.26, .13, .07)}[c]
        raya = rango(ruido(500, 2, (.06, 1, 1)), .6, .65); picado = rango(ruido(700, 2), .7, .75)
        polvo = rango(ruido(18, 5), .46, .64)
        col = mezcla(mate("MULTIPLY", raya, .35), base, tuple(min(1, k * 1.3) for k in base))
        col = mezcla(mate("MULTIPLY", roce, .35), col, tuple(min(1, k * 1.2) for k in base))
        col = mezcla(mate("MULTIPLY", picado, .5), col, (.035, .03, .025))
        col = mezcla(mate("MULTIPLY", mate("MAXIMUM", polvo, rincon), .3), col, (.11, .09, .065))   # polvo y barro seco
        col = mezcla(mate("MULTIPLY", mate("MAXIMUM", sucio, rincon), .6), col, (.02, .018, .015))   # hollin y grasa
        rug = mate("ADD", .55, mate("ADD", mate("MULTIPLY", raya, -.08), mate("MULTIPLY", mate("MAXIMUM", mate("MAXIMUM", sucio, picado), polvo), .35)), True)
        alto = mate("ADD", mate("MULTIPLY", raya, .3), mate("MULTIPLY", picado, -.8)); dist = .0001
        metal = mate("SUBTRACT", 1., mate("MULTIPLY", mate("MAXIMUM", sucio, polvo), .7))
    L.new(col, p.inputs["Base Color"]); L.new(rug, p.inputs["Roughness"])
    if isinstance(metal, float):p.inputs["Metallic"].default_value = metal
    else:L.new(metal, p.inputs["Metallic"])
    bp = nodo("ShaderNodeBump"); bp.inputs["Distance"].default_value = dist; bp.inputs["Strength"].default_value = .5; L.new(alto, bp.inputs["Height"])
    L.new(bp.outputs[0], p.inputs["Normal"])
    return m
MATS = {c: material(c) for c in ("madera", "hierro", "laton", "cobre")}

# ---------------------------------------------------------------- objetos en los ejes del juego
DIESTRO = Matrix.Scale(-1, 4, (0, 1, 0))                     # la llave se construye en +Y (lado izquierdo); el espejo la pasa al lado derecho (fusil para diestros)
A_JUEGO = Matrix.Rotation(math.radians(90), 4, "X")         # modelo (Z arriba) -> juego (-Y arriba)
raiz = bpy.data.objects.new(NOMBRE, None); raiz.empty_display_size = .2; sc.collection.objects.link(raiz); raiz["hueso"] = "Weapon1"
SUAVES = {"caja_nogal": 2, "canon": 1, "puntera": 1, "cantonera": 1, "guardamonte": 1, "disparador": 1, "baqueta": 1, "martillo": 1}
BISEL = {"bayoneta": .0004, "cubo_martillo": .0006, "rastrillo": .0007, "martillo": .0008, "platina": .0005, "rebaje_llave": .0012, "contraplatina": .0006}   # cantos redondeados, no de carton
objs = []
for nombre, (bm, c) in piezas.items():
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(nombre); bm.to_mesh(me); bm.free()
    me.transform(A_JUEGO @ DIESTRO); me.flip_normals(); me.materials.append(MATS[c])
    o = bpy.data.objects.new(nombre, me); sc.collection.objects.link(o); o.parent = raiz; o["clase"] = c
    if nombre in SUAVES:
        md = o.modifiers.new("sub", "SUBSURF"); md.levels = md.render_levels = SUAVES[nombre]
        with bpy.context.temp_override(object=o, active_object=o):bpy.ops.object.modifier_apply(modifier=md.name)
    if nombre in BISEL:
        md = o.modifiers.new("bisel", "BEVEL"); md.width = BISEL[nombre]; md.segments = 3; md.limit_method = "ANGLE"; md.angle_limit = math.radians(50)
        with bpy.context.temp_override(object=o, active_object=o):bpy.ops.object.modifier_apply(modifier=md.name)
    me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(40))
    objs.append(o)

# ---------------------------------------------------------------- fotos y archivos
def foto(ruta, sel, desde, mira, lente=50, orto=None, res=(1600, 560)):
    r = sc.render; r.engine = "CYCLES"; sc.cycles.device = "GPU"; sc.cycles.samples = 64; r.resolution_x, r.resolution_y = res; r.filepath = ruta
    sc.view_settings.view_transform = "AgX"
    w = bpy.data.worlds.new("_f"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (.3, .34, .4, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = .6; sc.world = w; ex = []
    for nom, en, rot in (("_sol", 3.5, (50, 0, -30)), ("_con", 1.5, (65, 0, 160))):
        s = bpy.data.objects.new(nom, bpy.data.lights.new(nom, "SUN")); s.data.energy = en; s.data.angle = math.radians(5)
        d = Euler([math.radians(a) for a in rot]).to_matrix() @ Vector((0, 0, -1)); d.z = -d.z          # luces espejadas: alumbran el lado de la llave (-Z)
        s.rotation_euler = (-d).to_track_quat("Z", "Y").to_euler(); sc.collection.objects.link(s); ex.append(s)
    for o in objs:o.hide_render = o not in sel
    cam = bpy.data.objects.new("_cam", bpy.data.cameras.new("_cam")); sc.collection.objects.link(cam); ex.append(cam); sc.camera = cam
    cam.data.clip_start = .001; cam.location = desde
    if orto:cam.data.type = "ORTHO"; cam.data.ortho_scale = orto
    else:cam.data.lens = lente
    f = (Vector(mira) - Vector(desde)).normalized(); der = f.cross(Vector((0, -1, 0))).normalized(); arr = der.cross(f)   # arriba del arma = -Y del juego
    cam.rotation_euler = Matrix((der, arr, -f)).transposed().to_euler()
    bpy.ops.render.render(write_still=True)
    for o in ex:bpy.data.objects.remove(o)
    for o in objs:o.hide_render = False
    sc.world = None; bpy.data.worlds.remove(w)
def J(x, y, z):return A_JUEGO @ DIESTRO @ Vector((x, y, z))           # punto del modelo en ejes del juego
os.makedirs(SALIDA, exist_ok=True)
cx = (XC + XM) / 2
if "rapido" not in ARGS and "sin_fotos" not in ARGS:foto(os.path.join(SALIDA, "vista.png"), objs, J(cx, 1.6, ZA - .03), J(cx, 0, ZA - .03), orto=1.5)
if "rapido" not in ARGS and "sin_fotos" not in ARGS:foto(os.path.join(SALIDA, "detalle_llave.png"), objs, J(.03, .32, ZA + .06), J(-.01, 0, ZA - .01), 50, res=(1400, 900))
if "bayoneta" in ARGS:
    bay = [o for o in objs if o.name == "bayoneta"]
    foto(os.path.join(SALIDA, "detalle_bayoneta.png"), bay, J(XM - .10, .16, ZA - .07), J(XM + .01, .02, ZA), 50, res=(1400, 900))
    foto(os.path.join(SALIDA, "bayoneta_entera.png"), bay, J(XM + .19, .02, ZA + .9), J(XM + .19, .02, ZA), orto=.62, res=(1600, 700)); sys.exit(0)
if "boca" in ARGS:
    foto(os.path.join(SALIDA, "detalle_boca.png"), objs, J(XM + .16, .14, ZA + .08), J(XM - .06, 0, ZA), 50, res=(1400, 900)); sys.exit(0)
if "sin_fotos" in ARGS:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SALIDA, NOMBRE + ".blend"), compress=True, check_existing=False); print("FIN", SALIDA); sys.exit(0)
if "rapido" in ARGS:
    foto(os.path.join(SALIDA, "detalle_llave.png"), objs, J(.03, .32, ZA + .06), J(-.01, 0, ZA - .01), 50, res=(1400, 900)); sys.exit(0)
foto(os.path.join(SALIDA, "detalle_boca.png"), objs, J(XM + .16, .14, ZA + .08), J(XM - .06, 0, ZA), 50, res=(1400, 900))
for o in objs:
    d = os.path.join(SALIDA, "piezas", o.name); os.makedirs(d, exist_ok=True)
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]; lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    cen = (lo + hi) / 2; t = max((hi - lo).length, .02)
    foto(os.path.join(d, "vista.png"), [o], cen + Vector((t * .3, -t * .5, -t * 1.2)), cen, orto=t * 1.15, res=(800, 600))
    s2 = bpy.data.scenes.new(o.name); s2.collection.objects.link(o)
    bpy.data.libraries.write(os.path.join(d, o.name + ".blend"), {s2}, compress=True); bpy.data.scenes.remove(s2)
for i in [i for i in bpy.data.images if i.name == "Render Result"]:bpy.data.images.remove(i)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SALIDA, NOMBRE + ".blend"), compress=True, check_existing=False)
print("PIEZAS", [(o.name, o["clase"], len(o.data.polygons)) for o in objs])
print("FIN", SALIDA)
