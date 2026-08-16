# G3 盲审第 2 轮报告（opus 4.8 同一盲审员续审，2026-08-15）

- 对象：repair-20260815-g3 @ 工单 C 消化完成态
- **VERDICT: PASS**（P0=0 P1=0 P2=0 P3=4）

## 核心结论
- round-1 两条实质缺陷已全部关死：7/7 破防探针重放失效（越界哨兵/混合越界/float/str number/log 半残/空正文/部分推进后空响应均 exit 3+不签+.partial）；round-1 端到端穿透（1 行数据换 991 块窗口 PASS）不可复现，链路断在采集器第一环。
- 13 条新边界外攻击全拦（上界+1/下界−1/先合法后越界/二次回退/timestamp 溢出与乱串/topics 缺短/非 hex data/tx hash 长度/logIndex 乱串/logs 非 list/number bool）。
- 9 种合法真实形态零误杀（闭区间两端/data="0x" 零值/uint256 最大/全大写 hex/4 topics/纯哨兵零匹配/多响应分页到界/无 timestamp/str 数字 timestamp）——无假阳性。
- emitter 恒等式（provider_next_block==requested_to）自洽无误伤；preflight 消费侧保持 >= 被判为必要设计（hypersync 续采链可合法大于）。
- round-1 四条 needle 变异（M1-M4）现全部转红；F-05 六项声明/F-13 结论无回归；SUITE 101/101。

## 残留 P3（全部留账，不阻断）
- [G3R2-01] fetch_sqd_evm parse 内部严格度不一致：data 长度不设限（截断 data 会静默改金额数量级）、header.hash 零校验、logIndex/timestamp 允许负整数。定性=设计取舍非已证破防：钉死 data 64 位会把非标 ERC20（Transfer data 非单 uint256）变硬失败。**交融合方裁决**：收紧 or docstring 明写边界；顺带建议补 hash 66 位断言与非负断言。
- [G3R2-02] A0 负向断言可被"另加一条矛盾命令"绕过（./ 前缀变体、非反引号纯文本）。round-1 形态已堵死；残留属蓄意形态。建议：负向断言改正则+扫描面扩到整段。
- [G3R2-03] paragraph() 守卫可被诱饵段影子化、"留标题掏空正文"不可拦——needle 守卫锁不住散文语义的固有上限。建议：命中段全量校验+补条目级 needle。
- [G3R2-04] data-pipeline-evm-channels.md"哨兵行给出的扫描前沿"措辞易被读成消费侧可独立验证——实际 provider 证据在采集运行时校验、不在字段本身（自签模型既有边界）。建议改口一句。

## 另
- G3R1-04（SKILL.md:43 阶段表产物名）按指示未复核，仍挂融合方名下未闭合。
- 附带发现：fetch_sqd_evm 的 provider_last < cur 分支已成死代码（parse 区间校验保证），无害可留可删。
