# 工单 T3（v2，T1 落地 55b56c2 后重锚行号）：高频机械活稳定命令 —— `handoff_manifest.py inspect / lookup` 两个只读分页子命令

> 出处：用户 2026-09-16 批准的三项修复计划 §2.2（裁决：本轮只做 inspect/lookup；`q` SQL、写入型入口不做）。原则：**不增加 skill 上下文；能删的不新增，能改的不新增**。
> 基线：分支 `fix/three-items-20260916`，在 T1 之后施工（T1 改同一文件的 :119-:120 / :254-:266 / :1366 前 / :1432 前；本单只在文件末尾 argparse 段与新函数区施工，行号以 T1 落地后重新 `nl -ba` 核对锚文本为准）。
> 动机（实测）：五个 −2 会话 1,411 条手写 python 里，schema 探测 495 条、按地址跨文件查字段 335 条。两个子命令只覆盖这两类，不做聚合/SQL/改写。

## 0. 开工纪律

- 工作目录 `/Users/uravvv/.claude/worktrees/tca-three-items`（独立克隆；**不要**碰 `/Users/uravvv/.claude/skills/token-chip-analysis`）。开工 `git status --short` 除 `maintenance/repair-20260916-three-items/` 外须为空。
- 锚文本不一致即停工写 `t3_done_attempt1_stopped.md`。**禁止**读取 `/Users/uravvv/.codex/`、`/Users/uravvv/.claude/skills/_archive/`、tag `codex-frozen-20260915`。离线；不 commit。
- **白名单**：`scripts/report/handoff_manifest.py`（只允许：新增两个 `cmd_inspect`/`cmd_lookup` 及其辅助函数、argparse 两个新 parser、dispatch 字典两项）、`scripts/tests/test_handoff_manifest.py`（新增用例）、`references/split-run.md:72`、`references/context-discipline.md:27`、本目录证据文件。**不改** generate/verify/receipt/freeze 任何既有逻辑与文案；不动 CHANGELOG/VERSION/pyproject。
- 两个子命令**只读**：不得 open(…, "w")、不得写收据、不得改 manifest；不引入 duckdb/pandas 等新依赖（标准库 json/argparse/os）。
- 完工写 `t3_done.md`：改动清单、RED→GREEN、run_all 结果行、两个文档改前/改后字节数、FORGGIE 实跑留给 Fable（案卷在仓库外）。

## 1. 共同的路径守卫（辅助函数，放在 `def cmd_freeze(a):` 之前的新函数区）

```python
def _readonly_case_file(case_dir, rel):
    """inspect/lookup 共用：案根内常规文件（safe_case_file 三验），且不得进 sealed/（密封纪律：只有 freeze --check-unseal 把关后才可读）。"""
    norm = rel.replace("\\", "/")
    if norm == "sealed" or norm.startswith("sealed/"):
        raise ValueError(f"sealed/ 下文件不得用只读查询工具读取（揭盲走 freeze --check-unseal）: {rel}")
    return str(safe_case_file(case_dir, rel))
```
`safe_case_file` 已在 `:44` 导入（`from case_paths import safe_case_dir, safe_case_file`）。案外路径、符号链接、`..` 均由它抛 `ValueError`；两个子命令捕获后 `print(f"[{subcmd}] 路径非法: {e}", file=sys.stderr); return 2`。

## 2. `inspect`：JSON 键树/类型/长度/样本，分页

用法：`handoff_manifest.py inspect --case-dir D --file <rel> [--path a.b.0] [--depth 2] [--limit 30] [--offset 0]`

- 读取：`.json` → `json.load`；`.jsonl` → 逐行 `json.loads` 成 list（空行跳过，坏行计入 `bad_lines` 计数并继续，不中断）；其他后缀 → exit 2 "只支持 .json/.jsonl"。
- `--path`：点分路径，段是整数则按 list 下标；不存在 → exit 2 "路径不存在: <段>"。
- 输出（纯文本，stdout，每行一个节点，缩进 2 空格/层）：
  - dict：按 key **排序**，从 `--offset` 起最多 `--limit` 个：`key: <type>` 后跟 `len=N`（容器）或 `= <repr 截 80 字符>`（标量）；子层递归到 `--depth`（默认 2）。
  - list：`list len=N`，只展开首元素 `[0]`（递归同上），不遍历。
  - 首行 `file=<rel> bytes=<n> path=<--path 或 .>`；末行 `total=<本层键数> returned=<本次> truncated=<true|false> next_offset=<k>`（list 节点 total=len，returned 恒 ≤1）。
- 退出码：0 正常；2 路径非法/不存在/不支持。**不写任何文件**。

## 3. `lookup`：按地址清单跨文件回填字段，分页

用法：`handoff_manifest.py lookup --case-dir D (--addr A [--addr B …] | --addr-file <rel>) --in <rel> [--in <rel> …] [--fields f1,f2] [--limit 50] [--offset 0] [--json]`

- 地址归一：形如 `0x`＋40 位十六进制 → 小写；其他（Solana base58 等）原样、区分大小写。`--addr-file`：案内文本文件（同守卫），每行一个地址，`#` 开头与空行跳过。
- 每个 `--in` 文件建索引 `{norm(addr): record}`，识别规则（按序，命中任一即用）：
  1. 顶层 dict 且存在 key 归一后等于任一查询地址 → 以 key 为地址（identity_cards / 标签 dict 形态）；
  2. 顶层 dict 中值为 list/dict 的容器（如 `entities/rows/items/records/holders/balances/addresses/cards/labels`，或**任何**值为 list-of-dict 的键）→ 对其元素按规则 3；
  3. list-of-dict 或 `.jsonl` 行：取首个存在的键 `addr / address / owner / wallet / account` 为地址；
  4. 记录若含 `members`/`addresses` 列表（实体名册形态 `{entity_id:[addr…]}` 或 `{"members":[…]}`）→ 列表内每个地址也索引到该记录（`entity_registry` 用例）。
  同一地址在同一文件多次命中 → 保留全部（列表），输出标 `n=<k>`。
- 输出：按查询地址顺序、从 `--offset` 起最多 `--limit` 个地址；每地址一块：`<addr>` 行，其下每个 `--in` 文件一行：`  <rel>: MISSING` 或 `  <rel>: {字段…}`——有 `--fields` 时只取这些字段（缺的写 `<f>=MISSING_FIELD`），无 `--fields` 时输出记录的 key 列表＋前 3 个标量字段值（截 80 字符）。`--json` 时改输出一个 JSON 对象 `{"query":[…],"files":[…],"rows":[{"addr":…, "hits":{rel: null|record|[records]}}],"total","returned","truncated","next_offset"}`（完整记录，不截断——截断只影响文本显示）。
- 末行（文本模式）：`total=<地址数> returned=<n> truncated=<bool> next_offset=<k> missing=<全部文件均 MISSING 的地址数>`。
- 退出码：0 正常（含 MISSING）；2 路径非法/文件不可解析/无查询地址。

## 4. argparse 与 dispatch（`main()` `:1647-1696`）

- 在 `f = sub.add_parser("freeze", …)` 段之后（`:1688` 锚 `f.add_argument("--check-unseal", action="store_true")` 之后）加两个 parser，帮助文案：`inspect`＝"只读：JSON/JSONL 键树、类型、长度、样本（分页），代替手写 python 探 schema"；`lookup`＝"只读：按地址清单跨文件回填字段（分页），代替手写 python 跨文件查"。
- `:1692-1693`（锚 `return {"generate": cmd_generate, "verify": cmd_verify,` / `"receipt": cmd_receipt, "freeze": cmd_freeze}[a.subcmd](a)`）字典加 `"inspect": cmd_inspect, "lookup": cmd_lookup`。

## 5. 测试 `scripts/tests/test_handoff_manifest.py`（新增用例，登记进 `main()`；夹具 `make_case`（`:73`）已建 `data/`）

夹具文件（用 `write_json`，jsonl 自写）：`data/identity_cards.json`＝`{"0xAbC…(40 位)": {"kind":"eoa","label":"W1"}, "0xdef…": {...}}`（含大写 key）；`data/balances_final.json`＝`[{"addr":"0xabc…","balance":"10","pct":1.5}, {"addr":"0x999…",…}]`；`data/labels.jsonl`＝两行 `{"address":…, "name":…}`＋一行坏 JSON；`data/entity_registry.json`＝`{"E1":{"members":["0xabc…","0x999…"]}}`；`sealed/x.json`＝任意。

1. `inspect 键树与分页`：对 `data/identity_cards.json` `--limit 1` → stdout 首行 `file=` 、含第一个 key（排序后）、末行 `total=2 returned=1 truncated=true next_offset=1`；`--offset 1` → `truncated=false`。`--path <key>.kind` → 输出标量 `= 'eoa'`。
2. `inspect jsonl 坏行不中断`：`data/labels.jsonl` → exit 0，输出含 `list len=2`、`bad_lines=1`。
3. `inspect 守卫`：`--file sealed/x.json` → exit 2，stderr 含"sealed/"；`--file ../outside.json` → exit 2；`--file data/nope.json` → exit 2。
4. `lookup 三文件回填`：`--addr 0xabc…（小写）--addr 0x999… --in data/identity_cards.json --in data/balances_final.json --in data/entity_registry.json --fields label,balance` → `0xabc…` 块：identity_cards 行含 `label=W1`、balances 行含 `balance=10`、entity_registry 行非 MISSING（经 members 命中）；`0x999…` 块：identity_cards 行 `MISSING`；末行 `total=2 returned=2 truncated=false missing=0`。
5. `lookup --addr-file 与 --json`：地址文件含注释行与空行 → `--json` 输出可 `json.loads`，`rows[0]["hits"]["data/identity_cards.json"]["label"] == "W1"`（大小写归一命中）。
6. `lookup 守卫`：`--in sealed/x.json` → exit 2；无 `--addr`/`--addr-file` → exit 2；`--limit 1` 分页 `next_offset=1`。
7. `只读断言`：用例 1–6 前后对案目录做一次文件清单＋sha 快照比对，完全一致（子命令零写入）。
- RED：改生产代码前，`inspect`/`lookup` 子命令不存在 → argparse exit 2（记录 stderr "invalid choice"）；改后全 GREEN。

## 6. 条文（只替换现有行；每文件字节不增）

改前 `wc -c`：`references/split-run.md` 28162（T1 落地后为 28135，以 T3 开工时实测为准）、`references/context-discipline.md` 9257。

- `references/split-run.md:72`（锚 `机器权威源一律 JSON；md 仅渲染层可选。工具：`）整行替换为：
  `机器权威源一律 JSON；md 仅渲染层可选。工具：`scripts/report/handoff_manifest.py`（子命令 `generate / verify / receipt / freeze / inspect / lookup`；后两个只读分页：看键树、按地址批查字段）。`（−5 字节；删去的"schema 常量内嵌／测试进 run_all"是仓库事实，run_all SUITE 本就登记）
- `references/context-discipline.md:27`（锚 `   历史清单项（标准脚本跑批与重试循环/对账四查执行侧/标签库批量 lookup/`）整行替换为：
  `   历史清单项（脚本跑批与重试循环/对账四查执行/键树与地址批查（`handoff_manifest.py inspect/lookup`）/大户批量排查/图表脚本执行/数据完整性验证/逐地址溯源 fan-out）继续有效；已归 −1 的项在 −1 内完成。`（−1 字节）
- 不加"禁止手写 python"条文。改后 `python3 scripts/tests/docs_lint.py --all` PASS。

## 7. 完成标准

- 两个子命令按 §2/§3 行为落地，§5 七条用例 GREEN，既有用例不改；run_all 全绿（nohup 落文件）。
- `git diff scripts/report/handoff_manifest.py` 只含新增函数、两个 parser、dispatch 两项；既有函数体零改动。
- 两个文档字节 ≤ 改前；docs_lint PASS。
- Fable 本机验收：FORGGIE 案卷 `inspect data/entity_series.json --depth 1`、`lookup --addr-file <案内清单> --in identity_cards.json --in balances_final.json` 实跑，exit 0、输出分页可读。
- `t3_red_evidence.txt`、`t3_done.md` 在本目录；不 commit。
