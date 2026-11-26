"""One-call entry point: build a dataset from a manifest with sensible defaults."""

from pathlib import Path

from geomake.build import (
    BuildPipeline,
    JsonCache,
    SubprocessRunner,
)
from geomake.ingest import LocalDataIngestor
from geomake.manifest import YamlManifest
from geomake.types import Artifact


def build(
    name: str,
    manifest: str | Path = "manifest.yml",
    *,
    output_dir: str | Path | None = None,
    workspace: str | Path = ".cache/build",
    keep_intermediates: bool = False,
    stream: bool = False,
) -> list[Artifact]:
    """Run every step declared for dataset ``name`` and return the built artifacts.

    Reads ``manifest.yml`` from the current folder unless ``manifest`` is given.
    Output goes to ``<manifest dir>/data/processed`` unless ``output_dir`` is given.
    """
    manifest_path = Path(manifest)
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    pipeline = BuildPipeline(
        manifest=YamlManifest().load(manifest_path),
        ingestor=LocalDataIngestor(workspace),
        runner=SubprocessRunner(),
        cache=JsonCache(workspace / "cache.json"),
        workspace=workspace,
        output_dir=Path(output_dir or manifest_path.parent / "data" / "processed"),
        keep_intermediates=keep_intermediates,
        stream=stream,
    )
    return pipeline.build(name)
