# W1 施工报告（停于 §1 提交前）

状态：未完成。§1 代码及守卫已修改并通过本节验证；git add 被当前沙箱拒绝，尚无施工 commit。§2—§5 未施工。

## 开工核验

- `git status --short` 输出为空；分支 `fix/solana-txv1`。
- 开工 HEAD：`9f74b851935a4a97667108881dedd311f26ccde6`。
- 工单所列代码行号及锚文本已核对；相关生产、测试、契约及版本文件与 `813ca6d` 无差异。未发现需触发行号不符停工的情况。

## 已做改动（当前工作树行号）

- `scripts/lib/solana_attested_session.py:10, 22`
- `scripts/lib/solana_exact_validate.py:32, 1214, 1220, 1222`
- `scripts/lib/solana_observation.py:20, 271`
- `scripts/solana/audit_closed_accounts.py:41, 231, 420, 483`
- `scripts/solana/decode_txs.py:10, 42`
- `scripts/solana/decode_txs_v2.py:25, 296, 341`
- `scripts/solana/fast_probe_tops.py:16, 55`
- `scripts/solana/gas_origin.py:19, 82`
- `scripts/solana/probe_escrows.py:21, 151`
- `scripts/solana/probe_window_moves.py:26, 122`
- `scripts/solana/sqd_gap_repair.py:27, 42, 636`
- `scripts/solana/stake_decode.py:23, 97`
- `scripts/solana/trace_wallet.py:15, 77`
- `scripts/solana/whale_deep.py:23, 65, 155`
- `scripts/tests/invariant_scan.py:355, 1353`
- `scripts/tests/test_batch4_invariant_guards.py:36, 526`
- `maintenance/repair-20260923-solana-txv1/W1_red_evidence.txt:1`：修改代码前保存四项基线红证据。
- `maintenance/repair-20260923-solana-txv1/W1_done.md:1`：本停工报告。

改动内容：交易版本上限统一为 1；修复请求模板集中至 validator；补包导入回退、producer 版本钉、禁止数值字面量的 AST 守卫及注入测试。所有生产与测试改动均在 §0.3 白名单内。

## 与工单差异及理由

- 未能完成 §1 commit，故不进入 §2；§3 登记、§4 认领测试和 §5 版本/文档均未执行。
- 执行显式白名单文件的 `git add -- ...` 时退出码 128，原始错误如下：

```text
fatal: Unable to create '/Users/uravvv/.claude/tca-fix-txv1/.git/index.lock': Operation not permitted
```

- 当前会话将 `.git` 限制为只读，且禁止请求提权；不能在本会话内完成正常暂存与提交。未尝试绕过限制。
- 未执行 git commit（git add 已失败）；未 push，未操作 main。现有改动留在工作树，不能视作完整可发布修复，producer 登记尚未更新。

## 定向验证及尾行

下列 Python 验证均带 `MPLCONFIGDIR=$HOME/.matplotlib`、`PYTHONDONTWRITEBYTECODE=1`。

- `python3 scripts/tests/test_batch4_invariant_guards.py`：退出码 0；尾行：
```text
PASS B4-G1: bare pool / labels / vertical slice / denominator injections
```
- `python3 -c "import scripts.lib.solana_attested_session, scripts.lib.solana_exact_validate"`：退出码 0，标准输出/错误均为空（无尾行）。
- `git diff --check`：退出码 0，无输出。

§0.7 其余定向测试尚未运行；`test_batch3_solana_vertical_slice.py` 尚未运行，未标记 SANDBOX-BLOCKED；未运行 `run_all.py`。本报告不宣称全套 PASS。

## 红证据

路径：`maintenance/repair-20260923-solana-txv1/W1_red_evidence.txt`。
已复现：13 文件 17 处字面量 0；repair argparse 无 `--adopt-pending`；版本 1 模板摘要的成功行不计入 completed；隔离导入报 `No module named 'endpoint_identity'`。尾行：
```text
RED evidence complete: all four baseline assertions reproduced.
```

## 禁读路径与操作自报

- 未读取 `~/.codex` 下任何文件；未读取 `~/Documents`、`~/Desktop`。启动自动披露的技能目录信息未用于打开文件。
- 全程离线，未访问网络，未启动子代理。
- 未批量删除任何文件或目录；测试及红证据的临时夹具由测试自身清理。

## 待裁决

请调度方提供允许对本克隆 `.git` 正常写入的施工环境，以便先提交现有 §1 改动（`W1(1):` 中文主题及指定 Co-Authored-By），再继续 §2—§5。当前会话不能申请提权；未获得具备该能力的环境前，不继续跨节施工。恢复时应核对本报告记录的工作树改动，不能将其误当作开工前的外来脏文件。


## 第 2 段开工核验（2026-09-23）

- 当前分支 `fix/solana-txv1`；`git diff --stat` 为 16 个文件，与第 1 段「已做改动」一致；`git ls-files --others --exclude-standard` 无输出。未发现其他工作树改动。
- 本段用户指令覆盖前述「待裁决」中的 git 写入要求：`.git` 只读，git add/commit 由调度方完成，不以不能提交为停工理由。
- 已按顺序读取 A1、v5 与本报告；尚未修改生产或测试文件。

## 停工原因

A1 第 2 条的数量断言与实况不符，触发本段用户纪律第 7 条「工单里任何行号/断言与实况不符：停工」。

- 工单位置：`maintenance/repair-20260923-solana-txv1/workorder_W1_amendment_A1.md:7`。该条先单独规定 `sqd_gap_repair.py` 的导入调整，随后写「其余 11 个 `scripts/solana/*.py`」。
- 实况：该目录共 11 个文件使用 `from solana_attested_session import SOLANA_MAX_SUPPORTED_TX_VERSION`；扣除已经单列的 `sqd_gap_repair.py:27` 后，其余只有 10 个。清单及当前行号如下：
  - `scripts/solana/audit_closed_accounts.py:41`
  - `scripts/solana/decode_txs.py:12`
  - `scripts/solana/decode_txs_v2.py:25`
  - `scripts/solana/fast_probe_tops.py:16`
  - `scripts/solana/gas_origin.py:19`
  - `scripts/solana/probe_escrows.py:21`
  - `scripts/solana/probe_window_moves.py:26`
  - `scripts/solana/stake_decode.py:23`
  - `scripts/solana/trace_wallet.py:15`
  - `scripts/solana/whale_deep.py:23`

- 复核方式：`rg -n 'from solana_attested_session import SOLANA_MAX_SUPPORTED_TX_VERSION' scripts/solana`，并用 Python 枚举该目录的 `*.py` 文件复核，数量断言 `len(files) == 11 and len(remaining) == 10` 通过。
- 建议调度方将 A1 第 2 条「其余 11 个」更正为「其余 10 个」。没有擅自更改工单或按推测继续施工。

### 本段改动、差异及验证记录

- 仅追加 `maintenance/repair-20260923-solana-txv1/W1_done.md` 本段开工及停工记录；第 1 段 16 个生产/测试文件改动保持原状。
- A1、§2、§4 均未完成；§3、§5 未执行。与计划的差异原因是上述数量断言不符，不是 git 写权限。
- 测试尾行：无。本段在开工核验阶段触发停工，未运行 A1 验收、§0.7 定向测试或 registry 测试；不宣称任何测试 PASS。
- 未读取 `~/.codex`、`~/Documents`、`~/Desktop`；全程离线；未启动子代理；未执行 git add/commit/push；未删除文件。
- 本记录仅供调度方接手，不表示第 2 段施工完成。

待调度方 commit
