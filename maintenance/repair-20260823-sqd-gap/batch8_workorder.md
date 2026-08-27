# 批 8 工单:修复生产者规模化改造(key 无关指纹+key 池热降级+并发保序+流式装配;内嵌两段提交协议)

日期:2026-08-25。基线 HEAD:**d8a427b**(v6.52.5 facts_gate 修复后的 main;该 commit 仅动 facts_gate.py/CHANGELOG/SKILL/VERSION,**sqd_gap_repair.py 与 d943c5f 逐字节一致**,下文全部行号在本基线有效)。开工门禁:`git rev-parse --short HEAD` == d8a427b,工作区 clean(本工单文件自身除外)。
编号说明:本目录批 4~7 为本工程线历史批号(消费端 resolver 等,已收官勿动),本单顺延为批 8;先前误发的同内容"批 4"工单已作废还原,以本单为唯一有效版。

## 背景与实证(只读事实,验收方已考古完毕,勿重新考古)

ARC formal live 全普查(153,667 候选)实测暴露三个致命问题,任一不修普查都完不成:

**P1 换 key 接力断裂(接力预案的生死项)。**
- `main()` :1440-1445 把含 key 的完整 endpoint URL 交给 `endpoint_fingerprint()`(=sha256(整串 URL),scripts/lib/endpoint_identity.py:56),存 `args.reference_fingerprint`。
- 该指纹进 plan.reference(:519 live 分支)→ 进 plan_digest(:537)→ pending 目录名 `pending-{plan_digest}`(:1105)、ledger header(:587-594)、每条 ledger 行(:809)、行校验(:667-668)。
- 后果:换 Helius key → URL 变 → 指纹变 → plan_digest 变 → resume 找不到原 pending(另开空目录从零拉),即使手改目录名也被 header 比对 :639-641 与行比对 :667 拒。而全量需 154 万 credits > 单 key 100 万/月,**不换 key 拉不完,换 key 进度全废**——用户已裁决的"配额尽换免费 key 接力"预案被实现挡死。
- 实证:案根已有两个互不相认的 pending(pending-4dfb09593a6cf57e=一号 key 首跑,pending-deab99a54343105f=二号 key)。

**P2 串行速率不可行。**
- `_live_payloads`(:775-875)严格串行:每 slot 依次 SQD state-probe → Helius getBlock(transactionDetails=full)→ SQD census,三次网络往返。
- 实测(pending-deab 账本 1,111 行):428 slot/h,单 slot 间隔中位 8s(p90 9s),getBlock 响应中位 **4.48MB**(深历史大块传输是瓶颈,不是 RPS 限速——实际请求频率 ~0.36 req/s,远低于免费层 10 RPS/key)。全量 153,667 → **14.9 天**。
- 并发可行性:带宽 0.54×N MB/s(N=20 → ~11MB/s,家宽可承受);Helius RPS 远未打满;SQD 请求短小但高并发有 529 间歇过载前科(探针工程实测),需退避重试。

**P3 装配内存死结。**
- `_live_payloads` 把全部 payload 收进内存列表(:874),`_produce_blocks` 装配循环(:1147-1162)全量结束后才消费;resume 分支(:784-788)同样全量重建。
- 每 payload 含数千条 helius_sigs/sqd_sigs/sqd_transactions,估 0.5-1.5MB → 全量 153,667 个 = **100GB+ 常驻内存,收尾装配必 OOM**。exploration(6,146 块)规模小未暴露。
- 磁盘侧无死结:evidence 落盘 ~0.43MB/slot → 全量 ~66GB,本机余量 110GB,可行。

**环境事实**:三个 Helius 免费 key 已实测可用(archival 深历史 getBlock 306M/426M 全过、blockhash 交叉一致),已落 `~/.config/helius/api-keys`(每行一 key,共 3 行,chmod 600);单 key 文件 `~/.config/helius/api-key` 保持单行不动(库内外其他消费者仍读它)。

## 第一段任务(施工后停,等验收方 commit)

全部改动集中在 `scripts/solana/sqd_gap_repair.py` + 新测试文件。行为规格如下,实现细节你定,规格不得打折:

### F1 指纹 key 无关化
- live 分支的 reference_fingerprint 改为对 **public_endpoint(endpoint)**(endpoint_identity 已有,剥 query/fragment/凭证段)的指纹,即 key 无关、host 级。`--reference-rpc` 自定义端点与 fixture://helius 同规则。
- ledger 行 :809 与 plan/header 同源引用该值,行校验逻辑 :667 不改(比对对象自动变为 key 无关值)。
- 效果:不同 key 同 host → 同指纹、同 plan_digest、同 pending 目录,换 key resume 天然接上。
- 注意:endpoint_identity.py 本体**禁改**(通用件,evm_observation 等在用);在 sqd_gap_repair.py 调用侧组合 public_endpoint()+endpoint_fingerprint()。

### F2 key 池与热降级
- 新 helper:endpoints 解析顺序 = CLI `--reference-keys-file <path>`(新参数)→ 缺省路径 `~/.config/helius/api-keys`(新常量 KEYS_FILE)→ 回退现有 KEY_FILE 单 key。每行一 key,strip、忽略空行;`--reference-rpc` 显式端点时为单元素列表(现行为)。KEY_FILE 单行语义与其他消费者不受任何影响。
- reference-getBlock 请求在池内 key 间轮转分布;某 key 命中 `_is_quota`(:575-584)→ 该 key 永久摘除(本进程内),该请求用剩余 key 立即重试;**全部 key 摘除才抛 QuotaStopped**(cursor=保序消费点的最小未落账 slot;STOPPED.json/exit 3/completed_slots 语义不变)。
- ledger 行 `attempt` 记该 slot getBlock 实际尝试次数(≥1;load_resume_slots 不校验该值,schema 的 required 字段集**禁变**)。
- beta 路径(run_beta_search)与 verify 的 live-canary 保持单 endpoint(取池首个),不做池化。

### F3 并发保序拉取
- 新 CLI `--workers N`,**默认 1**(默认行为与现串行逐字节等价,既有 fixture 测试零感知)。
- N>1:worker 池按 candidate 顺序领 slot,slot 内三次调用顺序不变(probe→getBlock→census);主线程**严格按 candidate 顺序**消费:_persist_live_slot → ledger append(seq 连续)→ completed 推进。乱序先完成的结果进有界重排缓冲(上限 ~4×N,防内存)。
- worker 内 SQD 两类调用(sqd-probe/sqd-census)加退避重试(≤3 次,2/4/8s)应对 529/瞬断;重试尽头仍按现语义抛 ValueError。getBlock 的非 quota 错误不重试(现语义)。
- QuotaStopped 时:消费点之前已全部落账;之后 worker 已拉但未落账的结果丢弃(resume 重拉,浪费有界)。
- 线程安全自查:transport 层调用链(net.py 的 curl 子进程后端)是否可并发,由你实测确认;RepairFixtureTransport 若不线程安全,测试用你新建的线程安全仿真 transport,fixture 类**禁改**。

### F4 流式装配(内存 O(1) per-slot)
- `_live_payloads` 改为生成器(逐 payload yield;QuotaStopped 在生成器内 raise,外层 :1139 except 语义不变);`_produce_blocks` 装配循环流式消费,payload 用完即弃;resume 的 evidence 重建同样惰性。
- 规格:formal live 全量运行的常驻内存 = O(聚合行:census/layer/maps/evidence_manifest,约几十 MB)+O(重排缓冲),**不得 O(payload 全集)**。
- blocks_cache(exploration)路径行为不变(规模小,可不流式,但不得破坏)。
- 装配循环里对 evidence 的 `_publish_json_exclusive`(:1152-1155)与 _persist_live_slot 已写文件的共存行为,先读懂现状(resume 路径能跑通说明有既存容忍),保持等价。

### 测试(新文件 scripts/tests/test_batch8_repair_scale.py)
1. 指纹 key 无关:两个不同 key 的 Helius URL → reference_fingerprint 相等、plan_digest 相等;指纹输入串不含 key 明文。红证:修复前旧代码上该断言红(临时回滚法取证,证据落盘后还原)。
2. key 池解析:多行文件/单行回退 KEY_FILE/CLI 覆盖/空行容错。
3. 并发保序:线程安全仿真 transport 注入乱序延迟,workers=4 跑 ~20 slot:ledger seq 连续、slot 按 candidate 顺序、load_resume_slots 全 completed、evidence 齐全。
4. 热降级:key1 注入 quota → 自动切 key2 完成全部;全部 key quota → QuotaStopped + STOPPED.json + exit 3 + cursor 正确。
5. 跨 key resume(P1 的直接反证):key 集 A 拉一半 quota 停 → 换 key 集 B `--resume` → completed 全命中、网络调用计数证明未重拉已完成 slot。
6. 流式:结构性断言(生成器类型/装配后不持有全量 payload 列表);弱断言可接受,在 done 报告里说明测法与局限。
- 绿证含红→绿全程,落 `batch8_green_evidence.txt`;既有 SUITE(133 项)全绿一并自报。

### 第一段收尾
写 `batch8_done_stage1.md`(改动清单+规格逐条对照+测法说明)。**停工等验收方 commit——不改 producer_history/版本五处/CHANGELOG/run_all 注册。**

## 第二段任务(验收方 commit 后以新锚续做)

验收方将把第一段 commit 哈希写入本目录 `batch8_stage2_anchor.txt`。读到锚后:
1. `scripts/lib/producer_history.py`:sqd_gap_repair.py 的 4 条登记按批 3c 先例新增同数量 ACTIVE 条目(sha256=`git show <锚>:scripts/solana/sqd_gap_repair.py` 复算,commit=锚全哈希;旧条保留);`test_anchor_plan_v3.py` 必须 PASS。
2. `scripts/tests/run_all.py` 注册新测试(SUITE 133→134)。
3. 版本五处 **6.52.6** + CHANGELOG 条目(三根因各一句:换 key 指纹断裂/串行 15 天不可行/装配内存死结;注明两段提交与 SUITE 变化);changelog_lint 前后各跑。
4. 全量 `run_all.py` 通过(机械计数自报,环境性失败如实记录)。
5. 正式 `batch8_done.md` + 绿证追加。

## 白名单

第一段:sqd_gap_repair.py、test_batch8_repair_scale.py(新)、batch8_green_evidence.txt、batch8_done_stage1.md。
第二段:producer_history.py(仅 sqd_gap_repair 条目)、run_all.py(仅注册行)、VERSION/pyproject.toml/SKILL.md(仅版本行)、CHANGELOG.md(仅新条目)、batch8_done.md、batch8_green_evidence.txt(追加)。

## 禁区

禁改:net.py、endpoint_identity.py、solana_exact_validate.py、sqd_coverage_probe.py、既有测试文件、RepairFixtureTransport 类、ledger 行 schema(required 字段集)、STOPPED/ERROR 收据结构、bundle/resolution/census 契约字段、beta 搜索逻辑、KEY_FILE 单行语义、本目录批 4~7 历史档案。
禁 commit/push;禁联网(所有网络行为规格已由验收方实测提供,离线仿真足够);规格间发现矛盾→停工写 batch8_stopped.md,不得自行裁量降规格。
