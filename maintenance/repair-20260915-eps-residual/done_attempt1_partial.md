# 7.0.3 → 7.0.4 施工交接

**状态：PARTIAL，未达到 §4 完工标准；不 commit。**

## 1. 改动清单

- 基线 HEAD：`2000b6e78f790ee0ed348cc2ecb8eae796d5136e`；`3b29e38` 为其祖先。初始工作区干净；工单所列行号与锚文本核对一致。
- 初始在 `.staging_eps/` 执行 `shasum -a 256 -c STAGING_SHA256.txt`：exit 0，33/33 OK；APU 诊断后复检仍 33/33 OK。
- 唯一生产逻辑变化为 A1 的缺口分类：新增 GAP_EPS_REL/gap_eps，将 EPS 以上、gap_eps 以下或等于阈值的短缺记 fp_residual，数量保留；其他改动为文档、登记和测试。
- VERSION、pyproject.toml、SKILL.md 同步 7.0.4；补 7.0.3 与 7.0.4 CHANGELOG 详细段及 schema 文档登记。
- 账户类、既有测试文本、禁改文件保持；`invariant_manifest.json`、PYTHIA fixture、run_all.py 未改，SUITE 未新增入口。见 scope_checks.json。
- 全程使用本仓库暂存输入、离线工具和本地 Git 对象；未访问原案目录、未 fetch、未 commit。

| 文件 | 新增行 | 删除行 |
|---|---:|---:|
| `CHANGELOG.md` | 19 | 0 |
| `SKILL.md` | 1 | 1 |
| `VERSION` | 1 | 1 |
| `maintenance/repair-20260915-eps-residual/apu_diff.json` | 12560 | 0 |
| `maintenance/repair-20260915-eps-residual/apu_formal_attempt1_trace_704.log` | 3 | 0 |
| `maintenance/repair-20260915-eps-residual/apu_formal_attempt1_trace_704_run.json` | 6 | 0 |
| `maintenance/repair-20260915-eps-residual/apu_regression.md` | 240 | 0 |
| `maintenance/repair-20260915-eps-residual/apu_trace_704_diagnostic.log` | 334 | 0 |
| `maintenance/repair-20260915-eps-residual/apu_trace_704_diagnostic_run.json` | 6 | 0 |
| `maintenance/repair-20260915-eps-residual/capture_red.py` | 46 | 0 |
| `maintenance/repair-20260915-eps-residual/changelog_lint.log` | 1 | 0 |
| `maintenance/repair-20260915-eps-residual/check_results.json` | 27 | 0 |
| `maintenance/repair-20260915-eps-residual/compare_apu.py` | 104 | 0 |
| `maintenance/repair-20260915-eps-residual/docs_lint.log` | 1 | 0 |
| `maintenance/repair-20260915-eps-residual/done.md` | 99 | 0 |
| `maintenance/repair-20260915-eps-residual/final_scope_checks.json` | 18 | 0 |
| `maintenance/repair-20260915-eps-residual/fixtures_lint.log` | 1 | 0 |
| `maintenance/repair-20260915-eps-residual/invariant_scan.log` | 1 | 0 |
| `maintenance/repair-20260915-eps-residual/pythia_extra_input_checks.json` | 16 | 0 |
| `maintenance/repair-20260915-eps-residual/pythia_input_probe.json` | 104 | 0 |
| `maintenance/repair-20260915-eps-residual/pythia_regression.md` | 34 | 0 |
| `maintenance/repair-20260915-eps-residual/red_evidence.txt` | 588 | 0 |
| `maintenance/repair-20260915-eps-residual/red_setup_attempt.txt` | 557 | 0 |
| `maintenance/repair-20260915-eps-residual/run_all_eps.exit` | 1 | 0 |
| `maintenance/repair-20260915-eps-residual/run_all_eps.log` | 199 | 0 |
| `maintenance/repair-20260915-eps-residual/run_all_result.json` | 14 | 0 |
| `maintenance/repair-20260915-eps-residual/run_apu.py` | 28 | 0 |
| `maintenance/repair-20260915-eps-residual/run_checks.py` | 23 | 0 |
| `maintenance/repair-20260915-eps-residual/scope_checks.json` | 62 | 0 |
| `maintenance/repair-20260915-eps-residual/staging_recheck.log` | 33 | 0 |
| `maintenance/repair-20260915-eps-residual/t7_ruling.md` | 25 | 0 |
| `maintenance/repair-20260915-eps-residual/test_entity_source_trace.log` | 107 | 0 |
| `maintenance/repair-20260915-eps-residual/test_version_consistency.log` | 1 | 0 |
| `maintenance/repair-20260915-eps-residual/write_done.py` | 72 | 0 |
| `pyproject.toml` | 1 | 1 |
| `references/scan-schemas.md` | 9 | 3 |
| `scripts/report/entity_source_trace.py` | 30 | 10 |
| `scripts/tests/test_entity_source_trace.py` | 184 | 0 |

## 2. 与工单差异

- T6：按原 params 还原的正式运行 exit 2，缺少裁决收据引用的 `data/stage2/flip_evidence.md`（4752 字节；SHA-256 `d79fd8ce0b6405b72ef7473e168b6401add7387f9c2c20c81b3a74ffd347f677`）。保留原始拒收日志与命令；已请求补入，尚未收到。另跑仅省略 --acknowledge-flip 的诊断，以计算数量差分；诊断不替代 T6 正式通过。
- T7：初次暂存只有 DuckDB；后补 2 个成员文件经补充清单 2/2 校验 OK，但平铺文件将 Q1/3yMk 合在 48 人实体内，不能直接替代历史两个锚点。run_params 仅记录 edge_budget，仍缺原标签、W1 名单和匹配历史锚点的实体范围说明。只读 ATTACH 验证 4,857,654 条边及四表结构，不能精确还原历史运行，未运行替代参数凑数；已请求补齐。fixture 各项旧值/新值：均未改，无新实测值可登记。
- `/tmp/trace_703.py` 已按工单用 git show 导出且内容未改。旧生产脚本运行时会按 __file__ 查找相邻 wave_scan.py 与 ../solana，因此测试将同一字节内容复制到临时 scripts/report/trace_703.py，并链接当前未改动依赖目录，设置 PYTHONPATH；未 patch 旧算法。
- 初次新增断言的旧脚本布局缺 lib 依赖，失败原文保存在 red_setup_attempt.txt；修复测试布局后，在生产代码未改动时重新捕获 red_evidence.txt。前者不计有效 RED。
- T8 在 test_entity_source_trace.py 内复用完整 READY 案根搭建和 subprocess harness，未启用独立文件/SUITE +1 备选。

## 3. RED → GREEN

- RED 生产 SHA-256：`ff4b640a1adbcecf8f3651efbda04493d3085754f939da1ef23b8d9f2efe0fc3`。T1 正式 CLI exit 0：data_gap_events=1，两锚点 data_gap raw="1"；T2① exit 0：data_gap raw="100"。三策略 policy_details、构成、closure_check 与命令/退出码/哈希/输出原文均保存在 red_evidence.txt。
- 新断言对未改动 7.0.3：exit 1，12 项预期失败；修改 A1 后完整 test_entity_source_trace.py：exit 0，105 个 check 通过、0 失败。T1/T2/T3/T4/T5 与原有全部断言通过。
- T8：新 trace → freeze exit 0；旧代码账本放回同一案根 → freeze exit 2，stderr 含“算法哈希已变化”。
- APU 诊断：105 实体、210 锚点，T4 失败 0；data_gap 条目 105 → 0，fp_residual 条目 105；非 gap/residual 的策略 raw 变化 0，指纹变化 118/210。旧裁决收据指纹不匹配 8/10，补齐 evidence 文件后仍需处理失配；本次未代改收据。详见 apu_regression.md / apu_diff.json。
- PYTHIA：未取得新 trace 账本；T7 未验证，见 pythia_regression.md。

## 4. 命令与结果

| 命令 | 实际结果 | 证据 |
|---|---|---|
| `python3 scripts/tests/changelog_lint.py` | exit 0 | changelog_lint.log |
| `python3 scripts/tests/docs_lint.py --all` | exit 0 | docs_lint.log |
| `python3 scripts/tests/test_version_consistency.py` | exit 0 | test_version_consistency.log |
| `python3 scripts/tests/invariant_scan.py` | exit 0 | invariant_scan.log |
| `python3 scripts/tests/fixtures_lint.py` | exit 0 | fixtures_lint.log |
| `python3 scripts/tests/test_entity_source_trace.py > /tmp/eps_trace_green.log 2>&1` | exit 0；105 check PASS | test_entity_source_trace.log |
| `nohup python3 scripts/tests/run_all.py > /tmp/run_all_eps.log 2>&1 &`，shell wait 记录退出码 | exit 1；汇总 PASS 145，FAIL 2 | run_all_eps.log / run_all_eps.exit |
| `git diff --check` | exit 0 | 工具实际执行 |
| 受保护代码与既有测试逐字比较 | PASS | scope_checks.json |

run_all 启动时 zsh 输出 `nice(5) failed: operation not permitted`；实际任务启动并等待退出，未用管道 tail，也未修改 suite。

全套失败项原文摘要：

- FAIL(rc=1)  test_batch3_solana_vertical_slice.py (无输出)
- FAIL(rc=1)  test_batch3_evm_vertical_slice.py (无输出)

两项均在 ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler) 的 socket.bind 处报 PermissionError: [Errno 1] Operation not permitted：Solana 测试第 625 行、EVM 测试第 281 行。当前执行环境禁止本地监听；没有改测试断言或尝试绕过限制。需要在允许本地监听的环境重新完成全套验证，当前结果保持 145/147、exit 1。

## 5. 已知未修与交接条件

- float64 根因未移除，极端累加序列仍可能超过 gap_eps 而被记 data_gap；int(float) 截断为 raw="0" 的既有现象未修。
- fp_residual 仍属 UNRESOLVED，数量保留并计入未决总量；账户 EPS 与闭合门禁未放大。
- 算法文件哈希变化后，旧账本 freeze 重放和 --check-unseal 会拒；“已封存不动”仅指本次不重写原案文件。
- 后续须补齐 APU 收据引用材料、PYTHIA 原始参数与辅助输入，完成 T6/T7；另需在允许 localhost bind 的环境复跑 run_all.py；本次两项 socket 权限失败未消除。未达到全绿前不得标记完工或代为 commit。
