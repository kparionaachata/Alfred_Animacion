"""Cacareo desesperado de los 3 pollos por comer los insectos de Alfred: rafagas rapidas de say1-3 (y algun hurt como
chillido) con tono variado, por pollo, al correr (desde que arrancan) y sobre todo mientras picotean (hasta f960).
Reemplaza los cacareos sueltos SND_pollos_alfred_cacarea_*."""
import bpy, random
sc = bpy.context.scene; ed = sc.sequence_editor
S = r"C:\Users\user\Desktop\Alfred_Animacion\capitulos\capitulo_4\sonidos_pollos_desesperados"   # say/hurt del pollo subidos de tono (ffmpeg asetrate x1.15 / x1.30)
logs = bpy.app.driver_namespace["_pollos_alfred_logs"]
for s in [s for s in ed.strips_all if s.name.startswith(("SND_pollos_alfred_cacarea", "SND_pollos_desesp"))]: ed.strips.remove(s)
rnd = random.Random(7)
def libre(f, n=20, ch0=41):
    for ch in range(ch0, 128):
        if not any(s.channel == ch and s.frame_final_start < f + n and s.frame_final_end > f for s in ed.strips_all): return ch
def poner(nm, ruta, f, vol, tono):
    x = ed.strips.new_sound(nm, ruta, libre(f), f); x.volume = vol; x["vol_base"] = vol
    return x
n_tot = 0; tiene_pitch = None
for k, (n, L) in enumerate(logs.items()):
    corre = next(a for slot, t, a, b in L if t == "caminar" and a >= 690)
    fin = sc.frame_end
    f = corre + rnd.randint(0, 6)
    while f < fin - 6:
        sobre = any(t == "saltar" and a <= f for slot, t, a, b in L)
        # rafaga de 2-4 cacareos seguidos, mas seguida sobre Alfred
        for j in range(rnd.randint(2, 4) if sobre else rnd.randint(1, 2)):
            if f >= fin - 6: break
            chillido = rnd.random() < 0.15
            tono = rnd.choice((115, 130))
            ruta = S + (r"\hurt%d_p%d.ogg" % (rnd.randint(1, 2), tono) if chillido else r"\say%d_p%d.ogg" % (rnd.randint(1, 3), tono))
            x = poner("SND_pollos_desesp_%s_%d" % (n, f), ruta, f, 0.42 if not chillido else 0.3, tono / 100)
            n_tot += 1
            f += rnd.randint(5, 9)
        f += rnd.randint(8, 16) if sobre else rnd.randint(14, 24)
DUCK = 0.56
exec(open(r"C:\Users\user\Desktop\Alfred_Animacion\generador de animaciones\alfred\refinar\docs\acciones\ducking_voces.py", encoding="utf-8").read(), {"__name__": "x", "DUCK": DUCK})
result = {"cacareos": n_tot}
