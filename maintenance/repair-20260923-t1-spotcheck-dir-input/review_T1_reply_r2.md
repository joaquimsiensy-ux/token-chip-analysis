# 工单T1复核r2：退回

退回原因限于**工单锚纪律**：文档锚带有真实反斜杠、CHANGELOG:13 未给出完整原文，以及三处重复事实行未注明非唯一。**生产修法、main mock 接线、自洽重绑负例均成立**，无须扩大修复范围。

报告全文已打印到 stdout。基线为 HEAD `dab5810db0c8bf6520b2e6d391d5bb7bb21c63a0`，包含 `f4f80567c21f`；工作区为空，指定生产及文档路径相对基线的 diff 为空。下文 L 指 [workorder_T1.md](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260923-t1-spotcheck-dir-input/workorder_T1.md) 当前行号。

**g）r1 吸收核对**

| r1 意见 | v2 位置 | 结论 |
|---|---|---|
| 接线位置、521 插入点 | L52、L94 | 正确吸收 |
| 完整行锚、重复行说明 | L17、L160–170 | 未完全吸收，见下方修订 |
| 文件分支校验顺序 | L24、L59–85 | 正确吸收 |
| helper 私有化、复用 try | L28、L37、L52 | 正确吸收 |
| 清单正文检查、不重哈希边界 | L25、L76–85 | 正确吸收 |
| 文档 0 B 替换 | L26、L162 | 算术正确，锚表示需改 |
| RED 三项定义、隔离求值 | L19 | 正确吸收 |
| `_produce_plan(directory=)` 复用 | L92 | 正确吸收 |
| main 接线测试 | L108–124 | 成立 |
| 消费者篡改与自洽重绑负例 | L129–152 | 成立 |
| 完工 diff 覆盖工作树 | L175 | 正确吸收；L13 开工比较 HEAD 也正确 |
| 历史时间、绝对路径保证范围、案情来源措辞 | L3、L6、L51 | 正确吸收 |
| 无公开入口、9.0.3 档位 | L7、L28、L170 | 正确吸收 |

**a）锚与行号：三处必须订正**

已对 68 个事实位置或范围端点提取整行执行 `grep -n -F -x`，均能定位到对应行号。明确给出的 time:180/420、shared:1033/1043、tests:99/521、CHANGELOG:99 施工锚均唯一且行号正确。

1. **L161 的文档锚按字面匹配为 0。** 工单包含真实反斜杠，去掉后才唯一命中 references:158。L163 的替换文本也有相同问题。使用代码围栏可避免把反斜杠写入文档、破坏 0 B 约束。

将 **L160–163** 替换为：

~~~~markdown
- 基线 `references/data-pipeline-evm-recon.md:158` 的唯一整行锚如下（UTF-8 326 B，不含换行）：

```text
- 产物 `time_spotcheck.json`（`time-spotcheck/v3`，target 绑定 chain/token/final-block，并绑定 plan、plan receipt、merged input 与逐笔 RPC transcript；verdict/exit_code 为 0 PASS/2 FAIL/1 检测自身失败禁当 PASS）；split-run 案是 READY 必备件＋AUTO_GATES（handoff_manifest 重读防手报）。
```

仅将 `merged input `（含末尾空格，13 B）替换为 `文件/清单`（13 B）；该行 UTF-8 326→326 B。替换后整行：

```text
- 产物 `time_spotcheck.json`（`time-spotcheck/v3`，target 绑定 chain/token/final-block，并绑定 plan、plan receipt、文件/清单与逐笔 RPC transcript；verdict/exit_code 为 0 PASS/2 FAIL/1 检测自身失败禁当 PASS）；split-run 案是 READY 必备件＋AUTO_GATES（handoff_manifest 重读防手报）。
```
~~~~

2. **L168 仍是首尾定位描述，没有提供 r1 要求的完整原文。** 虽然能唯一定位第 13 行，但不满足 L17 的整行锚纪律，也与 L8 声称的“13/99 全文”不符。

将 **L168** 替换为：

~~~~markdown
- `CHANGELOG.md:13` 的唯一整行锚如下，在其之前插入下述一行索引：

```text
- **9.0.2**（2026-09-19）口径漂移与文档-代码不符审计第二期闭环（针对 7.2.0→9.0.1 六版代码大改而文档零改动）：codex 两路盲审十三轮（a 路全范围术语表法 9→2→3→4→2→2→2→2→1→1→2→0→1，b 路 7.2.0 起代码变更区专审 0→0→2→1→1→0→1→2→2→0→0→0→0；用户裁决 R13 修完即收官），十二份工单皆先 codex 只读复核（退回 9 次全在派工前拦下）再 codex 施工，38 条/21 文件纯文本修复，零代码改动；references 930076→929092（净减 984 B）、SKILL.md 8021 不变、commands-staging 8798→8789；范围外残留一条登记（fetch_sqd_transfers_v2 帮助文字，改则变采集器 sha）。
```
~~~~

3. **L17 漏列三处非唯一事实行。** time:422 整行命中 4 处，time:424 命中 5 处，shared:369 命中 2 处。按本轮“未注明不唯一者须恰 1 处”的要求，应补齐。

将 **L17** 替换为：

> - 0.5 行号均指基线 f4f80567c21f；施工锚使用目标文件整行原文，以 `grep -n -F -x` 核验恰 1 处且行号一致，不符停工。`time_spotcheck.py:416、422、424` 为非唯一事实引用，以 `:415` 的唯一整行及其后收据封装 try/except 定位；`shared_release_receipt.py:369、371、377、997` 为非唯一事实引用，前三项按 `bound_case_ref`、末项按 `_validated_time_plan_authority` 定位。删除 > 修改 > 新增；新增代码只准放在 §2 指定位置。

核心事实无误：

- `bound_case_ref:347–377` 要求案根内普通文件及 size/hash 相等。
- `receipt_kernel:53–78` 拒绝目录输入。
- `anchor_plan:194–203` 写清单并绑定清单文件。
- `anchor_selection.input_identity:75–102` 对目录计算文件清单哈希；`_detect_input:105–136` 读取 `run_*` 的 logs/blocks parquet。

**b）来源与事实断言：通过**

| 核验项 | 结论与依据 |
|---|---|
| READY generate/verify 调用链 | handoff:349/483 → shared:1445 → :1391 → :1069 → authority。其他前置条件通过时，只修生产者仍被目录身份校验拒；generate:364–366 返回 2。verify 的条件是非 legacy，或 wrapper 存在 |
| 清单引用绝对路径 | 正常 anchor_plan 输出成立：:107/153 归一目录，:199–201 未传 input_base，kernel:87–94 保留绝对路径。任意外部 plan 不保证，v2 已正确限定 |
| 目录身份重算 | time:203 调 `input_identity`，:207 比较实际 SHA256 与 `plan.input.sha256`，随后重放选点与统计 |
| parquet 列与时间戳 | 所需 logs 五列及 blocks 两列齐全；block_hash/log_index 未使用。整数秒乘 1000000 后进入 `make_timestamp` 正确 |
| 最小覆盖 | per_cell=2 ≥ 2、edge_max=5 ≥ 3；只抽非空格子，没有九格齐全或额外最小总点数要求 |
| 历史来源 | 本地 git 确认 1a7e685 日期为 2026-08-07，其父提交已有目录读取、目录身份与清单绑定 |

独立内存实验使用相同 24 行数据、原目录 SQL 和完整选点函数，仅将 parquet 读取替换为内存表：日期为 2025-01-01～03，中·大户 8 行、晚·大户 16 行，**矩阵点 4、强制点 9，final_block=300 检查通过**。未落盘生成 parquet，不将此记为完整 CLI 测试。

QUQ 规模、原案运行结果及前案输入形态仍属于调度方提供的案情；L6 已正确限定来源。

**c）修法及两个新用例：通过**

支持修法的最强理由：目录输入已经由计划生产者和语义重放支持，绑定普通清单文件补上了生产、消费两端断点。

反对新增放行分支的最强理由：发布时不再像文件输入那样复核当前全部数据内容。真正的取舍是验证生产时已核过的目录身份，还是发布时重新读取全目录。**L25 已明确选择前者及其边界**，不应在本工单中把目录重哈希搬进消费者。

- **不能删清单正文核验。** 引用哈希只证明绑定了哪份文件，不证明正文 input 与 plan.input/input_identity 一致。自洽重绑负例正用于覆盖这一点。
- **可以内联以做到零新增函数，但不是必要修改。** 一个私有 helper 便于独立测试，并复用了既有异常处理，没有新增公开接口。
- **文件分支的绑定行为和错误顺序保留。** identity → 同一实物 → manifest 顺序未变；给 manifest_path 赋值不改变行为。scripts/tests 对三类错误文本均零命中。不能进一步声称整个新收据逐字节相同，因为修改生产脚本会改变 producer.sha256。
- **macOS 案根别名不会误拒。** directory 与 root 均 resolve 后比较，`/var`→`/private/var` 可归一；末级 symlink 单独拒绝，与 `bound_case_ref` 的祖先别名处理一致。

**main mock 成立。** time:56 在模块层导入 `build_envelope`，main:417 使用全局名，没有局部重新导入；RPC 池到 :447–449 才建立。工单 argv 满足前置条件，受控异常被 :422–424 捕获并返回 1。独立执行真实基线 main、替换计划加载与重放后，确实捕获到目录 `inputs.input` 并返回 1；该实验验证接线，不替代完整目录 fixture 运行。

**自洽重绑成立，应采用当前绝对路径形态。** `receipt_validate._input_file:67–78` 接受解析后位于案根内的绝对路径。`:40–41` 的相对路径要求属于 producer 的仓库路径规则，不适用于 inputs。实际调用 `_input_file`，案根内绝对文件路径在 case_root 有值和无值时均通过。

L139–152 同步修改清单引用、plan 输出 size/hash，同时保持 plan.input/input_identity 不变，拟改消费者会命中正文身份不一致的 needle。单纯篡改场景则先在 shared:1009–1012 命中 `plan receipt envelope invalid`。两个负例覆盖不同层次，应保留。

建议将 **L156 中说明④** 替换为：

> ④自洽重绑保留 `new_ref["path"] = str(manifest_path)`。当前 anchor_plan 生成绝对路径清单引用；`receipt_validate._input_file:67-78` 接受解析后位于案根内的绝对路径，不会因其绝对形态拒收。`_shared_authority` 的 plan/plan_receipt 引用仍由 `_ref` 生成案根相对路径；`_refresh_receipt:131-136` 同步更新 plan 输出的 size/sha256。该场景保持 plan.input/input_identity 不变，须命中清单正文身份不一致的错误。

相应将 **L175** 的：

> 与工单差异（若有，含 §2.3 说明④取哪一形态）

替换为：

> 与工单差异（若有）

**d）回归面：通过**

已搜索 scripts/report、scripts/lib 的指定表达式及其他引号写法，并追查相关入口。

| 消费点 | 判断 |
|---|---|
| receipt_validate、shared:999 | 要求输入引用指向普通文件；清单满足，不要求是 merged 数据表 |
| handoff、audit_release、stage2 | 复用共享深验链，未发现第三处必须将时间 inputs.input 当作转账数据读取的要求 |
| new-analysis | 当前是 audit_release_gate 的 profile，未找到独立 new_analysis_gate.py；没有额外时间输入类型契约 |
| shared witness:1964–1974 | 对全部 inputs 记录文件指纹，清单可正常进入 |
| reconciliation_report.snapshot_inputs:78–94 | spec 显式登记的 inputs 必须是文件；不会自动登记时间 CLI 的目录参数。原案若直接登记目录仍会拒，但未读原案，不能据此扩大修改范围 |
| data_map/artifacts | “收据全部 inputs 必须登记”的专门规则属于 Solana exact |
| freeze | handoff:1264–1277 要求登记 provenance source.files，不是所有 EVM 时间收据 inputs |

`invariant_scan` 登记 schema 生产/消费、transport、atomic 等面，不登记所有公开函数。两份拟改源码仅在内存中代入后，`scan_python` 结果均与基线相同，无须因 helper 修改 invariant_manifest。

time_spotcheck 不在 PRODUCER_HISTORY 或 CURRENT_PRODUCERS，不应补登记历史哈希。生产脚本修改后，旧时间收据可能需要按既有当前生产者哈希规则重跑。

**e）上下文与精简：通过**

文档替换确实为 **13 B→13 B，完整行 326 B→326 B**，计数不含换行。因禁读 references/attic.md，未独立累加包含它的 references 全量正文；929092 不作为本轮实测总量。

L169 索引为 **406 B**；现有 CHANGELOG:13–25 条目为 **192–1373 B**，量级相当，无须仅因长度退回。复用 `_produce_plan` 已减少重复生产逻辑；main 接线、外层篡改、正文自洽重绑各守不同约束，不建议删掉其中一项。

**f）范围与版本：9.0.3 恰当**

未见越界修复。schema/键不变本身不足以决定修版本；决定性证据是既有 CLI、计划生产者和语义重放已经支持目录输入，本次修通失效路径，并使用私有 helper。按 CHANGELOG:4，属于既定契约内修复。

| 审查项 | 结论 | 后续动作 |
|---|---|---|
| g r1 吸收 | 锚要求未完全吸收 | 修订 L17、L160–163、L168 |
| a 锚与行号 | 退回 | 去除字面反斜杠、补完整行及非唯一说明 |
| b 来源与事实 | 通过 | 无生产改法调整 |
| c 修法及新用例 | 通过 | 说明④确定绝对路径形态 |
| d 回归面 | 通过 | 不扩大白名单、不登记历史哈希 |
| e 上下文与精简 | 通过 | 保持 0 B 与测试复用 |
| f 范围与版本 | 通过 | 保留 9.0.3 |
| **整体** | **退回** | **修订工单文本，不要求重做修法** |

本轮完成源码、git 历史、整行锚和内存实验；未运行会创建案卷或临时文件的完整测试套件，不登记 §0.8 PASS。全程离线，无 commit，无文件新建或修改；未读 memories、`~/.codex/` 或其他禁读路径。首次系统 git 启动器尝试创建缓存被沙箱拒绝，随后改用 CommandLineTools 的 git，未产生该缓存。
