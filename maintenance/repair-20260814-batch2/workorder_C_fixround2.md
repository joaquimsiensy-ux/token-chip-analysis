# 工单 C 消化轮 2：盲审二轮 REOPEN（轻度）五项小修

> 输入＝blindreview_C_round2.md（同目录）。消化循环纪律：≤3 轮，本轮为第 2 轮（预算内最后一轮）。
> 裁判裁决：N-01/N-02 必修（缺陷），N-03/N-04/N-05 补锚与等深（随修），N-06 的 staging importer 重跑由裁判在验收环节执行（同上轮刷新模式），N-07/N-08 无需动作。
> 施工纪律同前：**禁一切 git 写命令**；完成后写 `workorder_C_fixround2_done.md`（逐项处置＋红→绿双跑＋自审）。
> 边界：只动 camp_series_provenance.py / replay_edges.py / audit_release_gate.py（load_json 相关行＋series 段，点名行号）/ test_repair_batch_c.py；工单 A/B 资产勿碰（supply_truth_gate.py、shared_release_receipt.py、adversarial_review_runner.py、a4_gate.py、test_repair_batch_a.py、test_repair_batch2_f02.py——SHA 自证与 HEAD 一致）；state_from_facts.py/import_pythia_legacy.py 本轮预计无需改动，若确需改在完工记录点名理由；staging-pythia/ 与 PYTHIA 案根禁触碰。

## 修复清单

### 1. N-01（缺陷）边文件闸拒 symlink，两侧等深

consumer 边实物闸与 producer 侧边文件打开处均补 `is_symlink()` 拒绝（与同文件 `_resolve_ref`/importer 的既定口径等深）。测试锚：边文件换 symlink（指向案外同内容实物，size/sha 均对）→ consumer 编译点拒＋producer reconcile 拒（盲审 E1 转红）；hard link 照常过（importer 设计依赖，防误伤）。

### 2. N-02（缺陷）发布点物理 sha 接线守卫（BC-04 同型）

为"发布点调用 `check_series_binding`/registry_anchor_check 时确实传了 `verify_edge_physical_sha=True`"加接线锚——照 BC-04 直调负向锚模式：构造"边文件同 size 内容篡改"案，直接走发布点入口（audit_release_gate 的 series 检查路径）必拒；该场景只有物理 sha 重算能拦，接线被删即红（盲审 n08 转红）。

### 3. N-03/N-04（假覆盖）三条负向锚

- 编译点 `edge_file_size` 对锚：meta 登记 size 与实物不符（内容同、登记错）→ 编译点拒；
- `edge_file_sha256` 形态：meta 登记非小写 hex/长度错 → 拒；
- producer 侧 `parse_constant`：对 producer 的正式解析路径注入 NaN JSON → rc=2（挂载点摘掉即红，照工单 A R-02 模式）。
（盲审 n06/n15/n13 转红；组合 c4 转红。）

### 4. N-05（观察随修）audit_release_gate 主入口 JSON 等深

`audit_release_gate.py:109` 通用 `load_json` 与 :758 裸 `json.loads` 换成带 `parse_constant` 拒绝器＋`RecursionError` 归类的入口（复用本文件/consumer 已有 loader，勿新造第三份）。配一条 NaN 注入锚（state 或 reconciliation_report 塞 NaN → 发布闸拒且错误语义为 JSON 非法而非逐点比对兜底）。

### 5. N-06 说明（裁判执行项，施工方不做）

staging importer 重跑由裁判在验收环节执行（import_pythia_legacy 全链：importer→reconcile→evolution→消费复算），验证 BC-O1 口径改动在真实案上闭合并刷新 migration_receipt 的 producer 指纹。完工记录无需涉及，此处仅为档案完整。

## 验收口径

裁判独立跑：symlink 边文件场景两侧拒；发布点接线场景拒；test_repair_batch_c.py rc=0（checks 上升如实报）；run_all 全绿；随后裁判重跑 staging importer 全链并复验（含 migration_receipt 新指纹）。消化轮闭合以盲审员 C 第三轮复核为准（≤3 轮预算此为最后一轮，三轮再 REOPEN 按纪律升格用户裁决）。
