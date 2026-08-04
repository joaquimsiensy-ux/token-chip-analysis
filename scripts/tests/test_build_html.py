#!/usr/bin/env python3
"""build_html.py 离线契约测试（v3.3）：WARN=拒绝交付 与看板四键约定的机器约束。

覆盖：
  1. 干净 md（无图引用）→ exit 0、产出 html
  2. md 引用缺失图片 → [WARN] 且 exit 1（缺图不许交付）
  3. --json 四键齐全 → exit 0、html 含 id="report-extract"（看板硬约定）
  4. --json 缺 chip_summary 键 → [WARN] 且 exit 1
用法：python3 scripts/tests/test_build_html.py    退出码 0=PASS / 1=FAIL
"""
import hashlib, json, os, subprocess, sys, tempfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SCRIPT = os.path.join(ROOT, 'scripts', 'report', 'build_html.py')
MD = "# 测试报告\n\n## 一、TL;DR\n\n> i 测试结论一句话\n\n正文段落。\n"
GOOD_JSON = {"chip_summary": {"zhuang_count": 1, "total_share_pct": 5.0,
                              "total_tokens": 1000000, "last_action": "测试"},
             "addresses": [{"address": "0x" + "a" * 40, "chain": "eth", "role": "测试钱包#1",
                            "balance_est": 1, "group": "", "sentinel": False,
                            "watch": True, "why": "测试"}],
             "unlock_events": [], "source_line": "测试口径"}


def run_case(tag, md_text, json_obj, expect_exit, expect_html_has=None, expect_out=None,
             state_obj=None, gate_obj=None, extra_args=None, mode='legacy-recompile'):
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, 'r.md'), 'w').write(md_text)
        cmd = [sys.executable, SCRIPT, '--mode', mode, '--md', 'r.md', '--out', 'r.html']
        if mode not in {'analysis-new', 'analysis-audit'}:
            cmd += ['--degrade-reason', '离线渲染契约测试']
        if json_obj is not None:
            json.dump(json_obj, open(os.path.join(d, 'a.json'), 'w'), ensure_ascii=False)
            cmd += ['--json', 'a.json']
        if state_obj is not None:
            state_path = os.path.join(d, 's.json')
            json.dump(state_obj, open(state_path, 'w'), ensure_ascii=False)
            cmd += ['--state', 's.json']
        if gate_obj is not None:
            gate_obj = dict(gate_obj)
            gate_obj.update({'schema': 'identity_gate_v2', 'chain': 'bsc',
                             'state_file': 's.json',
                             'state_sha256': hashlib.sha256(open(state_path, 'rb').read()).hexdigest(),
                             'n_addresses': len(gate_obj.get('rows', [])),
                             'n_flags': sum(bool(r.get('flag')) for r in gate_obj.get('rows', []))})
            json.dump(gate_obj, open(os.path.join(d, 'identity_gate.json'), 'w'), ensure_ascii=False)
        cmd += (extra_args or [])
        p = subprocess.run(cmd, cwd=d, capture_output=True, text=True)
        fails = []
        if p.returncode != expect_exit:
            fails.append(f'退出码 {p.returncode} != 期望 {expect_exit}\n{p.stdout}{p.stderr}')
        if expect_out and expect_out not in p.stdout:
            fails.append(f'stdout 缺「{expect_out}」')
        if expect_html_has:
            h = os.path.join(d, 'r.html')
            body = open(h).read() if os.path.exists(h) else ''
            if expect_html_has not in body:
                fails.append(f'html 缺「{expect_html_has}」')
        if fails:
            print(f'FAIL [{tag}]:');  [print('  ' + x) for x in fails]
            return False
        print(f'ok   [{tag}]')
        return True


def main():
    ok = True
    ok &= run_case('干净 md 零 WARN', MD, None, 0)
    ok &= run_case('缺图=WARN 拒交付', MD + "\n![图1](charts/nope.png)\n*题注*\n", None, 1,
                   expect_out='[WARN]')
    ok &= run_case('四键 JSON 嵌入+report-extract id', MD, GOOD_JSON, 0,
                   expect_html_has='id="report-extract"')
    bad = {k: v for k, v in GOOD_JSON.items() if k != 'chip_summary'}
    ok &= run_case('缺四键=WARN 拒交付', MD, bad, 1, expect_out='[WARN]')
    # G8 实体身份闸（v4.2：IQ/LPT/PYTHIA 托管误判三案根治）
    STATE = {"chain": "bsc", "whale_groups": [
        {"entity_id": "e_t", "addresses": ["0x" + "b" * 40]}]}
    LABEL = {"name": "known", "category": "other", "tier": "identity", "source": "fixture"}
    GATE_OK = {"rows": [
        {"address": "0x" + "b" * 40, "entity": "e_t", "share_pct": None,
         "label": LABEL, "on_curve": None, "flag": "", "resolution": ""}]}
    GATE_BAD = {"rows": [
        {"address": "0x" + "b" * 40, "entity": "e_t", "share_pct": None,
         "label": None, "on_curve": None, "flag": "BIG_UNLABELED", "resolution": ""}]}
    ok &= run_case('G8 无gate文件=WARN 拒交付', MD, None, 1, expect_out='G8 实体身份闸缺失',
                   state_obj=STATE)
    ok &= run_case('G8 flag未解决=WARN 拒交付', MD, None, 1, expect_out='无 resolution',
                   state_obj=STATE, gate_obj=GATE_BAD)
    ok &= run_case('G8 全解决=过闸', MD, None, 0, state_obj=STATE, gate_obj=GATE_OK)
    ok &= run_case('analysis-new 缺正式 gate 资产拒绝', MD, None, 2,
                   mode='analysis-new')
    ok &= run_case('降级模式必须带可见水印', MD, None, 0,
                   expect_html_has='非正式分析交付物')
    print('PASS: build_html 九条契约全过（含 analysis/legacy 模式边界）' if ok else 'FAIL: 见上')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
