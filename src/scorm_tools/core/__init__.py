"""Módulos del núcleo (core) de scorm-tools."""

from __future__ import annotations

from .descriptor import CourseDescriptorError, load_course
from .doctor import ejecutar_diagnostico_doctor
from .ecosystem import (
    deckard_to_scorm,
    extract_and_audit_c_code,
    generate_memory_diagram,
    gift_to_scorm_sco,
    idkfa_to_scorm_tracing,
    parse_gift_questions,
    parse_idkfa_template,
    parse_scorm_tracking_log,
    scaffold_wasm_playground,
)
from .manifest import render_manifest
from .models import (
    Course,
    Item,
    Objective,
    Organization,
    Resource,
    RollupRule,
    ScormVersion,
    SequencingRule,
)
from .moodle import (
    audit_moodle_compatibility,
    generate_moodle_settings,
    inject_completed_on_view,
    inject_iframe_resizer,
    sanitize_moodle_identifier,
)
from .optimizer import (
    check_package_size,
    minify_assets,
    minify_css,
    minify_js,
    optimize_images,
)
from .packager import build_package
from .scaffold import scaffold_course
from .sequencing import (
    analyze_sequencing_graph,
    render_sequencing_tree,
    validate_sequencing,
)
from .validator import ValidationReport, validate_package

__all__ = [
    "Course",
    "CourseDescriptorError",
    "Item",
    "Objective",
    "Organization",
    "Resource",
    "RollupRule",
    "ScormVersion",
    "SequencingRule",
    "ValidationReport",
    "analyze_sequencing_graph",
    "audit_moodle_compatibility",
    "build_package",
    "check_package_size",
    "deckard_to_scorm",
    "ejecutar_diagnostico_doctor",
    "extract_and_audit_c_code",
    "generate_memory_diagram",
    "generate_moodle_settings",
    "gift_to_scorm_sco",
    "idkfa_to_scorm_tracing",
    "inject_completed_on_view",
    "inject_iframe_resizer",
    "load_course",
    "minify_assets",
    "minify_css",
    "minify_js",
    "optimize_images",
    "parse_gift_questions",
    "parse_idkfa_template",
    "parse_scorm_tracking_log",
    "render_manifest",
    "render_sequencing_tree",
    "sanitize_moodle_identifier",
    "scaffold_course",
    "scaffold_wasm_playground",
    "validate_package",
    "validate_sequencing",
]
