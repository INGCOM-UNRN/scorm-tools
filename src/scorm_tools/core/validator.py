"""Validación de paquetes SCORM: esquema XSD + reglas de estructura + reglas Moodle."""

from __future__ import annotations

import tempfile
import zipfile
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

from lxml import etree

_CP_NS_12 = "http://www.imsproject.org/xsd/imscp_rootv1p1p2"
_CP_NS_2004 = "http://www.imsglobal.org/xsd/imscp_v1p1"
_ADLCP_NS_12 = "http://www.adlnet.org/xsd/adlcp_rootv1p2"
_ADLCP_NS_2004 = "http://www.adlnet.org/xsd/adlcp_v1p3"

_SCHEMA_ENTRYPOINT = {
    "1.2": ("scorm_tools.schemas.scorm12", "manifest.xsd"),
    "2004": ("scorm_tools.schemas.scorm2004", "manifest.xsd"),
}


@dataclass
class ValidationReport:
    """Resultado de validar un paquete SCORM."""

    manifest_path: str | None = None
    scorm_version: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_path": self.manifest_path,
            "scorm_version": self.scorm_version,
            "ok": self.ok,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }

    def to_json(self, indent: int = 2) -> str:
        import json
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        lines = ["### Informe de Validación SCORM", ""]
        if self.manifest_path:
            lines.append(f"- **Manifiesto:** `{self.manifest_path}`")
        if self.scorm_version:
            lines.append(f"- **Versión SCORM:** `{self.scorm_version}`")
        status_str = "✓ **Válido**" if self.ok else f"❌ **Inválido ({len(self.errors)} error(es))**"
        lines.append(f"- **Estado:** {status_str}")
        lines.append("")

        if self.warnings:
            lines.append("#### Advertencias")
            for w in self.warnings:
                lines.append(f"- ⚠️ {w}")
            lines.append("")

        if self.errors:
            lines.append("#### Errores")
            for e in self.errors:
                lines.append(f"- ❌ {e}")
            lines.append("")

        return "\n".join(lines)


def _detect_version(root: etree._Element) -> str:
    tag_ns = etree.QName(root).namespace
    if tag_ns == _CP_NS_12:
        return "1.2"
    if tag_ns == _CP_NS_2004:
        return "2004"
    raise ValueError(f"Namespace de manifiesto no reconocido: {tag_ns}")


def _load_schema(version: str) -> etree.XMLSchema:
    package, filename = _SCHEMA_ENTRYPOINT[version]
    pkg_root = resources.files(package)
    with resources.as_file(pkg_root) as pkg_dir:
        # Copiamos todo el directorio a un tmpdir real para garantizar que las
        # referencias relativas (schemaLocation) entre los .xsd se resuelvan
        # correctamente incluso si el paquete está instalado como .whl/zip.
        with tempfile.TemporaryDirectory(prefix="scorm-schema-") as tmp:
            tmp_dir = Path(tmp)
            for item in pkg_dir.iterdir():
                if item.suffix == ".xsd":
                    (tmp_dir / item.name).write_bytes(item.read_bytes())
            doc = etree.parse(str(tmp_dir / filename))
            return etree.XMLSchema(doc)


def _find_manifest(root_dir: Path, report: ValidationReport) -> Path | None:
    direct = root_dir / "imsmanifest.xml"
    if direct.exists():
        return direct

    candidates = list(root_dir.rglob("imsmanifest.xml"))
    if not candidates:
        report.add_error("No se encontró 'imsmanifest.xml' en el paquete.")
        return None

    report.add_error(
        "'imsmanifest.xml' no está en la raíz del paquete "
        f"(encontrado en: {candidates[0].relative_to(root_dir)}). "
        "Moodle requiere que esté en la raíz del ZIP."
    )
    return candidates[0]


def _check_moodle_zip_layout(root_dir: Path, report: ValidationReport) -> None:
    top_level = [p for p in root_dir.iterdir()]
    only_one_dir = len(top_level) == 1 and top_level[0].is_dir()
    if only_one_dir and not (root_dir / "imsmanifest.xml").exists():
        report.add_warning(
            f"El ZIP contiene una única carpeta raíz ('{top_level[0].name}') "
            "envolviendo el contenido. Moodle espera 'imsmanifest.xml' en la "
            "raíz del ZIP, no dentro de una subcarpeta."
        )


def _local_name(tag: str) -> str:
    return etree.QName(tag).localname


def _validate_manifest_structure(
    tree: etree._ElementTree, package_root: Path, manifest_dir: Path, report: ValidationReport
) -> None:
    root = tree.getroot()

    resource_ids: set[str] = set()
    item_ids: set[str] = set()

    for resource in root.iter():
        if _local_name(resource.tag) != "resource":
            continue
        rid = resource.get("identifier")
        if not rid:
            report.add_error("Se encontró un <resource> sin atributo 'identifier'.")
            continue
        if rid in resource_ids:
            report.add_error(f"Identificador de resource duplicado: '{rid}'.")
        resource_ids.add(rid)

        href = resource.get("href")
        if href:
            _check_referenced_file(href, manifest_dir, report, context=f"resource '{rid}'")
        for f in resource:
            if _local_name(f.tag) == "file":
                fhref = f.get("href")
                if fhref:
                    _check_referenced_file(
                        fhref, manifest_dir, report, context=f"resource '{rid}'"
                    )

    for item in root.iter():
        if _local_name(item.tag) != "item":
            continue
        iid = item.get("identifier")
        if not iid:
            report.add_error("Se encontró un <item> sin atributo 'identifier'.")
            continue
        if iid in item_ids:
            report.add_error(f"Identificador de item duplicado: '{iid}'.")
        item_ids.add(iid)

        ref = item.get("identifierref")
        if ref and ref not in resource_ids:
            report.add_error(
                f"El item '{iid}' referencia el resource inexistente '{ref}'."
            )

        mastery = item.find(f"{{{_ADLCP_NS_12}}}masteryscore")
        if mastery is not None and mastery.text is not None:
            try:
                score = int(mastery.text.strip())
                if not (0 <= score <= 100):
                    report.add_error(
                        f"masteryscore de item '{iid}' fuera de rango 0-100: {score}"
                    )
            except ValueError:
                report.add_error(
                    f"masteryscore de item '{iid}' no es un entero válido: {mastery.text!r}"
                )

    for href_el in root.iter():
        if _local_name(href_el.tag) == "resource":
            href = href_el.get("href", "")
            if href.startswith("/") or "\\" in href or ":" in href:
                report.add_warning(
                    f"El href '{href}' del resource '{href_el.get('identifier')}' usa "
                    "una ruta absoluta o separadores no portables; use rutas relativas "
                    "con '/'."
                )


def _check_referenced_file(
    href: str, manifest_dir: Path, report: ValidationReport, context: str
) -> None:
    clean = href.split("?", 1)[0].split("#", 1)[0]
    target = (manifest_dir / clean).resolve()
    try:
        target.relative_to(manifest_dir.resolve())
    except ValueError:
        report.add_error(f"{context}: ruta fuera del paquete: '{href}'.")
        return
    if not target.exists():
        report.add_error(f"{context}: archivo referenciado no existe: '{href}'.")


def validate_package(path: Path) -> ValidationReport:
    """Valida un paquete SCORM (directorio o `.zip`) y devuelve un reporte."""
    report = ValidationReport()
    path = path.resolve()

    with tempfile.TemporaryDirectory(prefix="scorm-validate-") as tmp:
        tmp_dir = Path(tmp)
        if path.is_file() and path.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(path) as zf:
                    zf.extractall(tmp_dir)
            except (zipfile.BadZipFile, OSError) as exc:
                report.add_error(f"El archivo no es un archivo ZIP válido: {path} ({exc})")
                return report
            root_dir = tmp_dir
            _check_moodle_zip_layout(root_dir, report)
        elif path.is_dir():
            root_dir = path
        else:
            report.add_error(f"Ruta no válida (ni directorio ni .zip): {path}")
            return report

        manifest_path = _find_manifest(root_dir, report)
        if manifest_path is None:
            return report

        report.manifest_path = str(manifest_path.relative_to(root_dir))

        try:
            tree = etree.parse(str(manifest_path))
        except etree.XMLSyntaxError as exc:
            report.add_error(f"XML inválido en imsmanifest.xml: {exc}")
            return report

        try:
            version = _detect_version(tree.getroot())
        except ValueError as exc:
            report.add_error(str(exc))
            return report

        report.scorm_version = version

        schema = _load_schema(version)
        if not schema.validate(tree):
            for e in schema.error_log:
                report.add_error(f"XSD ({e.line}): {e.message}")

        _validate_manifest_structure(tree, root_dir, manifest_path.parent, report)

    return report
