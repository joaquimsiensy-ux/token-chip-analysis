# 盲审 F04（只读，常规盲审，非攻击式）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918d-p1-f01-f04/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`；**禁读 `F04_done.md` 与 `F04_red_evidence.txt`**（盲审不看施工方自述，独立判断）。豁免：d) 项测试自身以子进程访问历史 maintenance 目录属测试依赖，允许原样运行，审方本人不主动打开那些历史文件。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 盲审 F04：PASS` 或 `# 盲审 F04：FAIL`。FAIL 时逐条给出：编号（F04-B1-NN）、文件:行、事实、后果、建议。PASS 时列出实际核过的项与实跑的命令/结果尾行。
3. 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，以当前 HEAD 为审对象；施工 diff＝`git diff a4a0f2ccb5cb HEAD -- scripts`。`maintenance/` 目录整体不在审查范围。

## 任务
审 F04 施工是否**真正解决**了 review 反例并符合工单 v2（`maintenance/repair-20260918d-p1-f01-f04/workorder_F04_retail_bucket.md`）：
a) **终点判据（必做，独立复现）**：`ruling_20260918.md` 的 `retail` 反例——自行构造 mint 100→A、A→B 40 两笔转账的 v1csv 通道（可复用 `scripts/tests/evm_channel_fixture.py` 的 `write_csv_channel_receipt` 与 `test_repair_batch_c.build_evm_case` 的写法）、`camps={大庄:[A],散户:[B]}`，HEAD 下 `replay_pass1 → replay_pass2` 与 `replay_duck --camps` 是否都 exit 2、stderr 含 `[camp-spec]` 与「残差桶」、全新输出目录不生成 `camp_series.json`（拒在哪一行、哪句文案）。再核：Solana `validate_camp_spec({"散户":[SA]}, chain_family="solana")` 仍接受；`load_addr_camp_json` 对值为「散户」的地址（Solana 默认链族）仍接受；既有合法 EVM spec（如 `{"项目方":[A],"大庄":[B]}`）行为逐字节不变。请自行构造夹具，不得只依赖新增测试的断言。**基线 RED 复现**：用 `git show a4a0f2ccb5cb:scripts/lib/camp_spec.py` 做内存对照，确认基线接受该 spec 且引擎产出「散户」长度 = 2×dates。
b) 修法与工单一致：`camp_spec.py` 只新增一条 `chain_family == "evm" and camp == "散户"` 拒收（走既有 `_fail`、exit 2）与 docstring `:22` 一行改动；`validate_camp_spec` 签名/返回形状不变；四入口调用点未动。
c) 白名单：**只核 `git diff --stat a4a0f2ccb5cb HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`**，须恰为 `scripts/lib/camp_spec.py`、`scripts/tests/test_repair_batch_c.py` 两文件；`SKILL.md` 8021 B、`references/**/*.md` 合计 930076 B、`commands-staging/*.md` 合计 8798 B 不变。
d) 实跑（贴尾行）。**沙箱口径**：若某测试因只读沙箱临时目录不可写而报 `No usable temporary directory found`，记为 `SANDBOX-BLOCKED`（贴该错误行）而**不计 FAIL**——由调度方本机补验；能跑的须 PASS。可先 `python3 -c "import tempfile;print(tempfile.gettempdir())"` 自检。命令：`python3 -B scripts/tests/test_repair_batch_c.py`、`test_repair_batch_d.py`、`test_engine_equivalence.py`、`test_fault_injection.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`、`python3 -B scripts/tests/invariant_scan.py`。
e) 结论规则：a)/b)/c) 全过且 d) 无真实 FAIL（SANDBOX-BLOCKED 不算）即 PASS。
