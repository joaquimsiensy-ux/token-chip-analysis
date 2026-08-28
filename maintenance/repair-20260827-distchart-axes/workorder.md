# 【修复工单】持仓分布图 write_png 升级为 matplotlib 带轴高档图(v6.53.0)

基线 commit:`252a11b`(main,工作区干净)。施工方 codex:只改本工单白名单内文件,**禁一切 git 写操作**(不 add/commit/branch);裁判方验收后代 commit。红绿证据与完工报告写入本目录。

## 出处(为什么改)

BTW·BSC 案报告里"当前持仓分布"图被用户误读:最高蓝柱是"地址数最多"的档(1,557 个空投残留地址,合计仅 0.05% 净供应),被看成大筹码档。根因=`scripts/report/holder_distribution_scan.py` 的 `write_png`(约 :732)是手写裸 PNG(zlib 逐像素,灰底+蓝柱 800×420),零文字渲染能力,画不出轴/刻度/标题/图例。本工单把它升级为 matplotlib 双轴中文图。**只动图,不动任何判定逻辑、不动 scan JSON 的内容与 schema。**

## 工单五栏

**1. 不变量(逐条,违反任一即返工)**
- `write_png(path: Path, scan: dict) -> None` 签名不变;唯一调用行 `atomic_json(out, scan); write_png(chart, scan)`(约 :896)逐字不动。
- 三个 PNG 路径字面量逐字不动:`charts/distribution_stage1.png`(scan_output_paths initial 分支)、`holder_distribution_round.png`(final 分支与 record-round 推导处)、`charts/final/holder_distribution_current.png`(record-round)。
- `scan_output_paths`、`record-round`(cmd_record_round)、`analyze`、`validate_scan`、`semantic_payload` 及一切判定/校验代码零改动。
- 任何 scan 输入(**包括无 `base_bins` 键的 low_sample 形态**)不得抛异常;只写 `path` 这一个文件;不得修改 `scan` 对象;scan JSON 产出逐字节不变。
- 不新增 payload 字段、不新增模块顶层第三方 import(matplotlib 相关 import 必须在函数体内)。

**2. 消费面清单(只动态消费本图,全部声明不动)**
record-round 把轮次图拷到 charts/final(路径由 scan 路径推导,**不消费 --chart 参数**);a5_report_seal.py 动态记录 final 图 size/sha 并重验;build_html.py G10/G11 重哈希内嵌;audit_release_gate.py 函数内 import 本模块;现役全链测试 5 处(test_distribution_gate.py 的 99-owner low_sample、test_a4_gate.py 的 final→record-round→A5、test_repair_batch_c.py ×1、test_repair_batch_d.py ×2)——它们的夹具是 owner 极少的 low_sample 案,**新实现必须让它们全绿**。

**3. 三件套测试**(新建 `scripts/tests/test_distribution_chart.py`,风格仿 test_distribution_gate.py 的 check() 模式;并在 `scripts/tests/run_all.py` 登记一行 → SUITE 139→140)
- **先红后绿(原反例)**:(a) `_chart_series` 语义断言:bars 序列==各 bin owner_count、expected 序列==各 bin expected_owner_count、right_pct==raw_balance/net_supply_raw×100(**零值档保留在序列里,不得删点**)、x 刻度位置符合对数换算式(见规格)、标题含 stage(final 时含轮次);(b) 渲染产物为合法 PNG(PIL `Image.open(...).verify()`)且像素尺寸 1800×840。——旧实现无 `_chart_series` 且 800×420,天然红;施工时先在基线跑红留证,再修绿。
- **同族变体**:initial 与 final 各按**标准生产路径**产图(final 必须走真实 `--stage final --round 1` + `record-round` 拷贝链,**禁用 --chart 自定义路径冒充**);low_sample 夹具(无 base_bins)→ mode=="low_sample"、note 文案含 "low_sample"、渲染不抛异常且产合法 PNG。
- **失败分支**:**子进程隔离**(subprocess 起新 python,先向 `sys.modules` 塞 `matplotlib=None` 毒丸,再 import 本模块调 write_png 喂正常 bins 夹具),断言**显式失败**(非零退出/异常),不产任何降级图。禁止在测试主进程塞毒丸(会污染其他测试的 matplotlib 缓存)。

**4. 新建代码自审(done.md 里逐条回填)**
matplotlib/chart_style import 未上移到模块顶层;未新增 payload 字段;未触碰三个路径字面量与调用行;figure 在异常路径也被 close(用 try/finally 或确保 close 在必经路径);无任何 `1e18`/decimals 类换算字面量(横轴是 %,与代币小数位无关);删除裸 PNG 代码后,孤儿 import `struct`、`zlib` 一并从 import 区删除(`shutil` 保留,record-round 在用)。

**5. 归因预判**
日后 −1 段/a5 环境崩=缺 matplotlib(requirements.lock 已含 matplotlib==3.11.0,env_check 三层守卫应先红);图数据错位=查 `_chart_series` 单测;测试套变慢=matplotlib 首次导入+字体缓存,预期内不修。

## 修复规格(按此施工,不得自行扩/缩范围)

### A. `_chart_series(scan: dict) -> dict`(新增,模块级私有,纯数据无渲染)

输入为 scan dict。可用字段:`base_bins`(list,每行 `{index, upper_private_pct, owner_count, expected_owner_count, raw_balance}`;low_sample 时**整个键缺失**)、`denominators.net_supply_raw`(str 整数)、`owner_count_private_main`(int,可能缺失)、`stage`("initial"/"final")、`round`(int,仅 final 有此键)、`not_evaluable_reason`。全部用 `.get` 防御取值。

返回 dict 契约:
```
{
  "mode": "normal" | "low_sample",
  "bars": [int, ...],          # 各 bin owner_count,按 index 序
  "expected": [float, ...],    # 各 bin expected_owner_count
  "right_pct": [float, ...],   # 各 bin int(raw_balance)/int(net_supply_raw)*100,零值保留
  "xticks": [{"pos": float, "label": str}, ...],
  "title": str,
  "note": str | None           # low_sample 说明文案,normal 为 None
}
```
- mode 判定:`base_bins` 缺失或空 → "low_sample"(bars/expected/right_pct 为空列表,xticks 空,note 见 C)。
- xticks(normal):v0=base_bins[0]["upper_private_pct"],r=base_bins[1]["upper_private_pct"]/v0(即 √2,从数据推,不写死);候选刻度=10 的整数幂(…1e-6, 1e-5, …, 100)中落在 [v0, 最末 bin upper] 区间者;每个刻度 v 的位置 `pos = log(v/v0)/log(r)`(柱画在 x=0..n-1,pos 落在同一坐标系);label 用纯文本 `f"{v:g}%"`(仓库惯例:chart_style.py docstring 明说对数刻度用 FuncFormatter 纯文本防上标乱码,这里同理不用 mathtext)。
- title:final 且有 round → `当前持仓分布(final·第{round}轮)——私人主桶 {owner_count_private_main:,} 址`;initial → `当前持仓分布(initial)——私人主桶 {N:,} 址`;owner_count_private_main 缺失时省略"——私人主桶"后缀。
- net_supply_raw 为 0/缺失的防御:right_pct 全 0(不除零)。

### B. `write_png(path, scan)` 重写(渲染层)

- 函数体内(非模块顶层):`from chart_style import setup`(chart_style 顶层已 `matplotlib.use("Agg")`,先 import 它保证 Agg 先于 pyplot),再 `import matplotlib.pyplot as plt`。**ImportError 自然抛出**=显式失败,不做静默降级、不做整体 try/except 吞异常(绘图 bug 不得洗成成功)。
- 惯例四件套(仿 standard_charts.py):`setup()` → `fig, ax = plt.subplots(figsize=(12, 5.6))` → 末尾 `fig.tight_layout()`、`fig.savefig(path, dpi=150)`、`plt.close(fig)`(close 放 try/finally 保证异常路径也关)。`path.parent.mkdir(parents=True, exist_ok=True)` 保留。
- normal 模式:
  - 左轴:柱 `ax.bar(range(n), bars, color="#3570b5", width=0.92)`,ylabel `地址数`;
  - 左轴期望线:`ax.stairs(expected, edges=[i-0.5 for i in range(n+1)]化为数组, ...)` 灰色虚线(baseline=None 只画顶线),图例名 `拟合期望人数(泊松零假设 λ,形态闸基线)`;
  - 右轴:`ax2 = ax.twinx()`,橙色折线经过全部点(含零),marker 只画正值(散点叠加 `right_pct>0` 的点),ylabel `该档合计持币占净供应 %`,线性刻度,底为 0;
  - 横轴:`ax.set_xticks([t.pos], [t.label])`,xlabel `单地址持仓占私人可入箱供应 %(对数分箱,每格 ×√2)`;
  - `ax.set_title(series["title"])`;图例含三元素(柱/期望线/右轴线,右轴线并入同一图例框)。
- low_sample 模式:单轴空白(不画右轴、不画常规图例),`ax.text(0.5, 0.5, note, ha="center", va="center", transform=ax.transAxes)` 居中说明,标题照常;note 文案=`私人主桶 {N:,} 址,低于形态闸样本门槛;形态统计未运行(low_sample)`(N 缺失时=`形态统计未运行(low_sample)`)。
- 删除:旧裸 PNG 全部代码(chunk/IHDR/IDAT 逻辑)与 import 区的 `struct`、`zlib`。

### C. 文档与版本记账(与代码同批)

- `VERSION`:6.52.15 → **6.53.0**;`pyproject.toml` `[project]` version 行同步;`SKILL.md` 第 23 行 skill-version 注释同步。
- `CHANGELOG.md` 双写:①版本索引节顶部加一行 `- **6.53.0**(2026-08-27)持仓分布图升级为 matplotlib 双轴带标签图…`(一行概括:哑图根因/横轴 %/取消裸 PNG/SUITE 140);②详情段 `## [6.53.0] - 2026-08-27 — …` 六栏(**出处与根因 / 设计与实现 / 消费面与防回流 / 测试 / 盲审与验收 / 成本-质量指标**);"盲审与验收"栏如实写:免两轮盲审(小改裁量),以 @CX 施工前计划复核+codex 施工后盲审+Fable 独立验收替代;版本位按书面规则升次版本(生产行为改变+复盘驱动)。
- 写入前跑 `python3 scripts/tests/changelog_lint.py` 确认无撞号/倒排。

### 测试与证据纪律(无 commit 模式)

1. 先在基线跑新测试留**红**证据(输出摘录存 `maintenance/repair-20260827-distchart-axes/red_evidence.md`);
2. 施工后同测试转**绿**,证据追加同文件;
3. `python3 scripts/tests/run_all.py` 全家桶 **140 项全绿**,输出尾部摘录存 done.md;
4. 完工报告 `maintenance/repair-20260827-distchart-axes/done.md`:改动清单(文件+函数级)、五栏第 4 项自审逐条回填、run_all 摘录、遗留说明。

## 白名单(全集,越界停工)

- `scripts/report/holder_distribution_scan.py` — 仅:write_png 重写+新增 _chart_series+删裸 PNG 代码与孤儿 import(struct/zlib)
- `scripts/tests/test_distribution_chart.py` — 新建
- `scripts/tests/run_all.py` — 仅登记一行
- `maintenance/repair-20260827-distchart-axes/` — red_evidence.md / done.md;另含 workorder.md 本文件(规格方产物,随批入库,施工方不得改动)
- `VERSION`、`pyproject.toml`(仅 version 行)、`SKILL.md`(仅 :23 版本注释)、`CHANGELOG.md`(索引一行+详情一段)

禁区:上列之外一切文件;a5_report_seal.py、build_html.py、references/**、scripts/report/ 其他脚本、任何案目录(尤其 /Users/uravvv/Documents/5.6筹码分析/**);git 一切写操作。

## 完工标准

- [ ] 新测试三件套:红证据在档 → 全绿
- [ ] run_all 140/140 全绿(含既有 5 处全链测试、test_version_consistency、changelog_lint 相关入口)
- [ ] 五栏第 1 条不变量逐条自查通过并回填 done.md
- [ ] 版本五处一致(VERSION/pyproject/SKILL.md:23/CHANGELOG 索引行/CHANGELOG 详情段)
- [ ] git status 显示的改动文件 ⊆ 白名单
