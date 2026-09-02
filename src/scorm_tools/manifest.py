"""Generación del `imsmanifest.xml` a partir de un `Course`."""

from __future__ import annotations

from importlib import resources

from jinja2 import Environment, FunctionLoader

from .models import Course, ScormVersion

_TEMPLATE_BY_VERSION = {
    ScormVersion.SCORM_12: "imsmanifest_12.xml.j2",
    ScormVersion.SCORM_2004_3ED: "imsmanifest_2004.xml.j2",
    ScormVersion.SCORM_2004_4ED: "imsmanifest_2004.xml.j2",
}


def _load_template_source(name: str) -> str:
    template_path = resources.files("scorm_tools.templates").joinpath(name)
    return template_path.read_text(encoding="utf-8")


_env = Environment(
    loader=FunctionLoader(_load_template_source),
    trim_blocks=True,
    lstrip_blocks=False,
    keep_trailing_newline=True,
)


def render_manifest(course: Course) -> str:
    """Renderiza el XML del `imsmanifest.xml` para el curso dado."""
    template_name = _TEMPLATE_BY_VERSION.get(course.version)
    if template_name is None:
        raise ValueError(f"Versión SCORM no soportada: {course.version}")

    template = _env.get_template(template_name)
    organization = course.organization()
    return template.render(course=course, organization=organization)
