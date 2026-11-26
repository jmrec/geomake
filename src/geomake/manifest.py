"""Load a manifest file into `DatasetSpec`s, validating every step."""

import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from geomake.schema import DatasetModel, ManifestModel, StepModel
from geomake.types import DatasetSpec, Step

PLACEHOLDER = re.compile(r"\{(\w+)\}")


class ManifestError(ValueError):
    pass


@dataclass
class YamlManifest:
    datasets: dict[str, DatasetSpec] = field(default_factory=dict)

    def load(self, path: Path) -> "YamlManifest":
        manifest_path = Path(path)
        config = yaml.safe_load(manifest_path.read_text()) or {}
        try:
            model = ManifestModel.model_validate(config)
        except ValidationError as exc:
            raise ManifestError(_describe(manifest_path, exc)) from None
        self.datasets = {
            name: _dataset(name, block, manifest_path.parent)
            for name, block in model.datasets.items()
        }
        _check_unique_outputs(self.datasets)
        return self

    def get(self, name: str) -> DatasetSpec:
        try:
            return self.datasets[name]
        except KeyError:
            known = ", ".join(sorted(self.datasets)) or "none"
            raise ManifestError(f"unknown dataset '{name}' (known: {known})") from None


def _describe(path: Path, exc: ValidationError) -> str:
    """One line (log renderers escape newlines), each problem with its key path."""
    problems = []
    for error in exc.errors():
        where = ".".join(str(part) for part in error["loc"]) or "<root>"
        problems.append(f"{where}: {error['msg'].removeprefix('Value error, ')}")
    return f"{path}: invalid manifest: " + "; ".join(problems)


def _dataset(name: str, block: DatasetModel, root: Path) -> DatasetSpec:
    sources = _sources(block.source, root)
    return DatasetSpec(
        name=name,
        attribution=block.attribution,
        sources=sources,
        steps=_steps(name, block.steps, sources),
    )


def _sources(block: str | dict[str, str], root: Path) -> dict[str, Path]:
    entries = {"source": block} if isinstance(block, str) else block
    return {key: _resolve_source(root, value) for key, value in entries.items()}


def _resolve_source(root: Path, source: str) -> Path:
    """Absolute paths are used as given; relative ones start at the manifest's folder."""
    declared = Path(source).expanduser()
    return declared if declared.is_absolute() else root / declared


def _steps(
    name: str, block: list[StepModel], sources: dict[str, Path]
) -> tuple[Step, ...]:
    readable = set(sources)  # names a step may read: sources, then earlier step ids
    ids: set[str] = set()
    written: dict[str, int] = {}  # intermediate file name -> step number
    steps: list[Step] = []
    for number, item in enumerate(block, start=1):
        run = item.run
        try:
            shlex.split(run)
        except ValueError as exc:
            raise ManifestError(
                f"dataset '{name}': step {number} is malformed: {exc}"
            ) from None

        refs = set(PLACEHOLDER.findall(run))
        if "out" not in refs:
            raise ManifestError(f"dataset '{name}': step {number} must use {{out}}")
        reads = refs - {"out"}
        if not reads:
            raise ManifestError(
                f"dataset '{name}': step {number} must read {{in}} or a named input"
            )
        for ref in sorted(reads):
            if ref == "in":
                if number == 1 and len(sources) > 1:
                    raise ManifestError(
                        f"dataset '{name}': step 1 uses {{in}} but the dataset has "
                        f"several sources; name one of: {', '.join(sorted(sources))}"
                    )
            elif ref not in readable:
                raise ManifestError(
                    f"dataset '{name}': step {number} uses unknown name '{{{ref}}}'"
                )

        step_id = item.id
        if step_id is not None:
            if step_id in sources:
                raise ManifestError(
                    f"dataset '{name}': step {number} 'id' must be a plain identifier "
                    f"that is not a source name ('{step_id}')"
                )
            if step_id in ids:
                raise ManifestError(
                    f"dataset '{name}': step id '{step_id}' is used twice"
                )

        out = item.out
        last = number == len(block)
        if not last:
            file_name = out or (
                f"{step_id}.geojson" if step_id else f"step{number}.geojson"
            )
            if file_name in written:
                raise ManifestError(
                    f"dataset '{name}': steps {written[file_name]} and {number} "
                    f"both write '{file_name}'"
                )
            written[file_name] = number

        steps.append(Step(run=run, out=out, id=step_id))
        if step_id is not None:
            ids.add(step_id)
            readable.add(step_id)
    return tuple(steps)


def _check_unique_outputs(datasets: dict[str, DatasetSpec]) -> None:
    owners: dict[str, str] = {}
    for spec in datasets.values():
        final = spec.steps[-1].out
        if final is None:
            raise ManifestError(f"dataset '{spec.name}' has no final output name")
        if final in owners:
            raise ManifestError(
                f"datasets '{owners[final]}' and '{spec.name}' both write '{final}'"
            )
        owners[final] = spec.name
