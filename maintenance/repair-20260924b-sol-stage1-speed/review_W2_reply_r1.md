# 工单W2复核：退回

W2 的方向合理：把地图发现变成开工步骤，能减少漏带 `--known-map`；保留正式加载时的完整校验，也符合现有实现。但 v1 存在事实错误、登记口径混淆、检查命令触犯禁读纪律，以及跨工单文档遗漏，尚不能直接派工。

复核开始 HEAD 为 `0ff4035`，期间外部操作将 HEAD 推进至 `5b1b85a`。已核实两者之间本次审查的源码、文档及 W1–W4 工单均无变化，最终 HEAD 包含 `cc6298b`，工作树最终干净。全程离线，未读取任何禁读路径或 memories，未修改文件、未 commit。一次 here-document 被只读沙箱拒绝创建临时文件，随后改用内存执行。未运行会写临时文件或读取禁区的测试。

以下行号均对应 [workorder_W2.md](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/workorder_W2.md) v1。

**1．【必改】事实①②及 §1.1：过期检查位置错误，唯一地图已过期，案侧证据不能冒充仓库亲核。**

亲核结果：

- `--known-map` 的实际加载条件确为 `sqd_coverage_probe.py:1223` 的 `if not args.resume and args.known_map:`。
- `scripts/cross_case_coverage_reuse_review.md` 在当前仓库不存在；PYTHIA/TROLL 案卷也不在本次可读范围，20 h、92% 等只能标为调度方提供。
- `validate_shared_map:728–740` 检查 `ttl_days==30` 和时间格式，**不检查当前是否过期**；过期判断在 `_load_known_map:697–700`。
- 唯一地图 `20260827.json` 的 `generated_at` 是 **2026-08-25T03:17:11.217739+00:00**，到期时间是 **2026-09-24T03:17:11.217739+00:00**。复核时 UTC 为 06:31，已经过期。文件名不是 TTL 起点。
- 覆盖区间为 `[306451717,440368381]`，共 **133,916,665 slot**；`candidate_slots=153667`，`refuted_slots=0`。
- JSON 为 1,538,739 B；counts 为 97,736,104 B；bitmap 为 210,555 B。两份二进制的实际 size 与 JSON 声明一致。另有 README，无其他地图 JSON。

替换第 4–6 行：

> 事实基线＝本轮实际 HEAD；当前生产文件与 cc6298b 一致，W2 派工基线另由调度方填为 W3 收官 commit，届时重核行号。  
> ① `scripts/solana/sqd_coverage_probe.py:1222-1227` 仅在非 resume 且指定 `--known-map` 时加载地图；resume 不支持中途换图或叠图。已启动任务不能靠追加该参数获得复用，另起新任务属于重新启动，不称“无法补救”。PYTHIA 未带地图、耗时 20 h、TROLL 地图可覆盖 92% 等为调度方提供的案侧记录，本仓库未亲核；删除不存在的 `scripts/cross_case_coverage_reuse_review.md` 引用。  
> ② 仓库仅有 `assets/sqd-solana-coverage-map/20260827.json` 及对应 counts/blocks 两份二进制。该图 generated_at＝2026-08-25T03:17:11.217739+00:00，到期＝2026-09-24T03:17:11.217739+00:00，本轮复核时已过期。`validate_shared_map` 检查 TTL 固定值与时间格式；实际过期检查由 `_load_known_map` 执行。不能将“唯一入库资产”表述为“当前可用地图”。

替换第 20 行：

> - 1.1 `find-known-map` 只读、离线执行文件扫描与轻校验，不读取或解压整份二进制，不运行逐 slot 分类。当前入库资产覆盖 133,916,665 slot；本轮未测全量校验耗时。完整资产校验在非 resume 的 `--known-map` 加载路径执行，其后仍须在线身份、历史锚及已知 slot 重查。

**2．【必改】事实⑤及 §2.7：历史协议集合写错；W1 哈希与 W2 最终哈希必须分清。**

已复算两个当前脚本，均与所登记 commit 的 `git show` 内容 SHA-256 一致：

| 脚本 | 当前 SHA-256 | 登记 commit |
|---|---|---|
| probe | `c4980c984b08d27f5a7e46db50f97c9c16e47ea491f37a459b3773f939218769` | `cdc4f87f8e3ee4d181760cb8455d688f23049f20` |
| repair | `3f89aab13054be76711d85d15a3e4f21d6113c35c905f55a8e60edb31ba8446b` | `7846184f9f2ba758027cd6c5ddb1b21e87b3c16f` |

现有条目逐条对应如下，行号为 `scripts/lib/producer_history.py` 的 **protocol 行**；全部为 ACTIVE：

| 脚本／哈希前缀 | 已登记协议及行号 |
|---|---|
| probe／`e41370b185ae` | `sqd-solana-coverage/v1`:47；`sqd-solana-coverage-pointer/v1`:55 |
| probe／`bccf1802b6a5` | `sqd-solana-coverage/v1`:63；`sqd-solana-coverage-pointer/v1`:71 |
| probe／`be415db35525` | `sqd-solana-coverage/v1`:79；`sqd-solana-coverage-pointer/v1`:87 |
| probe／`c4980c984b08` | `sqd-solana-coverage/v1`:95；`sqd-solana-coverage-pointer/v1`:103 |
| repair／`c8beb16e998c` | `sqd-solana-cache/v4`:111；`sqd-solana-repair-bundle/v1`:119；`sqd-solana-coverage-resolution/v1`:127；`sqd-solana-repair-pointer/v1`:135 |
| repair／`da6eb283ab08` | `sqd-solana-cache/v4`:143；`sqd-solana-repair-bundle/v1`:151；`sqd-solana-coverage-resolution/v1`:159；`sqd-solana-repair-pointer/v1`:167 |
| repair／`60b48f86154d` | `sqd-solana-cache/v4`:175；`sqd-solana-repair-bundle/v1`:183；`sqd-solana-coverage-resolution/v1`:191；`sqd-solana-repair-pointer/v1`:199 |
| repair／`25f04ff10bc4` | `sqd-solana-cache/v4`:207；`sqd-solana-repair-bundle/v1`:215；`sqd-solana-coverage-resolution/v1`:223；`sqd-solana-repair-pointer/v1`:231 |
| repair／`3f89aab13054` | `sqd-solana-cache/v4`:239；`sqd-solana-repair-bundle/v1`:247；`sqd-solana-coverage-resolution/v1`:255；`sqd-solana-repair-pointer/v1`:263 |

**没有任何 probe 的 shared-map 历史条目。** manifest 登记它生产/消费某 schema，不代表 producer_history 已登记该协议。

替换第 9 行：

> ⑤ producer_history 当前 probe 哈希 c4980c98…登记 coverage/v1、coverage-pointer/v1 两项；repair 哈希 3f89aab1…登记 cache/v4、repair-bundle/v1、coverage-resolution/v1、repair-pointer/v1 四项，均为 ACTIVE。probe 没有 shared-coverage-map/v1 历史条目，不能从 invariant_manifest 推导其存在。W1/W4 已提交版本的完整 commit 与 SHA-256 由调度方填入 v2，施工者通过 `git show <commit>:<script> | shasum -a 256` 复算。

替换第 33 行：

> - 2.7 在 `PRODUCER_HISTORY` 元组闭合整行 `)`（当前 :283）前追加六项 ACTIVE 条目：W1 已提交 probe 哈希对应 `sqd-solana-coverage/v1`、`sqd-solana-coverage-pointer/v1`；W4 已提交 repair 哈希对应 `sqd-solana-cache/v4`、`sqd-solana-repair-bundle/v1`、`sqd-solana-coverage-resolution/v1`、`sqd-solana-repair-pointer/v1`。完整 sha/commit 由调度方在 v2 填入并逐项复算，不一致停工。W2 新增 find 子命令还会再次改变 probe 文件哈希，因此 W1 条目登记的是前代，不能称为 W2 最终 producer。现行校验器接受当前文件哈希；W2 未提交工作树哈希不得写入历史表。如另要求登记 W2 最终哈希，须在其源码提交后另行登记。保留全部既有 ACTIVE 条目；本单不新增 shared-map 协议历史条目。

这一流程符合 `producer_history.py:3–6`，也符合当前哈希可直接获准的 `solana_exact_validate.py:499–506`；**不需要为了历史登记制造同一 commit 自引用。**

**3．【必改】§0.4：manifest 不钉 SHA，但 W1 新增 schema 消费关系不能漏登记。**

“仅改哈希不用改 manifest”是对的；“整个工程必定不需要改 manifest”则不成立。

当前 manifest 的 probe 消费者只有 shared-map（`:627–631`）。W1 §2.2 要求检查 `bundle.schema=="sqd-solana-repair-bundle/v1"`；按 `invariant_scan.py:1165–1172` 的扫描规则，直接实现该比较会新增消费者关系，未登记将触发 `:1277–1284` 的差异错误。

在第 15 行后新增：

> - 0.4a `invariant_manifest.json` 登记生产者/消费者的 script 与 schemas 关系，不登记脚本 SHA-256。W2 的 find 使用既有 shared-map schema，本身不要求新增关系；但 W1 导出逻辑新增的 repair-bundle schema 消费关系须由 W1 同步登记并通过 invariant_scan。调度方在 W2 派工前检查这一前置结果；若缺登记，退回 W1 收口，不得以“manifest 不钉 sha”为由忽略，也不得通过改写 schema 检查形式躲避扫描。W2 原则上不修改 manifest。

**4．【必改】§2.1：轻校验、搜索目录、输出与错误边界尚未定形。**

现有轻校验没有必要删掉，但缺少足以避免“明显坏图胜出”的廉价检查。也有两处表述错误：

- 三件套中，只有 **counts 与 bitmap** 在 JSON 内声明 size；JSON 没有声明自身 size。
- `[0-9]{8}.json` 是正则写法，不能直接当作 `Path.glob` 模式。

`_dry_run:1128–1145` 只读取 JSON、计算乐观交集，不验证资产可用性。find 的轻筛不与之等价；加载路径的二进制哈希、解压、分类及在线重查也不能被 find 替代。

替换第 27 行中“默认搜索目录”至“入口接线”前的设计文字：

> 默认目录用 `Path(__file__).resolve().parents[2] / "assets/sqd-solana-coverage-map"` 定位，不依赖 cwd；重复的 `--search-dir` 在默认目录之外追加，目录及候选路径 resolve 后去重。仅扫描每个目录直接子文件；文件名用 `[0-9]` 重复八次加 `.json` 的 glob，或等价 fullmatch，不把 `{8}` 当 glob。  
> CLI 要求 `0 <= N <= M`。逐文件读取 JSON 并轻校验：顶层为对象；schema 正确；version 为八位 ASCII 数字；ttl_days 为整数 30；generated_at 为可解析的带时区时间，转 UTC；到期判断与 `_load_known_map` 一致，以 `now > expires_at` 判过期。不要要求 version 与 generated_at 的日期相等。  
> slot_counts/blocks_bitmap 的元数据形态、encoding、非负整数区间及两者区间一致性正确；与 `[N,M]` 有非空交集。两份引用文件 resolve 后必须仍在资产目录内，为普通文件，实际 size 与声明一致；sha256 字段为 hex64，但不读取二进制重算哈希。candidate_slots/refuted_slots 为区间内、升序去重的整数数组；检查 W1 所定义的 refuted 子集与非空证据形态，兼容旧图 refuted 为空且无 refuted_evidence。检查 supersedes 和 canary 的基本形态，以及 `sqd.query_body_sha256 == sqd_query_template_sha256()`。轻筛不替代完整资产校验、实时身份校验及 SQD 重查。  
> `overlap_slots=max(0,min(M,to_slot)-max(N,from_slot)+1)`；`overlap_ratio=overlap_slots/(M-N+1)`；candidate_count/refuted_count 明确为交集内各数组元素数量。path 为绝对路径，generated_at/expires_at 为 UTC ISO-8601。stdout 仅输出一行合法 JSON：顶层固定为 chosen、accepted、rejected；chosen 为 accepted[0] 或 null；accepted 每项固定含 path/version/generated_at/expires_at/overlap_slots/overlap_ratio/candidate_count/refuted_count；rejected 每项含 path/reason。单个坏文件进入 rejected 后继续扫描。  
> 正常扫描有 chosen 返回 0，正常扫描无 chosen 返回 2，运行故障返回 1。argparse 参数错误沿用其 exit 2 与 stderr；调用方必须同时检查退出码与完整 JSON，不能把所有非零结果当作“没有地图”。缺失目录记录 reason，空目录允许；不可读取目录不得静默当作空目录。入口接线在 `main(argv)` 的 export 分支旁，使用独立 parser。

**5．【建议】§2.1 排序：保留重叠优先，但把交集内 refuted 数放在时间之前。**

支持原排序的最强理由是：覆盖越广，潜在减少的全扫越多；生成时间更新也更接近当前 SQD 状态。

反对理由是：本工程主要收益还来自省掉修复 getBlock。等覆盖范围时，较新却没有驳回证据的图，可能明显劣于稍旧但有大量驳回的图。`generated_at` 又来自 coverage 发布时刻，不能表示后来回填 census 的时间。全图 refuted 总数则会奖励案窗之外的无关 slot。

替换第 27 行排序句：

> 通过者按 `(overlap_slots desc, refuted_count desc, generated_at_utc desc, absolute_path asc)` 排序，其中 refuted_count 仅统计本案交集内 slot。此规则是确定性启发式，不宣称全局成本最优；不按文件名 version 单独优先。最后用绝对路径打破并列，避免目录枚举顺序改变 chosen。

**6．【必改】§2.2–2.5：继承范围、resume 限制、导出分支及 W4 文档必须补齐。**

W1 字段和状态名称基本引用正确，但有四个实际问题：

- W1 §1.2 要求 **成功复用区间内、非 unverified、重查值与资产值都为 2**；不能简化成任意“值相同”。
- “不拉 Helius”仅指该继承 slot 的修复 `getBlock`。探针仍在 `:1283–1285` 调用 `_confirm_getblocks`。
- W1 §2.3 明确 resume 不保留驳回继承，W2 只说不能换图，漏掉更重要的限制。
- W4 的 α 合并请求只进入 CHANGELOG，运行分册缺少这项说明；“一次”必须排除失败重试，β 保留。

将第 28 行追加文案替换为：

> **Solana coverage 开工硬性**：非 resume 启动前跑 `sqd_coverage_probe.py find-known-map --from-slot <案起> --to-slot <冻结slot>`，以 receipt 的 note 保存 JSON。chosen 非空必用 `--known-map <chosen.path>`；扫描正常且 chosen=null 才用 `--full`，记非阻断 INFO。轻筛不保证可复用，加载失败可自动回退并留因。resume 不加载或叠加地图，且不保留 W1 驳回继承。coverage 有效发布且满足导出条件后回填：有修复代传 `--repair-gid <gid>`，无代（含 refuted-only）用 `--no-repair`；完整命令见采集分册，资产由调度方验收入库。

将第 29 行追加文案替换为：

> Solana coverage 开工先 find-known-map；有 chosen 必带 --known-map；回填与 resume 限制按 split-run §1.3。

将第 30 行生命周期段替换要求改为以下原文，**897 B**：

> **共享地图生命周期**：开工必跑 `find-known-map`；TTL 从源 coverage 发布时刻算 30 天，不因导出刷新。`refuted_slots` 来自已发布修复 census 或链式继承；仅资产内、本案复用成功区间且不在 unverified_ranges 的 slot，SQD 重查成功且实测值＝资产值＝2，才记 `INHERITED_REFUTED`，不入候选，免该 slot 的修复 Helius getBlock；getBlocks 确认仍照常。重查值变化整图回退，失败重试按规则处理。refuted-only 无代，自有驳回不能导出，只能带出继承部分。回填用 `sqd_coverage_probe.py export-shared-map --case-root <案目录> --probe-id <probe_id> --out <skill根>/assets/sqd-solana-coverage-map/ --repair-gid <gid>`；无代将最后一项换为 `--no-repair`，仍须满足导出器前置校验；调度方验收入库。来源可信是前提，导出不深验源案全量证据。

第 30 行关于压缩的追加句可保留：它限定了经 `curl_json` 的请求，没有把 21 倍实测外推成 Helius 保证收益。另在同条新增：

> 在 `references/data-pipeline-solana-capture.md:198` 第 2 条末尾追加：“9.2.0 起 α 修复将状态探针并入 census；无重试时每候选 slot 一次 SQD 请求，β 不变；`coverage_probe_query_sha256/coverage_probe_response_sha256` 与 `query_body_sha256/response_sha256` 分别同值。”

第 31 行还需允许改 README 首段；目前 `README.md:3` 把来源限定为 `--full`，并保留“首版未入库”的过时叙述，与链式回填冲突。替换 §2.5：

> - 2.5 将资产 README 首段改为：“本目录存放由已发布案级 coverage 经 `sqd_coverage_probe.py export-shared-map` 导出的共享覆盖三件套；源 coverage 可来自全扫或成功的地图复用。”其后追加：“coverage 开工先 find-known-map；有 chosen 必用 --known-map，完整加载失败时按探针规则回退。coverage 发布后按 split-run §1.3 回填，有修复代指定 --repair-gid，无代使用 --no-repair。调度方验收后将三件套入库。”W1 新增的 refuted_evidence 段保留。

原 §2.2 的 `NO_KNOWN…` 不应作为状态名进入执行文档；以上改为发布条件与有代/无代分支，避免把 **repair 的 refuted-only** 与 **coverage verdict** 混为一谈。

**7．【必改】§0.5、§1.2：锚只有前缀；“禁止重写”又要求重写，必须消除自相矛盾。**

三处主锚及 gzip 锚均已按整行亲核，各恰好出现一次：

`references/split-run.md:41`

```text
- **A2 全部**：EVM 四查；Solana 五查＝四查＋精确重放 `exact_reconcile`。所有家族一律由 `scripts/report/reconciliation_report.py` 接收 job spec 后受控启动，并原子生成 `reconciliation-report/v3` wrapper；runner 校验新鲜 receipt、target、生产者和输入/receipt 哈希，禁止手拼 wrapper。Solana A2 FAIL 先跑 coverage 探针归因，再按 α/β 止损线运行修复生产者，禁止逐账户 BFS 补账。时间抽查跑 `scripts/lib/time_spotcheck.py`（EVM 案 `time_spotcheck.json` 为 READY 必备件＋AUTO_GATES，6.7.0）——**默认锚点级直查即闭环，全史第二源重拉是例外动作**（触发条件与 pilot 报 ETA 纪律见 evm-recon §13；APU 案照旧模板全史重拉 103 分钟纯冗余教训）。
```

`commands-staging/token-analyze-1.md:12`

```text
3. **范围**＝A0–A2 全部＋A3 机械子层（split-run §1.3）；Solana 案 A2＝五查（四查＋`exact_reconcile`）。其中第 9 项必须运行 initial 持仓分布扫描并产 `distribution_scan.json`；CEX 黑箱关卡维持点名制——仅当我在命令里附加"CEX 黑箱 ≤N% 才继续"类要求时执行。
```

`references/data-pipeline-solana-capture.md:202`

```text
**共享地图生命周期**：已知缺陷地图只省重复探测，不替代本案证据。地图 TTL（有效期）为 30 天；已知缺陷 slot 仍逐个复核；每次运行抽 canary（哨兵 slot）验证健康区和已知缺陷区，任一不符就停止复用并重建地图。
```

`references/data-pipeline-solana-capture.md:107`

```text
- **gzip 压缩 = 21 倍**：同段对照实测明文 4.65 slots/s vs `--compressed` 98 slots/s（wSOL 高密度压测,压缩比 ~40x；普通 mint 预计 5-15x）。requests.Session 默认协商 gzip——**新脚本一律 requests,遗留 curl 件必须补 `--compressed`**。
```

在第 13 行后新增：

> - 0.5 本单用上述完整原文作为锚，不能把“以……开头”当作 `grep -F -x` 的整行参数。调度方在 v2 中更新实际基线及完整锚；施工前逐一确认恰命中一处。基线检查中的比较 commit 必须替换为本单派工基线，不能原样沿用 W1 的 cc6298b 无差异要求。

替换第 21 行：

> - 1.2 文档以追加为主；仅允许 §2.4 生命周期段及 §2.5 README 首段按指定原文替换。`references/` 本单净增 ≤1,800 B，commands 指定文件净增 ≤260 B，按 UTF-8 字节计，以 W2 派工基线比较；另列全工程相对 cc6298b 的累计变化，避免把 W1 增量混作 W2 增量。不得为过预算删除无关内容。

预算核验：

- v1 原拟 split-run 追加 **711 B**，commands 追加 **172 B**，压缩句 **193 B**。
- 生命周期原段 **288 B**；替换为最多 900 B 时，原方案 references 合计净增约 **1,516 B**，能满足 1,800 B。
- 本报告第 6 条替换方案，包括新增 W4 句，references 净增约 **1,661 B**，仍有少量排版余量；commands 约 **120 B**。
- `SKILL.md` 当前 **8,021 B**；`docs_lint.py:300–302` 上限是 8,192 B，等长版本替换不增加字节。
- **docs_lint 没有 references 总字节预算检查；test_g3_docs_guards 也没有。** 后者检查的是 analyze/research 的四项文档约束，不能证明 W2 新句完整、预算合规。

**8．【必改】§2.6：9.2.0 档位正确，但索引超限、日期占位符非法，指标不能预填成结果。**

版本四处亲核一致：`VERSION:1`、`pyproject.toml:15`、`SKILL.md:23`、`CHANGELOG.md:13/:104` 均为 9.1.1。按 `CHANGELOG.md:4` 的规则，新增公开子命令及向后兼容字段扩展足以支持 **9.2.0**；不是因为“改了 producer SHA”就必须升次版本。

原拟索引 **240 B**，超过本单 220 B。`2026-09-2X` 不能通过 `changelog_lint.py:21–33`。

替换第 32 行：

> - 2.6 四处版本统一更新为 9.2.0。调度方在 v2 填入实际发布日期；若为 2026-09-24，索引采用下列 173 B 原文：  
> `- **9.2.0**（2026-09-24）Solana −1 提速：驳回继承、find-known-map 开工硬性、curl_json 压缩、修复 α 合并 SQD 请求；producer 登记，档位 次。`  
> 在原 :104 前插入 `## [9.2.0] - 2026-09-24 — Solana −1 机械段提速`，日期须与索引一致；按原 :106-109 保留“出处与裁决／改法／字节与测试／成本-质量指标”四条格式。“改法”按实际施工顺序 W1→W4→W3→W2 说明。测试和成本采用实际完成记录；缺失指标写“未记录”，不得预填 PASS、轮次或线上收益。W2 自身行数与测试由本次完成结果回填，避免要求先引用尚未完成的 W2_done。沙箱外部调用与调度方联网验收分别统计。

源码规则还包括：活跃与归档合并后的版本唯一性、活跃条目降序、归档降序及两者边界。它**不检查**索引长度、四条详细段内容，也没有用日历解析验证日期真实性；这些仍需人工验收。

**9．【必改】§0.7 与继承的 §0.6：检查命令会越过禁读边界；白名单和清理纪律也需明确。**

确定冲突：

- `changelog_lint.py:16/:41` 直接读取 `archive/CHANGELOG-archive.md`。
- `docs_lint.py:266–268/:303–306` 包含 `references/attic.md`；`:129–134` 递归读取仓库 Markdown，会进入其他 maintenance 等禁区。
- W2 沿用 W1 §0.6 的 `.staging_w1` 与 `rm -rf`，既用错工单目录，也违反当前禁止批量删除规则。

替换第 16 行，并补充 §0.6：

> - 0.7 施工者仅运行经源码确认不越过禁读范围的离线定向测试。`docs_lint.py`、`changelog_lint.py` 完整运行交调度方负责，完成报告明确写“待调度方验收”，不得伪报 PASS，也不得修改检查器以跳过禁区后称完整通过。调度方在具备相应读取权限的验收环境运行原版检查器及全工程回归，补录实际结果后收官。`test_g3_docs_guards.py` 仅作既有文档回归；W2 新增句和字节预算另行逐项验收。  
> - 0.6 保留离线、不 commit/push、禁 stash/checkout/reset、不建 worktree。施工测试使用 tempfile；如需工作树内临时目录，明确限定为本单 `.staging_w2/tmp`，仅允许创建和读取本次测试自行生成的内容，不读取任何既有 staging 资料。禁止 `rm -rf` 等批量清理；清理须遵守当前文件删除纪律。  
> - 0.3 白名单中的 find 实现包括私有 helper、parser、main 接线及必需 import；不得借此修改 `_dry_run`、`_load_known_map`、export 或查询模板语义。完成报告路径明确为 `maintenance/repair-20260924b-sol-stage1-speed/W2_done.md`。资产数据文件和仓库外 commands 不属于施工白名单。

**10．【必改】§2.1 测试只有筛选样例，不能验证选择规则或离线边界。**

临时小资产完全可行，不需要真实 98 MB counts 文件。现有共享地图夹具可参考 `test_sqd_coverage_probe.py:538–575`。但“一个合格、两个不合格”无法验证任何排名规则。

替换第 27 行末尾测试要求：

> 测试全部采用 tempfile 内小资产并固定当前时间；不得依赖仓库真实地图在测试当天是否过期。覆盖：①过期、不重叠、合格及空目录；②多份合格资产的 overlap、交集 refuted 数、UTC 时间和路径并列排序；③JSON 损坏、字段类型错误、缺失二进制、size 不符、区间不一致、路径逃逸、模板不符；④旧资产 refuted 空且缺 refuted_evidence 仍可轻筛；⑤多目录追加和去重、默认目录不依赖 cwd；⑥一行 JSON 的确切字段、chosen 与 accepted[0] 一致、正常无图 exit 2 与运行错误的区别。测试中将默认目录指向临时目录，并将网络调用、完整 validate_shared_map 及二进制解压替换为一旦调用即失败的桩，证明 find 保持离线轻筛。最后保留既有 probe/export 测试，确认 main 接线不破坏旧入口。

**11．【建议】事实③与完成报告：commands 同步已经注明责任，再补可检查的收官条件即可。**

本轮已逐字比较，`commands-staging/token-analyze-1.md` 与 `~/.claude/commands/token-analyze-1.md` 确实一致。v1 第 7 行已经写了“调度方收官后同步”，**不能判定它完全漏写责任人**；不足在于完成报告没有同步验收项。

在第 37 行后新增：

> 调度方收官项：将已验收的 commands-staging/token-analyze-1.md 同步至 `~/.claude/commands/token-analyze-1.md`，记录两者逐字比较结果；同步由调度方完成，不扩大施工者白名单。完整 docs_lint/changelog_lint、W3 压缩联网验收及 W4 合并查询实测均按实际结果记录，施工离线通过不替代这些验收。

| 条目 | 等级 | 依据文件:行 |
|---|---|---|
| ①②事实、TTL、资产现状及耗时口径 | 必改 | `sqd_coverage_probe.py:697/:1223`；`solana_exact_validate.py:728`；资产 JSON:1 |
| producer 协议集合与 W1/W2 哈希身份 | 必改 | `producer_history.py:3/:95/:103/:239/:247/:255/:263`；`solana_exact_validate.py:499` |
| manifest 的 W1 新消费者登记前置 | 必改 | `workorder_W1.md:48`；`invariant_manifest.json:627`；`invariant_scan.py:1165/:1277` |
| find 轻校验、路径、JSON 与退出码 | 必改 | `workorder_W2.md:27`；`sqd_coverage_probe.py:835/:1128`；`solana_exact_validate.py:785` |
| overlap／refuted／时间排序取舍 | 建议 | `sqd_coverage_probe.py:743/:849`；`workorder_W1.md:27` |
| 继承范围、resume、导出及 W4 文档遗漏 | 必改 | `workorder_W1.md:27/:31/:57`；`workorder_W4.md:25/:28`；`sqd_coverage_probe.py:1283` |
| 整行锚、段落改写例外与字节预算 | 必改 | `workorder_W2.md:21/:28–31`；`docs_lint.py:300`；`test_g3_docs_guards.py:78` |
| CHANGELOG 超限、日期与实际指标 | 必改 | `CHANGELOG.md:4/:13/:104`；`changelog_lint.py:21/:48/:57` |
| 禁读与检查命令冲突、施工白名单 | 必改 | `docs_lint.py:129/:266`；`changelog_lint.py:16/:41`；`workorder_W1.md:21` |
| find 测试覆盖不足 | 必改 | `workorder_W2.md:27`；`test_sqd_coverage_probe.py:538` |
| commands 同步验收记录 | 建议 | `workorder_W2.md:7/:37`；`commands-staging/token-analyze-1.md:12` |
