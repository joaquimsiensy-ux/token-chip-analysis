# 工单 W2 复核提示词（只读）
## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放在最终答复消息里**（不要只 print 到 stdout）。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，基线＝HEAD（须含 `cc6298b`）。
3. 每条意见须给出可直接替换进工单的原文（含行号/锚），并标注「必改/建议/存疑」；结尾给汇总表（条目/等级/依据文件:行）。你复核的是**工单定形**，不是施工；发现工单事实与源码不符的地方优先级最高。
首行固定 `# 工单W2复核：通过` 或 `# 工单W2复核：退回`。

## 任务
复核 `maintenance/repair-20260924b-sol-stage1-speed/workorder_W2.md`（v1；背景先读同目录 `README.md`，并对照 `workorder_W1.md`/`workorder_W4.md`/`workorder_W3.md` 的设计——W2 是收官单，其文档描述必须与前三单一致）。逐条审：
a) 事实段 ①–⑤ 亲核：`--known-map` 只在非 resume 加载（行号）；资产目录现状；文档三处锚整行；版本四处；producer_history 两脚本现有条目的协议集合（逐条列出）。
b) `find-known-map` 设计：轻校验项是否够/是否多余；排序键是否合理（重叠优先 vs 新版本优先 vs refuted 数量）；默认搜索目录相对脚本定位的写法；stdout JSON 形态；exit 码；与 `_dry_run`/`--known-map` 现有校验是否重复；测试可行性。
c) 文档硬性句（2.2/2.3/2.4）是否与 W1 定义的字段名/子命令/状态名一致、有无夸大（例如「不拉 Helius」只对继承 slot 成立）；`references/` 字节预算与 `docs_lint`/`test_g3_docs_guards` 约束；`commands-staging` 与 `~/.claude/commands` 同步由调度方做是否需要在工单标注。
d) 版本档位 9.2.0 是否恰当；CHANGELOG 索引行长度与详细段格式对照 `CHANGELOG.md:13/:104-110`；`changelog_lint.py` 规则（读源码）对新条目的要求。
e) producer_history 追加流程（sha/commit 由调度方填 v2）是否与 `producer_history.py` 顶部纪律一致；是否需要同时更新 `invariant_manifest.json`（它登记 schema 与脚本关系，不钉 sha——核实）。
f) 白名单/不改清单遗漏；W2 是否漏掉任何 W1/W3/W4 留给它的文档句。
