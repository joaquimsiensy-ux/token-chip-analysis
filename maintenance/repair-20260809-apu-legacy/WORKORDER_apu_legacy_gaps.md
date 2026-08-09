# 修复工单：APU 案（ANOM-012）存量迁移三缺口（v6.39.0，Fable 直接施工）

来源：APU 案首次让真实 EVM 案走受控 reconciliation runner 全链（−2 会话，
anomalies.json ANOM-012 status=resolved_with_backlog），暴露三项 skill 级存量
缺口。基线 main=ce8a66a（6.38.0），施工分支 fix/apu-legacy-gaps-20260809。
测试载体：`scripts/tests/test_apu_legacy_gaps.py`（23 项，先红后绿，入 SUITE）。

---

## 工单一：replay_stats 不写覆盖截止块，verify_recon 必读断言 → 真实首跑必断

1. **不变量**：每个 replay 引擎产出的 replay_stats.json 必须声明重放覆盖截止块
   `max_block = preflight 声明 expected_to − 1`（采集覆盖语义，非最后事件块——
   尾部空块不缩小覆盖），且该值取自重验过的 preflight 产物而非引擎自报，供
   verify_recon 断言重放范围对齐对账目标块。
2. **同族清单**（`rg -l replay_stats scripts/`）：生产者 replay_duck / replay_pass1 /
   replay_stream（三者共用 `replay_provenance()` 收尾 → 单点注入一处修三处等深）；
   replay_pass2 只消费 mint_total_wei 不产 stats；消费者 verify_recon（6.34.0 起必读，
   d8bd3c5）；对表契约 golden_baseline.STATS_CONTRACT + test_engine_equivalence；
   fixture 手写 stats 的 test_sixlens_receipts:95 已自带 max_block 不受影响。
3. **三件套**：a 原反例=真实 duck 产物 max_block==expected_to−1（修前 None）✅；
   a2 消费连线=真实产物喂 verify_recon 修前死于"截止块不一致"、修后推进到"缺 RPC"✅；
   b 同族变体=pass1 等深 + stream 等深（吃工单二迁移后的 v2 目录真跑）+ 契约键入
   等价性对表 ✅；c 失败分支=篡改 max_block 被 verify_recon 拒绝 ✅。
4. **新建代码自审**：①max_block 来源=validate_preflight_artifact 重验产物（非自报）；
   ②preflight 缺失/篡改时 replay_provenance 抛 ChannelsPreflightError fail-closed（既有）；
   失败重放产物（rejected rows receipt）无 provenance 无 max_block → verify_recon
   天然拒绝，fail-closed 方向正确。
5. **归因**：修复中新引入——6.34.0 repair diff 给 verify_recon 加消费断言时未同步任何
   生产者（producer/consumer 断契约），fixture 手写 stats 掩盖 4 个版本（维护模板 7.5
   "手写 receipt 不得冒充端到端执行成功"的反面实证）；流程段整改=consumer 断言类
   修复必须带真实 producer 连线测试。

改动：channels_preflight.py（replay_provenance 注入）、golden_baseline.py（契约键）。

## 工单二：无 schema 太古 done.json 无官方迁移路径，channels preflight 对存量 BLOCK

1. **不变量**：每一代已存在过的采集产物格式都必须有官方迁移路径到现行 schema，
   迁移只能经采集器同源函数重验数据实物后重建绑定件（禁手拼）；无法重验的存量
   fail-closed 拒绝且不落任何字节。
2. **同族清单**（`rg -n "LEGACY_MANIFEST_SCHEMAS|refresh_manifests"`）：
   fetch_hypersync_v2 的 --refresh-manifests 唯一迁移入口（v2→v3 已支持，太古缺）；
   下游链路 make_channel_receipt --format v2 → _v2_provenance → preflight_channels
   全部复用迁移后产物，无第二实现；partial_run_ 前缀目录不匹配 run_* glob 天然排除。
3. **三件套**：a 原反例=太古五键 done 修前被"不支持迁移的旧 schema: None"拒、修后
   upgraded=1 且升 v3 重建边界+补建 capture_identity+幂等 already_v3，连线到
   receipt→preflight→replay_stream 真跑 gate_pass ✅；b 同族变体=缺 next_block 拒 ✅、
   显式 "schema": null 畸形件不走太古分支照旧拒（分支判定 `"schema" not in d`）；
   c 失败分支=越界 run 使两阶段迁移整体拒绝、好 run 的 done 字节不变、不补建
   identity ✅。实弹=真实 APU 存量 943,807 行副本全链通过。
4. **新建代码自审**：①query_schema 补写依据=inspect_run_files 实读硬验 parquet 列集
   与现行采集器 field_selection 一致（列集是查询形态的物理证据，非信任旧声明）；
   边界/文件指纹全部从数据实物重算；②任一 run 不可验→ValueError→全不写；
   ensure_outdir_identity 挪到 done 落盘后的顺序变更经自审：唯一性已在收集阶段验证、
   ensure 幂等、中途失败重跑自愈（done 已 v3 走 already_v3）。
5. **归因**：历史漏检——refresh_manifests 上线（6.31.0 族）时存量枚举只到 v2 schema，
   库外真实存量还有更老一代（视角③"旧数据怎么办"的枚举不全）；补清单=存量迁移类
   工具上线前须 ls 真实案目录枚举在野格式。

改动：fetch_hypersync_v2.py（_prehistoric_refresh_candidate + refresh 顺序）。

## 工单三：旧 −1 产物格式与现行校验器漂移（data_map 前缀 / cid vs id / anchor 无 receipt）

1. **不变量**：旧案目录进入现行 −2 管线前必须经唯一官方迁移命令机械规范化；
   迁移只做格式归一不改语义，哈希失配即拒（不洗白腐坏账本），执行证据类缺失
   （kernel receipt）只能重跑补产不可补票。
2. **同族清单**（`rg -ln "data_map|candidate_universe|anchor_plan" scripts/`）：
   data_map 哈希消费者=holder_distribution_scan.verify_data_map（裸 hex 比对）、
   entity_source_trace（只记录不比对）、handoff_manifest（READY 必备件登记）；
   candidate_universe 校验者=handoff_manifest（要求 id/address/reasons）；
   anchor receipt 消费者=time_spotcheck（--plan-receipt 默认同目录）。生产侧：
   candidate_universe 为 −1 现场产物（split-run.md §表），无固定脚本。
3. **三件套**：a 原反例=旧案化石目录（前缀 data_map+cid 条目+无 receipt anchor）
   修前 verify_data_map 拒、迁移命令不存在；修后剥前缀 31→0 型规范化+补 id 保留
   cid+NEEDS_RERUN 报告 exit 2，verify_data_map 消费通过、幂等重跑不重复改写 ✅；
   b 同族变体=条目既无 id 也无 cid 拒迁不改写 ✅、非哈希形态值不被误剥 ✅；
   c 失败分支=登记文件哈希失配拒迁 data_map 且字节不变 ✅。
4. **新建代码自审**：①剥前缀仅精确形态 `^sha256:<64hex>`，重验对在场登记文件算
   实哈希（missing 计数不阻断——旧案数据文件可能已清理，verify_data_map 消费时
   仍有兜底）；②失配/孤儿条目/JSON 错误全部拒绝对应文件迁移，备份先行+原子写，
   备份撞名拒绝覆盖。
5. **归因**：历史漏检——三处漂移都是现行校验器各自升级时旧案产物无人回看
   （anchor receipt 6.35.0 kernel 化、data_map 裸哈希与 cid→id 契约为 −1/−2 文档
   演进），同属视角③存量迁移盲区；与工单二共用同一条补清单。

改动：新增 scripts/report/migrate_legacy_case.py（atomic_write_with_backup 已登记
invariant manifest atomic_writes）。

---

## 收口

- 文档双向同步：data-pipeline-evm-channels §存量迁移段（太古形态）、split-run §3.1
  步 2（migrate_legacy_case 指引）。
- 版本：VERSION/pyproject/SKILL 三处 6.39.0；CHANGELOG 索引+详情。
- 守卫：invariant_scan PASS（atomic_writes 43）、docs_lint --all PASS、
  changelog_lint PASS、test_contract_routes PASS。
- 全量 suite：见 run_all_final.txt。
