# 工单 R3：v9.0.1 口径漂移与文档-代码不符 3 条纯文本修复 v1

内容基线：`0a53cbd`（R2 施工落地后的内容态；施工 HEAD 可含 maintenance/ 提交，但 §0.1 差异校验须为空）。来源：盲审 R3a 3 条（`blind_r3a_report.md` D1–D3，全 minor，Fable 逐条亲核两侧原文属实）；R3b 报 0 条。本单全部为纯文本修复，零代码改动，只动 `references/scan-schemas.md`；**所有锚与替换文本均为代码块内整行片段，不含首尾空白**（表格行的 `\|` 是 markdown 单元格内竖线转义，按字面保留）。

## §0 施工纪律
0.1 开工先确认 `git status --short` 为空并记录施工 HEAD；`git diff --stat 0a53cbd HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md` 须为空，不符即停工汇报。
0.2 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）、`archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（§1.1 统计字节时 attic.md 只计大小不读内容；守卫脚本自身遍历文档属被测代码既有行为，允许并要求原样运行）；`maintenance/` 下只读本工程目录。
0.3 **白名单**：`references/scan-schemas.md`，以及新建 `maintenance/repair-20260919-drift-audit2/r3_done.md`。
0.4 删除 > 修改 > 新增；每处锚先 `grep -n -F` 核验恰 1 处且行号一致；不符停工；只动指定片段，锚外一字不动。
0.5 不 commit、不 push、不部署；不改 `scripts/`、`commands-staging/`、`CHANGELOG.md`、两份 manifest。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` 合计 = 8789 不变；references 三组 glob（`references/*.md references/casebook/*.md references/labels/*.md`）合计 ≤ 930260（基线 930079；Fable 本机按六处替换逐字模拟净增 +156 B → 930235，实测数写入报告）。本轮为 schema 字段表补正类型与条件，无可删冗余，净增不可避免。
1.2 守卫全绿：`python3 scripts/tests/docs_lint.py`、`docs_lint.py --all`、`casebook_lint.py`、`changelog_lint.py`、`test_contract_routes.py`、`test_sixlens_docs.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`、`test_commands_deploy_sync.py`，原始输出贴进 r3_done.md。
1.3 `git diff --stat` 只含 §0.3 白名单。

## §2 逐条施工（锚均已由 Fable `grep -c -F` 验为恰 1 处；行号以 `0a53cbd` 内容态为准）

### D1（R3a D1）`--live-canary` 被写成位图切片对表
`references/scan-schemas.md:714`。锚：
```
有效 verdict 为 INCONCLUSIVE；--live-canary 重拉若干段与位图切片对表。
```
→
```
有效 verdict 为 INCONCLUSIVE。
```
依据 `scripts/solana/sqd_coverage_probe.py` 的 parser 无 `--live-canary`；该参数属 `scripts/solana/sqd_gap_repair.py:1549` 的 `verify` 子命令，`:1507-1508` 抽 slot 重拉 `reference-getBlock`，`scripts/lib/solana_exact_validate.py:1404-1405` 只比 blockhash 与交易签名，不对位图切片。删除错误承诺（删除优先）。

### D2（R3a D2）缺块分支 `sqd_blockhash` 为 null，字段表限定 string
`references/scan-schemas.md:795`。锚：
```
| `census[].sqd_blockhash` | string | 是 |  |
```
→
```
| `census[].sqd_blockhash` | string\|null | 是 | 缺 SQD 区块（result=confirmed_missing_block）时为 null |
```
依据 `scripts/solana/sqd_gap_repair.py:1193`（`sqd_blockhash is None` → `confirmed_missing_block`）、`:1202`（原样写出 `payload.get("sqd_blockhash")`）；同表 `:793` 已列 `confirmed_missing_block` 为合法 result。类型写法沿用同表 `:690` 的 `string\|null`。

### D3（R3a D3）共享地图回退对象元数据为 null、canary 为空，字段表无条件要求完整值（四行）
`references/scan-schemas.md:688`、`:689`、`:691`、`:695`。锚→替换（各恰 1 处）：
```
| `shared_map.version` | string | 是 |  |
```
→
```
| `shared_map.version` | string\|null | 是 | 地图校验失败回退时本字段与 sha256/generated_at 为 null、canary.slots 为空 |
```
```
| `shared_map.sha256` | string (sha256 hex) | 是 |  |
```
→
```
| `shared_map.sha256` | string (sha256 hex)\|null | 是 |  |
```
```
| `shared_map.generated_at` | string | 是 |  |
```
→
```
| `shared_map.generated_at` | string\|null | 是 |  |
```
```
| `shared_map.canary.slots` | array[integer] | 是 | 长度64 |
```
→
```
| `shared_map.canary.slots` | array[integer] | 是 | 复用成功时长度 64；回退时为空 |
```
依据 `scripts/solana/sqd_coverage_probe.py:675-680`（回退诊断对象初值 version/sha256/generated_at=None、canary.slots=[]）、`:783-784`（校验失败返回该对象）、`:1333`（原样写入产物 `shared_map`）；顶层 `:667` 的 `object\|null` 与 `:709` 回退原因说明不动。

## §3 完成报告 `r3_done.md` 必含
①逐条改前→改后 diff；②§1.1 字节实测（三组数）；③§1.2 各守卫原始输出；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
