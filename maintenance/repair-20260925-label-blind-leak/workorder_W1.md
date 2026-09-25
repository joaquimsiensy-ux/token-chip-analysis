# 工单 W1：`label_lookup.py --blind-serial` 漏封「serial=False 但带 serial-offender 风险标记」的行（v2，吸收 codex 复核 r1 全部八条）

## 背景（大白话）
盲化模式（`--blind-serial` 或 `CHIP_BLIND_SERIAL=1`）的承诺是：A2–A3 阶段的公共输出**不含惯犯层信息**，真相封进 `sealed_serial_hits.jsonl`，A4 才揭盲。CLI 注释（`scripts/labels/label_lookup.py` 147–148 行）写明"serial 行整行剥离（其 risk_flags=serial-offender 会经 RISK 段泄露，故不能只隐 [SERIAL] 段）"。

但封存条件只看 `row.get('serial')`（151 行），而 `serial` 在 `labels_resolver.py` 216 行定义为 `category（去空白后）== SERIAL_CATEGORY('serial-actor')`，它不是"所有惯犯相关信息"的总标记。一条地址先由 `serial_actors.csv` 合并进库（category=serial-actor、risk_flags=serial-offender），又被人工 curation 改成别的类别（`add_labels.py` 151–164 行：合并来源与风险、覆盖分类）后，`serial` 变 False，但 `risk_flags='serial-offender'`、`source='serial-offenders+curation'` 仍在，**未被封存，相关字段继续进入公共输出**（JSON 174–177 行输出风险与来源；文本模式分段展示）。

## 真实复现（PYTHIA 案 2026-09-25，调度方只看聚合）
对 5,762 个候选跑 `--json --blind-serial`：5,762 行合法 JSON，23 行命中，其中 1 行 `{'category':'infra','tier':'exclude','serial':False,'risk_flags':'serial-offender','risk_partition':{'definitive':['serial-offender'],…},'sections':['risk','exclude'],'source':'serial-offenders+curation'}`。案内采集器的泄露检测判整批 `BLIND_OUTPUT_INTEGRITY_FAILED`。检测是对的，错在 CLI 封得不够。复核方只读聚合当前 8 个公共 `labels-*.csv`：按新判据命中 2,959 行，其中 10 行 category≠serial-actor、7 行 tier=exclude——即本单会让这 10 行在盲化期从公共输出消失。

## 调度方裁决（施工方照办，不必再议）
- **混合行整行封存**：曾带惯犯标记、后被 curation 改类别的行，在盲化期一律整行封存，主输出等同未命中；代价＝A2–A3 阶段暂时看不到它的设施身份/`no_merge`/`exclude`，A4 揭盲恢复。理由：盲化承诺优先于设施便利；"带历史标记"≠"当前确为惯犯"这一点由 A4 揭盲时人工判。CHANGELOG 要把这个代价写明。
- **本单只修 CLI**。复核确认的其他出口（`analyze_holdings.py` 192–224 同类漏封；`replay_edges.py` 64–79、`build_evolution.py` 107–121、`cluster.py` 200–242、`entity_identity_gate.py` 334–361 名称/类别直出；resolver `get/policy/resolve_file` 不盲化）**不在本单**，登记在本目录 README「后续单候选」。
- **`serial` 定义不改**（`cluster.py:130` 惯犯豁免等决策消费者依赖它）。
- `--unseal` 是显式揭盲入口，不受新函数约束；本单不动它。

## 改动范围
1. `scripts/labels/label_lookup.py`（主改）：新增模块级纯函数（建议名 `serial_marked(row) -> bool`，docstring 写"是否含须盲化的惯犯层结构化标记"），**精确匹配、不用子串**，任一成立即 True：
   - `row.get('serial') is True`；
   - `(row.get('category') or '').strip() == SERIAL_CATEGORY`（从 resolver import 常量）；
   - `risk_flags`：字符串按库里既有解析（`risk_flags.py` 的 `|` 分隔解析器或同规则 split+strip）后含 `'serial-offender'`；`None`/空串 → 不命中；若传入 list，逐项 strip 后精确匹配；**其他非空类型 → 视为命中（fail-closed，宁可多封）**。list 支持仅是本函数的输入兼容，不代表 resolver 或文本输出支持 list。
   - `source`：字符串按 `+` 拆分、逐项 strip 后含 `'serial-offenders'`。
   不额外加 `risk_partition`/`sections` 判据（它们由 risk_flags/category 派生）。
   盲化分支（现 150–157 行）改为 `if serial_marked(row):` 整行封存；封存记录格式不变；**单链模式**该地址进 `misses`（现有行为），`--chain all` 模式沿用现有"不加 misses"行为，不要改。JSON 与文本模式都消费过滤后的 `hits`，无需另写。
   同文件第 25 行注释"设施类输出不受影响"改为"不含惯犯标记的设施行不受影响"。
2. `scripts/labels/labels_resolver.py`、`--unseal` 路径、其他消费者：**不改**。
3. 新增 `scripts/tests/test_label_blind_seal.py` 并**加入 `scripts/tests/run_all.py` 的 `SUITE`**（它是显式清单，不是自动发现）。必须包含：
   a. `serial_marked()` 正反例：serial=True；category='serial-actor'（含带空白）；serial=False+risk_flags 字符串 `'serial-offender'`；多旗标 `'a|serial-offender|b'`；list 含 `'serial-offender'`；source `'serial-offenders+curation'`；**反例**：干净 infra 行；risk_flags `None`/`''`；相似子串 `'not-serial-offender'`、source `'non-serial-offenders'`（都不得命中）；缺字段；非法类型 risk_flags（如 dict）→ 命中。
   b. **集成测试（强制，不许降级）**：参照 `scripts/tests/test_cluster_quality.py` 34 行起的最小 CSV 构造与 64–107 行的盲化/揭盲用法，用 `tempfile.TemporaryDirectory` 造最小 labels 目录，放一条 `category=infra, tier=exclude, risk_flags=serial-offender, source=serial-offenders+curation` 的行和一条干净 infra 行；分别以 `--blind-serial --json`、`CHIP_BLIND_SERIAL=1`（环境变量模式）、文本模式、以及**非盲化对照**运行 CLI（`--sealed-dir` 指向临时目录）。断言：退出码 0；盲化 JSON 对混合行返回 `hit:false` 且**不带任何标签字段**（name/category/risk_flags/source/sections 均不出现）；干净 infra 行仍 `hit:true`；`sealed_serial_hits.jsonl` 含混合行原始信息；非盲化对照下混合行正常命中；封存内容不出现在 stdout。临时目录由测试自动清理，允许；**禁止读取任何真实案目录**。
4. 版本登记 9.2.0 → 9.2.1，按 `f78b5c4`（上次升版提交）同款四处：`VERSION`、`pyproject.toml`、`SKILL.md` 第 23 行版本元数据注释（允许改这一行，其余 SKILL 正文不动）、`CHANGELOG.md`（**顶部索引与首个详情条目都要写**，`test_version_consistency.py` 12–23 行会核；条目中文，写明混合行整行封存的代价与后续单登记）。历史条目/schema 版本/producer 历史理由里的旧版本号不要全局替换。
5. `references/`、`commands/` 正文不改；若发现 `references` 里描述盲化判据的句子与新判据矛盾，只把行号写进 done 报告。

## 施工前后要求
- 工作树干净再动手；git 即备份，不另做 .bak。
- 验证：新测试单独通过；`python3 scripts/tests/run_all.py` 与基线一致（已知环境红项逐项说明）；预提交三检（`.git/hooks/pre-commit`：`changelog_lint`、`docs_lint`、`env_check`）通过；`python3 scripts/tests/test_version_consistency.py` 通过。
- 不联网、不读任何真实案目录、不删文件（测试临时目录自动清理不算）。
- 完工写 `maintenance/repair-20260925-label-blind-leak/W1_done.md`：diff 摘要、测试用例清单与实际输出、run_all 结果、版本登记改动文件、commit 哈希（**只 commit 不 push**）。

## 验收判据
- `serial_marked()` 全部正反例通过，且不用子串匹配；
- 盲化分支只通过该函数决定封存，其余逻辑不变；第 25 行注释已改；
- 集成测试四种模式全部断言通过；
- run_all 与基线一致；9.2.1 四处登记齐全、版本一致性测试与 changelog_lint 通过；
- done 报告齐全。
