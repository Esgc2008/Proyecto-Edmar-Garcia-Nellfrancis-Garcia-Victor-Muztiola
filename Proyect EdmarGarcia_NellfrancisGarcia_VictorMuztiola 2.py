#!/usr/bin/env python3
"""
Buscador y Organizador de Archivos
=================================
Programa que busca archivos en el directorio del usuario y los ordena
alfabéticamente, por año y por tipo de archivo.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import argparse
from collections import defaultdict
import json
import logging

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class FileInfo:
    """Clase para almacenar información de archivos."""
    
    def __init__(self, path: Path):
        self.path = path
        self.name = path.name
        self.extension = path.suffix.lower() if path.suffix else 'sin_extension'
        self.size = path.stat().st_size if path.exists() else 0
        self.modified_time = datetime.fromtimestamp(path.stat().st_mtime) if path.exists() else datetime.now()
        self.created_time = datetime.fromtimestamp(path.stat().st_ctime) if path.exists() else datetime.now()
        self.is_file = path.is_file()
        self.is_dir = path.is_dir()
        self.parent = path.parent
        
    @property
    def year(self) -> int:
        """Obtiene el año de modificación del archivo."""
        return self.modified_time.year
    
    @property
    def type(self) -> str:
        """Obtiene el tipo de archivo (extensión sin punto)."""
        return self.extension[1:] if self.extension.startswith('.') else self.extension
    
    def to_dict(self) -> Dict:
        """Convierte la información a diccionario."""
        return {
            'nombre': self.name,
            'ruta': str(self.path),
            'extension': self.extension,
            'tipo': self.type,
            'tamaño_bytes': self.size,
            'tamaño_legible': self._format_size(self.size),
            'fecha_modificacion': self.modified_time.strftime('%Y-%m-%d %H:%M:%S'),
            'fecha_creacion': self.created_time.strftime('%Y-%m-%d %H:%M:%S'),
            'año': self.year,
            'es_archivo': self.is_file,
            'es_directorio': self.is_dir
        }
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Formatea el tamaño en unidades legibles."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def __repr__(self):
        return f"FileInfo({self.name})"


class FileSearcher:
    """Clase principal para búsqueda y ordenación de archivos."""
    
    def __init__(self, base_path: Optional[Path] = None, max_depth: int = 5):
        """
        Inicializa el buscador de archivos.
        
        Args:
            base_path: Ruta base para la búsqueda (None = directorio usuario)
            max_depth: Profundidad máxima de búsqueda
        """
        self.base_path = base_path or Path.home()
        self.max_depth = max_depth
        self.files: List[FileInfo] = []
        self.ignored_extensions = {'.tmp', '.temp', '.log', '.cache'}
        self.ignored_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}
        
    def search(self, include_dirs: bool = False, show_progress: bool = True) -> List[FileInfo]:
        """
        Busca archivos en el directorio base.
        
        Args:
            include_dirs: Incluir directorios en los resultados
            show_progress: Mostrar progreso durante la búsqueda
            
        Returns:
            Lista de FileInfo encontrados
        """
        self.files = []
        count = 0
        
        logger.info(f"Iniciando búsqueda en: {self.base_path}")
        
        for root, dirs, filenames in os.walk(self.base_path):
            # Filtrar directorios ignorados
            dirs[:] = [d for d in dirs if d not in self.ignored_dirs]
            
            # Verificar profundidad
            current_depth = Path(root).relative_to(self.base_path).parts
            if len(current_depth) > self.max_depth:
                continue
            
            # Procesar archivos
            for filename in filenames:
                file_path = Path(root) / filename
                
                # Verificar extensiones ignoradas
                if file_path.suffix.lower() in self.ignored_extensions:
                    continue
                
                # Verificar que el archivo existe y es accesible
                if not file_path.exists() or not os.access(file_path, os.R_OK):
                    continue
                
                self.files.append(FileInfo(file_path))
                count += 1
                
                if show_progress and count % 100 == 0:
                    logger.info(f"Procesados {count} archivos...")
        
        # Incluir directorios si se solicita
        if include_dirs:
            for root, dirs, _ in os.walk(self.base_path):
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    if dir_name not in self.ignored_dirs:
                        self.files.append(FileInfo(dir_path))
        
        logger.info(f"Búsqueda completada. {len(self.files)} elementos encontrados")
        return self.files
    
    def sort_alphabetic(self, files: List[FileInfo] = None) -> List[FileInfo]:
        """Ordena archivos alfabéticamente."""
        files = files or self.files
        return sorted(files, key=lambda f: f.name.lower())
    
    def sort_by_year(self, files: List[FileInfo] = None) -> List[FileInfo]:
        """Ordena archivos por año (más reciente primero)."""
        files = files or self.files
        return sorted(files, key=lambda f: f.year, reverse=True)
    
    def sort_by_type(self, files: List[FileInfo] = None) -> List[FileInfo]:
        """Ordena archivos por tipo (extensión)."""
        files = files or self.files
        return sorted(files, key=lambda f: (f.type, f.name.lower()))
    
    def group_by_type(self, files: List[FileInfo] = None) -> Dict[str, List[FileInfo]]:
        """Agrupa archivos por tipo."""
        files = files or self.files
        grouped = defaultdict(list)
        for file in files:
            grouped[file.type].append(file)
        return dict(grouped)
    
    def group_by_year(self, files: List[FileInfo] = None) -> Dict[int, List[FileInfo]]:
        """Agrupa archivos por año."""
        files = files or self.files
        grouped = defaultdict(list)
        for file in files:
            grouped[file.year].append(file)
        return dict(grouped)
    
    def filter_by_extension(self, extensions: List[str], files: List[FileInfo] = None) -> List[FileInfo]:
        """
        Filtra archivos por extensión.
        
        Args:
            extensions: Lista de extensiones (ej: ['.txt', '.pdf'])
            files: Lista de archivos a filtrar
            
        Returns:
            Lista filtrada de FileInfo
        """
        files = files or self.files
        return [f for f in files if f.extension in extensions or f.type in extensions]
    
    def filter_by_year_range(self, start_year: int, end_year: int, files: List[FileInfo] = None) -> List[FileInfo]:
        """Filtra archivos por rango de años."""
        files = files or self.files
        return [f for f in files if start_year <= f.year <= end_year]
    
    def generate_report(self, files: List[FileInfo] = None, sort_type: str = 'alphabetic') -> str:
        """
        Genera un reporte formateado de los archivos.
        
        Args:
            files: Lista de archivos
            sort_type: Tipo de ordenación ('alphabetic', 'year', 'type')
            
        Returns:
            String con el reporte
        """
        files = files or self.files
        
        if sort_type == 'alphabetic':
            sorted_files = self.sort_alphabetic(files)
            title = "Ordenado Alfabéticamente"
        elif sort_type == 'year':
            sorted_files = self.sort_by_year(files)
            title = "Ordenado por Año (Más Reciente)"
        elif sort_type == 'type':
            sorted_files = self.sort_by_type(files)
            title = "Ordenado por Tipo"
        else:
            sorted_files = files
            title = "Sin Ordenar"
        
        report = []
        report.append("=" * 80)
        report.append(f"REPORTE DE ARCHIVOS - {title}")
        report.append("=" * 80)
        report.append(f"Directorio base: {self.base_path}")
        report.append(f"Total de archivos: {len(sorted_files)}")
        report.append("-" * 80)
        
        # Agrupar por tipo para estadísticas
        grouped = self.group_by_type(sorted_files)
        report.append("\nESTADÍSTICAS POR TIPO:")
        for type_name, type_files in sorted(grouped.items()):
            total_size = sum(f.size for f in type_files)
            report.append(f"  {type_name}: {len(type_files)} archivos, {FileInfo._format_size(total_size)}")
        
        report.append("-" * 80)
        report.append("\nDETALLE DE ARCHIVOS:")
        
        for i, file in enumerate(sorted_files, 1):
            report.append(f"{i:4d}. {file.name}")
            report.append(f"      Ruta: {file.path}")
            report.append(f"      Tipo: {file.type}")
            report.append(f"      Año: {file.year}")
            report.append(f"      Tamaño: {FileInfo._format_size(file.size)}")
            report.append(f"      Modificado: {file.modified_time.strftime('%Y-%m-%d %H:%M')}")
            if i < len(sorted_files):
                report.append("")
        
        report.append("=" * 80)
        return "\n".join(report)


def parse_arguments():
    """Parse los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description='Buscador y ordenador de archivos para el usuario',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python file_searcher.py --sort alphabetic
  python file_searcher.py --sort year --max-depth 3
  python file_searcher.py --filter .txt,.pdf --sort type
  python file_searcher.py --output report.txt --sort alphabetic
  python file_searcher.py --extensions .jpg,.png --year-range 2020-2024
        """
    )
    
    parser.add_argument(
        '--path',
        type=str,
        default=str(Path.home()),
        help='Ruta base para la búsqueda (default: directorio del usuario)'
    )
    
    parser.add_argument(
        '--sort',
        choices=['alphabetic', 'year', 'type'],
        default='alphabetic',
        help='Tipo de ordenación (default: alphabetic)'
    )
    
    parser.add_argument(
        '--filter',
        type=str,
        help='Filtrar por extensión (ej: .txt,.pdf,.jpg)'
    )
    
    parser.add_argument(
        '--year-range',
        type=str,
        help='Filtrar por rango de años (ej: 2020-2024)'
    )
    
    parser.add_argument(
        '--extensions',
        type=str,
        help='Extensiones a incluir (ej: .txt,.pdf)'
    )
    
    parser.add_argument(
        '--max-depth',
        type=int,
        default=5,
        help='Profundidad máxima de búsqueda (default: 5)'
    )
    
    parser.add_argument(
        '--include-dirs',
        action='store_true',
        help='Incluir directorios en los resultados'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Archivo de salida para el reporte'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Salida en formato JSON'
    )
    
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='Ocultar progreso de búsqueda'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Mostrar información detallada'
    )
    
    return parser.parse_args()


def main():
    """Función principal del programa."""
    args = parse_arguments()
    
    # Configurar logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Crear buscador
        searcher = FileSearcher(
            base_path=Path(args.path),
            max_depth=args.max_depth
        )
        
        # Realizar búsqueda
        files = searcher.search(
            include_dirs=args.include_dirs,
            show_progress=not args.no_progress
        )
        
        if not files:
            logger.warning("No se encontraron archivos.")
            return
        
        # Aplicar filtros
        if args.filter or args.extensions:
            extensions = (args.filter or args.extensions).split(',')
            files = searcher.filter_by_extension(extensions, files)
            logger.info(f"Aplicado filtro de extensiones: {len(files)} archivos restantes")
        
        if args.year_range:
            try:
                start_year, end_year = map(int, args.year_range.split('-'))
                files = searcher.filter_by_year_range(start_year, end_year, files)
                logger.info(f"Aplicado filtro de años: {len(files)} archivos restantes")
            except ValueError:
                logger.error("Formato de año inválido. Use: AAAA-AAAA")
                sys.exit(1)
        
        # Generar reporte
        report = searcher.generate_report(files, args.sort)
        
        # Salida
        if args.json:
            output_data = {
                'base_path': str(searcher.base_path),
                'total_files': len(files),
                'sort_by': args.sort,
                'files': [f.to_dict() for f in files]
            }
            output = json.dumps(output_data, indent=2, ensure_ascii=False)
        else:
            output = report
        
        # Mostrar o guardar
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            logger.info(f"Reporte guardado en: {args.output}")
        else:
            print(output)
    
    except KeyboardInterrupt:
        logger.info("\nBúsqueda interrumpida por el usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()