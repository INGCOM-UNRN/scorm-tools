"""Carga del descriptor `scorm.yaml` a los modelos de datos del curso."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import Course, Item, Organization, Resource, ScormVersion

COURSE_DESCRIPTOR_NAME = "scorm.yaml"


class CourseDescriptorError(ValueError):
    """Error de validación del descriptor `scorm.yaml`."""


def _parse_item(data: dict[str, Any]) -> Item:
    if "identifier" not in data or "title" not in data:
        raise CourseDescriptorError(
            "Cada item requiere 'identifier' y 'title'."
        )
    children = [_parse_item(c) for c in data.get("children", [])]
    return Item(
        identifier=data["identifier"],
        title=data["title"],
        resource_identifier=data.get("resource"),
        children=children,
        mastery_score=data.get("mastery_score"),
        max_time_allowed=data.get("max_time_allowed"),
        time_action=data.get("time_action", "continue,message"),
        prerequisites=data.get("prerequisites"),
        parameters=data.get("parameters"),
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
