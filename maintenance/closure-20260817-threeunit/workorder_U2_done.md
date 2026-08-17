# 工单 U2 施工报告：HyperSync Parquet done v3→v4 逐段采集者归属 + C12 显式恢复

## 1. 基线与边界

- 动工前 `git rev-parse HEAD`：`837baa88cb3de281eb81a899aacba877ce88b391`，短 SHA 为工单要求的 `837baa8`。
- `VERSION`/`CHANGELOG.md`/`SKILL.md` 未改；未 commit、未 push。
- 动工前工作树只有调度方提供的未跟踪文件
  `maintenance/closure-20260817-threeunit/workorder_U2.md`；施工未修改该文件。
- 最终代码、测试、文档和本报告均在工单 §0 白名单内；`git diff --check` 通过。

## 2. 改动摘要

1. `fetch_hypersync_v2.py`
   - 现产 done 升为 `hypersync-v2-done/v4`，v2/v3 均进入 legacy 集合。
   - 原生 v4 每段写 `collector={path:scripts/evm/fetch_hypersync_v2.py,sha256:<启动冻结哈希>}`；写 done 前复验脚本哈希，漂移即拒写。这是防误漂移的自报绑定，不宣称抵抗能同时伪造脚本与收据的攻击者。
   - v2/v3/pre-schema refresh 生成 `collector=null`、`collector_provenance=legacy-unattributed`，并写 `refreshed_from_schema`、从实际解析字节计算的 `pre_migration_sha256`、可验 `migrator`。commit 每个 done 前复验原件哈希和 migrator 启动哈希。
   - `validate_done_manifest` 显式枚举 v4/legacy/pre-schema/未知 schema；只消费 v4，并硬验原生/迁移两态判别联合、枚举类型和 actor protocol allowlist。
   - 多段 pre-schema 未给 `--capture-from` 一律拒绝，不猜共同采集起点。
   - C12 自动签发只允许 `not any(root.iterdir())` 的真空目录；任何隐藏件、残段或其他遗留均指向 `--recover-identity`。
   - 新增显式 `--recover-identity`：共享精确 inventory 闸要求每个 `run_*` 恰有普通文件 done/logs/blocks 三件套，拒 symlink、孤儿、空 run 和未识别残件；逐 run 重验 token/url/query、完整边界和 Parquet 后签发 `hypersync-capture-identity/v2`，固定 `recovered=true`、`lineage=unknown`、现行 `query_schema`，以 `recoverer` 取代 `collector`，不改 done。
   - done 与 identity 全部读入点改用 `scripts/lib/anchor_point_contract.strict_json_loads`，重复键在解析层拒绝。
2. `channels_preflight.py`
   - `_v2_provenance` 与 fetch 侧 identity v1/v2 判定、注释和 protocol allowlist 同步；复用共享 inventory；done/identity 使用 strict JSON。
   - 每段 v4 collector 走 `hypersync-v2-done/v4` 历史集；迁移段只显示 `UNKNOWN_LEGACY`。
   - CSV 历史集显式绑定 `evm-collector-run/v2`。
3. `collector_history.py`
   - `historical_script_hashes(name, protocol=None)` 支持 protocol 精确过滤；REVOKED 仍从全表按 hash-wide 跨 protocol 否决。
   - 补登被替换版本 `f544a196…` 为 `hypersync-capture-identity/v1` ACTIVE。
4. `staged_capture.sh`
   - skip 循环前检查普通文件 `capture_identity.json`；缺失即 FATAL 并指向 `--recover-identity`。
5. 文档、invariant、既有 fixtures
   - 文档改为 recover→refresh、done/v4 两态和存量目录不自动改写；现产 fixture 改 v4+collector，legacy fixture 保留 v2/v3。
   - invariant producer/consumer 登记 identity/v2 与 done/v4；`run_all.py` 只新增 U2 测试注册行。

## 3. 先红后绿实证

### 3.1 修前红态

命令：

```bash
python3 scripts/tests/test_done_v4_collector.py
```

在未改生产代码、只新增测试后，退出码为 1，汇总为：

```text
FAIL: test_01_new_capture_writes_segment_collector
FAIL: test_02_toctou_script_drift_rejects_done_write
FAIL: test_03_v3_to_v4_migration_is_unattributed: recover_identity 不存在
FAIL: test_04_prehistoric_quq_shape_migrates: recover_identity 不存在
FAIL: test_05_done_v4_discriminated_union_rejects_hybrids: expected ValueError
FAIL: test_06_identity_protocol_hash_cannot_spoof_done_v4: protocol 参数不存在
FAIL: test_07_c12_only_vacuum_auto_signs: expected ValueError
FAIL: test_08_recover_identity_positive_and_inventory_negative: recover_identity 不存在
FAIL: test_09_legacy_readability_is_refresh_only: expected ValueError
FAIL: test_10_protocol_filter_and_hash_wide_revocation: protocol 参数不存在
FAIL: test_11_recover_then_refresh_order_is_mandatory: expected ValueError
FAIL: test_12_unregistered_migrator_rejected: recover_identity 不存在
FAIL: test_13_multirun_prehistoric_requires_capture_from: recover_identity 不存在
FAIL: test_14_staged_capture_missing_identity_is_fatal
FAIL: test_15_duplicate_done_collector_key_rejected: expected ValueError
PASS: test_16_unknown_done_schema_rejected
FAIL: test_17_collector_provenance_type_rejected: expected ValueError
FAIL: U2 done/v4 collector + C12 recovery (16/17)
```

这组红态分别证实旧代码没有逐段 collector/TOCTOU 闸、没有显式恢复、会自动给遗留目录补签、没有 protocol 隔离、没有判别联合与重复键闸。未知 schema 一项旧代码虽拒绝，但原因是现行 identity mismatch；修后由显式 schema 分派拒绝。

### 3.2 修后绿态

```text
PASS: U2 done/v4 collector + C12 recovery (17/17)
PASS: R-3 v2 historical identity maintenance/consumer parity
PASS: APU 存量缺口工单契约测试全绿
PASS: P0-01 collector provenance + P0-02 reproduce freshness regressions
PASS: P1-01 immutable HyperSync outdir identity and legal capture coexistence
PASS: 三引擎 gate/退出码 10 例 hypothesis 全等
BATCH D 全部通过
PASS invariant manifest: receipt_producers=63, receipt_consumers=91, transport_calls=63, atomic_writes=54, formal_entrypoints=58, exceptions=0
PASS: 58 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

全量命令：

```bash
MPLCONFIGDIR=/private/tmp/u2-mpl python3 scripts/tests/run_all.py
```

结果：除工单 §4.5 预先声明的两项 loopback 外全部 PASS；新增 U2 测试在全量入口中为 17/17。

- `test_batch3_solana_vertical_slice.py`：`ThreadingHTTPServer(("127.0.0.1", 0), ...)` 在 `socket.bind` 返回 `PermissionError: [Errno 1] Operation not permitted`。
- `test_batch3_evm_vertical_slice.py`：同一 loopback `socket.bind` 限制。

两项均在业务断言前被沙箱能力阻断，不计作 U2 红态；未出现其他失败。

## 4. `f544a196…` 登记与 git 考证

登记内容：

```text
script   = fetch_hypersync_v2.py
sha256   = f544a1968dfa86e1705b2c028b33ad591e869b4194e257313b58519bb12c6d11
commit   = 0ec6d1e2365c339d200fc26d17344f962fbdb7a9
protocol = hypersync-capture-identity/v1
status   = ACTIVE
```

考证命令与结果：

```bash
git log -1 --format='%H %s' -- scripts/evm/fetch_hypersync_v2.py
# 0ec6d1e2365c339d200fc26d17344f962fbdb7a9 批E盲审消化轮…

git show 0ec6d1e2365c339d200fc26d17344f962fbdb7a9:scripts/evm/fetch_hypersync_v2.py | shasum -a 256
# f544a1968dfa86e1705b2c028b33ad591e869b4194e257313b58519bb12c6d11  -
```

`test_collector_history.py` 的全登记表 git 可复算守卫通过。

## 5. APU 临时目录迁移演练命令

以下命令只操作 `/private/tmp` 副本，不触碰 APU 存量目录。调度方把前两项替换为实际冻结值；多段 pre-schema 必须给冻结下界，单段也可显式给以便验收口径统一。

```bash
APU_V2_SOURCE='/绝对路径/APU/data/v2'
APU_FROZEN_CAPTURE_FROM='冻结采集下界整数'
APU_U2_TMP="$(mktemp -d /private/tmp/apu-u2-v4.XXXXXX)"

ditto "$APU_V2_SOURCE" "$APU_U2_TMP/pristine"
ditto "$APU_V2_SOURCE" "$APU_U2_TMP/v2"

python3 scripts/evm/fetch_hypersync_v2.py \
  --recover-identity --outdir "$APU_U2_TMP/v2"
python3 scripts/evm/fetch_hypersync_v2.py \
  --refresh-manifests --outdir "$APU_U2_TMP/v2" \
  --capture-from "$APU_FROZEN_CAPTURE_FROM"

rg -n '"schema"|"collector"|"collector_provenance"|"pre_migration_sha256"|"migrator"' \
  "$APU_U2_TMP/v2"/run_*/done.json
diff -qr "$APU_V2_SOURCE" "$APU_U2_TMP/pristine"
```

最后一条应无输出，证明演练期间源目录与动工前副本一致。临时目录保留给调度方复核，不在本工单删除。

## 6. `hypersync-v2-done/v3` 残留归属

现役 `rg -n "hypersync-v2-done/v3"` 残留均有明确归属：

- `scripts/evm/fetch_hypersync_v2.py`：仅 legacy allowlist 与 v3 legacy `files` 重验分支，必须保留以支持 refresh/recover；不是现产 schema。
- `scripts/tests/invariant_manifest.json`：fetch 的 legacy consumer 登记；producer 已替换为 v4。
- `scripts/tests/test_done_v4_collector.py`：v3→v4 迁移、legacy 分层和攻击 fixture；不是现产断言。
- `maintenance/repair-20260813-sixlens/input_codex_review.md` 与 `maintenance/repair-20260815-g2/*.log`：历史审计/日志原文，白名单外且不可改。
- 工单原文中的 v3 字样是调度要求本身，未修改。

## 7. 契约 needle 与未尽事项

- `references/data-pipeline-evm-channels.md` 仍含原字面 `evm-collector-run/v2`（首个命中第 41 行）与 `--collector-receipt`（首个命中第 61 行）；`docs_lint.py --all` 通过。
- 存量 QUQ/APU/NES 等真实数据目录未改；下次使用必须在副本演练通过后按 recover→refresh 执行。
- 唯一未在本沙箱执行的业务测试是上述两个 loopback 纵切片；需在允许绑定 `127.0.0.1` 的环境原命令复跑。除此之外无未尽代码项。
- 本工单不 commit、不 push，版本号与发布记录留给调度方统一收口。
