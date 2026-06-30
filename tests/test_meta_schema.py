import pytest
from pathlib import Path
from scanners.registry.schema import validate_meta, MetaSchema


def test_minimal_valid_meta_passes(tmp_path: Path):
    meta_path = tmp_path / "comment" / "meta.yaml"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(
        """
id: comment
name: Comment
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
"""
    )
    meta = validate_meta(meta_path)
    assert isinstance(meta, MetaSchema)
    assert meta.id == "comment"
    assert meta.session.model == "sonnet"


def test_inject_as_must_be_data(tmp_path: Path):
    bad_yaml = """
id: bad
name: Bad
version: 1.0.0
description: x
consumes:
  - dim: elf
    inject_as: prompt  # FORBIDDEN per Q29
    severity_filter: [high]
    token_budget: 1000
references: []
session:
  model: sonnet
  max_tokens: 16000
  references_token_budget: 12000
failure:
  max_retries: 2
  on_failure: skip
"""
    p = tmp_path / "bad" / "meta.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(bad_yaml)
    with pytest.raises(ValueError, match="inject_as must be 'data'"):
        validate_meta(p)


def test_missing_id_raises(tmp_path: Path):
    bad_yaml = """
name: x
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
"""
    p = tmp_path / "missing-id" / "meta.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(bad_yaml)
    with pytest.raises(ValueError, match=str(p)):
        validate_meta(p)


def test_top_level_non_mapping_raises_value_error_with_path(tmp_path: Path):
    p = tmp_path / "bad-shape" / "meta.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("- elf\n")

    with pytest.raises(ValueError, match=str(p)):
        validate_meta(p)


def test_malformed_consumes_shape_raises_value_error_with_path(tmp_path: Path):
    p = tmp_path / "bad-consumes" / "meta.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        """
id: bad
name: Bad
version: 1.0.0
description: x
consumes: [elf]
references: []
session:
  model: sonnet
  max_tokens: 16000
  references_token_budget: 12000
failure:
  max_retries: 2
  on_failure: skip
"""
    )

    with pytest.raises(ValueError, match=str(p)):
        validate_meta(p)
