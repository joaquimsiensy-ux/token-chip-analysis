# R1 完成：候选边物化已落地，17 组等价对照与 7 项定向检查通过

生产改动为 +49/−26，共 75 行；版本登记 9.1.1。EXPLAIN 证明候选查询不再读取底层 parquet。30 万与 300 万边 EVM 墙钟分别为 2.120→1.191 秒、14.422→7.458 秒；物化增加 RSS，未验证亿级实跑或物化表跳块扫描。

## 开工基线与纪律

工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`；分支 `main`。

```text
$ git status --short
（空输出，exit 0）
$ git rev-parse --short HEAD
ff9fbab
$ git merge-base --is-ancestor 634c083 HEAD
（空输出，exit 0）
$ git diff --quiet 634c083 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
（空输出，exit 0）
```

未以固定 HEAD SHA 判定开工资格。以下整行锚按 634c083 原文，通过 `grep -n -F -x --` 验证恰好一处、行号一致，并读取核对完整目标块。核锚工具初次误将测试文件第 65 行空行列入检查，工具断言失败；未将其作为有效修改锚、当时未修改任何源码，随后改选非空唯一锚通过。没有发现工单所列源码锚或完整目标块与 634c083 不符。

```text
scripts/report/flow_anomaly_scan.py: 55:  - Q1Ac6Y 的 spray 候选保持 mode=pulse（2025-08-13 窗灌新仓）。
scripts/report/flow_anomaly_scan.py: 194:    con.execute("SET preserve_insertion_order=false")
scripts/report/flow_anomaly_scan.py: 205:    log(f"边表就绪 {n_edges:,} 条")
scripts/report/flow_anomaly_scan.py: 230:    sent_ph = "', '".join(sorted(sentinels))
scripts/report/flow_anomaly_scan.py: 235:    elig_ph = "', '".join(sorted(eligible - sentinels))
scripts/report/flow_anomaly_scan.py: 237:    pre_sinks = [r[0] for r in con.execute(f"""
scripts/report/flow_anomaly_scan.py: 238:        SELECT t FROM eflow
scripts/report/flow_anomaly_scan.py: 239:        WHERE f IN ('{elig_ph}') AND t NOT IN ('{sent_ph}') AND f <> t AND amt > 0
scripts/report/flow_anomaly_scan.py: 240:        GROUP BY t HAVING SUM(amt) >= {sink_min_raw}""").fetchall()]
scripts/report/flow_anomaly_scan.py: 244:    for t in pre_sinks:
scripts/report/flow_anomaly_scan.py: 246:            SELECT ts, f, amt FROM eflow
scripts/report/flow_anomaly_scan.py: 247:            WHERE t = '{t}' AND f IN ('{elig_ph}') AND f <> t AND amt > 0
scripts/report/flow_anomaly_scan.py: 259:        net_in = con.execute(f"""
scripts/report/flow_anomaly_scan.py: 260:            SELECT COALESCE(SUM(CASE WHEN t = '{t}' AND f <> t THEN amt
scripts/report/flow_anomaly_scan.py: 262:            FROM eflow WHERE t = '{t}' OR f = '{t}'""").fetchone()[0]
scripts/report/flow_anomaly_scan.py: 282:    sinks.sort(key=lambda s: -s["best_window"]["inflow_pct"])
scripts/report/flow_anomaly_scan.py: 288:    pre_sprays = [r[0] for r in con.execute(f"""
scripts/report/flow_anomaly_scan.py: 289:        SELECT f FROM eflow
scripts/report/flow_anomaly_scan.py: 290:        WHERE t NOT IN ('{sent_ph}') AND f NOT IN ('{sent_ph}') AND f <> t AND amt > 0
scripts/report/flow_anomaly_scan.py: 291:        GROUP BY f HAVING SUM(amt) >= {spray_min_raw}""").fetchall()]
scripts/report/flow_anomaly_scan.py: 296:        rows = [(int(ts), t, int(v)) for ts, t, v in con.execute(f"""
scripts/report/flow_anomaly_scan.py: 297:            SELECT ts, t, amt FROM eflow
scripts/report/flow_anomaly_scan.py: 298:            WHERE f = '{f}' AND t NOT IN ('{sent_ph}') AND f <> t AND amt > 0
scripts/report/flow_anomaly_scan.py: 377:            top = con.execute(f"""
scripts/report/flow_anomaly_scan.py: 378:                SELECT t, SUM(amt) AS v FROM eflow
scripts/report/flow_anomaly_scan.py: 379:                WHERE f = '{f}' AND t NOT IN ('{sent_ph}') AND f <> t AND amt > 0
scripts/report/flow_anomaly_scan.py: 380:                GROUP BY t ORDER BY v DESC LIMIT 500""").fetchall()
scripts/tests/test_flow_anomaly.py: 26:用法：python3 scripts/tests/test_flow_anomaly.py   退出码 0=PASS / 1=FAIL
scripts/tests/test_flow_anomaly.py: 175:        print(p.stdout, p.stderr)
scripts/tests/test_flow_anomaly.py: 216:    if "SlowSpray" in sp:
VERSION: 1:9.1.0
pyproject.toml: 15:version = "9.1.0"
SKILL.md: 23:<!-- skill-version-source: VERSION; skill-version: 9.1.0 -->
CHANGELOG.md: 13:- **9.1.0**（2026-09-23）Solana 交易版本上限统一为 `endpoint_identity.SOLANA_MAX_SUPPORTED_TX_VERSION=1`；新增 `--resume --adopt-pending` 与可选 `header.adopted`，支持可信前代 pending 证据认领、历史版本请求续跑及前代摘要复验；登记新 producer，旧 producer 保持 ACTIVE。新公开接口与持久化契约扩展，记次版本。
CHANGELOG.md: 103:## [9.1.0] - 2026-09-23 — Solana 交易版本 1 与可信前代 pending 认领
```

额外测试锚 `:30 import subprocess`、`:68 d = tempfile.mkdtemp(...)`、`:171 out1 = ...`、`:201 sp = ...`、`:217 ss = ...` 也分别整行唯一通过。临时目录均由 tempfile 生成并 resolve；基线两脚本来自 git show 634c083。冻结输入、formal_cli_args 和全部 17 份基线报告后才修改生产文件；原始输入和基线报告冻结哈希末次复验全部相同。

## 等价性

详见 [R1_equivalence.txt](R1_equivalence.txt)；生成与检查脚本为 [R1_fixture_tools.py](R1_fixture_tools.py)。主夹具 4,843 个实际地址、300,000 边、800 天；放大夹具 3,000,000 边，固定种子 20260924。

- `--edges-sol` 无 entity、有 entity、有 entity+exclude：sinks 8/7/6，sprays 均 7；只去 generated_at 后原始报告逐字节相等。同实体 Sink0 抵消、跨实体 Sink1 完整字段保留、exclude 移除 Sink3。
- `--edges-evm-v2` 与 `--duckdb` 主夹具：各 8 sinks/7 sprays，同入口新旧原始字节相等；300 万 EVM 同样通过。EVM 全边解码的时间、地址、金额及重复度与映射后的原始边多重集全等；两 run block 区间全局互斥，VIEW 轻路径日志和无 edge_source_binding 断言通过。
- 主夹具各变体顶层 pulse/pulse_all/slow_spray=3/2/2，mode_hits=3/5/2；两个老收方补货 pulse_all 的 fresh=0；Sink2 全史合格流入高于最佳窗；MixedHub 同时 sink/spray；两个纯 slow_spray 各 600 收方。输出相关排序键无并列断言通过。
- 三入口并列微夹具：同 ts 同额 sources、同窗口 pct sinks、同全史 pct sprays 和 top500 边界专验通过。top500 全体 540 收方，490 严格高于边界、40 在边界、10 低于；每次恰选 490+10、无重复，不以任意排序整个报告掩盖差异。
- 三入口空候选及 Solana/EVM 空 elig 微夹具通过。DuckDB 空 elig 含空字符串来源：新旧 eligible=0、sink 预筛恰为 EmptyHub、候选行恰为 (0,"",30000000000)，进一步核验全部预筛成员和候选行相等。
- DuckDB MixedHub 正值/负值独立副本：新旧分别确认净额 1.01%→1.03%，合格流入 3.0%、来源 5、正值收方 20 不变；ZeroOnly 不进入收方。正值自转不计净额，非合格 TinySrc 入边只计净额。回归第 17 例及既有 SlowSpray 600/top500 断言通过。

## 耗时、资源与机制

详见 [R1_timing.txt](R1_timing.txt)，含 34 次无插桩 CLI 的独立进程测量和 6 组新旧诊断。DuckDB 1.5.4，有效 memory_limit=7.4 GiB、temp_directory=.tmp、max_temp_directory_size=90% of available disk space；不改默认临时目录。新 CLI 直接记录资源行；基线配置由同入口诊断重放读取验证。

| 输入 | 基线墙钟 s | 新墙钟 s | 基线峰值 RSS bytes | 新峰值 RSS bytes |
|---|---:|---:|---:|---:|
| main_sol | 48.168 | 49.779 | 216629248 | 272777216 |
| main_sol_entity | 59.225 | 54.779 | 227901440 | 269778944 |
| main_sol_entity_exclude | 57.877 | 59.461 | 231374848 | 280117248 |
| main_duck | 0.764 | 0.973 | 136364032 | 242515968 |
| main_evm | 2.120 | 1.191 | 347226112 | 440582144 |
| large_evm | 14.422 | 7.458 | 1281933312 | 1798799360 |

RSS 来自每个目标 PID 的 os.wait4 rusage，macOS 单位 bytes，未使用父进程累计 RUSAGE_CHILDREN。每 50ms 采样独立运行目录的默认 .tmp 文件 allocated bytes（stat.st_blocks×512），34 次采样观察峰值均为 0；瞬时真实峰值无法由离散采样保证，未用容量上限或结束目录大小替代。

30 万/300 万主夹具均预筛 8 sinks、12 sprays；三表行数分别为 sink_edges=9,360/94,455，sink_net=8/8，spray_edges=283,190/2,862,193，容量随相关边数增长。两次预筛及三次物化均仅一份 eflow 展开；EVM 各为 1 logs reader+1 blocks reader，sink_net 为 CROSS_PRODUCT+HASH_JOIN SEMI，无 DELIM_JOIN。sink 结束 DROP 两表，之后才建 spray_edges；两边表 CTAS 时 preserve_insertion_order=true，finally 恢复 false，按 rowid 的候选列/ts 下降数为 0。

三类新点查计划只含物化表，净额第四处改为 Python 字典读取。300 万边诊断的逐候选 SQL execute+fetchall 均耗时：sink 0.446851→0.014134 秒，spray 0.357120→0.234828 秒，top 0.187831→0.012279 秒；不含 Python 滑窗及基线另查净额，诊断缓存影响已注明。扫描统计的 operator_rows_scanned 仍等于物化表总行数，虽计划带候选过滤、输出行数减少，不能据此证明跳块；本次只证明不再逐候选扫描底层 parquet。

## 实际 diff 与限制自证

生产 numstat：`49	26	scripts/report/flow_anomaly_scan.py`，增删合计 75≤110；模块私有 helper 1，docstring 新增 4 行（含空行）≤6。CLI 参数 AST、现有公开模块属性（含 load_sol 转导入）、三个判据 helper AST 均保持。地址原字符串与空 elig 空字符串兼容保留；info/eligible/build_addr_summary/data_first_day 仍取原 edges/addr；retention 和 fresh 判断未动。

实际零上下文 diff 行号如下（旧行号/新行号），含每个修改块的行数：

```diff
+++ b/CHANGELOG.md
@@ -12,0 +13 @@
@@ -102,0 +104,7 @@
+++ b/SKILL.md
@@ -23 +23 @@ description: >-
+++ b/VERSION
@@ -1 +1 @@
+++ b/pyproject.toml
@@ -15 +15 @@ name = "token-chip-analysis"
+++ b/scripts/report/flow_anomaly_scan.py
@@ -55,0 +56,4 @@ references/scan-schemas.md）。
@@ -137,0 +142,9 @@ def best_window_scan(rows, win_sec, min_val, min_keys):
@@ -205,0 +219,3 @@ def main():
@@ -230 +245,0 @@ def main():
@@ -235 +250,4 @@ def main():
@@ -237,4 +255,4 @@ def main():
@@ -241,0 +260,11 @@ def main():
@@ -245,4 +274 @@ def main():
@@ -259,4 +285 @@ def main():
@@ -282,0 +306 @@ def main():
@@ -288,4 +312,4 @@ def main():
@@ -292,0 +317,3 @@ def main():
@@ -296,4 +323,2 @@ def main():
@@ -377,4 +402,2 @@ def main():
+++ b/scripts/tests/test_flow_anomaly.py
@@ -25,0 +26 @@ fixtures/pythia_anchors.json）：
@@ -29,0 +31 @@ import os
@@ -68 +70 @@ def main():
@@ -170,0 +173,8 @@ def main():
@@ -201,0 +212,9 @@ def main():
@@ -217,0 +237,2 @@ def main():
```

版本 VERSION:1、pyproject.toml:15、SKILL.md:23 已为 9.1.1；SKILL 只改版本行。CHANGELOG 索引行含换行 158 B≤200，详细段四条。

```text
$ git diff --stat 634c083 -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
 CHANGELOG.md                        |  8 ++++
 SKILL.md                            |  2 +-
 VERSION                             |  2 +-
 pyproject.toml                      |  2 +-
 scripts/report/flow_anomaly_scan.py | 75 ++++++++++++++++++++++++-------------
 scripts/tests/test_flow_anomaly.py  | 23 +++++++++++-
 6 files changed, 82 insertions(+), 30 deletions(-)
```

`git diff --quiet 634c083 -- references commands-staging` exit 0；未为统计而读 attic。新增工程文件恰为 R1_fixture_tools.py、R1_equivalence.txt、R1_timing.txt、R1_done.md，均在本工单目录；其他 tracked diff 恰为白名单六文件。未修改 wave_scan.py、fixtures、invariant_manifest、F008 测试。`git diff --check` exit 0。

## §0.9 定向检查

均使用 `python3 -B scripts/tests/<name>`，PYTHONDONTWRITEBYTECODE=1；MPLCONFIGDIR=/private/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/R1_gqro5g85/matplotlib，TMPDIR 设为已 resolve 的本次 tempfile 子目录。全部 exit 0，尾行如下：

`test_flow_anomaly.py` — exit 0

```text
ok    ZeroSpray（仅 5 个真实收方）不报
ok    MidSpray（50 收方匀速）不报——残余缝如实存在
ok    实体内部流转抵消后 SinkA 不报
ok    跨实体转账保留：SinkA 仍命中（拍平抵消是旧 bug）
ok    同址跨实体名册冲突 exit 2
ok    正式 anomaly 链显式拒绝 legacy-sol5

PASS：0 项失败
```

`test_wave_scan.py` — exit 0

```text
ok    D 二轮复收命中（旧实现按首收去重必漏）
ok    D 二轮复收：tx_count=40 且 densest 窗 ≥20
ok    正式入口拒绝 5 元组
ok    legacy 显式入口强制 non-formal/order-ambiguous
ok    instr>=0 保持 instruction exact 语义
ok    tx_index 字符串受控 exit 2

PASS：0 项失败
```

`test_reconcile_v4_receipt.py` — exit 0

```text
重放末态已写 data/replay_final_balances.json
GREEN batch10 exact target 放宽仅限冻结点≤观测点；chain/token/future/cache-upper 错配均拒
GREEN 31 coverage CURRENT 更新后旧 receipt 被独立深验与 camp 拒绝
GREEN 33 v4 raw 字符串被独立深验拒绝
OBSERVED 11 receipt_validate generic envelope 拒绝 repair_bundle:null
GREEN 11 v4 base/repaired 条件 inputs 拒绝 repair_bundle:null
OBSERVED 32 receipt_validate PASS/2 => verdict/exit_code inconsistent
GREEN 32 verdict/exit_code/gate_pass 三元互洽
```

`fixtures_lint.py` — exit 0

```text
fixtures_lint PASS：pythia_anchors.json 结构完整（数值以文件为权威，回测后人工更新）
```

`invariant_scan.py` — exit 0

```text
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0
```

`test_batch4_invariant_guards.py` — exit 0

```text
PASS B4F2C2 M4/M5 import bindings + four live ready chains
PASS B4F2C2 local binding forms + nested scope boundary
INJECT R9-B4-STALE-01 failed producer leaves old canonical -> RED
INJECT B4F2-STALE-03 dead quarantine/error calls -> RED
INJECT B4F2-STALE-03B constant-false contract calls -> RED
INJECT R9-B4-STALE-02 remove formal producer artifact registration -> RED
INJECT B4F2-STALE-04 newly added standalone producer -> RED
PASS B4-G1: bare pool / labels / vertical slice / denominator injections
```

`test_exemption_guards.py` — exit 0

```text
PASS EX-01: no production import/string reference to multicall_balances
PASS EX-01: absent from formal producer registry / evidence targets
PASS EX-01: --chain choices remain exploration-derived
INJECT EX-01-RED production import -> RED
PASS: exemption guards (EX-01 full-F-03)
```

## 未做与证据边界

- run_all.py、changelog_lint.py 依工单留给调度方；没有执行真实案卷，也没有重写存量报告。
- 没有亿级实跑证据；候选数仅 8/12，不能外推 7,093 候选的总耗时。物化占用按相关边计，且 Python fetchall 不受 memory_limit 约束。
- 未证实物化表跳块扫描；临时盘只得到运行期间 50ms 采样峰值，下于采样间隔的峰值不可得。
- 同构放大以拆分整数金额保持语义，不代表真实链上全部分布。原始输入、报告、完整 stdout、计划与定向日志保留在临时目录 /private/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/R1_gqro5g85；未删除文件/目录。可从持久夹具脚本复现输入与检查，冻结哈希在等价性证据中。
- 不 commit、不 push，未使用 stash/checkout/reset、worktree，无外部网络调用，无子代理。

禁读路径披露：未读取 ~/.codex/（含 memories）、archive/、blind-reviews/、.staging_*、.hypothesis/、references/attic.md、其他历史 maintenance 目录，以及 Desktop/Documents 内容。
