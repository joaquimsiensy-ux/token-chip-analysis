#!/usr/bin/env python3
"""文档守护：引用断链 + 粗体配对 + SKILL.md 引用漂移哨。

背景：追加式迭代下文档互引会漂移（实证：SKILL.md 曾写 labels "v4 ~46.9 万条"而实际已 v4.2 ~47.1 万；
labels README 曾宣称 filecoin 接入 resolver 与事实不符）。本脚本抓"结构可查"的那部分：
1. md 里引用的本仓库文件路径必须存在（references/*.md、scripts/**.py、labels/*.csv|md）
2. 每行 ** 配对（奇数个 ** 的行=残缺粗体，渲染会烂）
3. SKILL.md「深入阅读」列出的文件必须齐全
4. 关键方法硬闸必须同时出现在工作流、方法、判级和报告验收四层，防规则只写在角落而实际被跳过
复盘写入后必跑（retrospective 步骤 3）；整编触发条件之一=本脚本抓出漂移 ≥3 处。

用法：python3 scripts/tests/docs_lint.py [--all]    退出码：0=PASS；1=FAIL。
  --all＝全量模式（v6.3.1）：额外纳入 commands-staging/*.md 与 evals/**/*.md——
  此前 44/66 文档的覆盖盲区（"三查→四查""SKILL.md 阶段 N"类漂移在这两处存活过）。
"""
import glob, os, re, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# 引用模式：仓库内相对路径（含 ` 包裹或裸写两种）；排除占位符 <chain> 与缩写 ...
REF_RE = re.compile(r'(?<![\w/~])(?:references/[\w./-]+\.(?:md|csv|png)|scripts/[\w./-]+\.(?:py|sh)|labels/[\w.-]+\.(?:md|csv))')
# 负向后顾排除长路径尾段（如 ~/Desktop/xx/scripts/chip_analysis.py 的历史出处说明——那不是仓库内引用）

def md_files(all_mode=False):
    out = [os.path.join(ROOT, 'SKILL.md'), os.path.join(ROOT, 'CHANGELOG.md')]
    out += sorted(glob.glob(os.path.join(ROOT, 'references', '**', '*.md'), recursive=True))
    out += sorted(glob.glob(os.path.join(ROOT, 'scripts', '**', 'README.md'), recursive=True))
    if all_mode:
        out += sorted(glob.glob(os.path.join(ROOT, 'commands-staging', '*.md')))
        out += sorted(glob.glob(os.path.join(ROOT, 'evals', '**', '*.md'), recursive=True))
    return [p for p in out if os.path.exists(p)]

def resolve(ref, src_path):
    """引用相对 skill 根、references/、或引用文件所在目录三种基准都试。"""
    cands = [os.path.join(ROOT, ref),
             os.path.join(ROOT, 'references', ref),
             os.path.join(os.path.dirname(src_path), ref)]
    return any(os.path.exists(c) for c in cands)

def main(all_mode=False):
    fails = []
    warn_broken = 0
    for path in md_files(all_mode):
        rel = os.path.relpath(path, ROOT)
        in_code = False
        for i, line in enumerate(open(path, encoding='utf-8'), 1):
            if line.strip().startswith('```'):
                in_code = not in_code
                continue
            if in_code:
                continue
            # 1) 断链
            for ref in REF_RE.findall(line):
                if '<' in ref or '...' in ref or '*' in ref:
                    continue
                if not resolve(ref, path):
                    fails.append(f'断链 {rel}:{i} → {ref}')
                    warn_broken += 1
            # 2) 粗体配对（该行 ** 计数应为偶数）
            if line.count('**') % 2 == 1:
                fails.append(f'残缺粗体 {rel}:{i}: {line.strip()[:60]}')
    # 3) SKILL.md 深入阅读清单齐全性
    skill = open(os.path.join(ROOT, 'SKILL.md'), encoding='utf-8').read()
    for name in re.findall(r'^- `([\w/.-]+\.md)`', skill, re.M):
        if not (os.path.exists(os.path.join(ROOT, 'references', name)) or os.path.exists(os.path.join(ROOT, name))):
            fails.append(f'SKILL.md 深入阅读清单断链: {name}')
    # 4) 反向漏列：references/ 顶层与 labels/ 的 md 都必须出现在 SKILL.md（v3.3：robinhood 曾漏列，
    #    正向断链检查抓不到"存在但没列"）
    should_list = sorted(glob.glob(os.path.join(ROOT, 'references', '*.md'))) \
                + sorted(glob.glob(os.path.join(ROOT, 'references', 'labels', '*.md')))
    for p in should_list:
        base = os.path.relpath(p, os.path.join(ROOT, 'references'))  # 如 labels/README.md
        if base not in skill and os.path.basename(p) not in skill:
            fails.append(f'SKILL.md 深入阅读清单漏列: references/{base}')

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
    #    在场检查=家族三档、②降级措辞、持仓画像旁证与 update-workflow 新指称不得回退；
    #    不在场检查=已删的"恒定滞后=跟单"伪判据（庄程序按序遍历同样产生该形态，两可无判别力）
    #    不得从旧案考古回捡进活跃规则（CHANGELOG 记录删除理由，不在禁扫范围）。
    simult_contracts = {
        'references/playbook-entity-cluster-methods.md': ['同时性共现（同秒/同块）家族', '① 候选发现档',
                                                          '② 单币强指纹档', '③ 跨币强证据档',
                                                          '高度疑似同一执行端', '持仓画像旁证'],
        'references/update-workflow.md': ['同时性共现家族①候选发现档'],
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
        'SKILL.md': ['restricted/top-200-windowed', 'Arbitrum', '三问一异常',
                     'A3 实体冻结门禁编号', '队列层 collect_manifest',
                     '链内 collection_manifest/receipt'],
        'references/independent-audit-protocol.md': ['--profile new-analysis',
                                                      '--profile independent-audit',
                                                      'id、规范化文本、最终 verdict、证据文件集合和报告位置',
                                                      'CHIP_REPRODUCE_OUTPUT',
                                                      '存量 reproduce-receipt/v1 迁移',
                                                      '不得原地升级', 'adversarial-review-execution/v1',
                                                      '案目录里的同名/复制脚本', '无 producer 的 accounting'],
        'references/report-template.md': ['state_from_facts.py', '--mode analysis-new',
                                           '--mode analysis-audit', 'a4-seal/v3', 'ET-1/ET-2'],
        'references/analyze-workflow.md': ['identity_gate_v3', '--snapshot-receipt',
                                           '--total-supply-raw', 'a4-seal/v3',
                                           '不得手工补字段', 'GPA raw/meta', '跨 scan pubkey 去重函数'],
        'references/data-pipeline-filecoin.md': ['restricted/top-200-windowed', 'f00–f0160',
                                                  'richlist_pagination_receipt.json'],
        'references/data-pipeline-evm-channels.md': ['evm-channel-receipt/v2',
                                                      'evm-collector-run/v2',
                                                      '--collector-receipt',
                                                      '--resume-receipt',
                                                      '存量 legacy CSV', 'channels_preflight.py` producer',
                                                      '完全相同的 inputs', '不能把两份互相咬合的 JSON'],
        'references/data-pipeline-solana-capture.md': ['免费层不支持 batch', '10 RPS'],
        'references/data-pipeline-solana-scan.md': ['G8 离线重放契约', 'parse_gpa_response',
                                                    'result.value.amount', '禁止手补 meta/hash'],
        'references/address-book.md': ['f00`–`f0160'],
        'references/playbook-entity-cluster-methods.md': ['f00–f0160'],
        'references/labels/MAINTENANCE.md': ['f00–f0160'],
        'references/analysis-playbook.md': ['三问一异常'],
        'commands-staging/token-analyze.md': ['三问一异常'],
        'commands-staging/token-analyze-2.md': ['三问一异常'],
    }
    for rel, needles in semantic_contracts.items():
        text = open(os.path.join(ROOT, rel), encoding='utf-8').read()
        for needle in needles:
            if needle not in text:
                fails.append(f'2026-08-04 语义口径回退 {rel}: 缺少 {needle}')

    banned_contracts = {
        'SKILL.md': ['对任意链上代币', 'v5.0 三问框架', '实体冻结前三硬闸'],
        'references/report-template.md': ['手写 15 行', 'a4-seal/v2'],
        'references/data-pipeline-filecoin.md': ['f00–f0126', '浏览器 API 准全量'],
        'references/data-pipeline-evm-channels.md': ['evm-channel-receipt/v1',
                                                      '--empty-proof'],
        'references/address-book.md': ['f0126'],
        'references/playbook-entity-cluster-methods.md': ['f0126'],
        'references/labels/MAINTENANCE.md': ['f0126'],
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
                        'references/easy-workflow.md', 'references/report-template.md',
                        'references/split-run.md']
    generic_mode = re.compile(r'--mode analysis(?=[\s`])')
    for rel in active_workflows:
        text = open(os.path.join(ROOT, rel), encoding='utf-8').read()
        if generic_mode.search(text):
            fails.append(f'2026-08-04 generic analysis 模式回退 {rel}')

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
