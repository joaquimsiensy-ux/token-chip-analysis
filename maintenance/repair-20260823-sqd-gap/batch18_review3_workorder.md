# 批 18 第三轮盲审消化工单 b18r3(v2,经 codex 复核重定形):witness 闭包改深验实录 + batch_d 墙钟报告契约

基线:main=50d7767(v6.54.2);当前 HEAD 与其唯一树差异=本工单文件,验收方确认按等价工作基线处理,不构成停工条件。
第三轮盲审 review-mti7cloy 三条(P1+P2×2)全 CONFIRMED;v1 工单经 codex 只读复核四条全退回,本 v2 按复核意见重定形。
版本:6.54.2 → **6.54.3**。

## 纪律
- 先红后绿,红证据存 `maintenance/repair-20260823-sqd-gap/batch18_review3_red_evidence.txt`。
- 白名单:`scripts/report/shared_release_receipt.py`、`scripts/lib/receipt_validate.py`、`scripts/lib/solana_observation.py`(仅加默认关闭的 observer 钩子与必要上报,不改任何校验语义)、`scripts/solana/audit_closed_accounts.py`、`references/data-pipeline-solana-capture.md`、`scripts/tests/test_batch18_review_digest.py`(既有断言只许随本契约变更同步且 done 逐条说明,原则上应全部天然保绿)、`VERSION`、`pyproject.toml`、`SKILL.md`(:23)、`CHANGELOG.md`、本目录 red_evidence/done。
- **test_repair_batch_d.py 禁改**;其余禁改同前批(handoff_manifest、audit_release_gate、既有其他测试断言、ARC 案根只读、API key)。
- ARC 案根允许**只读**取证(统计/签发实测),禁止任何写入。
- 锚点以 50d7767 为准,开工 grep 亲核,不符停工。完工不 commit。

## 第一部分(消化盲审 P1+P2×2):闭包语义从"形状近似"改为"深验实录"

### 背景与裁量(须写进代码注释与 CHANGELOG)
v6.54.2 的形状 BFS 把"JSON 里长得像文件引用的一切"都捞进闭包。ARC 正式修复代 `data/sqd_repair/6b99816bc26d8c53bac165b4efeb03a2b0beee563bf242e05b8906ae8dff3cb8/gen-80c6929bb5fd3c1d/evidence_manifest.json`(46.6MB)含 307,334 个 path 引用、声明约 40GB(含 2.30GB slot_index_map.jsonl)——该 manifest 经 repair bundle.json 从 exact receipt 可达,形状扫描会试图绑定全体:128 上限拒签(盲审 P1),放开上限则签发+消费各全量读 40GB、整读 sha() 数 GB 峰值内存,均不可行。
根治=**闭包只收深验实际打开并核过 sha 的文件**(深验没核过的引用,重跑深验同样发现不了,witness 如实反映深验新鲜度,不多不少):
- 盲审 P1 消失:evidence_manifest 未被深验逐件核,不入闭包;闭包=深验真实消费面(量级几十个文件)。
- 盲审 P2-a(非 .json 后缀)消失:入闭包与文件名无关,只看深验是否核过。
- 盲审 P2-b(holder 三基准)消失:validator(solana_observation.py:609-641)自己选中并核过的 actual 路径被原样登记,无需镜像 resolver。

### 实现定形
1. **observer 钩子**:
   - `shared_release_receipt.py` 模块级 `_DEEP_FILE_OBSERVER = None`;`sha(path)`(:85,ref_ok/bound_case_ref/repo_ref_ok 汇聚点)在 observer 非 None 时上报 `(resolved_path, digest)`(校验成功与否由调用方决定,上报发生在算出 digest 处;上报本身绝不改变任何现有行为)。
   - `receipt_validate.py` 模块级 `HASH_OBSERVER = None`;`_hash_file`(:22,调用点 :115 producer 与 :141 inputs)算出 digest 后同款上报。
   - `solana_observation.py` 模块级 `HASH_OBSERVER = None`;:638 holder_outputs 实物校验处把 `(actual, 算出的 digest)` 上报。
   - 三处默认 None=零行为变化;不引入 lib→report 反向 import(钩子是模块变量,由 shared 侧赋值)。
2. **采集窗口**:`witness_reconciliation_report` 在真跑 `validate_reconciliation_report` 前激活三个 observer 指向同一收集函数,`try/finally` 复原(嵌套/重入按"外层优先,内层沿用"处理并注释;深验单线程)。收集侧过滤:只收 `root` 案根内的文件(repo_ref_ok 报的仓库脚本路径丢弃),按 resolved 绝对路径去重;同一文件多次上报以**最后一次** digest 为准。收集所得排序为 `bound_files`。上限哨兵 4096(深验实录远不可能到;超过=病态,拒签 raise,不静默截断)。
3. **删除形状 BFS**:v6.54.2 的 `_reconciliation_bound_files` 递归扫描(candidate/discover/json_queue 全套)整体移除;wrapper 本体新鲜度已由 `report_sha256` 单验覆盖(消费三验保留),不再重复入闭包(入亦无害,取舍 done 说明)。冻结态 SOLANA_FROZEN_OBSERVATION_BUNDLE 深验真读并核(:1467-1494 validate_observation_bundle+信封),经 observer 自然入闭包——用断言验证而非显式补收;若实测未入,查漏钩而非绕过。
4. **消费重哈希**:三验中对 bound_files 逐文件重哈希改用**分块流式**读取(闭包专用 `_stream_sha`,131072 块;不改全局 `sha()`,回归面隔离);缺失/symlink/不符→统一 `ValueError("reconciliation witness 无效/过期")`。payload_sha256(b18r2)与身份注册表(b18r1)语义不变。
5. **覆盖面守卫**(防"深验新增哈希点绕过 observer"的回归):新增一个契约测试——在采集窗口内跑批 15 动态案深验,断言闭包**恰好等于**该案深验已知消费面(receipt 实物、inputs 实物、holder accounts/owners、observation bundle、frozen bundle 等,列表由你实测后固化);任何后续深验实现改动若引入未上报的哈希点,此测试与 N9/N10 联动能暴露。done 里列出你 grep 全库确认的"深验路径全部文件哈希点"清单及其上报状态。

### 红绿(先红后绿)
- R1(P1 复现):合成夹具案,在 exact receipt 的 inputs 里绑一个 bundle.json,bundle 引用一个含 ≥200 个真实小文件 path 的 evidence_manifest 形状文件——基线(50d7767)签发 raise "文件闭包超过 128";修后签发成功,且闭包**不含** manifest 引用的那批文件、只含深验实录面。
- R2(P2-a 复现):receipt 改名为无后缀仍被 wrapper 引用,篡改其 envelope inputs 绑定的实物——基线 witness 仍过(形状扫描未递归无后缀文件);修后拒(envelope _hash_file 实录)。
- R3(P2-b 复现):bundle 与 scan --work-dir 分离布局(holder 实物只在 gpa_rpc 实物目录),篡改 holder 实物——基线 witness 仍过;修后拒(:638 实录)。
- N:批 15 N6 案未篡改照常通过;篡改闭包内任一实录文件(receipt/owners/output/bundle)均拒(沿用既有 review 测试,应全部天然保绿);N9 calls==1/N10 calls==2 不变(observer 不增加深验调用);N11 errors 逐字不变。
- **ARC 实测**(验收方跑,你在 done 里写清命令):只读 ARC 案根签发 witness,报告墙钟/文件数/读取字节;此为 P1 的真实闭环证据。

## 第二部分 F4(既有 flaky,非盲审):audit_closed_accounts 报告契约统一
锚:`scripts/solana/audit_closed_accounts.py`——:49 `T0` 模块导入时初始化(同解释器多次 `main()` 继承旧时钟,batch_d 正是此调法,test_repair_batch_d.py:166);:56 附近早退报告无 `sampled` 段;:453/:465 主路径才写全段;墙钟在无样本阶段触发走 `bail_invalid` 且拿不到 wall 状态,`invalid_reasons` 可能无"墙钟"。基线 8ae0f63 复现 6/6 KeyError(验收方取证)。
修法(按复核意见定形):
1. 删除全局时钟语义:每次进入 `main()` 记录本次 `started_at`,deadline 与 `elapsed_sec` 均由它计算。
2. 单一 report/sampled builder 供早退与主路径共用;早退传入当前阶段统计与 wall 状态,`sampled` 段字段与主路径同构,未及采样的计数填 0 并增加 `sampling_phase`(或 `counts_complete: false`)字段写清"填 0=未采样"与"实际查得 0"的区别(文档同步)。
3. 墙钟命中(任何阶段)统一在 `invalid_reasons` 追加含"墙钟"字样的原因,`sampled.wall_truncated` 如实置位。
4. `references/data-pipeline-solana-capture.md:97` 附近"早退是精简 status 报告"的描述同步更新。
5. **test_repair_batch_d.py 禁改**,其 ⑤ 断言须在任何负载下天然成立;另在 `test_batch18_review_digest.py` 增加覆盖**全部 bail_invalid 调用点**(你 grep 逐一列出)的契约测试:每个早退分支的报告都含同构 `sampled` 段、墙钟触发时含"墙钟"原因。
红:极小 --wall-min+mock 延迟稳定触发早退,基线报告缺 `sampled` 键原文;修后同参数报告含全段,且 batch_d 连跑 5 次 rc=0(记入红证据绿段)。

## 收尾
- 回归重点:test_batch18_review_digest 全部(既有断言应天然保绿,凡需同步的逐条说明)、test_batch18_shared_bundle_witness(N11 逐字)、test_batch15_three_ledgers_frozen(N9/N10)、test_r9_batch3_solana_observation、test_repair_batch_b(B-1/B-2)、test_reconcile_v4_receipt、test_repair_batch1、test_repair_batch_d 连跑 5 次、changelog/docs/version lint。
- SUITE 分母 146 不变;版本五处 6.54.3;CHANGELOG 六栏(第一部分=盲审 P1+P2×2 经复核重定形为深验实录,第二部分=既有 flaky 收口)。全量 146 由验收方本机 nohup。
