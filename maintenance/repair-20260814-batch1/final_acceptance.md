# 批 1 修复工程终验收（final acceptance）

> 验收方：Fable（裁判，全程不写生产代码；施工=codex，盲审=独立子代理，三方隔离）
> 分支 repair-20260814-batch1；基线 main@c41ed07；终验 HEAD=2d69373
> 日期：2026-08-14　　版本交付：6.40.0 → 6.41.0

## 一、工程概览

两轮独立六视角 review（codex 全量 12 项＋Fable 全量 P2×3/P3×9）合并出批 1 五项，经 @CX codex 复核融合后开工。八步节拍＋一轮消化，全程隔离调度：codex 施工（无 git 权限）→ 裁判凭落盘报告＋diff＋独立复跑验收 → 裁判代 commit＋push。

| 修复项 | 一句话 | commit | 归因终判 |
|---|---|---|---|
| RV-07 | publish_supersede 原语：真 FAIL 经归档取代旧 PASS 落盘，五出口接入 | f490c1e | 修复中新引入（6.36.0） |
| RV-04＋RV-17 | proxy_config 统一解析器收编 10 点＋stake_decode 假闭合 fail-closed | 8be32d5 | 双历史漏检 |
| F-03 | replay 三引擎 gate 语义统一（pass1 退出码/pass2 前置检查/duck 诊断隔离） | d78e210 | 半修残留（6.13.0 判例族） |
| F-01 | fig1 白名单＋select_fig1_series 单源＋legend receipt | c5f3458 | 历史漏检（批 C 明示零触碰） |
| A5 v3 | legend receipt 双层信任根（A5 冻结实物＋发布闸重算语义） | e5c8043 | 历史漏检（F-01 同案） |
| F-04 | 四入口位置 token 移除＋自动枚举＋sentinel 不进输出 | 253ac79 | 半修残留（RA-07 族） |
| 收尾⑦+⑦b | manifest 登记清零＋P1-05 夹具升级＋6.41.0 四锚＋sol 日期断链修复 | deb073e | ⑦b＝历史漏检（端到端路径首曝） |
| 盲审+消化 | P1 锁遗留死锁修复＋P2 回显抑制＋P3×3 处置 | 2d69373 | P1＝修复中新引入（本批步骤①） |

## 二、验收方法与记录

每步验收四件套：①落盘施工报告五栏齐全性检查；②`git diff` 改动面与清单核对（含越界检查）；③关键验证命令**裁判独立复跑**（不信自报退出码）；④信任根/生产核心 diff **亲读**。加做的裁判独立攻击：

- 步骤⑥：自构造 sentinel（与 codex 测试面零重叠）注入 v2/v1 入口——均 rc=2 拒绝且零回显。
- 步骤⑧消化后：**自写探针重放盲审 SIGKILL 攻击链**——真实 SIGKILL（rc=-9）→锁遗留→拒绝消息三要素（锁绝对路径/恢复指引/SUPERSEDE_LOCK_PRESENT 分码）→`--recover` 判定 ROLLED_BACK→重试 supersede 成功落盘 FAIL。重放探针与施工方测试代码零重叠，"验自洽≠验真实"达成。
- 过程中裁判纠错 2 次：步骤⑦ BLOCKER（sol 日期断链）裁判查证后锁定 consumer 侧修复方向（producer ISO 格式是文档化契约不可动）；探针自身 3 次撞上 kernel 逐层校验（mode 枚举/target 三键/producer 实文件）——kernel 防伪面在裁判攻击下的意外正面样本。

## 三、盲审与消化

独立盲审（general-purpose 子代理，与施工方模型隔离，只看仓库现状）：**P0×0／P1×1／P2×1／P3×3**；四项 PASS、RV-07 FAIL；12 条攻击被挡清单在案；施工报告关键绿灯经盲审员实跑核实非自报。报告 `batch1_adversarial.md`（SHA `630b9174…`，消化施工前后一致，未被触碰）。

消化轮（codex，一轮闭合）：
- **P1（修）**：锁遗留死锁——分码指认＋恢复原语四态状态机；fcntl advisory lock 做活锁证据（内核在进程崩溃时自动释放，天然免疫 PID 复用，优于任务书原提的 PID+时间戳方案）；锁绑定目标 FAIL 载荷哈希防误判旧 FAIL；不可判定态 fail-closed 盘面不动。第八条反例（SIGKILL 崩溃→恢复→落盘）先红后绿入矩阵。
- **window_fetch 混合态（不改）**：现有事务顺序重跑幂等，注入测试实证"FAIL receipt＋旧 data＋.stale"重跑后闭合。
- **P2（修）**：四支 `_load_token` 固定文案，`--token-file` 值不再回显。
- **P3 处置**：枚举器 endpoint 独立充分证据＋排除清单（修）；pass2 信任边界注释（记，防篡改由 provenance 绑定＋下游哈希链承担）；stake_decode cap 截断→complete=false/ERROR（修，cap+1 探测证穷尽）。
- RV-07 裁决 FAIL→PASS（裁判独立重放确认）。

## 四、最终快照验证（HEAD=2d69373，裁判环境）

| 验证 | 结果 |
|---|---|
| `run_all.py` 全量 suite | **全部通过**（含 codex 沙箱跑不了的 2 项 loopback vertical slice） |
| `invariant_scan.py` | exit 0：producers=56/consumers=64/transport=62/atomic=49/formal=58/exceptions=0 |
| `docs_lint.py --all`／`changelog_lint.py` | PASS（58 文档；活跃 27 条） |
| `test_version_consistency.py` | PASS：四锚一致 6.41.0 |
| 盲审报告 SHA | 前后一致（`630b9174…`） |
| pre-commit 三检 | 八次 commit 全过 |

## 五、遗留与协调点

1. **batch2 协调（合并后必办）**：主工作树另一工程分支 `repair-20260814-batch2`（F-10 硬顶 100bps＋F-02）基于旧 main@c41ed07，本批合并后其收口时需 rebase/merge 新 main；预计冲突面：`supply_truth_gate.py`、`CHANGELOG.md`、`invariant_manifest.json`、版本号（batch2 需升 6.42.0）。
2. **R11 候选（不阻塞）**：盲审 P3 之 pass2 信任边界（已注释级写明）；duck `build_events` 缺文件 warning 旧文本（step3 报告§②点名，有下游重验兜底非 fail-open）；F-10 硬顶三段式属 batch2 范围。
3. codex 沙箱 2 项 loopback bind 失败为环境能力限制，非代码问题（裁判环境实证通过）。

## 六、裁决

批 1 五项修复全部验收通过，盲审 FAIL 项经消化轮闭合并由裁判独立重放确认。**准予合并 main。**
