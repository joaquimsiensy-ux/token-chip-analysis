# 批 14 完成记录：accounting 观测 bundle 冻结态内容寻址兜底

## 结论

- **代码修复、定向验收与守护登记完成；当前沙箱的全套验收仍为 PARTIAL，不能报全绿。**
- Solana accounting 仍先按收据记录的原路径做完整 `path+size+sha256` 三验。只有原路径
  现物报精确的 `size mismatch` 或 `sha256 mismatch` 时，才把同一份 size+sha256 指纹
  改在 `data/solana_observation_bundle_frozen.json` 上解析；指纹全等后继续既有 bundle
  深验和 snapshot slot 绑定，没有跳过任何后续检查。
- 路径逃逸、文件自身符号链接、缺件、非普通文件等安全失败不进入兜底；冻结件缺失或
  指纹不符则重新抛出原路径的原始 mismatch，保持 fail-closed。
- 静态 Solana 仍在原路径首次三验成功；EVM 分支一个字未改。
- 最终 `run_all.py` 共 138 项：**136 PASS / 2 FAIL，exit 1**。两项均在业务逻辑前因
  当前沙箱禁止 localhost bind 而失败；batch14 新守护在全套中 9/9 PASS。故工单要求的
  “run_all 真实失败清零”尚未在本环境达成，须由允许 `127.0.0.1` bind 的 Fable 环境复跑。

## RED 证据（生产代码修改前）

- 证据：`maintenance/repair-20260823-sqd-gap/batch14_red_evidence.txt`
- 基线 HEAD：`4d23230d0eec7fd1ce7a0410622c2f1d5febdf71`
- 命令：`python3 scripts/tests/test_batch14_accounting_bundle_fallback.py --r1`
- 退出码：`1`
- 原始失败：`ValueError: solana accounting observation bundle size mismatch`
- 夹具事实：accounting 收据绑定封账 bundle 的 size+sha256，但正式路径已放合法活 bundle，
  冻结件保存封账原字节；现行消费点在打开冻结件前稳定拒绝。

## 改动与行号

1. `scripts/report/shared_release_receipt.py:1756-1784`
   - 仅在 Solana accounting 局部分支捕获两种精确内容 mismatch。
   - 用复制后的同一 `bundle_ref` 只替换 path 为
     `SOLANA_FROZEN_OBSERVATION_BUNDLE`，再次调用未放宽的 `_bound_case_ref`，因此冻结件
     仍必须在案根内、存在、为普通文件、非文件自身 symlink，且 size+sha256 全等。
   - 原路径的安全类 `ValueError` 不捕获为兜底；冻结件校验失败重新抛原始 mismatch。
   - 兜底成功后仍执行 `json.loads`、`validate_observation_bundle(..., bundle_path=...)`、
     `expected_mint` 和 `observed_context_slot == snapshot.slot`。
2. `scripts/tests/test_batch14_accounting_bundle_fallback.py:1-226`
   - R1/G1：正式路径为不同大小的合法活 JSON，冻结件为封账原字节。
   - 补测同大小/不同 sha256 的第二个允许兜底分支。
   - 用 genesis 错链冻结件证明指纹命中后确实进入既有深验。
   - N1/N2：冻结件改字节或缺失均保留原始 size mismatch。
   - N3：`../` 路径逃逸与文件自身 symlink 各自直接拒绝，合法冻结件也不得救活。
   - N4：静态 Solana 与 EVM 正向回归。
3. `scripts/tests/run_all.py:180-181`
   - 新增 batch14 测试到全量 `SUITE`；最终全套汇总可见该项 9/9 PASS。

## 禁改面核对

- 通用 `_bound_case_ref` 保持 `scripts/report/shared_release_receipt.py:333-358` 原样；路径
  安全、普通文件和 path/size/sha256 三验没有放宽。
- `validate_observation_bundle`、`scripts/solana/accounting_gate_sol.py` 生产者、
  `scripts/lib/supply_truth_gate.py`、`scripts/solana/replay_edges.py`、批 10–13 改面均未改。
- EVM accounting 仍是 `shared_release_receipt.py:1733-1754` 原路径和原深验。
- `VERSION`、`SKILL.md`、`pyproject.toml`、CHANGELOG、契约注册表与 ID 快照均未改。

## 同型绑定波及面逐处核查

1. **Solana accounting producer** — `scripts/solana/accounting_gate_sol.py:157-178`
   - producer 对它当时消费的 bundle 深验后记录绝对 path、size、sha256。这里正是封账期
     收据来源，但 producer 没有消费“后来被活观测替换的路径”，无需改。
2. **Solana accounting 公共 consumer** —
   `scripts/report/shared_release_receipt.py:1756-1784`
   - 全库唯一把 `accounting.observation_bundle` 打开并验 path/size/sha256 的实现；本轮局部
     修复点。返回前仍完成 bundle 深验、mint 和 slot 绑定。
3. **shared release 调用链** — `scripts/report/shared_release_receipt.py:1811-1840`
   - `validate_sources` 和 `create_bundle` 都调用上述公共 validator；冻结态第二次带
     exact target 重验也走同一实现，故无需第二份同型补丁。
4. **handoff verify** — `scripts/report/handoff_manifest.py:420-459`
   - verify 在 reconciliation/exact 深验后于 :451-457 调公共 accounting validator；
     本轮修复传递覆盖 verify，没有手抄 path 比对。
5. **audit release** — `scripts/report/audit_release_gate.py:487-493,1438-1446`
   - `check_accounting` 直接复用公共 validator，shared receipt 验证也传递经过同一实现；
     无独立旧路径假设。`:625-635` 的另一处 Solana observation bundle 深验读的是 supply
     收据，不是 accounting 封账旧路径。
6. **supply_truth producer/consumer** — `scripts/lib/supply_truth_gate.py:590-623,769-772`；
   `scripts/report/shared_release_receipt.py:1298-1326`
   - producer 与 receipt 同时绑定本轮活 bundle；consumer 按该 receipt 自己的路径打开，
     并把 snapshot/supply slot 与 receipt target/observed slot 绑定。它没有绑定 accounting
     的封账旧字节，属于工单点名的自洽活 bundle，不应加兜底。
7. **exact_reconcile 冻结件绑定** — `scripts/report/shared_release_receipt.py:1441-1485`
   - 冻结态直接打开固定命名的 frozen bundle，并把 target 与 holders owners 指纹绑定；
     不读取已被活观测占用的正式旧路径，批 11 语义完整，无同型缺口。
8. **handoff generate** — `scripts/report/handoff_manifest.py:289-308`
   - READY generate 只深验 reconciliation、exact 必备路径和 derived bindings，不调用
     `validate_accounting_receipt`，没有 accounting bundle 的旧路径比较，因此无同型代码可修。
   - `python3 scripts/tests/test_recon_fifth_check.py` 两次真实打印 `[generate] READY ...` 且
     exit 0；`python3 scripts/tests/test_handoff_manifest.py` 的 `generate READY exit 0` 也通过。

全库对 `validate_accounting_receipt(`、`SOLANA_FROZEN_OBSERVATION_BUNDLE`、
`observation_bundle` 与 `_bound_case_ref` 的生产 Python 面扫描后，除以上路径外未发现另一个
“A0/封账期收据仍按已被活观测替换的正式路径校验旧内容”的消费点。

## 文档结论

- `references/scan-schemas.md` 没有 accounting observation bundle 的路径绑定段落；现有
  `:1180-1181` 是 reconciliation exact/live/frozen 语义，`:380` 是通用 holder_outputs
  文件级绑定，均不是本轮 accounting 绑定表述。按工单“无则 done 说明”，该文档未改。

## 测试结果

### 定向与硬闸

- `python3 scripts/tests/test_batch14_accounting_bundle_fallback.py`：**9/9 PASS**。
- `python3 -m py_compile scripts/report/shared_release_receipt.py scripts/tests/test_batch14_accounting_bundle_fallback.py`：PASS。
- `test_batch13_accounting_target.py`：**8/8 PASS**。
- `test_batch11_frozen_bundle_binding.py`：PASS。
- `test_evm_observation_release.py`：**11/11 PASS**。
- `test_recon_fifth_check.py`：PASS，handoff generate READY exit 0。
- `test_handoff_manifest.py`：**68 项 PASS**。
- `test_audit_release_gate.py`、`test_r9_batch3_release_guards.py`、
  `test_reconciliation_runner.py`：PASS。
- `invariant_scan.py`：PASS，计数保持
  `receipt_producers=75, receipt_consumers=112, transport_calls=65,`
  `atomic_writes=56, formal_entrypoints=61, exceptions=0`。
- `docs_lint.py --all`、`test_contract_routes.py`、`test_version_consistency.py`、
  `test_batch4_invariant_guards.py`、`git diff --check`：PASS。

### 最终 run_all

- 命令：`python3 scripts/tests/run_all.py`
- 结果：**138 total / 136 PASS / 2 FAIL，exit 1**。
- 新登记 `test_batch14_accounting_bundle_fallback.py`：**9/9 PASS**。
- 仅余两项：
  - `test_batch3_solana_vertical_slice.py:625`：
    `ThreadingHTTPServer(("127.0.0.1", 0), ...)` →
    `PermissionError: [Errno 1] Operation not permitted`。
  - `test_batch3_evm_vertical_slice.py:281`：同一 localhost bind 错误。
- 两项都在 producer/business assertions 前失败；这是当前沙箱能力阻塞，不是本批代码
  回归，但真实全套退出码仍为 1。因此本记录保持 PARTIAL，不伪装为全绿。

## 边界自查

- 改/建文件仅为：
  - `scripts/report/shared_release_receipt.py`
  - `scripts/tests/test_batch14_accounting_bundle_fallback.py`
  - `scripts/tests/run_all.py`
  - `maintenance/repair-20260823-sqd-gap/batch14_red_evidence.txt`
  - `maintenance/repair-20260823-sqd-gap/batch14_done.md`
- 用户提供的 `batch14_workorder.md` 只读，未改。
- 未读取或修改密钥；未访问、修改或重跑 ARC 案根。
- 本检出没有 `sync-from-cc.sh` / `SYNC.md`，只记录缺失，不当作同步 PASS。
- 分支仍为 `main`；未 commit、未 push、未切分支。

## Fable 验收待办

在允许绑定 localhost 的验收环境执行：

```bash
python3 scripts/tests/run_all.py
```

只有得到 **138/138 PASS、exit 0** 后，才可把本批从 PARTIAL 改为正式完成并由 Fable
代 commit；本轮不得因环境失败修改纵切片或弱化 `run_all` 守护。
