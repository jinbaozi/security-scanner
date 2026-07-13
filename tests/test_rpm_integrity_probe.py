import json
from pathlib import Path

from scripts.rpm_integrity_probe import CommandResult, classify_rpm_check, main, probe_rpms


def _rpm(tmp_path: Path, name: str = "package.rpm") -> Path:
    path = tmp_path / name
    path.write_bytes(b"rpm fixture")
    return path


def test_classifier_covers_verified_unsigned_and_failure_states():
    command = ["rpm", "--checksig", "package.rpm"]
    cases = [
        (CommandResult(command, 0, "package.rpm: digests signatures OK RSA/SHA256, key ID 1234", ""), "verified"),
        (CommandResult(command, 0, "package.rpm: digests OK", ""), "unsigned"),
        (CommandResult(command, 1, "package.rpm: digests SIGNATURES NOT OK", ""), "bad_signature"),
        (CommandResult(command, 1, "package.rpm: DIGESTS NOT OK", ""), "bad_digest"),
        (CommandResult(command, 1, "package.rpm: RSA/SHA256, key ID 1234: NOKEY", ""), "missing_key"),
        (CommandResult(command, 127, "", "rpm: command not found"), "tool_missing"),
        (CommandResult(command, 3, "unexpected output", ""), "unknown_failure"),
    ]

    for result, expected in cases:
        assert classify_rpm_check(result) == expected


def test_probe_keeps_nonzero_signature_failure_as_ready_evidence_not_pass(tmp_path):
    package = _rpm(tmp_path)

    def runner(command, **kwargs):
        return CommandResult(command, 1, f"{package}: digests SIGNATURES NOT OK", "")

    payload = probe_rpms([package], runner=runner)

    assert payload["status"] == "ready"
    assert payload["coverage_complete"] is True
    assert payload["results"][0]["verification_status"] == "bad_signature"
    assert payload["results"][0]["status"] == "ready"
    assert payload["tool_invocations"][0]["exit_code"] == 1
    assert payload["tool_invocations"][0]["locale"] == "C"


def test_probe_marks_unknown_output_blocked(tmp_path):
    package = _rpm(tmp_path)

    def runner(command, **kwargs):
        return CommandResult(command, 2, "unrecognized localized output", "")

    payload = probe_rpms([package], runner=runner)

    assert payload["status"] == "blocked"
    assert payload["results"][0]["verification_status"] == "unknown_failure"


def test_cli_writes_atomic_json_and_one_summary_line(tmp_path, capsys):
    package = _rpm(tmp_path)
    output = tmp_path / "reports" / "rpm-integrity.json"

    def runner(command, **kwargs):
        return CommandResult(command, 0, f"{package}: digests OK", "")

    exit_code = main(
        ["--rpm", str(package), "--output-json", str(output)],
        runner=runner,
    )

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "rpm_integrity_probe"
    assert payload["results"][0]["verification_status"] == "unsigned"
    assert len(capsys.readouterr().out.splitlines()) == 1
    assert not output.with_suffix(".json.tmp").exists()
