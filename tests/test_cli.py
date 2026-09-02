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

    # 8. check-sequencing
    res_seq = runner.invoke(app, ["check-sequencing", str(target_dir)])
    assert res_seq.exit_code == 0
    assert "Árbol de Secuenciamiento" in res_seq.output

    res_seq_json = runner.invoke(app, ["check-sequencing", str(target_dir), "--json"])
    assert res_seq_json.exit_code == 0
    seq_data = json.loads(res_seq_json.output)
    assert seq_data["valid"] is True

    # 9. check-size
    res_size = runner.invoke(app, ["check-size", str(output_zip)])
    assert res_size.exit_code == 0
    assert "Auditoría de Tamaño de Paquete" in res_size.output

    res_size_json = runner.invoke(app, ["check-size", str(output_zip), "--json"])
    assert res_size_json.exit_code == 0
    size_data = json.loads(res_size_json.output)
    assert size_data["total_bytes"] > 0
    assert "html" in size_data["categories_kb"]

    # 10. moodle-config
    moodle_cfg = tmp_path / "moodle_settings.json"
    res_moodle = runner.invoke(app, ["moodle-config", str(target_dir), "-o", str(moodle_cfg)])
    assert res_moodle.exit_code == 0
    assert moodle_cfg.exists()
    moodle_data = json.loads(moodle_cfg.read_text(encoding="utf-8"))
    assert moodle_data["course_title"] == "Curso CLI"
    assert "activity_settings" in moodle_data


def test_cli_build_with_optimization_and_moodle_flags(tmp_path: Path) -> None:
    target_dir = tmp_path / "curso_opt"
    runner.invoke(app, ["init", str(target_dir), "--title", "Curso Opt"])

    out_zip = tmp_path / "curso_opt.zip"
    res = runner.invoke(
        app,
        [
            "build",
            str(target_dir),
            "-o",
            str(out_zip),
            "--minify",
            "--sourcemap",
            "--inject-resizer",
            "--completed-on-view",
        ],
    )
    assert res.exit_code == 0
    assert out_zip.exists()

    # Validar que el zip contenga los archivos procesados
    import zipfile
    with zipfile.ZipFile(out_zip) as zf:
        namelist = zf.namelist()
        assert "style.css" in namelist
        assert "style.css.map" in namelist
        html = zf.read("index.html").decode("utf-8")
        assert "iframe-resizer helper" in html
        assert "completed-on-view auto-marker" in html


def test_cli_from_deckard_roundtrip(tmp_path: Path) -> None:
    guia_yaml = tmp_path / "guia.yaml"
    guia_yaml.write_text("""
nombre: "Guía 1: Punteros"
minutos_totales: 30
ejercicios:
  - id: swap-punteros
    minutos: 15
    bloom: 3
    tema: punteros
""", encoding="utf-8")

    target_dir = tmp_path / "scorm_deckard"
    res = runner.invoke(app, ["from-deckard", str(guia_yaml), str(target_dir), "--build"])
    assert res.exit_code == 0
    assert (target_dir / "scorm.yaml").exists()
    assert (target_dir / "swap-punteros.html").exists()
    assert (target_dir.with_suffix(".zip")).exists()


def test_cli_from_gift_roundtrip(tmp_path: Path) -> None:
    gift_file = tmp_path / "preguntas.gift"
    gift_file.write_text("""
::Punteros en C:: ¿El operador & obtiene la dirección de memoria? {T}

::Desreferencia:: ¿Qué operador desreferencia un puntero? {
  = *
  ~ &
  ~ ->
}
""", encoding="utf-8")

    target_dir = tmp_path / "scorm_gift"
    res = runner.invoke(app, ["from-gift", str(gift_file), str(target_dir), "--title", "Quiz Punteros", "--build"])
    assert res.exit_code == 0
    assert (target_dir / "scorm.yaml").exists()
    assert (target_dir / "index.html").exists()
    assert (target_dir.with_suffix(".zip")).exists()


def test_cli_audit_c(tmp_path: Path) -> None:
    # Caso 1: curso sin infracciones
    curso_limpio = tmp_path / "curso_limpio"
    curso_limpio.mkdir()
    (curso_limpio / "index.html").write_text("<code>int x = 42;</code>", encoding="utf-8")
    res_ok = runner.invoke(app, ["audit-c", str(curso_limpio)])
    assert res_ok.exit_code == 0

    # Caso 2: curso con gets()
    curso_inseguro = tmp_path / "curso_inseguro"
    curso_inseguro.mkdir()
    (curso_inseguro / "index.html").write_text("<code>char buf[10]; gets(buf);</code>", encoding="utf-8")
    res_bad = runner.invoke(app, ["audit-c", str(curso_inseguro)])
    assert res_bad.exit_code != 0
    assert "gets()" in res_bad.output


def test_cli_dredd_sync(tmp_path: Path) -> None:
    tracking_json = tmp_path / "tracking.json"
    tracking_json.write_text(json.dumps([
        {"student_id": "EST-101", "score_raw": 85, "lesson_status": "passed"},
        {"student_id": "EST-102", "score_raw": 40, "lesson_status": "failed"},
    ]), encoding="utf-8")

    out_file = tmp_path / "dredd_report.json"
    res = runner.invoke(app, ["dredd-sync", str(tracking_json), "-o", str(out_file)])
    assert res.exit_code == 0
    assert out_file.exists()
    assert "EST-101" in res.output
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data[0]["passed"] is True
    assert data[1]["passed"] is False
