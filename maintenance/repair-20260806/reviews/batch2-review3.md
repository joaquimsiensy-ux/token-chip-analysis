# 批二消化第二轮 —— 第三轮聚焦核验报告

- **审查对象**：`/Users/uravvv/Documents/5.6筹码分析/r8-closure-worktree`，分支 `fix/r8-closure-20260806`
- **HEAD 核验**：`db0b17dac5a4f3adec35d53de1f052ec1cc76a43`（符合工单 tip=db0b17d），`git status --short` 为空
- **消化区间**：`3ca824e..db0b17d`，两 commit（B2F2-G1 `9609655` / SHA 回填 `db0b17d`），4 文件、+85/-6
- **本轮性质**：第三循环聚焦审查。不重做全面审查，只验四项 B2FR 闭合 + 新 hunk 边界 + 映射复算 + 全量 suite
- **止损相关**：本轮裁决决定是否触发 PLAN 止损线

---

## 一、总裁决

**PASS**。

| 定级 | 数量 |
|---|---:|
| P0 | 0 |
| P1 | 0 |
| P2 | 0 |
| P3 | 0 |

**归因分布：新引入 0，半修残留 0，历史漏检 0。**

四项 B2FR 全部闭合且未引入新缺口；我对新判据 `wrapper_present` 构造的四个边界变体（目录冒充、案外 symlink、案内 symlink、严格路径 symlink）全部守住；单链正常路径与 C0 基线零回退；未映射 hunk 独立复算 = 0；全量 suite 独立复跑 **76/76 PASS，EXIT=0**。

**不触发止损线**：本循环新引入 = 0、半修残留 = 0、历史 P0/P1 = 0，无同一不变量再次被击穿，无豁免回流 formal。

---

## 二、四项闭合验证（工单重点 1）

全部为子进程黑盒调 CLI，`rc` 为进程退出码。

| 编号 | 上轮状态 | 本轮构造 | rc | 实测输出尾部 | 结论 |
|---|---|---|---:|---|---|
| B2FR-01 | 伪缺席 rc=0 | 摘 artifacts 登记 + 摘 gate + **磁盘保留** wrapper 并把 `target.chain` 篡改为 `robinhood` | **2** | `✗ reconciliation_report.json 深验失败` | **已闭合** |
| B2FR-01 反向 | — | RL3 真缺席合法旧案（bsc formal tier，wrapper 已 `unlink`） | **0** | `⚠ LEGACY READ-ONLY：handoff/v2 旧格式仅供读取既有冻结结论……` | **未误伤存量** |
| B2FR-02 | 自产过不了自验 | `--chain bsc,bsc` generate → strict verify | **0** | `[verify] PASS 15 件产物哈希一致，4 个 gate 重查通过，状态 READY`；`manifest chains=['bsc']` | **已闭合** |
| B2FR-03 | 主表漏列 | 核对 `diff-finding-map.md` B2F-G3 行与 `batch2-report.md` §8.4/§8.5 | — | 两表均已补 `reviews/batch2-review.md`；§8.5 改为"仅新增审查报告入库（+484 行，Fable 拷入），既有内容零改动" | **已闭合** |
| B2FR-04 | 区间末端非 tip | 核对未映射 hunk 计数段 | — | 消化区间已改 `5924cd5..3ca824e`；表下新增通例"区间末端恒取候选 tip；自指式 SHA 回填 commit 计入本区间" | **已闭合** |

生产改动仅两处，均与工单声明一致：

`scripts/report/handoff_manifest.py:178`（B2FR-02）——

```python
        chains = sorted(set(chains))
```

`scripts/report/handoff_manifest.py:333-335`（B2FR-01）——

```python
    wrapper_present = ("reconciliation_report.json" in art_paths
                       or os.path.isfile(os.path.join(case_dir, "reconciliation_report.json")))
    if not legacy or wrapper_present:
```

新反例与我上轮给出的最小复现构造**一一对应**：`test_batch2_legacy_hardening.py` 的 `test_b2f_lg_05_disk_wrapper_cannot_fake_absence`（摘登记 + 磁盘保留 + 篡改为 robinhood）与 `test_duplicate_generate_chain_is_canonical`（`bsc,bsc` → 断言 `chains == ["bsc"]` 且 verify rc=0），两者均已挂入 `main()` 的 tests 元组。

---

## 三、发现清单

**无。本轮零发现。**

新引入 = 0，半修残留 = 0，历史漏检 = 0。上轮遗留的 OB-E / OB-F / OB-G 三项观察按裁决零触碰，本轮未复查其状态变化（工单范围外）。

---

## 四、新 hunk 边界外一步核验（工单重点 2）

### 4.1 `os.path.isfile` 判据自身可否被操纵

新判据把"在场"从纯自报扩展为"清单登记 **或** 磁盘 `isfile`"。我针对 `isfile` 这个新增的真值来源构造四个变体。

| # | 构造 | rc | 实测 | 结论与收益评估 |
|---|---|---:|---|---|
| BD1 | **目录冒充文件**：删掉 wrapper 文件后，创建同名**目录** `reconciliation_report.json/` | 0 | LEGACY READ-ONLY 放行 | **守住**。`os.path.isfile(目录)` 为 False，判据落回"缺席"分支——但此时案内确实没有 wrapper 文件，效果与合法真缺席（RL3）完全等价，**零额外收益**。且下游 `audit_release_gate.run()` 的 `missing = [name for name in required if not (case_dir / name).is_file()]` 会直接报"缺必需资产: reconciliation_report.json"，正式发布路径仍拒 |
| BD2 | **symlink 指向案外**：把真 wrapper 移到案目录之外，案内留同名 symlink 指过去 | 2 | `✗ reconciliation_report.json ...` 深验触发后失败 | **守住**。`isfile` 跟随 symlink 返回 True → 触发深验 → `shared_release_receipt.regular()`（`:47-56`）先 `if raw.is_symlink(): raise ValueError`，再 `path.relative_to(root)` 做越界检查，两道都拦。方向是**更严**而非绕过 |
| BD3 | **symlink 指向案内**：wrapper 改名为 `real_w.json`，案内留同名 symlink 指过去 | 2 | 同上 | **守住**。同 BD2，`regular()` 的 symlink 拒绝不看指向何处 |
| BD4 | **严格路径 symlink**（非 legacy，验新判据未削弱主路径） | 2 | 同上 | **守住** |

如实结论：`isfile` 引入的新真值来源**没有**打开新的绕过面。它只有两种偏差方向——判 False 时退化为与合法缺席等价（无收益，且下游独立拒），判 True 时把可疑对象送进深验（更严）。`validate_reconciliation_report` 内部自带 symlink 与越界防护，是这个判据能安全使用的前提，已实测确认。

### 4.2 `sorted(set(chains))` 对单链正常路径的影响

| 核验项 | 实测 | 结论 |
|---|---|---|
| C0 基线正例（`GEN` 常量单链 `bsc`） | verify rc=0，`PASS 15 件产物哈希一致，4 个 gate 重查通过` | **零影响** |
| `--chain bsc,bsc` 规范化后 | manifest `scope.chains == ['bsc']`，strict verify rc=0 | 符合预期 |
| handoff 契约 65 项 | 在全量 suite 内 `test_handoff_manifest.py` PASS | **不回退** |

`sorted(set(['bsc']))` 恒等于 `['bsc']`，单链路径逐字不变；改动只在多元素输入时生效，且位置在唯一性判定 `if len(set(chains)) != 1: return 2` **之后**，不会放宽准入（真多链仍在前一行被拒）。

### 4.3 区间自指写法的裁决（工单点名）

map 第 53 行写法：

```
- 批二批内消化第二轮（`3ca824e..` 至本回填 commit 即候选 tip，含 `B2F2-G1`=`9609655` 与本表自身回填）：`0` 候选
```

**裁决：满足我 B2FR-04 的通例意图，且优于机械填 SHA。**

理由：回填 commit 在写入表格内容时物理上无法预知自身 SHA——这是我提出 B2FR-04 时未意识到的硬约束，也正是前两轮区间末端反复滞后一个 commit 的根因。该写法用文字自指精确锚定末端，并显式列出区间内两个 commit（`9609655` + 本表自身回填），读者可唯一确定区间边界，语义完备无歧义。配套通例句"区间末端恒取候选 tip；自指式 SHA 回填 commit 计入本区间"已落在表下，与我原建议逐字一致。

附注（非缺陷）：历史行（批一、批二、消化第一轮）仍用"下一轮补填 SHA"的写法，与新自指写法并存。因历史行的末端 SHA 已确定且标注正确，无需回改；后续新增区间沿用自指写法即可。

---

## 五、未映射 hunk 独立复算（工单重点 3）

区间 `3ca824e..db0b17d`，`git diff --stat` 合计 **4 文件**、+85/-6。

| 分组 / SHA | map B2F2-G1 行登记 | `git show --stat` 实际 | 差异 |
|---|---:|---:|---|
| B2F2-G1 `9609655` | 4（`handoff_manifest.py`、`test_batch2_legacy_hardening.py`、`diff-finding-map.md`、`batch2-report.md`） | 4（逐一吻合） | 无 |
| SHA 回填 `db0b17d` | 按新通例自指式计入 | 1（`diff-finding-map.md` 自身） | 无 |

**复算结果：未映射 hunk = 0**（生产、测试、台账三类 hunk 全部有 owner）。

逐 hunk 夹带检查：
- `handoff_manifest.py` 仅两处改动（`:178` 去重规范化、`:333-335` 判据取或），均在 B2FR-01/02 owner 范围内，无顺手整理。
- `test_batch2_legacy_hardening.py` 新增两个测试函数并挂入 `main()` tests 元组，改 print 文案为 `B2F-LG-01..05 + duplicate-chain canonicalization`，全部服务本轮 owner。
- 两份台账改动均为 B2FR-03/04 的修正内容，无历史段改写。
- 上轮已入库的 `reviews/batch2-review.md` 本轮**零改动**（不在改动文件列表内），我的报告未被事后修改。

---

## 六、全量 suite 独立复跑（工单重点 4）

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py
...
全部通过
EXIT=0
```

PASS 行计数 **76**，与修复方 `batch2-report.md` §8.6 自报的 76/76 一致。本次为我独立复跑所得，非引用自报。

---

## 七、台账一致性比对

以与前两轮相同的标准核对 `batch2-report.md` §8.6 新增章节：

| 修复方陈述 | 我的独立核验 | 判定 |
|---|---|---|
| B2FR-01 红例：`B2F-LG-05` 在旧代码上 `rc=0`，改判据后 `rc=2` | 与我上轮 RL7 实测（rc=0）及本轮复测（rc=2）吻合 | **属实** |
| "既有 `B2F-LG-03` 仍证明 wrapper 真缺席的合法 v1/v2 旧案 `rc=0`" | RL3 独立复现 rc=0 | **属实** |
| B2FR-02 红例：manifest 实存 `['bsc','bsc']` 被自家 strict verify 拒；绿例实存 `['bsc']` 双 `rc=0` | 独立复现，manifest `chains=['bsc']`，verify rc=0 | **属实** |
| B2FR-03 修正：两表补列、§8.5 表述改写 | map B2F-G3 行与 §8.4 均已补 `reviews/batch2-review.md`；§8.5 现为"仅新增审查报告入库（+484 行，Fable 拷入），既有内容零改动" | **属实**（表述张力已消除） |
| B2FR-04 修正：区间改 tip + 通例句 | 第 51 行为 `5924cd5..3ca824e`；通例句与我原建议逐字一致 | **属实** |
| "OB-E/OB-F/OB-G 按工单零改动" | 四文件改动清单中无 `chain_registry.py`、`formal_ready_test_harness.py`、`test_batch2_registry_harness_hardening.py`、`audit_release_gate.py` | **属实** |
| "改动文件仅为"四项列表 | 与 `git show --stat 9609655` 完全一致 | **属实** |
| "76/76 PASS，EXIT=0" | 独立复跑一致 | **属实** |

本轮未发现任何自报不实。前两轮各抓到一处（第一轮 harness"只在独立测试进程"表述、第二轮"`reviews/` 零改动"表述），两处均已在后续轮次修正。

---

## 八、执行命令清单

```bash
git -C <worktree> rev-parse HEAD                      # db0b17dac5a4...
git -C <worktree> log --oneline 3ca824e..db0b17d
git -C <worktree> diff --stat 3ca824e..db0b17d        # 4 files, +85/-6
git -C <worktree> diff 3ca824e..db0b17d -- scripts/report/handoff_manifest.py
git -C <worktree> show --stat --format="" 9609655 db0b17d      # 映射复算

# 动态验证（mktemp -d，全部 PYTHONDONTWRITEBYTECODE=1）
python3 $TD/v3.py     # RL7 闭合 / RL3 不误伤 / bsc,bsc 自产自验 / BD1-BD4 边界 / C0 基线

# 全量回归与收尾自查
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py     # 全部通过 EXIT=0（76）
git -C <worktree> status --porcelain                           # 空
```

---

## 九、复核方自我声明

- 仓库全程零写入：起止 `git status --short` / `--porcelain` 均为空。
- 临时件全部位于 `mktemp -d`，所有 Python 调用带 `PYTHONDONTWRITEBYTECODE=1`（含子进程继承）。
- 未与修复线程通信；未读主仓库 main 基线、`~/.codex/`、MEMORY 或历史案例目录。
- 每条论断均先读磁盘真实文件后作出；本轮无凭印象补全的代码摘录。
- 本轮为聚焦审查，未重做全面六视角扫描——"PASS"仅意味着在本轮指定范围（四项闭合、新 hunk 边界、映射复算、全量 suite）内未照出问题，不等于证明其余部分无缺陷。
