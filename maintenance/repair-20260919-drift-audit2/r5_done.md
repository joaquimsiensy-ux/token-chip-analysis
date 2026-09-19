# 施工 R5：完成

按 `workorder_r5.md` v2 的 §0–§3 执行。D1、D2、D3 共四处整行替换、两处整行删除；九项守卫全部通过。三份目标文档除指定片段外逐字节不变。无差异、无停工点。

## 1. §0.1 开工基线（实际执行与原始输出）

内容基线为 `de569f3`；施工 HEAD 为 `b88fca773d4132658b2c1b361ec388cf0a1dae77`。开工工作区干净，指定内容范围的基线差异为空。

### 工作区状态

命令：`git status --short`；退出码：`0`。原始输出为空。

```text
```

### 施工 HEAD

命令：`git rev-parse HEAD`；退出码：`0`。原始输出如下。

```text
b88fca773d4132658b2c1b361ec388cf0a1dae77
```

### 内容基线校验

命令：`git diff --stat de569f3 HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md`；退出码：`0`。原始输出为空。

```text
```

## 2. 整行锚核验

写入前对六处工单整行锚实际执行 `grep -n -F -x -- <整行字面锚> <目标文件>`，均恰好命中一处，且行号与工单一致；未猜测或扩大修改范围。

| 项目 | 文件 | 工单行号 | 实测行号 | 命中数 |
| --- | --- | ---: | ---: | ---: |
| D1 | `references/split-run.md` | 15 | 15 | 1 |
| D2a | `references/casebook/supply-accounting.md` | 35 | 35 | 1 |
| D2b | `references/casebook/supply-accounting.md` | 36 | 36 | 1 |
| D3a | `references/data-pipeline-evm-channels.md` | 208 | 208 | 1 |
| D3b | `references/data-pipeline-evm-channels.md` | 210 | 210 | 1 |
| D3c | `references/data-pipeline-evm-channels.md` | 211 | 211 | 1 |

## 3. 逐条改前 → 改后 diff

### D1：补齐 −1 示例中的 `full` 档位

````diff
diff --git a/references/split-run.md b/references/split-run.md
index de5571a..880b0a5 100644
--- a/references/split-run.md
+++ b/references/split-run.md
@@ -12,7 +12,7 @@
 
 ```
 用户在 codex CLI（主轨 GPT-5.6）："对 <币> 跑 −1（机械段）"
-  或 CC 开 Opus 会话（备轨）跑 /token-analyze-1 <币> [链]
+  或 CC 开 Opus 会话（备轨）跑 /token-analyze-1 <币> full [链]
         ↓ 产物全部落 <币>分析/ 工作目录，完成即停
 用户手动新开 Fable 5 会话（CC），同目录跑 /token-analyze-2 <币> full
         ↓ −2 判断收口：报告正文成稿＋产 a5_assembly_workorder.json，完成即停
````

### D2：两行仅替换指定短语

`无 sig 去重` → `旧五元组去重`；`无 sig 数据不得判重` → `旧五元组不得判重`。S-04 六字段结构不变。

```diff
diff --git a/references/casebook/supply-accounting.md b/references/casebook/supply-accounting.md
index abe7a8f..f0d8bd0 100644
--- a/references/casebook/supply-accounting.md
+++ b/references/casebook/supply-accounting.md
@@ -32,8 +32,8 @@
 ## S-04 跟踪集按现仓筛选——历史清零层全盲（已装机械闸 wave_scan） 【机制成立】
 
 - **触发现象**：构建深挖/跟踪名单的环节，名单来源是"当前余额 top N"/现仓快照/现役达标实体表；且分析问题涉及全生命周期（演变/换手/第几轮控盘）。同族的 12 个可操作触发场景：①常规 factory/pair 清单不含 V4 单例；②目标 Pancake V3 池按 Uniswap V3 topic 采集后无报错但为 0 行；③先排除池/路由的 `key_edges` 又被拿来解释来源去向；④负载均衡 RPC 台账与最新 `balanceOf` 不等；⑤缓存台账只有入腿或出腿被截断；⑥浏览器持有人榜少报或整址漏榜；⑦GPA 错误体或旧缓存被二跑静默复用；⑧大额变动地址只抽样定性；⑨无 sig 边出现同 slot/同双方/同额多笔；⑩锚点采样只覆盖窗口内活动地址且连续多日无观测；⑪末日强制封口后各闸全绿但倒数第二日到末日任一阵营跳变 >1pp；⑫签名提及 ATA、但 `postTokenBalances` 没有该 ATA。
-- **失败原因（禁止推断）**：现役名单里没有＝历史上从未存在（按现仓筛选对已清零地址物理不可见，漏检静默发生、无任何自检报警）；阵营图上散户带收缩默认解读为"散户离场"（PYTHIA 案该时段实为 63% 控盘波次换手）；**"有历史大户兜底桶"＝"历史层处理完了"（桶存在≠桶内被检验过——桶里可能藏着整个协同波次）**。同样禁止把常规池清单当全池、把静默 0 行当无交易、把筛选边/缓存/榜单当完整真值、把无 sig 去重当无损、把末日闭合当中段正确，或把缺失 ATA 余额填成 0。
-- **必做区分检验**：①重放全期**逐地址 max 持仓**，按 max≥实体门槛筛跟踪集（而非现仓）；②③已代码化为 `scripts/report/wave_scan.py` 四指纹机械扫描（同窗建仓聚类×喂币专属度×集中清仓窗×等额面额组，阈值全用合并口径）——名册定稿前必跑，候选逐条裁决完毕前历史大户兜底桶不准关闸（analyze-workflow A3.6 硬闸；split-run 下 wave_scan_report.json 为 READY 必产件）。回收去向追踪（候选波次的 recycle_top 字段）：回市场还是进后续实体——后者是两轮同一控制人的关键证据（PYTHIA 案 7.85% 直入后续体系吸筹仓）。对新增 12 场景逐案执行：V4 单例补入池清单并核毛量占比；Pancake/Uniswap topic 与 data 布局分开且目标池 0 行即阻断；以 `daily_delta` 对筛选边做缺口审计；RPC 台账逐钱包对最新 `balanceOf`、历史曲线另用 archive 快照重建；浏览器榜只找候选；GPA 返回体须含合法 result、命中缓存报告 mtime、增量前真扫，冲突先用第三通道查 2–3 个关键址；大额变动地址 100% 定性；无 sig 数据不得判重，正负成对差异须用 ATA tx 级真值替换受害地址；中段数值用日采样或全重放并执行末两日 >1pp 阻断；ATA 不在 `postTokenBalances` 就跳过该采样点、保持前值。
+- **失败原因（禁止推断）**：现役名单里没有＝历史上从未存在（按现仓筛选对已清零地址物理不可见，漏检静默发生、无任何自检报警）；阵营图上散户带收缩默认解读为"散户离场"（PYTHIA 案该时段实为 63% 控盘波次换手）；**"有历史大户兜底桶"＝"历史层处理完了"（桶存在≠桶内被检验过——桶里可能藏着整个协同波次）**。同样禁止把常规池清单当全池、把静默 0 行当无交易、把筛选边/缓存/榜单当完整真值、把旧五元组去重当无损、把末日闭合当中段正确，或把缺失 ATA 余额填成 0。
+- **必做区分检验**：①重放全期**逐地址 max 持仓**，按 max≥实体门槛筛跟踪集（而非现仓）；②③已代码化为 `scripts/report/wave_scan.py` 四指纹机械扫描（同窗建仓聚类×喂币专属度×集中清仓窗×等额面额组，阈值全用合并口径）——名册定稿前必跑，候选逐条裁决完毕前历史大户兜底桶不准关闸（analyze-workflow A3.6 硬闸；split-run 下 wave_scan_report.json 为 READY 必产件）。回收去向追踪（候选波次的 recycle_top 字段）：回市场还是进后续实体——后者是两轮同一控制人的关键证据（PYTHIA 案 7.85% 直入后续体系吸筹仓）。对新增 12 场景逐案执行：V4 单例补入池清单并核毛量占比；Pancake/Uniswap topic 与 data 布局分开且目标池 0 行即阻断；以 `daily_delta` 对筛选边做缺口审计；RPC 台账逐钱包对最新 `balanceOf`、历史曲线另用 archive 快照重建；浏览器榜只找候选；GPA 返回体须含合法 result、命中缓存报告 mtime、增量前真扫，冲突先用第三通道查 2–3 个关键址；大额变动地址 100% 定性；旧五元组不得判重，正负成对差异须用 ATA tx 级真值替换受害地址；中段数值用日采样或全重放并执行末两日 >1pp 阻断；ATA 不在 `postTokenBalances` 就跳过该采样点、保持前值。
 - **证据要求（证据不足时的结论上限）**：无全量历史数据（仅现仓快照）时，结论上限＝"现役结构如下；历史清零层未检测，无法排除已退场控盘波次"；禁写"历史无控盘"。任一新增场景的真值核验做不了时，只能声明相应池/边/地址/时段未闭合并阻断其数值结论；不得用零行、榜单、缓存、插值或填零代替缺失证据。装闸验收还必须请**闸外的人来试着绕它**，否则不能把自造 fixture 的通过当作防绕结论。
 - **正确规则指针**：analyze-workflow A3.6 三道互补防线硬闸＋wave_scan.py 头注（PYTHIA 回测基线）。新增场景的现役动作见 `data-pipeline-evm-channels.md` 与 `data-pipeline-solana-capture.md`
 - **案源**：出处：PYTHIA W1 前置波次 2026-07-29（重做版整体漏检 341 址峰值 63.44% 波次，交叉核实逐位复算翻案，用户终裁）；V4 清单哈基米 2026-07-18；Pancake topic SIREN 2026-07-19；筛选边 QUQ 2026-07-22；RPC 单腿 ASTEROID 2026-07；榜单 TOSHI 2026-07-26；缓存 PUB、抽样 CLUDE（均 2026-07-15）；无 sig 去重 TROLL 2026-07-29；锚点末日封口 GOAT 2026-07-26；缺失 ATA 填零 GOAT 2026-07。案源详见本条前述列表；返工过程已迁历史记录。
```

### D3：修正断点续传说明，删除两处旧脚本说明

替换原第 208 行；整行删除原第 210、211 行及各自行尾换行。原第 209 行保持不变。

```diff
diff --git a/references/data-pipeline-evm-channels.md b/references/data-pipeline-evm-channels.md
index abf4074..e848062 100644
--- a/references/data-pipeline-evm-channels.md
+++ b/references/data-pipeline-evm-channels.md
@@ -205,10 +205,8 @@ size 与 SHA-256；全部通过后才原子将 v2/v3/pre-schema done 升为
 ### 3.3 bloXroute getLogs 扫块
 
 正式操作入口为 `scripts/evm/scan_bloxroute_seg.py`。旧 `scan_transfers.py` 仅保留历史/诊断用途，不得作为正式或冷启动主线。
-- 断点续传：done-segments 清单跳过已完成段；多线程必留失败段，扫完自动列 remaining 并补扫，remaining=0 才算采集完成。（OPN，07）
+- 断点续传：`<out>.done.json` 记已完成段，重跑跳过；收尾 `fails=` 最多列 20 个失败段，须重跑补采至 `fails=[]`。（OPN，07）
 - 起始块定位：勿用 eth_getCode 二分找部署块（免费节点历史状态请求被拒，会找错块导致空扫秒退）；改按"块时间戳 >= 已知安全起始日期"二分，起始日期用 GMGN start_holding_at 或跨链铸造日锚定，多扫无害。（OPN/SIREN，07）
-- 同脚本顺带采时间戳锚点：每隔固定块距 eth_getBlockByNumber 取块头时间戳（数百个锚点几分钟采完），分析期 bisect 线性插值，省数千次逐块 RPC。（OPN，07）
-- **起点缓存坑**：`<chain>_scan_meta.json` 缓存 start_block/head，改 config 的 start_time_utc 后必须删除该文件才会重新二分，否则沿用旧起点空跑。（哈基米，07-18）
 - HTTP 客户端用 subprocess 调系统 curl（或 requests），绝不裸 urllib——macOS 证书链坑两次会话都踩过。（OPN/SIREN，07）
 
 ### 3.4 Etherscan V2（scripts/evm/fetch_etherscan.py，仅 ETH 主网）
```

## 4. §1.1 字节实测

按文件 UTF-8 实际字节大小统计，references 三组 glob 仅取文件大小；其中 `references/attic.md` 只调用 `stat` 计大小，未读取内容。

| 范围 | 开工基线（B） | 完成实测（B） | 变化（B） | 结果 |
| --- | ---: | ---: | ---: | --- |
| `SKILL.md` | 8021 | 8021 | 0 | 保持不变 |
| `commands-staging/*.md` 合计 | 8789 | 8789 | 0 | 保持不变 |
| `references/*.md references/casebook/*.md references/labels/*.md` 合计 | 929965 | 929549 | -416 | 不高于基线，与工单模拟一致 |

完整校验的原始输出：

```text
PASS: references/split-run.md: only workorder line edits; all other bytes unchanged
PASS: references/casebook/supply-accounting.md: only workorder line edits; all other bytes unchanged
PASS: references/data-pipeline-evm-channels.md: only workorder line edits; all other bytes unchanged
PASS: only the 3 whitelisted source files changed; index empty; HEAD unchanged
SKILL.md = 8021 B
commands-staging/*.md = 8789 B
references/*.md references/casebook/*.md references/labels/*.md = 929549 B
references delta = -416 B
PASS: all byte limits satisfied
```

## 5. §1.2 守卫原始输出

以下九个命令均按原命令执行，全部退出码为 0；输出原样保留。`casebook_lint.py` 为 6 册 38 条通过。

### docs_lint

命令：`python3 scripts/tests/docs_lint.py`；退出码：`0`。原始输出如下。

```text
PASS: 45 个文档，引用无断链、粗体配对完整
```

### docs_lint_all

命令：`python3 scripts/tests/docs_lint.py --all`；退出码：`0`。原始输出如下。

```text
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

### casebook_lint

命令：`python3 scripts/tests/casebook_lint.py`；退出码：`0`。原始输出如下。

```text
casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
```

### changelog_lint

命令：`python3 scripts/tests/changelog_lint.py`；退出码：`0`。原始输出如下。

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 80 条 + 归档 139 条
```

### test_contract_routes

命令：`python3 scripts/tests/test_contract_routes.py`；退出码：`0`。原始输出如下。

```text
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
```

### test_sixlens_docs

命令：`python3 scripts/tests/test_sixlens_docs.py`；退出码：`0`。原始输出如下。

```text
PASS: 六视角批⑤大小口径与 archive 路由
```

### test_g3_docs_guards

命令：`python3 scripts/tests/test_g3_docs_guards.py`；退出码：`0`。原始输出如下。

```text
PASS: F-08 A0 exploration command
PASS: F-08 A2 formal rerun order
PASS: F-13 runner injection boundary
PASS: F-05 machine boundary
```

### test_version_consistency

命令：`python3 scripts/tests/test_version_consistency.py`；退出码：`0`。原始输出如下。

```text
PASS: M-03 version metadata consistent at 9.0.1
```

### test_commands_deploy_sync

命令：`python3 scripts/tests/test_commands_deploy_sync.py`；退出码：`0`。原始输出如下。

```text
PASS: 4 份 staging/部署命令 SHA-256 逐文件一致
```

## 6. git diff --stat 与白名单

### git diff --stat

命令：`git diff --stat`；退出码：`0`。原始输出如下。

```text
 references/casebook/supply-accounting.md | 4 ++--
 references/data-pipeline-evm-channels.md | 4 +---
 references/split-run.md                  | 2 +-
 3 files changed, 4 insertions(+), 6 deletions(-)
```

上述原始 `git diff --stat` 仅含 §0.3 的三份目标文档。本报告为新建、未暂存文件，普通 `git diff --stat` 不显示未跟踪文件；本次新增文件仅为 `maintenance/repair-20260919-drift-audit2/r5_done.md`。未执行 `git add`、commit、push 或部署。

### 差异空白检查

命令：`git diff --check`；退出码：`0`。原始输出为空。

```text
```

## 7. 差异／停工点

无。内容基线、六处锚的唯一性及行号、三组字节数、九项守卫均符合工单。已用施工 HEAD 中三份文档的原始字节重建工单预期结果，与落盘内容逐字节一致，其他行未变。

未修改 `scripts/`、`commands-staging/`、`CHANGELOG.md`、两份 manifest；施工 HEAD 未变化，暂存区无修改。

## 8. 禁读披露

本轮未读取 `~/.codex/` 下任何文件，未读取 memories，未执行插件启动搜索。未主动读取本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md` 的内容；`attic.md` 仅在字节统计中计入文件大小。`maintenance/` 下只读取本工程目录 `maintenance/repair-20260919-drift-audit2/`。

守卫脚本按原命令执行；其自身遍历文档属于用户明确允许的被测代码既有行为。本轮全程离线，无外部数据请求。
