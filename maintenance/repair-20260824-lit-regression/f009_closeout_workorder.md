# 工单 批3收口：v6.52.2 登记面（版本/CHANGELOG/SUITE/文档/契约）（fresh 会话可独立执行）

一句话目标：F-007/F-008 两批代码已入库后，收齐 v6.52.2 全部登记面并跑全量 run_all。

## 【开工门禁】（不符即写停工报告并停）
- 仓库：/Users/uravvv/.claude/skills/token-chip-analysis
- `git branch --show-current` = `fix/lit-regression-v6522`
- `git log --oneline -5` 能看到 F-007 与 F-008 两批 commit
- `git status --short` 除 maintenance/repair-20260824-lit-regression/ 下文件外干净

## 施工清单（逐项做完在 done 里贴证据）

### 1. 版本三件＋CHANGELOG
- `VERSION` → `6.52.2`
- `pyproject.toml` `[project].version` → `6.52.2`
- `SKILL.md` 版本注释行 `<!-- skill-version-source: VERSION; skill-version: ... -->` → 6.52.2（**只改注释行等长替换，正文零改动**；改后 `wc -c SKILL.md` 必须 ≤8192，当前 7961B）
- `CHANGELOG.md`：索引行 `- **6.52.2**（2026-08-24）一句话` ＋ 详情节 `## [6.52.2] - 2026-08-24 — 标题`；内容涵盖 F-007/F-008 两 finding、SUITE 129→131、契约 195→197（若契约实设数不同，按实数写）；末尾带成本/质量指标行（参照 F-005 条目风格）
- 验证：`python3 scripts/tests/changelog_lint.py` PASS；`python3 scripts/tests/test_version_consistency.py` PASS

### 2. SUITE 登记
- `scripts/tests/run_all.py` 末尾新增块：
  `SUITE += ["test_lit_regression_f007.py", "test_lit_regression_f008.py"]  # v6.52.2 repair-20260824-lit-regression`
- 验证：SUITE 计数 129→131（AST 或人工数）；两个新测试文件确实被 runner 执行

### 3. references 文档同步（改后 `python3 scripts/tests/docs_lint.py --all` PASS）
- `references/scan-schemas.md` §13 三处（约 :590 末点对账⑤散户恒等式、:594 单式严判、:598 burn 口径定案）：旧"净分母族只认非 burn 之和/两族不得互救"一刀切表述改为 **series_format 分家**表述（evm-dict：「锁仓/销毁」参与堆叠与散户残差、不分口径、burn_cum_pct 豁免且 legacy 序列不得含它；sol-rows：「锁仓/销毁」为分母外披露桶不参与——每处带生产端代码行号依据 replay_pass2.py:84-116 / replay_edges.py:648,657）
- `references/scan-schemas.md` §4（约 :242）：`source.argument` 语义注明 "sol/duckdb=文件；evm_v2=目录（run_*/logs.parquet 与 run_*/blocks.parquet 的父目录）"；（约 :342）消费面同源句补：evm_v2 重放前有字符闸＋目录集合闸（当前命中集合必须与 source.files 精确相等）
- `references/report-template.md:203`：改为"formal 按 series_format 精确堆叠闭合；无 format 的手填路径才 dual"
- `references/split-run.md` §2.2 核对，如有旧表述同步
- 全库 rg 残留清点：旧一刀切表述在 references/ 与 scripts/ 注释中清零（archive/ 与 maintenance/ 历史档案除外——历史记录不改写），逐条归类进 done

### 4. 契约（目标 195→197；needle 三判据：修前 authority_file 精确命中、修后清零、新表述不含该字面）
- CT-BANNED-23（authority_file=references/scan-schemas.md）：needle 取 §13 旧全局句式的精确字面（你从修前原文里选，须避开 Solana 合法表述与 CHANGELOG/档案）
- CT-REQUIRED 新条（ID 按所在族惯例编号，authority_file=references/scan-schemas.md）：needle 取 §4 新句稳定片段（如"当前命中集合必须与 source.files 精确相等"）
- 同步 `scripts/tests/contract_manifest.json`（五字段严格）与 `scripts/tests/contract_ids_snapshot.json`（排序位置插入）
- 验证：`python3 scripts/tests/test_contract_routes.py` PASS；`python3 scripts/tests/docs_lint.py --all` PASS
- 若任一 needle 无法同时满足三判据：允许弃设该条，但必须把 CHANGELOG/done 中的 197 改为实数并说明——不得一边弃设一边硬写 197

### 5. 其余登记核对（在 done 显式声明结论）
- `scripts/tests/invariant_manifest.json`：核对本工程新增（safe_case_dir/常量/校验逻辑）不触发任何计数变化；如触发，按 invariant_scan 指引补登记
- `producer_history` / `collector_history`：不加条目（生产端产物字节零变化），写明判断依据
- `git diff --check` rc=0；自产文档零 EOF 空行/行尾空格

### 6. 全量测试
- `python3 scripts/tests/run_all.py` 全量跑：预期 131 项；**沙箱内 2 项 loopback 测试（test_batch3_solana_vertical_slice / test_batch3_evm_vertical_slice）如因 bind 权限失败，如实报 129/131＋原始 traceback，不伪报、不改测试**（本机复跑由裁判承担）

## 收尾
- done 报告 `f009_closeout_done.md`：逐项证据（命令＋原始输出＋EXIT_CODE）、SUITE/契约/docs_lint 实数、残留清点、发现项
- 本批同样不 commit（Fable 代 commit）、不联网

## 边界
- **禁改**：wave_scan.py、entity_source_trace.py、sqd_cache_identity.py、replay_pass2.py、replay_duck.py、replay_edges.py；F-007/F-008 已入库的代码文件本批不再动（发现问题只记录，交调度裁决）
- 白名单=本工单第 1-4 节点名的文件＋本工程档案目录
