# 工单 U1b：单元1 盲审消化轮（2 BREACH + 6 WEAK 修复）

> 基线 main=a2294e2（6.46.0）。盲审报告：本目录 blindreview_U1.md（38 向量：2 BREACH/16 WEAK/20 DEFENDED），先读它的 V-31/V-01/V-17/V-18/V-28/V-23/V-36/V-06/V-12/V-07 各节与 §8 修复清单。
> 攻击复现材料在 /tmp/blindreview-u1/（atk.py 等，只读参考，可用来先红取证）。
> 你（codex）只施工不 commit；报告写到本目录 workorder_U1b_done.md。

## 0. 边界

- **白名单**：
  ```
  scripts/lib/time_spotcheck.py         scripts/lib/anchor_point_contract.py
  scripts/lib/producer_history.py       scripts/lib/receipt_validate.py（仅注释/docstring）
  scripts/report/shared_release_receipt.py
  scripts/tests/invariant_manifest.json
  scripts/tests/test_anchor_plan_v3.py  scripts/tests/test_time_spotcheck.py
  maintenance/closure-20260817-threeunit/workorder_U1b_done.md
  ```
- 不 commit 不 push；不改版本号/CHANGELOG。
- 先红后绿：每项修复先用盲审攻击向量（或等价 fixture）取红态实证，修后转绿。
- kind 文案与 v2 存量兼容不得回归：NES 三份存量深验+重放必须继续全绿（修完后用 U1 报告 §5 的三条命令自验）。

## 1. 修复项（按优先级）

### R1〔关 V-31 BREACH〕plan/receipt 读入字节规范性闸——拒重复 JSON 键

- 新增共享 helper（建议放 anchor_point_contract.py，如 `reject_duplicate_keys_object_pairs_hook` 或 `strict_json_loads`）：`json.loads(..., object_pairs_hook=...)`，同一对象内重复键即 `ValueError`（信息含键名）。
- 接线到 anchor plan 消费链的**全部读入点**：time_spotcheck.load_validated_plan 的 plan 与 receipt 读入（:78-79 附近）、shared_release_receipt._validated_time_plan_authority 的 plan/plan_receipt 读入、执行器 CLI 路径若另有独立 json.loads 一并接。`rg -n "json.loads" scripts/lib/time_spotcheck.py scripts/report/shared_release_receipt.py` 逐处判断：属 anchor plan/receipt 消费的接钩子；其他 JSON（transcript/output 等）**不动**——本闸范围仅 anchor plan 链，勿全库扩散。
- 红态实证：用 /tmp/blindreview-u1/ 的 V-31 攻击件（或重构造：某余额点前置重复 `balance_block_source: "final_block"` 键+重签 receipt），修前全链 ACCEPTED，修后在读入层被拒。

### R2〔关 V-01 BREACH〕protocol 按被验 plan schema 动态传入

- time_spotcheck.py:82-83 与 shared_release_receipt.py:964-965 现把 protocol 硬编码 `"anchor-plan/v2"`。改为：先读 plan.schema（在 schema 白名单校验之后），`historical_producer_hashes("scripts/lib/anchor_plan.py", plan_schema)` 用被验 plan 的实际 schema。效果：v3 plan 的历史集为空（登记表现无 v3 条目）→ 只认当前哈希；v2 plan 才认 v2 历史。
- 注意执行顺序：validate_receipt 需要 allowed_producer_hashes，而 plan.schema 要先可信读取——plan 读入（经 R1 严格解析）→ schema ∈ {v2,v3} 白名单校验 → 按 schema 取历史集 → validate_receipt。若现行顺序是先 validate 后读 plan，按此重排并在报告说明。
- 红态实证：v3 plan 挂 `e5168a…` producer 哈希（重签 receipt），修前 ACCEPTED（盲审已证），修后拒。

### R3〔关 V-17/V-18〕分派 fail-open 转显式白名单 + 字面量收敛

- 三处 `if schema==v3: … else: <v2 语义>` 改为 `if v3 / elif v2 / else raise ValueError(unsupported schema)`：time_spotcheck.classify、time_spotcheck.balance_query_block、shared_release_receipt._plan_point（V-18 点名发布闸这处失败模式静默且靠 kind 恰好答对）。
- 发布闸的裸字面量 `"anchor-plan/v3"`（_plan_point 处）与 time_spotcheck.PLAN_SCHEMA 收敛到单一常量：统一从 anchor_point_contract.V3_SCHEMA 取（time_spotcheck.PLAN_SCHEMA 可保留但赋值改为 `V3_SCHEMA` 引用；SUPPORTED_PLAN_SCHEMAS 同理引用常量）。
- 红态实证：构造 schema="anchor-plan/v9" 的 plan 直调三函数，修前走 v2 语义（或静默），修后三处 ValueError。

### R4〔关 V-28〕v2 分支显式拒带 balance_block_source 的点

- v2 语义路径（classify 的 v2 分支、balance_query_block 的 v2 分支、_plan_point 的 v2 分支、_validate_probe_blocks 的 v2 分支）遇 point 含 `balance_block_source` 键即 ValueError（"v2 plan point carries v3 machine field"）。
- 盲审已实测三份 NES 存量件均无此键，零误伤；修后仍复跑 NES 三命令确认。
- 红态实证：v2 plan 的点塞 `balance_block_source: "final_block"`（说谎字段），修前被 v2 路径无视（文案兜底答对），修后拒。

### R5〔关 V-23〕枚举判定前收类型

- balance_block_source_of 的枚举判定（`source not in BALANCE_BLOCK_SOURCES`）前加 `isinstance(source, str)` 检查，不可哈希值（如 list）从 TypeError 收成 ValueError 统一错误面。
- 红态：source=["day_end_block"] 修前 TypeError 修后 ValueError。

### R6〔关 V-36〕单源对账守卫恢复全局语义

- test_time_spotcheck.py 的单源对账（U1 改在 :309 附近，加了 `script == EXPECTED_PLAN_PRODUCER` 限定使其检测不到第二个 anchor-plan producer）恢复全局语义：全 manifest 按 schema 过滤应恰一个 producer。
- time_spotcheck 自身 producer 面（它登记了 v3+time receipt 导致当时被迫削窄）改用 invariant_manifest.json 的 `exceptions` 机制显式豁免——先读 scripts/tests/invariant_scan.py 的 exceptions 语义照规范登记；若 exceptions 机制语义不适配（只服务 scan 不服务本测试），则在本测试内建显式豁免清单（带注释说明豁免理由），总之"守卫全局语义+豁免显式化"，不许静默削窄。
- 红态：往 manifest 塞第二个假 anchor-plan/v3 producer 条目（临时 fixture 内存态，勿落盘），修后守卫抓到；U1 现状守卫抓不到（盲审 V-36 已证）。

### R7〔关 V-06〕producer_history status 枚举守卫

- test_anchor_plan_v3.py 的登记表结构守卫加断言：每条 status ∈ {"ACTIVE", "REVOKED"}（拼写走样即红）。producer_history.historical_producer_hashes 本体也可在遍历时对未知 status 抛错（防运行时静默），二选一或都做，报告说明。

### R8〔关 V-12〕登记表 commit 形态统一全哈希

- producer_history.py 第二条 commit "0ec6d1e" 换全哈希（`git rev-parse 0ec6d1e` = 0ec6d1e2365c339d200fc26d17344f962fbdb7a9）；结构守卫加 commit 全哈希格式断言（40 位十六进制）。

### R9〔关 V-07〕参数契约注释

- receipt_validate.validate_receipt 的 allowed_producer_hashes 参数 docstring 注明："调用方必须传与 receipt.producer.path 对应脚本的登记哈希集；本函数不校验 script 对应性，对应性由调用方负责"（仅注释，不改逻辑）。

## 2. 维持与遗留（不施工，报告确认知悉即可）

- V-04/V-11/V-20/V-24/V-34 维持（调度方裁决在案）；V-32/V-33 发布闸深度差=旧账另立，本轮不动发布闸校验深度（R3 只动其分派结构）。

## 3. 完成标准

1. R1-R9 各红态实证+修后绿；
2. NES 三份存量深验+dry-run 重放复跑全绿（U1 报告 §5 三命令）；
3. `python3 scripts/tests/run_all.py` 除两个 loopback 外全绿；
4. git diff 只含白名单；
5. 报告 workorder_U1b_done.md：逐项 R1-R9 改动摘要+红绿实证+NES 复跑结果+未尽事项。
