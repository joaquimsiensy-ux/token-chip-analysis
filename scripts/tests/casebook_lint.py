#!/usr/bin/env python3
"""判例库守护：ID 唯一 + 六字段齐全 + 成熟度标记合法 + README 分册登记一致。

判例条目约定（references/casebook/README.md 六字段结构）：
  标题行:  ## <册前缀>-<两位序号> <标题> 【单案候选|机制成立|跨案复现】
  条目体:  必含五个粗体字段标记——触发现象/禁止推断/必做区分检验/证据不足时/权威与出处
用法：python3 scripts/tests/casebook_lint.py    退出码 0=PASS / 1=FAIL
"""
import glob
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
CASEBOOK = os.path.join(ROOT, "references", "casebook")
TITLE_RE = re.compile(r"^## ([A-Z])-(\d{2}) .+【(单案候选|机制成立|跨案复现)】\s*$")
REQUIRED_FIELDS = ["触发现象", "禁止推断", "必做区分检验", "证据不足时", "权威与出处"]
MAX_BYTES = 25 * 1024
MAX_ENTRIES = 25


def main():
    errs = []
    books = sorted(glob.glob(os.path.join(CASEBOOK, "*.md")))
    books = [b for b in books if os.path.basename(b) != "README.md"]
    if not books:
        print("FAIL: casebook 目录无分册")  # fail-closed：0 分册不算通过
        return 1

    readme_path = os.path.join(CASEBOOK, "README.md")
    readme = open(readme_path).read() if os.path.exists(readme_path) else ""
    if not readme:
        errs.append("casebook/README.md 缺失")

    all_ids = {}
    total_entries = 0
    for path in books:
        name = os.path.basename(path)
        text = open(path).read()
        size = os.path.getsize(path)
        if size > MAX_BYTES:
            errs.append(f"{name}: {size}B 超单册上限 {MAX_BYTES}B（先合并同族模式，不拆新册）")
        if name not in readme:
            errs.append(f"{name}: 未在 casebook/README.md 分册清单登记")

        # 切条目：以 "## " 分段
        lines = text.splitlines()
        heads = [(i, l) for i, l in enumerate(lines) if l.startswith("## ")]
        if not heads:
            errs.append(f"{name}: 无判例条目（## 标题）")
            continue
        if len(heads) > MAX_ENTRIES:
            errs.append(f"{name}: {len(heads)} 条超单册上限 {MAX_ENTRIES} 条")
        for k, (i, head) in enumerate(heads):
            m = TITLE_RE.match(head)
            if not m:
                errs.append(f"{name}:{i + 1}: 标题不合约定（需 '## X-NN 标题 【成熟度】'）: {head[:60]}")
                continue
            eid = f"{m.group(1)}-{m.group(2)}"
            if eid in all_ids:
                errs.append(f"{name}: 判例 ID {eid} 与 {all_ids[eid]} 重复")
            all_ids[eid] = name
            total_entries += 1
            end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
            body = "\n".join(lines[i:end])
            for field in REQUIRED_FIELDS:
                if f"**{field}**" not in body:
                    errs.append(f"{name}: {eid} 缺字段 **{field}**")

    if total_entries == 0:
        errs.append("全库 0 条判例（fail-closed：空库不算通过）")

    if errs:
        for e in errs:
            print(f"FAIL  {e}")
        print(f"{len(errs)} 处问题")
        return 1
    print(f"casebook lint 通过：{len(books)} 册 {total_entries} 条，ID 唯一、六字段齐全")
    return 0


if __name__ == "__main__":
    sys.exit(main())
