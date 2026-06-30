"""meta.yaml schema validation. See plan Task 1."""
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ValidationError


Severity = Literal["critical", "high", "medium", "low", "info"]


class ConsumeSpec(BaseModel):
    dim: str
    inject_as: Literal["data"]
    severity_filter: list[Severity]
    token_budget: int


class ReferenceSpec(BaseModel):
    path: str
    scope: Literal["shared", "local"]


class SessionSpec(BaseModel):
    model: str = "sonnet"
    max_tokens: int = 16000
    references_token_budget: int = 12000


class FailureSpec(BaseModel):
    max_retries: int = 2
    on_failure: Literal["skip", "fail_fast"] = "skip"


class MetaSchema(BaseModel):
    id: str
    name: str
    version: str
    description: str
    consumes: list[ConsumeSpec]
    references: list[ReferenceSpec]
    session: SessionSpec
    failure: FailureSpec


def validate_meta(meta_path: Path) -> MetaSchema:
    """Parse and validate meta.yaml. Raises ValueError on schema violation."""
    if not meta_path.exists():
        raise ValueError(f"meta.yaml not found: {meta_path}")

    try:
        data = yaml.safe_load(meta_path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML in {meta_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"meta.yaml must be a mapping in {meta_path}")

    consumes = data.get("consumes", [])
    if consumes is None:
        consumes = []
    if not isinstance(consumes, list):
        raise ValueError(f"consumes must be a list in {meta_path}")

    for consume in consumes:
        if not isinstance(consume, dict):
            raise ValueError(f"consume entries must be mappings in {meta_path}")
        if consume.get("inject_as") != "data":
            raise ValueError(
                f"inject_as must be 'data' (Q29), got {consume.get('inject_as')!r} "
                f"in {meta_path}"
            )

    try:
        return MetaSchema(**data)
    except ValidationError as exc:
        raise ValueError(f"invalid meta.yaml schema in {meta_path}: {exc}") from exc
