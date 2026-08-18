# 批 7 工单：opus 二次盲审消化（curve_cost 归属缺口 + provenance 威胁模型收敛）

> 先读同目录 `PLAN.md` 与六份 `batch*_done.md`（含 batch6_done.md 的 F-08 补丁节），再读本工单。
> 分支 `fix/sqd-solana-v4` 续作（开工先把本工单收编为独立 commit）。
> 背景：opus 二次攻击型盲审（三子代理交叉验证）对 v6.49.0（批 6 消化后态，HEAD≈`2fb1924`）的净结论——
> 一审 4 BREACH + 2 WEAK 的批 6 修复**全部闭合**（勿重复处理）；新增下列待消化项。
> 本批是同版本内继续收口，**不 bump 版本**。

## 验收方已下的定性（施工须遵循，不得擅自改级）

- **F2-01 curve_cost 归属缺口 = 必修**（覆盖面遗漏，与批 6 收敛主题一致）。
- **F2-03 攻击 B / 自证式 provenance 局限 = 非 bug，不阻断合并**：`collector_sha256` 是 git 可复现的
  **公开哈希**（`producer_history.py` docstring 自述可 `git show ... | shasum` 复现），本就是**完整性/
  版本对齐**机制，防"版本漂移 / 改装采集器冒名"，**从不是抗主动伪造的密码学签名**。攻击 B 前提是
  "对手能往 `data/` 落盘自洽伪造件"——那已是本地可信计算基失守，超出本工程"修 DISTINCT 吃边"范围。
  **禁止**为它引入签名/链上重验等新机制（那是根治宣告后的独立大工程，用户未批）。本项处置 = **文档
  定性 + 宣称收敛**，见 F2-03。
- 其余 F2-02 / F2-04 见各节。

## 施工总纪律

1. **先复核后处置**：每条动手前先给 `CONFIRMED`/`REFUTED` + **能独立跑的证据**（REFUTED 要反证）。
   二审报告过工具通道污染——你在**干净沙箱**里从**代码事实**独立复核，不采信任何二审的中间读取截图，
   只认你自己 `inspect.getsource` / 真跑 / SHA256 校验得到的确定性结论。
2. **先红后绿**：每处代码修复先提交能复现缺陷的红态测试（committed red），再修到绿。
3. **归因最小化**：只改本工单点名处，禁顺手重构。
4. **采集器零改动预期**：本批预计**不动** `fetch_sqd_transfers_v2.py`（curve_cost/replay 是消费端）。
   若复核发现确须改采集器，停下记 done 交验收方裁决，**不要**自行改采集器触发 producer 重登记。
5. ARC 案目录 `/Users/uravvv/Documents/5.6筹码分析/ARC分析/` **绝对只读**；merge/push 不做。
6. **收批标准 = SUITE 全绿（含本批新增回归）+ 每条 finding 处置台账**。SUITE 用**不含 `rg` 的
   PATH**（如 `env PATH=/usr/bin:/bin <绝对路径python3>`）复跑一遍自证可移植（批 6 F-08 教训）。

---

## F2-01 [必修] curve_cost.py 归属覆盖缺口——正式 v4 消费链未接 validate_cache_meta

**线索定位**（自行核对当前真实行号/字节，勿照抄二审给的行号）：`scripts/solana/curve_cost.py:load_edges`
的 meta 校验是**内联手写版**（只查 schema/version/mint/edge_schema/edge_semantics/order_granularity/
order_exact/finalized_upper_slot 八项），`import` 未取 `validate_cache_meta`，因此**漏掉**三道其余 5 个
正式入口都做的校验：① `collector_sha256` 命中 `producer_history` ACTIVE 归属对表；② `edge_logical_sha256`
边摘要绑定；③ `edge_rows` 行数绑定。名实不符要点：`batch3_done.md`/`batch4_done.md` 把 curve_cost 定性为
"正式内盘成本重建链，只认 v4/7""新增 v4 消费登记"，但其校验强度弱于其余 5 个走 `validate_cache_meta`
的入口。

**复核**：构造一份"字段对齐但无归属"的 v4 meta（八项内联校验能过、但 `edge_logical_sha256` 填错或
`collector_sha256` 非 ACTIVE）配伪造边喂 `curve_cost.load_edges`，确认能否放行并产出 `data/curve_costs.json`
成本结论；对照其余入口（如 replay_edges.load_edges）对同一输入应拒。**REFUTED 的话**（比如实测它其实
调了 validate_cache_meta）附反证，不修。

**修法**（CONFIRMED 才做）：把 curve_cost.load_edges 的内联校验替换为**复用** `sqd_cache_identity.
validate_cache_meta`（与 wave_scan/replay_edges/camp_series 同一套 v4 身份+归属+摘要+行数校验），别再自写
一份。**前置确认**：正式 v4 采集产物（批 4 起 finalize 必写 collector_sha256/edge_logical_sha256/edge_rows）
必带这三字段 → curve_cost 补校验**不误伤**合法使用；把这条确认写进 done。

**防回归**：新增 SUITE 用例——"字段对齐但无归属/摘要错"的 meta + 边喂 curve_cost 必拒（红→绿）；覆盖面
断言 curve_cost 与 replay 对同一非法输入等价拒绝。

---

## F2-02 [复核后接受或升级] audit_closed_accounts.py slot+owner 弱覆盖

**线索**：`audit_closed_accounts.py:load_edge_index` 完全不读 meta、只逐行 `validate_edge_row`，覆盖谓词是
slot+owner 而非交易精确。二审判 WEAK，理由 = ① 文档已诚实标注（`grep_legacy_whitelist.md` 与
`batch5_done.md` 明言其覆盖谓词仍为 slot+owner、签名未映射到 (slot,tx_index)）；② 审计结论有 RPC 链上
抽样兜底。

**处置**：**复核这两条理由是否属实**——
- 亲自读当前 `grep_legacy_whitelist.md` 与 `batch5_done.md`，确认"slot+owner 弱覆盖 + 签名未映射"的
  诚实标注**真实存在且措辞准确**（二审此处引用可能受污染，务必以当前文件真字节为准）；
- 确认 audit 的 RPC 抽样兜底路径确实存在。
- **若两条都属实** → 定为**已知的、文档化的接受项**，本批**不改逻辑**，只在 done 明确登记"6/7 入口走完整
  归属校验 + audit_closed_accounts 为文档化的第 7 个弱覆盖例外（slot+owner + RPC 兜底）"。
- **若标注不实或不存在**（污染幻觉）→ 升级：要么给 audit 也接 validate_cache_meta，要么补上诚实标注，
  记 done。

---

## F2-03 [文档定性 + 宣称收敛，非代码修复] 自证式 provenance 的威胁模型边界

**背景**：二审"攻击 B"证明——用"伪造边 + 抄公开 `collector_sha256` 常量的自洽 v4 meta + 自洽快照"可让
`cmd_reconcile` 吐 `gate_pass=True` 收据。验收方定性（见顶部）：**这不是 bug，是自证式校验的固有边界**，
不阻断合并、不引入新机制。但批 6 `batch6_done.md` §3 F-02 用了"建立归属根基""打断这个自证环"等**过强
措辞**，会造成"provenance 能抗主动伪造"的错觉。

**复核**：确认 `collector_sha256` 确为 git 可复现的公开值（读 `producer_history.py` 的 docstring/登记项
真字节）、`validate_cache_meta` 全程只校验 meta↔边文件的内部自洽而无任何"证明边真来自链上采集"的步骤。
（此结论不依赖运行时取证，污染影响不了它。）

**处置**（CONFIRMED 后）：
1. **宣称收敛**：在**当前可改的运行文档**（如 `references/data-pipeline-solana-capture.md` 的 provenance/
   威胁模型段；`PLAN.md` 走"历史件不改写、仅尾部追加"）写明 provenance 防线的**真实保护范围**——
   > 该防线防"版本漂移 / 旧采集器产物误用 / 改装采集器冒名（ARC-hotfix 型）"；**假设 `data/` 目录可信**；
   > 不防"能向 `data/` 落盘的对手用自洽伪造件（边+meta+快照）整体骗过 `gate_pass`"，因为 `collector_sha256`
   > 是完整性哈希非密码学签名。抗主动伪造需签名/链上重验，属根治宣告后续条件，本工程不实现。
   历史 done（batch6_done.md 等）**不改写**，若要修正措辞只在**文末追加勘误注记**指向本条。
2. **根治宣告条件登记**：把上述局限作为一条注记附到 PLAN 既有"根治宣告条件"（ARC 在 v4 下 A2 达 0/0 或
   47 残差归因）旁，说明"即便 A2 达标，provenance 保护范围如上，抗主动伪造是独立后续项"。
3. **不写任何新防御代码**。

---

## F2-04 [评估：低成本则修，否则记遗留] NOTE-01 reconcile TOCTOU

**线索**：`replay_edges.py:cmd_reconcile` 对内存边过逻辑摘要/行数校验后、`sha256_file(edge_path)` 物理读盘
前，磁盘边可被替换 → 最终收据 `edge_logical_sha256`(旧内存边) 与 `edge_file_sha256`(新磁盘边) 分属两份不同
边，`gate_pass` 仍 True。施工方批 6 已列此为遗留。

**复核**：确认该 TOCTOU 窗口真实存在（内存 load 与磁盘 sha256_file 是两次独立读）。

**处置裁量**：
- **若低成本可修**（例如：一次性把边文件读成 bytes，同一份 bytes 既算物理 `sha256`/大小、又 gzip 解析出
  边——load 与物理身份绑定到同一次冻结读，不改收据协议字段）→ 修，先红后绿。
- **若牵连收据协议/调用链大改** → **不强修**，在 done 明确记为遗留 + 给出推荐修法 + 影响面（同 F2-03 威胁
  模型：也属"对手能写盘"场景，严重度受同一前提约束）。
- 结论二选一必须明确，别含糊。

---

## F2-05 [污染对冲] 干净沙箱复跑与关键结论独立确认

二审报告工具通道污染。你的整批复核就是对冲——额外做两件事并写进 done：
1. 全量 SUITE 在**含 rg 与不含 rg 两种 PATH** 下各复跑一遍，贴真实汇总行与退出码（自证 121+新增用例全绿、
   可移植）。
2. F2-01 的 curve_cost 缺口用你自己的隔离构造独立复现一次（不复用二审任何产物），CONFIRMED/REFUTED 附证据。

---

## 交付物

`batch7_done.md`：
- F2-01～F2-05 每条 `CONFIRMED`/`REFUTED` 复核证据 + 处置；
- F2-01 修法 diff 要点、先红后绿证据（红态 commit 哈希）、"不误伤合法 v4 产物"确认；
- F2-02 两条理由的真字节复核结论 + 最终定性；
- F2-03 收敛后的文档措辞落点（文件+段落）+ PLAN 根治宣告条件注记；
- F2-04 修/遗留的明确二选一结论；
- 覆盖面终表（7 个 Solana 边消费入口，逐一标注归属校验状态）；
- 两种 PATH 的 SUITE 全绿输出；
- 六视角①②自审、遗留清单（交验收方/opus 三审的自述风险）。

完成即停，不 merge 不 push，等验收方复核。
