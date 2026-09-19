# 工单R8复核：退回

**退回原因：D3 漏掉同文件第 46、71 行的同源失效表述。** 原定九处替换均可采纳：锚点、行号、代码依据及字节预算全部核实。补齐两处后仍为 **5 文件，11 行整行替换，净减 361 B，references 合计 929167 B**；白名单无需扩展。

复核 HEAD 为 `c4ecdb4927b45b5e99371284aa14c152767f5770`。前后工作区均干净，工单指定内容范围相对 `c16bf8e` 的差异为空。

**D1：采纳，代码依据成立。**

[观测请求](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_observation.py:400)只有 mint 的 `memcmp`，两种程序共用该路径。抽取现行参数解析、拒绝条件和请求构造代码，在内存中复现确认：

- SPL 显式传 `165`、`170`、`165,170` 均通过尺寸参数检查，实际请求均不加 `dataSize`。
- Token-2022 仅接受 `auto/all`，上述显式尺寸均被拒绝。
- `main()` 对 `choose_datasizes()` 调用数为零，对 `observe_snapshot()` 调用数为一。**不能扩大成“全库无调用”**：测试文件第 126、128 行仍调用旧 helper；工单限定“main 内”正确。
- 供给闭合检查发生在正式 holders 写出之前，保留的失败行为说明成立。

采纳 [scan:64](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-scan.md:64) 的整行替换：

```text
- 坑预警（Token-2022 实测升级）`[VERIFIED·CLUDE实战]`：先 `getAccountInfo(<MINT>)` 看 mint 归属程序。若是 Token-2022（`TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb`）：①pump.fun 新币标准是 Token-2022，账户主流 dataSize=165 与 170 双形态并存，但**还有零星其他 dataSize**（CLUDE 实测 165/170 双扫漏 14 个账户 0.036% 供应，对账不闭合）——正解是 **api.mainnet-beta 无 dataSize 过滤全扫**（见 §0a Token-2022 行，publicnode 此路 504）+ `memcmp offset=0` 按 mint 过滤；②扫描器 `--datasizes` 仅兼容参数，一律不按 dataSize 过滤；Token-2022 显式 165/170 会拒绝，账户加总不等于 `getTokenSupply` 也不会写正式 holders 产物。（CLUDE，07-13；2026-08-02 加固）
```

回归检索仍命中 [scan:58](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-scan.md:58) 的 `{"dataSize":165}`。该示例固定使用 SPL 程序，是手工 RPC 调用，没有声称复刻现行扫描器请求；相邻第 61 行说明 SPL 定长。因此记录此命中，**不将它判为同款错误，也不扩改单**。历史 Token-2022 尺寸实测记录同样保留。

**D2：采纳，属于链族作用域澄清。**

[Solana 生产者](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/accounting_gate_sol.py:137)写 `accounting-gate/v1`；[发布消费者](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/shared_release_receipt.py:1715)明确要求 EVM v2、Solana v1。内存执行该版本分支得到相同结果。

原句紧接 Solana 说明，增加 `EVM ` 能消除实际歧义；这是 **4 个 UTF-8 字节**，不是改变收据规则。采纳 [workflow:66](/Users/uravvv/.claude/skills/token-chip-analysis/references/analyze-workflow.md:66) 的整行替换：

```text
3. **供给真值闸（v6 新增，重放收尾必跑）**：EVM 先运行 `python3 scripts/evm/observe_supply.py --chain <eth|bsc|base> --token 0x… --as-of-block <冻结块> --out evm_observation_bundle.json --transcript-out evm_observation_transcript.json`，再运行 `python3 scripts/evm/accounting_gate.py --token 0x… --chain <链> --bundle evm_observation_bundle.json --as-of-block <冻结块> --out accounting_mode.json`，最后运行 `python3 scripts/lib/supply_truth_gate.py --chain <链> --token 0x… --as-of-block <冻结块> --replay-stats <replay_stats.json> --observation-bundle evm_observation_bundle.json --out supply_truth.json`，产 `supply-truth-receipt/v4`；Solana 仍产 `supply-truth-receipt/v3`。EVM 正式记账重跑产 `accounting-gate/v2`，是发布消费面唯一认可的记账收据；A2 formal 结果为唯一 canonical，与 A0 预检结论不同时以 formal 为准并停止后续阶段等待人工裁决。两者均绑定 target。主规则按形态①对比 `mint−burn` 与链上 `totalSupply()`；EVM 主 FAIL 且拆分统计齐全时，形态②自动要求 `mint==totalSupply`、ZERO/dead 各自与冻结块 `balanceOf` 逐地址相等、两 sink 合计与 burn 闭合。这里只证明终态标量与 sink 逐地址归因闭合；混合形态、旧 stats 或任一观测失败均维持 fail-closed（见 casebook S-01/S-11）。
```

其他 `accounting-gate/v2` 文档命中均有 EVM 上下文或明确分链说明，未发现同款遗漏。

**D3：原替换采纳，但必须补两处遗漏。**

现行 [§8](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-capture.md:30)没有 CLUDE Plan B 定义；第 35 行反而说明 2–6 个月币龄全程重放数小时级。工单关于第 46 行“仅提及、无定义”的依据也属实。

采纳 [capture:237](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-capture.md:237) 的整行替换：

```text
**适用场景**：老 pump.fun 币在内盘（bonding curve）滞留数月甚至一年以上才毕业——内盘期交易稀疏，但**不能不采**：做量脉冲、早期集群、毕业前试盘仓全藏在这段。用 SQD 扫这段 slot 区间在死亡期每响应仅推进 ~3900 slot，工程上极不划算。本节是**稀疏长内盘期**的全量精确解——稀疏恰恰使逐笔 decode 可行。
```

最强的保留理由是这些段落记录历史实战。但第 46 行仍使用无定义的 Plan B 作比较，第 71 行更明确指向现行 §8 中不存在的表述，删除第 237 行后仍会留下同源引用问题。建议只删除失效比较，不改变方法适用范围。

[第 46 行](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-capture.md:46)旧锚：

```text
针对"4-5 个月币龄全量 SQD 挂机不现实"的 Plan B 的一个更轻量替代，已在 LAYOFF 跑通：
```

整行替换为：

```text
已在 LAYOFF 跑通：
```

[第 71 行](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-solana-capture.md:71)旧锚：

```text
§8"全程 SQD 重放不现实"与 §9 锚点法的合体升级——14 个月+币龄、13.5 万持仓账户量级标的实战定型：
```

整行替换为：

```text
14 个月+币龄、13.5 万持仓账户量级标的实战定型：
```

两条补充锚也已按整行 `grep -n -F -x` 验证唯一命中、行号一致。

**D4：六处全部采纳。**

[C-06](/Users/uravvv/.claude/skills/token-chip-analysis/references/casebook/cex-custody-methods.md:5)、[E-12](/Users/uravvv/.claude/skills/token-chip-analysis/references/casebook/entity-clustering-methods.md:5)确在续册，两个主册均无同号。无路径惯例明确存在：tiering 第 93 行已有 `casebook E-12`，第 121、122 行已有 `casebook C-07`；casebook README 也登记了六册路由。

采纳以下六条整行替换。

`references/playbook-entity-cluster-tiering.md:136`：

```text
翻案见 casebook C-06；案源：GOAT、IQ 2026-07-26。
```

`references/data-pipeline-evm-channels.md:255`：

```text
| CEX 归集身份 | 必须核下游对象身份，禁止只凭高入度低出度判 CEX | （判例：casebook C-06） |
```

`references/data-pipeline-evm-channels.md:259`：

```text
| four.meme creator/收币实体 | 同收币地址不得直接判项目方马甲；平台 creator 与收币实体按身份权威规则分账 | （判例：casebook E-12） |
```

`references/data-pipeline-solana-capture.md:39`：

```text
5. **铸造受益人全清单**：创建 tx 的全部铸造受益地址都作为 creator 系起点。（判例：casebook E-12）
```

`references/data-pipeline-solana-capture.md:53`：

```text
6. **creator 履历与变更**：拉 creator 全发币履历、RugCheck 风险并对比 `set_creator` 前后身份。（判例：casebook E-12）
```

`references/data-pipeline-solana-capture.md:83`：

```text
6. **letsbonk creator 经济流**：追踪 dev 直分后续流向、Raydium Lock harvest 与毕业迁移平台常数。（判例：casebook E-12）
```

六处覆盖了允许文档范围内全部同款错指主册的引用。`docs_lint.REF_RE` 对这些旧、新字符串均不匹配，因此不能靠 lint 证明编号归属正确；本次已另核实际条目、编号唯一性及既有引用惯例。

**锚点与 UTF-8 字节汇总**

字节数不含行末 LF；所有替换均保留 LF，行数不变。下表每条旧锚均恰好命中一次，且行号一致。

| 条目 | 文件简称及行号 | 旧行 B | 新行 B | 差值 B | 意见 |
|---|---|---:|---:|---:|---|
| D1 | solana-scan:64 | 783 | 781 | −2 | 采纳 |
| D2 | analyze-workflow:66 | 1375 | 1379 | +4 | 采纳 |
| D3 | solana-capture:237 | 502 | 410 | −92 | 采纳 |
| D4 | entity-cluster-tiering:136 | 73 | 58 | −15 | 采纳 |
| D4 | evm-channels:255 | 136 | 121 | −15 | 采纳 |
| D4 | evm-channels:259 | 194 | 173 | −21 | 采纳 |
| D4 | solana-capture:39 | 150 | 129 | −21 | 采纳 |
| D4 | solana-capture:53 | 166 | 145 | −21 | 采纳 |
| D4 | solana-capture:83 | 168 | 147 | −21 | 采纳 |
| **v1 合计** | **9 行** | **3547** | **3343** | **−204** | **声明正确** |
| D3 补充 | solana-capture:46 | 111 | 23 | −88 | 应补入 |
| D3 补充 | solana-capture:71 | 135 | 66 | −69 | 应补入 |
| **修订后合计** | **11 行** | **3793** | **3432** | **−361** | **更新工单预算** |

实测基线：`SKILL.md = 8021 B`，commands 合计 `8789 B`，references 三组 glob 合计 `929528 B`。v1 模拟结果 `929324 B` 完全正确；补齐遗漏后改为 `929167 B`，D3 小计改为 `−249 B`。

**范围、简洁性及验证边界**

全部建议均为文本修改或行内删除，没有增加 SKILL 入口、规则副本或代码改动。两处补充属于同源失效引用，现有白名单足够。D1 也可缩写为“扫描器不按 dataSize 过滤，`--datasizes` 仅兼容”；这属于可选措辞压缩，未计入预算，也不作为退回理由。

基线、v1 内存替换、补齐 D3 后的内存替换，均通过允许范围内的 `docs_lint` 检查：普通模式 44 文档，扩展模式 48 文档；同时通过 casebook、G3 文档及版本一致性检查。**未宣称 §1.2 原版全量守卫全绿**：原版部分检查会读取禁区，`test_contract_routes.py` 会创建临时文件，本次未原样执行这些检查。

本次未读取 `~/.codex/`、memories 或指定禁区；`attic.md` 仅统计文件大小。未联网、未修改或新建文件、未 commit。首次 shell here-document 和系统 Git 缓存创建尝试均被沙箱拒绝，随后改用无需临时文件的调用方式。
