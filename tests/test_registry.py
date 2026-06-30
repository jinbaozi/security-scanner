import pytest
from pathlib import Path
from scanners.registry import discover_scanners


def test_discover_finds_valid_scanners(tmp_path: Path):
    # Set up minimal scanner directory structure
    scanners_dir = tmp_path / "scanners"
    registry_dir = scanners_dir / "registry"
    registry_dir.mkdir(parents=True)
    (scanners_dir / "comment").mkdir()
    (scanners_dir / "comment" / "scanner.md").write_text("# Comment scanner prompt")
    (scanners_dir / "comment" / "meta.yaml").write_text("""
id: comment
name: 注释扫描
version: 1.0.0
description: 注释中的未公开接口
consumes: []
references: []
session:
  model: sonnet
  max_tokens: 16000
  references_token_budget: 12000
failure:
  max_retries: 2
  on_failure: skip
""")
    scanners = discover_scanners(scanners_dir)
    assert "comment" in scanners
    assert scanners["comment"].meta.id == "comment"
    assert "Comment scanner prompt" in scanners["comment"].prompt


def test_discover_skips_registry_dir(tmp_path: Path):
    scanners_dir = tmp_path / "scanners"
    (scanners_dir / "registry").mkdir(parents=True)
    scanners = discover_scanners(scanners_dir)
    assert scanners == {}


def test_discover_duplicate_id_raises(tmp_path: Path):
    scanners_dir = tmp_path / "scanners"
    for name in ("a", "b"):
        d = scanners_dir / name
        d.mkdir(parents=True)
        (d / "scanner.md").write_text("x")
        (d / "meta.yaml").write_text(f"""
id: duplicate
name: {name}
version: 1.0.0
description: x
consumes: []
references: []
session:
  model: sonnet
  max_tokens: 16000
  references_token_budget: 12000
failure:
  max_retries: 2
  on_failure: skip
""")
    with pytest.raises(ValueError, match="duplicate"):
        discover_scanners(scanners_dir)


def test_scanner_md_missing_raises(tmp_path: Path):
    scanners_dir = tmp_path / "scanners"
    d = scanners_dir / "orphan"
    d.mkdir(parents=True)
    (d / "meta.yaml").write_text("""
id: orphan
name: orphan
version: 1.0.0
description: x
consumes: []
references: []
session:
  model: sonnet
  max_tokens: 16000
  references_token_budget: 12000
failure:
  max_retries: 2
  on_failure: skip
""")
    with pytest.raises(ValueError, match="scanner.md"):
        discover_scanners(scanners_dir)
