#!/usr/bin/env python3
"""B5 复盘草稿生成器——从案目录工作底稿启发式抽取五类复盘候选条目，省打字。

定位：交付后复盘（新数据源/新坑/方法修正/脚本变更/遗留 TODO 五类）此前全靠人工
翻 findings.md 回忆。本脚本按关键词启发式把底稿逐行归类成草稿骨架，每条附出处
（文件:行号）供回看原文。**只是草稿不是成品**：召回优先、允许误报，人工删改比
从零写快；空类留"（人工补）"占位，别当"此类无事"的证据。

素材来源：案目录下 findings.md、retro_notes.md、报告.md（存在才读）+ --extra 附加
文件（可多个）。只读，不改案目录任何文件；输出默认写当前目录（--out 可指定）。

用法:
  python3 retro_draft.py <案目录> [--extra 文件 ...] [--out retro_draft.md] [--max-per-cat 40]
（来源：B5 小工程件，2026-07-22；GOAT 案 findings 实测通过）"""
import argparse
import datetime
import os
import re
import sys

# 五类 → 关键词（子串匹配为主；命中即候选，一行可入多类）
CATEGORIES = [
    ("新数据源", ["端点", "API", "api", "数据源", "通道", "接口", "直连", "代理", "限速",
                  "rpm", "RPS", "rps", "credits", "免 key", "免key", "免费层", "subgraph",
                  "RPC", "rpc", "hypersync", "HyperSync", "SQD", "BigQuery", "Dune",
                  "Helius", "Alchemy", "solscan", "bscscan", "etherscan"]),
    ("新坑",    ["坑", "翻车", "误报", "报错", "失败", "超时", "429", "403", "402", "404",
                  "断供", "断裂", "事故", "陷阱", "⚠", "注意", "谨防", "假阳", "假阴",
                  "错判", "漏检", "编造", "不可用", "被拦", "被墙", "brownout", "限流"]),
    ("方法修正", ["修正", "更正", "改判", "翻案", "推翻", "纠偏", "口径", "重判", "作废",
                  "校准", "改写", "REFUTED", "refuted", "复核", "裁决", "降级", "升级判",
                  "重新定性", "补认", "补录"]),
    ("脚本变更", ["脚本", ".py", "新增", "新建", "重写", "重构", "参数", "工程件",
                  "v2", "v3", "--", "函数", "flag", "CLI"]),
    ("遗留 TODO", ["TODO", "todo", "待", "下次", "遗留", "未完成", "未验证", "待验收",
                   "待补", "待定", "未登记", "进行中", "下一步", "待证"]),
]
MAX_LINE = 180  # 单条截断长度


def harvest(path):
    """文件 → [(行号, 文本)]，跳过空行与纯分隔线。"""
    out = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                t = line.strip()
                if t and not re.fullmatch(r"[-=#|\s]+", t):
                    out.append((i, t))
    except OSError as e:
        print(f"[warn] 读不了 {path}: {e}", file=sys.stderr)
    return out


def main():
    ap = argparse.ArgumentParser(description="B5 复盘草稿生成器（五类关键词启发式归类）")
    ap.add_argument("case_dir", help="案目录（读 findings.md / retro_notes.md / 报告.md）")
    ap.add_argument("--extra", nargs="*", default=[], help="附加素材文件（任意文本）")
    ap.add_argument("--out", default="retro_draft.md",
                    help="输出路径（默认当前目录 retro_draft.md，不写案目录）")
    ap.add_argument("--max-per-cat", type=int, default=40, help="每类最多列几条（默认 40）")
    a = ap.parse_args()

    if not os.path.isdir(a.case_dir):
        sys.exit(f"[fatal] 案目录不存在: {a.case_dir}")
    sources = [os.path.join(a.case_dir, n)
               for n in ("findings.md", "retro_notes.md", "报告.md")
               if os.path.exists(os.path.join(a.case_dir, n))]
    sources += [p for p in a.extra if os.path.exists(p)]
    missing = [p for p in a.extra if not os.path.exists(p)]
    for p in missing:
        print(f"[warn] --extra 文件不存在，跳过: {p}", file=sys.stderr)
    if not sources:
        sys.exit(f"[fatal] {a.case_dir} 下无 findings.md/retro_notes.md/报告.md，也无有效 --extra")

    buckets = {name: [] for name, _ in CATEGORIES}
    n_lines = 0
    for src in sources:
        rel = os.path.basename(src)
        for lineno, text in harvest(src):
            n_lines += 1
            for name, kws in CATEGORIES:
                if any(k in text for k in kws):
                    buckets[name].append((rel, lineno, text))

    case = os.path.basename(os.path.abspath(a.case_dir))
    today = datetime.date.today().isoformat()
    md = [f"# 复盘草稿 · {case}（{today} 生成，B5 启发式，人工删改后用）",
          f"素材：{', '.join(os.path.basename(s) for s in sources)}（共 {n_lines} 行）",
          "",
          "> 用法：每条是候选不是结论——保留则改写成一句话复盘，无关则整行删掉；",
          "> 空类的『（人工补）』必须人工确认后要么补要么删，不许原样留在成品里。",
          ""]
    for name, _ in CATEGORIES:
        rows = buckets[name]
        md.append(f"## {name}（候选 {len(rows)} 条）")
        if not rows:
            md.append("- （人工补）")
        else:
            for rel, lineno, text in rows[: a.max_per_cat]:
                t = text if len(text) <= MAX_LINE else text[:MAX_LINE] + "…"
                md.append(f"- [ ] {t}  ⟵ `{rel}:{lineno}`")
            if len(rows) > a.max_per_cat:
                md.append(f"- …（另有 {len(rows) - a.max_per_cat} 条超出上限，需要就调 --max-per-cat）")
        md.append("")
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    stat = " / ".join(f"{n}:{len(buckets[n])}" for n, _ in CATEGORIES)
    print(f"[done] {stat} -> {a.out}")


if __name__ == "__main__":
    main()
