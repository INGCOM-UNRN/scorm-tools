"""CLI de scorm-tools: crear, empaquetar y validar contenido SCORM."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .descriptor import CourseDescriptorError, load_course
from .models import ScormVersion
from .packager import build_package
from .scaffold import scaffold_course
from .validator import validate_package

app = typer.Typer(
    name="scorm-tools",
    help="Herramientas para crear, empaquetar y validar contenido SCORM compatible con Moodle.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


@app.command()
def init(
    target: Path = typer.Argument(..., help="Directorio destino del nuevo curso."),
    title: str = typer.Option(..., "--title", "-t", help="Título del curso."),
    version: ScormVersion = typer.Option(
        ScormVersion.SCORM_2004_4ED, "--version", "-v", help="Versión de SCORM."
    ),
    identifier: Optional[str] = typer.Option(
        None, "--id", help="Identificador único del curso (por defecto se deriva del título)."
    ),
) -> None:
    """Crea un curso SCORM de ejemplo listo para editar."""
    try:
        scaffold_course(target, title=title, version=version, identifier=identifier)
    except FileExistsError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"[green]Curso creado en[/green] {target}")
    console.print("Edite [bold]scorm.yaml[/bold] y el contenido del SCO, luego ejecute:")
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
    """Genera imsmanifest.xml y empaqueta el curso en un .zip para Moodle."""
    if not source.is_dir():
        err_console.print(f"[red]Error:[/red] {source} no es un directorio.")
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
) -> None:
    """Valida un paquete SCORM contra el esquema XSD y reglas de Moodle."""
    if not path.exists():
        err_console.print(f"[red]Error:[/red] {path} no existe.")
        raise typer.Exit(1)

    report = validate_package(path)
    _print_report(report)
    if not report.ok:
        raise typer.Exit(1)


@app.command()
def info(
    source: Path = typer.Argument(..., help="Directorio del curso (con scorm.yaml)."),
) -> None:
    """Muestra un resumen de la estructura del curso definida en scorm.yaml."""
    descriptor = source / "scorm.yaml" if source.is_dir() else source
    try:
        course = load_course(descriptor)
    except CourseDescriptorError as exc:
        err_console.print(f"[red]Error en scorm.yaml:[/red] {exc}")
        raise typer.Exit(1) from exc

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


def _print_report(report) -> None:
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
