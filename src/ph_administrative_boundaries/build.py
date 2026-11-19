import hashlib
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ph_administrative_boundaries.ingest import sha256_file
from ph_administrative_boundaries.types import (
    Artifact,
    Cache,
    Converter,
    DataIngestor,
    DatasetSpec,
    ExternalTool,
    Manifest,
    OutputSpec,
    Transformer,
)

_OUTPUT_EXTENSIONS = {"pmtiles": ".pmtiles", "mlt": ".mlt"}


class ToolError(RuntimeError):
    pass


class EncoderError(RuntimeError):
    pass


@dataclass
class SubprocessTool:
    name: str
    executable: str | None = None

    def run(self, args: list[str]) -> None:
        result = self._invoke([*args])
        if result.returncode != 0:
            raise ToolError(
                f"{self.name} exited with {result.returncode}: {result.stderr.strip()}"
            )

    def version(self) -> str:
        result = self._invoke(["--version"])
        return (result.stdout or result.stderr).strip()

    def _invoke(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                [self.executable or self.name, *args],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise ToolError(f"{self.name} is not installed or not on PATH") from exc


@dataclass
class MapshaperTransformer:
    mapshaper: ExternalTool
    workspace: Path

    def output_path(self, spec: DatasetSpec) -> Path:
        return self.workspace / "normalized" / f"{spec.name}.geojson"

    def transform(self, raw: Artifact, spec: DatasetSpec) -> Artifact:
        out = self.output_path(spec)
        out.parent.mkdir(parents=True, exist_ok=True)
        geometry = spec.geometry

        args = ["-i", str(raw.path)]
        if geometry.clean:
            args.append("-clean")
        if geometry.simplify_percent < 100:
            args += [
                "-simplify",
                "visvalingam",
                f"percentage={geometry.simplify_percent:g}%",
                "keep-shapes",
            ]
        args += ["-o", str(out)]
        if geometry.precision:
            args.append(f"precision={geometry.precision:g}")

        self.mapshaper.run(args)
        return Artifact(path=out, sha256=sha256_file(out))


@dataclass
class EncoderConverter:
    encoders: dict[str, ExternalTool]
    output_dir: Path

    def output_path(self, src: Artifact, out: OutputSpec) -> Path:
        extension = _OUTPUT_EXTENSIONS.get(out.format, f".{out.format}")
        return self.output_dir / f"{out.layer}{extension}"

    def convert(self, src: Artifact, out: OutputSpec) -> Artifact:
        encoder = self.encoders.get(out.format)
        if encoder is None:
            raise EncoderError(f"no encoder registered for format '{out.format}'")
        dest = self.output_path(src, out)
        dest.parent.mkdir(parents=True, exist_ok=True)
        encoder.run(self._args(src, out, dest))
        return Artifact(path=dest, sha256=sha256_file(dest))

    @staticmethod
    def _args(src: Artifact, out: OutputSpec, dest: Path) -> list[str]:
        if out.format != "pmtiles":
            raise EncoderError(f"unsupported output format '{out.format}'")
        args = [
            "-o",
            str(dest),
            "-f",
            "-P",
            "--simplify-only-low-zooms",
            "--detect-shared-borders",
            "--drop-densest-as-needed",
            f"--layer={out.layer}",
        ]
        if out.min_zoom:
            args.append(f"-Z{out.min_zoom}")
        args.append(f"-z{out.max_zoom}" if out.max_zoom else "-zg")
        return [*args, str(src.path)]


@dataclass
class JsonCache:
    path: Path
    entries: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.path.exists():
            self.entries = json.loads(self.path.read_text() or "{}")

    def is_fresh(self, key: str, out: Path) -> bool:
        recorded = self.entries.get(key)
        if recorded is None or not out.exists():
            return False
        return recorded == sha256_file(out)

    def record(self, key: str, out: Path) -> None:
        self.entries[key] = sha256_file(out)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        partial = self.path.with_suffix(".tmp")
        partial.write_text(json.dumps(self.entries, indent=2, sort_keys=True))
        partial.replace(self.path)


def fingerprint(*parts: object) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class BuildPipeline:
    manifest: Manifest
    ingestor: DataIngestor
    transformer: Transformer
    converter: Converter
    cache: Cache
    keep_intermediates: bool = False

    def ingest(self, name: str) -> Artifact:
        return self.ingestor.ingest(self.manifest.get(name))

    def build(self, name: str) -> list[Artifact]:
        spec = self.manifest.get(name)
        raw = self.ingestor.ingest(spec)

        normalized_key = fingerprint("normalized", spec.name, asdict(spec.geometry))
        normalized_path = self.transformer.output_path(spec)
        if self.cache.is_fresh(normalized_key, normalized_path):
            normalized = Artifact(normalized_path, sha256_file(normalized_path))
        else:
            normalized = self.transformer.transform(raw, spec)
            self.cache.record(normalized_key, normalized.path)

        artifacts: list[Artifact] = []
        for output in spec.outputs:
            dist_key = fingerprint("dist", normalized.sha256, asdict(output))
            dist_path = self.converter.output_path(normalized, output)
            if self.cache.is_fresh(dist_key, dist_path):
                artifacts.append(Artifact(dist_path, sha256_file(dist_path)))
            else:
                artifact = self.converter.convert(normalized, output)
                self.cache.record(dist_key, artifact.path)
                artifacts.append(artifact)

        if not self.keep_intermediates:
            shutil.rmtree(normalized.path.parent, ignore_errors=True)
        return artifacts
