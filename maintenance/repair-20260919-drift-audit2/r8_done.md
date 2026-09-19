# 施工 R8：完成

按 `maintenance/repair-20260919-drift-audit2/workorder_r8.md` v2 的 §0–§3 完成 D1–D4：5 个参考文档共 11 处整行替换，references 净减少 374 B；9 项守卫全部退出 0。除白名单中的上述文档及本报告外，无其他文件改动。

## 1. §0.1 内容基线校验

施工 HEAD：`8757237fa6ee1164d72b987611f9dce9154c2ff2`。开工工作区为空；指定范围与内容基线 `c16bf8e` 的差异为空。以下命令均实际执行，退出码均为 0；两条无输出命令在记录中保持空输出。

```text
$ git status --short
$ git rev-parse HEAD
8757237fa6ee1164d72b987611f9dce9154c2ff2
$ git diff --stat c16bf8e HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md
```


## 2. 锚点核验与逐条改前→改后 diff

施工前逐处实际执行 `grep -n -F -x -- <整行锚> <目标文件>`。11 处均恰好匹配 1 次，行号与工单完全一致；按工单代码块的 UTF-8 整行字面生成替换。

| 条目 | 文件 | 行号 |
| --- | --- | --- |
| D1 | `references/data-pipeline-solana-scan.md` | 64 |
| D2 | `references/analyze-workflow.md` | 66 |
| D3 | `references/data-pipeline-solana-capture.md` | 237、46、71 |
| D4 | `references/playbook-entity-cluster-tiering.md` | 136 |
| D4 | `references/data-pipeline-evm-channels.md` | 255、259 |
| D4 | `references/data-pipeline-solana-capture.md` | 39、53、83 |

以下是实际 `git diff --no-ext-diff --no-color --unified=0 -- <五个白名单文档>` 输出；每个 hunk 的 `-` 行为改前，`+` 行为改后，完整保留 11 处整行差异。

```diff
diff --git a/references/analyze-workflow.md b/references/analyze-workflow.md
index db91298..d79d0b5 100644
--- a/references/analyze-workflow.md
+++ b/references/analyze-workflow.md
@@ -66 +66 @@
-3. **供给真值闸（v6 新增，重放收尾必跑）**：EVM 先运行 `python3 scripts/evm/observe_supply.py --chain <eth|bsc|base> --token 0x… --as-of-block <冻结块> --out evm_observation_bundle.json --transcript-out evm_observation_transcript.json`，再运行 `python3 scripts/evm/accounting_gate.py --token 0x… --chain <链> --bundle evm_observation_bundle.json --as-of-block <冻结块> --out accounting_mode.json`，最后运行 `python3 scripts/lib/supply_truth_gate.py --chain <链> --token 0x… --as-of-block <冻结块> --replay-stats <replay_stats.json> --observation-bundle evm_observation_bundle.json --out supply_truth.json`，产 `supply-truth-receipt/v4`；Solana 仍产 `supply-truth-receipt/v3`。正式记账重跑产 `accounting-gate/v2`，是发布消费面唯一认可的记账收据；A2 formal 结果为唯一 canonical，与 A0 预检结论不同时以 formal 为准并停止后续阶段等待人工裁决。两者均绑定 target。主规则按形态①对比 `mint−burn` 与链上 `totalSupply()`；EVM 主 FAIL 且拆分统计齐全时，形态②自动要求 `mint==totalSupply`、ZERO/dead 各自与冻结块 `balanceOf` 逐地址相等、两 sink 合计与 burn 闭合。这里只证明终态标量与 sink 逐地址归因闭合；混合形态、旧 stats 或任一观测失败均维持 fail-closed（见 casebook S-01/S-11）。
+3. **供给真值闸（v6 新增，重放收尾必跑）**：EVM 先运行 `python3 scripts/evm/observe_supply.py --chain <eth|bsc|base> --token 0x… --as-of-block <冻结块> --out evm_observation_bundle.json --transcript-out evm_observation_transcript.json`，再运行 `python3 scripts/evm/accounting_gate.py --token 0x… --chain <链> --bundle evm_observation_bundle.json --as-of-block <冻结块> --out accounting_mode.json`，最后运行 `python3 scripts/lib/supply_truth_gate.py --chain <链> --token 0x… --as-of-block <冻结块> --replay-stats <replay_stats.json> --observation-bundle evm_observation_bundle.json --out supply_truth.json`，产 `supply-truth-receipt/v4`；Solana 仍产 `supply-truth-receipt/v3`。EVM 正式记账重跑产 `accounting-gate/v2`，是发布消费面唯一认可的记账收据；A2 formal 结果为唯一 canonical，与 A0 预检结论不同时以 formal 为准并停止后续阶段等待人工裁决。两者均绑定 target。主规则按形态①对比 `mint−burn` 与链上 `totalSupply()`；EVM 主 FAIL 且拆分统计齐全时，形态②自动要求 `mint==totalSupply`、ZERO/dead 各自与冻结块 `balanceOf` 逐地址相等、两 sink 合计与 burn 闭合。这里只证明终态标量与 sink 逐地址归因闭合；混合形态、旧 stats 或任一观测失败均维持 fail-closed（见 casebook S-01/S-11）。
diff --git a/references/data-pipeline-evm-channels.md b/references/data-pipeline-evm-channels.md
index cda55e4..7f8f04e 100644
--- a/references/data-pipeline-evm-channels.md
+++ b/references/data-pipeline-evm-channels.md
@@ -255 +255 @@ size 与 SHA-256；全部通过后才原子将 v2/v3/pre-schema done 升为
-| CEX 归集身份 | 必须核下游对象身份，禁止只凭高入度低出度判 CEX | （判例：casebook/cex-custody.md C-06） |
+| CEX 归集身份 | 必须核下游对象身份，禁止只凭高入度低出度判 CEX | （判例：casebook C-06） |
@@ -259 +259 @@ size 与 SHA-256；全部通过后才原子将 v2/v3/pre-schema done 升为
-| four.meme creator/收币实体 | 同收币地址不得直接判项目方马甲；平台 creator 与收币实体按身份权威规则分账 | （判例：casebook/entity-clustering.md E-12） |
+| four.meme creator/收币实体 | 同收币地址不得直接判项目方马甲；平台 creator 与收币实体按身份权威规则分账 | （判例：casebook E-12） |
diff --git a/references/data-pipeline-solana-capture.md b/references/data-pipeline-solana-capture.md
index 950844a..dfd3464 100644
--- a/references/data-pipeline-solana-capture.md
+++ b/references/data-pipeline-solana-capture.md
@@ -39 +39 @@
-5. **铸造受益人全清单**：创建 tx 的全部铸造受益地址都作为 creator 系起点。（判例：casebook/entity-clustering.md E-12）
+5. **铸造受益人全清单**：创建 tx 的全部铸造受益地址都作为 creator 系起点。（判例：casebook E-12）
@@ -46 +46 @@
-针对"4-5 个月币龄全量 SQD 挂机不现实"的 Plan B 的一个更轻量替代，已在 LAYOFF 跑通：
+已在 LAYOFF 跑通：
@@ -53 +53 @@
-6. **creator 履历与变更**：拉 creator 全发币履历、RugCheck 风险并对比 `set_creator` 前后身份。（判例：casebook/entity-clustering.md E-12）
+6. **creator 履历与变更**：拉 creator 全发币履历、RugCheck 风险并对比 `set_creator` 前后身份。（判例：casebook E-12）
@@ -71 +71 @@
-§8"全程 SQD 重放不现实"与 §9 锚点法的合体升级——14 个月+币龄、13.5 万持仓账户量级标的实战定型：
+14 个月+币龄、13.5 万持仓账户量级标的实战定型：
@@ -83 +83 @@
-6. **letsbonk creator 经济流**：追踪 dev 直分后续流向、Raydium Lock harvest 与毕业迁移平台常数。（判例：casebook/entity-clustering.md E-12）
+6. **letsbonk creator 经济流**：追踪 dev 直分后续流向、Raydium Lock harvest 与毕业迁移平台常数。（判例：casebook E-12）
@@ -237 +237 @@ JSON-RPC batch + 跨地址共享 sig 缓存（`--cache-dir`,按 sig 前 2 字符
-**适用场景**：老 pump.fun 币在内盘（bonding curve）滞留数月甚至一年以上才毕业——内盘期交易稀疏，但**不能不采**：做量脉冲、早期集群、毕业前试盘仓全藏在这段。用 SQD 扫这段 slot 区间在死亡期每响应仅推进 ~3900 slot，工程上极不划算。与 §8 CLUDE"Plan B 混合架构"的分工：那是**高密度短币龄**的取舍方案；本节是**稀疏长内盘期**的全量精确解——稀疏恰恰使逐笔 decode 可行。
+**适用场景**：老 pump.fun 币在内盘（bonding curve）滞留数月甚至一年以上才毕业——内盘期交易稀疏，但**不能不采**：做量脉冲、早期集群、毕业前试盘仓全藏在这段。用 SQD 扫这段 slot 区间在死亡期每响应仅推进 ~3900 slot，工程上极不划算。本节是**稀疏长内盘期**的全量精确解——稀疏恰恰使逐笔 decode 可行。
diff --git a/references/data-pipeline-solana-scan.md b/references/data-pipeline-solana-scan.md
index 28533c7..245b191 100644
--- a/references/data-pipeline-solana-scan.md
+++ b/references/data-pipeline-solana-scan.md
@@ -64 +64 @@
-- 坑预警（Token-2022 实测升级）`[VERIFIED·CLUDE实战]`：先 `getAccountInfo(<MINT>)` 看 mint 归属程序。若是 Token-2022（`TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb`）：①pump.fun 新币标准是 Token-2022，账户主流 dataSize=165 与 170 双形态并存，但**还有零星其他 dataSize**（CLUDE 实测 165/170 双扫漏 14 个账户 0.036% 供应，对账不闭合）——正解是 **api.mainnet-beta 无 dataSize 过滤全扫**（见 §0a Token-2022 行，publicnode 此路 504）+ `memcmp offset=0` 按 mint 过滤；②扫描器默认 `--datasizes auto`：Token-2022 强制 all，SPL 用 165；Token-2022 显式 165/170 会拒绝，账户加总不等于 `getTokenSupply` 也不会写正式 holders 产物。（CLUDE，07-13；2026-08-02 加固）
+- 坑预警（Token-2022 实测升级）`[VERIFIED·CLUDE实战]`：先 `getAccountInfo(<MINT>)` 看 mint 归属程序。若是 Token-2022（`TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb`）：①pump.fun 新币标准是 Token-2022，账户主流 dataSize=165 与 170 双形态并存，但**还有零星其他 dataSize**（CLUDE 实测 165/170 双扫漏 14 个账户 0.036% 供应，对账不闭合）——正解是 **api.mainnet-beta 无 dataSize 过滤全扫**（见 §0a Token-2022 行，publicnode 此路 504）+ `memcmp offset=0` 按 mint 过滤；②扫描器不按 dataSize 过滤，`--datasizes` 仅兼容；Token-2022 显式 165/170 会拒绝，账户加总不等于 `getTokenSupply` 也不会写正式 holders 产物。（CLUDE，07-13；2026-08-02 加固）
diff --git a/references/playbook-entity-cluster-tiering.md b/references/playbook-entity-cluster-tiering.md
index 0072872..48faf19 100644
--- a/references/playbook-entity-cluster-tiering.md
+++ b/references/playbook-entity-cluster-tiering.md
@@ -136 +136 @@
-翻案见 casebook/cex-custody.md C-06；案源：GOAT、IQ 2026-07-26。
+翻案见 casebook C-06；案源：GOAT、IQ 2026-07-26。
```


逐文件将施工 HEAD 的原始内容仅按工单指定行替换，再与落盘内容逐字节比较，结果如下；所有非指定行均未变：

```text
PASS references/analyze-workflow.md: lines 66; all other bytes unchanged
PASS references/data-pipeline-evm-channels.md: lines 255,259; all other bytes unchanged
PASS references/data-pipeline-solana-capture.md: lines 39,46,53,71,83,237; all other bytes unchanged
PASS references/data-pipeline-solana-scan.md: lines 64; all other bytes unchanged
PASS references/playbook-entity-cluster-tiering.md: lines 136; all other bytes unchanged
SKILL.md = 8021 B
commands-staging/*.md = 8789 B
references/*.md references/casebook/*.md references/labels/*.md = 929154 B
PASS: exactly 11 whole-line replacements in 5 whitelisted files; references delta = -374 B
```


`git diff --check` 实际执行，退出码为 0，原始输出为空。

## 3. §1.1 字节实测

仅使用文件元数据 `stat().st_size` 按三个指定范围求和，未读取 `references/attic.md` 内容。

| 范围 | 开工前（B） | 完成后（B） | 工单要求（B） |
| --- | ---: | ---: | ---: |
| `SKILL.md` | 8021 | 8021 | 8021 |
| `commands-staging/*.md` 合计 | 8789 | 8789 | 8789 |
| `references/*.md references/casebook/*.md references/labels/*.md` 合计 | 929528 | 929154 | 929154 |

三组实测全部符合要求；references 差额为 `929154 - 929528 = -374 B`。

## 4. §1.2 各守卫原始输出

以下 9 条命令均离线实际运行，退出码均为 0。执行环境设置 `PYTHONDONTWRITEBYTECODE=1`，避免生成字节码文件；守卫脚本及其参数均未修改。代码块保留各命令的原始输出。

### 1. `python3 scripts/tests/docs_lint.py`

```text
PASS: 45 个文档，引用无断链、粗体配对完整
```

退出码：`0`。

### 2. `python3 scripts/tests/docs_lint.py --all`

```text
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

退出码：`0`。

### 3. `python3 scripts/tests/casebook_lint.py`

```text
casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
```

退出码：`0`。

### 4. `python3 scripts/tests/changelog_lint.py`

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 80 条 + 归档 139 条
```

退出码：`0`。

### 5. `python3 scripts/tests/test_contract_routes.py`

```text
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
```

退出码：`0`。

### 6. `python3 scripts/tests/test_sixlens_docs.py`

```text
PASS: 六视角批⑤大小口径与 archive 路由
```

退出码：`0`。

### 7. `python3 scripts/tests/test_g3_docs_guards.py`

```text
PASS: F-08 A0 exploration command
PASS: F-08 A2 formal rerun order
PASS: F-13 runner injection boundary
PASS: F-05 machine boundary
```

退出码：`0`。

### 8. `python3 scripts/tests/test_version_consistency.py`

```text
PASS: M-03 version metadata consistent at 9.0.1
```

退出码：`0`。

### 9. `python3 scripts/tests/test_commands_deploy_sync.py`

```text
PASS: 4 份 staging/部署命令 SHA-256 逐文件一致
```

退出码：`0`。

## 5. §1.3 git diff --stat

命令：`git diff --stat`。实际输出如下，仅含 §0.3 白名单参考文档：

```text
 references/analyze-workflow.md                |  2 +-
 references/data-pipeline-evm-channels.md      |  4 ++--
 references/data-pipeline-solana-capture.md    | 12 ++++++------
 references/data-pipeline-solana-scan.md       |  2 +-
 references/playbook-entity-cluster-tiering.md |  2 +-
 5 files changed, 11 insertions(+), 11 deletions(-)
```


本报告为按工单新建的未跟踪文件，未执行 `git add`，因此不计入上述 `git diff --stat`。

## 6. 差异与停工点

无工单偏差，无停工点。D1、D2 各 1 行，D3 共 3 行，D4 共 6 行，合计 11 行；均采用工单给定的替换整行，未猜测锚点、扩大范围或修改其他片段。

未执行 commit、push 或部署；未改动 `scripts/`、`commands-staging/`、`CHANGELOG.md` 或两份 manifest；未删除文件或目录，未联网。

## 7. 禁读披露

本次未读取 `~/.codex/` 下任何文件，未读取该目录的 memories，也未启动插件搜索。未主动读取本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/` 或 `references/attic.md` 的内容；`attic.md` 仅通过文件元数据计入字节总数。`maintenance/` 下仅访问本工程目录 `maintenance/repair-20260919-drift-audit2/`。

工单指定守卫脚本已原样运行；脚本自身既有的文档遍历属于 §0.2／用户纪律第 5 条明确允许的行为，未据此另行打开禁读文件。

