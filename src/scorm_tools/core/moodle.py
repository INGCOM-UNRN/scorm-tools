"""Compatibilidad específica con Moodle, sanitización de identificadores y configuraciones."""

from __future__ import annotations

import re
from typing import Any

from .models import Course


def sanitize_moodle_identifier(identifier: str, max_length: int = 255) -> str:
    """Sanitiza un identificador para asegurar compatibilidad con tablas de base de datos Moodle."""
    sanitized = re.sub(r"[^a-zA-Z0-9_\-\.]+", "-", identifier).strip("-")
    sanitized = re.sub(r"-+", "-", sanitized)
    if not sanitized:
        sanitized = "item"
    return sanitized[:max_length]


def audit_moodle_compatibility(course: Course) -> list[str]:
    """Audita identificadores y recursos para prevenir errores conocidos de importación en Moodle."""
    warnings: list[str] = []

    # 1. Auditar identifier del curso
    if len(course.identifier) > 255:
        warnings.append(
            f"El identificador del curso '{course.identifier[:30]}...' supera 255 caracteres (Moodle truncará la clave)."
        )
    if re.search(r"[áéíóúÁÉÍÓÚñÑ\s]", course.identifier):
        warnings.append(
            f"El identificador del curso '{course.identifier}' contiene espacios o caracteres no ASCII."
        )

    # 2. Auditar recursos y rutas de archivos
    for res in course.resources:
        if len(res.identifier) > 255:
            warnings.append(f"El resource '{res.identifier}' supera 255 caracteres.")
        if " " in res.href:
            warnings.append(
                f"El recurso '{res.identifier}' usa un href con espacios ('{res.href}'). "
                "Moodle puede generar errores 404 al deszipear."
            )
        for f in res.files:
            if " " in f:
                warnings.append(f"El archivo '{f}' contiene espacios en el nombre.")

    # 3. Auditar ítems de la organización
    def _check_items(items):
        for it in items:
            if len(it.identifier) > 255:
                warnings.append(f"El ítem '{it.identifier[:30]}...' supera 255 caracteres.")
            if re.search(r"[áéíóúÁÉÍÓÚñÑ\s]", it.identifier):
                warnings.append(f"El ítem '{it.identifier}' contiene espacios o caracteres no ASCII.")
            if it.children:
                _check_items(it.children)

    _check_items(course.organization().items)

    return warnings


def generate_moodle_settings(
    course: Course,
    grademethod: int = 1,  # 1=HIGHEST_GRADE, 2=AVERAGE, 3=FIRST_ATTEMPT, 4=LAST_COMPLETED_ATTEMPT
    maxattempt: int = 3,
    popup: int = 0,  # 0=Enmarcado en ventana actual, 1=Nueva ventana
) -> dict[str, Any]:
    """Genera el diccionario de configuración recomendada para importar la actividad en Moodle."""
    has_score = any(
        it.mastery_score is not None
        for it in course.organization().items
    )

    return {
        "course_title": course.title,
        "scorm_identifier": course.identifier,
        "scorm_version": course.version.value,
        "activity_settings": {
            "name": course.title,
            "intro": course.description or f"Actividad interactiva: {course.title}",
            "grademethod": grademethod if has_score else 0,
            "maxgrade": 100 if has_score else 0,
            "maxattempt": maxattempt,
            "whatgrade": 0,  # 0=Highest attempt
            "popup": popup,
            "width": "100%",
            "height": 650,
            "auto": 0,
            "hidetbrowse": 1,  # Ocultar botón de vista previa no evaluada
            "hidenav": 0,
            "skipview": 1,  # Saltar página de estructura si sólo hay 1 SCO
        },
        "recommendations": [
            "Usar 'Modo de visualización: Enmarcado' si el SCO incluye iframe-resizer.",
            "Configurar 'Método de calificación: Calificación más alta' para permitir reintentos formativos.",
            "Deshabilitar 'Forzar nuevo intento' para permitir que el alumno retome la lección donde la dejó.",
        ],
    }


def inject_iframe_resizer(html: str) -> str:
    """Inyecta el script de comunicación de altura dinámica iframe-resizer en el HTML."""
    script_tag = """
<!-- scorm-tools: iframe-resizer helper -->
<script>
(function() {
  function notifyHeight() {
    var height = document.body.scrollHeight || document.documentElement.scrollHeight;
    window.parent.postMessage({ type: 'scorm-resize', height: height }, '*');
  }
  window.addEventListener('load', notifyHeight);
  window.addEventListener('resize', notifyHeight);
})();
</script>
"""
    if "</body>" in html:
        return html.replace("</body>", script_tag + "</body>", 1)
    return html + script_tag


def inject_completed_on_view(html: str, scorm_version: str = "2004") -> str:
    """Inyecta lógica automática para marcar el SCO como completado al cargarse."""
    if "1.2" in scorm_version:
        status_key = "cmi.core.lesson_status"
        commit_fn = "LMSCommit"
        api_obj = "window.API"
    else:
        status_key = "cmi.completion_status"
        commit_fn = "Commit"
        api_obj = "window.API_1484_11"

    script_tag = f"""
<!-- scorm-tools: completed-on-view auto-marker -->
<script>
window.addEventListener('load', function() {{
  try {{
    var api = {api_obj};
    if (api && typeof api.SetValue === 'function') {{
      api.SetValue('{status_key}', 'completed');
      api.{commit_fn}('');
    }} else if (api && typeof api.LMSSetValue === 'function') {{
      api.LMSSetValue('{status_key}', 'completed');
      api.{commit_fn}('');
    }}
  }} catch(e) {{}}
}});
</script>
"""
    if "</body>" in html:
        return html.replace("</body>", script_tag + "</body>", 1)
    return html + script_tag
