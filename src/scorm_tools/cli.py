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
from .core.ecosystem import (
    deckard_to_scorm,
    extract_and_audit_c_code,
    gift_to_scorm_sco,
    parse_scorm_tracking_log,
)
from .core.models import ScormVersion
from .core.moodle import (
    audit_moodle_compatibility,
    generate_moodle_settings,
)
from .core.optimizer import check_package_size
from .core.packager import build_package
from .core.scaffold import scaffold_course
from .core.sequencing import (
    analyze_sequencing_graph,
    render_sequencing_tree,
    validate_sequencing,
)
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


@app.command("check-sequencing")
def cmd_check_sequencing(
    source: Path = typer.Argument(..., help="Directorio del curso (con scorm.yaml)."),
    json_output: bool = typer.Option(
        False, "--json", help="Emite el análisis del grafo en formato JSON estructurado."
    ),
) -> None:
    """Verificá el grafo de secuenciamiento IMSSS y detectá ciclos o actividades huérfanas."""
    descriptor = source / "scorm.yaml" if source.is_dir() else source
    try:
        course = load_course(descriptor)
    except CourseDescriptorError as exc:
        err_console.print(f"[red]Error en scorm.yaml:[/red] {exc}")
        raise typer.Exit(1) from exc

    graph_info = analyze_sequencing_graph(course)
    errors = validate_sequencing(course)

    if json_output:
        res = {
            "graph": graph_info,
            "errors": errors,
            "valid": len(errors) == 0 and graph_info["valid"],
        }
        console.print(json.dumps(res, indent=2, ensure_ascii=False))
        if not res["valid"]:
            raise typer.Exit(1)
        return

    console.print(render_sequencing_tree(course))
    console.print()

    if errors:
        for err in errors:
            err_console.print(f"[red]ERROR SECUENCIAMIENTO:[/red] {err}")
        err_console.print(f"[red]✗ Se detectaron {len(errors)} problema(s) de secuenciamiento.[/red]")
        raise typer.Exit(1)
    else:
        console.print("[green]✓ Grafo de secuenciamiento válido (sin ciclos ni actividades huérfanas).[/green]")


@app.command("check-size")
def cmd_check_size(
    path: Path = typer.Argument(..., help="Paquete SCORM: archivo .zip o directorio."),
    max_mb: float = typer.Option(50.0, "--max-mb", help="Límite máximo permitido en MB (defecto: 50MB)."),
    json_output: bool = typer.Option(False, "--json", help="Emite el informe de tamaño en formato JSON estructurado."),
) -> None:
    """Audita el peso del paquete y su desglose por tipo de contenido para Moodle."""
    if not path.exists():
        err_console.print(f"[red]Error:[/red] {path} no existe.")
        raise typer.Exit(1)

    try:
        stats = check_package_size(path, max_mb=max_mb)
    except ValueError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    if json_output:
        console.print(json.dumps(stats, indent=2, ensure_ascii=False))
        if stats["exceeds_limit"]:
            raise typer.Exit(1)
        return

    table = Table(title=f"Auditoría de Tamaño de Paquete ({path.name})", border_style="cyan")
    table.add_column("Categoría", style="bold white")
    table.add_column("Tamaño (KB)", justify="right")
    table.add_column("Participación", justify="right")

    total_kb = stats["total_bytes"] / 1024.0 if stats["total_bytes"] > 0 else 1.0
    for cat, kb in stats["categories_kb"].items():
        pct = (kb / total_kb * 100.0) if total_kb > 0 else 0.0
        table.add_row(cat.capitalize(), f"{kb:.1f} KB", f"{pct:.1f}%")

    console.print(table)
    console.print(f"Tamaño total: [bold]{stats['total_mb']:.2f} MB[/bold] (Umbral máximo: {max_mb:.2f} MB)")

    if stats["exceeds_limit"]:
        err_console.print(f"[red]✗ El paquete supera el umbral fijado de {max_mb} MB.[/red]")
        raise typer.Exit(1)
    else:
        console.print(f"[green]✓ Paquete dentro del límite de subida ({max_mb} MB).[/green]")


@app.command("moodle-config")
def cmd_moodle_config(
    source: Path = typer.Argument(..., help="Directorio del curso (con scorm.yaml)."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Ruta donde guardar moodle_settings.json (opcional)."),
    grademethod: int = typer.Option(1, "--grade-method", help="Método de calificación: 1=Más alta, 2=Promedio, 3=Primer intento, 4=Último."),
    maxattempt: int = typer.Option(3, "--max-attempts", help="Número máximo de intentos permitidos."),
    popup: int = typer.Option(0, "--popup", help="Visualización: 0=Enmarcado en página, 1=Nueva ventana."),
    json_output: bool = typer.Option(False, "--json", help="Emite la configuración exclusivamente en JSON."),
) -> None:
    """Generá la configuración recomendada de actividad Moodle (moodle_settings.json)."""
    descriptor = source / "scorm.yaml" if source.is_dir() else source
    try:
        course = load_course(descriptor)
    except CourseDescriptorError as exc:
        err_console.print(f"[red]Error en scorm.yaml:[/red] {exc}")
        raise typer.Exit(1) from exc

    warnings = audit_moodle_compatibility(course)
    for w in warnings:
        console.print(f"[yellow]ADVERTENCIA MOODLE:[/yellow] {w}")

    settings = generate_moodle_settings(course, grademethod=grademethod, maxattempt=maxattempt, popup=popup)

    if output:
        output.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
        console.print(f"[green]Configuración Moodle guardada en:[/green] {output}")

    if json_output or not output:
        console.print(json.dumps(settings, indent=2, ensure_ascii=False))


@app.command("from-deckard")
def cmd_from_deckard(
    guia: Path = typer.Argument(..., help="Archivo guia.yaml de ejercicios de Deckard."),
    target: Path = typer.Argument(..., help="Directorio destino del paquete SCORM."),
    version: ScormVersion = typer.Option(
        ScormVersion.SCORM_2004_4ED, "--scorm-version", "--version", help="Versión SCORM (1.2 o 2004)."
    ),
    build: bool = typer.Option(
        False, "--build", "-b", help="Compilar automáticamente a archivo .zip tras generar los fuentes."
    ),
) -> None:
    """Convertí una guía de ejercicios de Deckard a un curso SCORM interactivo."""
    try:
        course = deckard_to_scorm(guia, target, version=version)
    except Exception as exc:
        err_console.print(f"[red]Error al convertir guía Deckard:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"[green]Curso SCORM generado en[/green] {target} con {len(course.organization().items)} ejercicios.")
    if build:
        zip_out = target.with_suffix(".zip")
        build_package(target, zip_out)
        console.print(f"[green]Paquete .zip compilado en:[/green] {zip_out}")


@app.command("from-gift")
def cmd_from_gift(
    gift_file: Path = typer.Argument(..., help="Archivo de preguntas en formato GIFT."),
    target: Path = typer.Argument(..., help="Directorio destino del paquete SCORM."),
    title: str = typer.Option("Cuestionario SCORM", "--title", "-t", help="Título del cuestionario."),
    build: bool = typer.Option(
        False, "--build", "-b", help="Compilar automáticamente a archivo .zip tras generar los fuentes."
    ),
) -> None:
    """Convertí un banco de preguntas GIFT (Moodle) en un módulo SCORM interactivo autoevaluable."""
    try:
        course = gift_to_scorm_sco(gift_file, target, title=title)
    except Exception as exc:
        err_console.print(f"[red]Error al procesar archivo GIFT:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"[green]Cuestionario SCORM generado en[/green] {target}")
    if build:
        zip_out = target.with_suffix(".zip")
        build_package(target, zip_out)
        console.print(f"[green]Paquete .zip compilado en:[/green] {zip_out}")


@app.command("audit-c")
def cmd_audit_c(
    source: Path = typer.Argument(..., help="Directorio del curso SCORM a auditar."),
    json_output: bool = typer.Option(
        False, "--json", help="Emite los hallazgos en formato JSON estructurado."
    ),
) -> None:
    """Auditá fragmentos de código C embebidos en el contenido SCORM contra reglas Ripley."""
    findings = extract_and_audit_c_code(source)
    if json_output:
        console.print(json.dumps(findings, indent=2, ensure_ascii=False))
        if findings:
            raise typer.Exit(1)
        return

    if not findings:
        console.print("[green]✓ No se detectaron infracciones de código C en las lecciones.[/green]")
        return

    table = Table(title="Auditoría de Código C Embebido (Ripley / Convenciones de Cátedra)", border_style="red")
    table.add_column("Archivo", style="cyan")
    table.add_column("Regla", style="bold yellow")
    table.add_column("Detalle", style="white")

    for f in findings:
        table.add_row(f["file"], f["rule"], f["detail"])

    console.print(table)
    err_console.print(f"[red]✗ Se encontraron {len(findings)} infracción(es) en el código C embebido.[/red]")
    raise typer.Exit(1)


@app.command("dredd-sync")
def cmd_dredd_sync(
    tracking_file: Path = typer.Argument(..., help="Archivo JSON con registros de tracking SCORM exportados."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Archivo donde guardar el reporte para Dredd."),
) -> None:
    """Procesá registros de tracking de Moodle SCORM para integrarlos al calificador docente Dredd."""
    if not tracking_file.exists():
        err_console.print(f"[red]Error:[/red] {tracking_file} no existe.")
        raise typer.Exit(1)

    try:
        raw = json.loads(tracking_file.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            raw = [raw]
        grades = parse_scorm_tracking_log(raw)
    except Exception as exc:
        err_console.print(f"[red]Error al parsear tracking:[/red] {exc}")
        raise typer.Exit(1) from exc

    table = Table(title="Calificaciones SCORM Procesadas para Dredd", border_style="cyan")
    table.add_column("Estudiante / Legajo", style="bold white")
    table.add_column("Nota", justify="right")
    table.add_column("Estado", justify="center")
    table.add_column("Aprobado", justify="center")

    for g in grades:
        color = "green" if g["passed"] else "red"
        table.add_row(
            g["student_id"],
            f"{g['score']:.1f}",
            g["status"],
            f"[{color}]{'SÍ' if g['passed'] else 'NO'}[/{color}]",
        )

    console.print(table)

    if output:
        output.write_text(json.dumps(grades, indent=2, ensure_ascii=False), encoding="utf-8")
        console.print(f"[green]Reporte Dredd exportado en:[/green] {output}")


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
