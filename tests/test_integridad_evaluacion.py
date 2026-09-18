"""Regresión de SCORM-D0301: nada se aprueba sin evaluar.

La actividad de tracing marcaba `success_status='passed'` y score 100 eligiera
lo que eligiera el estudiante, y el playground imprimía una salida de
compilación inventada ("Compilando código C con clang-wasm...") para después
aprobar igual. Ese `passed` viaja al seguimiento que dredd-sync consolida para
el docente.
"""

import re
from pathlib import Path

import pytest

from scorm_tools.core.ecosystem import (
    scaffold_wasm_playground,
    idkfa_to_scorm_tracing,
    parse_idkfa_template,
)

PLANTILLA = """// ¿Cuál es la salida del programa?
#include <stdio.h>
int main(void) { printf("42"); return 0; }

/*name
Tracing simple
*/

/*correcta
42
*/

/*opciones
0
Error de compilación.
*/
"""

CALCULADA = """// ¿Cuál es el valor final?
#include <stdio.h>
int main(void) { return 0; }

/*name
Con expresion
*/

/*correcta
# __loop_limit__ * __multiplier__
*/

/*opciones
Error de compilación.
*/
"""


@pytest.fixture
def plantilla(tmp_path):
    ruta = tmp_path / "tracing.c"
    ruta.write_text(PLANTILLA, encoding="utf-8")
    return ruta


def test_se_parsea_la_respuesta_correcta(plantilla):
    assert parse_idkfa_template(plantilla.read_text())["correcta"] == "42"


def test_la_actividad_compara_la_respuesta(tmp_path, plantilla):
    destino = tmp_path / "curso"
    idkfa_to_scorm_tracing(plantilla, destino)
    html = (destino / "index.html").read_text(encoding="utf-8")

    indice = int(re.search(r"OPCION_CORRECTA = (\d+)", html).group(1))
    opciones = re.findall(r"<code>(.*?)</code>", html)
    assert opciones[indice] == "42"
    assert "acerto ? 'passed' : 'failed'" in html


def test_no_hay_aprobado_incondicional(tmp_path, plantilla):
    destino = tmp_path / "curso"
    idkfa_to_scorm_tracing(plantilla, destino)
    html = (destino / "index.html").read_text(encoding="utf-8")
    assert "SetValue('cmi.success_status', 'passed')" not in html


def test_sin_respuesta_declarada_no_emite_veredicto(tmp_path):
    """idkfa resuelve la expresión al sortear; acá no se puede, así que no se
    aprueba ni se desaprueba: se registra la elección y corrige el docente."""
    ruta = tmp_path / "calculada.c"
    ruta.write_text(CALCULADA, encoding="utf-8")
    destino = tmp_path / "curso"
    idkfa_to_scorm_tracing(ruta, destino)
    html = (destino / "index.html").read_text(encoding="utf-8")

    # El paquete no lleva lógica de aprobación que no puede usar.
    assert "OPCION_CORRECTA" not in html
    assert "'passed'" not in html
    assert "equipo docente" in html
    assert "cmi.completion_status" in html


def test_el_playground_no_finge_compilar_ni_aprueba(tmp_path):
    destino = tmp_path / "playground"
    scaffold_wasm_playground(destino, "Playground")
    html = (destino / "index.html").read_text(encoding="utf-8")

    assert "clang-wasm" not in html
    assert "Ejecución completada con código 0" not in html
    assert "SetValue('cmi.success_status', 'passed')" not in html
    assert "cmi.completion_status" in html
