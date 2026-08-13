# token-chip-analysis 六视角 BLOCK 修复工程计划（定稿）

## Context

codex 对 skill 仓库 main@2ebd885（v6.39.5）做六视角全库 review 判 BLOCK：13 findings（5 P0/6 P1/2 P2），Fable 已逐条独立验证全部技术属实。用户拍板：①不回退 6.39.0，在当前版本上修；②范围＝5 个 P0＋3 个 6.39.x 新引入（F-06/07/08）＋流程债，R10 存量四条（F-09/10/11/13）留台账，F-12 维持已接受边界；③硬闸人工出口统一走**裁决收据**模式。修法草案已经过对抗性设计审查（一轮 Plan 审查：F-03 草案否决改两层案、F-01 限 EVM、F-06 加指纹绑定、F-05 补第四族）。

**执行模式（用户 08-13 指定，仅适用执行阶段）**：Fable 5＝纯调度/裁判（派工单、验收、代 commit），**不读取/展开/透传 codex 会话痕迹、执行栈帧、scratchpad 日志**，验收只消费落盘产物（git diff、测试退出码、工单 md）；所有代码修改由 codex 执行。

## GPT 5.6 Pro 报告交叉对账（08-13 增补，Fable 逐条读码验证）

GPT 5.6 Pro 独立六视角报告（11 findings：2 P0/5 P1/3 P2/1 P3，BLOCK）与 codex 13 条对照：

**8 条与既有发现重合**：GPT-F-01/02（图1自报/阵营覆盖）＝codex F-04/05→已在批 C；GPT-F-03/04/05/08（未知阵营漏画/对抗复核空壳/replay gate fail-open/v2 位置 token）＝codex F-09/10/11/13→R10 台账；GPT-F-10（formal_ready 静态可伪造）＝codex F-12→已接受边界；GPT-F-11（review 包 README 计数 353 vs 354）＝review 打包器口径问题，不在 skill 运行时。

**3 条真增量，Fable 已逐条验实，按用户既定范围（只修 P0＋6.39.x 新引入）全部归 R10 台账**：

- **GPT-F-06（P1）audit_closed_accounts.py fail-open——属实**：`:263-264` getMultipleAccounts 批失败仅 log+continue；closed 集空→深挖零循环→`:345` `exit(2 if missing else 0)`，checked=0/coverage=None 时照样 exit 0，与脚本头 `:27` 自定契约「1=运行失败/样本无效」直接冲突。归因＝fail-open 家族半修残留（CHANGELOG 曾修同族采集器，此正式审计入口未等深）。风险窗口＝Solana 案通道完整性审计假绿。
- **GPT-F-07（P1）test_commands_deploy_sync.py 两条假绿——机制属实、归因修正、当前无实害**：部署目录缺失打 SKIP 但 return 0；MIGRATION_CHANGED 豁免无期限（staging 含 needle 即永久绿，部署侧内容任意陈旧不拦）。git log 查实豁免机制引入于 08-05（v6.17/6.18），**非 6.39.x 新引入**（GPT 归因"新引入"指全库视角，不落本轮范围）。**部署实态已核**：三命令 staging/部署 SHA 全一致，迁移窗口当前关闭。
- **GPT-F-09（P2）env_check.py 覆盖不足——属实但降级**：不查 Python 版本（pyproject 要求 >=3.14）、KEY_PKGS 手写 14 个漏 7 个直接依赖（报告导出/BigQuery 备用件）。PASS 输出诚实声明"14 个关键依赖"，"语义过宽"仅 FAIL 分支措辞成立。台账级：修法＝KEY_PKGS 从 pyproject 机械生成＋requires-python 检查。

**2 条细节补漏合入批 C**（已覆盖 finding 内 GPT 提出的缺口，见批 C 正文）：F-04 补日期轴校验；F-05 补地址规范化查重。GPT-F-01 的"三引擎统一 camp-series-receipt/v2"重方案不采纳（改三引擎输出 schema 面超范围，声明式 --series-source＋逐位比对等效覆盖绑定环）。台账加深 2 条随 R10 记：A5 seal 增图例集合绑定（GPT-F-03 修法）、F-12 改名降权建议（GPT-F-10 修法）。

## 修复批次与修法定案

工程目录：`maintenance/repair-20260813-sixlens/`。基线冻结 main@2ebd885，修复期间不掺新功能；并行分析案子撞闸只记录不现场改。批序 A→B→C→D（F-02 钳制必须先于 F-03，因闭合容差依赖它；F-06 迁移面最大放最后）。

### 批 A：F-01＋F-02（发布收据验证链）

主改：`scripts/evm/accounting_gate.py`、`scripts/lib/supply_truth_gate.py`、`scripts/report/shared_release_receipt.py`（两条共改此文件，一批冻结）。

- **F-01**：`tip_block` 赋值从 :437 前移到 :432（tip 取得后一切 finish 路径必带）；探测块字段语义化命名 `model_probe_block`（"探测在 tip、绑定在 as_of_block"双时点诚实记录）；shared_release_receipt 增验 **仅 family=="evm"**：tip_block 存在且 as_of_block ≤ tip_block（Solana 侧禁止套用）。**验收口径（盲审修正）**：原反例 as_of<tip 修后是**合法双时点**，不列"被拒"——被拒的是缺 tip 与 as_of>tip 倒挂；补 `as_of=1, tip=100` 合法绿例。工单①栏写明"validator 是一致性校验器，不是真实性证明器"。
- **F-02**：supply_truth_gate **formal 模式**钳制 tolerance_bps ≤ 10（exploration 不钳）；超出须 `--tolerance-waiver <收据>`，schema `tolerance-waiver/v1` **按仓内最强先例造**（distribution waiver holder_distribution_scan.py:803-817，禁新造更弱收据）：`approved_tolerance_bps`（validator 校验 `0 ≤ receipt 值 ≤ 批准值`全范围钳制）＋**裁决主体＋user_decided_at_utc**＋target 三键全等＋replay_stats sha 绑定＋**每个 evidence_ref 的 sha/size 绑定**（不止存在性）＋理由。**waiver 只绑输入侧**（不得绑 supply_truth.json 输出——鸡生蛋死锁）；**waiver 只放大 supply truth 一个不变量，不得联动放大 F-03 快照闭合容差**（两个旋钮分开命名登记）。shared_release_receipt 独立重算判定：**强制 `from supply_truth_gate import decide` 同源复用**（禁手抄公式），校验 primary_verdict==重算值＋钳制/waiver 绑定。
- 同族台账（记录不修）：accounting `--samples`、verify_recon `--top-n`、anchor_sampler 覆盖窗——均属"证据强度参数"非"判定翻转参数"，工单同族清单列全＋查证结论。

### 批 B：F-03＋F-08（分布扫描族）

主改：`scripts/report/holder_distribution_scan.py`（两条共改）、`scripts/report/audit_release_gate.py`（仅 F-03 第二层）、`references/scan-schemas.md`＋`analyze-workflow.md`＋`split-run.md`（文档与代码同批改口）。

- **F-03（两层；第一层口径经盲审二次重写）**：
  - 第一层：build_scan 双向闭合的**分母＝total_supply_raw 不是 net**（盲审抓的第五卡死点：快照分桶含 burn_sentinel，dead 地址物理在快照内——sum(balances) 闭合对象是 total；net 只作分布百分比分母。原稿对 net 闭合会误杀 mint=100/burn=20 的合法 dead-sink 案，仓内已有该纵切片正例）。公式 `|sum(balances) − total_supply_raw| ≤ total × 10/10000`，**整数交叉乘法**（`abs(sum−total)*10000 <= total*tol_bps`，18 位 decimals 大整数禁 float）；**容差独立写死 10bps，不读 supply_truth 收据值**（防 F-02 waiver 放大连带松动本闸——两个不变量两个旋钮）。实现仍为 raise 式检查、零新增输出字段，semantic_payload 零改动，A5 终态案重验不死锁。**验收补 dead-sink 20% 正例**。
  - 第二层：audit_release_gate（new-analysis profile，:785-792 旁）加交叉检查（**sha 比对不比 path**）：EVM＝`distribution_scan.input_binding.snapshot.sha256 == recon balance 查 receipt 的 inputs.balances.sha256`；**Solana 不跳过（盲审翻案）**＝绑 observation bundle 的 `holder_outputs.owners` sha（scan_token_accounts.py:257-293 已输出并哈希绑定 holders_owners.json——原稿"Solana 无 balances producer"不成立；跳过会留同值换仓绕过：总和对但 owner 分配错）。施工前 codex 先核实存量字段在场率；new-analysis 限定不变（存量终态案不跑此 profile，无追溯卡死）。同批改工作流文档：−1 以同一快照文件喂 verify_recon 与 initial scan。**禁止放进 validate_scan**（防 A5 追溯卡死冻结终态案）。**若本批文档改动触及 commands-staging 命令契约：部署同步当场做＋SHA 实测验证**（deploy sync 测试自身是弱闸不可依赖，见 R10）。
- **F-08**：validate_scan 对"**列表里已记录的**"upstream_receipts 逐项三验（存在＋sha＋size）；校验对象是记录项不是磁盘现有项（方向写反会把 6.39.5 修掉的死环修回来）；`except ValueError: pass` 拆分——"文件不存在→跳过记录"与"存在但非法（损坏/越界/符号链接）→exit 2"必须区分；文档三处（scan-schemas.md :301/:336/:377）改口"记录性收据（在场即三验）"＋optional 标注。反例必须含合法分支："案根有 channels_preflight.json 但 scan 记录为空→PASS"。

### 批 C：F-05＋F-04（阵营序列 producer→consumer 链，批内先 F-05）

主改：`scripts/evm/replay_pass2.py`、`replay_duck.py`、`scripts/solana/replay_edges.py`、`scripts/solana/build_evolution.py`（**补漏第四族**）、`scripts/report/state_from_facts.py`、`scripts/report/standard_charts.py`。

- **F-05（四族等深，共享实现）**：**单一 `validate_camp_spec()` 共享函数，四入口全部调用**（盲审采纳——四份手抄条件必然再漂移）；camps 域重复地址（跨阵营＋同阵营）一律硬拒 exit 2；查重在 set() 化**之前**跑原始列表，且**先按链规范化再查重**（EVM lowercase；Solana base58 原样）——否则大小写变体（0xAbC vs 0xabc）绕过精确匹配，回归必含大小写变体用例；build_evolution 的 `{addr: camp}` 形态用 `object_pairs_hook` 在 JSON 解析层拒重复键（解析后查永远查不到）；**replay_edges 缺 camps 文件的合法性在工单派发前 rg 调用面定案**（不留施工现场临时判断）。三条边界：**互斥只属 camps 域，entities 的 setdefault-append 多归属是 by design 不许动**；replay_duck :380 "复刻 dict 语义"注释随修复删除；两 EVM 引擎同批同深度（否则 test_engine_equivalence 自红）。
- **F-04（经盲审二次强化：从"外部文件一致"升级为"producer sidecar 链"）**：
  - **burn schema 前置定案（盲审抓的第六卡死点）**：Solana replay_edges 现役输出把 `锁仓/销毁=burned/net` 与按 net 分母的 owner 桶写进同一行——有 burn 时合计必 >100%，原稿 100% 闭合闸会误杀全部 Solana burn 案。工单第一步定口径：burn 桶显式豁免键清单（`_meta`/`burn_cum_pct`/Solana `锁仓/销毁` 行内桶，精确键名施工前 rg 定案），闭合公式＝**非 burn 桶之和 ≈ 100%**，burn 桶单独验非负有限；口径写进 scan-schemas/report-template 文档同批。
  - 白名单与数值面：standard_charts.py 把 CAMP_ORDER 拆 `CAMP_ORDER_MODERN + CAMP_ORDER_LEGACY` 两段导出（合并保原序，plot 行为零变化），compile_state import 现代段做白名单（**禁手抄第二份清单**）；增验有限数值＋值域 [0,100]＋同点合计闭合（容差 0.05pp 级）＋**日期轴统一 UTC 解析后严格递增无重复**（测试面含时区变体/闰日/倒序/重复/非法日期/naive-aware 混用）。
  - **来源绑定＝producer sidecar（替换裸 --series-source）**：四族 replay producer 写序列文件时同步写 `<series>.provenance.json` sidecar（producer 名＋inputs 路径与 sha＋输出 sha），compile_state 的 `--series-source` 必须带 sidecar：验输出 sha 匹配＋inputs sha 命中案内 verify_data_map/supply 登记面（盲审属实：裸文件比对＝把自报数据换成自报文件，伪序列可双喂 source 与 --series-source；sidecar 把伪造成本推到"伪造整案数据链"＝F-12 已接受边界同款残余）。旧案无 sidecar→不经 compile_state 的重绘路径不受影响，无追溯卡死。
  - **末点对账＝camps spec 机械派生（替换 annotation 猜测）**：sidecar 携带 camps spec sha，末点检查＝从 camps spec＋案内终态余额快照机械重算各 camp 终点份额与序列末点比对（盲审属实：facts 无 entity→camp 机器映射，靠 annotations.type 猜不成立）。**实测前置保留**：两个真实纵切片先实测可行性；不可行时**上报用户裁决后**才降级，禁止默认降级单向下界。
  - **--tol-pp 同族钳制（盲审补漏的判定翻转参数）**：figures_from_facts.py check 的 `--tol-pp` formal 路径写死默认值、仅 exploration 可覆盖（同 F-02 模式）——它直接决定图 2 末点对账 PASS/FAIL，比 `--samples/--top-n` 更同族。
  - **调用面文档同批**：state_from_facts 模块用法注释＋report-template.md 唯一生成命令随新 CLI 同批更新。F-09 root cause 顺带闭合，台账条目仍留 R10（旧 state 直喂 fig1 的重绘路径不经 compile_state）。

### 批 D：F-06＋F-07＋GPT-F-06＋流程债＋版本收口

主改：`scripts/report/entity_source_trace.py`＋`handoff_manifest.py`（**必须同批同 hunk 组**）、`a5_report_seal.py`、`scripts/evm/fetch_hypersync_v2.py`、CHANGELOG、`scripts/tests/contract_manifest.json`。

- **F-06（经盲审强化：收据主体＋真实披露核对）**：`--acknowledge-flip` 升级为裁决收据文件 `flip-adjudications/v1`，**必选件＝翻转指纹绑定**：每锚点行含 `flip_fingerprint`＝该锚点三策略 policy_details 规范化子集 sha，trace 消费收据时重算当前运行同款指纹并要求相等——底层数据一变收据自动失效必须重裁。收据强度同 F-02 waiver（按 distribution waiver 先例）：**裁决主体＋user_decided_at_utc**＋entity_file sha 绑定＋**evidence_refs sha/size 绑定**。**handoff 重放参数装配（:796-797）同批同步改传收据文件引用**（否则 freeze 重放当场断裂自卡死）；recompute_provenance_sensitivity 改按 manifest 绑定的收据放行，不再信 ledger 内嵌自报。**披露检查升级为实文核对**（盲审属实：只验 claim ID 在场挡不住无关文本——a4_gate 通用 validator 只验 text 非空）：flip claim 结构化携带三策略 top 名称与份额数字＋报告可核位置，A5 对报告 Markdown 逐项核对这些值真实在场；同时 A5 校验 ledger sha == freeze 记录的 provenance_ledger_sha256（封死 freeze 后删/换 ledger 旁路）。③迁移声明：6.39.4 后用过 ack 的案子（MOG）重 freeze 须重跑 trace。
- **F-07（经盲审翻案：真事务，不是重跑自愈）**：原稿"边写边记＋提示重跑"被否决——不变量是**全有或全无**，部分成功＋自愈提示不恢复它，原反例仍得到混合状态。改为两阶段提交：**prepare**（全部新 manifest 写各自临时件＋fsync）→**commit**（先备份原件，逐个 os.replace）；commit 期任一失败→逐文件从备份回滚＋验证回滚结果，回滚失败保留 `.recover` 恢复件＋exit 1。CLI 补捕 OSError（罩住 ensure_outdir_identity）。验收：中途注入 OSError＋**断言所有已写文件字节回滚原样**（不是只断言报错干净）。
- **GPT-F-06（用户 08-13 裁决纳入）**：audit_closed_accounts.py fail-open 收口——报告 JSON 加显式 `status` 字段；退出码对齐脚本自身契约（:27）：任一 getMultipleAccounts 批失败、deep 全 fetch_failed、checked=0 且 closed>0、墙钟截断、undetermined 过半→**exit 1**（运行失败/样本无效）；发现漏边→exit 2；充分零漏→exit 0。**边界显式定案**：closed=0（抽样内无销户账户，审计对象为空）与"查询失败"必须区分——前者如实报弱结论（status 单列），不冒充零漏强证明。单元反例（mock RPC 失败路径）进 run_all；采集工具本体不进（需网络）。
- **流程债**：D-1 两笔无版本号提交（11193f6/b9f8871）在 6.40.0 条目内追认（CHANGELOG 有版本唯一性＋物理顺序守卫，禁止倒插历史版本号）；D-2 **契约登记统一留批 D**（盲审修正：test_contract_routes 对 manifest 与 contract_ids_snapshot 精确双向相等且在 run_all——A/B/C 批内单改 manifest 必红；A/B/C 期间新契约面记入各批工单，批 D 一次性 manifest＋snapshot＋权威文档三件同步，新 schema 在 scan-schemas.md 或唯一权威页完整定义）；D-3 补 6.39.4 存量案迁移后果注记。版本三处（VERSION/SKILL.md/pyproject）统一 bump **6.40.0**（中间批不动版本，保持三处 6.39.5 一致）。

## 执行协议

### 第 0 步：计划交 codex 盲审（已完成 08-13，产物 `plan_review_codex.md`）

盲审判**反对现稿直接开工**，12 个必须改的点。Fable 逐条独立消化：**11 项采纳并已合入上文**（F-03 分母翻案 total/dead-sink 正例、Solana 第二层不跳过、F-04 producer sidecar＋burn schema 前置＋camps spec 末点派生＋--tol-pp 钳制＋文档同批、F-02/F-06 收据强度对齐 distribution waiver 先例、F-06 实文披露核对、F-07 真事务翻案、契约登记统一留 D、验收矩阵重写＋端到端绿例、注入命中标志、R10 弱闸旁证）。**1 项上报用户已裁决（08-13）**：audit_closed_accounts.py（GPT-F-06）**纳入本轮**，编入批 D；R10 台账相应从 7 条减为 6 条。

### 每批节拍（六角色映射到双执行体）

1. **Fable 派工单**：从本计划复制该批 finding 的五栏工单骨架（①不变量②同族 rg 清单③三件套测试：原反例先红后绿＋同族变体＋失败分支④新建代码六视角①②自审⑤归因预判）＋验收标准 → codex 施工线程
2. **codex 施工**：填全五栏→先红后绿→run_all 全量自跑→写 `batch<X>_workorder.md` 落盘（中文大白话），含红绿证据＋同族 rg 输出＋diff-finding-map 增量段（每 hunk 有 owner）
3. **Fable 验收（只读落盘产物）**：git diff＋run_all 退出码＋工单文件；逐 hunk 对 map；**边界外一步**出 1-2 个攻击变体交 codex 执行（Fable 出题不动手）；grep 清零不信自报；声明与磁盘实态分别验
4. **Fable 代 commit**（codex 沙箱无 git 权限，v6.20.0 模式）＋push（既有授权）
5. **批内对抗审查**：新 codex 线程盲审该批 diff（六视角①②为主）→有 finding 则消化循环（≤3 次触线冻结上报用户）
6. 全批完成后**最终快照单独验收**（不拿"每步各自过了"凑数）

### codex 调度纪律

- 每批独立 codex 后台线程；发起前 cd 回仓库根；挂 Monitor 哨兵（僵死→cancel＋resume-last，resume 首条指令＝先把已有进度落盘工单文件）
- 可靠终态＝任务列表非 running＋log 静默＋工单文件"本批完成"标记 双确认
- **上下文隔离**：Fable 不读 codex 会话原文/中间日志/scratchpad，验收材料以仓库内落盘文件与命令退出码为准

## 验证方案（最终快照验收，经盲审重写）

1. `python3 scripts/tests/run_all.py` 全量绿；新测试文件逐一确认已加 SUITE 显式清单（run_all 无自动发现）
2. **反例矩阵（盲审修正版）**，反例脚本落盘 `counterexamples/` 可重放：
   - 转"被拒"：F-02（超钳容差无 waiver）、F-03（快照缺口＋同值换仓 EVM/Solana 各一）、F-04（值域/闭合/日期轴/白名单外键＋**伪序列双喂 source 与 --series-source**）、F-05（跨阵营重复＋大小写变体＋JSON 重复键）、F-06（无收据翻转＋指纹不匹配旧收据）、F-08（记录项缺件/错 sha/错 size/越界/符号链接，确认非前置闸提前拦）、GPT-F-06（mock RPC 全失败/部分失败/checked=0 且 closed>0→exit 1）
   - **合法绿例**（防误伤，比"被拒"同等重要）：F-01 双时点诚实记录（as_of=1,tip=100）、F-03 **dead-sink 20% 案**（sum=total≠net）、F-04 **Solana burn 案**（锁仓/销毁桶在场合计口径感知通过）＋合法多阵营案、F-08 磁盘有 receipt 但 scan 未记录仍 PASS
   - F-07：注入 OSError 后**断言全部文件字节回滚原样**（全有或全无恢复才算绿）
3. 破坏性注入反证：每道新校验注入坏产物各一，**每个注入写明命中标志**（先证到达目标分支，不以非零退出码凑数）
4. **端到端绿例（盲审翻案：batch3 纵切片只到 audit release，不含 state→fig1→A4→A5——不能冒充该段覆盖）**：新建/扩展走完 `state_from_facts→figures→A4 finalize→A5 seal` 的 EVM＋Solana（含 burn）各一条端到端用例，六个卡死点（Solana tip、A5 终态重验、Solana series、末点对账、dead-sink 闭合、burn 合计）逐一有绿例覆盖
5. 版本收口：三处 6.40.0 同步；CHANGELOG 全条目＋changelog_lint 过；契约注册表与 contract_ids_snapshot 双向对账（批 D 一次性三件同步）；R10 台账在 CHANGELOG 显式注明"本轮未修，台账保留"，台账文件落 `maintenance/repair-20260813-sixlens/r10_ledger.md`（含 GPT 修法建议与加深项：A5 图例集合绑定、F-12 改名降权）
6. **R10 弱闸旁证（盲审要求：不得拿弱闸 PASS 文案当证据）**：最终工单附三份命令 staging/部署 SHA 实测全等记录＋解释器版本与全部直接依赖 version/import 实测记录（deploy sync 与 env_check 两个弱闸的 rc=0 不作为证据引用）
7. Fable 代 commit main＋push

## 关键文件

`scripts/report/shared_release_receipt.py`、`scripts/report/holder_distribution_scan.py`、`scripts/report/handoff_manifest.py`、`scripts/report/state_from_facts.py`、`scripts/lib/supply_truth_gate.py`、`scripts/evm/accounting_gate.py`、`scripts/report/entity_source_trace.py`、`scripts/report/a5_report_seal.py`、`scripts/report/audit_release_gate.py`、`scripts/tests/run_all.py`
