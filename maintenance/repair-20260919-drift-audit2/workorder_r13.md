# 工单 R13：v9.0.1 口径漂移与文档-代码不符 1 条纯文本修复 v2（吸收 codex 复核：:95 联动删无条件 exit 1、:96 改为「漏边优先 exit 2」，两行净减）

内容基线：`16f9c44`（R11 施工落地后的内容态；R12 两路 0 条无施工；施工 HEAD 可含 maintenance/ 提交，但 §0.1 差异校验须为空）。来源：盲审 R13a 1 条 minor（`blind_r13a_report.md`）；R13b 0 条（`blind_r13b_report.md`）。Fable 亲核两侧原文与代码属实。本单为纯文本修复，零代码改动；**锚为目标文件整行原文，按代码块内整行字面处理**。

## §0 施工纪律
0.1 开工先确认 `git status --short` 为空并记录施工 HEAD；`git diff --stat 16f9c44 HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md` 须为空，不符即停工汇报。
0.2 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）、`archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（§1.1 统计字节时 attic.md 只计大小不读内容；守卫脚本自身遍历文档属被测代码既有行为，允许并要求原样运行）；`maintenance/` 下只读本工程目录。
0.3 **白名单**：`references/data-pipeline-solana-capture.md`，以及新建 `maintenance/repair-20260919-drift-audit2/r13_done.md`。
0.4 删除 > 修改 > 新增；锚必须是目标文件整行原文，以 `grep -n -F -x` 核验恰 1 处且行号一致；不符停工；按整行替换，其他行不动。
0.5 不 commit、不 push、不部署；不改 `scripts/`、`commands-staging/`、`CHANGELOG.md`、两份 manifest。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` 合计 = 8789 不变；references 三组 glob（`references/*.md references/casebook/*.md references/labels/*.md`）合计 = 929092（基线 929105；两处整行替换按 UTF-8 字面模拟净变动 -13 B：:95 -10、:96 -3；实测数写入报告，须等于该值）。
1.2 守卫全绿：`python3 scripts/tests/docs_lint.py`、`docs_lint.py --all`、`casebook_lint.py`、`changelog_lint.py`、`test_contract_routes.py`、`test_sixlens_docs.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`、`test_commands_deploy_sync.py`，原始输出贴进 r13_done.md。
1.3 `git diff --stat` 只含 §0.3 白名单。

## §2 逐条施工（锚为整行，已由 Fable 逐行匹配验为恰 1 处；行号以 `16f9c44` 内容态为准）

### D1（R13a D1）销户抽样「样本无效任一命中即 exit 1」缺漏边优先 exit 2 的条件
`references/data-pipeline-solana-capture.md:96`。锚（整行）：
```
- **退出码**：0=抽样零漏边；2=发现漏边（对账 gate 语义，报告 missing_detail 带 tx 级证据）；1=运行失败/样本无效。**样本无效机器判据（批 D GPT-F-06 收口，任一命中即 exit 1）**：任一 getMultipleAccounts 批失败／深挖账户全部 fetch_failed／checked=0 且 closed>0／墙钟截断／undetermined 过半。
```
→（括注内「任一命中即 exit 1」改为「漏边优先 exit 2」，其余逐字不动）
```
- **退出码**：0=抽样零漏边；2=发现漏边（对账 gate 语义，报告 missing_detail 带 tx 级证据）；1=运行失败/样本无效。**样本无效机器判据（批 D GPT-F-06 收口，漏边优先 exit 2）**：任一 getMultipleAccounts 批失败／深挖账户全部 fetch_failed／checked=0 且 closed>0／墙钟截断／undetermined 过半。
```
依据 `scripts/solana/audit_closed_accounts.py:526-529`（`if events["missing"]: LEAK_FOUND/2` 先于 `elif invalid_reasons: INVALID_SAMPLE/1`）、`:71-74`（墙钟截断仅在 status 不属 `{INVALID_SAMPLE, LEAK_FOUND}` 时改 exit 1，保留 LEAK_FOUND/2）。`:97` status 契约本身无优先级断言，不动。

同文件 `:95` 联动（复核指出同款无条件 exit 1 断言）。`references/data-pipeline-solana-capture.md:95`。锚（整行）：
```
- **undetermined 语义（诚实纪律）**：深挖账户按结果分类 events_found / all_zero_delta / fetch_failed——后两类是"没查出来"不是"没事件"（高频中转户 delta 笔可能在 --deep-sigs 窗口外），不构成"无漏"证据；过半 undetermined＝样本无效（批 D GPT-F-06 起 exit 1，不再只告警）。
```
→（括注内删「exit 1，」，其余逐字不动）
```
- **undetermined 语义（诚实纪律）**：深挖账户按结果分类 events_found / all_zero_delta / fetch_failed——后两类是"没查出来"不是"没事件"（高频中转户 delta 笔可能在 --deep-sigs 窗口外），不构成"无漏"证据；过半 undetermined＝样本无效（批 D GPT-F-06 起不再只告警）。
```
依据同上：存在样本无效原因不等于最终必返回 INVALID_SAMPLE/1（漏边时为 LEAK_FOUND/2 且 `invalid_reasons` 保留）。CHANGELOG.md:604 的同款为 6.40.0 历史条目、scripts/ 内 docstring/注释同款均不在本单范围。

## §3 完成报告 `r13_done.md` 必含
①改前→改后 diff；②§1.1 字节实测（三组数）；③§1.2 各守卫原始输出；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
