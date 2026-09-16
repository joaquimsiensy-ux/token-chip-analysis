# 工单 T1（v1）：备份堆积与裁决台账瘦身 —— repair-20260916-three-items 第一批（分支 `fix/three-items-20260916`）

> 出处：用户 2026-09-16 批准的三项修复计划（`~/.claude/plans/tca-three-items-20260915.md` §2.3）。本批只做第 3 项。原则：**不增加 skill 上下文；能删的不新增，能改的不新增**。
> 基线：本仓库分支 `fix/three-items-20260916`，HEAD 为 `b4f80cd`（main 7.0.4＋W1）的后继（工单已 commit）。

## 0. 开工纪律

- 工作目录即本仓库物理路径 `/Users/uravvv/.claude/worktrees/tca-three-items`（独立克隆，origin 指向主仓库；**不要**碰 `/Users/uravvv/.claude/skills/token-chip-analysis`，那里另一会话在施工）。开工先 `git status --short`，除本目录 `maintenance/repair-20260916-three-items/` 外须为空。
- 行号旁附锚文本；若行号与锚文本不一致，**停工**写 `t1_done_attempt1_stopped.md` 汇报，不得自行猜改。
- **禁止**读取 `/Users/uravvv/.codex/` 下任何文件、`/Users/uravvv/.claude/skills/_archive/`、git tag `codex-frozen-20260915`。
- 离线完成，无网络调用；不 `git fetch`；**不 commit**（Fable 代 commit）。
- **不改** `adjudication_validator.py` 的 `cmd_validate`/`cmd_distribution_validate`/`cmd_pattern_validate`（validate 语义零变动）；**不改** `handoff_manifest.py` 的 `cmd_verify`/`_reverse_bound_reason`/`check_bound_file`/freeze 四道前置的任何判定与返回码；**不动** CHANGELOG/VERSION/pyproject（三批合并后统一）；**不动** `~/.claude/commands/token-analyze-2.md`（无对应句，见 C 段）。
- 施工顺序 A → B → C。每段先跑 RED 再改生产代码。RED 证据 `t1_red_evidence.txt` 每段必含：准确命令、退出码、输出原文、测试文件 sha256、被测生产文件 sha256。
- 全套 `run_all.py` 本机约 11 分钟：`nohup python3 scripts/tests/run_all.py > /tmp/run_all_t1.log 2>&1 &` 再等结果；禁止 `| tail`。沙箱若因本地端口 PermissionError 失败两项，如实记录，Fable 本机复跑。
- 完工写 `t1_done.md`：改动文件清单、每段 RED→GREEN 命令与结果、run_all 结果行、五个文档改前/改后字节数表、与工单差异（若有）、遗留。

## 1. A 段：`scripts/report/adjudication_validator.py` —— 删 `_members_total` 预填，成员清单改写旁车文件

### A1 新增模块级函数（放在 `def distribution_candidates(case_dir, scan_rel):`（`:193`）之前）

```python
def write_members_sidecar(out_path, members_by_cid):
    """成员清单旁车：<台账名>.members.json，内容 {candidate_id: [addr…]}（派生件，总是覆盖；不进台账、不进 schema、无消费者）。"""
    side = out_path[:-5] + ".members.json" if out_path.endswith(".json") else out_path + ".members.json"
    with open(side, "w", encoding="utf-8") as fh:
        json.dump({cid: sorted(m) for cid, m in sorted(members_by_cid.items())}, fh, ensure_ascii=False, indent=1)
    return side
```

### A2 `cmd_distribution_template`：删预填，写旁车

- `:238`（锚 `"net_supply_pct": row["scale_pct"], "_members_total": sorted(row["members"])}`）改为 `"net_supply_pct": row["scale_pct"]}`。
- `:240-242`（锚 `with open(out_path, "w", encoding="utf-8") as fh:` … `log(f"distribution 模板 {len(cands)} 条 → {out_path}")`）：写完台账后调用 `side = write_members_sidecar(out_path, {cid: row["members"] for cid, row in cands.items()})`，log 改为 `log(f"distribution 模板 {len(cands)} 条 → {out_path}（成员清单 → {os.path.basename(side)}）")`。

### A3 `cmd_template`：同上

- `:417`（锚 `"_members_total": sorted(c["members"]),`）整行删除；`:416` 行尾（锚 `"note": None},`）保持逗号即可（dict 字面量尾逗号合法）。
- `:420-422`（锚 `with open(out_path, "w", encoding="utf-8") as f:` … `log(f"模板 {len(tpl['adjudications'])} 条候选 → {out_path}（成员级逐条填写后跑 validate）")`）：写完后 `side = write_members_sidecar(out_path, {cid: c["members"] for cid, c in cands.items()})`，log 改为 `…→ {out_path}（成员清单 → {os.path.basename(side)}；逐条填写后跑 validate）`。

### A4 CLI 帮助 `:581`（锚 `t = sub.add_parser("template", help="生成裁决模板（sha256/成员全集/机器 tier_impact 预填）")`）

改为 `help="生成裁决模板（sha256/机器 tier_impact 预填；成员清单写旁车 <out>.members.json）"`。`:591` distribution-template 帮助文案追加同样半句"；成员清单写旁车"。

### A5 测试联动

- `scripts/tests/test_adjudication_validator.py:101`（锚 `members = r.pop("_members_total")`）：改为从旁车读——在 `:99`（锚 `adj = json.load(open(os.path.join(d, "candidate_adjudications.json")))`）之后加 `side = json.load(open(os.path.join(d, "candidate_adjudications.members.json")))`，`:101` 改 `members = side[r["candidate_id"]]`。
- `scripts/tests/test_distribution_gate.py:377`（锚 `for x in row.pop("_members_total", [])]`）：同法，从 `d / "distribution_adjudications.members.json"` 读 `side[row["candidate_id"]]`；旁车文件不存在时该用例应 FAIL（不要 `.get(…, [])` 静默）。
- **新增两条用例**（放在 `test_adjudication_validator.py` 现有用例之后，按该文件既有 `check(...)` 风格）：
  1. `template 不含 _members_total 且旁车在场`：template 后台账每条记录无该键；旁车文件存在、键集合＝候选 id 集合、每个值非空列表。
  2. `老台账带 _members_total 仍 PASS`：`fill_all` 后给每条记录补回 `"_members_total": <该候选成员列表>` 再写回，`validate` 退出码仍 0（证明删预填不改 validate 语义）。
- RED：改生产代码前先改测试，用例 1 必 FAIL（旁车不存在）、`:101` 改后 fill_all 必 FAIL；改后全 GREEN。

## 2. B 段：`scripts/report/handoff_manifest.py` —— 精确排除规则、显式登记冲突报错、freeze 卫生 WARN

### B1 排除规则 `:119`（锚 `EXCLUDE_SUFFIXES = (".log", ".duckdb.wal", ".lock", ".tmp", ".bak")`）

改为：
```python
EXCLUDE_SUFFIXES = (".log", ".duckdb.wal", ".lock", ".tmp")
# 历史副本/归档件精确规则（不用 _pre_、.vN. 等宽泛版本特征，避免误伤 balances_pre_launch.json / labels.v3.jsonl）：
#   basename 命中 .bak / .bak_<任意> / *.superseded.json 族；或路径任一目录分量恰为 _history
EXCLUDE_NAME_RE = re.compile(r"\.bak(_|$)|\.superseded(\.|$)")
HISTORY_DIR = "_history"


def is_excluded_path(rel):
    """manifest 收录排除判定（generate 与 −2 收口共用）：临时件后缀、历史副本命名、_history/ 目录。"""
    base = os.path.basename(rel)
    if base in EXCLUDE_NAMES or base.endswith(EXCLUDE_SUFFIXES) or EXCLUDE_NAME_RE.search(base):
        return True
    return HISTORY_DIR in rel.replace("\\", "/").split("/")[:-1]
```
（`EXCLUDE_NAMES` 定义在 `:120`，函数体引用它须放在 `:120` 之后；确认文件顶部已 `import re`，没有则补。）

### B2 `add_path` 显式登记命中排除即报冲突 `:254-266`

- 签名改 `def add_path(rel, explicit=False):`。
- `:262-264`（锚 `base = os.path.basename(rel)` / `if base in EXCLUDE_NAMES or base.endswith(EXCLUDE_SUFFIXES):` / `return`）改为：
```python
        if is_excluded_path(rel):
            if explicit:
                print(f"[generate] 显式登记的路径命中排除规则（历史副本/临时件/_history 不得进 manifest，请移出登记或改名）: {rel}",
                      file=sys.stderr)
                raise SystemExit(2)
            return
```
- 调用点：`:298`（锚 `add_path(ent.get("path"))`）改 `add_path(ent.get("path"), explicit=True)`；`:280`（`add_explicit` 内锚 `add_path(rel)`）改 `add_path(rel, explicit=True)`；`:271`（`discover` 内）不传，保持自动发现静默跳过。
- `:298` 所在 try 只捕获 `ValueError`/`Exception`，`SystemExit` 会穿透到 `cmd_generate` 返回 2——确认 `cmd_generate` 无外层 `except Exception` 吞掉它（若有，改为显式 `return 2`）。

### B3 案根卫生 WARN（freeze 分支，不改返回码）

- 新增模块级函数（放在 `def cmd_freeze(a):`（`:1366`）之前）：
```python
HYGIENE_RE = re.compile(r"\.bak(_|$)|_pre_|\.v\d+\.|\.superseded(\.|$)")


def case_hygiene_warnings(case_dir):
    """案根一级与 data/ 一级里疑似手工历史副本（只提醒不拒；−2 收口可复用）。"""
    hits = []
    for sub in ("", "data"):
        d = os.path.join(case_dir, sub)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if os.path.isfile(os.path.join(d, name)) and HYGIENE_RE.search(name):
                hits.append(os.path.join(sub, name) if sub else name)
    return hits
```
- 在 `cmd_freeze` 的 `:1432`（锚 `if not a.members:`）之前插入：
```python
    hygiene = case_hygiene_warnings(case_dir)
    if hygiene:
        shown = ", ".join(hygiene[:10]) + ("…" if len(hygiene) > 10 else "")
        print(f"[freeze] WARN 案根疑似历史副本 {len(hygiene)} 件（请移入 _history/，不影响冻结）: {shown}", file=sys.stderr)
```
（`--check-unseal` 分支在此之前已 return，不受影响。）

### B4 测试 `scripts/tests/test_handoff_manifest.py`（新增用例，登记进该文件 `main()` 既有流程；参照 `make_case`（`:73`）与 `setup_freezeable`（`:275`）夹具）

1. `排除规则`：案目录放 `findings.md.bak_20260913`、`report.md.bak`、`_history/old.json`、`handoff_manifest.r0.superseded.json`（均**不**登记 data_map），`balances_pre_launch.json` 与 `labels.v3.jsonl` **登记** data_map → generate exit 0；manifest `artifacts` 路径集合不含前四者、含后两者。
2. `显式登记冲突`：data_map 登记 `x.bak_2026` → generate exit 2，stderr 含"命中排除规则"；另案 `--include _history/y.json`（文件在场）→ exit 2 同文案。
3. `freeze 卫生 WARN`：`setup_freezeable` 案根放 `report.md.bak_v7d_`、`data/entity_series.v2.json` → freeze exit 0（与不放时相同）且 stderr 含"WARN 案根疑似历史副本 2 件"。
4. `is_excluded_path` 单元：`("a/_history/b.json", True)`、`("_history_x/b.json", False)`、`("x.bak_v7d_", True)`、`("x.bakup.json", False)`、`("balances_pre_launch.json", False)`、`("data/labels.v3.jsonl", False)`。
- RED：改生产代码前，用例 1 中 `findings.md.bak_20260913` 被收录、用例 2 exit 0、用例 3 无 WARN，须以 FAIL 原文入证据。

## 3. C 段：条文（只替换；每个文件改后字节数 ≤ 改前）

改前字节：`references/split-run.md` 28162、`references/scan-schemas.md` 104942（`wc -c`）。改后 `wc -c` 写进 done。

- `references/split-run.md:109`（锚 `- **生成纪律**：原子生成（tmp+rename）`）整行替换为：
  `- **生成纪律**：原子生成（tmp+rename）、不含自身哈希；新增产物走 `late_additions`（重跑 generate，旧件自动归档带 run_id）；手工副本只进 `<案根>/_history/`，活跃路径唯一。`
- `references/split-run.md:110`（锚 `- **−2 重生成纪律**：首次 freeze 前`）整行替换为：
  `- **−2 重生成纪律**：首次 freeze 前可直接重跑 generate 再重跑一次溯源（`entity_source_trace`）即收敛；freeze 后再 generate 会使 entity_freeze 记的 manifest sha/run_id 过期（check-unseal 拒绝），须连锁重跑 trace → freeze revision → 受影响的 A4 / final 分布扫描 / A5。`
  （两行合计 −27 字节；`:90/:91` 产物表**不动**。）
- `references/scan-schemas.md:207-208`（锚 `"_members_total": [addr…]          # template 预填的候选成员全集` 与下一行 `#   validator 以源报告重算为准不读此字段）`）两行合并为一行：
  `    # template 不再预填 _members_total；候选成员清单在旁车 <台账名>.members.json（validator 以源报告重算为准）`
- `references/scan-schemas.md:523-524`（锚 `"raw_balance": str, "net_supply_pct": float,` / `"_members_total": [addr]`）：`:523` 去掉行尾逗号；`:524` 替换为：
  `    # excluded 的 reason 写简短可直读一句（同类成员同句），详细依据放 evidence；validator 只查 reason 非空`
- `~/.claude/commands/token-analyze-2.md`：grep 无"归档/备份/留底"句，**不改**（不新增行）。
- 改后跑 `python3 scripts/tests/docs_lint.py --all` 须 PASS。

## 4. 完成标准

- A1–A5、B1–B4、C 段落地；新用例 GREEN；`test_adjudication_validator.py`、`test_distribution_gate.py`、`test_handoff_manifest.py` 及其余既有测试不改断言（A5 两处联动除外）且 PASS；run_all 全绿（分母不变：新用例都在既有文件内）。
- `validate`/`distribution-validate` 生产代码零 diff（`git diff` 中不得出现这两个函数的行）。
- 两个文档字节数不增。
- `t1_red_evidence.txt`、`t1_done.md` 在本目录；不 commit。
