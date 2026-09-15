"""汇总实际回执与调度方全套日志；仅证据齐备时输出终态。"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
apu = json.loads((OUT/'apu_diff.json').read_text())
formal = json.loads((OUT/'apu_formal_followup_result.json').read_text())
pythia = json.loads((OUT/'pythia_diff.json').read_text())
external = json.loads((OUT/'run_all_fable_result.json').read_text())
external_complete = external.get('status') == 'PROVIDED_PASS'
checks = json.loads((OUT/'check_results.json').read_text())
followup = json.loads((OUT/'followup_checks.json').read_text())
assert formal['exit_code'] == 2 and apu['receipt_fingerprint_mismatches'] == 8
assert not apu['t4_failures'] and not apu['policy_failures']
assert pythia['exit_codes_equal'] and pythia['blocking_reasons_equal'] and not pythia['t4_failures']
assert all(r['exit_code'] == 0 for r in checks + followup)
if external_complete:
    assert external['passed'] == external['total'] == 147 and external['failed'] == 0
    assert external['log_sha256'] == hashlib.sha256((OUT/'run_all_fable.log').read_bytes()).hexdigest()
else:
    assert external['status'] == 'NOT_PROVIDED' and not (OUT/'run_all_fable.log').exists()
numstat = subprocess.run(['git','diff','--numstat'],cwd=ROOT,capture_output=True,text=True,check=True).stdout
changes = [(name,adds,dels) for adds,dels,name in (l.split('\t') for l in numstat.splitlines())]
untracked = subprocess.run(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.splitlines()
for name in untracked:
    if name.startswith('maintenance/repair-20260915-eps-residual/') and name != str((OUT/'done.md').relative_to(ROOT)):
        changes.append((name,str(len((ROOT/name).read_text().splitlines())),'0'))
changes.append((str((OUT/'done.md').relative_to(ROOT)),'SELF_LINES','0'))
lines = ['# 7.0.3 → 7.0.4 施工交接', '',
    '**状态：按补充裁决完成；未 commit。**' if external_complete else '**本轮施工终态：T6/T7 按补充裁决完成；调度方全套日志尚未落盘，全套证据待交付；未 commit。**', '',
    'T6 数量不变量通过，原参数正式跑因旧收据指纹失配 exit 2；T7 同输入双版本对照完成。全套结果由调度方沙箱外提供，指定文件为 run_all_fable.log；当前到位状态见第 4 节。本机沙箱的 145/147 结果保留，不记为本机全绿。', '',
    '## 1. 改动清单', '',
    '- 基线 HEAD：`2000b6e78f790ee0ed348cc2ecb8eae796d5136e`；`3b29e38` 为其祖先。初始工作区干净，工单行号与锚文本全部一致，无锚点不符停工事件。',
    '- 生产逻辑仅改 A1：新增 GAP_EPS_REL/gap_eps；EPS 以上、gap_eps 以下或等于阈值的短缺记 UNRESOLVED/fp_residual，数量保留。账户 EPS、账户类及闭合门禁保持原样。',
    '- VERSION、pyproject.toml、SKILL.md 同步 7.0.4；补 7.0.3/7.0.4 CHANGELOG、schema 登记和回归断言。',
    '- 既有测试、handoff_manifest.py、test_sqd_gap_repair.py、test_handoff_manifest.py、invariant_manifest.json、PYTHIA fixture、run_all.py 保持；SUITE 仍 147 项。见 scope_checks.json 与 final_scope_checks.json。',
    '- 原输入清单 33/33、APU 补件 1/1、PYTHIA 补件 2/2 已校验并复检；没有改收据或原案输入。新增输出仅存隔离暂存目录。',
    '- 全程离线，未访问 /Users/uravvv/Documents、未 fetch、未 commit；暂存目录已被忽略。', '',
    '| 文件 | 新增行 | 删除行 |', '|---|---:|---:|']
lines += [f'| `{n}` | {a} | {d} |' for n,a,d in sorted(changes)]
lines += ['', '## 2. 与工单差异', '',
    '- 以调度方补充裁决覆盖初次卡点；初次 PARTIAL 交接保存在 done_attempt1_partial.md，仅作历史记录。',
    '- T6：补件后原参数（含 --acknowledge-flip）正式重跑一次。验收改为“已完成的诊断 T4 数量证据 + 正式 fail-closed 记录”；旧收据 8/10 失配属设计内行为，不修改收据或参数凑通过。',
    '- T7：按 t7_ruling.md 改为 7.0.3/7.0.4 同输入双跑；使用 entity_file_flat.json 的 7 实体 102 址，不与历史 fixture 锚点作相等断言，不要求旧 W1/标签快照，不改 fixture。',
    '- run_all：本机两项 socket.bind PermissionError 属环境限制。按裁决不再重跑；全套结果由调度方沙箱外提供，引用 run_all_fable.log，归属不混写。',
    '- 旧算法由 git show HEAD:scripts/report/entity_source_trace.py 导出；为满足 __file__ 相邻依赖，逐字复制到临时 scripts/report/trace_703.py，链接未改动依赖，设置 PYTHONPATH；未改旧算法。',
    '- 初次 RED 布局缺 lib 的失败保存在 red_setup_attempt.txt，不计有效 RED。修复布局后于生产代码未修改时重新取证，见 red_evidence.txt。',
    '- T8 在既有 test_entity_source_trace.py 复用完整 READY 案根与 subprocess harness，未用新增测试文件/SUITE +1 备选。', '',
    '## 3. RED → GREEN', '',
    '- RED 算法 SHA-256：`ff4b640a1adbcecf8f3651efbda04493d3085754f939da1ef23b8d9f2efe0fc3`。T1 旧版 CLI exit 0、data_gap_events=1、两锚点 raw="1"；T2① 旧版 raw="100"。三策略明细、闭合、命令、退出码和原文见 red_evidence.txt。',
    '- 新断言运行于未改动 7.0.3：exit 1，12 项预期失败；A1 修复后 test_entity_source_trace.py：exit 0，105 check PASS、0 失败，含原有全部断言与 T1–T5。',
    '- T8：新 trace → freeze exit 0；同一案根换回旧算法账本 → freeze exit 2，stderr 含“算法哈希已变化”。',
    f'- T6：{apu["entities"]} 实体、{apu["anchors"]} 锚点，T4 和三策略数量失败均为 0；data_gap 条目 {apu["old_gap_entries"]} → {apu["new_gap_entries"]}，fp_residual {apu["residual_entries"]}；非 gap/residual 的策略 raw 变化为 0；指纹变化 {apu["fingerprints_changed"]}/210。TE-02/TE-04 尘埃字段保持。',
    f'- T6 原参数正式跑：exit {formal["exit_code"]}，旧收据 8/10 指纹不匹配；完整 stderr 与拒收原文见 apu_regression.md。118 个变化指纹全部对应旧 data_gap 明细，由调度方核实；CHANGELOG 已写明须重新裁决。']
if all(pythia['ledger_exists']):
    lines.append(f'- T7：两版 exit {pythia["exit_codes"][0]}，阻断原因文本相同；均落账本，{pythia["entities"]} 实体、{len(pythia["rows"])} 锚点，T4 数量失败 0。逐终点 raw、逐实体 gap/residual 事件见 pythia_diff.json / pythia_regression.md。')
else:
    lines += [f'- T7：两版 exit {pythia["exit_codes"][0]} 且均未落账本；阻断原因文本相同，按裁决第 5 条记录行为一致。',
              '- **T7 数量不变量未能在 PYTHIA 上取证，由 T6 APU 全量 105 实体承担。**']
lines += ['', '## 4. 命令与结果', '', '| 命令 | 实际结果 | 证据 |', '|---|---|---|',
    '| `python3 scripts/tests/changelog_lint.py` | exit 0；补充消费面说明后复检 exit 0 | changelog_lint.log / changelog_lint_followup.log |',
    '| `python3 scripts/tests/docs_lint.py --all` | exit 0；补充文档后复检 exit 0 | docs_lint.log / docs_lint_followup.log |',
    '| `python3 scripts/tests/test_version_consistency.py` | exit 0 | test_version_consistency.log |',
    '| `python3 scripts/tests/invariant_scan.py` | exit 0 | invariant_scan.log |',
    '| `python3 scripts/tests/fixtures_lint.py` | exit 0；裁决后复检 exit 0 | fixtures_lint.log / fixtures_lint_followup.log |',
    '| `python3 scripts/tests/test_entity_source_trace.py` | exit 0；105 check PASS | test_entity_source_trace.log |',
    '| 本机 `python3 scripts/tests/run_all.py` | exit 1；145 PASS / 2 FAIL；未重试 | run_all_eps.log / run_all_eps.exit / run_all_result.json |',
    ('| 调度方沙箱外 `python3 scripts/tests/run_all.py` | 147/147 PASS；全套结果由调度方沙箱外提供 | run_all_fable.log / run_all_fable_result.json |' if external_complete else '| 调度方沙箱外 `python3 scripts/tests/run_all.py` | 调度方称已运行；指定日志尚未落盘，未核实退出码及通过数 | run_all_fable.log（待提供）/ run_all_fable_result.json（缺件状态记录） |'),
    '| `python3 maintenance/repair-20260915-eps-residual/run_followup.py apu` | 子进程 exit 2；旧收据指纹拒收 | apu_formal_followup_result.json / apu_regression.md |',
    f'| `python3 maintenance/repair-20260915-eps-residual/run_followup.py pythia` | 子进程 703/704 exit {pythia["exit_codes"]} | pythia_run_703_result.json / pythia_run_704_result.json |',
    '| `python3 maintenance/repair-20260915-eps-residual/compare_pythia.py` | exit 0；同输入/退出码/原因及可得数量检查通过 | pythia_diff.json / pythia_regression.md |',
    '| `git diff --check`；受保护文件与范围核对 | exit 0；PASS | final_scope_checks.json |', '',
    '本机全套仅 test_batch3_solana_vertical_slice.py:625 与 test_batch3_evm_vertical_slice.py:281 在 ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler) 的 socket.bind 处 PermissionError: [Errno 1] Operation not permitted；没有修改断言或绕过环境限制。', '',
    ('调度方日志 SHA-256：`'+external['log_sha256']+'`。这里只读取并汇总其结果，不声称由本机执行。' if external_complete else '最后核对时间：'+external['checked_at_utc']+'；run_all_fable.log 不存在。已请求提供。待日志到位后仅核对并更新全套结果，不重跑 run_all。'), '',
    '## 5. 已知未修', '',
    '- float64 根因未移除；极端累加序列仍可能超过 gap_eps 并记 data_gap。int(float) 截断为 raw="0" 的既有现象未修。',
    '- fp_residual 仍属 UNRESOLVED，数量保留并计入未决；没有扩大账户 EPS 或闭合容差。',
    '- 算法哈希变化会使旧账本 freeze 重放与 --check-unseal 拒收；含 data_gap 锚点的旧翻转裁决收据须重新裁决，本次不代改。',
    '- PYTHIA 历史 q1 data_gap_events=2191 仅信息性并列；不据此声称新旧历史锚点相同，也不输出代币判断。',
    ('- 本机 socket.bind 限制仍存在；调度方沙箱外全套日志提供本次全套验证证据。按裁决完成即停，未 commit。' if external_complete else '- 本机 socket.bind 限制仍存在；T6/T7 均已完成，唯一未闭合项为调度方 run_all_fable.log 尚未提供，不预写全套通过。未 commit。')]
s='\n'.join(lines)+'\n'
s=s.replace('SELF_LINES',str(len(s.splitlines())))
(OUT/'done.md').write_text(s)
print('done.md:', 'COMPLETE' if external_complete else 'T6/T7 COMPLETE; EXTERNAL SUITE LOG NOT PROVIDED', '; no commit')
