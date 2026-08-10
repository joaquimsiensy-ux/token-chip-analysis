# 施工工单：supply_truth_gate 销毁形态②适配 + verify_recon 闭合口径修正（升 supply-truth-receipt/v3）

你是本仓库的施工执行者。**只改文件+跑离线测试；禁一切 git 操作（commit/branch/stash 都禁）；禁网络调用（所有新测试必须离线 mock）**。commit 由验收方（Claude/Fable）完成。你的工作目录就是本 worktree 根。

**进度纪律**：每完成一个子项，向 `WORKLOG_codex.md` 追加一行（`[时间] A<n> 完成：<一句话>`）。全部完成后跑 `python3 scripts/tests/run_all.py`，把完整输出保存到 `acceptance/run_all_final.txt`。

---

## 背景（为什么改）

**案例**：APU（ETH `0x594daad7d77592a2b97b725a7ad59d7e188b5bfa`）。链上 totalSupply=420,690,000,000 枚（constructor 一次铸完，无 burn() 外部函数，从未变过）。持有人把 82,800,853,653.911207346039942180 枚扔进 dead 地址（0x…dEaD）——这是"销毁形态②"（dead 沉没，totalSupply **不减**）。而 `scripts/lib/supply_truth_gate.py` 的判定 `replay_net = mint_total − burn_total` 对比 totalSupply 只适配"形态①"（合约级 burn，totalSupply 实减），于是形态②币种必假 FAIL（APU 实测差 1968.2bps）。两形态的权威定义早在 `references/playbook-supply-recon.md` 第 31 行档了，代码未跟。

**APU 实测数字（用于测试反例）**：
- mint_total_wei = 420690000000000000000000000000（=onchain totalSupply，逐 wei 相等）
- burn_total_wei = 82800853653911207346039942180（全部为转入 dead 的沉没，0x0 流入为 0）
- replay sum_balances_wei = 420690000000000000000000000000（sink 余额照加口径）
- 链上实查：balanceOf(dead)=82800853653911207346039942180，balanceOf(0x0)=0

**GNT 底线（此闸的存在理由，防护力不得削弱）**：GNT 案老合约 migrate() 静默改账不发事件，重放余额虚高 10 倍而其余自检全 PASS，唯一暴露手段就是 replay_net 对 totalSupply。GNT 形态下 mint_total(事件累计)=10 亿 vs 链上 2.035 亿——**任何新逻辑必须让 GNT 依旧 FAIL**。

**同批必修的 P0**：`scripts/evm/verify_recon.py:88` 的供给闭合判定 `balance_sum == mint - burn` 与 replay 口径矛盾——`scripts/evm/replay_duck.py` 明示（文件头注）burn 记账但 sink 收方余额**照加**，恒等式是 `sum_balances == mint_total`。burn>0 的币（如 APU）即使修好 truth gate，四查里这条也必炸。现纵切测试只测 burn=0 所以从没暴露。

---

## 施工清单（顺序执行，A1→A7）

### A1 新建 `scripts/lib/supply_semantics.py`（sink 语义常量单源）

零依赖小模块，内容：
- `ZERO = '0x0000000000000000000000000000000000000000'`（事件哨兵/潜在 sink 双语义，注释说明）
- `DEAD = '0x000000000000000000000000000000000000dead'`
- `REPLAY_BALANCE_SINKS = (ZERO, DEAD)`（重放侧"记 burn_total 但余额照加"的地址集合）
- 模块 docstring 写清形态①/②定义（指针到 playbook-supply-recon.md），说明"从事件流无法区分 to∈sink 的真 burn 与沉没，区分只能靠对照链上 totalSupply"。

**收敛 import（只改供给判定路径这 5 个文件，其余文件不动）**：`scripts/evm/replay_duck.py`、`scripts/evm/replay_pass1.py`、`scripts/evm/replay_stream.py`、`scripts/evm/verify_recon.py`、`scripts/lib/supply_truth_gate.py`——把各自内联的 0x0/dead 字面量改为 import 此单源（注意 scripts/evm 下脚本对 scripts/lib 的 sys.path 处理，仿照它们现有 import lib 模块的方式；若某文件原本没有这两个字面量则不动它）。`build_labels/wave_scan/anchor_selection/cluster_sensitivity/cost_engine` 里的 dead 是标签/排除用途，**明确不改**。

### A2 `replay_duck.py` 统计拆分（新增字段，旧字段全保留）

现状（main 版 ~198 行）：`burn_total` 是 `WHERE t2 IN (Z, DEAD)` 的合计。新增四个独立统计并写进 replay_stats JSON（旧字段 `mint_total_wei/burn_total_wei/sum_balances_wei/...` 一律保留不动）：
- `zero_event_inflow_wei`：`SUM(v) WHERE t2 = ZERO`
- `dead_event_inflow_wei`：`SUM(v) WHERE t2 = DEAD`
- `dead_event_outflow_wei`：`SUM(v) WHERE f2 = DEAD`（from 侧；dead 无私钥理论上恒 0，但记账要完整）
- `dead_sink_net_wei`：inflow − outflow

同族同步（**同深度原则**）：检查 `replay_pass1.py`、`replay_stream.py` 是否也产 replay_stats 同类统计——若是，同样拆分；若它们只是引用 sink 地址做排除/过滤，则只换 A1 的 import 不加字段。逐一在 worklog 记录你的判断依据。

### A3 `supply_truth_gate.py` 形态②回退判定

- `decide()` 纯函数**一行不改**（形态①行为零变化）。
- 新增纯函数（离线可测，不打网络）：
```python
def decide_sink_fallback(mint_total, burn_total, onchain,
                         zero_event_inflow, dead_sink_net,
                         onchain_zero_balance, onchain_dead_balance):
    """主判定 FAIL 后的形态②判定。全部 wei 级零容差，任何 None 分量→不适用（返回 FAIL 语义）。
    条件（全部成立才 PASS）：
      C1: mint_total == onchain                       # 链上自铸造从未减发
      C2a: zero_event_inflow == onchain_zero_balance   # 0x0 逐地址对账
      C2b: dead_sink_net == onchain_dead_balance       # dead 逐地址对账
      C3: zero_event_inflow + dead_sink_net == burn_total  # 拆分统计与合计闭合
    返回 (verdict, burn_form)：("PASS","dead_sink") 或 ("FAIL",None)。"""
```
- main 流程接线：仅当 **主判定 FAIL ∧ chain != "solana" ∧ replay_stats 含全部拆分字段**（旧格式 stats 缺字段→不触发回退，维持 FAIL，fail-closed）时：
  - 用**同一个** attested_rpc_pool、同一 `--as-of-block` 块高，**一次 call_many** 取三个链上值：totalSupply（已有）、balanceOf(ZERO)、balanceOf(DEAD)（ERC20 balanceOf selector `0x70a08231` + 左补零 32 字节地址）。任一调用失败/空返回/格式非法 → **exit 1**（检测自身失败，禁当 PASS）。
  - 跑 `decide_sink_fallback`，PASS 则 verdict=PASS/exit 0 并在 receipt 记 `burn_form="dead_sink"`；否则维持 FAIL/exit 2。
- **无任何人工 override 参数**（不加 --force-sink、不加可传 sink 地址的参数）。`--replay-net-raw` 探索路径无 mint/burn 分量，天然不触发回退。
- receipt 新增字段（见 A5 schema）：`decision_rule`（"primary_form1" | "sink_fallback_form2"）、`burn_form`、`primary_verdict`（主判定原始结果）、`sink_reconciliation`（逐地址：replay 侧值 vs 链上值，全部字符串化 wei）。
- **措辞纪律**：代码注释与 receipt 语义只写"终态标量与 sink 逐地址归因闭合"，**禁写**"排除静默改账"（总量不变的分布级改账本就不在此闸射程，由 A2 查1 余额对账/时间锚点/双源对照兜）。

### A4 `verify_recon.py` 闭合口径修正

第 88 行（main 版）：`supply_closed = mint == nominal and balance_sum == mint - burn and not negatives`
改为与 replay 口径同源：`supply_closed = mint == nominal and balance_sum == mint and not negatives`（sink 余额照加 ⇒ sum==mint 是恒等式）。burn 分量保留为独立记录字段（供报告引用），不再参与闭合等式。检查该文件产出 JSON 与下游对此字段的消费（rg 引用面），保持兼容。

### A5 schema 升 `supply-truth-receipt/v3`

- `supply_truth_gate.py` 的 `build_envelope("supply-truth-receipt/v2", ...)` → v3，新增 A3 所列字段。
- **全库同步（rg 'supply-truth-receipt' 逐个处理）**：`scripts/report/shared_release_receipt.py`（v2 接受点改 v3，必需字段清单更新）、`scripts/tests/invariant_manifest.json`（登记的 schemas 数组）、`scripts/report/audit_release_gate.py`（若校验 schema 串）、`scripts/tests/test_handoff_manifest.py` / `test_audit_release_gate.py` 等 fixture（升级为 v3 结构；**保留一条 v2 旧格式 fixture 作为 legacy 负例**——断言新校验器对 v2 的处理行为并显式写明预期）。
- `scripts/report/holder_distribution_scan.py` 的 `load_supply()`（~207-216 行）从 supply_truth.json 读 `replay_net` 当净供给分母——v3 下确认字段仍在（replay_net 字段保留）并按需兼容读取；**语义不改**（形态②下 replay_net=剔除 dead 后净供给，正是分布扫描想要的分母）。
- `scripts/report/handoff_manifest.py` AUTO_GATES 只读 verdict/exit_code——确认对 v3 无感后在 worklog 记一行证据。

### A6 测试（先红后绿，全部离线）

扩展 `scripts/tests/test_supply_truth_gate.py`（或按仓库惯例新建配套测试文件并挂进 `run_all.py` 的 SUITE）：

**操作顺序（红证据必须留档）**：先写下列测试 → 跑一遍 → 把失败输出保存 `acceptance/red_phase.txt`（此时 APU 反例应红，因为新逻辑还没写）→ 再施工 A1–A5 → 复跑变绿。

用例清单：
1. **APU 真实反例**（上方数字）：拆分字段齐全 + mock 链上三值 → 期望 PASS + burn_form=dead_sink + decision_rule=sink_fallback_form2。
2. **GNT 回归**：mint=1e9×1e18、onchain=2.035e8×1e18 → C1 不成立 → FAIL（不管 sink mock 给什么）。
3. **混合形态**：mint−onchain 差额 ≠ 0 且 ≠ burn_total（部分真 burn 部分沉没）→ FAIL。
4. **sink 逐地址差 1 wei**：dead_sink_net 与 onchain_dead_balance 差 1 → FAIL。
5. **地址间补偿攻击**：zero_inflow=100、dead_net=200，链上 zero=200、dead=100（合计相等但逐地址错位）→ FAIL（这正是逐地址设计要拦的）。
6. **旧格式 replay_stats**（无拆分字段）→ 回退不触发，维持 FAIL。
7. **形态①与容差内 PASS 案**：主判定 PASS 路径行为与产物字段零变化（decision_rule=primary_form1）。
8. **RPC 部分失败**：三个链上值任一 mock 失败 → exit 1（禁当 PASS）——mock 方式仿照本文件/仓库现有离线 mock 惯例（如注入 fetch 函数或 mock pool）。
9. **Solana 链**：回退不触发（分支限 EVM）。
10. **纵向非零 dead 反例**（补历史覆盖缺口）：在 `test_batch3_evm_vertical_slice.py` 或其配套处新增一条"非零 dead 沉没"贯穿用例——replay_stats(burn>0, 拆分字段) → verify_recon 闭合（sum==mint 口径）→ supply_truth v3 receipt → shared_release_receipt 校验通过。至少覆盖 verify_recon 新口径在 burn>0 时 PASS、旧口径必炸的对照。

### A7 文档与版本（同批）

- `references/data-pipeline-evm-recon.md`：供给真值闸描述段补形态②自动判别（两口径、逐地址 sink 对账、混合形态维持 FAIL、措辞降级）。
- `references/analyze-workflow.md`：A2 查3 描述若有 gate 判据句，同步一句（先 rg 定位，没有就不加）。
- `references/casebook/supply-accounting.md`：按册内既有条目格式新增一条（编号顺延，标【单案候选】）：形态②假 FAIL 触发现象、APU 案出处（2026-08-09）、机械闸=supply_truth_gate 形态②回退。
- `CHANGELOG.md`：按仓库现有条目格式新增 6.38.0 条目（注意仓库有 changelog_lint，格式仿最近条目）。
- 版本三处同步 **6.38.0**：`VERSION`、`SKILL.md` 的版本注释行、`pyproject.toml`（R9 教训：test_version_consistency 查三处一致）。

---

## 完成定义（DoD）

1. `acceptance/red_phase.txt`（先红证据）与 `acceptance/run_all_final.txt`（全量 suite 全绿）都在。
2. `rg -n 'supply-truth-receipt/v2' scripts/` 仅剩显式 legacy 负例 fixture（每处有注释说明）。
3. WORKLOG_codex.md 逐项打点，含 A2 同族判断依据与 A5 的 AUTO_GATES 无感证据。
4. 不存在任何 git 状态变更之外的副作用（无网络调用、无仓库外写入）。
