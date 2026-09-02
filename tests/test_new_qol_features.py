from __future__ import annotations

import json
from pathlib import Path
from io import StringIO

from rich.console import Console

from scorm_tools import __version__
from scorm_tools.core.doctor import ejecutar_diagnostico_doctor
from scorm_tools.core.models import ScormVersion
from scorm_tools.core.scaffold import scaffold_course
from scorm_tools.core.validator import ValidationReport, validate_package
from scorm_tools.core.packager import build_package


def test_package_version_exported() -> None:
    assert isinstance(__version__, str)
    assert len(__version__.split(".")) >= 3


def test_doctor_diagnostic_success() -> None:
    buf = StringIO()
    cons = Console(file=buf, force_terminal=False)
    ok = ejecutar_diagnostico_doctor(cons)
    output = buf.getvalue()

    assert ok is True
    assert "Diagnóstico del Entorno" in output
    assert "Python Runtime" in output
    assert "Esquema: SCORM 1.2" in output
    assert "Esquema: SCORM 2004" in output


def test_validation_report_serialization() -> None:
    rep = ValidationReport(manifest_path="imsmanifest.xml", scorm_version="2004")
    rep.add_warning("Advertencia didáctica")
    rep.add_error("Error crítico de prueba")

    # to_dict
    data = rep.to_dict()
    assert data["manifest_path"] == "imsmanifest.xml"
    assert data["scorm_version"] == "2004"
    assert data["ok"] is False
    assert "Advertencia didáctica" in data["warnings"]
    assert "Error crítico de prueba" in data["errors"]

    # to_json
    raw_json = rep.to_json()
    parsed = json.loads(raw_json)
    assert parsed["ok"] is False
    assert len(parsed["errors"]) == 1

    # to_markdown
    md = rep.to_markdown()
    assert "### Informe de Validación SCORM" in md
    assert "❌ **Inválido" in md
    assert "Advertencia didáctica" in md
    assert "Error crítico de prueba" in md


def test_validation_report_ok_markdown() -> None:
    rep = ValidationReport(manifest_path="imsmanifest.xml", scorm_version="1.2")
    md = rep.to_markdown()
    assert "✓ **Válido**" in md
    assert "#### Errores" not in md


def test_scorm_12_validation_markdown(tmp_path: Path) -> None:
    course_dir = tmp_path / "curso12"
    scaffold_course(course_dir, title="Curso SCORM 1.2", version=ScormVersion.SCORM_12)
    zip_out = tmp_path / "curso12.zip"
    build_package(course_dir, zip_out)

    report = validate_package(zip_out)
    assert report.ok is True
    md = report.to_markdown()
    assert "Versión SCORM:** `1.2`" in md
    assert "✓ **Válido**" in md


def test_minify_css_and_js() -> None:
    from scorm_tools.core.optimizer import minify_css, minify_js, generate_sourcemap

    raw_css = """
    /* Comentario de prueba */
    body {
        background-color: #fff;
        margin: 0px;
    }
    """
    min_css = minify_css(raw_css)
    assert "/* Comentario" not in min_css
    assert "background-color:#fff" in min_css

    raw_js = """
    // Line comment
    function saludar(nombre) {
        /* Multi-line
           comment */
        return "Hola " + nombre;
    }
    """
    min_js = minify_js(raw_js)
    assert "// Line comment" not in min_js
    assert "/* Multi-line" not in min_js
    assert 'return "Hola " + nombre;' in min_js

    sm = generate_sourcemap("script.js", raw_js)
    parsed_sm = json.loads(sm)
    assert parsed_sm["version"] == 3
    assert parsed_sm["file"] == "script.js"


def test_moodle_identifier_sanitization_and_settings() -> None:
    from scorm_tools.core.moodle import sanitize_moodle_identifier, generate_moodle_settings, audit_moodle_compatibility
    from scorm_tools.core.models import Course, Organization, Item

    bad_id = "  ¡Hola mundo! #123_test$  "
    san = sanitize_moodle_identifier(bad_id)
    assert san == "Hola-mundo-123_test"

    course = Course(
        identifier="CURSO-C",
        title="Curso de C",
        organizations=[Organization(identifier="ORG-1", title="Org", items=[Item(identifier="IT-1", title="T1", mastery_score=80)])]
    )
    settings = generate_moodle_settings(course)
    assert settings["scorm_identifier"] == "CURSO-C"
    assert settings["activity_settings"]["maxgrade"] == 100

    warns = audit_moodle_compatibility(course)
    assert len(warns) == 0


def test_sequencing_manifest_compilation_and_xsd_validation(tmp_path: Path) -> None:
    from scorm_tools.core.models import Item, Organization, Resource, SequencingRule, RollupRule, Objective
    from scorm_tools.core.descriptor import load_course
    from scorm_tools.core.packager import build_package

    scorm_yaml = tmp_path / "scorm.yaml"
    scorm_yaml.write_text("""
identifier: ADVANCED-SEQ-2004
title: Curso con Secuenciamiento Avanzado
version: 2004-4ed
organizations:
  - identifier: ORG-1
    title: Estructura de Módulos
    items:
      - identifier: MOD-1
        title: "Módulo 1: Fundamentos"
        resource: RES-1
        mastery_score: 75
        choice: true
        flow: true
        objectives:
          - id: OBJ-FUNDAMENTOS
            satisfied_by_measure: true
            min_normalized_measure: 0.75
        rollup_rules:
          - child_activity_set: all
            condition: satisfied
            action: satisfied
      - identifier: MOD-2
        title: "Módulo 2: Punteros Avanzados"
        resource: RES-1
        prerequisites: [MOD-1]
        sequencing_rules:
          - action: disabled
            condition: satisfied
            operator: not
            referenced_objective: OBJ-FUNDAMENTOS
resources:
  - identifier: RES-1
    href: index.html
    type: sco
""", encoding="utf-8")

    (tmp_path / "index.html").write_text("<html><body>Contenido</body></html>", encoding="utf-8")
    (tmp_path / "style.css").write_text("body { color: black; }", encoding="utf-8")

    zip_out = tmp_path / "advanced.zip"
    course = build_package(tmp_path, zip_out, minify=True, inject_resizer=True)

    assert zip_out.exists()
    report = validate_package(zip_out)
    assert report.ok is True, report.errors
    assert report.scorm_version == "2004"


def test_parse_gift_questions_and_diagram() -> None:
    from scorm_tools.core.ecosystem import parse_gift_questions, generate_memory_diagram

    gift_sample = """
    ::V/F:: En C los arreglos son 0-indexados {T}

    ::Pregunta MC:: ¿Cuál reserva memoria dinámica? {
      = malloc
      ~ printf
      ~ sizeof
    }
    """
    qs = parse_gift_questions(gift_sample)
    assert len(qs) == 2
    assert qs[0]["type"] == "true_false"
    assert qs[0]["correct"] is True
    assert qs[1]["type"] == "multiple_choice"
    assert any(opt["correct"] for opt in qs[1]["options"])

    diagram = generate_memory_diagram(
        stack_frames=[
            {"function": "main", "variables": {"argc": 1}},
            {"function": "factorial", "variables": {"n": 3}},
        ],
        heap_blocks=[{"address": "0x1000", "size": 64, "tag": "buffer"}],
    )
    assert "graph TD" in diagram
    assert "Memoria Stack" in diagram
    assert "Memoria Heap" in diagram
    assert "0x1000" in diagram
