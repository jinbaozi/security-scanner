from pathlib import Path

import pytest

from scripts.package_materializer import CommandResult, PackageMaterializer, detect_input_kind


class FakeRunner:
    def __init__(self, failures=None):
        self.commands = []
        self.failures = failures or {}

    def __call__(self, command, cwd=None, **kwargs):
        self.commands.append((tuple(command), Path(cwd) if cwd else None))
        cwd_path = Path(cwd) if cwd else None

        if command[0] == "cpio" and cwd_path:
            if "srpm-extract" in cwd_path.parts:
                (cwd_path / "pkg.spec").write_text(
                    "Name: pkg\nVersion: 1\nSource0: pkg.tar.gz\nPatch0: fix.patch\n",
                    encoding="utf-8",
                )
                (cwd_path / "pkg.tar.gz").write_text("tarball", encoding="utf-8")
                (cwd_path / "fix.patch").write_text("patch", encoding="utf-8")
            if "binary-root" in cwd_path.parts:
                bin_path = cwd_path / "usr" / "bin"
                bin_path.mkdir(parents=True, exist_ok=True)
                (bin_path / "app").write_bytes(b"\x7fELF")

        if command[0] == "rpmbuild" and cwd_path:
            if self.failures.get("rpmbuild"):
                return CommandResult(command, self.failures["rpmbuild"], "", "Failed build dependencies")
            build_dir = cwd_path / "BUILD" / "pkg-1"
            build_dir.mkdir(parents=True, exist_ok=True)
            (build_dir / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")

        if command[:2] == ["dnf", "builddep"] and self.failures.get("dnf"):
            return CommandResult(command, self.failures["dnf"], "", "dnf failed")

        return CommandResult(command, 0, "", "")


def test_detects_package_input_kinds(tmp_path):
    srpm = tmp_path / "pkg.src.rpm"
    rpm = tmp_path / "pkg.x86_64.rpm"
    src = tmp_path / "src"
    srpm.touch()
    rpm.touch()
    src.mkdir()

    assert detect_input_kind(srpm) == "srpm"
    assert detect_input_kind(rpm) == "binary_rpm"
    assert detect_input_kind(src) == "source_tree"

    (src / "nested.src.rpm").touch()
    assert detect_input_kind(src) == "package_directory"


def test_srpm_materialization_runs_prep_in_isolated_topdir(tmp_path):
    srpm = tmp_path / "pkg.src.rpm"
    srpm.touch()
    runner = FakeRunner()

    result = PackageMaterializer(runner=runner).materialize(srpm, tmp_path / "out")

    commands = [command for command, _ in runner.commands]
    rpmbuild = next(command for command in commands if command[0] == "rpmbuild")

    assert result["status"] == "ready"
    assert result["input_kind"] == "srpm"
    assert result["srpm_spec_files"]
    assert result["source_roots"] == [
        {"path": str(tmp_path / "out" / "rpmbuild" / "pkg" / "BUILD" / "pkg-1"), "origin": "source_prepped"}
    ]
    assert result["applied_patches"] == ["fix.patch"]
    assert "--nodeps" in rpmbuild
    assert "_topdir" in " ".join(rpmbuild)
    assert str(tmp_path / "out" / "rpmbuild" / "pkg") in " ".join(rpmbuild)


def test_binary_rpm_materialization_expands_binary_root(tmp_path):
    rpm = tmp_path / "pkg.x86_64.rpm"
    rpm.touch()

    result = PackageMaterializer(runner=FakeRunner()).materialize(rpm, tmp_path / "out")

    assert result["status"] == "ready"
    assert result["input_kind"] == "binary_rpm"
    assert result["binary_roots"] == [
        {"path": str(tmp_path / "out" / "binary-root" / "pkg.x86_64"), "origin": "binary_rpm"}
    ]


def test_failed_srpm_prep_requires_builddep_authorization_without_running_dnf(tmp_path):
    srpm = tmp_path / "pkg.src.rpm"
    srpm.touch()
    runner = FakeRunner(failures={"rpmbuild": 1})

    result = PackageMaterializer(runner=runner).materialize(srpm, tmp_path / "out")

    assert result["status"] == "blocked"
    assert result["builddep_attempted"] is False
    assert result["builddep_status"] == "authorization_required"
    assert result["errors"]
    assert not any(command[:2] == ("dnf", "builddep") for command, _ in runner.commands)


def test_builddep_success_retries_prep_when_authorized_as_root(tmp_path):
    srpm = tmp_path / "pkg.src.rpm"
    srpm.touch()
    attempts = {"rpmbuild": 0}

    def runner(command, cwd=None, **kwargs):
        if command[0] == "cpio" and cwd:
            cwd_path = Path(cwd)
            (cwd_path / "pkg.spec").write_text("Name: pkg\nVersion: 1\n", encoding="utf-8")
        if command[0] == "rpmbuild":
            attempts["rpmbuild"] += 1
            if attempts["rpmbuild"] == 1:
                return CommandResult(command, 1, "", "Failed build dependencies")
            build_dir = Path(cwd) / "BUILD" / "pkg-1"
            build_dir.mkdir(parents=True, exist_ok=True)
        return CommandResult(command, 0, "", "")

    result = PackageMaterializer(runner=runner, effective_uid=lambda: 0).materialize(
        srpm,
        tmp_path / "out",
        allow_builddep=True,
    )

    assert result["status"] == "ready"
    assert result["builddep_attempted"] is True
    assert result["builddep_status"] == "succeeded"
    assert attempts["rpmbuild"] == 2


def test_builddep_authorization_does_not_bypass_root_requirement(tmp_path):
    srpm = tmp_path / "pkg.src.rpm"
    srpm.touch()
    runner = FakeRunner(failures={"rpmbuild": 1})

    result = PackageMaterializer(runner=runner, effective_uid=lambda: 1000).materialize(
        srpm,
        tmp_path / "out",
        allow_builddep=True,
    )

    assert result["status"] == "blocked"
    assert result["builddep_status"] == "root_authorization_required"
    assert not any(command[:2] == ("dnf", "builddep") for command, _ in runner.commands)


def test_source_tree_is_recorded_without_rpm_semantics(tmp_path):
    src = tmp_path / "src"
    src.mkdir()

    result = PackageMaterializer(runner=FakeRunner()).materialize(src, tmp_path / "out")

    assert result["status"] == "ready"
    assert result["input_kind"] == "source_tree"
    assert result["source_roots"] == [{"path": str(src), "origin": "raw_directory"}]
    assert "未验证 RPM patch 语义" in result["audit_log"][0]
