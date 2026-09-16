# 工单 T3（v5，融合 codex 三轮复核 `t3_review_reply.txt` / `_r2.txt` / `_r3.txt`；v5 对 r3 两项：用例①深度断言改为与 §2 一致并加 `--path <A_UP>` 深度对比、用例⑦审计钩子补 `os.open` 整数 flags／目录边界归属／rename 两端／词法路径与 realpath 双检／监测器自检、`os.lstat`+`os.readlink` 描述更正、简写命令须补齐必填参数）：高频机械活稳定命令 —— `handoff_manifest.py inspect / lookup` 两个只读分页子命令

> 出处：用户 2026-09-16 批准的三项修复计划 §2.2（裁决：本轮只做 inspect/lookup；`q` SQL、写入型入口不做）。原则：**不增加 skill 上下文；能删的不新增，能改的不新增**。
> 基线：分支 `fix/three-items-20260916`，T1（55b56c2）与 T2（7ea6caa）均已落地，工作树干净；本单只在 `def cmd_freeze(a):` 前的新函数区与文件末尾 argparse 段施工，行号以开工时 `nl -ba` 核对锚文本为准（导入 :44、cmd_freeze :1402、main :1647、`--check-unseal` :1688、dispatch :1692-1693，均经 codex 第二轮核实唯一）。
> v4 变更（对 r2 六项）：§0 测试登记锚改为 main 结果汇总行；§1 守卫首段改 `rel.split("/",1)[0]`，删 lstrip/反斜杠处理；§2 `returned` 与 depth 解耦、标量 offset≥1 不输出；§3 地址候选仅非空字符串、`_key` 冲突 exit 2、按来源位置去重、坏行与异常策略与 inspect 同款；§5 `SCRIPT` 常量、真实路径、④补 list-of-dict 与名册混合夹具、⑥补 `--addr-file` 三反例、⑦改为进程内 audit hook 监测写操作（chmod/快照降为辅助）；§7 "既有函数体零改动"改为 main 例外明示、docs_lint 命令加 `-B`。
> 动机（实测）：五个 −2 会话 1,411 条手写 python 里，schema 探测 495 条、按地址跨文件查字段 335 条。两个子命令只覆盖这两类，不做聚合/SQL/改写。

## 0. 开工纪律

- 工作目录 `/Users/uravvv/.claude/worktrees/tca-three-items`（独立克隆；**不要**碰 `/Users/uravvv/.claude/skills/token-chip-analysis`）。开工 `git status --short` 除 `maintenance/repair-20260916-three-items/` 外须为空（T2 已提交，现应满足；不满足即停工）。
- 锚文本不一致即停工写 `t3_done_attempt1_stopped.md`。**禁止**施工者本人读取 `/Users/uravvv/.codex/`、`/Users/uravvv/.claude/skills/_archive/`、tag `codex-frozen-20260915` 作为参考（被测代码自身的 `git_sha` 探测是既有行为，允许原样运行）。离线；不 commit。
- **白名单**：`scripts/report/handoff_manifest.py`（只允许：新增 `_readonly_case_file`、`cmd_inspect`、`cmd_lookup` 及其辅助函数，`main()` 内新增两个 parser 与 dispatch 字典两项）、`scripts/tests/test_handoff_manifest.py`（新增用例函数＋在 `main()` 结果汇总之前登记调用：以 `print("=" * 40)`（当前 `:993`）为锚，插在其前；不得放在 return 之后；该位置在测试 main 的 `finally` 清理（`:990-991`）之后，新增用例须自建并自清理案根，不得复用已删除的 root）、`references/split-run.md:72`、`references/context-discipline.md:27`、本目录证据文件。**不改** generate/verify/receipt/freeze 任何既有逻辑与文案；不动 CHANGELOG/VERSION/pyproject。
- 两个子命令**只读**："零写入"指**案目录**零写入：不得 open(…, "w"/"a"/"x"/"+")、不得建临时文件、不得删/改名/改权限；解释器字节码缓存落在 skill 目录不在此列，验收与测试一律用 `python3 -B` 调用。不引入 duckdb/pandas 等新依赖（标准库 json/argparse/os/sys）。
- 完工写 `t3_done.md`：改动清单、RED→GREEN、run_all 结果行、两个文档改前/改后字节数、FORGGIE 实跑留给 Fable（案卷在仓库外）。

## 1. 共同的路径守卫（辅助函数，放在当前 `:1402` `def cmd_freeze(a):` 之前的新函数区，T1 的 `HYGIENE_RE`/`case_hygiene_warnings`（:1381-1399）保留在其前）

```python
def _readonly_case_file(case_dir, rel):
    """inspect/lookup 共用：先用原始 rel 过 safe_case_file 三验（案外/符号链接/非常规文件），再拒 sealed/。
    sealed 判定用首段 casefold（macOS 大小写不敏感文件系统下 SEALED/x 也能解析到密封目录）。
    边界：以 --case-dir 是真实案根为前提；案根本身被指到某案 sealed/ 目录时本守卫不识别——它不是揭盲授权闸，只是防误读。"""
    path = safe_case_file(case_dir, rel)          # 原始 rel 进三验；./、..、绝对路径、符号链接在此被拒
    first = rel.split("/", 1)[0]                  # 不做 lstrip/反斜杠替换：.sealed 之类合法目录不得误拒
    if first.casefold() == "sealed":
        raise ValueError(f"sealed/ 下文件不得用只读查询工具读取（揭盲走 freeze --check-unseal）: {rel}")
    return str(path)
```
`safe_case_file` 已在 `:44` 导入。案外路径、符号链接、`..`、`./` 前缀、绝对路径均由它抛 `ValueError`（错误文本含原始 rel）；两个子命令统一捕获后 `print(f"[{subcmd}] 路径非法: {e}", file=sys.stderr); return 2`。`--file`、`--in`、`--addr-file` 三个入口都走本守卫。

## 2. `inspect`：JSON 键树/类型/长度/样本，分页

用法：`handoff_manifest.py inspect --case-dir D --file <rel> [--path a.b.0] [--depth 2] [--limit 30] [--offset 0]`

- 参数约束：`--limit ≥ 1`、`--offset ≥ 0`、`--depth ≥ 0`，否则 exit 2（stderr 写明哪个参数）。
- 读取：`.json` → `json.load`；`.jsonl` → 逐行 `json.loads` 成 list（空行跳过，坏行计入 `bad_lines` 并继续，不中断）；其他后缀 → exit 2 "只支持 .json/.jsonl"。**JSON 损坏、编码错误、读取失败（`ValueError`/`UnicodeDecodeError`/`OSError`）在子命令内捕获 → exit 2**，不得漏到 `main` 兜底成 exit 1。
- `--path`：点分路径，逐段解析：当前节点是 dict → 按**原字符串键**匹配；是 list → 段必须是非负十进制整数下标（负数、越界 → exit 2 "下标非法/越界: <段>"）；带点的键本轮不支持（写在帮助里）；任一段不存在 → exit 2 "路径不存在: <段>"。
- 分页只作用于**根节点**（`--path` 选中的节点；默认整文件）。**`returned` = 根节点本页选中项数，与 depth 无关**：
  - 根是 dict：键排序后从 `--offset` 起最多 `--limit` 个；`total=<键数>`。
  - 根是 list：从 `--offset` 起最多 `--limit` 个元素；`total=<len>`。
  - 根是标量：`total=1`；offset=0 时打印 `= <repr 截 80 字符>`、returned=1；offset≥1 时不输出值、returned=0。
  - `next_offset=min(offset+returned,total)`、`truncated=<next_offset<total>`；`offset ≥ total` 时 returned=0、truncated=false。
- 深度：根层为 0。`--depth 0` 只显示本页选中项的一行摘要（`key: <type> len=N` 或 `= <repr 截 80>`），不展开子项；`--depth d` 把子层递归展开到第 d 层：dict 按键排序全列（不分页）；**子层 list 只采样首元素 `[0]`**，行首写 `list len=N`。
- 输出（纯文本，stdout，缩进 2 空格/层）：首行 `file=<rel> bytes=<n> path=<--path 或 .>`；末行 `total=… returned=… truncated=… next_offset=…`，`.jsonl` 时末行再加 ` bad_lines=<n>`。
- 退出码：0 正常；2 参数/路径非法、路径不存在、不支持后缀、解析失败。**不写任何文件**。

## 3. `lookup`：按地址清单跨文件回填字段，分页

用法：`handoff_manifest.py lookup --case-dir D (--addr A [--addr B …] | --addr-file <rel>) --in <rel> [--in <rel> …] [--fields f1,f2] [--limit 50] [--offset 0] [--json]`

- `--addr` 与 `--addr-file` **互斥**（同时给或都不给 → exit 2）；`--limit ≥ 1`、`--offset ≥ 0` 否则 exit 2。
- 地址归一：**地址候选只接受非空字符串**（其他类型一律跳过，不报错）；形如 `0x`＋40 位十六进制 → 小写；其他（Solana base58 等）原样、区分大小写。`--addr-file`：案内文本文件（同守卫），每行一个地址，`#` 开头与空行跳过。查询序列**保留原顺序与重复**；归一后无任何查询地址 → exit 2。
- 每个 `--in` 文件读取策略与 inspect 同款：`.json` → `json.load`，`.jsonl` → 逐行、坏行跳过继续（文本模式末行加 ` bad_lines=<rel>:<n>`，`--json` 放 `"bad_lines":{rel:n}`），其他后缀/解析失败/编码错误/读取失败 → exit 2。
- 每个 `--in` 文件建索引 `{norm(addr): [record…]}`，**与查询地址无关**（索引由文件结构决定）：
  - **选记录**（规则 1、2 都跑，不互斥）：
    1. 顶层 dict：每个 `(key, value)` 视为一条记录，地址候选＝key。value 是 dict → 记录＝value 并附 `_key=key`；**value 已含 `_key` 字段 → exit 2 并报"<rel>: 顶层键 <key> 的记录已有 _key 字段"（不得静默覆盖）**；value 是 list → 记录＝`{"_key": key, "members": value}`（名册形态 `{entity_id:[addr…]}` 的适配）；value 是标量 → 记录＝`{"_key": key, "value": value}`。
    2. 顶层 dict 中任何值为 list 的键（`entities/rows/items/records/holders/balances/addresses/cards/labels` 或其他），以及顶层就是 list 的 `.json` 与 `.jsonl` 每行：**列表中只取 dict 元素作为记录，其他元素跳过**。
  - **给每条记录定地址**（规则 3 与 4 **都执行**）：
    3. 取首个存在的键 `addr / address / owner / wallet / account` 的值为地址候选（规则 1 的记录再加上其 key）；该键存在但值不是非空字符串 → 不向后回退其他键，仍执行规则 4；
    4. 记录含 `members` 和/或 `addresses` 列表 → 两者都扫描，列表内每个非空字符串成员也索引到该记录（非字符串成员跳过）。
  - **去重按来源位置**（文件内记录序号），不按内容：同一来源记录对同一地址只登记一次；内容相同但位置不同的两条记录是两条，输出标 `n=<k>`。
- 输出：按查询序列顺序、从 `--offset` 起最多 `--limit` 个地址；每地址一块：`<addr>` 行，其下每个 `--in` 文件一行：`  <rel>: MISSING` 或 `  <rel>: {字段…}`（多条时 `n=<k>` 后逐条）——有 `--fields` 时只取这些字段（缺的写 `<f>=MISSING_FIELD`），无 `--fields` 时输出记录的 key 列表＋前 3 个标量字段值（截 80 字符）。
- `--json`：输出一个 JSON 对象 `{"query":[全部归一化查询地址，含重复],"files":[…],"rows":[本页 {"addr":…, "hits":{rel: null|[record…]}}],"total","returned","truncated","next_offset","missing","bad_lines":{rel:n}}`；**`--json` 忽略 `--fields`，记录完整不截断**（截断只影响文本显示）。
- 分页计数与 inspect 同公式：`total=<查询地址数>`、`returned=<本页地址数>`、`next_offset=min(offset+returned,total)`、`truncated=<next_offset<total>`；`missing=<本页内全部文件均 MISSING 的地址数>`（`--json` 同样只计本页）。
- 退出码：0 正常（含 MISSING）；2 参数非法/路径非法/文件不可解析/`_key` 冲突/无查询地址。

## 4. argparse 与 dispatch（`main()` `:1647-1696`）

- 在 `f = sub.add_parser("freeze", …)` 段之后（`:1688` 锚 `f.add_argument("--check-unseal", action="store_true")` 之后）加两个 parser，帮助文案：`inspect`＝"只读：JSON/JSONL 键树、类型、长度、样本（分页），代替手写 python 探 schema"；`lookup`＝"只读：按地址清单跨文件回填字段（分页），代替手写 python 跨文件查"。
- `:1692-1693`（锚 `return {"generate": cmd_generate, "verify": cmd_verify,` / `"receipt": cmd_receipt, "freeze": cmd_freeze}[a.subcmd](a)`）字典加 `"inspect": cmd_inspect, "lookup": cmd_lookup`。

## 5. 测试 `scripts/tests/test_handoff_manifest.py`（新增用例，登记位置见 §0；脚本路径常量用既有 `SCRIPT`（`:43`）；夹具 `make_case`（`:73`）已建 `data/`（`:83`）与 `sealed/`（`:219`）并在 `:222` 跑子进程生成夹具，调用者先建案根；`write_json`（`:63`）不建父目录）

地址常量（不要把省略号写进实际地址）：`A = "0x" + "abc"*13 + "a"`、`B = "0x" + "999"*13 + "9"`、`C = "0x" + "def"*13 + "d"`、`A_UP = "0x" + A[2:].upper()`。

夹具文件（**全部在快照与权限收紧之前写好**，含 broken.json 与符号链接）：
- `data/identity_cards.json`＝`{A_UP: {"kind":"eoa","label":"W1","note": "x"*100, "meta": {"k": 1}}, C: {"kind":"contract","label":"P1"}}`
- `data/balances_final.json`＝`[{"addr":A,"balance":"10","pct":1.5},{"addr":B,"balance":"3","pct":0.2},{"addr":A,"balance":"7","pct":1.0}]`（A 两条 → n=2）
- `data/labels.jsonl`＝两行 `{"address":…, "name":…}`＋一行坏 JSON
- `data/entity_registry.json`＝`{"E1":{"members":[A,B]},"E2":[C]}`
- `data/mixed.json`＝`{"rows":[{"addr":A},{"addr":7},"junk"],"E1":{"members":[A,B,null,5]}}`（list-of-dict 与名册混合；非字符串成员）
- `data/keyclash.json`＝`{A: {"_key":"dup","label":"x"}}`
- `data/broken.json`＝非法 JSON 文本
- `data/addrs.txt`＝`"# 注释\n\n" + A_UP + "\n" + B + "\n"`
- `sealed/x.json`＝任意；案根外 `outside.json`＋案内符号链接 `data/link.json → ../../outside.json`＋案内符号链接 `data/link.txt → ../../outside.json`

所有子命令调用用 `[sys.executable, "-B", SCRIPT, <subcmd>, "--case-dir", case, …]` 子进程；下文各条简写命令**都须补齐 `--case-dir`、有效地址入口（`--addr`/`--addr-file`）与 `--in`/`--file`**，除非该条正是在测这个参数缺失；`--in`/`--file` 一律写真实相对路径 `data/xxx.json`；守卫与参数负例**必须同时断言 exit 2 与 stderr 含指定文本**（防"子命令不存在"或"缺必填参数"假通过：参数负例断言文本须是被测参数自己的报错，如 `--limit`、`sealed/`、`路径非法`、`_key`）。

1. `inspect 键树/分页/深度/路径`：`--file data/identity_cards.json --limit 1` → 首行 `file=`、含排序后第一个 key、末行 `total=2 returned=1 truncated=true next_offset=1`；`--offset 1` → `returned=1 truncated=false next_offset=2`；`--offset 5` → `returned=0 truncated=false`；`--path <A_UP>.kind` → `= 'eoa'` 且 `total=1 returned=1`；`--path <A_UP>.kind --offset 1` → 正文没有以 `= ` 开头的标量行且 `returned=0`；`--path <A_UP>.meta --depth 0` → 显示 `k` 的标量摘要行、`total=1 returned=1`；深度对比用 `--path <A_UP>`：`--depth 0` 显示 `meta` 摘要行但不出现 `k` 的子项行，`--depth 1` 出现 `k` 的子项行，两者均 `total=4 returned=4`；`--file data/balances_final.json --limit 2` → 展开两个元素、`total=3 next_offset=2 truncated=true`；`--path 0.addr` 命中；`--path 9.addr`、`--path -1` → exit 2 含"越界"或"下标"；`--limit 0`、`--offset -1`、`--depth -1` → exit 2。
2. `inspect jsonl 坏行不中断`：`--file data/labels.jsonl` → exit 0，输出含 `total=2`、末行含 `bad_lines=1`；`--file data/broken.json` → exit 2 且 stderr 非空（不是 exit 1）。
3. `inspect 守卫`：`--file sealed/x.json`、`--file SEALED/x.json` → exit 2 且 stderr 含 `sealed/`（后者验 casefold）；`--file ./sealed/x.json`、`--file ../outside.json`、`--file <绝对路径 outside.json>`、`--file data/link.json` → exit 2 且 stderr 含 `路径非法`；`--file data/nope.json` → exit 2。
4. `lookup 三文件回填与混合结构`：`--addr A --addr B --in data/identity_cards.json --in data/balances_final.json --in data/entity_registry.json --fields label,balance` → A 块：identity_cards 行含 `label=W1`（大小写归一命中）、balances 行 `n=2` 且含 `balance=10` 与 `balance=7`、entity_registry 行非 MISSING（`label=MISSING_FIELD`）；B 块：identity_cards 行 `MISSING`、entity_registry 非 MISSING；`--addr C --in data/entity_registry.json` → 命中 E2；`--addr A --in data/mixed.json --json` → `hits["data/mixed.json"]` 长度 2（rows 内一条＋E1 一条），`--addr B` → 长度 1；`--addr A --in data/keyclash.json` → exit 2 且 stderr 含 `_key`；末行（首条命令）`total=2 returned=2 truncated=false next_offset=2 missing=0`。
5. `lookup --addr-file 与 --json 完整记录`：`--addr-file data/addrs.txt --in data/identity_cards.json --fields label --json` → 可 `json.loads`；`query == [A, B]`；`rows[0]["hits"]["data/identity_cards.json"][0]["label"] == "W1"` 且同记录含完整 `note`（100 字符）与嵌套 `meta`（`--fields` 被忽略、不截断）；`rows[1]["hits"][…] is None`；`missing == 1`。
6. `lookup 守卫与参数`：`--in sealed/x.json`、`--in SEALED/x.json`、`--addr-file sealed/x.json` → exit 2 含 `sealed/`；`--in data/link.json`、`--addr-file data/link.txt`、`--addr-file ./sealed/x.json`、`--addr-file <绝对路径 outside.json>` → exit 2 含 `路径非法`；无 `--addr`/`--addr-file`、两者同给 → exit 2；`--limit 0`、`--offset -1` → exit 2；`--addr A --addr B --limit 1` → `returned=1 truncated=true next_offset=1`，`--offset 1` → `next_offset=2 truncated=false`，`--offset 9` → `returned=0`；重复查询 `--addr A --addr A` → `total=2`。
7. `只读断言`（不依赖退出码）：
   - **主检查：进程内写操作监测。** 用一个包装脚本（写在 scratch 测试目录、不在案目录）通过 `sys.addaudithook` 注册钩子后再 `runpy.run_path(SCRIPT, run_name="__main__")` 执行子命令；钩子按**实际 audit 事件参数**解析（`open` 为 `(path, mode, flags)`，`os.open` 观察到 `mode=None` 只带整数 flags；处理 `dir_fd` 形态，无法归属的写事件记为"未归属写事件"，不得静默跳过），记录以下事件：`open` 且（字符串 mode 含 `w/a/x/+` **或** 整数 flags 含 `O_WRONLY/O_RDWR/O_CREAT/O_TRUNC/O_APPEND` 任一位）、`os.remove`/`os.unlink`/`os.rmdir`、`os.rename`/`os.replace`（**源、目标两端都检查**）、`os.chmod`、`os.mkdir`、`os.truncate`、`shutil.move`/`shutil.copyfile`/`shutil.rmtree`、`tempfile.mkstemp`/`mkdtemp`。**路径归属按目录边界比较**（`os.path.commonpath([case_real, p]) == case_real`，不用裸 `startswith`，防相邻目录误收）；目录项变更（删除/改名/建目录/chmod）检查**词法绝对路径**（`os.path.abspath`，不解析符号链接，这样删案内指向案外的链接也能抓到），文件访问（open/truncate）同时检查词法路径与 `realpath` 目标。记录写到案目录**外**的日志文件。对用例 1–6 的每条正例命令各跑一次，断言日志为空。
   - **监测器自检**（证明它真能报警）：在同一测试内用 `sys.audit()` 合成事件至少三例——`open` 且 `mode=None`、flags=`os.O_WRONLY|os.O_CREAT`、路径在案内；`os.rename` 源在案外、目标在案内；`os.remove` 目标为案内指向案外的符号链接词法路径——断言三例均被记录；再合成一例相邻目录 `case_real + "_sibling/x"` 的写 open，断言不被记录。
   - **辅助检查**：夹具全部就绪后做案目录文件清单＋sha 快照（`os.walk(followlinks=False)`；符号链接用 `os.lstat` 记元数据、`os.readlink` 记链接文本，不读取目标内容）；随后对案目录内常规文件与目录 `chmod` 去写位（跳过符号链接，记录原 mode），再跑一遍正例命令均 exit 0；`finally` 按记录恢复原 mode，恢复后再做一次快照比对完全一致（快照只比较路径、内容哈希、恢复后的权限位与链接文本；不比较 atime/ctime 等读取或 chmod 自身会改变的字段）。
- RED：改生产代码前，`inspect`/`lookup` 子命令不存在 → argparse exit 2 且 stderr 含 `invalid choice: 'inspect'` / `invalid choice: 'lookup'`（codex 第二轮已实跑确认）；改后全 GREEN。

## 6. 条文（只替换现有行；每文件字节不增）

改前 `wc -c`：`references/split-run.md` 28135、`references/context-discipline.md` 9257（codex 两轮均按 UTF-8 精算确认下列替换分别 −5、−1）。

- `references/split-run.md:72`（锚 `机器权威源一律 JSON；md 仅渲染层可选。工具：`）整行替换为：
  `机器权威源一律 JSON；md 仅渲染层可选。工具：`scripts/report/handoff_manifest.py`（子命令 `generate / verify / receipt / freeze / inspect / lookup`；后两个只读分页：看键树、按地址批查字段）。`（−5 字节；删去的"schema 常量内嵌／测试进 run_all"是仓库事实，`handoff_manifest.py:54-59` 常量仍在、`run_all.py:70` 仍登记，无别处依赖）
- `references/context-discipline.md:27`（锚 `   历史清单项（标准脚本跑批与重试循环/对账四查执行侧/标签库批量 lookup/`）整行替换为：
  `   历史清单项（脚本跑批与重试循环/对账四查执行/键树与地址批查（`handoff_manifest.py inspect/lookup`）/大户批量排查/图表脚本执行/数据完整性验证/逐地址溯源 fan-out）继续有效；已归 −1 的项在 −1 内完成。`（−1 字节）
- 不加"禁止手写 python"条文。改后 `python3 -B scripts/tests/docs_lint.py --all` PASS。

## 7. 完成标准

- 两个子命令按 §2/§3 行为落地，§5 七条用例 GREEN，既有用例不改；`python3 -B scripts/tests/run_all.py` 全绿（nohup 落文件；沙箱端口/临时目录类失败如实记录，不冒充通过）。
- `git diff scripts/report/handoff_manifest.py` 只含新增函数、两个 parser、dispatch 两项；**既有函数体不变，唯一例外是 `main()` 新增两个 parser 及 dispatch 两项；generate/verify/receipt/freeze 函数体零改动**。
- 两个文档字节 ≤ 改前（预期 28130 / 9256）；docs_lint PASS。
- Fable 本机验收（FORGGIE 案卷 D）：`python3 -B scripts/report/handoff_manifest.py inspect --case-dir D --file data/entity_series.json --depth 1`、`python3 -B scripts/report/handoff_manifest.py lookup --case-dir D --addr-file <案内清单相对路径> --in data/identity_cards.json --in data/balances_final.json`（以案内真实相对路径为准）实跑，exit 0、输出分页可读。
- `t3_red_evidence.txt`、`t3_done.md` 在本目录；不 commit。
