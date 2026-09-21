"""Integración con IDKFA: exportador de tracing C."""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

import yaml

from .models import Course, Item, Organization, Resource, ScormVersion


# ============================================================================
# 6. Integración con IDKFA: Exportador de Tracing C
# ============================================================================

def parse_idkfa_template(content: str) -> dict[str, Any]:
    """Parsea una plantilla C de idkfa extrayendo código, consigna, nombre y opciones."""
    name_match = re.search(r"/\*name\s*\n(.*?)\*/", content, re.DOTALL)
    name = name_match.group(1).strip() if name_match else "Ejercicio de Tracing de Código C"

    opts_match = re.search(r"/\*opciones\s*\n(.*?)\*/", content, re.DOTALL)
    options = []
    if opts_match:
        for line in opts_match.group(1).splitlines():
            trimmed = line.strip()
            if trimmed:
                options.append(trimmed)

    # La plantilla declara la respuesta correcta en /*correcta*/. Ignorarla era
    # la razón por la que la actividad no podía evaluar nada.
    correcta_match = re.search(r"/\*correcta\s*\n(.*?)\*/", content, re.DOTALL)
    correcta = ""
    if correcta_match:
        for line in correcta_match.group(1).splitlines():
            trimmed = line.strip()
            # Las líneas que arrancan con `#` son expresiones que idkfa evalúa
            # con los valores sorteados; acá no hay forma de resolverlas.
            if trimmed and not trimmed.startswith("#"):
                correcta = trimmed
                break

    consigna_match = re.search(r"//\s*(.*?)\n#include", content, re.DOTALL)
    prompt = consigna_match.group(1).strip() if consigna_match else "¿Cuál es la salida del programa?"

    code = content
    code = re.sub(r"/\*name.*?\*/", "", code, flags=re.DOTALL)
    code = re.sub(r"/\*opciones.*?\*/", "", code, flags=re.DOTALL)
    code = re.sub(r"//.*?\n", "\n", code)
    code = code.strip()

    return {
        "name": name,
        "prompt": prompt,
        "code": code,
        "options": options or ["Salida esperada", "Error de compilación", "0"],
        "correcta": correcta,
    }


def idkfa_to_scorm_tracing(template_path: Path, target_dir: Path) -> Course:
    """Convierte una plantilla de tracing C de idkfa en una actividad interactiva SCORM autoevaluable."""
    if not template_path.exists():
        raise FileNotFoundError(f"No existe la plantilla IDKFA: {template_path}")

    content = template_path.read_text(encoding="utf-8", errors="replace")
    data = parse_idkfa_template(content)

    # Si la plantilla declara la respuesta correcta, la actividad se autoevalúa.
    # Si no —porque idkfa la resuelve recién al sortear las variables—, se
    # registra la respuesta sin emitir veredicto: es preferible que el docente
    # corrija a que el LMS reciba un "aprobado" que nadie evaluó.
    autoevaluable = bool(data["correcta"])
    opciones = list(data["options"])
    if autoevaluable:
        # La correcta se mezcla entre los distractores en una posición estable
        # por plantilla, para que no quede siempre al final.
        indice_correcto = sum(ord(c) for c in data["name"]) % (len(opciones) + 1)
        opciones.insert(indice_correcto, data["correcta"])
    else:
        indice_correcto = -1
    data = {**data, "options": opciones}

    target_dir.mkdir(parents=True, exist_ok=True)
    cid = re.sub(r"[^a-zA-Z0-9]+", "-", data["name"].lower()).strip("-") or "tracing-c"

    if autoevaluable:
        script_evaluacion = """var OPCION_CORRECTA = %d;

    document.getElementById('btn-evaluar').addEventListener('click', function() {
      var sel = document.querySelector('input[name="opt"]:checked');
      if (!sel) return;
      this.disabled = true;

      var acerto = parseInt(sel.value, 10) === OPCION_CORRECTA;
      var puntaje = acerto ? '100' : '0';
      document.getElementById('feedback').textContent = acerto
        ? '\u2713 Respuesta correcta'
        : '\u2717 Respuesta incorrecta';

      if (window.API_1484_11) {
        window.API_1484_11.SetValue('cmi.score.raw', puntaje);
        window.API_1484_11.SetValue('cmi.completion_status', 'completed');
        window.API_1484_11.SetValue('cmi.success_status', acerto ? 'passed' : 'failed');
        window.API_1484_11.Commit('');
      } else if (window.API) {
        window.API.LMSSetValue('cmi.core.score.raw', puntaje);
        window.API.LMSSetValue('cmi.core.lesson_status', acerto ? 'passed' : 'failed');
        window.API.LMSCommit('');
      }
    });""" % indice_correcto
    else:
        script_evaluacion = """document.getElementById('btn-evaluar').addEventListener('click', function() {
      var sel = document.querySelector('input[name="opt"]:checked');
      if (!sel) return;
      this.disabled = true;

      // La plantilla no declara la respuesta correcta (idkfa la resuelve al
      // sortear las variables): se deja constancia de lo elegido y corrige el
      // equipo docente. Emitir un veredicto acá seria inventarlo.
      document.getElementById('feedback').textContent =
        'Respuesta registrada. La correccion la realiza el equipo docente.';

      if (window.API_1484_11) {
        window.API_1484_11.SetValue('cmi.suspend_data', 'opcion=' + sel.value);
        window.API_1484_11.SetValue('cmi.completion_status', 'completed');
        window.API_1484_11.Commit('');
      } else if (window.API) {
        window.API.LMSSetValue('cmi.suspend_data', 'opcion=' + sel.value);
        window.API.LMSSetValue('cmi.core.lesson_status', 'completed');
        window.API.LMSCommit('');
      }
    });"""

    options_html = ""
    for i, opt in enumerate(data["options"]):
        options_html += f"""
      <label class="option-item">
        <input type="radio" name="opt" value="{i}">
        <code>{html.escape(opt)}</code>
      </label><br>"""

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>{html.escape(data["name"])}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #0f172a; color: #f8fafc; }}
    .container {{ max-width: 800px; margin: auto; background: #1e293b; padding: 2rem; border-radius: 8px; }}
    h1 {{ color: #38bdf8; font-size: 1.4rem; }}
    .prompt {{ font-size: 1.1rem; margin-bottom: 1rem; }}
    pre {{ background: #020617; padding: 1rem; border-radius: 6px; border: 1px solid #334155; overflow-x: auto; color: #a5f3fc; }}
    .options {{ margin: 1.5rem 0; }}
    .option-item {{ display: block; padding: 0.5rem; margin-bottom: 0.5rem; background: #334155; border-radius: 4px; cursor: pointer; }}
    .btn {{ background: #0284c7; color: white; border: none; padding: 0.6rem 1.2rem; border-radius: 4px; cursor: pointer; }}
    .feedback {{ margin-top: 1rem; font-weight: bold; color: #4ade80; }}
  </style>
  <script src="scorm-api.js"></script>
</head>
<body>
  <div class="container">
    <h1>{html.escape(data["name"])}</h1>
    <div class="prompt">{html.escape(data["prompt"])}</div>
    <pre><code>{html.escape(data["code"])}</code></pre>
    <div class="options">
      {options_html}
    </div>
    <button id="btn-evaluar" class="btn">Confirmar Respuesta</button>
    <div id="feedback" class="feedback"></div>
  </div>
  <script>
    {script_evaluacion}
  </script>
</body>
</html>
"""
    (target_dir / "index.html").write_text(html_content, encoding="utf-8")
    (target_dir / "scorm-api.js").write_text("// SCORM API wrapper\n", encoding="utf-8")

    course = Course(
        identifier=f"COURSE-{cid.upper()}",
        title=data["name"],
        version=ScormVersion.SCORM_2004_4ED,
        organizations=[
            Organization(
                identifier=f"ORG-{cid.upper()}",
                title=data["name"],
                items=[Item(identifier=f"ITEM-{cid.upper()}", title=data["name"], resource_identifier=f"RES-{cid.upper()}", mastery_score=70)],
            )
        ],
        resources=[
            Resource(identifier=f"RES-{cid.upper()}", href="index.html", files=["index.html", "scorm-api.js"], scorm_type="sco")
        ],
    )

    (target_dir / "scorm.yaml").write_text(
        yaml.dump(
            {
                "identifier": course.identifier,
                "title": course.title,
                "version": course.version.value,
                "organizations": [{"identifier": f"ORG-{cid.upper()}", "title": data["name"], "items": [{"identifier": f"ITEM-{cid.upper()}", "title": data["name"], "resource": f"RES-{cid.upper()}", "mastery_score": 70}]}],
                "resources": [{"identifier": f"RES-{cid.upper()}", "href": "index.html", "type": "sco", "files": ["index.html", "scorm-api.js"]}],
            },
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    return course
