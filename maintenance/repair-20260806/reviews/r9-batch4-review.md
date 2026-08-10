# R9 批四批内对抗审查报告（防复发守卫 + 主账/文档收口）

> 存档说明（Fable）：Opus 4.8 只读子代理（agent accd20bb）批四批内攻击审查。带 du 避雷四预案，本发跑通（35 tool_uses）。报告写入被系统拦截，Fable 据其 result 转录。Fable 已读码核实 F-B4-01（G2 静态可绕）属实。

审查区间 `f4c40ea..65443cf`（`3b76db8`=批四主体，`65443cf`=SHA 回填）。只读原 worktree，mutant 只在最小镜像 `$M`（scratchpad 下 cp scripts+references）改。

## 一、总裁决：PASS（带 finding，不 BLOCK） · P0=0 / P1=0 / P2=1 / P3=4

五组守卫 G1~G5 均挂进 `validate_manifest()`，且 `invariant_scan.py` 与 `test_batch4_invariant_guards.py` 都在 `run_all.SUITE` 内——**必经之路成立，非旁挂**。现役全库零违规（invariant_scan PASS、10 条注入全红、三套真子进程测试全绿）。G3/G5 设计良好、机器同源、判别力经实测确认；主账诚实、文档纯追加。

**不 BLOCK 理由**：无 P0/P1，没有守卫"装了等于没装"。**但核心问题**：G2 是静态字符串匹配，可被"假 `run()` 字面量塞路径"绕过（P2），且施工记录自称的收紧未达成目标。

## 二、五组守卫 mutant 裁定表

| 守卫 | 先红后绿 | 必经性 | 攻击结论 | 裁定 |
|---|---|---|---|---|
| G1 main 退出传播 | ✓ bare int main→RED；`print(main())`→CAUGHT | ✓ validate_manifest+SUITE | 顶层裸调 `main()` 漏检 | 有效，1×P3 |
| G2 formal E2E provenance | ✓ 手写 bundle→CAUGHT | ✓ validate_manifest+SUITE | **假 `run()` 字面量可绕（CONFIRMED）** | 收紧未达自称目标，1×P2 |
| G3 capability 错身份执行 | ✓ 摘装饰器→sol 掉 ready→测试红 | ✓ 装饰器在 formal_ready 判定链上 | 无 | 有效，设计良好 |
| G4 失败产物登记 | ✓ 删登记→RED；contract→RED；3/3 真子进程 | ✓ validate_manifest+SUITE | contract 死代码可绕；standalone 硬编码 3 个 | 有效但静态层判别力有限，2×P3 |
| G5 anchor 弱覆盖下界 | ✓ 双端红；20 项 consumer 绿；3/3 producer 绿 | ✓ producer/consumer 共享唯一函数 | 无 | 有效，设计良好 |

## 三、finding 详表

**F-B4-01（P2）G2 静态可绕，收紧未达自称目标 — 半修残留**
- `formal_e2e_provenance_errors()` 对"内部只有假 `run()`（本地空函数）把 runner+5 个 required producer 路径当字符串塞进参数、零真实子进程"的伪 sol target 返回 `[]`（放行）。
- 复现：`probe_g2.py` → `G2-ATTACK errors=[] BYPASSED`，对照 `BASELINE(手写bundle)->CAUGHT`。根因：`_reachable_execution_evidence` 用 `_call_name(...).rsplit(".",1)[-1] in {"run","run_formal_script"}` 后缀匹配 + `ast.Constant` 字符串 `startswith("scripts/")`——`run` 真实性从未校验。
- `b4_progress.md:22` 自称"收紧后只计可达 run/run_formal_script 调用参数里的真实脚本"，但"真实脚本"仅字符串匹配。收紧只是把绕过语法从裸常量换成 run()-wrapped 常量。
- 定 P2 非 P1：真 target 是绿的（非误判）；利用需显式改 `VERTICAL_SLICE_EVIDENCE_TARGETS`+假 target 自带装饰器；真兜底是 SUITE 的 loopback E2E harness（但沙箱 EPERM 未跑通，且 formal_ready 与 E2E 真跑解耦）。
- 处置建议：最终盲审前把"run 是否真实子进程"纳入判据，或删除/修正过强措辞、显式声明 G2 深度边界。

**F-B4-02（P3）G4 contract_errors 死代码可充数 — 半修残留**
- `failure_artifact_contract_errors()` 纯 AST 计数（`quarantine_current`≥expected + 有 `publish_error_receipt`），不看可达性。全塞 `if False:` 死分支即绕过。复现：`probe_g4.py` → `G4-DEADCODE: [] BYPASSED`。配对真子进程测试是行为兜底。

**F-B4-03（P3）G1 顶层裸调 main() 漏检 — 新引入边界**
- `main_exit_propagation_errors()` 只在 `__main__` guard 内查 `main()`；模块顶层裸调漏检。复现 `G1-TOPLEVEL-bare: [] MISS`；guard 内 `print(main())` 正确抓。正式入口惯例 `raise SystemExit(main())`，顶层裸调罕见，理论边界。

**F-B4-04（P3）G4 standalone 集合硬编码三入口 — 新引入局限**
- formal producer 分母从 registry 机器派生（删登记即红，设计良好），但 `standalone={anchor_plan, fetch_pool_swaps, window_fetch}` 硬编码，将来新 standalone stale 入口不自动纳入。现役无缺口。

**F-B4-05（P3）pool 成功路径 CSV→marker 非原子 — 新引入，取决消费口径**
- `fetch_pool_swaps.py` 成功先 `os.replace` 发布 CSV canonical，之后才写 PASS marker；receipt 发布失败走 `fail(1)` 则 CSV 已在位而 marker=ERROR。与 anchor_plan 的 `publish_txn` 原子事务不同。安全性取决下游是否"无 PASS marker 不消费"。建议 marker 契约显式声明该顺序假设。

## 四、边界外一步
1. 必经之路——全部必经。invariant_scan+test_batch4 在 SUITE；五守卫挂 validate_manifest。G3 装饰器在 formal_ready 判定链上（摘 sol 装饰器即掉 ready 实测）。
2. 脆弱性——G2 CONFIRMED 可绕、G4-contract CONFIRMED 可绕（字符串/计数级）；G3 未发现可绕。
3. 生产文件连带——无破坏现役正确性回归。anchor final_block<0 校验移到 quarantine 后属 fail-closed 正确；pool 顺序面见 F-B4-05。
4. G5 共享同一函数——✓ `validate_anchor_coverage_parameters.__module__=='anchor_selection'`，producer/consumer 均 import。

## 五、主账诚实性
- ledger 49/49 零空栏——✓ test_sixlens_docs PASS；占位符 grep=0；盲审诚实标"总验收待执行"未伪造。
- diff-finding-map 未映射 hunk=0——✓（文件粒度；hunk 粒度未逐一机器复算）。
- maintenance-review-repair.md R9 章只追加——✓ 0 删除行。

## 六、REFUTED-CANDIDATE
G3 旁挂/G5 各写一份/主账伪造/文档改写历史/G1 连 print(main()) 抓不住——均 REFUTED。

## 七、工作区自查
只读原 worktree 未改；mutant 仅在镜像 $M（G3 摘装饰器已 cp 恢复）。未用 du/find 大目录/整树扫描；首条重命令即建镜像。未复现项：census 数值未逐字段手核（invariant_scan PASS 佐证）、pool 下游消费点未全追、hunk 粒度未逐一复算。
