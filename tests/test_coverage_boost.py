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


def test_sequencing_detects_cycles_and_missing_prereqs() -> None:
    from scorm_tools.core.models import Item, Organization
    from scorm_tools.core.sequencing import analyze_sequencing_graph, validate_sequencing

    # Ciclo A -> B -> A
    item_a = Item(identifier="ITEM-A", title="A", prerequisites=["ITEM-B"])
    item_b = Item(identifier="ITEM-B", title="B", prerequisites=["ITEM-A"])
    item_c = Item(identifier="ITEM-C", title="C", prerequisites=["NON_EXISTENT"])
    item_d = Item(identifier="ITEM-D", title="D", flow=False, choice=False)

    course = Course(
        identifier="COURSE-SEQ",
        title="Curso Ciclos",
        organizations=[Organization(identifier="ORG-1", title="Org", items=[item_a, item_b, item_c, item_d])],
    )

    graph = analyze_sequencing_graph(course)
    assert not graph["valid"]
    assert len(graph["cycles"]) > 0

    errors = validate_sequencing(course)
    assert any("el prerrequisito 'NON_EXISTENT' no existe" in e for e in errors)
    assert any("secuenciamiento circular" in e for e in errors)
    assert any("navegación deshabilitada" in e for e in errors)


def test_cli_check_sequencing_fails_on_broken_course(tmp_path: Path) -> None:
    broken_yaml = tmp_path / "scorm.yaml"
    broken_yaml.write_text("""
identifier: BROKEN-SEQ
title: Curso Roto
organizations:
  - identifier: ORG-1
    title: Org 1
    items:
      - identifier: ITEM-1
        title: Item 1
        prerequisites: [ITEM-2]
      - identifier: ITEM-2
        title: Item 2
        prerequisites: [ITEM-1]
resources: []
""", encoding="utf-8")

    res = runner.invoke(app, ["check-sequencing", str(tmp_path)])
    assert res.exit_code != 0
    assert "ERROR SECUENCIAMIENTO" in res.output


def test_cli_check_size_fails_if_exceeds_threshold(tmp_path: Path) -> None:
    sample_file = tmp_path / "grande.zip"
    sample_file.write_bytes(b"0" * 2000)

    # Fijamos umbral ridículamente bajo (0.0001 MB = ~100 bytes)
    res = runner.invoke(app, ["check-size", str(sample_file), "--max-mb", "0.0001"])
    assert res.exit_code != 0
    assert "supera el umbral" in res.output
