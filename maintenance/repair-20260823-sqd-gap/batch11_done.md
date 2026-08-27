# 批 11 施工报告（代码面完成；完整 suite 仅余沙箱 loopback 环境失败）

## 状态

- 基线 HEAD：`70ca1b4fd99be9e69f831486fe5ffda692be84fd`。
- R1 已在改生产代码前真实变红并留证；改后 G1、N1-N5 与静态存量端到端夹具全绿。
- 完整 `run_all.py` 共 135 项：133 PASS、0 项真实失败、2 项环境失败。两项都在
  `ThreadingHTTPServer.bind(127.0.0.1)` 处被沙箱以 `PermissionError: [Errno 1]`
  拒绝，尚未进入业务断言；因此不把完整 suite 写成 exit 0。
- 未 commit、未 push；未改版本登记面；未触碰密钥文件或 ARC 案根，产物不含 API key。

## 改动清单（当前文件行号）

1. `scripts/report/shared_release_receipt.py:72,1441-1485`
   - 登记 frozen bundle 正式案内路径。
   - 静态态（exact/wrapper `as_of_block` 相等）保留原 `exact_path == supply_path` 与原拒绝
     文案，不改变存量同文件绑定。
   - 冻结态（exact 早于 wrapper）固定读取案内
     `data/solana_observation_bundle_frozen.json`，先用 `validate_receipt(..., case_root=root)`
     验案根 envelope，再复用 `validate_observation_bundle` 验 schema、producer、主网 genesis
     attestation、slot/closed/closure、holder outputs 实物；随后要求 canonical target 与 exact
     target 全等，且 exact owners 与 frozen bundle owners 的 `sha256+size` 全等。
   - 所有冻结态拒绝带“大白话”前缀“冻结态第五查快照必须哈希绑定冻结观测 bundle”。
2. `scripts/report/handoff_manifest.py:44-49,125-136,288-304,435-448`
   - 新增 generate/verify 共用的 `_solana_required_exact_paths()`。
   - 仅当 exact slot 早于 wrapper slot 时，把 frozen bundle 加进 `required_exact`；两处 READY
     深验都要求它同时存在于 `data_map` 与 manifest `artifacts`。
3. `references/scan-schemas.md:1180`
   - 把旧“永远同文件”改成静态同文件／冻结态指纹绑定两态契约，并写明 frozen bundle
     的深验和 handoff 绑定要求。
4. `references/analyze-workflow.md:82`
   - 写明动态 job spec 必须把 supply `--work-dir` 放在独立子目录（如
     `data/observe_live`），不得覆盖封账快照三件；冻结 bundle 固定命名。
5. `scripts/tests/contract_manifest.json:195`、
   `scripts/tests/contract_ids_snapshot.json:169`
   - 新增并登记 `CT-SQDGAP-34`，守住 frozen bundle owners 指纹契约锚点。
6. `scripts/tests/test_batch11_frozen_bundle_binding.py:48-295`
   - 新增 R1/G1、N1（缺件）、N2（target 错配）、N3（指纹错配）、N4（静态同文件零变化）、
     N5（handoff 清单缺 frozen bundle）离线回归。
7. `scripts/tests/run_all.py:171-172`
   - batch11 新测试进入全量守护套件，登记一次。
8. `scripts/tests/test_recon_fifth_check.py:90-94,148-152`
   - 两个 handoff mock 补回真实 exact receipt 本来必有的 `target`；不改测试原断言或生产语义。
9. `maintenance/repair-20260823-sqd-gap/batch11_red_evidence.txt:1-19`
   - 保存改生产代码前 R1 命令、exit 1 与旧同文件闸原始输出。
10. `maintenance/repair-20260823-sqd-gap/batch11_green_evidence.txt:1-53`
    - 保存定向、静态端到端、invariant 与完整 suite 结果。

## 红绿证据

- 红证据：`maintenance/repair-20260823-sqd-gap/batch11_red_evidence.txt`
  - 改生产代码前 exit 1；唯一红点为旧
    `exact_reconcile.inputs.holders_owners ... 不是同一文件`。
- 绿证据：`maintenance/repair-20260823-sqd-gap/batch11_green_evidence.txt`
  - batch11 G1/N1-N5 exit 0。
  - `test_repair_batch_d.py` exit 0，含现役 Solana 静态同文件端到端夹具。
  - exact/fifth-check/handoff/docs/contracts/invariant/py_compile/diff-check 定向回归全绿。

## handoff_manifest 冻结 bundle 核查结论

结论：**做，且仅冻结态纳入必进清单。**

理由：冻结态不再用 live supply owners 的路径同一性防伪，
`data/solana_observation_bundle_frozen.json` 已成为 exact 快照来源真实性的机器链路；若它不进
`data_map` 与 manifest `artifacts`，交接后可缺失或换包而 manifest 不知情，防伪链会在 handoff
处断开。实现由 generate 与 verify 共用一套 required-set 计算；静态态 exact/wrapper slot 相等
时不添加 frozen bundle，避免给存量静态案新增清单要求。

## `run_all.py` 结果

命令：

```text
MPLCONFIGDIR=/private/tmp/token-chip-analysis-mpl-cache \
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/run_all.py
```

真实结果：exit 1；135 项中 133 PASS、2 FAIL。

仅余环境失败：

1. `test_batch3_solana_vertical_slice.py`：loopback `socket.bind` 被沙箱拒绝；
2. `test_batch3_evm_vertical_slice.py`：loopback `socket.bind` 被沙箱拒绝。

两项堆栈均为 `PermissionError: [Errno 1] Operation not permitted`，发生在 fixture HTTP
server 创建处，未进入 producer/runner 业务执行。除这两项外无真实失败；新增
`test_batch11_frozen_bundle_binding.py` 在全套中 PASS。应由验收方在允许绑定
`127.0.0.1` 的环境重跑，取得完整 suite exit 0。

## 边界自查

- 静态态：原路径全等代码与拒绝文案保留；batch11 N4、`test_repair_batch_d.py` 和全套存量
  Solana 夹具通过。
- 冻结态：缺 frozen bundle、target 不全等、owners `sha256+size` 任一不等均 fail-closed；
  合法分家夹具通过。
- frozen bundle 不只检查自报指纹：案根 envelope、producer、schema、主网 genesis、slot、
  closed/closure 与两份 holder outputs 实物均走现行校验器。
- handoff generate/verify 都要求冻结态 frozen bundle 同进 `data_map/artifacts`；静态态不新增。
- `scripts/solana/replay_edges.py`、`scripts/report/reconciliation_report.py`、EVM 分支与 supply
  观测生产逻辑未改。
- `VERSION`、`CHANGELOG.md`、`pyproject.toml`、`SKILL.md` 未改；`git diff --check` exit 0。
- 用户提供的 `batch11_workorder.md` 保持未跟踪且未修改；ARC 案根一个字未动。
- 无密钥路径被读取或写入；无真实 API key 进入代码、测试、证据或报告。
- 工作树保持未提交；本批未执行 `git add`、`commit`、`push`、切分支或删除操作。
