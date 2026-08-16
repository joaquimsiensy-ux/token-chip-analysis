# 工单 A 消化轮 2：盲审第二轮 REOPEN 五项处置

> 输入＝blindreview_A_round2.md（同目录）。消化循环纪律：≤3 轮，本轮为第 2 轮。
> 裁判裁决：R-01/R-02/R-03 必修（1 击穿＋2 缺陷），R-05 随 R-01 同修，R-04 半修半登记。
> 施工纪律同前：**禁一切 git 写命令**（add/commit/checkout/reset/restore/stash 均禁，只读 status/diff/log 可用）；完成后写 `workorder_A_fixround2_done.md`（逐项处置＋红→绿双跑＋自审）。
> 边界：勿碰 `shared_release_receipt.py` 的 `validate_adversarial_review` 段（工单 B 资产，修前修后 SHA 一致自证）；勿碰工单 C 的文件（camp_series_provenance.py / replay_edges.py / state_from_facts.py / audit_release_gate.py / test_repair_batch_c.py / invariant_manifest.json 的 solana-reconcile 段 / scan-schemas.md / .gitignore / test_review_resume_integrity.py）——若消化轮改动确需触及 invariant_manifest.json，只改 waiver/approval 相关行并在完工记录点名。

## 修复清单

### 1. R-01（击穿）`_meaningful_text` 判据翻转：黑名单 → 正向白名单

现判据"字符 category 不在 {Cf,Cc,Zs,Zl,Zp}"漏掉 Lo/So/Mn/Co/Cn 里的零渲染码位（U+3164 HANGUL FILLER、U+2800 BRAILLE BLANK、U+115F、U+FFA0、孤立组合符 U+0301/U+034F、私用区 U+E000、未分配 U+0378 等 13 个实测击穿）。**不要往黑名单里补类别**——Cn/Co 整区都是零宽候选且随 Unicode 版本漂移，枚举挡不住。

改法（方向，细节自定）：判据翻转为"**至少含一个确定可渲染字符**"。定义正向白名单区间集合，字符串必须至少含一个落在其中的字符才算有实义；白名单外字符允许共存（不误伤 emoji 等），但不能独自撑起实义性。白名单建议覆盖（按本工程用户实际书写面）：
- ASCII 可打印区（0x21–0x7E，注意**排除空格**——空格本就非实义）
- CJK 统一表意文字基本区＋扩展 A（U+4E00–9FFF、3400–4DBF）
- CJK 标点（U+3001–303F 中**排除 U+3000 全角空格**）、全角形式区可打印段（U+FF01–FF5E）
- 平假名/片假名（U+3041–30FF，**排除 U+3164 所在的 Hangul Compatibility Jamo 区 U+3130–318F——注意该区与假名区不重叠，列出只为提醒勿手滑并入**）
- 韩文音节区（U+AC00–D7A3；兼容字母区 U+3130–318F 与 Choseong filler 区**不入**白名单）
- 通用标点区可打印段（U+2010–2027，排除 U+2028/2029 行分隔符）
- 拉丁补充/扩展（U+00A1–024F 中排除 U+00AD 软连字符）
（可按此思路增删，原则：**每个入选区间人工确认无零渲染码位**；盲文区 U+2800–28FF 整区不入——U+2800 是空白，真盲文批复场景不存在。）

生产/消费两侧独立同名实现（沿用两侧独立纪律），黑名单层可以保留作为注释说明但判定以正向白名单为准。

测试锚：盲审 13 个残留码位逐个 × approval 四字段/waiver 两字段 × 两侧全拒（端到端至少抽 U+3164/U+2800 各一组全链）；混合串族——`"​ㅤ"` 拒、`"ㅤㅤ"` 拒、`"á"` **放行**（含可见 a）、20 个 U+2800 拒、三个 U+200B 拒；正常中英文（含前后空格）、纯中文、纯韩文音节（如 "승인"）放行防误伤。

### 2. R-02（缺陷）四个 parse_constant 挂载点各自独立锚

现锚只测 `_reject_constant` 函数本身；盲审注入实测：生产侧 waiver/approval、消费侧 waiver/approval 四个解析点的 `parse_constant=` 逐个乃至全部摘掉，38/38 仍全绿。

改法：新增挂载点锚测试——对四条真实解析路径（不是直调函数）各自注入含 `NaN` 的 JSON 原文，断言各自的拒绝出口触发（生产侧 TolerancePolicyError/exit 2、消费侧 ValueError）。要求：**摘掉任一挂载点该锚即红**（施工时先做一次破坏性自证：临时摘一个挂载点确认对应锚红，恢复后全绿；自证过程写进完工记录，不留在代码里）。盲审的注入 c/c2/c3/c4/c5 五场景修后全部转红。

### 3. R-03（缺陷）evidence 独立性从路径身份改内容身份

现检查 `approval_path in evidence_paths`（Path 相等）被三种写法绕过：硬链接指 approval、硬链接指 replay_stats（**存量 F-E 防线同样被绕**）、逐字节 `cp` 副本换名。

改法：独立性判定改为**内容身份**——evidence 实物的 sha256 等于 over-cap approval 实物 sha256 即拒；等于 replay_stats 实物 sha256 即拒（存量 F-E 同族同深收口，同一改法覆盖）。两侧等深。路径相等检查可保留为快捷层但不得是唯一层。

测试锚：硬链接指 approval／硬链接指 replay_stats／逐字节副本指 approval 三场景两侧全拒；正常独立 evidence（内容不同的真实文件）放行防误伤。

### 4. R-04（观察·半修）evidence 最低内容要求

实测 0 字节空文件、纯不可见字符文件冒充 evidence 全放行。本轮只做低误伤收口：
- **size > 0 硬性**（空文件拒），两侧；
- 文件内容可作 UTF-8 解码的 → 须含实义字符（复用 R-01 修后的 `_meaningful_text`）；解码失败（二进制，如截图/PDF）→ 仅要求非空，不做内容判定（防误伤二进制证据）。

测试锚：空文件拒、纯 U+200B 文件拒、纯 U+3164 文件拒、正常文本 evidence 过、伪二进制（含 0x00 的非 UTF-8 字节串）过。
更深的"evidence 内容语义真实性"超出机器可验范围，在完工记录"发现未修"节登记一句，留 R10 台账待裁。

### 5. R-05（观察·随 R-01）行为向量守卫扩容

`test_fixround_fa10` 的 `_meaningful_text` 行为向量集扩入盲审 13 个残留码位＋上述混合串族，保证两侧对新判据逐向量一致。

## 验收口径

裁判独立跑：盲审击穿复现场景（U+3164/U+2800 approval 四字段端到端、硬链接/副本三场景）修后全拒；test_repair_batch_a.py rc=0；run_all 全绿；工单 B 段 SHA 修前后一致。消化轮闭合以盲审员第三轮复核为准。
