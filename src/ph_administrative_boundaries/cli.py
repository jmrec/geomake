from pathlib import Path
from typing import Annotated

import typer

from ph_administrative_boundaries.build import (
    BuildPipeline,
    JsonCache,
    StepError,
    SubprocessRunner,
    ToolError,
)
from ph_administrative_boundaries.ingest import LocalDataIngestor
from ph_administrative_boundaries.manifest import ManifestError, YamlManifest

app = typer.Typer(help="Build vector tiles of Philippine administrative boundaries.")


@app.callback()
def main() -> None:
    """Build vector tiles of Philippine administrative boundaries."""


@app.command()
def build(
    name: Annotated[str, typer.Argument(help="Dataset name declared in the manifest")],
    manifest: Annotated[
        Path, typer.Option("--manifest", "-m", help="Path to the dataset manifest")
    ] = Path("manifest.yml"),
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "--output-dir",
            "-o",
            help="Where built artifacts go (default: <manifest dir>/data/processed)",
        ),
    ] = None,
    workspace: Annotated[
        Path,
        typer.Option(
            "--workspace",
            "-w",
            help="Scratch directory for intermediates and the build cache",
        ),
    ] = Path(".cache/build"),
    keep_intermediates: Annotated[
        bool,
        typer.Option(
            "--keep-intermediates",
            help="Keep the merged GeoJSON built from a glob source",
        ),
    ] = False,
) -> None:
    """Run every step declared for a dataset, in order."""
    workspace.mkdir(parents=True, exist_ok=True)
    destination = output_dir or manifest.parent / "data" / "processed"
    try:
        pipeline = BuildPipeline(
            manifest=YamlManifest().load(manifest),
            ingestor=LocalDataIngestor(workspace),
            runner=SubprocessRunner(),
            cache=JsonCache(workspace / "cache.json"),
            workspace=workspace,
            output_dir=destination,
            keep_intermediates=keep_intermediates,
        )
        artifacts = pipeline.build(name)
    except (ManifestError, ToolError, StepError, FileNotFoundError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    for artifact in artifacts:
        typer.echo(f"{artifact.path}  {artifact.sha256}")


if __name__ == "__main__":
    app()
