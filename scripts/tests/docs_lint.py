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
        'SKILL.md': ['历史静置仓反向扫描硬闸', 'dormant_warehouse_audit.json', '不允许冻结实体'],
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

    # 7) 三道互补防线是名册定稿前硬闸（W1 两度漏检 2026-08-01；v6.8.1 codex 验收返工版）；
    #    路由/工作流/契约/判例四层任一缺失＝方法回退。
    wave_contracts = {
        'SKILL.md': ['三道互补防线硬闸', 'wave_scan_report.json', 'flow_anomaly_report.json',
                     'entity_source_trace.py', '成员级裁决闭环', '四重前置'],
        'references/analyze-workflow.md': ['wave_scan.py', 'flow_anomaly_scan.py',
                                           'entity_source_trace.py', 'adjudication_validator.py',
                                           '兜底桶不准关闸', '覆盖真空声明', '正向模拟'],
        'references/split-run.md': ['wave_scan_report.json', 'flow_anomaly_report.json',
                                    '候选裁决闭环', '溯源闸', 'provenance_ledger.json',
                                    '四重前置', '--entity-file'],
        'references/casebook/supply-accounting.md': ['wave_scan.py', '桶存在≠桶内被检验过',
                                                     '闸外的人来试着绕它'],
        'references/scan-schemas.md': ['wave-scan/v3', 'flow-anomaly/v1',
                                       'candidate-adjudications/v1', 'provenance-ledger/v2',
                                       '正向模拟', 'members_sha256', '完整字段登记',
                                       'scan_universe', 'must_adjudicate'],
    }
    for rel, needles in wave_contracts.items():
        text = open(os.path.join(ROOT, rel), encoding='utf-8').read()
        for needle in needles:
            if needle not in text:
                fails.append(f'三道防线硬闸回退 {rel}: 缺少 {needle}')

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
