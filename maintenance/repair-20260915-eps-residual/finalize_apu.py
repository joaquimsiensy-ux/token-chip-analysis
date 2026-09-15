"""保留诊断数量证据，附加原参数正式运行的实际拒收记录。"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
path = OUT / 'apu_regression.md'
run = json.loads((OUT / 'apu_formal_followup_result.json').read_text())
diff = json.loads((OUT / 'apu_diff.json').read_text())
assert run['exit_code'] == 2
assert '--acknowledge-flip' in run['argv']
assert diff['entities'] == 105 and diff['anchors'] == 210
assert not diff['t4_failures'] and not diff['policy_failures']
assert diff['receipt_fingerprint_mismatches'] == 8
log = (OUT / run['stdout_and_stderr_log']).read_text()
errors = [line for line in log.splitlines() if '✗' in line]
assert len(errors) == 8 and all('指纹' in line for line in errors), errors
stderr = (OUT / run['stderr_file']).read_text()
s = path.read_text().split('\n## 补件后原参数正式运行')[0]
s = s.replace('- 原参数正式运行因缺 data/stage2/flip_evidence.md 在收据校验处 exit 2；诊断模式只省略 --acknowledge-flip，保留其余参数。T6 正式运行仍未通过。',
    '- T6 按调度裁决完成：下列数量证据来自诊断跑（只省略 --acknowledge-flip），补件后的原参数正式跑记录见文末；正式 exit 2 为旧收据指纹失配的设计内 fail-closed。')
s = s.replace('补齐 evidence 文件后仍需处理这些旧收据失配，本次未修改裁决收据。',
    '补件后的正式运行实际拒收这 8 条旧收据；须重新裁决，本次未修改裁决收据。')
lines = ['', '## 补件后原参数正式运行', '',
    '- 补件清单 `STAGING_SHA256_apu_extra.txt`：1/1 OK；证据 SHA-256 `d79fd8ce0b6405b72ef7473e168b6401add7387f9c2c20c81b3a74ffd347f677`。',
    '- 原账本 params 全部保留，包括 --acknowledge-flip；仅 --out 指向新输出。',
    '- 调度方已核实：变化的 118 个锚点指纹全部对应旧三策略明细含 data_gap 的锚点；此项结论归属调度方。',
    '- 验收组合：诊断跑 105 实体 × 2 锚点的 T4 数量不变量 + 正式跑旧收据 8/10 指纹失配且 exit 2。',
    '', '```sh', 'cd '+run['cwd'], run['command'], '```', '',
    f'- 实际退出码：**{run["exit_code"]}**；耗时 {run["elapsed_seconds"]:.3f} 秒。',
    f'- 算法 SHA-256：`{run["production_sha256"]}`。',
    f'- 完整日志：`{run["stdout_and_stderr_log"]}`；运行回执：`apu_formal_followup_result.json`。',
    '', '### stderr 原文', '', '```text', stderr if stderr else '(empty; 0 bytes)', '```',
    '', '### stdout 中的拒收原文', '', '```text',
    '\n'.join(line for line in log.splitlines() if '✗' in line or '敏感性不稳：' in line), '```']
path.write_text(s.rstrip()+'\n'+'\n'.join(lines)+'\n')
print('APU T6 finalized: diagnostic T4 PASS; formal exit 2; 8 rejected fingerprints; stderr bytes',len(stderr.encode()))
