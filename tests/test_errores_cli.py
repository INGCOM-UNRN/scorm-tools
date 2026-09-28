"""Errores de datos como mensajes, no como tracebacks (N-ECO-05).

Se invoca la app como lo hace el ejecutable `scorm-tools` (Typer.__call__),
que es donde actúa TyperConErrores; CliRunner la saltea.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scorm_tools.cli import app
from scorm_tools.errores import describir_error


def _invocar(args, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as salida:
        app(args, prog_name="scorm-tools")
    return salida.value.code


@pytest.mark.parametrize("comando", ["info", "check-sequencing", "moodle-config"])
def test_manifiesto_que_no_es_yaml_es_un_mensaje(comando, tmp_path: Path, monkeypatch, capsys):
    (tmp_path / "archivo.c").write_text("int main(void) { a: b: c; }\n")
    codigo = _invocar([comando, "archivo.c"], monkeypatch, tmp_path)
    err = capsys.readouterr().err
    assert codigo == 1
    assert "no es un YAML válido" in err
    assert "Traceback" not in err


def test_playground_sobre_un_archivo_existente(tmp_path: Path, monkeypatch, capsys):
    (tmp_path / "archivo.c").write_text("int x;\n")
    codigo = _invocar(["playground", "archivo.c"], monkeypatch, tmp_path)
    assert codigo == 1
    assert "ya existe" in capsys.readouterr().err


def test_p1_depurar_deja_ver_la_excepcion(tmp_path: Path, monkeypatch):
    (tmp_path / "archivo.c").write_text("a: b: c\n")
    monkeypatch.setenv("P1_DEPURAR", "1")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(yaml.YAMLError):
        app(["info", "archivo.c"], prog_name="scorm-tools")


def test_describir_error_incluye_linea():
    try:
        yaml.safe_load("clave: valor\notra: a: b\n")
    except yaml.YAMLError as error:
        assert "línea 2" in describir_error(error)
