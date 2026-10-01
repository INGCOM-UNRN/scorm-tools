"""`scorm-tools validate --a11y`: accesibilidad de las páginas HTML del paquete (revisión, 05 §3)."""

import json
from pathlib import Path

from typer.testing import CliRunner

from scorm_tools.cli import app
from scorm_tools.core.accesibilidad import auditar_html
from scorm_tools.core.validator import validate_package
from scorm_tools.models import ScormVersion
from scorm_tools.packager import build_package
from scorm_tools.scaffold import scaffold_course

runner = CliRunner()

PAGINA_OK = """<!DOCTYPE html>
<html lang="es"><head><title>Punteros</title></head>
<body>
<h1>Punteros</h1>
<h2>Uso</h2>
<img src="pila.png" alt="Pila con dos marcos de función">
<img src="borde.png" alt="">
<a href="guia.html">Guía de estilo</a>
<label for="r">Respuesta</label><input id="r" name="r">
<label>Edad <input name="edad"></label>
<input type="submit" value="Enviar">
<iframe title="Video: punteros" src="v.html"></iframe>
<span style="color: #222">texto</span>
</body></html>
"""


def _reglas(contenido: str) -> list:
    return [(h.regla, h.severidad) for h in auditar_html(contenido)]


def test_una_pagina_accesible_no_tiene_hallazgos():
    assert _reglas(PAGINA_OK) == []


def test_reglas_de_la_pagina():
    pagina = """<html><head></head><body>
<h1>A</h1><h3>B</h3><h1>C</h1>
<img src="a.png"><img src="b.png" alt="imagen">
<a href="x.html">acá</a><a href="y.html"><span></span></a>
<input name="nombre"><select name="s"></select>
<iframe src="v"></iframe>
<video src="v.mp4"></video>
<span style="color: #777; background: #555">x</span><span style="color: #aaa">y</span>
</body></html>"""
    assert _reglas(pagina) == [
        ("idioma", "error"), ("titulo-pagina", "error"),
        ("alt-faltante", "error"), ("alt-generico", "aviso"),
        ("encabezado-salto", "error"), ("titulo-repetido", "aviso"),
        ("enlace-generico", "error"), ("enlace-sin-texto", "error"),
        ("iframe-sin-titulo", "error"), ("video-sin-subtitulos", "aviso"),
        ("campo-sin-etiqueta", "error"), ("campo-sin-etiqueta", "error"),
        ("contraste", "error"), ("contraste", "aviso"),
    ]


def test_validate_a11y(tmp_path: Path):
    curso = tmp_path / "curso"
    scaffold_course(curso, title="Curso accesible", version=ScormVersion.SCORM_12)
    paquete = tmp_path / "curso.zip"
    build_package(curso, paquete)
    # El curso de ejemplo es accesible, y sin --a11y no se revisa nada de esto.
    reporte = validate_package(paquete, a11y=True)
    assert reporte.ok and reporte.accesibilidad == []
    assert "accesibilidad" not in validate_package(paquete).to_dict()

    (curso / "index.html").write_text('<html><head><title>x</title></head><body><img src="a.png"></body></html>',
                                      encoding="utf-8")
    build_package(curso, paquete)
    res = runner.invoke(app, ["validate", str(paquete), "--a11y", "--json"])
    assert res.exit_code == 1
    datos = json.loads(res.stdout)
    assert {h["regla"] for h in datos["accesibilidad"]} == {"idioma", "alt-faltante"}
    assert any(e.startswith("Accesibilidad (index.html:1, idioma)") for e in datos["errors"])
    assert runner.invoke(app, ["validate", str(paquete)]).exit_code == 0
