#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Buscador y organizador de archivos - Proyecto Edmar, Nellfrancis, Victor
====================================================
Este script explora una carpeta y sus subcarpetas para encontrar archivos.
Los resultados se pueden ordenar por nombre, por año o por tipo de archivo,
y también se puede guardar un reporte en texto o JSON.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import argparse
from collections import defaultdict
import json

DEBUG = False

def debug_print(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}")

# -------------------------------------------------

class FileInfo:
    """Información de un archivo o directorio."""
    def __init__(self, path):
        self.path = path
        self.name = path.name
        self.ext = path.suffix.lower() if path.suffix else 'sin_extension'
        self.size = path.stat().st_size if path.exists() else 0
        self.mod_time = datetime.fromtimestamp(path.stat().st_mtime) if path.exists() else datetime.now()
        self.creat_time = datetime.fromtimestamp(path.stat().st_ctime) if path.exists() else datetime.now()
        self.is_file = path.is_file()
        self.is_dir = path.is_dir()
        self.parent = path.parent

    @property
    def year(self):
        """Año de última modificación."""
        return self.mod_time.year

    @property
    def tipo(self):
        """Tipo de archivo sin el punto inicial."""
        return self.ext[1:] if self.ext.startswith('.') else self.ext

    def to_dict(self):
        """Convierte a diccionario (para JSON)"""
        return {
            'nombre': self.name,
            'ruta': str(self.path),
            'extension': self.ext,
            'tipo': self.tipo,
            'tamaño_bytes': self.size,
            'tamaño_legible': self._format_size(self.size),
            'fecha_modificacion': self.mod_time.strftime('%Y-%m-%d %H:%M:%S'),
            'fecha_creacion': self.creat_time.strftime('%Y-%m-%d %H:%M:%S'),
            'año': self.year,
            'es_archivo': self.is_file,
            'es_directorio': self.is_dir
        }

    @staticmethod
    def _format_size(size_bytes):
        """Formato bonito de tamaño"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def __repr__(self):
        return f"FileInfo({self.name})"


# -------------------------------------------------

class FileSearcher:
    """Busca, ordena y agrupa archivos en un camino dado."""
    def __init__(self, base_path=None, max_depth=5):
        self.base_path = base_path if base_path else Path.home()
        self.max_depth = max_depth
        self.files = []
        self.ignored_ext = {'.tmp', '.temp', '.log', '.cache', '.pyc'}
        self.ignored_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.idea'}

    def _is_ignored_directory(self, dir_name):
        return dir_name in self.ignored_dirs

    def _is_ignored_file(self, path):
        return path.suffix.lower() in self.ignored_ext or not path.exists() or not os.access(path, os.R_OK)

    def _is_too_deep(self, root):
        rel_path = Path(root).relative_to(self.base_path)
        depth = len(rel_path.parts) if rel_path != Path('.') else 0
        return depth > self.max_depth

    def _file_infos_in_root(self, root, filenames):
        return (
            FileInfo(Path(root) / fname)
            for fname in filenames
            if not self._is_ignored_file(Path(root) / fname)
        )

    def _directory_infos(self):
        return (
            FileInfo(Path(root) / dname)
            for root, dirs, _ in os.walk(self.base_path)
            for dname in dirs
            if not self._is_ignored_directory(dname)
        )

    def _report_progress(self, count, show_progress):
        if show_progress and count % 100 == 0:
            print(f"Ya procesados {count} archivos...", flush=True)

    def search(self, include_dirs=False, show_progress=True):
        """Busca archivos recursivamente, con límite de profundidad."""
        self.files = []
        count = 0
        print(f"Explorando {self.base_path} hasta {self.max_depth} niveles de profundidad...")

        for root, dirs, filenames in os.walk(self.base_path):
            dirs[:] = [d for d in dirs if not self._is_ignored_directory(d)]

            if self._is_too_deep(root):
                continue

            for file_info in self._file_infos_in_root(root, filenames):
                self.files.append(file_info)
                count += 1
                self._report_progress(count, show_progress)

        if include_dirs:
            self.files.extend(self._directory_infos())

        print(f"Búsqueda completa. Encontrados {len(self.files)} elementos.")
        return self.files

    def sort_alphabetic(self, files=None):
        """Orden alfabético (sin distinción mayúsculas)"""
        if files is None:
            files = self.files
        return sorted(files, key=lambda f: f.name.lower())

    def sort_by_year(self, files=None):
        """Orden por año (más reciente primero)"""
        if files is None:
            files = self.files
        return sorted(files, key=lambda f: f.year, reverse=True)

    def sort_by_type(self, files=None):
        """Orden por tipo (extensión) y luego nombre"""
        if files is None:
            files = self.files
        return sorted(files, key=lambda f: (f.tipo, f.name.lower()))

    def group_by_type(self, files=None):
        """Agrupa por tipo (devuelve dict)"""
        if files is None:
            files = self.files
        grouped = defaultdict(list)
        for f in files:
            grouped[f.tipo].append(f)
        return dict(grouped)

    def group_by_year(self, files=None):
        """Agrupa por año"""
        if files is None:
            files = self.files
        grouped = defaultdict(list)
        for f in files:
            grouped[f.year].append(f)
        return dict(grouped)

    def filter_by_extension(self, exts, files=None):
        """Filtra por lista de extensiones (pueden ser '.txt' o 'txt')."""
        if files is None:
            files = self.files
        normalized = {e if e.startswith('.') else '.' + e for e in exts}
        return [f for f in files if f.ext in normalized or f.tipo in normalized]

    def filter_by_year_range(self, start_year, end_year, files=None):
        """Filtra por rango de años (inclusive)"""
        if files is None:
            files = self.files
        return [f for f in files if start_year <= f.year <= end_year]

    def generate_report(self, files=None, sort_type='alphabetic'):
        """Genera un reporte en texto plano con estadísticas y listado."""
        if files is None:
            files = self.files
        if sort_type == 'alphabetic':
            sorted_files = self.sort_alphabetic(files)
            title = "Ordenado Alfabéticamente"
        elif sort_type == 'year':
            sorted_files = self.sort_by_year(files)
            title = "Ordenado por Año (más reciente primero)"
        elif sort_type == 'type':
            sorted_files = self.sort_by_type(files)
            title = "Ordenado por Tipo de Archivo"
        else:
            sorted_files = files
            title = "Sin ordenar"

        lines = []
        lines.append("="*80)
        lines.append(f"REPORTE DE ARCHIVOS - {title}")
        lines.append("="*80)
        lines.append(f"Directorio base: {self.base_path}")
        lines.append(f"Total de elementos: {len(sorted_files)}")
        lines.append("-"*80)

        grouped = self.group_by_type(sorted_files)
        lines.append("\nEstadísticas por tipo:")
        for t, archivos in sorted(grouped.items()):
            total_size = sum(archivo.size for archivo in archivos)
            lines.append(f"  {t}: {len(archivos)} elementos, {FileInfo._format_size(total_size)}")

        lines.append("-"*80)
        lines.append("\nDetalle de elementos:")
        for i, archivo in enumerate(sorted_files, 1):
            lines.append(f"{i:4d}. {archivo.name}")
            lines.append(f"      Ruta: {archivo.path}")
            lines.append(f"      Tipo: {archivo.tipo}")
            lines.append(f"      Año: {archivo.year}")
            lines.append(f"      Tamaño: {FileInfo._format_size(archivo.size)}")
            lines.append(f"      Modificado: {archivo.mod_time.strftime('%Y-%m-%d %H:%M')}")
            if i < len(sorted_files):
                lines.append("")
        lines.append("="*80)
        return "\n".join(lines)


# -------------------------------------------------
# Opciones del script
# -------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(description='Buscador de archivos amigable y fácil de usar')
    parser.add_argument('--path', default=str(Path.home()), help='Carpeta donde empezar la búsqueda; si no lo dices, uso tu carpeta home')
    parser.add_argument('--sort', choices=['alphabetic','year','type'], default='alphabetic',
                        help='Ordenar los resultados: alphabetic, year o type')
    parser.add_argument('--filter', help='Filtrar por extensiones separadas por coma, por ejemplo .txt,.pdf')
    parser.add_argument('--year-range', help='Rango de años para filtrar, ej: 2020-2024')
    parser.add_argument('--max-depth', type=int, default=5, help='Profundidad máxima de búsqueda')
    parser.add_argument('--include-dirs', action='store_true', help='Incluir carpetas también en el listado')
    parser.add_argument('--output', help='Guardar el reporte en un archivo')
    parser.add_argument('--json', action='store_true', help='Mostrar resultados en formato JSON')
    parser.add_argument('--no-progress', action='store_true', help='No mostrar mensajes de progreso durante la búsqueda')
    parser.add_argument('-v', '--verbose', action='store_true', help='Mostrar mensajes adicionales para depuración')
    return parser.parse_args()


def main():
    args = parse_args()
    global DEBUG
    if args.verbose:
        DEBUG = True
        print("Modo DEBUG activado")

    try:
        searcher = FileSearcher(base_path=Path(args.path), max_depth=args.max_depth)
        files = searcher.search(include_dirs=args.include_dirs, show_progress=not args.no_progress)

        if not files:
            print("No se encontraron archivos en la ruta indicada.")
            return

        if args.filter:
            exts = [e.strip() for e in args.filter.split(',')]
            files = searcher.filter_by_extension(exts, files)
            print(f"Aplicado filtro de extensiones: {len(files)} elementos restantes")

        if args.year_range:
            try:
                start, end = map(int, args.year_range.split('-'))
                files = searcher.filter_by_year_range(start, end, files)
                print(f"Aplicado filtro por años: {len(files)} elementos restantes")
            except ValueError:
                print("Error: el rango de años debe tener el formato AAAA-AAAA")
                sys.exit(1)

        # Preparar el reporte para mostrar o guardar
        report = searcher.generate_report(files, args.sort)

        if args.json:
            data = {
                'base_path': str(searcher.base_path),
                'total': len(files),
                'sort': args.sort,
                'files': [f.to_dict() for f in files]
            }
            output = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            output = report

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Reporte guardado en {args.output}")
        else:
            print(output)

    except KeyboardInterrupt:
        print("\n¡Interrupción! El usuario nos ha detenido.")
        sys.exit(0)
    except Exception as e:
        print(f"Error inesperado: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()