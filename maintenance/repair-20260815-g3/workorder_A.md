# 工单 A（AI-3 / repair-20260815-g3）：F-08 + F-13 + F-05 文档三件套 + 守卫测试

## 你的角色与硬边界

你是施工方，在本 worktree（分支 repair-20260815-g3，基线 ddba187 v6.44.0）纯改文件。硬边界：
1. **禁止 git 操作**（不 add/commit/push——由调度方验收后代 commit）
2. **只准改动以下文件**：`references/analyze-workflow.md`、`references/research-workflows.md`、新建 `scripts/tests/test_g3_docs_guards.py`、新建 `maintenance/repair-20260815-g3/workorder_A_done.md`。其余任何文件一律不碰（含 SKILL.md/VERSION/CHANGELOG/run_all.py/r10_ledger.md——三方并行工程有分域协议）
3. **不注册新测试进 run_all.py**（SUITE 注册行由融合方统一加）
4. 措辞纪律：所有新增文字与注释用中性词（负向测试/守卫/边界），整体工程背景是常规文档一致性修复
5. 完成标准里的测试命令必须真实跑过并把输出摘要写进 done 报告，禁止只声称

背景一句话：上游全量审查发现三处文档与代码现实脱节（F-08 命令必报错、F-13 描述与 runner 行为相反、F-05 文档承诺超出机器强制范围），本工单全部以"文档对齐现实"方式修复，零代码行为变更。

## 任务 1（F-08）：analyze-workflow.md 的 A0/A2 记账命令顺序修复

**现状**：
- A0 段（"**记账模型准入 gate**"段，约第 48 行）给出的 EVM 命令是 `python3 scripts/evm/accounting_gate.py --token 0x… --chain <链> --out accounting_mode.json`（eth 侧另提 --rpc）。而 `scripts/evm/accounting_gate.py` 第 412-413 行要求 `--bundle` 与 `--exploration` 必居其一，否则 argparse exit 2——按文档原样执行必死。
- observation bundle 要到 A2 第 3 查（"供给真值闸"段，约第 66 行）才由 `observe_supply.py` 首次产出，A0 时点不存在。
- formal 消费面（`scripts/report/shared_release_receipt.py` validate_accounting_receipt，843-848 行）EVM 案只认 `--bundle` 产的 `accounting-gate/v2`；`--exploration` 产 v1 被拒。

**修法**（两处改动，保持原文风格与粗体习惯）：
1. A0 段 EVM 命令改为：`python3 scripts/evm/accounting_gate.py --token 0x… --chain <链> --exploration --out accounting_mode.exploration.json`（eth 侧 --rpc 提示保留）。命令后紧跟补充说明（融入原段落语言风格）：A0 是模型预检（探索档，产 accounting-gate/v1，文件名固定 `accounting_mode.exploration.json` 不得占用正式名）；exit 0/2/1 三档语义维持原文不变；正式 `accounting_mode.json` 由 A2 生成 bundle 后重跑产出（见 A2 第 3 查）。
2. A2 第 3 查段：现有顺序是 observe_supply.py → supply_truth_gate.py。在两者之间插入正式记账重跑步骤：`python3 scripts/evm/accounting_gate.py --token 0x… --chain <链> --bundle evm_observation_bundle.json --as-of-block <冻结块> --out accounting_mode.json`，并注明：这一步产 `accounting-gate/v2` 正式件，是发布消费面唯一认可的记账收据；**A2 formal 结果为唯一 canonical，与 A0 预检结论不同时以 formal 为准并停止后续阶段等待人工裁决**；Solana 命令与流程不变。

**禁改**：A0 段的 exit 码语义文字、Solana 命令、其余段落。

## 任务 2（F-13）：research-workflows.md 的 runner 注入描述对齐

**现状**：`references/research-workflows.md` 第 102 行写"[输出 JSON schema（落盘前由受控 runner 补入 role 与 registry_sha256）]"。实际行为（`scripts/report/adversarial_review_runner.py` 491-494 行）：runner 只设 `CHIP_REVIEW_OUTPUT`/`CHIP_REVIEW_ROLE`/`CHIP_REVIEW_REGISTRY_SHA256` 三个环境变量，entrypoint 必须自行读取并写入字段，validator 校验一致否则拒收。

**修法**：把括号内文字改为（精确采用此措辞，可按上下文微调标点）："entrypoint 必须从 `CHIP_REVIEW_ROLE` 与 `CHIP_REVIEW_REGISTRY_SHA256` 读取值，逐字写入 `CHIP_REVIEW_OUTPUT` 指定的 artifact；runner 在发布前校验一致，不会静默覆盖或补入"。

## 任务 3（F-05）：A4 机器化边界的精确清单（两文档）

**背景与裁决**：analyze-workflow.md A4 执行序第 5 步（约 152-163 行）要求"N 路怀疑者＋1 完整性＋1 外部异构怀疑者"，但机器闸（adversarial_review_runner.py 的 finalize）不强制路数与异构性。用户已裁决**不加机器闸**，本任务只做文档边界澄清，runner 代码一个字不改。

**修法**：在以下两处各补一段边界声明（仿 research-workflows.md 已有的"这只封住已运行路次在 finalize 时被事后省略的面，不证明本地文件未被整套重造"的诚实边界句风格）：
1. analyze-workflow.md A4 第 5 步段末
2. research-workflows.md §2 对应位置（约 108-110 行"全部 claim-review 产物的 claim_id 并集…"那段之后）

边界声明必须**逐项列明**（两处可用同一段文字）：
- 机器已强制：两类角色在场（≥1 claim 怀疑者＋≥1 完整性批评）、claim_id 并集精确覆盖注册表、entrypoint 内容去重、execution ledger 哈希链精确对账、每条 evidence ≥10 实义白名单字符、findings/non_covered/REFUTED 与 blocker 双向联动。
- 机器未强制（依执行纪律与独立盲审落实）：怀疑者路数 N、每条结论的分档路数、外部路是否真为异构模型、外部异构路成功与否（该路失败不阻塞交付，见本册既有条款）。
- 收尾句：机器闸 PASS 不等于 N 路已落实——路数与异构性的核验责任在执行纪律与盲审，不在发布闸。

## 任务 4：新守卫测试 scripts/tests/test_g3_docs_guards.py

独立可执行（`python3 scripts/tests/test_g3_docs_guards.py`，exit 0 全过 / 非零任一失败，打印 PASS/FAIL 行），风格参照 `scripts/tests/test_round4_csv_adapters.py`（无 pytest 依赖，纯标准库）。断言清单：

1. **F-08 needle（按标题分段检查，不做全文匹配）**：
   - 定位"记账模型准入 gate"所在段（从该标题词到下一个 `## ` 标题之间的文本）：段内 EVM accounting_gate.py 命令行必含 `--exploration` 与 `accounting_mode.exploration.json`，且**不含** `--bundle`（A0 段不该出现 bundle 用法）
   - 定位 A2 供给真值闸段（含 `observe_supply.py` 的段落）：必含 `--bundle evm_observation_bundle.json` 与 `accounting_mode.json` 的重跑命令，且 observe_supply 命令出现在 accounting_gate --bundle 命令之前（顺序断言：按字符位置比较）
2. **F-13 needle**：research-workflows.md 必含"逐字写入"与"不会静默覆盖或补入"，且不含旧句"由受控 runner 补入 role"
3. **F-05 needle**：两份文档各含"机器未强制"（或你实际采用的等价标记词，测试与文档用词保持一致）与"路数与异构性"字样
4. 全部断言基于仓库相对路径读文件，不依赖网络

**注意**：不修改 run_all.py；测试文件自身要过 `python3 -m py_compile`。

## 完成标准（全部满足才算完）

1. 三份文档改动完成，`python3 scripts/tests/docs_lint.py --all` exit 0（docs_lint 有逐行粗体配对检查，改 Markdown 时注意 `**` 配对与既有契约字符串不被误删）
2. `python3 scripts/tests/test_g3_docs_guards.py` exit 0
3. 既有相关测试不破坏：`python3 scripts/tests/test_commands_deploy_sync.py`、`python3 scripts/tests/test_repair_batch_a.py` 各自 exit 0
4. 写 `maintenance/repair-20260815-g3/workorder_A_done.md`：改动文件清单（每处一句话说明）、上述四条命令的真实输出摘要（各 3-5 行）、自查确认"未动边界外文件"的声明

按任务 1→2→3→4 顺序执行。遇到与本工单描述不符的代码/文档现状（行号漂移属正常，按内容定位），如实记录在 done 报告并按实际现状施工；遇到真正的边界冲突（必须动边界外文件才能完成）则停工，把冲突写进 done 报告等待裁决，不得越界。
