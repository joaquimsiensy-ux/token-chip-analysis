# 工单 R3：v9.0.1 口径漂移与文档-代码不符 3 条纯文本修复 v2

内容基线：`0a53cbd`（R2 施工落地后的内容态；施工 HEAD 可含 maintenance/ 提交，但 §0.1 差异校验须为空）。来源：盲审 R3a 3 条（`blind_r3a_report.md` D1–D3，全 minor，Fable 逐条亲核两侧原文属实）；R3b 报 0 条。本单全部为纯文本修复，零代码改动，只动 `references/scan-schemas.md`；v2 吸收 codex 复核 r1（`review_wo3_reply.md`）：D1 改整行锚、D2 只补类型、D3 删去"回退一律为 null/为空"的过强说明并补 :667 总览行的 `slots[64]`；**所有锚与替换文本均为代码块内整行片段，不含首尾空白**（表格行的 `\|` 是 markdown 单元格内竖线转义，按字面保留）。

## §0 施工纪律
0.1 开工先确认 `git status --short` 为空并记录施工 HEAD；`git diff --stat 0a53cbd HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md` 须为空，不符即停工汇报。
0.2 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）、`archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（§1.1 统计字节时 attic.md 只计大小不读内容；守卫脚本自身遍历文档属被测代码既有行为，允许并要求原样运行）；`maintenance/` 下只读本工程目录。
0.3 **白名单**：`references/scan-schemas.md`，以及新建 `maintenance/repair-20260919-drift-audit2/r3_done.md`。
0.4 删除 > 修改 > 新增；每处锚先 `grep -n -F` 核验恰 1 处且行号一致；不符停工；只动指定片段，锚外一字不动。
0.5 不 commit、不 push、不部署；不改 `scripts/`、`commands-staging/`、`CHANGELOG.md`、两份 manifest。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` 合计 = 8789 不变；references 三组 glob（`references/*.md references/casebook/*.md references/labels/*.md`）合计 ≤ 930260（基线 930079；七处替换按 UTF-8 字面模拟净减 6 B → 930073，复核 r1 独立重算一致，实测数写入报告）。
1.2 守卫全绿：`python3 scripts/tests/docs_lint.py`、`docs_lint.py --all`、`casebook_lint.py`、`changelog_lint.py`、`test_contract_routes.py`、`test_sixlens_docs.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`、`test_commands_deploy_sync.py`，原始输出贴进 r3_done.md。
1.3 `git diff --stat` 只含 §0.3 白名单。

## §2 逐条施工（锚均为**整行**，已由 Fable `grep -c -F -x` 验为恰 1 处；行号以 `0a53cbd` 内容态为准）

### D1（R3a D1）`--live-canary` 被写成位图切片对表
`references/scan-schemas.md:714`。锚（整行）：
```
- array_monotonic_unique 与 array_in_range 是生产时对原始响应数组的断言结果；任一为 false 则该段 unconfirmed，其 NO_HEADER 保持未确认，有效 verdict 为 INCONCLUSIVE；--live-canary 重拉若干段与位图切片对表。
```
→
```
- array_monotonic_unique 与 array_in_range 是生产时对原始响应数组的断言结果；任一为 false 则该段 unconfirmed，其 NO_HEADER 保持未确认，有效 verdict 为 INCONCLUSIVE。
```
依据 `scripts/solana/sqd_coverage_probe.py` 的 parser 无 `--live-canary`；该参数属 `scripts/solana/sqd_gap_repair.py:1549` 的 `verify` 子命令，`:1507-1508` 抽 slot 重拉 `reference-getBlock`，`scripts/lib/solana_exact_validate.py:1404-1405` 只比 blockhash 与交易签名，不对位图切片。删除错误承诺（删除优先）。

### D2（R3a D2）缺块分支 `sqd_blockhash` 为 null，字段表限定 string
`references/scan-schemas.md:795`。锚（整行）：
```
| `census[].sqd_blockhash` | string | 是 |  |
```
→
```
| `census[].sqd_blockhash` | string\|null | 是 |  |
```
依据 `scripts/solana/sqd_gap_repair.py:1193`（`sqd_blockhash is None` → `confirmed_missing_block`）、`:1202`（原样写出）；同表 `:793` 已列 `confirmed_missing_block` 为合法 result，不必重复说明。类型写法沿用同文件 `:690` 的 `string\|null`。

### D3（R3a D3）共享地图回退对象元数据可为 null、canary 可为空，字段表无条件要求完整值（五行）
`references/scan-schemas.md:667`、`:688`、`:689`、`:691`、`:695`，各自整行独立替换（锚→替换依次）：
```
| `shared_map` | object\|null | 是 | asset_path,version,sha256,supersedes,generated_at,reused_ranges,unverified_ranges,recheck_stats,canary{slots[64],counts_sha256,verified_at} |
```
→
```
| `shared_map` | object\|null | 是 | asset_path,version,sha256,supersedes,generated_at,reused_ranges,unverified_ranges,recheck_stats,canary{slots,counts_sha256,verified_at} |
```
```
| `shared_map.version` | string | 是 |  |
```
→
```
| `shared_map.version` | string\|null | 是 |  |
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
| `shared_map.canary.slots` | array[integer] | 是 | 长度0或64；复用成功时为64 |
```
依据 `scripts/solana/sqd_coverage_probe.py:675-680`（回退诊断对象初值 version/sha256/generated_at=None、canary.slots=[]）；`:694-696` 中途填入元数据、`:757-761` 填入 64 项已验证 canary，其后校验失败（如 `:763-764` 区间不重叠）不会清空已填值；`:783-784` 返回当时的 info，`:1333` 写入产物。因此回退对象允许元数据为 null、canary 为空，也可能保留已填值，文档只放宽类型与长度、不写"一律为空"。共享地图**资产**侧的 64 项要求（`validate_shared_map`）不动。

## §3 完成报告 `r3_done.md` 必含
①逐条改前→改后 diff；②§1.1 字节实测（三组数）；③§1.2 各守卫原始输出；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
