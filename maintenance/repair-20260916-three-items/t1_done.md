# 施工 T1: 停工

施工基线：分支 fix/three-items-20260916，HEAD 14f249631895cc79954486174ddce5569cc63387。开工工作树干净。按 v3.1 工单核锚后依次完成 A → B → C；A/B/C 分段 GREEN，但 run_all 145/149 PASS、4 项失败，exit 1；未满足全套通过标准，停在最终验收。

## 改动文件

本次修改：
- scripts/report/adjudication_validator.py：两类模板成员清单移到旁车；安全路径校验、旁车先写、失败保留旧台账；同步帮助。
- scripts/report/handoff_manifest.py：精确排除规则、显式登记冲突 exit 2、freeze 卫生 WARN。
- scripts/tests/test_handoff_manifest.py：新增 B4 契约并登记 main，既有断言逐字未改。
- references/split-run.md、references/scan-schemas.md：工单指定条文替换。
- maintenance/repair-20260916-three-items/t1_anchor_check.txt、t1_red_evidence.txt：追加核锚与 RED。
- maintenance/repair-20260916-three-items/t1_green_evidence.txt、t1_scope_check.txt、t1_run_all.pid、t1_run_all.exit、t1_run_all.log、t1_done.md、t1_done_attempt2_stopped.md：本次验收证据与报告。

沿用 HEAD 中 attempt1 改动，未再修改：
- scripts/tests/test_adjudication_validator.py
- scripts/tests/test_distribution_gate.py

## RED → GREEN

准确命令、退出码、输出原文和 SHA256 见 t1_red_evidence.txt / t1_green_evidence.txt；RED 保留 attempt1 原文件全部字节作为前缀。

A RED 引用 attempt1：
1. 独立 test_members_sidecar_contract，exit 1：缺旁车、非法路径未拒、两个模板各自新台账/force 旧台账四案 FAIL。
2. 独立 make_reports → fill_all，exit 1：FileNotFoundError；未将之后未运行的用例计为通过。
3. python3 scripts/tests/test_distribution_gate.py，exit 1：旁车缺失。
A GREEN：python3 scripts/tests/test_adjudication_validator.py && python3 scripts/tests/test_distribution_gate.py，exit 0；两份测试全部通过，包含旧台账 _members_total 兼容与旁车成员集合完全一致。

B RED：
python3 -c 'import sys; sys.path.insert(0, "scripts/tests"); import test_handoff_manifest as t; t.test_history_exclusion_and_hygiene(); sys.exit(bool(t.FAILS))'
exit 1；data_map/--include/--gate 三案均旧实现 exit 0；freeze exit 0 但无 WARN；两个缺失函数 ImportError 在用例内捕获并记 FAIL。
B GREEN：python3 scripts/tests/test_handoff_manifest.py，exit 0。
结果原文：handoff_manifest 契约测试全部通过（109 项）。

C RED：wc -c references/split-run.md references/scan-schemas.md，exit 0，改前字节已在修改前落证据。按工单此 RED 是改前字节基线，不是故意失败的 docs_lint。
C GREEN：wc -c + Python 字节上限断言 + python3 scripts/tests/docs_lint.py --all，exit 0。
结果原文：PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）。

| 文件 | 改前 wc -c | 改后 wc -c | 差值 |
| --- | ---: | ---: | ---: |
| references/split-run.md | 28162 | 28135 | -27 |
| references/scan-schemas.md | 104942 | 104941 | -1 |

## run_all

命令：nohup python3 scripts/tests/run_all.py > /tmp/run_all_t1.log 2>&1 &
同一 shell 用 wait 等待，并保存原始退出码。未使用管道 tail；等待结束后才读取日志。
启动 shell 原文：zsh:1: nice(5) failed: operation not permitted。
最终 exit 1，149 项中 145 PASS、4 FAIL；run_all.py 未改，分母不变。日志完整副本：t1_run_all.log（与 /tmp/run_all_t1.log 字节一致）。
日志 SHA256：41d1a5b70b6a8e49aba8cc64994c1103a182c3a7d88504ce63eca433cc610781。

结果行原文：
```text
FAIL(rc=1)  test_batch3_solana_vertical_slice.py (无输出)
FAIL(rc=1)  test_batch3_evm_vertical_slice.py (无输出)
FAIL(rc=1)  test_sqd_gap_repair.py   GREEN E27-c-cas mechanism assert_resume_cas
FAIL(rc=1)  test_batch8_repair_scale.py (无输出)
4 项失败——修完再收工
```

- 前两项在 ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler) 的 socket.bind 报 PermissionError: [Errno 1] Operation not permitted，属于工单预告的沙箱端口限制。
- 后两项报 FileNotFoundError，缺少 .staging_b3/routeA_pilot/426649168.json.gz。已核实文件不存在且 git ls-files 对该路径无输出。引用点为 test_sqd_gap_repair.py:221、422–423；test_batch8_repair_scale.py:328 调用前者。不能把这两项归为端口失败。
- 三份本工单测试在 run_all 中全部 PASS：handoff 109 项、adjudication 0 项失败、distribution gate contract PASS。
- 缺失夹具路径及这两份失败测试均不在施工白名单，未补造夹具、未改测试、未跳过失败。

## 范围与差异

- A 的三个 validate 函数、B 的 cmd_verify/_reverse_bound_reason/check_bound_file/git_sha 逐字未变。
- cmd_freeze 去掉指定 WARN 插入段后，与 HEAD 逐字一致；四道前置未改。
- B 原测试移除新增函数与 main 调用后与 HEAD 逐字一致；A 两份测试与 HEAD 字节一致。
- split-run 产物表 90/91 行未动；版本文件、CHANGELOG、pyproject 未改。
- attempt1 测试符合工单，无修正、无回滚；既有 git_sha 按用户澄清原样运行。
- 功能实现无工单差异。未自行加入生产扫描、测试隔离或绕过逻辑。
- 本人未读取禁用目录作参考，无网络调用，无 Git 写操作、无 commit；未重写存量案卷台账。
- 最终 HEAD 与开工一致，git diff --check PASS，工作树改动均在白名单；全套日志与退出码已保存。
- 与工单预期的验收差异：除两项已预告端口限制外，多出两项缺夹具失败，因此不宣称施工完成或全套通过。

## 遗留与恢复条件

1. Fable 在具备 localhost bind 权限的本机环境复跑端口相关测试及 run_all。
2. 由有授权的一方恢复独立克隆所需的真实 .staging_b3/routeA_pilot/426649168.json.gz 夹具；当前白名单不授权施工者新增该文件，且不得从禁读目录取材或在线补抓。
3. 恢复夹具后再跑全套并取得实际结果；当前所有施工进度、RED/GREEN 与日志保留，无 commit。
