import json
import subprocess
import sys
from pathlib import Path

from scripts.build_report_values import DIMENSION_PREFIX, build_values


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_report_values.py"
RENDER = ROOT / "scripts" / "render_template.py"
AUDIT = ROOT / "scripts" / "audit_render.py"
TEMPLATE = ROOT / "templates" / "report-comprehensive.md"
DIMENSION_TEMPLATE = ROOT / "templates" / "report-安全编译.md"


def test_report_status_is_pass_when_coverage_is_complete_and_findings_are_pass_only():
    values = build_values(
        "[[REPORT_STATUS]]",
        "fixture",
        "/tmp/fixture",
        "2026-07-13",
        {},
        [{"status": "PASS", "severity": "info", "dimension": "elf", "verdict": "confirmed"}],
        {},
        {dimension: "ready" for dimension in DIMENSION_PREFIX},
    )

    assert values["REPORT_STATUS"] == "PASS"


def test_builder_produces_complete_comprehensive_values_for_empty_scan(tmp_path):
    values = tmp_path / "values.json"
    report = tmp_path / "report.md"
    audit = tmp_path / "audit.json"
    findings = tmp_path / "findings.json"
    scan_plan = tmp_path / "scan-plan.json"
    findings.write_text("[]", encoding="utf-8")
    scan_plan.write_text(json.dumps({"total_files": 3, "scan_files": 3}), encoding="utf-8")

    built = subprocess.run(
        [
            sys.executable, str(BUILD),
            "--template", str(TEMPLATE),
            "--component-name", "fixture",
            "--target-path", str(tmp_path),
            "--scan-date", "2026-07-13",
            "--scan-plan", str(scan_plan),
            "--findings", str(findings),
            "--output", str(values),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert built.returncode == 0
    assert built.stderr == ""
    assert built.stdout.count("\n") == 1
    built_values = json.loads(values.read_text(encoding="utf-8"))
    assert built_values["REPORT_STATUS"] == "UNVERIFIED"
    assert "未验证" in built_values["SECTION_DIMENSION_STATUS"]

    rendered = subprocess.run(
        [sys.executable, str(RENDER), "--template", str(TEMPLATE), "--values", str(values), "--output", str(report), "--strict"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert rendered.returncode == 0

    audited = subprocess.run(
        [sys.executable, str(AUDIT), "--rendered", str(report), "--template", str(TEMPLATE), "--output", str(audit)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert audited.returncode == 0
    assert json.loads(audit.read_text(encoding="utf-8"))["residual_count"] == 0


def test_builder_requires_coverage_status_for_every_dimension_before_pass(tmp_path):
    values = tmp_path / "values.json"
    findings = tmp_path / "findings.json"
    statuses = tmp_path / "dimension-statuses.json"
    findings.write_text("[]", encoding="utf-8")
    statuses.write_text(json.dumps({"elf": "ready"}), encoding="utf-8")

    built = subprocess.run(
        [
            sys.executable, str(BUILD),
            "--template", str(TEMPLATE),
            "--component-name", "fixture",
            "--target-path", str(tmp_path),
            "--scan-date", "2026-07-13",
            "--findings", str(findings),
            "--dimension-statuses", str(statuses),
            "--output", str(values),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert built.returncode == 0
    payload = json.loads(values.read_text(encoding="utf-8"))
    assert payload["REPORT_STATUS"] == "UNVERIFIED"
    assert "口令硬编码：未验证" in payload["SECTION_DIMENSION_STATUS"]


def test_builder_uses_dimension_coverage_and_never_turns_blocked_scan_into_pass(tmp_path):
    values = tmp_path / "values.json"
    findings = tmp_path / "findings.json"
    statuses = tmp_path / "dimension-statuses.json"
    findings.write_text("[]", encoding="utf-8")
    statuses.write_text(
        json.dumps({"elf": {"status": "blocked", "reason": "invocation_error"}, "url": "ready"}),
        encoding="utf-8",
    )

    built = subprocess.run(
        [
            sys.executable, str(BUILD),
            "--template", str(TEMPLATE),
            "--component-name", "fixture",
            "--target-path", str(tmp_path),
            "--scan-date", "2026-07-13",
            "--findings", str(findings),
            "--dimension-statuses", str(statuses),
            "--output", str(values),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert built.returncode == 0
    payload = json.loads(values.read_text(encoding="utf-8"))
    assert payload["REPORT_STATUS"] == "BLOCKED"
    assert "安全编译：已阻断" in payload["SECTION_DIMENSION_STATUS"]
    assert "公网地址：已执行" in payload["SECTION_DIMENSION_STATUS"]


def _run_builder(tmp_path, template, *, scan_plan, findings, statuses, materialization=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    values = tmp_path / f"{template.stem}-values.json"
    scan_plan_path = tmp_path / "scan-plan.json"
    findings_path = tmp_path / "findings.json"
    statuses_path = tmp_path / "statuses.json"
    scan_plan_path.write_text(json.dumps(scan_plan), encoding="utf-8")
    findings_path.write_text(json.dumps(findings), encoding="utf-8")
    statuses_path.write_text(json.dumps(statuses), encoding="utf-8")
    argv = [
        sys.executable, str(BUILD), "--template", str(template),
        "--component-name", "widget", "--target-path", "/scan/widget",
        "--scan-date", "2026-07-13", "--scan-plan", str(scan_plan_path),
        "--findings", str(findings_path), "--dimension-statuses", str(statuses_path),
        "--output", str(values),
    ]
    if materialization is not None:
        materialization_path = tmp_path / "materialization.json"
        materialization_path.write_text(json.dumps(materialization), encoding="utf-8")
        argv.extend(["--materialization", str(materialization_path)])
    result = subprocess.run(argv, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    return json.loads(values.read_text(encoding="utf-8")), values.read_bytes()


def test_builder_uses_real_materialization_and_scan_plan_counts(tmp_path):
    statuses = {dimension: "ready" for dimension in DIMENSION_PREFIX}
    payload, _ = _run_builder(
        tmp_path,
        TEMPLATE,
        scan_plan={
            "total_files": 12,
            "scan_files": 10,
            "timestamp": "2026-07-13T08:00:00Z",
            "file_lists": {
                "elf": {"count": 2}, "config": {"count": 3},
                "excluded": {"count": 2},
            },
            "source_shards": [{"file_count": 4}, {"file_count": 3}],
        },
        findings=[],
        statuses=statuses,
        materialization={
            "input_kind": "srpm", "status": "ready",
            "source_roots": [{"path": "/work/widget-1.0", "origin": "source_prepped"}],
            "binary_roots": [], "srpm_spec_files": ["/work/widget.spec"],
            "applied_patches": ["fix-one.patch"], "builddep_status": "not_required",
            "errors": [],
        },
    )

    assert payload["ELF_COUNT"] == 2
    assert payload["CONFIG_COUNT"] == 3
    assert payload["EXCLUDED_FILES"] == 2
    assert payload["SOURCE_COUNT"] == 7
    section = payload["SECTION_MATERIALIZATION"]
    assert "widget.spec" in section
    assert "fix-one.patch" in section
    assert "gcc" not in section.lower()
    assert "640" not in section


def test_dimension_report_does_not_claim_pass_for_blocked_string_status(tmp_path):
    payload, _ = _run_builder(
        tmp_path,
        DIMENSION_TEMPLATE,
        scan_plan={"total_files": 1, "scan_files": 1},
        findings=[],
        statuses={"elf": "blocked"},
    )

    assert payload["DIM_KEY"] == "elf"
    assert "已阻断" in payload["DEGRADATION_NOTE"]
    assert "覆盖完整性：PASS" not in payload["SECTION_AUDIT"]
    assert "未验证" in payload["SECTION_AUDIT"] or "阻断" in payload["SECTION_AUDIT"]
    assert "未发现问题" not in payload["SECTION_DETAIL"]


def test_redline_coverage_requires_exact_clause_binding(tmp_path):
    statuses = {dimension: "ready" for dimension in DIMENSION_PREFIX}
    payload, _ = _run_builder(
        tmp_path,
        TEMPLATE,
        scan_plan={"total_files": 1, "scan_files": 1},
        findings=[{
            "id": "NETWORK-001", "dimension": "network", "file": "/scan/widget/a.conf",
            "line": 1, "check_item": "other_network_issue", "status": "WARN",
            "severity": "medium", "confidence": "high", "verdict": "suspected",
            "verdict_reasoning": "测试", "detail": "无关网络问题", "suggestion": "复核",
            "evidence": "sample", "redline_clause": None, "rl_ids": [],
        }],
        statuses=statuses,
    )

    row = next(line for line in payload["TABLE_REDLINE_COVERAGE"].splitlines() if line.startswith("| 1.1.1 |"))
    assert "| no finding |" in row
    assert "NETWORK-001" not in row


def test_redline_coverage_lists_only_valid_exact_binding_ids(tmp_path):
    statuses = {dimension: "ready" for dimension in DIMENSION_PREFIX}
    payload, _ = _run_builder(
        tmp_path,
        TEMPLATE,
        scan_plan={"total_files": 1, "scan_files": 1},
        findings=[{
            "id": "NETWORK-240", "dimension": "network", "file": "/scan/widget/a.conf",
            "line": 1, "check_item": "port_inventory", "status": "WARN",
            "severity": "medium", "confidence": "high", "verdict": "suspected",
            "verdict_reasoning": "测试", "detail": "端口需复核", "suggestion": "复核",
            "evidence": "sample", "redline_clause": "1.1.1", "rl_ids": ["RL-240"],
        }],
        statuses=statuses,
    )

    row = next(line for line in payload["TABLE_REDLINE_COVERAGE"].splitlines() if line.startswith("| 1.1.1 |"))
    assert "| covered |" in row
    assert "NETWORK-240" in row


def test_builder_is_byte_deterministic_for_identical_inputs(tmp_path):
    statuses = {dimension: "ready" for dimension in DIMENSION_PREFIX}
    first, first_bytes = _run_builder(
        tmp_path / "first", DIMENSION_TEMPLATE,
        scan_plan={"timestamp": "2026-07-13T08:00:00Z"}, findings=[], statuses=statuses,
    )
    second, second_bytes = _run_builder(
        tmp_path / "second", DIMENSION_TEMPLATE,
        scan_plan={"timestamp": "2026-07-13T08:00:00Z"}, findings=[], statuses=statuses,
    )
    assert first["TIMESTAMP"] == "2026-07-13T08:00:00Z"
    assert first_bytes == second_bytes
