# W4盲审r2：FAIL

审查 HEAD：`70e14a81817316ea225d6341e2c8670c84e544a1`。

**未发现请求合并实现的新回归；WR-a 已消除 r1 的 producer 未登记问题。本轮 FAIL 是验收未完成：只读环境禁止创建系统 tempfile，导致 e 项三类产物的真实正式入口验证无法执行。不是已复现的软件正确性缺陷。**

**阻断项及复现**

我复用 `test_w4_evidence_generations` 的三类构造流程，仅在内存运行器中追加真实 `validate_repair_bundle(deep=True)`、`resolve_formal_cache` 及 kind/gid/binding/edge/meta 断言；没有替换 `historical_producer_hashes`。运行在创建第一个临时目录时停止，尚未生成产物或进入正式校验。

当前环境的最小复现命令：

```bash
python3 -B -S -c 'import tempfile; print(tempfile.mkdtemp(prefix="w4-r2-"))'
```

- **预期**：创建系统临时目录，支持构造三类产物并逐类验收。
- **实际**：`FileNotFoundError: [Errno 2] No usable temporary directory found ...`，候选包含系统临时目录、`/tmp`、`/var/tmp`。
- **影响**：不能声称三类产物已通过正式入口。`WR-a_acceptance.md` 也将此项交由盲审执行，未提供已完成的结果。

**独立核验结果**

| 项目 | 本轮结果 |
|---|---|
| a：范围与行数 | 指定 diff 仅四份文件。repair 为 `+19/-33=52` 行；登记表另由 WR-a 授权追加 `+32/-0`，不能判为 W4 越界。既有 34 条登记保持不变。manifest、schema、CLI、版本文件未改；未发现压行数造成的处理删减。 |
| b：请求与状态 | 独立执行 **39 组**响应，与基线 `_state_probe` 对照，present/nonce_count 一致。覆盖非目标块、缺键/null/空数组、重复块及 253/255/256/300 指令。7 组合法输入均为 census=1、probe=0、Helius=1。状态校验函数 AST 未变，仍先于 Helius。 |
| c：选择器与摘要 | 实际核对 instruction 字段及选择器来自 `sqd_query_body`，原有字段和键顺序保留。合法输入的两组摘要分别相等；深验源码仍检查 hex64，没有要求摘要互异。 |
| d：删除与保留 | 允许检索范围内 `_state_probe` 零残留。AST 差异仅涉及 `_census_body`、`_fetch_live_slot` 和删除 `_state_probe`；β 搜索、状态判定、退避函数未改。 |
| e：产物兼容 | 源码确有自包含的全旧、全新、混合构造，以及旧 evidence 字节、旧 ledger 行和不重采断言；**本轮磁盘构造及正式入口未完成**。 |
| f：失败与恢复 | 独立执行 SQD 耗尽：census=4、退避 2/4/8 秒、Helius=0；现有 probe/census 退避测试通过。STOPPED、成功前缀、恢复不重采完成源码复核，未重新执行磁盘流程。 |
| g：登记与报告 | W4 新测试已接入两份 main。52 行及完整 SHA 陈述正确。四协议登记均命中，且登记 commit 中脚本字节的 SHA 与当前文件一致。 |

核实的 SHA：

```text
15822564046e654b46300edcc26aeb51b397217ecce0fb555df0e891d98a1a33
```

**h：独立拒收验证**

下列输入均调用真实 `_fetch_live_slot` 与真实状态校验，仅用内存 transport 提供响应；实际 Helius 调用数均为 **0**。

| 不合法输入，slot=42 | 实际拒绝 |
|---|---|
| 两个目标块头 | `SQD census duplicated slot 42` |
| `MISSING_BLOCK` α 却有目标块头 | `SQD coverage state changed before repair` |
| `INHERITED_REFUTED` 进入 α | `non-candidate coverage state entered alpha` |
| `INHERITED_REFUTED` β，nonce=1 | `SQD coverage state changed before repair` |
| `INHERITED_REFUTED` β，无目标块头 | 同上 |
| `DEFECT_CANDIDATE` α，nonce=1 | 同上 |

“α 有块头就拒绝”不能泛化：`DEFECT_CANDIDATE` α 有头且 nonce=0 应通过，本轮正例也通过。

本轮未复跑并发磁盘流程、STOPPED 落盘、三类产物深验与 resolver、依赖 `.staging_b3` 的完整套件或在线 SQD；调度方已有结果未冒充独立复跑。完成 e 项仍需要允许系统 tempfile 写入的执行环境，仓库可继续保持只读。

全程未读取 `~/.codex/`、memories 或其他禁读路径，未联网、未成功新建或修改文件、未 commit；结束时工作树干净。