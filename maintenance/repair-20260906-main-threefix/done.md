# main 三缺陷独立修复施工记录

日期：2026-09-06  
工作基线：`main @ 8396aa48e6da318433571002e246f1c3ab78794b`  
版本：`7.0.1 → 7.0.2`  
状态：**A→C→B 修复、定向回归及四项门禁已完成；全套 rc=1、145/147 PASS，两项 localhost bind 被当前沙箱拒绝，未达到 147/147 完工验收标准。未 commit。**

## 1. 开工门与先红证据

- 开工 `git status --short` 为空；分支 main、HEAD 与用户指定一致；`git merge-base --is-ancestor f27d3d2 HEAD` 返回 0。
- 工单全文已读；施工前集中核对工单指定行号与锚文本，全部一致，没有触发锚点不符停工条件。没有读取 `/Users/uravvv/.codex` 下文件；未联网、未 fetch、未读取密钥文件。
- A 先运行新增守卫，rc=1，准确报出当前 `sqd_gap_repair.py` 哈希 `25f04ff1…` 的四个协议漏登记。工作树与 `git show 4c5cd578a5f1a10449d128dcdb91a724c359e7a5:scripts/solana/sqd_gap_repair.py` 哈希均为 `25f04ff10bc494be977e4c5b3193c3a928c0764fa529d8d5a47563fe2a825e66`。
- C 在原测试夹具的独立副本上复现 finalize rc=0、写出 seal，随后 build_html analysis-audit rc=1 且报“封口路径重复: v_ok.json”。新增回归在修复前 rc=1、6 项失败；修复后全部通过。
- B 在改生产代码前复现 sol-rows 夹具：非豁免桶合计 100，`validate_series_payload(..., series_format="sol-rows")` 无错误；但图一直出 rc=0、实绘含「锁仓/销毁」、豁免列表为空。追加端到端回归同样先失败于实绘集合断言。
- 命令、退出码、输出原文、测试/复现脚本和生产文件 SHA-256 均保存在 `red_evidence.txt`。`reproduce_c_red.py` 使用改动前 `test_a4_gate.py:426` 的夹具截点，只用于基线 RED 重演；不应对改后行号直接重跑。

## 2. 三段生产修复

- A：`producer_history.py` 只追加指定 commit、指定哈希对应的四条 ACTIVE 登记。新守卫动态覆盖每个脚本全部已出现的协议；历史豁免只限 anchor-plan/v2 对；全表逐条校验本地 git 对象，按 `(commit, script)` 缓存，不 mock 登记表。`run_all.py` 仅追加 SUITE 一项，146→147；REVOKED 规则不变。
- C：`cmd_finalize` 将三来源合并后的 `seal_files` 与 `{CLAIMS_NAME, verdict_rel} - {None}` 求交集，重复走既有失败出口 rc=2；不做路径归一化重构、不改构建端或分布消费方。
- B：四文件按工单接入同一 `series_format` 取值函数与 `stack_exempt_for` 派生豁免；只在 None 时保留历史规则。sol-rows 真烧毁轨不堆叠、图一标注净供应；EVM 堆叠规则保持，未增加 sol-anchor-rows 特判，CAMP_ORDER 与历史常量不变。
- 九处文档已同步 Solana 分支；没有改变总供应判级总原则。三个 manifest 均未改，invariant_scan 实际通过，未触发额外登记许可。

## 3. 回归覆盖与裁决调整

- C：四种独立副本反例分别覆盖 `--seal-files` / claim files 与 verdict / claims 两专用路径交叉，均 rc=2、stderr 点名重复路径且无 seal；已有 seal 再遇重复时，全案文件集合与字节不变。既有 check 保留。
- B：sol-rows 与 evm-dict 的同输入端到端直出、非空 PNG、实绘与豁免收据匹配；纯函数覆盖空串、非法字符串、非字符串、非对象 sidecar、缺 provenance 和历史回退副本；A5 与发布闸正常消费无错误，①实绘加回烧毁桶、②漏豁免项、③overlay 引用豁免桶三种篡改均被两个消费方拒绝。
- `test_repair_batch1.py` 未改且实际通过，包括既有 `selector.call_count == 2` 断言。

### 与工单差异

用户在施工中明确裁决收窄 B2 用例 5 的④：不在 A5 `_fig1_expected_from_state` 或发布闸 `check_figure1_legend_receipt` 新增任何数值校验。两个消费方只承担①②③键集合/overlay 篡改的双拒断言；sol-rows 的「锁仓/销毁」含 NaN、inf、非数值时，由 `figures_from_facts.py fig1` 原有豁免键校验非零退出并报“非有限数值”，三种输入均实测通过。理由：消费方只重算键集合；非有限值由画图层把关；state 篡改另有收据的 state 哈希绑定兜底。

`b_attempt1.log` 是裁决前仍按原 B2④要求执行的中间失败记录，保留原文，不作为最终验收结果；最终结果为 `b_green.log`。除此之外，没有扩大生产修复范围或降低既有断言。

## 4. GREEN 与门禁记录

| 命令 | 实际结果 / 日志 |
|---|---|
| `python3 scripts/tests/test_producer_registry_current.py` | rc=0，当前四脚本全部协议登记及全表 git 哈希通过；`a_green.log` |
| `python3 scripts/tests/test_a4_gate.py` | rc=0，新增及既有全部通过；`c_green.log` |
| `python3 scripts/tests/test_figures_from_facts.py` | rc=0，含用户裁决后的 B2 用例；`b_green.log` |
| `python3 scripts/tests/test_repair_batch1.py` | rc=0，既有 F-01/A5v3 等回归通过；`b_existing.log` |
| `python3 scripts/tests/changelog_lint.py` | 写前及写后均 rc=0；写后活跃 69 条＋归档 139 条 |
| `python3 scripts/tests/docs_lint.py --all` | rc=0，59 个文档通过 |
| `python3 scripts/tests/test_version_consistency.py` | rc=0，五处一致 7.0.2 |
| `python3 scripts/tests/invariant_scan.py` | rc=0；producer=75、consumer=112、transport=65、atomic=56、formal=61、exceptions=0 |
| `nohup python3 scripts/tests/run_all.py > /tmp/run_all.log 2>&1 &` | **rc=1；145/147 PASS**。两项 localhost bind 权限失败；完整原文 `run_all.log`，机器汇总 `run_all_result.json` |

运行时设置 `PYTHONDONTWRITEBYTECODE=1`、`MPLCONFIGDIR=/private/tmp/threefix-mpl`；全套另设 `PYTHONUNBUFFERED=1` 便于读取失败原文。全套通过 shell `wait` 获取 Python 正式退出码，落 `/tmp/threefix_run_all.exit`，不使用 `| tail`。启动时 zsh 报 `nice(5) failed: operation not permitted`，Python 已继续执行并产出测试日志。

全套失败明细（没有跳过、没有降断言，也没有重跑整套凑绿）：

1. `test_batch3_solana_vertical_slice.py`：`:625` 创建 `ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)`，最终 `socket.bind` 报 `PermissionError: [Errno 1] Operation not permitted`。
2. `test_batch3_evm_vertical_slice.py`：`:281` 同一 localhost fixture bind 报相同错误。

这两项尚未在允许 localhost bind 的环境完成，故交付为实现完成、全套验收未通过。当前会话不能申请扩大权限；没有改测试或绕过沙箱。其余 145 项通过，包括新增生产者登记守卫、A4、图一、既有 F-01 与禁改的 batch D。全套日志 SHA-256：`a565dc88babcdf76919397f308b751381bc4ae821320f7fe894abf7212b02504`。

## 5. 版本、交付与白名单

- 版本五处为 7.0.2；CHANGELOG 新增索引及六栏详情，出处只写“MELANIA/ARC 案触发的工具故障”，没有代币分析结论。
- 实施文件共 18 个：生产文件 6、测试文件 4（含新守卫和 run_all）、reference 文档 4、版本/发布文件 4；另有本工单目录内证据、日志与交付文件 18 个，实际改动总计 36 个文件。白名单外零改动。
- `scope_verification.json` 留存 18 个实施文件 SHA-256、SUITE=147、保护文件逐字节未改证据；SKILL.md 相对基线仅原第 23/27 行改变。HEAD 未变，未 commit。
- 遗留：`test_sqd_gap_repair.py:314-325` 与 `test_batch18_review_digest.py:97-105` 的 monkeypatch 不动；`test_a4_gate.py` 末尾“23 项”历史计数不动；evm-dict ylabel 不动。
- 已完成本环境全部授权施工与一次完整测试；因上述明确环境失败，147/147 验收仍未满足。到此停工交付，未 commit。

## P2 消化(第 1 轮盲审后)

日期：2026-09-06。三条 P2 已全部消化，以下八项指定检查均 rc=0，本轮完工，未 commit。仅修改本轮白名单文件，生产代码未改；离线执行，未读取 `/Users/uravvv/.codex` 下文件，未运行 `run_all.py`。

1. **P2-1 绘图层断言**：`test_figures_from_facts.py` 保留两种格式的 CLI 真实 PNG 正例，另直接调用 `plot_camp_evolution` 并显式传入 `series_format`、`note_supply`。临时捕获实际 `Axes.stackplot` 的阵营标签和数值序列及 `set_ylabel` 文案：sol-rows 仅堆叠大庄/散户且标注“占净供应量”，evm-dict 包含锁仓/销毁且标注“占总供应量”；调用原始 matplotlib 方法并在结束后恢复。GREEN：`python3 scripts/tests/test_figures_from_facts.py`，rc=0。
2. **P2-2 C 段夹具单一化**：两个 claim-files 副本按 claim ID 同步 `claim_registry.json` 的 `evidence_files`，保留 exit 2、stderr 点名重复路径、无 seal 三项断言。改动前已用 `reproduce_p2_c_red.py` 截取原夹具，内存执行 HEAD 8396aa4 的补硬拒前生产代码：两种路径未同步均 rc=2、报“claim C1 证据文件集合不一致”且无 seal；同步后均 rc=0 且写出 seal，证明修订夹具除重复路径外合法。准确命令、输出原文及哈希已追加 `red_evidence.txt`，复现脚本 rc=0。GREEN：`python3 scripts/tests/test_a4_gate.py`，rc=0。
3. **P2-3 裁决入档**：工单末尾追加 B2④ 收窄裁决、理由、裁决人 Fable 与日期；CHANGELOG 7.0.2 按本轮验收信息更新盲审与验收栏，保留测试栏末尾的完整门禁记录指向；SKILL.md 第 27 行仅移动句号，其他字不变。GREEN：`python3 scripts/tests/changelog_lint.py`、`python3 scripts/tests/docs_lint.py --all`、`python3 scripts/tests/test_version_consistency.py`、`python3 scripts/tests/invariant_scan.py`，各 rc=0。

验收信息来源为本轮用户转交的验收方核实结果：codex 第 1 轮只读盲审 PASS（0 P0/P1，3 P2）；验收方本机全套 `run_all` 147/147、RC=0。本记录前文的施工沙箱 145/147 为此前实际结果，保留不改；本轮没有重跑全套。

| GREEN 命令 | 退出码 | 日志 |
|---|---|---|
| `python3 scripts/tests/test_figures_from_facts.py` | rc=0 | `p2_test_figures_from_facts.py.log` |
| `python3 scripts/tests/test_a4_gate.py` | rc=0 | `p2_test_a4_gate.py.log` |
| `python3 scripts/tests/test_repair_batch1.py` | rc=0 | `p2_test_repair_batch1.py.log` |
| `python3 scripts/tests/test_producer_registry_current.py` | rc=0 | `p2_test_producer_registry_current.py.log` |
| `python3 scripts/tests/changelog_lint.py` | rc=0 | `p2_changelog_lint.py.log` |
| `python3 scripts/tests/docs_lint.py --all` | rc=0 | `p2_docs_lint.py.log` |
| `python3 scripts/tests/test_version_consistency.py` | rc=0 | `p2_test_version_consistency.py.log` |
| `python3 scripts/tests/invariant_scan.py` | rc=0 | `p2_invariant_scan.py.log` |

运行环境：`PYTHONDONTWRITEBYTECODE=1`、`MPLCONFIGDIR=/private/tmp/p2-mpl`。机器结果见 `p2_green_results.json`。
