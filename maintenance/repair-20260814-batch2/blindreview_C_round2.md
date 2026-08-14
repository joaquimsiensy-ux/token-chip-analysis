# 工单 C 消化轮 1 盲审复核报告（第二轮，对 2806e90）——判定 REOPEN（轻度）

> 入档件。盲审员（opus 子代理）35 单项＋5 组合破坏性注入＋15 mint 变体＋staging 独立复验。
> 判定：**REOPEN（轻度）**——首轮 2 击穿全 CLOSED、9 缺陷 8 条 CLOSED、16 假覆盖 12 咬中＋4 证实冗余等价（0 遗留真假覆盖）；本轮新代码引入 2 缺陷＋4 项新假覆盖＋观察若干。无新击穿。
> 裁判（Fable）处置：见同目录 `workorder_C_fixround2.md`。N-06 属裁判验收刷新遗漏（只重跑 producer 链未重跑 importer），裁判自认。

## 首轮逐项判定（摘要）

- **BC-01 CLOSED**：真实对账 FAIL 案喂 9 种 truthy 值全 `BLOCK: gate_pass 非 true`；gate_pass=True 伪绿被 mismatch_count 必验二次拦（双保险）。
- **BC-02 CLOSED**：closed 四变体全 rc=2；supply_raw 缺失显式拒。
- **BC-03 CLOSED**：三形态全拒；两处冗余组合注入均红。
- **BC-04 CLOSED**：r10 注入现红。
- **BC-05 部分 CLOSED**：边实物闸落地（空/size 差 1/sha 形态/缺键/改名全拒；等长垃圾与 sha 撒谎在发布点重哈希拒）；文档改诚实措辞。残留 N-01/02/03。
- **BC-06/07/08/09、BC-O1（夹具级）/O5/O6 全 CLOSED**（mint 15 变体 13 拒、data_cutoff_slot 三处登记在位、ts 降记录字段、10 万层嵌套 rc=2 带 BLOCK 语义、duckdb 改 FAIL rc=2）。
- BC-O2/O3/O4/O7 登记一致。

## 新缺陷

### N-01【缺陷·新引入】边文件闸不拒 symlink

`camp_series_provenance.py` 边实物闸用 `is_file()` 不查 symlink：边文件换成指向案外实物的软链（size/sha 均对）→ 编译 PASS＋发布零 error＋producer 侧同放行。同文件 `_resolve_ref` 对三输入明确拒 symlink、importer 只建 hard link——同文件不等深。"canonical 边文件在场"降级为"有个指向别处的名字在场"。

### N-02【缺陷·新引入】发布点 verify_edge_physical_sha=True 接线无守卫（BC-04 同型复发）

闸本身有钉（n07 红），但"发布点确实打开了这个开关"零守卫——删掉该实参后 216 checks＋run_all 96 项全绿。物理 sha 重算是编译/发布强度差的唯一支点，实参被删或默认值漂移则等长垃圾边从 SPLIT 变 BREACH 且无测试红。

## 新假覆盖（4 项）

n06 编译点 edge_file_size 对锚、n08 发布点接线（即 N-02）、n13 producer 侧 parse_constant、n15 edge_file_sha256 形态——单削全绿。组合 c4（size＋sha 形态同削）亦全绿。

## 观察

- **N-05**：`audit_release_gate.py:109` 通用 load_json 与 :758 仍裸 `json.loads`（发布闸读 state/reconciliation_report 主入口）；实测 NaN 不构成放行（重转换逐点比对兜住）但 BC-O5 收口不完整。
- **N-06**：staging 的 migration_receipt.producer.sha256 指旧 importer——裁判刷新只重跑 producer 链未重跑 importer；BC-O1 口径改动未经真实案实证（首轮独立重算证明 PYTHIA 两口径恰相等，重跑应成功，但推断非实证）；首轮完工摘要"importer SHA 与当前脚本一致"自证句已失效（历史档案不倒改，在案说明）。
- **N-07**：编译/发布强度差（等长垃圾边编译过发布拒）＝显式设计取舍有正反测试与文档，登记非缺陷。
- **N-08**：首轮 r09/r19/r24/n03/n04 五项 STILL_GREEN 经组合注入证实为冗余或语义等价（删后行为不变或同链另一闸兜住），非假覆盖。

## PYTHIA staging 独立复验（新产物）

net_supply_raw int/两计数 int 0/gate_pass bool True ✓；meta 物理指纹与盲审独立重算逐项相符 ✓；边文件非 symlink 同 inode nlink=2 ✓；producer sha=快照实算 ✓；分母三方对锚 998158041739995 ✓；三输入 sha 全符 ✓；唯一不符=migration_receipt 指旧 importer（N-06）。

## 注入总表

35 单项：RED 26、STILL_GREEN 9（5 项证实冗余等价，4 项真无覆盖=n06/n08/n13/n15）。组合 5：c1/c2/c3/c5 RED、c4 STILL_GREEN。

## 只读自证

零 git 写；快照六件 sha 与 git 对象相符；注入在 cp -al 副本＋写前断链；PYTHIA 案根零改动；staging 只读（其 09:08 变更为裁判刷新窗口，早于盲审起点 09:17）；注入目录已清。
