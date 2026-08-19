# 工单 U3b：单元3 盲审消化轮（本单元引入项修复 + 过度声称收窄）

> 基线 main=3ee1383（6.48.0）。盲审报告：本目录 blindreview_U3.md（总判 CONDITIONAL，1 BREACH/3 WEAK/4 NOTE/9 DEFENDED）。
> 本轮只消化**本单元引入**的债与**本单元造成的过度声称**。BREACH-01 的 SQD 侧代码修复不在本轮（盲审明确它非本单元引入、工单第 0 节把 csv_collector_receipt.py 划为不改），归第四单元候选——本轮只把那句字面涵盖 SQD 的过度声称文档收窄到诚实边界。
> 你（codex）只施工不 commit；报告写到本目录 workorder_U3b_done.md。

## 0. 边界

- **白名单**：
  ```
  scripts/evm/fetch_hypersync.py
  references/data-pipeline-evm-channels.md（CT-SEMANTIC-33/34 needle：evm-collector-run/v2、--collector-receipt 两字符串不得动）
  scripts/tests/test_csv_resume_collector_gate.py
  maintenance/closure-20260817-threeunit/workorder_U3b_done.md
  ```
- **明确不改**：csv_collector_receipt.py、fetch_sqd_evm.py、collector_history.py、channels_preflight.py（BREACH-01 与 W-01 反向守卫都归第四单元，本轮不碰这些）。
- 不 commit 不 push；不改版本号/CHANGELOG/SKILL.md。
- 先红后绿：每项先取红态实证再修绿。

## 1. 修复项

### R1〔关 W-02〕schema 常量收敛，消灭签发点字面量

- fetch_hypersync.py:282 的 `"schema": "evm-collector-run/v2"` 字面量改为引用 `COLLECTOR_RECEIPT_SCHEMA`（:38 已定义该常量）。本文件内 evm-collector-run/v2 字面量应只剩常量定义一处。
- channels_preflight.py:29 的副本本轮**不动**（跨文件常量统一归第四单元，避免动白名单外文件）；但在本文件 R1 改动处加一行注释指明"channels_preflight.py:29 另有一份 COLLECTOR_RECEIPT_SCHEMA 副本，升 schema 版本时两处必须同步"（防漏改的路标）。
- 红态：改前 `rg -n '"evm-collector-run/v2"' scripts/evm/fetch_hypersync.py` 有两处（常量定义 + :282 签发）；改后只剩常量定义一处。签发产物 schema 值不变（回归：现有 test_csv_resume_collector_gate 同哈希续采正例产出的 receipt schema 仍 == evm-collector-run/v2）。

### R2〔关 N-02〕怪写法改常规比较

- fetch_hypersync.py:148-151 的 `try: {COLLECTOR_RECEIPT_SCHEMA: True}[schema] except KeyError: raise ValueError(...)` 五行改为一行常规判断：`if schema != COLLECTOR_RECEIPT_SCHEMA: raise ValueError(f"前驱 receipt schema 必须是 {COLLECTOR_RECEIPT_SCHEMA}")`。:145-147 的 isinstance(schema,str) 前置检查保留（None/非串仍先拒，错误面不变）。
- 语义必须逐字等价：schema 非 evm-collector-run/v2 时仍 fail-closed 同文案。
- 红态：schema="evm-collector-run/v3"（未来版本）与 schema="foo" 改前后都拒且文案一致（等价性实证，非行为变更）。

### R3〔关 W-03〕--out 与 --receipt 同路径前置校验（对齐 SQD 范式）

- fetch_hypersync.py 的 receipt 分支（out_path 解析 :133 之后、正式采集之前）加校验：`a.receipt` 给出时，若 `os.path.realpath(a.out) == os.path.realpath(a.receipt)` → `ap.error("正式输出与 receipt 路径不得相同")`。范式对齐 fetch_sqd_evm.py:126。
- 红态：`--out x.csv --receipt x.csv`（同路径）改前以未捕获 FileExistsError 退出并残留 `.x.csv.tmp.<pid>` 临时件，改后被 ap.error 前置拒绝、无临时件残留。
- 注意仅当 --receipt 存在时校验（legacy 无 receipt 模式 --out 单独给不受影响）。

### R4〔关 BREACH-01 文档面 + W-01〕过度声称收窄 + 维护债申明

- references/data-pipeline-evm-channels.md:72 那句"自本版本起，同一 evm-collector-run/v2 receipt 的顶层 collector **保证**覆盖其全部 segments"收窄：明确该保证的**主语范围仅限 fetch_hypersync.py 签发的 CSV receipt**（同哈希续采闸+TOCTOU 冻结所覆盖者）；**同 schema 的 SQD 侧签发（csv_collector_receipt.py/emit_native_receipt）不在本保证内**——其 collector 哈希为写时实时值，采集期改档可致归属漂移，该缺口待第四单元收口，当前置信度=顶层自报。CT needle 两字符串所在行不得动，新增段落另起。
- 同处（或紧邻）补一句 W-01 维护债申明：方案 B 强制分段后，历史 collector 哈希从"续采瞬时依赖"升级为"每次 preflight 永久依赖登记在册"；采集器每次升级必须按维护纪律补登被替换版本（漏登=该版本采的存量段全部 preflight 被拒），反向断链守卫（"HEAD 前一版必须已登记"）待第四单元。
- 红态：docs_lint --all 改前后均 PASS（needle 完整、粗体配对、无断链）；人工核对新增段落如实、不与既有句冲突。

## 2. 维持与另立（报告确认知悉）

- **第四单元候选（本轮不施工，报告列清单交调度方）**：BREACH-01 SQD 侧 TOCTOU 收口（emit_native_receipt 收启动冻结哈希参数 + fetch_sqd_evm.py 入口冻结/写前复验/REVOKED 拒启动）、W-01 反向断链守卫（collector_history 加"HEAD 前一版必须已登记"测试）、W-02 跨文件常量统一（channels_preflight.py:29 副本）、N-01（SQD REVOKED 版本可跑完采集只消费侧兜底拒）。
- N-03（--receipt 缺席 --resume-receipt 被静默忽略）、N-04（prior receipt 双读窗口）：记录不修，不放大攻击面，报告确认知悉。

## 3. 完成标准

1. R1-R4 各红绿实证（R4 文档核对）；
2. `python3 scripts/tests/run_all.py` 除两个 loopback 外全绿（分母不变 117）；test_csv_resume_collector_gate 全绿+按需补 R2 等价性/R3 同路径用例；
3. git diff 只含白名单；docs_lint --all 过（needle 完整）；
4. 报告 workorder_U3b_done.md：逐项改动摘要+红绿实证+第四单元候选清单+未尽事项。
