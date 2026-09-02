"""Carga del descriptor `scorm.yaml` a los modelos de datos del curso."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

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

COURSE_DESCRIPTOR_NAME = "scorm.yaml"


class CourseDescriptorError(ValueError):
    """Error de validación del descriptor `scorm.yaml`."""


def _parse_item(data: dict[str, Any]) -> Item:
    if "identifier" not in data or "title" not in data:
        raise CourseDescriptorError(
            "Cada item requiere 'identifier' y 'title'."
        )
    children = [_parse_item(c) for c in data.get("children", [])]

    # Parse prerequisites
    prereqs_raw = data.get("prerequisites", [])
    if isinstance(prereqs_raw, str):
        prerequisites = [p.strip() for p in prereqs_raw.split(",") if p.strip()]
    elif isinstance(prereqs_raw, list):
        prerequisites = [str(p) for p in prereqs_raw]
    else:
        prerequisites = []

    # Parse sequencing rules
    seq_rules: list[SequencingRule] = []
    for r in data.get("sequencing_rules", []):
        seq_rules.append(
            SequencingRule(
                action=r.get("action", "disabled"),
                condition=r.get("condition", "satisfied"),
                operator=r.get("operator", "noOp"),
                referenced_objective=r.get("referenced_objective"),
            )
        )

    # Parse rollup rules
    rollup_rules: list[RollupRule] = []
    for ru in data.get("rollup_rules", []):
        rollup_rules.append(
            RollupRule(
                child_activity_set=ru.get("child_activity_set", "all"),
                condition=ru.get("condition", "satisfied"),
                action=ru.get("action", "satisfied"),
            )
        )

    # Parse objectives
    objectives: list[Objective] = []
    for obj in data.get("objectives", []):
        objectives.append(
            Objective(
                identifier=obj.get("identifier") or obj.get("id", "OBJ"),
                satisfied_by_measure=obj.get("satisfied_by_measure", False),
                min_normalized_measure=obj.get("min_normalized_measure"),
            )
        )

    return Item(
        identifier=data["identifier"],
        title=data["title"],
        resource_identifier=data.get("resource"),
        children=children,
        mastery_score=data.get("mastery_score"),
        max_time_allowed=data.get("max_time_allowed"),
        time_action=data.get("time_action", "continue,message"),
        prerequisites=prerequisites,
        parameters=data.get("parameters"),
        flow=data.get("flow", True),
        choice=data.get("choice", True),
        sequencing_rules=seq_rules,
        rollup_rules=rollup_rules,
        objectives=objectives,
        completed_on_view=data.get("completed_on_view", False),
    )


def _parse_resource(data: dict[str, Any]) -> Resource:
    if "identifier" not in data or "href" not in data:
        raise CourseDescriptorError(
            "Cada resource requiere 'identifier' y 'href'."
        )
    return Resource(
        identifier=data["identifier"],
        href=data["href"],
        files=data.get("files", [data["href"]]),
        scorm_type=data.get("type", "sco"),
        dependencies=data.get("dependencies", []),
    )


def load_course(descriptor_path: Path) -> Course:
    """Lee un archivo `scorm.yaml` y construye un `Course`."""
    if not descriptor_path.exists():
        raise CourseDescriptorError(f"No existe el descriptor: {descriptor_path}")

    raw = yaml.safe_load(descriptor_path.read_text(encoding="utf-8")) or {}

    if "identifier" not in raw or "title" not in raw:
        raise CourseDescriptorError(
            "El descriptor debe definir 'identifier' y 'title' de nivel superior."
        )

    version_raw = str(raw.get("version", "2004-4ed"))
    try:
        version = ScormVersion(version_raw)
    except ValueError as exc:
        valid = ", ".join(v.value for v in ScormVersion)
        raise CourseDescriptorError(
            f"version '{version_raw}' inválida. Valores válidos: {valid}"
        ) from exc

    organizations = []
    for org_data in raw.get("organizations", []):
        if "identifier" not in org_data or "title" not in org_data:
            raise CourseDescriptorError(
                "Cada organization requiere 'identifier' y 'title'."
            )
        items = [_parse_item(i) for i in org_data.get("items", [])]
        organizations.append(
            Organization(
                identifier=org_data["identifier"],
                title=org_data["title"],
                items=items,
            )
        )

    resources = [_parse_resource(r) for r in raw.get("resources", [])]

    return Course(
        identifier=raw["identifier"],
        title=raw["title"],
        version=version,
        organizations=organizations,
        resources=resources,
        description=raw.get("description", ""),
        default_organization=raw.get("default_organization"),
    )
