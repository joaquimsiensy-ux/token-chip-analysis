<!-- 由 Fable 从 codex 只读复核任务 task-mu4bhhdn-y0rdsx 的 Final output 段原样搬运 -->
# 工单复核 R2：退回

**60 个施工锚全部通过；字节预算、相关 needle、casebook 六字段和 G3 四项通过。退回原因是 F1 仍把哈希一致写成文件路径限制，D8 保留了未经证明的意图断言，白名单内另有五处同族遗漏。**

复核 HEAD：`adcbfe26842efc491c8248071fe064fa09fbc841`；VERSION：`7.1.1`。受审文件、`scripts/`、`commands-staging/`、`VERSION` 相对内容基线 `4445443` 未变。

## 逐条核对表

以下行号均为改前行号；文件简称指 `references/` 下对应文件。“通过”指本次内存模拟，不代表完成 §1.2 全套施工验收。

| 条目 | 锚命中 | 事实一致 | needle/守卫 | 意见 |
|---|---|---|---|---|
| D2 | 1@recon:152 | 是 | 通过 | 补齐必填 `--input`；正式示例只列 eth/bsc/base。锚及命令续行符实际均为一个反斜杠。 |
| D3 | 各 1@sources:60、63、64 | 是 | 通过 | 正式资格与历史实测区分正确，保留去重经验合理。 |
| D4 | 1@capture:48 | 是 | 通过 | 正式序列转换确实拒绝 `sol-anchor-rows`。 |
| D5 | 1@recon:13 | 是 | 通过 | `balance_sum == mint` 正确；不再把失败唯一归因于漏段。 |
| D5b | 1@supply-recon:41 | 是 | 通过 | §5 第 2 条引用正确。 |
| D6 | 1@supply-recon:42 | 是 | 通过 | 保留所选 top-N、RPC 失败阻断及 GMGN 黄灯查证义务。 |
| D7 | 各 1@tiering:31、workflow:145 | 是 | 通过 | strict／expanded 双边界与权威规则一致。 |
| D8 | tiering:82 两锚；scan:133、135、139；methods:134 两锚，均各 1 | **部分** | 通过 | tiering 第二锚、scan:135、methods:134 替换正确；scan:139 仍留下“反聚类伪装”。 |
| D9 | 1@scan:85 | 是 | 通过 | capture §9 第 7 条及 E-02/E-05 指针正确；另见同族遗漏。 |
| D10 | 各 1@casebook:18、19 | 是 | 六字段通过 | 四测及“未定性”状态均已修正。 |
| D11 | 1@wording:106 | 是 | 通过 | 与 tiering §6a 的其他大户线一致。 |
| D12 | 1@audit-protocol:166 | 是 | 通过 | 键序与逐查生产者分别指向正确权威源。 |
| F1：其他既有位置 | 13 锚均各 1：SKILL:32、45×2；template:90；supply:38、48；workflow:19、46；split:98×2、126、143；command:13 | 是 | 通过 | 泛化“四查”已修正，两份必读件文本同步。 |
| F1：快照段 | 4 锚均各 1：workflow:112、114；split:53×2 | **否** | 通过 | “同一个文件”“别另存内容一样的副本”仍与代码矛盾。 |
| F1：新增五处 | 6 锚均各 1：context:27、58；schemas:17、396×2、484 | 是 | 通过 | 未引入新的链别或绑定语义漂移；schemas:396 的“只比 sha256 不比 path”完整保留。 |
| D13 | 各 1@workflow:118、split:54 | 是 | G3 通过 | 合并边界另各 1@117、119；保留动态 Solana 前缀、缩进及完整命令。 |
| D14 | 1@labels/README:8 | 是 | 通过 | 删除统一开关承诺，同时覆盖两个不支持 `--no-labels` 的脚本。 |
| D15 | 1@channels:69 | 是 | 通过 | 当前 native done schema 为 v4。 |
| D16 | 1@channels:272 | 是 | 通过 | logs、blocks 均已采用 `iter_batches`。 |
| D17 | 1@channels:259 | 是 | 通过 | 不再用历史实测决定接口当前可用性。 |
| D18 | 1@labels/MAINTENANCE:19 | 是 | 通过 | `curation=-1`，manual/addressbook 为 0，较小值优先。 |
| D19 | 各 1@split:44—48 | 是 | 通过 | 五处删除不损坏现行动作。 |
| C1 | 1@capture:134 | 是 | 通过 | 上界取 `/head`、可选上界及 finalized slot 的较小值。 |
| C2 | 两锚均 1@methods:171 | 是 | 通过 | 去掉过期版本简称，`CT-METHOD-04` 原样保留。 |

**锚点结论：**实际逐项执行 `grep -n -F`，60 个明示施工锚全部恰好命中一次且行号一致。D13 两个区间边界也分别唯一；同行双锚按各自位置独立核验，整组替换区间无重叠。

**上一轮七条理由：**①锚不可执行、②引用错误、③D2 探索参数、④D10 错误归类、⑥D5/D6 检查边界、⑦内容基线与施工 HEAD，均已消化；⑤同族残留仅部分消化。上一轮 F1 修订建议中的“比较内容哈希、不要求相同路径”也尚未落实。

**按 v2 原文进行整组内存模拟：**

| 范围 | 改前 | 模拟改后 | 净变化 | 结果 |
|---|---:|---:|---:|---|
| `SKILL.md` | 8,024 B | 8,021 B | −3 B | 通过 |
| references 三组 glob | 930,850 B | 930,289 B | −561 B | 通过，净减 |
| `commands-staging/*.md` | 8,798 B | 8,798 B | 0 B | 通过 |

- 字节总量由文件大小元数据加模拟差量计算，未读取 attic 内容。
- 20 个修改文件全部在白名单内。相关 **183 条契约：166 required、17 banned**，无 required 丢失、无 banned 引入。
- 内存替换后执行 casebook 检查：**6 册、38 条通过**；变更的 E 册 **13 条**六字段完整。
- G3 的 F-08 A0、F-08 A2、F-13、F-05 **四项全部通过**；粗体配对通过。
- 未运行 `docs_lint.py`／`--all` 原命令，其遍历范围包含禁读内容；上述结果不冒充 §1.2 全套验收。

## 退回理由（若退回）

1. **F1 仍错误拒绝内容相同的合法副本。**  
   [工单第 103 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260916-drift-audit/workorder_r1.md:103)与第 105 行只替换“四查／verify_recon”字样，保留了 workflow 的“同一个文件”和 split 的“别另存一份内容一样的副本”。

   实际[发布闸](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/audit_release_gate.py:1252)只比较 SHA-256。对该函数做内存验证，EVM、Solana 均接受不同路径、相同哈希；initial 或 final 哈希不同均报错。各文件自身仍须通过登记与绑定校验，但不能把这些要求写成两边路径必须相同。

2. **D8 的 scan:139 仍把金额偏移直接解释为反聚类意图。**  
   替换后仍是“随机偏移（反聚类伪装）只作行为候选”。句尾降级没有消除括号里的确定性动机判断。上一轮建议整行替换，正是为了同时去掉这层预设。其余新增 D8 替换未发现此问题。

3. **白名单内仍有五处会绕过证据总闸的同族断言。**  
   scan:138、140、141、143 与 capture:37 仍从公共工具、代付、金额形态或共同资金路径直接推导专属控制。这些不是针脚问题；它们与 [methods 三问总闸](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-methods.md:144)、[公共归集工具排除规则](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-methods.md:128)及 [E-05 共同 funder 边界](/Users/uravvv/.claude/skills/token-chip-analysis/references/casebook/entity-clustering.md:44)冲突。

## 修订建议（逐条，可直接粘贴）

以下八项均为工单修订建议，未写入文件；使用改前行号。八个定位锚均已验证唯一。

**1. F1：撤销 workflow:112、114 两项碎片替换，改为 112—116 整段替换。**

首行锚：

```text
**喂它的 owner 快照必须与 A2 四查里 `verify_recon --balances` 吃的是同一个文件**
```

保留三空格缩进，整段替换为：

```text
   **owner 快照须与 A2 的权威输入绑定一致**：
   EVM 对 `balance` 收据的 `inputs.balances`；
   Solana 对 observation bundle 的 `holder_outputs.owners`。
   发布闸按 sha256 核对内容；即使总和相同，逐地址余额不同也会拒绝。
```

D13 的后续动态 Solana 段仍按原工单处理。

**2. F1：撤销 split-run:53 两项碎片替换，替换完整绑定说明。**

锚：`**快照单一来源硬性**：`。从该锚至同行“直接拒。”止替换为下文，前后其余文字保留：

```text
**快照单一来源硬性**：分布快照须与 A2 的权威输入内容一致：EVM 对 `balance` 收据的 `inputs.balances`，Solana 对 observation bundle 的 `holder_outputs.owners`；发布闸按 sha256 核对，逐地址余额不同即使总和相同也拒绝。
```

**3. D8：scan:139 改为整行替换。**

锚：`5. **金额分档 + ±10% 抖动**：`

```text
5. **金额分档 + ±10% 抖动**：近似买入额与偏移只作行为候选；须检验同期分母及工具/协议对照，不据此确证脚本驱动、反聚类意图或同一实体。
```

**4. D8 同族：补 scan:138。**

原锚：

```text
——普通用户不会用这套组合，是技术指纹（用户说"gas 都一样"即指此）；优先费按买/卖分固定档位也算。
```

替换为：

```text
——先检验同工具用户的组合普及率，并排除公共预设；买/卖分档亦同，不直接作控制证据。
```

**5. D8 同族：补 scan:140，整行替换。**

锚：`6. **母钱包代付创建落仓户 ATA**：`

```text
6. **代付 ATA 创建费**：同一交易中的 createAssociatedTokenAccount+transfer 只证明代付建户与转币，不证明付款方控制收款 owner；归属须另核收款方签名、后续处置和独立控制证据。（OPAL(Solana)，2026-07-14）
```

**6. D8 同族：补 scan:141。**

原锚：

```text
**跨地址的全局配平只有单一记账者能做到**，是"单一控制端"的强指纹（独立主体不会为凑别人仓位的整数而分15笔转账）。
```

替换为：

```text
只作跨地址配额管理候选；须排除公共执行服务，并补独立控制证据后再判同一实体。
```

**7. D8/D9 同族：补 scan:143，整行替换。**

锚：`**逆向找历代马甲（最高价值的一招）**：`

```text
**归集口上游候选反查**：总归集口的历史流入地址仅作为候选清单；逐址核验币流、公共服务属性与独立控制证据，不直接视为同一实体的历代马甲。（此方法跨链通用，见 playbook-entity-cluster-methods §6。）
```

**8. D9 同族：补 capture:37。**

原锚：

```text
识别马甲网络最有效的一招（母钱包收敛即实锤）。
```

替换为：

```text
母钱包收敛只作候选线索，须先按 casebook E-05 排除公共服务来源，再补独立控制证据。
```

**上述建议连同 v2 其余条目再次内存模拟：**`SKILL.md=8,021 B`；references 合计 **929,511 B，净减 1,339 B**；commands 合计 `8,798 B`。相关 183 条契约、casebook 检查、G3 四项及粗体配对仍全部通过，无需扩大文件白名单。

## 同族遗漏（白名单内 / 建议下轮）

**白名单内：**

| 位置 | 残留问题 | 对应建议 |
|---|---|---|
| workflow:112—116、split:53 | 把内容哈希一致误写成同文件、禁副本 | 1、2 |
| scan:139 | 金额偏移仍被预设为“反聚类伪装” | 3 |
| scan:138 | 未做同工具对照便断言普通用户不会使用该组合 | 4 |
| scan:140 | 代付 ATA 创建费被直接解释为控制收款钱包 | 5 |
| scan:141 | 凑整配平被断言只能来自单一记账者 | 6 |
| scan:143 | 归集口全部上游被直接等同历代马甲 | 7 |
| capture:37 | 共同 funder 收敛直接升级为实锤 | 8 |

未把 EVM 专属“四查”、明确的历史实测数字、快照窗口的轻量检查或 D3 修订后的历史采集经验误报为遗漏。

**白名单外，仅建议下轮：**

- `scripts/report/audit_release_gate.py:1253、1261、1291、1302` 的跨链注释及报错仍泛称“四查”。可统一为“A2 对账”；本轮不改代码。

本轮离线、零写入、未 commit，未通过工具打开禁读内容。结束时 HEAD 未变、工作区为空，20 个受审源文件哈希均未变化。
