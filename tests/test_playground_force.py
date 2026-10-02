"""playground no pisa un directorio con archivos sin --force."""

from typer.testing import CliRunner

from scorm_tools.cli import app

runner = CliRunner()


def test_playground_no_pisa_sin_force(tmp_path):
    destino = tmp_path / "pg"
    destino.mkdir()
    (destino / "notas.txt").write_text("mío", encoding="utf-8")
    assert runner.invoke(app, ["playground", str(destino)]).exit_code == 1
    assert (destino / "notas.txt").read_text(encoding="utf-8") == "mío"
    assert runner.invoke(app, ["playground", str(destino), "--force"]).exit_code == 0
