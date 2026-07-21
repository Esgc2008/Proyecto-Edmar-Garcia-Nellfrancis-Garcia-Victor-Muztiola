#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Buscador y organizador de archivos."""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

EXTENSIONES_IGNORADAS = {'.tmp', '.temp', '.log', '.cache', '.pyc'}
CARPETAS_IGNORADAS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.idea'}


def fmt_num(n):
    return f"{n:,}" if n >= 1000 else str(n)


def fmt_size(b):
    if b == 0:
        return "0.00 B"
    for i, unidad in enumerate(('B', 'KB', 'MB', 'GB', 'TB')):
        if b < 1024 or unidad == 'TB':
            return f"{b / 1024**i:.2f} {unidad}"


class ArchivoInfo(object):
    """Información de un archivo o carpeta."""

    def __init__(self, ruta):
        self.ruta = ruta
        self.nombre = ruta.name
        self.extension = ruta.suffix.lower() or 'sin_extension'
        self.es_archivo = ruta.is_file()
        self.es_carpeta = ruta.is_dir()
        if ruta.exists():
            st = ruta.stat()
            self.tamano = st.st_size
            self.fecha_modificacion = datetime.fromtimestamp(st.st_mtime)
            self.fecha_creacion = datetime.fromtimestamp(st.st_ctime)
        else:
            self.tamano = 0
            self.fecha_modificacion = self.fecha_creacion = datetime.now()

    @property
    def tipo(self):
        return self.extension[1:] if self.extension.startswith('.') else self.extension

    @property
    def anio(self):
        return self.fecha_modificacion.year

    def a_diccionario(self):
        return {
            'nombre': self.nombre,
            'ruta': str(self.ruta),
            'extension': self.extension,
            'tipo': self.tipo,
            'tamano_bytes': self.tamano,
            'tamano_legible': fmt_size(self.tamano),
            'fecha_modificacion': self.fecha_modificacion.strftime('%Y-%m-%d %H:%M:%S'),
            'fecha_creacion': self.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S'),
            'anio': self.anio,
            'es_archivo': self.es_archivo,
            'es_carpeta': self.es_carpeta,
        }


class BuscadorArchivos(object):
    """Busca y organiza archivos dentro de una carpeta."""

    def __init__(self, ruta_base=None, profundidad_maxima=5):
        self.ruta_base = Path(ruta_base) if ruta_base else Path.home()
        self.profundidad_maxima = profundidad_maxima
        self.archivos = []

    def es_ignorado(self, ruta):
        return ruta.is_file() and ruta.suffix.lower() in EXTENSIONES_IGNORADAS

    def _ruta_valida(self, ruta):
        return ruta.exists() and os.access(ruta, os.R_OK) and not self.es_ignorado(ruta)

    def _procesar_archivo(self, ruta, mostrar_progreso, contador):
        if not self._ruta_valida(ruta):
            return contador
        self.archivos.append(ArchivoInfo(ruta))
        contador += 1
        self._mostrar_progreso(contador, mostrar_progreso)
        return contador

    def _mostrar_progreso(self, contador, mostrar_progreso):
        if mostrar_progreso and contador % 100 == 0:
            print(f"Procesados {fmt_num(contador)} archivos...")

    def esta_muy_profundo(self, ruta):
        try:
            return len(ruta.relative_to(self.ruta_base).parts) > self.profundidad_maxima
        except ValueError:
            return False

    def buscar_archivos(self, incluir_carpetas=False, mostrar_progreso=True):
        self.archivos = []
        contador = 0
        print(f"Explorando {self.ruta_base} hasta {self.profundidad_maxima} niveles...")

        for root, dirs, files in os.walk(self.ruta_base, topdown=True):
            actual = Path(root)
            if self.esta_muy_profundo(actual):
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if d not in CARPETAS_IGNORADAS]
            if incluir_carpetas:
                self.archivos.extend(ArchivoInfo(actual / d) for d in dirs)
            for nombre in files:
                ruta = actual / nombre
                contador = self._procesar_archivo(ruta, mostrar_progreso, contador)

        print(f"Listo — encontrados {fmt_num(len(self.archivos))} elementos.")
        return self.archivos

    def ordenar(self, archivos=None, tipo='alfabetico'):
        archivos = archivos or self.archivos
        if tipo == 'anio':
            return sorted(archivos, key=lambda a: a.anio, reverse=True)
        if tipo == 'tipo':
            return sorted(archivos, key=lambda a: (a.tipo, a.nombre.lower()))
        return sorted(archivos, key=lambda a: a.nombre.lower())

    def agrupar(self, archivos=None, clave=lambda a: a.tipo):
        grupos = {}
        for archivo in archivos or self.archivos:
            grupos.setdefault(clave(archivo), []).append(archivo)
        return grupos

    def filtrar_por_extension(self, extensiones, archivos=None):
        valores = {e.lstrip('.').lower() for e in extensiones}
        return [a for a in (archivos or self.archivos) if a.tipo in valores]

    def filtrar_por_rango_anios(self, inicio, fin, archivos=None):
        return [a for a in (archivos or self.archivos) if inicio <= a.anio <= fin]

    def generar_reporte(self, archivos=None, tipo_orden='alfabetico'):
        archivos = self.ordenar(archivos, tipo_orden)
        lineas = [
            '=' * 80,
            f"REPORTE DE ARCHIVOS - {tipo_orden.title()}",
            '=' * 80,
            f"Directorio base: {self.ruta_base}",
            f"Total de elementos: {fmt_num(len(archivos))}",
            '-' * 80,
            '\nEstadísticas por tipo:',
        ]
        for tipo, lista in sorted(self.agrupar(archivos).items()):
            lineas.append(f"  {tipo}: {len(lista)} elementos, {fmt_size(sum(a.tamano for a in lista))}")
        lineas += ['-' * 80, '\nDetalle de elementos:']
        for i, archivo in enumerate(archivos, 1):
            lineas += [
                f"{i:4d}. {archivo.nombre}",
                f"      Ruta: {archivo.ruta}",
                f"      Tipo: {archivo.tipo}",
                f"      Año: {archivo.anio}",
                f"      Tamaño: {fmt_size(archivo.tamano)}",
                f"      Modificado: {archivo.fecha_modificacion.strftime('%Y-%m-%d %H:%M')}",
            ]
            if i < len(archivos):
                lineas.append('')
        lineas.append('=' * 80)
        return '\n'.join(lineas)


def procesar_argumentos():
    parser = argparse.ArgumentParser(description='Buscador y organizador de archivos')
    parser.add_argument('--path', type=Path, default=Path.home(), help='Carpeta donde buscar')
    parser.add_argument('--sort', choices=['alphabetic', 'year', 'type'], default='alphabetic', help='Ordenar por')
    parser.add_argument('--filter', help='Filtrar por extensiones (.txt,.pdf)')
    parser.add_argument('--year-range', help='Filtrar por rango de años AAAA-AAAA')
    parser.add_argument('--max-depth', type=int, default=5, help='Profundidad máxima de búsqueda')
    parser.add_argument('--include-dirs', action='store_true', help='Incluir carpetas en el listado')
    parser.add_argument('--output', help='Guardar reporte en un archivo')
    parser.add_argument('--json', action='store_true', help='Mostrar resultados en formato JSON')
    parser.add_argument('--no-progress', action='store_true', help='No mostrar progreso')
    parser.add_argument('-v', '--verbose', action='store_true', help='Mostrar mensajes de depuración')
    return vars(parser.parse_args())


def main():
    args = procesar_argumentos()
    if args['verbose']:
        print('Modo verbose activado — mostrando detalles')
    
    buscador = BuscadorArchivos(args['path'], args['max_depth'])
    archivos = buscador.buscar_archivos(args['include_dirs'], not args['no_progress'])
    
    if not archivos:
        print('No encontré ningún archivo en la ruta indicada.')
        return
    
    if args['filter']:
        archivos = buscador.filtrar_por_extension(args['filter'].split(','), archivos)
        print(f"Filtro aplicado — quedan {fmt_num(len(archivos))} elementos")
    
    if args['year_range']:
        try:
            # quitar espacios antes de dividir
            year_range_clean = args['year_range'].replace(' ', '')
            inicio, fin = map(int, year_range_clean.split('-'))
            archivos = buscador.filtrar_por_rango_anios(inicio, fin, archivos)
            print(f"Filtro por años aplicado — quedan {fmt_num(len(archivos))} elementos")
        except ValueError:
            print('Error: el rango de años debe tener el formato AAAA-AAAA')
            return
    
    # preparar salida
    if args['json']:
        salida = json.dumps({
            'ruta_base': str(buscador.ruta_base),
            'total': len(archivos),
            'orden': args['sort'],
            'archivos': [a.a_diccionario() for a in archivos]
        }, indent=2, ensure_ascii=False)
    else:
        salida = buscador.generar_reporte(archivos, args['sort'])
    
    # guardar o mostrar
    if args['output']:
        try:
            Path(args['output']).write_text(salida, encoding='utf-8')
            print(f"He guardado el reporte en {args['output']}")
        except Exception as error:
            print(f'Error al guardar el archivo: {error}')
    else:
        print(salida)


if __name__ == '__main__':
    main()