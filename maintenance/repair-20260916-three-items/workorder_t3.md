# 工单 T3（v3，融合 codex 第一轮复核 `t3_review_reply.txt` 六项）：高频机械活稳定命令 —— `handoff_manifest.py inspect / lookup` 两个只读分页子命令

> 出处：用户 2026-09-16 批准的三项修复计划 §2.2（裁决：本轮只做 inspect/lookup；`q` SQL、写入型入口不做）。原则：**不增加 skill 上下文；能删的不新增，能改的不新增**。
> 基线：分支 `fix/three-items-20260916`，在 T1（55b56c2）与 T2 之后施工；本单只在 `def cmd_freeze(a):` 前的新函数区与文件末尾 argparse 段施工，行号以开工时 `nl -ba` 核对锚文本为准（v2 已按 T1 落地重锚：导入 :44、cmd_freeze :1402、main :1647、`--check-unseal` :1688、dispatch :1692-1693）。
> v3 变更：§1 守卫改 casefold 判首段并写明边界；§2 分页/深度/路径/错误语义补全，jsonl 的 `bad_lines` 进末行；§3 索引规则改"选记录→每条记录跑规则 3＋4"、混合顶层全扫、`--json` 与计数语义定死；§5 地址常量固定、七条用例补反例与只读运行检查、RED 断言错误文本；§7 验收命令补 `--case-dir/--file` 与 `python3 -B`；§0 写明"零写入"指案目录。
> 动机（实测）：五个 −2 会话 1,411 条手写 python 里，schema 探测 495 条、按地址跨文件查字段 335 条。两个子命令只覆盖这两类，不做聚合/SQL/改写。

## 0. 开工纪律

- 工作目录 `/Users/uravvv/.claude/worktrees/tca-three-items`（独立克隆；**不要**碰 `/Users/uravvv/.claude/skills/token-chip-analysis`）。开工 `git status --short` 除 `maintenance/repair-20260916-three-items/` 外须为空。
- 锚文本不一致即停工写 `t3_done_attempt1_stopped.md`。**禁止**施工者本人读取 `/Users/uravvv/.codex/`、`/Users/uravvv/.claude/skills/_archive/`、tag `codex-frozen-20260915` 作为参考（被测代码自身的 `git_sha` 探测是既有行为，允许原样运行）。离线；不 commit。
- **白名单**：`scripts/report/handoff_manifest.py`（只允许：新增 `_readonly_case_file`、`cmd_inspect`、`cmd_lookup` 及其辅助函数，argparse 两个新 parser，dispatch 字典两项）、`scripts/tests/test_handoff_manifest.py`（新增用例＋在 `main()` 末尾登记调用，`:531` 附近）、`references/split-run.md:72`、`references/context-discipline.md:27`、本目录证据文件。**不改** generate/verify/receipt/freeze 任何既有逻辑与文案；不动 CHANGELOG/VERSION/pyproject。
- 两个子命令**只读**："零写入"指**案目录**零写入：不得 open(…, "w")、不得写收据、不得改 manifest、不得建临时文件；解释器字节码缓存落在 skill 目录不在此列，验收与测试一律用 `python3 -B` 调用。不引入 duckdb/pandas 等新依赖（标准库 json/argparse/os）。
- 完工写 `t3_done.md`：改动清单、RED→GREEN、run_all 结果行、两个文档改前/改后字节数、FORGGIE 实跑留给 Fable（案卷在仓库外）。

## 1. 共同的路径守卫（辅助函数，放在当前 `:1402` `def cmd_freeze(a):` 之前的新函数区，T1 的 `HYGIENE_RE`/`case_hygiene_warnings` 保留在其前）

```python
def _readonly_case_file(case_dir, rel):
    """inspect/lookup 共用：先用原始 rel 过 safe_case_file 三验（案外/符号链接/非常规文件），再拒 sealed/。
    sealed 判定用首段 casefold（macOS 大小写不敏感文件系统下 SEALED/x 也能解析到密封目录）。
    边界：以 --case-dir 是真实案根为前提；案根本身被指到某案 sealed/ 目录时本守卫不识别——它不是揭盲授权闸，只是防误读。"""
    path = safe_case_file(case_dir, rel)          # 原始 rel 进三验，保留非法段证据
    first = rel.replace("\\", "/").lstrip("./").split("/", 1)[0]
    if first.casefold() == "sealed":
        raise ValueError(f"sealed/ 下文件不得用只读查询工具读取（揭盲走 freeze --check-unseal）: {rel}")
    return str(path)
```
`safe_case_file` 已在 `:44` 导入。案外路径、符号链接、`..`、绝对路径均由它抛 `ValueError`；两个子命令统一捕获后 `print(f"[{subcmd}] 路径非法: {e}", file=sys.stderr); return 2`。`--file`、`--in`、`--addr-file` 三个入口都走本守卫。

## 2. `inspect`：JSON 键树/类型/长度/样本，分页

用法：`handoff_manifest.py inspect --case-dir D --file <rel> [--path a.b.0] [--depth 2] [--limit 30] [--offset 0]`

- 参数约束：`--limit ≥ 1`、`--offset ≥ 0`、`--depth ≥ 0`，否则 exit 2（argparse `type` 校验或函数内判定，stderr 写明哪个参数）。
- 读取：`.json` → `json.load`；`.jsonl` → 逐行 `json.loads` 成 list（空行跳过，坏行计入 `bad_lines` 并继续，不中断）；其他后缀 → exit 2 "只支持 .json/.jsonl"。**JSON 损坏、编码错误、读取失败（`ValueError`/`UnicodeDecodeError`/`OSError`）在子命令内捕获 → exit 2**，不得漏到 `main` 兜底成 exit 1。
- `--path`：点分路径，逐段解析：当前节点是 dict → 按**原字符串键**匹配；是 list → 段必须是非负十进制整数下标（负数、越界 → exit 2）；带点的键本轮不支持（写在帮助里）；任一段不存在 → exit 2 "路径不存在: <段>"。
- 分页只作用于**根节点**（`--path` 选中的节点；默认整文件）：
  - 根是 dict：键排序后从 `--offset` 起最多 `--limit` 个；`total=<键数>`。
  - 根是 list：从 `--offset` 起最多 `--limit` 个元素逐个展开；`total=<len>`。
  - 根是标量：直接打印 `= <repr 截 80 字符>`；`total=1 returned=1`（offset≥1 时 returned=0）。
  - `returned=<本页实际展开数>`、`next_offset=min(offset+returned,total)`、`truncated=<next_offset<total>`；`offset ≥ total` 时 returned=0、truncated=false。
- 子层（根以下）递归到 `--depth`（根层为深度 0）：dict 按键排序全列（不分页，每键一行 `key: <type>` 后跟 `len=N` 或 `= <repr 截 80>`）；**子层 list 只采样首元素 `[0]`**，行首写 `list len=N`。
- 输出（纯文本，stdout，缩进 2 空格/层）：首行 `file=<rel> bytes=<n> path=<--path 或 .>`；末行 `total=… returned=… truncated=… next_offset=…`，`.jsonl` 时末行再加 ` bad_lines=<n>`。
- 退出码：0 正常；2 参数/路径非法、路径不存在、不支持后缀、解析失败。**不写任何文件**。

## 3. `lookup`：按地址清单跨文件回填字段，分页

用法：`handoff_manifest.py lookup --case-dir D (--addr A [--addr B …] | --addr-file <rel>) --in <rel> [--in <rel> …] [--fields f1,f2] [--limit 50] [--offset 0] [--json]`

- `--addr` 与 `--addr-file` **互斥**（同时给或都不给 → exit 2）；`--limit ≥ 1`、`--offset ≥ 0` 否则 exit 2。
- 地址归一：形如 `0x`＋40 位十六进制 → 小写；其他（Solana base58 等）原样、区分大小写。`--addr-file`：案内文本文件（同守卫），每行一个地址，`#` 开头与空行跳过。查询序列**保留原顺序与重复**。
- 每个 `--in` 文件建索引 `{norm(addr): [record…]}`，分两步，且**与查询地址无关**（索引由文件结构决定，不因查什么而变）：
  - **选记录**（规则 1、2 都跑，不互斥）：
    1. 顶层 dict：每个 `(key, value)` 视为一条记录，地址＝key；value 是 dict 时记录＝value 并附 `_key=key`，value 是 list 时记录＝`{"_key": key, "members": value}`（名册形态 `{entity_id:[addr…]}` 的适配），value 是标量时记录＝`{"_key": key, "value": value}`。
    2. 顶层 dict 中任何值为 list-of-dict 的键（`entities/rows/items/records/holders/balances/addresses/cards/labels` 或其他），以及顶层就是 list 的 `.json` 与 `.jsonl` 每行：每个元素是一条记录。
  - **给每条记录定地址**（规则 3 与 4 **都执行**）：
    3. 取首个存在的键 `addr / address / owner / wallet / account` 的值为地址（规则 1 的记录再加上其 key）；
    4. 记录含 `members`/`addresses` 列表 → 列表内每个地址也索引到该记录。
  - 同一来源记录对同一地址只登记一次；不同记录全部保留，输出标 `n=<k>`。
- 输出：按查询序列顺序、从 `--offset` 起最多 `--limit` 个地址；每地址一块：`<addr>` 行，其下每个 `--in` 文件一行：`  <rel>: MISSING` 或 `  <rel>: {字段…}`（多条时 `n=<k>` 后逐条）——有 `--fields` 时只取这些字段（缺的写 `<f>=MISSING_FIELD`），无 `--fields` 时输出记录的 key 列表＋前 3 个标量字段值（截 80 字符）。
- `--json`：输出一个 JSON 对象 `{"query":[全部归一化查询地址，含重复],"files":[…],"rows":[本页 {"addr":…, "hits":{rel: null|[record…]}}],"total","returned","truncated","next_offset","missing"}`；**`--json` 忽略 `--fields`，记录完整不截断**（截断只影响文本显示）。
- 末行（文本模式）：`total=<查询地址数> returned=<n> truncated=<bool> next_offset=<k> missing=<本页内全部文件均 MISSING 的地址数>`；`--json` 的 `missing` 同样只计本页。
- 退出码：0 正常（含 MISSING）；2 参数非法/路径非法/文件不可解析/无查询地址。

## 4. argparse 与 dispatch（`main()` `:1647-1696`）

- 在 `f = sub.add_parser("freeze", …)` 段之后（`:1688` 锚 `f.add_argument("--check-unseal", action="store_true")` 之后）加两个 parser，帮助文案：`inspect`＝"只读：JSON/JSONL 键树、类型、长度、样本（分页），代替手写 python 探 schema"；`lookup`＝"只读：按地址清单跨文件回填字段（分页），代替手写 python 跨文件查"。
- `:1692-1693`（锚 `return {"generate": cmd_generate, "verify": cmd_verify,` / `"receipt": cmd_receipt, "freeze": cmd_freeze}[a.subcmd](a)`）字典加 `"inspect": cmd_inspect, "lookup": cmd_lookup`。

## 5. 测试 `scripts/tests/test_handoff_manifest.py`（新增用例，登记进 `main()` 末尾；夹具 `make_case`（`:73`）已建 `data/` 与 `sealed/`，调用者先建案根；`write_json` 不建父目录）

地址常量（不要把省略号写进实际地址）：`A = "0x" + "abc"*13 + "a"`、`B = "0x" + "999"*13 + "9"`、`C = "0x" + "def"*13 + "d"`、`A_UP = "0x" + A[2:].upper()`。

夹具文件（全部在**快照之前**写好）：`data/identity_cards.json`＝`{A_UP: {"kind":"eoa","label":"W1","note": "x"*100, "meta": {"k": 1}}, C: {"kind":"contract","label":"P1"}}`；`data/balances_final.json`＝`[{"addr":A,"balance":"10","pct":1.5},{"addr":B,"balance":"3","pct":0.2},{"addr":A,"balance":"7","pct":1.0}]`（A 两条 → n=2）；`data/labels.jsonl`＝两行 `{"address":…, "name":…}`＋一行坏 JSON；`data/entity_registry.json`＝`{"E1":{"members":[A,B]},"E2":[C]}`；`data/addrs.txt`＝`"# 注释\n\n" + A_UP + "\n" + B + "\n"`；`sealed/x.json`＝任意；案根外 `outside.json`＋案内符号链接 `data/link.json → ../../outside.json`。

所有子命令调用用 `[sys.executable, "-B", HM, …]` 子进程；守卫负例**必须同时断言 exit 2 与 stderr 含指定文本**（防"子命令不存在"假通过）。

1. `inspect 键树/分页/深度/路径`：`data/identity_cards.json --limit 1` → 首行 `file=`、含排序后第一个 key、末行 `total=2 returned=1 truncated=true next_offset=1`；`--offset 1` → `returned=1 truncated=false next_offset=2`；`--offset 5` → `returned=0 truncated=false`；`--path <A_UP>.kind` → `= 'eoa'` 且 `total=1 returned=1`；`--path <A_UP>.meta --depth 0` 不展开子层、`--depth 1` 展开 `k`；`data/balances_final.json --limit 2` → 展开两个元素、`total=3 next_offset=2 truncated=true`；`--path 0.addr` 命中、`--path 9.addr` 与 `--path -1` → exit 2 含"路径不存在"或"下标"；`--limit 0`/`--offset -1` → exit 2。
2. `inspect jsonl 坏行不中断`：`data/labels.jsonl` → exit 0，输出含 `total=2`、末行含 `bad_lines=1`；另写一份 `data/broken.json`（非法 JSON）→ exit 2 且 stderr 非空（不是 exit 1）。
3. `inspect 守卫`：`--file sealed/x.json`、`--file SEALED/x.json`、`--file ./sealed/x.json` → exit 2 且 stderr 含 `sealed/`；`--file ../outside.json`、`--file <绝对路径 outside.json>`、`--file data/link.json` → exit 2 且 stderr 含 `路径非法`；`--file data/nope.json` → exit 2。
4. `lookup 三文件回填`：`--addr A --addr B --in identity_cards --in balances_final --in entity_registry --fields label,balance` → A 块：identity_cards 行含 `label=W1`（大小写归一命中）、balances 行 `n=2` 且含 `balance=10` 与 `balance=7`、entity_registry 行非 MISSING（members 命中，`label=MISSING_FIELD`）；B 块：identity_cards 行 `MISSING`、entity_registry 非 MISSING；`--addr C --in entity_registry` → 命中 E2（`{entity_id:[addr…]}` 适配）；末行 `total=2 returned=2 truncated=false next_offset=2 missing=0`。
5. `lookup --addr-file 与 --json 完整记录`：`--addr-file data/addrs.txt --in identity_cards --fields label --json` → 可 `json.loads`；`query == [A, B]`；`rows[0]["hits"]["data/identity_cards.json"][0]["label"] == "W1"` 且同记录含完整 `note`（100 字符）与嵌套 `meta`（`--fields` 被忽略、不截断）；`rows[1]["hits"][…] is None`；`missing == 1`。
6. `lookup 守卫与参数`：`--in sealed/x.json`、`--addr-file sealed/x.json`、`--in SEALED/x.json` → exit 2 含 `sealed/`；`--in data/link.json` → exit 2 含 `路径非法`；无 `--addr`/`--addr-file`、两者同给 → exit 2；`--limit 0`、`--offset -1` → exit 2；`--addr A --addr B --limit 1` → `returned=1 truncated=true next_offset=1`，`--offset 1` → `next_offset=2 truncated=false`，`--offset 9` → `returned=0`；重复查询 `--addr A --addr A` → `total=2`。
7. `只读断言`：夹具全部就绪后先做案目录文件清单＋sha 快照；随后**把案目录整体 `chmod -R a-w`**（用例结束 `finally` 恢复）再跑用例 1–6 的正例命令各一次，均 exit 0（任何写入都会 PermissionError 变 exit≠0）；恢复权限后再做一次快照比对完全一致。
- RED：改生产代码前，`inspect`/`lookup` 子命令不存在 → argparse exit 2 且 stderr 含 `invalid choice`（记录原文）；改后全 GREEN。

## 6. 条文（只替换现有行；每文件字节不增）

改前 `wc -c`：`references/split-run.md` 28135、`references/context-discipline.md` 9257（以开工时实测为准）。

- `references/split-run.md:72`（锚 `机器权威源一律 JSON；md 仅渲染层可选。工具：`）整行替换为：
  `机器权威源一律 JSON；md 仅渲染层可选。工具：`scripts/report/handoff_manifest.py`（子命令 `generate / verify / receipt / freeze / inspect / lookup`；后两个只读分页：看键树、按地址批查字段）。`（−5 字节；删去的"schema 常量内嵌／测试进 run_all"是仓库事实，run_all SUITE 本就登记）
- `references/context-discipline.md:27`（锚 `   历史清单项（标准脚本跑批与重试循环/对账四查执行侧/标签库批量 lookup/`）整行替换为：
  `   历史清单项（脚本跑批与重试循环/对账四查执行/键树与地址批查（`handoff_manifest.py inspect/lookup`）/大户批量排查/图表脚本执行/数据完整性验证/逐地址溯源 fan-out）继续有效；已归 −1 的项在 −1 内完成。`（−1 字节）
- 不加"禁止手写 python"条文。改后 `python3 scripts/tests/docs_lint.py --all` PASS。

## 7. 完成标准

- 两个子命令按 §2/§3 行为落地，§5 七条用例 GREEN，既有用例不改；run_all 全绿（nohup 落文件；沙箱端口类失败如实记录）。
- `git diff scripts/report/handoff_manifest.py` 只含新增函数、两个 parser、dispatch 两项；既有函数体零改动。
- 两个文档字节 ≤ 改前（预期 28130 / 9256）；docs_lint PASS。
- Fable 本机验收（FORGGIE 案卷 D）：`python3 -B scripts/report/handoff_manifest.py inspect --case-dir D --file data/entity_series.json --depth 1`、`python3 -B scripts/report/handoff_manifest.py lookup --case-dir D --addr-file <案内清单相对路径> --in identity_cards.json --in balances_final.json`（以案内真实相对路径为准）实跑，exit 0、输出分页可读。
- `t3_red_evidence.txt`、`t3_done.md` 在本目录；不 commit。
