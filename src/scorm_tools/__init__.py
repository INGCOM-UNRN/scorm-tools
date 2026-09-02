"""scorm-tools: crear, gestionar y validar contenido SCORM para Moodle."""

from __future__ import annotations

__version__ = "0.1.0"

from .cli import app, main
from .core.descriptor import CourseDescriptorError, load_course
from .core.doctor import ejecutar_diagnostico_doctor
from .core.manifest import render_manifest
from .core.models import Course, Item, Organization, Resource, ScormVersion
from .core.packager import build_package
from .core.scaffold import scaffold_course
from .core.validator import ValidationReport, validate_package

__all__ = [
    "__version__",
    "main",
    "app",
    "Course",
    "CourseDescriptorError",
    "Item",
    "Organization",
    "Resource",
    "ScormVersion",
    "ValidationReport",
    "build_package",
    "ejecutar_diagnostico_doctor",
    "load_course",
    "render_manifest",
    "scaffold_course",
    "validate_package",
]
