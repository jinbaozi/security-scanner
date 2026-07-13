"""Shared compact argparse failure behavior for bundled scanner CLIs."""
from __future__ import annotations

import argparse
import re
import sys


class CompactArgumentParser(argparse.ArgumentParser):
    """Emit one machine-classifiable line for CLI contract violations."""

    def __init__(self, *args, status_name: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_name = status_name

    def error(self, message: str) -> None:
        detail = re.sub(r"\s+", "_", message.strip())[:240] or "invalid_arguments"
        print(
            f"{self.status_name} status=blocked reason=cli_contract_error detail={detail}",
            file=sys.stderr,
        )
        raise SystemExit(2)
