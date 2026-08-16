# 工单 消化轮 1：关闭盲审 time 查 7 条 BREACH（plan 权威链消费侧缺失）

> 执行者：codex（纯施工，**禁止任何 git 操作**）
> 背景：独立盲审报告 `maintenance/repair-20260815-g2/blindreview_g2_round1.md` 第八节（time 查攻击轮 H0–H49）抓出 BREACH 7 条——6 条同源＋1 条 P3。先读该节向量表再动工。

## 根因（盲审定性，施工前自行对照代码确认）

消费侧 `shared_release_receipt.py::_validate_time_receipt` 从 `inputs.plan` 取"标准答案"，但没验这份 plan 是权威签发的那一份。生产侧 `scripts/lib/time_spotcheck.py` 的 `load_validated_plan` 对同组文件做了约 8 项绑定（plan_receipt 的 schema/producer 必须 `anchor_plan.py`/verdict PASS、`plan_receipt.output` 的 size+sha256 必须就是这份 plan 实物、`probe_count` 必须等于实际点数、input_identity、target 绑定等——**以生产侧实现为准逐项清点**），消费侧只抄了 input_identity 一项。后果：自写 plan 配他案签发件、点位砍到 1 个自选点、任意仓库脚本冒充签发者，收据表面合规四查全 PASS。

## 修改点

1. **`shared_release_receipt.py::_validate_time_receipt`**（仅此函数区）：把生产侧 `load_validated_plan` 的全部绑定语义在消费侧**独立实现**（本工程双写纪律；逐项平移，一项不落）：plan_receipt 实物存在于案根且过安全路径校验、schema/producer/verdict 合规、其 `output` 的 size+sha256 与绑定的 plan 实物逐字节一致、`probe_count` 等于 plan 实际点数、input_identity 与本收据 `inputs.input` 同物、target 全等。任何一项不满足即拒，错误文案指明是 plan 权威链断裂。
2. **第 7 条（P3）**：time 六计数增加 bool 拒绝（`isinstance(x, bool)` 先拒再验 int——仓库既有 `isinstance(value, bool)` 先例手法）。
3. 检查 balance/supply/anchor 分支是否存在同族"标准答案来源未验权威"的缺口（balance 的答案=balances 实物本身有哈希绑定，anchor 的答案=output 已 size+sha 双验——预期无同族，但要在 done 报告写出你逐分支排查的结论，不许跳过）。

## 回归负测（固化盲审向量，防复发）

并入 `scripts/tests/test_recon_deep_reverify.py` 的 time 节（该文件已挂 run_all）：按盲审报告 H 向量表把**全部 6 条同源 BREACH＋bool 计数**固化为负测（自写 plan 配他案签发件、点位砍 1、冒充签发者、probe_count 不符、output sha 不符、input_identity 换绑、bool 计数），另加绿例：完整权威链（anchor_plan 真实签发）通过。

## 先红后绿纪律

先写负测对当前代码跑：6 条同源向量应体现"当前消费面放行"（红），落 `digest1_red.log`；修复后全绿落 `digest1_green.log`。

## 存量测试适配（授权范围）

新权威链断言会打红缺 plan_receipt 链的存量 time 夹具。授权适配：`test_recon_deep_reverify.py`、`test_audit_release_gate.py`（公共夹具 `write_deep_recon_fixtures` 的 time 部分补真实权威链件）、`test_sixlens_receipts.py`、`test_handoff_manifest.py`、`test_arbitrum_exploration_cli.py`（若其 formal 正例含 time 收据）。名单外打红停下请示。

## 验收标准

- 新负测绿；沙箱内 `run_all.py` 除两个 loopback EPERM 外全绿；
- done 报告 `workorder_DIGEST1_done.md`：根因确认、绑定清单逐项平移对照表（生产侧第几行→消费侧第几行）、同族排查结论（第 3 点）、红绿证据、存量适配理由。

## 硬约束

- 只改：`scripts/report/shared_release_receipt.py`（限 `_validate_time_receipt` 及其私有 helper）、`scripts/tests/test_recon_deep_reverify.py`、上述授权存量测试。
- 禁碰：VERSION、CHANGELOG、SKILL.md、r10_ledger.md、pyproject、run_all.py、manifest/契约文件（如 invariant 扫描因新代码点打红，把 diff 写进 done 报告请示，勿自行改）、生产侧 time_spotcheck.py（消费侧独立实现，不动生产侧）、shared 的 A4/adversarial 区。
- 禁止一切 git 操作。

## 补充裁决（调度方）

invariant_manifest 登记请示：**授权**。与第 3/4 刀"manifest 登记跟刀走"原则一致——按 `invariant_scan.py` 实际 diff 输出把 `anchor-plan/v2` 消费点登记进 `scripts/tests/invariant_manifest.json`（`minimum_counts` 只升不降），随后跑通 `invariant_scan.py` 与沙箱内 `run_all.py`（loopback 两项除外），在 done 报告追加登记 diff 与最终输出。
