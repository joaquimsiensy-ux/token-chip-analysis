#!/usr/bin/env python3
"""F-01 handoff case-root containment 负向测试（test-only，预期先红）。

覆盖 generate/verify/freeze/check-unseal 的案外路径、绝对路径、逐段 symlink、
原始字符串空段/点段，以及待新增 case_paths.safe_case_file 的单元向量。

用法：python3 scripts/tests/test_repair_g1_handoff_containment.py
未修复生产代码预期退出 1；修复后预期退出 0。
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

from formal_ready_test_harness import run_formal_script
from test_handoff_manifest import FRZ, GEN, make_case, setup_freezeable


HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "report" / "handoff_manifest.py"
FAILS: list[str] = []
CHECKS: list[str] = []
PATH_REJECTION_NEEDLES = (
    "路径", "案根", "相对", "绝对", "越界", "非法", "符号链接", "symlink", "path",
)


def run(args):
    return run_formal_script(str(SCRIPT), args)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def combined_output(proc) -> str:
    return (proc.stdout or "") + (proc.stderr or "")


def observed(proc) -> str:
    text = combined_output(proc).strip().replace("\n", " | ")
    return f"observed rc={proc.returncode}; output={text[-900:] or '<empty>'}"


def path_rejected(proc) -> bool:
    output = combined_output(proc).lower()
    return proc.returncode == 2 and any(needle.lower() in output for needle in PATH_REJECTION_NEEDLES)


def check(name: str, cond: bool, detail: str = "") -> None:
    CHECKS.append(name)
    if cond:
        print(f"ok    {name}")
        return
    FAILS.append(name)
    print(f"FAIL  {name}")
    if detail:
        print(f"      {detail}")


def ready_case(root: Path, name: str) -> Path:
    case = root / name
    case.mkdir()
    make_case(str(case))
    return case


def generate_ready(case: Path):
    return run(["generate", "--case-dir", str(case), "--status", "READY", *GEN])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_a1_include_dotdot(root: Path) -> None:
    case = ready_case(root, "a1_case")
    outside = root / "a1_outside.json"
    write_json(outside, {"secret": "a1"})
    proc = run(["generate", "--case-dir", str(case), "--status", "READY", *GEN,
                "--include", "../a1_outside.json"])
    check("a1 --include ../outside.json generate 硬退 rc=2 且报路径拒绝",
          path_rejected(proc), observed(proc))


def test_a2_data_map_dotdot(root: Path) -> None:
    case = ready_case(root, "a2_case")
    outside = root / "a2_outside.json"
    write_json(outside, {"secret": "a2"})
    data_map_path = case / "data_map.json"
    data_map = json.loads(data_map_path.read_text(encoding="utf-8"))
    data_map["files"].append({"path": "../a2_outside.json", "source": "escape"})
    write_json(data_map_path, data_map)
    proc = generate_ready(case)
    check("a2 data_map files[].path=../outside.json generate 硬退",
          path_rejected(proc), observed(proc))


def test_a3_manifest_dotdot(root: Path) -> None:
    case = ready_case(root, "a3_case")
    generated = generate_ready(case)
    if generated.returncode != 0:
        check("a3 前置 READY manifest 生成", False, observed(generated))
        return
    outside = root / "a3_outside.json"
    write_json(outside, {"secret": "a3"})
    manifest_path = case / "handoff_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"].append({
        "path": "../a3_outside.json",
        "bytes": outside.stat().st_size,
        "hash_algo": "sha256",
        "sha256": sha256(outside),
    })
    write_json(manifest_path, manifest)
    proc = run(["verify", "--case-dir", str(case)])
    check("a3 manifest artifacts[].path=../outside.json verify 拒 READY",
          path_rejected(proc), observed(proc))


def test_b1_include_absolute(root: Path) -> None:
    case = root / "b1_case"
    case.mkdir()
    outside = root / "b1_outside.json"
    write_json(outside, {"secret": "b1"})
    proc = run(["generate", "--case-dir", str(case), "--status", "PARTIAL",
                "--mode", "full", "--producer-model", "test-model",
                "--include", str(outside.resolve())])
    check("b1 --include 绝对路径 generate 硬退", path_rejected(proc), observed(proc))


def test_b2_data_map_intermediate_symlink(root: Path) -> None:
    case = ready_case(root, "b2_case")
    outside_dir = root / "b2_outside_dir"
    outside_dir.mkdir()
    outside = outside_dir / "payload.json"
    write_json(outside, {"secret": "b2"})
    os.symlink(outside_dir, case / "data" / "escape_link")
    data_map_path = case / "data_map.json"
    data_map = json.loads(data_map_path.read_text(encoding="utf-8"))
    data_map["files"].append({"path": "data/escape_link/payload.json", "source": "escape"})
    write_json(data_map_path, data_map)
    proc = generate_ready(case)
    check("b2 data_map 中间目录 symlink 指案外 generate 硬退",
          path_rejected(proc), observed(proc))


def test_b3_sealed_symlink(root: Path) -> None:
    case = ready_case(root, "b3_case")
    outside = root / "b3_outside.json"
    outside.write_bytes(b"b3-unique-outside-payload\n")
    os.symlink(outside, case / "sealed" / "outside-link.json")
    proc = generate_ready(case)
    sealed_hashes = set()
    if proc.returncode == 0:
        manifest = json.loads((case / "handoff_manifest.json").read_text(encoding="utf-8"))
        sealed_hashes = {entry.get("sha256") for entry in manifest.get("sealed", [])}
    safe = path_rejected(proc) or (proc.returncode == 0 and sha256(outside) not in sealed_hashes)
    check("b3 sealed/ 案外 symlink 拒绝或不收录案外哈希", safe,
          f"{observed(proc)}; outside_sha_in_manifest={sha256(outside) in sealed_hashes}")


def test_b4_freeze_absolute_members(root: Path) -> None:
    case = ready_case(root, "b4_case")
    generated = generate_ready(case)
    if generated.returncode != 0:
        check("b4 前置 READY manifest 生成", False, observed(generated))
        return
    setup_freezeable(str(case))
    proc = run(["freeze", "--case-dir", str(case),
                "--members", str((case / "analysis-state.json").resolve()),
                "--entity-file", "s2_entity_members.json"])
    check("b4 freeze --members 绝对路径硬退", path_rejected(proc), observed(proc))


def test_b5_check_unseal_dotdot_binding(root: Path) -> None:
    case = ready_case(root, "b5_case")
    generated = generate_ready(case)
    if generated.returncode != 0:
        check("b5 前置 READY manifest 生成", False, observed(generated))
        return
    setup_freezeable(str(case))
    frozen = run(["freeze", "--case-dir", str(case), *FRZ])
    if frozen.returncode != 0:
        check("b5 前置合法 freeze", False, observed(frozen))
        return
    outside = root / "b5_outside_members.json"
    shutil.copyfile(case / "analysis-state.json", outside)
    freeze_path = case / "entity_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    freeze["members_source"] = "../b5_outside_members.json"
    freeze["members_sha256"] = sha256(outside)
    write_json(freeze_path, freeze)
    proc = run(["freeze", "--case-dir", str(case), "--check-unseal"])
    output = combined_output(proc).lower()
    rejected = proc.returncode == 2 and any(
        needle in output for needle in ("路径", "案根", "相对", "越界", "绑定", "无效", "path"))
    check("b5 check-unseal 拒绝 entity_freeze.json 的 ../ 绑定路径",
          rejected, observed(proc))


def test_b6_raw_string_edges(root: Path) -> None:
    variants = (
        ("dot-segment", "a/./b.json"),
        ("empty-segment", "a//b.json"),
        ("empty-string", ""),
    )
    for label, shown in variants:
        case = root / f"b6_{label}"
        case.mkdir()
        write_json(case / "a" / "b.json", {"variant": label})
        proc = run(["generate", "--case-dir", str(case), "--status", "PARTIAL",
                    "--mode", "full", "--producer-model", "test-model",
                    "--include", shown])
        check(f"b6 --include 原始字符串 {shown!r} 硬退",
              path_rejected(proc), observed(proc))


def test_c1_safe_case_file_vectors(root: Path) -> None:
    case = root / "c1_case"
    case.mkdir()
    good = case / "good.json"
    write_json(good, {"ok": True})
    nested = case / "a" / "b"
    write_json(nested, {"ok": True})
    outside = root / "x"
    outside.write_text("outside\n", encoding="utf-8")
    details = []
    try:
        module = importlib.import_module("case_paths")
        safe_case_file = module.safe_case_file
    except Exception as exc:  # 本阶段模块尚不存在：把 import 缺失登记成预期红，不中止其余 CLI 例。
        check("c1 case_paths.safe_case_file 单元向量组", False,
              f"import failed: {type(exc).__name__}: {exc}")
        return

    invalid = ("../x", str(outside.resolve()), "a/./b", "a//b", "", 123)
    all_ok = True
    for value in invalid:
        try:
            safe_case_file(case, value)
        except ValueError:
            continue
        except Exception as exc:
            all_ok = False
            details.append(f"{value!r} raised {type(exc).__name__}, want ValueError")
        else:
            all_ok = False
            details.append(f"{value!r} did not raise ValueError")
    try:
        returned = Path(safe_case_file(case, "good.json"))
        if returned.resolve() != good.resolve() or not returned.is_file():
            all_ok = False
            details.append(f"normal path returned {returned!s}")
    except Exception as exc:
        all_ok = False
        details.append(f"normal path raised {type(exc).__name__}: {exc}")
    check("c1 case_paths.safe_case_file 单元向量组", all_ok, "; ".join(details))


def test_c2_normal_ready_chain(root: Path) -> None:
    case = ready_case(root, "c2_case")
    generated = generate_ready(case)
    verified = run(["verify", "--case-dir", str(case)]) if generated.returncode == 0 else generated
    check("c2 正常案 generate→verify 保持 READY",
          generated.returncode == 0 and verified.returncode == 0 and "READY" in combined_output(verified),
          f"generate: {observed(generated)}; verify: {observed(verified)}")


def test_c3_optional_contract_missing_partial(root: Path) -> None:
    case = root / "c3_case"
    case.mkdir()
    write_json(case / "candidate_universe.json", {"candidates": []})
    optional = case / "unlock_evidence.json"
    proc = run(["generate", "--case-dir", str(case), "--status", "PARTIAL",
                "--mode", "full", "--producer-model", "test-model"])
    paths = set()
    if proc.returncode == 0:
        manifest = json.loads((case / "handoff_manifest.json").read_text(encoding="utf-8"))
        paths = {entry.get("path") for entry in manifest.get("artifacts", [])}
    check("c3 CONTRACT_FILES 可选件缺失不误停 PARTIAL",
          not optional.exists() and proc.returncode == 0 and "unlock_evidence.json" not in paths,
          observed(proc))


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="repair_g1_handoff_containment_"))
    try:
        test_a1_include_dotdot(root)
        test_a2_data_map_dotdot(root)
        test_a3_manifest_dotdot(root)
        test_b1_include_absolute(root)
        test_b2_data_map_intermediate_symlink(root)
        test_b3_sealed_symlink(root)
        test_b4_freeze_absolute_members(root)
        test_b5_check_unseal_dotdot_binding(root)
        test_b6_raw_string_edges(root)
        test_c1_safe_case_file_vectors(root)
        test_c2_normal_ready_chain(root)
        test_c3_optional_contract_missing_partial(root)
    finally:
        shutil.rmtree(root)

    if FAILS:
        print(f"\nFAIL: {len(FAILS)}/{len(CHECKS)} checks failed (test-only expected red)")
        for name in FAILS:
            print(f"  - {name}")
        return 1
    print(f"\nPASS: {len(CHECKS)}/{len(CHECKS)} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
