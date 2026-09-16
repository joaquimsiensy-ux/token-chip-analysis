# 工单 T2（v1）：seal ↔ 正文零地址打架 —— 三策略翻转披露定为附录 F（零代码）

> 出处：用户 2026-09-16 批准的三项修复计划 §2.1（裁决："披露表定为附录、seal 不改"）。原则：**不增加 skill 上下文；能删的不新增，能改的不新增**。
> 基线：分支 `fix/three-items-20260916`，在 T1 之后施工（与 T1 无文件重叠，可独立）。

## 0. 开工纪律

- 工作目录 `/Users/uravvv/.claude/worktrees/tca-three-items`（独立克隆；**不要**碰 `/Users/uravvv/.claude/skills/token-chip-analysis`）。开工 `git status --short` 除 `maintenance/repair-20260916-three-items/` 外须为空。
- 行号均指施工前基线；锚文本不一致即停工写 `t2_done_attempt1_stopped.md`。
- **禁止**读取 `/Users/uravvv/.codex/`、`/Users/uravvv/.claude/skills/_archive/`、tag `codex-frozen-20260915`。离线；不 commit。
- **白名单**：`references/report-template.md`、`scripts/tests/test_repair_batch_d.py`、本目录证据文件。**`scripts/report/a5_report_seal.py` 一行不改**（`_disclosure_slice` :153-172 按标题行切片、任意层级；`provenance_flip_bundle` :175 逐字核 `terminal[2]`＋策略名＋份额——附录里写完整地址即可满足，无需改闸）。不动 CHANGELOG/VERSION/pyproject。
- 完工写 `t2_done.md`：改动清单、RED→GREEN、run_all 结果行、report-template.md 改前/改后字节数。

## 1. `references/report-template.md`（改前 42499 字节；改后须 ≤ 42499，预期 42489）

五处替换，逐字：

- `:145`（锚 `## 附录（默认四件套；E 买入后按需）`）→
  `## 附录（默认四件套；E 买入后按需；F 仅有翻转时）`
- `:148`（锚 `     **任何情况下不可省**：正文零地址设计下这是报告可验证性的唯一支点，`）→
  `     **不可省**：正文零地址下这是可验证性的唯一支点，`
- `:149`（锚 `     也是买入后补生成 JSON 的原料（生成后与 JSON addresses 完全一致）`）→
  `     也是买入后 JSON 附录的原料（与 addresses 完全一致）`
- `:153`（锚 `     schema 见 monitoring-package.md）`，即附录 E 第二行）之后**新增一行**：
  `  F. 溯源三策略翻转披露（仅存在真实翻转时；此处允许完整地址，写法见图层同源④）`
- `:222`（锚 `  ④溯源存在真实三策略翻转（flip-adjudications/v1 裁决）时，报告必须有**披露章节**：`…`写在别处不算数。`）整行替换为：
  `  ④溯源存在真实三策略翻转（flip-adjudications/v1 裁决）时，披露写在**附录 F**（标题含收据 `report_locations` 声明的位置串；正文只写"见附录 F"）：同段写全三策略（`pro_rata/fifo/lifo` 或"按比例/先进先出/后进先出"任一）、每策略主导终点完整地址与两位小数份额——A5 seal 只核该切片。`

`:53`（钱包标签制）、`:265`、`:284`（正文零地址）**不动**——附录本就允许完整地址（附录 A/B 已是先例），打架点只在 :222 曾要求正文写终点标识。
改后跑 `python3 scripts/tests/docs_lint.py --all` 须 PASS。

## 2. `scripts/tests/test_repair_batch_d.py` `t_f06_a5_disclosure`（新增一条绿例，原用例全部不动）

在 `:537-538`（锚 `check("F-06 A5 绿例：披露章节内含三策略名＋top＋份额 → DISCLOSED",`）之后、`# 报告缺披露段 → 拒` 之前插入：

```python
        # 模板 2.1：披露放附录 F，正文零地址只写"见附录 F" → 仍 DISCLOSED（切片按标题命中，不看层级/位置）
        appx_parts = ["# 报告", "## 实体", "项目方钱包 W1 的溯源存在三策略翻转，见附录 F。", "## 附录 F：溯源三策略翻转披露"]
        for info in real.values():
            for policy in hm.FLIP_POLICIES:
                appx_parts.append(f"{policy}: {info['tops'][policy][2]} 占 {info['shares'][policy]}%")
        appx_parts.append("## 附录 G：数据来源")
        appx_bundle = a5.provenance_flip_bundle(tmp, "\n".join(appx_parts), a4obj)
        check("2.1 绿例：披露在附录 F、正文只写'见附录 F' → DISCLOSED",
              appx_bundle["status"] == "DISCLOSED" and appx_bundle["anchors"], appx_bundle)
```

- 夹具的 flip receipt `report_locations` 为 `["翻转披露"]`（`:375`），标题"附录 F：溯源三策略翻转披露"含该子串即命中；无需改收据。
- RED 判据：本条属"证明现状已支持附录写法"，改前改后都应 GREEN——把改前运行结果原样记入 `t2_red_evidence.txt` 并注明"预期 GREEN（模板改动零代码，闸未变）"。

## 3. 完成标准

- report-template.md 字节 ≤ 42499；docs_lint PASS；`python3 scripts/tests/test_repair_batch_d.py` PASS（新增 1 条）；run_all 全绿（nohup 落文件）。
- Fable 本机验收项（案卷在仓库外，codex 不做）：APU 0914 已封口报告（披露在其"附录C"）复跑 `a5_report_seal.py` 仍 PASS，证明附录写法与现闸兼容。
- `t2_red_evidence.txt`、`t2_done.md` 在本目录；不 commit。
