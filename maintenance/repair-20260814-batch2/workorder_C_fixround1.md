# 工单 C 消化轮 1：盲审 FAIL 处置（布尔判定击穿族＋假覆盖 16 项收口）

> 输入＝blindreview_C.md（同目录）。消化循环纪律：≤3 轮，本轮为第 1 轮。
> 裁判裁决：BC-01/02 击穿必修，BC-03~09 缺陷全修，BC-O1/O5/O6/O8 观察随修，BC-O2/O3/O4/O7 登记不修。
> 施工纪律同前：**禁一切 git 写命令**；完成后写 `workorder_C_fixround1_done.md`（逐项处置＋红→绿双跑＋自审）。
> 边界：只动工单 C 文件面（replay_edges.py / camp_series_provenance.py / state_from_facts.py / audit_release_gate.py 的 series 段 / test_repair_batch_c.py / import_pythia_legacy.py / scan-schemas.md / report-template.md 的 token 字段清单行）＋invariant_manifest.json 相关行；工单 A/B 资产（supply_truth_gate.py、shared_release_receipt.py、adversarial_review_runner.py、test_repair_batch_a.py、test_repair_batch2_f02.py）勿碰；staging-pythia/ 与 PYTHIA 历史案根禁触碰（本轮全部用夹具，不重跑真实案）。

## 修复清单

### 1. BC-01/BC-02（击穿）布尔与数值字段族改精确判定

- consumer `camp_series_provenance.py`：`if not receipt.get("gate_pass")` → 精确 `receipt.get("gate_pass") is not True` 语义（True 之外一切值拒，含 truthy 字符串/数字/列表）；同函数内与 evm-dict 分支等深。
- consumer 新增必验：`negative_balance_count == 0`（精确 int 0）、`snapshot_mismatch_count == 0`、`net_supply_raw` 在场且为非负 int——对账结论不再压在单一布尔上。
- producer `replay_edges.py`：`bool(snap_meta.get("closed"))` → `snap_meta.get("closed") is True`；`int(snap_meta.get("supply_raw", -1))` 默认值静默 → `supply_raw` 缺失显式拒（fail-closed，不走 -1）。
- **同族 rg**：`rg -n "if not \w+\.get\(|bool\(\w+\.get\(" scripts/solana scripts/lib scripts/report` 圈出收据/meta 布尔闸同型写法，逐个判断是否同族收口（普通 dict 取值不在此列，只看"闸判定"语义），完工记录列全处置。
- **测试锚（吸取 i25 教训——类型宽松零区分力）**：`"false"`/`"FAIL"`/`"0"`/`[false]`/`1`/`0.1` 六种 truthy-非 True 值 × gate_pass/closed 两字段 → 全拒；缺 supply_raw → 拒；mismatch_count=1 但 gate_pass 被涂 True → consumer 必验层拒。

### 2. BC-03（缺陷）净供给交叉去条件式跳过

`endpoint_reconcile` 的 `if net_registered is not None and …` → `net_supply_raw` 必须在场（缺失即拒），交叉必跑。测试：删字段场景 → 拒（盲审 N1 转红）。

### 3. BC-04/05/06（缺陷）假覆盖三重灾区补钉＋边实物最低闸

- **BC-04**：`expected_*` 任一为 None 时的拒绝分支补直调负向锚（不传身份直调 `registry_anchor_check` → 必拒；盲审 i10 注入转红）。
- **BC-05**：
  - 新闸：consumer 验边实物在场——`data/soltx-<sha256(mint)>.jsonl.gz` 必须存在且非空；meta 若登记 size/物理 sha 字段则对锚（v3 meta 缺这些字段的话，producer/importer 落 meta 时补写 `edge_file_size`＋`edge_file_sha256` 物理指纹，consumer 对锚 size 必验、物理 sha 在发布点必验/编译点可跳过重哈希以控成本——两点行为差异写进文档）；
  - 测试锚：删边文件本体 → 拒（盲审 D2 转红）；meta 摘要登记错值 → producer reconcile 必拒（i14 转红；该锚同时钉住 i19——producer 若改取自报，"登记错值"场景恒等自洽不再被拦，此锚即红）；
  - `references/scan-schemas.md:563` 措辞改准：补回旧版两条现存约束（gate_pass 为 true、终态快照合计=net_supply_raw——BC-O8），"边完整性"表述与实际强度相符（消费侧对锚 meta＋实物在场/size，不声称消费侧重放边内容）。
- **BC-06**：producer `snapshot_ok` 六项各配负向场景锚（closed 非 True/owner 对账 mismatch/supply 不符等，逐项破坏 → reconcile rc=2；盲审 i28 转红）。

### 4. 其余 12 项假覆盖注入逐个补负向场景测试

用参数化/循环写法控制膨胀，每项＝构造该闸独拦的坏输入 → 断言拒绝（闸被删则该场景测试红）：
i02 chain 错值（"ethereum" 的 sol-rows）、i04 window.to > 案 cutoff（meta 自洽变体）、i09 v2 分支区分力（v2 收据的错误信息必须含"重跑 replay_edges reconcile"指引串——与通用 schema 错误文案区分）、i13 producer meta 非法（schema 错/mint 错/窗口非法三变体）、i17 consumer schema 非 v3 非 v2 的第三值、i21 soltx meta schema/mint 错、i22 window from>to、i23 edge_count 非正整数＋digest 非小写 hex、i24 owners 实物 size 与登记不符、i26 window 与 meta 采集窗口错位、i27 snapshot schema/mint/target 三错变体。

### 5. BC-07（缺陷）mint 形态校验

producer 与 consumer 两侧：mint 必须 strip 后非空、全部字符 ∈ base58 字母表 `[1-9A-HJ-NP-Za-km-z]`、长度 32~44。测试：纯空白/尾部 U+200B/U+FEFF/U+3164/U+2800/含 `0OIl` 字符/900 字符超长 → 全拒（盲审 M7~M12 转红）；PYTHIA 真实 mint 形态照常过。

### 6. BC-08（缺陷）data_cutoff_slot 登记

- `references/scan-schemas.md` 存量迁移段：写明 Solana 案 `source.json` 的 `token.data_cutoff_slot` 必填、含义（＝采集上界 slot，与 reconcile 收据 window.to/snapshot cutoff 同源）、存量案补填方法（从案内 collect_manifest/snapshot meta 查）。
- `references/report-template.md` token 必填字段清单补该键。
- consumer 缺该键的报错信息补一句指引（"存量案补填方法见 scan-schemas.md 存量迁移段"）。

### 7. BC-09（缺陷）edge_extrema.ts 明示记录字段

裁决＝不伪装防线：代码注释＋scan-schemas.md 明写"ts 为记录性字段（人读时间参考），身份校验以 slot 为准，ts 不参与机器判定"；删除或不再暗示元组比较里 ts 的防线作用。不为 ts 造伪校验。

### 8. BC-O5（观察随修）reconcile 链 JSON 解析等深

reconcile 链的正式 JSON 解析点（receipt/meta/owners/snapshot meta/sidecar/collect_manifest 消费处）统一 `parse_constant` 拒非有限数（生产侧 import supply_truth_gate._reject_constant，consumer 侧 camp_series_provenance 自备同款——注意 lib 层勿反向 import report 层）；`RecursionError` 归政策错 exit 2（补进 except 元组）。每个挂载点配摘掉即红锚（循环写法）。超深嵌套场景退出码 1→2 转正。

### 9. BC-O6（观察随修）duckdb SKIP 改硬失败

`test_repair_batch_c.main()` 的 `import duckdb` 失败分支从 `print SKIP; return 0` 改为返回非零（duckdb 是 requirements.lock 依赖、env_check 三检看护，缺席即环境坏，135 checks 静默全跳报成功不可接受）。

### 10. BC-O1（观察随修）importer 摘要口径统一

`import_pythia_legacy.replay_edge_facts` 的逻辑摘要改用与 `replay_edges._replay_with_evidence` 相同的 json.dumps 规范化口径（消除双口径隐式假设；PYTHIA 已收产物两口径恰相等，不需重跑）。

### 11. 登记不修（完工记录"发现未修"节列全，留 R10 台账）

- BC-O2：migration collector 标识零消费者（consumer 不区分迁移案/原生案）——是否要求 consumer 感知迁移身份属产品语义，待用户裁；
- BC-O3：`check_series_binding` 只在 new-analysis profile 跑，independent-audit 复核路径 sol-rows 身份闸不生效——扩 profile 影响存量复核工作流，待用户裁；
- BC-O4：sidecar producer 字段无锚——同族"哈希非签名"设计边界（工单 B 免责句同款）；
- BC-O7：hard link 替身 consumer 不可辨——importer 设计依赖，接受在案。

## 验收口径

裁判独立跑：盲审击穿复现（gate_pass="false" 涂改案、closed="false" 字符串案）修后全拒；16 项假覆盖注入抽样重放转红；test_repair_batch_c.py rc=0（checks 数上升）；run_all 全绿；staging-pythia 与 PYTHIA 案根零改动。消化轮闭合以盲审员 C 第二轮复核为准。
