"""Replay both claim-files fixtures against the pre-hard-rejection HEAD in memory."""
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/tests"))
import test_a4_gate as t

class Captured(Exception):
    pass

def trace(frame, event, arg):
    if (event != "line" or frame.f_code is not t.main.__code__
            or frame.f_lineno != cutoff):
        return trace
    sys.settrace(None)
    original = frame.f_locals["d"]
    output = ["\nP2-2 RED (2026-09-06): before fixture edits",
              "command: PYTHONDONTWRITEBYTECODE=1 python3 maintenance/repair-20260906-main-threefix/reproduce_p2_c_red.py"]
    for name in ("scripts/tests/test_a4_gate.py", "scripts/report/a4_gate.py",
                 str(Path(__file__).relative_to(ROOT))):
        output.append(f"sha256 {name}: {hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}")
    old = subprocess.check_output(["git", "show", "8396aa4:scripts/report/a4_gate.py"], cwd=ROOT)
    output.append(f"pre-hard-rejection production sha256: {hashlib.sha256(old).hexdigest()}")
    harness = '''import subprocess, sys
from pathlib import Path
root = Path(sys.argv.pop(1))
sys.path.insert(0, str(root / "scripts/tests"))
from formal_ready_test_harness import test_vertical_slices
script = str(root / "scripts/report/a4_gate.py")
sys.argv = [script] + sys.argv[1:]
source = subprocess.check_output(["git", "show", "8396aa4:scripts/report/a4_gate.py"], cwd=root)
with test_vertical_slices():
    exec(compile(source, script, "exec"), {"__name__": "__main__", "__file__": script})
'''
    passed = True
    for reserved in ("v_ok.json", "a4_claims.json"):
        for sync in (False, True):
            copied = Path(tempfile.mkdtemp(prefix="p2_c_red_")) / "case"
            shutil.copytree(original, copied)
            t.rebind_case_inputs(original, copied)
            claim_path = copied / "a4_claims.json"
            obj = json.loads(claim_path.read_text())
            obj["claims"][0]["files"].append(reserved)
            claim_path.write_text(json.dumps(obj, ensure_ascii=False))
            if sync:
                registry_path = copied / "claim_registry.json"
                registry = json.loads(registry_path.read_text())
                claim = obj["claims"][0]
                next(c for c in registry["claims"] if c["claim_id"] == claim["id"])["evidence_files"] = claim["files"]
                registry_path.write_text(json.dumps(registry, ensure_ascii=False))
            command = [sys.executable, "-c", harness, str(ROOT), "finalize",
                       "--case-dir", str(copied), "--seal-files", "findings.md,analysis-state.json",
                       "--verdicts-file", str(copied / "v_ok.json"), "--workflow-type", "independent-audit"]
            p = subprocess.run(command, capture_output=True, text=True)
            exists = (copied / "a4_seal.json").is_file()
            output.extend([f"reserved={reserved}, synchronized_registry={sync}",
                           f"command: {shlex.join(command)}", f"exit_code: {p.returncode}",
                           f"--- stdout ---\n{p.stdout}--- stderr ---\n{p.stderr}",
                           f"seal_exists: {exists}"])
            passed &= (p.returncode == 0 and exists) if sync else (
                p.returncode == 2 and "claim C1 证据文件集合不一致" in p.stderr and not exists)
    output.append(f"reproducer_exit_code: {0 if passed else 1}")
    text = "\n".join(output) + "\n"
    with (ROOT / "maintenance/repair-20260906-main-threefix/red_evidence.txt").open("a") as fh:
        fh.write(text)
    print(text)
    assert passed
    raise Captured

cutoff = next(i for i, line in enumerate(Path(t.__file__).read_text().splitlines(), 1)
              if 'for source, reserved in' in line)
sys.settrace(trace)
try:
    t.main()
except Captured:
    pass
finally:
    sys.settrace(None)
