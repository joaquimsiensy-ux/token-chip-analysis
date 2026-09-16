"""T1 evidence runner: preserve exact command, return code, streams and hashes."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys

phase, command, *files = sys.argv[1:]
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
p = subprocess.run(command, shell=True, executable="/bin/zsh", capture_output=True, env=env)
record = f"\n=== {phase} ===\nCOMMAND: {command}\nENV: PYTHONDONTWRITEBYTECODE=1\nEXIT CODE: {p.returncode}\n".encode()
for name in files:
    record += f"SHA256 {name}: {hashlib.sha256(Path(name).read_bytes()).hexdigest()}\n".encode()
record += b"--- STDOUT (raw) ---\n" + p.stdout + b"\n--- STDERR (raw) ---\n" + p.stderr + b"\n--- END ---\n"
path = Path(__file__).with_name("t1_red_evidence.txt" if "RED" in phase else "t1_green_evidence.txt")
with path.open("ab") as fh:
    fh.write(record)
sys.stdout.buffer.write(record)
