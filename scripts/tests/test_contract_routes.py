#!/usr/bin/env python3
"""R-01/R-02：契约注册表与运行时文档两跳路由的负向回归。"""
import copy
import importlib.util
import json
import os
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location('docs_lint', os.path.join(HERE, 'docs_lint.py'))
DOCS_LINT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DOCS_LINT)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def contract_manifest(authority='references/authority.md'):
    return {
        'schema': 'contract-manifest/v2',
        'contracts': [{
            'id': 'CT-TEST-01',
            'kind': 'required',
            'authority_file': authority,
            'needle': '完整权威规则',
            'stages': ['A3'],
        }],
    }


def runtime_manifest():
    return {
        'schema': 'runtime-docs-manifest/v2',
        'scope': ['references/*.md', 'references/labels/*.md'],
        'listed': [
            {'path': 'entry.md', 'entry': 'entry.md', 'stages': ['A0-A6']},
            {'path': 'leaf.md', 'entry': 'entry.md', 'stages': ['A3']},
        ],
        'maintenance': ['authority.md'],
    }


def main():
    with tempfile.TemporaryDirectory() as root:
        write(os.path.join(root, 'SKILL.md'), '路由：`entry.md`\n')
        write(os.path.join(root, 'references', 'entry.md'), '下钻：`leaf.md`\n')
        write(os.path.join(root, 'references', 'leaf.md'), '叶子规则。\n')
        write(os.path.join(root, 'references', 'authority.md'), '完整权威规则。\n')
        write(os.path.join(root, 'notes.md'), '引用契约 CT-TEST-01。\n')

        cm = contract_manifest()
        assert not DOCS_LINT.validate_contract_manifest(root, cm), '合法契约注册表应通过'

        write(os.path.join(root, 'references', 'authority.md'), '规则被删。\n')
        failures = DOCS_LINT.validate_contract_manifest(root, cm)
        assert any('权威 needle 缺失' in f for f in failures), failures
        write(os.path.join(root, 'references', 'authority.md'), '完整权威规则。\n')

        write(os.path.join(root, 'notes.md'), '引用契约 CT-NOT-FOUND-99。\n')
        failures = DOCS_LINT.validate_contract_manifest(root, cm)
        assert any('悬空契约引用' in f for f in failures), failures
        write(os.path.join(root, 'notes.md'), '引用契约 CT-TEST-01。\n')

        missing = contract_manifest('references/missing.md')
        failures = DOCS_LINT.validate_contract_manifest(root, missing)
        assert any('权威文件不存在' in f for f in failures), failures

        banned_missing = contract_manifest('references/banned-missing.md')
        banned_missing['contracts'][0]['kind'] = 'banned'
        failures = DOCS_LINT.validate_contract_manifest(root, banned_missing)
        assert any('权威文件不存在' in f for f in failures), failures

        banned = contract_manifest()
        banned['contracts'][0]['kind'] = 'banned'
        failures = DOCS_LINT.validate_contract_manifest(root, banned)
        assert any('禁用 needle 回捡' in f for f in failures), failures

        with_summary = contract_manifest()
        with_summary['contracts'][0]['summary'] = 'v2 禁止回潜的人读复述。'
        failures = DOCS_LINT.validate_contract_manifest(root, with_summary)
        assert any('未知字段' in f and 'summary' in f for f in failures), failures

        rm = runtime_manifest()
        assert not DOCS_LINT.validate_runtime_docs_manifest(root, rm), '合法两跳路由应通过'

        on_hit = copy.deepcopy(rm)
        on_hit['listed'][1]['stages'] = ['on-hit']
        assert not DOCS_LINT.validate_runtime_docs_manifest(root, on_hit), \
            'on-hit 只改变加载时机，不应影响两跳可达性'

        ghost = copy.deepcopy(rm)
        ghost['listed'].append({'path': 'ghost.md', 'entry': 'entry.md', 'stages': ['A3']})
        failures = DOCS_LINT.validate_runtime_docs_manifest(root, ghost)
        assert any('幽灵条目' in f for f in failures), failures

        unknown_stage = copy.deepcopy(rm)
        unknown_stage['listed'][0]['stages'] = ['A7']
        failures = DOCS_LINT.validate_runtime_docs_manifest(root, unknown_stage)
        assert any('stages 含未知值' in f and 'A7' in f for f in failures), failures

        legacy_all = copy.deepcopy(rm)
        legacy_all['listed'][0]['stages'] = ['all']
        failures = DOCS_LINT.validate_runtime_docs_manifest(root, legacy_all)
        assert any('stages 含未知值' in f and 'all' in f for f in failures), failures

        write(os.path.join(root, 'references', 'entry.md'), '入口不再引用叶子。\n')
        failures = DOCS_LINT.validate_runtime_docs_manifest(root, rm)
        assert any('两跳内不可达' in f for f in failures), failures

    # 第六类负向（6.29.0 验收加固）：真实注册表条目可被静默删除——lint 只查"在表契约的
    # 权威在场"，不守表自身完整性。基线=总数下限+五组首根锚 ID，删条目/删整组立红。
    real = json.load(open(os.path.join(HERE, 'contract_manifest.json'), encoding='utf-8'))
    real_ids = {c['id'] for c in real['contracts']}
    assert len(real_ids) >= 138, f'契约注册表条目数 {len(real_ids)} 低于 6.30.0 基线 138（删除契约须同步降基线并留 CHANGELOG 记录）'
    anchors = {'CT-METHOD-01', 'CT-CONTROL-01', 'CT-WAVE-01', 'CT-SIMULT-01', 'CT-DISTRIBUTION-01'}
    lost = anchors - real_ids
    assert not lost, f'契约注册表缺五组锚 ID: {sorted(lost)}'

    print('PASS: R-01/R-02 manifest required/banned 负向反证全部阻断＋真实注册表基线（≥138 条、五组锚在场）')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
