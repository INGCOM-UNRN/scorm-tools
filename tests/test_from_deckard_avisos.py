"""Regresión de SCORM-D0904: campos ausentes en guia.yaml no degradan en silencio."""

import json

from typer.testing import CliRunner

from scorm_tools.cli import app

runner = CliRunner()


def test_guia_incompleta_emite_avisos(tmp_path):
    guia = tmp_path / "guia.yaml"
    guia.write_text("ejercicios:\n  - id: e1\n  - {}\n", encoding="utf-8")
    res = runner.invoke(app, ["from-deckard", str(guia), str(tmp_path / "s"), "--json"])
    assert res.exit_code == 0, res.output
    avisos = json.loads(res.stdout)["avisos"]
    assert any("nombre" in a for a in avisos)
    assert any("ejercicio 1: falta `minutos`" in a for a in avisos)
    assert any("ejercicio 2: falta `id`" in a for a in avisos)


def test_guia_completa_sin_avisos(tmp_path):
    guia = tmp_path / "guia.yaml"
    guia.write_text(
        "nombre: G\nejercicios:\n  - {id: e1, minutos: 10, bloom: 2, tema: X}\n", encoding="utf-8"
    )
    res = runner.invoke(app, ["from-deckard", str(guia), str(tmp_path / "s"), "--json"])
    assert json.loads(res.stdout)["avisos"] == []
