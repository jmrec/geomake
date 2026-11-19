from pathlib import Path
from typing import Annotated

import typer

from ph_administrative_boundaries.build import (
    BuildPipeline,
    EncoderConverter,
    EncoderError,
    JsonCache,
    MapshaperTransformer,
    SubprocessTool,
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
        bool, typer.Option("--keep-intermediates", help="Keep normalized GeoJSON")
    ] = False,
) -> None:
    """Build every output declared for a dataset."""
    workspace.mkdir(parents=True, exist_ok=True)
    destination = output_dir or manifest.parent / "data" / "processed"
    try:
        pipeline = BuildPipeline(
            manifest=YamlManifest().load(manifest),
            ingestor=LocalDataIngestor(workspace),
            transformer=MapshaperTransformer(
                mapshaper=SubprocessTool("mapshaper"), workspace=workspace
            ),
            converter=EncoderConverter(
                encoders={"pmtiles": SubprocessTool("tippecanoe")},
                output_dir=destination,
            ),
            cache=JsonCache(workspace / "cache.json"),
            keep_intermediates=keep_intermediates,
        )
        artifacts = pipeline.build(name)
    except (ManifestError, ToolError, EncoderError, FileNotFoundError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    for artifact in artifacts:
        typer.echo(f"{artifact.path}  {artifact.sha256}")


if __name__ == "__main__":
    app()
