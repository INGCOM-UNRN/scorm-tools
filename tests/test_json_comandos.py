"""Regresión de SCORM-D0601: --json versionado en los comandos que solo imprimían texto."""

import json
from pathlib import Path

from typer.testing import CliRunner

from scorm_tools.cli import app

runner = CliRunner()


def _j(res, comando):
    assert res.exit_code == 0, res.output
    d = json.loads(res.output)
    assert d["schema_version"] == "1.0.0" and d["herramienta"] == "scorm-tools"
    assert d["comando"] == comando
    return d


def test_init_build_json(tmp_path: Path):
    curso = tmp_path / "c"
    d = _j(runner.invoke(app, ["init", str(curso), "--title", "T", "--json"]), "init")
    assert d["titulo"] == "T"
    d = _j(runner.invoke(app, ["build", str(curso), "-o", str(tmp_path / "c.zip"), "--json"]), "build")
    assert d["validacion"]["ok"] is True


def test_from_gift_json(tmp_path: Path):
    gift = tmp_path / "q.gift"
    gift.write_text("::P:: ¿2+2? {=4 ~3}\n", encoding="utf-8")
    d = _j(runner.invoke(app, ["from-gift", str(gift), str(tmp_path / "s"), "--json"]), "from-gift")
    assert d["zip"] is None and isinstance(d["avisos"], list)


def test_playground_json(tmp_path: Path):
    d = _j(runner.invoke(app, ["playground", str(tmp_path / "p"), "--json"]), "playground")
    assert d["directorio"].endswith("p")


def test_diagram_memory_json(tmp_path: Path):
    traza = tmp_path / "t.json"
    traza.write_text(json.dumps({"stack": [], "heap": []}), encoding="utf-8")
    d = _j(runner.invoke(app, ["diagram-memory", str(traza), "--json"]), "diagram-memory")
    assert "diagrama" in d


def test_dredd_sync_json(tmp_path: Path):
    log = tmp_path / "l.json"
    log.write_text("[]", encoding="utf-8")
    d = _j(runner.invoke(app, ["dredd-sync", str(log), "--json"]), "dredd-sync")
    assert d["calificaciones"] == []


def test_doctor_json():
    d = _j(runner.invoke(app, ["doctor", "--json"]), "doctor")
    assert d["ok"] is True
