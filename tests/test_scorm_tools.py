from __future__ import annotations

from pathlib import Path

import pytest

from scorm_tools.descriptor import CourseDescriptorError, load_course
from scorm_tools.manifest import render_manifest
from scorm_tools.models import ScormVersion
from scorm_tools.packager import build_package
from scorm_tools.scaffold import scaffold_course
from scorm_tools.validator import validate_package


@pytest.mark.parametrize("version", [ScormVersion.SCORM_12, ScormVersion.SCORM_2004_4ED])
def test_scaffold_build_validate_roundtrip(tmp_path: Path, version: ScormVersion) -> None:
    course_dir = tmp_path / "curso"
    scaffold_course(course_dir, title="Curso de test", version=version)

    assert (course_dir / "scorm.yaml").exists()
    assert (course_dir / "index.html").exists()

    output_zip = tmp_path / "curso.zip"
    course = build_package(course_dir, output_zip)
    assert course.version == version
    assert output_zip.exists()

    report = validate_package(output_zip)
    assert report.ok, report.errors
    assert report.scorm_version in ("1.2", "2004")


def test_validate_detects_broken_resource_reference(tmp_path: Path) -> None:
    course_dir = tmp_path / "curso"
    scaffold_course(course_dir, title="Curso roto", version=ScormVersion.SCORM_2004_4ED)

    descriptor = course_dir / "scorm.yaml"
    descriptor.write_text(
        descriptor.read_text(encoding="utf-8").replace("resource: RES-1", "resource: NOPE"),
        encoding="utf-8",
    )

    output_zip = tmp_path / "curso.zip"
    build_package(course_dir, output_zip)

    report = validate_package(output_zip)
    assert not report.ok
    assert any("NOPE" in e for e in report.errors)


def test_validate_warns_on_nested_manifest(tmp_path: Path) -> None:
    course_dir = tmp_path / "curso"
    scaffold_course(course_dir, title="Curso anidado", version=ScormVersion.SCORM_2004_4ED)
    output_zip = tmp_path / "curso.zip"
    build_package(course_dir, output_zip)

    import zipfile

    nested_zip = tmp_path / "nested.zip"
    with zipfile.ZipFile(output_zip) as src, zipfile.ZipFile(nested_zip, "w") as dst:
        for name in src.namelist():
            dst.writestr(f"wrapper/{name}", src.read(name))

    report = validate_package(nested_zip)
    assert not report.ok
    assert any("raíz" in e for e in report.errors)
    assert any("carpeta raíz" in w for w in report.warnings)


def test_load_course_requires_identifier_and_title(tmp_path: Path) -> None:
    descriptor = tmp_path / "scorm.yaml"
    descriptor.write_text("title: Solo titulo\n", encoding="utf-8")
    with pytest.raises(CourseDescriptorError):
        load_course(descriptor)


def test_manifest_mastery_score_out_of_range_is_flagged(tmp_path: Path) -> None:
    course_dir = tmp_path / "curso"
    scaffold_course(course_dir, title="Curso mastery", version=ScormVersion.SCORM_12)
    descriptor = course_dir / "scorm.yaml"
    descriptor.write_text(
        descriptor.read_text(encoding="utf-8").replace("mastery_score: 80", "mastery_score: 150"),
        encoding="utf-8",
    )
    output_zip = tmp_path / "curso.zip"
    build_package(course_dir, output_zip)

    report = validate_package(output_zip)
    assert not report.ok
    assert any("fuera de rango" in e for e in report.errors)


def test_render_manifest_contains_resource_and_item(tmp_path: Path) -> None:
    course_dir = tmp_path / "curso"
    scaffold_course(course_dir, title="Curso render", version=ScormVersion.SCORM_2004_4ED)
    course = load_course(course_dir / "scorm.yaml")
    xml = render_manifest(course)
    assert "RES-1" in xml
    assert "ITEM-1" in xml
    assert "imsss:primaryObjective" in xml
