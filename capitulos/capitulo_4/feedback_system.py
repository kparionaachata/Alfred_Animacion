#!/usr/bin/env python3
"""
feedback_system.py - Sistema de organización automática de feedback IA
Contiene integración con FeedbackOrganizerSystem
"""

# ============================================================================
# INTEGRACIÓN CON SISTEMA DE FEEDBACK IA
# ============================================================================

import bpy
import os
import json
import datetime
import importlib.util
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, IntProperty, BoolProperty, CollectionProperty
from bpy.types import Operator

# Importar sistema de organización de feedback
try:
    from Extractor_de_datos.feedback_organizer_system import FeedbackOrganizerSystem
    FEEDBACK_ORGANIZER_AVAILABLE = True
    print("✅ Sistema de organización de feedback disponible")
except ImportError as e:
    print(f"⚠️ Sistema de organización de feedback no disponible: {e}")
    FEEDBACK_ORGANIZER_AVAILABLE = False
    FeedbackOrganizerSystem = None

# ============================================================================
# SISTEMA AVANZADO DE EXPORTACIÓN DE FEEDBACK
# ============================================================================

def categorize_rating(rating):
    """Categoriza rating en niveles de calidad"""
    if rating >= 8:
        return "alta_calidad"      # 8-10 ⭐
    elif rating >= 5:
        return "media_calidad"     # 5-7 ⭐
    else:
        return "baja_calidad"      # 1-4 ⭐

def normalize_comment(comment):
    """Normaliza comentario para nombre de carpeta"""
    if not comment:
        return "comentario_sin_comentario"

    # Normalizar: minúsculas, reemplazar espacios y caracteres especiales
    import re
    normalized = comment.lower()
    normalized = re.sub(r'[^\w\s]', '', normalized)  # Remover puntuación
    normalized = re.sub(r'\s+', '_', normalized)     # Espacios a guiones bajos

    return f"comentario_{normalized}"

def extract_action_from_slot(slot_data, manager=None):
    """Extrae acción del slot usando metadata disponible"""
    # Intentar del animation_name
    animation_name = slot_data.get('animation_name', '').lower()

    # Mapeo de acciones comunes EXPANDIDO
    action_mappings = {
        'caminando': 'caminar',
        'caminar': 'caminar',
        'walk': 'caminar',
        'saltando': 'saltar',
        'saltar': 'saltar',
        'jump': 'saltar',
        'corriendo': 'correr',
        'correr': 'correr',
        'run': 'correr',
        'luchando': 'luchar',
        'luchar': 'luchar',
        'fight': 'luchar',
        'atacando': 'atacar',
        'atacar': 'atacar',
        'attack': 'atacar',
        'volando': 'volar',
        'volar': 'volar',
        'fly': 'volar',
        'nadando': 'nadar',
        'nadar': 'nadar',
        'swim': 'nadar',
        'explosion': 'explotar',
        'explotar': 'explotar',
        'explode': 'explotar',
        'ataque': 'atacar',
        'defensa': 'defender',
        'defender': 'defender',
        'defense': 'defender',
        'muerte': 'morir',
        'morir': 'morir',
        'die': 'morir',
        'idle': 'esperar',
        'esperar': 'esperar',
        'wait': 'esperar',
        'mirar': 'mirar',
        'look': 'mirar',
        'gaze': 'mirar',
        'levantar': 'levantar',
        'levantar': 'levantar',
        'lift': 'levantar',
        'bajar': 'bajar',
        'lower': 'bajar',
        'down': 'bajar',
        'girar': 'girar',
        'turn': 'girar',
        'rotate': 'girar',
        'caer': 'caer',
        'fall': 'caer',
        'drop': 'caer',
        'recuperar': 'recuperar',
        'recover': 'recuperar',
        'heal': 'recuperar',
        'reaccion': 'reaccionar',
        'reaccionar': 'reaccionar',
        'react': 'reaccionar',
        'feliz': 'alegrarse',
        'alegrarse': 'alegrarse',
        'happy': 'alegrarse',
        'triste': 'entristecerse',
        'entristecerse': 'entristecerse',
        'sad': 'entristecerse',
        'asustado': 'asustarse',
        'asustarse': 'asustarse',
        'scared': 'asustarse',
        'enojado': 'enojarse',
        'enojarse': 'enojarse',
        'angry': 'enojarse',
        'sorprendido': 'sorprenderse',
        'sorprenderse': 'sorprenderse',
        'surprised': 'sorprenderse',
        'cansado': 'cansarse',
        'cansarse': 'cansarse',
        'tired': 'cansarse',
        'dormir': 'dormir',
        'sleep': 'dormir',
        'rest': 'dormir',
        'despertar': 'despertar',
        'despertar': 'despertar',
        'wake': 'despertar',
        'comer': 'comer',
        'eat': 'comer',
        'beber': 'beber',
        'drink': 'beber',
        'hablar': 'hablar',
        'talk': 'hablar',
        'speak': 'hablar',
        'escuchar': 'escuchar',
        'listen': 'escuchar',
        'hear': 'escuchar',
        'ver': 'ver',
        'see': 'ver',
        'watch': 'ver',
        'tocar': 'tocar',
        'touch': 'tocar',
        'feel': 'tocar',
        'oler': 'oler',
        'smell': 'oler',
        'sentir': 'sentir',
        'feel': 'sentir',
        'sense': 'sentir',
        'pensar': 'pensar',
        'think': 'pensar',
        'consider': 'pensar',
        'recordar': 'recordar',
        'remember': 'recordar',
        'recall': 'recordar',
        'olvidar': 'olvidar',
        'forget': 'olvidar',
        'lose': 'olvidar',
        'aprender': 'aprender',
        'learn': 'aprender',
        'study': 'aprender',
        'enseñar': 'enseñar',
        'teach': 'enseñar',
        'instruct': 'enseñar',
        'trabajar': 'trabajar',
        'work': 'trabajar',
        'labor': 'trabajar',
        'jugar': 'jugar',
        'play': 'jugar',
        'bailar': 'bailar',
        'dance': 'bailar',
        'move': 'bailar',
        'cantar': 'cantar',
        'sing': 'cantar',
        'song': 'cantar'
    }

    for key, action in action_mappings.items():
        if key in animation_name:
            return action

    # Intentar del prompt context si está disponible (usando manager si existe)
    prompt_context = ''
    if manager:
        prompt_context = getattr(manager, 'current_prompt_text', '')
    elif hasattr(slot_data, 'get') and 'prompt_context' in slot_data:
        prompt_context = slot_data.get('prompt_context', {}).get('prompt_original', '')

    if prompt_context:
        # Extraer verbo principal del prompt
        for key, action in action_mappings.items():
            if key in prompt_context.lower():
                return action

    # MEJORA: Intentar extraer acción del nombre del archivo si contiene palabras clave
    # Ejemplo: "slot_001_caminar_normal.py" -> "caminar"
    filename_parts = animation_name.lower().split('_')
    for part in filename_parts:
        for key, action in action_mappings.items():
            if key in part or part in key:
                return action

    # Fallback: usar nombre del slot o 'unknown'
    return 'accion_desconocida'

def export_enhanced_feedback_json(slot_data, user_rating, user_feedback, manager=None):
    """Exporta JSON enriquecido con guidance completo para organización automática"""

    # Crear estructura de guidance
    guidance = {
        "entity": slot_data.get('entity_name', 'unknown'),
        "action": extract_action_from_slot(slot_data, manager),
        "quality_category": categorize_rating(user_rating),
        "normalized_comment": normalize_comment(user_feedback),
        "prompt_context": getattr(manager, 'current_prompt_id', 'unknown') if manager else 'unknown',
        "timeline_slot": slot_data.get('slot_number', 1),  # CORRECCIÓN: usar 1 como default en lugar de 0
        "export_timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Crear JSON completo
    enhanced_data = {
        "manager_guidance": guidance,
        "user_evaluation": {
            "rating": user_rating,
            "feedback": user_feedback,
            "has_rating": user_rating > 0,
            "has_feedback": bool(user_feedback.strip())
        },
        "slot_metadata": slot_data,
        "animation_info": {
            "frame_count": slot_data.get('frame_count', 0),
            "fps": slot_data.get('fps', 24),
            "duration_seconds": slot_data.get('frame_count', 0) / slot_data.get('fps', 24) if slot_data.get('fps', 24) > 0 else 0
        },
        "technical_analysis": {
            "export_method": "enhanced_with_guidance",
            "version": "2.0",
            "manager_version": "2.1.0"
        }
    }

    # Generar nombre de archivo guiado
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{guidance['entity']}_slot_{guidance['timeline_slot']}_{guidance['action']}_{timestamp}.json"

    # Ruta de exportación (carpeta incoming del organizer)
    fixed_path = "c:\\Users\\user\\Desktop\\Alfred_Animacion"
    incoming_path = os.path.join(fixed_path, "Extractor_de_datos", "incoming_feedback")
    export_path = os.path.join(incoming_path, filename)

    # Crear directorio si no existe
    os.makedirs(os.path.dirname(export_path), exist_ok=True)

    # Guardar JSON
    try:
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(enhanced_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Feedback enriquecido exportado: {export_path}")

        # Notificar al organizer (si está corriendo)
        notify_feedback_organizer(filename)

        return export_path

    except Exception as e:
        print(f"❌ Error exportando feedback enriquecido: {e}")
        return None

def notify_feedback_organizer(filename):
    """Notifica al sistema organizer sobre nuevo archivo"""
    try:
        # Intentar comunicación con organizer (socket o archivo de señal)
        signal_file = os.path.join("Extractor_de_datos", "incoming_feedback", ".new_feedback_signal")
        with open(signal_file, 'w') as f:
            f.write(f"{filename}\n{datetime.datetime.now().isoformat()}")

        print(f"📡 Señal enviada al organizer sobre: {filename}")

    except Exception as e:
        print(f"⚠️ No se pudo notificar al organizer: {e}")

def collect_slot_analysis_data(manager, entity_name, slot):
    """Recopila todos los datos de análisis para retroalimentación IA"""
    # Obtener datos de la entidad específica
    if entity_name not in manager.entities:
        return {"error": f"Entidad '{entity_name}' no encontrada"}

    entity_data = manager.entities[entity_name]
    entity_controller = entity_data.get('controller')
    if not entity_controller or slot not in entity_controller.blocks:
        return {"error": f"Slot {slot} no válido para entidad '{entity_name}'"}

    block = entity_controller.blocks[slot]

    # Información básica del slot
    slot_data = {
        # NOMBRE DE ENTIDAD AL NIVEL RAÍZ PARA MAYOR VISIBILIDAD
        "entity_name": entity_name,  # ← AGREGADO: Nombre de entidad al nivel raíz
        "entity_info": {
            "entity_name": entity_name,
            "entity_type": entity_data.get('type', 'unknown'),
            "blend_file": entity_data.get('blend_file', ''),
            "is_entity_loaded": entity_data.get('is_loaded', False)
        },
        "slot_metadata": {
            "export_timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "entity_name": entity_name,
            "slot_number": slot,
            "animation_name": block['name'],
            "file_path": block['file_path'],
            "is_loaded": block['is_loaded']
        },
        "animation_info": {
            "frame_count": block['frame_count'],
            "fps": block['fps'],
            "duration_seconds": block['frame_count'] / block['fps'] if block['fps'] > 0 else 0,
            "description": block['description']
        },
        "user_evaluation": {
            "rating": block['rating'],  # 1-10 estrellas
            "feedback": block['feedback'],  # Comentarios sobre qué mejorar
            "has_rating": block['rating'] > 0,
            "has_feedback": len(block['feedback']) > 0
        }
    }

    # Análisis técnico de la animación (si está cargada en escena)
    if block['is_loaded'] and block['file_path'] and os.path.exists(block['file_path']):
        try:
            # Leer el archivo de animación para extraer metadata técnica
            with open(block['file_path'], 'r', encoding='utf-8') as f:
                animation_content = f.read()

            # Extraer ANIMATION_INFO si existe
            animation_info = extract_animation_metadata(animation_content)
            slot_data["technical_analysis"] = animation_info

            # Análisis de keyframes (si hay acciones en la escena)
            keyframe_analysis = analyze_keyframes(slot)
            slot_data["keyframe_analysis"] = keyframe_analysis

            # Análisis de curvas de movimiento
            curve_analysis = analyze_animation_curves(slot)
            slot_data["curve_analysis"] = curve_analysis

        except Exception as e:
            slot_data["technical_analysis"] = {
                "error": f"No se pudo analizar archivo: {str(e)}"
            }

    # Información del prompt si está disponible
    if manager.prompt_metadata:
        slot_data["prompt_context"] = {
            "prompt_original": manager.prompt_metadata.get('prompt_info', {}).get('original_prompt', ''),
            "scene_number": None,  # Podría determinarse del nombre del archivo
            "narrative_theme": manager.prompt_metadata.get('prompt_info', {}).get('narrative_theme', '')
        }

    # Sugerencias para IA basadas en rating y feedback
    ai_feedback = generate_ai_feedback(block)
    slot_data["ai_feedback"] = ai_feedback

    return slot_data

def extract_animation_metadata(content):
    """Extrae metadata técnica de la animación"""
    metadata = {
        "has_animation_info": False,
        "parameters": {},
        "functions": [],
        "complexity": "unknown"
    }

    try:
        # Buscar ANIMATION_INFO
        if "ANIMATION_INFO =" in content:
            metadata["has_animation_info"] = True

        # Buscar parámetros de configuración
        import re
        param_patterns = {
            "AMPLITUDE": r"AMPLITUDE = ([0-9.]+)",
            "FREQUENCY": r"FREQUENCY = ([0-9.]+)",
            "FPS": r"FPS = ([0-9.]+)",
            "DURATION_SEC": r"DURATION_SEC = ([0-9.]+)"
        }

        for param_name, pattern in param_patterns.items():
            match = re.search(pattern, content)
            if match:
                metadata["parameters"][param_name.lower()] = float(match.group(1))

        # Contar funciones execute_
        execute_functions = re.findall(r"def execute_\w+\(", content)
        metadata["functions"] = execute_functions

        # Estimar complejidad
        lines_count = len(content.split('\n'))
        if lines_count < 100:
            metadata["complexity"] = "simple"
        elif lines_count < 300:
            metadata["complexity"] = "medium"
        else:
            metadata["complexity"] = "complex"

    except Exception as e:
        metadata["error"] = str(e)

    return metadata

def analyze_keyframes(slot):
    """Analiza keyframes de la animación cargada"""
    analysis = {
        "total_keyframes": 0,
        "objects_with_animation": [],
        "animation_ranges": {},
        "frame_distribution": {}
    }

    try:
        # Buscar objetos con animación
        for obj in bpy.data.objects:
            if obj.animation_data and obj.animation_data.action:
                action = obj.animation_data.action
                obj_analysis = {
                    "name": obj.name,
                    "fcurves_count": len(action.fcurves),
                    "frame_range": list(action.frame_range),
                    "data_paths": []
                }

                # Analizar fcurves
                for fcurve in action.fcurves:
                    obj_analysis["data_paths"].append(fcurve.data_path)
                    analysis["total_keyframes"] += len(fcurve.keyframe_points)

                analysis["objects_with_animation"].append(obj_analysis)

    except Exception as e:
        analysis["error"] = str(e)

    return analysis

def analyze_animation_curves(slot):
    """Analiza las curvas de animación para detectar problemas"""
    analysis = {
        "smoothness_score": 0,
        "issues_detected": [],
        "recommendations": []
    }

    try:
        # Análisis básico de suavidad
        total_objects = 0
        smooth_objects = 0

        for obj in bpy.data.objects:
            if obj.animation_data and obj.animation_data.action:
                total_objects += 1
                action = obj.animation_data.action

                # Verificar interpolación
                has_bezier = False
                for fcurve in action.fcurves:
                    for keyframe in fcurve.keyframe_points:
                        if keyframe.interpolation == 'BEZIER':
                            has_bezier = True
                            break
                    if has_bezier:
                        break

                if has_bezier:
                    smooth_objects += 1

        if total_objects > 0:
            analysis["smoothness_score"] = (smooth_objects / total_objects) * 100

        # Detectar issues comunes
        if analysis["smoothness_score"] < 50:
            analysis["issues_detected"].append("Interpolación no suave")
            analysis["recommendations"].append("Usar interpolación BEZIER en lugar de LINEAR")

        if analysis["smoothness_score"] == 0:
            analysis["issues_detected"].append("Sin animación detectada")
            analysis["recommendations"].append("Verificar que la animación se cargó correctamente")

    except Exception as e:
        analysis["error"] = str(e)

    return analysis

def generate_ai_feedback(block):
    """Genera feedback específico para IA basado en rating y comentarios"""
    feedback = {
        "priority_level": "low",
        "correction_needed": False,
        "specific_issues": [],
        "improvement_suggestions": [],
        "regeneration_recommended": False
    }

    rating = block['rating']
    user_feedback = block['feedback'].lower()

    # Analizar rating (escala 1-10)
    if rating <= 4:
        feedback["priority_level"] = "high"
        feedback["correction_needed"] = True
        feedback["regeneration_recommended"] = True
        feedback["specific_issues"].append("Baja calificación del usuario")
    elif rating <= 6:
        feedback["priority_level"] = "medium"
        feedback["correction_needed"] = True
    elif rating >= 7:
        feedback["priority_level"] = "low"
        feedback["correction_needed"] = False

    # Analizar comentarios del usuario
    if "rígido" in user_feedback or "duro" in user_feedback:
        feedback["specific_issues"].append("Movimiento demasiado rígido")
        feedback["improvement_suggestions"].append("Aumentar suavidad de interpolación")

    if "lento" in user_feedback:
        feedback["specific_issues"].append("Animación demasiado lenta")
        feedback["improvement_suggestions"].append("Aumentar frecuencia o velocidad")

    if "rápido" in user_feedback or "veloz" in user_feedback:
        feedback["specific_issues"].append("Animación demasiado rápida")
        feedback["improvement_suggestions"].append("Reducir frecuencia o velocidad")

    if "natural" in user_feedback or "realista" in user_feedback:
        feedback["specific_issues"].append("Falta de naturalidad")
        feedback["improvement_suggestions"].append("Ajustar amplitudes y fases para movimiento más natural")

    if "sync" in user_feedback or "sincron" in user_feedback:
        feedback["specific_issues"].append("Problemas de sincronización")
        feedback["improvement_suggestions"].append("Alinear fases de movimiento entre partes del cuerpo")

    # Si no hay rating ni feedback específico
    if rating == 0 and not user_feedback.strip():
        feedback["priority_level"] = "unknown"
        feedback["correction_needed"] = None
        feedback["specific_issues"].append("Sin evaluación del usuario")

    return feedback

def categorize_and_save_json(json_filepath, entity_name):
    """
    Jerarquiza automáticamente el archivo JSON según rating y comentarios
    """
    try:
        # Leer el JSON generado
        with open(json_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extraer datos críticos
        rating = data.get('user_evaluation', {}).get('rating', 0)
        feedback = data.get('user_evaluation', {}).get('feedback', '').strip()

        # Determinar carpeta de calidad por rating
        if rating >= 8:
            quality_folder = "calidad_prioritaria_8-10_estrellas"
        elif rating >= 6:
            quality_folder = "calidad_aceptable_6-7_estrellas"
        elif rating >= 4:
            quality_folder = "requiere_atencion_4-5_estrellas"
        elif rating >= 1:
            quality_folder = "necesita_mejoras_criticas_1-3_estrellas"
        else:
            quality_folder = "pendiente_evaluacion"

        # Determinar subcarpeta por comentarios
        if feedback:
            comment_folder = "con_comentarios_detallados"
        else:
            comment_folder = "solo_rating_numerico"

        # Construir ruta jerárquica
        base_path = "c:\\Users\\user\\Desktop\\Alfred_Animacion"
        entity_base_path = os.path.join(base_path, "Extractor_de_datos", entity_name, "base_de_datos")
        quality_path = os.path.join(entity_base_path, quality_folder)
        comment_path = os.path.join(quality_path, comment_folder)

        # Crear jerarquía de carpetas automáticamente
        os.makedirs(comment_path, exist_ok=True)

        # Mover archivo a ubicación jerárquica (en lugar de copiar)
        filename = os.path.basename(json_filepath)
        final_path = os.path.join(comment_path, filename)

        import shutil
        shutil.move(json_filepath, final_path)

        print(f"✅ JSON jerarquizado y movido: {final_path}")
        return final_path

    except Exception as e:
        print(f"❌ Error en jerarquización automática: {e}")
        return json_filepath

# ============================================================================
# FUNCIONES DE SOPORTE PARA FEEDBACK IA
# ============================================================================

def initialize_feedback_system():
    """Inicializa el sistema de organización de feedback IA"""
    from .core_system import blocks_manager

    if FEEDBACK_ORGANIZER_AVAILABLE and FeedbackOrganizerSystem:
        try:
            blocks_manager.feedback_organizer = FeedbackOrganizerSystem()
            blocks_manager.feedback_organizer_enabled = True
            print("✅ Sistema de organización de feedback inicializado")
        except Exception as e:
            print(f"❌ Error inicializando sistema de feedback: {e}")
            blocks_manager.feedback_organizer_enabled = False
    else:
        blocks_manager.feedback_organizer_enabled = False
        print("⚠️ Sistema de organización de feedback no disponible")

def process_feedback_for_animation(animation_name: str, feedback_data: dict):
    """Procesa feedback para una animación específica"""
    from .core_system import blocks_manager

    if not blocks_manager.feedback_organizer_enabled:
        return False

    try:
        if blocks_manager.feedback_organizer:
            success = blocks_manager.feedback_organizer.organize_feedback(
                animation_name, feedback_data
            )
            if success:
                print(f"✅ Feedback procesado para {animation_name}")
                return True
            else:
                print(f"⚠️ Error procesando feedback para {animation_name}")
                return False
        else:
            print("⚠️ Organizador de feedback no disponible")
            return False
    except Exception as e:
        print(f"❌ Error procesando feedback: {e}")
        return False

def get_feedback_summary():
    """Obtiene resumen de feedback organizado"""
    from .core_system import blocks_manager

    if not blocks_manager.feedback_organizer_enabled or not blocks_manager.feedback_organizer:
        return {}

    try:
        return blocks_manager.feedback_organizer.get_organized_feedback()
    except Exception as e:
        print(f"❌ Error obteniendo resumen de feedback: {e}")
        return {}

def export_feedback_to_json(filepath: str):
    """Exporta feedback organizado a archivo JSON"""
    from .core_system import blocks_manager

    if not blocks_manager.feedback_organizer_enabled:
        print("⚠️ Sistema de feedback no disponible")
        return False

    try:
        feedback_data = get_feedback_summary()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(feedback_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Feedback exportado a {filepath}")
        return True
    except Exception as e:
        print(f"❌ Error exportando feedback: {e}")
        return False

# ============================================================================
# INTEGRACIÓN CON ANIMATIONS
# ============================================================================

def integrate_feedback_with_animation_manager():
    """Integra el sistema de feedback con el manager de animaciones"""
    from .core_system import blocks_manager

    class FeedbackIntegratedAnimationManager:
        def __init__(self, animation_manager):
            self.animation_manager = animation_manager
            self.feedback_data = {}

        def execute_animation_block(self, block, start_frame, end_frame, player_parts):
            """Ejecuta bloque con integración de feedback"""
            # Ejecutar animación normalmente
            try:
                from .animation_engine import execute_animation_block
                success = execute_animation_block(block, start_frame, end_frame, player_parts)
            except ImportError:
                # Fallback si animation_engine no está disponible
                success = True  # Asumir éxito para compatibilidad

            if success:
                # Recopilar feedback automáticamente
                feedback = self.collect_animation_feedback(block, start_frame, end_frame)
                if feedback:
                    self.feedback_data[block['name']] = feedback
                    process_feedback_for_animation(block['name'], feedback)

            return success

        def collect_animation_feedback(self, block, start_frame, end_frame):
            """Recopila feedback automático de la animación"""
            feedback = {
                'animation_name': block['name'],
                'frame_range': f"{start_frame}-{end_frame}",
                'duration_frames': end_frame - start_frame + 1,
                'fps': block.get('fps', 24),
                'timestamp': datetime.datetime.now().isoformat(),
                'auto_feedback': {
                    'smoothness': 'unknown',  # Podría analizarse con algoritmos
                    'completeness': 'executed_successfully',
                    'performance': 'good'
                }
            }
            return feedback

    # Integrar con el manager existente (solo si no existe ya)
    try:
        if not hasattr(blocks_manager, 'feedback_integrator'):
            setattr(blocks_manager, 'feedback_integrator', FeedbackIntegratedAnimationManager(blocks_manager))
    except (AttributeError, TypeError):
        # Si no se puede asignar, continuar sin integración
        pass

    return getattr(blocks_manager, 'feedback_integrator', None)

# ============================================================================
# REGISTRO DEL MÓDULO
# ============================================================================

def register():
    """Registra el sistema de feedback"""
    try:
        initialize_feedback_system()
        integrate_feedback_with_animation_manager()
        print("✅ Sistema de feedback registrado correctamente")
    except Exception as e:
        print(f"⚠️ Error registrando sistema de feedback: {e}")

def unregister():
    """Desregistra el sistema de feedback"""
    try:
        from .core_system import blocks_manager

        blocks_manager.feedback_organizer = None
        blocks_manager.feedback_organizer_enabled = False

        if hasattr(blocks_manager, 'feedback_integrator'):
            delattr(blocks_manager, 'feedback_integrator')

        print("✅ Sistema de feedback desregistrado correctamente")
    except Exception as e:
        print(f"⚠️ Error desregistrando sistema de feedback: {e}")