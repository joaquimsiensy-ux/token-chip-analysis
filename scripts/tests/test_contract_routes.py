#!/usr/bin/env python3
"""R-01/R-02：契约注册表与运行时文档两跳路由的负向回归。"""
import copy
import importlib.util
import json
import os
import re
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
        'scope': ['references/*.md', 'references/labels/*.md', 'references/casebook/*.md'],
        'listed': [
            {'path': 'entry.md', 'entry': 'entry.md', 'stages': ['A0-A6']},
            {'path': 'leaf.md', 'entry': 'entry.md', 'stages': ['A3']},
        ],
        'maintenance': ['authority.md'],
    }


def assert_contract_ids_match(actual_ids, snapshot_ids):
    missing = sorted(snapshot_ids - actual_ids)
    extra = sorted(actual_ids - snapshot_ids)
    assert not missing and not extra, (
        f'契约 ID 快照漂移：快照有但 manifest 缺失={missing}；'
        f'manifest 多出但快照未登记={extra}。'
        '增删契约须同步更新 contract_ids_snapshot.json 并在 CHANGELOG 留记录')


def assert_skill_route_stages(skill_text):
    """全流程路由表必须覆盖全部原子阶段，也不得私生未知阶段号。"""
    start = skill_text.index('## 全流程路由')
    end = skill_text.index('\n## ', start + 3)
    table = skill_text[start:end]
    routed = set()
    for line in table.splitlines():
        match = re.match(r'^\|\s*(A\d+(?:\.\d+)?(?:[–-]A\d+(?:\.\d+)?)?)\b', line)
        if match:
            routed.add(match.group(1))
    atomic = {'A0', 'A1', 'A2', 'A3', 'A4', 'A4.5', 'A5', 'A6'}
    missing = sorted(atomic - routed)
    assert not missing, f'SKILL.md 全流程路由表缺原子阶段: {missing}'
    unknown = sorted(stage for stage in routed
                     if stage not in DOCS_LINT.RUNTIME_STAGES
                     and not re.fullmatch(r'A\d+(?:\.\d+)?[–-]A\d+(?:\.\d+)?', stage))
    assert not unknown, f'SKILL.md 全流程路由表出现未知阶段: {unknown}'


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

    # 第六类负向：真实注册表条目可被静默增删——完整 ID 集合快照双向闭合。
    real = json.load(open(os.path.join(HERE, 'contract_manifest.json'), encoding='utf-8'))
    real_ids = {c['id'] for c in real['contracts']}
    snapshot_list = json.load(open(os.path.join(HERE, 'contract_ids_snapshot.json'), encoding='utf-8'))
    assert (isinstance(snapshot_list, list) and snapshot_list
            and all(isinstance(contract_id, str) and contract_id for contract_id in snapshot_list)), \
        'contract_ids_snapshot.json 必须是非空字符串数组'
    assert snapshot_list == sorted(set(snapshot_list)), \
        'contract_ids_snapshot.json 必须按 ID 排序且不得重复'
    snapshot_ids = set(snapshot_list)
    assert_contract_ids_match(real_ids, snapshot_ids)

    # 内存反例：删一条与加一条必须分别落入 missing / extra，禁止仅守数量。
    removed_id = snapshot_list[0]
    without_one = set(snapshot_ids)
    without_one.remove(removed_id)
    try:
        assert_contract_ids_match(without_one, snapshot_ids)
    except AssertionError as exc:
        assert removed_id in str(exc) and 'manifest 缺失' in str(exc), exc
    else:
        raise AssertionError('删除一条契约 ID 未被快照守卫捕获')
    fake_id = 'CT-SNAPSHOT-FAKE-99'
    with_extra = set(snapshot_ids) | {fake_id}
    try:
        assert_contract_ids_match(with_extra, snapshot_ids)
    except AssertionError as exc:
        assert fake_id in str(exc) and 'manifest 多出' in str(exc), exc
    else:
        raise AssertionError('新增一条假契约 ID 未被快照守卫捕获')

    anchors = {'CT-METHOD-01', 'CT-CONTROL-01', 'CT-WAVE-01', 'CT-SIMULT-01', 'CT-DISTRIBUTION-01'}
    lost = anchors - real_ids
    assert not lost, f'契约注册表缺五组锚 ID: {sorted(lost)}'

    skill_text = open(os.path.join(HERE, '..', '..', 'SKILL.md'), encoding='utf-8').read()
    assert_skill_route_stages(skill_text)

    print('PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
