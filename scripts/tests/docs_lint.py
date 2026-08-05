#!/usr/bin/env python3
"""文档守护：引用断链 + 粗体配对 + SKILL.md 引用漂移哨。

背景：追加式迭代下文档互引会漂移。本脚本抓"结构可查"的那部分：
1. md 里引用的本仓库文件路径必须存在（references/*.md、scripts/**.py、labels/*.csv|md）
2. 每行 ** 配对（奇数个 ** 的行=残缺粗体，渲染会烂）
3. SKILL.md「深入阅读」列出的文件必须齐全
4. 关键方法硬闸必须同时出现在工作流、方法、判级和报告验收四层，防规则只写在角落而实际被跳过
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

    # 3) SKILL.md 深入阅读清单齐全性
    skill = open(skill_path, encoding='utf-8').read()
    for name in re.findall(r'^- `([\w/.-]+\.md)`', skill, re.M):
        if not (os.path.exists(os.path.join(ROOT, 'references', name)) or os.path.exists(os.path.join(ROOT, name))):
            fails.append(f'SKILL.md 深入阅读清单断链: {name}')
    # 4) 运行时文档 manifest 是“必须列入/维护禁列”的唯一事实源。SKILL.md 只路由
    #    现役文档，维护件不得再因为 lint 的反向漏列检查而被迫进入口。
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

    required_manifest_fields = {'schema', 'scope', 'listed', 'maintenance'}
    if manifest is not None:
        if not isinstance(manifest, dict):
            manifest_failure('运行时文档 manifest 顶层必须是对象')
            manifest = None
        else:
            missing_fields = sorted(required_manifest_fields - set(manifest))
            if missing_fields:
                manifest_failure(f'运行时文档 manifest 缺字段: {missing_fields}')
                manifest = None

    if manifest is not None:
        manifest_valid = True
        expected_scope = ['references/*.md', 'references/labels/*.md']
        if manifest['schema'] != 'runtime-docs-manifest/v1':
            manifest_failure(f'运行时文档 manifest schema 非法: {manifest["schema"]!r}')
            manifest_valid = False
        if manifest['scope'] != expected_scope:
            manifest_failure(f'运行时文档 manifest scope 非法: {manifest["scope"]!r}')
            manifest_valid = False
        for field in ('listed', 'maintenance'):
            value = manifest[field]
            if (not isinstance(value, list)
                    or any(not isinstance(item, str) or not item for item in value)):
                manifest_failure(f'运行时文档 manifest {field} 必须是非空字符串数组')
                manifest_valid = False
            elif len(value) != len(set(value)):
                manifest_failure(f'运行时文档 manifest {field} 含重复条目')
                manifest_valid = False

        if manifest_valid:
            refs_root = os.path.join(ROOT, 'references')
            actual_docs = set()
            for pattern in manifest['scope']:
                for path in glob.glob(os.path.join(ROOT, pattern)):
                    if os.path.isfile(path):
                        actual_docs.add(os.path.relpath(path, refs_root))
            listed_docs = set(manifest['listed'])
            maintenance_docs = set(manifest['maintenance'])

            for base in sorted(actual_docs - listed_docs - maintenance_docs):
                manifest_failure(f'未归类文档: references/{base}')
            for base in sorted((listed_docs | maintenance_docs) - actual_docs):
                manifest_failure(f'幽灵条目: references/{base}')
            for base in sorted(listed_docs & maintenance_docs):
                manifest_failure(f'listed 与 maintenance 交集: references/{base}')

            # listed 沿用旧判定：相对路径或文件名任一出现在 SKILL.md 即视为已列。
            for base in sorted(listed_docs):
                if base not in skill and os.path.basename(base) not in skill:
                    manifest_failure(f'SKILL.md 深入阅读清单漏列: references/{base}')

            # maintenance 反向禁列；attic.md 只允许一条含“禁读”的负向边界声明。
            skill_lines = skill.splitlines()
            for base in sorted(maintenance_docs):
                name = os.path.basename(base)
                occurrences = [(i, line) for i, line in enumerate(skill_lines, 1)
                               if base in line or name in line]
                if base == 'attic.md':
                    legal = [(i, line) for i, line in occurrences if '禁读' in line]
                    illegal = [(i, line) for i, line in occurrences if '禁读' not in line]
                    for i, _ in illegal:
                        manifest_failure(f'SKILL.md maintenance 禁列: references/{base} 出现在第 {i} 行')
                    if len(legal) > 1:
                        manifest_failure('SKILL.md attic.md 禁读边界声明只能出现一条')
                else:
                    for i, _ in occurrences:
                        manifest_failure(f'SKILL.md maintenance 禁列: references/{base} 出现在第 {i} 行')

    # 5) 历史静置仓反向扫描是实体冻结前硬闸；四层任一缺失都视为方法回退。
    method_contracts = {
        'SKILL.md': ['EF-2 历史静置仓反扫', 'dormant_warehouse_audit.json', '不允许冻结实体'],
        'references/playbook-entity-cluster-methods.md': ['候选全集从三条现役机械通道取齐', 'strict ∪ expanded', '同一交易末快照',
                                                          'universe_ref', 'must_adjudicate', 'OTC 排除检验'],
        'references/playbook-entity-cluster-tiering.md': ['历史静置仓反向扫描后的双边界峰值', '严格下限', '扩展上限',
                                                          'prev_close_plus_gross_in/v2', 'trigger_days.json'],
        'references/report-template.md': ['历史静置仓反向扫描硬闸', 'dormant_warehouse_audit.json', 'strict/expanded/excluded'],
    }
    for rel, needles in method_contracts.items():
        text = open(os.path.join(ROOT, rel), encoding='utf-8').read()
        for needle in needles:
            if needle not in text:
                fails.append(f'方法硬闸回退 {rel}: 缺少 {needle}')

    # 6) 控盘主口径必须跨工作流、判级、报告和专册四层一致：成员表排除设施，
    #    不等于设施内可证权益不计入实体经济控制。
    control_contracts = {
        'SKILL.md': ['控盘看最终经济控制', 'economic_control_ledger.json', '公共设施不进永久成员表'],
        'references/economic-control-accounting.md': ['实体成员表', '链上位置账', '经济控制账', 'unresolved_facility_exposure'],
        'references/playbook-entity-cluster-tiering.md': ['判级的"持仓"强制解释为可证经济控制量', '严格/扩展是确权边界'],  # c2.0：needle 随 v5 判级口径迁移（P0/P1 废止）
        'references/report-template.md': ['经济控制穿透硬闸', 'economic_control_ledger.json', '不得拿钱包自持替代'],
    }
    for rel, needles in control_contracts.items():
        text = open(os.path.join(ROOT, rel), encoding='utf-8').read()
        for needle in needles:
            if needle not in text:
                fails.append(f'经济控制口径回退 {rel}: 缺少 {needle}')

    # 7) EF-3 覆盖发现闸是名册定稿前硬闸；稳定编号替代层级含混的
    #    “三道防线/四重前置”口号，路由/工作流/契约/判例任一缺失＝回退。
    wave_contracts = {
        'SKILL.md': ['EF-3 覆盖发现闸', 'EF-3A 波次扫描', 'EF-3B 资金流异常扫描',
                     'EF-3C 候选裁决与实体溯源', 'EF-3C-P1', 'P4 原始输入及算法绑定重放'],
        'references/analyze-workflow.md': ['EF-3A 全体持仓波次扫描', 'EF-3B 资金流异常扫描',
                                           'EF-3C 候选裁决与实体溯源', 'entity_source_trace.py',
                                           'adjudication_validator.py', '覆盖真空声明', 'EF-3C-P1'],
        'references/split-run.md': ['wave_scan_report.json', 'flow_anomaly_report.json',
                                    'EF-3A/EF-3B', 'EF-3C', 'EF-3C-P1～P4',
                                    'provenance_ledger.json'],
        'references/casebook/supply-accounting.md': ['wave_scan.py', '桶存在≠桶内被检验过',
                                                     '闸外的人来试着绕它'],
        'references/scan-schemas.md': ['wave-scan/v3', 'flow-anomaly/v2',
                                       'candidate-adjudications/v1', 'provenance-ledger/v2',
                                       '正向模拟', 'members_sha256', '完整字段登记',
                                       'scan_universe', 'must_adjudicate'],
    }
    for rel, needles in wave_contracts.items():
        text = open(os.path.join(ROOT, rel), encoding='utf-8').read()
        for needle in needles:
            if needle not in text:
                fails.append(f'EF-3 覆盖发现闸回退 {rel}: 缺少 {needle}')

    # 8) 同时性家族合并与"恒定滞后"判据删除（2026-08-02 用户裁决，v6.12.0）：
    #    在场检查=家族三档、②降级措辞、持仓画像旁证与候选发现档不得回退；
    #    不在场检查=已删的"恒定滞后=跟单"伪判据（庄程序按序遍历同样产生该形态，两可无判别力）
    #    不得从旧案考古回捡进活跃规则（CHANGELOG 记录删除理由，不在禁扫范围）。
    simult_contracts = {
        'references/playbook-entity-cluster-methods.md': ['同时性共现（同秒/同块）家族', '① 候选发现档',
                                                          '② 单币强指纹档', '③ 跨币强证据档',
                                                          '高度疑似同一执行端', '持仓画像旁证'],
    }
    for rel, needles in simult_contracts.items():
        text = open(os.path.join(ROOT, rel), encoding='utf-8').read()
        for needle in needles:
            if needle not in text:
                fails.append(f'同时性家族回退 {rel}: 缺少 {needle}')
    simult_banned = {
        'references/playbook-entity-cluster-methods.md': ['程序化跟单不是同一人'],
    }
    for rel, needles in simult_banned.items():
        text = open(os.path.join(ROOT, rel), encoding='utf-8').read()
        for needle in needles:
            if needle in text:
                fails.append(f'已删判据回捡 {rel}: 出现 {needle}')

    # 9) 2026-08-04 一致性复核的语义守护。只扫活跃权威文档/代码，CHANGELOG
    #    的历史原文不在禁扫范围。
    semantic_contracts = {
        'SKILL.md': ['Arbitrum 仅保留探索支持', '三问一异常',
                     'A3 实体冻结门禁编号', '链内 collection_manifest/receipt'],
        'references/independent-audit-protocol.md': ['--profile new-analysis',
                                                      '--profile independent-audit',
                                                      'id、规范化文本、最终 verdict、证据文件集合和报告位置',
                                                      'CHIP_REPRODUCE_OUTPUT',
                                                      '存量 reproduce-receipt/v1 迁移',
                                                      '不得原地升级', 'adversarial-review-execution/v1',
                                                      '案目录里的同名/复制脚本', '无 producer 的 accounting'],
        'references/report-template.md': ['state_from_facts.py', '--mode analysis-new',
                                           '--mode analysis-audit', 'a4-seal/v4', 'ET-1/ET-2'],
        'references/analyze-workflow.md': ['Arbitrum（探索）', 'identity_gate_v3', '--snapshot-receipt',
                                           '--total-supply-raw', 'a4-seal/v4',
                                           '不得手工补字段', 'GPA raw/meta', '跨 scan pubkey 去重函数',
                                           '既有采集产物复用', 'data/v2/run_*/done.json',
                                           'data/soltx-*.jsonl.gz', 'done_with_gaps',
                                           'collection_manifest.json'],
        'references/data-pipeline-evm-channels.md': ['evm-channel-receipt/v2',
                                                      'evm-collector-run/v2',
                                                      '--collector-receipt',
                                                      '--resume-receipt',
                                                      '存量 legacy CSV', 'channels_preflight.py` producer',
                                                      '完全相同的 inputs', '不能把两份互相咬合的 JSON'],
        'references/data-pipeline-solana-capture.md': ['免费层不支持 batch', '10 RPS'],
        'references/data-pipeline-solana-scan.md': ['G8 离线重放契约', 'parse_gpa_response',
                                                    'result.value.amount', '禁止手补 meta/hash'],
        'references/analysis-playbook.md': ['三问一异常'],
        'commands-staging/token-analyze.md': ['三问一异常'],
        'commands-staging/token-analyze-2.md': ['三问一异常'],
    }
    for rel, needles in semantic_contracts.items():
        text = open(os.path.join(ROOT, rel), encoding='utf-8').read()
        for needle in needles:
            if needle not in text:
                fails.append(f'2026-08-04 语义口径回退 {rel}: 缺少 {needle}')

    distribution_contracts = {
        'references/scan-schemas.md': ['distribution-scan/v1', 'distribution-explanation/v1',
                                       'distribution-adjudications/v1', 'pattern-resolutions/v1',
                                       'distribution-rounds/v1', 'distribution-exception-receipt/v1',
                                       'Holm-Bonferroni', 'launch_covered=false'],
        'references/analyze-workflow.md': ['当前持仓分布初判', '当前持仓分布终判环',
                                           'a5-report-seal/v2', 'G11'],
        'references/split-run.md': ['distribution_scan.json', 'handoff/v3',
                                    'holder_distribution_current.png', 'a4-seal/v4'],
        'references/report-template.md': ['holder_distribution_current.png',
                                           '形态统计因样本不足未做', '分布发布闸（G11）'],
    }
    for rel, needles in distribution_contracts.items():
        text = open(os.path.join(ROOT, rel), encoding='utf-8').read()
        for needle in needles:
            if needle not in text:
                fails.append(f'持仓分布硬闸口径回退 {rel}: 缺少 {needle}')

    banned_contracts = {
        'SKILL.md': ['对任意链上代币', 'v5.0 三问框架', '实体冻结前三硬闸'],
        'references/report-template.md': ['手写 15 行', 'a4-seal/v2'],
        'references/data-pipeline-evm-channels.md': ['evm-channel-receipt/v1',
                                                      '--empty-proof'],
        'references/analysis-playbook.md': ['三问框架'],
        'commands-staging/token-analyze.md': ['三问框架'],
        'commands-staging/token-analyze-2.md': ['三问框架'],
        'scripts/solana/decode_txs_v2.py': ['默认 20 笔/POST', '[--batch 20]', '免代理且 50 RPS'],
    }
    for rel, needles in banned_contracts.items():
        text = open(os.path.join(ROOT, rel), encoding='utf-8').read()
        for needle in needles:
            if needle in text:
                fails.append(f'2026-08-04 已删口径回捡 {rel}: 出现 {needle}')

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
