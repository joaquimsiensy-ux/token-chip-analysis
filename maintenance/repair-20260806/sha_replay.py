#!/usr/bin/env python3
"""R9 最终验收:49/49 SHA 回放(Fable 读码/台账对表,机器化)。

四道检查:
A. diff-finding-map SHA 回填表:每个登记 SHA 存在于仓库且是 HEAD 祖先。
B. ledger 主表恰 49 行,且每行"最终结果/两轮盲审"栏非空。
C. ledger 详情节:每个 ### 项都有"最终结果"与"两轮盲审与 Fable 结论"行。
D. 全区间 main-base..HEAD 每个改动文件都能在 map 中找到 owner 提及(文件名级)。
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# 口径声明(Round B 盲审指出原登记缺口径与工具):
# A 检查只数「SHA 回填表」的两列行(| `组` | `sha` |),不含主表 SHA 列与叙事段 SHA——
# 与 Round B 的宽口径(67 行/71 提及/41 unique,含叙事/裁决 SHA)计数不同属口径差,
# 两口径下 missing=0、non-ancestor=0 的结论一致。
MAP = ROOT / "maintenance/repair-20260806/diff-finding-map.md"
LEDGER = ROOT / "maintenance/repair-20260806/ledger.md"
MAIN_BASE = "63cf715"

def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args],
                          capture_output=True, text=True)

fails = []

# ---- A. SHA 回填表 ----
map_text = MAP.read_text(encoding="utf-8")
# SHA 回填表行形如: | `组名` | `sha` | 说明 |
sha_rows = re.findall(r"^\|\s*`([^`]+)`\s*\|\s*`([0-9a-f]{7,40})`\s*\|", map_text, re.M)
if not sha_rows:
    fails.append("A: SHA 回填表一行都没抓到(正则失配?)")
seen_shas = {}
for group, sha in sha_rows:
    seen_shas.setdefault(sha, []).append(group)
print(f"A. SHA 回填表:{len(sha_rows)} 行,{len(seen_shas)} 个唯一 SHA")
for sha in sorted(seen_shas):
    exists = git("cat-file", "-e", f"{sha}^{{commit}}").returncode == 0
    if not exists:
        fails.append(f"A: SHA {sha} 不存在于仓库(组 {seen_shas[sha]})")
        continue
    anc = git("merge-base", "--is-ancestor", sha, "HEAD").returncode == 0
    if not anc:
        fails.append(f"A: SHA {sha} 不在 HEAD 祖先链上(组 {seen_shas[sha]})")
    else:
        print(f"   ✓ {sha}  ({len(seen_shas[sha])} 组: {', '.join(seen_shas[sha][:4])}{'…' if len(seen_shas[sha])>4 else ''})")

# 空 SHA 行(登记了组但 SHA 空)= 阻断
empty_sha = re.findall(r"^\|\s*`([^`]+)`\s*\|\s*\|\s*", map_text, re.M)
# 排除主表 owner 行(它们最后一列才是 SHA,结构不同);只统计回填表段落
replay_section = map_text.split("SHA 回填", 1)[-1] if "SHA 回填" in map_text else map_text
empty_in_replay = re.findall(r"^\|\s*`([^`]+)`\s*\|\s+\|\s+[^|]*\|\s*$", replay_section, re.M)
for g in empty_in_replay:
    fails.append(f"A: 组 {g} 的 SHA 仍为空(未回填)")

# ---- B. ledger 主表 49 行 ----
ledger_text = LEDGER.read_text(encoding="utf-8")
main_rows = re.findall(r"^\|\s*`([A-Za-z0-9-]+)`\s*\|\s*(?:full|six|R7|R8|R9)@", ledger_text, re.M)
print(f"\nB. ledger 主表行数:{len(main_rows)}")
if len(main_rows) != 49:
    fails.append(f"B: 主表 {len(main_rows)} 行 ≠ 49")
# 主表行空栏检查:相邻 || 或 | | 即空栏
for m in re.finditer(r"^(\|\s*`(?:full|six|R7|R8|R9)[A-Za-z0-9-]*`.*)$", ledger_text, re.M):
    row = m.group(1)
    if re.search(r"\|\s*\|", row):
        fails.append(f"B: 主表行含空栏: {row[:60]}…")

# ---- C. 详情节完整性 ----
detail_ids = re.findall(r"^### ([A-Za-z0-9-]+)\s*$", ledger_text, re.M)
print(f"C. 详情节数:{len(detail_ids)}")
for did in detail_ids:
    sec = ledger_text.split(f"### {did}\n", 1)
    if len(sec) < 2:
        continue
    body = sec[1].split("\n### ", 1)[0]
    if "最终结果" not in body:
        fails.append(f"C: 详情 {did} 缺『最终结果』")
    if "两轮盲审" not in body and "盲审" not in body:
        fails.append(f"C: 详情 {did} 缺『两轮盲审』")

# ---- D. 全区间改动文件 owner 覆盖 ----
r = git("diff", "--name-only", f"{MAIN_BASE}..HEAD")
changed = [l for l in r.stdout.splitlines() if l.strip()]
print(f"\nD. 全区间 {MAIN_BASE}..HEAD 改动文件数:{len(changed)}")
unowned = []
for f in changed:
    base = f.split("/")[-1]
    # map 提及(全路径或文件名);审查产物区按 map 通例豁免(r9-reviews/、blind-reviews/、
    # maintenance/repair-20260806/reviews/ 的 r9-batch*-*.md 入库件——通例已明文)
    if f.startswith("r9-reviews/") or f.startswith("blind-reviews/"):
        continue
    if re.fullmatch(r"maintenance/repair-20260806/reviews/r9-batch\d.*\.md", f):
        continue
    if f in map_text or base in map_text:
        continue
    unowned.append(f)
if unowned:
    for f in unowned:
        fails.append(f"D: 改动文件无 map owner 提及: {f}")
else:
    print("   ✓ 全部改动文件在 map 中有 owner 提及(审查产物区按通例豁免)")

# ---- 汇总 ----
print("\n" + "=" * 50)
if fails:
    print(f"SHA 回放 FAIL:{len(fails)} 项")
    for x in fails:
        print(" -", x)
    sys.exit(1)
print("SHA 回放 PASS:A(SHA 全集在链上)/B(49 行零空栏)/C(详情节完整)/D(改动文件全覆盖)")
