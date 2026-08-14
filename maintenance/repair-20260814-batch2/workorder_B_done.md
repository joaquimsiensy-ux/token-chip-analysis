# 工单 B（F-02）完工摘要

施工分支：`repair-20260814-batch2`。全程未执行 `git add/commit/push/checkout` 或其他 git 写命令；修改均在本仓库内。

## 一、同族 `rg` 复核

开工后先按工单原样执行：

```bash
rg -ln "adversarial-review" --glob '!maintenance/**' --glob '!archive/**' --glob '!blind-reviews/**'
rg -ln "adversarial_review_runner|check_adversarial|ADVERSARIAL_RUNNERS" --glob '!maintenance/**'
```

除工单已知生产/消费/测试/文档面外，新增命中与处置如下：

- `scripts/report/a4_gate.py`：仅方法说明提到 adversarial-review，与 v3 artifact/aggregate 无生产消费逻辑；不改。
- `references/research-workflows.md`：旧 prompt 仍输出未包裹的单条 verdict schema，已同步为 `adversarial-review-artifact/v1`，并写明 critic 分型及并集覆盖。
- `scripts/tests/contract_manifest.json`：现有针只要求正式文档保留 `adversarial-review-execution/v1`；v3 文档仍满足，未新增或改动契约 ID。
- `scripts/tests/invariant_scan.py`：只从生产代码派生 schema/runner/原子写清单，不含本单手写校验逻辑；无需改逻辑，`invariant_manifest.json` 已按真实生产/消费关系同步。
- `blind-reviews/r9/45bf8f3/round-a-sixlens.md` 是工单指定原反例存档；`archive/CHANGELOG-archive.md` 是第二条 rg 未排除 archive 后的历史命中，均不改。

## 二、改动清单

### 生产与消费链

- `scripts/report/adversarial_review_runner.py`
  - 公共纯校验函数：A4 registry、分型 artifact、blocker、claim 并集覆盖。
  - runner 默认且强制绑定案根固定权威表 `a4_claims.json`；向 entrypoint 提供 registry sha 环境变量。
  - claim-review 校验三档 verdict、非空 evidence、alternative_explanations 类型、artifact 内 claim_id 唯一且不得越界；critic 校验 `findings[]` 与 `non_covered[]` 在场。
  - execution receipt 新增 `registry_sha256`，并与 role/artifact 三方互验。
  - 新增 `finalize` 子命令：读取当前 registry、execution receipts、artifact 实物和 blocker 输入，重建覆盖并原子产出 `adversarial-review/v3`。
  - runner/finalize 错误统一 exit 2；staging/tmp/未配套正式 artifact 清理，输入不合格不落聚合半成品。
- `scripts/report/shared_release_receipt.py`
  - 新增 `validate_adversarial_review`，独立重读固定 registry、重算 size/sha/schema，逐件重验 runner、execution receipt、artifact 内容与并集覆盖。
  - v2 明确 fail-closed，并给出“按 v3 重跑对抗复核”迁移指引。
- `scripts/report/audit_release_gate.py`
  - `check_adversarial` 显式只认 v3，并复用 shared 的同一字节级验证链；不再以角色名子串和 blocker 自报作为放行依据。

### 测试与登记

- 新增 `scripts/tests/test_repair_batch2_f02.py`，覆盖原反例、同族变体、失败原子性、两侧消费重验、v2 迁移与全链绿例；已挂 `scripts/tests/run_all.py`。
- `scripts/tests/invariant_manifest.json` 登记 artifact/execution/aggregate 的真实 producer/consumer 关系及 `finalize_review` 原子写入口。
- `scripts/tests/test_audit_release_gate.py` 抽出 `refresh_adversarial`：任何夹具改写 `a4_claims.json` 后都真跑 runner/finalize，不手补 sha。
- `scripts/tests/test_repair_batch_d.py` 的 Solana 同构 fixture、`test_round4b_provenance.py` 的 runner fixture 升级为 v3。
- 全量首轮发现另外两处共享 fixture 在 build_case 后改写 registry：`test_review_20260804_p105.py` 与 `test_a4_gate.py` 已按真实 A4 顺序重跑对抗复核及 shared receipt；由其共享的 `test_repair_batch_b.py` 随之恢复。

### 文档与存量影响

- `references/independent-audit-protocol.md`：更新 runner/finalize 命令、v3 结构和迁移纪律。
- `references/analyze-workflow.md`：A4 增加 artifact/v1、并集覆盖和 v3 finalize 要求。
- `references/research-workflows.md`：prompt 输出结构对齐正式 artifact。
- `CHANGELOG.md`：登记 F-02 闭环及 AKE/B2/MOG/TAG 至少四案 v2 的重发布影响；本工单不提前执行整批计划中的 6.41.0 版本收口。

## 三、红 → 绿双跑证据

### 修前双红（生产代码未改）

命令连续执行两次：

```bash
python3 scripts/tests/test_repair_batch2_f02.py
python3 scripts/tests/test_repair_batch2_f02.py
```

两次结果完全一致：整体 `rc=1`，各报 8 项失败。原反例的逐次证据均为：

```text
FAIL 原反例：2 字节 ok 必须被 runner 拒绝且正式位/暂存位零残留
(runner rc=0, artifact_exists=True, receipt_exists=True, staging_residue=[])
```

同时非法 verdict、三种坏 evidence、重复 claim_id、损坏 JSON 均被旧 runner 以 `rc=0` 放行，确证不是“测试没命中”。

### 修后绿

- `python3 scripts/tests/test_repair_batch2_f02.py`：`rc=0`，21 项定向检查全部通过；原 `ok` 反例变为 runner `rc=2`，artifact/receipt/staging 零残留。
- 工单点名受影响测试：
  - `test_audit_release_gate.py`：`rc=0`
  - `test_repair_batch_d.py`：`rc=0`，`BATCH D 全部通过`
  - `test_round4b_provenance.py`：`rc=0`
- 全量首轮在受限沙箱内如实得到 `rc=1`：两项正式链纵切片因 `127.0.0.1 socket.bind` 被环境以 `EPERM` 阻断，另有 3 项 registry 改写夹具回归；后者已修复并逐项 `rc=0`。
- 在允许 loopback 的非沙箱环境最终连续两次运行 `python3 scripts/tests/run_all.py` 均 `rc=0`，末行均为 `全部通过`。最终一轮包含：Solana/EVM 正式纵切片、三个受影响测试、新增 F-02 回归、docs/changelog/invariant 全部 PASS。
- 最终静态检查：`git diff --check` 无输出；`invariant_scan.py` 为 producers=55、consumers=69、transport=62、atomic_writes=47、formal_entrypoints=58、exceptions=0。

## 四、六视角自审 ①：新字段与信任根

1. `claim_registry.path`：不是聚合层自报任意案内文件；生产/消费共同强制固定为案根 `a4_claims.json`，同字节替身路径也拒。
2. `claim_registry.size/sha256/schema`：finalize 从文件实物生成；shared/audit 消费时重新读取实物并独立计算 size/sha，且重新解析 `a4-claims/v2` 与唯一 claim id。
3. artifact 的 `role/registry_sha256`：runner 受控注入的 role 与当前 registry sha 为预期值；execution receipt 记录二者；finalize/shared/audit 再把 artifact 实物、execution receipt 与聚合 registry 三方比对，任何撕裂均拒。
4. `results[].claim_id/verdict/evidence/alternative_explanations`：由公共校验函数从 artifact JSON 实物读取；verdict 只认三档，evidence 必须是至少一个非空字符串，claim_id 在单 artifact 内唯一且不得越出 registry。
5. 覆盖集合：finalize 与两个消费侧均从所有 claim-review artifact 的 `results[]` 现场重建并集，不读取聚合层自报 coverage；并集必须覆盖 registry 全集，critic 不混入逐 claim 投票。
6. critic 的 `findings/non_covered` 与 `blocking_findings`：前者按角色分型强制数组在场；后者强制非空唯一 id、严格 bool、resolved=true 时非空 resolution。release_decision 只有在结构合法且无未决 blocker 时才可为 PASS，消费侧仍独立重验。
7. target/producer：finalize 从当前 `accounting_mode.json` 派生 target；shared/audit 与各自持有的当前案 target 比对；aggregate/每路 execution 的 producer/runner 均绑定当前仓库 runner 路径与 sha。

结论：没有新字段以“聚合层自己说了算”为信任根；覆盖、registry 内容与 artifact 内容都由消费侧从案内字节独立重建。

## 五、六视角自审 ②：失败路径 fail-closed 与零残留

1. runner：entrypoint 非零、未落 staging、空文件、坏 JSON、角色/schema/registry sha 错、非法 verdict/evidence/claim_id 均 exit 2；异常处理删除随机 staging、receipt tmp，以及“artifact 已发布但 receipt 未成功”的孤件。
2. runner 正式位：artifact 或 execution receipt 预先存在时拒绝覆盖；坏件测试逐条断言 artifact/receipt/staging 全不存在。
3. finalize 输入期：缺 registry、缺 execution receipt、缺 artifact、registry sha 撕裂、缺覆盖、越界 claim、坏 blocker、缺正式角色均在创建 tmp 前 exit 2，正式 `adversarial_review.json` 不存在。
4. finalize 写入期：采用同目录随机 tmp，写入后 flush+fsync，再 `os.replace`；写入/替换异常清理该次精确 tmp。已有正式输出时拒绝覆盖，防旧件被半次运行静默替换。
5. 消费侧：artifact、execution、registry、producer、target 任一后改写均拒；v2 旧件不走兼容放宽，直接给重跑指引。
6. 实跑证据覆盖了坏 JSON 的 staging 清理、三类 finalize 缺件零半成品、registry 后改写、同字节替身、execution 撕裂和 v2 拒绝；全量 suite 证明正常两角色路径未被误伤。

结论：本单涉及的失败出口均 fail-closed；受控 staging/tmp 与未配套正式位没有残留。

## 六、发现未修节

- F-02 范围内无已知未修缺口。
- `a4_gate.py` 新命中仅为方法注释，`contract_manifest.json` 新命中仅为仍有效的 execution/v1 文档针，`invariant_scan.py` 新命中仅为派生扫描器；未为凑改动而改写无关逻辑。
- 两项 loopback `EPERM` 是当前受限沙箱能力边界，不是仓库失败；已在获准环境用同一条全量命令复跑为绿。
- 6.41.0 版本号统一收口属于批 2 总计划后续工单，不在本工单提前执行；CHANGELOG 已以“待 6.41.0 汇总发布”诚实登记本单影响。
