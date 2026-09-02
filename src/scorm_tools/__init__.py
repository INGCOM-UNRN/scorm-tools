"""scorm-tools: crear, gestionar y validar contenido SCORM para Moodle."""

from __future__ import annotations

__version__ = "0.1.0"

from .cli import app, main
from .core.descriptor import CourseDescriptorError, load_course
from .core.doctor import ejecutar_diagnostico_doctor
from .core.manifest import render_manifest
from .core.models import (
    Course,
    Item,
    Objective,
    Organization,
    Resource,
    RollupRule,
    ScormVersion,
    SequencingRule,
)
from .core.moodle import (
    audit_moodle_compatibility,
    generate_moodle_settings,
    inject_completed_on_view,
    inject_iframe_resizer,
    sanitize_moodle_identifier,
)
from .core.optimizer import (
    check_package_size,
    minify_assets,
    minify_css,
    minify_js,
    optimize_images,
)
from .core.packager import build_package
from .core.scaffold import scaffold_course
from .core.sequencing import (
    analyze_sequencing_graph,
    render_sequencing_tree,
    validate_sequencing,
)
from .core.validator import ValidationReport, validate_package

__all__ = [
    "__version__",
    "main",
    "app",
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
