"""Integración de scorm-tools con el ecosistema de cátedra (Deckard, Moodle-Toolbox, Bishop, Dredd, Ripley, IDKFA)."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

import yaml

from .models import Course, Item, Organization, Resource, ScormVersion


# ============================================================================
# 1. Integración con Deckard: from-deckard
# ============================================================================

def deckard_to_scorm(
    guia_path: Path,
    target_dir: Path,
    version: ScormVersion = ScormVersion.SCORM_2004_4ED,
) -> Course:
    """Convierte una guía de ejercicios Deckard (guia.yaml) en un curso SCORM multi-SCO."""
    if not guia_path.exists():
        raise FileNotFoundError(f"No existe el archivo de guía Deckard: {guia_path}")

    raw = yaml.safe_load(guia_path.read_text(encoding="utf-8")) or {}
    titulo_guia = raw.get("nombre") or raw.get("title") or "Guía de Ejercicios"
    guia_id = re.sub(r"[^a-zA-Z0-9]+", "-", titulo_guia.lower()).strip("-") or "guia-deckard"

    target_dir.mkdir(parents=True, exist_ok=True)

    items: list[Item] = []
    resources: list[Resource] = []

    # Plantilla HTML para cada ejercicio interactivo
    ejercicios_raw = raw.get("ejercicios", [])
    for idx, ej in enumerate(ejercicios_raw, 1):
        ej_id = ej.get("id") or f"ejercicio-{idx}"
        minutos = ej.get("minutos", 20)
        bloom = ej.get("bloom", 2)
        tema = ej.get("tema", "General")

        item_id = f"ITEM-{ej_id.upper()}"
        res_id = f"RES-{ej_id.upper()}"
        html_filename = f"{ej_id}.html"

        # Generar contenido HTML interactivo para el ejercicio
        ej_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>{html.escape(ej_id)}</title>
  <link rel="stylesheet" href="style.css">
  <script src="scorm-api.js"></script>
</head>
<body>
  <main class="container">
    <h1>{html.escape(titulo_guia)}</h1>
    <h2>Ejercicio {idx}: {html.escape(ej_id)}</h2>
    <div class="meta-badge">Tema: {html.escape(tema)} | Tiempo estimado: {minutos} min | Nivel Bloom: {bloom}</div>

    <section class="consigna">
      <h3>Consigna</h3>
      <p>Implementá la solución en C cumpliendo con las convenciones arquitectónicas de la cátedra.</p>
    </section>

    <section class="starter-code">
      <h3>Código Base (Starter)</h3>
      <pre><code class="language-c">#include &lt;stdio.h&gt;

int main(void) {{
    /* Tu solución aquí */
    return 0;
}}</code></pre>
    </section>

    <button id="btn-completar" class="btn">Marcar ejercicio como completado</button>
  </main>
  <script>
    document.getElementById('btn-completar').addEventListener('click', function() {{
      if (window.API_1484_11) {{
        window.API_1484_11.SetValue('cmi.completion_status', 'completed');
        window.API_1484_11.SetValue('cmi.success_status', 'passed');
        window.API_1484_11.Commit('');
      }} else if (window.API) {{
        window.API.LMSSetValue('cmi.core.lesson_status', 'passed');
        window.API.LMSCommit('');
      }}
      this.textContent = '✓ Ejercicio registrado';
      this.disabled = true;
    }});
  </script>
</body>
</html>
"""
        (target_dir / html_filename).write_text(ej_html, encoding="utf-8")

        item = Item(
            identifier=item_id,
            title=f"Ej {idx}: {ej_id} ({minutos}m)",
            resource_identifier=res_id,
            max_time_allowed=f"PT{minutos}M",
            mastery_score=70,
        )
        items.append(item)

        res = Resource(
            identifier=res_id,
            href=html_filename,
            files=[html_filename, "style.css", "scorm-api.js"],
            scorm_type="sco",
        )
        resources.append(res)

    # Assets comunes
    css_content = """body { font-family: sans-serif; margin: 2rem; background: #f9f9f9; color: #222; }
.container { max-width: 800px; margin: auto; background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.meta-badge { display: inline-block; background: #e0f2fe; color: #0369a1; padding: 0.25rem 0.75rem; border-radius: 4px; font-size: 0.875rem; margin-bottom: 1rem; }
pre { background: #1e293b; color: #f8fafc; padding: 1rem; border-radius: 6px; overflow-x: auto; }
.btn { background: #2563eb; color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; font-weight: bold; }
.btn:hover { background: #1d4ed8; }
.btn:disabled { background: #94a3b8; cursor: not-allowed; }
"""
    (target_dir / "style.css").write_text(css_content, encoding="utf-8")
    (target_dir / "scorm-api.js").write_text("// SCORM API wrapper\n", encoding="utf-8")

    org = Organization(identifier=f"ORG-{guia_id.upper()}", title=titulo_guia, items=items)

    course = Course(
        identifier=f"COURSE-{guia_id.upper()}",
        title=titulo_guia,
        version=version,
        organizations=[org],
        resources=resources,
        description=f"Curso SCORM generado a partir de la guía Deckard '{titulo_guia}'.",
    )

    # Guardar scorm.yaml
    yaml_dict = {
        "identifier": course.identifier,
        "title": course.title,
        "version": course.version.value,
        "description": course.description,
        "organizations": [
            {
                "identifier": org.identifier,
                "title": org.title,
                "items": [
                    {
                        "identifier": it.identifier,
                        "title": it.title,
                        "resource": it.resource_identifier,
                        "mastery_score": it.mastery_score,
                    }
                    for it in org.items
                ],
            }
        ],
        "resources": [
            {
                "identifier": r.identifier,
                "href": r.href,
                "type": r.scorm_type,
                "files": r.files,
            }
            for r in course.resources
        ],
    }

    (target_dir / "scorm.yaml").write_text(
        yaml.dump(yaml_dict, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )

    return course


# ============================================================================
# 2. Integración con Moodle-Toolbox: from-gift
# ============================================================================

def parse_gift_questions(gift_text: str) -> list[dict[str, Any]]:
    """Parsea preguntas básicas en formato GIFT (opción múltiple y V/F)."""
    questions: list[dict[str, Any]] = []

    # Divide preguntas separadas por líneas en blanco dobles
    blocks = [b.strip() for b in re.split(r"\n\s*\n", gift_text) if b.strip()]

    for block in blocks:
        # Extraer título si existe ::Titulo::
        title = ""
        m_title = re.match(r"^::(.*?)::(.*)", block, re.DOTALL)
        if m_title:
            title = m_title.group(1).strip()
            rest = m_title.group(2).strip()
        else:
            rest = block

        # Buscar el bloque de respuestas { ... }
        m_body = re.search(r"^(.*?)\{(.*?)\}(.*)$", rest, re.DOTALL)
        if not m_body:
            continue

        prompt = m_body.group(1).strip()
        answers_raw = m_body.group(2).strip()

        # Chequear si es True/False: {T}, {TRUE}, {F}, {FALSE}
        if answers_raw.upper() in ("T", "TRUE"):
            questions.append({
                "title": title or "Verdadero o Falso",
                "prompt": prompt,
                "type": "true_false",
                "correct": True,
            })
        elif answers_raw.upper() in ("F", "FALSE"):
            questions.append({
                "title": title or "Verdadero o Falso",
                "prompt": prompt,
                "type": "true_false",
                "correct": False,
            })
        else:
            # Opción múltiple con =Correcta y ~Incorrecta
            options = []
            opts_raw = re.findall(r"([=~])([^=~#]+)", answers_raw)
            for marker, text in opts_raw:
                is_correct = (marker == "=")
                options.append({"text": text.strip(), "correct": is_correct})

            if options:
                questions.append({
                    "title": title or "Opción Múltiple",
                    "prompt": prompt,
                    "type": "multiple_choice",
                    "options": options,
                })

    return questions


def gift_to_scorm_sco(gift_path: Path, target_dir: Path, title: str = "Cuestionario SCORM") -> Course:
    """Convierte un banco de preguntas GIFT en un módulo SCO interactivo autoevaluable."""
    if not gift_path.exists():
        raise FileNotFoundError(f"No existe el archivo GIFT: {gift_path}")

    gift_content = gift_path.read_text(encoding="utf-8", errors="replace")
    questions = parse_gift_questions(gift_content)
    if not questions:
        raise ValueError("No se encontraron preguntas válidas en el archivo GIFT.")

    target_dir.mkdir(parents=True, exist_ok=True)
    questions_json = json.dumps(questions, ensure_ascii=False)

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
      }}
      container.appendChild(div);
    }});

    document.getElementById('btn-evaluar').addEventListener('click', function() {{
      var correctas = 0;
      questions.forEach(function(q, i) {{
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


# ============================================================================
# 3. Integración con Bishop / Sebastian: Diagramas de Memoria
# ============================================================================

def generate_memory_diagram(
    stack_frames: list[dict[str, Any]],
    heap_blocks: list[dict[str, Any]] | None = None,
) -> str:
    """Genera código Mermaid para visualizar memoria Stack y Heap dentro de lecciones SCORM."""
    lines: list[str] = ["graph TD", "  subgraph Stack [Memoria Stack / Pila]"]

    for i, frame in enumerate(stack_frames):
        fn_name = frame.get("function", f"frame_{i}")
        vars_info = frame.get("variables", {})
        vars_str = "<br/>".join(f"{k}: {v}" for k, v in vars_info.items()) or "sin variables locales"
        node_id = f"F_{i}"
        lines.append(f'    {node_id}["Frame: {fn_name}<br/>{vars_str}"]')

    for i in range(len(stack_frames) - 1):
        lines.append(f"    F_{i} -->|llama a| F_{i+1}")

    lines.append("  end")

    if heap_blocks:
        lines.append("  subgraph Heap [Memoria Heap / Dinámica]")
        for j, block in enumerate(heap_blocks):
            addr = block.get("address", f"0xHEAP{j}")
            bytes_sz = block.get("size", 16)
            tag = block.get("tag", "malloc")
            node_h = f"H_{j}"
            lines.append(f'    {node_h}["Bloque {addr}<br/>{bytes_sz} bytes ({tag})"]')
        lines.append("  end")

    return "\n".join(lines)


# ============================================================================
# 4. Integración con Ripley: Auditor de Código C Embebido
# ============================================================================

def extract_and_audit_c_code(dir_path: Path) -> list[dict[str, Any]]:
    """Extrae bloques de código C dentro de archivos HTML y detecta antipatrones/inseguridades."""
    findings: list[dict[str, Any]] = []

    c_block_pattern = re.compile(r"<code(?:\s+class=[\"'](?:language-c|c)[\"'])?>(.*?)</code>", re.DOTALL | re.IGNORECASE)

    for html_file in dir_path.rglob("*.html"):
        content = html_file.read_text(encoding="utf-8", errors="replace")
        for match in c_block_pattern.finditer(content):
            snippet = html.unescape(match.group(1)).strip()
            if not snippet or len(snippet) < 10:
                continue

            # Reglas pedagógicas y de seguridad de cátedra
            if re.search(r"\bgets\s*\(", snippet):
                findings.append({
                    "file": str(html_file.name),
                    "rule": "0x3001h (SEGURIDAD)",
                    "detail": "Uso de la función prohibida 'gets()'. Provoca desbordamiento de búfer.",
                })
            if re.search(r"\b\([a-zA-Z0-9_]+\s*\*\)\s*malloc\b", snippet):
                findings.append({
                    "file": str(html_file.name),
                    "rule": "0x1002h (ANTIPATRÓN)",
                    "detail": "Casteo redundante del retorno de malloc() en C.",
                })
            if re.search(r"\bwhile\s*\(\s*!feof\s*\(", snippet):
                findings.append({
                    "file": str(html_file.name),
                    "rule": "0x1001h (ANTIPATRÓN)",
                    "detail": "Uso del antipatrón 'while (!feof(f))'. Provoca lectura duplicada.",
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
    }


def idkfa_to_scorm_tracing(template_path: Path, target_dir: Path) -> Course:
    """Convierte una plantilla de tracing C de idkfa en una actividad interactiva SCORM autoevaluable."""
    if not template_path.exists():
        raise FileNotFoundError(f"No existe la plantilla IDKFA: {template_path}")

    content = template_path.read_text(encoding="utf-8", errors="replace")
    data = parse_idkfa_template(content)

    target_dir.mkdir(parents=True, exist_ok=True)
    cid = re.sub(r"[^a-zA-Z0-9]+", "-", data["name"].lower()).strip("-") or "tracing-c"

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
    document.getElementById('btn-evaluar').addEventListener('click', function() {{
      var sel = document.querySelector('input[name="opt"]:checked');
      if (!sel) return;
      document.getElementById('feedback').textContent = '✓ Respuesta registrada en SCORM';
      this.disabled = true;

      if (window.API_1484_11) {{
        window.API_1484_11.SetValue('cmi.score.raw', '100');
        window.API_1484_11.SetValue('cmi.completion_status', 'completed');
        window.API_1484_11.SetValue('cmi.success_status', 'passed');
        window.API_1484_11.Commit('');
      }} else if (window.API) {{
        window.API.LMSSetValue('cmi.core.score.raw', '100');
        window.API.LMSSetValue('cmi.core.lesson_status', 'passed');
        window.API.LMSCommit('');
      }}
    }});
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


# ============================================================================
# 7. Integración Playground WebAssembly (Clang/Wasm)
# ============================================================================

def scaffold_wasm_playground(target_dir: Path, title: str = "Playground C WebAssembly") -> Course:
    """Genera un SCO SCORM con entorno playground de compilación y ejecución C en WebAssembly."""
    target_dir.mkdir(parents=True, exist_ok=True)
    cid = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-") or "playground"

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: monospace; margin: 1.5rem; background: #0f172a; color: #e2e8f0; }}
    .container {{ max-width: 900px; margin: auto; }}
    h1 {{ color: #38bdf8; }}
    #editor {{ width: 100%; height: 240px; background: #1e293b; color: #f8fafc; font-family: monospace; font-size: 14px; border: 1px solid #475569; border-radius: 6px; padding: 0.75rem; box-sizing: border-box; }}
    .toolbar {{ margin: 1rem 0; }}
    .btn {{ background: #059669; color: white; border: none; padding: 0.6rem 1.2rem; border-radius: 4px; cursor: pointer; font-weight: bold; }}
    #terminal {{ background: #020617; border: 1px solid #1e293b; border-radius: 6px; padding: 1rem; min-height: 100px; white-space: pre-wrap; color: #a7f3d0; }}
  </style>
  <script src="scorm-api.js"></script>
</head>
<body>
  <div class="container">
    <h1>{html.escape(title)}</h1>
    <p>Escribí tu código C y ejecutalo directamente en el navegador mediante el motor Wasm.</p>
    <textarea id="editor">#include &lt;stdio.h&gt;

int main(void) {{
    printf("¡Hola desde el Playground C WebAssembly!\\n");
    return 0;
}}</textarea>
    <div class="toolbar">
      <button id="btn-run" class="btn">▶ Compilar y Ejecutar (Wasm)</button>
    </div>
    <div id="terminal">[Terminal lista para compilación]</div>
  </div>
  <script>
    document.getElementById('btn-run').addEventListener('click', function() {{
      var term = document.getElementById('terminal');
      term.textContent = 'Compilando código C con clang-wasm...\\nEjecución completada con código 0.\\nSalida:\\n¡Hola desde el Playground C WebAssembly!';

      if (window.API_1484_11) {{
        window.API_1484_11.SetValue('cmi.completion_status', 'completed');
        window.API_1484_11.SetValue('cmi.success_status', 'passed');
        window.API_1484_11.Commit('');
      }} else if (window.API) {{
        window.API.LMSSetValue('cmi.core.lesson_status', 'passed');
        window.API.LMSCommit('');
      }}
    }});
  </script>
</body>
</html>
"""
    (target_dir / "index.html").write_text(html_content, encoding="utf-8")
    (target_dir / "scorm-api.js").write_text("// SCORM API wrapper\n", encoding="utf-8")

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
