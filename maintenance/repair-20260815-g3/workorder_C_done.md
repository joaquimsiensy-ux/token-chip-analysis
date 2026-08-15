# 工单 C 完成报告（repair-20260815-g3）

- 基线：`ddba1871e27777cae347a2eae107a295b06376b4`
- 日期：2026-08-15
- 范围：G3R1-01/02/03/05/06/07
- 结论：工单 C 指定修复、先红后绿、定向回归与四项变异自证均完成；G3R1-04 按边界未修。

## Finding 处置表

| Finding | 处置 | 验证证据 |
|---|---|---|
| G3R1-01 | `parse_stream_response` 强制 `header.number` 为非 bool 的 int，并限制在请求闭区间；主循环传入当前请求上下界；正式 CSV receipt 强制 `provider_next_block == requested_to`。 | R4 越界哨兵、R5 真实行加越界哨兵均非零退出、不签 receipt、产出 `.partial`；纯函数 float/数字字符串/上下界外均拒绝；emitter 越界拒绝。 |
| G3R1-02 | SQD 每条 log 强制校验 topics 数量与逐项 66 位 hex、data hex、transactionHash、logIndex；timestamp 存在时只接受安全整数并把日期溢出统一转为 `ValueError`。 | R6 半残 log 非零退出、不签 receipt、产出 `.partial`；缺 topics、仅 2 topics、短 topic、非法 data、乱串 logIndex、非法或溢出 timestamp 均拒绝。 |
| G3R1-03 | A0 守卫改为完整连续 EVM 命令串断言，并对同一 EVM inline command 增加正式文件名负向断言。 | 文档守卫绿；M1 正式文件名回退、M2 将 `--exploration` 挪入括注均 `EXPECTED_RED`。 |
| G3R1-04 | **边界外未修，交融合方**。未改 `SKILL.md`。 | 白名单边界自查。 |
| G3R1-05 | Alchemy `rawContract.value` 与 `blockNum` 均改为 `re.fullmatch(r"0x[0-9a-fA-F]+", value)` 后再解析。 | `-0x5`、`0x_f`、前后空白三类反例对两个字段均拒绝。 |
| G3R1-06 | `--receipt` help 改为“已除名：Alchemy 无 provider 侧完成证据，不支持正式 receipt，仅探索采集”。 | D3 仍验证 CLI 立即拒绝；D4 验证 help 含除名指引且不再承诺正式 v2 receipt。 |
| G3R1-07 | F13 守卫锚定 `[输出 JSON schema` 所在段；F05 对两份文档分别要求存在以 `**机器化边界**` 开头的段，并在该段内校验三项关键子串。 | 文档守卫绿；M3 将 F13 关键句移出 schema 段、M4 将机器化边界降级为 HTML 注释均 `EXPECTED_RED`。 |

## 先红证据

完整摘要见 `maintenance/repair-20260815-g3/evidence_C_red.txt`。

- `python3 scripts/tests/test_g3_alt_collectors.py`：退出 1，`6 passed, 6 failed`。红项为 R4、R5、R6、SQD 新签名/字段契约、Alchemy 畸形 hex、emitter 上界。
- `python3 scripts/tests/test_g3_docs_guards.py`：退出 0，4 项全绿。当前真实文档未变异，本来即绿，符合工单说明。
- 补充边界反例：加入超平台时间范围的整数 timestamp 后，修复前得到 `OverflowError: timestamp out of range for platform time_t`、退出 1；随后统一为协议 `ValueError` 并转绿。

## 转绿与回归

| 命令 | 结果 |
|---|---|
| `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_g3_alt_collectors.py` | exit 0；`13 passed, 0 failed, 0 skip-red` |
| `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_g3_docs_guards.py` | exit 0；4/4 PASS |
| `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_round4_csv_adapters.py` | exit 0；PASS |
| `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/invariant_scan.py` | exit 0；`receipt_producers=62, receipt_consumers=82, transport_calls=63, atomic_writes=52, formal_entrypoints=58, exceptions=0` |
| `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/docs_lint.py --all` | exit 0；58 个文档 PASS |
| `PYTHONPYCACHEPREFIX=/tmp/repair_g3_c_pycache_final python3 -m py_compile scripts/evm/fetch_sqd_evm.py scripts/evm/fetch_alchemy.py scripts/evm/csv_collector_receipt.py` | exit 0 |

## 变异自证（临时内存副本，不入库）

| 变异 | 结果 |
|---|---|
| M1：A0 输出回退到 `accounting_mode.json` | `EXPECTED_RED`：完整探索命令不匹配 |
| M2：A0 将 `--exploration` 从连续命令移入括注 | `EXPECTED_RED`：完整探索命令不匹配 |
| M3：F13 两个关键短语移出 JSON schema 段、保留在全文件其他位置 | `EXPECTED_RED`：schema 段缺少“逐字写入” |
| M4：F05 将 `**机器化边界**` 段降级为 HTML 注释 | `EXPECTED_RED`：段落不再以机器化边界标题开头 |

汇总：`MUTATION SUMMARY: 4/4 expected red`，命令退出 0。真实 `references/analyze-workflow.md` 与 `references/research-workflows.md` 未改。

## 边界自查

- 既有文件只施工：`scripts/evm/fetch_sqd_evm.py`、`scripts/evm/fetch_alchemy.py`、`scripts/evm/csv_collector_receipt.py`、`scripts/tests/test_g3_alt_collectors.py`、`scripts/tests/test_g3_docs_guards.py`。
- 只新建：`maintenance/repair-20260815-g3/evidence_C_red.txt`、`maintenance/repair-20260815-g3/workorder_C_done.md`。
- 未改 `SKILL.md`，未处理边界外 G3R1-04。
- 零真实网络；所有采集主路径测试均使用伪 transport。
- 未执行 Git 写操作；仅按工单要求执行一次只读 `git rev-parse HEAD` 记录基线。
