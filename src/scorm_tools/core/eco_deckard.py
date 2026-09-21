"""Integración con Deckard: from-deckard."""

from __future__ import annotations

import html
import re
from pathlib import Path

import yaml

from .models import Course, Item, Organization, Resource, ScormVersion


# ============================================================================
# 1. Integración con Deckard: from-deckard
# ============================================================================

def deckard_to_scorm(
    guia_path: Path,
    target_dir: Path,
    version: ScormVersion = ScormVersion.SCORM_2004_4ED,
    avisos: list[str] | None = None,
) -> Course:
    """Convierte una guía de ejercicios Deckard (guia.yaml) en un curso SCORM multi-SCO.

    El schema de deckard no está versionado, así que la lectura es por duck-typing
    (`nombre|title`, `ejercicios[].id/minutos/bloom/tema`). Todo campo esperado que
    falte se informa en `avisos` en vez de degradar en silencio a los defaults.
    """
    if avisos is None:
        avisos = []
    if not guia_path.exists():
        raise FileNotFoundError(f"No existe el archivo de guía Deckard: {guia_path}")

    raw = yaml.safe_load(guia_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("la guía Deckard debe ser un mapa YAML (nombre/ejercicios)")
    if not (raw.get("nombre") or raw.get("title")):
        avisos.append("la guía no define `nombre` ni `title`: se usa «Guía de Ejercicios»")
    titulo_guia = raw.get("nombre") or raw.get("title") or "Guía de Ejercicios"
    guia_id = re.sub(r"[^a-zA-Z0-9]+", "-", titulo_guia.lower()).strip("-") or "guia-deckard"

    target_dir.mkdir(parents=True, exist_ok=True)

    items: list[Item] = []
    resources: list[Resource] = []

    # Plantilla HTML para cada ejercicio interactivo
    ejercicios_raw = raw.get("ejercicios", [])
    if not ejercicios_raw:
        avisos.append("la guía no tiene `ejercicios`: el curso queda vacío")
    for idx, ej in enumerate(ejercicios_raw, 1):
        ej_id = ej.get("id") or f"ejercicio-{idx}"
        for campo, defecto in (("id", ej_id), ("minutos", 20), ("bloom", 2), ("tema", "General")):
            if campo not in ej or ej.get(campo) in (None, ""):
                avisos.append(f"ejercicio {idx}: falta `{campo}`, se usa {defecto!r}")
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
      // El estudiante declara haber hecho el ejercicio: eso es "completado",
      // no "aprobado". Marcar passed acá ponía un aprobado en el LMS sin que
      // nadie evaluara la solución.
      if (window.API_1484_11) {{
        window.API_1484_11.SetValue('cmi.completion_status', 'completed');
        window.API_1484_11.Commit('');
      }} else if (window.API) {{
        window.API.LMSSetValue('cmi.core.lesson_status', 'completed');
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
