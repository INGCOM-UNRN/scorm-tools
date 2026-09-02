"""Modelos de datos que describen un curso SCORM."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ScormVersion(str, Enum):
    """Versiones del estándar SCORM soportadas."""

    SCORM_12 = "1.2"
    SCORM_2004_3ED = "2004-3ed"
    SCORM_2004_4ED = "2004-4ed"


@dataclass
class Resource:
    """Un recurso SCORM: un SCO (lanzable) o un asset (recurso estático)."""

    identifier: str
    href: str
    files: list[str] = field(default_factory=list)
    scorm_type: str = "sco"  # "sco" | "asset"
    dependencies: list[str] = field(default_factory=list)


@dataclass
class Item:
    """Nodo de la jerarquía de organización (lo que el alumno navega)."""

    identifier: str
    title: str
    resource_identifier: str | None = None
    children: list["Item"] = field(default_factory=list)
    mastery_score: int | None = None
    max_time_allowed: str | None = None
    time_action: str = "continue,message"
    prerequisites: str | None = None
    parameters: str | None = None


@dataclass
class Organization:
    """Estructura de navegación (curso) que agrupa items."""

    identifier: str
    title: str
    items: list[Item] = field(default_factory=list)


@dataclass
class Course:
    """Representación completa de un paquete SCORM antes de compilarlo."""

    identifier: str
    title: str
    version: ScormVersion = ScormVersion.SCORM_2004_4ED
    organizations: list[Organization] = field(default_factory=list)
    resources: list[Resource] = field(default_factory=list)
    description: str = ""
    default_organization: str | None = None

    def organization(self) -> Organization:
        if not self.organizations:
            raise ValueError("El curso no tiene organizaciones definidas.")
        if self.default_organization:
            for org in self.organizations:
                if org.identifier == self.default_organization:
                    return org
        return self.organizations[0]
