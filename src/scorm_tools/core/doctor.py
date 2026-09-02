"""Diagnóstico del entorno y dependencias para scorm-tools."""

from __future__ import annotations

import sys
from importlib import resources
from typing import Any

from rich.console import Console
from rich.table import Table


def ejecutar_diagnostico_doctor(console: Console | None = None) -> bool:
    """Ejecuta la auditoría integral de dependencias y esquemas XSD de scorm-tools."""
    cons = console or Console()

    # 1. Chequeo de versión de Python (>= 3.10)
    py_major, py_minor = sys.version_info.major, sys.version_info.minor
    py_ok = (py_major, py_minor) >= (3, 10)
    py_version = f"{py_major}.{py_minor}.{sys.version_info.micro}"

    # 2. Chequeo de dependencias de Python
    deps = [
        ("lxml", "Parser XML y validador de esquemas XSD", True),
        ("jinja2", "Motor de plantillas para imsmanifest.xml y assets", True),
        ("yaml", "Parser PyYAML para descriptores scorm.yaml", True),
    ]

    dep_results: list[dict[str, Any]] = []
    for mod_name, desc, required in deps:
        try:
            mod = __import__(mod_name)
            ver = getattr(mod, "__version__", "Instalado")
            dep_results.append({"name": mod_name, "desc": desc, "ok": True, "version": ver, "required": required})
        except ImportError:
            dep_results.append({"name": mod_name, "desc": desc, "ok": False, "version": "No instalado", "required": required})

    # 3. Chequeo de esquemas XSD empaquetados
    schemas = [
        ("SCORM 1.2 (manifest.xsd)", "scorm_tools.schemas.scorm12", "manifest.xsd"),
        ("SCORM 2004 4ed (manifest.xsd)", "scorm_tools.schemas.scorm2004", "manifest.xsd"),
    ]

    schema_results: list[dict[str, Any]] = []
    for label, pkg, fname in schemas:
        try:
            pkg_res = resources.files(pkg)
            target = pkg_res.joinpath(fname)
            exists = target.is_file()
            schema_results.append({"label": label, "ok": exists, "detail": "Disponible" if exists else "No encontrado"})
        except Exception as exc:
            schema_results.append({"label": label, "ok": False, "detail": f"Error: {exc}"})

    # 4. Chequeo de plantillas Jinja2
    templates = [
        ("Plantilla SCORM 1.2", "scorm_tools.templates", "imsmanifest_12.xml.j2"),
        ("Plantilla SCORM 2004", "scorm_tools.templates", "imsmanifest_2004.xml.j2"),
    ]
    template_results: list[dict[str, Any]] = []
    for label, pkg, fname in templates:
        try:
            pkg_res = resources.files(pkg)
            target = pkg_res.joinpath(fname)
            exists = target.is_file()
            template_results.append({"label": label, "ok": exists, "detail": "Disponible" if exists else "No encontrado"})
        except Exception as exc:
            template_results.append({"label": label, "ok": False, "detail": f"Error: {exc}"})

    # 5. Render de tabla Rich
    tabla = Table(title="🏥 Diagnóstico del Entorno (scorm-tools doctor)", border_style="cyan")
    tabla.add_column("Componente / Recurso", style="bold white")
    tabla.add_column("Estado", justify="center")
    tabla.add_column("Versión / Detalle", style="dim")
    tabla.add_column("Propósito", style="yellow")

    tabla.add_row(
        "Python Runtime",
        "[bold green]✓ OK[/bold green]" if py_ok else "[bold red]✗ No soportado[/bold red]",
        f"Python {py_version}",
        "Entorno de ejecución (requiere >= 3.10)",
    )

    for r in dep_results:
        status = "[bold green]✓ OK[/bold green]" if r["ok"] else "[bold red]✗ Faltante[/bold red]"
        tabla.add_row(f"Librería: {r['name']}", status, r["version"], r["desc"])

    for s in schema_results:
        status = "[bold green]✓ OK[/bold green]" if s["ok"] else "[bold red]✗ Faltante[/bold red]"
        tabla.add_row(f"Esquema: {s['label']}", status, s["detail"], "Validación XSD oficial")

    for t in template_results:
        status = "[bold green]✓ OK[/bold green]" if t["ok"] else "[bold red]✗ Faltante[/bold red]"
        tabla.add_row(f"Template: {t['label']}", status, t["detail"], "Generación de manifiesto")

    cons.print(tabla)

    todo_ok = (
        py_ok
        and all(r["ok"] for r in dep_results if r["required"])
        and all(s["ok"] for s in schema_results)
        and all(t["ok"] for t in template_results)
    )

    if todo_ok:
        cons.print("\n[bold green]✓ Todos los componentes y esquemas XSD están listos y operativos.[/bold green]\n")
    else:
        cons.print("\n[bold red]❌ Se detectaron anomalías o recursos faltantes en el entorno de scorm-tools.[/bold red]\n")

    return todo_ok
