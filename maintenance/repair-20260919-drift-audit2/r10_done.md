# 施工 R10：完成

按 `maintenance/repair-20260919-drift-audit2/workorder_r10.md` v2 §0–§3 完成。仅替换 `references/data-pipeline-solana-scan.md:67` 的指定整行，并新建本报告。正文实际净变动为 `-21 B`，九项守卫均通过。

## 0. 开工内容基线与锚点

施工 HEAD：`9983ba8d78879284a26acd0dde3a78c743385a70`；内容基线：`4353454`。开工工作区为空，指定内容范围与基线的差异为空。以下为实际执行命令和原始输出；无输出的命令保持空输出，不填入占位内容。

```text
$ git status --short
```

退出码：`0`。

```text
$ git rev-parse HEAD
9983ba8d78879284a26acd0dde3a78c743385a70
```

退出码：`0`。

```text
$ git diff --stat 4353454 HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md
```

退出码：`0`。

使用 `grep -n -F -x` 按工单整行字面核验，恰好 1 处且位于第 67 行；替换前字节数和 UTF-8 模拟净变动一并核验：

```text
$ grep -n -F -x -- <工单 §2 原整行锚> references/data-pipeline-solana-scan.md
67:- **G8 离线重放契约**：`holders_snapshot_meta.json` 绑定的每个 GPA `raw_artifact` 不是“有文件有哈希”即算通过；identity emitter/check 必须调用 `scan_token_accounts.py` 的同一套 `parse_gpa_response`＋`parse_token_accounts`，从原始 RPC JSON 重做 base64 解码、跨 dataSlice/pubkey 去重、账户明细和 owner 聚合，并要求逐条等于 `holders_accounts.json`/`holders_owners.json`；同时解析 supply receipt 的 `result.value.amount` 与 `supply_raw` 闭合。round4b 格式存量若 raw/supply 实物完整可直接重新 emit；缺失或重放不一致则必须重跑 `scan_token_accounts.py`，禁止手补 meta/hash。
anchor_count = 1; anchor_line = 67; PASS
SKILL.md: 8021 B
commands-staging/*.md: 8789 B
references three globs: 929131 B
simulated UTF-8 delta: -21 B
```

## 1. 改前 → 改后 diff

```diff
diff --git a/references/data-pipeline-solana-scan.md b/references/data-pipeline-solana-scan.md
index 245b191..177489f 100644
--- a/references/data-pipeline-solana-scan.md
+++ b/references/data-pipeline-solana-scan.md
@@ -64,7 +64,7 @@
 - 坑预警（Token-2022 实测升级）`[VERIFIED·CLUDE实战]`：先 `getAccountInfo(<MINT>)` 看 mint 归属程序。若是 Token-2022（`TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb`）：①pump.fun 新币标准是 Token-2022，账户主流 dataSize=165 与 170 双形态并存，但**还有零星其他 dataSize**（CLUDE 实测 165/170 双扫漏 14 个账户 0.036% 供应，对账不闭合）——正解是 **api.mainnet-beta 无 dataSize 过滤全扫**（见 §0a Token-2022 行，publicnode 此路 504）+ `memcmp offset=0` 按 mint 过滤；②扫描器不按 dataSize 过滤，`--datasizes` 仅兼容；Token-2022 显式 165/170 会拒绝，账户加总不等于 `getTokenSupply` 也不会写正式 holders 产物。（CLUDE，07-13；2026-08-02 加固）
 - 冒烟与交叉校验：正式扫描前先 `getTokenSupply(<MINT>)`（链上总供应）+ `getTokenLargestAccounts(<MINT>)`（top 20 token account）各打一发，扫描结果的总和与 top 榜必须能对上（IO 实录：扫描加总 799,211,891 vs getTokenSupply 799,211,890.5，个位级吻合）。
 - 解码要点：dataSlice 返回 base64，解码后 `bytes[0:32]` = owner（base58 编码回地址串，可纯 Python 手写无外部依赖）、`bytes[32:40]` = amount（u64 LE 原始数）；UI 数量换算用 `getTokenSupply` 返回的 `decimals`，不要自己去 mint 账户抠字节。
-- **G8 离线重放契约**：`holders_snapshot_meta.json` 绑定的每个 GPA `raw_artifact` 不是“有文件有哈希”即算通过；identity emitter/check 必须调用 `scan_token_accounts.py` 的同一套 `parse_gpa_response`＋`parse_token_accounts`，从原始 RPC JSON 重做 base64 解码、跨 dataSlice/pubkey 去重、账户明细和 owner 聚合，并要求逐条等于 `holders_accounts.json`/`holders_owners.json`；同时解析 supply receipt 的 `result.value.amount` 与 `supply_raw` 闭合。round4b 格式存量若 raw/supply 实物完整可直接重新 emit；缺失或重放不一致则必须重跑 `scan_token_accounts.py`，禁止手补 meta/hash。
+- **G8 离线重放契约**：`holders_snapshot_meta.json` 绑定的每个 GPA `raw_artifact` 不是“有文件有哈希”即算通过；identity emitter/check 必须调用 `scan_token_accounts.py` 的同一套 `parse_gpa_response`＋`parse_token_accounts`，从原始 RPC JSON 重做 base64 解码、跨 dataSlice/pubkey 去重、账户明细和 owner 聚合，并要求逐条等于 `holders_accounts.json`/`holders_owners.json`；同时解析 supply receipt 的 `result.value.amount` 与 `supply_raw` 闭合。存量 producer 哈希须匹配当前扫描器且 raw/supply 重放一致，否则重跑 `scan_token_accounts.py`，禁止手补 meta/hash。
 - 供给基线双口径纪律：链上实查总供应（精确到个位）与 CMC/CoinGecko 流通量是两套数——流通量链上算不出来，必须借第三方口径。全文分开使用、分开标注来源，禁止混用。
 - 分层默认档位（按供应量级可调）：`≥100万 / 10–100万 / 1–10万 / 1千–1万 / <1千` 五档，产出集中度画像表——它是整份报告的定量地基。
 - 扫描副产品 = 老鼠仓排查输入：统计 Top N 每个 owner 的 token account 数量、余额分布、建仓时间同步性，排查蚂蚁搬家式多钱包暗仓；**阴性结论也写进报告**（防读者高估链上暗仓风险）。
```

另以 `git show HEAD:references/data-pipeline-solana-scan.md` 的字节内容作比较：施工后的文件严格等于仅替换指定整行一次的结果；其余字节不变。新整行锚仍唯一且位于第 67 行。

## 2. §1.1 字节实测

统计使用文件 `stat().st_size`，未读取文件内容；`references/attic.md` 仅计文件大小。

| 范围 | 改前（B） | 改后实测（B） | 工单要求（B） | 净变动（B） |
| --- | ---: | ---: | ---: | ---: |
| `SKILL.md` | 8021 | 8021 | 8021 | 0 |
| `commands-staging/*.md` 合计 | 8789 | 8789 | 8789 | 0 |
| `references/*.md references/casebook/*.md references/labels/*.md` 合计 | 929131 | 929110 | 929110 | -21 |

替换后验证的原始输出：

```text
Exact whole-line replacement only: PASS
New anchor unique at line 67: PASS
SKILL.md: 8021 B
commands-staging/*.md: 8789 B
references three globs: 929110 B
Actual file delta: -21 B
```

## 3. §1.2 各守卫原始输出

以下九项命令均按工单原样执行，全部退出码为 `0`。输出逐字保留。

### 1. `python3 scripts/tests/docs_lint.py`

```text
$ python3 scripts/tests/docs_lint.py
PASS: 45 个文档，引用无断链、粗体配对完整
```

退出码：`0`。

### 2. `python3 scripts/tests/docs_lint.py --all`

```text
$ python3 scripts/tests/docs_lint.py --all
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

退出码：`0`。

### 3. `python3 scripts/tests/casebook_lint.py`

```text
$ python3 scripts/tests/casebook_lint.py
casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
```

退出码：`0`。

### 4. `python3 scripts/tests/changelog_lint.py`

```text
$ python3 scripts/tests/changelog_lint.py
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 80 条 + 归档 139 条
```

退出码：`0`。

### 5. `python3 scripts/tests/test_contract_routes.py`

```text
$ python3 scripts/tests/test_contract_routes.py
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
```

退出码：`0`。

### 6. `python3 scripts/tests/test_sixlens_docs.py`

```text
$ python3 scripts/tests/test_sixlens_docs.py
PASS: 六视角批⑤大小口径与 archive 路由
```

退出码：`0`。

### 7. `python3 scripts/tests/test_g3_docs_guards.py`

```text
$ python3 scripts/tests/test_g3_docs_guards.py
PASS: F-08 A0 exploration command
PASS: F-08 A2 formal rerun order
PASS: F-13 runner injection boundary
PASS: F-05 machine boundary
```

退出码：`0`。

### 8. `python3 scripts/tests/test_version_consistency.py`

```text
$ python3 scripts/tests/test_version_consistency.py
PASS: M-03 version metadata consistent at 9.0.1
```

退出码：`0`。

### 9. `python3 scripts/tests/test_commands_deploy_sync.py`

```text
$ python3 scripts/tests/test_commands_deploy_sync.py
PASS: 4 份 staging/部署命令 SHA-256 逐文件一致
```

退出码：`0`。

## 4. git diff --stat 与范围检查

```text
$ git diff --stat
 references/data-pipeline-solana-scan.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

退出码：`0`。

`git diff --stat` 仅显示已跟踪文件的改动，因此本次新建、尚未跟踪的 `maintenance/repair-20260919-drift-audit2/r10_done.md` 不计入上面的输出。白名单范围为该正文文件及本报告。

守卫执行后、创建本报告前的状态原始输出：

```text
$ git status --short --untracked-files=all
 M references/data-pipeline-solana-scan.md
```

退出码：`0`。

空白字符检查原始输出：

```text
$ git diff --check
```

退出码：`0`。

## 5. 差异与停工点

- 无工单内容偏离；基线、原锚唯一性、第 67 行位置、整行替换、字节数和全部守卫均满足要求，未触发停工条件。
- 辅助路径枚举命令首次因 shell 引号未闭合退出 `1`（原始报错：`zsh:1: unmatched '`）；已修正并重跑成功。该命令未改动文件，不属于守卫失败或基线、锚点不符。
- 未修改 `scripts/`、`commands-staging/`、`CHANGELOG.md` 或两份 manifest；未 commit、未 push、未部署。

## 6. 禁读披露

- 本轮未读取 `~/.codex/` 下任何文件，包括插件、技能与 memories。
- 未自行读取本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/` 的内容；`references/attic.md` 仅通过 `stat` 统计字节。
- `maintenance/` 下仅访问本工程目录 `maintenance/repair-20260919-drift-audit2/`。
- 所列守卫脚本按原样运行；脚本自身既有的文档遍历行为采用工单 §0.2 与用户指令第 5 条明确授权的例外。

