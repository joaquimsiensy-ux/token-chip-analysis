# 批 2 版本收口工单：6.40.0 → 6.41.0（三线三轮盲审全 CLOSED 后的统一收尾）

> 前提：工单 A/B/C 均三轮盲审 CLOSED（blindreview_A_round2＋三轮 CLOSED 消息、blindreview_B_round3.md、blindreview_C_round3.md）。本单为批 2 最后一个施工单。
> 施工纪律：**禁一切 git 写命令**；完成后写 `workorder_final_closure_done.md`；输出 `WORKORDER_FINAL_CLOSURE_COMPLETE`。
> 本单解除对 supply_truth_gate.py 与 shared 保护切片的冻结（仅限下述 docstring/注释项，零行为变化——行为向量守卫与全量 suite 看护）；staging-pythia/ 与 PYTHIA 案根仍禁触碰。

## 清单

### 1. 版本收口

- `VERSION`（或版本事实源所在文件，rg 确认）6.40.0 → 6.41.0。
- `CHANGELOG.md` 新增 6.41.0 条目（批 2 总账，活口径）：F-10 waiver 三段分级硬顶＋over-cap-approval/v1（工单 A，三轮盲审：零宽→13 码位→正向白名单穷举闭合）；F-02 对抗复核结构化 v3＋finalize（工单 B，三轮：零宽击穿族→claim_id all 语义→对账键黑名单方向）；F-09 solana-reconcile v3 身份键＋PYTHIA 真实案端到端（工单 C，三轮：布尔精确判定族→16 假覆盖清零→symlink/接线锚）；已有的"AKE/B2/MOG/TAG 四案 v2 待 6.41.0 汇总"登记句并入本条目正文。
- R10 台账状态同步（rg 定位台账所在文件——final_acceptance.md 或其后继）：批 2 清账 R10-2/R10-10/R10-11/R10-12；新增登记项（源自三线盲审，逐条注明出处）：B-09 blocker 存在性自报（待用户裁）、any 语义"证据够不够"阈值、risk_flags 黑名单版存量（批 4）、BC-O2 迁移身份消费者、BC-O3 series binding 仅 new-analysis profile、BC-O4 sidecar producer 无锚、BC-O7 hard link 不可辨（接受在案）、B 三轮 R-1 组合符语义窄口（文档已补）、C 三轮 O-1 目录级 symlink 全库口径（跨工单面）、O-3 symlink 退出码两路、O-4 a4_gate/a5_report_seal 裸 json.loads 同族面、emoji 白名单扩容候选（A 三轮误伤评估）。

### 2. docstring 豁免项补齐（冻结解除，零行为变化）

- `scripts/lib/supply_truth_gate.py` 与 `scripts/report/shared_release_receipt.py` 两份 `_meaningful_text` docstring：补白名单语种覆盖清单一句＋"两侧刻意双写（独立重验纪律），改动须两处同步并过行为向量守卫"一句。
- 自证：两文件除 docstring 行外 diff 为空；test_repair_batch_a.py 44/44（行为向量守卫）；改后 shared 保护切片新 SHA 在完工记录留档（基线自此更新）。

### 3. 文档三处（B 三轮 R-1＋A 三轮误伤）

- `scripts/report/a4_gate.py` 对账键注释改口："移除已知零渲染点名集＋Cf/Cc/Zl/Zp/Mn/Me 全类（后者含可见组合符，属刻意取舍——项目语料中英日韩拉丁 NFC 后零撞键）"，删除"only known zero-rendering"不实表述。
- `references/independent-audit-protocol.md` 加一句：命题文本不得依赖泰文/阿拉伯文/天城文/藏文/希伯来文的附加符（组合符）承载语义差异（对账键会移除它们）。
- `references/analyze-workflow.md` 超顶特批段（A2）加一句：用户批复必须含文字（中英文等白名单语种），纯表情符号不构成有效批复文本。

### 4. 两条一行级修复＋锚（B 三轮 R-2/R-3，盲审员定性"一行可修"）

- **R-2**：completeness_critic 挂 entrypoint 语义锚——(role, entrypoint sha) 去重扩到全部角色（或等价：critic 恰好 1 路，协议本写"＋1 完整性批评"，二选一取更简者）；锚测试＝同一 critic entrypoint 跑 3 次 → finalize 与消费侧双拒（盲审场景 reviews=4 转红）。
- **R-3**：`remove_any` 的 rmtree 加 onexc 处理（先补权限再删）或删除失败时保留原始 BLOCK 错误语义（异常链不吞 verdict）；锚测试＝staging 目录 chmod 0o500 场景 → rc=2 且零残留且错误信息含原始拒绝理由。
- **O-2（C 三轮，同型顺手）**：`check_reproduce_receipt` 的 load_json 调用点接线锚一条（reproduce output 塞 NaN → 拒，接线删除即红）。

### 5. B-16 元教训入 casebook

rg 定位 casebook 分册（references/ 下判例库），新增一条：**字符过滤的黑白名单方向由漏网后果决定**——实义判定漏网＝放行（fail-open）须白名单收严；对账/规范化键漏网＝视觉同文判不同＝误报失败（fail-closed）应黑名单保全。同一字符分类工具在两个场景安全方向相反；本批 B-16 回归即"一张白名单办两件事"所致。注明案例出处（repair-20260814-batch2 工单 B 消化轮 2）。

### 6. 最终整体验收（不拿"每步各自过了"凑数）

- `python3 scripts/tests/run_all.py` 全量（获准环境）rc=0，**记录本次套件项数与业务断言数作为 6.41.0 冻结基线**（写进完工记录与 CHANGELOG 条目）。
- `invariant_scan.py` census 数字留档。
- `docs_lint.py --all`、`git diff --check` 干净。
- 三线保护面终态 SHA 清单留档（供合并前最后核对）。

## 验收口径

裁判独立跑：run_all 全绿＋抽验 R-2/R-3/O-2 三锚场景＋docstring diff 纯注释自证；随后裁判执行最终合并（squash 或直并按既定）→ main → push。
