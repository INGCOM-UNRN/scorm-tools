"""Integración con Ripley / Kaneda / Spunkmeyer y Dredd: auditoría de C embebido y trazas."""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any




# ============================================================================
# 4. Integración con Ripley / Kaneda / Spunkmeyer: Auditor de Código C Embebido
# ============================================================================

def _obtener_catalogo_kaneda() -> dict[str, dict[str, str]]:
    """Carga canónicamente el catálogo de seguridad de Kaneda."""
    try:
        from kaneda.core.rules import CATALOGO_SEGURIDAD
        return CATALOGO_SEGURIDAD
    except ImportError:
        import sys
        sibling = Path(__file__).resolve().parents[4] / "kaneda" / "src"
        if sibling.is_dir() and str(sibling) not in sys.path:
            sys.path.insert(0, str(sibling))
        try:
            from kaneda.core.rules import CATALOGO_SEGURIDAD
            return CATALOGO_SEGURIDAD
        except ImportError:
            return {
                "KAN001": {
                    "titulo": "Uso de la función prohibida 'gets()'",
                    "severidad": "CRITICO",
                    "descripcion": "'gets()' no verifica los límites del búfer destino y es intrínsecamente vulnerable a desbordamientos de búfer (Buffer Overflow).",
                    "sugerencia": "Reemplazá 'gets(buf)' por 'fgets(buf, sizeof(buf), stdin)'.",
                }
            }


def _obtener_catalogo_spunkmeyer() -> dict[str, dict[str, str]]:
    """Carga canónicamente el catálogo de antipatrones de Spunkmeyer."""
    try:
        from spunkmeyer.core.detector import CATALOGO_ANTIPATRONES
        return CATALOGO_ANTIPATRONES
    except ImportError:
        import sys
        sibling = Path(__file__).resolve().parents[4] / "spunkmeyer" / "src"
        if sibling.is_dir() and str(sibling) not in sys.path:
            sys.path.insert(0, str(sibling))
        try:
            from spunkmeyer.core.detector import CATALOGO_ANTIPATRONES
            return CATALOGO_ANTIPATRONES
        except ImportError:
            return {
                "0x300Ah": {
                    "codigo": "0x300Ah", "alias": "AP001",
                    "nombre": "Casteo redundante de malloc()",
                    "mensaje": "Castear el retorno de 'malloc()' es innecesario en C y puede enmascarar la falta de #include <stdlib.h>.",
                },
                "0x4002h": {
                    "codigo": "0x4002h", "alias": "AP002",
                    "nombre": "Control de lectura con while(!feof())",
                    "mensaje": "Usar '!feof(f)' como condición del bucle provoca procesar el último registro dos veces.",
                },
            }


def extract_and_audit_c_code(dir_path: Path) -> list[dict[str, Any]]:
    """Extrae bloques de código C dentro de archivos HTML y detecta antipatrones/inseguridades consumiendo Kaneda y Spunkmeyer."""
    findings: list[dict[str, Any]] = []

    c_block_pattern = re.compile(r"<code(?:\s+class=[\"'](?:language-c|c)[\"'])?>(.*?)</code>", re.DOTALL | re.IGNORECASE)

    kaneda_cat = _obtener_catalogo_kaneda()
    spunk_cat = _obtener_catalogo_spunkmeyer()

    for html_file in dir_path.rglob("*.html"):
        content = html_file.read_text(encoding="utf-8", errors="replace")
        for match in c_block_pattern.finditer(content):
            snippet = html.unescape(match.group(1)).strip()
            if not snippet or len(snippet) < 10:
                continue

            # Inseguridad en funciones (Kaneda KAN001)
            if re.search(r"\bgets\s*\(", snippet):
                kan_info = kaneda_cat.get("KAN001", {})
                findings.append({
                    "file": str(html_file.name),
                    "rule": "KAN001 / 0x3001h (SEGURIDAD)",
                    "detail": kan_info.get("titulo", "Uso de la función prohibida 'gets()'.") + " " + kan_info.get("descripcion", "Provoca desbordamiento de búfer."),
                })

            # Antipatrones didácticos (Spunkmeyer AP001: 0x300Ah / AP002: 0x4002h)
            if re.search(r"\([a-zA-Z0-9_]+\s*\*\)\s*malloc\b", snippet):
                sp_info = spunk_cat.get("0x300Ah", {})
                findings.append({
                    "file": str(html_file.name),
                    "rule": f"{sp_info.get('alias', 'AP001')} / 0x300Ah (ANTIPATRÓN)",
                    "detail": sp_info.get("mensaje", "Casteo redundante del retorno de malloc() en C."),
                })

            if re.search(r"\bwhile\s*\(\s*!feof\s*\(", snippet):
                sp_info = spunk_cat.get("0x4002h", {})
                findings.append({
                    "file": str(html_file.name),
                    "rule": f"{sp_info.get('alias', 'AP002')} / 0x4002h (ANTIPATRÓN)",
                    "detail": sp_info.get("mensaje", "Uso del antipatrón 'while (!feof(f))'. Provoca lectura duplicada."),
                })

    return findings


# ============================================================================
# 5. Integración con Dredd: Parser de Trazas y Reportes
# ============================================================================

def parse_scorm_tracking_log(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parsea entradas de tracking de Moodle SCORM para consolidar notas e intentos para Dredd."""
    grades: list[dict[str, Any]] = []

    for entry in entries:
        student_id = entry.get("student_id") or entry.get("userid") or "DESCONOCIDO"
        score_raw = entry.get("score_raw") or entry.get("cmi.core.score.raw") or entry.get("cmi.score.raw")
        status = entry.get("lesson_status") or entry.get("cmi.core.lesson_status") or entry.get("cmi.completion_status") or "incomplete"

        try:
            score = float(score_raw) if score_raw is not None else 0.0
        except ValueError:
            score = 0.0

        passed = (status.lower() in ("passed", "completed") or score >= 70.0)

        grades.append({
            "student_id": str(student_id),
            "score": score,
            "status": status,
            "passed": passed,
            "feedback": f"SCORM Score: {score:.1f}% | Estado: {status}",
        })

    return grades
