你是收官审查员（工程 repair-20260925-label-blind-leak 的最后一道）。写权限**只限系统临时目录**；仓库 `/Users/uravvv/.claude/skills/token-chip-analysis` 下任何文件不得新建/修改/删除，不 git 写操作、不联网、不读真实案目录；结束时 `git status --porcelain` 须为空；报告只写在最终回复里。
目的不是重复盲审，而是回答一个问题：**原始缺陷是否真正被解决、有没有留下同类漏洞在本单声称的范围内。**
原始缺陷（来自真实案 PYTHIA，你不必也不能读它）：标签库里存在一行 `category=infra`（经 curation 改类别）、`risk_flags` 含 `serial-offender`、`source=serial-offenders+curation` 的记录；`label_lookup.py --blind-serial --json` 把它按普通设施行输出到公共 stdout（含 risk_flags/source），下游采集器的泄露检测判 BLIND_OUTPUT_INTEGRITY_FAILED。
请做：
1) 反例复现：在临时目录构造上述那一行（真实 15 列表头、合法 Base58 32 字节地址），用**父提交** `84006ae` 的 `label_lookup.py`（`git show 84006ae:scripts/labels/label_lookup.py` 写到临时目录，PYTHONPATH 指向仓库 `scripts/labels`）跑 `--blind-serial --json` 与文本模式，证明它确实泄露；再用 HEAD（`e1fa33f` 之后的当前 main）跑同样命令，证明整行封存、stdout 不含 `serial-offender`/`serial-offenders`/category。
2) 同族变体：`risk_flags` 里 serial-offender 夹在其他旗标中间（含空白）、`source` 只有 `serial-offenders`、`serial` 字段被上游以字符串 `"True"` 或整数 1 给出、`risk_flags` 为空但 `source` 含 serial-offenders——逐一跑 HEAD，说明哪些封、哪些不封，并判断不封的是否符合工单 `workorder_W1.md` 的精确匹配裁决（不是缺陷）。
3) 范围内遗漏：本单只修 CLI；`maintenance/repair-20260925-label-blind-leak/README.md`「后续单候选」登记了其他出口（analyze_holdings.py 等）。请核这些登记是否准确（文件与行号仍对得上），并检查 `scripts/` 下还有没有**未登记**的、同样只按 `row.get('serial')`/`serial is True` 做盲化封存判断的消费者（grep `blind`/`serial` 相关调用点），只登记不修。
4) 版本与文档：`references/analyze-workflow.md:88` 被施工方登记为「与整行封存判据不一致」的文档矛盾，核实并说明是否需要另单；CHANGELOG 9.2.1 条目对代价的描述是否与实际行为一致。
输出中文报告：P0/P1/P2 分级列出发现（无则写"无"），最后一行只写 PASS 或 FAIL（P0/P1 存在即 FAIL）。
