# 工单 T1（v2）：备份堆积与裁决台账瘦身 —— repair-20260916-three-items 第一批（分支 `fix/three-items-20260916`）

> 出处：用户 2026-09-16 批准的三项修复计划（`~/.claude/plans/tca-three-items-20260915.md` §2.3）。本批只做第 3 项。原则：**不增加 skill 上下文；能删的不新增，能改的不新增**。
> 基线：本仓库分支 `fix/three-items-20260916`，HEAD 为 `b4f80cd`（main 7.0.4＋W1）的后继（工单已 commit）。
> v2 变更：融合 codex 第一轮只读复核 12 条（`t1_review_reply.txt`）：旁车路径走 `safe_case_file`、B2 文案更正、B3 捕获 OSError、B4/A5 的 RED 重定义、scan-schemas 字节修正、白名单显式化、模块帮助同步。

## 0. 开工纪律

- 工作目录即本仓库物理路径 `/Users/uravvv/.claude/worktrees/tca-three-items`（独立克隆，origin 指向主仓库；**不要**碰 `/Users/uravvv/.claude/skills/token-chip-analysis`，那里另一会话在施工）。开工先 `git status --short`，除本目录 `maintenance/repair-20260916-three-items/` 外须为空。
- **行号均指施工前基线**（HEAD 的文件）；插入代码后按已核验的锚文本定位。行号与锚文本不一致时**停工**写 `t1_done_attempt1_stopped.md` 汇报，不得自行猜改。
- **禁止**读取 `/Users/uravvv/.codex/` 下任何文件、`/Users/uravvv/.claude/skills/_archive/`、git tag `codex-frozen-20260915`。
- 离线完成，无网络调用；不 `git fetch`；**不 commit**（Fable 代 commit）。
- **白名单**（只允许改这些文件）：生产 `scripts/report/adjudication_validator.py`、`scripts/report/handoff_manifest.py`；测试 `scripts/tests/test_adjudication_validator.py`、`scripts/tests/test_distribution_gate.py`、`scripts/tests/test_handoff_manifest.py`；文档 `references/split-run.md`、`references/scan-schemas.md`；本目录的证据文件。允许区域包括：新增辅助函数、`import re`、模块 docstring 帮助、安全路径处理。
- **不改** `adjudication_validator.py` 的 `cmd_validate`/`cmd_distribution_validate`/`cmd_pattern_validate`（validate 语义零变动）；**不改** `handoff_manifest.py` 的 `cmd_verify`/`_reverse_bound_reason`/`check_bound_file`/freeze 四道前置的任何判定与返回码；**不动** CHANGELOG/VERSION/pyproject（三批合并后统一）；**不动** `~/.claude/commands/token-analyze-2.md`（无对应句）。**不重写任何存量案卷台账**（台账内容变化会改整文件哈希）；兼容性只用测试夹具验证。
- 施工顺序 A → B → C。每段先跑 RED 再改生产代码；RED 的定义见各段末尾（C 段的 RED 是字节断言，不是 docs_lint）。RED 证据 `t1_red_evidence.txt` 每段必含：准确命令、退出码、输出原文、测试文件 sha256、被测生产文件 sha256。
- 全套 `run_all.py` 本机约 11 分钟：`nohup python3 scripts/tests/run_all.py > /tmp/run_all_t1.log 2>&1 &` 再等结果；禁止 `| tail`。沙箱若因本地端口 PermissionError 失败两项，如实记录，Fable 本机复跑。
- 完工写 `t1_done.md`：改动文件清单、每段 RED→GREEN 命令与结果、run_all 结果行、两个文档改前/改后字节数表、与工单差异（若有）、遗留。

## 1. A 段：`scripts/report/adjudication_validator.py` —— 删 `_members_total` 预填，成员清单改写旁车文件

### A1 新增模块级函数（放在 `def distribution_candidates(case_dir, scan_rel):`（`:193`）之前）

```python
def sidecar_rel(out_rel):
    """台账相对路径 → 同目录旁车相对路径：foo.json → foo.members.json。"""
    return out_rel[:-5] + ".members.json" if out_rel.endswith(".json") else out_rel + ".members.json"


def write_members_sidecar(side_path, members_by_cid):
    """成员清单旁车（派生件，总是覆盖；不进台账、不进 schema、不登记 data_map、无消费者）。
    side_path 须是调用方已用 safe_case_file 校验过的绝对路径。"""
    with open(side_path, "w", encoding="utf-8") as fh:
        json.dump({cid: sorted(m) for cid, m in sorted(members_by_cid.items())}, fh, ensure_ascii=False, indent=1)
    return side_path
```

### A2 `cmd_distribution_template`：旁车路径先校验，删预填，写旁车

- 在 `:226`（锚 `out_path = str(safe_case_file(case_dir, a.out, must_exist=False))`）同一 `try` 内紧接一行：`side_path = str(safe_case_file(case_dir, sidecar_rel(a.out), must_exist=False))`。旁车若是符号链接、目录、越界，沿用既有 `except ValueError` 报错并返回，**此时台账尚未写入**。
- `:238`（锚 `"net_supply_pct": row["scale_pct"], "_members_total": sorted(row["members"])}`）改为 `"net_supply_pct": row["scale_pct"]}`。
- `:240-242`（锚 `with open(out_path, "w", encoding="utf-8") as fh:` … `log(f"distribution 模板 {len(cands)} 条 → {out_path}")`）：写完台账后 `write_members_sidecar(side_path, {cid: row["members"] for cid, row in cands.items()})`，log 改为 `log(f"distribution 模板 {len(cands)} 条 → {out_path}（成员清单 → {os.path.basename(side_path)}）")`。

### A3 `cmd_template`：同法

- 找到该函数里 `out_path = str(safe_case_file(case_dir, a.out, must_exist=False))`（`:398` 之前不远处，锚文本同上）同一 `try` 内紧接 `side_path = str(safe_case_file(case_dir, sidecar_rel(a.out), must_exist=False))`。
- `:417`（锚 `"_members_total": sorted(c["members"]),`）整行删除；`:416` 行尾（锚 `"note": None},`）保持逗号即可。
- `:420-422`（锚 `with open(out_path, "w", encoding="utf-8") as f:` … `log(f"模板 {len(tpl['adjudications'])} 条候选 → {out_path}（成员级逐条填写后跑 validate）")`）：写完后 `write_members_sidecar(side_path, {cid: c["members"] for cid, c in cands.items()})`，log 改为 `…→ {out_path}（成员清单 → {os.path.basename(side_path)}；逐条填写后跑 validate）`。

### A4 帮助文案

- 模块 docstring `:11-12`（锚 `candidate_adjudications.json（id/candidate_sha256/成员全集/机器 tier_impact` / `预填，verdict 留空待 −2 逐条填写——candidate_sha256 不必手算）`）改为 `candidate_adjudications.json（id/candidate_sha256/机器 tier_impact 预填；成员清单另写` / `同目录旁车 <台账名>.members.json；verdict 留空待 −2 逐条填写）`（两行仍两行）。
- CLI `:581`（锚 `t = sub.add_parser("template", help="生成裁决模板（sha256/成员全集/机器 tier_impact 预填）")`）改为 `help="生成裁决模板（sha256/机器 tier_impact 预填；成员清单写同目录 <台账名>.members.json）"`。`:591` distribution-template 帮助文案追加同样半句"；成员清单写同目录 <台账名>.members.json"。

### A5 测试联动（RED 顺序已按复核意见重排）

- **先加独立契约用例**（放在 `test_adjudication_validator.py` `main()` 里**第一次 `fill_all` 调用（`:121`）之前**，用独立临时目录，不依赖 fill_all）：
  1. `template 不含 _members_total 且旁车在场`：`template --force` 后，台账每条记录无该键；`candidate_adjudications.members.json` 存在、键集合＝候选 id 集合、每个值非空列表。旁车不存在时通过 `check(...)` 输出 FAIL（不得抛异常）。
  2. `旁车路径不合法即拒且台账未写`：预置 `candidate_adjudications.members.json` 为**目录**（或符号链接）→ template 退出码非 0，且 `candidate_adjudications.json` 不存在。
- **再改联动读取**：`:99-101`（锚 `adj = json.load(open(os.path.join(d, "candidate_adjudications.json")))` … `members = r.pop("_members_total")`）：`:99` 后加 `side = json.load(open(os.path.join(d, "candidate_adjudications.members.json")))`，`:101` 改 `members = side[r["candidate_id"]]`。
- `scripts/tests/test_distribution_gate.py:377`（锚 `for x in row.pop("_members_total", [])]`）：同法从 `distribution_adjudications.members.json` 读 `side[row["candidate_id"]]`；旁车不存在时该用例应 FAIL（不要 `.get(…, [])` 静默）。并新增独立断言：distribution-template 后台账无 `_members_total`、旁车成员集合与源扫描候选成员**完全一致**。
- **兼容用例**（`test_adjudication_validator.py` 现有用例之后）：`老台账带 _members_total 仍 PASS`：`fill_all` 后给每条记录补回 `"_members_total": <该候选成员列表>` 写回，`validate` 退出码仍 0。
- RED：改生产代码前，用例 1 FAIL（旁车不存在）、用例 2 FAIL（旧代码不校验旁车即写台账）、`:101` 改后 fill_all 抛 FileNotFoundError（作为联动负测**单独**执行并记录异常，不当作末尾用例已跑）；改后全 GREEN。

## 2. B 段：`scripts/report/handoff_manifest.py` —— 精确排除规则、显式登记冲突报错、freeze 卫生 WARN

文件顶部无 `import re`，须在 `:1-9` 标准库 import 段按字母序补 `import re`。

### B1 排除规则 `:119`（锚 `EXCLUDE_SUFFIXES = (".log", ".duckdb.wal", ".lock", ".tmp", ".bak")`）

改为：
```python
EXCLUDE_SUFFIXES = (".log", ".duckdb.wal", ".lock", ".tmp")
# 历史副本/归档件精确规则（不用 _pre_、.vN. 等宽泛版本特征，避免误伤 balances_pre_launch.json / labels.v3.jsonl）：
#   basename 含 .bak_ 或以 .bak 结尾，或含 .superseded. 或以 .superseded 结尾；或路径任一目录分量恰为 _history
EXCLUDE_NAME_RE = re.compile(r"\.bak(_|$)|\.superseded(\.|$)")
HISTORY_DIR = "_history"


def is_excluded_path(rel):
    """manifest 收录排除判定（generate 与 −2 收口共用）：临时件后缀、历史副本命名、_history/ 目录。"""
    base = os.path.basename(rel)
    if base in EXCLUDE_NAMES or base.endswith(EXCLUDE_SUFFIXES) or EXCLUDE_NAME_RE.search(base):
        return True
    return HISTORY_DIR in rel.replace("\\", "/").split("/")[:-1]
```
（`EXCLUDE_NAMES` 定义在 `:120`，函数体引用它，函数须放在 `:120` 之后。）

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
- 说明（已核）：`:299-303` 与 `main:1653` 只捕获 `ValueError`/`Exception`，`SystemExit(2)` 穿透使 CLI 退出 2；直接调用 `cmd_generate` 时表现为抛出 `SystemExit` 而非返回整数。`add_explicit` 同时服务 `--include` 与 `--gate`（`:380`），所以 `--gate` 绑定排除路径也会被拒（B4 补测）。`cmd_verify` 不调 `add_path`，无须改。

### B3 案根卫生 WARN（freeze 分支，不改返回码）

- 新增模块级函数（放在 `def cmd_freeze(a):`（`:1366`）之前）：
```python
HYGIENE_RE = re.compile(r"\.bak(_|$)|_pre_|\.v\d+\.|\.superseded(\.|$)")


def case_hygiene_warnings(case_dir):
    """案根一级与 data/ 一级里疑似手工历史副本（只提醒不拒；−2 收口可复用）。扫描失败也只提醒。"""
    hits = []
    for sub in ("", "data"):
        d = os.path.join(case_dir, sub)
        if not os.path.isdir(d):
            continue
        try:
            names = sorted(os.listdir(d))
        except OSError as e:
            print(f"[freeze] WARN 卫生扫描跳过 {sub or '.'}（{e}）", file=sys.stderr)
            continue
        for name in names:
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
（`--check-unseal` 分支 `:1369-1430` 在此之前已 return，不调用卫生扫描。）

### B4 测试 `scripts/tests/test_handoff_manifest.py`（新增用例，登记进该文件 `main()` 既有流程；参照 `make_case`（`:73`，已建 `data/`）与 `setup_freezeable`（`:275`）夹具；`write_json`（`:63-65`）不建父目录，`_history/` 由测试自行 `os.makedirs`）

data_map 登记方式：读现有 `data_map.json`，向 `dm["files"]` **追加** `{"path": "balances_pre_launch.json", "source": "test"}` 等条目再写回；不替换原有 files、不用 items 结构。

1. `排除规则（保持行为）`：案目录放 `findings.md.bak_20260913`、`report.md.bak`、`_history/old.json`、`handoff_manifest.r0.superseded.json`（均不登记），`balances_pre_launch.json` 与 `data/labels.v3.jsonl` 登记 data_map → generate exit 0；manifest 路径集合不含前四者、含后两者。（未登记文件本就不会被收录，此条**不要求 RED**。）
2. `显式登记冲突`：data_map 登记 `x.bak_2026`（文件在场）→ generate exit 2，stderr 含"命中排除规则"；另案 `--include _history/y.json`（文件在场）→ exit 2 同文案；再一案 `--gate custom:PASS:0:_history/z.json` → exit 2 同文案。
3. `freeze 卫生 WARN`：顺序 `make_case → generate READY 并断言 exit 0 → setup_freezeable → 放入 report.md.bak_v7d_ 与 data/entity_series.v2.json（不登记）→ freeze`：exit 与不放时相同（应为 0）且 stderr 含"WARN 案根疑似历史副本 2 件"。同案再跑 `freeze --check-unseal`：stderr **不含**"疑似历史副本"。
4. `卫生扫描失败不改返回码`：直接调用 `case_hygiene_warnings(tmp)`，先 `os.chmod(tmp/data, 0)`（`finally` 恢复 0o755）→ 不抛异常、返回列表、stderr 含"卫生扫描跳过"。
5. `is_excluded_path` 单元：`("a/_history/b.json", True)`、`("_history_x/b.json", False)`、`("x.bak_v7d_", True)`、`("x.bakup.json", False)`、`("balances_pre_launch.json", False)`、`("data/labels.v3.jsonl", False)`、`("x.superseded", True)`。
- RED：改生产代码前，用例 2 三案均 exit 0（旧代码静默丢弃）、用例 3 无 WARN、用例 4/5 因函数不存在 ImportError（记录为 FAIL）；以原文入证据。不得为制造 RED 给生产代码加全目录扫描。

## 3. C 段：条文（只替换；每个文件改后字节数 ≤ 改前）

改前字节（`wc -c`）：`references/split-run.md` 28162、`references/scan-schemas.md` 104942。C 段的 RED＝这两个数先写入证据；GREEN＝改后 `wc -c` 分别 ≤ 28162、≤ 104942（预期 28135、104941），写进 done。

- `references/split-run.md:109`（锚 `- **生成纪律**：原子生成（tmp+rename）`）整行替换为：
  `- **生成纪律**：原子生成（tmp+rename）、不含自身哈希；新增产物走 `late_additions`（重跑 generate，旧件自动归档带 run_id）；手工副本只进 `<案根>/_history/`，活跃路径唯一。`
- `references/split-run.md:110`（锚 `- **−2 重生成纪律**：首次 freeze 前`）整行替换为：
  `- **−2 重生成纪律**：首次 freeze 前可直接重跑 generate 再重跑一次溯源（`entity_source_trace`）即收敛；freeze 后再 generate 会使 entity_freeze 记的 manifest sha/run_id 过期（check-unseal 拒绝），须连锁重跑 trace → freeze revision → 受影响的 A4 / final 分布扫描 / A5。`
  （两行合计 −27 字节；`:90/:91` 产物表**不动**。）
- `references/scan-schemas.md:207-208`（锚 `"_members_total": [addr…]          # template 预填的候选成员全集` 与下一行 `#   validator 以源报告重算为准不读此字段）`）两行合并为一行：
  `    # template 不再预填 _members_total；候选成员清单在旁车 <台账名>.members.json（validator 以源报告重算为准）`
- `references/scan-schemas.md:523-524`（锚 `"raw_balance": str, "net_supply_pct": float,` / `"_members_total": [addr]`）：`:523` 去掉行尾逗号；`:524` 替换为：
  `    # excluded 的 reason 写简短一句（同类成员同句），详细依据放 evidence；validator 只查 reason 非空`
  （"简短一句"与证据写法是填写纪律，校验器只强制 reason 非空——文案不得声称校验器强制更多。）
- `~/.claude/commands/token-analyze-2.md`：无"归档/备份/留底"句，**不改**。
- 改后跑 `python3 scripts/tests/docs_lint.py --all` 须 PASS（这是回归检查，不是 C 的 RED）。

## 4. 完成标准

- A1–A5、B1–B4、C 段落地；新用例 GREEN；三份测试文件其余既有断言不改且 PASS；run_all 全绿（分母不变：新用例都在既有文件内）。
- `cmd_validate`/`cmd_distribution_validate`/`cmd_pattern_validate` 函数体不得有新增或删除行（diff 上下文行不计）。
- 两个文档字节数不增。
- `t1_red_evidence.txt`、`t1_done.md` 在本目录；不 commit。
