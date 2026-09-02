"""Empaquetado de un curso SCORM en un archivo `.zip` listo para Moodle."""

from __future__ import annotations

import zipfile
from pathlib import Path

from .descriptor import COURSE_DESCRIPTOR_NAME, load_course
from .manifest import render_manifest
from .models import Course

_EXCLUDED_NAMES = {COURSE_DESCRIPTOR_NAME, "imsmanifest.xml", ".git", "__pycache__"}


def _iter_content_files(source_dir: Path):
    for path in sorted(source_dir.rglob("*")):
        if path.is_dir():
            continue
        if any(part in _EXCLUDED_NAMES for part in path.parts):
            continue
        if path.name.startswith("."):
            continue
        yield path


def build_package(source_dir: Path, output_zip: Path) -> Course:
    """Genera `imsmanifest.xml` y empaqueta `source_dir` en `output_zip`.

    `source_dir` debe contener un descriptor `scorm.yaml` en su raíz junto
    con los archivos de contenido (HTML, JS, CSS, medios, etc.) referenciados
    en él.
    """
    source_dir = source_dir.resolve()
    descriptor_path = source_dir / COURSE_DESCRIPTOR_NAME
    course = load_course(descriptor_path)
    manifest_xml = render_manifest(course)

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("imsmanifest.xml", manifest_xml)
        for file_path in _iter_content_files(source_dir):
            arcname = file_path.relative_to(source_dir).as_posix()
            zf.write(file_path, arcname)

    return course
