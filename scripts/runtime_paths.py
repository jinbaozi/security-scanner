"""Runtime path guards for the immutable skill tree."""
from __future__ import annotations

from pathlib import Path


class SkillRootWriteForbidden(ValueError):
    """Raised when a runtime output resolves inside the protected skill tree."""


def is_within(path: Path, root: Path) -> bool:
    resolved_path = path.expanduser().resolve(strict=False)
    resolved_root = root.expanduser().resolve(strict=False)
    return resolved_path == resolved_root or resolved_root in resolved_path.parents


def require_outside_skill_root(path: Path, skill_root: Path) -> Path:
    resolved = path.expanduser().resolve(strict=False)
    if is_within(resolved, skill_root):
        raise SkillRootWriteForbidden(str(resolved))
    return resolved
