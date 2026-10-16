#!/usr/bin/env python3
"""
translation_system.py - Sistema de traducción español-inglés para entidades
Contiene el mapeo de traducciones y funciones de traducción
"""

# Sistema de mapeo Español → Inglés para nombres de entidades
# ACTUALIZADO: Mapeo completo con todos los modelos disponibles en estructura_lista/
ENTITY_NAME_MAPPING = {
    # 🐾 ANIMALES PASIVOS (25 modelos)
    'pollo': 'chicken',
    'vaca': 'cow',
    'cerdo': 'pig',
    'oveja': 'sheep',
    'conejo': 'rabbit',
    'caballo': 'horse',
    'burro': 'donkey',
    'mula': 'mule',
    'lobo': 'wolf',
    'gato': 'cat',
    'perro': 'dog',
    'zorro': 'fox',
    'oso': 'bear',
    'oso polar': 'polar_bear',
    'panda': 'panda',
    'abeja': 'bee',
    'murcielago': 'bat',
    'rana': 'frog',
    'axolotl': 'axolotl',
    'calamar': 'squid',
    'calamar luminoso': 'glow_squid',
    'tortuga': 'turtle',
    'delfin': 'dolphin',
    'cabra': 'goat',
    'llama': 'llama',
    'ocelot': 'ocelot',

    # 🐟 PECES Y CRIATURAS ACUÁTICAS
    'pez': 'fish',
    'pez globo': 'pufferfish',
    'pez tropical': 'tropical_fish',
    'salmon': 'salmon',
    'bacalao': 'cod',
    'guardian': 'guardian',
    'guardian anciano': 'elder_guardian',

    # 👹 MOBS HOSTILES (25+ modelos)
    'creeper': 'creeper',
    'zombie': 'zombie',
    'esqueleto': 'skeleton',
    'esqueleto wither': 'wither_skeleton',
    'arana': 'spider',
    'arana de cueva': 'cave_spider',
    'enderman': 'enderman',
    'endermite': 'endermite',
    'blaze': 'blaze',
    'ghast': 'ghast',
    'wither': 'wither',
    'shulker': 'shulker',
    'piglin': 'piglin',
    'piglin zombificado': 'zombified_piglin',
    'hoglin': 'hoglin',
    'hoglin zombificado': 'hoglin_zombificado',
    'drowned': 'drowned',
    'husk': 'husk',
    'phantom': 'phantom',
    'ravager': 'ravager',
    'warden': 'warden',
    'ender dragon': 'ender_dragon',
    'enderman': 'enderman',
    'evokers': 'evokers',
    'vindicator': 'vindicator',
    'pillager': 'pillager',
    'wandering trader': 'wandering_trader',

    # 👤 PERSONAJES PRINCIPALES
    'jugador': 'player',
    'alfred': 'alfred',
    'flink': 'flink',
    'steve': 'steve',
    'alex': 'alex',
    'herobrine': 'herobrine',
    'jerry': 'jerry',

    # 🏘️ ALDEANOS Y NPCS
    'aldeano': 'villager',
    'aldeano zombi': 'zombievillager',
    'armeria': 'armorer',
    'bibliotecario': 'librarian',
    'carnicero': 'butcher',
    'clerigo': 'cleric',
    'granjero': 'farmer',
    'herrero': 'weaponsmith',
    'pescador': 'fisherman',
    'cocinero': 'chef',
    'mason': 'mason',
    'nitwit': 'nitwit',

    # 🏗️ GOLEMS Y CONSTRUCTOS
    'iron golem': 'iron_golem',
    'snow golem': 'snow_golem',

    # 🦗 CRIATURAS MISCELÁNEAS
    'allay': 'allay',
    'loro': 'parrot',
    'silverfish': 'silverfish',
    'slime': 'slime',
    'magma cube': 'magma_cube',
    'strider': 'strider',
    'witch': 'witch',

    # 🌱 VEGETACIÓN Y BLOQUES
    'mooshroom marron': 'mooshroom_brown',
    'mooshroom roja': 'mooshroom_red',
    'champiñaca marron': 'mooshroom_brown',
    'champiñaca roja': 'mooshroom_red',

    # 🏹 VARIACIONES ESPECIALES
    'lobo con perro': 'jerry',
    'wolf with dog skin': 'jerry',
    'wolf_with_dog_skin': 'jerry',

    # =================================================================
    # MAPEO INVERSO: Inglés → Inglés (para compatibilidad)
    # =================================================================
    'spider': 'spider',
    'chicken': 'chicken',
    'cow': 'cow',
    'pig': 'pig',
    'sheep': 'sheep',
    'wolf': 'wolf',
    'cat': 'cat',
    'dog': 'dog',
    'horse': 'horse',
    'donkey': 'donkey',
    'mule': 'mule',
    'rabbit': 'rabbit',
    'fish': 'fish',
    'pufferfish': 'pufferfish',
    'tropicalfish': 'tropical_fish',
    'tropical_fish': 'tropical_fish',
    'salmon': 'salmon',
    'cod': 'cod',
    'dolphin': 'dolphin',
    'turtle': 'turtle',
    'bee': 'bee',
    'bat': 'bat',
    'bear': 'bear',
    'polarbear': 'polar_bear',
    'polar_bear': 'polar_bear',
    'fox': 'fox',
    'frog': 'frog',
    'cavespider': 'cave_spider',
    'cave_spider': 'cave_spider',
    'skeleton': 'skeleton',
    'witherskeleton': 'wither_skeleton',
    'wither_skeleton': 'wither_skeleton',
    'zombie': 'zombie',
    'zombiepigman': 'zombiepigman',
    'zombifiedpiglin': 'zombified_piglin',
    'zombified_piglin': 'zombified_piglin',
    'enderman': 'enderman',
    'creeper': 'creeper',
    'goat': 'goat',
    'axolotl': 'axolotl',
    'squid': 'squid',
    'glowsquid': 'glow_squid',
    'glow_squid': 'glow_squid',
    'guardian': 'guardian',
    'elderguardian': 'elder_guardian',
    'elder_guardian': 'elder_guardian',
    'villager': 'villager',
    'zombievillager': 'zombievillager',
    'wanderingtrader': 'wandering_trader',
    'wandering_trader': 'wandering_trader',
    'armorer': 'armorer',
    'librarian': 'librarian',
    'butcher': 'butcher',
    'cleric': 'cleric',
    'farmer': 'farmer',
    'weaponsmith': 'weaponsmith',
    'fisherman': 'fisherman',
    'chef': 'chef',
    'mason': 'mason',
    'player': 'player',
    'iron_golem': 'iron_golem',
    'snow_golem': 'snow_golem',
    'allay': 'allay',
    'parrot': 'parrot',
    'silverfish': 'silverfish',
    'slime': 'slime',
    'magma_cube': 'magma_cube',
    'strider': 'strider',
    'witch': 'witch',
    'mooshroom_brown': 'mooshroom_brown',
    'mooshroom_red': 'mooshroom_red',
    'pufferfish_normal': 'pufferfish_normal',
    'pufferfish_semi': 'pufferfish_semi',
    'pufferfish_full': 'pufferfish_full',
    'hoglin_zombificado': 'hoglin_zombificado',
    'zombified_piglin_v2': 'zombified_piglin_v2',

    # =================================================================
    # VARIACIONES COMUNES Y ERRORES FRECUENTES
    # =================================================================
    'araña': 'spider',
    'mariposa': 'butterfly',
    'sapo': 'toad',
    'serpiente': 'snake',
    'ballena': 'whale',
    'zombie pigman': 'zombiepigman',
    'aldeano errante': 'wandering_trader',
    'disecado': 'husk',
    'lavagante': 'strider',
    'enderdragon': 'ender_dragon',
    'ender_dragon': 'ender_dragon',
    'polarbear': 'polar_bear',
    'witherskeleton': 'wither_skeleton',
    'zombiepigman': 'zombiepigman',
    'zombifiedpiglin': 'zombified_piglin',
    'elderguardian': 'elder_guardian',
    'zombievillager': 'zombievillager',
    'weaponsmith': 'weaponsmith',
    'glowsquid': 'glow_squid',
    'tropicalfish': 'tropical_fish',
    'cavespider': 'cave_spider',
    'iron golem': 'iron_golem',
    'snow golem': 'snow_golem',
    'magma cube': 'magma_cube',
    'hoglin zombificado': 'hoglin_zombificado',
    'champiñaca_marron': 'mooshroom_brown',
    'champiñaca_roja': 'mooshroom_red',
    'champiñaca marron': 'mooshroom_brown',
    'champiñaca roja': 'mooshroom_red',
    'pez_globo_normal': 'pufferfish_normal',
    'pez_globo_semi': 'pufferfish_semi',
    'pez_globo_completamente_inflado': 'pufferfish_full',
    'pez globo completamente inflado': 'pufferfish_full',
    'pez globo semi inflado': 'pufferfish_semi',
    'pez globo normal': 'pufferfish_normal',
}

def translate_entity_name(spanish_name: str) -> str:
    """
    Traduce nombres de entidades del español al inglés para encontrar archivos
    Maneja acentos, mayúsculas y variaciones comunes
    """
    if not spanish_name:
        return spanish_name

    # Normalizar: minúsculas, quitar acentos y caracteres especiales
    normalized = spanish_name.lower().strip()

    # Quitar acentos
    normalized = normalized.replace('á', 'a').replace('é', 'e').replace('í', 'i')
    normalized = normalized.replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
    normalized = normalized.replace('ü', 'u')

    # Quitar caracteres especiales y espacios extra
    import re
    normalized = re.sub(r'[^\w\s]', '', normalized)  # Solo letras, números y espacios
    normalized = re.sub(r'\s+', ' ', normalized)  # Espacios múltiples a uno solo

    # Buscar en mapeo directo
    if normalized in ENTITY_NAME_MAPPING:
        return ENTITY_NAME_MAPPING[normalized]

    # Si no encuentra, devolver el nombre original (podría ya estar en inglés)
    return spanish_name

def find_blend_file_with_translation(entity_name: str, search_paths: list = None) -> str:
    """
    Busca archivos .blend con sistema de traducción inteligente
    """
    import os

    if search_paths is None:
        # Rutas de búsqueda por defecto
        search_paths = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "estructura_lista"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "MCprep_addon", "MCprep_resources", "rigs"),
            os.path.dirname(os.path.dirname(__file__))  # Directorio raíz del proyecto
        ]

    print(f"🔍 Buscando archivo .blend para entidad: {entity_name}")

    # 1. Intentar con el nombre original
    for path in search_paths:
        if os.path.exists(os.path.join(path, f"{entity_name}.blend")):
            found_path = os.path.join(path, f"{entity_name}.blend")
            print(f"✅ Encontrado (original): {os.path.basename(found_path)}")
            return found_path

    # 2. Traducir al inglés y buscar
    english_name = translate_entity_name(entity_name)
    if english_name != entity_name:
        print(f"🔄 Traducción: '{entity_name}' → '{english_name}'")
        for path in search_paths:
            if os.path.exists(os.path.join(path, f"{english_name}.blend")):
                found_path = os.path.join(path, f"{english_name}.blend")
                print(f"✅ Encontrado (traducido): {os.path.basename(found_path)}")
                return found_path

    # 3. Buscar variaciones comunes del nombre en inglés
    variations = [
        english_name.replace(' ', ''),  # quitar espacios
        english_name.replace(' ', '_'),  # espacios por guiones bajos
        f"{english_name}_rig",  # agregar _rig
        f"rig_{english_name}",  # rig_ al inicio
        f"{english_name}_rigs",  # plural rigs
        f"{english_name}_blend",  # agregar _blend
    ]

    for variation in variations:
        for path in search_paths:
            blend_path = os.path.join(path, f"{variation}.blend")
            if os.path.exists(blend_path):
                print(f"✅ Encontrado (variación): {os.path.basename(blend_path)}")
                return blend_path

    # 4. Búsqueda recursiva en subdirectorios
    for base_path in search_paths:
        if os.path.exists(base_path):
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.endswith('.blend'):
                        # Comparar nombre sin extensión
                        file_name = os.path.splitext(file)[0]
                        if file_name.lower() == english_name.lower():
                            found_path = os.path.join(root, file)
                            print(f"✅ Encontrado (recursivo): {os.path.basename(found_path)}")
                            return found_path

    # 5. No encontrado - mostrar sugerencias
    print(f"❌ No se encontró archivo .blend para: {entity_name}")
    print(f"💡 Sugerencias:")
    print(f"   - Verificar que existe '{english_name}.blend' en estructura_lista/")
    print(f"   - O agregar entrada al diccionario ENTITY_NAME_MAPPING")
    print(f"   - O especificar 'nombre_traduccion' en metadata.json")

    return None

def show_translation_examples():
    """Muestra ejemplos de traducciones disponibles para debugging"""
    print("🌍 EJEMPLOS DE TRADUCCIONES DISPONIBLES:")
    examples = [
        # Animales básicos
        ("araña", "spider"),
        ("pollo", "chicken"),
        ("vaca", "cow"),
        ("cerdo", "pig"),
        ("lobo", "wolf"),
        ("creeper", "creeper"),
        ("jugador", "player"),
        ("aldeano", "villager"),
        ("esqueleto", "skeleton"),
        ("zombie", "zombie"),
        # Nuevos ejemplos con entidades actualizadas
        ("axolotl", "axolotl"),
        ("calamar luminoso", "glow_squid"),
        ("guardian anciano", "elder_guardian"),
        ("piglin zombificado", "zombified_piglin"),
        ("ender dragon", "ender_dragon"),
        ("iron golem", "iron_golem"),
        ("snow golem", "snow_golem"),
        ("champiñaca roja", "mooshroom_red"),
        ("pez globo completamente inflado", "pufferfish_full"),
        ("hoglin zombificado", "hoglin_zombificado"),
        # Personajes principales
        ("alfred", "alfred"),
        ("jerry", "jerry"),
        ("flink", "flink"),
        # Variaciones comunes
        ("lobo con perro", "jerry"),
        ("champiñaca marron", "mooshroom_brown"),
        ("pez globo semi inflado", "pufferfish_semi")
    ]

    success_count = 0
    for spanish, expected_english in examples:
        translated = translate_entity_name(spanish)
        status = "✅" if translated == expected_english else "❌"
        if translated == expected_english:
            success_count += 1
        print(f"  {status} {spanish} → {translated}")

    print(f"📊 Traducciones correctas: {success_count}/{len(examples)}")
    print(f"📚 Total de traducciones disponibles: {len(ENTITY_NAME_MAPPING)}")
    print("💡 Para añadir más traducciones, editar ENTITY_NAME_MAPPING")
    return True

# ============================================================================
# REGISTRO DEL MÓDULO
# ============================================================================

def register():
    """Registra el sistema de traducción"""
    print("✅ Sistema de traducción registrado correctamente")

def unregister():
    """Desregistra el sistema de traducción"""
    print("✅ Sistema de traducción desregistrado correctamente")