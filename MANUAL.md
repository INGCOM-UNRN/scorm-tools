# Manual de Uso y Referencia Técnica: scorm-tools

> **SCORM-TOOLS** — Herramientas para crear, empaquetar y validar contenido SCORM (1.2 / 2004) para Moodle.
> **Versión:** `0.1.0` · **CLI principal:** `scorm-tools` · **Plugin Ripley:** `scorm-tools`

---

## 1. Arquitectura y Propósito Pedagógico

`scorm-tools` forma parte del ecosistema de herramientas de la cátedra de Programación 1 (UNRN). Su objetivo central es resolver de forma modular, determinista y automatizada las tareas asociadas a su dominio específico dentro del ciclo de desarrollo, evaluación y aprendizaje de software en C.

### Alcance Funcional (Qué cubre)
- Inicialización, validación formal y empaquetado de módulos de aprendizaje interactivo en formato SCORM para Moodle.
- Soporte completo para especificaciones SCORM 1.2 y SCORM 2004 4th Edition.
- Validación rigurosa de manifiestos `imsmanifest.xml` contra los esquemas XSD oficiales provistos localmente.
- Accesibilidad de las páginas HTML del paquete (`validate --a11y`, criterios de WCAG 2.1): idioma, `<title>`, texto alternativo, orden de encabezados, enlaces, campos sin etiqueta, iframes, subtítulos y contraste.
- Scaffolding declarativo de cursos a través de archivo de configuración `scorm.yaml`.
- Generación de paquetes comprimidos `.zip` listos para desplegar en plataformas LMS.

### Límites de Responsabilidad y Delegación (Qué no cubre)
- Autoría del contenido interactivo HTML, CSS o JavaScript del módulo.
- Calificación directa de entregas de código de software (delegado a `dredd`).
- Gestión de bancos de preguntas Moodle XML o GIFT (delegado a `moodle-toolbox`).

### Principios de Diseño
- **Enfoque Pedagógico:** Diagnósticos y mensajes en español rioplatense orientados a facilitar la comprensión de errores conceptuales.
- **Salida Estructurada Dual:** Soporte nativo para visualización enriquecida en terminal (Rich) y salida parseable para orquestadores (`--json`).
- **Integración Contractual:** Capacidad de emitir secciones de reporte para `dredd` (`dredd-section`) y actuar como satélite orquestado por `ripley`.
- **Idempotencia y Robustez:** Validación de precondiciones y comandos de autodiagnóstico (`doctor`) para verificación del entorno.

---

## 2. Instalación y Requisitos

### Requisitos del Sistema
- **Python:** `>= 3.10` (recomendado Python 3.11 o 3.12).
- **Gestor de paquetes:** [`uv`](https://github.com/astral-sh/uv) (entorno estándar de cátedra).
- **Toolchain C (si aplica):** GCC / Clang, Make, GDB y bibliotecas estándar de desarrollo.

### Instalación en el Entorno de Usuario
Para instalar la herramienta de forma global y aislada en el sistema mediante `uv tool`:
```bash
uv tool install "scorm-tools[ecosistema] @ git+https://github.com/INGCOM-UNRN/scorm-tools"
```

### Verificación de Instalación
Ejecutá el comando `doctor` para constatar que todas las dependencias y binarios requeridos estén presentes y operativos:
```bash
scorm-tools doctor
```

---

## 3. Guía Integral de Comandos (CLI)

| Comando | Descripción Breve |
| :--- | :--- |
| [`scorm-tools doctor`](#doctor) | Verificá el estado del entorno, dependencias y esquemas XSD de scorm-tools. |
| [`scorm-tools init`](#init) | Creá un curso SCORM de ejemplo listo para editar. |
| [`scorm-tools build`](#build) | Generá imsmanifest.xml y empaquetá el curso en un .zip para Moodle. |
| [`scorm-tools validate`](#validate) | Validá un paquete SCORM contra el esquema XSD y reglas de Moodle. |
| [`scorm-tools info`](#info) | Mostrá un resumen de la estructura del curso definida en scorm.yaml. |
| [`scorm-tools check-sequencing`](#checksequencing) | Verificá el grafo de secuenciamiento IMSSS y detectá ciclos o actividades huérfanas. |
| [`scorm-tools check-size`](#checksize) | Audita el peso del paquete y su desglose por tipo de contenido para Moodle. |
| [`scorm-tools moodle-config`](#moodleconfig) | Generá la configuración recomendada de actividad Moodle (moodle_settings.json). |
| [`scorm-tools from-deckard`](#fromdeckard) | Convertí una guía de ejercicios de Deckard a un curso SCORM interactivo. |
| [`scorm-tools from-gift`](#fromgift) | Convertí un banco de preguntas GIFT (Moodle) en un módulo SCORM interactivo autoevaluable. |
| [`scorm-tools audit-c`](#auditc) | Auditá fragmentos de código C embebidos en el contenido SCORM contra reglas Ripley. |
| [`scorm-tools dredd-sync`](#dreddsync) | Procesá registros de tracking de Moodle SCORM para integrarlos al calificador docente Dredd. |
| [`scorm-tools diagram-memory`](#diagrammemory) | Generá un diagrama Mermaid de memoria Stack y Heap (Bishop/Sebastian) para lecciones SCORM. |
| [`scorm-tools from-idkfa`](#fromidkfa) | Convertí una plantilla de tracing C de IDKFA a una lección interactiva SCORM autoevaluable. |
| [`scorm-tools playground`](#playground) | Generá un módulo SCORM interactivo con compilador C WebAssembly en el navegador. |

### `scorm-tools doctor`

Verificá el estado del entorno, dependencias y esquemas XSD de scorm-tools.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--json` | `bool` | `False` | Emite el resultado en formato JSON versionado. |

#### Ejemplo de Invocación
```bash
scorm-tools doctor
```

### `scorm-tools init`

Creá un curso SCORM de ejemplo listo para editar.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `target` | `Path` | Directorio destino del nuevo curso. |
| `title` | `str` | Título del curso. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--scorm-version` | `ScormVersion` | `ScormVersion.SCORM_2004_4ED` | Versión de SCORM (1.2 o 2004). |
| `--id` | `Optional[str]` | `None` | Identificador único del curso (por defecto se deriva del título). |
| `--json` | `bool` | `False` | Emite el resultado en formato JSON versionado. |

#### Ejemplo de Invocación
```bash
scorm-tools init <target> <title>
```

### `scorm-tools build`

Generá imsmanifest.xml y empaquetá el curso en un .zip para Moodle.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `source` | `Path` | Directorio del curso (con scorm.yaml). |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--output`, `-o` | `Optional[Path]` | `None` | Ruta del .zip resultante (por defecto <source>.zip). |
| `--validate/--no-validate` | `bool` | `True` | Validar el paquete tras generarlo. |
| `--minify` | `bool` | `False` | Minificar scripts JavaScript y estilos CSS antes de empaquetar. |
| `--sourcemap` | `bool` | `False` | Generar source maps .map para archivos minificados. |
| `--inject-resizer` | `bool` | `False` | Inyectar helper iframe-resizer para vista enmarcada en Moodle. |
| `--completed-on-view` | `bool` | `False` | Marcar automáticamente el SCO como completado al abrirse. |
| `--json` | `bool` | `False` | Emite el resultado en formato JSON versionado. |

#### Ejemplo de Invocación
```bash
scorm-tools build <source>
```

### `scorm-tools validate`

Validá un paquete SCORM contra el esquema XSD y reglas de Moodle.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `path` | `Path` | Paquete SCORM: directorio o archivo .zip. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--json` | `bool` | `False` | Emite el informe en formato JSON estructurado. |
| `--md`, `--output-md` | `bool` | `False` | Emite el informe en formato Markdown. |
| `--a11y` | `bool` | `False` | Revisa también la accesibilidad de las páginas HTML (WCAG 2.1). |

Con `--a11y` revisa además la accesibilidad de cada página HTML del paquete (WCAG 2.1, los mismos
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

#### Ejemplo de Invocación
```bash
scorm-tools validate <path>
scorm-tools validate mi-curso.zip --a11y
```

### `scorm-tools info`

Mostrá un resumen de la estructura del curso definida en scorm.yaml.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `source` | `Path` | Directorio del curso (con scorm.yaml). |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--json` | `bool` | `False` | Emite la estructura del curso en formato JSON estructurado. |

#### Ejemplo de Invocación
```bash
scorm-tools info <source>
```

### `scorm-tools check-sequencing`

Verificá el grafo de secuenciamiento IMSSS y detectá ciclos o actividades huérfanas.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `source` | `Path` | Directorio del curso (con scorm.yaml). |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--json` | `bool` | `False` | Emite el análisis del grafo en formato JSON estructurado. |

#### Ejemplo de Invocación
```bash
scorm-tools check-sequencing <source>
```

### `scorm-tools check-size`

Audita el peso del paquete y su desglose por tipo de contenido para Moodle.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `path` | `Path` | Paquete SCORM: archivo .zip o directorio. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--max-mb` | `float` | `50.0` | Límite máximo permitido en MB (defecto: 50MB). |
| `--json` | `bool` | `False` | Emite el informe de tamaño en formato JSON estructurado. |

#### Ejemplo de Invocación
```bash
scorm-tools check-size <path>
```

### `scorm-tools moodle-config`

Generá la configuración recomendada de actividad Moodle (moodle_settings.json).

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `source` | `Path` | Directorio del curso (con scorm.yaml). |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--output`, `-o` | `Optional[Path]` | `None` | Ruta donde guardar moodle_settings.json (opcional). |
| `--grade-method` | `int` | `1` | Método de calificación: 1=Más alta, 2=Promedio, 3=Primer intento, 4=Último. |
| `--max-attempts` | `int` | `3` | Número máximo de intentos permitidos. |
| `--popup` | `int` | `0` | Visualización: 0=Enmarcado en página, 1=Nueva ventana. |
| `--json` | `bool` | `False` | Emite la configuración exclusivamente en JSON. |

#### Ejemplo de Invocación
```bash
scorm-tools moodle-config <source>
```

### `scorm-tools from-deckard`

Convertí una guía de ejercicios de Deckard a un curso SCORM interactivo.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `guia` | `Path` | Archivo guia.yaml de ejercicios de Deckard. |
| `target` | `Path` | Directorio destino del paquete SCORM. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--scorm-version` | `ScormVersion` | `ScormVersion.SCORM_2004_4ED` | Versión SCORM (1.2 o 2004). |
| `--build`, `-b` | `bool` | `False` | Compilar automáticamente a archivo .zip tras generar los fuentes. |
| `--json` | `bool` | `False` | Emite el resultado en formato JSON versionado. |

#### Ejemplo de Invocación
```bash
scorm-tools from-deckard <guia> <target>
```

### `scorm-tools from-gift`

Convertí un banco de preguntas GIFT (Moodle) en un módulo SCORM interactivo autoevaluable.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `gift_file` | `Path` | Archivo de preguntas en formato GIFT. |
| `target` | `Path` | Directorio destino del paquete SCORM. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--title`, `-t` | `str` | `Cuestionario SCORM` | Título del cuestionario. |
| `--build`, `-b` | `bool` | `False` | Compilar automáticamente a archivo .zip tras generar los fuentes. |
| `--json` | `bool` | `False` | Emite el resultado en formato JSON versionado. |

#### Ejemplo de Invocación
```bash
scorm-tools from-gift <gift_file> <target>
```

### `scorm-tools audit-c`

Auditá fragmentos de código C embebidos en el contenido SCORM contra reglas Ripley.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `source` | `Path` | Directorio del curso SCORM a auditar. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--json` | `bool` | `False` | Emite los hallazgos en formato JSON estructurado. |

#### Ejemplo de Invocación
```bash
scorm-tools audit-c <source>
```

### `scorm-tools dredd-sync`

Procesá registros de tracking de Moodle SCORM para integrarlos al calificador docente Dredd.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `tracking_file` | `Path` | Archivo JSON con registros de tracking SCORM exportados. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--output`, `-o` | `Optional[Path]` | `None` | Archivo donde guardar el reporte para Dredd. |
| `--json` | `bool` | `False` | Emite el resultado en formato JSON versionado. |

#### Ejemplo de Invocación
```bash
scorm-tools dredd-sync <tracking_file>
```

### `scorm-tools diagram-memory`

Generá un diagrama Mermaid de memoria Stack y Heap (Bishop/Sebastian) para lecciones SCORM.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `trace_file` | `Path` | Archivo JSON con la traza de memoria (frames y heap). |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--output`, `-o` | `Optional[Path]` | `None` | Archivo de salida para el diagrama Mermaid. |
| `--json` | `bool` | `False` | Emite el resultado en formato JSON versionado. |

#### Ejemplo de Invocación
```bash
scorm-tools diagram-memory <trace_file>
```

### `scorm-tools from-idkfa`

Convertí una plantilla de tracing C de IDKFA a una lección interactiva SCORM autoevaluable.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `template` | `Path` | Plantilla C de ejercicio de tracing de IDKFA. |
| `target` | `Path` | Directorio destino del paquete SCORM. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--build`, `-b` | `bool` | `False` | Compilar automáticamente a archivo .zip. |
| `--json` | `bool` | `False` | Emite el resultado en formato JSON versionado. |

#### Ejemplo de Invocación
```bash
scorm-tools from-idkfa <template> <target>
```

### `scorm-tools playground`

Generá un módulo SCORM interactivo con compilador C WebAssembly en el navegador.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `target` | `Path` | Directorio destino del módulo Playground Wasm. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--title`, `-t` | `str` | `Playground C WebAssembly` | Título del módulo. |
| `--build`, `-b` | `bool` | `False` | Compilar automáticamente a archivo .zip. |
| `--json` | `bool` | `False` | Emite el resultado en formato JSON versionado. |

#### Ejemplo de Invocación
```bash
scorm-tools playground <target>
```

---

## 4. Formatos de Salida e Integración con el Ecosistema

### Modo Interactivo / Terminal (Rich)
Por defecto, la herramienta renderiza paneles, árboles y tablas estilizadas para facilitar la lectura del estudiante y docente en terminales modernas con soporte ANSI.

### Modo Estructurado JSON (`--json`)
Para integración con pipelines de CI/CD, scripts de automatización u orquestadores externos, la opción `--json` emite un documento JSON estricto por la salida estándar (`stdout`), dirigiendo cualquier mensaje de logging a `stderr`:
```bash
scorm-tools doctor --json
```

### Integración con Dredd (`dredd-section`)
Cuando la herramienta genera reportes de evaluación para entregas de alumnos, produce una sección Markdown estandarizada conforme al contrato de integración de Dredd (v1.0.0):
```markdown
<!-- dredd-section: scorm-tools, tool=scorm-tools, version=0.1.0, status=ok -->
```
Este encabezado garantiza la agregación determinista de los hallazgos en la rúbrica docente.

### Integración con Ripley
`scorm-tools` está registrada en el catálogo de plugins satélites de Ripley (`SATELLITE_CATALOG`). Puede invocarse directamente a través del motor de evaluación de Ripley configurando el análisis en `ripley.toml`.

---

## 5. Diagnóstico y Códigos de Salida

### Códigos de Retorno (`exit code`)
| Código | Significado |
| :---: | :--- |
| `0` | Ejecución exitosa sin hallazgos críticos ni errores de sintaxis. |
| `1` | Hallazgos pedagógicos detectados, infracción de reglas o advertencias activas. |
| `2` | Error de sintaxis en argumentos CLI o archivo fuente no encontrado. |
| `>2` | Error no recuperable del sistema, fallo de memoria o excepción interna. |

### Diagnóstico del Entorno (`doctor`)
Ante comportamientos inesperados, verificá el estado operativo con:
```bash
scorm-tools doctor
```
Comprueba la presencia de las dependencias requeridas y la integridad de los componentes del paquete.