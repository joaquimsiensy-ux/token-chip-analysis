# 工单 U2：HyperSync Parquet done v3→v4 逐段采集者归属 + C12 显式恢复

> 三单元收口工程第 2 单元。基线 `main=837baa8`（6.46.1，单元1 及其盲审消化已收口），动工前 `git rev-parse HEAD` 核对，不一致即停工留报告。
> 本工单全部行号已由调度方在 837baa8 上亲核（fetch_hypersync_v2 与 preflight/manifest/tests 四批实测）；若你复核发现某行号与描述不符，按"不一致即停工"纪律停工留报告，勿自行猜测施工。
> 你（codex）只施工不 commit；完成后写施工报告到本目录 `workorder_U2_done.md`。

## 0. 边界（违规即返工）

- **白名单（只允许改/建这些文件，超出即违规）**：
  ```
  scripts/evm/fetch_hypersync_v2.py     scripts/evm/collector_history.py
  scripts/evm/channels_preflight.py     scripts/evm/staged_capture.sh
  scripts/tests/invariant_manifest.json
  scripts/tests/test_done_v4_collector.py（新建）
  scripts/tests/test_v2_identity_history.py
  scripts/tests/test_collector_history.py
  scripts/tests/test_review_resume_integrity.py   scripts/tests/test_apu_legacy_gaps.py
  scripts/tests/test_repair_batch_d.py            scripts/tests/test_review_20260804_p0.py
  scripts/tests/test_review_20260804_p101.py      scripts/tests/test_engine_equivalence.py
  scripts/tests/run_all.py（仅加注册行）
  references/data-pipeline-evm-channels.md（不得动 CT-SEMANTIC-33/34 needle：`evm-collector-run/v2`、`--collector-receipt` 两个字符串）
  maintenance/closure-20260817-threeunit/workorder_U2_done.md（施工报告）
  ```
- 不 commit、不 push；不改版本号/CHANGELOG/SKILL.md。
- 先红后绿，红实证入报告。

## 1. 背景（一句话）

Parquet 通道每段 done.json 不记采集脚本指纹（升级续采/删身份重建都能"改姓"），identity 缺失时自动补签是洗归属窗口——本单元 done 升 v4 逐段带 collector、identity 只在真空目录自动建、其余走显式恢复。

## 2. 施工内容（行号基于 837baa8，调度方已亲核）

1. **schema 升 v4**：fetch_hypersync_v2.py:43 `MANIFEST_SCHEMA = "hypersync-v2-done/v4"`；:44 `LEGACY_MANIFEST_SCHEMAS` 加入 `"hypersync-v2-done/v3"`（连同现有 v2）。
2. **每段 done 写 collector**：done dict（:542-548）加 `"collector": {"path": "scripts/evm/fetch_hypersync_v2.py", "sha256": <启动冻结哈希>}`。
3. **TOCTOU 防漂移**：main() 启动时算 `collector_start_hash` 冻结；每次写 done 前重算，不等即 fail-closed 拒写。文档注明这是自报绑定，不宣称防蓄意伪造。
4. **旧段迁移（--refresh-manifests 路径 :461 附近）**：v2/v3/pre-schema done 升 v4 时写 `"collector": null` + `"collector_provenance": "legacy-unattributed"` + 迁移记录 `{migrated_from_schema, pre_migration_sha256, migrator: {path, sha256}}`。键名说明：现行太古迁移已有 `refreshed_from_schema` 前例（test_apu_legacy_gaps:208 断言）——源 schema 键沿用 `refreshed_from_schema` 以保一致性亦可，报告说明选择即可；语义三件套（源 schema／迁移前整份 done 的哈希／迁移器身份）缺一不可。
   - pre_migration_sha256 必须来自实际被解析的那份原始字节（读一次字节流同时算哈希+解析），commit 前复验原文件未变（现行 :254 读取与 :384 staging 重算之间有窗口，消掉）。
   - **pre-schema 多段 capture_from**：现行 _prehistoric_refresh_candidate（:297-326）把每段 capture_from 设为本段 from_block；同目录多个连续 pre-schema run 无法唯一推导同源 capture 时**拒绝并要求显式 `--capture-from`，不猜**（单段目录不受影响）。
5. **判别联合（validate_done_manifest 硬闸）**：原生 v4 ⇒ collector 非 null 且禁止 collector_provenance/迁移记录键；迁移 v4 ⇒ collector==null ∧ provenance=="legacy-unattributed" ∧ 迁移记录齐全。两态互换即拒。下游展示 UNKNOWN_LEGACY，不得渲染成已验证。
6. **allowlist 按 protocol 过滤**：collector_history.py:110 `historical_script_hashes(name, protocol=None)`——语义=「ACTIVE ∧ script==name ∧ protocol==指定值，减全表 REVOKED 同哈希（hash-wide，跨 protocol 不缩窄）」。所有调用点显式传 protocol：
   - done v4 段级新线 protocol="hypersync-v2-done/v4"（首版历史集为空）；
   - identity 线 protocol="hypersync-capture-identity/v1"：fetch_hypersync_v2.py:191-192 ＋ channels_preflight.py:223-224（镜像处）；
   - CSV 线 channels_preflight.py:154 显式 protocol="evm-collector-run/v2"。
7. **维护纪律（同单元原子）**：被替换的 fetch_hypersync_v2.py 现版本哈希 `f544a1968dfa86e1705b2c028b33ad591e869b4194e257313b58519bb12c6d11` 补登 collector_history（protocol="hypersync-capture-identity/v1"，commit=`0ec6d1e2365c339d200fc26d17344f962fbdb7a9`——调度方已考证该文件最后变更即此 commit；登记表 commit 一律 40 位全哈希，U1b R8 教训）。
8. **migrator/recoverer 身份可验**：migrator.sha256 / recoverer.sha256 必须 ∈ {当前脚本} ∪ protocol 过滤后历史 ACTIVE。
9. **C12 收严 + --recover-identity**：
   - ensure_outdir_identity 迁移放行段（:207-220）收严：自动创建仅限**真空目录**（`not any(root.iterdir())`——任何条目含隐藏文件/残段都算遗留）；有遗留即 fail-closed 报错指向 --recover-identity；:186-188 与 :207-209 注释撤换（channels_preflight.py:217-219 镜像注释同步撤换）。
   - 新 CLI `--recover-identity`：只读重验目录内所有 run（url/token/query_schema 同一性、done 可解析、inventory 精确核对：每个 run_* 恰有普通文件 done.json/logs.parquet/blocks.parquet 三件套，拒 symlink/孤儿 done/孤儿 parquet/空 run/未识别残件——channels_preflight.py:240-244 已有 run↔done 集合闭合逻辑，抽成共享函数复用勿复制），通过后签发 recovered identity；不动 done。
   - **recovered identity 用 `hypersync-capture-identity/v2`** schema：含 recovered=true、lineage="unknown"（固定值）、recovery_time、recoverer{path,sha256}。消费者接受集合={原生 v1} ∪ {recovered v2 ∧ lineage=unknown}，两态判别互斥：**v1 件有 collector 无 recovered 族键；v2 件有 recoverer 无 collector 键**（recoverer 取代 collector，勿两键并存）。
   - **recovered v2 的 query_schema 定案（太古目录三态闭合）**：字段值一律记**现行 QUERY_SCHEMA**（其唯一后续用途=与 refresh 升级后的 done 对账，记 null 会在 refresh 后永久失配）。recover 同一性验证：token/url 硬性一致；done 的 query_schema 键=带键者彼此一致且==现行 QUERY_SCHEMA，缺键（太古）者跳过该项；带键者一致但≠现行值 ⇒ 拒签并在报告说明（未知采集时代，留人工裁决）。
   - **顺序**：缺 identity 的旧目录先 --recover-identity 再 --refresh-manifests；refresh 不再自动补建 identity（:458-461 的自动 ensure 改为仅校验已存在 identity，缺失即报错指向 recover）。
10. **消费侧**：validate_done_manifest 验 v4 形态+判别联合；channels_preflight._v2_provenance 验段 collector ∈ 当前 ∪ protocol="hypersync-v2-done/v4" 历史；legacy 策略=迁移器可读 v2/v3/pre-schema，resume/verify-done/preflight 对未迁移 legacy 拒（现行对 v2 已如此，v3 入 legacy 同规则）。
11. **staged_capture.sh 假成功收口**：skip 循环前加根 identity 存在性检查（缺失即 FATAL 指向 --recover-identity）；test_review_resume_integrity.py 的 staged_capture 测试段（:155-160）扩展。
12. **存量数据目录一律不动**（QUQ/APU/NES 等在下次使用时走 recover→refresh；文档写明）。
13. **invariant_manifest.json**：:50 producer 与 :316 consumer 的 `hypersync-v2-done/v3` 都**替换**为 v4（preflight 拒未迁移 legacy，不存在"继续消费 v3"的 consumer——与 U1 的 consumer 保留规则不同，勿套用）。
14. **现有测试修正**（断言的是被本单元变更的行为）：test_review_resume_integrity.py:175（迁移后 schema 断言 v3→v4）/:177（refresh 自动补 identity → 改为先 recover 再 refresh 的两步断言）；test_apu_legacy_gaps.py:203-208（太古迁移后 v3→v4+legacy-unattributed）；test_repair_batch_d.py:70 附近同族断言；test_review_20260804_p0/p101、test_engine_equivalence 中 v3 fixture 逐条检查（构造 legacy 验兼容的保留，断言现产 schema 的改 v4），报告逐条说明。

15. **U1 盲审跨单元传染修复（三条，随本单元一并落地）**：
   - **重复 JSON 键闸（V-31 同构，必做）**：done v4 判别联合是"键存在性"判定——重复键攻击可让同一 done.json 里 `"collector": null`（给人看）与 `"collector": {...}`（json.loads 取后值）并存，人机读取分裂。done.json 与 capture_identity.json 的**全部读入点**（fetch_hypersync_v2 的 validate/resume/refresh/verify 路径＋channels_preflight 镜像处）改用 `scripts/lib/anchor_point_contract.strict_json_loads`（已有共享件，**引用勿复制**；跨目录 import 按仓库 sys.path 惯例）。范围仅 done+identity 两族文件，勿全库扩散。红态：构造重复 `collector` 键的 done 修前被接受、修后读入层拒。
   - **分派禁 fail-open else（V-17/V-18 教训）**：done schema 分派必须显式枚举（v4 / LEGACY_MANIFEST_SCHEMAS / pre-schema 判别），不认识的 schema 值一律 ValueError，禁止落入任何默认分支。
   - **枚举判定前收类型（V-23 教训）**：collector_provenance、schema 等枚举成员判定前先 `isinstance(x, str)`，统一 ValueError 错误面。

## 3. 测试矩阵（新文件 scripts/tests/test_done_v4_collector.py，注册 run_all.py）

照施工计划 §4.3 的 14 条：新采带 collector／TOCTOU 篡改拒／v3→v4 迁移正例／太古迁移（QUQ run_0 键集 elapsed_s,from_block,next_block,token,url）／判别联合负例×3／protocol 伪造入口负测（identity/v1 历史哈希不得进 done v4 allowlist）／C12 真空与遗留两态／recover 正负例／legacy 可读性分层／protocol 过滤+REVOKED 跨界否决／先 recover 后 refresh 顺序（refresh 缺 identity 拒）／migrator 未登记拒／多段 pre-schema 无 --capture-from 拒／staged_capture identity 缺失 FATAL。
另加 §2.15 三条：重复 collector 键的 done 拒／未知 done schema 拒（不落默认分支）／collector_provenance=list 型 ValueError。

## 4. 地雷区

1. channels_preflight._v2_provenance（:201-244）是 fetch_hypersync_v2 判定逻辑的逐字镜像（含注释）——两处必须同步改。
2. data-pipeline-evm-channels.md 的 CT needle 两字符串不得动（docs_lint 兜底）。
3. REVOKED 否决保持 hash-wide。
4. refresh/recover 顺序装反=缺 identity 旧目录卡死。
5. 你的沙箱跑不了两个 loopback 测试（test_batch3_*_vertical_slice），跳过不算失败。

## 5. 完成标准

run_all 除 loopback 外全绿；新测试 14 用例全绿+负测红实证；`rg -n "hypersync-v2-done/v3"` 残留逐条归属说明；git diff 只含白名单；施工报告含改动摘要/红实证/f544a196 git 考证/APU 临时目录迁移演练命令（供调度方验收）/未尽事项。
