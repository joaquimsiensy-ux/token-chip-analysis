#!/usr/bin/env python3
"""文档守护：引用断链 + 粗体配对 + SKILL.md 引用漂移哨。

背景：追加式迭代下文档互引会漂移。本脚本抓"结构可查"的那部分：
1. md 里引用的本仓库文件路径必须存在（references/*.md、scripts/**.py、labels/*.csv|md）
2. 每行 ** 配对（奇数个 ** 的行=残缺粗体，渲染会烂）
3. runtime docs manifest v2 的文档必须从 SKILL.md 经入口两跳可达
4. canonical contract manifest 的权威 needle、路径与契约 ID 引用必须闭合
复盘写入后必跑（retrospective 步骤 3）；整编触发条件之一=本脚本抓出漂移 ≥3 处。

用法：python3 scripts/tests/docs_lint.py [--all]    退出码：0=PASS；1=FAIL。
  --all＝全量模式（v6.3.1）：额外纳入 commands-staging/*.md 与 archive/evals/**/*.md——
  此前 44/66 文档的覆盖盲区（"三查→四查""SKILL.md 阶段 N"类漂移在这两处存活过）。
"""
import ast, glob, json, os, re, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# 引用模式：仓库内相对路径（含 ` 包裹或裸写两种）；排除占位符 <chain> 与缩写 ...
REF_RE = re.compile(r'(?<![\w/~])(?:references/[\w./-]+\.(?:md|csv|png)|scripts/[\w./-]+\.(?:py|sh)|labels/[\w.-]+\.(?:md|csv))')
# 负向后顾排除长路径尾段（如 ~/Desktop/xx/scripts/chip_analysis.py 的历史出处说明——那不是仓库内引用）
REMOVED_FEATURE_TERMS = re.compile(
    r'easy-workflow|update-workflow|token-easy-analysis|token-update|'
    r'collect-data|collect-workflow|\bcollect_queue\b|\bnightly_collect\b|'
    r'\bcollect_manifest\b|\bprobe_keys\b|\bweekly-probe\b|'
    r'批量预采集|预采集衔接|easy 初筛|easy E5|'
    r'\bE0b?\b|\bU[0-6]\b',
    re.I)
RETAINED_FEATURE_TERMS = ('collector', 'collection_manifest', 'csv_collector_receipt', 'probe')
CONTRACT_REF_RE = re.compile(r'契约\s+(CT-[A-Z][A-Z0-9-]*-\d{2,})')
MD_NAME_RE = re.compile(r'(?<![\w/])(?:references/)?([\w./-]+\.md)')
RUNTIME_STAGES = {
    'preflight', 'on-hit', 'A0', 'A1', 'A2', 'A3', 'A4', 'A4.5', 'A5', 'A6', 'post-A5',
    'A0-A2', 'A0-A3', 'A0-A5', 'A0-A6',
}


def _safe_repo_path(root, rel):
    """只接受仓库内相对路径，避免 manifest 用绝对路径或 .. 逃逸。"""
    if not isinstance(rel, str) or not rel or os.path.isabs(rel):
        return None
    path = os.path.normpath(os.path.join(root, rel))
    try:
        inside = os.path.commonpath([os.path.abspath(root), os.path.abspath(path)]) == os.path.abspath(root)
    except ValueError:
        inside = False
    return path if inside else None


def _markdown_targets(text):
    """抽取文档引用并统一成 references/ 根下的相对路径。"""
    out = set()
    for target in MD_NAME_RE.findall(text):
        target = target.removeprefix('references/')
        out.add(os.path.normpath(target))
    return out


def validate_contract_manifest(root, manifest):
    """R-02：校验 required/banned needle、路径和全库契约 ID 引用。"""
    failures = []
    if not isinstance(manifest, dict):
        return ['契约注册表顶层必须是对象']
    top_fields = {'schema', 'contracts'}
    unknown_top = sorted(set(manifest) - top_fields)
    missing_top = sorted(top_fields - set(manifest))
    if missing_top:
        failures.append(f'契约注册表缺字段: {missing_top}')
    if unknown_top:
        failures.append(f'契约注册表未知字段: {unknown_top}')
    if manifest.get('schema') != 'contract-manifest/v2':
        failures.append(f'契约注册表 schema 非法: {manifest.get("schema")!r}')
    contracts = manifest.get('contracts')
    if not isinstance(contracts, list) or not contracts:
        failures.append('契约注册表 contracts 必须是非空数组')
        return failures

    known_ids = set()
    authority_needles = set()
    required = {'id', 'kind', 'authority_file', 'needle', 'stages'}
    for index, contract in enumerate(contracts, 1):
        label = f'contracts[{index}]'
        if not isinstance(contract, dict):
            failures.append(f'{label} 必须是对象')
            continue
        missing = sorted(required - set(contract))
        unknown = sorted(set(contract) - required)
        if missing:
            failures.append(f'{label} 缺字段: {missing}')
            continue
        if unknown:
            failures.append(f'{label} 未知字段: {unknown}')
            continue
        contract_id = contract['id']
        if not isinstance(contract_id, str) or not re.fullmatch(r'CT-[A-Z][A-Z0-9-]*-\d{2,}', contract_id):
            failures.append(f'{label} 契约 ID 非法: {contract_id!r}')
        elif contract_id in known_ids:
            failures.append(f'重复契约 ID: {contract_id}')
        else:
            known_ids.add(contract_id)
        kind = contract['kind']
        if kind not in {'required', 'banned'}:
            failures.append(f'{label} kind 非法: {kind!r}')
        stages = contract['stages']
        if (not isinstance(stages, list) or not stages
                or any(not isinstance(stage, str) or not stage for stage in stages)):
            failures.append(f'{label} stages 必须是非空字符串数组')
        needle = contract['needle']
        if not isinstance(needle, str) or not needle:
            failures.append(f'{label} needle 必须是非空字符串')
            continue
        authority = contract['authority_file']
        authority_path = _safe_repo_path(root, authority)
        if authority_path is None or not os.path.isfile(authority_path):
            failures.append(f'权威文件不存在 {contract_id}: {authority}')
            continue
        pair = (os.path.normpath(authority), needle)
        if pair in authority_needles:
            failures.append(f'重复权威 needle {contract_id}: {authority} → {needle}')
        authority_needles.add(pair)
        with open(authority_path, encoding='utf-8') as f:
            authority_text = f.read()
        if kind == 'required' and needle not in authority_text:
            failures.append(f'权威 needle 缺失 {contract_id}: {authority} → {needle}')
        if kind == 'banned' and needle in authority_text:
            failures.append(f'禁用 needle 回捡 {contract_id}: {authority} → {needle}')

    # 引用只在 Markdown 中具有契约语义；JSON 中的 ID 是定义，不算引用。
    for path in sorted(glob.glob(os.path.join(root, '**', '*.md'), recursive=True)):
        rel = os.path.relpath(path, root)
        if rel.startswith(f'.git{os.sep}'):
            continue
        with open(path, encoding='utf-8') as f:
            for line_no, line in enumerate(f, 1):
                for contract_id in CONTRACT_REF_RE.findall(line):
                    if contract_id not in known_ids:
                        failures.append(f'悬空契约引用 {rel}:{line_no}: {contract_id}')
    return failures


def validate_runtime_docs_manifest(root, manifest):
    """R-01：校验 v2 分类结构和 SKILL→入口→分册两跳可达性。"""
    failures = []
    if not isinstance(manifest, dict):
        return ['运行时文档 manifest 顶层必须是对象']
    required = {'schema', 'scope', 'listed', 'maintenance'}
    missing = sorted(required - set(manifest))
    if missing:
        return [f'运行时文档 manifest 缺字段: {missing}']
    if manifest['schema'] != 'runtime-docs-manifest/v2':
        failures.append(f'运行时文档 manifest schema 非法: {manifest["schema"]!r}')
    expected_scope = ['references/*.md', 'references/labels/*.md',
                      'references/casebook/*.md']
    scope = manifest['scope']
    if (not isinstance(scope, list)
            or any(not isinstance(pattern, str) or not pattern for pattern in scope)):
        failures.append('运行时文档 manifest scope 必须是非空字符串数组')
        scope = []
    elif scope != expected_scope:
        failures.append(f'运行时文档 manifest scope 非法: {scope!r}')

    listed = manifest['listed']
    maintenance = manifest['maintenance']
    if not isinstance(listed, list) or not listed:
        failures.append('运行时文档 manifest listed 必须是非空对象数组')
        listed = []
    if (not isinstance(maintenance, list)
            or any(not isinstance(item, str) or not item for item in maintenance)):
        failures.append('运行时文档 manifest maintenance 必须是字符串数组')
        maintenance = []
    elif len(maintenance) != len(set(maintenance)):
        failures.append('运行时文档 manifest maintenance 含重复条目')

    entries = []
    listed_paths = []
    for index, item in enumerate(listed, 1):
        if not isinstance(item, dict):
            failures.append(f'listed[{index}] 必须是对象')
            continue
        item_missing = sorted({'path', 'entry', 'stages'} - set(item))
        if item_missing:
            failures.append(f'listed[{index}] 缺字段: {item_missing}')
            continue
        path, entry, stages = item['path'], item['entry'], item['stages']
        if (not isinstance(path, str) or not path or path.startswith('references/')
                or _safe_repo_path(os.path.join(root, 'references'), path) is None):
            failures.append(f'listed[{index}] path 非法: {path!r}')
            continue
        if (not isinstance(entry, str) or not entry or entry.startswith('references/')
                or _safe_repo_path(os.path.join(root, 'references'), entry) is None):
            failures.append(f'listed[{index}] entry 非法: {entry!r}')
            continue
        if (not isinstance(stages, list) or not stages
                or any(not isinstance(stage, str) or not stage for stage in stages)):
            failures.append(f'listed[{index}] stages 必须是非空字符串数组')
            continue
        unknown_stages = sorted(set(stages) - RUNTIME_STAGES)
        if unknown_stages:
            failures.append(f'listed[{index}] stages 含未知值: {unknown_stages}')
            continue
        path = os.path.normpath(path)
        entry = os.path.normpath(entry)
        entries.append((path, entry))
        listed_paths.append(path)
    if len(listed_paths) != len(set(listed_paths)):
        failures.append('运行时文档 manifest listed 含重复 path')

    refs_root = os.path.join(root, 'references')
    actual_docs = set()
    for pattern in scope:
        for path in glob.glob(os.path.join(root, pattern)):
            if os.path.isfile(path):
                actual_docs.add(os.path.relpath(path, refs_root))
    listed_set = set(listed_paths)
    maintenance_set = set(maintenance)
    for base in sorted(actual_docs - listed_set - maintenance_set):
        failures.append(f'未归类文档: references/{base}')
    for base in sorted((listed_set | maintenance_set) - actual_docs):
        failures.append(f'幽灵条目: references/{base}')
    for base in sorted(listed_set & maintenance_set):
        failures.append(f'listed 与 maintenance 交集: references/{base}')

    skill_path = os.path.join(root, 'SKILL.md')
    if not os.path.isfile(skill_path):
        failures.append('SKILL.md 不存在，无法校验两跳路由')
        skill = ''
    else:
        with open(skill_path, encoding='utf-8') as f:
            skill = f.read()
    skill_targets = _markdown_targets(skill)
    entry_targets = {}
    for path, entry in entries:
        if entry not in listed_set:
            failures.append(f'入口未登记: references/{path} → references/{entry}')
        if entry not in skill_targets:
            failures.append(f'入口未从 SKILL.md 路由: references/{entry}')
        entry_path = os.path.join(refs_root, entry)
        if entry not in entry_targets:
            if os.path.isfile(entry_path):
                with open(entry_path, encoding='utf-8') as f:
                    entry_targets[entry] = _markdown_targets(f.read())
            else:
                entry_targets[entry] = set()
        if path != entry and path not in entry_targets[entry]:
            failures.append(
                f'两跳内不可达: SKILL.md → references/{entry} → references/{path}')

    # maintenance 反向禁列；attic.md 只允许一条含“禁读”的负向边界声明。
    skill_lines = skill.splitlines()
    for base in sorted(maintenance_set):
        name = os.path.basename(base)
        occurrences = [(i, line) for i, line in enumerate(skill_lines, 1)
                       if base in line or name in line]
        if base == 'attic.md':
            legal = [(i, line) for i, line in occurrences if '禁读' in line]
            illegal = [(i, line) for i, line in occurrences if '禁读' not in line]
            for i, _ in illegal:
                failures.append(f'SKILL.md maintenance 禁列: references/{base} 出现在第 {i} 行')
            if len(legal) > 1:
                failures.append('SKILL.md attic.md 禁读边界声明只能出现一条')
        else:
            for i, _ in occurrences:
                failures.append(f'SKILL.md maintenance 禁列: references/{base} 出现在第 {i} 行')
    return failures

def md_files(all_mode=False):
    out = [os.path.join(ROOT, 'SKILL.md'), os.path.join(ROOT, 'CHANGELOG.md')]
    out += sorted(glob.glob(os.path.join(ROOT, 'references', '**', '*.md'), recursive=True))
    out += sorted(glob.glob(os.path.join(ROOT, 'scripts', '**', 'README.md'), recursive=True))
    if all_mode:
        out += sorted(glob.glob(os.path.join(ROOT, 'commands-staging', '*.md')))
        out += sorted(glob.glob(os.path.join(ROOT, 'archive', 'evals', '**', '*.md'), recursive=True))
    return [p for p in out if os.path.exists(p)]

def resolve(ref, src_path):
    """引用相对 skill 根、references/、或引用文件所在目录三种基准都试。"""
    cands = [os.path.join(ROOT, ref),
             os.path.join(ROOT, 'references', ref),
             os.path.join(os.path.dirname(src_path), ref)]
    return any(os.path.exists(c) for c in cands)

def removed_feature_in_module_docstring(source, rel):
    """返回 module docstring 的已删功能命中；语法不可解析时容错跳过。"""
    try:
        tree = ast.parse(source, filename=rel)
    except (SyntaxError, ValueError):
        return None
    docstring = ast.get_docstring(tree)
    if not docstring:
        return None
    match = REMOVED_FEATURE_TERMS.search(docstring)
    if match:
        return f'已删功能回捡 {rel}: 出现 {match.group(0)}'
    return None

def main(all_mode=False):
    fails = []
    warn_broken = 0
    skill_path = os.path.join(ROOT, 'SKILL.md')
    skill_bytes = os.path.getsize(skill_path)
    if skill_bytes > 8192:
        fails.append(f'SKILL.md 超过 8192 bytes：{skill_bytes}')
    for path in md_files(all_mode):
        rel = os.path.relpath(path, ROOT)
        in_code = False
        for i, line in enumerate(open(path, encoding='utf-8'), 1):
            if line.strip().startswith('```'):
                in_code = not in_code
                continue
            if in_code:
                continue
            # 1) 断链。CHANGELOG 历史条目引用当时存在的文件是历史记录，不是死链；
            #    每轮功能删除都会让旧条目变成“断链”，为守卫改史不可持续（6.17/6.18
            #    两轮已实证）。archive/CHANGELOG-archive.md 本就不在 md_files 扫描集；此处豁免
            #    CHANGELOG.md，使两份 CHANGELOG 口径一致，并与守卫 11 的禁词豁免对齐。
            #    只跳过断链检查，下面的粗体配对等其他检查仍照常执行。
            if rel != 'CHANGELOG.md':
                for ref in REF_RE.findall(line):
                    if '<' in ref or '...' in ref or '*' in ref:
                        continue
                    if not resolve(ref, path):
                        fails.append(f'断链 {rel}:{i} → {ref}')
                        warn_broken += 1
            # 2) 粗体配对（该行 ** 计数应为偶数）
            if line.count('**') % 2 == 1:
                fails.append(f'残缺粗体 {rel}:{i}: {line.strip()[:60]}')

    # 2b) 考古资料不得重新进入执行上下文。只允许维护记录、考古区自身、
    #    明示的存留审计/判例/复盘文档，以及 SKILL.md 的单行禁读边界声明；
    #    后者只声明不可读取，不是把 archive 资产路由回执行会话。
    archive_guard_docs = [os.path.join(ROOT, 'SKILL.md'), os.path.join(ROOT, 'CHANGELOG.md')]
    archive_guard_docs += sorted(glob.glob(os.path.join(ROOT, 'references', '**', '*.md'), recursive=True))
    archive_guard_docs += sorted(glob.glob(os.path.join(ROOT, 'archive', '**', '*.md'), recursive=True))
    archive_ref_exempt = {'CHANGELOG.md', 'references/attic.md', 'references/retrospective.md'}
    skill_archive_boundary = ('archive/ = 考古区（旧 CHANGELOG 归档/评测题库/冲突审计历史），'
                              '执行会话禁读。')
    for path in archive_guard_docs:
        rel = os.path.relpath(path, ROOT)
        if (rel in archive_ref_exempt or rel.startswith(f'archive{os.sep}')
                or rel.startswith(f'references{os.sep}casebook{os.sep}')):
            continue
        for i, line in enumerate(open(path, encoding='utf-8'), 1):
            if 'archive/' not in line:
                continue
            if rel == 'SKILL.md' and line.strip() == skill_archive_boundary:
                continue
            fails.append(
                f'考古区越界引用 {rel}:{i}: 现役执行文档不得引用 archive/，防止历史资产回流执行上下文')

    # 3) SKILL.md 显式 bullet 引用的遗留兼容断链检查；v2 两跳守卫在下方执行。
    skill = open(skill_path, encoding='utf-8').read()
    for name in re.findall(r'^- `([\w/.-]+\.md)`', skill, re.M):
        if not (os.path.exists(os.path.join(ROOT, 'references', name)) or os.path.exists(os.path.join(ROOT, name))):
            fails.append(f'SKILL.md 深入阅读清单断链: {name}')
    # 4) 运行时文档 manifest 是分类、入口归属和阶段语义的唯一事实源。SKILL.md
    #    只列二级入口，分册由入口继续路由；维护件不得被反向漏列检查强迫进入口。
    manifest_rel = 'scripts/tests/runtime_docs_manifest.json'
    manifest_path = os.path.join(ROOT, manifest_rel)
    manifest_hint = f'{manifest_rel}；新增文档须先在 manifest 归类'

    def manifest_failure(message):
        fails.append(f'{message}（{manifest_hint}）')

    try:
        with open(manifest_path, encoding='utf-8') as f:
            manifest = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        manifest_failure(f'运行时文档 manifest 无法解析: {exc}')
        manifest = None

    if manifest is not None:
        for failure in validate_runtime_docs_manifest(ROOT, manifest):
            manifest_failure(failure)

    # 5) required/banned 契约由 canonical manifest 单点登记；复述层不再被 lint 强迫复制。
    contract_manifest_rel = 'scripts/tests/contract_manifest.json'
    contract_manifest_path = os.path.join(ROOT, contract_manifest_rel)
    try:
        with open(contract_manifest_path, encoding='utf-8') as f:
            contract_manifest = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        fails.append(f'契约注册表无法解析 {contract_manifest_rel}: {exc}')
        contract_manifest = None
    if contract_manifest is not None:
        fails.extend(validate_contract_manifest(ROOT, contract_manifest))

    # 9) 2026-08-04 一致性复核的 required/banned 语义针脚已并入上方 manifest。
    active_workflows = ['SKILL.md', 'references/analyze-workflow.md',
                        'references/report-template.md', 'references/split-run.md']
    generic_mode = re.compile(r'--mode analysis(?=[\s`])')
    for rel in active_workflows:
        text = open(os.path.join(ROOT, rel), encoding='utf-8').read()
        if generic_mode.search(text):
            fails.append(f'2026-08-04 generic analysis 模式回退 {rel}')

    # 10) 执行文档只能从 VERSION 读取当前版本，禁止重新把大 CHANGELOG 拉回开工阅读链。
    version_instruction = re.compile(
        r'读[^。\n]{0,24}CHANGELOG[^。\n]{0,24}版本号|CHANGELOG[^。\n]{0,16}首(?:个)?版本号')
    execution_docs = ['SKILL.md', 'references/analyze-workflow.md',
                      'references/split-run.md', 'references/context-discipline.md']
    for rel in execution_docs:
        text = open(os.path.join(ROOT, rel), encoding='utf-8').read()
        if version_instruction.search(text):
            fails.append(f'版本读取回退 {rel}: 执行文档必须读 VERSION，不得读 CHANGELOG 首版本号')

    # 11) 已下线的轻量筛查/增量更新/批量预采集/API key 周巡检功能不得重回现役文档。
    for retained_term in RETAINED_FEATURE_TERMS:
        if REMOVED_FEATURE_TERMS.search(retained_term):
            fails.append(f'已删功能禁词误伤保留概念: {retained_term}')
    active_docs = [p for p in md_files(all_mode=True)
                   if os.path.relpath(p, ROOT) not in {'CHANGELOG.md', 'archive/CHANGELOG-archive.md'}
                   and os.path.relpath(p, ROOT) != 'references/attic.md'
                   and not os.path.relpath(p, ROOT).startswith('references/casebook/')]
    for path in active_docs:
        rel = os.path.relpath(path, ROOT)
        text = open(path, encoding='utf-8').read()
        match = REMOVED_FEATURE_TERMS.search(text)
        if match:
            fails.append(f'已删功能回捡 {rel}: 出现 {match.group(0)}')
    python_files = sorted(glob.glob(os.path.join(ROOT, 'scripts', '**', '*.py'), recursive=True))
    for path in python_files:
        rel = os.path.relpath(path, ROOT)
        if rel.startswith(f'scripts{os.sep}tests{os.sep}'):
            continue
        failure = removed_feature_in_module_docstring(open(path, encoding='utf-8').read(), rel)
        if failure:
            fails.append(failure)

    if fails:
        for f in fails[:30]:
            print('FAIL:', f)
        if len(fails) > 30:
            print(f'…共 {len(fails)} 处')
        if warn_broken >= 3:
            print(f'⚠ 断链 ≥3 处——按 retrospective 2b 触发整编条件')
        return 1
    print(f'PASS: {len(md_files(all_mode))} 个文档，引用无断链、粗体配对完整'
          + ('（--all 全量模式）' if all_mode else ''))
    return 0

if __name__ == '__main__':
    sys.exit(main('--all' in sys.argv[1:]))
