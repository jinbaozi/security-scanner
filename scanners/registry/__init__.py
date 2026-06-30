"""Scanner registry: discovery + validation. See plan Task 1."""
from dataclasses import dataclass
from pathlib import Path

from scanners.registry.schema import MetaSchema, validate_meta


@dataclass
class Scanner:
    meta: MetaSchema
    prompt: str
    scanner_md_path: Path


def discover_scanners(root: Path = Path("scanners")) -> dict[str, Scanner]:
    """Discover all valid scanners under root/<dim>/{scanner.md,meta.yaml}."""
    if not root.exists():
        return {}

    scanners: dict[str, Scanner] = {}
    for dim_dir in sorted(root.iterdir()):
        if not dim_dir.is_dir():
            continue
        if dim_dir.name == "registry":
            continue

        scanner_md = dim_dir / "scanner.md"
        meta_yaml = dim_dir / "meta.yaml"
        has_scanner_md = scanner_md.exists()
        has_meta_yaml = meta_yaml.exists()
        if not has_scanner_md and not has_meta_yaml:
            continue
        if not has_scanner_md:
            raise ValueError(
                f"scanner.md missing in {dim_dir} (meta.yaml exists but no prompt)"
            )
        if not has_meta_yaml:
            raise ValueError(
                f"meta.yaml missing in {dim_dir} (scanner.md exists but no metadata)"
            )

        meta = validate_meta(meta_yaml)
        if meta.id in scanners:
            raise ValueError(f"duplicate scanner id {meta.id!r}")

        scanners[meta.id] = Scanner(
            meta=meta,
            prompt=scanner_md.read_text(),
            scanner_md_path=scanner_md,
        )

    return scanners
