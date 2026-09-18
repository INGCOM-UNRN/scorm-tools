"""Regresión de SCORM-D0303: `diagram-memory` no entendía el JSON real de bishop.

Esperaba `variables` como dict y falló con `AttributeError: 'list' object has no attribute
'items'` frente al único productor del ecosistema: bishop emite `variables` como lista de dicts
(`nombre`, `valor`, `direccion`, `tamanio_bytes`) y los bloques de heap con `direccion`,
`tamanio_bytes` y `esta_liberado`.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from scorm_tools.cli import app
from scorm_tools.core.ecosystem import generate_memory_diagram

runner = CliRunner()

# Forma de `bishop snapshot --json` (recortada): claves en español y sus alias en inglés.
SNAPSHOT_BISHOP = {
    "schema_version": "1.0.0",
    "linea": 4,
    "frames": [
        {
            "funcion": "main", "function": "main",
            "variables": [
                {"nombre": "a", "name": "a", "tipo": "int", "valor": "5", "direccion": "0x7ffc0", "tamanio_bytes": 4},
                {"nombre": "p", "name": "p", "tipo": "int*", "valor": "0x5555a0", "direccion": "0x7ffb8", "es_puntero": True},
            ],
        },
        {"funcion": "suma", "function": "suma", "variables": []},
    ],
    "stack": [
        {
            "funcion": "main", "function": "main",
            "variables": [
                {"nombre": "a", "valor": "5"},
                {"nombre": "p", "valor": "0x5555a0"},
            ],
        },
        {"funcion": "suma", "function": "suma", "variables": []},
    ],
    "heap": [
        {"direccion": "0x5555a0", "address": "0x5555a0", "tamanio_bytes": 16, "esta_liberado": False},
        {"direccion": "0x5555c0", "address": "0x5555c0", "tamanio_bytes": 32, "esta_liberado": True},
    ],
}


def test_el_diagrama_acepta_variables_como_lista_de_dicts_de_bishop():
    diagrama = generate_memory_diagram(SNAPSHOT_BISHOP["stack"], SNAPSHOT_BISHOP["heap"])
    assert "Frame: main" in diagrama and "a: 5" in diagrama and "p: 0x5555a0" in diagrama
    assert "Frame: suma" in diagrama and "sin variables locales" in diagrama


def test_el_heap_de_bishop_usa_direccion_tamanio_y_estado():
    diagrama = generate_memory_diagram(SNAPSHOT_BISHOP["stack"], SNAPSHOT_BISHOP["heap"])
    assert "0x5555a0" in diagrama and "16 bytes (malloc)" in diagrama
    assert "0x5555c0" in diagrama and "32 bytes (liberado)" in diagrama


def test_el_esquema_propio_anterior_sigue_funcionando():
    stack = [{"function": "f", "variables": {"x": 1, "y": 2}}]
    heap = [{"address": "0xH", "size": 8, "tag": "malloc"}]
    diagrama = generate_memory_diagram(stack, heap)
    assert "x: 1" in diagrama and "y: 2" in diagrama and "8 bytes (malloc)" in diagrama


def test_la_cli_procesa_el_snapshot_de_bishop_de_punta_a_punta(tmp_path):
    traza = tmp_path / "snap.json"
    traza.write_text(json.dumps(SNAPSHOT_BISHOP), encoding="utf-8")
    salida = tmp_path / "mem.mmd"
    res = runner.invoke(app, ["diagram-memory", str(traza), "-o", str(salida)])
    assert res.exit_code == 0, res.output
    assert "Error" not in res.output
    assert "Frame: main" in salida.read_text(encoding="utf-8")


@pytest.mark.skipif(not shutil.which("bishop"), reason="requiere bishop instalado")
def test_con_la_salida_real_de_bishop(tmp_path):
    fuente = tmp_path / "p.c"
    fuente.write_text(
        "#include <stdlib.h>\nint main(void) { int a = 5; int *p = malloc(16); *p = a; free(p); return 0; }\n",
        encoding="utf-8",
    )
    snap = subprocess.run(
        ["bishop", "snapshot", str(fuente), "-l", "2", "--json"], capture_output=True, text=True
    )
    if snap.returncode != 0 or not snap.stdout.strip().startswith("{"):
        pytest.skip("bishop no pudo tomar el snapshot en este entorno")
    traza = tmp_path / "real.json"
    traza.write_text(snap.stdout, encoding="utf-8")
    res = runner.invoke(app, ["diagram-memory", str(traza)])
    assert res.exit_code == 0, res.output
    assert "Frame: main" in res.output
