"""Comandos de ciclo de vida del curso: doctor, init, build, validate, info."""

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


from ._cli_base import _emit_json, app, console, err_console


@app.command()
def doctor(
    json_output: bool = typer.Option(False, "--json", help="Emite el resultado en formato JSON versionado."),
) -> None:
    """Verificá el estado del entorno, dependencias y esquemas XSD de scorm-tools."""
    if json_output:
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            ok = ejecutar_diagnostico_doctor(Console(file=io.StringIO()))
        _emit_json("doctor", {"ok": ok})
        if not ok:
            raise typer.Exit(1)
        return
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
        help="Versión de SCORM (1.2 o 2004).",
    ),
    identifier: Optional[str] = typer.Option(
        None, "--id", help="Identificador único del curso (por defecto se deriva del título)."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emite el resultado en formato JSON versionado."),
) -> None:
    """Creá un curso SCORM de ejemplo listo para editar."""
    try:
        scaffold_course(target, title=title, version=version, identifier=identifier)
    except FileExistsError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    if json_output:
        _emit_json("init", {"directorio": str(target), "titulo": title, "version": version.value})
        return
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
    minify: bool = typer.Option(
        False, "--minify", help="Minificar scripts JavaScript y estilos CSS antes de empaquetar."
    ),
    sourcemap: bool = typer.Option(
        False, "--sourcemap", help="Generar source maps .map para archivos minificados."
    ),
    inject_resizer: bool = typer.Option(
        False, "--inject-resizer", help="Inyectar helper iframe-resizer para vista enmarcada en Moodle."
    ),
    completed_on_view: bool = typer.Option(
        False, "--completed-on-view", help="Marcar automáticamente el SCO como completado al abrirse."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emite el resultado en formato JSON versionado."),
) -> None:
    """Generá imsmanifest.xml y empaquetá el curso en un .zip para Moodle."""
    if not source.is_dir():
        err_console.print(f"[red]Error:[/red] {source} no es un directorio válido.")
        raise typer.Exit(1)

    output_zip = output or source.with_suffix(".zip")

    try:
        course = build_package(
            source,
            output_zip,
            minify=minify,
            generate_sourcemap=sourcemap,
            inject_resizer=inject_resizer,
            completed_on_view=completed_on_view,
        )
    except CourseDescriptorError as exc:
        err_console.print(f"[red]Error en scorm.yaml:[/red] {exc}")
        raise typer.Exit(1) from exc

    if not json_output:
        console.print(
            f"[green]Paquete generado:[/green] {output_zip} "
            f"(SCORM {course.version.value}, identifier={course.identifier})"
        )

    report = validate_package(output_zip) if validate else None
    if json_output:
        _emit_json("build", {
            "paquete": str(output_zip), "version": course.version.value,
            "identifier": course.identifier,
            "validacion": None if report is None else {"ok": report.ok},
        })
    elif report is not None:
        _print_report(report)
    if report is not None and not report.ok:
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
                    "prerequisites": item.prerequisites,
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


