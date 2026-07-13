import json
from pathlib import Path

from scripts.elf_hardening_probe import CommandResult, ElfHardeningProbe, main


def _elf_file(tmp_path: Path, name: str = "app") -> Path:
    path = tmp_path / name
    path.write_bytes(b"\x7fELF test binary\n")
    return path


def _help_ok(command):
    return CommandResult(command, 0, "checksec help\n", "")


def _readelf_file_runner(command):
    if command[:2] == ["readelf", "-l"]:
        return CommandResult(command, 0, "GNU_STACK      0x000000  RW\nGNU_RELRO\n", "")
    if command[:2] == ["readelf", "-d"]:
        return CommandResult(command, 0, "0x000000000000001e (FLAGS) BIND_NOW\n", "")
    if command[:2] == ["readelf", "-h"]:
        return CommandResult(command, 0, "  Type: DYN (Position-Independent Executable file)\n", "")
    if command[:2] == ["readelf", "-s"]:
        return CommandResult(command, 0, "__stack_chk_fail\n__printf_chk@\n", "")
    if command[0] == "file":
        return CommandResult(command, 0, f"{command[-1]}: ELF 64-bit LSB executable, stripped\n", "")
    raise AssertionError(f"unexpected command: {command!r}")


def test_checksec_format_json_is_preferred(tmp_path):
    elf = _elf_file(tmp_path)
    calls = []

    def runner(command, **kwargs):
        calls.append(tuple(command))
        if command[:2] == ["checksec", "--help"]:
            return _help_ok(command)
        if command[0] == "checksec" and "--format=json" in command:
            return CommandResult(command, 0, '{"relro":"Full RELRO","nx":"NX enabled"}', "")
        raise AssertionError(f"unexpected command: {command!r}")

    result = ElfHardeningProbe(runner=runner).probe([elf])

    assert result["status"] == "ready"
    assert result["checksec_state"] == "available"
    assert result["selected_mode"] == "format_json"
    assert result["fallback_used"] is False
    assert result["results"][0]["source"] == "checksec"
    assert result["results"][0]["parser"] == "json"
    assert any("--format=json" in command for command in calls)
    assert not any("--output=json" in command for command in calls)


def test_checksec_output_json_is_used_when_format_json_is_unsupported(tmp_path):
    elf = _elf_file(tmp_path)
    calls = []

    def runner(command, **kwargs):
        calls.append(tuple(command))
        if command[:2] == ["checksec", "--help"]:
            return _help_ok(command)
        if command[0] == "checksec" and "--format=json" in command:
            return CommandResult(command, 1, "", "usage: checksec: unknown option --format")
        if command[0] == "checksec" and "--output=json" in command:
            return CommandResult(command, 0, '{"relro":"Full RELRO","nx":"NX enabled"}', "")
        raise AssertionError(f"unexpected command: {command!r}")

    result = ElfHardeningProbe(runner=runner).probe([elf])

    assert result["status"] == "ready"
    assert result["selected_mode"] == "output_json"
    assert result["results"][0]["source"] == "checksec"
    assert not any(command[0] == "readelf" for command in calls)


def test_unparseable_json_modes_switch_to_checksec_text_not_readelf(tmp_path):
    elf = _elf_file(tmp_path)
    calls = []

    def runner(command, **kwargs):
        calls.append(tuple(command))
        if command[:2] == ["checksec", "--help"]:
            return _help_ok(command)
        if command[0] == "checksec" and ("--format=json" in command or "--output=json" in command):
            return CommandResult(command, 0, "this is not json", "")
        if command[0] == "checksec":
            return CommandResult(
                command,
                0,
                (
                    "RELRO           STACK CANARY      NX            PIE             RPATH      "
                    "RUNPATH      Symbols         FORTIFY  Fortified  Fortifiable  FILE\n"
                    f"Full RELRO      Canary found      NX enabled    PIE enabled     No RPATH   "
                    f"No RUNPATH   No Symbols      Yes      3          5            {elf}\n"
                ),
                "",
            )
        raise AssertionError(f"unexpected command: {command!r}")

    result = ElfHardeningProbe(runner=runner).probe([elf])

    assert result["status"] == "ready"
    assert result["selected_mode"] == "text"
    assert result["results"][0]["source"] == "checksec"
    assert result["results"][0]["parser"] == "text"
    assert result["results"][0]["checks"]["nx"] == "NX enabled"
    assert not any(command[0] == "readelf" for command in calls)


def test_checksec_usage_errors_block_instead_of_readelf_fallback(tmp_path):
    elf = _elf_file(tmp_path)
    calls = []

    def runner(command, **kwargs):
        calls.append(tuple(command))
        if command[:2] == ["checksec", "--help"]:
            return _help_ok(command)
        if command[0] == "checksec":
            return CommandResult(command, 1, "", "usage: checksec --file <binary>")
        raise AssertionError(f"unexpected command: {command!r}")

    result = ElfHardeningProbe(runner=runner).probe([elf])

    assert result["status"] == "blocked"
    assert result["checksec_state"] == "available"
    assert result["fallback_used"] is False
    assert result["fallback_reason"] is None
    assert result["results"][0]["status"] == "blocked"
    assert result["results"][0]["failure_reason"] == "invocation_error"
    assert not any(command[0] == "readelf" for command in calls)


def test_checksec_per_file_runtime_broken_allows_readelf_fallback(tmp_path):
    elf = _elf_file(tmp_path)
    calls = []

    def runner(command, **kwargs):
        calls.append(tuple(command))
        if command[:2] == ["checksec", "--help"]:
            return _help_ok(command)
        if command[0] == "checksec":
            return CommandResult(command, 127, "", "error while loading shared libraries: libpcre.so.3: cannot open shared object file")
        return _readelf_file_runner(command)

    result = ElfHardeningProbe(runner=runner).probe([elf])

    assert result["status"] == "degraded"
    assert result["checksec_state"] == "available"
    assert result["fallback_used"] is True
    assert result["results"][0]["status"] == "degraded"
    assert result["results"][0]["source"] == "readelf"
    assert result["results"][0]["unavailable_proof"]["classification"] == "broken"
    assert result["results"][0]["checks"]["nx"] == "NX enabled"
    assert any(command[0] == "readelf" for command in calls)


def test_checksec_confirmed_missing_allows_readelf_fallback(tmp_path):
    elf = _elf_file(tmp_path)
    calls = []

    def runner(command, **kwargs):
        calls.append(tuple(command))
        if command[:2] == ["checksec", "--help"]:
            return CommandResult(command, 127, "", "checksec: command not found")
        return _readelf_file_runner(command)

    result = ElfHardeningProbe(runner=runner).probe([elf])

    assert result["status"] == "degraded"
    assert result["checksec_state"] == "confirmed_unavailable"
    assert result["fallback_used"] is True
    assert result["fallback_reason"] == "checksec_confirmed_unavailable"
    assert result["unavailable_proof"]["classification"] == "missing"
    assert result["selected_mode"] == "readelf"
    assert result["results"][0]["source"] == "readelf"
    assert result["results"][0]["checks"]["nx"] == "NX enabled"
    assert any(command[0] == "readelf" for command in calls)


def test_readelf_partial_failures_do_not_infer_negative_hardening_results(tmp_path):
    elf = _elf_file(tmp_path)

    def runner(command, **kwargs):
        if command[:2] == ["checksec", "--help"]:
            return CommandResult(command, 127, "", "checksec: command not found")
        if command[:2] == ["readelf", "-l"]:
            return CommandResult(command, 0, "GNU_STACK      0x000000  RW\nGNU_RELRO\n", "")
        if command[:2] == ["readelf", "-d"]:
            return CommandResult(command, 1, "", "readelf: failed to read dynamic section")
        if command[:2] == ["readelf", "-h"]:
            return CommandResult(command, 0, "", "")
        if command[:2] == ["readelf", "-s"]:
            return CommandResult(command, 1, "", "readelf: symbols unavailable")
        if command[0] == "file":
            return CommandResult(command, 0, "", "")
        raise AssertionError(f"unexpected command: {command!r}")

    result = ElfHardeningProbe(runner=runner).probe([elf])
    checks = result["results"][0]["checks"]

    assert result["status"] == "degraded"
    assert checks["nx"] == "NX enabled"
    assert checks["relro"] == "unknown/unverified"
    assert checks["bind_now"] == "unknown/unverified"
    assert checks["pie"] == "unknown/unverified"
    assert checks["stack_canary"] == "unknown/unverified"
    assert checks["rpath_runpath"] == "unknown/unverified"
    assert checks["fortify_source"] == "unknown/unverified"
    assert checks["strip"] == "unknown/unverified"


def test_readelf_empty_or_failed_outputs_make_file_unverified(tmp_path):
    elf = _elf_file(tmp_path)

    def runner(command, **kwargs):
        if command[:2] == ["checksec", "--help"]:
            return CommandResult(command, 127, "", "checksec: command not found")
        if command[0] in {"readelf", "file"}:
            return CommandResult(command, 0, "", "")
        raise AssertionError(f"unexpected command: {command!r}")

    result = ElfHardeningProbe(runner=runner).probe([elf])

    assert result["status"] == "degraded"
    assert result["results"][0]["status"] == "unverified"
    assert result["results"][0]["checks"] == {}
    assert result["results"][0]["failure_reason"] == "fallback_tools_unavailable"


def test_multi_file_success_and_invocation_error_preserves_per_file_results(tmp_path):
    good = _elf_file(tmp_path, "good")
    bad = _elf_file(tmp_path, "bad")

    def runner(command, **kwargs):
        if command[:2] == ["checksec", "--help"]:
            return _help_ok(command)
        if command[0] == "checksec" and str(good) in command[1] and "--format=json" in command:
            return CommandResult(command, 0, '{"relro":"Full RELRO","nx":"NX enabled"}', "")
        if command[0] == "checksec" and str(bad) in command[1]:
            return CommandResult(command, 1, "", "usage: checksec --file <binary>")
        raise AssertionError(f"unexpected command: {command!r}")

    result = ElfHardeningProbe(runner=runner).probe([good, bad])

    assert result["status"] == "blocked"
    assert result["checksec_state"] == "available"
    assert result["selected_mode"] == "format_json"
    assert result["results"][0]["status"] == "ready"
    assert result["results"][0]["mode"] == "format_json"
    assert result["results"][1]["status"] == "blocked"
    assert result["results"][1]["failure_reason"] == "invocation_error"


def test_unreadable_file_is_unverified_without_polluting_global_tool_state(tmp_path):
    good = _elf_file(tmp_path, "good")
    missing = tmp_path / "missing"
    calls = []

    def runner(command, **kwargs):
        calls.append(tuple(command))
        if command[:2] == ["checksec", "--help"]:
            return _help_ok(command)
        if command[0] == "checksec" and "--format=json" in command:
            return CommandResult(command, 0, '{"relro":"Full RELRO"}', "")
        raise AssertionError(f"unexpected command: {command!r}")

    result = ElfHardeningProbe(runner=runner).probe([good, missing])

    assert result["status"] == "blocked"
    assert result["checksec_state"] == "available"
    assert [entry["status"] for entry in result["results"]] == ["ready", "unverified"]
    assert result["results"][1]["failure_reason"] == "file_unreadable"
    assert not any(str(missing) in " ".join(command) for command in calls)


def test_non_elf_input_is_skipped_and_blocks_false_complete_result(tmp_path):
    elf = _elf_file(tmp_path, "good")
    text = tmp_path / "not-elf"
    text.write_text("plain text", encoding="utf-8")
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        if command[:2] == ["checksec", "--help"]:
            return _help_ok(command)
        if command[0] == "checksec" and "--format=json" in command:
            return CommandResult(command, 0, '{"nx":"NX enabled"}', "")
        raise AssertionError(f"unexpected command: {command!r}")

    result = ElfHardeningProbe(runner=runner).probe([elf, text])

    assert result["status"] == "blocked"
    assert result["coverage_complete"] is True
    assert result["input_total"] == result["result_total"] == 2
    assert result["result_counts"] == {
        "ready": 1,
        "degraded": 0,
        "blocked": 0,
        "unverified": 0,
        "skipped": 1,
    }
    assert result["results"][1]["failure_reason"] == "not_elf"
    assert not any(str(text) in " ".join(command) for command in calls)


def test_cli_batches_and_checkpoints_results(tmp_path, capsys):
    files = [_elf_file(tmp_path, f"app-{index}") for index in range(3)]
    output_json = tmp_path / "elf-probe.json"

    def runner(command, **kwargs):
        if command[:2] == ["checksec", "--help"]:
            return _help_ok(command)
        if command[0] == "checksec" and "--format=json" in command:
            return CommandResult(command, 0, '{"nx":"NX enabled"}', "")
        raise AssertionError(f"unexpected command: {command!r}")

    argv = [item for path in files for item in ("--file", str(path))]
    exit_code = main(
        argv
        + [
            "--output-json",
            str(output_json),
            "--batch-size",
            "2",
            "--checkpoint",
        ],
        runner=runner,
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert len(payload["results"]) == 3
    assert payload["coverage_complete"] is True
    assert payload["input_total"] == payload["result_total"] == 3
    assert payload["result_counts"]["ready"] == 3
    assert payload["checkpoint"]["batches_completed"] == 2
    assert payload["checkpoint"]["input_total"] == 3
    assert payload["checkpoint"]["remaining"] == 0
    assert len(capsys.readouterr().out.splitlines()) == 1


def test_cli_resume_skips_files_already_in_checkpoint(tmp_path, capsys):
    first = _elf_file(tmp_path, "first")
    second = _elf_file(tmp_path, "second")
    output_json = tmp_path / "elf-probe.json"
    output_json.write_text(
        json.dumps(
            {
                "status": "ready",
                "tool_invocations": [],
                "results": [{"file": str(first), "status": "ready", "checks": {}}],
                "checkpoint": {"batches_completed": 1},
            }
        ),
        encoding="utf-8",
    )
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        if command[:2] == ["checksec", "--help"]:
            return _help_ok(command)
        if command[0] == "checksec" and "--format=json" in command:
            return CommandResult(command, 0, '{"nx":"NX enabled"}', "")
        raise AssertionError(f"unexpected command: {command!r}")

    exit_code = main(
        [
            "--file",
            str(first),
            "--file",
            str(second),
            "--output-json",
            str(output_json),
            "--batch-size",
            "1",
            "--checkpoint",
            "--resume",
        ],
        runner=runner,
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert [entry["file"] for entry in payload["results"]] == [str(first), str(second)]
    assert payload["checkpoint"]["resumed_count"] == 1
    assert not any(str(first) in " ".join(command) for command in calls)
    assert len(capsys.readouterr().out.splitlines()) == 1


def test_cli_missing_list_file_blocks_without_traceback(tmp_path, capsys):
    output_json = tmp_path / "probe.json"

    exit_code = main(["--list-file", str(tmp_path / "missing.txt"), "--output-json", str(output_json)])

    captured = capsys.readouterr()
    assert exit_code == 5
    assert "reason=list_file_not_found" in captured.err
    assert "Traceback" not in captured.err
    assert not output_json.exists()


def test_cli_writes_json_and_prints_single_summary_line(tmp_path, capsys):
    elf = _elf_file(tmp_path)
    output_json = tmp_path / "security-reports" / "elf-probe.json"

    def runner(command, **kwargs):
        if command[:2] == ["checksec", "--help"]:
            return _help_ok(command)
        if command[0] == "checksec" and "--format=json" in command:
            return CommandResult(command, 0, '{"relro":"Full RELRO"}', "")
        raise AssertionError(f"unexpected command: {command!r}")

    exit_code = main(["--file", str(elf), "--output-json", str(output_json)], runner=runner)

    stdout_lines = capsys.readouterr().out.splitlines()
    payload = json.loads(output_json.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["status"] == "ready"
    assert len(stdout_lines) == 1
    assert "elf_probe status=ready" in stdout_lines[0]
    assert "checksec=available" in stdout_lines[0]
    assert not stdout_lines[0].lstrip().startswith("{")
