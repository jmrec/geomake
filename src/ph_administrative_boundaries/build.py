"""Run each dataset's steps in order, skipping any step whose inputs are unchanged."""

import hashlib
import json
import re
import shlex
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ph_administrative_boundaries.ingest import LocalDataIngestor, sha256_file
from ph_administrative_boundaries.manifest import PLACEHOLDER, YamlManifest
from ph_administrative_boundaries.types import Artifact, DatasetSpec, Step


class ToolError(RuntimeError):
    pass


class StepError(RuntimeError):
    pass


class Runner(Protocol):
    def run(self, argv: list[str]) -> str: ...


class SubprocessRunner:
    def run(self, argv: list[str]) -> str:
        try:
            result = subprocess.run(argv, check=False, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise ToolError(f"{argv[0]} is not installed or not on PATH") from exc
        if result.returncode != 0:
            raise ToolError(
                f"{argv[0]} exited with {result.returncode}: {result.stderr.strip()}"
            )
        return result.stdout or result.stderr


def render(run: str, paths: Mapping[str, Path]) -> list[str]:
    """Split a step into argv, replacing each `{name}` token by token.

    `paths` maps every name the step uses, including "out", to a path.
    Splitting first keeps a path with spaces in one argument.
    """

    def substitute(match: re.Match[str]) -> str:
        return str(paths[match.group(1)])

    return [PLACEHOLDER.sub(substitute, token) for token in shlex.split(run)]


def fingerprint(*parts: object) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


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


@dataclass
class BuildPipeline:
    manifest: YamlManifest
    ingestor: LocalDataIngestor
    runner: Runner
    cache: JsonCache
    workspace: Path
    output_dir: Path
    keep_intermediates: bool = False

    def build(self, name: str) -> list[Artifact]:
        spec = self.manifest.get(name)
        sources = self.ingestor.ingest(spec)
        final = self._run_steps(spec, sources)
        # Merged glob copies are scratch space; declared files are never removed.
        if not self.keep_intermediates:
            for key, artifact in sources.items():
                if artifact.path != spec.sources[key]:
                    artifact.path.unlink(missing_ok=True)
        return [final]

    def _run_steps(self, spec: DatasetSpec, sources: dict[str, Artifact]) -> Artifact:
        names: dict[str, Artifact] = dict(sources)
        # `{in}` is the sole source for the first step, then the previous output.
        # Validation rejects `{in}` on the first step when there are several sources.
        current = next(iter(sources.values()))
        for index, step in enumerate(spec.steps, start=1):
            reads = set(PLACEHOLDER.findall(step.run)) - {"out"}
            inputs: dict[str, Artifact] = {
                name: names[name] for name in reads if name != "in"
            }
            if "in" in reads:
                inputs["in"] = current
            current = self._run_step(spec, index, step, inputs)
            if step.id is not None:
                names[step.id] = current
        return current

    def _run_step(
        self,
        spec: DatasetSpec,
        index: int,
        step: Step,
        inputs: dict[str, Artifact],
    ) -> Artifact:
        dest = self._destination(spec, index, step)
        key = fingerprint(
            "step",
            spec.name,
            index,
            step.run,
            step.out,
            sorted((name, art.sha256) for name, art in inputs.items()),
            self._tool_version(step),
        )
        if not self.cache.is_fresh(key, dest):
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.unlink(missing_ok=True)
            paths = {name: art.path for name, art in inputs.items()}
            paths["out"] = dest
            self.runner.run(render(step.run, paths))
            if not dest.is_file():
                raise StepError(f"'{spec.name}' step {index} wrote no file to {dest}")
            self.cache.record(key, dest)
        return Artifact(dest, sha256_file(dest))

    def _destination(self, spec: DatasetSpec, index: int, step: Step) -> Path:
        if index == len(spec.steps):
            return self.output_dir / (step.out or "")
        default = f"{step.id}.geojson" if step.id else f"step{index}.geojson"
        return self.workspace / "steps" / spec.name / (step.out or default)

    def _tool_version(self, step: Step) -> str:
        """Best-effort version of the step's tool, part of its cache key.

        Tools that have no `--version` still work; they just don't invalidate
        the cache when upgraded.
        """
        tool = shlex.split(step.run)[0]
        try:
            return self.runner.run([tool, "--version"]).strip()
        except ToolError:
            return "unknown"
