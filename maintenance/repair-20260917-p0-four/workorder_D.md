# 工单 D（v4）：R09 日级峰值闸——rglob 定位＋补算覆盖收据＋`replay_duck --only-addrs` 生产者 —— repair-20260917-p0-four 第四段

> 出处：codex 对 7.0.4 的 review（`REVIEW.md` R09，P0）：①发布闸 `check_daily_peaks` 只看案根 `peaks_summary.json`，真实案子产物在 `data/peaks_daily/`（APU分析0801 实证：`data/peaks_daily/peaks_summary.json`），闸被整段绕过；②即使找到，闸也不验 `needs_block_precision.json`（L1 未达但 L2 达标、须补块级精确值的地址）是否真的补算过——"同日等额进出"的地址可漏判。用户 2026-09-17 裁决：修，三件套＝闸定位改 rglob、补算覆盖收据、`replay_duck.py --only-addrs` 生产者入口；总原则"能不新增不新增、skill 上下文不增"。
> v4 变更（对 codex r3，见 `review_D_reply_r3.md`）：D-R3-01 D4-b 最后一笔转出改 `5*10**18`（原 `10**19` 使 ADDRS[1] 余额为负、全量 exit 4）；D-R3-02 D4-a 逐例循环捕获 `Exception`（保留异常类型记为 RED，基线用例 13 是 AttributeError）。
> v3 变更（对 codex r2 四条＋诊断，见 `review_D_reply_r2.md`，全采纳）：D-R2-01 D2 summary/trigger 顶层须为对象、`active_candidates` 缺项/null 不作零候选（须为列表）；D-R2-02 D3 触发日逐日验 `active_candidates` 为列表，统一 `_fail`；D-R2-03 坏事件反例改为"先成功全量→再用另一含坏事件的通道跑 only-addrs"比较原产物字节；D-R2-04 用例 2/12 标 GREEN→GREEN、子函数 1..13、§0.7 按真实基线记录；D-R2-05 `raw_int` 追加错误即 continue。
> v2 变更（对 codex r1 八条，见 `review_D_reply_r1.md`，全采纳）：D-01 `--only-addrs` 模式下坏事件分支不写 `replay_stats.json`（校验照旧、只不落收据）＋坏事件反例；D-02 needs/触发日形状严格校验＋地址两侧统一小写；D-03 followup 顶层/inputs/addresses 逐项形状校验（peak>0 ⇒ peak_blk 非负整数，peak==0 ⇒ null），结构错误进 errors 不崩；D-04 schema 比对去掉 `str()` 包裹（扫描器只识别裸 `.get("schema")`）；D-05 坏 JSON/空并集/格式非法一律 stderr＋`SystemExit(2)`，测试断言 `== 2`；D-06 h 例夹具补合法空 needs＋summary 两字段并加放行断言（不豁免旧 summary）；D-07 基线声明订正；D-08 deltas 抽取与 h 例改用唯一锚。
> 内容基线：HEAD＝C 段落地后的 commit（开工 HEAD 以 `construct_D_prompt.md` 派工副本首行标注为准）。本段白名单文件中 `peaks_daily.py`、`replay_duck.py`、`test_engine_equivalence.py`、`test_peaks_daily.py`、两份文档与 `4cbfe48` 逐字节相同（A/B/C 未触及）；`test_audit_release_gate.py` 经 B/C 段各有新增（R03 用例、facts 夹具助手），以 C 落地后为基线；`audit_release_gate.py` 经 C 段插入后行号已漂移，本工单全部锚点已在 C 落地后的 HEAD（1b317b3）上重新 `grep -n -F` 实证；`invariant_manifest.json` 以 C 段落地后为基线。行号均指施工前基线。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `D_done.md`：`git status --short`（须为空）；`git rev-parse --short HEAD`（须与 `construct_D_prompt.md` 派工副本首行标注一致）。不符即停工写 `D_done_attempt1_stopped.md`。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 在 done 里披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`；**禁读** `/Users/uravvv/Desktop` 下任何文件。
- 0.3 **白名单**：生产 `scripts/evm/peaks_daily.py`、`scripts/evm/replay_duck.py`、`scripts/report/audit_release_gate.py`；测试 `scripts/tests/test_audit_release_gate.py`、`scripts/tests/test_engine_equivalence.py`、`scripts/tests/test_peaks_daily.py`；登记 `scripts/tests/invariant_manifest.json`（只按 invariant_scan 报出的缺项增补）；文档 `references/data-pipeline-evm-recon.md`（只改 :132）、`references/playbook-entity-cluster-tiering.md`（只改 :149 一个子串）；本目录新建 `D_done.md`、`D_red_evidence.txt`，停工时 `D_done_attempt1_stopped.md`。
- 0.4 **不改**：`peaks_daily.py` 的 L1/L2 算法、`--pct` 默认值与 docstring 里的 1%（登记 P2 另单）、`needs_block_precision.json` 内容格式、`trigger_days.json` 格式与 schema；`replay_duck.py` 的 `build_events`/`replay_pass1`/`emit_merged`/`replay_pass2` 逻辑（只允许把 :190-194 的 `deltas` 视图创建抽成小函数供两处调用，SQL 文本逐字不变）；`audit_release_gate.py` 除 `check_daily_peaks` 及其新增辅助外的一切；契约针 `prev_close_plus_gross_in/v2`、`trigger-days-replay/v1`；SKILL.md、commands-staging、VERSION、pyproject、CHANGELOG、contract_manifest。
- 0.5 行号均指施工前基线；锚 `grep -n -F` 恰 1 处且行号一致，不符**停工**。删除 > 修改 > 新增。
- 0.6 离线；不 commit、不 push、不部署；禁 stash/checkout/reset。
- 0.7 先红后绿：D4 新用例改动前先跑取基线结果写 `D_red_evidence.txt`（逐例独立、逐例捕获 AssertionError；按各例**真实基线**如实记录 RED 或 GREEN→GREEN 回归例，不制造 RED；基线抛非 AssertionError 异常也记为 RED，不得当 GREEN），改后取 GREEN。
- 0.8 本段只跑：`python3 -B scripts/tests/test_audit_release_gate.py`、`test_engine_equivalence.py`、`test_peaks_daily.py`、`test_batch15_three_ledgers_frozen.py`、`test_repair_batch_d.py`、`test_stage2_closeout.py`、`python3 -B scripts/tests/invariant_scan.py`。不跑 run_all。

## 1. 硬约束

- 1.1 文档字节：SKILL.md 8021、commands-staging 8798 不变；references ＝ C 段落地值 **930065 − 13 + 9 ＝ 930061**（命令同工单 A §1.1，只用 stat）。
- 1.2 `git diff --stat` 只含 0.3 白名单。
- 1.3 `--only-addrs` 运行**不得**写/覆盖 `replay_stats.json`、`peaks.json`、`balances_final.json`、`mint_ledger.json`、merged 产物、pass2 产物；收据写到第一个 `--only-addrs` 文件所在目录。
- 1.4 闸对"案内零份 peaks_summary.json"仍 return（不强制所有案都跑 peaks_daily——与现行契约一致）；对"多份"拒。

## 2. 逐条施工

### D1 `scripts/evm/peaks_daily.py`：summary 登记 needs 文件哈希

- `:171`（锚 `    json.dump(need, open(f"{a.out_dir}/needs_block_precision.json", "w"), indent=1)`）之后插入：

```python
    need_sha = hashlib.sha256(
        open(f"{a.out_dir}/needs_block_precision.json", "rb").read()).hexdigest()
```

- `:213`（锚 `               "trigger_days_sha256": trig_sha,`）之后插入：

```python
               "needs_block_precision_file": "needs_block_precision.json",
               "needs_block_precision_sha256": need_sha,
```

`hashlib` 已在本文件使用（`:202`）。docstring `:60-63` 的产物说明补一行 `needs_block_precision_sha256`（发布闸靠它咬合补算收据），字节不限（脚本不计入文档预算）。

### D2 `scripts/report/audit_release_gate.py`：`check_daily_peaks` 改 rglob 定位＋needs 咬合＋补算覆盖收据

- `:1074-1103`（锚首行 `def check_daily_peaks(case_dir: Path, errors: list[str]):`，末行 `        errors.append("trigger_days.json 触发日为空且无 empty_reason 显式声明")`）整个函数替换为下述（保留原 docstring 主旨与全部原错误文案，便于既有断言子串不变）：

```python
BLOCK_PRECISION_FOLLOWUP_SCHEMA = "block-precision-followup/v1"


def _find_peaks_summaries(case_dir: Path) -> list[Path]:
    """R09（7.2.0）：peaks_daily 产物根不限定案根——递归定位 peaks_summary.json；
    跳过隐藏目录（.duck_tmp 等）、_history 与符号链接路径。"""
    hits = []
    for p in sorted(case_dir.rglob("peaks_summary.json")):
        rel = p.relative_to(case_dir)
        if any(part.startswith(".") or part == "_history" for part in rel.parts):
            continue
        cur, linked = p, False
        while cur != case_dir:
            if cur.is_symlink():
                linked = True
                break
            cur = cur.parent
        if linked or not p.is_file():
            continue
        hits.append(p)
    return hits


def check_daily_peaks(case_dir: Path, errors: list[str]):
    """日级峰值口径闭环（v6.9.1）：案内出现 peaks_summary.json 即视为用了
    peaks_daily 替代件——旧上界公式产物拒收（Σmax(day_delta,0) 非恒等上界，
    同日等额进出会漏），且四类触发日必须有显式产物（空也要声明）。
    R09（7.2.0）：①产物根按 rglob 定位（原只看案根，data/peaks_daily/ 下的产物整段绕过闸）；
    ②needs_block_precision.json 与 summary 哈希咬合；③needs ∪ 触发日活跃候选非空时，
    必须有 replay_duck.py --only-addrs 产出的 block_precision_followup.json 覆盖每一址。"""
    hits = _find_peaks_summaries(case_dir)
    if not hits:
        return
    if len(hits) > 1:
        errors.append("案内出现多份 peaks_summary.json（"
                      + ", ".join(str(h.relative_to(case_dir)) for h in hits)
                      + "）——峰值产物根须唯一，清理陈旧目录后重验")
        return
    ps_path = hits[0]
    pd = ps_path.parent
    ps = load_json(ps_path, errors)
    if not isinstance(ps, dict):
        errors.append("peaks_summary.json 顶层须为对象")
        return
    if str(ps.get("ub_formula")) != "prev_close_plus_gross_in/v2":
        errors.append("peaks_daily 产物是旧上界公式（缺 ub_formula=prev_close_plus_gross_in/v2）"
                      "——同日等额进出会被对冲漏检，升级脚本重跑")
    # v6.9.2（codex 验收 P2）：目录复用时残留的旧 trigger_days.json 不作数——
    # 本次运行必须真带 --trigger-days，且产物哈希与 summary 登记咬合。
    if not ps.get("trigger_days_file"):
        errors.append("peaks_daily 本次运行未带 --trigger-days（四类触发日义务未履行）"
                      "——目录里残留的旧 trigger_days.json 不作数，带触发日清单重跑")
        return
    tp = pd / "trigger_days.json"
    if not tp.is_file() or tp.is_symlink():
        errors.append("peaks_summary 声称产出触发日但 trigger_days.json 缺失")
        return
    trig_sha = str(ps.get("trigger_days_sha256", "")).lower()
    if not trig_sha or sha256_file(tp).lower() != trig_sha:
        errors.append("trigger_days.json 与本次 peaks_daily 运行不咬合"
                      "（sha256 不匹配或 summary 未登记）——陈旧/换包产物拒收")
    td = load_json(tp, errors)
    if not isinstance(td, dict):
        errors.append("trigger_days.json 顶层须为对象")
        return
    if str(td.get("schema")) != "trigger-days-replay/v1":
        errors.append("trigger_days.json schema 非法（须 trigger-days-replay/v1）")
    elif not td.get("days") and not td.get("empty_reason"):
        errors.append("trigger_days.json 触发日为空且无 empty_reason 显式声明")
    # R09 ②：needs 文件必须在场且与 summary 登记哈希咬合（旧版 peaks_daily 未登记＝升级重跑）
    needs_path = pd / "needs_block_precision.json"
    needs_sha = str(ps.get("needs_block_precision_sha256", "")).lower()
    if needs_path.is_symlink() or not needs_path.is_file() or not needs_sha \
            or sha256_file(needs_path).lower() != needs_sha:
        errors.append("needs_block_precision.json 缺失或与 peaks_summary 登记的 sha256 不咬合"
                      "（旧版 peaks_daily 未登记该哈希＝升级脚本重跑）")
        return
    need = load_json(needs_path, errors)
    if not isinstance(need, dict) or any(not isinstance(v, list) for v in need.values()):
        errors.append("needs_block_precision.json 形状非法（须 {门槛: [地址]} 字典）")
        return
    union = set()
    for bucket in need.values():
        if any(not isinstance(x, str) or not x.strip() for x in bucket):
            errors.append("needs_block_precision.json 地址项须为非空字符串")
            return
        union.update(x.strip().lower() for x in bucket)
    days = td.get("days")
    if days is not None and not isinstance(days, dict):
        errors.append("trigger_days.json days 须为对象（日→{reason,count,active_candidates}）")
        return
    td_union = set()
    for key, day in (days or {}).items():
        if not isinstance(day, dict):
            errors.append(f"trigger_days.json days[{key}] 须为对象")
            return
        cands = day.get("active_candidates")
        if not isinstance(cands, list) or any(not isinstance(x, str) or not x.strip() for x in cands):
            errors.append(f"trigger_days.json days[{key}].active_candidates 须为地址字符串列表（缺项/null 不作零候选）")
            return
        td_union.update(x.strip().lower() for x in cands)
    union |= td_union
    if not union:
        return
    # R09 ③：补算覆盖收据——每个待补地址都必须有块级精确峰值，且收据绑定当前 needs/触发日
    fu_path = pd / "block_precision_followup.json"
    if fu_path.is_symlink() or not fu_path.is_file():
        errors.append(f"日级峰值有 {len(union)} 址需块级精确补算，但缺 block_precision_followup.json "
                      "收据（replay_duck.py --only-addrs 产出）——L2 过线地址未补算不得判级")
        return
    fu = load_json(fu_path, errors)
    if not isinstance(fu, dict):
        errors.append("block_precision_followup.json 顶层须为对象")
        return
    if fu.get("schema") != BLOCK_PRECISION_FOLLOWUP_SCHEMA:
        errors.append(f"block_precision_followup.json schema 非法（须 {BLOCK_PRECISION_FOLLOWUP_SCHEMA}）")
    if fu.get("engine") != "replay_duck.py":
        errors.append("block_precision_followup.json engine 非 replay_duck.py——块级补算须走重放引擎")
    items = fu.get("inputs")
    if not isinstance(items, list) or any(not isinstance(i, dict) for i in items):
        errors.append("block_precision_followup.json inputs 须为 [{path, sha256}] 列表")
        return
    bound = {Path(str(i.get("path") or "")).name: str(i.get("sha256") or "").lower() for i in items}
    if bound.get("needs_block_precision.json") != needs_sha:
        errors.append("block_precision_followup.json 未绑定当前 needs_block_precision.json（inputs sha 不咬合）——needs 变了要重跑补算")
    if td_union and bound.get("trigger_days.json") != trig_sha:
        errors.append("block_precision_followup.json 未绑定当前 trigger_days.json（inputs sha 不咬合）——触发日活跃候选也须补算")
    addrs = fu.get("addresses")
    if not isinstance(addrs, dict):
        errors.append("block_precision_followup.json 缺 addresses 映射")
        return
    norm = {}
    for key, entry in addrs.items():
        k = str(key).strip().lower()
        if k in norm:
            errors.append(f"block_precision_followup.json addresses 含大小写重复地址 {k}")
            return
        norm[k] = entry
    missing = sorted(a for a in union if a not in norm)
    if missing:
        errors.append(f"块级补算收据未覆盖 {len(missing)} 址（样例 {missing[:3]}）——只多查不漏查")
    for addr in sorted(union - set(missing)):
        entry = norm[addr]
        if not isinstance(entry, dict) or "peak" not in entry or "peak_blk" not in entry:
            errors.append(f"块级补算收据 {addr} 须含 peak 与 peak_blk 两字段")
            continue
        before = len(errors)
        peak = raw_int(entry.get("peak"), f"block_precision_followup.addresses[{addr}].peak", errors)
        if len(errors) > before:
            continue   # peak 本身非法只报根因，不再用替代值 0 判 peak_blk
        blk = entry.get("peak_blk")
        if peak > 0:
            if isinstance(blk, bool) or not isinstance(blk, int) or blk < 0:
                errors.append(f"块级补算收据 {addr}.peak_blk 须为非负整数区块（peak>0）")
        elif blk is not None:
            errors.append(f"块级补算收据 {addr}.peak_blk 在 peak==0 时须为 null")
```

`load_json`（:408）、`sha256_file`（:457）、`raw_int`（:603）为本文件既有。调用点 `:1676`（锚 `    check_daily_peaks(case_dir, errors)`）不变。

### D3 `scripts/evm/replay_duck.py`：`--only-addrs` 生产者

- `:190-194`（`replay_pass1` 内 `deltas` 视图创建；`:190` 的 `    con.execute(f"""` 全文多处不作锚，以 `:191` 锚 `        CREATE VIEW deltas AS` 与 `:194` 锚 `        SELECT frm, b, -CAST(v AS {vt}) FROM events WHERE frm <> '{Z}'""")` 定界）抽成模块级 `def _create_deltas_view(con, vt):`（SQL 文本逐字不变），`replay_pass1` 原位改为 `    _create_deltas_view(con, vt)`。
- 新增模块级函数（放在 `:330`（锚 `def _peaks_python(con, peak_min):`）之前）：

```python
def _load_only_addrs(paths):
    """--only-addrs 输入三态：needs_block_precision.json（{门槛:[地址]}）、trigger_days.json
    （{"days":{日:{"active_candidates":[...]}}}）、纯地址列表。返回 (并集(小写), [(basename, sha256)])。"""
    union, inputs = set(), []
    for p in paths:
        try:
            raw = json.load(open(p, encoding="utf-8"))
        except (OSError, ValueError) as exc:
            _fail(f"[only-addrs] 读不了 {p}: {exc}")
        if isinstance(raw, list):
            found = raw
        elif isinstance(raw, dict) and "days" in raw:
            days = raw["days"]
            if not isinstance(days, dict) or any(not isinstance(d, dict) for d in days.values()):
                _fail(f"[only-addrs] {p} trigger_days 形状非法（days 须为 日→对象）")
            found = []
            for key, d in days.items():
                cands = d.get("active_candidates")
                if not isinstance(cands, list):
                    _fail(f"[only-addrs] {p} days[{key}].active_candidates 须为列表（缺项/null 不作零候选）")
                found.extend(cands)
        elif isinstance(raw, dict):
            if any(not isinstance(v, list) for v in raw.values()):
                _fail(f"[only-addrs] {p} needs 形状非法（须 {{门槛: [地址]}}）")
            found = [x for v in raw.values() for x in v]
        else:
            _fail(f"[only-addrs] {p} 格式非法（需 needs 字典 / trigger_days / 地址列表）")
        if any(not isinstance(x, str) or not x.strip() for x in found):
            _fail(f"[only-addrs] {p} 地址项须为非空字符串")
        union.update(x.strip().lower() for x in found)
        with open(p, "rb") as fh:
            inputs.append((os.path.basename(p), hashlib.sha256(fh.read()).hexdigest()))
    if not union:
        _fail("[only-addrs] 地址并集为空——无需补算（needs 与触发日活跃候选均空）")
    return union, inputs


def _fail(msg):
    print(msg, file=sys.stderr, flush=True)
    raise SystemExit(2)


def followup_peaks(con, a, vt):
    """R09（7.2.0）：只对 --only-addrs 并集算块级精确峰值（无门槛、无预筛），写
    block_precision_followup.json 到第一个 --only-addrs 文件所在目录。整段跳过 pass1/merged/
    pass2，不碰 replay_stats/peaks.json 等全量产物。窗口 SQL 与 replay_pass1 逐字相同。"""
    union, inputs = _load_only_addrs(a.only_addrs)
    _create_deltas_view(con, vt)
    con.execute("CREATE TABLE only_addrs (a VARCHAR)")
    con.executemany("INSERT INTO only_addrs VALUES (?)", [(x,) for x in sorted(union)])
    con.execute("""
        CREATE TABLE ab AS
        SELECT a, b, SUM(d) dd FROM deltas
        WHERE a IN (SELECT a FROM only_addrs) GROUP BY a, b""")
    try:
        con.execute("""
            CREATE TABLE peaks AS
            WITH cum AS (SELECT a, b, SUM(dd) OVER (PARTITION BY a ORDER BY b) c FROM ab),
                 mx AS (SELECT a, MAX(c) mc FROM cum GROUP BY a HAVING MAX(c) > 0)
            SELECT m.a, m.mc, MIN(cum.b) pb FROM mx m
            JOIN cum ON cum.a = m.a AND cum.c = m.mc GROUP BY m.a, m.mc""")
        peak_rows = con.execute("SELECT a, mc, pb FROM peaks").fetchall()
    except duckdb.Error as e:
        print(f"[only-addrs] SQL 窗口不可用（{str(e)[:80]}），回退 Python 流式", flush=True)
        peak_rows = _peaks_python(con, 0)
    found = {str(x): {"peak": str(int(mc)), "peak_blk": int(pb)} for x, mc, pb in peak_rows}
    addresses = {x: found.get(x, {"peak": "0", "peak_blk": None}) for x in sorted(union)}
    with open(a.channels, "rb") as fh:
        chan_sha = hashlib.sha256(fh.read()).hexdigest()
    with open(__file__, "rb") as fh:
        self_sha = hashlib.sha256(fh.read()).hexdigest()
    receipt = {"schema": "block-precision-followup/v1", "engine": "replay_duck.py",
               "producer": {"path": os.path.basename(__file__), "sha256": self_sha},
               "value_type": vt,
               "inputs": [{"path": n, "sha256": s} for n, s in inputs],
               "channels": {"path": os.path.basename(a.channels), "sha256": chan_sha},
               "count": len(addresses), "addresses": addresses}
    out = os.path.join(os.path.dirname(os.path.abspath(a.only_addrs[0])), "block_precision_followup.json")
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(receipt, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, out)
    print(f"[only-addrs] 块级精确峰值 {len(addresses)} 址（有事件 {len(found)}）→ {out}", flush=True)
    return 0
```

- `:556`（锚 `    ap.add_argument("--force-varint", action="store_true",`）之前插入：

```python
    ap.add_argument("--only-addrs", action="append", metavar="JSON",
                    help="只对这些地址算块级精确峰值（needs_block_precision.json / trigger_days.json / "
                         "地址列表，可重复）；写 block_precision_followup.json 到首个文件所在目录，"
                         "跳过 pass1/merged/pass2，不覆盖全量产物")
```

- `:577`（锚 `        json.dump(receipt, open(f"{a.out_dir}/replay_stats.json", "w"), indent=1)`，坏事件分支的全量收据写入）改为：

```python
        if a.only_addrs:
            print("[only-addrs] 输入含 rejected rows，不写 replay_stats.json（不覆盖全量产物）", file=sys.stderr, flush=True)
        else:
            json.dump(receipt, open(f"{a.out_dir}/replay_stats.json", "w"), indent=1)
```

  （坏事件校验与随后的 `raise SystemExit(...)` 不动——`--only-addrs` 不绕过事件校验，只不落全量收据。）
- `:587`（锚 `    stats, mint_total = replay_pass1(con, a.out_dir, vt)`）之前插入：

```python
    if a.only_addrs:
        raise SystemExit(followup_peaks(con, a, vt))
```

`hashlib` 若未 import（`:36` 为 `import argparse, csv, glob, json, os, sys, time`）则在该行加入 `hashlib`。`_peaks_python(con, peak_min)`（`:330`）读 `ab` 表——施工方核对其实现确实只依赖 `ab` 且 `peak_min=0` 语义为"无门槛"，不成立即停工汇报。事件表地址归一方式（`build_events` 是否小写）须与 `_load_only_addrs` 的 `.lower()` 一致（复核 r1 已证 `build_events` 小写），收据 `addresses` 键一律小写，与 D2 消费者两侧同一归一。

### D4 测试

**D4-a `scripts/tests/test_audit_release_gate.py`**：在 `:970`（锚 `        assert not any(("trigger" in x or "上界" in x) for x in errors), errors`，h 例末行）之后、`:972`（锚 `    # 6.9.2 修复反例（codex 验收 P1）：挂名≠裁决——空壳候选拒。`）之前插入新块。**先改 h 例**：`:960`（锚 `        # h) 显式空声明＋哈希咬合 → 峰值/触发日检查放行`，本文件唯一）起至 `:970`（锚 `        assert not any(("trigger" in x or "上界" in x) for x in errors), errors`）共 11 行整块替换为——在写 `trigger_days.json` 之后、写 summary 之前加 `write_json(root, "needs_block_precision.json", {"0.0100": []})`，summary 加 `"needs_block_precision_file": "needs_block_precision.json"` 与 `"needs_block_precision_sha256": sha(root / "needs_block_precision.json")`，原断言保留并追加一行 `assert not any(("needs" in x or "followup" in x) for x in errors), errors`（h 例在基线因新闸报 needs 哈希错误而假绿——不豁免旧 summary，补夹具）；`:953-957` g 例 summary 与 h 同文不作锚、不改。新块为独立子函数 `_r09_case_1..13(root)`＋逐例捕获循环（写法照 B 段 `_r03_*`，但 `except` 改捕获 `Exception`——记录 `type(exc).__name__` 与原文，基线用例 13 抛 AttributeError 须记为该例 RED 而非逃出），每例 `build_case(root, historical=False)` 后 `gate.run(root, report)`，夹具助手 `_r09_write_peaks(pd, *, needs, days=None, empty_reason="夹具案：窗内无四类触发日", needs_sha=None, followup=None)` 在目录 `pd` 写 `needs_block_precision.json`(`{"0.0100": needs}`)、`trigger_days.json`、`peaks_summary.json`（ub_formula/trigger_days_file True/trigger_days_sha256/needs_block_precision_file/needs_block_precision_sha256＝实算或 `needs_sha` 覆盖）与可选 `block_precision_followup.json`：

| # | 名称 | 夹具 | 断言 | 基线 |
|---|---|---|---|---|
| 1 | R09 子目录旧公式拒（原反例） | `data/peaks_daily/peaks_summary.json` 只有 `{"engine":"peaks_daily.py"}` | 含 `旧上界公式` | RED：基线只看案根，零错误 |
| 2 | R09 子目录完整产物放行 | `data/peaks_daily/` 写 needs `[]`＋空触发日声明＋summary 全字段 | 不含 `trigger`/`上界`/`needs`/`followup` | GREEN→GREEN（回归例；用例 1 证明缺陷） |
| 3 | R09 needs 非空缺收据拒 | needs `["0xabc"]`，无 followup | 含 `block_precision_followup.json` | RED |
| 4 | R09 收据少一址拒 | needs `["0xabc","0xdef"]`，followup 只含 0xabc | 含 `未覆盖 1 址` | RED |
| 5 | R09 needs sha 不咬合拒 | summary `needs_sha="0"*64` | 含 `needs_block_precision.json 缺失或` | RED |
| 6 | R09 多份 summary 拒 | 案根与 `data/peaks_daily/` 各一份完整 summary | 含 `多份 peaks_summary.json` | RED |
| 7 | R09 触发日活跃候选进并集 | needs `[]`，days `{"2026-01-01":{"reason":"launch","count":1,"active_candidates":["0xdef"]}}`；无 followup → 含 `followup`；补 followup 覆盖 0xdef 且 inputs 绑 needs+trigger sha → 不含 `followup`/`未覆盖` | RED（前半） |
| 8 | R09 needs 形状非法拒 | needs 文件内容分别为 `["0xabc"]`、`{"0.0100":"0xabc"}`（summary sha 按实物登记） | 含 `形状非法` | RED（基线放行） |
| 9 | R09 触发日形状非法拒 | days `{"2026-01-01":"x"}` → 含 `days[2026-01-01] 须为对象`；days `{"2026-01-01":{"reason":"launch","count":1,"active_candidates":null}}` 与缺 `active_candidates` 字段 → 含 `不作零候选`（三变体） | RED（基线放行） |
| 10 | R09 收据结构非法进 errors 不崩 | followup 顶层 `[]` → 含 `顶层须为对象`；`inputs: 7` → 含 `inputs 须为`（两变体） | RED（基线无此检查） |
| 11 | R09 收据地址项非法拒 | needs `["0xabc"]`；followup 覆盖但 `{"peak":"1"}`（缺 peak_blk）→ 含 `两字段`；`{"peak":"1","peak_blk":-1}` → 含 `非负整数`；`{"peak":"0","peak_blk":5}` → 含 `须为 null` | RED |
| 12 | R09 地址大小写归一放行 | needs `["0xABC"]`；followup addresses 键 `0xabc` `{"peak":"1","peak_blk":1}` 绑定正确 → 不含 `未覆盖`/`followup` | GREEN→GREEN（基线无覆盖检查；回归例） |
| 13 | R09 顶层非对象进 errors 不崩 | summary 顶层 `[]` → 含 `peaks_summary.json 顶层须为对象`；trigger 顶层 `null`（summary sha 按实物登记）→ 含 `trigger_days.json 顶层须为对象`；followup 某址 `{"peak":"x","peak_blk":9}` → 含 `peak` 根因且**不含** `须为 null` | RED（基线 AttributeError / 无检查） |

**D4-b `scripts/tests/test_engine_equivalence.py`**：在 `:236`（锚 `def main():`）之前新增 `followup_case()`，并在 `main()` 里 `varint_equivalence_case()` 之后调用；确定性事件（照 `varint_equivalence_case` 写法，不用 hypothesis）：`[(Z, ADDRS[0], 10**20, 1), (ADDRS[0], ADDRS[1], 10**19, 1), (ADDRS[1], ADDRS[2], 5*10**18, 1), (ADDRS[0], ADDRS[1], 2*10**18, 1), (ADDRS[1], ADDRS[0], 5*10**18, 1)]`。步骤：`_write_inputs`；全量 `replay_duck.py --channels channels.json --out-dir new --no-merged --threads 2 --mem-limit 2GB` rc 0，记 `peaks.json`、`replay_stats.json` 字节；写 `needs.json` `{"0.0100": [ADDRS[1], ADDRS[2], ADDRS[5]]}`（ADDRS[5] 无事件）；跑 `--only-addrs needs.json`（同 channels，`--out-dir new`）rc 0；断言：`tmp/block_precision_followup.json` schema/engine/inputs[0].path=="needs.json" 且 sha 正确；ADDRS[1]/[2] 的 `peak`/`peak_blk` 与全量 `peaks.json` 对应项相等；ADDRS[5] == `{"peak":"0","peak_blk":None}`；`peaks.json`/`replay_stats.json` 字节未变；`--only-addrs` 传坏 JSON 文件 → rc **== 2** 且无收据更新；传 `[]` → rc == 2；传 `{"0.0100":"x"}` → rc == 2。**坏事件反例**（须能抓住 r1 D-01 原缺陷）：在上面成功全量跑完、`new/replay_stats.json`/`peaks.json` 字节已记之后，另建 `bad/` 目录用 `_write_inputs` 写一份**含一条坏事件**的通道（在同一事件列表末尾追加一条 `value="BAD"`——`_write_inputs` 写 CSV 后生成 collector/channel 两层收据，`_csv_stats` 只统计行数/区块不拒坏 value，故收据绑定正确、能到达 `build_events` 的 n_bad_fields 分支；**不得**事后追加 CSV 行否则只命中 preflight sha 错误），把 needs 放在独立目录 `bad_needs/needs.json`，跑 `--channels bad/channels.json --only-addrs bad_needs/needs.json --out-dir new` → rc 非 0、`new/replay_stats.json` 与 `peaks.json` 字节与成功跑后相同、`bad_needs/block_precision_followup.json` 不存在。基线（无条件写入）会把 `new/replay_stats.json` 覆盖成拒收收据（字节变化），本例即 RED。RED：基线 argparse 拒 `--only-addrs`（rc 2）——注意基线 rc 恰为 2 会让"rc == 2"断言在基线假绿，RED 取证以"收据文件不存在"为准；`_load_only_addrs` 的坏形状反例再加 trigger_days `active_candidates` 为 `7` / `"0xABC"` / `{"0xABC":1}` / `null` 四变体（各 rc == 2、无收据）。

**D4-c `scripts/tests/test_peaks_daily.py`**：在 `:113`（锚 `          and summary.get("trigger_days_sha256") == real_sha)`）之后加：

```python
    need_sha = hashlib.sha256(
        open(os.path.join(out1, "needs_block_precision.json"), "rb").read()).hexdigest()
    check("summary 登记 needs_block_precision 哈希（发布闸补算覆盖咬合依据）",
          summary.get("needs_block_precision_file") == "needs_block_precision.json"
          and summary.get("needs_block_precision_sha256") == need_sha)
```

RED：基线 summary 无该键 → check FAIL（`finish()` 非零）。

### D5 `scripts/tests/invariant_manifest.json`

施工完成后跑 `python3 -B scripts/tests/invariant_scan.py`，按其报出缺项逐条增补（消费者 schema 比对必须是裸 `fu.get("schema") != …`，扫描器 `_is_schema_access` 不识别 `str(...)` 包裹；预期：`receipt_producers` 加 `{"schemas":["block-precision-followup/v1"],"script":"scripts/evm/replay_duck.py"}`；`receipt_consumers` 的 audit_release_gate.py 条目加 `block-precision-followup/v1`；`atomic_writes` 加 replay_duck.py `followup_peaks` overwrite_single；`minimum_counts` 按实际）。不得整体回填。

### D6 文档

- `references/data-pipeline-evm-recon.md:132` 行内唯一子串 `对这批再补块级精确值——**只多查不漏查**。` → `` `replay_duck.py --only-addrs` 出收据过闸。``（61 B → 48 B，−13）。
- `references/playbook-entity-cluster-tiering.md:149` 行内唯一子串 `过线地址补块级精查。` → `过线地址补块级精查出收据。`（30 B → 39 B，+9）。该行末尾的日期戳 `2026-08-02 定。` 保留。

## 3. 完成报告 `D_done.md` 必含

①0.1 输出；②D1/D2/D3 diff 原文与 D4/D5/D6 摘要；③RED 摘要（逐例）；④0.8 各测试结果尾行；⑤§1.1 三字节数；⑥`git diff --stat`；⑦差异/停工点；⑧禁读披露。stdout 首行 `# 施工 D：完成` / `# 施工 D：停工`。

## 4. 调度方本机验收项（施工方不做）

- APU 0801 对照：改前 `check_daily_peaks` 对案目录返回 `[]`（缺陷本体：子目录产物被绕过）；改后须报错（错误集合取决于子目录 `trigger_days.json` 是否在场：在场且咬合 → needs 哈希缺失"升级脚本重跑"；缺失 → "声称产出触发日但 trigger_days.json 缺失"先返回），记录实际原文，不预设唯一文案；该案再发布前须重跑 peaks_daily＋`--only-addrs` 补算（81 址）。
- 登记 `code_change_pending.md`：P2（预筛 0.1% vs 1%）、P3（APU trigger_days `days` 键为原因名）维持；新增 P13＝闸不验 followup 收据 `channels` 与全量重放输入是否同源（只记录 sha），另单。
