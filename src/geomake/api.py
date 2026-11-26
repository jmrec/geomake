"""One-call entry point: build datasets from a manifest with sensible defaults."""

from pathlib import Path

from geomake.build import BuildPipeline, JsonCache, SubprocessRunner
from geomake.ingest import LocalDataIngestor
from geomake.manifest import YamlManifest
from geomake.types import Artifact


def build(
    *names: str,
    manifest: str | Path = "manifest.yml",
    output_dir: str | Path | None = None,
    workspace: str | Path = ".cache/build",
    keep_intermediates: bool = False,
    stream: bool = False,
) -> list[Artifact]:
    """Run every step of each named dataset, in order, and return the built artifacts.

    Reads ``manifest.yml`` from the current folder unless ``manifest`` names another
    file. Relative source paths start at the manifest's folder. Output goes to
    ``<manifest folder>/data/processed`` unless ``output_dir`` is given.

    Every name is checked before anything runs. The first failure stops the build;
    datasets finished by then stay cached, so a rerun skips them.
    """
    if not names:
        raise ValueError("name at least one dataset to build")
    manifest_path = Path(manifest)
    loaded = YamlManifest().load(manifest_path)
    for name in names:
        loaded.get(name)
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    pipeline = BuildPipeline(
        manifest=loaded,
        ingestor=LocalDataIngestor(workspace),
        runner=SubprocessRunner(),
        cache=JsonCache(workspace / "cache.json"),
        workspace=workspace,
        output_dir=Path(output_dir or manifest_path.parent / "data" / "processed"),
        keep_intermediates=keep_intermediates,
        stream=stream,
    )
    return [artifact for name in names for artifact in pipeline.build(name)]
