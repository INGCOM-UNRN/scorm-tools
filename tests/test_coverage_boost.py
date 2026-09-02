from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from scorm_tools.cli import app
from scorm_tools.core.manifest import render_manifest
from scorm_tools.core.models import Course, ScormVersion
from scorm_tools.core.validator import validate_package

runner = CliRunner()


def test_cli_init_fails_if_target_not_empty(tmp_path: Path) -> None:
    target = tmp_path / "ocupado"
    target.mkdir()
    (target / "archivo.txt").write_text("contenido", encoding="utf-8")

    res = runner.invoke(app, ["init", str(target), "--title", "Curso Ocupado"])
    assert res.exit_code != 0
    assert "no está vacío" in res.output or "Error" in res.output


def test_cli_build_fails_if_source_not_dir(tmp_path: Path) -> None:
    fake = tmp_path / "no_existe"
    res = runner.invoke(app, ["build", str(fake)])
    assert res.exit_code != 0
    assert "no es un directorio válido" in res.output


def test_cli_validate_fails_if_path_not_exists(tmp_path: Path) -> None:
    fake = tmp_path / "inexistente.zip"
    res = runner.invoke(app, ["validate", str(fake)])
    assert res.exit_code != 0
    assert "no existe" in res.output


def test_cli_info_fails_if_invalid_descriptor(tmp_path: Path) -> None:
    invalid_dir = tmp_path / "invalido"
    invalid_dir.mkdir()
    (invalid_dir / "scorm.yaml").write_text("clave_invalida: [1, 2, 3]\n", encoding="utf-8")

    res = runner.invoke(app, ["info", str(invalid_dir)])
    assert res.exit_code != 0
    assert "Error en scorm.yaml" in res.output


def test_validate_package_detects_invalid_zip_archive(tmp_path: Path) -> None:
    corrupt_zip = tmp_path / "corrupto.zip"
    corrupt_zip.write_bytes(b"esto no es un zip valido")

    report = validate_package(corrupt_zip)
    assert not report.ok
    assert any("no es un archivo ZIP válido" in e for e in report.errors)


def test_validate_package_detects_missing_manifest_in_zip(tmp_path: Path) -> None:
    zip_without_manifest = tmp_path / "no_manifest.zip"
    with zipfile.ZipFile(zip_without_manifest, "w") as z:
        z.writestr("readme.txt", "sin manifiesto")

    report = validate_package(zip_without_manifest)
    assert not report.ok
    assert any("No se encontró 'imsmanifest.xml'" in e for e in report.errors)


def test_render_manifest_unsupported_version_raises() -> None:
    class DummyVersion:
        pass

    dummy_course = Course(
        identifier="ID-1",
        title="Test",
        version=DummyVersion(),  # type: ignore
    )
    with pytest.raises(ValueError, match="Versión SCORM no soportada"):
        render_manifest(dummy_course)
