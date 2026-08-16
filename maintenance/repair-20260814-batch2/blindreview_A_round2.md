# 工单 A 消化轮 1 盲审复核报告（第二轮，对 5150d9c）——判定 REOPEN

> 入档件。盲审员（opus 子代理）基于干净快照 `git archive 5150d9c` 复核消化轮 1 的 10 项修复。
> 判定：**REOPEN**——7 项完全闭合、1 项修了一半（F-A5）、2 项残留（F-A1/F-A9），另 2 项新观察。
> 裁判（Fable）处置：见同目录 `workorder_A_fixround2.md`。

## 逐项复核结论

| 项 | 状态 | 依据 |
|---|---|---|
| ① F-A1 零宽字符 | **残留** | 点名三码位闭合，排除集外 13 个不可见码位仍放行 |
| ② F-A2 巨整数/深嵌套 | ✅ 闭合 | exit=2 + 作废归档=1 + 现役收据清空，两侧 |
| ③ F-A3 三值主闸锚 | ✅ 真实 | 注入后定向测试转红 |
| ③ F-A4 第四值锚 | ✅ 真实 | 注入后定向测试转红 |
| ③ F-A5 NaN 双防线锚 | **修了一半** | `_finite_number` 有锚；`parse_constant` 四个挂载点全摘掉仍 38/38 全绿 |
| ④ F-A7 有效期 | ✅ 闭合 | 29/30 天过，31 天与 9999 年拒，两侧 |
| ⑤ F-A8 inputs 绑定 | ✅ 闭合 | 生产侧写入；摘条目、指别处，消费侧均拒 |
| ⑥ F-A9 evidence 兼任 | **残留** | 直白写法闭合，硬链接/逐字节副本可绕 |
| ⑦ F-A10 行为向量守卫 | ✅ 在场 | 逐向量比对两侧三函数（但向量集不含残留码位） |

## R-01【残留·击穿级】`_meaningful_text` 的排除集 ≠"视觉不可见"集

修复用 `unicodedata.category not in {"Cf","Cc","Zs","Zl","Zp"}` 判实义。工单点名的 U+200B/U+FEFF/U+2060 都是 Cf，确实闭合。但渲染为空白的字符不止这五类，实测 13 个视觉不可见码位通过判定：

```
U+3164 HANGUL FILLER               cat=Lo  meaningful=True
U+2800 BRAILLE PATTERN BLANK       cat=So  meaningful=True
U+115F HANGUL CHOSEONG FILLER      cat=Lo  meaningful=True
U+FFA0 HALFWIDTH HANGUL FILLER     cat=Lo  meaningful=True
U+0301 COMBINING ACUTE ACCENT      cat=Mn  meaningful=True（孤立组合符）
U+034F COMBINING GRAPHEME JOINER   cat=Mn  meaningful=True
U+E000 PRIVATE USE                 cat=Co  meaningful=True
U+0378 UNASSIGNED                  cat=Cn  meaningful=True
（等共 13 个）
```

端到端击穿复现（approval 四字段全填该码位，偏差 9900bps）：U+3164/U+2800 × approval 四字段＝生产 rc=0 落 PASS 收据、消费放行；waiver approved_by/reason 同族同样放行。U+3164 与 U+2800 恰是网络上最常被用来伪造空白用户名的两个码位。

根因：把"不可见"当成了五个 Unicode 类别的并集，但 Lo/So/Mn/Co/Cn 里都有零渲染宽度字符。枚举黑名单挡不住（Cn 未分配区、Co 私用区全是零宽候选且随 Unicode 版本变动）。方向：判据从"不在这些类别里"翻转成"至少含一个已知可渲染字符"（正向集合）。

## R-02【残留·缺陷】F-A5 只给零件装锚，没给装配点装锚

`test_fixround_fa5` 直调 `_reject_constant` 与 `json.loads(..., parse_constant=...)`——测的是函数能不能拒 NaN，不是四个解析点有没有真挂上。破坏性注入实测：生产侧 waiver/approval、消费侧 waiver/approval 四个挂载点的 `parse_constant` 逐个摘掉、乃至四个一起摘掉，38/38 仍全绿——零独立锚。对照同批其余修复点的锚全部真实（摘掉即红）。

## R-03【新击穿·缺陷级】evidence 独立性比的是路径不是内容

F-A9 修复用 `Path` 相等比较（`approval_path in evidence_paths`）。三种绕法实测全放行：evidence 硬链接指 approval（inode 相同）、硬链接指 replay_stats（**存量 F-E 防线同样被绕**）、`cp` 逐字节副本换名指过去。根因：独立性是内容属性，检查建在路径身份上。方向：内容身份（sha256 比对），顺手把存量 F-E 面关到同一深度。

## R-04【观察】evidence 文件内容零校验

`evidence_refs` 只验 path/size/sha256 绑定不验内容。实测 0 字节空文件、只含一个 U+200B、只含一个 U+3164 的 evidence 文件全部放行。与 R-03 叠加后，"至少一份独立人工核对证据"实质只剩"案内存在一个被哈希绑定的文件"。既有设计面，本轮未触及，登记待裁。

## R-05【观察】F-A10 行为向量守卫的向量集不含残留码位

守卫在场且有效（两侧一致地放行 U+3164——36 码位逐一比对无分叉），但向量集只覆盖工单点名码位，发现不了 R-01。

## 已确认完全闭合的项（摘要）

- **F-A2**：10**400 生产 exit=2＋作废归档件=1＋现役收据清空；20 万层深嵌套同；消费侧拒。
- **F-A7**：29/30 天过、31 天与 9999 年拒，两侧。
- **F-A8**：inputs 三键在场；摘条目→`receipt inputs missing over_cap_approval`；指同内容别件→`does not bind waiver same file`。
- **F-A9 直白写法**：两侧拒 approval 兼任 evidence。
- **`_finite_number` 类型面新变体**：Decimal/Fraction/complex/bool 全 False；10**308 True、10**309 False（float 边界正确）。
- **Unicode 已闭合族**：Cf 族 9 码位、Zs/Zl/Cc 族全拒，两侧逐码位一致无分叉。

## 攻击清单规模

36 码位边界探测＋24 组端到端放行验证＋F-A2 重放 3＋有效期 4＋绑定 3＋兼任 2＋破坏性注入反证 17＋新变体 13＋类型变体 6。另：approval 顶层塞 `__proto__` 与 5000 字符超长键放行（顶层无 canonical 约束，观察级，Python 无原型污染面，不立项）。

## 仓库只读确认

盲审全程零 git 写命令，在 /private/tmp 临时快照上执行，工作区未触碰。（其"工作区有工单 B 残留未提交"的方法论提示经裁判核实为误判：test_repair_batch2_f02.py 已于 6da206b 入库；其所见为工单 C 施工中间态。）
