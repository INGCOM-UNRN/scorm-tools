from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from scorm_tools.cli import app
from scorm_tools import __version__

runner = CliRunner()


def test_cli_version_flags() -> None:
    res1 = runner.invoke(app, ["--version"])
    assert res1.exit_code == 0
    assert __version__ in res1.output

    res2 = runner.invoke(app, ["-V"])
    assert res2.exit_code == 0
    assert __version__ in res2.output


def test_cli_help() -> None:
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "Herramientas para crear" in res.output
    assert "doctor" in res.output
    assert "init" in res.output
    assert "build" in res.output
    assert "validate" in res.output
    assert "info" in res.output


def test_cli_doctor() -> None:
    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 0
    assert "Diagnóstico del Entorno" in res.output
    assert "✓ OK" in res.output


def test_cli_lifecycle_roundtrip(tmp_path: Path) -> None:
    target_dir = tmp_path / "mi_curso"
    
    # 1. init
    res_init = runner.invoke(app, ["init", str(target_dir), "--title", "Curso CLI", "--scorm-version", "2004-4ed"])
    assert res_init.exit_code == 0
    assert (target_dir / "scorm.yaml").exists()

    # 2. info
    res_info = runner.invoke(app, ["info", str(target_dir)])
    assert res_info.exit_code == 0
    assert "Curso CLI" in res_info.output

    # 3. info --json
    res_info_json = runner.invoke(app, ["info", str(target_dir), "--json"])
    assert res_info_json.exit_code == 0
    info_data = json.loads(res_info_json.output)
    assert info_data["title"] == "Curso CLI"
    assert info_data["version"] == "2004-4ed"

    # 4. build
    output_zip = tmp_path / "mi_curso.zip"
    res_build = runner.invoke(app, ["build", str(target_dir), "-o", str(output_zip)])
    assert res_build.exit_code == 0
    assert output_zip.exists()

    # 5. validate standard
    res_val = runner.invoke(app, ["validate", str(output_zip)])
    assert res_val.exit_code == 0
    assert "✓ Paquete válido." in res_val.output

    # 6. validate --json
    res_val_json = runner.invoke(app, ["validate", str(output_zip), "--json"])
    assert res_val_json.exit_code == 0
    val_data = json.loads(res_val_json.output)
    assert val_data["ok"] is True
    assert val_data["scorm_version"] in ("1.2", "2004")

    # 7. validate --md
    res_val_md = runner.invoke(app, ["validate", str(output_zip), "--md"])
    assert res_val_md.exit_code == 0
    assert "### Informe de Validación SCORM" in res_val_md.output
    assert "✓ **Válido**" in res_val_md.output
