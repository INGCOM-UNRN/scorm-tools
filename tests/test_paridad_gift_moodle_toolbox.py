"""SCORM-D0902: from-gift usa un parser propio; este test verifica su paridad con el del dueño.

moodle-toolbox no es dependencia (un `uv tool` aislado no puede importar su paquete),
así que el test se omite si `questions` no está instalado en el entorno.
"""

import pytest

parser_dueno = pytest.importorskip(
    "questions.core.parser", reason="moodle-toolbox (paquete `questions`) no está instalado"
)

from scorm_tools.core.gift_quiz import parsear_gift  # noqa: E402

BANCO = """::mc:: ¿2+2? {=4 ~3 ~5}

::tf:: El cielo es azul. {T}

::corta:: Capital de Francia {=París}

::num:: ¿Pi? {#3.14:0.01}
"""


def test_mismo_conteo_de_preguntas_que_el_parser_del_dueno():
    dueno = parser_dueno.parse_gift(BANCO)
    propio = parsear_gift(BANCO)
    assert len(propio.preguntas) == len(dueno["questions"]) == 4
