# scorm-tools

> 📖 **Manual de Usuario:** Para una guía exhaustiva de comandos, banderas, arquitectura y ejemplos, consultá el [Manual de Uso](MANUAL.md).

Herramientas de línea de comandos, gestionadas con [`uv`](https://docs.astral.sh/uv/),
para crear, gestionar y validar contenido compatible con el estándar **SCORM**
(1.2 y 2004 3ra/4ta edición), listo para integrarse en plataformas LMS como
**Moodle**.

---

## 🎯 Alcance

### Qué cubre
- Inicialización, validación formal y empaquetado de módulos de aprendizaje interactivo en formato SCORM para Moodle.
- Soporte completo para especificaciones SCORM 1.2 y SCORM 2004 4th Edition.
- Validación rigurosa de manifiestos `imsmanifest.xml` contra los esquemas XSD oficiales provistos localmente.
- Accesibilidad de las páginas HTML del paquete (`validate --a11y`, criterios de WCAG 2.1): idioma, `<title>`, texto alternativo, orden de encabezados, enlaces, campos sin etiqueta, iframes, subtítulos y contraste.
- Scaffolding declarativo de cursos a través de archivo de configuración `scorm.yaml`.
- Generación de paquetes comprimidos `.zip` listos para desplegar en plataformas LMS.

### Qué no cubre (Límites y Delegación)
- Autoría del contenido interactivo HTML, CSS o JavaScript del módulo.
- Calificación directa de entregas de código de software (delegado a `dredd`).
- Gestión de bancos de preguntas Moodle XML o GIFT (delegado a `moodle-toolbox`).

---

## 📋 Requisitos

### Requisitos de Sistema y Entorno
- Multiplataforma. Python >= 3.10.

### Dependencias Externas y Binarios
- Ninguno obligatorio.

### Integración en el Ecosistema
- CLI `scorm-tools`.

---

## Instalación

```bash
uv sync
```

Esto crea el entorno virtual `.venv` e instala el paquete en modo editable.
El comando queda disponible como `uv run scorm-tools ...`, o bien
`uv tool install .` para tenerlo en el `PATH` global.

## Comandos

### `init` — crear un curso de ejemplo

```bash
uv run scorm-tools init ./mi-curso --title "Introducción a Python" --scorm-version 2004-4ed
```

Genera:

- `scorm.yaml`: descriptor del curso (organizaciones, items, resources).
- `index.html`, `scorm-api.js`, `style.css`: SCO de ejemplo con el wrapper de
  comunicación SCORM (API 1.2 y 2004) ya integrado (`ScormAPI.init()`,
  `setCompleted()`, `setScore()`, `commit()`, `terminate()`).

`--scorm-version` acepta `1.2`, `2004-3ed` o `2004-4ed`.

### `build` — generar el `imsmanifest.xml` y empaquetar

```bash
uv run scorm-tools build ./mi-curso -o mi-curso.zip
```

Lee `scorm.yaml`, genera `imsmanifest.xml` (SCORM 1.2 o 2004 según
`version`) y empaqueta todo el contenido en un `.zip` importable directamente
en Moodle (actividad "Paquete SCORM"). Valida el resultado automáticamente
(usar `--no-validate` para omitirlo).

### `validate` — validar un paquete existente

```bash
uv run scorm-tools validate mi-curso.zip
# o sobre una carpeta ya descomprimida
uv run scorm-tools validate ./mi-curso-descomprimido
```

Verifica:

- **Esquema XSD** oficial de IMS Content Packaging + extensiones ADL
  (masteryscore, scormtype, sequencing, etc.) para SCORM 1.2 y 2004.
- **Integridad estructural**: identificadores únicos, `identifierref` de cada
  `item` apuntando a un `resource` existente, archivos referenciados (`href`)
  presentes en el paquete, rutas relativas (sin absolutas ni `\`).
- **Reglas específicas de Moodle**: `imsmanifest.xml` debe estar en la raíz
  del `.zip` (detecta y advierte sobre el error común de subir un `.zip` con
  una carpeta contenedora).

Con `--a11y` (`scorm-tools validate mi-curso.zip --a11y`) revisa además la accesibilidad de cada página HTML del paquete (WCAG 2.1, los mismos
criterios que `myst-tools check-a11y` aplica al fuente MyST). Los errores invalidan el paquete y los
avisos se informan; en `--json`, la lista `accesibilidad` trae cada hallazgo con archivo, línea, regla
y severidad.

| Regla | Severidad | Qué detecta |
| :--- | :--- | :--- |
| `idioma`, `titulo-pagina` | error | `<html>` sin `lang`; página sin `<title>`. |
| `alt-faltante`, `alt-generico` | error, aviso | `<img>` sin `alt` (o `alt=""` si es decorativa); un alt que no describe nada. |
| `encabezado-salto`, `titulo-repetido` | error, aviso | `<h2>` → `<h4>`; más de un `<h1>`. |
| `enlace-generico`, `enlace-sin-texto` | error | Enlaces «acá» o «click aquí»; enlaces sin texto ni `aria-label`. |
| `campo-sin-etiqueta` | error | `<input>`, `<select>` o `<textarea>` sin `<label>` ni `aria-label`. |
| `iframe-sin-titulo`, `video-sin-subtitulos` | error, aviso | `<iframe>` sin `title`; `<video>` sin `<track kind="captions">`. |
| `contraste` | error, o aviso sin fondo declarado | `style="color: …"` con contraste menor que 4.5:1. |

### `info` — inspeccionar la estructura de un curso

```bash
uv run scorm-tools info ./mi-curso
```

Muestra en tablas la jerarquía de items/resources definida en `scorm.yaml`
antes de compilar el paquete.

### `doctor` — diagnóstico del entorno

```bash
uv run scorm-tools doctor
```

Verifica dependencias, esquemas XSD vendorizados y utilidades del sistema.

### Comandos adicionales e integraciones

```bash
# Validar secuenciamiento SCORM 2004
uv run scorm-tools check-sequencing ./mi-curso

# Auditar tamaño de assets y empaquetado para Moodle
uv run scorm-tools check-size ./mi-curso

# Generar configuración recomendada para actividad SCORM en Moodle
uv run scorm-tools moodle-config ./mi-curso

# Nota: `from-gift` usa un parser GIFT propio (soporta MC, V/F, respuesta corta y
# numérica; avisa de lo que no puede representar) porque moodle-toolbox no puede
# importarse desde un `uv tool` aislado. tests/test_paridad_gift_moodle_toolbox.py
# verifica la paridad con el parser del dueño cuando ambos paquetes coexisten.
# Generar módulos SCORM desde guías deckard o cuestionarios GIFT/idkfa
uv run scorm-tools from-deckard guia.yaml -o ./scorm-guia
uv run scorm-tools from-gift preguntas.gift -o ./scorm-preguntas
uv run scorm-tools from-idkfa plantilla.c -o ./scorm-tracing

# Auditar código C embebido en recursos interactivos
uv run scorm-tools audit-c ./mi-curso

# Servidor de desarrollo interactivo con runtime SCORM simulado
uv run scorm-tools playground ./mi-curso --port 8080
```

## Formato de `scorm.yaml`

```yaml
identifier: COURSE-DEMO
title: "Mi curso"
version: "2004-4ed"        # 1.2 | 2004-3ed | 2004-4ed

organizations:
  - identifier: ORG-1
    title: "Mi curso"
    items:
      - identifier: ITEM-1
        title: "Módulo 1"
        resource: RES-1
        mastery_score: 80   # 0-100
        children: []         # items anidados opcionales

resources:
  - identifier: RES-1
    href: index.html
    type: sco               # sco | asset
    files: [index.html, scorm-api.js, style.css]
    dependencies: []
```

## Desarrollo

```bash
uv run pytest        # tests
uv run scorm-tools --help
```

Los esquemas XSD oficiales (IMS CP 1.1.2/1.1, ADL CP 1.2/1.3, ADL SEQ/NAV
1.3, IMS Simple Sequencing 1.0) están vendorizados en
`src/scorm_tools/schemas/` para que la validación funcione sin conexión a
internet.

<!-- p1:referencia:inicio — generado por p1-tools/scripts/readme_generado.py: no editar a mano -->

## Referencia rápida

### Requisitos

- Python ≥ 3.11 y [uv](https://docs.astral.sh/uv/getting-started/installation/).

### Comandos

| Comando | Descripción |
|:--|:--|
| `scorm-tools doctor` | Verificá el estado del entorno, dependencias y esquemas XSD de scorm-tools. |
| `scorm-tools init` | Creá un curso SCORM de ejemplo listo para editar. |
| `scorm-tools build` | Generá imsmanifest.xml y empaquetá el curso en un .zip para Moodle. |
| `scorm-tools validate` | Validá un paquete SCORM contra el esquema XSD y reglas de Moodle. |
| `scorm-tools info` | Mostrá un resumen de la estructura del curso definida en scorm.yaml. |
| `scorm-tools check-sequencing` | Verificá el grafo de secuenciamiento IMSSS y detectá ciclos o actividades huérfanas. |
| `scorm-tools check-size` | Audita el peso del paquete y su desglose por tipo de contenido para Moodle. |
| `scorm-tools moodle-config` | Generá la configuración recomendada de actividad Moodle (moodle_settings.json). |
| `scorm-tools from-deckard` | Convertí una guía de ejercicios de Deckard a un curso SCORM interactivo. |
| `scorm-tools from-gift` | Convertí un banco de preguntas GIFT (Moodle) en un módulo SCORM interactivo autoevaluable. |
| `scorm-tools audit-c` | Auditá fragmentos de código C embebidos en el contenido SCORM contra reglas Ripley. |
| `scorm-tools dredd-sync` | Procesá registros de tracking de Moodle SCORM para integrarlos al calificador docente Dredd. |
| `scorm-tools diagram-memory` | Generá un diagrama Mermaid de memoria Stack y Heap (Bishop/Sebastian) para lecciones SCORM. |
| `scorm-tools from-idkfa` | Convertí una plantilla de tracing C de IDKFA a una lección interactiva SCORM autoevaluable. |
| `scorm-tools playground` | Generá un módulo SCORM interactivo con compilador C WebAssembly en el navegador. |

Ayuda de cada comando: `scorm-tools <comando> -h`.

### Salida JSON

Con `--json`, estos comandos emiten el resultado como JSON por la salida estándar, para usarlo desde scripts, ripley o dredd: `scorm-tools doctor`, `scorm-tools init`, `scorm-tools build`, `scorm-tools validate`, `scorm-tools info`, `scorm-tools check-sequencing`, `scorm-tools check-size`, `scorm-tools moodle-config`, `scorm-tools from-deckard`, `scorm-tools from-gift`, `scorm-tools audit-c`, `scorm-tools dredd-sync`, `scorm-tools diagram-memory`, `scorm-tools from-idkfa`, `scorm-tools playground`. El de `doctor --json` lleva `schema_version` y `ok`.

### Códigos de salida

| Código | Significado |
|:--|:--|
| `0` | Terminó bien (en `doctor`: está todo lo requerido). |
| `1` | El comando encontró problemas (hallazgos, pruebas que fallan, un umbral que no se alcanza) o un dato no se pudo usar (un archivo ilegible, un formato inválido). |
| `2` | Error de uso: comando, opción o argumento inválido. |

<!-- p1:referencia:fin -->
