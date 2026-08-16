# 【修复工单 F04】bug：deploy-sync 门禁两条假绿——缺目录 SKIP 记 rc=0、迁移豁免无界（codex review F-04，P2；R10-5）

> 施工方：codex。**禁一切 git 写命令**；只改文件。完成后写 `maintenance/repair-20260814-batch3/workorder_F04_done.md`。
> 禁触清单同 plan.md。

## 1. 不变量

1. 在正式部署机上（skill 仓库位于其规范安装路径），`~/.claude/commands` 缺失或三份命令文件与 staging 任何字节不一致 → 非零退出。
2. 非部署环境（临时 clone/盲审 checkout）→ 明确打印 `SKIP_NON_CANONICAL_CHECKOUT` 且 rc=0（run_all 无 SKIP 状态机，语义由输出行承载）。
3. 不再存在任何"deployed 内容陈旧但因迁移豁免记 PASS"的路径。

## 2. 同族清单

- 唯一改动文件：`scripts/tests/test_commands_deploy_sync.py`（run_all.py:38 挂载）。
- MIGRATION_CHANGED/MIGRATION_NEEDLES 引用仅此文件内（rg 复核）。
- 归因：无界豁免引入于 ede24d7（把豁免与 retired_present 隐式过期解耦、只查 staging needle），非 15dc48c。

## 3. 施工内容

- **删除** MIGRATION_CHANGED、MIGRATION_NEEDLES 及其豁免分支，回到逐文件 SHA-256 等值严判（实测当前部署侧三命令 SHA 与 staging 全等、退役文件已清——本删除对现状是 no-op，安全窗口）。
- **缺目录判定改"canonical 部署机"精确判**（@CX 定案，不用环境变量）：
  - `ROOT.resolve()` 精确等于 `(Path.home()/".claude"/"skills"/"token-chip-analysis").resolve()` → 部署机：DEPLOYED 缺失 → FAIL rc=1。
  - 其他位置 → 打印 `SKIP_NON_CANONICAL_CHECKOUT: <root>` → rc=0。
- **校验主体拆纯函数**：`check_deploy_sync(root: Path, deployed: Path) -> list[str]`（返回 failures 列表），main() 只做路径解析与 canonical 判定。测试直接对纯函数注入临时目录。
- RETIRED 提示逻辑保留（.bak_* 改名副本不在 RETIRED 精确名单内，现状 retired_present=[]，行为不变）。
- 输出行保持一行结论风格（run_all 只取最后一行 stdout）。

## 4. 三件套测试（并入 scripts/tests/test_repair_batch3_f01.py 同文件的独立小节，或新文件 test_repair_batch3_gates.py——二选一，选后者则挂 run_all SUITE）

- 注入临时 root+deployed：deployed 缺一文件 → FAIL；一文件字节改一位 → FAIL（原豁免文件 token-analyze-1.md 也必须 FAIL——先红点：HEAD 上该场景被 needle 豁免放行）；三文件全等 → PASS。
- 缺 deployed 目录：注入非 canonical root → SKIP rc0 且输出含 SKIP_NON_CANONICAL_CHECKOUT；canonical 判定分支用参数化纯函数直测（不真删本机目录）。
- 真环境绿例：本机实跑 test_commands_deploy_sync.py rc=0。
- 先红纪律：HEAD 上"迁移文件陈旧内容放行"反例（codex 报告 F-04 反例 2：deployed 写 STALE 字节仍 PASS）记入先红清单，修后转 FAIL。

## 5. 新建代码自审

失败分支全走 failures 列表聚合（无中途 return 0 旁路）；纯函数无 IO 副作用。

## 6. 归因预判

半修复（c62b689 原始 SKIP 设计"异机允许"意图合理但机器不可分；ede24d7 删除隐式过期未补界，属修复中引入回归）。

## 7. 验收标准（裁判执行）

- 新测试 rc=0；本机 `python3 scripts/tests/test_commands_deploy_sync.py` rc=0 且输出为逐文件一致 PASS；run_all 全绿。
- codex 报告 F-04 两个反例复跑：临时 HOME 缺目录（非 canonical root 场景）→ SKIP 行为符合新语义；STALE 字节 → FAIL。
