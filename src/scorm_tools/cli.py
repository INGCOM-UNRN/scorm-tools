"""CLI de scorm-tools: crear, empaquetar y validar contenido SCORM."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .core.descriptor import CourseDescriptorError, load_course
from .core.doctor import ejecutar_diagnostico_doctor
from .core.models import ScormVersion
from .core.packager import build_package
from .core.scaffold import scaffold_course
from .core.validator import ValidationReport, validate_package

__version__ = "0.1.0"

app = typer.Typer(
    name="scorm-tools",
    help="Herramientas para crear, empaquetar y validar contenido SCORM compatible con Moodle.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


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
        "-V",
        help="Muestra la versión de scorm-tools y sale.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Herramientas para crear, empaquetar y validar contenido SCORM compatible con Moodle."""


@app.command()
def doctor() -> None:
    """Verificá el estado del entorno, dependencias y esquemas XSD de scorm-tools."""
    ok = ejecutar_diagnostico_doctor(console)
    if not ok:
        raise typer.Exit(1)


@app.command()
def init(
    target: Path = typer.Argument(..., help="Directorio destino del nuevo curso."),
    title: str = typer.Option(..., "--title", "-t", help="Título del curso."),
    version: ScormVersion = typer.Option(
        ScormVersion.SCORM_2004_4ED,
        "--scorm-version",
        "--version",
        help="Versión de SCORM (1.2 o 2004).",
    ),
    identifier: Optional[str] = typer.Option(
        None, "--id", help="Identificador único del curso (por defecto se deriva del título)."
    ),
) -> None:
    """Creá un curso SCORM de ejemplo listo para editar."""
    try:
        scaffold_course(target, title=title, version=version, identifier=identifier)
    except FileExistsError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"[green]Curso creado en[/green] {target}")
    console.print("Editá [bold]scorm.yaml[/bold] y el contenido del SCO, luego ejecutá:")
    console.print(f"  scorm-tools build {target} -o {target.name}.zip")


@app.command()
def build(
    source: Path = typer.Argument(..., help="Directorio del curso (con scorm.yaml)."),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Ruta del .zip resultante (por defecto <source>.zip)."
    ),
    validate: bool = typer.Option(
        True, "--validate/--no-validate", help="Validar el paquete tras generarlo."
    ),
) -> None:
    """Generá imsmanifest.xml y empaquetá el curso en un .zip para Moodle."""
    if not source.is_dir():
        err_console.print(f"[red]Error:[/red] {source} no es un directorio válido.")
        raise typer.Exit(1)

    output_zip = output or source.with_suffix(".zip")

    try:
        course = build_package(source, output_zip)
    except CourseDescriptorError as exc:
        err_console.print(f"[red]Error en scorm.yaml:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(
        f"[green]Paquete generado:[/green] {output_zip} "
        f"(SCORM {course.version.value}, identifier={course.identifier})"
    )

    if validate:
        report = validate_package(output_zip)
        _print_report(report)
        if not report.ok:
            raise typer.Exit(1)


@app.command()
def validate(
    path: Path = typer.Argument(..., help="Paquete SCORM: directorio o archivo .zip."),
    json_output: bool = typer.Option(
        False, "--json", help="Emite el informe en formato JSON estructurado."
    ),
    md_output: bool = typer.Option(
        False, "--md", "--output-md", help="Emite el informe en formato Markdown."
    ),
) -> None:
    """Validá un paquete SCORM contra el esquema XSD y reglas de Moodle."""
    if not path.exists():
        err_console.print(f"[red]Error:[/red] {path} no existe.")
        raise typer.Exit(1)

    report = validate_package(path)
    if json_output:
        console.print(report.to_json())
    elif md_output:
        console.print(report.to_markdown())
    else:
        _print_report(report)

    if not report.ok:
        raise typer.Exit(1)


@app.command()
def info(
    source: Path = typer.Argument(..., help="Directorio del curso (con scorm.yaml)."),
    json_output: bool = typer.Option(
        False, "--json", help="Emite la estructura del curso en formato JSON estructurado."
    ),
) -> None:
    """Mostrá un resumen de la estructura del curso definida en scorm.yaml."""
    descriptor = source / "scorm.yaml" if source.is_dir() else source
    try:
        course = load_course(descriptor)
    except CourseDescriptorError as exc:
        err_console.print(f"[red]Error en scorm.yaml:[/red] {exc}")
        raise typer.Exit(1) from exc

    if json_output:
        info_dict = {
            "title": course.title,
            "identifier": course.identifier,
            "version": course.version.value,
            "items": [
                {
                    "identifier": item.identifier,
                    "title": item.title,
                    "resource": item.resource_identifier,
                    "mastery_score": item.mastery_score,
                }
                for item in course.organization().items
            ],
            "resources": [
                {
                    "identifier": r.identifier,
                    "href": r.href,
                    "type": r.scorm_type,
                }
                for r in course.resources
            ],
        }
        console.print(json.dumps(info_dict, indent=2, ensure_ascii=False))
        return

    console.print(f"[bold]{course.title}[/bold] ({course.identifier})")
    console.print(f"Versión SCORM: {course.version.value}")

    table = Table(title="Organización")
    table.add_column("Item")
    table.add_column("Título")
    table.add_column("Resource")
    table.add_column("Mastery score")

    def _walk(items, prefix=""):
        for item in items:
            table.add_row(
                prefix + item.identifier,
                item.title,
                item.resource_identifier or "-",
                str(item.mastery_score) if item.mastery_score is not None else "-",
            )
            _walk(item.children, prefix + "  ")

    _walk(course.organization().items)
    console.print(table)

    res_table = Table(title="Resources")
    res_table.add_column("Identifier")
    res_table.add_column("Href")
    res_table.add_column("Tipo")
    for r in course.resources:
        res_table.add_row(r.identifier, r.href, r.scorm_type)
    console.print(res_table)


def _print_report(report: ValidationReport) -> None:
    if report.manifest_path:
        console.print(f"Manifiesto: [cyan]{report.manifest_path}[/cyan]")
    if report.scorm_version:
        console.print(f"Versión detectada: [cyan]SCORM {report.scorm_version}[/cyan]")

    for warning in report.warnings:
        console.print(f"[yellow]ADVERTENCIA:[/yellow] {warning}")
    for error in report.errors:
        err_console.print(f"[red]ERROR:[/red] {error}")

    if report.ok:
        console.print("[green]✓ Paquete válido.[/green]")
    else:
        err_console.print(f"[red]✗ Paquete inválido ({len(report.errors)} error(es)).[/red]")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
