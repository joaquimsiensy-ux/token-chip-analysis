# 工单 B（F-02）盲审攻击报告（对 6da206b）——判定 FAIL

> 入档件。盲审员（opus 子代理）基于干净快照 `git archive 6da206b` 攻击工单 B 修复面，约 85 个攻击点。
> 判定：**FAIL**——原反例（2 字节 "ok" 空壳）确已闭合，但"每条裁决携带非空证据"这条不变量被零宽字符从另一个门重新打穿。
> 裁判（Fable）处置：见同目录 `workorder_B_fixround1.md`。

## 击穿级（3 条，同一根因）

### B-01【击穿】零宽字符击穿"evidence 非空"

`adversarial_review_runner.py` 的 `_nonempty_string` 用 `bool(value.strip())`。`str.strip()` 只剥 `isspace()` 为真的字符：U+200B/U+FEFF/U+2060/U+180E 的 `isspace()` 全是 False，被判"非空"。端到端复现：每条结论 CONFIRMED、证据字段是一个零宽字符 → runner rc=0、finalize rc=0、release_decision=PASS、shared/audit 两消费侧全绿。人眼看到的证据字段渲染为空。

### B-02【击穿】blocker resolution 填零宽即自称已解决 → 机器派生 PASS

同函数被 `validate_blocking_findings` 复用。对照实验：resolution=普通空格/NBSP 被拦（isspace=True），resolution=U+2060/U+180E 全链放行。blocker id 同样可填零宽。工单 item 8 的"resolved=true 时 resolution 非空"实际堵不住。

### B-03【击穿】registry + artifact 全零宽 → 端到端"全空白复核链"

a4_claims.json 的 claim id、artifact 的 claim_id 与 evidence 全填零宽 → finalize rc=0、shared/audit 全绿。机器眼里结构完备、覆盖完整、证据齐备；人眼一片空白。门槛只从"写 2 字节"抬到"写一个 JSON 骨架"。

### 共同根因（裁判重点）

**仓库里早有单源修法没用上**：`scripts/labels/risk_flags.py` 的 `_strip_invisible_space()`（8f3600c「B2-G0 批一 P3 收尾」落地，剥 isspace＋Cf/Zl/Zp/Zs，配套测试断言 `parse_risk_flags("﻿")==()`）。**同一仓库第二次打开同一个洞**，违反元规则「同族要关到同一深度」。盲审实测该函数对四个零宽码位全归空。
同族面更宽（供圈范围）：`shared_release_receipt.py` waiver/approval 字段（6da206b 时点；消化轮 1 已改 `_meaningful_text` 黑名单版、消化轮 2 将升正向白名单）、`a4_gate.py:157` `check_audit_registry_alignment` 的 `.strip()+" ".join(split())` 同不剥零宽。
裁判补充：risk_flags 的黑名单版本身也挡不住 U+3164/U+2800（工单 A 盲审二轮已证明），修复不得照搬它，须对齐 A 消化轮 2 的正向白名单深度。

## 缺陷级

- **B-04 staging 目录形态残留**：`run_review` 异常清理只处理 `is_file()/is_symlink()`；entrypoint 在 CHIP_REVIEW_OUTPUT 建**目录** → runner 正确拒绝（rc=2）但 `.staging` 目录留在案根，与完工摘要"零残留"结论冲突。
- **B-05 N 路复核路数注水**：finalize 只按 resolved 路径去重——`cp` 一份 execution receipt 换名重交，聚合 reviews 长度 3（实际 2 路）；消费侧手抄 6 份自称 6 路复核，shared/audit 全绿。路数是交付给读者的审计证据，可随手翻倍。
- **B-06 四处闸零测试钉（假覆盖）**：破坏性注入证明以下四闸功能在但**削掉后 F-02 测试与 run_all 仍全绿**：①消费侧聚合 claim_registry 自报 ref 比对（削掉后可自报 sha="0"*64 不拦）②contained_regular/output 的 symlink 拒绝 ③finalize 输出防覆盖 ④run_review 正式位防覆盖。其余 7 注入均有测试咬中。
- **B-07 execution_receipt.size 不验**：`validate_adversarial_review` 对 artifact 显式比 size，对 execution_receipt 只比 sha——同函数两个 ref 校验深度不一致。实测 size 改 999999（sha 对）全链接受。
- **B-08 schema 字面量三抄**：校验逻辑层真同源（shared import runner 7 符号、audit 转调 shared），但 `"adversarial-review/v3"` 字面量在 shared:604/audit:827 各手写一遍，`V3_RERUN_HINT` 中文原句被 audit:824,828 原样抄两遍（未 import）。

## 观察级

- **B-09 blocker 清单 100% 自报**：全部 verdict=REFUTED、critic findings 非空，只要 blockers.json 写 `[]`，release_decision 仍 PASS。工单明写"不判断观点对错"不算违约，但"blocker 存不存在"与 artifact 内容零联动。
- **B-10 finalize 非必经之路**：手写 v3 聚合件（引真实 artifact/receipt、填公开可算的 sha）绕过 finalize，消费侧全绿。"producer 是公开哈希不是签名"的设计必然；reconciliation 节有同类免责句，对抗复核节没有，口径不齐。
- **B-11 registry 视觉同名双胞胎**：`"C1"` 与 `"C1​"` 不算重复，两条都要求覆盖，肉眼同一条。同根因 B-01。
- **B-12 对抗复核链未套 JSON 非有限数禁令**：waiver/approval 有 `parse_constant=_reject_constant`，对抗复核链全裸 `json.loads`，聚合件塞 NaN 全链接受。当前无可利用面，口径不齐。
- **B-13 TOCTOU 卡案**：entrypoint 执行中改写 a4_claims.json → runner 仍 rc=0 落盘（绑旧 sha），下游拒（链级 fail-closed 成立），但正式位被占、重跑被 "must be absent" 挡，须人工删两文件恢复——文档没写恢复动作。
- **B-14 entrypoint 随案保留**：receipt 绑 entrypoint path+sha，删脚本后发布闸失败。属预期，但协议文档交付清单没写"entrypoint 脚本必须随案保留"。
- **B-15 subprocess 无 timeout**：挂死 entrypoint 永久挂住 runner。存量问题非本单引入，记账。

## 文档对齐核查

- ✅ 协议 §156-158 两条命令逐字可跑通；三个环境变量描述与代码一致；research-workflows prompt 骨架一致；工单 item 1 前提（a4_gate 双向对账）复核属实。
- ❌ 可执行性缺口：critic 完整命令行未给；`--blockers` 输入文件结构只存在于代码里，照文档写不出。
- ⚠️ analyze-workflow A4 §5"证据非空"半句被 B-01 证伪。

## 未击穿防线（摘要）

verdict 枚举精确比对（含尾缀零宽拒）、claim_id strip 对称/registry 内 strip 后重复拒、registry 绑定全族（symlink/同字节替身/旧产物重放/事后改写全拒）、三方撕裂全族拒、finalize 失败路径全族拒（resolved 非 bool/输出预存在/symlink victim/缺角色/零表态/critic 顶替覆盖/手改 PASS 被独立重判）、artifact 形态族拒、runner 原子性族拒（staging symlink/tmp 抢占/正式位二跑）、路径逃逸族拒。

## 复现产物（盲审员落盘于其 scratchpad）

`repro_F02_zerowidth.py`（主击穿一条命令）、`attack_b.py`/`attack_b2.py`（全量 harness）、`inj1`~`inj11`（破坏性注入副本）。基线：快照内 F-02 测试 21 项全绿、run_all 全过——施工方自报属实。全程零 git 写命令。
