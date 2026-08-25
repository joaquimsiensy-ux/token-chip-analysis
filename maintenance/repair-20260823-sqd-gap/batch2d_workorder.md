# 批 2d 工单:SQD stream 区间尾部无块的流结束语义修复(sqd_coverage_probe.py)

日期:2026-08-24。基线 HEAD:e3969e1(v6.52.2,main,工作树干净)。
本工单属 maintenance/repair-20260823-sqd-gap 工程批 2 探针家族(2→2b 分页续读→2c 检查点→**2d 本单**)。

## 背景与实证(只读事实,不得改写)

ARC 全区间覆盖扫描(306,451,717→440,368,381,1.34 亿 slot)两轮均以 exit 2 结束:
- 首轮(08-23 17:19Z→08-24 17:35Z):残留 785 区段 46,692 slot(其中 44,100 大洞与 102 条失败=本机代理瞬断,已由续扫补回;另 766 条失败=HTTP 200 空响应)。
- 续扫轮(08-24 23:42Z→23:56Z):代理类洞全部补回,但残留 778 区段 1,497 slot——与首轮"200 空响应"失败**位置完全重合,两轮确定性复现**。
- 位置规律:全部残留洞都是某扫描请求区间(SQD_PAGE_SLOTS=450 步长切分)的**最后 1~11 个 slot**。
- 链上实证(Helius getBlocks,4 样本 4/4 吻合):洞内 slot 链上无块(Solana 跳块),洞前紧邻 slot 有块。样本:306463860-66(7 宽)/306467916(单)/313820906-16(11 宽)/380245860-66(7 宽)。
- ledger 指纹:失败行 `provider=SQD, http_status=200, error="curl returned empty stdout"`。

## 根因链(已核对代码)

1. `_scan_partition`(scripts/solana/sqd_coverage_probe.py:276-293)按游标续页:cursor=最后返回块 slot+1 后再发 `_scan_request(cursor, end)`。
2. 当 [cursor, end] 链上全为跳块时,SQD portal 返回 **HTTP 200 + 零字节 body**(流已尽,无块可返回)。
3. `scripts/lib/net.py:152` 对空 stdout 统一判 `_curl_error("decode", "curl returned empty stdout", http_status=200, retryable=True)` → result.ok=False。
4. `_scan_request:228-230` 见 result 不 ok 直接记失败行返回 part=None → `_scan_partition:284-285` break → 尾部 slot 永远留 0(UNSCANNED)→ 整趟结束 `run_probe:953-957` 因 counts 含 0 而 exit 2,永不收敛。
5. 探针作者已预想"空数组=[from,to] 无块头"的正确语义(`_scan_request:235-237`:empty_response=True、整段记 NO_HEADER=1、ok=True),但 200 空体在传输层就被拦,走不到该分支。

## 修复要求

**只改探针层,禁改 net.py**(全库共用传输件,200 空体在其他调用方语义下可能是真故障)。

在 `_scan_request` 的 `if not result.ok:` 路径中增加特判:当且仅当该失败满足全部机械判据——
- error category == "decode",且
- http_status == 200,且
- 错误文本为 net.py 的空体常量 "curl returned empty stdout"(区分同 category 的 "invalid JSON response" 真故障;两处源码加交叉注释钉住该常量的双向依赖;若 result.error 实际结构无法拿到该区分子,停工回报,不得放宽判据)

——则按既有空数组分支同等语义处理:`slots_covered=end-start+1, empty_response=True, ok=True`,返回整段 NO_HEADER 的 counts 段(bytes([1])*(end-start+1));ledger 行照该分支惯例落(response_sha256 取空 body 或 canonical_json([]) 的哈希,二选一并在 done 报告说明;`_successful_coverage_range` 与独立 validator(solana_exact_validate.py)的台账/覆盖重算必须照常接受该行,不得为此改 validator)。

其余一切失败路径(非 200 空体、200 无效 JSON、非 decode 类)语义零变更。

## 先红后绿(必做,证据落盘)

新增测试文件(建议 `scripts/tests/test_batch2d_stream_tail.py`),用 `--transport-fixture` 或等价单元注入:
1. **红**(修复前语义,以注入旧行为或对照断言呈现):fixture 首页返回区间前段块、续页返回 200 空体 → 旧代码该请求 ok=False、尾部 UNSCANNED;
2. **绿**(修复后):同 fixture → 尾部整段 NO_HEADER(=1)、empty_response=True、ok=True;小区间端到端(--no-getblocks)exit 0、slot_counts 无 0;
3. **防误伤绿例**(至少三条):(a) http_status=529 空体仍为可重试失败;(b) 200 + 无效 JSON(非空)仍失败;(c) 200 + 正常块数组计数不变。另跑既有 coverage/validator 相关测试确认零回归。

## 登记面与版本(全部必做)

- `scripts/lib/producer_history.py`:sqd_coverage_probe.py 两条登记按维护惯例更新(六字段、ACTIVE、`git show <commit>:<script>` 哈希与工作树一致的登记方式与批 6 T5 相同;commit 字段按"Fable 验收后代 commit"流程的占位惯例处理,若该文件惯例要求 commit 哈希而本轮不 commit,如实在 done 报告标注待验收方回填)。
- 版本五处:VERSION、pyproject.toml:15、SKILL.md 版本注释行 → 6.52.3;CHANGELOG 首索引+首详情新条目(写明批 2d、根因一句话、SUITE 计数变化)。`changelog_lint.py` 先跑后写各一次。
- `scripts/tests/run_all.py` 注册新测试;SUITE 机械计数 +1。
- 本工单与 done 报告落 `maintenance/repair-20260823-sqd-gap/`(batch2d_workorder.md 已存在,done 报告写 `batch2d_done.md`,绿证写 `batch2d_green_evidence.txt`)。

## 白名单(只许改/新增以下路径)

- scripts/solana/sqd_coverage_probe.py
- scripts/lib/net.py **仅允许加注释**(交叉注释钉常量;逻辑零变更,diff 里除注释行外不得有任何改动)
- scripts/tests/test_batch2d_stream_tail.py(新增)
- scripts/tests/run_all.py(仅注册行)
- scripts/lib/producer_history.py(仅 sqd_coverage_probe 两条目)
- VERSION / pyproject.toml / SKILL.md(仅版本行)/ CHANGELOG.md(仅新增条目)
- maintenance/repair-20260823-sqd-gap/batch2d_done.md、batch2d_green_evidence.txt(新增,**含本 done 报告自身**)

## 禁区

- 禁改 net.py 逻辑、replay_edges.py、sqd_gap_repair.py、solana_exact_validate.py、任何其他生产者/闸/契约文件;禁改既有测试;禁碰 ~/.claude/commands 部署副本;禁 commit/push(Fable 验收后代 commit);禁联网(fixture 离线足够)。
- 发现工单矛盾或白名单缺口:停工写 `batch2d_done_attempt_stopped.md` 请示,不得自行扩权。

## 完成标准

红证据+绿证据落盘;新测试与既有 coverage 相关测试全绿;`python3 scripts/tests/run_all.py` 全量通过(机械计数自报);done 报告逐项落。
