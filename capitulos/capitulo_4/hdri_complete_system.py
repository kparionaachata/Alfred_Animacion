import bpy
import os
import math
import mathutils
from bpy.props import StringProperty, IntProperty, FloatProperty, BoolProperty, EnumProperty, FloatVectorProperty
from bpy.types import Panel, Operator, PropertyGroup

def get_hdri_files(context):
    """Escanea la carpeta seleccionada y retorna lista de archivos .exr"""
    hdri_files = []
    props = context.scene.hdri_tester_props
    folder_path = props.hdri_folder_path

    if folder_path and os.path.exists(folder_path):
        for file in os.listdir(folder_path):
            if file.lower().endswith('.exr'):
                hdri_files.append(file)
    hdri_files.sort()
    return hdri_files

def get_hdri_items(self, context):
    """Genera items para el EnumProperty"""
    items = []
    hdri_files = get_hdri_files(context)
    if not hdri_files:
        items.append(("NONE", "No HDRI files found", "No se encontraron archivos HDRI en la carpeta seleccionada"))
    else:
        for hdri in hdri_files:
            display_name = hdri.replace('_', ' ').replace('.exr', '').title()
            items.append((hdri, display_name, f"HDRI: {hdri}"))
    return items

class HDRITesterProperties(PropertyGroup):
    solar_rays_enabled: BoolProperty(name="Activar rayos de luz", default=True)
    solar_rays_count: IntProperty(name="Cantidad de rayos", default=32, min=6, max=64)
    solar_rays_power: FloatProperty(name="Potencia por rayo (W)", default=1500.0, min=0.0, max=1000000.0)
    solar_rays_length: FloatProperty(name="Alcance de rayos", default=25.0, min=1.0, max=1000.0)
    solar_rays_angle: FloatProperty(name="Apertura de rayos (grados)", default=12.0, min=1.0, max=90.0)
    solar_rays_density: FloatProperty(name="Atmósfera para rayos", default=0.025, min=0.0, max=1.0,
        description="Dispersión del aire que hace visibles los haces; 0 deja solo iluminación de superficies")
    solar_face_enabled: BoolProperty(name="Activar cara del sol", default=True)
    solar_happy_frames: StringProperty(name="Frames feliz", default="1-120", description="Intervalos inclusivos: 1-80, 150-200. Vacío: sin expresión feliz")
    solar_sad_frames: StringProperty(name="Frames triste", default="121-240", description="Intervalos inclusivos. Triste tiene prioridad si se solapan")
    solar_duration: FloatProperty(name="Duración (segundos)", default=60.0, min=0.1, max=86400.0)
    solar_start: IntProperty(name="Frame de amanecer", default=1)
    solar_full_day: BoolProperty(name="Incluir noche (vuelta completa)", default=False)
    solar_repeat: BoolProperty(name="Repetir ciclo", default=False)
    solar_radius: FloatProperty(name="Distancia del sol", default=100.0, min=1.0, max=100000.0)
    solar_size: FloatProperty(name="Radio de la esfera", default=2.0, min=0.01, max=1000.0)
    solar_elevation: FloatProperty(name="Altura máxima (grados)", default=60.0, min=1.0, max=90.0)
    solar_heading: FloatProperty(name="Orientación del recorrido", default=0.0, min=-360.0, max=360.0)
    solar_center: FloatVectorProperty(name="Centro del horizonte", subtype='TRANSLATION', default=(0.0, 0.0, 0.0))
    solar_energy: FloatProperty(name="Intensidad solar máxima", default=5.0, min=0.0, max=1000.0)
    solar_emission: FloatProperty(name="Brillo de la esfera", default=10.0, min=0.0, max=1000.0)
    solar_color: FloatVectorProperty(name="Color del sol", subtype='COLOR', default=(1.0, 0.75, 0.35), min=0.0, max=1.0)

    hdri_folder_path: StringProperty(
        name="HDRI Folder",
        description="Ruta a la carpeta que contiene los archivos HDRI (.exr)",
        default=r"C:\Users\user\Desktop\Alfred_Animacion\cielos",
        subtype='DIR_PATH'
    )

    # Controles de visualización independiente
    enable_main_hdri: BoolProperty(
        name="Activar HDRI Principal",
        description="Activa/desactiva la visualización del HDRI principal",
        default=True
    )

    enable_moving_hdri: BoolProperty(
        name="Activar HDRI Movimiento",
        description="Activa/desactiva la visualización del HDRI de movimiento",
        default=True
    )

    hdri_visible: BoolProperty(
        name="HDRI Visible",
        description="Muestra u oculta completamente el HDRI (viewport y render) sin perder la configuración",
        default=True
    )

    # HDRI Principal (estático)
    selected_hdri_main: EnumProperty(
        name="HDRI Principal",
        description="HDRI principal que permanece estático",
        items=get_hdri_items
    )
    
    main_hdri_strength: FloatProperty(
        name="Intensidad Principal",
        description="Intensidad de iluminación del HDRI principal",
        default=1.0,
        min=0.0,
        max=10.0
    )
    
    main_hdri_rotation: FloatProperty(
        name="Rotación Principal",
        description="Rotación del HDRI principal en el eje Z (grados)",
        default=0.0,
        min=0.0,
        max=360.0
    )
    
    # HDRI de Movimiento (dinámico)
    selected_hdri_moving: EnumProperty(
        name="HDRI de Movimiento",
        description="HDRI que rotará detrás del principal",
        items=get_hdri_items
    )
    
    moving_hdri_strength: FloatProperty(
        name="Intensidad Movimiento",
        description="Intensidad/Opacidad del HDRI en movimiento",
        default=0.5,
        min=0.0,
        max=2.0
    )
    
    moving_hdri_visibility: FloatProperty(
        name="Visibilidad",
        description="Qué tan visible es el HDRI en movimiento (0=invisible, 1=totalmente visible)",
        default=0.3,
        min=0.0,
        max=1.0
    )
    
    moving_speed: FloatProperty(
        name="Velocidad de Rotación",
        description="Velocidad de rotación del HDRI en movimiento (grados por frame)",
        default=0.2,
        min=-5.0,
        max=5.0
    )
    
    moving_initial_rotation: FloatProperty(
        name="Rotación Inicial",
        description="Ángulo de inicio del HDRI en movimiento",
        default=0.0,
        min=0.0,
        max=360.0
    )
    
    # ============ SISTEMA DE LUZ SOLAR ============
    enable_sun_light: BoolProperty(
        name="Activar Luz Solar",
        description="Activa/desactiva la luz solar direccional",
        default=True
    )
    
    light_type: EnumProperty(
        name="Tipo de Luz",
        description="Tipo de fuente de luz",
        items=[
            ('SUN', "Sol", "Luz direccional paralela (ideal para sol)"),
            ('POINT', "Punto", "Luz omnidireccional desde un punto"),
            ('SPOT', "Spot", "Luz cónica direccional"),
            ('AREA', "Área", "Luz desde una superficie rectangular"),
        ],
        default='SUN'
    )
    
    sun_horizontal_angle: FloatProperty(
        name="Ángulo Horizontal",
        description="Posición horizontal del sol (coincide con rotación del HDRI)",
        default=0.0,
        min=0.0,
        max=360.0
    )
    
    sun_vertical_angle: FloatProperty(
        name="Ángulo Vertical",
        description="Altura del sol (0=horizonte, 90=cenit)",
        default=45.0,
        min=0.0,
        max=90.0
    )
    
    light_distance: FloatProperty(
        name="Distancia",
        description="Distancia de la luz al origen (Point/Spot/Area)",
        default=10.0,
        min=0.1,
        max=100.0
    )
    
    sun_intensity: FloatProperty(
        name="Intensidad",
        description="Potencia de la luz",
        default=5.0,
        min=0.0,
        max=1000.0
    )
    
    light_color: FloatVectorProperty(
        name="Color de Luz",
        description="Color RGB de la luz",
        subtype='COLOR',
        default=(1.0, 0.95, 0.8),
        min=0.0,
        max=1.0,
        size=3
    )
    
    use_color_presets: BoolProperty(
        name="Usar Presets de Color",
        description="Usar presets de temperatura de color predefinidos",
        default=False
    )
    
    sun_color_preset: EnumProperty(
        name="Preset de Color",
        description="Temperatura de color predefinida",
        items=[
            ('SUNRISE', "Amanecer", "Naranja cálido (2000K)"),
            ('MORNING', "Mañana", "Amarillo suave (3500K)"),
            ('NOON', "Mediodía", "Blanco neutro (5500K)"),
            ('AFTERNOON', "Tarde", "Amarillo cálido (4000K)"),
            ('SUNSET', "Atardecer", "Naranja intenso (2500K)"),
            ('OVERCAST', "Nublado", "Blanco frío (6500K)"),
            ('MOONLIGHT', "Luz Lunar", "Azul frío (4100K)"),
        ],
        default='NOON'
    )
    
    sun_size: FloatProperty(
        name="Tamaño Angular",
        description="Ángulo del sol (afecta suavidad de sombras) - Solo SUN",
        default=0.545,
        min=0.0,
        max=10.0
    )
    
    spot_size: FloatProperty(
        name="Tamaño Spot",
        description="Ángulo del cono de luz - Solo SPOT",
        default=45.0,
        min=1.0,
        max=180.0
    )
    
    spot_blend: FloatProperty(
        name="Suavidad Spot",
        description="Suavidad de los bordes del spot",
        default=0.15,
        min=0.0,
        max=1.0
    )
    
    area_size_x: FloatProperty(
        name="Ancho Área",
        description="Ancho de la luz de área",
        default=2.0,
        min=0.01,
        max=100.0
    )
    
    area_size_y: FloatProperty(
        name="Alto Área",
        description="Alto de la luz de área",
        default=2.0,
        min=0.01,
        max=100.0
    )
    
    area_shape: EnumProperty(
        name="Forma Área",
        description="Forma de la luz de área",
        items=[
            ('SQUARE', "Cuadrado", "Luz cuadrada"),
            ('RECTANGLE', "Rectángulo", "Luz rectangular"),
            ('DISK', "Disco", "Luz circular"),
            ('ELLIPSE', "Elipse", "Luz elíptica"),
        ],
        default='SQUARE'
    )

    # ============ ARCHIVO DE ESCENA ============
    scene_file_name: StringProperty(
        name="Nombre de Escena",
        description="Nombre del archivo de escena HDRI (sin extensión .py)",
        default="scene_hdri_config"
    )

    # ============ POSICIÓN DE LA LUZ ============
    light_position_x: FloatProperty(
        name="Posición X",
        description="Posición X de la luz en el espacio 3D",
        default=0.0,
        min=-1000.0,
        max=1000.0
    )

    light_position_y: FloatProperty(
        name="Posición Y",
        description="Posición Y de la luz en el espacio 3D",
        default=0.0,
        min=-1000.0,
        max=1000.0
    )

    light_position_z: FloatProperty(
        name="Posición Z",
        description="Posición Z de la luz en el espacio 3D",
        default=0.0,
        min=-1000.0,
        max=1000.0
    )
    
    # ============ SISTEMA VOLUMÉTRICO (GOD RAYS) ============
    enable_volumetric: BoolProperty(
        name="Activar Volumétrico",
        description="Activa rayos volumétricos (God Rays) visibles en la atmósfera",
        default=False
    )
    
    volumetric_density: FloatProperty(
        name="Densidad Volumétrica",
        description="Densidad de la atmósfera/niebla volumétrica",
        default=0.01,
        min=0.0,
        max=1.0
    )
    
    volumetric_anisotropy: FloatProperty(
        name="Anisotropía",
        description="Dirección del scatter (-1=atrás, 0=uniforme, 1=adelante)",
        default=0.5,
        min=-1.0,
        max=1.0
    )
    
    volumetric_scatter_color: FloatVectorProperty(
        name="Color de Scatter",
        description="Color del scatter volumétrico",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0),
        min=0.0,
        max=1.0,
        size=3
    )
    
    volumetric_absorption: FloatProperty(
        name="Absorción",
        description="Cuánta luz es absorbida por el volumen",
        default=0.0,
        min=0.0,
        max=1.0
    )
    
    volumetric_emission_strength: FloatProperty(
        name="Emisión Volumétrica",
        description="Luz emitida por el volumen mismo",
        default=0.0,
        min=0.0,
        max=10.0
    )
    
    volumetric_volume_size: FloatProperty(
        name="Tamaño del Volumen",
        description="Tamaño del cubo volumétrico",
        default=20.0,
        min=1.0,
        max=1000.0
    )
    
    volumetric_steps: IntProperty(
        name="Pasos Volumétricos",
        description="Calidad del render volumétrico (más = mejor calidad)",
        default=128,
        min=1,
        max=1024
    )
    
    volumetric_step_size: FloatProperty(
        name="Tamaño de Paso",
        description="Tamaño de cada paso de muestreo volumétrico",
        default=0.1,
        min=0.001,
        max=10.0
    )
    
    # ============ SISTEMA DE GLARE (LENS FLARE) ============
    enable_glare: BoolProperty(
        name="Activar Lens Flare",
        description="Activa el efecto de destello cuando la cámara apunta al sol",
        default=False
    )
    
    glare_type: EnumProperty(
        name="Tipo de Glare",
        description="Tipo de efecto de destello",
        items=[
            ('GHOSTS', "Ghosts", "Destellos fantasma (lente sucia)"),
            ('STREAKS', "Streaks", "Rayos de luz en estrella"),
            ('FOG_GLOW', "Fog Glow", "Resplandor difuso"),
            ('SIMPLE_STAR', "Simple Star", "Estrella simple"),
        ],
        default='STREAKS'
    )
    
    glare_threshold: FloatProperty(
        name="Umbral",
        description="Brillo mínimo para activar el glare",
        default=1.0,
        min=0.0,
        max=10.0
    )
    
    glare_intensity: FloatProperty(
        name="Intensidad Glare",
        description="Intensidad del efecto de destello",
        default=0.5,
        min=0.0,
        max=5.0
    )
    
    glare_iterations: IntProperty(
        name="Iteraciones",
        description="Calidad del glare (más = mejor calidad)",
        default=3,
        min=1,
        max=5
    )
    
    glare_mix: FloatProperty(
        name="Mix",
        description="Mezcla del glare con la imagen original",
        default=1.0,
        min=-1.0,
        max=1.0
    )


def apply_sky_settings_from_dict(settings_dict):
    """Aplica la configuración del cielo desde un diccionario"""
    props = bpy.context.scene.hdri_tester_props

    for key, value in settings_dict.items():
        if hasattr(props, key):
            setattr(props, key, value)

    # Aplicar los cambios
    bpy.ops.hdri.apply_selected()


def load_slot_sky_configuration(slot_path=None):
    """Carga automáticamente la configuración del cielo desde un archivo slot"""
    if not slot_path:
        # Intentar rutas comunes de slots
        possible_paths = [
            r"C:\Users\user\Desktop\Alfred_Animacion\animacion\Prompt_053\ecena\slot_001_caminar_llanura_animated.py",
            r"C:\Users\user\Desktop\Alfred_Animacion\animacion\Prompt_054\ecena\slot_001_caminar_llanura_animated.py",
            r"C:\Users\user\Desktop\Alfred_Animacion\animacion\Prompt_055\ecena\slot_001_caminar_llanura_animated.py",
            r"C:\Users\user\Desktop\Alfred_Animacion\animacion\Prompt_056\ecena\slot_001_caminar_llanura_animated.py",
        ]

        for path in possible_paths:
            if os.path.exists(path):
                slot_path = path
                break

    if not slot_path or not os.path.exists(slot_path):
        print("⚠️ No se encontró ningún archivo slot válido para cargar configuración")
        return False

    try:
        # Leer el contenido del archivo
        with open(slot_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extraer valores usando expresiones regulares
        import re

        # Patrones para extraer los valores
        patterns = {
            # HDRI - Buscar tanto las variables directas como las del import_sky_hdri_direct
            'skies_dir': r'skies_dir\s*=\s*r?"([^"]*)"',
            'primary_hdri_file': r'primary_hdri_file\s*=\s*"([^"]*)"',
            'primary_strength': r'primary_strength\s*=\s*([\d.]+)',
            'primary_rotation': r'primary_rotation\s*=\s*([\d.]+)',
            'secondary_hdri_file': r'secondary_hdri_file\s*=\s*"([^"]*)"',
            'secondary_visibility': r'secondary_visibility\s*=\s*([\d.]+)',
            'secondary_strength': r'secondary_strength\s*=\s*([\d.]+)',
            'secondary_speed': r'secondary_speed\s*=\s*([\d.]+)',
            'secondary_initial_rotation': r'secondary_initial_rotation\s*=\s*([\d.]+)',
            # Luz solar
            'enable_sun_light': r'enable_sun_light\s*=\s*(True|False)',
            'light_type': r'light_type\s*=\s*"([^"]*)"',
            'sun_horizontal_angle': r'sun_horizontal_angle\s*=\s*([\d.]+)',
            'sun_vertical_angle': r'sun_vertical_angle\s*=\s*([\d.]+)',
            'light_distance': r'light_distance\s*=\s*([\d.]+)',
            'sun_intensity': r'sun_intensity\s*=\s*([\d.]+)',
            'light_color': r'light_color\s*=\s*\(([^)]+)\)',
            'use_color_presets': r'use_color_presets\s*=\s*(True|False)',
            'sun_color_preset': r'sun_color_preset\s*=\s*"([^"]*)"',
            'sun_size': r'sun_size\s*=\s*([\d.]+)',
            'spot_size': r'spot_size\s*=\s*([\d.]+)',
            'spot_blend': r'spot_blend\s*=\s*([\d.]+)',
            'area_size_x': r'area_size_x\s*=\s*([\d.]+)',
            'area_size_y': r'area_size_y\s*=\s*([\d.]+)',
            'area_shape': r'area_shape\s*=\s*"([^"]*)"',
        }

        extracted_values = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                value = match.group(1)
                # Convertir a tipo apropiado
                if key in ['primary_strength', 'primary_rotation', 'secondary_visibility',
                          'secondary_strength', 'secondary_speed', 'secondary_initial_rotation',
                          'sun_horizontal_angle', 'sun_vertical_angle', 'light_distance',
                          'sun_intensity', 'sun_size', 'spot_size', 'spot_blend',
                          'area_size_x', 'area_size_y']:
                    extracted_values[key] = float(value)
                elif key in ['enable_sun_light', 'use_color_presets']:
                    extracted_values[key] = value == 'True'
                elif key == 'light_color':
                    # Convertir string de tupla a tupla real
                    extracted_values[key] = tuple(float(x.strip()) for x in value.split(','))
                else:
                    extracted_values[key] = value

        # Verificar que tenemos algunos valores esenciales
        # Si no se encontraron las variables de luz solar, usar valores por defecto del slot
        required_keys = ['enable_sun_light', 'light_type']
        if not all(key in extracted_values for key in required_keys):
            print("⚠️ No se pudieron extraer variables de luz solar del slot")
            print(f"   Valores encontrados: {list(extracted_values.keys())}")
            print(f"   Valores requeridos: {required_keys}")
            print("   🔄 Usando valores por defecto del slot para luz solar...")
            # Establecer valores por defecto del slot
            extracted_values['enable_sun_light'] = True
            extracted_values['light_type'] = 'SUN'
            extracted_values['sun_horizontal_angle'] = 0.0
            extracted_values['sun_vertical_angle'] = 45.0
            extracted_values['sun_intensity'] = 5.0
            extracted_values['light_color'] = (1.0, 0.949999988079071, 0.800000011920929)
            extracted_values['sun_size'] = 0.5450000166893005
            print("   ✅ Valores por defecto de luz solar establecidos")

        # Aplicar los valores al panel
        props = bpy.context.scene.hdri_tester_props

        # Configurar carpeta HDRI por defecto si no está especificada
        if 'skies_dir' in extracted_values:
            props.hdri_folder_path = extracted_values['skies_dir']
        else:
            # Usar carpeta por defecto
            props.hdri_folder_path = r"C:\Users\user\Desktop\Alfred_Animacion\cielos"

        # Configurar valores por defecto para HDRI si no se encontraron en el slot
        # (este slot específico define los HDRI dentro de la función import_sky_hdri_direct)
        props.enable_main_hdri = True
        props.enable_moving_hdri = True

        # Valores por defecto basados en el slot actual
        if 'primary_hdri_file' in extracted_values:
            props.selected_hdri_main = extracted_values['primary_hdri_file']
        else:
            props.selected_hdri_main = "cielo_atardecer_03.exr"  # Valor por defecto del slot

        if 'primary_strength' in extracted_values:
            props.main_hdri_strength = extracted_values['primary_strength']
        else:
            props.main_hdri_strength = 0.31  # Valor por defecto del slot

        if 'primary_rotation' in extracted_values:
            props.main_hdri_rotation = extracted_values['primary_rotation']
        else:
            props.main_hdri_rotation = 0.0  # Valor por defecto del slot

        # Valores secundarios
        if 'secondary_hdri_file' in extracted_values:
            props.selected_hdri_moving = extracted_values['secondary_hdri_file']
        else:
            props.selected_hdri_moving = "cielo_nublado_03.exr"  # Valor por defecto del slot

        if 'secondary_visibility' in extracted_values:
            props.moving_hdri_visibility = extracted_values['secondary_visibility']
        else:
            props.moving_hdri_visibility = 0.80  # Valor por defecto del slot

        if 'secondary_strength' in extracted_values:
            props.moving_hdri_strength = extracted_values['secondary_strength']
        else:
            props.moving_hdri_strength = 0.33  # Valor por defecto del slot

        if 'secondary_speed' in extracted_values:
            props.moving_speed = extracted_values['secondary_speed']
        else:
            props.moving_speed = 0.005  # Valor por defecto del slot

        if 'secondary_initial_rotation' in extracted_values:
            props.moving_initial_rotation = extracted_values['secondary_initial_rotation']
        else:
            props.moving_initial_rotation = 0.0  # Valor por defecto del slot

        # Configuración de luz solar
        if 'enable_sun_light' in extracted_values:
            props.enable_sun_light = extracted_values['enable_sun_light']
        if 'light_type' in extracted_values:
            props.light_type = extracted_values['light_type']
        if 'sun_horizontal_angle' in extracted_values:
            props.sun_horizontal_angle = extracted_values['sun_horizontal_angle']
        if 'sun_vertical_angle' in extracted_values:
            props.sun_vertical_angle = extracted_values['sun_vertical_angle']
        if 'light_distance' in extracted_values:
            props.light_distance = extracted_values['light_distance']
        if 'sun_intensity' in extracted_values:
            props.sun_intensity = extracted_values['sun_intensity']
        if 'light_color' in extracted_values:
            props.light_color = extracted_values['light_color']
        if 'use_color_presets' in extracted_values:
            props.use_color_presets = extracted_values['use_color_presets']
        if 'sun_color_preset' in extracted_values:
            props.sun_color_preset = extracted_values['sun_color_preset']
        if 'sun_size' in extracted_values:
            props.sun_size = extracted_values['sun_size']
        if 'spot_size' in extracted_values:
            props.spot_size = extracted_values['spot_size']
        if 'spot_blend' in extracted_values:
            props.spot_blend = extracted_values['spot_blend']
        if 'area_size_x' in extracted_values:
            props.area_size_x = extracted_values['area_size_x']
        if 'area_size_y' in extracted_values:
            props.area_size_y = extracted_values['area_size_y']
        if 'area_shape' in extracted_values:
            props.area_shape = extracted_values['area_shape']

        # Posición de la luz
        if 'light_position_x' in extracted_values:
            props.light_position_x = extracted_values['light_position_x']
        if 'light_position_y' in extracted_values:
            props.light_position_y = extracted_values['light_position_y']
        if 'light_position_z' in extracted_values:
            props.light_position_z = extracted_values['light_position_z']

        print(f"✅ Configuración completa cargada desde: {os.path.basename(slot_path)}")
        print(f"   🌅 HDRI Principal: {extracted_values.get('primary_hdri_file', 'cielo_atardecer_03.exr (por defecto)')}")
        print(f"   🌪️ HDRI Secundario: {extracted_values.get('secondary_hdri_file', 'cielo_nublado_03.exr (por defecto)')}")

        # Información de luz solar si está disponible
        if 'enable_sun_light' in extracted_values and extracted_values['enable_sun_light']:
            light_type = extracted_values.get('light_type', 'SUN')
            intensity = extracted_values.get('sun_intensity', 5.0)
            print(f"   💡 Luz Solar: Activada (Tipo: {light_type}, Intensidad: {intensity})")
            if 'sun_horizontal_angle' in extracted_values:
                h_angle = extracted_values['sun_horizontal_angle']
                v_angle = extracted_values.get('sun_vertical_angle', 45.0)
                print(f"      📍 Posición: H:{h_angle:.1f}° V:{v_angle:.1f}°")
            print(f"   🔄 Creando objeto luz solar en el outliner...")

            # Crear automáticamente la luz solar si está activada (o por defecto si no se encontraron variables)
            print(f"   🔄 Creando luz solar automáticamente...")
            try:
                # Crear la luz directamente en lugar de usar el operador
                props = bpy.context.scene.hdri_tester_props

                # Buscar luz existente
                light_obj = None
                for obj in bpy.data.objects:
                    if obj.type == 'LIGHT' and obj.name.startswith("HDRI_Light"):
                        light_obj = obj
                        break

                # Si cambia el tipo de luz, eliminar la anterior y crear nueva
                default_light_type = extracted_values.get('light_type', 'SUN')
                if light_obj and light_obj.data.type != default_light_type:
                    bpy.data.objects.remove(light_obj, do_unlink=True)
                    light_obj = None

                # Crear nueva luz si no existe
                if not light_obj:
                    light_data = bpy.data.lights.new(name="HDRI_Light_Data", type=default_light_type)
                    light_obj = bpy.data.objects.new(name="HDRI_Light", object_data=light_data)
                    bpy.context.scene.collection.objects.link(light_obj)
                    print(f"   ✅ Nueva luz solar creada: {light_obj.name}")

                # Configurar propiedades de la luz con valores por defecto del slot
                light_obj.data.energy = extracted_values.get('sun_intensity', 5.0)
                light_obj.data.color = extracted_values.get('light_color', (1.0, 0.95, 0.8))

                if default_light_type == 'SUN':
                    light_obj.data.angle = math.radians(extracted_values.get('sun_size', 0.545))

                # Calcular posición con valores por defecto del slot
                h_rad = math.radians(extracted_values.get('sun_horizontal_angle', 0.0))
                v_rad = math.radians(extracted_values.get('sun_vertical_angle', 45.0))

                if default_light_type == 'SUN':
                    light_obj.rotation_euler[0] = math.radians(90) - v_rad
                    light_obj.rotation_euler[1] = 0
                    light_obj.rotation_euler[2] = h_rad
                    light_obj.location = (0, 0, 0)
                else:
                    distance = extracted_values.get('light_distance', 10.0)
                    x = distance * math.cos(v_rad) * math.cos(h_rad)
                    y = distance * math.cos(v_rad) * math.sin(h_rad)
                    z = distance * math.sin(v_rad)
                    light_obj.location = (x, y, z)

                    direction = (0, 0, 0)
                    rot_quat = (light_obj.location - mathutils.Vector(direction)).to_track_quat('-Z', 'Y')
                    light_obj.rotation_euler = rot_quat.to_euler()

                # Activar/desactivar visibilidad (por defecto activada)
                enable_sun = extracted_values.get('enable_sun_light', True)
                light_obj.hide_viewport = not enable_sun
                light_obj.hide_render = not enable_sun

                print(f"   ✅ Luz solar configurada y visible en el outliner: {light_obj.name}")
                print(f"      📍 Posición: {light_obj.location}")
                print(f"      🎨 Color: {light_obj.data.color}")
                print(f"      💡 Intensidad: {light_obj.data.energy}")
                print(f"      🔆 Tipo: {default_light_type}, Activada: {enable_sun}")

            except Exception as e:
                print(f"   ❌ Error creando luz solar directamente: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"   💡 Luz Solar: Desactivada")

        return True

    except Exception as e:
        print(f"❌ Error cargando configuración del slot: {e}")
        return False

SOLAR_FIELDS = ('solar_duration', 'solar_start', 'solar_full_day', 'solar_repeat',
                'solar_radius', 'solar_size', 'solar_elevation', 'solar_heading',
                'solar_center', 'solar_energy', 'solar_emission', 'solar_color',
                'solar_face_enabled', 'solar_happy_frames', 'solar_sad_frames',
                'solar_rays_enabled', 'solar_rays_count', 'solar_rays_power',
                'solar_rays_length', 'solar_rays_angle', 'solar_rays_density')


def attach_solar_light(sphere, light):
    """One position source: the visible sphere, including manual transforms."""
    for axis in range(3):
        light.driver_remove('location', axis)
    light.parent = sphere
    light.matrix_parent_inverse = mathutils.Matrix.Identity(4)
    light.location = (0, 0, 0)
    light.delta_location = (0, 0, 0)
    light.lock_location = (True, True, True)
    position = light.constraints.get('HDRI_Solar_Center')
    if position is None:
        position = light.constraints.new('COPY_LOCATION')
        position.name = 'HDRI_Solar_Center'
    position.target = sphere
    position.owner_space = 'WORLD'
    position.target_space = 'WORLD'
    position.use_offset = False
    position.influence = 1.0
    position.mute = False
    light.constraints.move(list(light.constraints).index(position), 0)


def attach_all_solar_lights(scene, sphere, sunlight):
    """Include the original HDRI SUN, which predates the animated solar rig."""
    import re
    lights = [sunlight]
    for obj in scene.objects:
        if obj == sunlight or obj.type != 'LIGHT' or obj.data.type != 'SUN':
            continue
        if (obj.get('hdri_solar_role') == 'light' or
                re.fullmatch(r'HDRI_(?:Solar_)?Light(?:\.\d+)?', obj.name)):
            lights.append(obj)
    target = next((obj for obj in scene.objects if obj.get('hdri_solar_role') == 'target'), None)
    for light in lights:
        attach_solar_light(sphere, light)
        if target:
            aim = light.constraints.get('HDRI_Solar_Aim')
            if aim is None:
                aim = light.constraints.new('TRACK_TO')
                aim.name = 'HDRI_Solar_Aim'
            aim.target = target
            aim.track_axis = 'TRACK_NEGATIVE_Z'
            aim.up_axis = 'UP_Y'
    return lights


def build_solar_rays(scene, sphere, sunlight):
    """Real outward spot lights, scattered by a bounded atmosphere following the sun."""
    import bmesh
    p = scene.hdri_tester_props
    attach_all_solar_lights(scene, sphere, sunlight)
    for obj in list(scene.objects):
        if str(obj.get('hdri_solar_role', '')).startswith('ray_'):
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data and not data.users:
                if isinstance(data, bpy.types.Light):
                    bpy.data.lights.remove(data)
                elif isinstance(data, bpy.types.Mesh):
                    bpy.data.meshes.remove(data)
    if not p.solar_rays_enabled:
        return
    for index in range(p.solar_rays_count):
        # Fibonacci distribution emits in every direction, independent of the camera.
        z = 1 - 2 * (index + 0.5) / p.solar_rays_count
        angle = index * math.pi * (3 - math.sqrt(5))
        radius = math.sqrt(1 - z*z)
        direction = mathutils.Vector((radius*math.cos(angle), radius*math.sin(angle), z))
        data = bpy.data.lights.new('HDRI_Solar_Ray', 'SPOT')
        data.color = p.solar_color
        data.spot_size = math.radians(p.solar_rays_angle)
        data.spot_blend = 0.65
        data.shadow_soft_size = 0.05
        data.use_custom_distance = True
        data.cutoff_distance = p.solar_rays_length
        ray = bpy.data.objects.new('HDRI_Solar_Ray', data)
        scene.collection.objects.link(ray)
        ray['hdri_solar_role'] = 'ray_light'
        ray.parent = sphere
        ray.location = direction * 1.02
        ray.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        driver = data.driver_add('energy').driver
        variable = driver.variables.new()
        variable.name = 'sun'
        variable.type = 'SINGLE_PROP'
        variable.targets[0].id_type = 'LIGHT'
        variable.targets[0].id = sunlight.data
        variable.targets[0].data_path = 'energy'
        driver.expression = f'{p.solar_rays_power!r}*min(max(sun/{max(p.solar_energy, 0.0001)!r},0),1)'
    if p.solar_rays_density <= 0:
        return
    mesh = bpy.data.meshes.new('HDRI_Solar_Ray_Atmosphere')
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2)
    bm.to_mesh(mesh)
    bm.free()
    volume = bpy.data.objects.new('HDRI_Solar_Ray_Atmosphere', mesh)
    scene.collection.objects.link(volume)
    volume['hdri_solar_role'] = 'ray_volume'
    volume.parent = sphere
    extent = (p.solar_rays_length + p.solar_size) / p.solar_size
    volume.scale = (extent,) * 3
    volume.display_type = 'WIRE'
    volume.hide_select = True
    mat = next((m for m in bpy.data.materials if m.get('hdri_solar_ray_volume')), None)
    if mat is None:
        mat = bpy.data.materials.new('HDRI_Solar_Ray_Atmosphere')
        mat['hdri_solar_ray_volume'] = True
    elif mat.users:
        mat = mat.copy()
    mesh.materials.append(mat)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    links = mat.node_tree.links
    coord = nodes.new('ShaderNodeTexCoord')
    distance = nodes.new('ShaderNodeVectorMath')
    distance.operation = 'DISTANCE'
    distance.inputs[1].default_value = (0.5, 0.5, 0.5)
    links.new(coord.outputs['Generated'], distance.inputs[0])
    fade = nodes.new('ShaderNodeMapRange')
    fade.inputs['From Min'].default_value = 0.0
    fade.inputs['From Max'].default_value = 0.5
    fade.inputs['To Min'].default_value = p.solar_rays_density
    fade.inputs['To Max'].default_value = 0.0
    fade.clamp = True
    links.new(distance.outputs['Value'], fade.inputs['Value'])
    scatter = nodes.new('ShaderNodeVolumeScatter')
    scatter.inputs['Color'].default_value = (1, 1, 1, 1)
    scatter.inputs['Anisotropy'].default_value = 0.25
    links.new(fade.outputs[0], scatter.inputs['Density'])
    output = nodes.new('ShaderNodeOutputMaterial')
    links.new(scatter.outputs[0], output.inputs['Volume'])


def solar_frame_expression(text):
    """Parse explicit timeline intervals without executing user input."""
    import re
    intervals = []
    for item in text.split(','):
        if not item.strip():
            continue
        match = re.fullmatch(r'\s*(-?\d+)\s*(?:-\s*(-?\d+))?\s*', item)
        if not match:
            raise ValueError('Usa frames o intervalos: 1-80, 150-200')
        start = int(match[1])
        end = int(match[2]) if match[2] is not None else start
        if end < start:
            raise ValueError('El frame final debe ser mayor o igual al inicial')
        intervals.append(f'({start}<=frame<={end})')
    expression = ' or '.join(intervals) or '0'
    if len(expression) > 240:
        raise ValueError('Demasiados intervalos: divide la configuración en menos rangos')
    return expression


def solar_face_texture(expression):
    """Packed RGBA decal, generated locally; no external texture paths required."""
    import numpy as np
    name = 'HDRI_Solar_Face_Texture_' + expression
    image = next((im for im in bpy.data.images
                  if im.get('hdri_solar_texture') == expression), None)
    if image:
        return image
    size = 1024
    axis = (np.arange(size, dtype=np.float32) + 0.5) / size * 2 - 1
    x, y = np.meshgrid(axis, axis)
    pixels = np.zeros((size, size, 4), dtype=np.float32)

    def paint(mask, color):
        pixels[mask, :3] = color
        pixels[mask, 3] = 1.0

    def oval(cx, cy, rx, ry, color):
        paint(((x-cx)/rx)**2 + ((y-cy)/ry)**2 <= 1, color)

    dark = (0.012, 0.002, 0.001)
    for side in (-1, 1):
        cx = side * 0.34
        oval(side*0.51, -0.06, 0.14, 0.105, (1.0, 0.10, 0.008))
        if expression == 'happy':
            t = np.clip((x-cx+0.13)/0.26, 0, 1)
            curve = 0.16 + 0.095*np.sin(np.pi*t)
            paint((np.abs(x-cx) <= 0.145) & (np.abs(y-curve) <= 0.033), dark)
        else:
            oval(cx, 0.13 if expression == 'sad' else 0.16, 0.045, 0.07, dark)
            if expression == 'sad':
                brow = 0.30-side*0.08*(x-cx)/0.13
                paint((np.abs(x-cx) <= 0.13) & (np.abs(y-brow) <= 0.026), dark)
    if expression == 'happy':
        oval(0, -0.29, 0.245, 0.17, dark)
        oval(0, -0.36, 0.12, 0.055, (1.0, 0.025, 0.035))
    elif expression == 'sad':
        curve = -0.37+0.13*np.sin(np.pi*np.clip((x+0.22)/0.44, 0, 1))
        paint((np.abs(x) <= 0.22) & (np.abs(y-curve) <= 0.033), dark)
    else:
        paint((np.abs(x) <= 0.15) & (np.abs(y+0.29) <= 0.025), dark)
    image = bpy.data.images.new(name, width=size, height=size, alpha=True)
    image['hdri_solar_texture'] = expression
    image.colorspace_settings.name = 'Non-Color'
    image.pixels.foreach_set(pixels.ravel())
    image.update()
    image.pack()
    return image


def build_solar_face(scene, sphere, happy, sad):
    """Project the expressions on the visible hemisphere in the shader itself."""
    # Migrate previous geometric faces, including their viewport target.
    for obj in list(scene.objects):
        if str(obj.get('hdri_solar_role', '')).startswith('face_'):
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data and data.users == 0:
                if isinstance(data, bpy.types.Mesh):
                    bpy.data.meshes.remove(data)
                elif isinstance(data, bpy.types.Curve):
                    bpy.data.curves.remove(data)
    material = sphere.active_material
    material.diffuse_color = (*scene.hdri_tester_props.solar_color, 1.0)
    if not scene.hdri_tester_props.solar_face_enabled:
        return
    tree = material.node_tree
    nodes, links = tree.nodes, tree.links
    base = next(n for n in nodes if n.bl_idname == 'ShaderNodeEmission')
    output = next(n for n in nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
    geometry = nodes.new('ShaderNodeNewGeometry')
    transform = nodes.new('ShaderNodeVectorTransform')
    transform.vector_type = 'NORMAL'
    transform.convert_from = 'WORLD'
    transform.convert_to = 'CAMERA'
    links.new(geometry.outputs['Normal'], transform.inputs['Vector'])
    scale = nodes.new('ShaderNodeVectorMath')
    scale.operation = 'SCALE'
    scale.inputs[3].default_value = 0.5
    links.new(transform.outputs['Vector'], scale.inputs[0])
    offset = nodes.new('ShaderNodeVectorMath')
    offset.operation = 'ADD'
    offset.inputs[1].default_value = (0.5, 0.5, 0.0)
    links.new(scale.outputs['Vector'], offset.inputs[0])
    textures = {}
    for state in ('neutral', 'happy', 'sad'):
        tex = nodes.new('ShaderNodeTexImage')
        tex.name = 'Solar_Face_' + state
        tex.label = 'Rostro ' + state
        tex.image = solar_face_texture(state)
        tex.extension = 'EXTEND'
        links.new(offset.outputs['Vector'], tex.inputs['Vector'])
        textures[state] = tex
    color = textures['neutral'].outputs['Color']
    alpha = textures['neutral'].outputs['Alpha']
    for state, expression in (('happy', happy), ('sad', sad)):
        color_mix = nodes.new('ShaderNodeMixRGB')
        color_mix.name = 'Solar_Expression_' + state
        color_mix.inputs[0].driver_add('default_value').driver.expression = expression
        links.new(color, color_mix.inputs[1])
        links.new(textures[state].outputs['Color'], color_mix.inputs[2])
        alpha_mix = nodes.new('ShaderNodeMixRGB')
        alpha_mix.inputs[0].driver_add('default_value').driver.expression = expression
        links.new(alpha, alpha_mix.inputs[1])
        links.new(textures[state].outputs['Alpha'], alpha_mix.inputs[2])
        color, alpha = color_mix.outputs[0], alpha_mix.outputs[0]
    ink = nodes.new('ShaderNodeEmission')
    ink.name = 'Solar_Face_Ink'
    ink.inputs['Strength'].default_value = 1.0
    links.new(color, ink.inputs['Color'])
    mix = nodes.new('ShaderNodeMixShader')
    links.new(alpha, mix.inputs[0])
    links.new(base.outputs[0], mix.inputs[1])
    links.new(ink.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs['Surface'])
    nodes.active = textures['happy']

def solar_object(scene, role, object_type, factory):
    """Own objects per scene; never claim a user's object by its name."""
    for obj in scene.objects:
        if obj.get('hdri_solar_role') == role and obj.type == object_type:
            return obj
    obj = factory()
    obj['hdri_solar_role'] = role
    scene.collection.objects.link(obj)
    return obj


def apply_solar_cycle(context):
    import bmesh
    scene = context.scene
    p = scene.hdri_tester_props
    happy = solar_frame_expression(p.solar_happy_frames)
    sad = solar_frame_expression(p.solar_sad_frames)
    rig = solar_object(scene, 'orbit', 'EMPTY',
                       lambda: bpy.data.objects.new('HDRI_Solar_Orbit', None))
    rig.location = p.solar_center
    rig.rotation_euler = (0, 0, math.radians(p.solar_heading))
    rig.empty_display_size = 2.0
    target = solar_object(scene, 'target', 'EMPTY',
                          lambda: bpy.data.objects.new('HDRI_Solar_Target', None))
    target.parent = rig
    target.location = (0, 0, 0)
    target.hide_render = True

    def make_sphere():
        mesh = bpy.data.meshes.new('HDRI_Solar_Sphere_Mesh')
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1.0)
        bm.to_mesh(mesh)
        bm.free()
        for face in mesh.polygons:
            face.use_smooth = True
        return bpy.data.objects.new('HDRI_Solar_Sphere', mesh)

    sphere = solar_object(scene, 'sphere', 'MESH', make_sphere)
    sphere.parent = rig
    sphere.scale = (p.solar_size,) * 3
    # The SUN supplies illumination; the mesh supplies the visible disc.
    if hasattr(sphere, 'visible_shadow'):
        sphere.visible_shadow = False
    if hasattr(sphere, 'visible_diffuse'):
        sphere.visible_diffuse = False
    if hasattr(sphere, 'visible_glossy'):
        sphere.visible_glossy = False
    material = sphere.active_material
    if not material or not material.get('hdri_solar_material'):
        material = bpy.data.materials.new('HDRI_Solar_Emission')
        material['hdri_solar_material'] = True
        sphere.data.materials.clear()
        sphere.data.materials.append(material)
    material.use_nodes = True
    material.node_tree.nodes.clear()
    emission = material.node_tree.nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value = (*p.solar_color, 1.0)
    emission.inputs['Strength'].default_value = p.solar_emission
    output = material.node_tree.nodes.new('ShaderNodeOutputMaterial')
    material.node_tree.links.new(emission.outputs[0], output.inputs['Surface'])

    light = solar_object(scene, 'light', 'LIGHT', lambda: bpy.data.objects.new(
        'HDRI_Solar_Light', bpy.data.lights.new('HDRI_Solar_Light', 'SUN')))
    attach_solar_light(sphere, light)
    light.data.type = 'SUN'
    light.data.color = p.solar_color
    light.data.angle = math.radians(p.sun_size)
    constraint = light.constraints.get('HDRI_Solar_Aim')
    if not constraint:
        constraint = light.constraints.new('TRACK_TO')
        constraint.name = 'HDRI_Solar_Aim'
    constraint.target = target
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'

    frames = p.solar_duration * scene.render.fps / scene.render.fps_base
    progress = f'((frame-({p.solar_start}))/{frames!r})'
    progress = f'({progress}%1.0)' if p.solar_repeat else f'min(max({progress},0.0),1.0)'
    phase = f'({progress}*{(2 * math.pi if p.solar_full_day else math.pi)!r})'
    elevation = math.radians(p.solar_elevation)
    expressions = (f'{-p.solar_radius!r}*cos({phase})',
                   f'{-p.solar_radius * math.cos(elevation)!r}*sin({phase})',
                   f'{p.solar_radius * math.sin(elevation)!r}*sin({phase})')
    for obj in (sphere, light):
        obj.hide_viewport = False
        obj.hide_render = False
    for axis, expression in enumerate(expressions):
        sphere.driver_add('location', axis).driver.expression = expression
    light.data.driver_add('energy').driver.expression = (
        f'{p.solar_energy!r}*min(max(sin({phase})*10.0,0.0),1.0)')
    build_solar_face(scene, sphere, happy, sad)
    build_solar_rays(scene, sphere, light)
    scene.frame_set(scene.frame_current)
    context.view_layer.update()
    return sphere


class HDRI_OT_solar_cycle(Operator):
    bl_idname = 'hdri.solar_cycle'
    bl_label = 'Crear / actualizar ciclo solar'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            apply_solar_cycle(context)
        except ValueError as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        # Solid mode displays only a flat material color, never the face shader.
        if context.scene.hdri_tester_props.solar_face_enabled and context.screen:
            views = [area for area in context.screen.areas if area.type == 'VIEW_3D']
            area = context.area if context.area and context.area.type == 'VIEW_3D' else (
                max(views, key=lambda item: item.width * item.height) if views else None)
            if area and area.spaces.active.shading.type in {'SOLID', 'WIREFRAME'}:
                area.spaces.active.shading.type = 'MATERIAL'
        self.report({'INFO'}, 'Ciclo actualizado: luz del ciclo y luces SUN HDRI vinculadas al centro de la esfera.')
        return {'FINISHED'}


class HDRI_OT_attach_solar_light(Operator):
    bl_idname = 'hdri.attach_solar_light'
    bl_label = 'Unir luz al centro del sol'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        objects = context.scene.objects
        sphere = next((o for o in objects if o.get('hdri_solar_role') == 'sphere'), None)
        light = next((o for o in objects if o.get('hdri_solar_role') == 'light'), None)
        if sphere is None or light is None:
            self.report({'ERROR'}, 'No se encontró el ciclo solar. Crea el ciclo primero.')
            return {'CANCELLED'}
        attach_all_solar_lights(context.scene, sphere, light)
        context.view_layer.update()
        self.report({'INFO'}, 'Luz vinculada al centro de la esfera. Mueve la esfera o HDRI_Solar_Orbit.')
        return {'FINISHED'}


class HDRI_OT_apply_solar_rays(Operator):
    bl_idname = 'hdri.apply_solar_rays'
    bl_label = 'Aplicar / actualizar rayos del sol'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        sphere = next((o for o in scene.objects if o.get('hdri_solar_role') == 'sphere'), None)
        light = next((o for o in scene.objects if o.get('hdri_solar_role') == 'light'), None)
        if sphere is None or light is None:
            self.report({'ERROR'}, 'Crea primero el ciclo solar.')
            return {'CANCELLED'}
        build_solar_rays(scene, sphere, light)
        scene.frame_set(scene.frame_current)
        self.report({'INFO'}, 'Rayos actualizados. Usa vista Renderizada con luces de escena para ver su iluminación.')
        return {'FINISHED'}


class HDRI_OT_repair_solar_face(Operator):
    bl_idname = 'hdri.repair_solar_face'
    bl_label = 'Aplicar textura al sol existente'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        props = scene.hdri_tester_props
        sphere = next((obj for obj in scene.objects if obj.type == 'MESH' and
                       obj.get('hdri_solar_role') == 'sphere'), None)
        if sphere is None:
            sphere = scene.objects.get('HDRI_Solar_Sphere')
        if sphere is None or sphere.type != 'MESH':
            self.report({'ERROR'}, 'No se encontró HDRI_Solar_Sphere. Crea el ciclo solar primero.')
            return {'CANCELLED'}
        try:
            happy = solar_frame_expression(props.solar_happy_frames)
            sad = solar_frame_expression(props.solar_sad_frames)
        except ValueError as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        props.solar_face_enabled = True
        # Replace all material slots: every face must use the textured material.
        mat = sphere.active_material
        if not mat or not mat.get('hdri_solar_material'):
            mat = bpy.data.materials.new('HDRI_Solar_Emission')
        elif mat.users > 1:
            mat = mat.copy()
        mat['hdri_solar_material'] = True
        mat.use_nodes = True
        mat.node_tree.animation_data_clear()
        mat.node_tree.nodes.clear()
        emission = mat.node_tree.nodes.new('ShaderNodeEmission')
        emission.inputs['Color'].default_value = (*props.solar_color, 1.0)
        emission.inputs['Strength'].default_value = props.solar_emission
        output = mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
        mat.node_tree.links.new(emission.outputs[0], output.inputs['Surface'])
        if sphere.data.users > 1:
            sphere.data = sphere.data.copy()
        sphere.data.materials.clear()
        sphere.data.materials.append(mat)
        for face in sphere.data.polygons:
            face.material_index = 0
        build_solar_face(scene, sphere, happy, sad)
        scene.frame_set(scene.frame_current)
        if sphere.name in context.view_layer.objects:
            for obj in context.selected_objects:
                obj.select_set(False)
            sphere.hide_set(False)
            sphere.hide_viewport = False
            sphere.select_set(True)
            context.view_layer.objects.active = sphere
        if context.screen:
            for area in context.screen.areas:
                if area.type == 'VIEW_3D' and area.spaces.active.shading.type in {'SOLID', 'WIREFRAME'}:
                    area.spaces.active.shading.type = 'MATERIAL'
                elif area.type == 'NODE_EDITOR' and area.spaces.active.tree_type == 'ShaderNodeTree':
                    area.spaces.active.pin = False
                    area.spaces.active.shader_type = 'OBJECT'
        self.report({'INFO'}, 'Texturas aplicadas a HDRI_Solar_Sphere; esfera seleccionada para inspeccionar su material.')
        return {'FINISHED'}


class HDRI_OT_remove_solar_cycle(Operator):
    bl_idname = 'hdri.remove_solar_cycle'
    bl_label = 'Eliminar ciclo solar'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in list(context.scene.objects):
            if obj.get('hdri_solar_role'):
                bpy.data.objects.remove(obj, do_unlink=True)
        return {'FINISHED'}


class HDRI_OT_apply_hdri(Operator):
    """Aplica el sistema de HDRI con capas principal y de movimiento"""
    bl_idname = "hdri.apply_selected"
    bl_label = "Aplicar Sistema HDRI"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.hdri_tester_props

        # Usa directamente la configuración actual del panel (sin sobrescribir con el slot)
        selected_main = props.selected_hdri_main

        if selected_main == "NONE":
            self.report({'ERROR'}, "Debes seleccionar un HDRI principal")
            return {'CANCELLED'}

        hdri_main_path = os.path.join(props.hdri_folder_path, selected_main)

        if not os.path.exists(hdri_main_path):
            self.report({'ERROR'}, f"Archivo HDRI principal no encontrado: {hdri_main_path}")
            return {'CANCELLED'}

        # Obtener o crear el mundo
        world = bpy.context.scene.world
        if not world:
            world = bpy.data.worlds.new("HDRI World")
            bpy.context.scene.world = world

        # Limpiar nodos existentes
        world.use_nodes = True
        nodes = world.node_tree.nodes
        links = world.node_tree.links
        nodes.clear()

        # === OUTPUT ===
        output = nodes.new(type='ShaderNodeOutputWorld')
        output.location = (1800, 0)

        # === MIX SHADER (combina HDRI principal con HDRI en movimiento) ===
        mix_shader = nodes.new(type='ShaderNodeMixShader')
        mix_shader.location = (1200, 100)
        mix_shader.name = "Mix_Main_Moving"

        # Configurar factor de mezcla según capas activas
        if not props.enable_main_hdri and not props.enable_moving_hdri:
            mix_shader.inputs[0].default_value = 0.5
        elif not props.enable_moving_hdri:
            mix_shader.inputs[0].default_value = 1.0
        elif not props.enable_main_hdri:
            mix_shader.inputs[0].default_value = 0.0
        else:
            mix_shader.inputs[0].default_value = 1.0 - props.moving_hdri_visibility

        # === HDRI PRINCIPAL (Capa frontal - estático) ===
        background_main = nodes.new(type='ShaderNodeBackground')
        background_main.location = (1000, 100)
        background_main.name = "Background_Main"
        
        mapping_main = nodes.new(type='ShaderNodeMapping')
        mapping_main.location = (400, 100)
        mapping_main.name = "Mapping_Main"
        
        tex_coord_main = nodes.new(type='ShaderNodeTexCoord')
        tex_coord_main.location = (200, 100)
        
        env_tex_main = nodes.new(type='ShaderNodeTexEnvironment')
        env_tex_main.location = (600, 100)
        env_tex_main.name = "EnvTex_Main"
        
        # Cargar imagen HDRI principal
        if selected_main in bpy.data.images:
            hdri_main_image = bpy.data.images[selected_main]
        else:
            hdri_main_image = bpy.data.images.load(hdri_main_path)
            hdri_main_image.name = selected_main
        
        env_tex_main.image = hdri_main_image
        
        # Conectar HDRI principal
        links.new(tex_coord_main.outputs['Generated'], mapping_main.inputs['Vector'])
        links.new(mapping_main.outputs['Vector'], env_tex_main.inputs['Vector'])
        links.new(env_tex_main.outputs['Color'], background_main.inputs['Color'])
        links.new(background_main.outputs['Background'], mix_shader.inputs[2])
        
        # Configurar HDRI principal
        background_main.inputs['Strength'].default_value = props.main_hdri_strength
        mapping_main.inputs['Rotation'].default_value[2] = math.radians(props.main_hdri_rotation)

        # === HDRI DE MOVIMIENTO (Capa trasera - dinámico) ===
        has_moving_layer = False
        if props.enable_moving_hdri and props.selected_hdri_moving != "NONE":
            selected_moving = props.selected_hdri_moving
            hdri_moving_path = os.path.join(props.hdri_folder_path, selected_moving)
            
            if os.path.exists(hdri_moving_path):
                has_moving_layer = True
                background_moving = nodes.new(type='ShaderNodeBackground')
                background_moving.location = (1000, -100)
                background_moving.name = "Background_Moving"
                
                mapping_moving = nodes.new(type='ShaderNodeMapping')
                mapping_moving.location = (400, -100)
                mapping_moving.name = "Mapping_Moving"
                
                tex_coord_moving = nodes.new(type='ShaderNodeTexCoord')
                tex_coord_moving.location = (200, -100)
                
                env_tex_moving = nodes.new(type='ShaderNodeTexEnvironment')
                env_tex_moving.location = (600, -100)
                env_tex_moving.name = "EnvTex_Moving"
                
                # Cargar imagen HDRI en movimiento
                if selected_moving in bpy.data.images:
                    hdri_moving_image = bpy.data.images[selected_moving]
                else:
                    hdri_moving_image = bpy.data.images.load(hdri_moving_path)
                    hdri_moving_image.name = selected_moving
                
                env_tex_moving.image = hdri_moving_image
                
                # Conectar HDRI en movimiento
                links.new(tex_coord_moving.outputs['Generated'], mapping_moving.inputs['Vector'])
                links.new(mapping_moving.outputs['Vector'], env_tex_moving.inputs['Vector'])
                links.new(env_tex_moving.outputs['Color'], background_moving.inputs['Color'])
                links.new(background_moving.outputs['Background'], mix_shader.inputs[1])
                
                # Configurar HDRI en movimiento
                background_moving.inputs['Strength'].default_value = props.moving_hdri_strength
                mapping_moving.inputs['Rotation'].default_value[2] = math.radians(props.moving_initial_rotation)
                
                # Actualizar factor de mezcla
                mix_shader.inputs[0].default_value = 1.0 - props.moving_hdri_visibility
        
        # Si no hay capa de movimiento, conectar directamente el principal o crear fondo negro
        if not has_moving_layer:
            if props.enable_main_hdri:
                links.new(background_main.outputs['Background'], mix_shader.inputs[1])
            else:
                black_background = nodes.new(type='ShaderNodeBackground')
                black_background.location = (1000, -100)
                black_background.name = "Background_Black"
                black_background.inputs['Color'].default_value = (0, 0, 0, 1)
                black_background.inputs['Strength'].default_value = 0.0
                links.new(black_background.outputs['Background'], mix_shader.inputs[1])
        
        # === INTERRUPTOR MAESTRO DE VISIBILIDAD (ON/OFF) ===
        # Nodo negro usado cuando el HDRI está desactivado
        master_black = nodes.new(type='ShaderNodeBackground')
        master_black.location = (1400, -300)
        master_black.name = "Background_MasterOff"
        master_black.inputs['Color'].default_value = (0, 0, 0, 1)
        master_black.inputs['Strength'].default_value = 0.0

        master_mix = nodes.new(type='ShaderNodeMixShader')
        master_mix.location = (1600, 0)
        master_mix.name = "Master_Visibility_Mix"
        master_mix.inputs[0].default_value = 0.0 if props.hdri_visible else 1.0

        links.new(mix_shader.outputs['Shader'], master_mix.inputs[1])
        links.new(master_black.outputs['Background'], master_mix.inputs[2])

        # Conectar al output a través del interruptor maestro
        links.new(master_mix.outputs['Shader'], output.inputs['Surface'])

        message = f"Sistema HDRI: Principal '{selected_main}'"
        if has_moving_layer:
            message += f" + Movimiento '{selected_moving}'"
        self.report({'INFO'}, message)

        return {'FINISHED'}


class HDRI_OT_toggle_hdri_visibility(Operator):
    """Muestra u oculta el HDRI sin borrar la configuración aplicada"""
    bl_idname = "hdri.toggle_visibility"
    bl_label = "Mostrar/Ocultar HDRI"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.hdri_tester_props
        props.hdri_visible = not props.hdri_visible

        world = context.scene.world
        if not world or not world.use_nodes:
            self.report({'WARNING'}, "No hay sistema HDRI aplicado todavía")
            return {'CANCELLED'}

        master_mix = world.node_tree.nodes.get("Master_Visibility_Mix")
        if master_mix is None:
            self.report({'WARNING'}, "Vuelve a presionar 'Aplicar Sistema HDRI' para habilitar el interruptor")
            return {'CANCELLED'}

        master_mix.inputs[0].default_value = 0.0 if props.hdri_visible else 1.0

        estado = "activado 👁" if props.hdri_visible else "desactivado 🚫"
        self.report({'INFO'}, f"HDRI {estado}")
        return {'FINISHED'}


class HDRI_OT_clear_hdri(Operator):
    """Elimina por completo el sistema HDRI de la escena (nodos de mundo y datos de imagen)"""
    bl_idname = "hdri.clear_hdri"
    bl_label = "Borrar HDRI"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.hdri_tester_props
        world = context.scene.world

        if not world or not world.use_nodes:
            self.report({'WARNING'}, "No hay ningún HDRI aplicado en la escena")
            return {'CANCELLED'}

        # Guardar referencias a las imágenes usadas antes de borrar los nodos
        image_names = set()
        for node in world.node_tree.nodes:
            if node.type == 'TEX_ENVIRONMENT' and node.image:
                image_names.add(node.image.name)

        # Limpiar todos los nodos del árbol de mundo
        world.node_tree.nodes.clear()

        # Reconstruir un fondo negro simple para dejar la escena limpia
        nodes = world.node_tree.nodes
        links = world.node_tree.links
        black_bg = nodes.new(type='ShaderNodeBackground')
        black_bg.inputs['Color'].default_value = (0, 0, 0, 1)
        black_bg.inputs['Strength'].default_value = 0.0
        output = nodes.new(type='ShaderNodeOutputWorld')
        links.new(black_bg.outputs['Background'], output.inputs['Surface'])

        # Eliminar las imágenes HDRI cargadas que ya no se usan (evita basura en memoria)
        removed = 0
        for name in image_names:
            img = bpy.data.images.get(name)
            if img and img.users == 0:
                bpy.data.images.remove(img)
                removed += 1

        # Resetear estado de visibilidad en el panel
        props.hdri_visible = True

        self.report({'INFO'}, f"HDRI eliminado de la escena ({removed} imagen(es) liberada(s))")
        return {'FINISHED'}


class HDRI_OT_create_sun_light(Operator):
    """Crea o actualiza la luz direccional"""
    bl_idname = "hdri.create_sun_light"
    bl_label = "Aplicar Luz"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.hdri_tester_props
        
        # Buscar luz existente
        light_obj = None
        for obj in bpy.data.objects:
            if obj.type == 'LIGHT' and obj.name.startswith("HDRI_Light"):
                light_obj = obj
                break
        
        # Si cambia el tipo de luz, eliminar la anterior y crear nueva
        if light_obj and light_obj.data.type != props.light_type:
            bpy.data.objects.remove(light_obj, do_unlink=True)
            light_obj = None
        
        # Crear nueva luz si no existe
        if not light_obj:
            light_data = bpy.data.lights.new(name="HDRI_Light_Data", type=props.light_type)
            light_obj = bpy.data.objects.new(name="HDRI_Light", object_data=light_data)
            context.scene.collection.objects.link(light_obj)
        
        # === CONFIGURAR COLOR ===
        if props.use_color_presets:
            # Presets de temperatura de color
            color_map = {
                'SUNRISE': (1.0, 0.6, 0.4),      # Naranja cálido
                'MORNING': (1.0, 0.9, 0.7),      # Amarillo suave
                'NOON': (1.0, 1.0, 1.0),         # Blanco neutro
                'AFTERNOON': (1.0, 0.9, 0.6),    # Amarillo cálido
                'SUNSET': (1.0, 0.5, 0.3),       # Naranja intenso
                'OVERCAST': (0.9, 0.95, 1.0),    # Blanco frío
                'MOONLIGHT': (0.7, 0.8, 1.0),    # Azul frío
            }
            light_obj.data.color = color_map[props.sun_color_preset]
        else:
            # Color personalizado RGB
            light_obj.data.color = props.light_color
        
        # === CONFIGURAR INTENSIDAD ===
        light_obj.data.energy = props.sun_intensity
        
        # === CONFIGURAR PROPIEDADES ESPECÍFICAS POR TIPO ===
        if props.light_type == 'SUN':
            light_obj.data.angle = math.radians(props.sun_size)
            
        elif props.light_type == 'SPOT':
            light_obj.data.spot_size = math.radians(props.spot_size)
            light_obj.data.spot_blend = props.spot_blend
            
        elif props.light_type == 'AREA':
            light_obj.data.shape = props.area_shape
            if props.area_shape in ['SQUARE', 'DISK']:
                light_obj.data.size = props.area_size_x
            else:  # RECTANGLE, ELLIPSE
                light_obj.data.size = props.area_size_x
                light_obj.data.size_y = props.area_size_y
        
        # === CALCULAR POSICIÓN Y ROTACIÓN ===
        h_rad = math.radians(props.sun_horizontal_angle)
        v_rad = math.radians(props.sun_vertical_angle)

        # Usar la posición almacenada en lugar de calcularla
        stored_position = (props.light_position_x, props.light_position_y, props.light_position_z)
        light_obj.location = stored_position

        if props.light_type == 'SUN':
            # Sun light: mantener rotación para dirección, pero usar posición almacenada
            light_obj.rotation_euler[0] = math.radians(90) - v_rad  # Pitch
            light_obj.rotation_euler[1] = 0  # Roll
            light_obj.rotation_euler[2] = h_rad  # Yaw
            # La posición ya está configurada arriba con stored_position
        else:
            # Point/Spot/Area: usar posición almacenada + rotación hacia origen
            # Apuntar hacia el origen desde la posición almacenada
            direction = (0, 0, 0)
            rot_quat = (light_obj.location - mathutils.Vector(direction)).to_track_quat('-Z', 'Y')
            light_obj.rotation_euler = rot_quat.to_euler()
        
        # Activar/desactivar
        light_obj.hide_viewport = not props.enable_sun_light
        light_obj.hide_render = not props.enable_sun_light
        
        if props.enable_sun_light:
            light_type_name = {'SUN': 'Solar', 'POINT': 'Punto', 'SPOT': 'Spot', 'AREA': 'Área'}
            self.report({'INFO'}, f"Luz {light_type_name[props.light_type]} aplicada")
        else:
            self.report({'INFO'}, "Luz desactivada")
        
        return {'FINISHED'}


class HDRI_OT_setup_volumetric(Operator):
    """Configura el sistema volumétrico (God Rays)"""
    bl_idname = "hdri.setup_volumetric"
    bl_label = "Aplicar Volumétrico"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.hdri_tester_props
        
        # Buscar o crear cubo volumétrico
        volume_obj = None
        for obj in bpy.data.objects:
            if obj.name == "HDRI_Volume_Cube":
                volume_obj = obj
                break
        
        if props.enable_volumetric:
            # Crear cubo si no existe
            if not volume_obj:
                bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
                volume_obj = context.active_object
                volume_obj.name = "HDRI_Volume_Cube"
            
            # Escalar cubo
            scale = props.volumetric_volume_size
            volume_obj.scale = (scale, scale, scale)
            
            # Crear o obtener material volumétrico
            mat_name = "HDRI_Volumetric_Material"
            if mat_name in bpy.data.materials:
                mat = bpy.data.materials[mat_name]
            else:
                mat = bpy.data.materials.new(name=mat_name)
            
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            nodes.clear()
            
            # === NODOS VOLUMÉTRICOS ===
            output = nodes.new(type='ShaderNodeOutputMaterial')
            output.location = (400, 0)
            
            volume_scatter = nodes.new(type='ShaderNodeVolumeScatter')
            volume_scatter.location = (0, 100)
            volume_scatter.name = "Volume_Scatter"
            
            volume_absorption = nodes.new(type='ShaderNodeVolumeAbsorption')
            volume_absorption.location = (0, -100)
            volume_absorption.name = "Volume_Absorption"
            
            add_shader = nodes.new(type='ShaderNodeAddShader')
            add_shader.location = (200, 0)
            
            # Configurar propiedades
            volume_scatter.inputs['Density'].default_value = props.volumetric_density
            volume_scatter.inputs['Anisotropy'].default_value = props.volumetric_anisotropy
            volume_scatter.inputs['Color'].default_value = (*props.volumetric_scatter_color, 1.0)
            
            volume_absorption.inputs['Density'].default_value = props.volumetric_absorption
            volume_absorption.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
            
            # Emisión si está configurada
            if props.volumetric_emission_strength > 0:
                volume_emission = nodes.new(type='ShaderNodeEmission')
                volume_emission.location = (0, -250)
                volume_emission.inputs['Strength'].default_value = props.volumetric_emission_strength
                volume_emission.inputs['Color'].default_value = (*props.volumetric_scatter_color, 1.0)
                
                add_shader2 = nodes.new(type='ShaderNodeAddShader')
                add_shader2.location = (200, -150)
                
                links.new(volume_scatter.outputs['Volume'], add_shader.inputs[0])
                links.new(volume_absorption.outputs['Volume'], add_shader.inputs[1])
                links.new(add_shader.outputs['Shader'], add_shader2.inputs[0])
                links.new(volume_emission.outputs['Emission'], add_shader2.inputs[1])
                links.new(add_shader2.outputs['Shader'], output.inputs['Volume'])
            else:
                # Sin emisión
                links.new(volume_scatter.outputs['Volume'], add_shader.inputs[0])
                links.new(volume_absorption.outputs['Volume'], add_shader.inputs[1])
                links.new(add_shader.outputs['Shader'], output.inputs['Volume'])
            
            # Asignar material
            if len(volume_obj.data.materials) == 0:
                volume_obj.data.materials.append(mat)
            else:
                volume_obj.data.materials[0] = mat
            
            # Configurar render settings para volumétricos
            context.scene.cycles.volume_max_steps = props.volumetric_steps
            context.scene.cycles.volume_step_rate = props.volumetric_step_size
            
            # Asegurar que Cycles esté activado
            if context.scene.render.engine != 'CYCLES':
                self.report({'WARNING'}, "Cambiando a Cycles - requerido para volumétricos")
                context.scene.render.engine = 'CYCLES'
            
            # Mostrar objeto
            volume_obj.hide_viewport = False
            volume_obj.hide_render = False
            
            # Hacer que no sea seleccionable para no estorbar
            volume_obj.hide_select = True
            
            self.report({'INFO'}, "Sistema volumétrico activado (God Rays)")
        
        else:
            # Desactivar volumétrico
            if volume_obj:
                volume_obj.hide_viewport = True
                volume_obj.hide_render = True
            self.report({'INFO'}, "Sistema volumétrico desactivado")
        
        return {'FINISHED'}


class HDRI_OT_setup_glare(Operator):
    """Configura el sistema de glare (lens flare) en el compositor"""
    bl_idname = "hdri.setup_glare"
    bl_label = "Aplicar Lens Flare"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.hdri_tester_props
        
        # Activar compositor
        context.scene.use_nodes = True
        tree = context.scene.node_tree
        nodes = tree.nodes
        links = tree.links
        
        # Buscar nodos existentes
        render_layers = None
        composite = None
        glare_node = None
        
        for node in nodes:
            if node.type == 'R_LAYERS':
                render_layers = node
            elif node.type == 'COMPOSITE':
                composite = node
            elif node.type == 'GLARE' and node.name == "HDRI_Glare":
                glare_node = node
        
        # Crear nodos básicos si no existen
        if not render_layers:
            render_layers = nodes.new(type='CompositorNodeRLayers')
            render_layers.location = (0, 0)
        
        if not composite:
            composite = nodes.new(type='CompositorNodeComposite')
            composite.location = (600, 0)
        
        # Crear o actualizar nodo Glare
        if not glare_node:
            glare_node = nodes.new(type='CompositorNodeGlare')
            glare_node.location = (300, 0)
            glare_node.name = "HDRI_Glare"
        
        # Configurar glare
        glare_node.glare_type = props.glare_type
        glare_node.threshold = props.glare_threshold
        glare_node.mix = props.glare_mix
        glare_node.quality = 'HIGH'
        glare_node.iterations = props.glare_iterations
        
        # Streaks específicos
        if props.glare_type == 'STREAKS':
            glare_node.streaks = 4
            glare_node.angle_offset = math.radians(45)
        
        # Conectar nodos
        if props.enable_glare:
            # Render Layers -> Glare -> Composite
            links.new(render_layers.outputs['Image'], glare_node.inputs['Image'])
            links.new(glare_node.outputs['Image'], composite.inputs['Image'])
            
            # Escalar intensidad mediante mezcla
            glare_node.mix = props.glare_intensity
            
            self.report({'INFO'}, f"Lens Flare activado: {props.glare_type}")
        else:
            # Bypass: Render Layers -> Composite directo
            links.new(render_layers.outputs['Image'], composite.inputs['Image'])
            self.report({'INFO'}, "Lens Flare desactivado")
        
        return {'FINISHED'}


class HDRI_OT_animate_moving_hdri(Operator):
    """Anima la rotación del HDRI en movimiento"""
    bl_idname = "hdri.animate_moving"
    bl_label = "Animar HDRI de Movimiento"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.hdri_tester_props
        world = context.scene.world
        
        if not world or not world.use_nodes:
            self.report({'ERROR'}, "Primero aplica el sistema HDRI")
            return {'CANCELLED'}
        
        if not props.enable_moving_hdri:
            self.report({'ERROR'}, "Activa el HDRI de movimiento primero")
            return {'CANCELLED'}
        
        # Buscar nodo de mapping del HDRI en movimiento
        mapping_moving = None
        for node in world.node_tree.nodes:
            if node.name == "Mapping_Moving":
                mapping_moving = node
                break
        
        if not mapping_moving:
            self.report({'ERROR'}, "No se encontró el HDRI de movimiento en la escena")
            return {'CANCELLED'}
        
        # Configurar animación
        start_frame = context.scene.frame_start
        end_frame = context.scene.frame_end
        
        # Keyframe inicial
        context.scene.frame_set(start_frame)
        mapping_moving.inputs['Rotation'].default_value[2] = math.radians(props.moving_initial_rotation)
        mapping_moving.inputs['Rotation'].keyframe_insert(data_path="default_value", index=2)
        
        # Keyframe final
        context.scene.frame_set(end_frame)
        total_rotation = props.moving_initial_rotation + ((end_frame - start_frame) * props.moving_speed)
        mapping_moving.inputs['Rotation'].default_value[2] = math.radians(total_rotation)
        mapping_moving.inputs['Rotation'].keyframe_insert(data_path="default_value", index=2)
        
        # Hacer interpolación lineal
        if mapping_moving.inputs['Rotation'].id_data.animation_data:
            for fcurve in mapping_moving.inputs['Rotation'].id_data.animation_data.action.fcurves:
                for keyframe in fcurve.keyframe_points:
                    keyframe.interpolation = 'LINEAR'
        
        context.scene.frame_set(start_frame)
        self.report({'INFO'}, f"Animación configurada: {props.moving_speed}°/frame")
        return {'FINISHED'}


class HDRI_OT_update_settings(Operator):
    """Actualiza la configuración de ambos HDRIs en tiempo real"""
    bl_idname = "hdri.update_settings"
    bl_label = "Actualizar Configuración"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.hdri_tester_props
        world = context.scene.world

        if not world or not world.use_nodes:
            self.report({'ERROR'}, "Primero aplica el sistema HDRI")
            return {'CANCELLED'}

        # Actualizar nodos
        for node in world.node_tree.nodes:
            # HDRI Principal
            if node.name == "Background_Main":
                if not props.enable_main_hdri:
                    node.inputs['Strength'].default_value = 0.0
                else:
                    node.inputs['Strength'].default_value = props.main_hdri_strength
            elif node.name == "Mapping_Main":
                node.inputs['Rotation'].default_value[2] = math.radians(props.main_hdri_rotation)

            # HDRI en Movimiento
            elif node.name == "Background_Moving":
                if not props.enable_moving_hdri:
                    node.inputs['Strength'].default_value = 0.0
                else:
                    node.inputs['Strength'].default_value = props.moving_hdri_strength
            elif node.name == "Mapping_Moving":
                # Solo actualizar si no hay animación activa
                try:
                    if not node.inputs['Rotation'].is_animated:
                        node.inputs['Rotation'].default_value[2] = math.radians(props.moving_initial_rotation)
                except AttributeError:
                    node.inputs['Rotation'].default_value[2] = math.radians(props.moving_initial_rotation)

            # Mix Shader - Control de activación independiente
            elif node.name == "Mix_Main_Moving":
                if not props.enable_moving_hdri:
                    node.inputs[0].default_value = 1.0
                elif not props.enable_main_hdri:
                    node.inputs[0].default_value = 0.0
                else:
                    node.inputs[0].default_value = 1.0 - props.moving_hdri_visibility

        self.report({'INFO'}, "Configuración actualizada")
        return {'FINISHED'}


class HDRI_OT_update_sun_light(Operator):
    """Actualiza la configuración de la luz solar sin recrearla ni cambiar posición"""
    bl_idname = "hdri.update_sun_light"
    bl_label = "Actualizar Luz"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.hdri_tester_props

        # Buscar luz existente
        light_obj = None
        for obj in bpy.data.objects:
            if obj.type == 'LIGHT' and obj.name.startswith("HDRI_Light"):
                light_obj = obj
                break

        if not light_obj:
            self.report({'ERROR'}, "No se encontró la luz HDRI. Aplica el sistema de luz primero.")
            return {'CANCELLED'}

        # === GUARDAR POSICIÓN Y ROTACIÓN ACTUALES ===
        saved_location = light_obj.location.copy()
        saved_rotation = light_obj.rotation_euler.copy()

        # === ACTUALIZAR PROPIEDADES DE POSICIÓN ===
        props.light_position_x = saved_location.x
        props.light_position_y = saved_location.y
        props.light_position_z = saved_location.z

        # === ACTUALIZAR COLOR ===
        if props.use_color_presets:
            # Presets de temperatura de color
            color_map = {
                'SUNRISE': (1.0, 0.6, 0.4),      # Naranja cálido
                'MORNING': (1.0, 0.9, 0.7),      # Amarillo suave
                'NOON': (1.0, 1.0, 1.0),         # Blanco neutro
                'AFTERNOON': (1.0, 0.9, 0.6),    # Amarillo cálido
                'SUNSET': (1.0, 0.5, 0.3),       # Naranja intenso
                'OVERCAST': (0.9, 0.95, 1.0),    # Blanco frío
                'MOONLIGHT': (0.7, 0.8, 1.0),    # Azul frío
            }
            light_obj.data.color = color_map[props.sun_color_preset]
        else:
            # Color personalizado RGB
            light_obj.data.color = props.light_color

        # === ACTUALIZAR INTENSIDAD ===
        light_obj.data.energy = props.sun_intensity

        # === ACTUALIZAR PROPIEDADES ESPECÍFICAS POR TIPO ===
        if light_obj.data.type == 'SUN':
            light_obj.data.angle = math.radians(props.sun_size)

        elif light_obj.data.type == 'SPOT':
            light_obj.data.spot_size = math.radians(props.spot_size)
            light_obj.data.spot_blend = props.spot_blend

        elif light_obj.data.type == 'AREA':
            light_obj.data.shape = props.area_shape
            if props.area_shape in ['SQUARE', 'DISK']:
                light_obj.data.size = props.area_size_x
            else:  # RECTANGLE, ELLIPSE
                light_obj.data.size = props.area_size_x
                light_obj.data.size_y = props.area_size_y

        # === RESTAURAR POSICIÓN Y ROTACIÓN (NO CAMBIAR NUNCA) ===
        light_obj.location = saved_location
        light_obj.rotation_euler = saved_rotation

        # Activar/desactivar
        light_obj.hide_viewport = not props.enable_sun_light
        light_obj.hide_render = not props.enable_sun_light

        light_type_name = {'SUN': 'Solar', 'POINT': 'Punto', 'SPOT': 'Spot', 'AREA': 'Área'}
        self.report({'INFO'}, f"Luz {light_type_name[light_obj.data.type]} actualizada (posición conservada)")

        return {'FINISHED'}


class HDRI_OT_update_glare(Operator):
    """Actualiza la configuración del lens flare sin recrearlo"""
    bl_idname = "hdri.update_glare"
    bl_label = "Actualizar Lens Flare"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.hdri_tester_props

        # Verificar que el compositor esté activo
        if not context.scene.use_nodes:
            self.report({'ERROR'}, "El compositor no está activo")
            return {'CANCELLED'}

        tree = context.scene.node_tree

        # Buscar nodo Glare existente
        glare_node = None
        for node in tree.nodes:
            if node.type == 'GLARE' and node.name == "HDRI_Glare":
                glare_node = node
                break

        if not glare_node:
            self.report({'ERROR'}, "No se encontró el nodo Glare. Aplica el Lens Flare primero.")
            return {'CANCELLED'}

        # Actualizar configuración
        glare_node.glare_type = props.glare_type
        glare_node.threshold = props.glare_threshold
        glare_node.mix = props.glare_mix
        glare_node.quality = 'HIGH'
        glare_node.iterations = props.glare_iterations

        # Streaks específicos
        if props.glare_type == 'STREAKS':
            glare_node.streaks = 4
            glare_node.angle_offset = math.radians(45)

        # Escalar intensidad mediante mezcla
        glare_node.mix = props.glare_intensity

        self.report({'INFO'}, f"Lens Flare actualizado: {props.glare_type}")
        return {'FINISHED'}


class HDRI_OT_update_volumetric(Operator):
    """Actualiza la configuración volumétrica sin recrearla"""
    bl_idname = "hdri.update_volumetric"
    bl_label = "Actualizar Volumétrico"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.hdri_tester_props

        # Buscar cubo volumétrico existente
        volume_obj = None
        for obj in bpy.data.objects:
            if obj.name == "HDRI_Volume_Cube":
                volume_obj = obj
                break

        if not volume_obj:
            self.report({'ERROR'}, "No se encontró el cubo volumétrico. Aplica el sistema volumétrico primero.")
            return {'CANCELLED'}

        # Buscar material volumétrico
        mat = None
        if len(volume_obj.data.materials) > 0:
            mat = volume_obj.data.materials[0]
            if mat.name != "HDRI_Volumetric_Material":
                mat = None

        if not mat:
            self.report({'ERROR'}, "No se encontró el material volumétrico")
            return {'CANCELLED'}

        # Escalar cubo
        scale = props.volumetric_volume_size
        volume_obj.scale = (scale, scale, scale)

        # Actualizar propiedades del material
        nodes = mat.node_tree.nodes

        # Buscar nodos volumétricos
        volume_scatter = None
        volume_absorption = None

        for node in nodes:
            if node.name == "Volume_Scatter":
                volume_scatter = node
            elif node.name == "Volume_Absorption":
                volume_absorption = node

        if volume_scatter:
            volume_scatter.inputs['Density'].default_value = props.volumetric_density
            volume_scatter.inputs['Anisotropy'].default_value = props.volumetric_anisotropy
            volume_scatter.inputs['Color'].default_value = (*props.volumetric_scatter_color, 1.0)

        if volume_absorption:
            volume_absorption.inputs['Density'].default_value = props.volumetric_absorption
            volume_absorption.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)

        # Buscar nodos de emisión si existen
        for node in nodes:
            if node.type == 'ShaderNodeEmission':
                node.inputs['Strength'].default_value = props.volumetric_emission_strength
                node.inputs['Color'].default_value = (*props.volumetric_scatter_color, 1.0)

        # Configurar render settings para volumétricos
        context.scene.cycles.volume_max_steps = props.volumetric_steps
        context.scene.cycles.volume_step_rate = props.volumetric_step_size

        # Mostrar/ocultar objeto
        volume_obj.hide_viewport = not props.enable_volumetric
        volume_obj.hide_render = not props.enable_volumetric

        self.report({'INFO'}, "Sistema volumétrico actualizado")
        return {'FINISHED'}


class HDRI_OT_load_slot_configuration(Operator):
    """Carga automáticamente la configuración del cielo desde un archivo slot"""
    bl_idname = "hdri.load_slot_configuration"
    bl_label = "Cargar Configuración del Slot"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        success = load_slot_sky_configuration()
        if success:
            self.report({'INFO'}, "Configuración del slot cargada exitosamente")
            # Aplicar automáticamente los cambios
            bpy.ops.hdri.apply_selected()
        else:
            self.report({'ERROR'}, "No se pudo cargar la configuración del slot")
        return {'FINISHED'}


class HDRI_OT_export_scene(Operator):
    """Exporta la configuración de escena HDRI a un archivo separado"""
    bl_idname = "hdri.export_scene"
    bl_label = "Exportar escena"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.hdri_tester_props

        # Ruta del archivo de escena con nombre personalizado
        scene_dir = r"C:\Users\user\Desktop\Alfred_Animacion\animacion\Prompt_054\ecena"
        file_name = props.scene_file_name if props.scene_file_name else "scene_hdri_config"
        scene_file_path = os.path.join(scene_dir, f"{file_name}.py")

        # Crear directorio si no existe
        os.makedirs(scene_dir, exist_ok=True)

        try:
            # Extraer valores actuales del panel
            skies_dir = props.hdri_folder_path if props.hdri_folder_path else r"C:\Users\user\Desktop\Alfred_Animacion\cielos"
            skies_dir_escaped = skies_dir.replace('\\', '\\\\')
            primary_hdri_file = props.selected_hdri_main if props.selected_hdri_main != "NONE" else "cielo_atardecer_03.exr"
            primary_strength = props.main_hdri_strength
            primary_rotation = props.main_hdri_rotation
            secondary_hdri_file = props.selected_hdri_moving if props.selected_hdri_moving != "NONE" else "cielo_nublado_03.exr"
            secondary_visibility = props.moving_hdri_visibility
            secondary_strength = props.moving_hdri_strength
            secondary_speed = props.moving_speed
            secondary_initial_rotation = props.moving_initial_rotation

            # Configuración de luz solar
            enable_sun_light = props.enable_sun_light
            light_type = props.light_type
            sun_horizontal_angle = props.sun_horizontal_angle
            sun_vertical_angle = props.sun_vertical_angle
            light_distance = props.light_distance
            sun_intensity = props.sun_intensity
            light_color = tuple(props.light_color)  # Convertir FloatVector a tupla
            use_color_presets = props.use_color_presets
            sun_color_preset = props.sun_color_preset
            sun_size = props.sun_size
            spot_size = props.spot_size
            spot_blend = props.spot_blend
            area_size_x = props.area_size_x
            area_size_y = props.area_size_y
            area_shape = props.area_shape

            # Posición actual de la luz
            light_position_x = props.light_position_x
            light_position_y = props.light_position_y
            light_position_z = props.light_position_z

            # Intentar obtener la posición de la luz existente en la escena
            try:
                for obj in bpy.data.objects:
                    if obj.type == 'LIGHT' and obj.name.startswith("HDRI_Light"):
                        light_position_x = obj.location.x
                        light_position_y = obj.location.y
                        light_position_z = obj.location.z
                        print(f"   📍 Posición actual de la luz capturada: ({light_position_x:.3f}, {light_position_y:.3f}, {light_position_z:.3f})")
                        break
            except:
                print(f"   ⚠️ No se pudo capturar posición de luz existente, usando valores del panel")

            # Configuración volumétrica
            enable_volumetric = props.enable_volumetric
            volumetric_density = props.volumetric_density
            volumetric_anisotropy = props.volumetric_anisotropy
            volumetric_scatter_color = tuple(props.volumetric_scatter_color)
            volumetric_absorption = props.volumetric_absorption
            volumetric_emission_strength = props.volumetric_emission_strength
            volumetric_volume_size = props.volumetric_volume_size
            volumetric_steps = props.volumetric_steps
            volumetric_step_size = props.volumetric_step_size

            # Configuración de glare
            enable_glare = props.enable_glare
            glare_type = props.glare_type
            glare_threshold = props.glare_threshold
            glare_intensity = props.glare_intensity
            glare_iterations = props.glare_iterations
            glare_mix = props.glare_mix

            # Crear contenido del archivo de escena
            scene_content = f'''# Archivo de configuración de escena HDRI
# Generado automáticamente por HDRI Tester Pro
# Fecha: {context.scene.render.datetime if hasattr(context.scene.render, 'datetime') else 'N/A'}

# ============================================
# CONFIGURACIÓN HDRI DE ESCENA
# ============================================

# Carpeta de archivos HDRI
skies_dir = r"{skies_dir_escaped}"

# Configuración HDRI Principal (Estático)
primary_hdri_file = "{primary_hdri_file}"
primary_strength = {primary_strength:.2f}
primary_rotation = {primary_rotation}

# Configuración HDRI Secundario (Dinámico)
secondary_hdri_file = "{secondary_hdri_file}"
secondary_visibility = {secondary_visibility:.2f}
secondary_strength = {secondary_strength:.2f}
secondary_speed = {secondary_speed:.3f}
secondary_initial_rotation = {secondary_initial_rotation}

# ============================================
# CONFIGURACIÓN DE LUZ SOLAR
# ============================================

enable_sun_light = {str(enable_sun_light)}
light_type = "{light_type}"
sun_horizontal_angle = {sun_horizontal_angle}
sun_vertical_angle = {sun_vertical_angle}
light_distance = {light_distance}
sun_intensity = {sun_intensity}
light_color = {light_color}
use_color_presets = {str(use_color_presets)}
sun_color_preset = "{sun_color_preset}"
sun_size = {sun_size}
spot_size = {spot_size}
spot_blend = {spot_blend}
area_size_x = {area_size_x}
area_size_y = {area_size_y}
area_shape = "{area_shape}"

# Posición de la luz en el espacio 3D
light_position_x = {light_position_x}
light_position_y = {light_position_y}
light_position_z = {light_position_z}

# ============================================
# CONFIGURACIÓN VOLUMÉTRICA (GOD RAYS)
# ============================================

enable_volumetric = {str(enable_volumetric)}
volumetric_density = {volumetric_density}
volumetric_anisotropy = {volumetric_anisotropy}
volumetric_scatter_color = {volumetric_scatter_color}
volumetric_absorption = {volumetric_absorption}
volumetric_emission_strength = {volumetric_emission_strength}
volumetric_volume_size = {volumetric_volume_size}
volumetric_steps = {volumetric_steps}
volumetric_step_size = {volumetric_step_size}

# ============================================
# CONFIGURACIÓN DE GLARE (LENS FLARE)
# ============================================

enable_glare = {str(enable_glare)}
glare_type = "{glare_type}"
glare_threshold = {glare_threshold}
glare_intensity = {glare_intensity}
glare_iterations = {glare_iterations}
glare_mix = {glare_mix}

# ============================================
# CONTROL DE CAPAS
# ============================================

enable_main_hdri = True
enable_moving_hdri = True

print("✅ Configuración de escena HDRI cargada exitosamente")
'''

            import json
            solar_config = {key: (list(getattr(props, key)) if key in
                            ('solar_center', 'solar_color') else getattr(props, key))
                            for key in SOLAR_FIELDS}
            solar_config['active'] = any(obj.get('hdri_solar_role') == 'orbit' for obj in context.scene.objects)
            scene_content += '\n# HDRI_SOLAR_CONFIG: ' + json.dumps(solar_config) + '\n'
            # Escribir el archivo de escena
            with open(scene_file_path, 'w', encoding='utf-8') as f:
                f.write(scene_content)

            self.report({'INFO'}, f"Escena exportada a {os.path.basename(scene_file_path)}")
            print(f"✅ CONFIGURACIÓN DE ESCENA EXPORTADA:")
            print(f"   📁 Archivo: {scene_file_path}")
            print(f"   📝 Nombre: {file_name}.py")
            print(f"   🌅 HDRI Principal: {primary_hdri_file} (Intensidad: {primary_strength:.2f}, Rotación: {primary_rotation}°)")
            print(f"   🌪️ HDRI Secundario: {secondary_hdri_file} (Visibilidad: {secondary_visibility:.2f}, Intensidad: {secondary_strength:.2f})")
            print(f"   💡 Luz Solar: {'Activada' if enable_sun_light else 'Desactivada'} (Tipo: {light_type}, Intensidad: {sun_intensity})")
            print(f"   🌫️ Volumétrico: {'Activado' if enable_volumetric else 'Desactivado'}")
            print(f"   ✨ Lens Flare: {'Activado' if enable_glare else 'Desactivado'}")

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error exportando escena: {str(e)}")
            print(f"❌ Error exportando escena: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class HDRI_OT_import_scene(Operator):
    """Importa la configuración de escena HDRI desde un archivo separado"""
    bl_idname = "hdri.import_scene"
    bl_label = "Importar escena"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.hdri_tester_props

        # Ruta del archivo de escena con nombre personalizado
        scene_dir = r"C:\Users\user\Desktop\Alfred_Animacion\animacion\Prompt_054\ecena"
        file_name = props.scene_file_name if props.scene_file_name else "scene_hdri_config"
        scene_file_path = os.path.join(scene_dir, f"{file_name}.py")

        if not os.path.exists(scene_file_path):
            self.report({'ERROR'}, "No se encontró el archivo de escena scene_hdri_config.py")
            return {'CANCELLED'}

        try:
            # Leer el contenido del archivo de escena
            with open(scene_file_path, 'r', encoding='utf-8') as f:
                scene_content = f.read()

            # Usar regex para extraer valores (más confiable que exec)
            import re

            # Patrones para extraer diferentes tipos de valores
            patterns = {
                # Strings con comillas
                'skies_dir': r'skies_dir\s*=\s*r?"([^"]*)"',
                'primary_hdri_file': r'primary_hdri_file\s*=\s*"([^"]*)"',
                'secondary_hdri_file': r'secondary_hdri_file\s*=\s*"([^"]*)"',
                'light_type': r'light_type\s*=\s*"([^"]*)"',
                'sun_color_preset': r'sun_color_preset\s*=\s*"([^"]*)"',
                'area_shape': r'area_shape\s*=\s*"([^"]*)"',
                'glare_type': r'glare_type\s*=\s*"([^"]*)"',


                # Números (float/int)
                'primary_strength': r'primary_strength\s*=\s*([\d.]+)',
                'primary_rotation': r'primary_rotation\s*=\s*([\d.]+)',
                'secondary_visibility': r'secondary_visibility\s*=\s*([\d.]+)',
                'secondary_strength': r'secondary_strength\s*=\s*([\d.]+)',
                'secondary_speed': r'secondary_speed\s*=\s*([\d.]+)',
                'secondary_initial_rotation': r'secondary_initial_rotation\s*=\s*([\d.]+)',
                'sun_horizontal_angle': r'sun_horizontal_angle\s*=\s*([\d.]+)',
                'sun_vertical_angle': r'sun_vertical_angle\s*=\s*([\d.]+)',
                'light_distance': r'light_distance\s*=\s*([\d.]+)',
                'sun_intensity': r'sun_intensity\s*=\s*([\d.]+)',
                'sun_size': r'sun_size\s*=\s*([\d.]+)',
                'spot_size': r'spot_size\s*=\s*([\d.]+)',
                'spot_blend': r'spot_blend\s*=\s*([\d.]+)',
                'area_size_x': r'area_size_x\s*=\s*([\d.]+)',
                'area_size_y': r'area_size_y\s*=\s*([\d.]+)',
                'volumetric_density': r'volumetric_density\s*=\s*([\d.]+)',
                'volumetric_anisotropy': r'volumetric_anisotropy\s*=\s*([\d.]+)',
                'volumetric_absorption': r'volumetric_absorption\s*=\s*([\d.]+)',
                'volumetric_emission_strength': r'volumetric_emission_strength\s*=\s*([\d.]+)',
                'volumetric_volume_size': r'volumetric_volume_size\s*=\s*([\d.]+)',
                'volumetric_steps': r'volumetric_steps\s*=\s*([\d.]+)',
                'volumetric_step_size': r'volumetric_step_size\s*=\s*([\d.]+)',
                'glare_threshold': r'glare_threshold\s*=\s*([\d.]+)',
                'glare_intensity': r'glare_intensity\s*=\s*([\d.]+)',
                'glare_iterations': r'glare_iterations\s*=\s*([\d.]+)',
                'glare_mix': r'glare_mix\s*=\s*([\d.]+)',
                'light_position_x': r'light_position_x\s*=\s*([-\d.]+)',
                'light_position_y': r'light_position_y\s*=\s*([-\d.]+)',
                'light_position_z': r'light_position_z\s*=\s*([-\d.]+)',

                # Booleanos
                'enable_sun_light': r'enable_sun_light\s*=\s*(True|False)',
                'use_color_presets': r'use_color_presets\s*=\s*(True|False)',
                'enable_volumetric': r'enable_volumetric\s*=\s*(True|False)',
                'enable_glare': r'enable_glare\s*=\s*(True|False)',
                'enable_main_hdri': r'enable_main_hdri\s*=\s*(True|False)',
                'enable_moving_hdri': r'enable_moving_hdri\s*=\s*(True|False)',

                # Tuplas (colores)
                'light_color': r'light_color\s*=\s*\(([^)]+)\)',
                'volumetric_scatter_color': r'volumetric_scatter_color\s*=\s*\(([^)]+)\)',
            }

            extracted_values = {}
            for key, pattern in patterns.items():
                match = re.search(pattern, scene_content)
                if match:
                    value = match.group(1)
                    # Convertir a tipo apropiado
                    if key in ['volumetric_steps', 'glare_iterations']:
                        # Propiedades que deben ser int
                        extracted_values[key] = int(float(value))
                    elif key in ['primary_strength', 'primary_rotation', 'secondary_visibility',
                              'secondary_strength', 'secondary_speed', 'secondary_initial_rotation',
                              'sun_horizontal_angle', 'sun_vertical_angle', 'light_distance',
                              'sun_intensity', 'sun_size', 'spot_size', 'spot_blend',
                              'area_size_x', 'area_size_y', 'volumetric_density', 'volumetric_anisotropy',
                              'volumetric_absorption', 'volumetric_emission_strength', 'volumetric_volume_size',
                              'volumetric_step_size', 'glare_threshold', 'glare_intensity', 'glare_mix']:
                        # Propiedades que deben ser float
                        extracted_values[key] = float(value)
                    elif key in ['enable_sun_light', 'use_color_presets', 'enable_volumetric',
                                'enable_glare', 'enable_main_hdri', 'enable_moving_hdri']:
                        extracted_values[key] = value == 'True'
                    elif key in ['light_color', 'volumetric_scatter_color']:
                        # Convertir string de tupla a tupla real
                        extracted_values[key] = tuple(float(x.strip()) for x in value.split(','))
                    else:
                        extracted_values[key] = value

            # Debug: mostrar valores extraídos
            print(f"🔍 Extrayendo valores del archivo de escena...")
            print(f"   📊 Total de valores encontrados: {len(extracted_values)}")

            # Aplicar los valores extraídos al panel
            if 'skies_dir' in extracted_values:
                props.hdri_folder_path = extracted_values['skies_dir']
                print(f"   ✅ Carpeta HDRI: {extracted_values['skies_dir']}")

            if 'primary_hdri_file' in extracted_values:
                props.selected_hdri_main = extracted_values['primary_hdri_file']
            if 'primary_strength' in extracted_values:
                props.main_hdri_strength = extracted_values['primary_strength']
            if 'primary_rotation' in extracted_values:
                props.main_hdri_rotation = extracted_values['primary_rotation']

            if 'secondary_hdri_file' in extracted_values:
                props.selected_hdri_moving = extracted_values['secondary_hdri_file']
            if 'secondary_visibility' in extracted_values:
                props.moving_hdri_visibility = extracted_values['secondary_visibility']
            if 'secondary_strength' in extracted_values:
                props.moving_hdri_strength = extracted_values['secondary_strength']
            if 'secondary_speed' in extracted_values:
                props.moving_speed = extracted_values['secondary_speed']
            if 'secondary_initial_rotation' in extracted_values:
                props.moving_initial_rotation = extracted_values['secondary_initial_rotation']

            # Configuración de luz solar
            if 'enable_sun_light' in extracted_values:
                props.enable_sun_light = extracted_values['enable_sun_light']
            if 'light_type' in extracted_values:
                props.light_type = extracted_values['light_type']
            if 'sun_horizontal_angle' in extracted_values:
                props.sun_horizontal_angle = extracted_values['sun_horizontal_angle']
            if 'sun_vertical_angle' in extracted_values:
                props.sun_vertical_angle = extracted_values['sun_vertical_angle']
            if 'light_distance' in extracted_values:
                props.light_distance = extracted_values['light_distance']
            if 'sun_intensity' in extracted_values:
                props.sun_intensity = extracted_values['sun_intensity']
            if 'light_color' in extracted_values:
                props.light_color = extracted_values['light_color']
            if 'use_color_presets' in extracted_values:
                props.use_color_presets = extracted_values['use_color_presets']
            if 'sun_color_preset' in extracted_values:
                props.sun_color_preset = extracted_values['sun_color_preset']
            if 'sun_size' in extracted_values:
                props.sun_size = extracted_values['sun_size']
            if 'spot_size' in extracted_values:
                props.spot_size = extracted_values['spot_size']
            if 'spot_blend' in extracted_values:
                props.spot_blend = extracted_values['spot_blend']
            if 'area_size_x' in extracted_values:
                props.area_size_x = extracted_values['area_size_x']
            if 'area_size_y' in extracted_values:
                props.area_size_y = extracted_values['area_size_y']
            if 'area_shape' in extracted_values:
                props.area_shape = extracted_values['area_shape']

            # Configuración volumétrica
            if 'enable_volumetric' in extracted_values:
                props.enable_volumetric = extracted_values['enable_volumetric']
            if 'volumetric_density' in extracted_values:
                props.volumetric_density = extracted_values['volumetric_density']
            if 'volumetric_anisotropy' in extracted_values:
                props.volumetric_anisotropy = extracted_values['volumetric_anisotropy']
            if 'volumetric_scatter_color' in extracted_values:
                props.volumetric_scatter_color = extracted_values['volumetric_scatter_color']
            if 'volumetric_absorption' in extracted_values:
                props.volumetric_absorption = extracted_values['volumetric_absorption']
            if 'volumetric_emission_strength' in extracted_values:
                props.volumetric_emission_strength = extracted_values['volumetric_emission_strength']
            if 'volumetric_volume_size' in extracted_values:
                props.volumetric_volume_size = extracted_values['volumetric_volume_size']
            if 'volumetric_steps' in extracted_values:
                props.volumetric_steps = extracted_values['volumetric_steps']
            if 'volumetric_step_size' in extracted_values:
                props.volumetric_step_size = extracted_values['volumetric_step_size']

            # Configuración de glare
            if 'enable_glare' in extracted_values:
                props.enable_glare = extracted_values['enable_glare']
            if 'glare_type' in extracted_values:
                props.glare_type = extracted_values['glare_type']
            if 'glare_threshold' in extracted_values:
                props.glare_threshold = extracted_values['glare_threshold']
            if 'glare_intensity' in extracted_values:
                props.glare_intensity = extracted_values['glare_intensity']
            if 'glare_iterations' in extracted_values:
                props.glare_iterations = extracted_values['glare_iterations']
            if 'glare_mix' in extracted_values:
                props.glare_mix = extracted_values['glare_mix']

            # Control de capas
            if 'enable_main_hdri' in extracted_values:
                props.enable_main_hdri = extracted_values['enable_main_hdri']
            if 'enable_moving_hdri' in extracted_values:
                props.enable_moving_hdri = extracted_values['enable_moving_hdri']

            # ============================================
            # APLICAR LA CONFIGURACIÓN IMPORTADA A LA ESCENA
            # ============================================

            print(f"🔄 Aplicando configuración importada a la escena...")

            # 1. Aplicar sistema HDRI
            try:
                bpy.ops.hdri.apply_selected()
                print(f"   ✅ Sistema HDRI aplicado")
            except Exception as e:
                print(f"   ⚠️ Error aplicando HDRI: {e}")

            # 2. Aplicar luz solar si está activada
            if props.enable_sun_light:
                try:
                    bpy.ops.hdri.create_sun_light()
                    print(f"   ✅ Luz solar aplicada")
                except Exception as e:
                    print(f"   ⚠️ Error aplicando luz solar: {e}")

            # 3. Aplicar sistema volumétrico si está activado
            if props.enable_volumetric:
                try:
                    bpy.ops.hdri.setup_volumetric()
                    print(f"   ✅ Sistema volumétrico aplicado")
                except Exception as e:
                    print(f"   ⚠️ Error aplicando volumétrico: {e}")

            # 4. Aplicar lens flare si está activado
            if props.enable_glare:
                try:
                    bpy.ops.hdri.setup_glare()
                    print(f"   ✅ Lens Flare aplicado")
                except Exception as e:
                    print(f"   ⚠️ Error aplicando lens flare: {e}")

            # ============================================
            # APLICAR POSICIÓN DE LUZ AL FINAL (DESPUÉS DE TODO LO DEMÁS)
            # ============================================

            # Buscar la luz creada y aplicar la posición almacenada
            if 'light_position_x' in extracted_values and 'light_position_y' in extracted_values and 'light_position_z' in extracted_values:
                try:
                    light_obj = None
                    for obj in bpy.data.objects:
                        if obj.type == 'LIGHT' and obj.name.startswith("HDRI_Light"):
                            light_obj = obj
                            break

                    if light_obj:
                        stored_pos = (
                            float(extracted_values['light_position_x']),
                            float(extracted_values['light_position_y']),
                            float(extracted_values['light_position_z'])
                        )
                        light_obj.location = stored_pos
                        print(f"   ✅ Posición de luz restaurada: {stored_pos}")
                    else:
                        print(f"   ⚠️ No se encontró luz HDRI para aplicar posición")
                except Exception as e:
                    print(f"   ❌ Error aplicando posición de luz: {e}")

            import json
            for line in scene_content.splitlines():
                if line.startswith('# HDRI_SOLAR_CONFIG: '):
                    solar_config = json.loads(line.split(': ', 1)[1])
                    for key in SOLAR_FIELDS:
                        if key in solar_config:
                            setattr(props, key, solar_config[key])
                    if solar_config.get('active'):
                        apply_solar_cycle(context)
                    else:
                        bpy.ops.hdri.remove_solar_cycle()
                    break
            print(f"🎬 Configuración de escena completamente aplicada")

            self.report({'INFO'}, f"Escena importada y aplicada desde {os.path.basename(scene_file_path)}")
            print(f"✅ CONFIGURACIÓN DE ESCENA IMPORTADA Y APLICADA:")
            print(f"   📁 Archivo: {scene_file_path}")
            print(f"   📝 Nombre: {file_name}.py")
            print(f"    Valores importados: {len(extracted_values)}")
            print(f"   🌅 HDRI Principal: {props.selected_hdri_main}")
            print(f"   🌪️ HDRI Secundario: {props.selected_hdri_moving}")
            print(f"   💡 Luz Solar: {'Activada' if props.enable_sun_light else 'Desactivada'}")
            print(f"   🌫️ Volumétrico: {'Activado' if props.enable_volumetric else 'Desactivado'}")
            print(f"   ✨ Lens Flare: {'Activado' if props.enable_glare else 'Desactivado'}")

            # Debug: mostrar valores críticos
            if props.enable_sun_light:
                print(f"      📍 Ángulos: H={props.sun_horizontal_angle:.1f}° V={props.sun_vertical_angle:.1f}°")
                print(f"      🎨 Color: {props.light_color}")
                print(f"      💡 Intensidad: {props.sun_intensity}")
                # Mostrar posición final de la luz
                light_obj = None
                for obj in bpy.data.objects:
                    if obj.type == 'LIGHT' and obj.name.startswith("HDRI_Light"):
                        light_obj = obj
                        break
                if light_obj:
                    print(f"      📍 Posición final: {light_obj.location}")
            if props.enable_volumetric:
                print(f"      🌫️ Densidad: {props.volumetric_density:.3f}")
                print(f"      📏 Tamaño volumen: {props.volumetric_volume_size:.1f}")

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error importando escena: {str(e)}")
            print(f"❌ Error importando escena: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class HDRI_PT_tester_panel(Panel):
    """Panel principal para HDRI"""
    bl_label = "HDRI Tester Pro"
    bl_idname = "HDRI_PT_tester_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'HDRI Tester'

    def draw(self, context):
        layout = self.layout
        props = context.scene.hdri_tester_props

        # Título
        box = layout.box()
        box.label(text="Sistema HDRI con Capas + Luz Solar", icon='WORLD')

        # Selector de carpeta
        box = layout.box()
        box.label(text="Carpeta HDRI:", icon='FILE_FOLDER')
        box.prop(props, "hdri_folder_path", text="")

        # Información de archivos
        hdri_files = get_hdri_files(context)
        box = layout.box()
        box.label(text=f"HDRI encontrados: {len(hdri_files)}", icon='FILE_IMAGE')

        box = layout.box()
        box.label(text="Ciclo solar: Este → Sur → Oeste", icon='LIGHT_SUN')
        box.label(text="Este = -X; Sur = -Y; Oeste = +X")
        for key in SOLAR_FIELDS:
            box.prop(props, key)
        box.label(text="Duración: amanecer a ocaso, o día + noche.")
        box.label(text="Cara: intervalos inclusivos, ej. 1-80, 150-200.")
        box.label(text="Fuera de rangos: neutral. Solapamiento: triste.")
        box.label(text="Rostros integrados en la textura del sol (Material o Renderizado).")
        solar_end = props.solar_start + round(props.solar_duration * context.scene.render.fps / context.scene.render.fps_base)
        box.label(text=f"Fin del primer ciclo: frame {solar_end}")
        if context.scene.frame_end < solar_end:
            box.label(text="Amplía el fin de la línea de tiempo para ver el ciclo completo.", icon='INFO')
        box.label(text="La cámara debe tener alcance de recorte suficiente para ver la esfera.")
        box.label(text="Aplica de nuevo después de cambiar valores o FPS.")
        box.label(text="La luz solar manual y el HDRI siguen siendo independientes.")
        box.operator('hdri.solar_cycle', icon='PLAY')
        box.operator('hdri.repair_solar_face', icon='MATERIAL')
        box.operator('hdri.apply_solar_rays', icon='LIGHT_SPOT')
        box.operator('hdri.attach_solar_light', icon='CONSTRAINT')
        box.label(text="Rayos: usa vista Renderizada. Densidad 0 = sin haces visibles.")
        box.operator('hdri.remove_solar_cycle', icon='TRASH')

        # === CONTROLES DE ACTIVACIÓN INDEPENDIENTE ===
        layout.separator()
        box = layout.box()
        box.label(text="Control de Capas:", icon='HIDE_OFF')
        col = box.column(align=True)
        col.prop(props, "enable_main_hdri", text="HDRI Principal")
        col.prop(props, "enable_moving_hdri", text="HDRI Movimiento")

        # === CONTROLES HDRI (SIEMPRE VISIBLES) ===
        layout.separator()
        box = layout.box()
        box.label(text="HDRI Principal (Cielo Estático):", icon='LIGHTPROBE_VOLUME')
        if hdri_files:
            box.prop(props, "selected_hdri_main", text="")
        else:
            box.label(text="Configure carpeta HDRI arriba", icon='INFO')

        col = box.column(align=True)
        col.prop(props, "main_hdri_strength", slider=True)
        col.prop(props, "main_hdri_rotation", slider=True)

        # === HDRI DE MOVIMIENTO ===
        layout.separator()
        box = layout.box()
        box.label(text="HDRI de Movimiento (Nubes Dinámicas):", icon='FORCE_VORTEX')

        if props.enable_moving_hdri:
            if hdri_files:
                box.prop(props, "selected_hdri_moving", text="")
            else:
                box.label(text="Configure carpeta HDRI arriba", icon='INFO')

            col = box.column(align=True)
            col.prop(props, "moving_hdri_visibility", slider=True)
            col.prop(props, "moving_hdri_strength", slider=True)
            col.prop(props, "moving_speed", slider=True)
            col.prop(props, "moving_initial_rotation", slider=True)

            # Botón de animación
            row = box.row()
            row.scale_y = 1.3
            row.operator("hdri.animate_moving", text="Generar Animación", icon='PREVIEW_RANGE')
        else:
            box.label(text="Desactivado - Activa arriba", icon='INFO')

        # === SISTEMA DE LUZ SOLAR ===
        layout.separator()
        box = layout.box()
        row = box.row()
        row.prop(props, "enable_sun_light", text="", icon='LIGHT_SUN')
        row.label(text="💡 Sistema de Iluminación Direccional")

        if props.enable_sun_light:
            # Tipo de luz
            col = box.column(align=True)
            col.label(text="Tipo de Luz:", icon='LIGHT')
            col.prop(props, "light_type", text="")

            col.separator()

            # Posición
            col.label(text="Posición:", icon='ORIENTATION_GIMBAL')
            col.prop(props, "sun_horizontal_angle", slider=True)
            col.prop(props, "sun_vertical_angle", slider=True)

            # Distancia (solo para Point, Spot, Area)
            if props.light_type != 'SUN':
                col.prop(props, "light_distance", slider=True)

            col.separator()

            # Color
            col.label(text="Color:", icon='COLOR')
            col.prop(props, "use_color_presets", text="Usar Presets")

            if props.use_color_presets:
                col.prop(props, "sun_color_preset", text="")
            else:
                col.prop(props, "light_color", text="")

            col.separator()

            # Posición de la luz
            col.label(text="Posición de la Luz:", icon='OBJECT_ORIGIN')
            col.prop(props, "light_position_x", text="X")
            col.prop(props, "light_position_y", text="Y")
            col.prop(props, "light_position_z", text="Z")

            col.separator()

            # Intensidad
            col.label(text="Intensidad:", icon='LIGHT_SUN')
            col.prop(props, "sun_intensity", slider=True)

            col.separator()

            # Propiedades específicas por tipo
            if props.light_type == 'SUN':
                col.label(text="Propiedades Sol:", icon='LIGHT_SUN')
                col.prop(props, "sun_size", slider=True)

            elif props.light_type == 'SPOT':
                col.label(text="Propiedades Spot:", icon='LIGHT_SPOT')
                col.prop(props, "spot_size", slider=True)
                col.prop(props, "spot_blend", slider=True)

            elif props.light_type == 'AREA':
                col.label(text="Propiedades Área:", icon='LIGHT_AREA')
                col.prop(props, "area_shape", text="")
                if props.area_shape in ['SQUARE', 'DISK']:
                    col.prop(props, "area_size_x", text="Tamaño")
                else:
                    col.prop(props, "area_size_x", text="Ancho")
                    col.prop(props, "area_size_y", text="Alto")

            # Botones aplicar y actualizar
            row = box.row()
            row.scale_y = 1.3
            row.operator("hdri.create_sun_light", text="Aplicar Luz", icon='LIGHT')

            row = box.row()
            row.scale_y = 1.1
            row.operator("hdri.update_sun_light", text="🔄 Actualizar Luz", icon='FILE_REFRESH')

            # Info según tipo
            info = box.box()
            if props.light_type == 'SUN':
                info.label(text="☀️ Luz paralela infinita (ideal para sol)", icon='INFO')
            elif props.light_type == 'POINT':
                info.label(text="💡 Luz omnidireccional desde un punto", icon='INFO')
            elif props.light_type == 'SPOT':
                info.label(text="🔦 Luz cónica direccional", icon='INFO')
            elif props.light_type == 'AREA':
                info.label(text="📺 Luz suave desde superficie", icon='INFO')
        else:
            box.label(text="Activa para crear iluminación direccional", icon='INFO')

        # === SISTEMA DE GLARE (LENS FLARE) ===
        layout.separator()
        box = layout.box()
        row = box.row()
        row.prop(props, "enable_glare", text="", icon='LIGHT_SUN')
        row.label(text="✨ Lens Flare (Destello Solar)")

        if props.enable_glare:
            col = box.column(align=True)
            col.prop(props, "glare_type", text="Tipo")
            col.prop(props, "glare_threshold", slider=True)
            col.prop(props, "glare_intensity", slider=True)
            col.prop(props, "glare_iterations", slider=True)
            col.prop(props, "glare_mix", slider=True)

            row = box.row()
            row.scale_y = 1.3
            row.operator("hdri.setup_glare", text="Aplicar Lens Flare", icon='LIGHT_SUN')

            row = box.row()
            row.scale_y = 1.1
            row.operator("hdri.update_glare", text="🔄 Actualizar Lens Flare", icon='FILE_REFRESH')

            info = box.box()
            info.label(text="Crea destellos cuando la cámara", icon='INFO')
            info.label(text="apunta hacia el sol")
        else:
            box.label(text="Activa para crear destellos solares", icon='INFO')

        # === SISTEMA VOLUMÉTRICO (GOD RAYS) ===
        layout.separator()
        box = layout.box()
        row = box.row()
        row.prop(props, "enable_volumetric", text="", icon='VOLUME_DATA')
        row.label(text="🌫️ Rayos Volumétricos (God Rays)")

        if props.enable_volumetric:
            col = box.column(align=True)

            col.label(text="Densidad y Scatter:", icon='FORCE_TURBULENCE')
            col.prop(props, "volumetric_density", slider=True)
            col.prop(props, "volumetric_anisotropy", slider=True)

            col.separator()

            col.label(text="Color del Scatter:", icon='COLOR')
            col.prop(props, "volumetric_scatter_color", text="")

            col.separator()

            col.label(text="Propiedades Avanzadas:", icon='PROPERTIES')
            col.prop(props, "volumetric_absorption", slider=True)
            col.prop(props, "volumetric_emission_strength", slider=True)
            col.prop(props, "volumetric_volume_size", slider=True)

            col.separator()

            col.label(text="Calidad de Render:", icon='SCENE')
            col.prop(props, "volumetric_steps", slider=True)
            col.prop(props, "volumetric_step_size", slider=True)

            row = box.row()
            row.scale_y = 1.3
            row.operator("hdri.setup_volumetric", text="Aplicar Volumétrico", icon='VOLUME_DATA')

            row = box.row()
            row.scale_y = 1.1
            row.operator("hdri.update_volumetric", text="🔄 Actualizar Volumétrico", icon='FILE_REFRESH')

            info = box.box()
            info.label(text="⚠️ Requiere Cycles Render", icon='INFO')
            info.label(text="Crea rayos de luz visibles en la atmósfera")
            info.label(text="Mayor densidad = más visibles los rayos")
        else:
            box.label(text="Activa para hacer rayos de luz visibles", icon='INFO')

        # === BOTONES PRINCIPALES ===
        layout.separator()
        row = layout.row()
        row.scale_y = 1.8
        row.operator("hdri.apply_selected", text="Aplicar Sistema HDRI", icon='PLAY')

        row = layout.row()
        row.scale_y = 1.5
        if props.hdri_visible:
            row.operator("hdri.toggle_visibility", text="Ocultar HDRI", icon='HIDE_OFF')
        else:
            row.operator("hdri.toggle_visibility", text="Mostrar HDRI", icon='HIDE_ON')

        row = layout.row()
        row.scale_y = 1.5
        row.operator("hdri.clear_hdri", text="Borrar HDRI", icon='TRASH')

        row = layout.row()
        row.scale_y = 1.3
        row.operator("hdri.update_settings", text="Actualizar Configuración", icon='FILE_REFRESH')

        # === ARCHIVO DE ESCENA ===
        box = layout.box()
        box.label(text="Archivo de Escena:", icon='FILE')
        box.prop(props, "scene_file_name", text="")

        # === BOTONES DE CARGA Y GUARDADO ===
        row = layout.row()
        row.scale_y = 1.3
        row.operator("hdri.load_slot_configuration", text="📂 Cargar Configuración del Slot", icon='IMPORT')

        row = layout.row()
        row.scale_y = 1.3
        row.operator("hdri.export_scene", text="📤 Exportar escena", icon='EXPORT')

        row = layout.row()
        row.scale_y = 1.3
        row.operator("hdri.import_scene", text="📥 Importar escena", icon='IMPORT')

        if not hdri_files:
            box = layout.box()
            box.label(text="⚠️ Configure la carpeta HDRI arriba para ver opciones completas", icon='ERROR')


# Registro de clases
classes = (
    HDRITesterProperties,
    HDRI_OT_solar_cycle,
    HDRI_OT_repair_solar_face,
    HDRI_OT_apply_solar_rays,
    HDRI_OT_attach_solar_light,
    HDRI_OT_remove_solar_cycle,
    HDRI_OT_apply_hdri,
    HDRI_OT_toggle_hdri_visibility,
    HDRI_OT_clear_hdri,
    HDRI_OT_create_sun_light,
    HDRI_OT_update_sun_light,
    HDRI_OT_setup_volumetric,
    HDRI_OT_update_volumetric,
    HDRI_OT_setup_glare,
    HDRI_OT_update_glare,
    HDRI_OT_animate_moving_hdri,
    HDRI_OT_update_settings,
    HDRI_OT_load_slot_configuration,
    HDRI_OT_export_scene,
    HDRI_OT_import_scene,
    HDRI_PT_tester_panel,
)

def register():
    # Running the updated text again must replace the old registered operators,
    # while preserving all existing scene settings and animation objects.
    saved = []
    for scene in bpy.data.scenes:
        props = getattr(scene, 'hdri_tester_props', None)
        values = {}
        if props is not None:
            for prop in props.bl_rna.properties:
                if prop.identifier == 'rna_type' or prop.is_readonly:
                    continue
                try:
                    value = getattr(props, prop.identifier)
                    values[prop.identifier] = list(value) if prop.is_array else value
                except (AttributeError, TypeError, ValueError):
                    pass
        saved.append((scene, values))
    # Remove callbacks left by older geometric-face versions.
    for name in ('render_init', 'render_pre', 'render_complete', 'render_cancel', 'frame_change_post'):
        handlers = getattr(bpy.app.handlers, name)
        for callback in list(handlers):
            if getattr(callback, '__name__', '') in {'solar_face_render_start', 'solar_face_render_end', 'solar_face_frame_changed'}:
                timer = callback.__globals__.get('solar_face_timer')
                if timer and bpy.app.timers.is_registered(timer):
                    bpy.app.timers.unregister(timer)
                handlers.remove(callback)
    if hasattr(bpy.types.Scene, 'hdri_tester_props'):
        del bpy.types.Scene.hdri_tester_props
    for cls in reversed(classes):
        identifier = cls.__name__
        if issubclass(cls, Operator):
            prefix, suffix = cls.bl_idname.split('.')
            identifier = prefix.upper() + '_OT_' + suffix
        old = getattr(bpy.types, identifier, None)
        if old is not None:
            bpy.utils.unregister_class(old)
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.hdri_tester_props = bpy.props.PointerProperty(type=HDRITesterProperties)
    for scene, values in saved:
        for name, value in values.items():
            if name in HDRITesterProperties.__annotations__:
                try:
                    setattr(scene.hdri_tester_props, name, value)
                except (TypeError, ValueError):
                    pass
    print("✓ HDRI Tester Pro registrado correctamente")

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.hdri_tester_props
    print("HDRI Tester Pro desregistrado")

if __name__ == "__main__":
    register()
