# 批 18 第三轮盲审消化工单(b18r3):闭包上限/入队判据/基准镜像 + batch_d 墙钟报告契约

基线:main=50d7767(v6.54.2)。第三轮盲审 review-mti7cloy(base=8ae0f63)三条(P1+P2×2)全部 CONFIRMED;另并入 F4=既有 flaky(与盲审无关,验收方 0901 判定)。
版本:6.54.2 → **6.54.3**。

## 纪律
- 先红后绿,红证据存 `maintenance/repair-20260823-sqd-gap/batch18_review3_red_evidence.txt`。
- 白名单:`scripts/report/shared_release_receipt.py`、`scripts/solana/audit_closed_accounts.py`、`scripts/tests/test_batch18_review_digest.py`(只许追加)、`VERSION`、`pyproject.toml`、`SKILL.md`(:23)、`CHANGELOG.md`、本目录 red_evidence/done 两件。**test_repair_batch_d.py 禁改**(F4 必须只改生产脚本使既有断言天然稳定);其余禁改同前批(scripts/lib、handoff_manifest、audit_release_gate、既有断言、ARC 案根、API key)。
- 锚点以 50d7767 为准,开工 grep 亲核,不符停工。完工不 commit。

## F1(P1)128 文件上限拒签合法大修复案
锚:`_reconciliation_bound_files` 内 `max_files = 128`(remember 超限 raise)。
实锤:ARC 案(只读参考,勿改)`data/sqd_repair/.../evidence_manifest.json` 单文件含 **12,292** 个 path 引用;修复案闭包远超 128,witness 签发 raise → 发布闸对合法案 fail-closed 误杀。
修法:上限大幅上调(建议 65536,或给出你论证的量级;防病态语义保留=超限仍拒签;JSON 扫描队列与嵌套深度同步评估)。done 里评估大闭包的签发+消费重哈希成本(万级小文件,每 run 各一遍)并给实测数字(可用合成夹具)。
红:构造引用 >128 个真实小文件的案(或直接夹具化 manifest 链),基线签发 raise;修后签发成功且全部绑定。

## F2(P2)非 .json 文件名不入递归队列
锚:`remember` 内 `path.suffix.lower() == ".json"` 才入队。receipt 路径可配置、契约不要求 .json 后缀 → 无后缀/异后缀的已验 JSON 的下游引用漏绑。
修法:入队判据从文件名改为内容嗅探——文件大小 ≤ 合理上限(与 SPARSE_THRESHOLD 对齐或 64MB)且首个非空白字节为 `{`/`[` 时尝试 `json.loads`,成功才递归;失败只保留字节绑定。防大二进制误读(先 stat 大小再读)。
红:夹具中把某 receipt 改名为无后缀且仍被 wrapper 引用,其下游实物篡改后基线 witness 仍过;修后拒。

## F3(P2)holder_outputs 解析基准与 validator 不镜像
锚:闭包 `candidate` 只试(案根,所在文档父目录)两基准且按全 path;而 `solana_observation.py:609-641` validator 对 holder_outputs 用 **basename** 在三基准搜:①`inputs.gpa_rpc` 实物父目录 ②bundle 同目录 ③bundle 同目录 `data/`。bundle 与 `scan_token_accounts.py --work-dir` 分离布局下,已验 holder 实物被闭包静默漏绑。
修法:对含 `holder_outputs`+`inputs.gpa_rpc` 形状的文档,镜像 validator 的 search_dirs+basename 逻辑把 accounts/owners 实物 remember(逐段 symlink/containment 检查同 candidate 口径);通用形状扫描保持不变。宁多勿漏。
红:构造 bundle 与 work-dir 分离(holder 实物只在 gpa 目录)的案,基线闭包不含 holder 实物、篡改后 witness 仍过;修后拒。

## F4(既有 flaky,非盲审)audit_closed_accounts 早退分支缺 sampled 段
锚:`scripts/solana/audit_closed_accounts.py:465` 附近——`"sampled"` 段只在主报告路径写;墙钟极短(如 --wall-min 0.0005)且负载高时,采样前即截断走早退报告分支,产出的 JSON 无 `sampled` 键 → `test_repair_batch_d.py:314` `report["sampled"]["wall_truncated"]` KeyError。基线 8ae0f63 复现 6/6(验收方取证)。
修法:**只改生产脚本**——统一报告契约:所有报告写出分支(含早退/各 INVALID_SAMPLE 路径)一律包含完整 `sampled` 段(字段同主路径,未及采样的计数填 0,`wall_truncated` 如实置位),墙钟截断时 `invalid_reasons` 照常含"墙钟"字样。这样 batch_d ⑤ 断言在任何负载下同构成立。**不许改 test_repair_batch_d.py**。
红:用早退可稳定触发的参数(极小 --wall-min + mock 延迟)复现基线 KeyError 或缺键报告原文;修后同参数报告含 sampled 段且 batch_d 连跑 5 次 rc=0(把 5 次 rc 记入红证据文件绿段)。

## 测试与收尾
- 新测试追加进 `test_batch18_review_digest.py`(F1/F2/F3 各一组;F4 由 batch_d 既有断言覆盖,另在红证据记连跑 5 次);SUITE 分母 146 不变。
- 回归重点:test_batch18_review_digest 全部、test_batch18_shared_bundle_witness(N11 逐字)、test_batch15_three_ledgers_frozen(N9/N10)、test_repair_batch_d 连跑 5 次、changelog/docs/version lint。
- 版本五处 6.54.3;CHANGELOG 六栏(来源=第三轮盲审 P1+P2×2,F4 单独说明为既有 flaky 收口)。全量 146 由验收方本机 nohup。
