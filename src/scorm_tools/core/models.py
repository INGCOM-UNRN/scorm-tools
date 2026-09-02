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
class SequencingRule:
    """Regla de secuenciamiento IMSSS (pre-condition, post-condition)."""

    action: str  # "disabled", "hideLMSUI", "skip", "exitParent", "retry"
    condition: str  # "satisfied", "notSatisfied", "completed", "incomplete", "attempted"
    operator: str = "noOp"  # "noOp", "not"
    referenced_objective: str | None = None


@dataclass
class RollupRule:
    """Regla de acumulación de objetivos y completitud IMSSS."""

    child_activity_set: str = "all"  # "all", "any", "none"
    condition: str = "satisfied"  # "satisfied", "completed"
    action: str = "satisfied"  # "satisfied", "notSatisfied", "completed", "incomplete"


@dataclass
class Objective:
    """Objetivo de aprendizaje SCORM 2004."""

    identifier: str
    satisfied_by_measure: bool = False
    min_normalized_measure: float | None = None


@dataclass
class Item:
    """Nodo de la jerarquía de organización (lo que el alumno navega)."""

    identifier: str
    title: str
    resource_identifier: str | None = None
    children: list[Item] = field(default_factory=list)
    mastery_score: int | None = None
    max_time_allowed: str | None = None
    time_action: str = "continue,message"
    prerequisites: list[str] = field(default_factory=list)
    parameters: str | None = None
    flow: bool = True
    choice: bool = True
    sequencing_rules: list[SequencingRule] = field(default_factory=list)
    rollup_rules: list[RollupRule] = field(default_factory=list)
    objectives: list[Objective] = field(default_factory=list)
    completed_on_view: bool = False


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
