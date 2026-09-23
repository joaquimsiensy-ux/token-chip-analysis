# T3 完成：目录案消费期重算完整身份已落地，版本升至 9.0.5

施工范围按工单 T3 v2：目录身份重算与签名身份全等，文件时间校验分支逐字不变。三条 RED 已在未修改生产代码的基线上取得，新增 test_17 覆盖全部六步。生产改动为 +4/−1，按增删合计 5 行，未超过 12 行上限。定向结果见下表；EVM 纵切片受沙箱限制，changelog_lint/run_all 留调度方验收。

## 开工基线与施工锚

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`。以下输出在任何文件修改之前取得：

```text
$ git status --short
（stdout 为空，exit 0）

$ git rev-parse --short HEAD
492b53c
（exit 0）

$ git merge-base --is-ancestor 2197505 HEAD
（stdout 为空，exit 0）

$ git diff --quiet 2197505 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
（stdout 为空，exit 0）
```

首次修改前，对全部九个施工锚逐一使用 `grep -n -F -x -- '<整行原文>' <文件>`，断言输出恰好一行且行号等于工单指定值；同时通过 `git show 2197505:<文件>` 核对对应基线行。结果：

```text
scripts/report/shared_release_receipt.py: 39:from anchor_point_contract import (LEGACY_FINAL_BLOCK_EDGE_KIND, V2_SCHEMA,
scripts/report/shared_release_receipt.py: 1047:            # 清单正文 input 须与签名身份全等，目录只做案根内存在性检查，不重算哈希
scripts/report/shared_release_receipt.py: 1059:                     "signed directory identity is not a directory inside the case root")
scripts/tests/test_anchor_plan_v3.py: 600:def main():
VERSION: 1:9.0.4
pyproject.toml: 15:version = "9.0.4"
SKILL.md: 23:<!-- skill-version-source: VERSION; skill-version: 9.0.4 -->
CHANGELOG.md: 13:- **9.0.4**（2026-09-23）登记旧 time-spotcheck/v3 哈希并接通 EVM 时间收据两层校验，恢复存量文件案兼容；补充同一输入目录用法。schema 不变，版本档位 修。
CHANGELOG.md: 101:## [9.0.4] - 2026-09-23 — 时间抽查历史生产者登记与发布两层校验接线
ALL 9 ANCHORS PASS (working tree and 2197505)
```

已核对原 1055–1059 行：`directory = Path(str(identity.get("path") or ""))`，随后依次检查绝对路径、末级非 symlink、resolve 后为目录、resolve 后位于案根内；源码事实与工单一致。

## RED 证据

完整可复现命令、代码、stdout、stderr 和退出码见 [T3_red_evidence.txt](T3_red_evidence.txt)。命令为 `PYTHONDONTWRITEBYTECODE=1 python3 -B - <<'PY'`，在同一原始签名目录夹具中依次完成三次独立篡改，每次恢复后均再次断言放行；未重签或刷新清单。基线 HEAD 为 492b53c，生产源码与 2197505 一致。

| RED | 实际操作命令（Python） | 基线输出 |
| --- | --- | --- |
| 同长度覆写 | `logs.write_bytes(original[:-1] + bytes([original[-1] ^ 1])); accepted()` | `RED-1: same-length logs.parquet last-byte flip STILL ACCEPTED` |
| 删除叶子 | `blocks.rename(root / "blocks.bak"); accepted()` | `RED-2: blocks.parquet removed from identity root STILL ACCEPTED` |
| 新增叶子 | `extra.write_bytes(b"t3-extra-leaf"); accepted()` | `RED-3: extra.bin added STILL ACCEPTED` |

三次均先验证基线放行，篡改仍放行，恢复后仍放行；完整脚本 exit 0。删除步骤使用同案根、身份根外的预先不存在路径 `root/blocks.bak`，目录中保留 logs。

## 逐条施工结果

以下行号为修改后的实际文件行号，来源为 `git diff --unified=0 2197505`：

| 工单条目 | 文件与实际行号 | 改动行数与结果 |
| --- | --- | --- |
| §2.1(a) | `scripts/report/shared_release_receipt.py:39` | +1：在 anchor_point_contract import 前导入 input_identity |
| §2.1(b) | `scripts/report/shared_release_receipt.py:1048` | +1/−1：订正完整目录身份重算注释 |
| §2.1(c) | `scripts/report/shared_release_receipt.py:1061–1062` | +2：调用 input_identity(directory)[0] 与 identity 全等比较，无局部异常包装 |
| §2.2 | `scripts/tests/test_anchor_plan_v3.py:600–657` | +58：新增 test_17；main 自然移至 658，无接线改动 |
| §2.3 VERSION | `VERSION:1` | +1/−1：9.0.4 → 9.0.5 |
| §2.3 pyproject | `pyproject.toml:15` | +1/−1：9.0.4 → 9.0.5 |
| §2.3 SKILL | `SKILL.md:23` | +1/−1：仅版本号 |
| §2.3 CHANGELOG 索引 | `CHANGELOG.md:13` | +1：原工单整行，UTF-8 176 B（不计换行），≤ 200 B |
| §2.3 CHANGELOG 详细段 | `CHANGELOG.md:102–108` | +7：标题、四条说明、空行；含成本、兼容范围和待验事项 |

生产文件合计 **+4/−1，净增 3 行，增删合计 5 行 ≤ 12**。将 2197505 原文仅应用工单三处精确替换后，与当前生产文件全文比较相等；因此文件分支、既有后续逻辑、错误文本和外层 authority-chain 异常上下文均逐字不变。新增公开函数、模块常量均为 0。

test_17 包含：原始目录放行；logs 同长度翻转末字节拒收；extra.bin 新增拒收；blocks 移出身份根拒收；目录内 link.parquet 指向 logs.parquet 拒收；独立 root2 文件夹具原始放行、CSV 同长度翻转末字节按既有 `time plan input identity sha256 mismatch` 拒收。每次恢复后均再次放行；目录内容差异和 symlink 分别断言工单指定的错误文本。未使用 _refresh_receipt，未刷新签名或输入清单。删除新增测试段后，原有测试文件与 2197505 全文一致。

## 定向测试

所有测试实际使用以下命令形式，逐项脚本替换见表：

```sh
PYTHONDONTWRITEBYTECODE=1 \
MPLCONFIGDIR=/private/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/t3_validation_9feb86ir/mplconfig \
TMPDIR=/private/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/t3_validation_9feb86ir/tmp \
python3 -B scripts/tests/<脚本名>
```

当前沙箱可写范围不含 `$HOME/.matplotlib`，因此使用 tempfile 创建并经 Path.resolve() 得到的可写配置目录；TMPDIR 同样为真实路径。RED 和新增回归的案根均显式使用 `Path(td).resolve()`。完整原始测试日志保留在 `/private/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/t3_validation_9feb86ir/<脚本名>.log`。

| 脚本 | exit | 结果及原始尾行 |
| --- | ---: | --- |
| `test_anchor_plan_v3.py` | 0 | PASS：`anchor-plan v3: 17/17 PASS` |
| `test_time_spotcheck.py` | 0 | PASS：`time_spotcheck 契约测试全部通过（20 项）` |
| `test_recon_deep_reverify.py` | 0 | PASS：`PASS test_recon_deep_reverify` |
| `test_handoff_manifest.py` | 0 | PASS：`handoff_manifest 契约测试全部通过（283 项）` |
| `test_audit_release_gate.py` | 0 | PASS：`PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过` |
| `test_batch4_invariant_guards.py` | 0 | PASS：`PASS B4-G1: bare pool / labels / vertical slice / denominator injections` |
| `test_exemption_guards.py` | 0 | PASS：`PASS: exemption guards (EX-01 full-F-03)` |
| `invariant_scan.py` | 0 | PASS：`PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0` |
| `test_batch3_evm_vertical_slice.py` | 1 | SANDBOX-BLOCKED：`PermissionError: [Errno 1] Operation not permitted` |

SANDBOX-BLOCKED 单列：`test_batch3_evm_vertical_slice.py` 在 `ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)` → `socket.bind` 失败，exit 1；尾行为 `PermissionError: [Errno 1] Operation not permitted`。未记 PASS，未尝试绕过沙箱，需调度方在允许本地监听的环境补验。

调度方待验：`changelog_lint.py` 本轮按 §0.2/§0.8 禁止执行（会读取 archive），未记 PASS。`run_all.py` 按工单未执行，由调度方运行。

## 字节与白名单核验

| 对象 | 基线 B | 完成 B | 核验 |
| --- | ---: | ---: | --- |
| SKILL.md | 8021 | 8021 | 唯一差异为第 23 行版本号 |
| commands-staging/*.md | 8789 | 8789 | 4 文件，零 diff |
| references/*.md + references/*/*.md + references/*/*/*.md | 929085 | 929085 | 33 + 9 + 0 文件，824130 + 104955 + 0 B，零 diff |

字节统计使用文件 stat 大小，不读取 references/attic.md 正文。`git diff --exit-code 2197505 -- references commands-staging` exit 0，无输出。`git diff --check` exit 0，无输出。

```text
$ git diff --stat 2197505 -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
 CHANGELOG.md                             |  8 +++++
 SKILL.md                                 |  2 +-
 VERSION                                  |  2 +-
 pyproject.toml                           |  2 +-
 scripts/report/shared_release_receipt.py |  5 ++-
 scripts/tests/test_anchor_plan_v3.py     | 58 ++++++++++++++++++++++++++++++++
 6 files changed, 73 insertions(+), 4 deletions(-)
```

上述 tracked 修改全部位于 §0.3 白名单；此外仅新增本目录 `T3_done.md`、`T3_red_evidence.txt`。生产、测试之外未改 references、commands-staging、anchor_selection、receipt_kernel、receipt_validate、time_spotcheck、anchor_plan、handoff_manifest、audit_release_gate、invariant_manifest 或 contract_manifest。

## 影响、未做与存疑

- 完整身份比较包含 path/kind/size/sha256，复用生产者既有身份定义；不支持新增搬移语义。
- 正常 verify 重算一次，正常 EVM 发布闸重算两次。允许读取的 T3_cost_quq_v2_identity.log 为 `files=61 size=7.62GB elapsed=3.5s match_signed=True`；约增加 3.5 s／7 s 为据此估计。本轮未访问 QUQ 原案、未重新做性能实测，也未展示完整案卷身份。
- 所有旧 shared_release_receipt.json（含文件案）均因 producer.sha256 改变须走现有 create_bundle 重建；该源码身份约束自 9.0.3 起已存在。文件时间校验分支不变不代表共享发布产物字节不变。未为存量收据放宽校验，未操作用户案卷重建收据。
- 保证仅覆盖本次深验时的目录实物；同一次发布继续改目录、长期保留 witness 后直接消费不在本单范围，未扩展 witness 缓存边界。
- 未执行 run_all.py、changelog_lint.py；EVM 纵切片 SANDBOX-BLOCKED，三项需调度方接续验收。
- 未 commit、push、stash、checkout、reset，未建 worktree，未改工单方案，未调用外部网络，未启动子代理。
- 其他源码事实冲突或待决疑点：无。

禁读路径披露：本轮未读取 ~/.codex/（含 memories）、archive/、blind-reviews/、.staging_*、.hypothesis/、references/attic.md 正文、其他历史 maintenance 目录或 /Users/uravvv/Desktop 下案卷。未因插件启动搜索读取 memories。

