# 批 16 完工报告：序列来源链登记路径按案根解析兜底

## 1. 结论

- 状态：**完成，沙箱验收 PARTIAL**。Batch 16 新回归 7/7 PASS；点名既有测试全部 PASS；完整 SUITE 为 142 项，其中 140 PASS、2 项仅因沙箱禁止 loopback bind 而 FAIL。
- 基线：开工 `git status --short` 无输出；冻结 `main@730495e23c416b656c879a13e3412054f20f7018`。
- 版本：`6.53.1 → 6.53.2`；`VERSION`、`pyproject.toml`、`SKILL.md`、CHANGELOG 索引与详情已同步。
- 生产改动唯一落点：`scripts/lib/camp_series_provenance.py::_resolve_ref` 函数体与 docstring。调用点、`:647` resolver 等值检查、`solana_exact_validate.py`、`audit_release_gate.py` 及全部既有测试均未改。

## 2. 开工门禁与锚文本

开工逐项核对工单锚文本，全部与冻结 HEAD 一致：

| 文件 | 冻结行 | 核对结果 |
|---|---:|---|
| `scripts/lib/camp_series_provenance.py` | 179–201 | `_resolve_ref` 定义、docstring、basename、原错误文案逐行一致 |
| 同上 | 226、229、232、235 | sidecar 两层 `search_dirs` 与三个调用点一致 |
| 同上 | 629、631、633、635、647 | reconcile 两层目录、三输入解析与 resolver 路径等值检查一致 |
| `scripts/lib/solana_exact_validate.py` | 354 | `_safe_case_path(case_root, rel)` 一致 |

不存在行号/描述漂移，故未触发停工。

## 3. 先红后绿证据

- 修生产代码前新增 `scripts/tests/test_batch16_resolve_ref_case_path.py`，只运行 `--r1`。
- 命令：`python3 scripts/tests/test_batch16_resolve_ref_case_path.py --r1`。
- 修前退出码：`1`。
- 修前异常原文：`sidecar reconcile.inputs.soltx_meta（soltx-a.repaired.meta.json）在序列目录与案根两层内都找不到`。
- 完整 HEAD、命令、退出码与 stdout 已固化在 `batch16_red_evidence.txt`；记录时 `camp_series_provenance.py` 尚未改动。
- 修后同一 R1 与全文件均绿：`PASS batch16 resolve_ref case path: 7/7`。

## 4. 实现对照

原 basename 两层循环逐字保留：仍按 `search_dirs` 顺序找 `Path(str(ref["path"])).name`，仍逐个拒末端 symlink，首个实物命中即做 size/sha256 三验；不匹配立即 raise，不会降级到新兜底。

只有两层均未命中后才进入登记路径兜底：

1. 登记值转字符串后拒绝绝对路径，并按原始 `/` 分段拒绝空段、`.`、`..`。
2. 对每个 base 保持原顺序；从 `base.resolve()` 起逐段执行 `is_symlink()`，中间目录与末端链接均拒。
3. `cand.resolve()` 必须等于 base 根或位于其 descendants 内，阻断逃逸。
4. 首个 `cand.is_file()` 命中即全等校验 size 与 sha256；任一不等立即 raise，不试下一个 base。
5. 全部未命中时保留“找不到”关键词，并明确 basename 与登记路径两条搜索均失败。

sha256 继续是权威身份；返回登记的原实物 `cand`，不会复制、改址或制造同名副本。

## 5. Batch 16 测试矩阵

| 场景 | 实际覆盖 | 结果 |
|---|---|---|
| R1 | `data/sqd_repair/<sha>/gen-x/soltx-a.repaired.meta.json` 仅深层在场 | PASS，返回深层实物 |
| N1 | `data/../outside.json` | PASS，登记路径拒收 |
| N2 | 绝对登记路径 | PASS，登记路径拒收 |
| N3 | `data/sqd_repair` 为指向案外的中间 symlink | PASS，逐段拒收 |
| N4 | 深层实物 size 错、sha256 错各一例 | PASS，首命中即拒 |
| N5 | 实物在 data/ 或案根的老 basename 形态；basename decoy 哈希错但深层真件在场 | PASS，老形态返回不变；decoy 命中即拒、不落兜底 |
| N6 | v4 receipt 的 `soltx_meta` 改登记深层实物，真实独立深验后跑 `registry_anchor_check` | PASS，resolver 与 meta 的 `resolve()` 等值成立 |

N6 降级说明：完整 repaired cache producer 布局需要构造 repair bundle、repair pointer、coverage resolution 与深层组合判定，夹具成本超出本工单单点 resolver 回归。按工单允许项，仅 monkeypatch `camp_series_provenance.resolve_formal_cache` 返回同一深层 meta；`solana_exact_validate.validate_reconcile_receipt_deep`、receipt 输入三验、`registry_anchor_check` 其余逻辑及 resolver/meta 路径等值检查均真实执行。

## 6. 同族 basename 口径核查（只核不改）

全库以 `Path(...).name`、`is_file()`、`search_dirs` 组合核查，结果如下：

| 位置 | 用途 | 是否会被 sqd_repair 深层 `soltx_meta` 卡住 | 结论 |
|---|---|---|---|
| `scripts/report/audit_release_gate.py:768–777` | `_recon_owner_snapshot` 的 Solana observation `holder_outputs.owners` 静态/活观察分支，按 basename 在 GPA/bundle 邻近目录找实物 | **不直接消费 soltx_meta**，所以不会触发本次 ARC 故障；但若 observation holder output 未来只按更深相对路径存放，存在同构 basename-only 风险 | 批 15 明令禁改静态段，本批只报，交调度方裁决 |
| `scripts/report/audit_release_gate.py:1331–1340` | figure2 收据输入 | 否；该协议明确要求 producer 输入以案根 basename 随案，且不消费 SQD cache | 保持不改 |
| `scripts/report/audit_release_gate.py:1463–1475` | analysis-state 绑定的 camp series | 否；sidecar `series_file` 协议本身是 basename，搜索对象是正式序列而非 cache meta | 保持不改 |
| `scripts/lib/solana_observation.py:622–633` | observation bundle 的 accounts/owners 输出 | 否；搜索域由 GPA 输入目录与 bundle 邻近目录定义，产物族不是 sqd_repair cache | 保持不改；未来若协议允许深层 holder output，应单独开单 |
| `scripts/report/shared_release_receipt.py:1522–1542` | 派生文件相关性筛选 | 否；`.name` 只判断文件类型，真正解析用完整安全相对路径、逐段 symlink 与 containment | 非 basename resolver，无缺口 |
| `scripts/lib/solana_exact_validate.py:553,581,608` | coverage pointer 与 map 内部路径字段归一比较 | 否；实物已在 `_check_file_ref` 按案根完整相对路径解析，`.name` 仅比较内层 metadata 的 basename 协议 | 无缺口 |
| `scripts/report/a5_report_seal.py:94` | PNG 引用与 report images 集合对账 | 否；只做已密封集合内名字唯一性，不负责磁盘路径解析 | 无缺口 |
| `scripts/report/identity_snapshot_receipt.py:55,59,155`、`scripts/solana/scan_token_accounts.py:254` | producer 写 basename 登记 | 否；这些是登记协议生成/等值检查，不是多目录 basename resolver | 无缺口 |

## 7. 验收结果

### 新回归与静态卫生

- `python3 scripts/tests/test_batch16_resolve_ref_case_path.py`：PASS，7/7。
- `python3 scripts/tests/changelog_lint.py`：PASS，活跃 60 条＋归档 139 条，版本唯一且倒排正确。
- `python3 scripts/tests/test_version_consistency.py`：PASS，6.53.2。
- `python3 -m py_compile scripts/lib/camp_series_provenance.py scripts/tests/test_batch16_resolve_ref_case_path.py scripts/tests/run_all.py`：PASS。
- `git diff --check`：PASS，无 whitespace error。
- `scripts/tests/run_all.py` 已在 SUITE 末尾登记 Batch 16，机械计数 `141 → 142`。

### 工单点名既有测试

| 命令 | 结果 |
|---|---|
| `test_a4_gate.py` | PASS，23 项 |
| `test_lit_regression_f007.py` | PASS，15/15 |
| `test_reconcile_v4_receipt.py` | PASS |
| `test_repair_batch_c.py` | PASS，227 checks |
| `test_repair_batch_d.py` | PASS，`BATCH D 全部通过` |
| `test_review_20260804_p105.py` | PASS |
| `test_sqd_consumer_v4.py` | PASS |

并行首跑 `test_repair_batch_d.py` 曾在 GPT-F-06 固定临时产物读取处出现 `KeyError: 'sampled'`；独立复跑通过，随后完整 run_all 内再次通过，定性为并行共享临时产物干扰，不是本改动回归。

### 沙箱完整 run_all

命令：`MPLCONFIGDIR=/private/tmp/batch16-runall-mpl python3 scripts/tests/run_all.py`

- 真实退出码：`1`。
- 分母：142；PASS：140；FAIL：2。
- Batch 16 末项：`PASS batch16 resolve_ref case path: 7/7`。
- 唯一失败 1：`test_batch3_solana_vertical_slice.py:625`，`ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)` 绑定时报 `PermissionError: [Errno 1] Operation not permitted`。
- 唯一失败 2：`test_batch3_evm_vertical_slice.py:281`，同样在 loopback bind 阶段报 `PermissionError: [Errno 1] Operation not permitted`。
- 两项均未进入业务断言；与既往沙箱残差一致。本报告不把 140/142 冒充全绿，允许 loopback bind 的本机全套须由调度方复跑。

## 8. 改动面与 diff

最终 `git diff --stat`（Git 原生命令不显示 3 个 untracked 新文件）：

```text
CHANGELOG.md                          | 10 ++++++++++
SKILL.md                              |  2 +-
VERSION                               |  2 +-
pyproject.toml                        |  2 +-
scripts/lib/camp_series_provenance.py | 37 ++++++++++++++++++++++++++++++++---
scripts/tests/run_all.py              |  3 +++
6 files changed, 50 insertions(+), 6 deletions(-)
```

另有白名单内新文件：

- `scripts/tests/test_batch16_resolve_ref_case_path.py`
- `maintenance/repair-20260823-sqd-gap/batch16_red_evidence.txt`
- `maintenance/repair-20260823-sqd-gap/batch16_done.md`

无 commit、无网络调用、无 key 写入、无案卷目录改动、无白名单外文件改动。

## 9. 待调度方裁决

1. 在允许 loopback bind 的本机复跑完整 142 项 SUITE，补齐全绿证据。
2. 决定是否另开工单处理 `audit_release_gate._recon_owner_snapshot` 静态段的 basename-only 通用深层路径风险；本批按禁改边界未动。
