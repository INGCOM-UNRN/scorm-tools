"""Comandos de integración con el ecosistema: from-*, audit-c, dredd-sync, diagram-memory, playground."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from .core.ecosystem import (
    deckard_to_scorm,
    extract_and_audit_c_code,
    generate_memory_diagram,
    gift_to_scorm_sco,
    idkfa_to_scorm_tracing,
    parse_scorm_tracking_log,
    scaffold_wasm_playground,
)
from .core.models import ScormVersion
from .core.packager import build_package


from ._cli_base import _emit_json, app, console, err_console


@app.command("from-deckard")
def cmd_from_deckard(
    guia: Path = typer.Argument(..., exists=True, help="Archivo guia.yaml de ejercicios de Deckard."),
    target: Path = typer.Argument(..., help="Directorio destino del paquete SCORM."),
    version: ScormVersion = typer.Option(
        ScormVersion.SCORM_2004_4ED, "--scorm-version", help="Versión SCORM (1.2 o 2004)."
    ),
    build: bool = typer.Option(
        False, "--build", "-b", help="Compilar automáticamente a archivo .zip tras generar los fuentes."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emite el resultado en formato JSON versionado."),
) -> None:
    """Convertí una guía de ejercicios de Deckard a un curso SCORM interactivo."""
    avisos: list[str] = []
    try:
        course = deckard_to_scorm(guia, target, version=version, avisos=avisos)
    except Exception as exc:
        err_console.print(f"[red]Error al convertir guía Deckard:[/red] {exc}")
        raise typer.Exit(1) from exc

    for aviso in avisos:
        err_console.print(f"[yellow]Aviso:[/yellow] {aviso}")

    zip_out = None
    if build:
        zip_out = target.with_suffix(".zip")
        build_package(target, zip_out)
    if json_output:
        _emit_json("from-deckard", {"directorio": str(target), "avisos": avisos,
                                    "ejercicios": len(course.organization().items),
                                    "zip": str(zip_out) if zip_out else None})
        return
    console.print(f"[green]Curso SCORM generado en[/green] {target} con {len(course.organization().items)} ejercicios.")
    if zip_out:
        console.print(f"[green]Paquete .zip compilado en:[/green] {zip_out}")


@app.command("from-gift")
def cmd_from_gift(
    gift_file: Path = typer.Argument(..., exists=True, help="Archivo de preguntas en formato GIFT."),
    target: Path = typer.Argument(..., help="Directorio destino del paquete SCORM."),
    title: str = typer.Option("Cuestionario SCORM", "--title", "-t", help="Título del cuestionario."),
    build: bool = typer.Option(
        False, "--build", "-b", help="Compilar automáticamente a archivo .zip tras generar los fuentes."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emite el resultado en formato JSON versionado."),
) -> None:
    """Convertí un banco de preguntas GIFT (Moodle) en un módulo SCORM interactivo autoevaluable."""
    avisos: list[str] = []
    try:
        course = gift_to_scorm_sco(gift_file, target, title=title, avisos=avisos)
    except Exception as exc:
        err_console.print(f"[red]Error al procesar archivo GIFT:[/red] {exc}")
        raise typer.Exit(1) from exc

    for aviso in avisos:
        err_console.print(f"[yellow]Aviso:[/yellow] {aviso}")
    zip_out = None
    if build:
        zip_out = target.with_suffix(".zip")
        build_package(target, zip_out)
    if json_output:
        _emit_json("from-gift", {"directorio": str(target), "avisos": avisos,
                                 "zip": str(zip_out) if zip_out else None})
        return
    console.print(f"[green]Cuestionario SCORM generado en[/green] {target}")
    if zip_out:
        console.print(f"[green]Paquete .zip compilado en:[/green] {zip_out}")


@app.command("audit-c")
def cmd_audit_c(
    source: Path = typer.Argument(..., exists=True, help="Directorio del curso SCORM a auditar."),
    json_output: bool = typer.Option(
        False, "--json", help="Emite los hallazgos en formato JSON estructurado."
    ),
) -> None:
    """Auditá fragmentos de código C embebidos en el contenido SCORM contra reglas Ripley."""
    findings = extract_and_audit_c_code(source)
    if json_output:
        typer.echo(json.dumps(findings, indent=2, ensure_ascii=False))
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
    tracking_file: Path = typer.Argument(..., exists=True, help="Archivo JSON con registros de tracking SCORM exportados."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Archivo donde guardar el reporte para Dredd."),
    json_output: bool = typer.Option(False, "--json", help="Emite el resultado en formato JSON versionado."),
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

    if output:
        output.write_text(json.dumps(grades, indent=2, ensure_ascii=False), encoding="utf-8")
    if json_output:
        _emit_json("dredd-sync", {"calificaciones": grades, "salida": str(output) if output else None})
        return

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
        console.print(f"[green]Reporte Dredd exportado en:[/green] {output}")


@app.command("diagram-memory")
def cmd_diagram_memory(
    trace_file: Path = typer.Argument(..., exists=True, help="Archivo JSON con la traza de memoria (frames y heap)."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Archivo de salida para el diagrama Mermaid."),
    json_output: bool = typer.Option(False, "--json", help="Emite el resultado en formato JSON versionado."),
) -> None:
    """Generá un diagrama Mermaid de memoria Stack y Heap (Bishop/Sebastian) para lecciones SCORM."""
    if not trace_file.exists():
        err_console.print(f"[red]Error:[/red] {trace_file} no existe.")
        raise typer.Exit(1)

    # bishop es el dueño de los diagramas de memoria (N-ECO-12): si está instalado (extra
    # `ecosistema`) dibuja él; si no, queda el diagrama propio. Este comando se va a retirar.
    aviso = "diagram-memory pasa a bishop: usá `bishop diagram traza.json` (este comando se va a retirar)."
    if not json_output:
        err_console.print(f"[yellow]Aviso:[/yellow] {aviso}")
    try:
        raw = json.loads(trace_file.read_text(encoding="utf-8"))
        try:
            from bishop.core.diagrama import generar_diagrama, snapshot_desde_dict
        except ImportError:
            frames = raw.get("stack", raw.get("frames", []))
            diagram = generate_memory_diagram(frames, raw.get("heap", []))
        else:
            diagram = generar_diagrama(snapshot_desde_dict(raw, trace_file.name), "mermaid")
    except Exception as exc:
        err_console.print(f"[red]Error al procesar traza de memoria:[/red] {exc}")
        raise typer.Exit(1) from exc

    if output:
        output.write_text(diagram, encoding="utf-8")
    if json_output:
        _emit_json("diagram-memory", {"salida": str(output) if output else None,
                                      "diagrama": None if output else diagram, "aviso": aviso})
    elif output:
        console.print(f"[green]Diagrama Mermaid guardado en:[/green] {output}")
    else:
        console.print(diagram)


@app.command("from-idkfa")
def cmd_from_idkfa(
    template: Path = typer.Argument(..., exists=True, help="Plantilla C de ejercicio de tracing de IDKFA."),
    target: Path = typer.Argument(..., help="Directorio destino del paquete SCORM."),
    build: bool = typer.Option(False, "--build", "-b", help="Compilar automáticamente a archivo .zip."),
    json_output: bool = typer.Option(False, "--json", help="Emite el resultado en formato JSON versionado."),
) -> None:
    """Convertí una plantilla de tracing C de IDKFA a una lección interactiva SCORM autoevaluable."""
    try:
        course = idkfa_to_scorm_tracing(template, target)
    except Exception as exc:
        err_console.print(f"[red]Error al convertir plantilla IDKFA:[/red] {exc}")
        raise typer.Exit(1) from exc

    zip_out = None
    if build:
        zip_out = target.with_suffix(".zip")
        build_package(target, zip_out)
    if json_output:
        _emit_json("from-idkfa", {"directorio": str(target), "zip": str(zip_out) if zip_out else None})
        return
    console.print(f"[green]Lección SCORM generada en[/green] {target}")
    if zip_out:
        console.print(f"[green]Paquete .zip compilado en:[/green] {zip_out}")


@app.command("playground")
def cmd_playground(
    target: Path = typer.Argument(..., help="Directorio destino del módulo Playground Wasm."),
    title: str = typer.Option("Playground C WebAssembly", "--title", "-t", help="Título del módulo."),
    build: bool = typer.Option(False, "--build", "-b", help="Compilar automáticamente a archivo .zip."),
    json_output: bool = typer.Option(False, "--json", help="Emite el resultado en formato JSON versionado."),
) -> None:
    """Generá un módulo SCORM interactivo con compilador C WebAssembly en el navegador."""
    course = scaffold_wasm_playground(target, title=title)
    zip_out = None
    if build:
        zip_out = target.with_suffix(".zip")
        build_package(target, zip_out)
    if json_output:
        _emit_json("playground", {"directorio": str(target), "zip": str(zip_out) if zip_out else None})
        return
    console.print(f"[green]Playground Wasm generado en[/green] {target}")
    if zip_out:
        console.print(f"[green]Paquete .zip compilado en:[/green] {zip_out}")


