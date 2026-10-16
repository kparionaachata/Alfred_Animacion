#!/usr/bin/env python3
"""
UNIVERSAL FILE ANALYZER - Herramienta para análisis inteligente de archivos largos
==================================================================================

Esta herramienta permite analizar archivos de cualquier tipo (Python, JSON, XML, etc.)
de manera estructurada, dividiendo el contenido en secciones lógicas y extrayendo
información clave sin sobrecargar el procesamiento.

Características principales:
- Detección automática del tipo de archivo
- Análisis modular por secciones
- Extracción inteligente de información clave
- Reportes estructurados en JSON/Markdown
- Sistema de consultas enfocadas
- Documentación completa para otras IAs

Uso básico:
    analyzer = UniversalFileAnalyzer()
    report = analyzer.analyze_file('archivo.json')
    print(report)

Uso avanzado con consultas:
    analyzer = UniversalFileAnalyzer()
    analyzer.load_file('archivo.py')
    results = analyzer.query('class.*Manager')
    print(results)
"""

import json
import re
import ast
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import hashlib
import time
from dataclasses import dataclass, asdict
from enum import Enum


class FileType(Enum):
    """Tipos de archivo soportados"""
    PYTHON = "python"
    JSON = "json"
    XML = "xml"
    YAML = "yaml"
    MARKDOWN = "markdown"
    TEXT = "text"
    UNKNOWN = "unknown"


@dataclass
class FileSection:
    """Representa una sección lógica de un archivo"""
    name: str
    type: str
    start_line: int
    end_line: int
    content: str
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AnalysisReport:
    """Reporte completo de análisis"""
    file_path: str
    file_type: FileType
    file_size: int
    total_lines: int
    checksum: str
    sections: List[FileSection]
    key_info: Dict[str, Any]
    timestamp: float
    analysis_time: float

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el reporte a diccionario"""
        return {
            "file_info": {
                "path": self.file_path,
                "type": self.file_type.value,
                "size": self.file_size,
                "lines": self.total_lines,
                "checksum": self.checksum,
                "timestamp": self.timestamp,
                "analysis_time": self.analysis_time
            },
            "sections": [asdict(section) for section in self.sections],
            "key_info": self.key_info
        }

    def to_markdown(self) -> str:
        """Convierte el reporte a formato Markdown"""
        md = [f"# Análisis de Archivo: {Path(self.file_path).name}\n"]
        md.append("## Información General")
        md.append(f"- **Tipo**: {self.file_type.value}")
        md.append(f"- **Tamaño**: {self.file_size} bytes")
        md.append(f"- **Líneas**: {self.total_lines}")
        md.append(f"- **Checksum**: {self.checksum[:16]}...")
        md.append(f"- **Tiempo de análisis**: {self.analysis_time:.2f}s\n")

        md.append("## Secciones Principales\n")
        for i, section in enumerate(self.sections, 1):
            md.append(f"### {i}. {section.name}")
            md.append(f"- **Tipo**: {section.type}")
            md.append(f"- **Líneas**: {section.start_line}-{section.end_line}")
            if section.metadata:
                md.append("- **Metadata**:")
                for key, value in section.metadata.items():
                    md.append(f"  - {key}: {value}")
            md.append("")

        md.append("## Información Clave\n")
        for category, info in self.key_info.items():
            md.append(f"### {category.title()}")
            if isinstance(info, dict):
                for key, value in info.items():
                    md.append(f"- **{key}**: {value}")
            elif isinstance(info, list):
                for item in info:
                    md.append(f"- {item}")
            else:
                md.append(f"{info}")
            md.append("")

        return "\n".join(md)


class UniversalFileAnalyzer:
    """
    Analizador universal de archivos largos

    Esta clase proporciona métodos para analizar archivos de cualquier tipo
    de manera estructurada y eficiente.
    """

    def __init__(self):
        self.current_file: Optional[str] = None
        self.current_content: Optional[str] = None
        self.current_report: Optional[AnalysisReport] = None

    def detect_file_type(self, file_path: str) -> FileType:
        """Detecta automáticamente el tipo de archivo"""
        extension = Path(file_path).suffix.lower()

        type_map = {
            '.py': FileType.PYTHON,
            '.json': FileType.JSON,
            '.xml': FileType.XML,
            '.yaml': FileType.YAML,
            '.yml': FileType.YAML,
            '.md': FileType.MARKDOWN,
            '.txt': FileType.TEXT
        }

        return type_map.get(extension, FileType.UNKNOWN)

    def load_file(self, file_path: str) -> bool:
        """Carga un archivo en memoria"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.current_content = f.read()
            self.current_file = file_path
            return True
        except Exception as e:
            print(f"Error cargando archivo {file_path}: {e}")
            return False

    def analyze_file(self, file_path: str) -> AnalysisReport:
        """Analiza un archivo completo y retorna un reporte"""
        start_time = time.time()

        # Cargar archivo
        if not self.load_file(file_path):
            raise FileNotFoundError(f"No se pudo cargar {file_path}")

        # Detectar tipo
        file_type = self.detect_file_type(file_path)

        # Obtener estadísticas básicas
        if self.current_content is None:
            raise ValueError("Contenido del archivo no cargado")

        lines = self.current_content.split('\n')
        file_size = len(self.current_content.encode('utf-8'))
        checksum = hashlib.md5(self.current_content.encode()).hexdigest()

        # Analizar según tipo
        sections = self._analyze_by_type(file_type, lines)
        key_info = self._extract_key_info(file_type, lines)

        # Crear reporte
        analysis_time = time.time() - start_time
        report = AnalysisReport(
            file_path=file_path,
            file_type=file_type,
            file_size=file_size,
            total_lines=len(lines),
            checksum=checksum,
            sections=sections,
            key_info=key_info,
            timestamp=time.time(),
            analysis_time=analysis_time
        )

        self.current_report = report
        return report

    def _analyze_by_type(self, file_type: FileType, lines: List[str]) -> List[FileSection]:
        """Analiza el archivo según su tipo"""
        analyzers = {
            FileType.PYTHON: self._analyze_python,
            FileType.JSON: self._analyze_json,
            FileType.XML: self._analyze_xml,
            FileType.YAML: self._analyze_yaml,
            FileType.MARKDOWN: self._analyze_markdown,
            FileType.TEXT: self._analyze_text
        }

        analyzer = analyzers.get(file_type, self._analyze_generic)
        return analyzer(lines)

    def _analyze_python(self, lines: List[str]) -> List[FileSection]:
        """Analiza archivos Python"""
        sections = []
        current_class = None
        current_function = None
        in_docstring = False
        docstring_start = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Detectar clases
            class_match = re.match(r'^class\s+(\w+)', stripped)
            if class_match:
                if current_class:
                    sections.append(current_class)
                current_class = FileSection(
                    name=class_match.group(1),
                    type="class",
                    start_line=i,
                    end_line=i,
                    content=line,
                    metadata={"methods": [], "attributes": []}
                )
                if current_class.metadata is None:
                    current_class.metadata = {"methods": [], "attributes": []}
                continue

            # Detectar funciones/métodos
            func_match = re.match(r'^\s*def\s+(\w+)', stripped)
            if func_match:
                func_name = func_match.group(1)
                section = FileSection(
                    name=func_name,
                    type="function",
                    start_line=i,
                    end_line=i,
                    content=line,
                    metadata={"class": current_class.name if current_class else None}
                )

                if current_class and current_class.metadata is not None:
                    current_class.metadata["methods"].append(func_name)
                    current_class.end_line = i

                sections.append(section)
                continue

            # Detectar imports
            if stripped.startswith('import ') or stripped.startswith('from '):
                sections.append(FileSection(
                    name=f"import_{i}",
                    type="import",
                    start_line=i,
                    end_line=i,
                    content=line
                ))

            # Actualizar línea final de clase actual
            if current_class and not stripped.startswith(' ') and stripped:
                current_class.end_line = i

        # Cerrar clase final
        if current_class:
            sections.append(current_class)

        return sections

    def _analyze_json(self, lines: List[str]) -> List[FileSection]:
        """Analiza archivos JSON"""
        sections = []
        content = '\n'.join(lines)

        try:
            data = json.loads(content)
            sections = self._parse_json_structure(data, "root", 1, len(lines))
        except json.JSONDecodeError:
            sections.append(FileSection(
                name="invalid_json",
                type="error",
                start_line=1,
                end_line=len(lines),
                content="JSON inválido"
            ))

        return sections

    def _parse_json_structure(self, data: Any, name: str, start_line: int, end_line: int) -> List[FileSection]:
        """Parsea recursivamente la estructura JSON"""
        sections = []

        if isinstance(data, dict):
            section = FileSection(
                name=name,
                type="object",
                start_line=start_line,
                end_line=end_line,
                content=json.dumps(data, indent=2),
                metadata={"keys": list(data.keys()), "size": len(data)}
            )
            sections.append(section)

            # Analizar subobjetos
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    subsections = self._parse_json_structure(value, key, start_line, end_line)
                    sections.extend(subsections)

        elif isinstance(data, list):
            section = FileSection(
                name=name,
                type="array",
                start_line=start_line,
                end_line=end_line,
                content=json.dumps(data, indent=2),
                metadata={"length": len(data)}
            )
            sections.append(section)

        return sections

    def _analyze_xml(self, lines: List[str]) -> List[FileSection]:
        """Analiza archivos XML"""
        sections = []
        content = '\n'.join(lines)

        try:
            root = ET.fromstring(content)
            sections = self._parse_xml_structure(root, "root", 1, len(lines))
        except ET.ParseError:
            sections.append(FileSection(
                name="invalid_xml",
                type="error",
                start_line=1,
                end_line=len(lines),
                content="XML inválido"
            ))

        return sections

    def _parse_xml_structure(self, element: ET.Element, name: str, start_line: int, end_line: int) -> List[FileSection]:
        """Parsea recursivamente la estructura XML"""
        sections = []

        section = FileSection(
            name=name,
            type="element",
            start_line=start_line,
            end_line=end_line,
            content=ET.tostring(element, encoding='unicode'),
            metadata={
                "tag": element.tag,
                "attributes": dict(element.attrib),
                "children": len(element)
            }
        )
        sections.append(section)

        # Analizar hijos
        for child in element:
            subsections = self._parse_xml_structure(child, child.tag, start_line, end_line)
            sections.extend(subsections)

        return sections

    def _analyze_yaml(self, lines: List[str]) -> List[FileSection]:
        """Analiza archivos YAML (placeholder)"""
        return [FileSection(
            name="yaml_content",
            type="yaml",
            start_line=1,
            end_line=len(lines),
            content='\n'.join(lines)
        )]

    def _analyze_markdown(self, lines: List[str]) -> List[FileSection]:
        """Analiza archivos Markdown"""
        sections = []
        current_section = None

        for i, line in enumerate(lines, 1):
            if line.startswith('#'):
                # Cerrar sección anterior
                if current_section:
                    current_section.end_line = i - 1
                    sections.append(current_section)

                # Nueva sección
                level = len(line.split()[0])  # Contar #
                title = line.strip('#').strip()
                current_section = FileSection(
                    name=title,
                    type=f"heading_{level}",
                    start_line=i,
                    end_line=i,
                    content=line,
                    metadata={"level": level}
                )

        # Cerrar última sección
        if current_section:
            current_section.end_line = len(lines)
            sections.append(current_section)

        return sections

    def _analyze_text(self, lines: List[str]) -> List[FileSection]:
        """Analiza archivos de texto plano"""
        return [FileSection(
            name="text_content",
            type="text",
            start_line=1,
            end_line=len(lines),
            content='\n'.join(lines)
        )]

    def _analyze_generic(self, lines: List[str]) -> List[FileSection]:
        """Análisis genérico para tipos desconocidos"""
        return [FileSection(
            name="generic_content",
            type="unknown",
            start_line=1,
            end_line=len(lines),
            content='\n'.join(lines)
        )]

    def _extract_key_info(self, file_type: FileType, lines: List[str]) -> Dict[str, Any]:
        """Extrae información clave según el tipo de archivo"""
        extractors = {
            FileType.PYTHON: self._extract_python_info,
            FileType.JSON: self._extract_json_info,
            FileType.XML: self._extract_xml_info,
            FileType.YAML: self._extract_yaml_info,
            FileType.MARKDOWN: self._extract_markdown_info,
            FileType.TEXT: self._extract_text_info
        }

        extractor = extractors.get(file_type, self._extract_generic_info)
        return extractor(lines)

    def _extract_python_info(self, lines: List[str]) -> Dict[str, Any]:
        """Extrae información clave de archivos Python"""
        info = {
            "classes": [],
            "functions": [],
            "imports": []
        }

        for line in lines:
            stripped = line.strip()

            # Clases
            class_match = re.match(r'^class\s+(\w+)', stripped)
            if class_match:
                info["classes"].append(class_match.group(1))

            # Funciones
            func_match = re.match(r'^\s*def\s+(\w+)', stripped)
            if func_match:
                info["functions"].append(func_match.group(1))

            # Imports
            if stripped.startswith('import ') or stripped.startswith('from '):
                info["imports"].append(stripped)

        return info

    def _extract_json_info(self, lines: List[str]) -> Dict[str, Any]:
        """Extrae información clave de archivos JSON"""
        content = '\n'.join(lines)
        info = {"valid": False, "structure": {}}

        try:
            data = json.loads(content)
            info["valid"] = True
            info["structure"] = self._analyze_json_structure(data)
        except json.JSONDecodeError as e:
            info["error"] = str(e)

        return info

    def _analyze_json_structure(self, data: Any) -> Dict[str, Any]:
        """Analiza la estructura de un objeto JSON"""
        if isinstance(data, dict):
            return {
                "type": "object",
                "keys": len(data),
                "nested": {k: self._analyze_json_structure(v) for k, v in data.items()}
            }
        elif isinstance(data, list):
            return {
                "type": "array",
                "length": len(data),
                "item_types": list(set(type(item).__name__ for item in data[:10]))  # Muestra primeros 10
            }
        else:
            return {"type": type(data).__name__}

    def _extract_xml_info(self, lines: List[str]) -> Dict[str, Any]:
        """Extrae información clave de archivos XML"""
        content = '\n'.join(lines)
        info = {"valid": False, "structure": {}}

        try:
            root = ET.fromstring(content)
            info["valid"] = True
            info["root_tag"] = root.tag
            info["attributes"] = dict(root.attrib)
            info["children_count"] = len(root)
        except ET.ParseError as e:
            info["error"] = str(e)

        return info

    def _extract_yaml_info(self, lines: List[str]) -> Dict[str, Any]:
        """Extrae información clave de archivos YAML"""
        return {"note": "YAML analysis not fully implemented"}

    def _extract_markdown_info(self, lines: List[str]) -> Dict[str, Any]:
        """Extrae información clave de archivos Markdown"""
        info = {"headings": []}

        for line in lines:
            if line.startswith('#'):
                level = len(line.split()[0])
                title = line.strip('#').strip()
                info["headings"].append({"level": level, "title": title})

        return info

    def _extract_text_info(self, lines: List[str]) -> Dict[str, Any]:
        """Extrae información clave de archivos de texto"""
        content = '\n'.join(lines)
        return {
            "characters": len(content),
            "words": len(content.split()),
            "lines": len(lines)
        }

    def _extract_generic_info(self, lines: List[str]) -> Dict[str, Any]:
        """Extracción genérica de información"""
        content = '\n'.join(lines)
        return {
            "characters": len(content),
            "lines": len(lines)
        }

    def query(self, pattern: str, section_type: Optional[str] = None) -> List[FileSection]:
        """Realiza consultas enfocadas en el archivo cargado"""
        if not self.current_report:
            return []

        results = []
        regex = re.compile(pattern, re.IGNORECASE)

        for section in self.current_report.sections:
            if section_type and section.type != section_type:
                continue

            if regex.search(section.name) or regex.search(section.content):
                results.append(section)

        return results

    def get_section_by_name(self, name: str) -> Optional[FileSection]:
        """Obtiene una sección por nombre"""
        if not self.current_report:
            return None

        for section in self.current_report.sections:
            if section.name == name:
                return section

        return None

    def export_report(self, output_path: str, format: str = "json") -> bool:
        """Exporta el reporte actual a un archivo"""
        if not self.current_report:
            return False

        try:
            if format.lower() == "json":
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(self.current_report.to_dict(), f, indent=2, ensure_ascii=False)
            elif format.lower() == "markdown":
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(self.current_report.to_markdown())
            else:
                return False

            return True
        except Exception as e:
            print(f"Error exportando reporte: {e}")
            return False


# FUNCIONES DE UTILIDAD PARA OTRAS IAs
def quick_analyze(file_path: str) -> Dict[str, Any]:
    """
    Función de conveniencia para análisis rápido

    Args:
        file_path: Ruta al archivo a analizar

    Returns:
        Diccionario con información básica del análisis
    """
    analyzer = UniversalFileAnalyzer()
    try:
        report = analyzer.analyze_file(file_path)
        return {
            "success": True,
            "file_type": report.file_type.value,
            "sections_count": len(report.sections),
            "key_info": report.key_info,
            "analysis_time": report.analysis_time
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def analyze_section(file_path: str, section_name: str) -> Optional[Dict[str, Any]]:
    """
    Analiza una sección específica de un archivo

    Args:
        file_path: Ruta al archivo
        section_name: Nombre de la sección a analizar

    Returns:
        Información de la sección o None si no se encuentra
    """
    analyzer = UniversalFileAnalyzer()
    try:
        analyzer.load_file(file_path)
        section = analyzer.get_section_by_name(section_name)
        if section:
            return asdict(section)
        return None
    except Exception as e:
        return {"error": str(e)}


# EJEMPLOS DE USO PARA OTRAS IAs
USAGE_EXAMPLES = """
EJEMPLOS DE USO PARA OTRAS IAs:

1. Análisis básico:
   analyzer = UniversalFileAnalyzer()
   report = analyzer.analyze_file('mi_archivo.json')
   print(f"Tipo: {report.file_type.value}")
   print(f"Secciones: {len(report.sections)}")

2. Consulta enfocada:
   analyzer.load_file('codigo.py')
   clases = analyzer.query(r'^class\s+\w+', 'class')
   for clase in clases:
       print(f"Clase: {clase.name}")

3. Análisis rápido:
   info = quick_analyze('archivo_largo.json')
   if info['success']:
       print(f"Analizado en {info['analysis_time']:.2f}s")

4. Exportar reporte:
   analyzer.export_report('reporte.md', 'markdown')

5. Analizar sección específica:
   section_data = analyze_section('archivo.py', 'MiClase')
   if section_data:
       print(f"Líneas: {section_data['start_line']}-{section_data['end_line']}")
"""


def auto_run():
    """
    Función de auto-ejecución automática del analizador
    Se ejecuta cuando el script se corre directamente
    """
    print("UNIVERSAL FILE ANALYZER - AUTO RUN")
    print("=" * 60)

    analyzer = UniversalFileAnalyzer()
    analyzed_files = []

    # Lista de archivos a analizar automáticamente
    files_to_analyze = [
        "Proyecto/outliner_data.json",
        "Proyecto/README_proyecto.md",
        "Proyecto/simple_animation_blocks_manager.py"
    ]

    for file_path in files_to_analyze:
        try:
            print(f"\n[*] Analizando: {file_path}")
            print("-" * 40)

            report = analyzer.analyze_file(file_path)
            analyzed_files.append(report)

            print(f"[OK] Tipo: {report.file_type.value}")
            print(f"[+] Tamano: {report.file_size:,} bytes")
            print(f"[+] Lineas: {report.total_lines:,}")
            print(f"[+] Secciones: {len(report.sections)}")
            print(f"[+] Tiempo: {report.analysis_time:.2f}s")

            # Mostrar primeras secciones según tipo
            if report.file_type == FileType.JSON:
                print("\n[+] Primeras secciones JSON:")
                for i, section in enumerate(report.sections[:3], 1):
                    print(f"  {i}. {section.name} ({section.type})")
            elif report.file_type == FileType.MARKDOWN:
                headings = [s for s in report.sections if s.type.startswith('heading_')]
                print(f"\n[+] Encabezados encontrados: {len(headings)}")
                for i, heading in enumerate(headings[:3], 1):
                    print(f"  {i}. {heading.name} ({heading.type})")
            elif report.file_type == FileType.PYTHON:
                classes = [s for s in report.sections if s.type == 'class']
                functions = [s for s in report.sections if s.type == 'function']
                print(f"\n[+] Clases: {len(classes)}, Funciones: {len(functions)}")
                for cls in classes[:2]:
                    print(f"  [+] {cls.name} (lineas {cls.start_line}-{cls.end_line})")

            # Exportar reporte Markdown
            md_filename = f"analisis_{Path(file_path).stem}.md"
            analyzer.export_report(md_filename, "markdown")
            print(f"[+] Reporte guardado: {md_filename}")

        except FileNotFoundError:
            print(f"[!] Archivo no encontrado: {file_path}")
        except Exception as e:
            print(f"[!] Error analizando {file_path}: {e}")

    # Resumen final
    print(f"\n[*] ANALISIS COMPLETADO")
    print("=" * 60)
    print(f"[+] Archivos analizados: {len(analyzed_files)}")
    total_time = sum(r.analysis_time for r in analyzed_files)
    total_size = sum(r.file_size for r in analyzed_files)
    total_sections = sum(len(r.sections) for r in analyzed_files)

    print(f"[+] Tiempo total: {total_time:.2f}s")
    print(f"[+] Tamano total: {total_size:,} bytes")
    print(f"[+] Secciones totales: {total_sections}")

    if analyzed_files:
        print("\n[+] Reportes generados:")
        for report in analyzed_files:
            md_filename = f"analisis_{Path(report.file_path).stem}.md"
            print(f"  - {md_filename}")

    print(f"\n[+] Para analisis personalizado, usa:")
    print(f"   from universal_file_analyzer import UniversalFileAnalyzer")
    print(f"   analyzer = UniversalFileAnalyzer()")
    print(f"   report = analyzer.analyze_file('tu_archivo')")

    return analyzed_files


if __name__ == "__main__":
    # Auto-run automático
    auto_run()