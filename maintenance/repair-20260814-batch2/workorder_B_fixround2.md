# 工单 B 消化轮 2：盲审二轮 REOPEN 四项处置（B-16 回归为 P0）

> 输入＝blindreview_B_round2.md（同目录）。消化循环纪律：≤3 轮，本轮为第 2 轮（最后一轮预算内）。
> 裁判裁决：B-16 必修（P0，回归击穿——根因在裁判 amendment 的"白名单减法做对账键"裁决，本轮更正裁决）、B-17/B-18 必修（P1）、B-19 修文档＋边界（P2）；两条观察登记。
> 施工纪律同前：**禁一切 git 写命令**；完成后写 `workorder_B_fixround2_done.md`（逐项处置＋红→绿双跑＋自审）。
> 边界：同消化轮 1——supply_truth_gate.py 只 import 不改；shared 的 waiver/approval 保护切片勿碰（SHA 自证）；工单 C 文件勿碰（**注意工单 C 消化轮 1 可能已在 HEAD 里改过 camp_series_provenance.py 等——以派单时 HEAD 为基线，那些文件同样禁碰**）；staging-pythia/ 与 PYTHIA 案根禁触碰。

## 修复清单

### 1. B-16（P0·回归击穿）对账比较键换黑名单方向

**裁决更正**：amendment 里"比较键保留白名单字符与空格、其余移除"的减法方案作废——白名单外还有大量实义字符（≥/≤/↑/↓/≈/≠/希腊字母/其他语种），减法把语义差异抹掉＝对账闸对笔误失明（fail-open）。

新方案（黑名单方向，漏网倒向 fail-closed）：`a4_gate` 对账正文比较键构造改为——
1. `unicodedata.normalize("NFC", text)` 归一（把组合序列并入基字符，防 NFD 形式被下一步误伤）；
2. 移除 category ∈ {Cf, Cc, Zl, Zp} 的字符＋显式零渲染点名集（U+3164/U+115F/U+1160/U+FFA0/U+2800——Lo/So 类填充符，类别删不到的已知点）；NFC 后仍残留的孤立 Mn/Me（无基字符附着）一并移除；
3. Zs 类全部折叠为普通空格；
4. `" ".join(split())`。
其余一切字符（箭头/数学符/任意语种/emoji）**原样保留进比较键**。
原理注释写清楚：实义判定用白名单（漏网=放行故须收严）、对账键用黑名单（漏网=视觉同文判不同=对账报错人来查，安全方向），两者不是同一张表——这是本轮回归的根因，注释防复发。

测试锚（先红——现行白名单减法版对这些必须先红）：
- `净流入 ≥ 10%` vs `净流入 ≤ 10%` → 比较键不同（对账应报不一致）；
- `持仓 ↑` vs `持仓 ↓`、`误差 ≈ 0` vs `误差 ≠ 0` 同族；
- 俄文承载的"已确认" vs "已推翻"两版本 → 键不同；
- 零渲染回归：正文含 U+0591（NFC 后孤立）/U+200B/U+3164 与不含的版本 → 键相同（规范化仍生效）；
- á 的 NFC/NFD 两种形式 → 键相同（归一生效）；
- 端到端：`check_audit_registry_alignment` 对"一份 ≥ 一份 ≤"的双 registry 必须 fails 非空。

claim_id（all 语义）不在本条范围——id 合法性已由白名单 all 语义把关，符号进不了 id，维持消化轮 1 方案。

### 2. B-17（P1）路数去重换语义锚

现锚=字节 sha 集合，重排版副本（indent 变化）两 sha 都变即绕。改法：保留现有 sha 去重（挡逐字节副本零成本），**新增语义锚**——finalize 与消费侧双双校验：claim-review 路的 `(role, entrypoint 实物 sha256)` 二元组不得重复（同一审查脚本以同一角色出现两次＝无增量价值的复读，拒；两个不同 entrypoint 真跑两遍＝合规多路，过）。critic 路本就单份（角色必备约束已在）。

测试锚：盲审 N1（重排版副本注水）→ finalize 拒＋消费侧拒；盲审 N2（两个不同 entrypoint 真 2 路）→ 照常过（防误伤绿例）；同 entrypoint 同 role 真跑两遍 → 拒。

### 3. B-18（P1）staging 清理 lexists 兜底

形态分派改兜底式：`os.path.lexists(p)` 为真 → `is_dir() and not is_symlink()` 走 `shutil.rmtree`，其余（file/symlink/FIFO/socket/任何未来形态）走 `unlink`。receipt tmp 清理同改。

测试锚：FIFO 场景 → rc=2 且零残留（盲审 N3 转红）；目录/symlink/socket 回归保持。

### 4. B-19（P2）文档口径与 id 边界

- `references/analyze-workflow.md` 与 `references/independent-audit-protocol.md` 的"含实义字符（不可见字符不算）"表述改准：写明白名单覆盖面（ASCII 可打印/拉丁补充与扩展/通用标点段/CJK/假名/韩文音节/全角段），**不在覆盖面的语种（俄文/阿拉伯文等）与纯 emoji 文本会被拒**——证据/批复须含至少一个覆盖面内字符（中英文工作流零影响；外语原文证据建议附一行中文说明或保留 URL/数字即可通过）；
- 两侧 `_meaningful_text` docstring 补覆盖语种清单一句＋"两侧刻意双写（独立重验纪律），改动必须两处同步并跑行为向量守卫"一句（回应盲审"双写还是单源"观察）；
- claim_id 不得含空格明示进文档（协议 blockers/claims 结构段）；仓库内 fixtures 扫一遍确认无 `A4 01` 形含空格 id（存量案在案根不受本仓库约束，文档写明存量案重跑时如遇此形 id 须先改 registry）。

### 5. 登记不修（完工记录"发现未修"节，留 R10 台账）

- any 语义固有边界（`零宽×2000＋单可见字符`放行）——"证据够不够"属策略阈值决定，与 evidence="-" 同口径待裁；
- B-09/B-15/risk_flags 维持消化轮 1 登记。

## 验收口径

裁判独立跑：B-16 六符号对场景（≥/≤、↑/↓、≈/≠）修后对账键必不同、零渲染/NFC 归一场景键相同；FIFO 零残留；重排版注水拒＋真 2 路过；test_repair_batch2_f02.py rc=0；test_repair_batch_a.py rc=0；test_a4_gate.py rc=0；run_all 全绿。消化轮闭合以盲审员 B 第三轮复核为准（≤3 轮预算此为最后一轮，若三轮再 REOPEN 按纪律升格用户裁决）。
