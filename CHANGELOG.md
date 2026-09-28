# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/);
versiones según [SemVer](https://semver.org/lang/es/).

## [0.2.0] - 2026-09-28

Primera versión con registro de cambios; lo anterior está en el historial de git.

### Agregado

- **cli**: cumplir el contrato de línea de comandos de LINEAMIENTOS §3.2 (N-ECO-04) (`406af74`)

### Cambiado

- **cli**: tomar la versión de scorm_tools.__version__ en lugar de repetirla (N-ECO-06) (`2ffd13e`)

### Corregido

- **cli**: mostrar los errores de datos como mensajes en lugar de tracebacks (N-ECO-05) (`c63d656`)

### Documentación

- agregar el texto de la licencia GPL-3.0-or-later que declara pyproject (N-ECO-06) (`bb4ea22`)
- incorporar manual de uso integral y referencia tecnica (scorm-tools) (`2ceebcb`)

### Mantenimiento

- **calidad**: verificar errores de Python y dependencias vulnerables (N-ECO-08, N-ECO-13) (`fad33a7`)
