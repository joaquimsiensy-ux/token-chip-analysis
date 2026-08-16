# G3 盲审第 1 轮报告（opus 4.8 独立子代理，2026-08-15）

- 对象：repair-20260815-g3 @ 工单 A+B 完成态（基线 ddba187）
- 方式：只读+伪 transport 探针（零真实网络、零 worktree 改动）；SUITE 101/101 独立复跑确认
- **VERDICT: BLOCK**（P0×1 P1×1 P2×2 P3×3）

## findings

- [G3R1-01] P0 | F-06/fetch_sqd_evm.py+csv_collector_receipt.py | SQD 完成证据只有下界没上界：任一 provider 行 header.number >= --to-block 即 break 并签正式 receipt，单行越界哨兵响应（如 number=10^9）可把"零行"签成"全覆盖"，端到端穿透 make_channel_receipt→channels_preflight 全 PASS。number 为 float/字符串同样通过（仅拦 bool）。属基线既有形态未关死（非新引入），但"已关死残响应假完整"声明不成立。修法：parse 增区间校验（header.number 必落 [req_from,req_to]，越界=协议异常）；emitter 补上界（provider_next_block > requested_to 即 raise）；负测补越界哨兵。
- [G3R1-02] P1 | F-06/fetch_sqd_evm.py parse | log 级零校验：topics/data/timestamp 缺失静默降级为空地址+零金额入 CSV，receipt 完全"合规"；同次修复给 Alchemy（探索档）做了逐字段严校验，能签正式 receipt 的 SQD 反而没做。修法：log 逐字段校验拉齐（topics>=3 且各 66 位 hex、data 合法 hex、transactionHash/logIndex 类型合法，任一不合=ValueError）。
- [G3R1-03] P2 | test_g3_docs_guards.py check_f08_a0 | A0 needle 按段内任意位置匹配，两种变异（命令回退正式文件名/--exploration 挪进括注）守卫仍绿。修法：整串精确断言+负向断言（A0 段不得含 --out accounting_mode.json）。
- [G3R1-04] P2 | SKILL.md:43 | A0 产物改名后 SKILL.md 阶段路由表仍写 accounting_mode.json——本次改动新引入的不一致；SKILL.md 在本组协调边界外，**交融合方同步**。
- [G3R1-05] P3 | fetch_alchemy.py | "合法 hex"实为 int(v,16) 可解析：负数/下划线/前后空白均通过。修法：re.fullmatch(r"0x[0-9a-fA-F]+")。
- [G3R1-06] P3 | fetch_alchemy.py --receipt help | help 文本仍承诺"写正式 evm-collector-run/v2"与立即拒绝的行为矛盾。修法：help 改除名指引。
- [G3R1-07] P3 | test_g3_docs_guards.py check_f13/f05 | 全文件字符串匹配，删整段/降级 HTML 注释仍绿。修法：锚到所在段落，强度与 check_f08_a2 拉齐。

## 零发现区（攻击未破防）

F-05 六项"已强制"逐行对照 adversarial_review_runner.py 全部属实（roles/并集/entrypoint 去重/ledger 对账/evidence 门槛/blocker 联动，行号在案）；四项"未强制"披露无遗漏。F-13 新句与 runner 逐字吻合。F-08 命令序列与 accounting_gate argparse/shared_release_receipt formal 消费逐项吻合，A0→A2 间无闸消费 accounting_mode.json。--receipt 前置绕过五例（symlink/同文件拼法/悬垂链接/零字节）全拦。.partial 四条失败路径全隔离。除名完备性全库 rg 无第三入口。bool 陷阱有效。Alchemy 声明各项生效。哨兵乱序保守方向+下游冲突检测兜底。SUITE 101/101。

## 探针清单（摘要）

probe_sqd_overshoot A1-A5（越界哨兵/真实行+越界/float/str/log 半残）5 破防；probe_e2e_preflight 三级链路端到端破防；probe_needles M1/M2/M3/M3b/M4 守卫弱（M5 顺序倒置被拦=合格）；probe_misc B1 畸形 hex 4/5 弱、B2 前置绕过 5/5 拦；run_all 101/101。
