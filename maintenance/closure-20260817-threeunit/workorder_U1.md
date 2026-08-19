# 工单 U1：anchor-plan v2→v3 机器字段正向白名单 + producer 历史哈希登记

> 三单元收口工程第 1 单元。基线 main=0ec6d1e（v6.45.1）。
> 你（codex）只施工不 commit；完成后写施工报告到本目录 `workorder_U1_done.md`。
> 上游计划：本工单是唯一施工依据，冲突时以本工单为准。

## 0. 边界（违规即返工）

- **白名单（只允许改/建这些文件，超出即违规）**：
  ```
  scripts/lib/anchor_plan.py            scripts/lib/anchor_selection.py
  scripts/lib/anchor_point_contract.py  scripts/lib/time_spotcheck.py
  scripts/lib/receipt_validate.py       scripts/lib/producer_history.py（新建）
  scripts/report/shared_release_receipt.py
  scripts/tests/invariant_manifest.json
  scripts/tests/test_anchor_plan_v3.py（新建）
  scripts/tests/test_time_spotcheck.py  scripts/tests/test_r9_batch1_boundaries.py
  scripts/tests/run_all.py（仅加注册行）
  maintenance/closure-20260817-threeunit/workorder_U1_done.md（施工报告）
  ```
- **不 commit、不 push**（调度方代 commit）。
- **不改版本号/CHANGELOG/SKILL.md**（调度方收口时做）。
- **先红后绿**：每个新增负测先证明"在旧代码或未加闸状态下会漏过/在新代码下正确拒绝"，红态实证（命令+输出摘要）写入施工报告。
- **kind 中文文案一字不改**（含 `LEGACY_FINAL_BLOCK_EDGE_KIND = "门槛±10% 边缘地址"` 的值），只让它退出语义判定。存量 v2 重放对文案字面敏感。

## 1. 背景（一句话）

锚点计划（anchor plan）里"余额点查哪个块"目前靠 kind 中文文案精确匹配推断（改措辞即误拦），且存量 receipt 的 producer 哈希校验在当前 HEAD 已断（`producer hash mismatch`）——本单元升 schema v3 加机器字段，并建 producer 历史登记表修复存量深验。

## 2. 施工内容（带行号，行号基于 HEAD=0ec6d1e）

### 2.1 v3 契约：正向白名单 + 严格 XOR 点型

v3 plan（`schema == "anchor-plan/v3"`）中每个点必属且仅属下列两类之一：

- **balance 型**（判据：有 `expected_balance_raw` + `addr`）：
  - 必带 `balance_block_source`，枚举仅 `"day_end_block" | "final_block"`；
  - 禁止 `tx`/`block`/`expected_value_raw` 键；
  - `"day_end_block"` 分支：必有合法 int `day_end_block` 键；
  - `"final_block"` 分支：只允许出现在 forced_points；禁止 `day_end_block`/`block`/`tx` 键；`day` 必须 == `date_range[-1]`（保留现行自洽约束）；
- **tx 型**（判据：有 `tx` + `expected_value_raw`）：
  - 禁止 `addr`/`day_end_block`/`expected_balance_raw`/`balance_block_source` 键；
- 两类判据都不命中、或同时命中 ⇒ 拒（现行 classify 在 time_spotcheck.py:193-208 是 balance 优先 if/elif，会吞混合点；v3 收成互斥硬闸）。

### 2.2 版本分派

- `PLAN_SCHEMA` 升 `"anchor-plan/v3"`——**两处定义都改**：anchor_plan.py:45 ＋ time_spotcheck.py:59。
- anchor_point_contract.py 新增 v3 判定入口（纯机器字段，建议 `balance_block_source_of(point, family, plan)`：按 2.1 白名单校验后返回块源枚举值或抛错）；**保留** `is_legacy_final_block_edge_point`（:18）给 v2 存量。
- 四处消费方按 `plan["schema"]` 分派（v3 走机器字段，v2 走现行文案兼容路径，v2 行为零变化）：
  - anchor_plan.py:51-52（`_validate_probe_blocks` 签发侧）
  - time_spotcheck.py:218-219（`balance_query_block` 执行侧）
  - shared_release_receipt.py:876-877（`_plan_point` 发布深验）＋ :887-888（tx 反向校验）
  - time_spotcheck.py:202-204（classify 反向校验）
- 存量 v2 plan/receipt 一律不重签。

### 2.3 receipt 配对矩阵

`RECEIPT_SCHEMA = "anchor-plan-receipt/v2"`（anchor_plan.py:46）**不升版**。shared_release_receipt.py 两处硬编码改配对矩阵：

- :957-958 `_require(plan.get("schema") == "anchor-plan/v2", ...)` → 接受 `{"anchor-plan/v2", "anchor-plan/v3"}`；
- :987 `_require(plan_receipt.get("plan_schema") == "anchor-plan/v2", ...)` → 要求 `plan_receipt.plan_schema == plan.schema`（且 ∈ 同一枚举）；
- 其余组合全拒。

### 2.4 语义重放 schema-aware（v2 存量全绿是硬线）

`validate_semantic_replay`（time_spotcheck.py:143-190）：生成器只维护一套（产 v3 形态点）。重放被验 plan 时：

- 被验 plan 是 v3：重算结果直接 `_point_multiset` 比对（现行 :181-189 逻辑）；
- 被验 plan 是 v2：把**重算结果**投影回 v2 形态再比对。投影三纪律：
  1. **只投影重算结果，绝不投影被验 plan**（否则等于替攻击输入擦字段）；
  2. 投影前先按 2.1 XOR 契约断言重算每个点字段形态合法，**然后**剥离 `balance_block_source`——禁止无条件 `dict.pop("balance_block_source", None)` 式静默剥离（会掩盖生成器漏字段）；
  3. 投影只剥 `balance_block_source` 这一个键，其余字节不动。

### 2.5 生成侧

anchor_selection.py：

- `point()` 函数（:253-260）返回 dict 加 `"balance_block_source": "day_end_block"`；
- 边缘点（:313-319）加 `"balance_block_source": "final_block"`；
- tx 型点（:272-277 最大单笔、:300-306 交界块）不加。

### 2.6 producer 历史哈希登记（新模块）

新建 `scripts/lib/producer_history.py`，与 scripts/evm/collector_history.py **同构**（读它作为模板）：

- 条目式六字段：`script/sha256/commit/protocol/status/reason`；
- 登记纪律（模块 docstring 写明）：每条必须 `git show <commit>:scripts/lib/anchor_plan.py | shasum -a 256` 可复现；脏工作树产物不得入表；
- `historical_producer_hashes(script, protocol)` 查询函数：过滤语义 =「status==ACTIVE ∧ script 匹配 ∧ protocol 匹配，再减去全表任何 REVOKED 同哈希」（REVOKED hash-wide 否决，跨 protocol 不缩窄）；
- **放 lib/ 不放 evm/**（receipt_validate 在 lib 层，不得反向 import evm 层）；
- 登记两条（protocol 均为 `"anchor-plan/v2"`，commit 用 git log 沿 `scripts/lib/anchor_plan.py` 历史逐版算哈希考证，考证不出就在报告中说明并停下，**不许猜**）：
  1. `e5168a455d53bb5163722ea7f2a67c42b20bd3dd8ef6c3ae5e588014842cc1d9`（NES 案三份 receipt 的签发者版本）；
  2. `1a461169f0770c7a4b8d74eb185f68ae225906cf1ec49b9ad04154e340ebebb2`（HEAD=0ec6d1e 的现版本——本次施工把它替换掉，按维护纪律同单元补登，commit 记 `0ec6d1e`）。

消费端接线：

- `receipt_validate.validate_receipt`（scripts/lib/receipt_validate.py，producer 校验在 :101-110）加**可选参数** `allowed_producer_hashes=None`：None 时行为与现行完全一致（仅认当前脚本哈希）；传入集合时，producer.sha256 ∈ {当前} ∪ 集合 即放行。**默认路径语义零变化**——其他回执类型不得被放宽；
- time_spotcheck.py:77（`load_validated_plan` 里的 `errors = validate_receipt(receipt)` 调用；:75 是 plan 读取行，勿混）传入 `historical_producer_hashes("scripts/lib/anchor_plan.py", "anchor-plan/v2")`；〔行号勘误 2026-08-17：原工单误写 :75，codex 开工门禁抓获，已核实真身 :77〕
- shared_release_receipt.py:948 附近 `repo_ref_ok()` 对 anchor plan producer 的校验同策略（当前 ∪ 登记历史）；
- **不得凭 receipt 自报哈希放行，只认登记表**。

### 2.7 invariant_manifest.json 区别处理

- :88 producer 条目（scripts/lib/anchor_plan.py）schema 串 `anchor-plan/v2` **替换**为 `anchor-plan/v3`（producer 只产 v3）；
- :366（consumer time_spotcheck.py）与 :476（consumer shared_release_receipt.py）**保留 v2 并新增 v3**（还要继续消费存量 v2）；
- 新模块 producer_history.py 若被 invariant_scan 扫出新的 producer/consumer/atomic_write 面，按 `python3 scripts/tests/invariant_scan.py --dump-actual` 输出如实登记；
- test_time_spotcheck.py:305-312 的单源对账（按 `anchor-plan/v2` 过滤 producers）同步改为按 v3（或 v2+v3 集合语义，与 manifest 实改保持一致）。

### 2.8 现有测试必要修正（仅限这两处，其余测试不许动）

- test_r9_batch1_boundaries.py:206：`assert plan["schema"] == "anchor-plan/v2"` → v3（真实 producer 现产 v3）；
- test_time_spotcheck.py 中依赖 v2 串的断言（:118/:136/:309 等）逐条检查：属"构造 v2 fixture 验兼容路径"的保留；属"断言现产 schema"的改 v3。报告逐条说明改/不改理由。

## 3. 测试矩阵（新文件 scripts/tests/test_anchor_plan_v3.py，并在 run_all.py 注册）

| # | 用例 | 期望 |
|---|---|---|
| 1 | v3 正例：新签发 plan 全点带合法 balance_block_source，过签发→语义重放→发布深验形态校验全链 | PASS |
| 2 | balance_block_source 枚举外值（"foo"） | 拒 |
| 3 | `final_block` 源出现在 matrix_points | 拒 |
| 4 | `final_block` 分支携带 day_end_block/block/tx 任一键 | 拒 |
| 5 | `day_end_block` 分支缺块号或块号非 int | 拒 |
| 6 | tx 点携带 balance_block_source | 拒 |
| 7 | balance 型点缺 balance_block_source（v3 下） | 拒 |
| 8 | 文案免疫：改 kind 文案后**重新产 plan+对应重放**，v3 全链判定不变（不得篡改已签件后要求旧件通过） | PASS |
| 9 | v2 存量回归：v2 形态 fixture plan（含边缘点）走签发校验+语义重放+发布深验形态校验 | 全绿 |
| 10 | v2 重放投影正确性：重算结果按 XOR 断言后剥字段与 v2 声明逐点一致；人为让生成器漏字段时投影断言先炸 | PASS |
| 11 | XOR 负例：balance 点带 tx 键／tx 点带 balance_block_source／混合命中点 | 全拒 |
| 12 | producer 历史：未登记哈希拒；e5168a 登记后放行；REVOKED 压过 ACTIVE；默认路径（不传参数）语义不变 | 按各期望 |

producer_history 的结构守卫（六字段完备、git 考证格式、REVOKED 语义）参照 scripts/tests/test_collector_history.py 的模式并入 test_anchor_plan_v3.py 或独立小节。

## 4. 地雷区（施工时必读）

1. `_point_multiset`（time_spotcheck.py:136-140）逐点 JSON 规范化精确比对——任何字段增删立即炸 v2 重放；投影是唯一防线。
2. kind 文案一字不改。
3. PLAN_SCHEMA 双定义（anchor_plan.py:45 + time_spotcheck.py:59）、shared 双硬编码（:957+:987）——漏一处即断。
4. invariant_manifest 漏同步 invariant_scan 会红（g2 工程有停工先例）。
5. receipt_validate 默认路径不得放宽（非 anchor 回执不受影响）。
6. 你的沙箱跑不了 test_batch3_evm_vertical_slice / test_batch3_solana_vertical_slice（loopback bind）——这两个跳过不算你的失败，其余测试全量自跑。

## 5. 完成标准

1. `python3 scripts/tests/run_all.py` 除两个 loopback 测试外全绿（在报告中列出你实际跑的方式与结果统计）；
2. 新测试 12 用例全绿且每个负测有红态实证；
3. `rg -n "anchor-plan/v2"` 全库残留逐条列入报告并标注"兼容路径/测试 fixture/文档"归属，不允许存在未解释残留；
4. `git diff --stat` 只含白名单文件；
5. 施工报告 `workorder_U1_done.md` 含：改动摘要（每文件一段）、红实证记录、e5168a 的 git 考证过程与结论、NES 存量深验的精确复跑命令（供调度方本机验收，含 --plan/--input 等实参路径模板）、v2 残留清单、未尽事项。
