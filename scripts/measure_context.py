"""Estimate Pi context risk from artifact metadata without reading contents."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

TOKENS_MEDIUM = 30_000
TOKENS_HIGH = 60_000
TOKENS_CRITICAL = 100_000


def measure(phase: str, paths: list[Path]) -> dict[str, Any]:
    inputs: list[dict[str, Any]] = []
    warnings: list[str] = []
    total_bytes = 0
    for path in paths:
        resolved = path.expanduser().resolve()
        if not resolved.is_file():
            if "input_not_found" not in warnings:
                warnings.append("input_not_found")
            inputs.append({"path": str(resolved), "exists": False, "bytes": 0})
            continue
        size = resolved.stat().st_size
        total_bytes += size
        inputs.append({"path": str(resolved), "exists": True, "bytes": size})

    estimated_tokens = (total_bytes + 2) // 3
    if estimated_tokens >= TOKENS_CRITICAL:
        risk = "critical"
    elif estimated_tokens >= TOKENS_HIGH:
        risk = "high"
    elif estimated_tokens >= TOKENS_MEDIUM or warnings:
        risk = "medium"
    else:
        risk = "low"

    recommendations: list[str] = []
    if risk in {"medium", "high", "critical"}:
        recommendations.append("read compact summaries instead of full artifacts")
    if risk in {"high", "critical"}:
        recommendations.append("split the next phase into file-backed batches")
    if risk == "critical":
        recommendations.append("stop model injection and emit a partial checkpoint")

    return {
        "phase": phase,
        "risk_level": risk,
        "estimated_tokens": estimated_tokens,
        "total_input_bytes": total_bytes,
        "safe_thresholds": {
            "medium_tokens": TOKENS_MEDIUM,
            "high_tokens": TOKENS_HIGH,
            "critical_tokens": TOKENS_CRITICAL,
        },
        "inputs": inputs,
        "warnings": warnings,
        "recommendations": recommendations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Estimate context risk from file sizes.")
    parser.add_argument("--phase", required=True)
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    report = measure(args.phase, args.inputs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"context-check phase={args.phase} risk={report['risk_level']} "
        f"tokens={report['estimated_tokens']} inputs={len(report['inputs'])} "
        f"output={args.output}"
    )
    return {"low": 0, "medium": 2, "high": 2, "critical": 3}[
        report["risk_level"]
    ]


if __name__ == "__main__":
    raise SystemExit(main())
