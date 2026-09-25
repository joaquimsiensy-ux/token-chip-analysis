# 工单 W1：`label_lookup.py --blind-serial` 漏封「serial=False 但带 serial-offender 风险标记」的行（v1）

## 背景（大白话）
盲化模式（`--blind-serial` 或 `CHIP_BLIND_SERIAL=1`）的承诺是：A2–A3 阶段的公共输出**不含任何惯犯层信息**，真相封进 `sealed_serial_hits.jsonl`，A4 才揭盲。CLI 自己的注释（`scripts/labels/label_lookup.py` 第 147–148 行）也写明："serial 行整行剥离（其 risk_flags=serial-offender 会经 RISK 段泄露，故不能只隐 [SERIAL] 段）"。

但封存条件只看 `row.get('serial')`（第 151 行），而 `serial` 在 `labels_resolver.py` 第 216 行被定义为 `category == 'serial-actor'`。当标签库里一条地址先由 `serial_actors.csv` 合并进来（category=serial-actor、risk_flags=serial-offender），又被人工 curation 改成别的类别（例如 infra / tier=exclude）时，`serial` 变成 False，但 `risk_flags='serial-offender'`、`source='serial-offenders+curation'`、`risk_partition.definitive=['serial-offender']` 都还在，整行原样进公共输出——惯犯层信息就这样泄露了。

## 真实复现（PYTHIA 案 2026-09-25，调度方只看聚合不看地址）
对 5,762 个候选地址跑 `label_lookup.py --chain sol --file … --json --blind-serial --sealed-dir <临时目录>`：5,762 行合法 JSON，23 行 hit=true，其中 **1 行**字段为 `{'category': 'infra', 'tier': 'exclude', 'serial': False, 'risk_flags': 'serial-offender', 'risk_partition': {'definitive': ['serial-offender'], …}, 'sections': ['risk', 'exclude'], 'source': 'serial-offenders+curation'}`。案内采集器的泄露检测（匹配 `serial is True` / `category=='serial-actor'` / `'serial-offender' in risk_flags` / `'serial' in sections`）因此判整批 `BLIND_OUTPUT_INTEGRITY_FAILED`，A3 标签通道缺项。这个检测是对的，错在 CLI 封得不够。

## 改动范围
1. `scripts/labels/label_lookup.py`（主改）：把"这一行是否属于惯犯层"抽成一个模块级纯函数（建议名 `serial_marked(row)`），判据为**任一**成立：
   - `row.get('serial')` 为真；
   - `row.get('category') == 'serial-actor'`；
   - `'serial-offender'` 出现在 `row.get('risk_flags')`（字符串或列表都要覆盖）；
   - `'serial-offenders'` 出现在 `row.get('source')` 字符串里。
   盲化分支（现第 150–157 行）改用该函数决定整行封存；封存记录格式不变；主输出中该地址仍等同未命中（进 misses）。非 JSON 文本输出走的是同一个 `hits` 列表，自然一并覆盖，不要另写一套。
2. `scripts/labels/labels_resolver.py`：**不改** `serial` 的定义（A4 揭盲与其他消费者依赖它的现有语义）；如复核认为 `is_serial()` 也应认风险标记，另开工单，本单不动。
3. 新增测试 `scripts/tests/test_label_blind_seal.py`：直接对 `serial_marked()` 做正反例（serial=True；serial=False+risk_flags 字符串含 serial-offender；serial=False+risk_flags 为列表含 serial-offender；serial=False+source 含 serial-offenders；serial=False 干净行 → False；category=serial-actor → True）。再加一个端到端小用例：用临时 labels 目录/最小表让 resolver 命中一条"category=infra 但 risk_flags=serial-offender"的行，跑 `--blind-serial --json`，断言公共 stdout 里该地址 hit=false（或不出现命中字段）、`sealed_serial_hits.jsonl` 里有它。若构造最小表的成本过高，至少把纯函数用例做全，并在 done 报告里说明。测试要挂进 `scripts/tests/run_all.py` 的发现范围（看它怎么收集用例）。
4. 版本登记：patch 升一号（当前 9.2.0 → 9.2.1）。版本号出现的位置按仓库既有做法找（提示：`git log --oneline -3 -- CHANGELOG.md` 看上一次登记的 commit 改了哪些文件，`pyproject` 也含版本号），CHANGELOG 加一条中文条目，预提交钩子 `changelog_lint` 要过。
5. 不改 `references/`、`SKILL.md`、`commands/` 的正文；如 `references` 里有描述盲化判据的句子与新判据矛盾，只列出行号写进 done 报告，由调度方另单处理。

## 施工前后要求
- 工作树必须干净再动手；改前对 `label_lookup.py` 不必另做 .bak（git 即备份）。
- 验证：`python3 scripts/tests/run_all.py` 全绿（或与基线一致的已知环境红项，须逐项说明）；单独跑新测试；预提交三检通过。
- 不联网、不读任何案目录、不删文件。
- 完工写 `maintenance/repair-20260925-label-blind-leak/W1_done.md`：diff 摘要、新测试用例清单与输出、run_all 结果、版本登记改了哪些文件、commit 哈希（施工方只 commit 不 push）。

## 验收判据
- `serial_marked()` 六类正反例全对；
- 盲化分支只用它做封存判断，其余逻辑不变；
- run_all 与基线一致；版本 9.2.1 登记齐全、changelog_lint 过；
- done 报告齐全。
