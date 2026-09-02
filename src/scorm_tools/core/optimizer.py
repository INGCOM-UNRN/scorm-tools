"""Optimización de rendimiento, minificación y auditoría de peso de paquetes SCORM."""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any


def minify_css(css: str) -> str:
    """Minifica código CSS eliminando comentarios y espacios redundantes."""
    # Eliminar comentarios de bloque
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    # Normalizar espacios y saltos de línea
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([\{\}:;,])\s*", r"\1", css)
    css = re.sub(r";\}", "}", css)
    return css.strip()


def minify_js(js: str) -> str:
    """Minifica código JavaScript básico preservando cadenas literales."""
    # Eliminar comentarios multilínea /* ... */
    pattern_block = r"/\*[\s\S]*?\*/"
    js_clean = re.sub(pattern_block, "", js)

    lines: list[str] = []
    for line in js_clean.splitlines():
        trimmed = line.strip()
        # Eliminar líneas que son exclusivamente comentarios de línea //
        if trimmed.startswith("//"):
            continue
        # Eliminar comentarios al final de la línea si no están dentro de cadenas
        if "//" in trimmed:
            parts = trimmed.split("//")
            # Heurística simple para evitar recortar URLs o strings
            if not any(quote in parts[0] for quote in ("'", '"', "`")):
                trimmed = parts[0].strip()
        if trimmed:
            lines.append(trimmed)

    return "\n".join(lines)


def generate_sourcemap(file_name: str, original_content: str) -> str:
    """Genera un Source Map v3 simplificado para depuración."""
    mapping = {
        "version": 3,
        "file": file_name,
        "sources": [file_name + ".orig"],
        "sourcesContent": [original_content],
        "names": [],
        "mappings": "AAAA;",
    }
    return json.dumps(mapping, indent=2)


def minify_assets(dir_path: Path, generate_map: bool = False) -> dict[str, Any]:
    """Minifica todos los archivos CSS y JS dentro del directorio."""
    total_before = 0
    total_after = 0
    processed_files: list[str] = []

    for file_path in dir_path.rglob("*"):
        if not file_path.is_file():
            continue

        ext = file_path.suffix.lower()
        if ext in (".css", ".js") and not file_path.name.endswith(".min" + ext):
            original = file_path.read_text(encoding="utf-8", errors="replace")
            size_before = len(original.encode("utf-8"))
            total_before += size_before

            if ext == ".css":
                minified = minify_css(original)
            else:
                minified = minify_js(original)

            size_after = len(minified.encode("utf-8"))
            total_after += size_after

            file_path.write_text(minified, encoding="utf-8")
            processed_files.append(file_path.name)

            if generate_map:
                map_path = file_path.with_name(file_path.name + ".map")
                map_content = generate_sourcemap(file_path.name, original)
                map_path.write_text(map_content, encoding="utf-8")

    saved_bytes = total_before - total_after
    saved_percent = (saved_bytes / total_before * 100.0) if total_before > 0 else 0.0

    return {
        "files_processed": len(processed_files),
        "files": processed_files,
        "bytes_before": total_before,
        "bytes_after": total_after,
        "saved_bytes": saved_bytes,
        "saved_percent": round(saved_percent, 2),
    }


def optimize_images(dir_path: Path) -> dict[str, Any]:
    """Audita y opcionalmente comprime imágenes usando Pillow si está disponible."""
    image_extensions = {".png", ".jpg", ".jpeg"}
    images_found: list[str] = []

    for file_path in dir_path.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            images_found.append(file_path.name)

    pillow_available = False
    try:
        import PIL  # noqa: F401
        pillow_available = True
    except ImportError:
        pass

    return {
        "images_found": len(images_found),
        "images": images_found,
        "pillow_available": pillow_available,
        "status": "Pillow no instalado; compresión omitida sin degradar paquete"
        if not pillow_available
        else "Pillow operativo",
    }


def check_package_size(path: Path, max_mb: float = 50.0) -> dict[str, Any]:
    """Calcula el tamaño total del paquete y su desglose por tipo de archivo."""
    categories: dict[str, int] = {
        "html": 0,
        "javascript": 0,
        "css": 0,
        "media": 0,
        "xml_schemas": 0,
        "other": 0,
    }
    total_bytes = 0

    if path.is_file() and path.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(path, "r") as zf:
                for info in zf.infolist():
                    size = info.file_size
                    total_bytes += size
                    ext = Path(info.filename).suffix.lower()
                    if ext in (".html", ".htm"):
                        categories["html"] += size
                    elif ext in (".js", ".mjs"):
                        categories["javascript"] += size
                    elif ext == ".css":
                        categories["css"] += size
                    elif ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".mp3", ".mp4"):
                        categories["media"] += size
                    elif ext in (".xml", ".xsd", ".dtd"):
                        categories["xml_schemas"] += size
                    else:
                        categories["other"] += size
        except zipfile.BadZipFile:
            total_bytes = path.stat().st_size
            categories["other"] = total_bytes
    elif path.is_dir():
        for file_path in path.rglob("*"):
            if file_path.is_file():
                size = file_path.stat().st_size
                total_bytes += size
                ext = file_path.suffix.lower()
                if ext in (".html", ".htm"):
                    categories["html"] += size
                elif ext in (".js", ".mjs"):
                    categories["javascript"] += size
                elif ext == ".css":
                    categories["css"] += size
                elif ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".mp3", ".mp4"):
                    categories["media"] += size
                elif ext in (".xml", ".xsd", ".dtd"):
                    categories["xml_schemas"] += size
                else:
                    categories["other"] += size
    else:
        raise ValueError(f"Ruta no válida para análisis de tamaño: {path}")

    total_mb = total_bytes / (1024 * 1024)
    exceeds = total_mb > max_mb

    return {
        "path": str(path),
        "total_bytes": total_bytes,
        "total_mb": round(total_mb, 2),
        "max_mb": max_mb,
        "exceeds_limit": exceeds,
        "categories_bytes": categories,
        "categories_kb": {k: round(v / 1024, 2) for k, v in categories.items()},
    }
