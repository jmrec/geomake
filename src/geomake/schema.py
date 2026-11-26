"""Shape of `manifest.yml`. Unknown keys and wrong types fail at load time."""

import re
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

NAME = re.compile(r"[A-Za-z_]\w*")
RESERVED = frozenset({"in", "out"})


def _check_identifier(value: str, what: str) -> str:
    if not NAME.fullmatch(value) or value in RESERVED:
        raise ValueError(
            f"{what} {value!r} must be a plain identifier, not 'in' or 'out'"
        )
    return value


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StepModel(_Strict):
    run: str
    out: str | None = None
    id: str | None = None

    @field_validator("run")
    @classmethod
    def _run_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("'run' must not be empty")
        return value.strip()

    @field_validator("out")
    @classmethod
    def _out_is_file_name(cls, value: str | None) -> str | None:
        if value is not None and (not value or "/" in value):
            raise ValueError("'out' must be a plain file name")
        return value

    @field_validator("id")
    @classmethod
    def _id_is_identifier(cls, value: str | None) -> str | None:
        return None if value is None else _check_identifier(value, "step id")


class DatasetModel(_Strict):
    attribution: str = ""
    source: str | dict[str, str] = Field(min_length=1)
    steps: list[StepModel] = Field(min_length=1)

    @field_validator("source")
    @classmethod
    def _source_names(cls, value: str | dict[str, str]) -> str | dict[str, str]:
        if isinstance(value, dict):
            for key, path in value.items():
                _check_identifier(key, "source name")
                if not path:
                    raise ValueError(f"source '{key}' must be a path")
        return value

    @model_validator(mode="after")
    def _last_step_sets_out(self) -> Self:
        if self.steps[-1].out is None:
            raise ValueError("the last step must set 'out' (the final file name)")
        return self


class ManifestModel(_Strict):
    datasets: dict[str, DatasetModel] = Field(default_factory=dict)
