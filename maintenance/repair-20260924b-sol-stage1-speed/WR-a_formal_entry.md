# WR-a正式入口验收：PASS

B 三类产物的两个真实正式入口均通过；C 仅在内存移除本次四条登记后，同一批产物的两个入口均按预期拒收。登记单 0.7 已完成。

- 验收 HEAD：`797583225ced895e11e7dc926c7bf6676b52438b`。
- 登记 commit：`70e14a81817316ea225d6341e2c8670c84e544a1`。
- repair 源码 commit：`59f88b84c9ab9eeb95c92a15e342d8cbe09925db`。
- repair SHA-256：`15822564046e654b46300edcc26aeb51b397217ecce0fb555df0e891d98a1a33`；工作树与源码 commit 内容复算一致。
- Python：`3.14.6 (v3.14.6:c63aec69bd5, Jun 10 2026, 08:07:54) [Clang 21.0.0 (clang-2100.1.1.101)]`；解释器 `/usr/local/bin/python3`。
- tempfile：`/private/tmp/WR-a-formal-entry-22smuw9u`，由 `tempfile.mkdtemp()` 创建并保留。
- 完整运行器：[runner.py](/private/tmp/WR-a-formal-entry-22smuw9u/runner.py)；原始输出：[run.log](/private/tmp/WR-a-formal-entry-22smuw9u/run.log)；结构化结果：[results.json](/private/tmp/WR-a-formal-entry-22smuw9u/results.json)。退出码 `0`，尾行 `FINAL PASS`。

复用 `test_w4_evidence_generations` 的自包含构造逻辑及 `build_batch3b_case`、`w4_old_payload_and_ledger`、`repair_slot_responses`、`w4_missing_transaction`、`write_repair_fixture`。未执行测试文件的 `main()` 或读取 `.staging_b3` 的测试入口。

全旧／全新／混合表示旧双查询证据与新合并查询证据的组合，最终均由本次登记的当前 repair 生产者发布。每类均确认 slot `19998`、`19999` 为 `confirmed_nonce_defect`，发布 generation 和 repair CURRENT。旧证据字节、旧 ledger 保留检查通过；旧／新／混合新增夹具请求数分别为 `0/4/2`，无旧证据重取。

B 使用真实 `sqd_cache_identity` 和原始 `historical_producer_hashes`，不替换任何登记查询。构造阶段仅沿用 W4 的 transport 调用计数包装，该包装在 B 前已退出。`current_base.edge_sha256` 来自本案规范 base 文件的实际哈希。

全旧，case：`/private/tmp/WR-a-formal-entry-22smuw9u/w4-old-81uce3e3/case`。调用结果原文：

```text
validate_repair_bundle(deep=True): PASS: returned bundle gid=290b57be199a484d, mode=formal
resolve_formal_cache: PASS: kind=repaired, gid=290b57be199a484d, binding.cache_kind=repaired; edge/meta=CURRENT-selected generation
```

全新，case：`/private/tmp/WR-a-formal-entry-22smuw9u/w4-new-c046vooc/case`。调用结果原文：

```text
validate_repair_bundle(deep=True): PASS: returned bundle gid=065f1e4ce2f03b9e, mode=formal
resolve_formal_cache: PASS: kind=repaired, gid=065f1e4ce2f03b9e, binding.cache_kind=repaired; edge/meta=CURRENT-selected generation
```

混合，case：`/private/tmp/WR-a-formal-entry-22smuw9u/w4-mixed-xze0xrau/case`。调用结果原文：

```text
validate_repair_bundle(deep=True): PASS: returned bundle gid=9d4be46e62d00ad4, mode=formal
resolve_formal_cache: PASS: kind=repaired, gid=9d4be46e62d00ad4, binding.cache_kind=repaired; edge/meta=CURRENT-selected generation
```

三类均断言 `kind == "repaired"`、`gid == bundle["gid"] == CURRENT["gid"]`、`binding["cache_kind"] == "repaired"`；edge/meta 精确匹配该代 bundle 的 merged 文件，且父目录相同。另核对 CURRENT 的 bundle 路径和 binding 的 edge/meta 实际哈希。

C 使用 `patch.object(producer_history, "PRODUCER_HISTORY", filtered)`，仅移除目标 script、目标 SHA 对应的四条 ACTIVE 登记：`sqd-solana-cache/v4`、`sqd-solana-repair-bundle/v1`、`sqd-solana-coverage-resolution/v1`、`sqd-solana-repair-pointer/v1`。查询函数保持原对象；每类对照结束后断言登记元组已恢复。异常原文如下：

| 产物 | validate_repair_bundle(deep=True) | resolve_formal_cache |
| --- | --- | --- |
| 全旧 | `ValueError: formal repair producer is not registered` | `ValueError: formal repair producer is not registered` |
| 全新 | `ValueError: formal repair producer is not registered` | `ValueError: formal repair producer is not registered` |
| 混合 | `ValueError: formal repair producer is not registered` | `ValueError: formal repair producer is not registered` |

这证明本次四条登记作为一组使正式入口接收这些产物；未声称逐条隔离验证了四个协议各自的必要性。

运行器关键代码如下，摘自完整运行器的三类循环体。上下文为 `t = test_sqd_gap_repair`、真实 `repair/identity/registry` 模块；`slots = [19998, 19999]`，循环参数 `(label, old_count)` 为 `("old", 2)`、`("new", 0)`、`("mixed", 1)`；`old_sha = "25f04ff10bc494be977e4c5b3193c3a928c0764fa529d8d5a47563fe2a825e66"`，`fp` 为 `fixture://helius` 的 reference 指纹，`OUT` 为上述 tempfile。

构造并发布：

```python
root = Path(tempfile.mkdtemp(prefix=f'w4-{label}-', dir=OUT))
case = t.build_batch3b_case(root, set(slots), [
    [i + 1, slot, 0, -1, t.ZERO, f'Base{i}', 1]
    for i, slot in enumerate(slots)])
plan, _, _ = repair._plan(case, MINT, reference_fingerprint=fp)
parent, pointer, _ = repair.sqd_repair_paths(case, MINT)
old_bytes = {}
args = ['repair', '--mint', MINT, '--case-root', str(case)]
if old_count:
    previous = deepcopy(plan)
    previous['producer']['sha256'] = old_sha
    previous['plan_digest'] = repair.compute_plan_digest(previous)
    old = parent / f"pending-{previous['plan_digest']}"
    old.mkdir(parents=True)
    repair.load_resume_slots(old, repair._ledger_header(previous))
    for seq, slot in enumerate(slots[:old_count]):
        payload, ledger = t.w4_old_payload_and_ledger(repair, slot, fp, seq)
        repair._persist_live_slot(old, payload, MINT, ledger)
    old_bytes = {str(p.relative_to(old)): p.read_bytes() for p in old.rglob('*') if p.is_file()}
    args += ['--resume', '--adopt-pending', str(old)]
responses = {}
for slot in slots[old_count:]:
    responses.update(t.repair_slot_responses(repair, slot, t.w4_missing_transaction(slot)))
fixture = t.write_repair_fixture(root / 'fixture', responses)
calls = []
def observe(self, kind, body):
    calls.append((kind, body['params'][0] if kind == 'reference-getBlock' else body['fromBlock']))
    return original_call(self, kind, body)
with patch.object(repair.RepairFixtureTransport, 'call', observe):
    assert repair.main(args + ['--transport-fixture', str(fixture)]) == 0
```

发布后从 CURRENT 读取 `gen` 和 `bundle`，完成上述证据格式与 confirmed 检查，然后执行：

```python
base_edge, _, _ = repair.soltx_cache_paths(MINT, case / 'data')
assert base_edge.resolve() == (case / bundle['base']['edge_file']).resolve()
assert repair.sha256_file(base_edge) == plan['base']['edge_sha256']
kwargs = dict(deep=True, case_root=case, current_base={'edge_sha256': repair.sha256_file(base_edge)})
row.update(case=str(case), gen=str(gen), base_edge=str(base_edge), confirmed=confirmed, gid=bundle['gid'], calls=calls)
# B: real registry and query function, without patches.
assert registry.PRODUCER_HISTORY is original_registry
assert identity.historical_producer_hashes is original_query
checked = identity.validate_repair_bundle(gen / 'bundle.json', **kwargs)
assert checked == bundle
row['B_validate'] = f"PASS: returned bundle gid={checked['gid']}, mode={checked['mode']}"
edge, meta, kind, gid, binding = identity.resolve_formal_cache(MINT, case)
assert kind == 'repaired' and gid == bundle['gid'] == current['gid']
assert binding['cache_kind'] == 'repaired' and binding['gid'] == gid
assert edge.resolve() == (gen / bundle['merged']['edge_file']).resolve()
assert meta.resolve() == (gen / bundle['merged']['meta_file']).resolve()
assert edge.parent.resolve() == meta.parent.resolve() == gen.resolve()
assert (case / current['inputs']['bundle']['path']).resolve() == (gen / 'bundle.json').resolve()
assert binding['soltx_edges_sha256'] == repair.sha256_file(edge)
assert binding['soltx_meta_sha256'] == repair.sha256_file(meta)
row['B_resolve'] = f"PASS: kind={kind}, gid={gid}, binding.cache_kind={binding['cache_kind']}; edge/meta=CURRENT-selected generation"
row.update(edge=str(edge), meta=str(meta), binding=binding)
# C: remove exactly the four entries, in memory only; same artifacts and calls.
row['C'] = {}
with patch.object(registry, 'PRODUCER_HISTORY', filtered):
    assert identity.historical_producer_hashes is original_query
    for protocol in PROTOCOLS:
        assert SHA not in original_query(SCRIPT, protocol)
    for name, call in (
        ('validate_repair_bundle', lambda: identity.validate_repair_bundle(gen / 'bundle.json', **kwargs)),
        ('resolve_formal_cache', lambda: identity.resolve_formal_cache(MINT, case)),
    ):
        try:
            call()
        except ValueError as exc:
            row['C'][name] = f'{type(exc).__name__}: {exc}'
            assert str(exc) == 'formal repair producer is not registered'
        else:
            raise AssertionError(name + ' unexpectedly accepted unregistered producer')
assert registry.PRODUCER_HISTORY is original_registry
```

复现命令（完整运行器会在同一 tempfile 下创建新的三类目录，更新运行器结果文件）：

```sh
python3 -B /private/tmp/WR-a-formal-entry-22smuw9u/runner.py
```

是否读到任何禁区：**否**。未读取 `~/.codex/` 或 memories，未读取其他列明禁区；maintenance 仅访问本次允许目录。运行器安装了文件访问、网络及子进程审计拦截，`blocked_events = []`，无联网或子进程调用。使用 `-B` 禁止写入字节码。夹具、运行器及结果仅在系统 tempfile；仓库内仅新增指定 `WR-a_formal_entry.md`。未 commit、push、stash、checkout、reset、创建 worktree 或执行批量删除。
