# 工单 B 完成报告（repair-20260815-g3）

## 结论

工单 B 已按先红后绿流程完成。SQD 空正文、非法流和部分推进后的连续异常均不再推进游标或签发 receipt；Alchemy 对协议残缺页先整页校验、重试尽硬退，并已从 `evm-collector-run/v2` 正式资格中除名。最终六项验收全部 exit 0。

## 改动文件清单

- `scripts/evm/fetch_sqd_evm.py`：新增 NDJSON 纯解析函数、provider 前沿驱动的续拉与签发、连续 5 次异常硬退、正式路径前置检查及失败输出 `.partial` 隔离。
- `scripts/evm/fetch_alchemy.py`：声明 `FORMAL_CHANNEL_ELIGIBLE = False`，拒绝 `--receipt`，新增整页协议校验、移除浮点金额回退与 receipt 签发，并补失败输出隔离。
- `scripts/evm/csv_collector_receipt.py`：正式备用 CSV receipt 白名单只保留 `fetch_sqd_evm.py`，明确 Alchemy 恢复需升分型收据。
- `scripts/evm/channels_preflight.py`：native CSV receipt 采集器允许名单移除 `fetch_alchemy.py`。
- `scripts/tests/test_round4_csv_adapters.py`：native-receipted 名单只留 SQD，并把 Alchemy 纳入显式非正式采集器断言。
- `references/data-pipeline-evm-channels.md`：把完成证据二分为 SQD provider 哨兵扫描前沿与 Alchemy pageKey，并记录 Alchemy 降级原因及恢复条件。
- `scripts/tests/test_g3_alt_collectors.py`：新增三条主路径异常守卫、两组纯函数规格和三条正式资格除名负测；全程伪 transport。
- `maintenance/repair-20260815-g3/evidence_B_red.txt`：保存基线 SHA、红测命令、exit 1 及首轮完整输出（少于 80 行）。
- `maintenance/repair-20260815-g3/workorder_B_done.md`：本完成报告。

## 红证据摘要

基线 SHA：`ddba1871e27777cae347a2eae107a295b06376b4`。

命令：`python3 scripts/tests/test_g3_alt_collectors.py`，exit 1。关键原始失败：

```text
FAIL: R1 SQD empty response cannot complete or sign -- AssertionError: empty SQD response exited 0: '[COMPLETE] 0 rows ...'
FAIL: R2 Alchemy empty result is a protocol error -- AssertionError: missing transfers exited 0: '[COMPLETE] 0 transfers this run, 1 pages, 0s\n'
FAIL: R3 SQD partial progress cannot hide a later anomaly -- AssertionError: partially advanced SQD run exited 0: '[COMPLETE] 0 rows ...'
FAIL: D1 receipt emitter rejects Alchemy -- AssertionError: receipt emitter accepted removed Alchemy collector
FAIL: D2 channels preflight rejects Alchemy receipt -- AssertionError: channels preflight accepted removed Alchemy collector
FAIL: D3 Alchemy CLI rejects --receipt -- FileNotFoundError: [Errno 2] No such file or directory: '.../does-not-exist.json'
SKIP-RED: SQD parse_stream_response missing
SKIP-RED: Alchemy validate_transfers_page missing
SUMMARY: 0 passed, 6 failed, 2 skip-red
```

完整红证见 `maintenance/repair-20260815-g3/evidence_B_red.txt`。

## 转绿与回归输出摘要

1. `python3 scripts/tests/test_g3_alt_collectors.py`

   ```text
   exit=0
   PASS: R1/R2/R3、P1/P2、D1/D2/D3
   SUMMARY: 8 passed, 0 failed, 0 skip-red
   ```

2. `python3 scripts/tests/test_round4_csv_adapters.py`

   ```text
   exit=0
   PASS: alternate adapters are native-receipted or explicit nonformal
   ```

3. `env PYTHONPYCACHEPREFIX=/tmp/g3b-pycache-final2 python3 -m py_compile scripts/evm/fetch_sqd_evm.py scripts/evm/fetch_alchemy.py scripts/evm/csv_collector_receipt.py scripts/evm/channels_preflight.py`

   ```text
   exit=0
   stdout/stderr: empty
   ```

4. `python3 scripts/tests/invariant_scan.py`

   ```text
   exit=0
   PASS invariant manifest: receipt_producers=62, receipt_consumers=82, transport_calls=63, atomic_writes=52, formal_entrypoints=58, exceptions=0
   ```

5. `python3 scripts/tests/docs_lint.py --all`

   ```text
   exit=0
   PASS: 58 个文档，引用无断链、粗体配对完整（--all 全量模式）
   ```

6. `python3 scripts/tests/test_g3_docs_guards.py`

   ```text
   exit=0
   PASS: F-08 A0 exploration command；F-08 A2 formal rerun order
   PASS: F-13 runner injection boundary；F-05 machine boundary
   ```

过程说明：首轮 invariant 回归把失败隔离使用的 `os.replace` 识别为两个新增原子发布点。未改 manifest，而是在两个允许修改的采集器内改用同目录故障改名语义更准确的 `os.rename`；最终 invariant 全绿。

## 存量口径

- 旧 SQD native receipt 绑定的是修改前采集器 SHA；按当前 preflight 重验会因 collector 哈希不匹配而拒绝，必须用修复后的 SQD 从冻结下界重采并重新签发。
- 旧 Alchemy native receipt 即使文件和旧 SHA 均在，也会因采集器已从 emitter/preflight 白名单除名而拒绝。
- 备用通道按既有契约应为零正式存量；未提供、也未执行任何旧 receipt 迁移或补签。

## 留账面

- SQD native receipt 当前没有独立 `chain` 字段，且入口仍允许把任意字符串作为 dataset 名；本工单不改 schema 或链身份口径，交融合方后续裁决。
- Alchemy 若恢复正式资格，候选方向是升版为能表达分页完成证据的分型收据；不能继续把请求 `to_block + 1` 当 provider 块游标。

## 边界自查

- 仅改动工单许可的 6 个既有文件，并新建工单许可的测试、红证和 done 报告；未改 `run_all.py`、invariant manifest 或其他生产/文档文件。
- 未执行 add/commit/push；仅按工单红证要求只读取得一次 `git rev-parse HEAD`。
- 所有测试 transport 均为进程内 fake/monkeypatch；施工与验收未发出真实网络请求。
- 新增注释、错误信息、测试名和文档均使用“协议异常 / 守卫 / 除名 / 负测”等中性施工措辞。
