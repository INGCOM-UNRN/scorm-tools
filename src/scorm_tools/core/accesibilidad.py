"""Accesibilidad de las páginas HTML de un paquete SCORM (`scorm-tools validate --a11y`).

Revisión 05 §3: ninguna herramienta chequeaba la accesibilidad del material en SCORM. Se revisan los
criterios de WCAG 2.1 que se ven en el HTML; son los mismos que `myst-tools check-a11y` aplica al
fuente MyST (texto alternativo, encabezados, enlaces, contraste, iframes), más los propios de una
página: el idioma (`lang`), el `<title>`, las etiquetas de los campos de formulario y los subtítulos
de los videos.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lxml import html as lxml_html


@dataclass
class HallazgoA11y:
    archivo: str
    linea: int
    regla: str
    severidad: str  # "error" o "aviso"
    mensaje: str

    def to_dict(self) -> dict:
        return {"archivo": self.archivo, "linea": self.linea, "regla": self.regla,
                "severidad": self.severidad, "mensaje": self.mensaje}


ALT_GENERICOS = {"imagen", "image", "img", "figura", "figure", "foto", "photo", "captura", "screenshot",
                 "grafico", "gráfico", "diagrama", "icono", "ícono", "logo", "picture"}
ENLACES_GENERICOS = {"aqui", "aquí", "aca", "acá", "click", "clic", "click aqui", "click aquí", "clic aqui",
                     "clic aquí", "hace click aqui", "hacé click aquí", "hacé clic aquí", "este enlace", "enlace",
                     "link", "este link", "ver mas", "ver más", "mas", "más", "leer mas", "leer más", "here",
                     "click here", "more", "read more"}
COLORES_CON_NOMBRE = {"black": "#000000", "white": "#ffffff", "red": "#ff0000", "green": "#008000",
                      "blue": "#0000ff", "yellow": "#ffff00", "gray": "#808080", "grey": "#808080",
                      "silver": "#c0c0c0", "orange": "#ffa500", "lightgray": "#d3d3d3", "lightgrey": "#d3d3d3",
                      "lime": "#00ff00", "cyan": "#00ffff", "aqua": "#00ffff", "pink": "#ffc0cb"}
SIN_ETIQUETA = {"hidden", "submit", "button", "reset", "image"}


def _normalizar(texto: str) -> str:
    return re.sub(r"[\s\W_]+", " ", texto.lower()).strip()


def color_a_rgb(valor: str) -> Optional[Tuple[int, int, int]]:
    v = COLORES_CON_NOMBRE.get(valor.strip().lower(), valor.strip().lower())
    if re.fullmatch(r"#[0-9a-f]{3}", v):
        return tuple(int(c * 2, 16) for c in v[1:])  # type: ignore[return-value]
    if re.fullmatch(r"#[0-9a-f]{6}", v):
        return tuple(int(v[i:i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]
    m = re.fullmatch(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*[\d.]+\s*)?\)", v)
    return tuple(min(255, int(x)) for x in m.groups()) if m else None  # type: ignore[return-value]


def contraste(primero: Tuple[int, int, int], segundo: Tuple[int, int, int]) -> float:
    """Relación de contraste WCAG 2.1 entre dos colores (1 a 21)."""
    def luminancia(rgb: Tuple[int, int, int]) -> float:
        c = [(x / 255) / 12.92 if x / 255 <= 0.03928 else ((x / 255 + 0.055) / 1.055) ** 2.4 for x in rgb]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

    claro, oscuro = sorted((luminancia(primero), luminancia(segundo)), reverse=True)
    return (claro + 0.05) / (oscuro + 0.05)


def _texto(elemento) -> str:
    return " ".join(elemento.text_content().split())


def auditar_html(contenido: str, archivo: str = "") -> List[HallazgoA11y]:
    """Hallazgos de accesibilidad de una página HTML."""
    hallazgos: List[HallazgoA11y] = []
    try:
        documento = lxml_html.document_fromstring(contenido)
    except Exception:  # noqa: BLE001 — una página vacía o rota no tiene nada que revisar
        return hallazgos

    def anotar(elemento, regla: str, severidad: str, mensaje: str) -> None:
        hallazgos.append(HallazgoA11y(archivo, getattr(elemento, "sourceline", 0) or 0, regla, severidad, mensaje))

    raiz = documento.getroottree().getroot()
    if not (raiz.get("lang") or "").strip():
        anotar(raiz, "idioma", "error", "<html> no declara el idioma (lang=\"es\"): un lector de pantalla lo "
                                        "leería con la pronunciación de otro idioma.")
    titulo = documento.find(".//title")
    if titulo is None or not _texto(titulo):
        anotar(raiz, "titulo-pagina", "error", "La página no tiene <title>: es lo primero que anuncia un lector "
                                               "de pantalla y lo que se ve en la pestaña.")

    for img in documento.iter("img"):
        alt = img.get("alt")
        origen = img.get("src", "<img>")
        if alt is None and img.get("role") not in ("presentation", "none"):
            anotar(img, "alt-faltante", "error", f"La imagen {origen} no tiene atributo alt (si es decorativa, "
                                                 "alt=\"\").")
        elif alt and (_normalizar(alt) in ALT_GENERICOS or alt.strip() == origen.rsplit("/", 1)[-1]):
            anotar(img, "alt-generico", "aviso", f"El texto alternativo «{alt.strip()}» de {origen} no describe "
                                                 "la imagen.")

    nivel_anterior, titulos = 0, 0
    for encabezado in documento.iter("h1", "h2", "h3", "h4", "h5", "h6"):
        nivel = int(encabezado.tag[1])
        if nivel == 1:
            titulos += 1
            if titulos > 1:
                anotar(encabezado, "titulo-repetido", "aviso", "La página tiene más de un <h1>.")
        if nivel_anterior and nivel > nivel_anterior + 1:
            anotar(encabezado, "encabezado-salto", "error",
                   f"El encabezado salta de <h{nivel_anterior}> a <h{nivel}>: usá <h{nivel_anterior + 1}>.")
        nivel_anterior = nivel

    for enlace in documento.iter("a"):
        if enlace.get("href") is None:
            continue
        texto = _texto(enlace) or enlace.get("aria-label", "") or enlace.get("title", "")
        if not texto:
            texto = " ".join(i.get("alt", "") for i in enlace.iter("img")).strip()
        if not texto:
            anotar(enlace, "enlace-sin-texto", "error", f"El enlace a {enlace.get('href')} no tiene texto ni "
                                                        "aria-label: un lector de pantalla no puede nombrarlo.")
        elif _normalizar(texto) in {_normalizar(e) for e in ENLACES_GENERICOS}:
            anotar(enlace, "enlace-generico", "error", f"El enlace «{texto}» no dice adónde lleva.")

    for iframe in documento.iter("iframe"):
        if not (iframe.get("title") or "").strip():
            anotar(iframe, "iframe-sin-titulo", "error", "El <iframe> no tiene title.")

    for video in documento.iter("video"):
        if not any(t.get("kind") in ("captions", "subtitles") for t in video.iter("track")):
            anotar(video, "video-sin-subtitulos", "aviso", "El <video> no tiene <track kind=\"captions\">: sin "
                                                           "subtítulos, no lo puede seguir quien no oye el audio.")

    etiquetados = {lbl.get("for") for lbl in documento.iter("label") if lbl.get("for")}
    for campo in documento.iter("input", "select", "textarea"):
        if campo.tag == "input" and (campo.get("type") or "text").lower() in SIN_ETIQUETA:
            continue
        envuelto = any(a.tag == "label" for a in campo.iterancestors())
        if not (envuelto or campo.get("id") in etiquetados or campo.get("aria-label")
                or campo.get("aria-labelledby") or campo.get("title")):
            anotar(campo, "campo-sin-etiqueta", "error",
                   f"El campo <{campo.tag}{' name=' + repr(campo.get('name')) if campo.get('name') else ''}> no "
                   "tiene <label>: un lector de pantalla no puede decir qué se pide.")

    for elemento in documento.iter():
        estilo = elemento.get("style") if isinstance(elemento.tag, str) else None
        if not estilo:
            continue
        declaraciones: Dict[str, str] = {}
        for parte in estilo.split(";"):
            if ":" in parte:
                nombre, valor = parte.split(":", 1)
                declaraciones[nombre.strip().lower()] = valor.strip()
        texto_rgb = color_a_rgb(declaraciones.get("color", ""))
        fondo_declarado = declaraciones.get("background-color") or declaraciones.get("background")
        fondo_rgb = color_a_rgb(fondo_declarado) if fondo_declarado else None
        if texto_rgb is None or (fondo_declarado and fondo_rgb is None):
            continue
        relacion = contraste(texto_rgb, fondo_rgb or (255, 255, 255))
        if relacion < 4.5:
            fondo = fondo_declarado or "fondo blanco"
            anotar(elemento, "contraste", "error" if fondo_rgb else "aviso",
                   f"El texto ({declaraciones['color']}) sobre {fondo} tiene contraste {relacion:.1f}:1; WCAG pide "
                   "al menos 4.5:1.")
    return hallazgos


def auditar_paquete(raiz: Path) -> List[HallazgoA11y]:
    """Hallazgos de accesibilidad de todas las páginas HTML de un paquete descomprimido."""
    hallazgos: List[HallazgoA11y] = []
    for pagina in sorted(list(raiz.rglob("*.html")) + list(raiz.rglob("*.htm"))):
        contenido = pagina.read_text(encoding="utf-8", errors="replace")
        hallazgos.extend(auditar_html(contenido, pagina.relative_to(raiz).as_posix()))
    return hallazgos
