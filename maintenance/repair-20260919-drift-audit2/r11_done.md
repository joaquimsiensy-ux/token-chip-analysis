# 施工 R11：完成

按 `workorder_r11.md` v2 执行。D1、D2 已按工单整行替换，其他行逐字节不变；9 项守卫全部通过。仅修改两份白名单文档，并新建本报告；未 commit、push 或部署。

## 1. §0.1 开工基线

内容基线：`8f73554`。施工 HEAD：`f883449c5d5613e0f98c798968abfbccee11a2b6`。

`git status --short`

退出码：`0`。原始输出为空。

```text
```

`git rev-parse HEAD`

退出码：`0`。

```text
f883449c5d5613e0f98c798968abfbccee11a2b6
```

`git diff --stat 8f73554 HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md`

退出码：`0`。原始输出为空。

```text
```

工作区开工时干净，指定内容路径相对 `8f73554` 的差异统计为空，满足开工条件。

## 2. 锚点与逐条改前 → 改后 diff

实际使用 `grep -n -F -x --` 核验整行锚；`--` 仅用于终止选项解析，确保 D2 行首的 `-` 按字面处理。两个原锚各匹配 1 处，行号分别为 61、20。

```text
D1: grep -n -F -x -- [workorder literal anchor] references/data-pipeline-solana-capture.md
61:1. **新全量快照**：`scan_token_accounts.py`（Token-2022 记得 `--rpc api.mainnet-beta` + 先把旧 `_gpa_raw_*` 改名存档，见 §9.8）；同时 `getTokenSupply` 复验供给闭合（窗口内销毁体现在总量差）。
D1: matches=1, line=61, UTF-8 delta=+5 B
D2: grep -n -F -x -- [workorder literal anchor] references/data-pipeline-robinhood-methods.md
20:- **★gas_trace_bs 只抓普通 tx，会整体漏掉 internal 转账入金**（VIRTUAL 实测：Safe 部署者军资表面 464E 实际 1,699E 差 8 倍——73% 经 Across SpokePool 以 internal 交付）——大额资金溯源必须补 `/addresses/{a}/internal-transactions`（浏览器 UA）；"资金链断头"结论在补查 internal 前不得下（VIRTUAL 复核，07-16）
D2: matches=1, line=20, UTF-8 delta=-10 B
```

D1：将 RPC 参数改为完整公共 URL，删除“记得 ”和“同时 ”，净增加 5 B。D2：仅删除“ 差 8 倍”，净减少 10 B。

`git diff --no-ext-diff --no-color -- references/data-pipeline-solana-capture.md references/data-pipeline-robinhood-methods.md` 的原始输出：

```diff
diff --git a/references/data-pipeline-robinhood-methods.md b/references/data-pipeline-robinhood-methods.md
index 93e4256..bead776 100644
--- a/references/data-pipeline-robinhood-methods.md
+++ b/references/data-pipeline-robinhood-methods.md
@@ -17,7 +17,7 @@
 - **Virtuals Team 金库（金库1）性质判定三步**（RAXOL 实测 2026-07-14，补旧报告"性质未验证"空白）：①getCode——实测为 0age 最小代理（`0x3d3d3d3d363d3d37363d73<impl>5af43d…`，44B），实现未验证 ②`owner()`（selector 0x8da5cb5b）——返回 Virtuals 跨项目 keeper `0x81f7ca…`（即平台托管，非项目方自持私钥）③平台 API tokenomics 拿正式解锁表（见 channels 分册通道表）。标准 vesting selector（start/duration/beneficiary/unlockTime）全不响应，属 Virtuals 自有托管模板；表述纪律："解锁表=平台注册承诺+托管合约形态"，非纯链上可验证铁证。
 - **Virtuals 平台侧情报直查**：`api.virtuals.io/api/virtuals?filters[tokenAddress]=<addr>`（走代理）一次拿 creator 钱包/DAO/veToken/TBA/内盘 pair/tokenomics 解锁表/projectMembers（团队推特）；virtualId=该链第 N 个毕业 agent。veVEX 类 sVEX 的质押物是 V2 LP 而非本币（assetToken() 实查）；**LP 锁定验证**：V2 pair 的 LP token holders 若 100% 在 ve 合约=毕业 LP 全锁（撤池风险排除），一次 RPC balanceOf 即可验。
 
-- **★gas_trace_bs 只抓普通 tx，会整体漏掉 internal 转账入金**（VIRTUAL 实测：Safe 部署者军资表面 464E 实际 1,699E 差 8 倍——73% 经 Across SpokePool 以 internal 交付）——大额资金溯源必须补 `/addresses/{a}/internal-transactions`（浏览器 UA）；"资金链断头"结论在补查 internal 前不得下（VIRTUAL 复核，07-16）
+- **★gas_trace_bs 只抓普通 tx，会整体漏掉 internal 转账入金**（VIRTUAL 实测：Safe 部署者军资表面 464E 实际 1,699E——73% 经 Across SpokePool 以 internal 交付）——大额资金溯源必须补 `/addresses/{a}/internal-transactions`（浏览器 UA）；"资金链断头"结论在补查 internal 前不得下（VIRTUAL 复核，07-16）
 - **★纯 LP-token 持有地址是溯源候选集的结构性盲区**：候选集只用代币持仓榜会漏掉 LP 层实体（VIRTUAL 实测：一个五地址集群持主池 LP 5.83%=第 4 大 LP 实体，代币口径峰值仅 0.64% 不入任何榜，靠对抗复核翻出；其中两仓各恰 1,500.0000 LP 的整数指纹早已可见但未深挖）——报价币/主池型标的做 LP 集中度分析时，**LP 持有人榜必须独立生成溯源候选**（VIRTUAL 复核，07-16）
 - **Blockscout holders 快照有瞬态伪影**：快照可能恰好拍到某地址"收币后、卖出前"的分钟级窗口（实测一个显示 1.56% 的"大户"实为 2 分钟过手通道）——大户名单以全量重放末态为准，快照只作对账参照（VIRTUAL，07-16）
 - **★0xb92fe925（Relay）是多身份设施，"经过它"读不出方向语义**：既是 App 代币交付金库（本币侧双向：入=市场买入、转给它=同 tx 原子落池卖出，GME 增量已验），**又是 RelayRouterV3 公共 swap 路由（原生 ETH 侧：multicall 收 ETH 换出 USDG 等稳定币回到发起人）**——把"9.81E 转给它"读成"App 黑箱提现"是错的，实为 swap；真正的跨链出境是**下一笔** USDG 转入 RelayDepository（`0x4cd00e38…`，Relay 桥存管）。判定资金出境=看稳定币是否进 Depository，不看是否碰过 0xb92fe（Pointless 二次增量对抗复核，07-17）
diff --git a/references/data-pipeline-solana-capture.md b/references/data-pipeline-solana-capture.md
index dfd3464..a6fd1cb 100644
--- a/references/data-pipeline-solana-capture.md
+++ b/references/data-pipeline-solana-capture.md
@@ -58,7 +58,7 @@
 
 旧研报为锚点法（非全量流水重放）时，增量更新**不必补拉全量转账**，走快照对比五步：
 
-1. **新全量快照**：`scan_token_accounts.py`（Token-2022 记得 `--rpc api.mainnet-beta` + 先把旧 `_gpa_raw_*` 改名存档，见 §9.8）；同时 `getTokenSupply` 复验供给闭合（窗口内销毁体现在总量差）。
+1. **新全量快照**：`scan_token_accounts.py`（Token-2022 `--rpc https://api.mainnet-beta.solana.com` + 先把旧 `_gpa_raw_*` 改名存档，见 §9.8）；`getTokenSupply` 复验供给闭合（窗口内销毁体现在总量差）。
 2. **快照 diff**：`snapshot_diff.py --old 旧owners --new 新owners --entities 实体表` → 实体逐址变动 + 大额变动榜（新面孔/清零标注）。**排名变化不是证据**（持有人增多会把静止地址挤出 topN），一切以余额 Δ 为准。
 3. **窗口变动全覆盖定性**：`probe_window_moves.py --targets 变动榜 --cutoff <ISO时间>` → 每址 pool_buy/pool_sell/direct_transfer 分类 + 直转对汇总；大额变动地址必须 100% 覆盖，直转对按对手方 |Δ|。（判例：casebook/supply-accounting.md S-04）
 4. **对账三查（轻量版）**：新快照加总=getTokenSupply（diff=0）；top20 与 `getTokenLargestAccounts` 双源对表（活跃池允许时点差）；重点地址签名史净额 vs 快照 Δ 分毫互验。
```

替换后以 `8f73554` 对应文件为基准，仅替换工单指定行生成预期字节，再与工作区完整文件比较；同时核验新行仍唯一且行号不变：

```text
61:1. **新全量快照**：`scan_token_accounts.py`（Token-2022 `--rpc https://api.mainnet-beta.solana.com` + 先把旧 `_gpa_raw_*` 改名存档，见 §9.8）；`getTokenSupply` 复验供给闭合（窗口内销毁体现在总量差）。
D1: exact workorder replacement; all other bytes unchanged; delta=+5 B
20:- **★gas_trace_bs 只抓普通 tx，会整体漏掉 internal 转账入金**（VIRTUAL 实测：Safe 部署者军资表面 464E 实际 1,699E——73% 经 Across SpokePool 以 internal 交付）——大额资金溯源必须补 `/addresses/{a}/internal-transactions`（浏览器 UA）；"资金链断头"结论在补查 internal 前不得下（VIRTUAL 复核，07-16）
D2: exact workorder replacement; all other bytes unchanged; delta=-10 B
```

## 3. §1.1 字节实测

全部以文件 `stat().st_size` 求和；统计 `references/attic.md` 时仅取大小，不读取内容。

| 范围 | 施工前（B） | 施工后（B） | 工单要求（B） | 结果 |
| --- | ---: | ---: | ---: | --- |
| `SKILL.md` | 8021 | 8021 | 8021 | 通过 |
| `commands-staging/*.md` 合计 | 8789 | 8789 | 8789 | 通过 |
| `references/*.md references/casebook/*.md references/labels/*.md` 合计 | 929110 | 929105 | 929105 | 通过 |

施工前原始输出：

```text
SKILL.md: 8021 B
commands-staging/*.md: 8789 B
references/*.md references/casebook/*.md references/labels/*.md: 929110 B
```

施工后原始输出（总净变化 -5 B）：

```text
SKILL.md: 8021 B
commands-staging/*.md: 8789 B
references/*.md references/casebook/*.md references/labels/*.md: 929105 B
```

## 4. §1.2 守卫原始输出

`python3 scripts/tests/docs_lint.py`

退出码：`0`。

```text
PASS: 45 个文档，引用无断链、粗体配对完整
```

`python3 scripts/tests/docs_lint.py --all`

退出码：`0`。

```text
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

`python3 scripts/tests/casebook_lint.py`

退出码：`0`。

```text
casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
```

`python3 scripts/tests/changelog_lint.py`

退出码：`0`。

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 80 条 + 归档 139 条
```

`python3 scripts/tests/test_contract_routes.py`

退出码：`0`。

```text
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
```

`python3 scripts/tests/test_sixlens_docs.py`

退出码：`0`。

```text
PASS: 六视角批⑤大小口径与 archive 路由
```

`python3 scripts/tests/test_g3_docs_guards.py`

退出码：`0`。

```text
PASS: F-08 A0 exploration command
PASS: F-08 A2 formal rerun order
PASS: F-13 runner injection boundary
PASS: F-05 machine boundary
```

`python3 scripts/tests/test_version_consistency.py`

退出码：`0`。

```text
PASS: M-03 version metadata consistent at 9.0.1
```

`python3 scripts/tests/test_commands_deploy_sync.py`

退出码：`0`。

```text
PASS: 4 份 staging/部署命令 SHA-256 逐文件一致
```

## 5. §1.3 git diff --stat 与白名单

`git diff --stat`

退出码：`0`。

```text
 references/data-pipeline-robinhood-methods.md | 2 +-
 references/data-pipeline-solana-capture.md    | 2 +-
 2 files changed, 2 insertions(+), 2 deletions(-)
```

统计只含两份白名单文档。本报告为新增未跟踪文件，普通 `git diff --stat` 不列出未跟踪文件；未执行暂存操作。

`git diff --check`

退出码：`0`。原始输出为空。

```text
```

## 6. 差异 / 停工点

最终内容与工单要求一致，无未解决项。未发生内容基线不符、锚点不唯一或行号不符，未触发工单规定的停工条件。

执行纠正记录：首次核验 D2 时，`grep` 缺少 `--`，将以 `-` 开头的锚误作选项而报错；当时未修改文件，补上 `--` 后重新核验两处锚均通过。D2 首次编辑误写临时占位文本，随即仅在原目标行按工单纠正；所有替换后字节核验、diff 和守卫均在纠正之后运行。最终两个文件分别只有工单指定的一行变化。

未修改 `scripts/`、`commands-staging/`、`CHANGELOG.md`、两份 manifest 或任何其他非白名单受版本控制文件。

## 7. 禁读披露

未读取 `~/.codex/` 下任何文件，未读取启动 memories；未读取本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/` 或 `references/attic.md` 的内容。`maintenance/` 下仅访问本工程目录 `maintenance/repair-20260919-drift-audit2/`。字节统计对 `references/attic.md` 仅调用 `stat`。守卫按工单原样运行，其自身既有文档遍历属于工单明确允许的行为。

全程离线，未调用外部数据、网络、API 或插件；未读取密钥登记文件。

