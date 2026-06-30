import pytest
from pathlib import Path
from scanners.registry.schema import validate_meta, MetaSchema


def test_minimal_valid_meta_passes():
    meta_path = Path("tests/_fixtures_meta/comment/meta.yaml")
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


def test_inject_as_must_be_data():
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
    p = Path("tests/_fixtures_meta/bad/meta.yaml")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(bad_yaml)
    with pytest.raises(ValueError, match="inject_as must be 'data'"):
        validate_meta(p)


def test_missing_id_raises():
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
    p = Path("tests/_fixtures_meta/missing-id/meta.yaml")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(bad_yaml)
    with pytest.raises(ValueError):
        validate_meta(p)
