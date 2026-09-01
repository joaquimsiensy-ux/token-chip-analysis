# 批 18 第三轮复核施工完成记录

日期：2026-09-01  
工作基线：`56e7cf3cce74b873f847fd929a8e8fdf95622ed7`  
等价代码基线：`50d7767`  
工单 SHA-256：`014659d9a2b37eb5834f972fc88ed0bb0a5fec89ceaee9a6208db5e3a66d68f8`  
状态：**机械施工、RED、定向 GREEN、Batch D 连续 5 次、版本/文档/lint 与白名单核验均完成；未 commit。全量 SUITE 146 与 ARC 只读实测按工单留给验收方。**

## 1. 开工门与 RED

- `main=56e7cf3`；`git diff 50d7767..56e7cf3` 只有本工单文件历史版本，代码零差异，按用户声明的等价工作基线开工。
- 开工时工作树 clean；50d7767 锚点逐项命中。
- 生产文件零改动时先落 `batch18_review3_red_evidence.txt`。
- R1：真实 repaired exact-reconcile 夹具先完成 `validate_repair_bundle_deep`，日志明确出现 `RED_PRECONDITION ... PASS`；随后旧递归 collector 打开 bundle 的 evidence manifest、遍历 200 个真实叶并原样报 `ValueError: reconciliation witness 文件闭包超过 128 个文件`。未 monkeypatch 深验。
- F4：mock monotonic 推进越过 deadline，基线首个早退报告直接索引原样报 `KeyError: 'sampled'`。

## 2. frontier 实现与担保边界

- `_reconciliation_bound_files` 已替换为 `_reconciliation_frontier_files`；删除引用 JSON 的 BFS/队列/递归打开。兜底遍历只处理验证器已返回的内存 receipt 对象。
- `DeepReconciliationWitness.bound_files` 已不兼容更名为 `frontier_files`；frozen dataclass 注解、签发构造、消费循环与测试引用同步。`payload_sha256`、WeakSet 签发身份、`report_sha256` 均保持原语义。
- wrapper 本体不进入 `frontier_files`，继续由 `report_sha256` 单独锁定。
- 所有 frontier 内容哈希与消费复验使用 `_stream_sha`，块大小 131072 字节；不改全局 `sha()`。
- frontier 最多 512 件，超过直接拒签；兜底内存树深度最多 64。成本是 `O(frontier 总字节)`，512 只限制件数，不限制总字节。
- 担保：wrapper、各家族 receipt 本体、receipt JSON 的一级实物引用与显式冻结 bundle 在签发后发生任意字节变化，同一 witness 消费必拒。
- 不担保：repair bundle/manifest 再指向的更深 evidence leaf 在签发后的变化。同一 witness 可继续消费；但重新签发会重新进入真实深验并拒绝被改叶。这是用户 2026-09-01 裁决的公开边界，不宣称递归实时新鲜度。

## 3. 必选层与 `validate_reconciliation_check` 逐条比对

| 家族/对象 | 现行深验实际消费与 resolver | frontier 固化 | 结果 |
|---|---|---|---|
| 全家族 wrapper receipt refs | `checks[key].receipt` 由 `ref_ok(root, ref)` 解析；ref 可无 size | 对 `RECON_CHECK_KEYS[family]` 每项调用同一 `ref_ok`，绑定 receipt 本体 | 等同，fail-closed |
| 全家族 receipt envelope inputs | `validate_receipt(case_root=...)` 对每个 `inputs` ref 使用案根约束、size/sha 校验；EVM balance/supply/time 与 supply_truth 的 config、balances、replay_stats、transcript、observation_bundle、gmgn/waiver 等均从此层进入 | 对每份已深验 receipt 的全部 `inputs.items()` 调用 `_bound_case_ref(root, ref, label)`；不是易漏的名称白名单 | 同 resolver 的严格超集枚举，fail-closed |
| EVM 四项 receipt | `validate_reconciliation_check` 进入 balance、supply、supply_truth、time 分支；provider 路径仍真调深验 | 绑定四份 receipt 本体及其全部一级 inputs；未改变 provider/validator 调用路径 | N3 语义不变 |
| Solana exact_reconcile | receipt inputs 包含 repair_bundle、repair_pointer、coverage_* 及其它冻结输入，深验继续进入真实 exact validator | `exact_reconcile.inputs` 全量经 `_bound_case_ref` 绑定 | 全覆盖，fail-closed |
| Solana supply output | `receipt["output"]` 经 `ref_ok` 消费 | 对同一字段调用 `ref_ok` 并绑定 | 等同，fail-closed |
| Solana balance/time anchor output | anchor validator 消费 receipt 顶层 `output`，按案根 ref 约束 | balance/time 各自顶层 output 经 `_bound_case_ref` 绑定 | 等同，fail-closed |
| Solana holder outputs | `solana_observation` 三基准先中：`inputs.gpa_rpc` 实物父目录，再 supply receipt 父目录，再其 `data/`；校验 size/sha | 复刻相同顺序和 basename 选择，命中后校验 size/sha、案根包含并绑定 accounts/owners | 分离 bundle 布局已回归，fail-closed |
| Solana frozen fifth-check | exact target 与发布 target slot 不同的冻结路径显式消费 `data/solana_observation_bundle_frozen.json` | 同条件下用 `regular` 显式绑定该 bundle | 等同，fail-closed |
| 其它三字段一级 ref | 深验已返回的 receipt 对象中可能存在非必选命名的 `{path,size,sha256}` | 只遍历内存对象；分别以案根和 receipt 父目录解析，逐段拒 symlink；两个基准若命中不同实物则两个都绑定；失败只在兜底层跳过 | 宁严兜底，不打开引用文件 |

必选 ref 的形状、解析、缺件、越界或 hash 不符均拒签；只有兜底层允许解析失败后跳过。中间 symlink 及 macOS `/tmp` alias 按现行必选 resolver 的归一行为放行；兜底 candidate 仍按工单逐段拒 symlink。

## 4. R1-R4 与 resolver GREEN

- R1：100 个真实 repair slot、200 个 evidence leaf；真实 exact 深验通过后签发成功。`frontier_files` 含 repair bundle，不含 200 个叶。
- R2：签发后改一级 owners 一字节，同一 witness 消费统一报 `reconciliation witness 无效/过期`。
- R3：wrapper 不在 frontier，但改 wrapper 由 `report_sha256` 拒；冻结 bundle 在 frontier，改动后由 frontier 复验拒。
- R4：真实 repaired exact 三步边界通过：改深层 leaf 后同一 witness 可消费；不恢复 leaf 重新签发被真实深验拒；改 bundle/manifest 本体后同一 witness 被拒。
- resolver：gpa_rpc 实物父目录分离布局、案内中间 symlink、macOS alias 与现行深验等价通过；双基准同名不同实物时两个都绑定；必选 ref 实物缺失时拒签。

## 5. F4 五个 bail 点映射

| 50d7767 锚/当前调用点 | `sampling_phase` | 早退时已有部分状态 | `counts_complete` | 原因与 wall 规则 |
|---|---|---|---|---|
| :293 / 当前 :368，边集不存在 | `edges_missing` | 边数/slot/抽样/深挖均为零或空 | `false` | 保留“边集不存在”直接原因；若 clock 已越界再追加唯一墙钟原因 |
| :301 / 当前 :377，边集解析无效 | `edges_invalid` | resolver/RPC 已可建立；边集有效计数仍未完成 | `false` | 保留解析异常原文；墙钟原因并存、去重 |
| :304 / 当前 :380，边集为空 | `edges_empty` | `n_edges=0`，lo/hi 按实际解析结果 | `false` | 保留“边文件为空”直接原因；墙钟原因并存、去重 |
| :324 / 当前 :403，签名发现失败 | `signature_discovery` | 已有边集范围、模式、签名/decoded 部分计数 | `false` | 保留“mint 签名史为空/拉取失败”；auto probe 的 `wall_hit` 已并入共享 flag |
| :350 / 当前 :431，初始化发现失败 | `init_discovery` | 已有边集、签名、decoded 与初始化部分计数 | `false` | 保留“抽样未命中”直接原因；墙钟原因并存、去重 |

单一 `_build_report` 供上述五点与 complete 路径共用。每条路径均输出完整 `sampled` 键集：`decoded_txs`、`init_events`、`alive`、`closed`、`deep_checked`、`deep_account_classes`、`gma_batch_failed`、`wall_truncated`、`sampling_phase`、`counts_complete`。`deep_account_classes` 始终有 `events_found/all_zero_delta/fetch_failed` 三键。`started_at` 是 `main()` 第一条业务语句；deadline、四个循环比较点、最终 deadline 复核与 `elapsed_sec` 均在 monotonic 域，`generated` 单独保留墙上时间。最终 builder 瞬间越过 deadline 时，除既有优先级更高的 `LEAK_FOUND` 外，报告、打印状态与退出码同步转为 `INVALID_SAMPLE/1`。

## 6. 既有断言同步说明

`scripts/tests/test_batch18_review_digest.py` 中只有下列既有断言因公开合同变更而同步；未改其它测试文件：

1. `test_f2_issued_witness_binds_deep_file_closure` 更名为 `test_f2_issued_witness_binds_frontier_files`，字段断言 `bound_files` 改为 `frontier_files`；receipt/owners 一级新鲜度断言保持不变。
2. review2 F1 仅把构造/访问字段 `bound_files` 改为 `frontier_files`；payload 原地篡改必拒断言不变。
3. `test_review2_f2_recursive_closure_binds_supply_output` 更名为 `test_review2_f2_supply_output_stays_in_mandatory_frontier`；断言从“递归发现 output”改为“supply output 属于必选 frontier”，字段同步改名。
4. review2 F2 的形状上限期望从旧闭包 `128` 同步为 frontier `512`；供给 output 改字节后同一 witness 必拒的既有安全断言保留。
5. 测试 main 列表只同步上述函数名并追加 5 个 review3 测试函数。`test_repair_batch_d.py` 未改。

## 7. GREEN 回归记录

| 命令 | 结果 |
|---|---|
| `python3 scripts/tests/test_batch18_review_digest.py` | PASS 10/10；含真实 R1/R4、R2/R3、resolver、F4 五 bail |
| `python3 scripts/tests/test_batch18_shared_bundle_witness.py` | PASS 6/6；N11 错误文本逐字保持 |
| `python3 scripts/tests/test_batch15_three_ledgers_frozen.py` | PASS 12/12；N9 calls=1，N10 calls=2 |
| `python3 scripts/tests/test_reconcile_v4_receipt.py` | PASS |
| `python3 scripts/tests/test_repair_batch1.py` | PASS |
| `python3 scripts/tests/test_r9_batch3_release_guards.py` | PASS 6/6 |
| `python3 scripts/tests/test_r9_batch3_solana_observation.py` | PASS |
| `python3 scripts/tests/test_repair_batch_d.py` 连续运行 5 次 | 1/5 至 5/5 均 `BATCH D 全部通过`，无失败重跑 |
| `python3 scripts/tests/changelog_lint.py` | PASS；活跃 67 条、归档 139 条 |
| `python3 scripts/tests/docs_lint.py --all` | PASS；59 个文档 |
| `python3 scripts/tests/test_version_consistency.py` | PASS；五处一致为 7.0.0 |
| `git diff --check` | PASS |

全量 **未执行**；按工单由验收方本机在仓库根执行 `PYTHONDONTWRITEBYTECODE=1 nohup python3 scripts/tests/run_all.py >/private/tmp/batch18-review3-run-all.log 2>&1 &`，分母必须保持 146，不能用定向回归冒充 146/146。

## 8. ARC 案根只读实测命令

施工未读取或修改 ARC 案根。验收方在仓库根执行下列命令；它只读签发/消费并只把统计打印到 stdout，不向 ARC 写结果文件。命令通过进程内包装 `_reconciliation_frontier_files` 单独计时，不改变验证逻辑：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import json
import sys
import time
from pathlib import Path

repo = Path.cwd().resolve()
case = Path("/Users/uravvv/Documents/5.6筹码分析/ARC分析").resolve()
sys.path.insert(0, str(repo / "scripts/report"))
import shared_release_receipt as shared

original_frontier = shared._reconciliation_frontier_files
original_stream = shared._stream_sha
timing = {}

def timed_stream(path):
    started = time.monotonic()
    value = original_stream(path)
    timing["frontier_hash_sec"] = (
        timing.get("frontier_hash_sec", 0.0) + time.monotonic() - started)
    return value

def timed_frontier(*args, **kwargs):
    started = time.monotonic()
    shared._stream_sha = timed_stream
    try:
        value = original_frontier(*args, **kwargs)
    finally:
        shared._stream_sha = original_stream
    timing["frontier_collect_sec"] = time.monotonic() - started
    return value

shared._reconciliation_frontier_files = timed_frontier
started = time.monotonic()
witness = shared.witness_reconciliation_report(case)
sign_sec = time.monotonic() - started
rows = []
for raw_path, _digest in witness.frontier_files:
    path = Path(raw_path)
    rows.append({"path": str(path), "bytes": path.stat().st_size})
started = time.monotonic()
shared._consume_reconciliation_witness(case, witness)
consume_sec = time.monotonic() - started
print(json.dumps({
    "frontier_files": len(rows),
    "frontier_total_bytes": sum(row["bytes"] for row in rows),
    "frontier_largest_five": sorted(
        rows, key=lambda row: row["bytes"], reverse=True)[:5],
    "sign_total_sec": sign_sec,
    "frontier_hash_sec": timing["frontier_hash_sec"],
    "frontier_collect_sec": timing["frontier_collect_sec"],
    "same_witness_consume_sec": consume_sec,
}, ensure_ascii=False, indent=2))
PY
```

验收判定不是预设的“<1GB/秒级”。若实际总字节达到 GB 级或同 witness 消费达到分钟级等显著超出，应停止发布并交用户重新裁决，不能强行判绿。

## 9. 版本、白名单与交接边界

- 版本五处均为 7.0.0：`VERSION`、`pyproject.toml`、`SKILL.md` 版本标记、CHANGELOG 活跃索引、CHANGELOG 详情。
- CHANGELOG 7.0.0 具备出处根因、设计实现、消费/F4、测试、盲审验收、成本质量六栏；明确用户裁决与担保/不担保边界。
- 6.54.1/6.54.2 历史条目中的 `bound_files` 原文未改。
- 相对 50d7767，`receipt_validate.py`、`solana_observation.py`、`solana_exact_validate.py`、`test_repair_batch_d.py`、handoff/audit release 的差异列表为空。
- 实际施工文件全部落在工单白名单；ARC 案根、API key 未触碰。
- 未 commit。

## 10. 验收方补记(Fable,2026-09-01)

- 定向复跑亲证:digest 10/10、batch15 冻结消费 12/12、batch_d 连跑 3 次全过(F4 前 3/5 概率 KeyError,已转稳)。
- 全量 SUITE:146/146 全部通过(rc=0,分母亲核 len(SUITE)=146)。
- diff 逐段亲核:9 文件全在白名单;禁改文件差异为空;CHANGELOG 历史条目原文未动。
- **ARC 只读实测门(通过)**:frontier 29 件 / 824,938,917 字节(824.9MB);最大五件=修复边集 497.8MB、coverage_resolution 141.8MB、slot_counts 97.7MB、_gpa_raw_all 43.1MB、supply_snapshot 10.5MB;收集+哈希 1.13s;同 witness 消费重哈希 0.36s;全部指纹匹配。判据(总字节 GB 级/消费分钟级)未触发。
- 实测方法说明:完整签发(含深验)实测进程被中止,frontier 统计改用静态枚举(盘上 wrapper/receipts 直构 receipts 后调 `_reconciliation_frontier_files`,与签发路径同函数);签发总耗时以基线实测为准——v6.54.2 基线上同案深验真跑 4661.5s(77.7 分钟)成功后在旧 collector 撞 128 拒签(scratchpad/arc_witness_timing.txt,盲审 P1 活体复现),深验成本不因本修复改变。
- 基线红证据旁证:见上条——真实 ARC 案上"深验成功→闭包超过 128 拒签"原样复现,与 R1 合成案红证据同构。
