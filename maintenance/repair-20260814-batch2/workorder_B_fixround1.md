# 工单 B 消化轮 1：盲审 FAIL 处置（零宽击穿族＋缺陷 5＋文档 5）

> 输入＝blindreview_B.md（同目录）。消化循环纪律：≤3 轮，本轮为第 1 轮。
> 裁判裁决：B-01/02/03/11 同根因必修，B-04/05/06/07/08 必修，B-10/12/13/14＋可执行性缺口修（文档/口径），B-09/B-15/risk_flags 存量升级登记不修。
> **时序依赖：本单在工单 A 消化轮 2 收口之后施工**——直接使用其产出的正向白名单版实义判定（黑名单版已被 A 盲审二轮证明挡不住 U+3164/U+2800，不得照搬 risk_flags 的 isspace+Cf/Zl/Zp/Zs 版本）。
> 施工纪律同前：**禁一切 git 写命令**；完成后写 `workorder_B_fixround1_done.md`（逐项处置＋红→绿双跑＋自审）。
> 边界：supply_truth_gate.py 只 import 不改动；shared_release_receipt.py 的 waiver/approval 段（工单 A 资产）勿碰——只动 `validate_adversarial_review` 段及其辅助；工单 C 文件（camp_series_provenance.py / replay_edges.py / state_from_facts.py / test_repair_batch_c.py 等）勿碰；audit_release_gate.py 只动 check_adversarial 相关行（该文件同时是工单 C 施工面，改动最小化并在完工记录点名行号）。

## 修复清单

### 1. B-01/B-02/B-03（击穿）`_nonempty_string` 升实义判定，全链等深

`adversarial_review_runner.py` 的 `_nonempty_string`（`bool(value.strip())`）被零宽字符打穿——evidence、blocker id/resolution、claim_id、critic findings/non_covered 全部失守。修法：

- **生产侧**（runner 及 finalize）：从 `scripts/lib/supply_truth_gate.py` import 正向白名单版 `_meaningful_text`（A 消化轮 2 产出；同侧单源复用，不重抄第三份）。所有"非空字符串"语义的校验点（evidence、blocker id、resolution、claim_id、findings/non_covered 元素、role 等人工文本面）统一换用。
- **消费侧**（shared 的 `validate_adversarial_review` 段）：使用 shared 文件内已有的消费侧 `_meaningful_text`（A 消化轮 2 同步升级的那份），保持两侧独立纪律。audit 转调 shared 自动继承。
- 注意：verdict 是枚举精确比对（盲审确认含尾缀零宽会拒），不需要动。

### 2. B-11（随上）claim_id 规范化补剥零渲染字符

registry 内 `"C1"` 与 `"C1​"` 现不算重复（视觉同名双胞胎）。修法：claim_id 的规范化函数（runner/shared 两侧的 strip-比较处）升级为"剥除零渲染字符后再比"——剥除集至少含 Unicode Cf/Cc/Zs/Zl/Zp 及 A 盲审 13 码位所在的零渲染面（与 `_meaningful_text` 的白名单互补：规范化剥的是"不可渲染部分"，实义判定验的是"剩余部分非空"，可共享同一字符分类辅助函数）。同步：`a4_gate.py` `check_audit_registry_alignment` 的文本规范化（`" ".join(split())`）比较前先做同款剥除（盲审点名同族；只影响含零渲染字符的病态输入，正常案文本零波及）。

### 3. B-04（缺陷）staging 清理补目录形态

`run_review` 异常清理只处理 `is_file()/is_symlink()`；entrypoint 建目录时 `.staging` 目录残留案根。修法：清理分支补 `is_dir()` → `shutil.rmtree`；receipt tmp 清理同查。测试：entrypoint 建目录场景 → rc=2 且案根零残留（盲审 E1 转红）。

### 4. B-05（缺陷）N 路复核路数按内容身份去重

finalize 只按 resolved 路径去重，`cp` 副本换名可注水路数；消费侧手抄条目同。修法：finalize 与消费侧（shared 重建时）双双校验——reviews 内 execution_receipt.sha256 集合无重复、artifact.sha256 集合无重复，重复即拒（真实多路每路 artifact 内容天然不同；同字节即复读机，拒之合理）。测试：receipt 副本重交 finalize 拒；消费侧手抄 6 份拒（盲审 D3b/W11 转红）；真实两角色链照常绿。

### 5. B-06（缺陷）四处裸闸补测试钉

四闸功能在但削掉后测试全绿（假覆盖）。补四条负向锚（进 test_repair_batch2_f02.py）：
- 聚合 `claim_registry` 自报假 ref（sha="0"*64/size=1）→ 消费侧必须拒；
- artifact/receipt 输出位为 symlink → runner 必须拒；
- finalize 输出预存在 → 必须拒且原件未被覆盖；
- run_review 正式位预存在 → 必须拒。
要求：施工时对四闸各做一次临时削除自证（对应锚转红），恢复后全绿，过程写完工记录。

### 6. B-07（缺陷）execution_receipt ref 校验补 size

`validate_adversarial_review` 对 artifact 比 size、对 execution_receipt 只比 sha。修法：统一 ref 校验深度（path+size+sha256 三验），消费侧。测试：receipt.size 改 999999（sha 对）→ 拒（盲审 W7 转红）；artifact 侧回归保持。

### 7. B-08（缺陷）schema 字面量与迁移提示单源化

`"adversarial-review/v3"` 与 `V3_RERUN_HINT` 在 shared/audit 手抄。修法：shared、audit 统一 import runner 的 `AGGREGATE_SCHEMA` 与 `V3_RERUN_HINT` 常量，删除手写字面量（校验逻辑层已同源，本项只收常量层）。

### 8. B-12（口径）对抗复核链 JSON 解析补非有限数禁令＋挂载点锚

对抗复核链（runner/finalize/shared/audit 的 artifact/聚合件/registry/blockers/execution receipt 解析点）全裸 `json.loads`。修法：统一加 `parse_constant` 拒绝（生产侧用 supply_truth_gate 的 `_reject_constant`，消费侧用 shared 自己的）。**吸取 A 消化轮 R-02 教训：每个新挂载点配"摘掉即红"锚**——测试对各正式解析点注入含 NaN 的 JSON，断言各自拒绝出口触发（循环写法即可，防膨胀）。

### 9. 文档四处（B-10/B-13/B-14＋可执行性）

`references/independent-audit-protocol.md` 对抗复核节：
- 补免责句（与 reconciliation 节同款口径）："producer/runner 哈希是公开可算的完整性锚，不是签名——防走捷径与误操作，不防持同用户权限的恶意进程；finalize 不是唯一物理路径，消费侧以内容重验为准"；
- 补 TOCTOU 卡案恢复动作："entrypoint 执行中改写 registry 导致正式位被占时，删除该角色 artifact＋execution receipt 后重跑"；
- 交付清单补"复核 entrypoint 脚本必须随案保留（receipt 绑其 path+sha，删除即发布闸失败）"；
- 补 critic 完整命令行示例＋`--blockers` 输入文件结构示例（`[{"id":…, "resolved":bool, "resolution":…}]`）——照文档可写出可跑通。

`references/analyze-workflow.md` A4 §5："证据非空"表述升为"证据含实义字符（不可见字符不算）"。

### 10. 登记不修（完工记录"发现未修"节列全，留 R10 台账）

- B-09：blocker 清单存在性 100% 自报、与 artifact 内容零联动——语义层联动超出 F-02"客观结构"边界，待用户裁决；
- B-15：runner subprocess 无 timeout——存量非本单引入；
- `risk_flags.py` `_strip_invisible_space` 黑名单版存量升级（挡不住 U+3164 族）——留批 4 守卫收尾轮统一处理。

## 验收口径

裁判独立跑：盲审主击穿复现（零宽 evidence 端到端、resolution=U+2060、全空白链）修后全拒且换 U+3164/U+2800 同拒（正向白名单深度确认）；目录残留场景零残留；注水场景拒；test_repair_batch2_f02.py rc=0；run_all 全绿；工单 A 段（waiver/approval）与工单 C 文件零改动自证。消化轮闭合以盲审员 B 第二轮复核为准。
