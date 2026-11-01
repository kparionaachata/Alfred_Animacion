"""Prepara la biblioteca: un .glb por personaje con cada pieza y arma como objeto aparte, y el manifiesto.

Uso:  python -I exportar_biblioteca.py carpeta_temporal
Despues:  blender -b --factory-startup --python construir_biblioteca.py -- carpeta_temporal
"""
import json, os, re, struct, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ntw_lib import cola_attach, leer_anim, leer_parte, matrices_mundo, posed_parte
from exportar_personajes import (ANIM_CABALLO, ANIM_HOMBRE, ES_ARMA, Glb, P, UNIDADES, anadir_esqueleto, atributos, guardar_originales,
                                 leer_caballo, material_de, normales_de_caras, partes_variant, primitiva, tabla_equipo)

ARMAS = ES_ARMA
INSTRUMENTOS = r"drum|bugle|flute"
_tex_cache = {}


def textura(g, base, tinte, nombre, alfa=False):
    """Una sola imagen y material por textura dentro del mismo .glb."""
    if base in _tex_cache:
        return _tex_cache[base]
    guardar_originales(base)
    mat = material_de(g, base, tinte, nombre, alfa=alfa)
    _tex_cache[base] = mat
    return mat


def anadir_pieza(g, skin, nombre, prim):
    g.j["meshes"].append({"name": nombre, "primitives": [prim]})
    g.j["nodes"].append({"name": nombre, "mesh": len(g.j["meshes"]) - 1, "skin": skin})
    g.j["scenes"][0]["nodes"].append(len(g.j["nodes"]) - 1)


def clave_equipo(eq, nombre):
    for k in (nombre + "_lod1", re.sub(r"\d+$", "", nombre) + "_lod1", nombre):
        if k in eq:
            return k
    return None


def soldado(unidad, tinte, salida):
    _, hs, fr = leer_anim(P.leer(ANIM_HOMBRE))
    W = matrices_mundo(hs, fr[0])
    id_head = [n for n, _ in hs].index("Head")
    g = Glb()
    _tex_cache.clear()
    skin = anadir_esqueleto(g, hs, W, "soldado")
    piezas, sin_malla = [], []
    pares, _ = partes_variant(f"variantmodels/units/{unidad}.unit_variant")
    union = None
    for cat, malla, tex in pares:
        if cat == "hats":
            f3, cola = cola_attach(P.leer(malla + ".variant_part_mesh"))
            if f3:
                union = np.frombuffer(cola, dtype=np.float32, offset=32, count=16).reshape(4, 4).astype(np.float64)
    for cat, malla, tex in pares:
        m = leer_parte(P.leer(malla + ".variant_part_mesh"))
        mat = textura(g, tex, tinte, cat, alfa=(cat == "plumes"))
        if m["rigido"]:
            local = m["pos"]
            if union is not None:
                local = (union[:3, :3] @ local[..., None])[..., 0] + union[:3, 3]
            pos = (W[id_head, :3, :3] @ local[..., None])[..., 0] + W[id_head, :3, 3]
            n = normales_de_caras(pos, m["ind"])
            hb, pw = np.tile([id_head, 0, 0, 0], (len(pos), 1)), np.tile([1.0, 0, 0, 0], (len(pos), 1))
        else:
            pos, n = posed_parte(m, W)
            hb = np.zeros((len(pos), 4), dtype=np.uint8)
            hb[:, 0], hb[:, 1] = m["b1"], m["b2"]
            pw = np.zeros((len(pos), 4))
            pw[:, 0], pw[:, 1] = m["w1"], 1 - m["w1"]
        anadir_pieza(g, skin, cat, primitiva(g, pos, n, m["uv"], hb, pw, m["ind"], mat))
        piezas.append({"nodo": cat, "coleccion": "cuerpo"})
    # equipo: el de la lista de la unidad; de cada tipo se ve la primera variante, el resto queda en alternativas
    b = P.leer(f"variantmodels/units/{unidad}.unit_variant")
    ini = struct.unpack_from("<I", b, 16)[0]
    txt = [t.decode("utf-16le").lower() for t in re.findall(rb"(?:[\x20-\x7e]\x00){3,}", b[ini:])]
    eq = tabla_equipo()
    lista = [t for t in txt if t.startswith("rigid_equip")]
    if any("musket" in t or "rifle" in t for t in lista):
        lista += ["rigid_equip_gen_socket_bayonet", "rigid_equip_gen_musket_ramrod01"]
    if "_cav_lancer_" in unidad and not any("lance" in t for t in lista):
        lista.append("rigid_equip_nap_lance")
    pais = "russian" if unidad.startswith("russia") else "british"
    opcional = [f"rigid_equip_nap_backpack_{pais}", "rigid_equip_nap_ammopouch"] if "_cav_" not in unidad else ["rigid_equip_nap_ammopouch"]
    vistos, armas = set(), []
    for t in lista + opcional:
        k = clave_equipo(eq, t)
        if k is None:
            sin_malla.append(t)
            continue
        corto = re.sub(r"rigid_equip_|_lod\d$", "", k.lower())
        if any(p["nodo"] == corto for p in piezas):
            continue
        e = eq[k]
        hueso = e["hueso"]
        # las armas van aparte, en biblioteca_personajes/armas: aqui solo se anota cuales usa la unidad
        if re.search(ARMAS, corto):
            if not any(a["arma"] == corto for a in armas):
                armas.append({"arma": corto, "hueso": hs[hueso][0]})
            continue
        pos = (W[hueso, :3, :3] @ e["pos"][..., None])[..., 0] + W[hueso, :3, 3]
        mat = textura(g, e["tex"], None, "equipo" if e["tex"].endswith("texture") else "equipo2")
        anadir_pieza(g, skin, corto, primitiva(g, pos, normales_de_caras(pos, e["ind"]), e["uv"],
                                               np.tile([hueso, 0, 0, 0], (len(pos), 1)), np.tile([1.0, 0, 0, 0], (len(pos), 1)), e["ind"], mat))
        tipo = re.sub(r"\d+$", "", corto)
        if t in opcional:
            col = "alternativas"
        else:
            col = "alternativas" if tipo in vistos else ("instrumentos" if re.search(INSTRUMENTOS, corto) else "equipo")
            vistos.add(tipo)
        piezas.append({"nodo": corto, "coleccion": col, "hueso": hs[hueso][0]})
    g.guardar(salida)
    return piezas, armas, sorted(set(sin_malla))


def caballo(nombre, salida):
    _, hs, fr = leer_anim(P.leer(ANIM_CABALLO))
    W = matrices_mundo(hs, fr[0])
    g = Glb()
    _tex_cache.clear()
    skin = anadir_esqueleto(g, hs, W, "caballo")
    mat = textura(g, "unitmodels/horse/textures/horse", None, "caballo", alfa=True)
    piezas, vistos = [], set()
    for gr in leer_caballo(P.leer(f"unitmodels/horse/{nombre}_lod1.variant_weighted_mesh")):
        nv = len(gr["inf"])
        pos, nr = np.zeros((nv, 3)), np.zeros((nv, 3))
        hb, pw = np.zeros((nv, 4), dtype=np.uint8), np.zeros((nv, 4))
        for i, inf in enumerate(gr["inf"]):
            for k, (bi, of, n, w) in enumerate(inf[:4]):
                pos[i] += w * (W[bi, :3, :3] @ of + W[bi, :3, 3])
                nr[i] += w * (W[bi, :3, :3] @ n)
                hb[i, k], pw[i, k] = bi, w
        nr /= np.maximum(np.linalg.norm(nr, axis=1, keepdims=True), 1e-9)
        anadir_pieza(g, skin, gr["nombre"], primitiva(g, pos, nr, gr["uv"], hb, pw, gr["ind"], mat))
        tipo = re.sub(r"\d+$", "", gr["nombre"].lower())
        piezas.append({"nodo": gr["nombre"], "coleccion": "alternativas" if tipo in vistos else "cuerpo"})
        vistos.add(tipo)
    g.guardar(salida)
    return piezas


def equipo_suelto(tmp):
    """Todas las armas y piezas del juego, sin esqueleto, en dos .glb (uno por textura)."""
    res = []
    eq = tabla_equipo()
    hs = leer_anim(P.leer(ANIM_HOMBRE))[1]
    for sufijo, tex in (("texture", "variantmodels/equipment/texture"), ("texture2", "variantmodels/equipment/texture2")):
        g = Glb()
        _tex_cache.clear()
        mat = textura(g, tex, None, "equipo_" + sufijo)
        piezas = []
        for k, e in sorted(eq.items()):
            if e["tex"] != tex or not k.startswith("rigid_equip") or re.search(r"_lod[2-9]$", k):
                continue
            corto = re.sub(r"rigid_equip_|_lod\d$", "", k)
            pr = {"attributes": atributos(g, e["pos"], normales_de_caras(e["pos"], e["ind"]), e["uv"], e["ind"]),
                  "indices": g.acc(e["ind"], "SCALAR", 5125, 34963), "material": mat}
            g.j["meshes"].append({"name": corto, "primitives": [pr]})
            g.j["nodes"].append({"name": corto, "mesh": len(g.j["meshes"]) - 1})
            g.j["scenes"][0]["nodes"].append(len(g.j["nodes"]) - 1)
            col = "armas" if re.search(ARMAS, corto) else "instrumentos" if re.search(INSTRUMENTOS, corto) else "equipo"
            piezas.append({"nodo": corto, "coleccion": col, "hueso": hs[e["hueso"]][0] if 0 <= e["hueso"] < len(hs) else ""})
        f = os.path.join(tmp, f"equipo_{sufijo}.glb")
        g.guardar(f)
        res.append({"glb": f, "piezas": piezas})
    return res


def main(tmp):
    os.makedirs(tmp, exist_ok=True)
    # el indice de hueso de las mallas depende del orden: tiene que coincidir con el de un clip normal
    assert [h for h, _ in leer_anim(P.leer(ANIM_HOMBRE))[1]] == [h for h, _ in leer_anim(P.leer("animations/men/musket/mus_alt_stand1/mus_altstand1.anim"))[1]]
    assert [h for h, _ in leer_anim(P.leer(ANIM_CABALLO))[1]] == [h for h, _ in leer_anim(P.leer("animations/animals/horse/horse_gallop.anim"))[1]]
    man = {"personajes": [], "equipo": equipo_suelto(tmp), "sin_malla": {}}
    for carpeta, lista in UNIDADES.items():
        for unidad, tinte in lista:
            for n in sorted(P.lista("variantmodels/units/" + unidad + ".", ".unit_variant")):
                nom = os.path.basename(n)[:-len(".unit_variant")]
                f = os.path.join(tmp, nom + ".glb")
                piezas, armas, sin = soldado(nom, tinte, f)
                man["personajes"].append({"nombre": nom, "grupo": carpeta, "glb": f, "tipo": "hombre", "piezas": piezas, "armas": armas})
                man["sin_malla"][nom] = sin
                print("ok", nom, len(piezas), flush=True)
    for letra in "abcdef":
        for tipo in ("hussar", "basic"):
            nom = f"horse_{letra}_{tipo}"
            f = os.path.join(tmp, nom + ".glb")
            man["personajes"].append({"nombre": nom, "grupo": "caballos", "glb": f, "tipo": "caballo", "piezas": caballo(nom, f)})
            print("ok", nom, flush=True)
    with open(os.path.join(tmp, "manifiesto.json"), "w", encoding="utf-8") as fo:
        json.dump(man, fo, indent=1)
    print("SIN_MALLA", sorted({x for v in man["sin_malla"].values() for x in v}))


if __name__ == "__main__":
    main(sys.argv[1])
