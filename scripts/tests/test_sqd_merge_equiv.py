#!/usr/bin/env python3
"""fetch_sqd_transfers_v2 收尾合并 + 伪 scan-fail 判定的离线守护（2026-07-26 两处缺陷修复的活体门禁）。

覆盖七条契约：
  1. 两条收尾路径（全内存 / DuckDB 磁盘外排）产物**逐字节一致**——按
     (slot, tx_index) 交易身份去重、超 int64 金额（10^19）、同 slot 多交易、ts=0
  2. 超 int64 金额全程保真（任何数值 CAST 都会溢出/失真）
  3. 路径选择：估算行数超阈值才降级外排，否则全内存（历史行为）
  4. 原子落盘：写入中途异常不留下半截 gz（旧版 OOM 落在写 gz 中途会毁缓存触发全量重扫）
  5. 伪 scan-fail 判定：零行 + 跨度 ≤ EMPTY_MAX → 判完成；跨度超闸门时以块探针实证定夺
  6. scan_area 集成：尾段零行响应 → finished=True 且 done_to=to（旧版返回 False→记 gaps）

无网络（HTTP 全 mock）、无外部服务；缺 duckdb 时自动跳过外排相关契约。
用法：python3 scripts/tests/test_sqd_merge_equiv.py    退出码 0=PASS / 1=FAIL
"""
import gzip, importlib.util, json, os, sys, tempfile
from pathlib import Path

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SCRIPT = os.path.join(ROOT, 'scripts', 'solana', 'fetch_sqd_transfers_v2.py')

_spec = importlib.util.spec_from_file_location('sqd_v2', SCRIPT)
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

ZERO = M.ZERO
BIG = 10 ** 19                       # BONK 创世铸造边量级：超 int64 上限
HUGE = 123456789012345678901234567890


def _mk(d, parts_rows, old_rows):
    """造 parts（紧凑格式）+ 旧缓存 gz（默认带空格格式）→ (cache_fp, parts_dir, part_files)。"""
    data = Path(d) / 'data'
    parts_dir = data / 'soltx-x.parts'
    parts_dir.mkdir(parents=True)
    cache_fp = data / 'soltx-x.jsonl.gz'
    files = []
    for i, chunk in enumerate(parts_rows):
        fp = parts_dir / f'{i}.jsonl'
        fp.write_text(''.join(json.dumps(r, separators=(',', ':')) + '\n' for r in chunk))
        files.append(fp)
    if old_rows is not None:
        with gzip.open(cache_fp, 'wt') as f:
            for r in old_rows:
                f.write(json.dumps(r) + '\n')
    return cache_fp, parts_dir, sorted(files)


# v4 7 元组。tx=(101,0) 的完整边集同时出现在 part 与旧 gz，必须按交易身份留一份；
# tx=(101,1) 内容与其中一条边同 owner 但金额不同，是同 slot 的另一笔真实交易，必须保留。
PARTS = [[[0, 100, 0, -1, ZERO, 'AAA', BIG],
          [1700000000, 101, 0, -1, 'AAA', 'BBB', 5],
          [1700000000, 101, 0, -1, 'BBB', 'CCC', 7],
          [1700000000, 101, 0, -1, 'AAA', 'BBB', 5]],   # 同 source 重复行
         [[1699999999, 99, 0, -1, 'CCC', ZERO, HUGE],
          [1700000000, 101, 1, -1, 'AAA', 'BBB', 9],
          [1700000001, 102, 0, -1, 'DDD', 'EEE', 1]]]
OLD = [[1700000000, 101, 0, -1, 'AAA', 'BBB', 5],
       [1700000000, 101, 0, -1, 'BBB', 'CCC', 7],
       [1699999998, 98, 0, -1, 'EEE', 'FFF', 42]]


def c1_c2_equivalence():
    """契约 1+2：两条收尾路径逐字节一致 + 大数保真。"""
    if M.duckdb is None:
        print('SKIP: 无 duckdb，跳过外排等价性（契约 1/2/3-外排）')
        return True, None
    out = {}
    for name, cls in (('inmem', M.MemMerger), ('ext', M.ExtMerger)):
        with tempfile.TemporaryDirectory() as d:
            cache_fp, parts_dir, files = _mk(d, PARTS, OLD)
            res = cls(cache_fp, parts_dir, files, True).finalize()
            out[name] = (gzip.open(cache_fp, 'rb').read(), res)
    same = out['inmem'][0] == out['ext'][0]
    body = out['inmem'][0].decode()
    ok = same
    if not same:
        print('FAIL: 两条收尾路径产物不一致')
        print('  inmem:', out['inmem'][0].decode().splitlines())
        print('  ext  :', out['ext'][0].decode().splitlines())
    for k in ('rows', 'has_mint', 'min_ts'):
        if out['inmem'][1][k] != out['ext'][1][k]:
            print(f'FAIL: 统计字段 {k} 不一致 {out["inmem"][1][k]} vs {out["ext"][1][k]}')
            ok = False
    # 输入 10 条，tx=(101,0) 跨 source 重复且组内有重复行 → 交易身份去重后 7 条边
    if out['inmem'][1]['rows'] != 7:
        print(f'FAIL: 去重后行数 {out["inmem"][1]["rows"]} ≠ 7（交易身份去重失效？）')
        ok = False
    if str(BIG) not in body or str(HUGE) not in body:
        print('FAIL: 超 int64 金额未保真（被数值 CAST 溢出/失真）')
        ok = False
    # (slot, ts) 主序单调
    slots = [json.loads(l)[1] for l in body.splitlines() if l.strip()]
    if slots != sorted(slots):
        print(f'FAIL: 未按 slot 排序 {slots}')
        ok = False
    if ok:
        print(f'PASS: 契约1+2 两路径逐字节一致（{len(slots)} 行，大数保真，slot 单调）')
    return ok, body


def c1a_distinct_poison():
    """T1a 原反例：同 slot 等额不同 tx_index 不能被五字段 DISTINCT 吃掉。"""
    def rec(ti, account, owner, pre, post):
        return {"transactionIndex": ti, "account": account,
                "preMint": "MINT", "postMint": "MINT",
                "preOwner": owner, "postOwner": owner,
                "preAmount": str(pre), "postAmount": str(post)}

    block = {"header": {"number": 101, "timestamp": 1700000000},
             "transactions": [{"transactionIndex": 1, "err": None},
                              {"transactionIndex": 2, "err": None}],
             "tokenBalances": [rec(1, "acct-a1", "AAA", 5, 0),
                               rec(1, "acct-b1", "BBB", 0, 5),
                               rec(2, "acct-a2", "AAA", 5, 0),
                               rec(2, "acct-b2", "BBB", 0, 5)]}
    fx, _ = _fx([_FakeResp(200, json.dumps(block) + '\n')])
    edges, done_to, finished = fx.scan_area(101, 101, deadline=M.time.time() + 60)
    with tempfile.TemporaryDirectory() as d:
        cache_fp, parts_dir, files = _mk(d, [], None)
        merger = M.MemMerger(cache_fp, parts_dir, files, False)
        merger.absorb(edges)
        result = merger.finalize()
        body = gzip.open(cache_fp, 'rt').read().splitlines() if cache_fp.exists() else []
    if not finished or done_to != 101 or result["rows"] != 2:
        print("FAIL: T1a DISTINCT 吃边仍存在：同 slot 等额不同 tx_index 未保留 2 笔"
              f"（finished={finished} done_to={done_to} rows={result['rows']} body={body}）")
        return False
    parsed = [json.loads(line) for line in body]
    if {row[2] for row in parsed} != {1, 2}:
        print(f"FAIL: T1a 产物缺失交易身份 tx_index: {parsed}")
        return False
    print("PASS: T1a 同 slot 等额不同 tx_index 保留 2 笔")
    return True


def c1b_identity_conflict_and_width():
    """T1b/c：同身份同 digest 留一，异 digest 与旧/混合行宽必须硬失败。"""
    ok = True
    same = [1700000000, 200, 7, -1, "AAA", "BBB", 5]
    conflict = [1700000000, 200, 7, -1, "AAA", "BBB", 6]
    old5 = [1700000000, 200, "AAA", "BBB", 5]
    cases = (
        ("同交易身份异 digest", [[same], [conflict]]),
        ("旧 5 元组", [[old5]]),
        ("5/7 混合行宽", [[same, old5]]),
    )
    for label, part_rows in cases:
        with tempfile.TemporaryDirectory() as d:
            cache_fp, parts_dir, files = _mk(d, part_rows, None)
            try:
                M.MemMerger(cache_fp, parts_dir, files, False).finalize()
            except (TypeError, ValueError, RuntimeError):
                pass
            else:
                print(f"FAIL: {label} 未 fail-closed")
                ok = False
    if ok:
        print("PASS: T1b/c 同身份异 digest 与旧/混合行宽均硬失败")
    return ok


def c3_route():
    """契约 3：按预估规模选路径。"""
    ok = True
    with tempfile.TemporaryDirectory() as d:
        cache_fp, parts_dir, files = _mk(d, PARTS, OLD)
        m, est = M.make_merger(cache_fp, parts_dir, files, True, 2, 10 ** 9)
        if m.mode != 'inmem':
            print(f'FAIL: 小样本应走全内存，实走 {m.mode}'); ok = False
        m2, est2 = M.make_merger(cache_fp, parts_dir, files, True, 2, 1)
        want = 'duckdb-external' if M.duckdb is not None else 'inmem'
        if m2.mode != want:
            print(f'FAIL: 超阈值应走 {want}，实走 {m2.mode}'); ok = False
        if est <= 0:
            print(f'FAIL: 行数估算异常 {est}'); ok = False
    if ok:
        print(f'PASS: 契约3 路径选择正确（估算 {est} 行；阈值内=inmem / 超阈值={want}）')
    return ok


def c4_atomic():
    """契约 4：写入中途异常不留下半截 gz，原有缓存不被破坏。"""
    ok = True
    with tempfile.TemporaryDirectory() as d:
        cache_fp, parts_dir, files = _mk(d, PARTS, OLD)
        before = gzip.open(cache_fp, 'rb').read()

        def boom():
            yield json.dumps([1, 2, 'A', 'B', 3])
            raise MemoryError('模拟收尾 OOM')

        try:
            M._atomic_gz(cache_fp, boom())
            print('FAIL: 异常未透传'); ok = False
        except MemoryError:
            pass
        if gzip.open(cache_fp, 'rb').read() != before:
            print('FAIL: 原缓存被半截写入破坏'); ok = False
        leftovers = list(cache_fp.parent.glob('*.tmp'))
        if leftovers:
            print(f'FAIL: 残留临时文件 {leftovers}'); ok = False
    if ok:
        print('PASS: 契约4 原子落盘（中途 OOM 既不毁旧缓存也不留残件）')
    return ok


class _FakeResp:
    def __init__(self, status=200, text=''):
        self.status_code, self.text = status, text

    def iter_lines(self, decode_unicode=True):
        for ln in self.text.splitlines():
            yield ln

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeSess:
    """按调用序返回预置响应；记录每次请求体供断言。"""
    def __init__(self, seq):
        self.seq, self.calls = list(seq), []

    def post(self, url, **kw):
        self.calls.append(kw.get('json'))
        return self.seq.pop(0) if self.seq else _FakeResp(200, '')


def _fx(seq, empty_max=M.EMPTY_MAX):
    fx = M.Fetcher(M.DEF_URL, 'MINT', None, M.TokenBucket(1000), 1, empty_max=empty_max)
    sess = _FakeSess(seq)
    fx._sess = lambda: sess
    return fx, sess


def c5_empty_ok():
    """契约 5：零行判定——窄区间免探针放行；宽区间由块探针定夺。"""
    ok = True
    fx, _ = _fx([])
    if not fx._empty_ok(1000, 1000 + M.EMPTY_MAX - 1):
        print('FAIL: 跨度 = EMPTY_MAX 应免探针判完成'); ok = False
    # 宽区间 + 探针查到块 → 不放行（服务端过滤路径异常）
    fx2, s2 = _fx([_FakeResp(200, '{"header":{"number":2000}}')])
    if fx2._empty_ok(2000, 2000 + M.EMPTY_MAX * 4):
        print('FAIL: 宽区间探针查到块时不应判完成'); ok = False
    if s2.calls and 'tokenBalances' in (s2.calls[0] or {}):
        print('FAIL: 块探针不应带 tokenBalance 过滤器（成本会爆）'); ok = False
    # 宽区间 + 探针确认无块 → 放行
    fx3, _ = _fx([_FakeResp(200, '')])
    if not fx3._empty_ok(3000, 3000 + M.EMPTY_MAX * 4):
        print('FAIL: 宽区间探针确认无块时应判完成'); ok = False
    # 探针自身失败（非 200）→ 不放行
    fx4, _ = _fx([_FakeResp(500, '')])
    if fx4._empty_ok(4000, 4000 + M.EMPTY_MAX * 4):
        print('FAIL: 探针失败时不应判完成'); ok = False
    # 204（超出已索引范围）→ 不放行，否则会漏数据
    fx5, _ = _fx([_FakeResp(204, '')])
    if fx5._empty_ok(5000, 5000 + M.EMPTY_MAX * 4):
        print('FAIL: 探针 204 不应判完成（区间超出已索引范围＝会漏数据）'); ok = False
    if ok:
        print(f'PASS: 契约5 零行判定五分支正确（EMPTY_MAX={M.EMPTY_MAX}，审计留痕 '
              f'{len(fx.empty_hits) + len(fx3.empty_hits)} 条）')
    return ok


def c6_scan_area():
    """契约 6：尾段零行 → finished=True 且 done_to=to（旧版此处返回 False 记 scan-fail）。"""
    ok = True
    blk = json.dumps({'header': {'number': 1200, 'timestamp': 1700000000}}) + '\n'
    # 第一次返回推进到 1200 的块行，第二次（尾段 1201-1300）零行
    fx, _ = _fx([_FakeResp(200, blk), _FakeResp(200, '')])
    edges, done_to, fin = fx.scan_area(1000, 1300, deadline=M.time.time() + 60)
    if not fin or done_to != 1300:
        print(f'FAIL: 尾段零行应判完成到 1300，实得 fin={fin} done_to={done_to}'); ok = False
    if len(fx.empty_hits) != 1:
        print(f'FAIL: 空区间未留痕（empty_hits={fx.empty_hits}）'); ok = False
    # 对照：非 200 仍必须走失败路径（不能把真失败也判成空）
    fx2, _ = _fx([_FakeResp(503, '')] * 8)
    _e, _d, fin2 = fx2.scan_area(1000, 1010, deadline=M.time.time() + 60)
    if fin2:
        print('FAIL: HTTP 503 被误判为空区间完成'); ok = False
    if ok:
        print('PASS: 契约6 scan_area 尾段零行判完成、真失败仍失败')
    return ok


def main():
    ok = True
    ok &= c1a_distinct_poison()
    ok &= c1b_identity_conflict_and_width()
    eq, _ = c1_c2_equivalence()
    ok &= eq
    ok &= c3_route()
    ok &= c4_atomic()
    ok &= c5_empty_ok()
    ok &= c6_scan_area()
    print('PASS: fetch_sqd_transfers_v2 六条契约全过' if ok else 'FAIL: 见上')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
