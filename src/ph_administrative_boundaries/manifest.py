from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ph_administrative_boundaries.types import (
    DatasetSpec,
    GeometrySpec,
    OutputSpec,
)

KEEP_ALL_POINTS = 100.0


class ManifestError(ValueError):
    pass


@dataclass
class YamlManifest:
    datasets: dict[str, DatasetSpec] = field(default_factory=dict)

    def load(self, path: Path) -> "YamlManifest":
        manifest_path = Path(path)
        config = yaml.safe_load(manifest_path.read_text()) or {}
        blocks = config.get("datasets") or {}
        if not isinstance(blocks, dict):
            raise ManifestError(f"{manifest_path}: 'datasets' must be a mapping")
        self.datasets = {
            name: _dataset(name, block, manifest_path.parent)
            for name, block in blocks.items()
        }
        return self

    def get(self, name: str) -> DatasetSpec:
        try:
            return self.datasets[name]
        except KeyError:
            known = ", ".join(sorted(self.datasets)) or "none"
            raise ManifestError(f"unknown dataset '{name}' (known: {known})") from None


def _dataset(name: str, block: Any, root: Path) -> DatasetSpec:
    if not isinstance(block, dict):
        raise ManifestError(f"dataset '{name}' must be a mapping")
    if "source" not in block:
        raise ManifestError(f"dataset '{name}' is missing 'source'")
    return DatasetSpec(
        name=name,
        attribution=str(block.get("attribution", "")),
        source=_resolve_source(root / "data", block["source"]),
        geometry=_geometry(name, block.get("geometry") or {}),
        outputs=_outputs(name, block.get("outputs") or {}),
    )


def _resolve_source(data_root: Path, source: str) -> Path:
    declared = Path(source)
    if declared.is_absolute():
        return declared
    # Sources are read from `<manifest dir>/data` unless the declared path already
    # resolves from the manifest directory (e.g. `data/raw/boundaries.geojson`).
    unscoped = data_root.parent / declared
    return unscoped if unscoped.exists() else data_root / declared


def _geometry(name: str, block: Any) -> GeometrySpec:
    if not isinstance(block, dict):
        raise ManifestError(f"dataset '{name}': 'geometry' must be a mapping")
    simplify = block.get("simplify")
    if isinstance(simplify, dict):
        percent = float(simplify.get("percent", KEEP_ALL_POINTS))
    elif simplify is None:
        percent = KEEP_ALL_POINTS
    else:
        percent = float(simplify)
    return GeometrySpec(
        clean=bool(block.get("clean", False)),
        precision=float(block.get("precision", 0.0)),
        simplify_percent=percent,
    )


def _outputs(name: str, block: Any) -> list[OutputSpec]:
    if not isinstance(block, dict):
        raise ManifestError(f"dataset '{name}': 'outputs' must be a mapping")
    if not block:
        raise ManifestError(f"dataset '{name}' declares no outputs")
    outputs = []
    for fmt, options in block.items():
        if not isinstance(options, dict):
            raise ManifestError(f"dataset '{name}': output '{fmt}' must be a mapping")
        outputs.append(
            OutputSpec(
                format=fmt,
                layer=str(options.get("layer", name)),
                min_zoom=int(options.get("minzoom", options.get("min_zoom", 0))),
                max_zoom=int(options.get("maxzoom", options.get("max_zoom", 0))),
            )
        )
    return outputs
