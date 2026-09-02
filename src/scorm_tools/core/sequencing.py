"""Auditoría, validación y análisis de grafos de secuenciamiento IMSSS para SCORM 2004."""

from __future__ import annotations

from typing import Any

from .models import Course, Item


def _collect_all_items(items: list[Item]) -> dict[str, Item]:
    result: dict[str, Item] = {}
    for it in items:
        result[it.identifier] = it
        if it.children:
            result.update(_collect_all_items(it.children))
    return result


def analyze_sequencing_graph(course: Course) -> dict[str, Any]:
    """Construye y analiza el grafo de dependencias y prerrequisitos del curso."""
    org = course.organization()
    all_items = _collect_all_items(org.items)

    nodes = list(all_items.keys())
    adj: dict[str, list[str]] = {node: [] for node in nodes}

    for node_id, item in all_items.items():
        for req in item.prerequisites:
            if req in adj:
                adj[req].append(node_id)

    # Detección de ciclos mediante DFS
    visited: dict[str, int] = {n: 0 for n in nodes}  # 0=unvisited, 1=visiting, 2=visited
    cycles: list[list[str]] = []

    def dfs(curr: str, path: list[str]) -> None:
        visited[curr] = 1
        path.append(curr)

        for neighbor in adj.get(curr, []):
            if visited[neighbor] == 1:
                # Ciclo encontrado
                idx = path.index(neighbor)
                cycles.append(path[idx:] + [neighbor])
            elif visited[neighbor] == 0:
                dfs(neighbor, path)

        path.pop()
        visited[curr] = 2

    for node in nodes:
        if visited[node] == 0:
            dfs(node, [])

    roots = [n for n, it in all_items.items() if not it.prerequisites]
    leaves = [n for n in nodes if not adj[n]]

    return {
        "nodes": nodes,
        "edges": [{"from": req, "to": n} for n, it in all_items.items() for req in it.prerequisites],
        "cycles": cycles,
        "roots": roots,
        "leaves": leaves,
        "valid": len(cycles) == 0,
    }


def validate_sequencing(course: Course) -> list[str]:
    """Audita reglas de secuenciamiento IMSSS y prerrequisitos en el árbol del curso."""
    errors: list[str] = []
    org = course.organization()
    all_items = _collect_all_items(org.items)

    # 1. Verificar existencia de ítems referenciados en prerrequisitos
    for node_id, item in all_items.items():
        for req in item.prerequisites:
            if req not in all_items:
                errors.append(
                    f"Ítem '{node_id}': el prerrequisito '{req}' no existe en el curso."
                )

    # 2. Detección de ciclos
    graph_info = analyze_sequencing_graph(course)
    for cycle in graph_info["cycles"]:
        cycle_str = " -> ".join(cycle)
        errors.append(f"Ciclo de secuenciamiento circular detectado: {cycle_str}")

    # 3. Verificar objetivos referenciados en reglas de secuenciamiento
    declared_objectives: set[str] = set()
    for item in all_items.values():
        for obj in item.objectives:
            declared_objectives.add(obj.identifier)

    for node_id, item in all_items.items():
        for rule in item.sequencing_rules:
            if rule.referenced_objective and rule.referenced_objective not in declared_objectives:
                errors.append(
                    f"Ítem '{node_id}': la regla de acción '{rule.action}' referencia un objetivo "
                    f"no declarado: '{rule.referenced_objective}'."
                )

        # 4. Ítems inalcanzables (choice=false y flow=false)
        if not item.choice and not item.flow and not item.prerequisites:
            errors.append(
                f"Ítem '{node_id}': navegación deshabilitada (flow=false y choice=false) sin reglas de activación."
            )

    return errors


def render_sequencing_tree(course: Course) -> str:
    """Genera una vista en texto estructurado del árbol y prerrequisitos."""
    org = course.organization()
    lines: list[str] = [f"Árbol de Secuenciamiento: {org.title} ({course.version.value})", ""]

    def _walk(items: list[Item], prefix: str = "") -> None:
        for i, it in enumerate(items):
            is_last = (i == len(items) - 1)
            marker = "└── " if is_last else "├── "
            child_prefix = "    " if is_last else "│   "

            flags = []
            if it.mastery_score is not None:
                flags.append(f"score>={it.mastery_score}")
            if it.prerequisites:
                flags.append(f"req:[{','.join(it.prerequisites)}]")
            if not it.flow:
                flags.append("flow=no")
            if not it.choice:
                flags.append("choice=no")
            if it.sequencing_rules:
                flags.append(f"rules:{len(it.sequencing_rules)}")
            if it.rollup_rules:
                flags.append(f"rollup:{len(it.rollup_rules)}")

            extra = f" ({', '.join(flags)})" if flags else ""
            lines.append(f"{prefix}{marker}{it.identifier}: {it.title}{extra}")

            if it.children:
                _walk(it.children, prefix + child_prefix)

    _walk(org.items)
    return "\n".join(lines)
