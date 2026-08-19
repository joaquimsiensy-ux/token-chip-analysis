# U2b 完工报告：单元 2 盲审消化轮

日期：2026-08-17  
施工基线：`2e986c085540ab62b90158961fc3527d9fe2edf8`（`2e986c0`，6.47.0）  
施工状态：完成；未 commit、未 push；版本号、CHANGELOG、SKILL.md 均未改。

## 1. 边界与取舍

- 只修改工单白名单内文件；工单与盲审报告是开工前已在场的未跟踪输入，不属于本轮施工改动。
- R3 的 `quarantine/`、`*.recover`、`.done.json.refresh-tmp.*` / `.done.json.refresh-bak.*` 与其他残件仍全部 fail-closed。只增加分类原因和人工处置指引，不提供自动清理，避免把异常现场洗白成可采集目录。
- R5 只豁免精确文件名 `.DS_Store`，没有隐藏文件通配豁免；`.foo` 仍拒绝。
- N-01 保留 `v3` consumer 机器契约，未按旧工单误判删除；W-03 所述 recover 按 done 签发 token 的既有行为未动。
- `pre_migration_sha256` 的判别逻辑未改：仍要求键存在且为 64 位小写十六进制；证据等级改为“迁移时点自报留痕，原件覆盖后事后不可独立复验”。

## 2. R1–R10 红绿实证与改动

### R1 / B-01：collector 标签语义

- 红态：对迁移段删除 `collector_provenance`、`refreshed_from_schema`、`pre_migration_sha256`、`migrator`，再填当前公开脚本哈希，同一 `_v2_provenance` 构造输出 `R1_RED label=VERIFIED`。
- 修复：原生 v4 改标 `SELF_REPORTED` 并透传 `collector_sha256`；迁移段保持 `UNKNOWN_LEGACY` 且 `collector_sha256=null`。`scripts/` 已无 `VERIFIED` 消费。
- 绿态：同一洗标签构造输出 `R1_GREEN=SELF_REPORTED`；`test_18_preflight_labels_are_self_reported_and_identity_lineage_is_visible` PASS。
- 声明边界：该改写后的联合仍会被放行；本项只消除“已验证”过度语义，不把自报绑定升级为真伪鉴别闸。

### R2 / B-02：升级按 protocol 补登纪律

- 红态：monkeypatch 当前脚本哈希模拟升级，存量原生 v4 被拒为 `capture_identity.json ... 签发形态不一致`，recovered identity 被拒为 `recoverer 未绑定当前或历史 ACTIVE hypersync-capture-identity/v2 采集器`。
- 修复：`maintenance-review-repair.md` 明定被替换版本按其生前签发过的每个 protocol 各补一条；一版多 protocol 必须多条登记，漏一条会误拦该 protocol 全部存量。
- 绿态：新增断链固化测试 `test_19_script_upgrade_breaks_each_unsigned_protocol_boundary`，明确引用维护纪律并同时断言原生 v4 与 recovered identity 在未补登时仍拒；PASS。没有预登记未来哈希。

### R3 / B-03：inventory 分类人工出路

- 红态：三类构造分别只得到笼统结果：`quarantine` 为“未识别残件”，`done.json.recover` 和 `.done.json.refresh-tmp.123` 为“inventory 非精确三件套”。
- 修复与绿态：
  - `quarantine/`：仍拒，改报“人工检视其内容后整体移出采集根再继续”；
  - `done.json.recover`：仍拒，改报“确认同名 done 原件完好后手动移除”；
  - `.done.json.refresh-tmp.123` / `.refresh-bak.*`：仍拒，改报“刷新中断残留临时件；确认后手动移除”；
  - `.foo`：仍拒，报“逐一检视后移出采集根再继续”。
- `test_20_owned_inventory_residues_are_classified_but_still_rejected` PASS；数据管线文档新增“遗留目录残件处置手册”，并纳入 APU 0801 诊断目录。

### R4 / B-04：staged_capture 首采三态

- 红态：不存在的全新 outdir 在进入采集循环前 `rc=2`，报“缺普通文件 capture_identity.json；先运行 --recover-identity”，形成空目录死路。
- 修复：outdir 不存在、目录真空、目录仅有 `.DS_Store` 时允许进入 fetch；identity 普通文件存在时沿用；其他非真空缺 identity 目录仍 FATAL 并指向 recovery。
- 绿态：`test_u2b_staged_capture_first_run` 用 transport-only 假 `python3` 证明三种首采状态均真实进入采集循环并执行两次 fetch；`.foo` 非真空负例未触达 fetch、`rc=2`。`test_review_resume_integrity.py` PASS。

### R5 / W-01：`.DS_Store` 唯一豁免

- 红态：根目录 `.DS_Store` 使 recover 报“未识别残件”；run 内 `.DS_Store` 使 inventory 报“非精确三件套”。
- 修复：inventory 根、run 内、C12 真空判定、staged shell 真空判定只忽略精确名 `.DS_Store`。
- 绿态：根与 run 同时含 `.DS_Store` 时 recover → refresh → preflight PASS（1 条 receipt）；根或 run 放 `.foo` 仍拒。`test_21_ds_store_is_the_only_inventory_and_vacuum_exemption` PASS，staged 三态也由 R4 测试覆盖。

### R6 / W-02：REVOKED 压过当前哈希

- 红态：把当前 `fetch_hypersync_v2.py` 哈希加入全表 `REVOKED` 后，`_allowed_script_hashes` 仍返回包含当前哈希，preflight 仍输出 `VERIFIED`。
- 修复：fetch 的签发/校验 allowlist 与 channels preflight 的 v2/CSV 当前脚本并入点均先取全表 hash-wide REVOKED；命中即拒绝“当前脚本版本已被吊销，禁止继续签发/校验”。
- 绿态：同一注入得到该拒绝；`test_22_current_script_revocation_beats_current_hash_injection` 与 CSV 镜像负例均 PASS。

### R7 / W-03：recovered 身份透传

- 红态：recovered 目录的 preflight `identity_keys=provider_url,query_schema,token`，与原生身份输出同形。
- 修复：identity 段新增 `identity_schema`、`recovered`、`lineage`。
- 绿态：恢复目录输出 `identity_schema=hypersync-capture-identity/v2`、`recovered=true`、`lineage=unknown`；原生目录为 v1、`false`、`null`。由 `test_18` 固化并 PASS。

### R8 / W-05：symlink 根拒绝

- 红态：`ln -s <真实目录> <别名根>` 后，recover 成功且 refresh `upgraded=1`。
- 修复：recover/refresh 在 `resolve()` 前检查原始 outdir 是否 symlink，并把原始路径交给共享 inventory 闸。
- 绿态：同一 symlink 根报“v2 采集根目录不存在、非目录或为符号链接”；recover 与 refresh 两入口均由 `test_23_symlink_capture_roots_are_rejected_by_recover_and_refresh` 固化并 PASS。

### R9 / W-06：CSV collector receipt 严格 JSON

- 红态：含重复 `collector` 键的 CSV collector receipt 被后值覆盖并接受，输出 `kind=collector-native-csv-chain`。
- 修复：该读入点由裸 `json.loads` 改为 `strict_json_loads`。
- 绿态：同一构造拒绝 `CSV 采集回执不可读: duplicate JSON key rejected: 'collector'`；`test_24_csv_collector_receipt_is_strict_and_current_revocation_wins` PASS。

### R10 / W-04：迁移哈希证据等级

- 红态文案：管线文档称旧段“绑定迁移前整份 done 字节哈希”，未说明原件覆盖后的不可复验性。
- 修复/绿态：代码注释和管线文档均明确 `pre_migration_sha256` 为 `self-reported at migration time`，原件覆盖后事后不可独立复验；逻辑仍只验存在性和 64 位十六进制格式。

## 3. 验收结果

### 定向回归

- `python3 scripts/tests/test_done_v4_collector.py`：24/24 PASS（原 17 项 + 本轮 7 项）。
- `python3 scripts/tests/test_review_resume_integrity.py`：PASS，含 U2b staged first-capture 新用例。
- `python3 scripts/tests/docs_lint.py`：PASS，45 个默认范围文档无断链、粗体配对完整。
- `git diff --check`：PASS。
- `rg -n '"VERIFIED"|VERIFIED' scripts/`：零命中。
- `references/data-pipeline-evm-channels.md` 中 `evm-collector-run/v2` 与 `--collector-receipt` 两个契约 needle 均仍在，未改字符串。

### 全量 suite

命令：`python3 scripts/tests/run_all.py`

- 除下列两个工单预声明的 loopback 沙箱失败外，其余全部 PASS；其中 `docs_lint.py --all` PASS（58 个文档），`test_review_resume_integrity.py` PASS，`test_done_v4_collector.py` 24/24 PASS。
- `test_batch3_solana_vertical_slice.py`：`ThreadingHTTPServer(("127.0.0.1", 0), ...)` 在 `socket.bind` 报 `PermissionError: [Errno 1] Operation not permitted`。
- `test_batch3_evm_vertical_slice.py`：同一 loopback `socket.bind` 沙箱权限错误。
- 两项均未进入业务断言，符合工单指定的不计红例外；没有其他失败。

## 4. 未尽事项与工作树

- 产品/文档修复无未尽项；未提供任何自动残件清理入口。
- 未 commit、未 push。
- 最终差异应只包含白名单内 7 个既有文件与本报告；`blindreview_U2.md`、`workorder_U2b.md` 是开工前已存在的未跟踪输入，未修改。
