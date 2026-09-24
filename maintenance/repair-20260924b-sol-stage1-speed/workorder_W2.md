# 工单 W2（v3.1）：−1 执行者强制使用共享覆盖地图（`find-known-map` 子命令＋流程硬性＋文档）＋ 版本 9.2.0 登记 —— 本工程收官单（producer 登记走 `workorder_WR.md` WR-b）

> 出处：用户 2026-09-24 裁决第 2 条「让 codex/opus 跑 −1 阶段时使用共享地图」。
> v3.1 变更：codex 复核 r3 通过（`review_W2_reply_r3.md`），采纳建议（CHANGELOG 施工顺序文字；README 两行）。
> v3 变更：吸收 codex 复核 r2（`review_W2_reply_r2.md`）——必改 1（§2.4 文案改为实测字节合规原文、时效起点与 β 范围改准）、2（事实快照与派工基线分离、六处完整整行锚）、3（find 部分扫描故障与退出码优先级、廉价形态约束）；建议 4（WR 时序，已改 `workorder_WR.md` v2 与 README）、5（changelog_lint 能力说明）采纳；存疑 6（W1 过渡 probe）已写入 WR v2 §0.8。
> v2 变更：吸收 codex 复核 r1（`review_W2_reply_r1.md`）11 条——必改 1/2/3/4/6/7/8/9/10 全采纳（事实与 TTL 改写、producer 登记移出本单为独立登记单、manifest 前置检查、find 轻校验/路径/JSON/退出码定形、继承范围与 resume 与导出分支与 W4 文档句、完整整行锚与预算口径、CHANGELOG 索引 173 B 与真实日期、禁读与检查器冲突、find 测试覆盖）；建议 5（排序加交集内 refuted 数）、11（commands 同步验收项）采纳。
> 事实快照＝`60c88b88a024bf463e819d846b1ba3a9e06c7ecd`（下列源码、文档行号及现役 producer 哈希均对应此快照，生产文件相对 `cc6298b` 无差异）。W2 派工基线另为前序施工收官 commit `<W2_BASE>`；派工时须更新已变化的事实、行号和锚，不能只改基线名称而沿用旧现役哈希。
> ① `scripts/solana/sqd_coverage_probe.py:1222-1227` 仅在非 resume 且指定 `--known-map` 时加载地图；resume 不支持中途换图或叠图（另起新任务属重新启动）。PYTHIA 未带地图耗时 20 h、TROLL 地图可覆盖 92% 为调度方案侧记录，本仓库未亲核。
> ② 仓库仅有 `assets/sqd-solana-coverage-map/20260827.json` 及 counts/bitmap 两份二进制（JSON 1,538,739 B；counts 97,736,104 B；bitmap 210,555 B；覆盖 `[306451717,440368381]` 共 133,916,665 slot；candidate 153,667；refuted 0）。`generated_at`＝2026-08-25T03:17:11.217739+00:00，到期 2026-09-24T03:17:11+00:00，**本工程期间已过期**；文件名不是 TTL 起点。`validate_shared_map:728-740` 只检查 `ttl_days==30` 与时间格式，过期判断在 `_load_known_map:697-700`。
> ③ 六处施工目标的完整整行锚如下（快照下均经 `grep -n -F -x` 恰命中一次；派工时按 `<W2_BASE>` 重核；不以省略号或前缀充当整行参数）：
>   - `references/split-run.md:41`：
>     ```text
>     - **A2 全部**：EVM 四查；Solana 五查＝四查＋精确重放 `exact_reconcile`。所有家族一律由 `scripts/report/reconciliation_report.py` 接收 job spec 后受控启动，并原子生成 `reconciliation-report/v3` wrapper；runner 校验新鲜 receipt、target、生产者和输入/receipt 哈希，禁止手拼 wrapper。Solana A2 FAIL 先跑 coverage 探针归因，再按 α/β 止损线运行修复生产者，禁止逐账户 BFS 补账。时间抽查跑 `scripts/lib/time_spotcheck.py`（EVM 案 `time_spotcheck.json` 为 READY 必备件＋AUTO_GATES，6.7.0）——**默认锚点级直查即闭环，全史第二源重拉是例外动作**（触发条件与 pilot 报 ETA 纪律见 evm-recon §13；APU 案照旧模板全史重拉 103 分钟纯冗余教训）。
>     ```
>   - `commands-staging/token-analyze-1.md:12`：
>     ```text
>     3. **范围**＝A0–A2 全部＋A3 机械子层（split-run §1.3）；Solana 案 A2＝五查（四查＋`exact_reconcile`）。其中第 9 项必须运行 initial 持仓分布扫描并产 `distribution_scan.json`；CEX 黑箱关卡维持点名制——仅当我在命令里附加"CEX 黑箱 ≤N% 才继续"类要求时执行。
>     ```
>   - `references/data-pipeline-solana-capture.md:202`（288 B）：
>     ```text
>     **共享地图生命周期**：已知缺陷地图只省重复探测，不替代本案证据。地图 TTL（有效期）为 30 天；已知缺陷 slot 仍逐个复核；每次运行抽 canary（哨兵 slot）验证健康区和已知缺陷区，任一不符就停止复用并重建地图。
>     ```
>   - 同文件 `:107`：
>     ```text
>     - **gzip 压缩 = 21 倍**：同段对照实测明文 4.65 slots/s vs `--compressed` 98 slots/s（wSOL 高密度压测,压缩比 ~40x；普通 mint 预计 5-15x）。requests.Session 默认协商 gzip——**新脚本一律 requests,遗留 curl 件必须补 `--compressed`**。
>     ```
>   - 同文件 `:198`：
>     ```text
>     2. `sqd_gap_repair.py/v1` 只修已确认缺陷，产 `sqd-solana-coverage-resolution/v1`、repaired `sqd-solana-cache/v4`、`sqd-solana-repair-bundle/v1` 与 `sqd-solana-repair-pointer/v1`。交易按签名取参考源真值，并统一成 `reference-nonvote-ordinal/v1`。producer 升版后同案旧 pending 可经 `--resume --adopt-pending <旧目录>` 认领（前代 sha 须在 producer_history 登记、台账 header 记 `adopted`、深验重算前代 digest；来源可信是输入前提）；Solana 请求的交易版本上限统一取 `endpoint_identity.SOLANA_MAX_SUPPORTED_TX_VERSION`，升版本或改修复请求模板须同步换代 producer。
>     ```
>   - `assets/sqd-solana-coverage-map/README.md:3`：
>     ```text
>     本目录存放由 `scripts/solana/sqd_coverage_probe.py --full` 在可联网主机完成全史扫描后发布的、可复算的 SQD 覆盖资产。批 2 只交付生产程序与协议说明，不放首版数据；首版由 Fable 本机完成 ARC 全扫并验收后入库。
>     ```
>   `~/.claude/commands/token-analyze-1.md` 与 `commands-staging/` 逐字一致（调度方收官后同步，仓库外）。
> ④ 版本四处：`VERSION:1`、`pyproject.toml:15`、`SKILL.md:23`、`CHANGELOG.md:13/:104` 均 9.1.1；`CHANGELOG.md:4` 档位规则；`changelog_lint.py:21-33` 只检查版本标题及 `YYYY-MM-DD` 日期格式，不验证日历日期真实性；实际发布日期由调度方人工核定，`2026-09-2X` 不通过；`SKILL.md` 8,021 B（`docs_lint.py:300-302` 上限 8,192 B）。
> ⑤ `invariant_manifest.json` 登记 script×schemas 关系不登记 sha；探针消费者仅 shared-map（`:627-631`）。W1 若在探针新增 schema 比较会触发 `invariant_scan.py:1277-1284` 差异（W1 已要求放校验器 helper）。
> ⑥ producer_history（快照下）：probe 现役 `c4980c98…` 登记 coverage/v1、coverage-pointer/v1；repair 现役 `3f89aab1…` 登记 cache/v4、repair-bundle/v1、coverage-resolution/v1、repair-pointer/v1；**无 shared-map 历史条目**。本单不改 producer_history（登记单 WR-b 在本单收官后登记探针最终 sha）。

## 0. 开工纪律

- 0.1 工作目录同 W1；开工贴 `git status --short`（空）、`git rev-parse HEAD`（＝`<W2_BASE>`）、`git merge-base --is-ancestor cc6298b HEAD` exit 0。**不继承** W1「相对 cc6298b 无差异」检查。
- 0.2 禁读同 W1 §0.2（含子进程）。本目录可读：`README.md`、`workorder_W*.md`、`*_done.md`、`review_W2_reply_*.md`。
- 0.3 **白名单**：生产 `scripts/solana/sqd_coverage_probe.py`（仅 `find-known-map`：私有 helper、parser、`main` 接线及必需 import；不得借此改 `_dry_run`、`_load_known_map`、export 或查询模板语义）；测试 `scripts/tests/test_sqd_coverage_probe.py`（仅新增 find 用例＋登记 main 列表）；文档 `references/split-run.md`、`references/data-pipeline-solana-capture.md`、`commands-staging/token-analyze-1.md`、`assets/sqd-solana-coverage-map/README.md`；版本 `VERSION`、`pyproject.toml`、`SKILL.md:23`、`CHANGELOG.md`；完成报告 `maintenance/repair-20260924b-sol-stage1-speed/W2_done.md`。资产数据文件与仓库外 commands 不在白名单。
- 0.4 **不改**：`scripts/lib/solana_exact_validate.py`、`scripts/solana/sqd_gap_repair.py`、`scripts/lib/net.py`、`scripts/lib/producer_history.py`、`scripts/tests/invariant_manifest.json`、`references/scan-schemas.md`、其他。
- 0.4a 调度方派工前置检查：W1 收官的 `invariant_scan.py` 结果证明探针无新增 schema 消费者；若缺 → 退回 W1 收口，不得改 manifest 规避。
- 0.5 锚用事实③列出的**完整整行**（`grep -n -F -x`），派工时由调度方重核；不能把「以……开头」当整行参数。
- 0.6 离线、不 commit/push、禁 stash/checkout/reset、不建 worktree；测试用系统 `tempfile`；**禁止 `rm -rf` 等批量删除**。
- 0.7 只运行经源码确认不越禁读范围的离线定向测试：`test_sqd_coverage_probe.py`、`invariant_scan.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`test_g3_docs_guards.py`（仅作既有文档回归）、`test_review_scale_guards.py`。`docs_lint.py`、`changelog_lint.py` 读禁区（`archive/`、`attic.md`、其他 maintenance），**交调度方本机运行**；报告写「待调度方验收」不得写 PASS，不得改检查器跳过禁区。

## 1. 硬约束

- 1.1 `find-known-map` 只读、离线执行文件扫描与轻校验，不读取/解压整份二进制、不逐 slot 分类；完整资产校验在非 resume 的 `--known-map` 加载路径执行，其后仍有在线身份、历史锚及已知 slot 重查。轻筛不替代这些。
- 1.2 文档以追加为主；仅允许 §2.4 生命周期段与 §2.5 README 首段按指定原文替换。`references/` 本单净增 ≤1,800 B、`commands-staging/token-analyze-1.md` ≤260 B（UTF-8 字节，以 `<W2_BASE>` 比较）；另列全工程相对 cc6298b 的累计变化。不得为过预算删无关内容。
- 1.3 版本档位 **9.2.0**（新增公开子命令＋向后兼容字段扩展）。
- 1.4 `SKILL.md` 只改版本号（等长替换，≤8,192 B）。

## 2. 逐条施工

- 2.1 `sqd_coverage_probe.py` 新子命令 `find-known-map --from-slot N --to-slot M [--search-dir DIR]...`，入口接线在 `main(argv)` 的 export 分支旁（锚 `    if argv and argv[0] == "export-shared-map":`），独立 parser。设计：
  - 默认目录 `Path(__file__).resolve().parents[2] / "assets/sqd-solana-coverage-map"`，不依赖 cwd；重复 `--search-dir` 在默认目录之外追加；目录与候选路径 resolve 后去重；仅扫描每个目录直接子文件；文件名用 `[0-9]` 重复八次＋`.json` 的 glob 或等价 fullmatch。CLI 要求 `0<=N<=M`。
  - 逐文件读 JSON 轻校验：顶层对象；schema `sqd-solana-shared-coverage-map/v1`；version 八位 ASCII 数字；`ttl_days` 整数 30；`generated_at` 可解析带时区 → UTC，`now > generated_at+30d` 判过期（与 `_load_known_map` 一致；不要求 version 与日期相等）；`slot_counts`/`blocks_bitmap` 元数据形态、encoding、非负整数区间、两者区间一致；与 `[N,M]` 有非空交集；两份引用文件 resolve 后仍在资产目录内、普通文件、实际 size＝声明；sha256 字段 hex64 但**不重算**；`candidate_slots`/`refuted_slots` 区间内升序去重整数；W1 定义的 `refuted_origin`/`refuted_evidence` 形态（兼容旧图空 refuted 无两键）；supersedes/canary 基本形态；`sqd.query_body_sha256 == sqd_query_template_sha256()`。
  - 轻校验补充：整数均排除 bool；两份二进制引用 resolve 后必须满足 `resolved.parent == asset_json.resolve().parent`（与正式校验器 `solana_exact_validate.py:797-799` 一致）；JSON 层检查 `refuted_slots ⊆ candidate_slots`，并检查 W1 §2.1 规定的 origin 索引、等长关系及逐证据计数；需要二进制内容才能证明的条件留给正式加载。accepted 中 `generated_at`/`expires_at` 统一输出 UTC ISO-8601。
  - 指标：`overlap_slots=max(0,min(M,to_slot)-max(N,from_slot)+1)`；`overlap_ratio=overlap_slots/(M-N+1)`；`candidate_count`/`refuted_count`＝交集内各数组元素数。排序 `(overlap_slots desc, refuted_count desc, generated_at_utc desc, absolute_path asc)`（确定性启发式，不宣称全局最优）。
  - stdout 仅一行 JSON：`{"chosen": accepted[0]|null, "accepted": [{path(绝对), version, generated_at, expires_at, overlap_slots, overlap_ratio, candidate_count, refuted_count}...], "rejected": [{path, reason}...]}`。退出码优先级：发生目录枚举、目录权限等**扫描级故障 → 1**；否则有 chosen → 0；否则 → 2。缺失目录记入 rejected 后继续（视为正常扫描）；空目录允许；单个候选文件的读取或校验失败记入 rejected 后继续，不升级为扫描级故障；扫描级故障也记录目录绝对路径与 reason，已得到的 accepted 仍排序输出、chosen 仍＝accepted[0] 或 null，但调用方不得使用 exit 1 的部分结果。除 argparse 参数错误沿用 exit 2＋stderr 外，受控退出均输出一行固定结构 JSON。调用方必须同时检查退出码与完整 JSON：仅 exit 0 可采用 chosen；仅 exit 2 且合法 JSON 中 chosen=null 才可按无图执行 `--full`；其他结果先处理错误。
  - 测试（tempfile 小资产＋固定当前时间，不依赖仓库真实地图当天是否过期）：①过期/不重叠/合格/空目录；②多份合格资产按 overlap、交集 refuted、UTC 时间、路径并列排序；③JSON 损坏、字段类型错、缺二进制、size 不符、区间不一致、路径逃逸、模板不符；④旧资产 refuted 空缺两键仍可轻筛；⑤多目录追加去重、默认目录不依赖 cwd；⑥一行 JSON 确切字段、chosen==accepted[0]、无图 exit 2 与运行错误 exit 1 区分。默认目录指向临时目录；网络调用、完整 `validate_shared_map`、二进制解压替换为一旦调用即失败的桩。保留既有 probe/export 测试确认 main 接线不破坏旧入口。补测「一目录有合格地图＋另一目录不可读」仍返回 1、保留部分 accepted 且调用方不采用；缺失目录＋合格地图返回 0；argparse exit 2 无合法结果 JSON 时不得误判为无图。
- 2.2 `references/split-run.md:41` 整行末尾追加：「**Solana coverage 开工硬性（9.2.0）**：非 resume 启动前跑 `sqd_coverage_probe.py find-known-map --from-slot <案起> --to-slot <冻结slot>`，以 receipt 的 note 保存 JSON。chosen 非空必用 `--known-map <chosen.path>`；扫描正常且 chosen=null 才用 `--full`，记非阻断 INFO。轻筛不保证可复用，加载失败可自动回退并留因。resume 不加载或叠加地图，且不保留 W1 驳回继承。coverage 有效发布且满足导出条件后回填：有修复代传 `--repair-gid <gid>`，无代（含 refuted-only）用 `--no-repair`；完整命令见采集分册，资产由调度方验收入库。」
- 2.3 `commands-staging/token-analyze-1.md:12` 整行末尾追加：「Solana coverage 开工先 find-known-map；有 chosen 必带 --known-map；回填与 resume 限制按 split-run §1.3。」
- 2.4 `references/data-pipeline-solana-capture.md:202` 整行替换为以下原文（890 B，不含行末换行）：
  「**共享地图生命周期**：地图 TTL 为源 coverage 发布后 30 天；驳回时效从首次直接 census 所属 coverage 发布时间算，链式导出不续期。资产 refuted slot 仅在本案成功复用且非 unverified 区间，重查值＝资产值＝2 且证据未过期才记 `INHERITED_REFUTED`，不入候选、免修复 Helius getBlock；getBlocks 照常。重查只证块头在、零 AdvanceNonce，不证交易集合未变；须信任来源，导出不深验源案全量证据。值变整图回退，失败按规则重试。refuted 来自发布修复 census 或继承；refuted-only 无代，只能导出继承。有效发布且满足导出条件才回填：`sqd_coverage_probe.py export-shared-map --case-root <案目录> --probe-id <probe_id> --out <skill根>/assets/sqd-solana-coverage-map/ --repair-gid <gid>`；无代改用 `--no-repair`；调度方验收入库。」
  `:107` 整行末尾追加（前置一个 ASCII 空格，192 B）：「（9.2.0 起 `scripts/lib/net.py::curl_json` 内置 `--compressed`，经该层的 Helius getBlock 与 SQD 请求自动协商压缩；ledger 字节/哈希按解码后内容计算不受影响）」
  `:198` 第 2 条整行末尾追加（前置一个 ASCII 空格，278 B）：「9.2.0 起共用修复流程将状态探针并入 census；无重试时每候选 slot 一次 SQD 请求（含 β 候选），β 搜索不变；新采 evidence 的 `coverage_probe_query_sha256/coverage_probe_response_sha256` 与 `query_body_sha256/response_sha256` 分别同值。」
  预算核算（调度方复核 r2 实测）：references 净增 1,716 B（含三处分隔空格）≤1,800 B；commands 121 B ≤260 B。
- 2.5 资产 README `:3` 首段替换为：「本目录存放由已发布案级 coverage 经 `sqd_coverage_probe.py export-shared-map` 导出的共享覆盖三件套；源 coverage 可来自全扫或成功的地图复用。」其后追加：「coverage 开工先 find-known-map；有 chosen 必用 --known-map，完整加载失败时按探针规则回退。coverage 发布后按 split-run §1.3 回填，有修复代指定 --repair-gid，无代使用 --no-repair。调度方验收后将三件套入库。」W1 新增的驳回继承段保留。
- 2.6 版本四处 9.1.1→9.2.0。CHANGELOG `:13` 前插索引（日期由调度方在派工时填实际日期，示例 2026-09-24，173 B）：`- **9.2.0**（2026-09-24）Solana −1 提速：驳回继承、find-known-map 开工硬性、curl_json 压缩、修复 α 合并 SQD 请求；producer 登记，档位 次。`；`:104` 前插 `## [9.2.0] - 2026-09-24 — Solana −1 机械段提速`（日期与索引一致），按 `:106-109` 四条格式「出处与裁决／改法（按实际施工与登记顺序 W3→W1→W4→WR-a→W2→WR-b）／字节与测试（引用 `W*_done.md` 实际记录）／成本-质量指标」；缺失指标写「未记录」，不预填 PASS/轮次/线上收益；W2 自身行数与测试由本次完成结果回填；沙箱外部调用与调度方联网验收分别统计。索引原文 173 B（不含 LF），长度由人工字节核算验收；changelog_lint 检查活跃与归档合并后的版本唯一性、活跃降序、归档降序及两者边界，不检查索引字节数、四条详细段内容或日期真实性；原版完整检查读取 archive，由调度方执行并记录。

## 3. 完成报告 `W2_done.md` 与调度方收官项

首行 `# W2 完成：…`；§0.1 输出；find 用例输出样例；文档字节净增（`wc -c` 前后，按 `<W2_BASE>` 与 cc6298b 两口径）；版本四处 grep；§0.7 尾行与未运行项；披露禁读路径。
**调度方收官项**：本机跑原版 `docs_lint.py`/`changelog_lint.py`/`run_all.py` 并记录；登记单 WR-b 登记探针最终 sha；同步 `commands-staging/token-analyze-1.md` → `~/.claude/commands/token-analyze-1.md` 并记录逐字比较；W3 压缩联网验收与 W4 合并查询实测按实际结果记录。
