from __future__ import annotations

import json
from pathlib import Path
from io import StringIO

from rich.console import Console

from scorm_tools import __version__
from scorm_tools.core.doctor import ejecutar_diagnostico_doctor
from scorm_tools.core.models import ScormVersion
from scorm_tools.core.scaffold import scaffold_course
from scorm_tools.core.validator import ValidationReport, validate_package
from scorm_tools.core.packager import build_package


def test_package_version_exported() -> None:
    assert isinstance(__version__, str)
    assert len(__version__.split(".")) >= 3


def test_doctor_diagnostic_success() -> None:
    buf = StringIO()
    cons = Console(file=buf, force_terminal=False)
    ok = ejecutar_diagnostico_doctor(cons)
    output = buf.getvalue()

    assert ok is True
    assert "Diagnóstico del Entorno" in output
    assert "Python Runtime" in output
    assert "Esquema: SCORM 1.2" in output
    assert "Esquema: SCORM 2004" in output


def test_validation_report_serialization() -> None:
    rep = ValidationReport(manifest_path="imsmanifest.xml", scorm_version="2004")
    rep.add_warning("Advertencia didáctica")
    rep.add_error("Error crítico de prueba")

    # to_dict
    data = rep.to_dict()
    assert data["manifest_path"] == "imsmanifest.xml"
    assert data["scorm_version"] == "2004"
    assert data["ok"] is False
    assert "Advertencia didáctica" in data["warnings"]
    assert "Error crítico de prueba" in data["errors"]

    # to_json
    raw_json = rep.to_json()
    parsed = json.loads(raw_json)
    assert parsed["ok"] is False
    assert len(parsed["errors"]) == 1

    # to_markdown
    md = rep.to_markdown()
    assert "### Informe de Validación SCORM" in md
    assert "❌ **Inválido" in md
    assert "Advertencia didáctica" in md
    assert "Error crítico de prueba" in md


def test_validation_report_ok_markdown() -> None:
    rep = ValidationReport(manifest_path="imsmanifest.xml", scorm_version="1.2")
    md = rep.to_markdown()
    assert "✓ **Válido**" in md
    assert "#### Errores" not in md


def test_scorm_12_validation_markdown(tmp_path: Path) -> None:
    course_dir = tmp_path / "curso12"
    scaffold_course(course_dir, title="Curso SCORM 1.2", version=ScormVersion.SCORM_12)
    zip_out = tmp_path / "curso12.zip"
    build_package(course_dir, zip_out)

    report = validate_package(zip_out)
    assert report.ok is True
    md = report.to_markdown()
    assert "Versión SCORM:** `1.2`" in md
    assert "✓ **Válido**" in md
