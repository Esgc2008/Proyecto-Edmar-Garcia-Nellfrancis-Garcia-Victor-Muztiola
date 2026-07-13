#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Buscador y organizador de archivos - Proyecto Edmar, Nellfrancis, Victor
====================================================
Este script busca archivos en el directorio que le digas y los ordena
alfabéticamente, por año o por extensión. También los puede agrupar.
Hecho por un humano (o eso creemos).
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import argparse
from collections import defaultdict
import json

# --- Configuración de depuración (a veces lo activo, a veces no) ---
DEBUG = False  # Cambiar a True para ver mensajes

def debug_print(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}")

# FIXME: quizá debería usar logging en lugar de prints, pero bueno

# -------------------------------------------------

class FileInfo:
    """Clase para guardar información de un archivo/directorio."""
    def __init__(self, path):
        self.path = path
        self.name = path.name
        # Si no tiene extensión, le ponemos 'sin_ext'
        self.ext = path.suffix.lower() if path.suffix else 'sin_extension'
        self.size = path.stat().st_size if path.exists() else 0
        self.mod_time = datetime.fromtimestamp(path.stat().st_mtime) if path.exists() else datetime.now()
        self.creat_time = datetime.fromtimestamp(path.stat().st_ctime) if path.exists() else datetime.now()
        self.is_file = path.is_file()
        self.is_dir = path.is_dir()
        self.parent = path.parent
        # Esto lo puse para probar, pero no lo uso (despiste humano)
        self.temp = "no usado"

    @property
    def year(self):
        """Año de modificación (para ordenar)"""
        return self.mod_time.year

    @property
    def tipo(self):
        """Tipo = extensión sin el punto"""
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
    """Clase principal para buscar y ordenar archivos"""
    def __init__(self, base_path=None, max_depth=5):
        # Si no dan ruta, usamos el home del usuario
        self.base_path = base_path if base_path else Path.home()
        self.max_depth = max_depth
        self.files = []   # Lista de FileInfo
        # Extensiones y carpetas que no me interesan (porque son basura)
        self.ignored_ext = {'.tmp', '.temp', '.log', '.cache', '.pyc'}
        self.ignored_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.idea'}
        # Esto es para pruebas, no lo borro
        self.extra_info = ""

    def search(self, include_dirs=False, show_progress=True):
        """Busca archivos recursivamente, con límite de profundidad."""
        self.files = []
        count = 0
        print(f"Buscando en: {self.base_path} (profundidad máxima: {self.max_depth})")
        # Recorremos el árbol
        for root, dirs, filenames in os.walk(self.base_path):
            # Filtramos directorios ignorados (modificamos la lista in-place)
            dirs[:] = [d for d in dirs if d not in self.ignored_dirs]

            # Calculamos profundidad actual
            rel_path = Path(root).relative_to(self.base_path)
            depth = len(rel_path.parts) if rel_path != Path('.') else 0
            if depth > self.max_depth:
                # Si ya superamos la profundidad, no entramos más abajo
                continue

            # Procesar archivos
            for fname in filenames:
                file_path = Path(root) / fname
                # Saltar extensiones molestas
                if file_path.suffix.lower() in self.ignored_ext:
                    continue
                # Comprobar que se puede leer
                if not file_path.exists() or not os.access(file_path, os.R_OK):
                    continue
                self.files.append(FileInfo(file_path))
                count += 1
                if show_progress and count % 100 == 0:
                    print(f"Llevo {count} archivos...", flush=True)

        # Si quieren incluir directorios, los añadimos (pero sin profundizar más)
        if include_dirs:
            for root, dirs, _ in os.walk(self.base_path):
                for dname in dirs:
                    dir_path = Path(root) / dname
                    if dname not in self.ignored_dirs:
                        self.files.append(FileInfo(dir_path))

        print(f"Búsqueda terminada. Encontrados {len(self.files)} elementos.")
        # print("Esto es un mensaje de depuración que me olvidé de quitar")  # lo dejo comentado
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
        """Filtra por lista de extensiones (pueden ser '.txt' o 'txt')"""
        if files is None:
            files = self.files
        result = []
        for f in files:
            for e in exts:
                e_clean = e if e.startswith('.') else '.' + e
                if f.ext == e_clean or f.tipo == e:
                    result.append(f)
                    break
        return result

    def filter_by_year_range(self, start_year, end_year, files=None):
        """Filtra por rango de años (inclusive)"""
        if files is None:
            files = self.files
        return [f for f in files if start_year <= f.year <= end_year]

    def generate_report(self, files=None, sort_type='alphabetic'):
        """Genera un reporte en texto plano con estadísticas y listado."""
        if files is None:
            files = self.files
        # Ordenar según el tipo
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

        # Estadísticas por tipo
        grouped = self.group_by_type(sorted_files)
        lines.append("\nEstadísticas por tipo:")
        for t, flist in sorted(grouped.items()):
            total_size = sum(f.size for f in flist)
            lines.append(f"  {t}: {len(flist)} archivos, {FileInfo._format_size(total_size)}")

        lines.append("-"*80)
        lines.append("\nDetalle de archivos:")
        for i, f in enumerate(sorted_files, 1):
            lines.append(f"{i:4d}. {f.name}")
            lines.append(f"      Ruta: {f.path}")
            lines.append(f"      Tipo: {f.tipo}")
            lines.append(f"      Año: {f.year}")
            lines.append(f"      Tamaño: {FileInfo._format_size(f.size)}")
            lines.append(f"      Modificado: {f.mod_time.strftime('%Y-%m-%d %H:%M')}")
            if i < len(sorted_files):
                lines.append("")
        lines.append("="*80)
        return "\n".join(lines)


# -------------------------------------------------
# Argumentos de línea de comandos (versión simplificada)
# -------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(description='Buscador de archivos con ordenación (hecho por humanos)')
    parser.add_argument('--path', default=str(Path.home()), help='Ruta donde buscar (default: home)')
    parser.add_argument('--sort', choices=['alphabetic','year','type'], default='alphabetic',
                        help='Orden: alphabetic, year, type (default: alphabetic)')
    parser.add_argument('--filter', help='Filtrar por extensiones separadas por coma (ej: .txt,.pdf)')
    parser.add_argument('--year-range', help='Rango de años, ej: 2020-2024')
    parser.add_argument('--max-depth', type=int, default=5, help='Profundidad máxima (default: 5)')
    parser.add_argument('--include-dirs', action='store_true', help='Incluir directorios en la lista')
    parser.add_argument('--output', help='Guardar reporte en archivo')
    parser.add_argument('--json', action='store_true', help='Salida en JSON')
    parser.add_argument('--no-progress', action='store_true', help='No mostrar progreso')
    # Corrijo el error: el flag corto debe ser '-v', no '--v'
    parser.add_argument('-v', '--verbose', action='store_true', help='Modo verbose (mensajes de depuración)')
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
            print("No se encontraron archivos. ¡Qué raro!")
            return

        # Filtros
        if args.filter:
            exts = [e.strip() for e in args.filter.split(',')]
            files = searcher.filter_by_extension(exts, files)
            print(f"Filtro por extensiones: {len(files)} archivos restantes")

        if args.year_range:
            try:
                start, end = map(int, args.year_range.split('-'))
                files = searcher.filter_by_year_range(start, end, files)
                print(f"Filtro por años: {len(files)} archivos restantes")
            except ValueError:
                print("Error: el rango de años debe ser AAAA-AAAA")
                sys.exit(1)

        # Generar reporte
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