# AI-1 Pack 2 fix 施工报告

日期：2026-08-15  
范围：F-01 handoff 案根 containment 的 fix 阶段  
结论：生产代码已完成 generate、verify、freeze/check-unseal 全入口收口；冻结 test-only 基线由 12/14 红转为 14/14 绿。指定回归全部 rc=0，`run_all.py` 只做 import 级登记检查，未运行会受 deploy-sync 预期红干扰的全量 suite。施工期间未执行任何 git 操作。

## 改动文件与行号

- `scripts/lib/case_paths.py:1-45`：新建共享 `safe_case_file(case_root, rel, *, must_exist=True) -> Path`。在任何 `Path` 规范化前用原始 `rel.split('/')` 拒绝非字符串、空串/纯空白、绝对路径以及空段、`.`、`..`；逐段检查 lexical symlink；最终用 realpath + `commonpath` 证明目标落在案根 realpath 内；存在目标只接受常规文件，`must_exist=True` 时缺件抛 `ValueError`。
- `scripts/report/handoff_manifest.py:38-45`：显式安排 `scripts/lib` 搜索路径并导入共享 helper。
- `scripts/report/handoff_manifest.py:192-295`：generate 的 artifact 汇流拆成 `discover()` 与 `add_explicit()`；`CONTRACT_FILES` 缺件保持跳过，`data_map`/`--include`/`--gate` 的非法或缺失显式引用统一 stderr + rc=2；`data_map` 路径 `ValueError` 不再被宽异常吞掉；`sealed/` 目录或直接条目为 symlink 时硬退 rc=2，普通子目录仍跳过。
- `scripts/report/handoff_manifest.py:492-558`：verify 在哈希、gate 语义重验前，先分别校验 `artifacts[].path` 与 `gates[].artifact`；只有安全且存在的常规文件才进入 READY 必备件集合与哈希重算。
- `scripts/report/handoff_manifest.py:625-670`：`resolve_bound_path()` 删除绝对路径放行分支，所有案内绑定统一先过 `safe_case_file`。仓库算法依赖不是案内 artifact，单独以 `check_algorithm_file()` 限死为验证器选定的 `entity_source_trace.py`/`wave_scan.py` 实物及其完整哈希、大小，不接受任意绝对路径。
- `scripts/report/handoff_manifest.py:1018-1029,1106-1111`：freeze provenance 初验与 source replay 分别使用固定算法依赖校验和收口后的案内绑定解析。
- `scripts/report/handoff_manifest.py:1161-1241`：check-unseal 对冻结主绑定、原始输入和算法依赖逐项重验；freeze CLI 的 `--members`/`--entity-file` 改为必须是案内安全相对常规文件，绝对路径、`../`、点段、空段和 symlink 均 rc=2。
- `scripts/report/a4_gate.py:41-84,403-418`：从共享模块 re-export `safe_case_file`；文件消费点保持原调用；`charts_dir` 保留独立的目录专用 `safe_case_dir`，不让常规文件 helper 兼任目录语义。
- `scripts/report/audit_release_gate.py:18-23,184-189`：导入共享 helper；`regular_case_path()` 收薄为 `try safe_case_file / except ValueError: None`，既有 `is None` 消费点不变。
- `scripts/tests/run_all.py:112-115`：按唯一测试文件例外追加 `test_repair_g1_audit_report.py`、`test_repair_g1_risk_flags_pipeline.py`、`test_repair_g1_handoff_containment.py` 三项 SUITE 登记及一行来源注释；未改任何测试断言或夹具。
- `maintenance/repair-20260815-g1/workorder_pack2_fix_done.md`：本施工报告。

## 验证实况

### 先红基线

命令：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_repair_g1_handoff_containment.py`  
修复前结果：rc=1，12/14 checks failed；与 `workorder_pack2_testonly_done.md` 的 a1-a3、b1-b6、c1 红因一致，c2/c3 防误伤基线为绿。

### 本包目标

| 验证 | 结果 | 实况 |
|---|---:|---|
| `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_repair_g1_handoff_containment.py` | rc=0 | PASS 14/14；a1-a3、b1-b6、c1-c3 全绿 |
| `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_handoff_manifest.py` | rc=0 | 68/68 checks 通过 |
| `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_a4_gate.py` | rc=0 | A4 gate 契约测试全部通过 |
| `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_audit_release_gate.py` | rc=0 | audit release gate 全部通过 |
| `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_distribution_gate.py` | rc=0 | distribution gate red-green contract 通过 |
| `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_repair_g1_audit_report.py` | rc=0 | F-02 四件套通过 |
| `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/docs_lint.py` | rc=0 | PASS：45 个文档，无断链，粗体配对完整 |

### SUITE 登记与语法

| 验证 | 结果 | 实况 |
|---|---:|---|
| 对 5 个改动 Python 文件执行 `ast.parse` | rc=0 | `syntax ok` |
| 通过 `importlib` import `scripts/tests/run_all.py` 并断言三项测试名均在字符串 SUITE 条目中 | rc=0 | `run_all import and registrations ok` |

遵照工单，未执行 `python3 scripts/tests/run_all.py` 全量 suite；原因是 deploy-sync 在当前融合前快照预期红，会制造与本包无关的干扰。

## Hunk 映射

| 文件/hunk | invariant | finding/入口 | 目的 | test owner |
|---|---|---|---|---|
| `case_paths.py:1-45` | 案内常规文件引用必须拒绝 abs、`.`、`..`、空段、逐段 symlink 与 realpath 越界 | F-01 共享不变量 | 建立单一、原串优先、ValueError 契约的 containment helper | F-01 c1 |
| `handoff_manifest.py:38-45` | handoff 不依赖其他 report 的延迟 import 副作用 | F-01 公共汇流 | 显式加载共享 helper | F-01 c1/c2 |
| `handoff_manifest.py:192-236` | discovery 缺件跳过；显式引用非法/缺件硬退 | G1-G4 | 拆分双入口并确保 data_map 路径错误不被宽 except 吞掉 | F-01 a1/a2/b1/b2/b6/c3 |
| `handoff_manifest.py:237-257` | sealed 目录和条目不得通过 symlink 把案外字节哈希进 manifest | G5 | 对目录本身及直接条目采取硬退策略 | F-01 b3 |
| `handoff_manifest.py:269-295` | declared gate artifact 是显式引用，必须先验路径与存在性 | G4 | 收口 `--gate` 后再建立 gate 记录 | F-01 同族/既有 handoff gate 回归 |
| `handoff_manifest.py:492-558` | consumer 不信 producer；manifest 两类引用须先 containment 再重验 | V1/V2 | 阻断手改 artifact/gate 指向案外文件 | F-01 a3；handoff 68 项 |
| `handoff_manifest.py:625-644` | 所有案内 ledger/binding 引用只接受案根内安全相对常规文件 | F1-F10/R10-15 | 删除 `resolve_bound_path` 的 isabs 放行，一次收口全部调用点 | F-01 b5；handoff freeze/check-unseal 回归 |
| `handoff_manifest.py:647-670,1018-1029,1194-1199` | 仓库代码依赖必须绑定验证器选定实物，不能被当成任意案外文件通道 | F-01 防误伤补强 | 保留算法代码哈希契约，同时与案内 artifact resolver 分账 | handoff 68 项正常 freeze/replay |
| `handoff_manifest.py:1106-1111,1161-1214` | replay argument、冻结主绑定及 provenance 绑定均走收口后的分类校验 | F1-F10 | 覆盖重放与 check-unseal 的真实消费链 | F-01 b5；handoff 原始边漂移回归 |
| `handoff_manifest.py:1227-1241` | freeze CLI 两个显式文件参数必须是案内相对路径 | F11 | 删除绝对 members/entity 放行 | F-01 b4 |
| `a4_gate.py:41-84,403-418` | A4 文件语义共用 helper，目录语义保持独立 | F-01 同族归并/目录豁免 | re-export 文件 helper，避免 charts_dir 被误当文件 | A4 gate 回归 |
| `audit_release_gate.py:18-23,184-189` | audit 的常规文件语义与 handoff 同源，失败仍返回 None | F-01 同族归并 | 薄封装且消费点零改动 | audit release 回归 |
| `run_all.py:112-115` | 新负向测试必须进入全量守卫且不改冻结断言 | 修复计划公共纪律 | 登记三个 G1 测试文件 | import 级 SUITE 检查 |

未映射生产/登记 hunk：0。

## 存量影响声明

- 新生成的 handoff artifact、gate、freeze 与 provenance 案内绑定继续使用相对路径，正常 generate→verify→freeze→check-unseal 已由 containment 14/14 与 handoff 68/68 双重证明。
- 含绝对路径、`../`、`.`、重复 `/` 空段或 symlink 的旧案内绑定，在 verify、freeze 或 check-unseal 时将 fail-closed；这是本修复的预期存量影响。已经交付且不重跑的静态报告字节不受影响。
- provenance 中两个仓库算法脚本的代码依赖记录不属于案内 artifact。它们只允许精确绑定当前验证器固定的 `entity_source_trace.py` 和 `wave_scan.py`，并重验完整 SHA-256 与大小；这不是通用绝对路径豁免。
- `sealed/` 采用计划允许的硬退策略：目录本身或直接条目为 symlink 时 generate rc=2；缺失 `sealed/`、普通文件以及其中的普通子目录扫描语义保持不变。
- A4 的 `charts_dir` 仍是目录专用契约；共享 `safe_case_file` 明确不支持目录，没有把 `must_exist=False` 偷换成通用路径 helper。

## 问题与决策

1. 首轮 fix 后，containment 已有 13/14 绿，但合法 freeze 被 provenance 的两个仓库算法脚本绝对路径阻断。直接让 `safe_case_file` 接受它们会重开案外通道，因此按语义分账：案内数据/台账绑定全部收紧；仓库代码依赖仅接受验证器写死的两个实物及其哈希。处理后 containment 14/14、handoff 68/68 均绿。
2. macOS 的 `/var` 与 `/private/var` realpath 别名会让临时案重放的路径字符串变化。`resolve_bound_path` 先用共享 helper 对 realpath 做 containment 证明，再返回案根词法路径供重放，避免只因系统目录别名造成 provenance 语义摘要漂移；安全判定仍以 realpath/commonpath 为准。
3. b3 的两种合法策略中选择硬退而非静默跳过，理由是 sealed 是密封边界，发现 symlink 时显式失败比悄悄减少密封清单更可审计。
4. 未发现测试断言错误，无待裁决项；除允许的 `run_all.py` SUITE 追加外，`scripts/tests/` 下文件均未修改。
5. 未执行任何 git 命令，未写唯一可写区之外的文件。
