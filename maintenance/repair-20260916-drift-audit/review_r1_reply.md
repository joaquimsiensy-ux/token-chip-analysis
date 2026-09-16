<!-- 由 Fable 从 codex 只读复核任务 task-mu4arrp7-guj86g 的 Final output 段原样搬运 -->
# 工单复核 R1：退回

复核对象为 `workorder_r1.md` v1。实际 HEAD 为 `c394976fe1112e4d0e42be6db47223accc170c7d`，VERSION 为 `7.1.1`；相对工单所写的 `4445443`，仅新增三份维护文档，受审文档和脚本未变。

**退回主要因为：5 个锚点零命中，3 处章节引用错误，部分替换仍不符合代码或证据边界，且白名单内存在同族遗漏。字节预算与本次检查的守卫不是退回原因。**

## 逐条核对表

“1@行号”表示实际执行 `grep -n -F`，恰好命中一次且行号正确。“守卫通过*”指去除工单多余转义后，在内存中模拟替换的结果，不代表已施工或完成 §1.2 全套验收。

| 条目 | 锚命中 | 事实一致 | needle/守卫 | 意见 |
|---|---|---|---|---|
| D2 | 1@152 | 部分一致 | 通过* | 补 `--input` 正确；但替换命令仍允许选 Arbitrum，却未加其必需的 `--exploration`。 |
| D3 | 各 1@60、63、64 | 一致 | 通过* | Alchemy 确无正式资格；channels §1 末段确有正式 CSV 规则。 |
| D4 | 1@48 | 一致 | 通过* | `sol-anchor-rows` 确被正式编译拒收；替换文本中的反引号不要带反斜杠。 |
| D5 | 1@13 | 部分一致 | 通过* | `sum_balances == mint_total` 正确；“不等即漏了转账段”不是代码能推出的唯一原因。 |
| D5b | 1@41 | 引用错误 | 通过* | 应引用 evm-recon **§5 第 2 条**，不存在所写的 §1 第 2 条。 |
| D6 | 1@42 | 部分一致 | 通过* | 应引用 **§5 第 1 条**；代码只核所选 top-N，且 GMGN 黄灯仍有发布前查证义务。 |
| D7 | 各 1@tiering:31、workflow:145 | 一致 | 通过* | “历史静置仓反向扫描后的双边界峰值”条真实存在；严格口径用于判级，扩展口径并列披露。 |
| D8 | 各 1@tiering:82、scan:133、135 | 修复不完整 | 通过* | 仍保留“行为级同一实体”“同 block → 单控制端 bundle”等越级推断，另有同族遗漏。 |
| D9 | 1@85 | 规则正确、引用错误 | 通过* | Streamflow 规则在 capture **§9 第 7 条**；§7 是遗留验证清单，只有四项。E-02/E-05 均存在。 |
| D10 | 1@18 | 不一致 | 六字段通过* | “未过四测”不能直接定性为公共设施；下一行还保留“三测做不全”。 |
| D11 | 1@106 | 一致 | 通过* | tiering §6a 存在，其他大户线确为 ≥0.1% 总供应或 ≥0.2% 流通。 |
| D12 | **0；去除转义后 1@166** | 键集正确、指针不足 | 通过* | scan-schemas §14.10 有 wrapper 字段表，但没有逐查生产者映射。Solana 固定顺序还与 EVM 不同。 |
| F1 | 8 个锚均恰 1 次：SKILL:32、45×2；template:90；supply:48；workflow:19；split:126；command:13 | 定义一致、覆盖不足 | 通过* | EVM 四查／Solana 五查正确；白名单内仍有七行泛化“四查”。 |
| D13 | workflow:117、119 各 1；**118 和 split:54 为 0** | 替换意图一致 | G3 通过* | 去除转义后均在指定行。代码是显式指定优先；final 取 initial 绑定；initial 取 data_map 唯一登记候选。 |
| D14 | **0；去除转义后 1@8** | 修复不完整 | 通过* | 除 `build_evolution.py`，同句列出的 `label_lookup.py` 也没有 `--no-labels`。 |
| D15 | 1@69 | 一致 | 通过* | 当前 `MANIFEST_SCHEMA` 为 `hypersync-v2-done/v4`，v3 属旧格式。 |
| D16 | 1@272 | 一致 | 通过* | logs 和 blocks 均已使用 `ParquetFile.iter_batches`；删除旧整表读取结论合理。 |
| D17 | 1@259 | 方向正确，时效表述需修 | 通过* | 可以删除“全路径 404”；但历史实测表不能决定接口当前可用性。 |
| D18 | 1@19 | 一致 | 通过* | `curation=-1`；`manual/addressbook/serial=0`，较小值优先。 |
| D19 | 各 1@44–48 | 一致 | 通过* | 五处删除均准确，不损坏现行动作或契约。 |
| C1 | **0；去除转义后 1@134** | 核心事实一致 | 通过* | 上界取 `/head`、可选 `--to-slot`、RPC finalized slot 的较小值；不是无条件等于 finalized slot。 |
| C2 | 两锚均 1@171 | 一致 | 通过* | 当前为 `wave-scan/v5`；删除旧版本简称合理，`CT-METHOD-04` needle 完整保留。 |

**锚点合计：42 个，37 个通过，5 个零命中。**没有发现“去除多余转义后，实际行号仍与工单不一致”的条目。D2 命令的续行符实测都是一个反斜杠，没有双反斜杠问题。

**守卫结果：**

- 内存模拟涉及 manifest 的 **139 条规则：124 required、15 banned**；required 无丢失，banned 无引入。
- 现状实际运行 `casebook_lint.py`：**6 册、38 条通过**；模拟后的变更册 **13 条，六字段完整**。
- `test_g3_docs_guards.py` 的四项检查：现状实际运行及模拟替换后均通过。
- 未运行 §1.2 全套。`docs_lint.py` 会遍历禁读文档，本次仅检查受影响针脚、粗体结构及上述指定守卫，未把局部通过当成整套验收。

**§1.1 字节约束可行。**以下为去除多余转义、保留 D13 首行前缀及缩进后的内存模拟；总量按文件大小元数据求和，没有执行会读取 attic 内容的 `cat`：

| 范围 | 改前 | 按原工单意图改后 | 净变化 | 上限 |
|---|---:|---:|---:|---:|
| `SKILL.md` | 8,024 B | 8,021 B | −3 B | 8,024 B |
| 指定 references 三组 glob | 930,850 B | 930,210 B | −640 B | 930,850 B，且须净减 |
| `commands-staging/*.md` | 8,798 B | 8,798 B | 0 B | 8,798 B |

**§0.3 白名单覆盖正确：**§2 涉及 18 个现有文件，全部在白名单内；第 19 个路径 `r1_done.md` 是 §4 明确要求的新报告，无漏项或无关文件。

## 退回理由（若退回）

1. **锚文本不能原样执行。**D12、D13 两处、D14、C1 的锚含字面量反斜杠，源文件只有反引号。按 §0.4，施工者必须停工，不能自行解码猜测。

2. **新增引用存在错误。**D5b/D6 将 evm-recon §5 写成 §1；D9 将 capture §9 写成 §7。D12 所指 wrapper 表确有对应内容，但逐查生产者应查代码中的 `RECON_PRODUCERS`，不能宣称该表提供了完整映射。“methods 行为指纹总纲”可理解为简称，实际可定位条目名是“行为指纹三问总闸与强弱两档”。

3. **D2 的完整命令仍存在可复现的参数失败。**Arbitrum 属探索档；没有 `--exploration` 时，执行模式解析直接拒绝。证据：[chain_registry.py:301](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/chain_registry.py:301)、[time_spotcheck.py:339](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/time_spotcheck.py:339)。

4. **D10 引入“未确认＝已确认设施”的错误归类。**方法册要求“四测未过不得入成员或惯犯库”，不等于所有未完成核验者都已经是公共设施；判例自身下一行也要求“未定性合约持仓单列”。证据：[methods:198](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-methods.md:198)、[entity-clustering:19](/Users/uravvv/.claude/skills/token-chip-analysis/references/casebook/entity-clustering.md:19)。

5. **D8、D14、F1、D10 有白名单内残留。**尤其 D8 仅把句尾“铁证”降级，仍保留句中确定性归属；D14 只补一个例外，仍会对 `label_lookup.py` 承诺不存在的开关。其参数定义见 [label_lookup.py:87](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/labels/label_lookup.py:87)。

6. **D5/D6 的替换需保留真实检查边界。**`verify_recon` 的闭合条件为 `mint == nominal and balance_sum == mint and not negatives`；不闭合不能唯一归因于漏段。RPC 比较只覆盖确定性选出的 top-N；GMGN 差异达到 0.15pp 后仍须处理发布阻断。证据：[verify_recon.py:337](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/verify_recon.py:337)、[verify_recon.py:357](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/verify_recon.py:357)。

7. **§0.1 需要区分内容基线与施工 HEAD。**现行工单要求 HEAD 等于 `4445443`，同时又要求先提交工单；当前归档提交已是 `c394976`，按字面必停。应允许仅包含工单落档的提交，同时单独校验受审内容未变。

D1 暂缓决定不在本次评价范围。

## 修订建议（逐条，给可直接粘贴的修订文本）

以下均为工单修订建议，未写入文件。除明确补充的同族句子外，保留同行其余文字。

**1. §0.1、§0.4：明确基线与锚点核验时机。**

§0.1 可改为：

```text
0.1 开工先确认 git status --short 为空，并记录施工 HEAD。文档/代码核对基线为 444544360179d5080657aafd5ad60a78fe89e9b3；工单落档提交允许存在，但 §2 所涉文件、scripts/ 与 VERSION 相对核对基线必须未变。不符即停工汇报。
```

§0.4 的锚点纪律可改为：

```text
全部锚文本与行号先在冻结的改前文本上逐项核验；同一文件按改前位置从后向前替换。任一锚不唯一或行号不符即停工，不自行猜测。
```

**2. D2：正式示例只列正式链。**

```bash
python3 scripts/lib/time_spotcheck.py --plan anchor_plan.json --input <生成plan所用的merged转账数据> \
    --rpc <独立archive节点> --chain <eth|bsc|base> --token 0x标的 \
    --out time_spotcheck.json --final-block <数据截止块>
```

若另保留 Arbitrum 示例，必须明确添加 `--exploration`，不能把它并入这条正式示例。

**3. D4：替换文本使用真实反引号。**

```text
产出 `sol-anchor-rows` 序列，仅探索辅助、不进正式编译链（正式序列走 replay_edges/replay_duck）。
```

**4. D5、D5b、D6：分别采用以下替换文本。**

D5：

```text
2. **全网余额和=mint_total**：重建余额按 raw integer 求和等于铸币总量（sink 收方照加），不等即对账失败，须排查数据或重放口径。（SIREN，07）
```

D5b：

```text
- 全网余额和 = mint_total（sink 收方照加；定义见 data-pipeline-evm-recon §5 第 2 条）（SIREN，07）
```

D6 整行：

```text
- 按 verify_recon 所选 top-N 与冻结块 RPC balanceOf 逐地址精确对账，差异或观测失败均阻断；GMGN top10 差异 ≥0.15pp 时记黄灯，并在发布前绑定合格查证说明（data-pipeline-evm-recon §5 第 1 条；OPN，07；08-15 黄灯制）
```

**5. D8：同时修正结论和仍残留的归属推断。**

tiering:82，将原“三者叠加……”句替换为：

```text
三者叠加仍只作行为证据；定级须过 methods“行为指纹三问总闸与强弱两档”，无独立控制证据时最高为“高度疑似”。
```

同行原“gas 不同源时只能写行为级同一实体，不得写资金同源。”替换为：

```text
未补独立控制证据不得确证同一实体；gas 不同源不得写资金同源。
```

scan:133 的原锚替换为：

```text
的关联候选指纹（定级须过 playbook-entity-cluster-methods“行为指纹三问总闸与强弱两档”；纯行为最高为“高度疑似”）
```

scan:135 整行替换为：

```text
1. **同 slot 共现**：多钱包同 slot 同买同卖只作候选发现；用 pre/postTokenBalances 按 `(mint,side)` 定位后，须排除公共工具和协议机制；同 slot 本身不证明原子 bundle 或单一控制端。
```

补 scan:139，整行替换为：

```text
5. **金额分档 + ±10% 抖动**：近似买入额与偏移只作行为候选；须检验同期分母及工具/协议对照，不据此确证脚本驱动或同一实体。
```

补 methods:134，两处片段替换：

```text
①**配对自证**
→
①**配对指纹候选**
```

```text
=批量定制的配对地址，同一实体最硬指纹之一（铁证级；识别看中段不看前缀）
→
只作定制地址候选指纹；须过行为指纹三问总闸，不能仅据共享中段确证同一实体
```

**6. D9：修正章节号。**

```text
多笔提取共用此 feePayer 只证明同用该服务，不作控制边；归属须沿代币流穿透（data-pipeline-solana-capture §9 第 7 条、casebook E-02/E-05）。
```

**7. D10：保留未定性状态，并补下一行。**

原三测片段替换为：

```text
**公共基础设施先验四测**（按 playbook-entity-cluster-methods“公共基础设施先验四测”执行；未完成核验不得入成员或惯犯库，列为未定性；确认公共设施后按设施单列）。
```

同文件:19 补一处：

```text
三测做不全时
→
四测做不全时
```

六字段标签及其余同行文字不动。

**8. D12：修正锚，并分别指向键序与生产者。**

实际锚为：

```text
受控启动四查生产者生成：balance/supply=`verify_recon.py`、supply_truth=`supply_truth_gate.py`、time=`time_spotcheck.py`（Solana 对应 anchor sampler 与 holder snapshot）。
```

替换为：

```text
受控启动各链对账生产者生成（EVM 四查、Solana 五查；键序见 scan-schemas §14.10，逐查生产者见 scripts/report/shared_release_receipt.py 的 RECON_PRODUCERS）。
```

代码规定的顺序是：

```text
EVM:    balance,supply,supply_truth,time
Solana: supply,balance,supply_truth,time,exact_reconcile
```

**9. F1：补齐白名单内遗漏。**

supply-recon:38 整行替换为：

```text
**总原则：按 analyze-workflow A2 完成全部对账关卡后才进入分析；EVM 四查、Solana 五查（另含 exact_reconcile）。** 下方各链条目为历史校验形态，不替代正式查项；GMGN 黄灯处理见 data-pipeline-evm-recon §5 第 1 条。
```

analyze-workflow:46，片段替换：

```text
采集 receipt、四查、标签 resolver
→
采集 receipt、按链定义的对账关卡、标签 resolver
```

analyze-workflow:112–116 整段替换为：

```text
   **owner 快照须与 A2 的权威输入绑定一致**：
   EVM 对 `balance` 收据的 `inputs.balances`；
   Solana 对 observation bundle 的 `holder_outputs.owners`。
   发布闸按 sha256 核对内容；即使总和相同，逐地址余额不同也会拒绝。
```

split-run:53，仅替换从“**快照单一来源硬性**：”至“直接拒。”的片段：

```text
**快照单一来源硬性**：分布快照须与 A2 的权威输入内容一致：EVM 对 `balance` 收据的 `inputs.balances`，Solana 对 observation bundle 的 `holder_outputs.owners`；发布闸按 sha256 核对，逐地址余额不同即使总和相同也拒绝。
```

这里同时避免把 Solana 写成使用 `verify_recon --balances`，也避免把哈希一致约束误写成路径必须相同；代码明确只比较 sha256，见 [audit_release_gate.py:1255](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/audit_release_gate.py:1255)。

另补三处：

| 文件、改前行号 | 原锚 | 替换 |
|---|---|---|
| split-run:98 | `四查 producer receipt` | `A2 全部 producer receipt` |
| split-run:98 | `四查 receipt 格式零改动` | `各项 receipt 按现行 schema 提供` |
| split-run:143 | `verify＋四查兜底` | `verify＋A2 全部对账关卡兜底` |

**10. D13：删除锚中的反斜杠，保留动态 Solana 前缀。**

analyze-workflow:118 的实际锚：

```text
`holder_distribution_scan.find_snapshot` 默认优先 `data/holders_owners.json`（冻结件），
```

117–119 指定片段合并为：

```text
必须显式指定观察快照（`--snapshot`），因为发布闸的分布绑定要求 observation bundle 的观察 owners。完整命令：
```

保留首行原有“动态 Solana（`exact_reconcile` 早于 wrapper）”和缩进，完整命令不动。

split-run:54 实际锚：

```text
必须显式使用观察 owners；`find_snapshot` 默认优先 `data/holders_owners.json`（冻结件），发布闸分布绑定却要求 observation bundle 的观察件。
```

替换为：

```text
必须显式使用观察 owners（`--snapshot`），因为发布闸分布绑定要求 observation bundle 的观察件。
```

**11. D14：直接删除统一开关承诺。**

实际锚：

```text
均已默认接入（`--no-labels` 关闭）
```

替换为：

```text
均已默认接入
```

这同时解决 `build_evolution.py` 和 `label_lookup.py` 两个例外，符合删除优先原则。

**12. D17：不把历史表当成当前可用性判据。**

```text
正身可试 meme-api（历史实测见 data-pipeline-evm-sources，当前可用性须实测），或查创世 tx HTML 是否触及
```

本轮离线，没有对接口今日状态作判断。

**13. C1：修正锚，并写明取较小上界。**

实际锚：

```text
采集上界取 `/head` 没问题（实测到 head 仍正常返回数据）,但别拿两者的差当异常。
```

替换为：

```text
生产者上界不超过 finalized slot，并与 `/head`、可选 `--to-slot` 取较小值（`fetch_sqd_transfers_v2.py`），别拿两者的差当异常。
```

其余 D3、D7、D11、D15、D16、D18、D19、C2 保持原工单方案。

**上述建议整组再次内存模拟：**`SKILL.md=8,021 B`；references 合计 `929,969 B`，净减 `881 B`；commands 合计 `8,798 B`。相关 needle 无损，G3 四项及变更判例册六字段检查均通过。全部建议仍在原有文件白名单内。

## 同族遗漏（白名单内 / 建议下轮）

**白名单内，应补入本工单：**

| 同族 | 位置（改前行号） | 未覆盖内容 |
|---|---|---|
| F1／D12 | `playbook-supply-recon.md:38` | 三处把跨链对账统一写成“四查”；开头还把所有差异直接等同数据洞。 |
| F1／D12 | `analyze-workflow.md:46、112、114` | 新链及跨链快照规则仍泛化“四查”；Solana 被卷入 `verify_recon --balances` 说法。 |
| F1／D12 | `split-run.md:53、98、143` | 快照、交接产物、数据完整性保障仍泛化“四查”。 |
| D10 | `casebook/entity-clustering.md:19` | “三测做不全”未同步修改。 |
| D8 | `playbook-entity-cluster-tiering.md:82` | 同一行仍允许“行为级同一实体”。 |
| D8 | `data-pipeline-solana-scan.md:135` | 只改句尾，仍保留“同 block → 单控制端 bundle”。 |
| D8 | `data-pipeline-solana-scan.md:139` | 仍称金额抖动为“脚本驱动铁证”；直接结论虽是脚本驱动，仍属过强确定性。 |
| D8 | `playbook-entity-cluster-methods.md:134` | vanity 共享中段仍被称为“配对自证”“铁证级”。 |
| D14 | `references/labels/README.md:8` | 同一句还有不支持该开关的 `label_lookup.py`。 |

**白名单外，仅建议下轮：**

| 同族 | 位置 | 建议 |
|---|---|---|
| F1／D12 | `references/context-discipline.md:27、58` | 将泛化的“对账四查”改为按链定义的 A2 全部查项。 |
| F1／D12 | `references/scan-schemas.md:17` | `four-check 对账` 仍覆盖 Solana 语境。 |
| F1／D12 | `references/scan-schemas.md:396、484` | 跨链快照绑定仍统称“四查”；保留其中明确限定 EVM 的正确“四查”说法。 |

未将 EVM 专属“四查”、已明确记载的历史版本、附录“四件套”或已有“Solana 五查”说明误报为遗漏。D3 修改后的 §8.1 历史标题也覆盖该节保留的拼接经验，不另判其为现役 Alchemy 正式通道推荐。

本轮离线、零写入、未 commit，未通过工具打开禁读内容。复核前工作区为空；结束时 HEAD 未变、已跟踪文件 diff 为空，但出现未跟踪文件 `maintenance/repair-20260916-drift-audit/code_change_pending.md`，本轮未创建、读取或修改该文件。
