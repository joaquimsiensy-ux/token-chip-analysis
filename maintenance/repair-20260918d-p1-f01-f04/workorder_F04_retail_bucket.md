# 工单 F04（v1）：EVM camps spec 显式「散户」桶在共享校验层硬拒 —— repair-20260918d-p1-f01-f04 第一段

> 出处：codex 对 9.0.0（868d3f61）六视角 review F04（P1，A2/B2；历史漏审 0fe2d601/ff477632）：`scripts/lib/camp_spec.py:59-61` 只验阵营名非空、成员互斥，不拒保留桶；`scripts/evm/replay_pass2.py:102-106`（`snap()` 先对 `stack` 每桶 append 一次，`:106` 再对 `series["散户"]` append 残差）与 `scripts/evm/replay_duck.py:555-560` 同构——spec 显式配置「散户」时，「散户」既在 `stack` 里被 append 一次、又作残差被 append 一次，同一天两个元素，两引擎 rc=0 产出坏形状序列；`camp_series_provenance.py:426` 的长度检查才拦（报错过晚、白跑一遍重放）。反例：mint 100→A、A→B 40，`camps={大庄:[A],散户:[B]}` → 两引擎 rc=0、dates 长度 1、「散户」=[40,0]。用户 09-18 裁决：修。总原则：skill 上下文不增；能删不增、能改不增；references/SKILL/commands 本段零改动。
> 修法：在四入口共享的 `validate_camp_spec` 里，`chain_family == "evm"` 且阵营名恰为「散户」→ `_fail`（exit 2，与既有互斥拒同通道）。不改两引擎的 append 结构（台账 Q6）；Solana 不拒（台账 Q5：`build_evolution.py:173` 以「散户」为默认桶、`:181` 标量加残差无重复；LAYOFF 案 `entity_camps.json` 27 处显式「散户」为存量）。
> 内容基线：`868d3f61`（v9.0.0）加本工程已入库 commit；本段先于 F01 施工，行号按 868d3f61 核。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `F04_done.md`：`git status --short`（须为空）；`git diff --stat 868d3f61 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（须为空）。不空即停工写 `F04_done_attempt<N>_stopped.md`。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、本目录以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。**豁免**：§0.8 指定的测试自身按既有代码以子进程或文件读取方式访问历史 maintenance 目录（如 `test_repair_batch_c.py`/`test_exemption_guards.py`）属测试依赖，**允许原样运行**、不算违反本条；施工方本人不得主动打开、阅读、复制或修改那些历史文件，完成报告如实披露"仅由测试子进程访问"即可。
- 0.3 **白名单**：生产 `scripts/lib/camp_spec.py`；测试 `scripts/tests/test_repair_batch_c.py`；本目录新建 `F04_done.md`、`F04_red_evidence.txt`，停工时 `F04_done_attempt<N>_stopped.md`（N＝派工提示词给的尝试序号）。
- 0.4 **不改**：`scripts/evm/replay_pass2.py`、`scripts/evm/replay_duck.py`、`scripts/solana/replay_edges.py`、`scripts/solana/build_evolution.py`（四入口调用点不动，`validate_camp_spec` 签名不动）；`camp_spec.py` 的 `_normalize`/`load_addr_camp_json`/互斥查重逻辑；`camp_series_provenance.py`；任何 `references/`、`SKILL.md`、`commands-staging/`、`VERSION`、`pyproject.toml`、`CHANGELOG.md`、`contract_manifest.json`、`invariant_manifest.json`（开工用 `python3 -B scripts/tests/invariant_scan.py` 证实无需登记）。
- 0.5 行号均指施工前基线（868d3f61）；锚 `grep -n -F` 恰 1 处且行号一致，不符**停工**。删除 > 修改 > 新增。
- 0.6 离线；不 commit、不 push、不部署；禁 stash/checkout/reset。
- 0.7 先红后绿：§2.3 四个新 check 在改生产代码前**逐表达式独立执行**取 RED 写 `F04_red_evidence.txt`（`check()`（`:54-57`）是 raise 型，不能靠跑整测试取证；用 `python3 -c` 或临时脚本分别求值四个条件表达式并记录 True/False 与 stderr 尾行；临时脚本不得留在仓库）。
- 0.8 不跑 `run_all.py`、不跑 `test_stage2_reseal.py`。定向跑（全部须 PASS）：`python3 -B scripts/tests/test_repair_batch_c.py`、`test_repair_batch_d.py`、`test_engine_equivalence.py`、`test_fault_injection.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`python3 -B scripts/tests/invariant_scan.py`。冷字体缓存环境项：遇 `data_broken: '_items'` 时保留首次输出写 done，再 `MPLCONFIGDIR="$HOME/.matplotlib" python3 -B …` 重跑，重跑必须真实 PASS。

## 1. 硬约束

- 1.1 文档三处字节不变：`SKILL.md` 8021、`references/**/*.md` 合计 930076、`commands-staging/*.md` 合计 8798。只用元数据：`stat -f %z SKILL.md`；`find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'`；`stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'`。
- 1.2 `git diff --stat` 只含 0.3 白名单。
- 1.3 `validate_camp_spec` 签名、返回形状（规范化同形 dict、保序）不变；新增拒收走既有 `_fail`（stderr 前缀 `[camp-spec] `、exit 2）。
- 1.4 Solana 语义不变：`validate_camp_spec({"散户": [SA]}, chain_family="solana")` 仍返回 `{"散户": [SA]}`；`load_addr_camp_json` 对值为「散户」的地址仍接受。
- 1.5 既有 EVM 合法 spec（`test_repair_batch_c.py:252` `ok_spec` 等）行为逐字节不变。

## 2. 逐条施工

### 2.1 `scripts/lib/camp_spec.py`

- `:22`（锚 `  - "销毁"阵营由引擎自动补列（烧入 0x0 的量），spec 里可不配置。`，唯一）改为：
  `  - "销毁"阵营由引擎自动补列（烧入 0x0 的量），spec 里可不配置；EVM 的"散户"是引擎残差桶（100−已知阵营），spec 里配置即拒（F04，2026-09-18）。`
- `:61`（锚 `            _fail(f"{source_label} 含非法阵营名: {camp!r}")`，唯一）之后插入：

```python
        if chain_family == "evm" and camp == "散户":
            _fail(f"{source_label} 阵营「散户」是 EVM 引擎的残差桶（100−已知阵营），不得在 spec 里配置"
                  f"——显式配置会让 replay_pass2/replay_duck 同日写两个元素；把这些地址归入其他阵营或删掉")
```

说明：①放在阵营名非空检查之后、值类型检查之前，对非法 `chain_family` 的既有报错顺序不变（`_normalize` 仍在有地址时才校验 chain_family；`chain_family="x"` 配「散户」会先被本条放过再在 `_normalize` 拒——可接受，本条只认 `"evm"`）；②精确匹配 `"散户"`，不 strip：带空白的变体（如 `" 散户"`）不会撞 `series["散户"]` 键、不构成本缺陷；③`_load_camps_spec`（`camp_series_provenance.py:780-789`）consumer 侧重读 spec 走同一函数，EVM 正式案 spec 从未配置「散户」（review 全量检索 0 实例；本仓库 `grep -rn '"散户"\s*:' scripts` 命中全是序列值非配置键），无存量影响。

### 2.2 `scripts/tests/test_repair_batch_c.py` —— 单元级

- `:159`（锚 `    check("F05 空阵营名硬拒", rejected({"": [A]}, "evm"))`，唯一）之后插入：

```python
    # F04（review 9.0.0）：EVM 残差桶不得显式配置；Solana 分格式语义不变（build_evolution 默认桶）
    check("F04 EVM 显式散户桶硬拒", rejected({"大庄": [A], "散户": [B]}, "evm"))
    check("F04 solana 显式散户不误杀",
          validate_camp_spec({"散户": [SA]}, chain_family="solana") == {"散户": [SA]})
```

### 2.3 `scripts/tests/test_repair_batch_c.py` —— 引擎级（两引擎同深）

- `:251`（锚 `    dup_spec = {"camps": {"camp_A": [A], "camp_B": [A]}, "entities": {}}`，唯一）之后插入一行：
  `    retail_spec = {"camps": {"大庄": [A], "散户": [B]}, "entities": {}}`
- `:256`（锚 `        check("F05 replay_duck 跨营重复 exit2", "camp-spec" in p.stderr, p.stderr[-300:])`，唯一）之后插入：

```python
    with tempfile.TemporaryDirectory() as s:
        td = Path(s)
        p = build_evm_case(td, retail_spec, expect_rc=2)
        check("F04 replay_duck 显式散户桶 exit2 且不产序列",
              "残差桶" in p.stderr and not (td / "data/camp_series.json").exists(), p.stderr[-300:])
```

- `:272`（锚 `        check("F05 replay_pass2 合法 spec 绿例", p.returncode == 0, p.stderr[-300:])`，唯一）之后插入：

```python
        (td / "camps_retail.json").write_text(json.dumps(retail_spec, ensure_ascii=False))
        p = run([ROOT / "scripts/evm/replay_pass2.py", "camps_retail.json",
                 "--data-dir", "data"], td)
        check("F04 replay_pass2 显式散户桶 exit2",
              p.returncode == 2 and "残差桶" in p.stderr, f"rc={p.returncode} {p.stderr[-300:]}")
```

说明：①`build_evm_case`（`:184-209`）以 `expect_rc` 断言 `replay_duck` 退出码；duck 的 `validate_camp_spec` 在 `:467`，早于 `:567` 的序列写盘，拒收时 `data/camp_series.json` 不存在；②pass2 用例放在合法绿例之后：`:270-272` 已用 `camps.json` 产出 `data/camp_series.json`，pass2 在 `:57` 校验处退出、不覆盖产物，`:273-275` sidecar 断言不受影响；③沿用同函数既有 `run()`/`ROOT`/`tempfile` 与 `A`/`B`/`SA` 常量（`:44-49`），不新增 helper。

RED 证据（改 `camp_spec.py` 之前，逐表达式独立执行，写 `F04_red_evidence.txt`）：
1. `rejected({"大庄":[A],"散户":[B]},"evm")` 基线 **False**（RED）；
2. `validate_camp_spec({"散户":[SA]},chain_family="solana") == {"散户":[SA]}` 基线 True（GREEN→GREEN，防误杀对照）；
3. duck：临时目录里按 `build_evm_case` 同款输入跑 `replay_duck.py --camps`（配 `retail_spec`）基线 **rc=0 且 `data/camp_series.json` 存在、「散户」长度 2**（RED）；
4. pass2：同目录 `--emit-csv` 后跑 `replay_pass2.py camps_retail.json --data-dir data` 基线 **rc=0**（RED）。
记录每项的 rc、stderr 尾行、序列「散户」值。

## 3. 完成报告 `F04_done.md` 必含

①0.1 两条命令输出；②§2 各处 `git diff` 原文；③RED 摘要（逐项）；④0.8 各测试结果尾行；⑤1.1 三个字节数；⑥`git diff --stat`；⑦与工单差异/停工点；⑧禁读披露。stdout 首行 `# 施工 F04：完成` 或 `# 施工 F04：停工`。

## 4. 登记不修（`code_change_pending.md` Q5/Q6/Q7，调度方维护）

- Solana 不拒显式「散户」（Q5）；不改引擎 append 结构（Q6）；references 零改动（Q7）。
