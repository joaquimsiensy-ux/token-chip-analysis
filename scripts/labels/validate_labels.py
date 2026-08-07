#!/usr/bin/env python3
"""标签库 CSV 卫生与一致性校验器（v4 2026-07-16，codex 交叉复核第二轮融合）

用法：
  python3 validate_labels.py <目录>      # 校验目录下全部 labels-*.csv（构建器自动调用 out/）
  python3 validate_labels.py             # 默认校验 references/labels/（现库体检）

检查项（FAIL 任一项即 exit 1）：
  1. 文件 UTF-8 可解码、无 NUL/控制字符
  2. 表头 = v3 基础 9 列，或 v4 扩展列（基础 9 列 + merge_policy/balance_policy/
     source_snapshot_at/verified_at/status/raw_labels 的前缀子集）
  3. 地址格式按链校验（与 labels_resolver.norm_addr 同一逻辑，要求已规范化）
  4. (chain,address) 无重复
  5. tier ∈ {exclude, identity, risk}；category 非空
  6. burn 类不带任何 risk_flags；exclude 类不带行为型旗标（tornado-user）
  7. tier=risk 行必须有 risk_flags 与 evidence
  8. 【v4】risk_flags 白名单制：任何旗标必须可分类为 definitive/candidate/privacy，
     白名单外旗标 = FAIL（入库前先扩 labels_resolver 白名单，禁止未知旗标带病入库）
  9. 【v4】merge_policy/balance_policy 若非空必须是合法值
 10. 【v4】category=serial-actor 行必须有 evidence（惯犯指控必须带案源证据）
另输出行数概览（对比上版靠人工判断，行数突变见 stdout 警告）。
"""
import csv, glob, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from labels_resolver import (BASE_FIELDS, V4_OPTIONAL_FIELDS, norm_addr,
                             _classify_flag, SERIAL_CATEGORY)
from risk_flags import canonical_risk_flags, parse_risk_flags

TIERS = {'exclude', 'identity', 'risk'}
BEHAVIORAL_FLAGS = {'tornado-user'}
MERGE_VALUES = {'', 'allow', 'no_merge'}
BALANCE_VALUES = {'', 'count', 'bucket', 'exclude'}
# ---- v4.2 不变量（codex 第四轮复核后固化：让机器守住已发现的错误模式） ----
STATUS_VALUES = {'', 'historical'}                      # 11. status 枚举（曾漏进错位日期值）
FACILITY_MUST_EXCLUDE = {'cex', 'bridge', 'router', 'mixer', 'bot-service'}  # 12. 设施类目≠identity
AA_NAME_RE = re.compile(r'\b(bundler|paymaster|entry ?point)\b|erc-?4337', re.I)  # 13. AA 设施必须 exclude
SUSPECT_NAME_RE = re.compile(r'疑似|未确证|unverified|unconfirmed', re.I)  # 14. 未确证不得 exclude


def _valid_header(header):
    if header == BASE_FIELDS:
        return True
    # v4：基础列后接可选列的前缀子集（允许只加前 N 个可选列）
    if header[:len(BASE_FIELDS)] != BASE_FIELDS:
        return False
    extra = header[len(BASE_FIELDS):]
    return extra == V4_OPTIONAL_FIELDS[:len(extra)]


def validate_file(path, *, strict_canonical=None):
    errs, warns = [], []
    if strict_canonical is None:
        active = os.path.abspath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', '..',
            'references', 'labels'))
        strict_canonical = os.path.abspath(os.path.dirname(path)) != active
    chain = os.path.basename(path).replace('labels-', '').replace('.csv', '')
    if chain.endswith('-privacy'):
        chain = chain[:-len('-privacy')]
    raw = open(path, 'rb').read()
    if b'\x00' in raw:
        errs.append(f'含 {raw.count(b"\x00")} 个 NUL 字节')
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as e:
        errs.append(f'非 UTF-8: {e}')
        return errs, warns, 0
    ctrl = len(re.findall(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', text))
    if ctrl:
        errs.append(f'含 {ctrl} 个控制字符')
    reader = csv.DictReader(text.splitlines())
    header = reader.fieldnames or []
    rows = list(reader)
    # 空文件/只有表头的文件也必须经过 schema gate，不能靠“没有数据行”绕过。
    if not _valid_header(header):
        errs.append(f'表头异常: {header}')
    seen = set()
    for i, r in enumerate(rows, 2):
        a = r.get('address') or ''
        na = norm_addr(a, chain)
        if na != a:
            errs.append(f'行{i} 地址格式错(chain={chain}，须已规范化): {a[:50]}')
        if a in seen:
            errs.append(f'行{i} 重复地址: {a}')
        seen.add(a)
        if r.get('tier') not in TIERS:
            errs.append(f'行{i} 非法 tier: {r.get("tier")}')
        cat = (r.get('category') or '').strip()
        if not cat:
            errs.append(f'行{i} category 为空: {a}')
        raw_flags = r.get('risk_flags') or ''
        flags = list(parse_risk_flags(raw_flags))
        canonical_flags = canonical_risk_flags(raw_flags)
        if raw_flags != canonical_flags:
            message = (f'行{i} risk_flags 非 canonical（读取按 {canonical_flags!r} '
                       f'解释；新写入须规范化）: {a}')
            (errs if strict_canonical else warns).append(message)
        if cat == 'burn' and flags:
            errs.append(f'行{i} burn 地址带 risk_flags({r["risk_flags"]}): {a}')
        if r.get('tier') == 'exclude' and (set(flags) & BEHAVIORAL_FLAGS):
            errs.append(f'行{i} exclude 设施带行为旗标({r["risk_flags"]}): {a}')
        if r.get('tier') == 'risk':
            if not flags:
                errs.append(f'行{i} tier=risk 无 risk_flags: {a}')
            if not (r.get('evidence') or '').strip():
                errs.append(f'行{i} tier=risk 无 evidence: {a}')
        for f in flags:
            if _classify_flag(f) == 'unknown':
                errs.append(f'行{i} 白名单外旗标 "{f}"（先扩 labels_resolver 白名单再入库）: {a}')
        if (r.get('merge_policy') or '') not in MERGE_VALUES:
            errs.append(f'行{i} 非法 merge_policy: {r.get("merge_policy")}')
        if (r.get('balance_policy') or '') not in BALANCE_VALUES:
            errs.append(f'行{i} 非法 balance_policy: {r.get("balance_policy")}')
        if cat == SERIAL_CATEGORY and not (r.get('evidence') or '').strip():
            errs.append(f'行{i} serial-actor 无 evidence（惯犯指控必须带案源）: {a}')
        # ---- v4.2 不变量 11-14 ----
        if (r.get('status') or '') not in STATUS_VALUES:
            errs.append(f'行{i} 非法 status "{r.get("status")}"（枚举: 空/historical）: {a}')
        nm = r.get('name') or ''
        if cat in FACILITY_MUST_EXCLUDE and r.get('tier') == 'identity':
            errs.append(f'行{i} 设施类目 {cat} 却 tier=identity（会参与聚类/持仓）: {a} {nm[:30]}')
        if AA_NAME_RE.search(nm) and r.get('tier') != 'exclude' and cat not in (
                'token-contract', 'kol', 'smart-money', 'serial-actor', 'validator'):
            errs.append(f'行{i} AA 设施（bundler/paymaster/EntryPoint）未 exclude: {a} {nm[:40]}')
        if SUSPECT_NAME_RE.search(nm) and r.get('tier') == 'exclude':
            errs.append(f'行{i} 未确证条目（name 含"疑似/未确证"）不得 exclude——用 no_merge+count: {a} {nm[:40]}')
        if len(errs) > 30:
            errs.append('…(错误过多截断)')
            break
    return errs, warns, len(rows)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.normpath(
        os.path.join(here, '..', '..', 'references', 'labels'))
    files = sorted(glob.glob(os.path.join(target, 'labels-*.csv')))
    if not files:
        print(f'FAIL: {target} 下无 labels-*.csv'); sys.exit(1)
    total_errs = 0
    for p in files:
        errs, warns, n = validate_file(p)
        st = 'OK ' if not errs else 'FAIL'
        print(f'[{st}] {os.path.basename(p)}: {n} 行' + (f' | {len(errs)} 项错误' if errs else ''))
        for e in errs[:15]:
            print(f'    - {e}')
        for warning in warns[:15]:
            print(f'    [WARN] {warning}')
        total_errs += len(errs)
    if total_errs:
        print(f'\n校验未通过：共 {total_errs} 项错误'); sys.exit(1)
    print('\n全部通过')

if __name__ == '__main__':
    main()
