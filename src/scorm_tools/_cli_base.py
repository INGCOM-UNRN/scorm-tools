"""Base compartida de la CLI de scorm-tools: app Typer, consolas y JSON versionado."""

from __future__ import annotations

import json

import typer
from rich.console import Console

from .errores import TyperConErrores

__version__ = "0.1.0"

# La app raíz muestra los errores de datos como mensajes (N-ECO-05).
app = TyperConErrores(
    context_settings={"help_option_names": ["-h", "--help"]},
    name="scorm-tools",
    help="Herramientas para crear, empaquetar y validar contenido SCORM compatible con Moodle.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


SCHEMA_VERSION = "1.0.0"


def _emit_json(comando: str, datos: dict) -> None:
    """JSON versionado por stdout (sin formato Rich, que podría cortar líneas)."""
    payload = {"schema_version": SCHEMA_VERSION, "herramienta": "scorm-tools", "comando": comando}
    payload.update(datos)
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


def version_callback(value: bool) -> None:
    if value:
        console.print(f"scorm-tools {__version__}")
        raise typer.Exit(0)


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        "-V",
        help="Muestra la versión de scorm-tools y sale.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Herramientas para crear, empaquetar y validar contenido SCORM compatible con Moodle."""


