"""Módulos del núcleo (core) de scorm-tools."""

from __future__ import annotations

from .descriptor import CourseDescriptorError, load_course
from .doctor import ejecutar_diagnostico_doctor
from .manifest import render_manifest
from .models import Course, Item, Organization, Resource, ScormVersion
from .packager import build_package
from .scaffold import scaffold_course
from .validator import ValidationReport, validate_package

__all__ = [
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
