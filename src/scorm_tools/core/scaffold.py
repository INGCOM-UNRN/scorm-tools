"""Generación de un curso SCORM de ejemplo (`scorm-tools init`)."""

from __future__ import annotations

import re
from importlib import resources
from pathlib import Path

from jinja2 import Template

from .models import ScormVersion

_STATIC_ASSETS = ("scorm-api.js", "style.css")
_TEMPLATED_ASSETS = ("index.html.j2", "scorm.yaml.j2")


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug or "curso"


def scaffold_course(
    target_dir: Path,
    title: str,
    version: ScormVersion = ScormVersion.SCORM_2004_4ED,
    identifier: str | None = None,
    lang: str = "es",
) -> Path:
    """Crea la estructura mínima de un curso SCORM en `target_dir`.

    Genera `scorm.yaml`, un SCO de ejemplo (`index.html` + JS + CSS) con el
    wrapper de comunicación con el LMS ya integrado.
    """
    if target_dir.exists() and any(target_dir.iterdir()):
        raise FileExistsError(f"El directorio destino no está vacío: {target_dir}")

    target_dir.mkdir(parents=True, exist_ok=True)
    identifier = identifier or f"COURSE-{_slugify(title).upper()}"

    assets_pkg = resources.files("scorm_tools.scaffold_assets")

    for name in _STATIC_ASSETS:
        content = assets_pkg.joinpath(name).read_text(encoding="utf-8")
        (target_dir / name).write_text(content, encoding="utf-8")

    index_tpl = Template(assets_pkg.joinpath("index.html.j2").read_text(encoding="utf-8"))
    (target_dir / "index.html").write_text(
        index_tpl.render(title=title, lang=lang), encoding="utf-8"
    )

    descriptor_tpl = Template(
        assets_pkg.joinpath("scorm.yaml.j2").read_text(encoding="utf-8")
    )
    (target_dir / "scorm.yaml").write_text(
        descriptor_tpl.render(
            identifier=identifier,
            title=title,
            version=version.value,
            description="",
        ),
        encoding="utf-8",
    )

    return target_dir
