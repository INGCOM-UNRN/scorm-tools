"""Módulos del núcleo (core) de scorm-tools."""

from __future__ import annotations

from .descriptor import CourseDescriptorError, load_course
from .doctor import ejecutar_diagnostico_doctor
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
    "ejecutar_diagnostico_doctor",
    "generate_moodle_settings",
    "inject_completed_on_view",
    "inject_iframe_resizer",
    "load_course",
    "minify_assets",
    "minify_css",
    "minify_js",
    "optimize_images",
    "render_manifest",
    "render_sequencing_tree",
    "sanitize_moodle_identifier",
    "scaffold_course",
    "validate_package",
    "validate_sequencing",
]
