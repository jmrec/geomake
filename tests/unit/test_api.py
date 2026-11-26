"""`geomake.build` and the CLI: several datasets, custom manifests, free-form paths."""

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

import geomake.api
from geomake import build
from geomake.cli import app
from geomake.manifest import ManifestError


class CopyRunner:
    """Stands in for the real tools: every step copies its inputs to the output."""

    def run(self, argv: list[str], *, stream: bool = False) -> str:
        if argv[1:] == ["--version"]:
            return "1.0"
        destination = Path(argv[argv.index("-o") + 1])
        inputs = [Path(arg) for arg in argv[1:] if Path(arg).is_file()]
        destination.write_text("".join(path.read_text() for path in inputs))
        return ""


@pytest.fixture(autouse=True)
def fake_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(geomake.api, "SubprocessRunner", CopyRunner)


def dataset(source: str, out: str) -> dict:
    return {"source": source, "steps": [{"run": "tool -i {in} -o {out}", "out": out}]}


def write_manifest(path: Path, datasets: dict) -> Path:
    path.write_text(yaml.safe_dump({"datasets": datasets}))
    return path


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    (tmp_path / "inputs").mkdir()
    (tmp_path / "inputs" / "a.json").write_text("a")
    (tmp_path / "inputs" / "b.json").write_text("b")
    write_manifest(
        tmp_path / "geomake.yml",
        {
            "alpha": dataset("inputs/a.json", "alpha.pmtiles"),
            "beta": dataset("inputs/b.json", "beta.pmtiles"),
        },
    )
    return tmp_path


def test_builds_several_datasets_in_order(project: Path) -> None:
    artifacts = build(
        "beta",
        "alpha",
        manifest=project / "geomake.yml",
        workspace=project / ".cache",
    )

    processed = project / "data" / "processed"
    assert [artifact.path for artifact in artifacts] == [
        processed / "beta.pmtiles",
        processed / "alpha.pmtiles",
    ]
    assert (processed / "alpha.pmtiles").read_text() == "a"
    assert (processed / "beta.pmtiles").read_text() == "b"


def test_a_misspelled_name_runs_nothing(project: Path) -> None:
    with pytest.raises(ManifestError, match="unknown dataset 'gamma'"):
        build(
            "alpha",
            "gamma",
            manifest=project / "geomake.yml",
            workspace=project / ".cache",
        )

    assert not (project / "data").exists()


def test_a_dataset_name_is_required(project: Path) -> None:
    with pytest.raises(ValueError, match="at least one dataset"):
        build(manifest=project / "geomake.yml", workspace=project / ".cache")


def test_manifest_can_have_any_file_name(project: Path) -> None:
    renamed = project / "boundaries.yaml"
    (project / "geomake.yml").rename(renamed)

    [artifact] = build("alpha", manifest=renamed, workspace=project / ".cache")

    assert artifact.path == project / "data" / "processed" / "alpha.pmtiles"


def test_sources_need_not_be_inside_data(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "far.json").write_text("far")
    (tmp_path / "near.json").write_text("near")
    manifest = write_manifest(
        tmp_path / "geomake.yml",
        {
            "relative": dataset("near.json", "relative.pmtiles"),
            "absolute": dataset(str(elsewhere / "far.json"), "absolute.pmtiles"),
        },
    )

    build("relative", "absolute", manifest=manifest, workspace=tmp_path / ".cache")

    processed = tmp_path / "data" / "processed"
    assert (processed / "relative.pmtiles").read_text() == "near"
    assert (processed / "absolute.pmtiles").read_text() == "far"


def test_output_dir_can_be_overridden(project: Path, tmp_path_factory) -> None:
    destination = tmp_path_factory.mktemp("tiles")

    [artifact] = build(
        "alpha",
        manifest=project / "geomake.yml",
        output_dir=destination,
        workspace=project / ".cache",
    )

    assert artifact.path == destination / "alpha.pmtiles"
    assert not (project / "data" / "processed").exists()


def test_cli_builds_several_datasets(project: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "build",
            "alpha",
            "beta",
            "--manifest",
            str(project / "geomake.yml"),
            "--workspace",
            str(project / ".cache"),
            "--quiet",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "alpha.pmtiles" in result.output
    assert "beta.pmtiles" in result.output


def test_cli_reports_a_misspelled_name_before_building(project: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "build",
            "alpha",
            "gamma",
            "-m",
            str(project / "geomake.yml"),
            "-w",
            str(project / ".cache"),
            "-q",
        ],
    )

    assert result.exit_code == 1
    assert not (project / "data").exists()
