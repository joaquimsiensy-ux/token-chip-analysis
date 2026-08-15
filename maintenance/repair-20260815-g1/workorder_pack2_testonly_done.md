# AI-1 Pack 2 test-only 施工报告

日期：2026-08-15  
范围：F-01 handoff 案根 containment 的 test-only 阶段  
结论：新增负向测试在未修复生产代码上得到目标先红证据：12/14 checks 红，a1-a3、b1-b6 与 c1 全部暴露缺口；c2、c3 两条防误伤基线为绿。既有 `test_handoff_manifest.py` 68/68 通过。未修改生产代码，未创建 `scripts/lib/case_paths.py`，未执行 git 操作。

## 改动文件

- `scripts/tests/test_repair_g1_handoff_containment.py`：新增 F-01 原反例、同族变体、helper 单元向量及两条防误伤基线；所有 handoff CLI 调用均走 `run_formal_script`，READY/freeze 夹具复用 `test_handoff_manifest.py` 的真实上游产物惯例。
- `maintenance/repair-20260815-g1/workorder_pack2_testonly_done.md`：本报告。

生产文件改动：0。  
`scripts/lib/case_paths.py`：仍不存在，符合 test-only 边界。

## 验证实况

### 新测试

命令：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_repair_g1_handoff_containment.py`  
结果：预期红，rc=1；12/14 checks failed。

| 编号 | 状态 | 当前未修复代码实况与红因 |
|---|---|---|
| a1 `--include ../outside.json` | 红 | generate rc=0，输出 READY、18 件产物、4 gates、1 sealed；案外文件被收录，没有 rc=2 或路径拒绝信息。 |
| a2 `data_map.files[].path=../outside.json` | 红 | generate rc=0，输出 READY、18 件产物；data_map 的案外相对路径被静默收录。 |
| a3 手改 `artifacts[].path=../outside.json` 并同步 bytes/SHA | 红 | verify rc=0，输出 PASS、18 件产物哈希一致、状态 READY；V1 重验跟随案外路径并接受匹配哈希。 |
| b1 `--include` 绝对路径 | 红 | generate rc=0，输出 PARTIAL、1 件产物；绝对路径直接进入 manifest。 |
| b2 data_map 穿过案内中间目录 symlink | 红 | generate rc=0，输出 READY、18 件产物；逐段 symlink 未被拒绝。 |
| b3 `sealed/` 条目 symlink 指向案外文件 | 红 | generate rc=0，输出 READY、17 artifacts、2 sealed；测试确认案外文件 SHA 确实出现在 `manifest.sealed`。 |
| b4 freeze `--members` 绝对路径 | 红 | freeze rc=0，输出“初次冻结”；CLI 的绝对路径放行分支真实可达。 |
| b5 `entity_freeze.json.members_source=../...` 后 `--check-unseal` | 红 | check-unseal rc=0，输出“已冻结——允许揭盲/读 sealed”；`resolve_bound_path` 跟随案外绑定。 |
| b6 `a/./b.json` | 红 | generate rc=0，输出 PARTIAL、1 件产物；点段被词法规范化后收录。 |
| b6 `a//b.json` | 红 | generate rc=0，输出 PARTIAL、1 件产物；空段被词法规范化后收录。 |
| b6 空字符串 | 红 | generate rc=0，输出 PARTIAL、0 件产物；显式非法引用被静默跳过，没有硬退。 |
| c1 `case_paths.safe_case_file` 单元向量组 | 红 | `ModuleNotFoundError: No module named 'case_paths'`；测试捕获 import 缺失并继续运行其余 CLI 例。fix 阶段建模块后将继续逐项断言 `../x`、绝对路径、点段、空段、空串、非字符串均抛 `ValueError`，正常相对文件返回案根内 `Path`。 |
| c2 正常相对路径 generate→verify | 绿 | generate rc=0，verify rc=0 且输出 READY；正常正式案未被负测夹具误伤。 |
| c3 `CONTRACT_FILES` 可选件 `unlock_evidence.json` 缺失 | 绿 | PARTIAL generate rc=0，缺失可选件未进入 artifacts；固化 discovery 缺失应跳过的语义。 |

### 既有回归

命令：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_handoff_manifest.py`  
结果：rc=0，68/68 checks 通过。READY、PARTIAL、BLOCKED、verify、freeze、check-unseal、哈希漂移、schema、gate、provenance 重放及 legacy 路径的既有契约均无回归。

## Hunk 映射

| 文件/hunk | invariant | finding | 目的 | test owner |
|---|---|---|---|---|
| `test_repair_g1_handoff_containment.py:23-82` | 测试必须跑真实 formal CLI，并同时断言 rc=2 与路径拒绝 needle | F-01 | 复用 `run_formal_script`、READY/freeze 夹具，统一采集 rc 与输出 | F-01 |
| `test_repair_g1_handoff_containment.py:85-127` | generate/verify 不得收录或重验案外 `../` 文件 | F-01 G2/G3/V1 | 固化 include、data_map、手改 manifest 三个原反例 | F-01 |
| `test_repair_g1_handoff_containment.py:130-169` | 绝对路径及逐段 symlink 不得进入 artifacts/sealed | F-01 G2/G3/G5 | 覆盖 absolute include、中间目录 symlink、sealed symlink，并对 sealed 直接核对案外 SHA | F-01 |
| `test_repair_g1_handoff_containment.py:172-208` | freeze 与 check-unseal 的全部绑定只能指向案根内常规文件 | F-01 F1-F11 / R10-15 | 用完整 READY→freeze 黑盒链证明绝对 members 与 `../` ledger 绑定当前均可放行 | F-01 |
| `test_repair_g1_handoff_containment.py:211-225` | 原始字符串中的 `.`、空段、空串必须在 `Path` 规范化前拒绝 | F-01 G3 / @CX 陷阱1 | 三个独立 CLI 变体防止 `Path.parts` 吞段 | F-01 |
| `test_repair_g1_handoff_containment.py:228-267` | 共享 helper 对非法向量统一抛 `ValueError`，正常相对文件返回案根内文件 | F-01 helper contract | 模块不存在时先红；模块创建后自动展开完整单元向量 | F-01 |
| `test_repair_g1_handoff_containment.py:270-292` | containment 收口不得误伤正常 READY，也不得把可选 discovery 缺失改成硬退 | F-01 双入口语义 | 固化正常全链与 PARTIAL 可选件缺失两条绿色基线 | F-01 |
| `test_repair_g1_handoff_containment.py:295-323` | 任一负向断言失败必须令测试 rc=1，同时全部案例继续执行 | F-01 test-only evidence | 汇总 14 checks，保留逐例机器实况 | F-01 |

未映射测试 hunk：0。

## 库外同族分类矩阵

本阶段只读盘点，不扩写生产文件。

| 同族点 | 本阶段结论 | 后续处置 |
|---|---|---|
| `a5_report_seal.py:32-38 safe_file` | 接受 absolute 输入后再做 resolved containment；与 handoff“显式引用必须相对”不是同一契约。 | 保留豁免候选，交融合方裁决；A5 的 absolute report 调用形态不能在本包顺带改。 |
| `shared_release_receipt.py:65-74 regular` | 有 resolve containment 与叶节点 symlink 检查，但不按原始字符串拒绝 `.`/空段，也不逐段查中间 symlink。 | owner=AI-2/AI-3；本组不碰。 |
| `distribution_explanation_check.py:34-43`、`holder_distribution_scan.py:121-130` | 两份实现逐字节同形；都用 `Path.parts`，会吞 `./` 与重复 `/`，且只查叶节点 symlink。 | 按计划在融合后归并到共享 helper，本包不扩面。 |
| `adversarial_review_runner.py:48-61 contained_regular` | 有 realpath containment，但接受 absolute，且只查叶节点 symlink，不满足 handoff 原串/逐段要求。 | owner=AI-3，由其决定等深加固或正式豁免。 |
| `receipt_validate.py:33-78 _regular_file/_input_file` | 独立 validator 已有 traversal、symlink、strict resolve 与 case-root containment；保留独立实现可维持双链重验。 | 正式豁免共享 helper，避免 producer/consumer 共因失效。 |
| `identity_snapshot_receipt.py` 路径面 | 未证明与 handoff 等深：producer 以 snapshot parent 为自派生 root，validate 以 receipt parent 为 root；有叶节点 symlink/resolve containment与同目录约束，但没有外部 `--case-dir` 契约，也没有原串空段与逐段 symlink 检查。 | 不在本包宣称等深；交融合方明确 owner 或正式豁免，禁止以“已有 `relative_to`”直接销项。 |

## 问题与决策

- a1-a3、b1、b4、b5 六个主反例全部是黑盒 CLI；b2、b3、b6 也保持 CLI 级，没有降级到 helper 单测。
- b4/b5 没有用人工空壳绕过 freeze。测试先由现有 `make_case` 真跑上游脚本生成 READY 契约件，再用 `setup_freezeable` 生成合法裁决/溯源夹具；b5 先完成一次合法相对路径 freeze，之后只变异 `members_source` 与匹配 SHA，因此 rc=0 明确归因于案外绑定放行。
- b3 接受未来实现的两种合法策略：显式硬退，或 discovery 跳过 symlink；若 generate 成功，则直接断言案外文件 SHA 不得进入 sealed 清单，避免只按 path 文本作弱断言。
- b6 为点段和重复斜杠实际创建同一规范化目标文件，使当前 rc=0 确实证明词法折叠吞段；空串单独证明显式非法引用不能借“文件不存在即跳过”静默放行。
- c1 在模块不存在时只把该组记红，不让 import 异常中止 a/b/c 其他案例；fix 阶段模块出现后，同一测试自动执行六个非法向量和一个正常向量。
- 未把新测试登记进 `run_all.py`：本包要求先红，且用户指定的既有回归是 `test_handoff_manifest.py`。测试注册留到 fix/融合阶段，避免全量 suite 在 test-only 快照中被预期红永久阻断。
- 本阶段未修改 `handoff_manifest.py`、`a4_gate.py`、`audit_release_gate.py` 或 `scripts/lib/` 下任何现有文件。
