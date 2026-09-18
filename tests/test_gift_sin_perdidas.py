"""Regresión de SCORM-D0302: `from-gift` perdía preguntas en silencio.

Un banco de cuatro preguntas (numérica, cloze, V/F con retroalimentación y opción múltiple
con escapes) terminaba con 2 y sin ningún aviso; el cloze se truncaba al primer grupo `{...}`.
"""

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from scorm_tools.cli import app
from scorm_tools.core.ecosystem import gift_to_scorm_sco, parse_gift_questions
from scorm_tools.core.gift_quiz import parsear_gift

runner = CliRunner()

BANCO = r"""
// comentario que no es una pregunta
$CATEGORY: $course$/tema1

::num:: ¿Cuánto es 2+2? {#4}

::cloze:: La capital de Francia es {=París ~Roma} y la de Italia {=Roma ~Milán}.

::tf:: El cielo es azul {T #### Correcto porque sí}

::mc:: ¿Qué imprime `printf("%d", 3 \{ 1)`? {=3 ~4 #es el otro ~5}

::corta:: Capital de Argentina {=Buenos Aires =BA}

::empa:: Emparejá {=a -> 1 =b -> 2}

::ensayo:: Explicá punteros {}
"""


def _por_titulo(resultado):
    return {p["title"]: p for p in resultado.preguntas}


def test_se_leen_los_cuatro_tipos_que_el_cuestionario_corrige():
    res = parsear_gift(BANCO)
    assert set(_por_titulo(res)) == {"num", "tf", "mc", "corta"}


def test_la_numerica_y_la_de_v_f_con_retroalimentacion_ya_no_se_pierden():
    res = _por_titulo(parsear_gift(BANCO))
    assert res["num"]["type"] == "numeric" and res["num"]["answers"] == [{"value": 4.0, "tolerance": 0.0}]
    assert res["tf"]["type"] == "true_false" and res["tf"]["correct"] is True
    assert res["tf"]["feedback"] == "Correcto porque sí"


def test_la_opcion_multiple_conserva_escapes_y_retroalimentacion():
    mc = _por_titulo(parsear_gift(BANCO))["mc"]
    assert mc["prompt"] == '¿Qué imprime `printf("%d", 3 { 1)`?'
    assert [o["correct"] for o in mc["options"]] == [True, False, False]
    assert mc["options"][1]["feedback"] == "es el otro"


def test_la_respuesta_corta_acepta_todas_las_alternativas():
    assert _por_titulo(parsear_gift(BANCO))["corta"]["answers"] == ["Buenos Aires", "BA"]


def test_lo_que_no_se_puede_representar_se_informa_con_su_motivo_y_no_se_trunca():
    omitidas = {o["titulo"]: o["motivo"] for o in parsear_gift(BANCO).omitidas}
    assert set(omitidas) == {"cloze", "empa", "ensayo"}
    assert "2 respuestas incrustadas" in omitidas["cloze"]
    assert "emparejamiento" in omitidas["empa"]
    assert "ensayo" in omitidas["ensayo"]


def test_el_total_leido_mas_el_omitido_es_el_del_banco():
    res = parsear_gift(BANCO)
    assert len(res.preguntas) + len(res.omitidas) == 7  # el comentario y $CATEGORY no cuentan


@pytest.mark.parametrize(
    "cuerpo, esperado",
    [
        ("#4:0.5", [{"value": 4.0, "tolerance": 0.5}]),
        ("#1..3", [{"min": 1.0, "max": 3.0}]),
        ("#=1.5:0.1 =2", [{"value": 1.5, "tolerance": 0.1}, {"value": 2.0, "tolerance": 0.0}]),
        ("#3,14", [{"value": 3.14, "tolerance": 0.0}]),
    ],
)
def test_formatos_de_respuesta_numerica(cuerpo, esperado):
    res = parsear_gift(f"::n:: Valor? {{{cuerpo}}}")
    assert res.preguntas[0]["answers"] == esperado


def test_una_numerica_que_no_se_puede_interpretar_se_informa():
    res = parsear_gift("::n:: Valor? {#abc}")
    assert res.preguntas == [] and "numérica" in res.omitidas[0]["motivo"]


def test_una_linea_vacia_dentro_de_las_llaves_no_parte_la_pregunta():
    res = parsear_gift("::mc:: ¿Cuál?\n{\n=uno\n\n~dos\n}\n")
    assert len(res.preguntas) == 1 and len(res.preguntas[0]["options"]) == 2


def test_parse_gift_questions_conserva_su_contrato_de_lista():
    assert len(parse_gift_questions(BANCO)) == 4


def test_from_gift_avisa_de_lo_omitido_y_no_falla(tmp_path):
    gift = tmp_path / "banco.gift"
    gift.write_text(BANCO, encoding="utf-8")
    res = runner.invoke(app, ["from-gift", str(gift), str(tmp_path / "out")])
    assert res.exit_code == 0, res.output
    salida = " ".join(res.output.split())
    assert "Se omitió «cloze»" in salida and "Se omitió «empa»" in salida and "Se omitió «ensayo»" in salida


def test_si_no_queda_ninguna_pregunta_el_error_dice_por_que(tmp_path):
    gift = tmp_path / "solo_ensayo.gift"
    gift.write_text("::e:: Explicá {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="ensayo"):
        gift_to_scorm_sco(gift, tmp_path / "out")


def test_el_cuestionario_generado_incluye_todas_las_leidas(tmp_path):
    gift = tmp_path / "banco.gift"
    gift.write_text(BANCO, encoding="utf-8")
    gift_to_scorm_sco(gift, tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    incrustado = re.search(r"var questions = (\[.*?\]);\n", html, re.S).group(1)
    assert {q["type"] for q in json.loads(incrustado.replace("<\\/", "</"))} == {
        "numeric", "true_false", "multiple_choice", "short_answer",
    }
    assert "short_answer" in html and "numericaCorrecta" in html


def test_un_cierre_de_script_en_el_texto_no_rompe_el_html(tmp_path):
    gift = tmp_path / "x.gift"
    gift.write_text("::x:: ¿Qué hace </script> en HTML? {=cierra ~abre}\n", encoding="utf-8")
    gift_to_scorm_sco(gift, tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    assert html.count("</script>") == 2  # el de scorm-api.js y el del cuestionario; ninguno colado


def test_la_correccion_en_el_navegador_de_numericas_y_cortas_funciona(tmp_path):
    """Ejecuta con node las funciones de corrección incrustadas en el cuestionario generado."""
    import shutil
    import subprocess

    if not shutil.which("node"):
        pytest.skip("requiere node")
    gift = tmp_path / "q.gift"
    gift.write_text("::c:: Capital {=Buenos Aires =BA}\n\n::n:: Valor {#4:0.5}\n\n::r:: Rango {#1..3}\n", encoding="utf-8")
    gift_to_scorm_sco(gift, tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    funciones = re.search(r"(function normalizar.*?\n      \}\n      questions\.forEach)", html, re.S).group(1)
    funciones = funciones.rsplit("questions.forEach", 1)[0]
    programa = funciones + """
const corta = {answers: ['Buenos Aires', 'BA']};
const num = {answers: [{value: 4, tolerance: 0.5}]};
const rango = {answers: [{min: 1, max: 3}]};
const acepta = (q, t) => q.answers.some(a => normalizar(a) === normalizar(t));
console.log(JSON.stringify([
  acepta(corta, '  buenos   AIRES '), acepta(corta, 'ba'), acepta(corta, 'Córdoba'),
  numericaCorrecta(num, '4'), numericaCorrecta(num, '4,4'), numericaCorrecta(num, '4.6'), numericaCorrecta(num, 'x'),
  numericaCorrecta(rango, '2.5'), numericaCorrecta(rango, '3.1'),
]));
"""
    salida = subprocess.run(["node", "-e", programa], capture_output=True, text=True, check=True).stdout
    assert json.loads(salida) == [True, True, False, True, True, False, False, True, False]
