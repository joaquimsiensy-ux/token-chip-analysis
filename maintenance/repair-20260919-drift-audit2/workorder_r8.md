# 工单 R8：v9.0.1 口径漂移与文档-代码不符 4 条纯文本修复 v1

内容基线：`c16bf8e`（R7 施工落地后的内容态；施工 HEAD 可含 maintenance/ 提交，但 §0.1 差异校验须为空）。来源：盲审 R8a 1 条 minor＋1 条待确认（Fable 亲核升为发现）（`blind_r8a_report.md`）＋ R8b 2 条 nit（`blind_r8b_report.md`），共 4 条、5 文件、9 行；Fable 逐条亲核两侧原文属实。本单全部为纯文本修复，零代码改动；**所有锚均为目标文件整行原文，按代码块内整行字面处理**。

## §0 施工纪律
0.1 开工先确认 `git status --short` 为空并记录施工 HEAD；`git diff --stat c16bf8e HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md` 须为空，不符即停工汇报。
0.2 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）、`archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（§1.1 统计字节时 attic.md 只计大小不读内容；守卫脚本自身遍历文档属被测代码既有行为，允许并要求原样运行）；`maintenance/` 下只读本工程目录。
0.3 **白名单**：`references/data-pipeline-solana-scan.md`、`references/analyze-workflow.md`、`references/data-pipeline-solana-capture.md`、`references/data-pipeline-evm-channels.md`、`references/playbook-entity-cluster-tiering.md`，以及新建 `maintenance/repair-20260919-drift-audit2/r8_done.md`。
0.4 删除 > 修改 > 新增；每处锚必须是目标文件整行原文，以 `grep -n -F -x` 核验恰 1 处且行号一致；不符停工；按整行替换，其他行不动。
0.5 不 commit、不 push、不部署；不改 `scripts/`、`commands-staging/`、`CHANGELOG.md`、两份 manifest。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` 合计 = 8789 不变；references 三组 glob（`references/*.md references/casebook/*.md references/labels/*.md`）合计 = 929324（基线 929528；九处整行替换按 UTF-8 字面模拟净减 204 B：D1 -2、D2 +4、D3 -92、D4 -114；实测数写入报告，须等于该值）。
1.2 守卫全绿：`python3 scripts/tests/docs_lint.py`、`docs_lint.py --all`、`casebook_lint.py`、`changelog_lint.py`、`test_contract_routes.py`、`test_sixlens_docs.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`、`test_commands_deploy_sync.py`，原始输出贴进 r8_done.md。
1.3 `git diff --stat` 只含 §0.3 白名单。

## §2 逐条施工（锚均为整行，已由 Fable 逐行匹配验为恰 1 处；行号以 `c16bf8e` 内容态为准）

### D1（R8a D1）扫描器默认 dataSize 过滤说明与现行观测请求不符
`references/data-pipeline-solana-scan.md:64`。锚（整行）：
```
- 坑预警（Token-2022 实测升级）`[VERIFIED·CLUDE实战]`：先 `getAccountInfo(<MINT>)` 看 mint 归属程序。若是 Token-2022（`TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb`）：①pump.fun 新币标准是 Token-2022，账户主流 dataSize=165 与 170 双形态并存，但**还有零星其他 dataSize**（CLUDE 实测 165/170 双扫漏 14 个账户 0.036% 供应，对账不闭合）——正解是 **api.mainnet-beta 无 dataSize 过滤全扫**（见 §0a Token-2022 行，publicnode 此路 504）+ `memcmp offset=0` 按 mint 过滤；②扫描器默认 `--datasizes auto`：Token-2022 强制 all，SPL 用 165；Token-2022 显式 165/170 会拒绝，账户加总不等于 `getTokenSupply` 也不会写正式 holders 产物。（CLUDE，07-13；2026-08-02 加固）
```
→
```
- 坑预警（Token-2022 实测升级）`[VERIFIED·CLUDE实战]`：先 `getAccountInfo(<MINT>)` 看 mint 归属程序。若是 Token-2022（`TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb`）：①pump.fun 新币标准是 Token-2022，账户主流 dataSize=165 与 170 双形态并存，但**还有零星其他 dataSize**（CLUDE 实测 165/170 双扫漏 14 个账户 0.036% 供应，对账不闭合）——正解是 **api.mainnet-beta 无 dataSize 过滤全扫**（见 §0a Token-2022 行，publicnode 此路 504）+ `memcmp offset=0` 按 mint 过滤；②扫描器 `--datasizes` 仅兼容参数，一律不按 dataSize 过滤；Token-2022 显式 165/170 会拒绝，账户加总不等于 `getTokenSupply` 也不会写正式 holders 产物。（CLUDE，07-13；2026-08-02 加固）
```
依据 `scripts/lib/solana_observation.py:400-405`（filters 仅 `memcmp offset=0 mint`，无 dataSize；两程序同一路径）、`scripts/solana/scan_token_accounts.py:149-150`（`--datasizes` 注明 compatibility option）、`:212-213`（仅 Token-2022 显式非 auto/all 拒绝）、`:60`（`choose_datasizes` 在 `main` 内无调用）。

### D2（R8a 待确认项，Fable 亲核升为发现）记账收据版本句未限定链族
`references/analyze-workflow.md:66`。锚（整行）：
```
3. **供给真值闸（v6 新增，重放收尾必跑）**：EVM 先运行 `python3 scripts/evm/observe_supply.py --chain <eth|bsc|base> --token 0x… --as-of-block <冻结块> --out evm_observation_bundle.json --transcript-out evm_observation_transcript.json`，再运行 `python3 scripts/evm/accounting_gate.py --token 0x… --chain <链> --bundle evm_observation_bundle.json --as-of-block <冻结块> --out accounting_mode.json`，最后运行 `python3 scripts/lib/supply_truth_gate.py --chain <链> --token 0x… --as-of-block <冻结块> --replay-stats <replay_stats.json> --observation-bundle evm_observation_bundle.json --out supply_truth.json`，产 `supply-truth-receipt/v4`；Solana 仍产 `supply-truth-receipt/v3`。正式记账重跑产 `accounting-gate/v2`，是发布消费面唯一认可的记账收据；A2 formal 结果为唯一 canonical，与 A0 预检结论不同时以 formal 为准并停止后续阶段等待人工裁决。两者均绑定 target。主规则按形态①对比 `mint−burn` 与链上 `totalSupply()`；EVM 主 FAIL 且拆分统计齐全时，形态②自动要求 `mint==totalSupply`、ZERO/dead 各自与冻结块 `balanceOf` 逐地址相等、两 sink 合计与 burn 闭合。这里只证明终态标量与 sink 逐地址归因闭合；混合形态、旧 stats 或任一观测失败均维持 fail-closed（见 casebook S-01/S-11）。
```
→
```
3. **供给真值闸（v6 新增，重放收尾必跑）**：EVM 先运行 `python3 scripts/evm/observe_supply.py --chain <eth|bsc|base> --token 0x… --as-of-block <冻结块> --out evm_observation_bundle.json --transcript-out evm_observation_transcript.json`，再运行 `python3 scripts/evm/accounting_gate.py --token 0x… --chain <链> --bundle evm_observation_bundle.json --as-of-block <冻结块> --out accounting_mode.json`，最后运行 `python3 scripts/lib/supply_truth_gate.py --chain <链> --token 0x… --as-of-block <冻结块> --replay-stats <replay_stats.json> --observation-bundle evm_observation_bundle.json --out supply_truth.json`，产 `supply-truth-receipt/v4`；Solana 仍产 `supply-truth-receipt/v3`。EVM 正式记账重跑产 `accounting-gate/v2`，是发布消费面唯一认可的记账收据；A2 formal 结果为唯一 canonical，与 A0 预检结论不同时以 formal 为准并停止后续阶段等待人工裁决。两者均绑定 target。主规则按形态①对比 `mint−burn` 与链上 `totalSupply()`；EVM 主 FAIL 且拆分统计齐全时，形态②自动要求 `mint==totalSupply`、ZERO/dead 各自与冻结块 `balanceOf` 逐地址相等、两 sink 合计与 burn 闭合。这里只证明终态标量与 sink 逐地址归因闭合；混合形态、旧 stats 或任一观测失败均维持 fail-closed（见 casebook S-01/S-11）。
```
依据 `scripts/solana/accounting_gate_sol.py:137`（Solana 写 `accounting-gate/v1`）、`scripts/report/shared_release_receipt.py:1716-1724`（EVM 要求 v2、Solana 要求 v1）、`references/independent-audit-protocol.md:164`（已按链族分写）。只加"EVM "三字节+空格，其余逐字不动。

### D3（R8b D1）§15 指向现行 §8 中不存在的"CLUDE Plan B 混合架构"
`references/data-pipeline-solana-capture.md:237`。锚（整行）：
```
**适用场景**：老 pump.fun 币在内盘（bonding curve）滞留数月甚至一年以上才毕业——内盘期交易稀疏，但**不能不采**：做量脉冲、早期集群、毕业前试盘仓全藏在这段。用 SQD 扫这段 slot 区间在死亡期每响应仅推进 ~3900 slot，工程上极不划算。与 §8 CLUDE"Plan B 混合架构"的分工：那是**高密度短币龄**的取舍方案；本节是**稀疏长内盘期**的全量精确解——稀疏恰恰使逐笔 decode 可行。
```
→
```
**适用场景**：老 pump.fun 币在内盘（bonding curve）滞留数月甚至一年以上才毕业——内盘期交易稀疏，但**不能不采**：做量脉冲、早期集群、毕业前试盘仓全藏在这段。用 SQD 扫这段 slot 区间在死亡期每响应仅推进 ~3900 slot，工程上极不划算。本节是**稀疏长内盘期**的全量精确解——稀疏恰恰使逐笔 decode 可行。
```
依据同文件 §8（:30-42）无 Plan B 定义、:46 仅一句提及无定义。删去失效比较半句，保留"本节是稀疏长内盘期…"。

### D4（R8b D2）C-06/E-12 六处引用指向主册，条目实在 `-methods` 续册
改法沿用文档既有"判例见 casebook C-07"不带路径惯例（全库同款已有多处），把 `casebook/cex-custody.md C-06`→`casebook C-06`、`casebook/entity-clustering.md E-12`→`casebook E-12`，比补路径更短。依据 `references/casebook/cex-custody-methods.md:5`、`references/casebook/entity-clustering-methods.md:5`（条目所在）；主册 `cex-custody.md`/`entity-clustering.md` 无 C-06/E-12 标题。六处整行：

`references/playbook-entity-cluster-tiering.md:136`。锚（整行）：
```
翻案见 casebook/cex-custody.md C-06；案源：GOAT、IQ 2026-07-26。
```
→
```
翻案见 casebook C-06；案源：GOAT、IQ 2026-07-26。
```

`references/data-pipeline-evm-channels.md:255`。锚（整行）：
```
| CEX 归集身份 | 必须核下游对象身份，禁止只凭高入度低出度判 CEX | （判例：casebook/cex-custody.md C-06） |
```
→
```
| CEX 归集身份 | 必须核下游对象身份，禁止只凭高入度低出度判 CEX | （判例：casebook C-06） |
```

`references/data-pipeline-evm-channels.md:259`。锚（整行）：
```
| four.meme creator/收币实体 | 同收币地址不得直接判项目方马甲；平台 creator 与收币实体按身份权威规则分账 | （判例：casebook/entity-clustering.md E-12） |
```
→
```
| four.meme creator/收币实体 | 同收币地址不得直接判项目方马甲；平台 creator 与收币实体按身份权威规则分账 | （判例：casebook E-12） |
```

`references/data-pipeline-solana-capture.md:39`。锚（整行）：
```
5. **铸造受益人全清单**：创建 tx 的全部铸造受益地址都作为 creator 系起点。（判例：casebook/entity-clustering.md E-12）
```
→
```
5. **铸造受益人全清单**：创建 tx 的全部铸造受益地址都作为 creator 系起点。（判例：casebook E-12）
```

`references/data-pipeline-solana-capture.md:53`。锚（整行）：
```
6. **creator 履历与变更**：拉 creator 全发币履历、RugCheck 风险并对比 `set_creator` 前后身份。（判例：casebook/entity-clustering.md E-12）
```
→
```
6. **creator 履历与变更**：拉 creator 全发币履历、RugCheck 风险并对比 `set_creator` 前后身份。（判例：casebook E-12）
```

`references/data-pipeline-solana-capture.md:83`。锚（整行）：
```
6. **letsbonk creator 经济流**：追踪 dev 直分后续流向、Raydium Lock harvest 与毕业迁移平台常数。（判例：casebook/entity-clustering.md E-12）
```
→
```
6. **letsbonk creator 经济流**：追踪 dev 直分后续流向、Raydium Lock harvest 与毕业迁移平台常数。（判例：casebook E-12）
```


## §3 完成报告 `r8_done.md` 必含
①逐条改前→改后 diff；②§1.1 字节实测（三组数）；③§1.2 各守卫原始输出；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
