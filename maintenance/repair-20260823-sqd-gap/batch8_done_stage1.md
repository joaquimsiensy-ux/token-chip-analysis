# Batch 8 第一段施工完成报告

## 结论

第一段 F1-F4 与新测试已在 `d8a427b` 基线上完成，未 commit，未触碰第二段文件。
Batch 8 定向测试及原 SQD repair 回归为 GREEN。既有 133 项 suite 实测为
`130 PASS / 3 FAIL`，不能声称全绿：两项是沙箱禁止 loopback bind，另一项是
`d8a427b` 自带的版本不一致，且修复面属于第二段白名单。

## 开工门禁与写边界

- 开工 HEAD：`d8a427b`。
- 开工分支：`main`。
- 开工状态：仅 `batch8_workorder.md` untracked，符合工单例外。
- 第一段施工文件：
  - `scripts/solana/sqd_gap_repair.py`
  - `scripts/tests/test_batch8_repair_scale.py`（新）
  - `maintenance/repair-20260823-sqd-gap/batch8_green_evidence.txt`（新）
  - `maintenance/repair-20260823-sqd-gap/batch8_done_stage1.md`（本文件，新）
- 未改 `producer_history.py`、`run_all.py`、VERSION/pyproject/SKILL、CHANGELOG，
  未改禁区文件，未注册第 134 项测试。

## 规格逐条对照

### F1 指纹 key 无关化

- 新增 `reference_endpoint_identity()`，先调用既有 `public_endpoint()` 去除
  query、fragment 与凭证路径段，再对公开 host/path 输入调用
  `endpoint_fingerprint()`。
- plan、ledger header、ledger row 继续同源使用 `args.reference_fingerprint`；
  `load_resume_slots()` 的行校验和 required 字段集未改。
- 两个 Helius key、两个自定义凭证 URL、两个 fixture query 的等价测试均通过；
  Helius key A/B 的 plan digest 相同。

### F2 key 池与热降级

- 新增 `KEYS_FILE=~/.config/helius/api-keys`、`--reference-keys-file` 与
  `load_reference_endpoints()`；顺序为显式 RPC 单端点，或 CLI key 文件，或
  缺省多 key 文件，最后回退原 `KEY_FILE` 单 key。
- 每行 strip、忽略空行、保序去重；未改变 `KEY_FILE` 常量及其单行含义。
- `ReferenceEndpointPool` 锁保护轮转游标与 active 集；quota key 在进程内永久
  摘除，本 slot 立即换剩余 key；全部摘除才抛 `QuotaStopped`。
- ledger `attempt` 是该 slot 的实际 getBlock 尝试数；required 字段集未变。
- beta 与 verify live-canary 只取解析后第一个 endpoint，未池化 beta 逻辑。

### F3 并发保序

- 新增 `--workers N`，默认 1，拒绝小于 1。
- `workers=1` 保留逐 slot 的 probe -> getBlock -> census 顺序。
- `workers>1` 使用线程池按 candidate 顺序提交；主线程按 candidate 顺序等待、
  落 evidence、追加 ledger、推进 completed，再 yield 给装配层。
- futures 重排缓冲上限为 `4 * workers`；quota 时取消未开始任务、等待在途任务
  收口但丢弃未到消费点的结果，STOPPED cursor 使用最小未落账消费 slot。
- SQD probe/census 对 retryable/529/5xx 最多重试三次，退避为 2/4/8 秒；
  getBlock 非 quota 错误不重试。
- 线程安全自查：`RepairLiveTransport` 只有不可变 endpoint 字段；
  `net.curl_json()` 每次调用构造局部命令、局部 subprocess 结果，没有共享 session
  或共享可变响应状态。线程安全仿真 transport 的实测 `max_active > 1`。

### F4 流式装配

- `_live_payloads` 现为生成器；resume evidence 逐 slot 惰性重建，新增 payload
  持久化后立即 yield，不再保留全量 `payloads` 列表。
- `_produce_blocks` 在 try 内直接流式消费生成器，生成器内的 `QuotaStopped`
  仍由原 STOPPED/exit 3 语义收口。
- 允许的聚合结构 census/layer/maps/evidence_manifest 保持；并发额外常驻量限制为
  最多 `4 * workers` 个 future/result。
- blocks-cache 路径仍使用原 `_cache_payloads` 小规模列表，行为未改。
- `_persist_live_slot` 与装配 `_publish_json_exclusive` 的幂等共存路径未改变。

## 测试方法与结果

- RED：在生产者仍为 `d8a427b` 原实现时先运行新测试，退出 1；首个 F1 断言因
  `reference_endpoint_identity` 不存在而失败。原始失败要点已写入绿证。
- Batch 8 GREEN：退出 0。覆盖 key-neutral fingerprint/plan digest、key 文件优先级、
  workers=4 的 20-slot 乱序保序、10/10 key 轮转、resume 全命中、evidence 完整、
  单 key 热摘除、全池 quota STOPPED/exit 3、跨 key resume 不重拉、SQD 2/4/8
  退避与流式结构。
- 原 `test_sqd_gap_repair.py`：退出 0。
- `test_batch3c_census_fields.py`、`test_net_result.py`、`git diff --check`：均退出 0。
- 既有 suite：133 项中 130 PASS、3 FAIL：
  1. Solana vertical slice：loopback bind `EPERM`；
  2. EVM vertical slice：loopback bind `EPERM`；
  3. version consistency：基线 `VERSION=6.52.5`、`pyproject.toml=6.52.4`。

流式测试的局限：结构断言证明生产生成器不再持有 payload 全集，20-slot 并发测试
证明消费顺序、evidence/ledger 与 resume 语义；它不是 153,667-slot 实机 RSS 压测。
内存上界还由实现中的 `4 * workers` future 窗口直接约束。

## 基线残余与停工边界

`git show d8a427b:VERSION` 为 `6.52.5`，而
`git show d8a427b:pyproject.toml` 为 `version = "6.52.4"`。当前两文件与基线一致。
工单把版本五处升级到 6.52.6 明确放在第二段，因此第一段不能通过修改
`pyproject.toml` 消除该失败。两项 loopback 失败同样发生在未修改的既有测试中。

本报告写毕即停工：不 commit，不进入第二段，等待验收方处理第一段 commit 与
`batch8_stage2_anchor.txt`。
