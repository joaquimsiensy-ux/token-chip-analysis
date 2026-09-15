<!-- 由 Fable 从 codex 只读盲审任务 task-mu2vc405-ewdr62 的最终报告正文原样搬运 -->
# 盲审 R3:FAIL

**发现 1 项 blocker：R3 已落实双向舍入界，但“四项精确不变”中的①逐笔短缺数量、③非 gap/residual 构成 raw，仍被实际内存重放反证。F1 不能关闭。**

完整逐项报告及全部只读复现命令已打印到 stdout。全程离线、未修改文件；审查前后 **1120 个仓库文件及四份账本的 SHA-256 均未变化**。

## 逐项结论

第 2、5 项属于同一个 blocker。

| 核对项 | 结果 | severity | 结论 |
|---|---|---|---|
| 1. 生产文件哈希 | PASS | none | 精确等于指定的 `e85acee4…eda3cd1` |
| 2. T4 通用不变量 | **FAIL** | **blocker** | 实现与裁决一致，旧通用上下界已删除；但①、③的精确承诺存在反例 |
| 3. T4-mixed-b | PASS | none | 两锚点三策略 Δ 为 **−128／0／+1**，库存及闭合值匹配 |
| 4. T4-stress | PASS | none | 实际重放全部 200 组；max\|Δ\|=788，出现 2 次，负差 360、正差 270、零差 570，超界 0；常数未放宽 |
| 5. 文档承诺 | **FAIL** | **blocker** | 三处旧措辞已清理，新表述符合裁决并注明双向；但①、③仍是不成立的保证 |
| 6. APU/PYTHIA | PASS | none | 全量核对 **224 锚点、666 组策略明细**，Δ 全为 0，回归表与账本一致 |
| 7. 断言、范围、日志 | PASS | none | 原始 69 处 check 全保留；仅授权替换两处旧界。六个既有文件变化、28 个允许新增，无越界；七项退出码及日志哈希匹配 |

## Blocker：两个四笔交易反例

位置：[CHANGELOG.md:92](/Users/uravvv/.claude/skills/token-chip-analysis/CHANGELOG.md:92)、[scan-schemas.md:329](/Users/uravvv/.claude/skills/token-chip-analysis/references/scan-schemas.md:329)、[T4 比较器:266](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_entity_source_trace.py:266)。

令 `H=2^60`，供应量 `S=10·2^90`，`Z` 为零地址，全部边同日且顺序精确。

### A：非 gap/residual 来源改变

```text
X → A  H
Z → A  H
X → A  257
A → D  H
```

完整 `trace_entity()` 内存重放结果：

| 主策略字段 | 7.0.3 | 7.0.4 |
|---|---:|---:|
| mint raw | 576460752303423488 | 576460752303423360 |
| stock_raw | 1152921504606846976 | 1152921504606846976 |
| 闭合 pct | 100.0 | 100.0 |

**mint 减少 128 raw，推翻③。** 当前 T4 比较器实际报 **4 条 FAIL**：current/peak 的主构成及 pro_rata 明细检查。Δ=−128，舍入界通过。

### B：逐笔短缺改变

保留前三笔，第四笔改为：

```text
A → D  2H+512
```

该笔 `take()` 返回的 pro_rata 短缺为：

| 7.0.3 | 7.0.4 |
|---:|---:|
| 512 | 0 |

**推翻①。** 当前 T4 比较器实际报 **1 条 FAIL**。两版库存相同、闭合均为 100.0；Δ=−511，舍入界仍通过。

原因是拆桶改变浮点求和次序，影响可用余额及比例扣减系数。压力测试中的 74 组 mint 都直接进入 D，没有进入 A 参与混合扣减，因此未覆盖上述路径。

## 独立抽查结果

压力样本两锚点结果一致：

| case | n | pro_rata Δ | fifo Δ | lifo Δ |
|---|---:|---:|---:|---:|
| 0 | 8 | +96 | 0 | −126 |
| 1，含 mint | 8 | −6 | −14 | 0 |
| 74 | 4 | +344 | +347 | 0 |
| 101 | 8 | −788 | −672 | −719 |
| 199 | 6 | 0 | 0 | 0 |

账本抽查：

| 锚点 | gap703 | gap704 | residual704 | Δ |
|---|---:|---:|---:|---:|
| APU TE-01 current | 304489068582 | 0 | 304489068582 | 0 |
| APU TE-03 peak | 2542235651 | 0 | 2542235651 | 0 |
| PYTHIA e_lp current | 6827586 | 6827586 | 0 | 0 |

**总结论：FAIL——1 项 blocker；双向界及施工证据通过，但逐笔短缺和非 gap/residual raw 的精确不变承诺被反例推翻，F1 不能关闭。**
