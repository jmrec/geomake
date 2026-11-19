"""Integration tests for the build flow described by `types.py`."""

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from ph_administrative_boundaries.build import (
    BuildPipeline,
    EncoderConverter,
    EncoderError,
    JsonCache,
    MapshaperTransformer,
    SubprocessTool,
)
from ph_administrative_boundaries.cli import app
from ph_administrative_boundaries.ingest import LocalDataIngestor, sha256_file
from ph_administrative_boundaries.manifest import ManifestError, YamlManifest
from ph_administrative_boundaries.types import (
    Artifact,
    DatasetSpec,
    ExternalTool,
    GeometrySpec,
    OutputSpec,
)

SOURCE = Path(__file__).resolve().parent / "fixtures" / "country" / "country.0.1.json"

requires_tools = pytest.mark.skipif(
    shutil.which("mapshaper") is None or shutil.which("tippecanoe") is None,
    reason="mapshaper and tippecanoe must be installed",
)

MANIFEST = {
    "datasets": {
        "country": {
            "source": "raw/source.geojson",
            "geometry": {
                "clean": True,
                "precision": 0.00001,
                "simplify": {
                    "method": "visvalingam",
                    "percent": 10,
                    "keep_shapes": True,
                },
            },
            "outputs": {
                "pmtiles": {"layer": "country", "minzoom": 4, "maxzoom": 14},
            },
        }
    }
}


class CountingTool:
    """Delegates to a real external tool while recording every invocation."""

    def __init__(self, tool: ExternalTool) -> None:
        self.name = tool.name
        self.calls: list[list[str]] = []
        self._tool = tool

    def run(self, args: list[str]) -> None:
        self.calls.append([*args])
        self._tool.run(args)

    def version(self) -> str:
        return self._tool.version()


@dataclass
class Harness:
    root: Path
    mapshaper: CountingTool
    tippecanoe: CountingTool

    @property
    def workspace(self) -> Path:
        return self.root / ".cache" / "build"

    @property
    def output_dir(self) -> Path:
        return self.root / "data" / "processed"

    def pipeline(self, manifest: Path | None = None, **options: bool) -> BuildPipeline:
        return BuildPipeline(
            manifest=YamlManifest().load(manifest or self.root / "manifest.yml"),
            ingestor=LocalDataIngestor(self.workspace),
            transformer=MapshaperTransformer(self.mapshaper, self.workspace),
            converter=EncoderConverter({"pmtiles": self.tippecanoe}, self.output_dir),
            cache=JsonCache(self.workspace / "cache.json"),
            **options,
        )


@pytest.fixture(scope="module")
def source_slice(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if not SOURCE.is_file():
        pytest.skip(f"missing source data: {SOURCE}")
    collection = json.loads(SOURCE.read_text())
    collection["features"] = collection["features"][:2]
    path = tmp_path_factory.mktemp("slice") / "source.geojson"
    path.write_text(json.dumps(collection))
    return path


@pytest.fixture()
def project(tmp_path: Path, source_slice: Path) -> Path:
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    shutil.copy(source_slice, raw / "source.geojson")
    (tmp_path / "manifest.yml").write_text(yaml.safe_dump(MANIFEST, sort_keys=False))
    return tmp_path


@pytest.fixture()
def harness(project: Path) -> Harness:
    return Harness(
        root=project,
        mapshaper=CountingTool(SubprocessTool("mapshaper")),
        tippecanoe=CountingTool(SubprocessTool("tippecanoe")),
    )


def test_manifest_maps_yaml_onto_types(project: Path) -> None:
    spec = YamlManifest().load(project / "manifest.yml").get("country")

    assert isinstance(spec, DatasetSpec)
    assert spec.source == project / "data" / "raw" / "source.geojson"
    assert spec.geometry == GeometrySpec(
        clean=True, precision=0.00001, simplify_percent=10.0
    )
    assert spec.outputs == [
        OutputSpec(format="pmtiles", layer="country", min_zoom=4, max_zoom=14)
    ]


def test_unknown_dataset_is_reported(project: Path) -> None:
    manifest = YamlManifest().load(project / "manifest.yml")

    with pytest.raises(ManifestError, match="unknown dataset 'provinces'"):
        manifest.get("provinces")


def test_ingest_hashes_the_declared_source(project: Path) -> None:
    spec = YamlManifest().load(project / "manifest.yml").get("country")

    artifact = LocalDataIngestor().ingest(spec)

    assert artifact.path == spec.source
    assert artifact.sha256 == sha256_file(spec.source)


def test_unregistered_format_is_reported(project: Path) -> None:
    converter = EncoderConverter({}, project / "build")
    source = Artifact(project / "source.geojson", "0" * 64)

    with pytest.raises(EncoderError, match="mlt"):
        converter.convert(source, OutputSpec("mlt", "country", 0, 0))


@requires_tools
def test_build_writes_pmtiles_artifact(harness: Harness) -> None:
    artifacts = harness.pipeline().build("country")

    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact.path == harness.output_dir / "country.pmtiles"
    assert artifact.path.read_bytes()[:7] == b"PMTiles"
    assert artifact.sha256 == sha256_file(artifact.path)
    assert harness.mapshaper.calls[0][0] == "-i"
    zoom_args = [
        arg
        for arg in harness.tippecanoe.calls[0]
        if arg.startswith(("-Z", "-z", "--layer"))
    ]
    assert zoom_args == ["--layer=country", "-Z4", "-z14"]


@requires_tools
def test_build_drops_normalized_intermediates(harness: Harness) -> None:
    harness.pipeline().build("country")

    assert not (harness.workspace / "normalized").exists()
    assert (harness.output_dir / "country.pmtiles").is_file()


@requires_tools
def test_keep_intermediates_preserves_normalized(harness: Harness) -> None:
    harness.pipeline(keep_intermediates=True).build("country")

    assert (harness.workspace / "normalized" / "country.geojson").is_file()


@requires_tools
def test_rebuild_reuses_converted_artifacts(harness: Harness) -> None:
    first = harness.pipeline().build("country")
    second = harness.pipeline().build("country")

    assert [artifact.sha256 for artifact in second] == [
        artifact.sha256 for artifact in first
    ]
    assert len(harness.tippecanoe.calls) == 1
    assert len(harness.mapshaper.calls) == 2


@requires_tools
def test_geometry_change_invalidates_converted_artifacts(harness: Harness) -> None:
    first = harness.pipeline().build("country")

    config = yaml.safe_load((harness.root / "manifest.yml").read_text())
    config["datasets"]["country"]["geometry"]["precision"] = 0.001
    changed = harness.root / "changed.yml"
    changed.write_text(yaml.safe_dump(config))

    second = harness.pipeline(changed).build("country")

    assert len(harness.tippecanoe.calls) == 2
    assert second[0].sha256 != first[0].sha256


def test_cli_reports_unknown_dataset(project: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["build", "provinces", "--manifest", str(project / "manifest.yml")],
    )

    assert result.exit_code == 1
    assert "unknown dataset 'provinces'" in result.output


@requires_tools
def test_cli_build_writes_artifacts_to_data_processed(project: Path) -> None:
    workspace = project / ".cache" / "build"

    result = CliRunner().invoke(
        app,
        [
            "build",
            "country",
            "--manifest",
            str(project / "manifest.yml"),
            "--workspace",
            str(workspace),
        ],
    )

    assert result.exit_code == 0, result.output
    assert (project / "data" / "processed" / "country.pmtiles").is_file()
    assert not (workspace / "dist").exists()
    assert "data/processed/country.pmtiles" in result.output


@requires_tools
def test_cli_output_dir_override(project: Path) -> None:
    destination = project / "tiles"

    result = CliRunner().invoke(
        app,
        [
            "build",
            "country",
            "--manifest",
            str(project / "manifest.yml"),
            "--workspace",
            str(project / ".cache" / "build"),
            "--output-dir",
            str(destination),
        ],
    )

    assert result.exit_code == 0, result.output
    assert (destination / "country.pmtiles").is_file()
