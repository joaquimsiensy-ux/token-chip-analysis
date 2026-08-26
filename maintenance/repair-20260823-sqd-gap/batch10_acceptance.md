# 批 10 Fable 验收记录（2026-08-26）

裁决依据：用户当日拍板方案 A（第五查对冻结点对账；封账日对上即收，观测差由既有
supply_truth 容差兜底、保留当报警器）。

## 验收项与结论

1. **diff 逐 hunk 审查**：runner 两处 + 公共深验一处，改动面与工单一致；
   EVM 与其余 solana check 走原全等 else 分支，零外溢。✅
2. **canonical_target 类型兜底核实**：shared_release_receipt.py:317-330 确实拒
   bool/负数/非 int——codex 依赖它做 receipt slot 类型校验成立。✅
3. **深验正向绑定考据独立复核**：solana_exact_validate.py:1919-1934 逐行读过，
   `receipt.target.as_of_block == soltx_meta.finalized_upper_slot` 否则深验失败——
   done 报告"改前已存在"结论属实，放宽全等后防"旧时点收据冒充"的权威闸在位。✅
4. **生产者硬闸不动**：replay_edges.py:394-396 原样；done 报告给出 SHA-256 与
   HEAD 全等。✅
5. **红绿证据抽查**：R1 红证据为改前真实报错 traceback（非事后编造）；绿证据
   含 N1-N5/EVM 回归/契约守卫。✅
6. **边界外一步攻击（Fable 亲打 6 发）**：
   - A1 尾部裸 flag → 拒；A2 双 flag 混合 → 拒；A3 占位符藏 receipt 路径 → 拒；
     A4 负数 → 拒；A6 正常字面量 → 过。
   - **A5 非 ASCII 数字（阿拉伯-印度数字"٥"）→ 放行**：isdigit 单用的已知陷阱。
     判定＝化妆级瑕疵非漏洞（生产者 _valid_nonnegative_int＋硬闸==冻结点双兜底，
     两层对该字面量的数值解释一致），但按纪律收紧：Fable 亲修加 `isascii()`
     （reconciliation_report.py 校验行，带注释）。收紧后三个直接相关测试复跑全绿。
7. **run_all**：施工树 134 全绿（EXIT=0，本机无 loopback 限制，codex 沙箱的
   2 失败确认纯环境）；亲修后终树再跑一轮全绿后方 commit。✅
8. **禁改面**：版本登记面由 Fable 操作（6.52.9）；密钥零触碰；ARC 案根零触碰
   （job spec 由本验收方后续修改）。✅

## codex 施工质量评注

诚实度高：沙箱 2 项环境失败如实标注"未获完整 suite exit 0、不宣称全绿"，
未改测试绕过、未伪报。工单理解准确，深验绑定考据给了行号而非重复造闸。

## 后续（本验收通过即执行）

commit v6.52.9 → ARC reconciliation_job.json 第五查钉冻结点 440368381 →
重跑五查 → A3 机械层 → handoff READY 即停。
