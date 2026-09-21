"""Integración con Moodle-Toolbox: from-gift."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

import yaml

from .gift_quiz import parsear_gift
from .models import Course, Item, Organization, Resource, ScormVersion


# ============================================================================
# 2. Integración con Moodle-Toolbox: from-gift
# ============================================================================

def parse_gift_questions(gift_text: str) -> list[dict[str, Any]]:
    """Parsea un banco GIFT a las preguntas que el cuestionario sabe corregir.

    Las que no se pueden representar se descartan de esta lista; `parsear_gift` devuelve además
    cuáles fueron y por qué (`gift_to_scorm_sco` lo informa).
    """
    return parsear_gift(gift_text).preguntas


def gift_to_scorm_sco(
    gift_path: Path,
    target_dir: Path,
    title: str = "Cuestionario SCORM",
    avisos: list[str] | None = None,
) -> Course:
    """Convierte un banco de preguntas GIFT en un módulo SCO interactivo autoevaluable.

    Si se pasa `avisos`, se le agrega un mensaje por cada pregunta que no se pudo incluir.
    """
    if not gift_path.exists():
        raise FileNotFoundError(f"No existe el archivo GIFT: {gift_path}")

    gift_content = gift_path.read_text(encoding="utf-8", errors="replace")
    leidas = parsear_gift(gift_content)
    questions = leidas.preguntas
    if avisos is not None:
        avisos.extend(f"Se omitió «{o['titulo']}»: {o['motivo']}." for o in leidas.omitidas)
    if not questions:
        detalle = "; ".join(f"«{o['titulo']}»: {o['motivo']}" for o in leidas.omitidas)
        raise ValueError(
            "No se encontraron preguntas válidas en el archivo GIFT."
            + (f" Omitidas: {detalle}." if detalle else "")
        )

    target_dir.mkdir(parents=True, exist_ok=True)
    # `</` dentro de un texto cerraría el <script> que lo contiene.
    questions_json = json.dumps(questions, ensure_ascii=False).replace("</", "<\\/")

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #f8fafc; color: #0f172a; }}
    .container {{ max-width: 750px; margin: auto; background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
    .pregunta {{ margin-bottom: 2rem; padding: 1rem; border: 1px solid #e2e8f0; border-radius: 6px; }}
    .btn {{ background: #0284c7; color: white; border: none; padding: 0.6rem 1.2rem; border-radius: 4px; cursor: pointer; font-size: 1rem; }}
    .btn:hover {{ background: #0369a1; }}
    .resultado {{ margin-top: 1rem; font-weight: bold; font-size: 1.1rem; }}
  </style>
  <script src="scorm-api.js"></script>
</head>
<body>
  <div class="container">
    <h1>{html.escape(title)}</h1>
    <div id="quiz-container"></div>
    <button id="btn-evaluar" class="btn">Entregar y Calificar</button>
    <div id="resultado" class="resultado"></div>
  </div>
  <script>
    var questions = {questions_json};
    var container = document.getElementById('quiz-container');

    questions.forEach(function(q, i) {{
      var div = document.createElement('div');
      div.className = 'pregunta';
      div.innerHTML = '<h3>' + (i+1) + '. ' + q.prompt + '</h3>';
      if (q.type === 'true_false') {{
        div.innerHTML += '<label><input type="radio" name="q' + i + '" value="true"> Verdadero</label><br>' +
                         '<label><input type="radio" name="q' + i + '" value="false"> Falso</label>';
      }} else if (q.type === 'multiple_choice') {{
        q.options.forEach(function(opt, j) {{
          div.innerHTML += '<label><input type="radio" name="q' + i + '" value="' + j + '"> ' + opt.text + '</label><br>';
        }});
      }} else if (q.type === 'short_answer' || q.type === 'numeric') {{
        div.innerHTML += '<input type="text" name="q' + i + '" autocomplete="off" placeholder="Tu respuesta">';
      }}
      container.appendChild(div);
    }});

    document.getElementById('btn-evaluar').addEventListener('click', function() {{
      var correctas = 0;
      function normalizar(t) {{ return t.trim().toLowerCase().replace(/\\s+/g, ' '); }}
      function numericaCorrecta(q, texto) {{
        var v = parseFloat(texto.trim().replace(',', '.'));
        if (isNaN(v)) return false;
        return q.answers.some(function(a) {{
          if (a.min !== undefined) return v >= a.min && v <= a.max;
          return Math.abs(v - a.value) <= a.tolerance + 1e-9;
        }});
      }}
      questions.forEach(function(q, i) {{
        if (q.type === 'short_answer' || q.type === 'numeric') {{
          var caja = document.querySelector('input[name="q' + i + '"]');
          if (!caja || !caja.value.trim()) return;
          if (q.type === 'short_answer') {{
            if (q.answers.some(function(a) {{ return normalizar(a) === normalizar(caja.value); }})) correctas++;
          }} else if (numericaCorrecta(q, caja.value)) {{
            correctas++;
          }}
          return;
        }}
        var sel = document.querySelector('input[name="q' + i + '"]:checked');
        if (!sel) return;
        if (q.type === 'true_false') {{
          if ((sel.value === 'true') === q.correct) correctas++;
        }} else if (q.type === 'multiple_choice') {{
          var idx = parseInt(sel.value, 10);
          if (q.options[idx] && q.options[idx].correct) correctas++;
        }}
      }});
      var nota = Math.round((correctas / questions.length) * 100);
      var aprobado = (nota >= 70);
      document.getElementById('resultado').innerHTML = 'Calificación: ' + nota + '/100 (' + (aprobado ? 'Aprobado' : 'Desaprobado') + ')';

      if (window.API_1484_11) {{
        window.API_1484_11.SetValue('cmi.score.raw', nota.toString());
        window.API_1484_11.SetValue('cmi.completion_status', 'completed');
        window.API_1484_11.SetValue('cmi.success_status', aprobado ? 'passed' : 'failed');
        window.API_1484_11.Commit('');
      }} else if (window.API) {{
        window.API.LMSSetValue('cmi.core.score.raw', nota.toString());
        window.API.LMSSetValue('cmi.core.lesson_status', aprobado ? 'passed' : 'failed');
        window.API.LMSCommit('');
      }}
      this.disabled = true;
    }});
  </script>
</body>
</html>
"""
    (target_dir / "index.html").write_text(html_content, encoding="utf-8")
    (target_dir / "scorm-api.js").write_text("// SCORM API wrapper\n", encoding="utf-8")

    cid = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-") or "cuestionario"
    course = Course(
        identifier=f"COURSE-{cid.upper()}",
        title=title,
        version=ScormVersion.SCORM_2004_4ED,
        organizations=[
            Organization(
                identifier=f"ORG-{cid.upper()}",
                title=title,
                items=[Item(identifier=f"ITEM-{cid.upper()}", title=title, resource_identifier=f"RES-{cid.upper()}", mastery_score=70)],
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
                "organizations": [{"identifier": f"ORG-{cid.upper()}", "title": title, "items": [{"identifier": f"ITEM-{cid.upper()}", "title": title, "resource": f"RES-{cid.upper()}", "mastery_score": 70}]}],
                "resources": [{"identifier": f"RES-{cid.upper()}", "href": "index.html", "type": "sco", "files": ["index.html", "scorm-api.js"]}],
            },
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    return course
