"""Comandos de chequeo: check-sequencing, check-size, check-a11y, moodle-config."""

from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from .core.accesibilidad import HallazgoA11y, auditar_html, auditar_paquete
from .core.descriptor import CourseDescriptorError, load_course
from .core.moodle import (
    audit_moodle_compatibility,
    generate_moodle_settings,
)
from .core.optimizer import check_package_size
from .core.sequencing import (
    analyze_sequencing_graph,
    render_sequencing_tree,
    validate_sequencing,
)


from ._cli_base import app, console, err_console


@app.command("check-sequencing")
def cmd_check_sequencing(
    source: Path = typer.Argument(..., exists=True, help="Directorio del curso (con scorm.yaml)."),
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
        typer.echo(json.dumps(res, indent=2, ensure_ascii=False))
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
    path: Path = typer.Argument(..., exists=True, help="Paquete SCORM: archivo .zip o directorio."),
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
        typer.echo(json.dumps(stats, indent=2, ensure_ascii=False))
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
    source: Path = typer.Argument(..., exists=True, help="Directorio del curso (con scorm.yaml)."),
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
        typer.echo(json.dumps(settings, indent=2, ensure_ascii=False))


@app.command("check-a11y")
@app.command("audit-a11y", hidden=True)
def cmd_check_a11y(
    path: Path = typer.Argument(..., help="Paquete SCORM (.zip, directorio) o archivo HTML."),
    strict: bool = typer.Option(False, "--strict", help="Tratar los avisos de accesibilidad como errores."),
    json_output: bool = typer.Option(False, "--json", help="Emitir el informe de accesibilidad en formato JSON."),
) -> None:
    """Auditá el cumplimiento de accesibilidad WCAG 2.1 AA en páginas HTML y paquetes SCORM."""
    if not path.exists():
        err_console.print(f"[red]Error:[/red] {path} no existe.")
        raise typer.Exit(1)

    hallazgos: list[HallazgoA11y] = []
    if path.is_dir():
        hallazgos = auditar_paquete(path)
    elif path.suffix.lower() in (".html", ".htm"):
        contenido = path.read_text(encoding="utf-8", errors="replace")
        hallazgos = auditar_html(contenido, path.name)
    elif zipfile.is_zipfile(path):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with zipfile.ZipFile(path, "r") as zf:
                zf.extractall(tmp_path)
            hallazgos = auditar_paquete(tmp_path)
    else:
        err_console.print(f"[red]Error:[/red] {path} no es un directorio, archivo .zip ni página HTML válida.")
        raise typer.Exit(1)

    errores = [h for h in hallazgos if h.severidad == "error"]
    avisos = [h for h in hallazgos if h.severidad == "aviso"]
    ok = len(errores) == 0 and (not strict or len(avisos) == 0)

    if json_output:
        typer.echo(json.dumps({
            "archivo": str(path),
            "ok": ok,
            "errores": len(errores),
            "avisos": len(avisos),
            "hallazgos": [h.to_dict() for h in hallazgos],
        }, indent=2, ensure_ascii=False))
    else:
        for h in hallazgos:
            etiqueta = "[red]ERROR[/red]" if h.severidad == "error" else "[yellow]AVISO[/yellow]"
            ubicacion = f"{h.archivo}:{h.linea}" if h.linea else h.archivo
            console.print(f"  {etiqueta} [{h.regla}] {ubicacion}: {h.mensaje}")
        if ok and not hallazgos:
            console.print(f"[green]✓ Sin problemas de accesibilidad WCAG 2.1 AA en {path}[/green]")
        else:
            color = "red" if not ok else "yellow"
            console.print(f"[{color}]Total: {len(errores)} error(es), {len(avisos)} aviso(s)[/{color}]")

    if not ok:
        raise typer.Exit(1)



