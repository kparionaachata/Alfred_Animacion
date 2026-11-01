"""Exporta de Napoleon: Total War las animaciones, armas, efectos, sonidos y tablas de combate.

Uso:  python -I exportar_mecanicas.py [animaciones] [armas] [efectos] [sonidos] [tablas]
Salida: capitulos/delgada_linea_roja/efectos_y_mecanicas/
Sin argumentos exporta todo. Solo lee la carpeta del juego.
"""
import csv, io, json, os, re, struct, sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ntw_lib import DATA, _indice_pack, leer_anim, matrices_mundo
from exportar_personajes import ANIM_CABALLO, ANIM_HOMBRE, ES_ARMA, Glb, atributos, P, material_de, normales_de_caras

SALIDA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "efectos_y_mecanicas")

GRUPOS = {
    "infanteria_mosquete": "animations/men/musket/",
    "infanteria_sable": "animations/men/sabre/",
    "jinete": "animations/men/horse_rider/",
    "caballo": "animations/animals/horse/",
    "combate_emparejado": "animations/matched_combat/",
    "abanderado": "animations/men/flag_bearer/",
    "musico": "animations/men/musician/",
    "capitan": "animations/men/captain/",
}
SALIDA_ARMAS = os.path.join(os.path.dirname(SALIDA), "armas_napoleon")
SALIDA_EQUIPO = os.path.join(SALIDA, "equipo")
EQUIPO = ("euro_bugle", "euro_drum", "drumstick", "euro_flute", "euro_flask", "nap_ammopouch", "nap_backpack_british",
          "nap_backpack_russian", "euro_telescope", "euro_stake")
TABLAS = ("projectiles", "projectile_trails", "projectile_impacts", "projectiles_explosions", "particle_effects",
          "gun_types", "gun_type_to_projectiles", "battle_entities", "entity_training_levels", "unit_stats_land",
          "unit_stats_land_experience_bonuses", "units", "unit_abilities", "unit_special_abilities", "unit_to_unit_abilities_junctions",
          "unit_movement_modifiers", "unit_class", "unit_category", "fatigue_effects", "anim_reference_poses",
          "_kv_rules", "_kv_rules_ext", "_kv_morale", "_kv_morale_ext", "_kv_fatigue")
SCHEMA = os.environ.get("NTW_SCHEMA", "")  # schema_nap.ron de rpfm-schemas (nombres de columnas)

SON_SI = re.compile(r"musket|flintlock|carbine|rifle|pistol|bullet|sabre|sword|bayonet|lance|hand_grab|foley|man_|horse|"
                    r"punch|kick|cannon|flag_flap|cheval|melee|charge|march|group|equipment|infantry|cavalry", re.I)
SON_NO = re.compile(r"campaign|camel|elephant|arrow|axe|pike|club|longsword|rocket|mortar|decking|ship|puckle|naval|"
                    r"fougasse|quicklime|carcas|chakkar|wooden_shield|sail|shield|wood$|glass", re.I)


def escribir_json(ruta, datos):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)


# ------------------------------------------------------------------ animaciones
def rest_hombre():
    _, hs, fr = leer_anim(P.leer(ANIM_HOMBRE))
    return hs, fr[0]


def rest_caballo():
    # la misma pose de reposo que usan los .glb de personajes_napoleon/caballos
    _, hs, fr = leer_anim(P.leer(ANIM_CABALLO))
    return hs, fr[0]


def unitario(q):
    return q / np.maximum(np.linalg.norm(q, axis=-1, keepdims=True), 1e-12)


def glb_clips(clips, hs, rest, nombre, salida):
    """Esqueleto (misma pose de reposo que los personajes) + un clip glTF por animacion."""
    g = Glb()
    g.j["samplers"] = []
    hijos = {i: [] for i in range(len(hs))}
    raices = []
    for i, (_, par) in enumerate(hs):
        (raices if par < 0 else hijos[par]).append(i)
    for i, (nom, _) in enumerate(hs):
        n = {"name": nom, "translation": rest[i, :3].tolist(), "rotation": unitario(rest[i, 3:7]).tolist()}
        if hijos[i]:
            n["children"] = hijos[i]
        g.j["nodes"].append(n)
    W = matrices_mundo(hs, rest)
    ib = np.array([np.linalg.inv(m).T.flatten() for m in W], dtype=np.float32)
    g.j["skins"].append({"name": nombre, "joints": list(range(len(hs))), "inverseBindMatrices": g.acc(ib, "MAT4", 5126)})
    g.j["nodes"].append({"name": nombre + "_armature", "children": raices})
    g.j["scenes"][0]["nodes"].append(len(hs))
    ind = {n: i for i, (n, _) in enumerate(hs)}
    anims = []
    for clip in clips:
        t = np.arange(clip["frames"].shape[0], dtype=np.float32) / clip["fps"]
        if len(t) < 2:
            continue
        tt = g.acc(t, "SCALAR", 5126, minmax=True)
        g.j["accessors"][tt]["min"] = [float(t.min())]
        g.j["accessors"][tt]["max"] = [float(t.max())]
        samplers, canales = [], []
        for k, (nom, _) in enumerate(clip["huesos"]):
            if nom not in ind:
                continue
            i = ind[nom]
            pos = clip["frames"][:, k, :3].astype(np.float32)
            q = unitario(clip["frames"][:, k, 3:7])
            for f in range(1, len(q)):  # sin saltos de hemisferio entre fotogramas
                if np.dot(q[f], q[f - 1]) < 0:
                    q[f] = -q[f]
            q = q.astype(np.float32)
            qr = unitario(rest[i, 3:7])
            if np.abs(pos - rest[i, :3]).max() > 1e-4:
                samplers.append({"input": tt, "output": g.acc(pos, "VEC3", 5126), "interpolation": "LINEAR"})
                canales.append({"sampler": len(samplers) - 1, "target": {"node": i, "path": "translation"}})
            if (1 - np.abs(q @ qr)).max() > 1e-6:
                samplers.append({"input": tt, "output": g.acc(q, "VEC4", 5126), "interpolation": "LINEAR"})
                canales.append({"sampler": len(samplers) - 1, "target": {"node": i, "path": "rotation"}})
        if canales:
            anims.append({"name": clip["nombre"], "samplers": samplers, "channels": canales})
    g.j["animations"] = anims
    g.guardar(salida)


def marcadores(ruta_anim):
    txt = ruta_anim[:-5] + ".txt"
    if not P.existe(txt):
        return []
    res = []
    for nom, pos in re.findall(r"Marker name:\s*(.+?)\s*[\r\n]+Position:\s*(.+?)\s*[\r\n]", P.leer(txt).decode("latin1") + "\n"):
        seg = sum(float(v) * {"min": 60, "s": 1, "ms": .001}[u] for v, u in re.findall(r"([\d.]+)\s*(min|ms|s)\b", pos))
        res.append({"t": round(seg, 3), "evento": nom})
    return res


def animaciones():
    hombre, caballo = rest_hombre(), rest_caballo()
    indice, fallos = {}, []
    for cat, ini in GRUPOS.items():
        por_archivo = {}
        for ruta in sorted(P.lista(ini, ".anim")):
            try:
                fps, hs, fr = leer_anim(P.leer(ruta))
            except Exception as e:
                fallos.append((ruta, repr(e)))
                continue
            if not hs or len(fr) < 2:  # hay .anim vacios en el juego
                fallos.append((ruta, "vacio"))
                continue
            tipo = "caballo" if any(n == "Lstirrup1" for n, _ in hs) else "hombre"
            rel = os.path.dirname(ruta[len(ini):]).replace("/", "__") or "general"
            # en cada carpeta puede haber clips de los dos esqueletos: nunca en el mismo archivo
            nom = rel if tipo == ("caballo" if cat == "caballo" else "hombre") else f"{rel}_{tipo}"
            por_archivo.setdefault((nom, tipo), []).append(
                {"ruta": ruta, "nombre": os.path.basename(ruta)[:-5], "fps": fps, "huesos": hs, "frames": fr})
        for (nom, tipo), clips in por_archivo.items():
            hs, rest = hombre if tipo == "hombre" else caballo
            d = os.path.join(SALIDA, "animaciones", cat)
            os.makedirs(d, exist_ok=True)
            f = os.path.join(d, nom + ".glb")
            glb_clips(clips, hs, rest, tipo, f)
            for c in clips:
                raiz = c["frames"][:, 0, :3]
                dist = float(np.linalg.norm((raiz[-1] - raiz[0])[[0, 2]]))
                dur = (len(raiz) - 1) / c["fps"]
                indice[c["ruta"]] = {
                    "glb": f"animaciones/{cat}/{nom}.glb", "clip": c["nombre"], "esqueleto": tipo, "fps": c["fps"],
                    "frames": len(raiz), "duracion_s": round(dur, 3), "avance_m": round(dist, 3),
                    "velocidad_m_s": round(dist / dur, 2) if dur else 0, "marcadores": marcadores(c["ruta"])}
            print("ok", cat, nom, len(clips), os.path.getsize(f) // 1024, "KB", flush=True)
    escribir_json(os.path.join(SALIDA, "mecanicas", "clips.json"), indice)
    acciones()
    print("CLIPS", len(indice), "FALLOS", fallos)


def acciones():
    """Que animacion usa el juego para cada accion (FIRE, RELOAD_1, CHARGE...) y con que mezcla."""
    d = os.path.join(SALIDA, "mecanicas", "fragmentos_originales")
    os.makedirs(d, exist_ok=True)
    res = {}
    for ruta in sorted(P.lista("animations/battleconfiguration/", ".txt")):
        b = P.leer(ruta)
        nom = os.path.basename(ruta)
        with open(os.path.join(d, nom), "wb") as f:
            f.write(b)
        tabla = res.setdefault(nom[:-4], {})
        for lin in b.decode("latin1").splitlines():
            m = re.match(r'\s*(\w+)\s+filename\s*=\s*"([^"]+)"(.*)', lin)
            if not m:
                continue
            e = {"anim": m.group(2).replace("\\", "/").lower()}
            for k, v in re.findall(r"(\w+)\s*=\s*([\w.]+)", m.group(3)):
                e[k] = float(v) if re.fullmatch(r"[\d.]+", v) else v
            tabla.setdefault(m.group(1), []).append(e)
    escribir_json(os.path.join(SALIDA, "mecanicas", "acciones.json"), res)


# ------------------------------------------------------------------ armas y equipo
def armas():
    """Cada arma en armas_napoleon/ y el equipo en efectos_y_mecanicas/equipo/."""
    hs, rest = rest_hombre()
    indice = {d: {} for d in (SALIDA_ARMAS, SALIDA_EQUIPO)}
    for arch, tex in (("mesh", "variantmodels/equipment/texture"), ("mesh2", "variantmodels/equipment/texture2")):
        b = P.leer(f"variantmodels/equipment/{arch}.variant_part_mesh")
        ng = struct.unpack_from("<I", b, 16)[0]
        p = 36
        for _ in range(ng):
            nom = b[p:p + 80].decode("utf-16le").split("\0")[0]
            par, nv, ni = struct.unpack_from("<iII", b, p + 80)
            q = p + 92
            a = np.frombuffer(b, dtype=np.float32, count=nv * 16, offset=q).reshape(nv, 16).astype(np.float64)
            ind = np.frombuffer(b, dtype=np.uint16, count=ni, offset=q + nv * 64).astype(np.uint32)
            p = q + nv * 64 + ni * 2
            n = nom.lower()
            es_arma = n.startswith("rigid_equip") and re.search(ES_ARMA, n)
            if re.search(r"_lod[2-9]$", n) or not (es_arma or any(x in n for x in EQUIPO)):  # baqueta, catalejo y estaca no llevan _lod1
                continue
            g = Glb()
            mat = material_de(g, tex, None, "equipo")
            pos = a[:, :3]
            pr = {"attributes": atributos(g, pos, normales_de_caras(pos, ind), a[:, 7:9], ind),
                  "indices": g.acc(ind, "SCALAR", 5125, 34963), "material": mat}
            corto = n.replace("rigid_equip_", "").replace("_lod1", "")
            hueso = hs[par][0] if 0 <= par < len(hs) else ""
            g.j["meshes"].append({"name": corto, "primitives": [pr]})
            g.j["nodes"].append({"name": corto, "mesh": 0, "extras": {"hueso": hueso}})  # Blender lo lee como propiedad
            g.j["scenes"][0]["nodes"].append(0)
            d = SALIDA_ARMAS if es_arma else SALIDA_EQUIPO
            os.makedirs(d, exist_ok=True)
            g.guardar(os.path.join(d, corto + ".glb"))
            indice[d][corto] = {"hueso": hueso, "vertices": nv}
            print("ok", corto, indice[d][corto], flush=True)
    for d, tabla in indice.items():
        escribir_json(os.path.join(d, "huesos.json"), tabla)


# ------------------------------------------------------------------ efectos
def valor(s):
    s = s.strip()
    m = re.fullmatch(r"(variance|vector)\((.*)\)", s)
    if m:
        partes, nivel, act = [], 0, ""
        for c in m.group(2):
            if c == "," and nivel == 0:
                partes.append(act)
                act = ""
                continue
            nivel += (c == "(") - (c == ")")
            act += c
        return [valor(x) for x in partes + [act]]
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d*\.\d+", s):
        return float(s)
    return {"true": True, "false": False}.get(s, s)


def efectos():
    d = os.path.join(SALIDA, "efectos")
    os.makedirs(os.path.join(d, "texturas"), exist_ok=True)
    x = P.leer("effects/landbattle.xml")
    with open(os.path.join(d, "landbattle_original.xml"), "wb") as f:
        f.write(x)
    with open(os.path.join(d, "unit_dust_parameters.txt"), "wb") as f:
        f.write(P.leer("effects/unit_dust_parameters.txt"))
    s = x.decode("latin1")
    attrs = lambda t: {k: valor(v) for k, v in re.findall(r"(\w+)='([^']*)'", t)}
    infos, grupos = {}, {}
    for m in re.finditer(r"<SCRIPTED_EFFECT_INFO (.*?)>(.*?)</SCRIPTED_EFFECT_INFO>", s, flags=re.S):
        e = attrs(m.group(1))
        cuerpo = re.sub(r"<EMISSION_MODIFIERS.*?</EMISSION_MODIFIERS>", "", m.group(2), flags=re.S)
        for tag, a in re.findall(r"<([A-Z_]+) ([^<>]*?)/?>", cuerpo):
            e[tag.lower()] = attrs(a)
        e["modificadores"] = {t.lower(): attrs(a) for t, a in re.findall(r"<(EMISSION_MODIFIER_[A-Z_0-9]+) ([^<>]*?)/>", m.group(2))
                              if "TYPE_NONE" not in a}
        infos[e["name"]] = e
    for m in re.finditer(r"<SCRIPTED_EFFECT_GROUP name='([^']+)'.*?</SCRIPTED_EFFECT_GROUP>", s, flags=re.S):
        grupos[m.group(1)] = re.findall(r"<SCRIPTED_EFFECT_GROUP_ENTRY name='[^']*' effect='([^']*)'", m.group(0))
    faltan = sorted({e for g in grupos.values() for e in g} - set(infos))
    escribir_json(os.path.join(d, "efectos.json"), {"grupos": grupos, "efectos": infos})
    hechas, fallos = 0, []
    nombres = {}
    for ruta in P.lista("effects/textures/"):
        base, ext = os.path.splitext(ruta)
        if ext in (".dds", ".tga") and (ext == ".dds" or base not in nombres):
            nombres[base] = ruta
    nombres.update({"rigidmodels/projectile/textures/empire_cannon_muzzleflash": "rigidmodels/projectile/textures/empire_cannon_muzzleflash.dds"})
    for base, ruta in sorted(nombres.items()):
        try:
            Image.open(io.BytesIO(P.leer(ruta))).convert("RGBA").save(os.path.join(d, "texturas", os.path.basename(base) + ".png"))
            hechas += 1
        except Exception as e:
            fallos.append((ruta, repr(e)))
    print("EFECTOS", len(infos), "GRUPOS", len(grupos), "SIN_DEFINICION", faltan, "TEXTURAS", hechas, "FALLOS", fallos)


# ------------------------------------------------------------------ sonidos
def sonidos():
    sp = _indice_pack(os.path.join(DATA, "sound.pack"))
    d = os.path.join(SALIDA, "sonidos")
    eventos, faltan, copiados, tam = {}, set(), set(), 0
    for n in ("weapons", "animations", "battle", "battle_group_movement"):
        filas = list(csv.reader(io.StringIO(P.leer(f"sounds/events/sound_events_{n}.csv").decode("latin1"))))
        cab = [c.strip().strip('"').strip() for c in filas[0]]
        col = {c: i for i, c in enumerate(cab)}
        for fila in filas[1:]:
            if not fila or not fila[0] or not SON_SI.search(fila[0]) or SON_NO.search(fila[0]):
                continue
            lee = lambda c: fila[col[c]] if col.get(c, 10 ** 6) < len(fila) else ""
            archivos = []
            for w in fila[col["wavefile_1"]:]:
                w = w.strip().replace("\\", "/").lower()
                if not w:
                    continue
                k = next((x for x in (w, w[:-4] + ".mp3", w[:-4] + ".wav") if x in sp), None)
                if k is None:
                    faltan.add(w)
                    continue
                archivos.append(k)
                if k not in copiados:
                    pa, off, t = sp[k]
                    dst = os.path.join(d, k)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    with open(pa, "rb") as f:
                        f.seek(off)
                        b = f.read(t)
                    with open(dst, "wb") as f:
                        f.write(b)
                    copiados.add(k)
                    tam += t
            eventos[fila[0]] = {"tabla": n, "volumen": lee("volume"), "tono_min": lee("min_pitch"), "tono_max": lee("max_pitch"),
                                "dist_min": lee("min_dist"), "dist_max": lee("max_dist"), "en_bucle": lee("looped"),
                                "reproduccion": lee("playback"), "probabilidad": lee("probability"), "archivos": archivos}
    escribir_json(os.path.join(d, "eventos.json"), eventos)
    print("EVENTOS", len(eventos), "ARCHIVOS", len(copiados), round(tam / 1e6), "MB", "NO_ENCONTRADOS", len(faltan), sorted(faltan)[:10])


# ------------------------------------------------------------------ tablas
def esquemas():
    t = open(SCHEMA, encoding="utf8").read()
    res = {}
    claves = list(re.finditer(r'^\s*"(\w+_tables)": \[', t, flags=re.M))
    for i, m in enumerate(claves):
        fin = claves[i + 1].start() if i + 1 < len(claves) else len(t)
        bloque = t[m.end():fin]
        vs = list(re.finditer(r"^\s*version: (\d+),", bloque, flags=re.M))
        res[m.group(1)] = [(int(v.group(1)), re.findall(r'name: "(\w+)",\s+field_type: (\w+)',
                            bloque[v.end():vs[j + 1].start() if j + 1 < len(vs) else len(bloque)]))
                           for j, v in enumerate(vs)]
    return res


def leer_fila(b, p, campos):
    fila = []
    for _, tipo in campos:
        if tipo == "Boolean":
            if b[p] > 1:
                raise ValueError
            fila.append(bool(b[p]))
            p += 1
        elif tipo == "F32":
            fila.append(round(struct.unpack_from("<f", b, p)[0], 5))
            p += 4
        elif tipo == "I32":
            fila.append(struct.unpack_from("<i", b, p)[0])
            p += 4
        elif tipo == "I16":
            fila.append(struct.unpack_from("<h", b, p)[0])
            p += 2
        elif tipo in ("StringU16", "OptionalStringU16"):
            if tipo[0] == "O":
                hay = b[p]
                p += 1
                if hay > 1:
                    raise ValueError
                if not hay:
                    fila.append("")
                    continue
            n = struct.unpack_from("<H", b, p)[0]
            fila.append(b[p + 2:p + 2 + 2 * n].decode("utf-16le"))
            if p + 2 + 2 * n > len(b):
                raise ValueError
            p += 2 + 2 * n
        elif tipo in ("StringU8", "OptionalStringU8"):
            if tipo[0] == "O":
                hay = b[p]
                p += 1
                if not hay:
                    fila.append("")
                    continue
            n = struct.unpack_from("<H", b, p)[0]
            fila.append(b[p + 2:p + 2 + n].decode("latin1"))
            p += 2 + n
        else:
            raise ValueError(tipo)
    return fila, p


def tablas():
    sch = esquemas()
    d = os.path.join(SALIDA, "mecanicas", "tablas")
    os.makedirs(d, exist_ok=True)
    fallos = []
    for t in TABLAS:
        clave = f"db/{t}_tables/{t}"
        if not P.existe(clave):
            fallos.append((t, "no esta"))
            continue
        b = P.leer(clave)
        p = 0
        if b[:4] == b"\xfd\xfe\xfc\xff":
            n = struct.unpack_from("<H", b, 4)[0]
            p = 6 + 2 * n
        ver = 0
        if b[p:p + 4] == b"\xfc\xfd\xfe\xff":
            ver = struct.unpack_from("<I", b, p + 4)[0]
            p += 8
        nf = struct.unpack_from("<I", b, p + 1)[0]
        p += 5
        hecho = False
        for v, campos in sorted(sch.get(t + "_tables", []), key=lambda x: x[0] != ver):
            try:
                q, filas = p, []
                for _ in range(nf):
                    fila, q = leer_fila(b, q, campos)
                    filas.append(fila)
                if q != len(b):
                    continue
            except (ValueError, struct.error, IndexError, UnicodeDecodeError):
                continue
            with open(os.path.join(d, t + ".csv"), "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow([c for c, _ in campos])
                w.writerows(filas)
            print("ok", t, "filas", nf, "columnas", len(campos), flush=True)
            hecho = True
            break
        if not hecho:
            fallos.append((t, f"esquema no encaja (version {ver}, {nf} filas)"))
    print("TABLAS FALLOS", fallos)


if __name__ == "__main__":
    pedir = sys.argv[1:] or ["animaciones", "armas", "efectos", "sonidos", "tablas"]
    for s in pedir:
        print("==", s, flush=True)
        globals()[s]()
