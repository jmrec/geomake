import hashlib
import json
from dataclasses import dataclass
from glob import glob, has_magic
from pathlib import Path
from typing import Any

from ph_administrative_boundaries.types import Artifact, DatasetSpec

_CHUNK_SIZE = 1 << 20


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class LocalDataIngestor:
    workspace: Path = Path(".cache/build")

    def ingest(self, spec: DatasetSpec) -> Artifact:
        pattern = str(spec.source)
        if has_magic(pattern):
            return self._ingest_many(spec, [Path(p) for p in glob(pattern)])
        if not spec.source.is_file():
            raise FileNotFoundError(
                f"dataset '{spec.name}' source is missing: {spec.source}"
            )
        return Artifact(path=spec.source, sha256=sha256_file(spec.source))

    def merged_path(self, spec: DatasetSpec) -> Path:
        return self.workspace / "raw" / f"{spec.name}.geojson"

    def _ingest_many(self, spec: DatasetSpec, sources: list[Path]) -> Artifact:
        if not sources:
            raise FileNotFoundError(
                f"dataset '{spec.name}' source matched no files: {spec.source}"
            )
        merged = self.merged_path(spec)
        merged.parent.mkdir(parents=True, exist_ok=True)
        merged.write_text(json.dumps(_combine(sorted(sources))))
        return Artifact(path=merged, sha256=sha256_file(merged))


def _combine(sources: list[Path]) -> dict[str, Any]:
    features: list[Any] = []
    for source in sources:
        features.extend(json.loads(source.read_text())["features"])
    return {"type": "FeatureCollection", "features": features}
