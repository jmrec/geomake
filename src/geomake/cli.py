from pathlib import Path
from typing import Annotated

import structlog
import typer

from geomake.api import build as api_build
from geomake.build import StepError, ToolError
from geomake.logs import LogFormat, configure_logging
from geomake.manifest import ManifestError

app = typer.Typer(
    help="Build geospatial datasets from a manifest of cached, ordered CLI steps."
)


@app.callback()
def main() -> None:
    """Build geospatial datasets from a manifest of cached, ordered CLI steps."""


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
    log_format: Annotated[
        LogFormat,
        typer.Option(
            "--log-format",
            help="console: readable lines; json: one JSON object per line",
        ),
    ] = LogFormat.console,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet", "-q", help="Show only the built artifacts, not the logs"
        ),
    ] = False,
) -> None:
    """Run every step declared for a dataset, in order."""
    configure_logging(log_format, quiet=quiet)
    try:
        artifacts = api_build(
            name,
            manifest,
            output_dir=output_dir,
            workspace=workspace,
            keep_intermediates=keep_intermediates,
            stream=not quiet,
        )
    except (ManifestError, ToolError, StepError, FileNotFoundError) as exc:
        structlog.get_logger().error("build_failed", dataset=name, error=str(exc))
        raise typer.Exit(1) from exc
    for artifact in artifacts:
        typer.echo(f"{artifact.path}  {artifact.sha256}")


if __name__ == "__main__":
    app()
