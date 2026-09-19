# 盲审 R3a：3 条发现

审查基线：`c22d102aa4f59ee647def2b63d55e24f96316097`；分支 `main`；VERSION=`9.0.1`；git status 前/后：空/空。两次状态检查均退出 0、stdout 为 0 字节。

本轮发现 **3 条 minor，均为 B 类**。未发现 R1/R2 修复新引入的不一致。以下发现涉及的文档及代码，相对 R1 内容基线 `3942c23` 均无差异。

全程离线、只读；未读取 `~/.codex/` 或指定禁读内容，未新建或修改文件，未 commit。

## 覆盖声明

46 份必审文档共 6,564 行，全部纳入逐文件检索；另核对 `CHANGELOG.md` 文件头版本规则及 7.2.0–9.0.1 当前行为描述。

从 SKILL、analyze-workflow、split-run 提取并清理出 **263 个核心检索条目**：阶段 11、门禁编号 17、schema/协议 22、脚本 33、CLI 参数 41、文件名 90、阈值 19、角色/链档位 13、子命令 17。使用显式文件白名单执行 `rg -n -F`，得到 1,230 行命中，展开相关上下文核对；对 schema 分册另逐节比对字段、常量与生产分支。

代码侧检查了 argparse/分派定义、产物构造与写出路径、相关校验器及测试；对 `scripts/` 的 310 个 Python 文件做了只读 AST 解析。重点核对用户指定的分段命令、Solana CLI、标签维护、环境依赖和复盘命令，并检查 `agents/openai.yaml`、`pyproject.toml`。候选问题均反查了历史说明、探索档、别名及前两轮报告。未复跑需要落盘的测试；下述内存复现没有联网或写文件。

逐文件覆盖清单：

```text
SKILL.md
references/address-book.md
references/analysis-playbook.md
references/analyze-workflow.md
references/context-discipline.md
references/data-pipeline-evm-channels.md
references/data-pipeline-evm-recon.md
references/data-pipeline-evm-sources.md
references/data-pipeline-evm.md
references/data-pipeline-robinhood-channels.md
references/data-pipeline-robinhood-methods.md
references/data-pipeline-robinhood-traps.md
references/data-pipeline-robinhood.md
references/data-pipeline-solana-capture.md
references/data-pipeline-solana-scan.md
references/data-pipeline-solana.md
references/economic-control-accounting.md
references/environment.md
references/independent-audit-protocol.md
references/lp-fee-accounting.md
references/maintenance-review-repair.md
references/monitoring-package.md
references/playbook-entity-cluster-cost.md
references/playbook-entity-cluster-methods.md
references/playbook-entity-cluster-tiering.md
references/playbook-evidence-wording.md
references/playbook-state-anomaly.md
references/playbook-supply-recon.md
references/report-template.md
references/research-workflows.md
references/retrospective.md
references/scan-schemas.md
references/split-run.md
references/casebook/README.md
references/casebook/cex-custody-methods.md
references/casebook/cex-custody.md
references/casebook/entity-clustering-methods.md
references/casebook/entity-clustering.md
references/casebook/supply-accounting-methods.md
references/casebook/supply-accounting.md
references/labels/README.md
references/labels/MAINTENANCE.md
commands-staging/token-analyze-1.md
commands-staging/token-analyze-2.md
commands-staging/token-analyze-3.md
commands-staging/token-analyze.md
CHANGELOG.md（限定上述范围）
```

## 发现（按严重度排序）

### D1 — minor — B 类 — `--live-canary` 被描述为复验覆盖位图，实际核对的是单块哈希与交易签名

- 位置甲：[references/scan-schemas.md:714](/Users/uravvv/.claude/skills/token-chip-analysis/references/scan-schemas.md:714) 原文「`--live-canary 重拉若干段与位图切片对表。`」
- 位置乙：
  - [scripts/solana/sqd_gap_repair.py:1549](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_gap_repair.py:1549) 原文「`verify.add_argument("--live-canary", type=int, default=0)`」
  - 同文件第 1508 行原文「`result = transport.call("reference-getBlock", _rpc_body(slot))`」
  - [scripts/lib/solana_exact_validate.py:1404](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_exact_validate.py:1404) 原文：
    ```python
    if block.get("blockhash") != expected.get("blockhash") \
            or signatures != expected_signatures:
    ```
- 矛盾点：该参数属于 repair 的 `verify` 子命令，抽取 census 中的 slot 重拉 `getBlock`，比较块哈希和交易签名；没有执行文档承诺的 getBlocks 区间与位图切片核对，会使执行者误以为覆盖位图已获在线复验。
- 反向验证：覆盖探针的 `build_parser()` 没有此参数。仅抽取现行 parser 做内存解析，探针携带 `--live-canary 1` 返回 exit 2；repair `verify` 接受该参数。不是两个入口的同名功能。
- 修法建议：优先**删除**第 714 行末尾这句错误承诺；如保留说明，改为明确指向 repair `verify` 的块哈希/签名抽查。只改文本。
- 复现：
  ```sh
  rg -n -- 'live-canary|live_canary|reference-getBlock|signatures != expected_signatures' references/scan-schemas.md scripts/solana/sqd_coverage_probe.py scripts/solana/sqd_gap_repair.py scripts/lib/solana_exact_validate.py
  ```

### D2 — minor — B 类 — 缺块修复会输出 `sqd_blockhash: null`，字段表却限定为 string

- 位置甲：[references/scan-schemas.md:795](/Users/uravvv/.claude/skills/token-chip-analysis/references/scan-schemas.md:795) 原文「``| `census[].sqd_blockhash` | string | 是 |  |``」。同表第 793 行明确允许结果 `confirmed_missing_block`。
- 位置乙：[scripts/solana/sqd_gap_repair.py:1193](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_gap_repair.py:1193) 原文「`result = ("confirmed_missing_block" if payload.get("sqd_blockhash") is None`」；第 1202 行原文「`"sqd_blockhash": payload.get("sqd_blockhash"),`」。
- 矛盾点：缺失 SQD 区块正是该字段为 null 的生产分支；按文档的非空 string 类型验收，会把这种修复产物误判为字段类型错误。
- 反向验证：不是 legacy/exploration 差异；当前 `_routea_slot()` 同时生成该结果枚举和 census 字段。抽取原函数作内存调用，实际输出：
  ```json
  {"result":"confirmed_missing_block","sqd_blockhash":null}
  ```
- 修法建议：**修改**类型为 `string|null`，在现有说明栏注明缺失 SQD 区块时为 null。只改文本。
- 复现：
  ```sh
  rg -n 'census\[\]\.sqd_blockhash|confirmed_missing_block|"sqd_blockhash": payload.get' references/scan-schemas.md scripts/solana/sqd_gap_repair.py
  ```

### D3 — minor — B 类 — 共享地图回退对象允许空 canary 和 null 元数据，字段表仍无条件要求完整值

- 位置甲：[references/scan-schemas.md:695](/Users/uravvv/.claude/skills/token-chip-analysis/references/scan-schemas.md:695) 原文「``| `shared_map.canary.slots` | array[integer] | 是 | 长度64 |``」。第 688、689、691 行还分别把 `shared_map.version`、`shared_map.sha256`、`shared_map.generated_at` 限定为 string。
- 位置乙：[scripts/solana/sqd_coverage_probe.py:675](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_coverage_probe.py:675) 原文：
  ```python
  info = {"asset_path": str(asset_path), "version": None, "sha256": None,
          "supersedes": None, "generated_at": None, "reused_ranges": [],
  ```
  第 679 行原文「`"canary": {"slots": [], "counts_sha256": sha256_bytes(b""),`」；第 783–784 行原文：
  ```python
  info["fallback_reason"] = _safe_text(exc, endpoints)
  return info, None, None, None
  ```
  第 1333 行继续把这个对象写入产物：「`"skipped_confirmation": confirmation, "shared_map": shared_map,`」。
- 矛盾点：共享地图校验失败后，代码保留诊断对象并回退全扫，`shared_map` 并非整体置 null；因此文档对其子字段的无条件约束不成立，会把正常回退产物误判为不合规。
- 反向验证：第 1224–1248 行接收回退对象并清零 counts，随后补扫；不是异常分支直接退出。抽取现行函数及实际辅助函数，以非地图文件触发校验失败，内存结果确为 `slots=[]`，且 `version/sha256/generated_at=null`。现有回归 `test_f03_sharedmap_reuse.py:579` 亦覆盖回退后发布并验收的路径，本轮未执行该落盘测试。
- 修法建议：**修改**现有字段约束：成功复用要求 64 个 canary slot；回退允许空列表，未取得的地图元数据允许 null。只改文本，不扩大代码行为。
- 复现：
  ```sh
  rg -n 'shared_map\.(version|sha256|generated_at|canary.slots)|"version": None|"canary": \{"slots": \[\]|fallback_reason|return info, None|"shared_map": shared_map' references/scan-schemas.md scripts/solana/sqd_coverage_probe.py
  ```

## 待确认（不计入 N）

无。未把历史描述、探索档差异、代码新增而文档未提及的能力，或单纯措辞偏好计入发现。

## 汇总表

| 编号 | 严重度 | 类别 | 文件甲 | 文件乙 | 一句话 |
|---|---|---|---|---|---|
| D1 | minor | B 类 | scan-schemas.md:714 | sqd_gap_repair.py:1508；solana_exact_validate.py:1404 | live-canary 核对单块哈希/签名，并非覆盖位图 |
| D2 | minor | B 类 | scan-schemas.md:795 | sqd_gap_repair.py:1193、1202 | 缺块分支的 blockhash 为 null，与 string 类型声明冲突 |
| D3 | minor | B 类 | scan-schemas.md:688–695 | sqd_coverage_probe.py:675、783、1333 | 回退对象不满足无条件 64-slot 及非空元数据约束 |
