# 🎭 Sistema Multi-Entidad Proyecto

## 📋 Descripción

Sistema avanzado de gestión de animaciones multi-entidad para personajes estilo Minecraft. Permite manejar múltiples personajes simultáneamente con timeline compartido, sistema de calificación y exportación inteligente para IA.

## 🚀 Inicio Rápido

### Opción 1: Flujo Automático (Recomendado)
```bash
# Ejecutar el archivo batch para iniciar todo automáticamente
start_proyecto.bat
```

Este comando:
1. ✅ Verifica que Blender esté instalado
2. ✅ Valida que existan `base.blend` y `simple_animation_blocks_manager.py`
3. ✅ Carga el addon automáticamente
4. ✅ Abre Blender con la escena base lista para usar

### Opción 2: Inicio Manual
```bash
# Abrir Blender manualmente
blender.exe base.blend

# Dentro de Blender:
# 1. Ir a Edit > Preferences > Add-ons
# 2. Install... > seleccionar simple_animation_blocks_manager.py
# 3. Activar el addon "Multi-Entity Animation Blocks Manager"
```

## 🎯 Características Principales

### 🎭 Multi-Entidad
- **Entidades soportadas**: alfred, creeper, wolf, chicken, cow, pig, sheep, etc.
- **Slots por entidad**: 20 slots de animación independientes
- **Timeline compartido**: Sincronización automática entre entidades

### 🌍 Sistema de Traducción
- Traducción automática Español → Inglés
- Ejemplos: "araña" → "spider", "pollo" → "chicken"
- Soporte para acentos y variaciones comunes

### ⭐ Sistema de Evaluación
- **Calificación**: 1-10 estrellas por animación
- **Comentarios**: Feedback detallado para mejoras
- **Exportación IA**: Análisis automático para retroalimentación

### 🎬 Gestión Avanzada
- **Concatenación**: Unir animaciones en secuencias
- **Reproducción**: Control manual de playback
- **Loop**: Reproducción cíclica automática
- **Indicadores visuales**: Estados de animación en tiempo real
- **Extracción del Outliner**: Análisis completo de jerarquía para IA
- **🆕 Universal File Analyzer**: Herramienta disponible para todas las IAs para análisis estructurado de archivos largos

## 📁 Estructura del Proyecto

```
Proyecto/
├── base.blend                          # Escena base de Blender
├── simple_animation_blocks_manager.py  # Addon principal (5057 líneas)
├── universal_file_analyzer.py           # 🆕 Herramienta universal para análisis de archivos largos
├── outliner_extractor_2.py             # Extractor independiente del outliner
├── plano_generador_addon.py            # 🆕 Generador de planos con orientación y textura
├── outliner_data.json                  # JSON generado con estructura completa (generado)
├── start_blender_proyecto.bat          # Script de inicio automático
└── README_proyecto.md                  # Esta documentación
```

## 🎮 Workflow de Uso

### 1. Preparación
```bash
# Ejecutar el flujo automático
start_proyecto.bat
```

### 2. Carga de Prompt
- En Blender: Ir al panel "Animation Blocks" en la sidebar
- Click en "Cargar Carpeta Prompt"
- Seleccionar carpeta Prompt_X (ej: `../animacion/Prompt_007/`)

### 3. Configuración de Entidades
- El sistema detecta automáticamente entidades desde `metadata.json`
- Cada entidad aparece en su propia columna
- Cargar estructuras .blend para cada entidad según sea necesario

### 4. Carga de Animaciones
- Las animaciones se cargan automáticamente desde archivos `slot_xxx_*.py`
- Sistema de traducción encuentra archivos aunque estén en inglés
- 20 slots disponibles por entidad

### 5. Reproducción
- **Individual**: Usar "🔗 Concatenar" en cada columna
- **Completo**: Usar "🎭 Reproducir Todas las Entidades"
- Timeline compartido sincroniza todas las entidades

### 6. Extracción del Outliner
- **Actualizar**: Presiona "🔃 Actualizar" para recargar `Prompt_xxx` y eliminar `outliner_data.json`. No modifica ningún archivo `.blend` ya cargado en el addon (ni `base.blend` ni estructuras como `alfred.blend`, `creeper.blend`, etc.).
- **Extraer**: Luego presiona "Extraer Datos" para regenerar `outliner_data.json` actualizado
- **Análisis completo**: Jerarquía de collections, objetos, armatures y relaciones
- **Disponible para IA**: JSON local en carpeta Proyecto para análisis inmediato
- **🆕 Universal File Analyzer**: Todas las IAs disponen de `universal_file_analyzer.py` para análisis estructurado de archivos largos
- **Estructura por entidad**: Cada entidad tiene su carpeta en `Extractor_de_datos/{entidad}` (ej.: `Extractor_de_datos/creeper`).
- **JSON por entidad**: Cada entidad en `outliner_data.json` incluye `data_folder_project_path`, `data_folder_full_path` y `data_folder_exists` para enlazar su carpeta en `Extractor_de_datos`. sin sobrecarga cognitiva

#### ⚠️ **CORRECCIÓN CRÍTICA v2.1.2 (2025-10-19)**
**Problema identificado:** El extractor siempre reportaba `Prompt_004` independientemente del prompt realmente cargado.

**Causa raíz:** El sistema detectaba prompts por fecha de modificación en lugar de consultar el estado actual del manager.

**Solución implementada:**
- ✅ **Primera prioridad**: Consultar `get_blocks_manager().current_prompt_folder` para obtener el prompt actualmente cargado
- ✅ **Fallback**: Solo usar detección automática por fecha como respaldo
- ✅ **Marcador de fuente**: Agregar `'source': 'manager_current_loaded'` o `'source': 'automatic_detection'`

**Resultado:** Ahora `outliner_data.json` refleja correctamente el prompt que está realmente cargado en el sistema.

### 7. Evaluación y Exportación
- **Calificar**: 1-10 estrellas por slot
- **Comentarios**: Feedback detallado
- **Exportar**: Datos estructurados para análisis IA

## 🔧 Requisitos del Sistema

### Software
- **Blender 3.0+** (recomendado 3.6+)
- **Python 3.7+** (incluido con Blender)
- **Windows 10/11** (soporte nativo)

### Archivos Necesarios
- `base.blend`: Escena base
- `simple_animation_blocks_manager.py`: Addon principal
- Carpetas Prompt_X con `metadata.json`

### Estructuras de Soporte
- `estructura_lista/`: Archivos .blend de entidades
- `Extractor_de_datos/`: Sistema de exportación
- `acciones/`: Templates de animación

## 🐛 Solución de Problemas

### Error: "Blender no encontrado"
```bash
# Agregar Blender al PATH del sistema o ejecutar desde:
# "C:\Program Files\Blender Foundation\Blender 3.6\blender.exe" base.blend
```

### Error: "Addon no carga"
- Verificar versión de Blender (3.0+ requerida)
- Revisar consola de Blender para errores específicos
- Asegurar que `simple_animation_blocks_manager.py` esté en el directorio correcto

### Error: "Entidades no se cargan"
- Verificar que existe `metadata.json` en la carpeta Prompt_X
- Revisar formato del metadata (debe tener sección `entidades`)
- Verificar traducciones en `ENTITY_NAME_MAPPING`

### Error: "Animaciones no funcionan"
- Verificar que las estructuras .blend estén cargadas
- Revisar que los nombres de objetos coincidan con lo esperado
- Usar diagnóstico integrado para entidades específicas

## 📊 Sistema de Calificación

### Escala de Estrellas
- ⭐ (1-2): Problemas críticos, necesita re-generación
- ⭐⭐ (3-4): Problemas mayores, corrección necesaria
- ⭐⭐⭐ (5-6): Aceptable con mejoras menores
- ⭐⭐⭐⭐ (7-8): Bueno, pequeñas optimizaciones
- ⭐⭐⭐⭐⭐ (9-10): Excelente, listo para producción

### Categorización Automática
- **1-3 estrellas**: `necesita_mejoras_criticas_1-3_estrellas`
- **4-5 estrellas**: `requiere_atencion_4-5_estrellas`
- **6-7 estrellas**: `calidad_aceptable_6-7_estrellas`
- **8-10 estrellas**: `calidad_prioritaria_8-10_estrellas`

## 🔄 Sistema de Traducción

### Ejemplos de Traducciones
```
araña → spider
pollo → chicken
vaca → cow
lobo → wolf
creeper → creeper
jugador → player
aldeano → villager
esqueleto → skeleton
```

### Configuración Manual
En `metadata.json`:
```json
{
  "entidades": {
    "mi_personaje": {
      "tipo": "player",
      "nombre_traduccion": "custom_character"
    }
  }
}
```

## 📈 Métricas y Análisis

### Datos Exportados por Slot
- Información básica (frames, fps, duración)
- Calificación y comentarios del usuario
- Análisis técnico de keyframes
- Curvas de movimiento y suavidad
- Feedback inteligente para IA

### Jerarquización Automática
Los archivos JSON se organizan automáticamente en:
```
Extractor_de_datos/{entidad}/base_de_datos/
├── calidad_prioritaria_8-10_estrellas/
│   ├── con_comentarios_detallados/
│   └── solo_rating_numerico/
├── calidad_aceptable_6-7_estrellas/
└── ...
```

## 🎨 Interfaz de Usuario

### Panel Principal
- **Controles Generales**: Reset, Actualizar, Timeline, Loop
- **Carga Multi-Entidad**: Cargar carpetas Prompt_X
- **Columnas por Entidad**: Una columna dedicada por personaje

### Controles por Entidad
- **Cargar Estructura**: Importar .blend de la entidad
- **Animaciones**: Lista de slots con calificaciones
- **Concatenar**: Probar entidad individualmente
- **Extraer Datos**: Generar outliner_data.json para IA
- **Exportar**: Datos de análisis por slot

### Indicadores Visuales
- 🎬 Slots activos durante reproducción
- ✅ Estructuras cargadas
- ⭐ Calificaciones por animación
- ⏱️ Timeline compartido

## 🔗 Integraciones

### Sistemas Conectados
- **estructura_lista/**: Librería de .blend
- **Extractor_de_datos/**: Análisis y exportación
- **post_generation_validator/**: Validación automática
- **narrative_object_parser/**: Objetos dinámicos
- **feedback_organizer_system/**: Organización IA
- **outliner_extractor_2.py**: Extracción independiente del outliner
- **🆕 plano_generador_addon.py**: Generador de planos con orientación y textura
- **🆕 universal_file_analyzer.py**: Herramienta universal para análisis estructurado de archivos largos (disponible para todas las IAs)

### Compatibilidad
- Compatible con animaciones originales
- Soporte para exportaciones previas
- Integración con sistema de prompts
- API extensible para nuevas entidades

## 📝 Notas de Desarrollo

### Version: 2.1.2 (2025-10-19)
- Soporte multi-entidad completo
- Sistema de traducción inteligente
- Exportación con guidance para IA
- Timeline compartido dinámico
- Sistema de calificación integrado
- Extracción del outliner para IA (corregida)
- 🆕 **Universal File Analyzer**: Herramienta disponible para todas las IAs para análisis estructurado de archivos largos
- ✅ **CORRECCIÓN**: Detección correcta del prompt actualmente cargado
- 🆕 **Plano Generador Addon**: Generador de planos con orientación y textura configurable

## ⚠️ **REGLAS CRÍTICAS PARA CONFIGURACIÓN IA**

### 🧠 **SISTEMA DE MEMORIA TEMPORAL - MOCHILA DE SESIÓN**

**IMPORTANTE PARA TODAS LAS IAs**: Antes de comenzar cualquier trabajo, deben crear su "mochila de sesión" para mantener memoria persistente durante la conversación.

#### **¿Cómo crear la Mochila de Sesión?**
```bash
# Crear carpeta de memoria temporal
mkdir Proyecto\.session_cache

# Copiar archivos clave (el usuario indicará cuáles)
# La IA debe esperar que el usuario especifique qué archivos llevar como "libros de referencia"
```

#### **Funcionamiento del Sistema**:
1. **El usuario indica** qué archivos deben ser los "libros de referencia"
2. **La IA crea** la carpeta `Proyecto/.session_cache/` y copia los archivos
3. **Durante la sesión**: La IA consulta estos archivos para recordar reglas y estado
4. **Al finalizar**: El usuario borra manualmente la carpeta `.session_cache/`
5. **Nueva sesión**: Se repite el ciclo con nuevos libros si es necesario

#### **Archivos Típicos de Referencia**:
- `README_proyecto.md` - Reglas del sistema
- `outliner_data.json` - Estado actual del proyecto
- `simple_animation_blocks_manager.py` - APIs disponibles
- `metadata.json` del prompt actual - Configuración activa

### 🚨 **REGLA OBLIGATORIA: MODIFICACIONES ÚNICAMENTE EN SLOTS EXISTENTES**

**Cualquier configuración o modificación que realice cualquier IA para este flujo DEBE hacerse ÚNICAMENTE en los archivos `.py` que están dentro de la carpeta `Alfred_Animacion\animacion\Prompt_xxx\` (donde `Prompt_xxx` es el prompt actualmente cargado en el sistema).**

#### ✅ **PERMITIDO:**
- Modificar parámetros dentro de archivos `slot_xxx_*.py` existentes
- Ajustar valores de animación, timing, posiciones, etc.
- Cambiar configuraciones de interpolación y curvas
- Optimizar movimientos y expresiones

#### ❌ **PROHIBIDO:**
- Crear nuevos archivos `slot_xxx_*.py`
- Modificar archivos fuera de `animacion/Prompt_xxx/`
- Crear carpetas adicionales o estructuras nuevas
- Alterar archivos del sistema base (addon, base.blend, etc.)

#### 🎯 **EXCEPCIÓN:**
**Solo se crearán nuevos slots si se solicita explícitamente "agregar más slots" o "crear slot adicional".**

**Esta regla asegura consistencia del sistema y evita fragmentación innecesaria de animaciones.**

### 📚 **Ciclo de Memoria Temporal**
1. **Inicio de sesión**: IA crea `.session_cache/` con libros indicados por el usuario
2. **Durante trabajo**: IA consulta la mochila para recordar información clave
3. **Fin de sesión**: Usuario borra manualmente `.session_cache/`
4. **Nueva sesión**: Se repite el ciclo con nuevos libros de referencia según necesidad

**El usuario es el responsable de gestionar el ciclo de memoria - indicando qué recordar y cuándo limpiar.**

### Próximas Características
- [x] Extracción del outliner para IA
- [x] 🆕 Universal File Analyzer para todas las IAs
- [ ] Animación relativa avanzada
- [ ] Sistema de objetos dinámicos completo
- [ ] Modo narrativa vs coherencia
- [ ] Exportación batch masiva
- [ ] Interfaz web complementaria

---

## 🎯 Resumen Ejecutivo

El **Sistema Multi-Entidad Proyecto** es una solución completa para gestión de animaciones complejas en Blender, específicamente diseñado para proyectos multi-personaje estilo Minecraft. Combina facilidad de uso con características avanzadas de producción, incluyendo evaluación IA, extracción del outliner y organización automática de feedback.

**Punto de entrada**: `start_blender_proyecto.bat`

---

## 🆕 **Universal File Analyzer - Herramienta para IAs**

### 🎯 **¿Qué es?**
Herramienta especializada para análisis estructurado de archivos largos, diseñada específicamente para resolver problemas de sobrecarga cognitiva en IAs al analizar archivos complejos como `outliner_data.json` o `simple_animation_blocks_manager.py`.

### 📍 **Ubicación**
- Archivo: `Proyecto/universal_file_analyzer.py`
- Disponible para todas las IAs del sistema

### 🚀 **Uso Básico**
```python
from universal_file_analyzer import UniversalFileAnalyzer

# Análisis completo
analyzer = UniversalFileAnalyzer()
report = analyzer.analyze_file('outliner_data.json')
print(f"Secciones encontradas: {len(report.sections)}")

# Consulta enfocada
analyzer.load_file('simple_animation_blocks_manager.py')
clases = analyzer.query(r'^class\s+\w+', 'class')
print(f"Clases encontradas: {len(clases)}")

# Análisis rápido
from universal_file_analyzer import quick_analyze
info = quick_analyze('archivo_largo.json')
```

### ✅ **Beneficios para IAs**
- **Análisis sin sobrecarga**: Divide archivos grandes en secciones manejables
- **Consultas específicas**: Encuentra exactamente lo que necesitas
- **Reportes navegables**: Estructura clara con referencias específicas
- **Tiempo de análisis**: ~0.1s para archivos de 400KB+

### 🎨 **Formatos Soportados**
- **Python**: Clases, funciones, imports, métodos
- **JSON**: Objetos, arrays, estructura jerárquica
- **XML**: Elementos, atributos, jerarquía
- **Markdown**: Encabezados, secciones
- **Texto plano**: Análisis genérico

### 📊 **Ejemplo de Uso con outliner_data.json**
```python
analyzer = UniversalFileAnalyzer()
report = analyzer.analyze_file('Proyecto/outliner_data.json')

# Resultado: 53 secciones identificadas en 0.10s
# - system_context: objeto con 3 claves
# - collections: objeto con jerarquía completa
# - relationships: mapeo mesh-to-armature
# - etc.
```

**Esta herramienta garantiza que todas las IAs puedan analizar archivos largos de manera estructurada y eficiente, eliminando respuestas genéricas y sobrecarga cognitiva.**