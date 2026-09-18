# 工单 F07（v3，融合 codex 复核 r1 四条＋r2 一条 F07-R2-01）：日级峰值闸——产物目录按三件生成产物任一定位＋补算收据绑定 producer/channels —— repair-20260918-p0-f04-f07 第三段

> 出处：codex 对 7.2.0（311e6c4）的六视角 review F07（P0，**半修复 R09**）：①`_find_peaks_summaries`（`:1077-1094`）只按文件名 `peaks_summary.json` rglob，零命中即整段 return——把 summary 改名，needs/trigger/followup 还在原位也不再检查；②`check_daily_peaks` 对 `block_precision_followup.json`（`:1179-1229`）只核 schema/engine 字符串、needs/trigger sha 与 peak/peak_blk 形状，不消费真实 producer `replay_duck.py:405-410` 已写出的 `producer`/`channels`/`value_type`/`count` 字段——手写 `{engine:"replay_duck.py", inputs:[needs sha], addresses:{0xabc:{peak:"0",peak_blk:null}}}` 即从阻断变放行。反例：review 附录 D `repro_core.py` F07 段与 `repro_preseal.py` F07-selfreport/F07-rename（真实 `build_html --mode analysis-new` rc 1→0）。用户 2026-09-18 裁决：修。总原则：**skill 上下文不增**；能删不增、能改不增。
> v3 变更（`review_F07_reply_r2.md` F07-R2-01）：§4 订正——只剩 followup 时会因缺 summary 被拒，不可绕过；只有三件生成产物全部不存在/全部改名才与"未跑 peaks_daily"不可区分；标题与 §2.1 小节名"四件"改"三件生成产物"；用例 22 落地前须先建 `data` 父目录（`write_json` `:36-37` 不自动建目录）。
> v2 变更（`review_F07_reply_r1.md`，四条全采纳）：R1-01 定位只按**生成产物**三件（summary/needs/followup），`trigger_days.json` 既是 `--trigger-days` 原始输入的常见名也是输出名，不作定位依据；改单次 `rglob("*.json")` 按名过滤；补两条兼容布局用例；R1-02 §1.4 迁移改为 needs＋trigger 双 `--only-addrs`；R1-03 成本表述订正（全量通道仍要读取去重）；R1-04 §0.8 删误挂的 F12 例外。调度方实核 APU 0914 案：`channels.json` 在案根且案内唯一，峰值三件在 `peaks_daily_out/`，`trigger_days.json` 随产物目录。
> 内容基线：`311e6c4` 加本工程前段（F06、F04）落地 commit；`audit_release_gate.py` 经 F04 段在 `check_figure2_receipt`（`:1571` 起）插入约 14 行，**本工单锚点全部位于 `:1229` 之前，不受漂移影响**；`test_audit_release_gate.py`、`scripts/tests/invariant_manifest.json` 与 311e6c4 逐字节相同。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `F07_done.md`：`git status --short`（须为空）；`git rev-parse --short HEAD`（须与 `construct_F07_prompt.md` 首行标注一致）；`git diff --stat 311e6c4 HEAD -- scripts/tests/test_audit_release_gate.py scripts/tests/invariant_manifest.json scripts/evm references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（须为空）。不符即停工写 `F07_done_attempt1_stopped.md`。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260917-p0-four/` 以外的历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
- 0.3 **白名单**：生产 `scripts/report/audit_release_gate.py`；测试 `scripts/tests/test_audit_release_gate.py`；登记 `scripts/tests/invariant_manifest.json`（只按 `invariant_scan.py` 报出的缺项增补，不动其他键）；本目录新建 `F07_done.md`、`F07_red_evidence.txt`，停工时 `F07_done_attempt1_stopped.md`。
- 0.4 **不改**：`scripts/evm/replay_duck.py`（producer `:405-410` 已写全字段，一字不动）、`scripts/evm/peaks_daily.py`；`audit_release_gate.py` 中 `check_daily_peaks` 的 `:1113-1177` 段（summary/trigger/needs 校验与并集构造）、`:1192-1229` 段（inputs 咬合与 addresses 逐项形状）——只允许 §2.1/§2.2 指定的插入与替换；契约针 `prev_close_plus_gross_in/v2`、`trigger-days-replay/v1`、`BLOCK_PRECISION_FOLLOWUP_SCHEMA`；任何 `references/`、`SKILL.md`、`commands-staging/`、`VERSION`、`pyproject.toml`、`CHANGELOG.md`、`contract_manifest.json`；其他测试只跑不改。
- 0.5 行号均指施工前基线；锚 `grep -n -F` 恰 1 处且行号一致，不符**停工**。删除 > 修改 > 新增。
- 0.6 离线；不 commit、不 push、不部署；禁 stash/checkout/reset。
- 0.7 先红后绿：§2.3 新用例改动前逐例取 RED 写 `F07_red_evidence.txt`（逐例捕获 Exception 保留类型，按真实基线记 RED 或 GREEN→GREEN）。
- 0.8 不跑 `run_all.py`。定向跑：`python3 -B scripts/tests/test_audit_release_gate.py`、`test_engine_equivalence.py`（`:257-313` 用真 `replay_duck --only-addrs` 产收据，须仍绿——这是"真产物含全字段"的实证）、`test_peaks_daily.py`、`test_batch15_three_ledgers_frozen.py`、`test_repair_batch_d.py`、`test_stage2_closeout.py`、`python3 -B scripts/tests/invariant_scan.py`。全部须 PASS。（F12 环境项 `test_stage2_reseal.py::dry_run_touches_nothing` 由调度方全套验收处理。）

## 1. 硬约束

- 1.1 文档三处字节不变：SKILL.md 8021、references 930061、commands-staging 8798（命令同工单 F06 §1.1）。
- 1.2 `git diff --stat` 只含 0.3 白名单。
- 1.3 "案内三件生成产物（summary/needs/followup）皆无"仍 return（不强制所有案跑 peaks_daily，与现行契约一致）；`trigger_days.json` **不作定位依据**（`peaks_daily.py:91` 接受任意路径的 `--trigger-days` 原始清单，同名文件可能在 `data/` 等目录）；"多个产物目录"拒；"有目录但缺 summary"拒。
- 1.4 存量迁移代价（明示，属裁决已接受）：R09（7.2.0）前产出的 followup 收据缺 `producer`/`channels`/`value_type`/`count` → 本段起被拒，须用当前 `replay_duck.py --channels <通道清单> --out-dir <补算工作目录> --only-addrs <产物目录>/needs_block_precision.json --only-addrs <产物目录>/trigger_days.json`（两件都传：义务＝needs 各档 ∪ 触发日活跃候选，闸 `:1175/:1199` 绑定 trigger 哈希；首个 `--only-addrs` 决定收据落点 `:411`）重跑补算——只限制峰值聚合的地址范围，但仍执行全量通道校验、读取与去重（`:653/:666` 先物化全部 `raw_rows`），耗时与临时空间按案量评估，不是"成本小"；`producer.sha256` 与仓库当前 `scripts/evm/replay_duck.py` 不符同样拒（升级引擎即重跑补算）。

## 2. 逐条施工

### 2.1 `scripts/report/audit_release_gate.py` —— 定位改为"三件生成产物任一在场即进入检查"

替换 `:1077-1094`（锚起 `def _find_peaks_summaries(case_dir: Path) -> list[Path]:`，锚止 `    return hits`——`:1094` 的 `return hits` 在 `:1077-1094` 区间内唯一）为：

```python
PEAKS_DAILY_PRODUCTS = ("peaks_summary.json", "needs_block_precision.json",
                        "block_precision_followup.json")


def _find_peaks_dirs(case_dir: Path) -> list[Path]:
    """R09（7.2.0）：peaks_daily 产物根不限定案根——递归定位；跳过隐藏目录（.duck_tmp 等）、
    _history 与符号链接路径。F07（7.2.1）：三件**生成产物**任一在场即认定为峰值产物目录，
    改名 summary 不再使整段检查零命中；trigger_days.json 既是 --trigger-days 原始输入的常见名
    也是输出名，不作定位依据。单次遍历；返回去重排序后的目录列表。"""
    dirs = set()
    for p in case_dir.rglob("*.json"):
        if p.name not in PEAKS_DAILY_PRODUCTS:
            continue
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
        dirs.add(p.parent)
    return sorted(dirs)
```

替换 `:1104-1112`（锚起 `    hits = _find_peaks_summaries(case_dir)`，锚止 `    ps_path = hits[0]`）为：

```python
    dirs = _find_peaks_dirs(case_dir)
    if not dirs:
        return
    if len(dirs) > 1:
        errors.append("案内出现多个峰值产物目录（"
                      + ", ".join(str(h.relative_to(case_dir)) for h in dirs)
                      + "）——峰值产物根须唯一，清理陈旧目录后重验")
        return
    pd = dirs[0]
    ps_path = pd / "peaks_summary.json"
    if ps_path.is_symlink() or not ps_path.is_file():
        errors.append(f"峰值产物目录 {pd.relative_to(case_dir)} 缺 peaks_summary.json"
                      "（needs/trigger/followup 在场而 summary 缺席＝改名或残缺产物，拒）")
        return
```

紧随其后的 `:1113`（锚 `    pd = ps_path.parent`，唯一）**删除**（pd 已在上面赋值）。docstring `:1101-1103` 的 R09 三点后追加一行 `F07（7.2.1）：④summary/needs/followup 任一在场即检查（trigger_days 不作定位依据）；⑤followup 须绑定当前 replay_duck.py producer 与 channels 实物。`。

### 2.2 `scripts/report/audit_release_gate.py` —— followup 绑定 producer/channels/value_type/count

在 `:1190-1191`（锚 `    if fu.get("engine") != "replay_duck.py":` 与其 `errors.append(...)` 行）之后、`:1192`（锚 `    items = fu.get("inputs")`，在 `check_daily_peaks` 内唯一——注意 `_run` 内也可能有同名变量，锚要带前导 4 空格并限定在 `:1180-1230` 区间核）之前插入：

```python
    # F07（7.2.1）：消费 producer 已写出的绑定字段——自报收据（只有 engine 字符串）拒
    producer = fu.get("producer")
    engine_path = Path(__file__).resolve().parent.parent / "evm" / "replay_duck.py"
    if (not isinstance(producer, dict) or producer.get("path") != "replay_duck.py"
            or str(producer.get("sha256") or "").lower() != sha256_file(engine_path).lower()):
        errors.append("block_precision_followup.json producer 未绑定当前 scripts/evm/replay_duck.py"
                      "（缺 producer 或 sha256 不符）——旧收据/手写收据拒，用当前引擎重跑 --only-addrs")
    chan = fu.get("channels")
    chan_name = Path(str((chan or {}).get("path") or "")).name if isinstance(chan, dict) else ""
    chan_hits = [p for p in case_dir.rglob(chan_name)
                 if chan_name and p.is_file() and not p.is_symlink()
                 and not any(part.startswith(".") or part == "_history"
                             for part in p.relative_to(case_dir).parts)]
    if not chan_name or len(chan_hits) != 1 \
            or sha256_file(chan_hits[0]).lower() != str(chan.get("sha256") or "").lower():
        errors.append("block_precision_followup.json channels 未绑定案内唯一常规文件"
                      f"（{chan_name or '缺 path'}：命中 {len(chan_hits)} 个或 sha256 不符）——通道清单须随案")
    if fu.get("value_type") not in ("HUGEINT", "VARINT"):
        errors.append("block_precision_followup.json value_type 须为 HUGEINT/VARINT（replay_duck 写出）")
    addrs_obj = fu.get("addresses")
    if isinstance(addrs_obj, dict) and fu.get("count") != len(addrs_obj):
        errors.append("block_precision_followup.json count 与 addresses 条数不一致")
```

说明：①`sha256_file` 为本文件既有辅助（`:1132`/`:1147` 已用）；②`channels` 文件位置由 `replay_duck --channels` 调用者决定，producer 只记 basename，故消费侧按 basename 在案内 rglob（同 `_find_peaks_dirs` 过滤规则），要求**恰 1 个**常规文件且 sha 一致；③`addresses` 的形状检查仍由 `:1201-1204` 负责，这里只在它是 dict 时比对 count；④这些检查不 return，继续走既有 inputs/addresses 校验，错误累加。

### 2.3 `scripts/tests/test_audit_release_gate.py` —— 夹具补全字段＋新用例

- 夹具 `_r09_followup`（`:995-999`）改为写全字段：在 `pd` 下写 `channels.json`（内容 `{"fixture": "channels"}` 即可，闸不验内容）；返回 `{"schema": ..., "engine": "replay_duck.py", "producer": {"path": "replay_duck.py", "sha256": sha(REPO / "scripts/evm/replay_duck.py")}, "value_type": "HUGEINT", "inputs": [...同前...], "channels": {"path": "channels.json", "sha256": sha(pd / "channels.json")}, "count": len(addresses), "addresses": addresses}`（`REPO` 为本文件既有常量，开工 `grep -n '^REPO'` 核）。
- `r09_cases` 元组（`:1129-1143`）追加：
  14 `R09/F07 summary 改名仍检查`：`_r09_write_peaks(root/"data/peaks_daily", needs=["0xabc"])` 后 `rename` summary 为 `renamed_summary.json` → errors 含"缺 peaks_summary.json"。**RED**（基线 `[]`）。
  15 `F07 followup 缺 producer 拒`：`_r09_followup` 结果 `pop("producer")` → 含"producer 未绑定"。**RED**。
  16 `F07 followup producer sha 过期拒`：`producer.sha256="0"*64` → 含"producer 未绑定"。**RED**。
  17 `F07 followup channels 缺席拒`：删 `pd/channels.json` → 含"channels 未绑定"。**RED**。
  18 `F07 followup channels sha 不符拒`：改写 `channels.json` 内容不更新收据 → 含"channels 未绑定"。**RED**。
  19 `F07 count 不一致拒`：`count=7` → 含"count 与 addresses"。**RED**。
  20 `F07 只有 needs/trigger 无 summary 拒`：只写 needs＋trigger 两件（不写 summary）→ 含"缺 peaks_summary.json"。**RED**（基线 `[]`）。
  21 `F07 兼容：原始触发日清单在 data/ 不被误判（GREEN→GREEN）`：`_r09_write_peaks(root/"data/peaks_daily", needs=[])` 完整产物，另在 `root/"data/trigger_days.json"` 写一份原始清单 `{"schema": "trigger-days-replay/v1", "days": {}, "empty_reason": "raw input"}` → errors 不含 "多个峰值产物目录"/"缺 peaks_summary.json"。
  22 `F07 兼容：只有原始触发日清单、无峰值产物（GREEN→GREEN）`：先 `(root/"data").mkdir()`（`write_json` `:36-37` 不自动建目录），再只写 `root/"data/trigger_days.json"` → errors 不含 "峰值"/"peaks_summary" 字样。用例 21 同样先建目录后再 `_r09_write_peaks`（它自带 `mkdir(parents=True)`，但原始清单要单独写）。
- `:1154`（锚 `    assert not r09_failures, f"R09 失败 {len(r09_failures)}/13: {r09_failures}"`）的 `13` 改为 `{len(r09_cases)}`。
- 既有用例 2/12（GREEN→GREEN）与 3–13 用更新后的夹具须仍绿；用例 6"多份 summary 拒"文案若断言 `多份 peaks_summary.json`，改为断言"多个峰值产物目录"（开工 `grep -n '多份' scripts/tests/test_audit_release_gate.py` 核实并写进 done）。

RED 证据：改生产代码前逐例跑 14–22 记（21/22 按真实基线记 GREEN→GREEN） AssertionError/异常原文（含命令与被测文件 sha256）。

## 3. 完成报告 `F07_done.md` 必含

①0.1 三条命令输出；②2.1/2.2/2.3 `git diff` 原文；③RED 摘要；④0.8 各测试结果尾行；⑤1.1 三个字节数；⑥`git diff --stat`；⑦与工单差异/停工点（含 `invariant_manifest.json` 实际增补项）；⑧禁读披露。stdout 首行 `# 施工 F07：完成` 或 `# 施工 F07：停工`。

## 4. 登记不修（`code_change_pending.md`，调度方维护）

- 全套字段齐全的手写 followup（含正确 producer sha 与随案 channels）仍可过：闭合它需要闸侧按 channels 重放指定地址（引擎级复算），属另单；本段把"抄近路"的门槛从写 4 个字段抬到完整伪造引擎产物。
- `channels` 文件内容不验：preflight 校验属采集侧 `channels_preflight`。
- 峰值口径选择无冻结 manifest（"不用 peaks_daily 的案可不带产物"）：与现行契约一致，不扩。
- summary、needs、followup 三件生成产物**全部**不存在或全部改名时，闸无法区分"未跑 peaks_daily"与"隐藏全部产物"，属口径选择未冻结的同一残余；只剩 followup（或只剩 needs）时会因缺 summary 被拒，不是绕过路径。
