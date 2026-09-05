# 批 17 完工报告：G8 身份闸链名别名归一

## 1. 结论与状态

- 代码与定向验收：**COMPLETE**。
- 沙箱全套验收：**PARTIAL**。`run_all.py` 共 143 项，141 PASS、2 FAIL、退出码 1；两项失败均为既有 R9 纵切片在沙箱内绑定 `127.0.0.1` 时触发 `PermissionError: [Errno 1] Operation not permitted`，未进入业务断言。
- 调度方后续：在允许 loopback bind 的本机环境复跑 `python3 scripts/tests/run_all.py`，取得全套最终验收结果。
- 未 commit、未联网、未写 key；未进入其它批次或案卷路径。

## 2. 开工门禁与锚点

- 开工 `git status --short`：空。
- 分支：`main`。
- 冻结 HEAD：`70a9212ed6fac2b600553fda30975cdb3c2e0dc7`。
- 开工版本：`6.53.4`。
- 工单列出的九组行号/锚文本全部逐字命中：生产导入、state chain 取值与裸比较、`build()`、`resolve_alias`、真实 Solana fixture/emitter、Batch 16 suite 登记均无漂移。

## 3. 先红证据

完整证据见 `maintenance/repair-20260823-sqd-gap/batch17_red_evidence.txt`。

命令：

```text
python3 scripts/tests/test_batch17_identity_chain_alias.py --r1
```

修前真实 Solana 路线输出要点：

```text
snapshot_slot=103 accounts=1 owners=1 supply=100 activity=complete -> snapshot.json
[identity_gate] 1 址入闸，0 个 flag 待解决
FAIL R1 Solana alias state: R1 errors 原文: ["chain 与 state 不绑定: gate='sol' state='solana'"]
FAIL batch17 identity chain alias: 1/1
EXIT=1
```

错误恰为一条，证明 RED 只来自 `validate_gate` 的 `sol`/`solana` 裸比较；证据固化早于生产改动。

## 4. 实现逐项对照

### 4.1 生产

- `scripts/report/entity_identity_gate.py` 仅改工单指定两处：
  - 导入改为 `from chain_registry import identity_chains, resolve_alias`；未导入 `audit_release_gate`。
  - state/gate chain 改为 `resolve_alias(state_chain) != resolve_alias(chain)` 双向归一比较。
- 错误文案未改，继续显示 gate/state 原始输入值。
- 未改 snapshot receipt adapter 严格比较、gate chain 的 `identity_chains()` 限定、`build()`、`build_html.py`、`a4_gate.py`、`audit_release_gate.py`、`state_from_facts.py`。

### 4.2 测试

- 新增 `scripts/tests/test_batch17_identity_chain_alias.py`，支持 `--r1` 单跑且以 `main()` 返回码出闸。
- fixture 未降级：四个场景均真实调用 `test_round4_identity_emitter.run_solana`，再由 `identity_snapshot_receipt.emit_solana` 产规范 `sol` 收据，并经 `entity_identity_gate.build(..., "sol")` 生成 gate；填完 flag resolution 后真实进入 `validate_gate`。
- `scripts/tests/run_all.py` 在 Batch 16 后追加 Batch 17，SUITE 142→143。

## 5. R1 与 N1–N4 结果

R1 修后：

```text
PASS R1 Solana alias state
PASS batch17 identity chain alias: 1/1
R1_EXIT=0
```

批 17 全跑原文：

```text
PASS R1 Solana alias state
PASS N1 canonical state
PASS N2 wrong chain
PASS N3 token.chain fallback
PASS batch17 identity chain alias: 4/4
ALL_EXIT=0
```

- N1 实际 `errors == []`：state 顶层与 token 均为旧规范形 `sol`，零回退。
- N2 实际 `errors == ["chain 与 state 不绑定: gate='sol' state='bsc'"]`：错链仍拒，错误文案保留原始值。
- N3 实际 `errors == []`：state 顶层无 `chain`，仅 `token.chain="solana"`，回退取值路径通过。
- N4：`build_html.py` 共用 `entity_identity_gate.validate_gate`，按工单不另测；生产 diff 未触碰 `build_html.py`。

## 6. 版本与 CHANGELOG

- `VERSION`、`pyproject.toml`、`SKILL.md` 同步到 `6.53.5`。
- `CHANGELOG.md` 已增加顶部索引与 `6.53.5` 六栏详情。
- `python3 scripts/tests/changelog_lint.py`：PASS，退出码 0。
- `python3 scripts/tests/test_version_consistency.py`：`PASS: M-03 version metadata consistent at 6.53.5`，退出码 0。

## 7. 定向验收

```text
PY_COMPILE_EXIT=0
PASS batch17 identity chain alias: 4/4
BATCH17_EXIT=0
PASS: P2-01 total-supply share binding + Arbitrum G8 support
P201_EXIT=0
PASS: real EVM collector+preflight+replay and Solana scan chains; copied-hash self-reports blocked
ROUND4_EXIT=0
BATCH D 全部通过
BATCH_D_EXIT=0
CHANGELOG_LINT_EXIT=0
VERSION_EXIT=0
```

点名既有 `test_review_20260804_p201.py`、`test_round4_identity_emitter.py`、`test_repair_batch_d.py` 全绿且未改一字。

## 8. 沙箱完整套件

命令：

```text
python3 scripts/tests/run_all.py
```

汇总：

```text
143 total / 141 PASS / 2 FAIL
RUN_ALL_EXIT=1
```

仅有失败：

1. `test_batch3_solana_vertical_slice.py`：`ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)` 在 `socket.bind` 抛 `PermissionError: [Errno 1] Operation not permitted`。
2. `test_batch3_evm_vertical_slice.py`：同样在 loopback `socket.bind` 抛相同 `PermissionError`。

其余 141 项全部 PASS；其中 `test_batch17_identity_chain_alias.py` 在全套内为 `PASS batch17 identity chain alias: 4/4`。这两个失败属于沙箱 loopback 能力限制，不能把本次沙箱结果称为全绿，故状态保持 PARTIAL；需调度方本机复跑。

## 9. diff 与白名单核查

写 done 前的原始 `git diff --stat`（Git 默认不计未跟踪新文件）：

```text
 CHANGELOG.md                           | 10 ++++++++++
 SKILL.md                               |  2 +-
 VERSION                                |  2 +-
 pyproject.toml                         |  2 +-
 scripts/report/entity_identity_gate.py |  4 ++--
 scripts/tests/run_all.py               |  3 +++
 6 files changed, 18 insertions(+), 5 deletions(-)
```

最终改动/新建路径共九个，全部在工单白名单：

1. `scripts/report/entity_identity_gate.py`
2. `scripts/tests/test_batch17_identity_chain_alias.py`
3. `scripts/tests/run_all.py`
4. `VERSION`
5. `pyproject.toml`
6. `SKILL.md`
7. `CHANGELOG.md`
8. `maintenance/repair-20260823-sqd-gap/batch17_red_evidence.txt`
9. `maintenance/repair-20260823-sqd-gap/batch17_done.md`

- `git diff --check`：退出码 0，无空白错误。
- 生产 diff 精确为导入一行与比较一行；`build()` 及所有禁改生产面无 diff。
- 无其它 tracked/untracked 仓库变化；无 commit。
