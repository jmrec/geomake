from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Self


@dataclass
class GeometrySpec:
    clean: bool
    precision: float
    simplify_percent: float


@dataclass
class OutputSpec:
    format: str
    layer: str
    min_zoom: int
    max_zoom: int


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    attribution: str
    source: Path
    geometry: GeometrySpec
    outputs: list[OutputSpec]


@dataclass(frozen=True)
class Artifact:
    path: Path
    sha256: str


class Pipeline(Protocol):
    def build(self, name: str) -> list[Artifact]: ...

    def ingest(self, name: str) -> Artifact: ...


class Cache(Protocol):
    def is_fresh(self, key: str, out: Path) -> bool: ...

    def record(self, key: str, out: Path) -> None: ...


class ExternalTool(Protocol):
    name: str

    def run(self, args: list[str]) -> None: ...

    def version(self) -> str: ...


class DataIngestor(Protocol):
    def ingest(self, spec: DatasetSpec) -> Artifact: ...


class Transformer(Protocol):
    mapshaper: ExternalTool

    def output_path(self, spec: DatasetSpec) -> Path: ...

    def transform(self, raw: Artifact, spec: DatasetSpec) -> Artifact: ...


class Converter(Protocol):
    encoders: dict[str, ExternalTool]

    def output_path(self, src: Artifact, out: OutputSpec) -> Path: ...

    def convert(self, src: Artifact, out: OutputSpec) -> Artifact: ...


class Manifest(Protocol):
    def load(self, path: Path) -> Self: ...

    def get(self, name: str) -> DatasetSpec: ...
