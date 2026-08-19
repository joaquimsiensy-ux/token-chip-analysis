# 工单 U2b：单元2 盲审消化轮（4 BREACH + 5 WEAK 修复 + 1 注）

> 基线 main=2e986c0（6.47.0）。盲审报告：本目录 blindreview_U2.md（4 BREACH/6 WEAK/2 NOTE/11 DEFENDED），先读 B-01～B-04 与 W-01/02/03/05/06/04 各节。
> 盲审攻击脚本可只读参考：session scratchpad（`attack_u2.py`/`attack2.py`/`baseline_check.py`/`scan_real_dirs.py`，路径见你启动目录同级的 scratchpad；找不到就按各修复项描述自行重构红态，不阻塞）。
> 你（codex）只施工不 commit；报告写到本目录 workorder_U2b_done.md。

## 0. 边界

- **白名单**：
  ```
  scripts/evm/fetch_hypersync_v2.py     scripts/evm/channels_preflight.py
  scripts/evm/staged_capture.sh
  references/maintenance-review-repair.md
  references/data-pipeline-evm-channels.md（CT-SEMANTIC-33/34 needle：evm-collector-run/v2、--collector-receipt 两字符串不得动）
  scripts/tests/test_done_v4_collector.py
  scripts/tests/test_review_resume_integrity.py
  maintenance/closure-20260817-threeunit/workorder_U2b_done.md
  ```
- 不 commit 不 push；不改版本号/CHANGELOG/SKILL.md。
- 先红后绿：每项先取红态实证（可复用盲审攻击构造）再修绿。
- 修完后 NES/APU 存量行为回归：test_done_v4_collector 17 用例与本轮新增用例全绿。

## 1. 修复项

### R1〔关 B-01〕preflight 收据 collector 标签去"验证"语义

- channels_preflight._v2_provenance 的 receipts 条目：`"VERIFIED"` 改 `"SELF_REPORTED"`（原生 v4 段），并新增 `collector_sha256` 字段透传该段 done 实际 collector 哈希；迁移段保持 `"UNKNOWN_LEGACY"`（该词无过度宣称）＋`collector_sha256: null`。语义：闸只做自报绑定核对，不给"已验证"二值标签；置信判定交上层。
- `rg -n '"VERIFIED"' scripts/` 检查该字符串消费面，有下游断言同步改。
- 红态：盲审 B-01 构造（迁移段删 legacy 键+填当前脚本公开哈希）修前得 "VERIFIED"，修后同一构造只能得 "SELF_REPORTED"（与真原生段同级，不再有可洗白的高信标签）。注意：该构造本身仍会被判别联合放行（自报绑定的声明边界），本项修的是**标签语义**不是判别闸——报告如实写这个边界。

### R2〔关 B-02〕维护纪律 protocol 逐条补登 + 断链固化测试

- references/maintenance-review-repair.md 的"登记被替换版本"条款（:172 附近）改为："被替换版本按其生前**签发过的每个 protocol 各补一条**（一版签发多 protocol＝多条目；漏一条＝该 protocol 存量在升级后全部误拦——NES 0816 169 份正版 receipt 误拦同族）"。
- test_done_v4_collector.py 新增断链固化测试：monkeypatch 当前脚本哈希（模拟升级），断言①存量原生 v4 done 被拒、②recovered identity 被拒——固化"升级必须按 protocol 补登"为可见硬边界，测试注释指向上述纪律条款。
- 本项不预登记未来哈希（当前哈希本就在 allowlist），修的是纪律文档+边界固化。

### R3〔关 B-03〕inventory 闸分类报错给人工出路

- validate_capture_inventory 对已知自有工件**分类报错**（全部仍拒，不放行、不提供自动清理——防洗白通道，报告写明取舍）：
  - `quarantine/` 目录 → 错误信息："存在 staged_capture 隔离区 quarantine/；人工检视其内容后整体移出采集根再继续"；
  - `*.recover` → "refresh 回滚保留件；确认同名 done 原件完好后手动移除"；
  - `.done.json.refresh-tmp.*` / `.*.refresh-bak.*`（按实际命名模式）→ "刷新中断残留临时件；确认后手动移除"；
  - 其他 → 保持"未识别残件"但补一句通用指引（逐一检视后移出采集根）。
- references/data-pipeline-evm-channels.md 补"遗留目录残件处置手册"小节：各残件语义、产生原因、处置法；并把现有"APU 0801 诊断目录须移出"一句并入该手册。
- 红态：quarantine/、.recover、.refresh-tmp 三类各构造一例，修前统一"未识别残件"无出路，修后各得分类指引；三类仍全拒（绿例=错误信息断言）。

### R4〔关 B-04〕staged_capture.sh 首采放行

- identity 检查改三态（与 C12 真空判定等深）：
  - `$OUTDIR` 不存在 → 放行（fetch 首跑自建）；
  - 目录存在且真空（忽略 `.DS_Store`，与 R5 一致）→ 放行；
  - `capture_identity.json` 存在且为普通文件 → 放行；
  - 其余（有遗留缺 identity）→ FATAL 指向 --recover-identity（保持现文案）。
- 红态：全新空目录修前 FATAL rc=2（盲审 B-04 已证死路），修后进入采集循环（可用假 URL 让后续采集步骤自然失败，只断言不再死于 identity 检查）；遗留缺 identity 目录仍 FATAL。
- test_review_resume_integrity.py 的 staged_capture 测试段补首采放行用例。

### R5〔关 W-01〕.DS_Store 唯一豁免三处等深

- `.DS_Store` 加入显式忽略清单（**仅此一名，不搞通配隐藏文件豁免**），三处等深：validate_capture_inventory（根目录与 run 内）、C12 真空判定（`not any(iterdir())` 处）、staged_capture.sh 真空判定（R4）。
- 红态：根目录与 run 内各放一个 .DS_Store，修前 recover/preflight 拒，修后放行；放其他隐藏文件（如 `.foo`）仍拒（豁免面窄性负例）。

### R6〔关 W-02〕REVOKED 压过当前脚本哈希

- fetch_hypersync_v2._allowed_script_hashes：先取全表 hash-wide REVOKED 集，若 `sha256_file(__file__)` ∈ REVOKED → 抛错"当前脚本版本已被吊销，禁止继续签发/校验"；否则并入。channels_preflight 镜像处（allowed_collector_hashes 构造 :241 附近与 CSV 线 :158 的 `_sha256_file(expected_script)` 并入处）同语义同步。
- 红态：monkeypatch 登记表塞入"当前脚本哈希 REVOKED"条目，修前照常放行（盲审 W-02），修后抛错。

### R7〔关 W-03〕recovered 身份透传到 preflight 收据

- _v2_provenance 输出的 identity 段（或 receipts 顶层）新增：`identity_schema`（v1/v2 实值）、`recovered`（bool）、`lineage`（v1 为 null，v2 为 "unknown"）。上层展示可如实区分恢复目录。
- 红态：recovered 目录跑 preflight，修前输出与原生完全同形（盲审 W-03），修后带 recovered=true/lineage=unknown。

### R8〔关 W-05〕symlink 根判定修死代码

- `root = Path(outdir).resolve()` 后的 `root.is_symlink()` 恒假：改为对**未 resolve 的原始路径**判 symlink（含逐级父链已有逻辑则只修根这一处），symlink 根拒。
- 红态：`ln -s 真目录 假根` 跑 recover/refresh，修前放行，修后拒。

### R9〔关 W-06〕CSV 回执读入接 strict

- channels_preflight.py:141 附近 CSV collector receipt 的裸 `json.loads` 换 `strict_json_loads`（重复键跨通道等深；U2 §2.15 传染修复的漏网点）。
- 红态：重复 `collector` 键的 CSV receipt 修前按后值放行，修后读入层拒。

### R10〔W-04 注〕pre_migration_sha256 证据等级改口（仅注释/文档）

- fetch_hypersync_v2 相应注释与 data-pipeline-evm-channels.md：`pre_migration_sha256` 定性为"迁移时点留痕（self-reported at migration time），原件被覆盖后**事后不可独立复验**"；判别联合仍验键存在+64 位十六进制格式，但不得称其为可验证闸。不改逻辑。

## 2. 维持与不动（报告确认知悉）

- N-01：工单 U2 §13 "consumer 替换 v4" 判断有误，施工保留 v3 是机器必需（盲审实测删 v3 后 invariant_scan 红）——维持现状，无需改动。
- W-03 附带的"recover 照 done 自证签发 token"维持（下游通道声明 token 兜底，盲审未列 BREACH）。
- 不提供残件自动清理命令（R3 取舍）。

## 3. 完成标准

1. R1-R10 各红态实证+修后绿（R10 仅文案核对）；
2. test_done_v4_collector 原 17 用例+本轮新增全绿；test_review_resume_integrity 全绿；
3. `python3 scripts/tests/run_all.py` 除两个 loopback 外全绿；
4. git diff 只含白名单；docs_lint 过（needle 完整）；
5. 报告 workorder_U2b_done.md：逐项改动摘要+红绿实证+未尽事项。
