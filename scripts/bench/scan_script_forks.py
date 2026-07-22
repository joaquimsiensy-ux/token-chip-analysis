#!/usr/bin/env python3
"""C7 脚本分叉盘点——扫工作目录各币案的私版 *.py，按同名分组+AST 归一化指纹找分叉。

痛点定位：每个案子都在案内 scripts/ 抄改一批脚本（make_charts.py 之流十几份），
谁改了什么、跟 skill 通用件差多远没人说得清。本脚本盘点：同名文件分组 → AST
归一化指纹（ast.parse 后剥 docstring，注释天然不入 AST，再 ast.dump 取 hash——
只改注释/docstring/空白的副本判同版）→ 每组报版本数/指纹种数/各指纹所在币目录/
最近 mtime/SKILL_ROOT/scripts 是否已有同名通用件（有则标"已有通用件仍存私版"，
是收编或清理的头号候选）。语法不合法的文件退化为原文 hash 并标注 syntax_error。

只读扫描+写一份 md 报告到工作目录根，不动任何案内文件。

用法:
  python3 scan_script_forks.py --workroot /path/to/工作目录 \
      [--skill-scripts SKILL_ROOT/scripts] [--out 报告.md] [--min-copies 2]
（来源：C7 小工程件，2026-07-22；457 份案内脚本实测）"""
import argparse
import ast
import datetime
import hashlib
import os
import sys
import warnings

warnings.simplefilter("ignore", SyntaxWarning)  # 被扫文件的坏转义等告警不进输出

EXCLUDE_PARTS = ("/data/", "venv", "site-packages", "node_modules", "__pycache__",
                 "skill-archive", "skill备份")


def strip_docstrings(tree):
    """剥掉 Module/ClassDef/FunctionDef/AsyncFunctionDef 的 docstring（body 首个字符串 Expr）。"""
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                node.body = body[1:] or [ast.Pass()]
    return tree


def fingerprint(path):
    """→ (指纹12位, 是否语法退化)。AST 归一化优先，语法不合法退化为原文 hash。"""
    try:
        src = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return "unreadable", True
    try:
        dump = ast.dump(strip_docstrings(ast.parse(src)), include_attributes=False)
        return hashlib.sha1(dump.encode()).hexdigest()[:12], False
    except (SyntaxError, ValueError, RecursionError):
        return "raw:" + hashlib.sha1(src.encode()).hexdigest()[:12], True


def case_of(path, workroot):
    """文件 → 所属币目录名（workroot 下第一层）。"""
    rel = os.path.relpath(path, workroot)
    return rel.split(os.sep)[0]


def main():
    ap = argparse.ArgumentParser(description="C7 脚本分叉盘点（同名分组+AST 指纹）")
    ap.add_argument("--workroot", required=True, help="各币分析产物的工作目录根")
    ap.add_argument("--skill-scripts",
                    default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."),
                    help="skill 通用脚本根（默认=本脚本上级 scripts/）")
    ap.add_argument("--out", default=None,
                    help="报告路径（默认=workroot/脚本分叉盘点_<今天>.md）")
    ap.add_argument("--min-copies", type=int, default=2, help="主表最少份数（默认 2）")
    a = ap.parse_args()

    workroot = os.path.abspath(a.workroot)
    if not os.path.isdir(workroot):
        sys.exit(f"[fatal] workroot 不存在: {workroot}")
    skill_names = set()
    for r, _, fs in os.walk(os.path.abspath(a.skill_scripts)):
        if "__pycache__" in r:
            continue
        skill_names |= {f for f in fs if f.endswith(".py")}

    groups = {}  # basename -> [(path, fp, degraded, mtime, case)]
    n_scanned = n_excluded = 0
    for r, dirs, fs in os.walk(workroot):
        dirs[:] = [d for d in dirs if not any(
            x in (os.path.join(r, d) + "/") for x in EXCLUDE_PARTS)]
        for f in fs:
            if not f.endswith(".py"):
                continue
            p = os.path.join(r, f)
            if any(x in p for x in EXCLUDE_PARTS):
                n_excluded += 1
                continue
            n_scanned += 1
            fp, degraded = fingerprint(p)
            groups.setdefault(f, []).append(
                (p, fp, degraded, os.path.getmtime(p), case_of(p, workroot)))

    today = datetime.date.today().isoformat()
    out = a.out or os.path.join(workroot, f"脚本分叉盘点_{today}.md")
    multi = {k: v for k, v in groups.items() if len(v) >= a.min_copies}
    order = sorted(multi.items(), key=lambda kv: (-len(kv[1]),
                                                  -len({x[1] for x in kv[1]})))
    md = [f"# 脚本分叉盘点（{today}）",
          f"- 扫描根：`{workroot}`（排除 {', '.join(EXCLUDE_PARTS)}）",
          f"- 命中 .py {n_scanned} 份（另排除 {n_excluded}）；同名组 {len(groups)} 个，"
          f"≥{a.min_copies} 份的 {len(multi)} 个",
          f"- 指纹口径：AST 剥 docstring 归一化（只改注释/docstring 判同版）；"
          f"`raw:` 前缀=语法不合法退化原文 hash",
          "",
          "## 同名多份组（按份数降序）",
          "| 脚本名 | 份数 | 指纹种数 | 最近改动 | 通用件 | 各指纹分布（币目录） |",
          "|---|---|---|---|---|---|"]
    for name, rows in order:
        fps = {}
        for p, fp, deg, mt, case in rows:
            fps.setdefault(fp, []).append(case)
        latest = datetime.date.fromtimestamp(max(r[3] for r in rows)).isoformat()
        flag = "**已有通用件仍存私版**" if name in skill_names else "无"
        dist = "; ".join(
            f"`{fp[:8]}`×{len(cs)}({','.join(sorted(set(cs))[:6])}"
            + ("…" if len(set(cs)) > 6 else "") + ")"
            for fp, cs in sorted(fps.items(), key=lambda kv: -len(kv[1])))
        deg_n = sum(1 for r in rows if r[2])
        if deg_n:
            dist += f"；⚠语法退化 {deg_n} 份"
        md.append(f"| {name} | {len(rows)} | {len(fps)} | {latest} | {flag} | {dist} |")
    singles = [k for k, v in groups.items() if len(v) < a.min_copies]
    dup_in_skill = [n for n, rows in order if n in skill_names]
    md += ["",
           "## 摘要",
           f"- 单份脚本 {len(singles)} 个（未列主表）",
           f"- 已有通用件仍存私版的组：{len(dup_in_skill)} 个"
           + (f" —— {', '.join(dup_in_skill[:15])}" + ("…" if len(dup_in_skill) > 15 else "")
              if dup_in_skill else ""),
           "- 处置建议：指纹种数=1 的多份组 → 纯复制，直接删私版引通用件；"
           "指纹种数>1 → diff 最新版与通用件，把私版增量收编进 skill 后清理。"]
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"[done] {n_scanned} 份 / {len(groups)} 组 / 多份组 {len(multi)} -> {out}")
    for name, rows in order[:8]:
        print(f"  top: {name} ×{len(rows)}（指纹 {len({r[1] for r in rows})} 种）")


if __name__ == "__main__":
    main()
