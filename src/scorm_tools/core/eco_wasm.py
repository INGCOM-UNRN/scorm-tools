"""Playground WebAssembly (Clang/Wasm)."""

from __future__ import annotations

import html
import re
from pathlib import Path

import yaml

from .models import Course, Item, Organization, Resource, ScormVersion


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
    <p>Escribí y revisá tu código C. Este paquete no incluye un compilador: para
    compilarlo y ejecutarlo usá <code>daedalus</code> en tu equipo.</p>
    <textarea id="editor">#include &lt;stdio.h&gt;

int main(void) {{
    printf("¡Hola desde el Playground C WebAssembly!\\n");
    return 0;
}}</textarea>
    <div class="toolbar">
      <button id="btn-copiar" class="btn">Copiar código</button>
    </div>
    <div id="terminal">[Sin compilador embebido: copiá el código y compilalo con `daedalus compile`]</div>
  </div>
  <script>
    document.getElementById('btn-copiar').addEventListener('click', function() {{
      var codigo = document.getElementById('editor').value;
      var term = document.getElementById('terminal');
      if (navigator.clipboard) {{
        navigator.clipboard.writeText(codigo);
        term.textContent = 'Código copiado. Compilalo con: daedalus compile archivo.c -o programa';
      }} else {{
        term.textContent = 'Copiá el código del editor y compilalo con: daedalus compile archivo.c -o programa';
      }}

      // Un playground es una zona de práctica, no una evaluación: marcar la
      // actividad como vista alcanza. Antes fijaba success_status='passed' sin
      // compilar ni evaluar nada, y ese "aprobado" viajaba al seguimiento que
      // dredd-sync consolida para el docente.
      if (window.API_1484_11) {{
        window.API_1484_11.SetValue('cmi.completion_status', 'completed');
        window.API_1484_11.Commit('');
      }} else if (window.API) {{
        window.API.LMSSetValue('cmi.core.lesson_status', 'completed');
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
