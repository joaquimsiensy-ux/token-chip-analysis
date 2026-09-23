# 施工 T1：停工

attempt 2 已按工单 v4 完成 §2.1–2.5 的代码、测试、文档与版本改动，但 §0.8 定向验收未闭合，不能报完成。`test_batch3_evm_vertical_slice.py` 原样运行时在创建本地测试服务器的 `socket.bind` 被沙箱拒绝，exit=1；这不是工单唯一豁免的 `No usable temporary directory found`，不记作该条款的 SANDBOX-BLOCKED，不计 PASS。未自行更改测试、网络夹具或生产方案绕过限制。其余七项定向检查均 PASS。

停工原因是执行环境阻断验收，并非已发现工单与源码不符或本次逻辑回归。当前权限不能升级，保留工作树供调度方本机补验；未生成 `T1_done.md`。CHANGELOG 的验收引用改指本停工报告，未宣称全部验收通过。

## 开工基线

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`；分支：`main`。

```text
$ git rev-parse HEAD
b52cbedf230218e5da46334cf99b7111235e8367
$ git status --short
（空输出）
$ git diff --stat f4f80567c21f HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
（空输出）
```

两项基线均通过。施工整行锚逐项以 `grep -n -F -x` 核验恰一处且行号一致；原始结果见下文。开工 invariant：

```text
$ python3 -B scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
exit=0
```

## RED 取证与回归结果

详细证据：[T1_red_evidence.txt](T1_red_evidence.txt)。保留已入库 attempt1 原文，追加 attempt2 基线实测；本次三项全部独立重跑，不依赖沿用。每项各用独立临时夹具，`root = Path(td).resolve()`；生产与仓库测试文件当时尚未修改，只在仓库外 `/private/tmp/t1_attempt2_red.py` 将测试函数 `_produce_plan` 的目录分支在内存展开。24 行 logs/blocks，原 anchor_plan 调用参数不变，三份计划均真实生成、加载并通过语义重放，矩阵点 4、强制点 9。某项异常不会跳过后项。

1. **生产者 main 接线 RED**：mock 捕获 `inputs.input` 为实际 v2 目录，并非 `anchor_plan.input.json`；受控异常 `stop-before-rpc` 后 main exit=1、无收据文件，无 RPC。修复后新用例断言捕获清单路径，PASS。
2. **消费者合法目录 RED**：清单绑定的合法目录计划在基线抛 `time plan authority chain broken: time plan input identity is not a regular file`。修复后清单绑定放行、绑定计划文件拒收，PASS。
3. **消费者篡改拒收负例**：清单 `input.sha256` 改成 64 个 0，基线即以 `plan receipt envelope invalid: ['input input_manifest size mismatch']` 拒收，保持 PASS；修复后同类篡改仍拒，helper 也拒。新用例另将清单引用与 plan 输出哈希自洽重绑，保持 plan.input/input_identity 不变，命中 `input manifest identity differs from signed identity` 拒收，PASS。

新回归用例 `test_16_directory_input_binds_signed_manifest` 已运行通过；完整 `anchor-plan v3: 16/16 PASS`。没有以缺失 helper 的 AttributeError 充当原缺陷证据。

## 实施明细与实际 diff 行号

以下为当前工作树行号，括号中注明基线位置；源码三段固定代码块与工单逐字一致。

| 工单 | 文件及当前行号 | 实际改动 |
| --- | --- | --- |
| §2.1 | scripts/lib/time_spotcheck.py:180、431、435（基线 :180 前、:417 前、:420） | 新增唯一私有 helper；既有 try 内选绑定对象；目录绑清单，文件仍绑原文件，既有异常处理不变 |
| §2.2 | scripts/report/shared_release_receipt.py:1033–1059（基线 :1033–1043） | 原段按工单替换；文件分支 identity→同一实物→manifest 顺序保留；目录验证清单、正文身份与目录围栏，不重算目录哈希 |
| §2.3 | scripts/tests/test_anchor_plan_v3.py:99–148、541–597（基线 :99、:521 前） | 原 _produce_plan 加 directory 参数与 24 行 Parquet 分支，共用原 anchor_plan 调用；新目录用例由 main 自动发现 |
| §2.4 | references/data-pipeline-evm-recon.md:158 | merged input（含末尾空格）→文件/清单，等长替换 |
| §2.5 | VERSION:1、pyproject.toml:15、SKILL.md:23 | 9.0.2→9.0.3；SKILL 仅版本注释变化 |
| §2.5 | CHANGELOG.md:13、100–107 | 一行索引与五项详情；真实 diff 数字、验证边界、成本指标；验收状态指向本停工报告 |

生产代码只新增 `_bound_input_ref` 一个私有函数；AST 对比确认两生产文件 import 不变、消费者新增函数为 0。文件分支原三行只增加条件缩进，仍先核 identity 绑定并验证同一实物，再核 manifest。未改 receipt_kernel、anchor_plan、anchor_selection、receipt_validate、producer_history、其他测试、invariant_manifest/contract_manifest 或 commands-staging。发布检查不证明目录内容自生产完成后未改变；本次未跑真实案卷判断链，外部网络调用 0。

## §0.8 定向验收

全部命令均按工单原样运行。以下为真实退出码和日志尾行；完整测试日志位于 `/private/tmp/t1_attempt2_<脚本名>.log`。changelog_lint 在报告引用修正后再次运行 PASS。

```text
$ python3 -B scripts/tests/test_anchor_plan_v3.py
anchor-plan v3: 16/16 PASS
exit=0
```

```text
$ python3 -B scripts/tests/test_time_spotcheck.py
time_spotcheck 契约测试全部通过（20 项）
exit=0
```

```text
$ python3 -B scripts/tests/test_recon_deep_reverify.py
PASS test_recon_deep_reverify
exit=0
```

```text
$ python3 -B scripts/tests/test_handoff_manifest.py
handoff_manifest 契约测试全部通过（283 项）
exit=0
```

```text
$ python3 -B scripts/tests/test_audit_release_gate.py
PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过
exit=0
```

```text
$ python3 -B scripts/tests/test_batch3_evm_vertical_slice.py
    socketserver.TCPServer.server_bind(self)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/socketserver.py", line 478, in server_bind
    self.socket.bind(self.server_address)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
PermissionError: [Errno 1] Operation not permitted
exit=1
```

```text
$ python3 -B scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
exit=0
```

```text
$ python3 -B scripts/tests/changelog_lint.py
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 82 条 + 归档 139 条
exit=0
```

阻断位置：`test_batch3_evm_vertical_slice.py:283` 执行 `ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)`，调用 Python socketserver 的 `socket.bind` 抛 `PermissionError: [Errno 1] Operation not permitted`；第一个 eth 纵切片在启动本地服务器时退出，未完成该用例，其余链用例未执行。没有外部网络访问；未改成 mock 或跳过监听以宣称 PASS。按当前工单无可适用豁免，记一项非零退出、七项 PASS，等待调度方本机补验此命令。`run_all.py` 未运行，仍由调度方本机负责。

## 字节与差异核验

字节合计按文件元数据读取（未读取 references/attic.md 内容）；references 行字节不含换行。

| 范围 | 开工 B | 停工 B |
| --- | ---: | ---: |
| SKILL.md | 8021 | 8021 |
| commands-staging/*.md | 8789 | 8789 |
| references/**/*.md | 929092 | 929092 |
| references/data-pipeline-evm-recon.md:158 | 326 | 326 |

`git diff --check` PASS。scripts 三文件 +124/−14（生产者 +16/−1，消费者 +20/−4，测试 +88/−9）；生产、测试、文档和版本范围共八文件 +137/−18；另有本工单目录内证据追加与停工报告。所有改动均在 §0.3 白名单。

与工单差异：修法、schema/键、文件校验顺序、固定代码块、字节约束和版本档位均无偏离；唯一未闭合项是上述定向测试受沙箱本地监听权限阻断。因其不满足工单全部 PASS 条件且不属临时目录错误豁免，按停工交付报告，并把 CHANGELOG 验收引用改指本报告，未生成完成报告。不请求扩大权限，不自行改方案；无 commit/push/stash/checkout/reset。

## 施工锚核验原始匹配

```text
scripts/lib/time_spotcheck.py:180:def validate_semantic_replay(plan, raw_input, *, mem_limit="6GB", threads=4):
scripts/lib/time_spotcheck.py:415:    target = {"chain": a.chain, "token": token, "as_of_block": a.final_block}
scripts/lib/time_spotcheck.py:420:                                          "input": a.input},
scripts/report/shared_release_receipt.py:1033:        identity = plan_receipt.get("input_identity")
scripts/report/shared_release_receipt.py:1043:                 "plan input manifest differs from signed receipt binding")
scripts/tests/test_anchor_plan_v3.py:99:def _produce_plan(root):
scripts/tests/test_anchor_plan_v3.py:521:def main():
references/data-pipeline-evm-recon.md:158:- 产物 `time_spotcheck.json`（`time-spotcheck/v3`，target 绑定 chain/token/final-block，并绑定 plan、plan receipt、merged input 与逐笔 RPC transcript；verdict/exit_code 为 0 PASS/2 FAIL/1 检测自身失败禁当 PASS）；split-run 案是 READY 必备件＋AUTO_GATES（handoff_manifest 重读防手报）。
VERSION:1:9.0.2
pyproject.toml:15:version = "9.0.2"
SKILL.md:23:<!-- skill-version-source: VERSION; skill-version: 9.0.2 -->
CHANGELOG.md:13:- **9.0.2**（2026-09-19）口径漂移与文档-代码不符审计第二期闭环（针对 7.2.0→9.0.1 六版代码大改而文档零改动）：codex 两路盲审十三轮（a 路全范围术语表法 9→2→3→4→2→2→2→2→1→1→2→0→1，b 路 7.2.0 起代码变更区专审 0→0→2→1→1→0→1→2→2→0→0→0→0；用户裁决 R13 修完即收官），十二份工单皆先 codex 只读复核（退回 9 次全在派工前拦下）再 codex 施工，38 条/21 文件纯文本修复，零代码改动；references 930076→929092（净减 984 B）、SKILL.md 8021 不变、commands-staging 8798→8789；范围外残留一条登记（fetch_sqd_transfers_v2 帮助文字，改则变采集器 sha）。
CHANGELOG.md:99:## [9.0.2] - 2026-09-19 — 口径漂移与文档-代码不符审计第二期闭环（零代码改动）
```

## 最终工作树

```text
$ git diff --stat f4f80567c21f -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
 CHANGELOG.md                             |  9 +++
 SKILL.md                                 |  2 +-
 VERSION                                  |  2 +-
 pyproject.toml                           |  2 +-
 references/data-pipeline-evm-recon.md    |  2 +-
 scripts/lib/time_spotcheck.py            | 17 +++++-
 scripts/report/shared_release_receipt.py | 24 ++++++--
 scripts/tests/test_anchor_plan_v3.py     | 97 +++++++++++++++++++++++++++++---
 8 files changed, 137 insertions(+), 18 deletions(-)
```

```text
$ git status --short
 M CHANGELOG.md
 M SKILL.md
 M VERSION
 M maintenance/repair-20260923-t1-spotcheck-dir-input/T1_red_evidence.txt
 M pyproject.toml
 M references/data-pipeline-evm-recon.md
 M scripts/lib/time_spotcheck.py
 M scripts/report/shared_release_receipt.py
 M scripts/tests/test_anchor_plan_v3.py
?? maintenance/repair-20260923-t1-spotcheck-dir-input/T1_done_attempt2_stopped.md
```

本目录 `T1_red_evidence.txt` 已由 attempt1 入库，本次为追加修改；`T1_done_attempt2_stopped.md` 为本次新增。所有临时脚本均在 `/private/tmp`，未留入仓库。

禁读路径披露：未直接读取 ~/.codex/（含 memories）、archive/、blind-reviews/、.staging_*、references/attic.md 内容、其他历史 maintenance 目录、Desktop 或 Documents。按 §0.2/§0.8 原样运行指定测试，其自身依赖访问适用工单豁免（如 changelog_lint 读取归档、相关测试使用历史夹具）；未为调查测试依赖另行读取禁读文件。
