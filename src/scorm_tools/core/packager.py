"""Empaquetado de un curso SCORM en un archivo `.zip` listo para Moodle."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

from .descriptor import COURSE_DESCRIPTOR_NAME, load_course
from .manifest import render_manifest
from .models import Course
from .moodle import inject_completed_on_view, inject_iframe_resizer
from .optimizer import minify_assets

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


def build_package(
    source_dir: Path,
    output_zip: Path,
    minify: bool = False,
    generate_sourcemap: bool = False,
    inject_resizer: bool = False,
    completed_on_view: bool = False,
) -> Course:
    """Genera `imsmanifest.xml` y empaqueta `source_dir` en `output_zip`.

    Permite optimizaciones automáticas no destructivas (minificación, inyección
    de iframe-resizer y auto-completitud en vista) utilizando un directorio temporal.
    """
    source_dir = source_dir.resolve()
    descriptor_path = source_dir / COURSE_DESCRIPTOR_NAME
    course = load_course(descriptor_path)
    manifest_xml = render_manifest(course)

    output_zip.parent.mkdir(parents=True, exist_ok=True)

    needs_staging = minify or inject_resizer or completed_on_view

    with tempfile.TemporaryDirectory(prefix="scorm-build-") as staging_tmp:
        staging_dir = Path(staging_tmp)
        if needs_staging:
            # Copiar archivos de contenido al staging temporal para no mutar los fuentes del usuario
            for f in _iter_content_files(source_dir):
                rel = f.relative_to(source_dir)
                dest = staging_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)

            if inject_resizer or completed_on_view:
                for html_file in staging_dir.rglob("*.html"):
                    content = html_file.read_text(encoding="utf-8", errors="replace")
                    if inject_resizer:
                        content = inject_iframe_resizer(content)
                    if completed_on_view:
                        content = inject_completed_on_view(content, course.version.value)
                    html_file.write_text(content, encoding="utf-8")

            if minify:
                minify_assets(staging_dir, generate_map=generate_sourcemap)

            package_root = staging_dir
        else:
            package_root = source_dir

        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("imsmanifest.xml", manifest_xml)
            for file_path in _iter_content_files(package_root):
                arcname = file_path.relative_to(package_root).as_posix()
                zf.write(file_path, arcname)

    return course
