# scorm-tools

Herramientas de línea de comandos, gestionadas con [`uv`](https://docs.astral.sh/uv/),
para crear, gestionar y validar contenido compatible con el estándar **SCORM**
(1.2 y 2004 3ra/4ta edición), listo para integrarse en plataformas LMS como
**Moodle**.

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
uv run scorm-tools init ./mi-curso --title "Introducción a Python" --version 2004-4ed
```

Genera:

- `scorm.yaml`: descriptor del curso (organizaciones, items, resources).
- `index.html`, `scorm-api.js`, `style.css`: SCO de ejemplo con el wrapper de
  comunicación SCORM (API 1.2 y 2004) ya integrado (`ScormAPI.init()`,
  `setCompleted()`, `setScore()`, `commit()`, `terminate()`).

`--version` acepta `1.2`, `2004-3ed` o `2004-4ed`.

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

### `info` — inspeccionar la estructura de un curso

```bash
uv run scorm-tools info ./mi-curso
```

Muestra en tablas la jerarquía de items/resources definida en `scorm.yaml`
antes de compilar el paquete.

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
