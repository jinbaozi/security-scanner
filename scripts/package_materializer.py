"""Materialize RPM/SRPM inputs before scanner reconnaissance.

The scanner itself is prompt-driven, but package handling needs deterministic
filesystem preparation. This helper expands binary RPMs and runs SRPM %prep in
an isolated rpmbuild topdir so later phases scan final patched source trees.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


Runner = Callable[..., "CommandResult"]


@dataclass
class CommandResult:
    command: list[str] | tuple[str, ...]
    returncode: int
    stdout: str | bytes = ""
    stderr: str | bytes = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def default_runner(command: list[str], cwd: Path | None = None, **kwargs: Any) -> CommandResult:
    """Run a command and return captured output.

    ``capture_bytes`` and ``input_bytes`` are intentionally small extensions used
    for the rpm2cpio -> cpio stream without invoking a shell pipeline.
    """
    capture_bytes = bool(kwargs.pop("capture_bytes", False))
    input_bytes = kwargs.pop("input_bytes", None)
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        input=input_bytes,
        capture_output=True,
        text=not capture_bytes and input_bytes is None,
        check=False,
    )
    return CommandResult(command, completed.returncode, completed.stdout, completed.stderr)


def detect_input_kind(path: Path | str) -> str:
    target = Path(path)
    name = target.name.lower()
    if target.is_dir():
        return "package_directory" if any(target.rglob("*.rpm")) else "source_tree"
    if name.endswith(".src.rpm") or name.endswith(".srpm"):
        return "srpm"
    if name.endswith(".rpm"):
        return "binary_rpm"
    return "unknown"


def _rpm_stem(path: Path) -> str:
    name = path.name
    for suffix in (".src.rpm", ".srpm", ".rpm"):
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def _text(value: str | bytes) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


class PackageMaterializer:
    def __init__(
        self,
        runner: Runner = default_runner,
        effective_uid: Callable[[], int] | None = None,
    ) -> None:
        self.runner = runner
        self.effective_uid = effective_uid or (lambda: os.geteuid() if hasattr(os, "geteuid") else 0)

    def materialize(
        self,
        target_path: Path | str,
        output_dir: Path | str,
        *,
        allow_builddep: bool = False,
    ) -> dict[str, Any]:
        target = Path(target_path).resolve()
        materialized_root = Path(output_dir).resolve()
        materialized_root.mkdir(parents=True, exist_ok=True)
        input_kind = detect_input_kind(target)

        result = self._empty_result(target, materialized_root, input_kind)

        if input_kind == "source_tree":
            result["source_roots"].append({"path": str(target), "origin": "raw_directory"})
            result["audit_log"].append("普通目录按 raw_directory 扫描，未验证 RPM patch 语义。")
            return result

        if input_kind == "srpm":
            self._materialize_srpm(target, materialized_root, result, allow_builddep=allow_builddep)
            return result

        if input_kind == "binary_rpm":
            self._materialize_binary_rpm(target, materialized_root, result)
            return result

        if input_kind == "package_directory":
            packages = sorted(target.rglob("*.rpm"))
            if not packages:
                result["status"] = "blocked"
                result["errors"].append(f"目录中未找到 RPM/SRPM: {target}")
                return result
            for package in packages:
                kind = detect_input_kind(package)
                if kind == "srpm":
                    self._materialize_srpm(package, materialized_root, result, allow_builddep=allow_builddep)
                elif kind == "binary_rpm":
                    self._materialize_binary_rpm(package, materialized_root, result)
            if result["errors"]:
                result["status"] = "blocked"
            return result

        result["status"] = "blocked"
        result["errors"].append(f"不支持的输入类型: {target}")
        return result

    def _empty_result(self, target: Path, materialized_root: Path, input_kind: str) -> dict[str, Any]:
        return {
            "input_path": str(target),
            "input_kind": input_kind,
            "materialized_root": str(materialized_root),
            "source_roots": [],
            "binary_roots": [],
            "srpm_spec_files": [],
            "applied_patches": [],
            "builddep_attempted": False,
            "builddep_status": "not_required",
            "status": "ready",
            "errors": [],
            "audit_log": [],
        }

    def _materialize_srpm(
        self,
        srpm_path: Path,
        materialized_root: Path,
        result: dict[str, Any],
        *,
        allow_builddep: bool,
    ) -> None:
        package_name = _rpm_stem(srpm_path)
        extract_dir = materialized_root / "srpm-extract" / package_name
        extract_dir.mkdir(parents=True, exist_ok=True)
        extract = self._extract_rpm_payload(srpm_path, extract_dir)
        if not extract.ok:
            result["status"] = "blocked"
            result["errors"].append(f"SRPM 解包失败: {srpm_path}: {_text(extract.stderr)}")
            return

        specs = sorted(extract_dir.glob("*.spec"))
        if not specs:
            result["status"] = "blocked"
            result["errors"].append(f"SRPM 中未找到 spec 文件: {srpm_path}")
            return

        for spec in specs:
            self._run_prep_for_spec(spec, extract_dir, materialized_root, result, allow_builddep)

    def _materialize_binary_rpm(
        self,
        rpm_path: Path,
        materialized_root: Path,
        result: dict[str, Any],
    ) -> None:
        binary_root = materialized_root / "binary-root" / _rpm_stem(rpm_path)
        binary_root.mkdir(parents=True, exist_ok=True)
        extract = self._extract_rpm_payload(rpm_path, binary_root)
        if not extract.ok:
            result["status"] = "blocked"
            result["errors"].append(f"binary RPM 解包失败: {rpm_path}: {_text(extract.stderr)}")
            return
        result["binary_roots"].append({"path": str(binary_root), "origin": "binary_rpm"})
        result["audit_log"].append(f"binary RPM 已展开: {rpm_path} -> {binary_root}")

    def _extract_rpm_payload(self, rpm_path: Path, destination: Path) -> CommandResult:
        rpm2cpio = self.runner(["rpm2cpio", str(rpm_path)], capture_bytes=True)
        if not rpm2cpio.ok:
            return rpm2cpio
        stdout = rpm2cpio.stdout if isinstance(rpm2cpio.stdout, bytes) else _text(rpm2cpio.stdout).encode()
        return self.runner(["cpio", "-idm", "--quiet"], cwd=destination, input_bytes=stdout)

    def _run_prep_for_spec(
        self,
        spec: Path,
        extract_dir: Path,
        materialized_root: Path,
        result: dict[str, Any],
        allow_builddep: bool,
    ) -> None:
        package_name = spec.stem
        topdir = materialized_root / "rpmbuild" / package_name
        sourcedir = topdir / "SOURCES"
        specdir = topdir / "SPECS"
        builddir = topdir / "BUILD"
        for path in (sourcedir, specdir, builddir, topdir / "RPMS", topdir / "SRPMS", topdir / "BUILDROOT"):
            path.mkdir(parents=True, exist_ok=True)

        copied_spec = specdir / spec.name
        for item in sorted(extract_dir.iterdir()):
            if not item.is_file():
                continue
            destination = copied_spec if item.suffix == ".spec" else sourcedir / item.name
            shutil.copy2(item, destination)

        result["srpm_spec_files"].append(str(copied_spec))
        for patch in self._parse_declared_patches(copied_spec):
            if patch not in result["applied_patches"]:
                result["applied_patches"].append(patch)

        prep = self._run_rpmbuild_bp(copied_spec, topdir, sourcedir, specdir, builddir)
        if prep.ok:
            self._record_build_roots(builddir, result)
            result["audit_log"].append(f"SRPM %prep 完成: {copied_spec}")
            return

        if not self._looks_like_builddep_failure(prep):
            result["status"] = "blocked"
            result["errors"].append(f"rpmbuild -bp 失败: {copied_spec}: {_text(prep.stderr)}")
            return

        if not allow_builddep:
            result["status"] = "blocked"
            result["builddep_status"] = "authorization_required"
            result["errors"].append(
                f"rpmbuild -bp 失败且疑似缺少构建依赖；需要用户明确授权后才能执行 dnf builddep: {copied_spec}"
            )
            return

        if self.effective_uid() != 0:
            result["status"] = "blocked"
            result["builddep_status"] = "root_authorization_required"
            result["errors"].append("dnf builddep 会修改系统包环境；当前用户非 root，需要 root/sudo 授权后重试。")
            return

        result["builddep_attempted"] = True
        builddep = self.runner(["dnf", "builddep", "-y", str(copied_spec)])
        if not builddep.ok:
            result["status"] = "blocked"
            result["builddep_status"] = "failed"
            result["errors"].append(f"dnf builddep 失败: {_text(builddep.stderr)}")
            return

        retry = self._run_rpmbuild_bp(copied_spec, topdir, sourcedir, specdir, builddir)
        if retry.ok:
            result["builddep_status"] = "succeeded"
            self._record_build_roots(builddir, result)
            result["audit_log"].append(f"builddep 后 SRPM %prep 完成: {copied_spec}")
            return

        result["status"] = "blocked"
        result["builddep_status"] = "prep_failed_after_builddep"
        result["errors"].append(f"builddep 后 rpmbuild -bp 仍失败: {_text(retry.stderr)}")

    def _run_rpmbuild_bp(
        self,
        spec: Path,
        topdir: Path,
        sourcedir: Path,
        specdir: Path,
        builddir: Path,
    ) -> CommandResult:
        return self.runner(
            [
                "rpmbuild",
                "-bp",
                "--nodeps",
                "--define",
                f"_topdir {topdir}",
                "--define",
                f"_sourcedir {sourcedir}",
                "--define",
                f"_specdir {specdir}",
                "--define",
                f"_builddir {builddir}",
                str(spec),
            ],
            cwd=topdir,
        )

    def _record_build_roots(self, builddir: Path, result: dict[str, Any]) -> None:
        roots = sorted(path for path in builddir.iterdir() if path.is_dir())
        if not roots and builddir.exists():
            roots = [builddir]
        known = {entry["path"] for entry in result["source_roots"]}
        for root in roots:
            root_entry = {"path": str(root), "origin": "source_prepped"}
            if root_entry["path"] not in known:
                result["source_roots"].append(root_entry)
                known.add(root_entry["path"])

    def _parse_declared_patches(self, spec: Path) -> list[str]:
        patches: list[str] = []
        for line in spec.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped.lower().startswith("patch"):
                continue
            _, sep, value = stripped.partition(":")
            if sep and value.strip():
                patches.append(value.strip().split()[0])
        return patches

    def _looks_like_builddep_failure(self, result: CommandResult) -> bool:
        message = f"{_text(result.stdout)}\n{_text(result.stderr)}".lower()
        signals = (
            "failed build dependencies",
            "build dependencies",
            "is needed by",
            "no matching package",
            "unsatisfied dependency",
        )
        return any(signal in message for signal in signals)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Materialize SRPM/RPM inputs for security scanning.")
    parser.add_argument("target_path", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--allow-builddep",
        action="store_true",
        help="Allow dnf builddep after explicit user authorization and root execution.",
    )
    args = parser.parse_args(argv)

    result = PackageMaterializer().materialize(
        args.target_path,
        args.output_dir,
        allow_builddep=args.allow_builddep,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())

