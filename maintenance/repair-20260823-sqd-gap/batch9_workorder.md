# 批 9 工单：validate_repair_bundle_deep 内存规模化（校验侧流式/惰性化）

## 背景（事实，已实证）
批 8 已把修复**生产侧**装配改为流式（F4），但**校验侧** `validate_repair_bundle_deep`
（`scripts/lib/solana_exact_validate.py:1064` 起）仍将全部产物整载内存。
ARC 正式修复代 `gen-80c6929bb5fd3c1d` 的规模：

- candidate slots 153,667；evidence 文件 64,922 个（manifest 46MB）
- slot_index_map.jsonl **2.3GB**、repair_layer.jsonl 213MB、coverage_resolution.json 141MB、rpc_ledger.jsonl 60MB

在 16GB 内存的本机上，resume 发布路径调用该校验时进程两次被系统按内存压力终止
（runlogs/arc_repair_live.log：EXIT=137 于 06:24Z 与 07:43Z，各跑约 76 分钟，
调用栈采样显示大部分时间在 gc_collect_main 遍历千万级对象图）。
整载点实锤（行号按当前 HEAD=5db0abe）：

1. `evidence` 字典（约 :1186-1193）：manifest 逐项 `read_json` 后**全部驻留**——最大头；
2. `map_rows = _jsonl(slot_index_map)`（约 :1128）：2.3GB 整载为列表；
3. `layer_rows`（213MB）、`ledger_rows`（60MB）整载；resolution（141MB）整载。

## 任务
把 `validate_repair_bundle_deep`（及其私有 helper）的峰值内存降到 **O(单 slot)＋O(小型聚合)** 量级，
使其能在 16GB 本机上校验上述规模的代。**校验语义零变更**：

- 每一项检查（含批 7 盲审加固的全部检查）**一项不得少、触发条件不得变**；
- `reasons` 的文本与生成条件逐字不变；返回结构不变；
- 对同一输入，改造前后 `ok`/`reasons` 结论必须等价。

改造方向（执行方可按代码实况调整，但不得引入新依赖）：

- `evidence` 字典 → 惰性按需读盘：manifest 遍历阶段仍须逐文件完成现有校验
  （`_repair_ref` 路径校验＋JSON 可解析＋`canonical_json`），但**不驻留内容**；
  逐 slot 严格校验循环、map 循环、repair_edges 循环、live_canary 按 slot 现读所需的
  `<slot>.sqd.json`/`<slot>.ref.json`（可做小容量 LRU，容量固定常数）；
- `slot_index_map`/`repair_layer`/`rpc_ledger` 三个 jsonl → 流式逐行消费：
  header 行单独校验；逐行契约校验在流中完成；需要跨行的聚合
  （seq 连续性、slot 唯一性、签名排序唯一、计数对账、`map_lookup` 若被下游消费）
  只保留**必要的紧凑聚合**（如集合/计数/上一行值），不保留原始行列表；
  若 `map_lookup` 在函数后段被消费（请通读 :1400 之后确认），可与 merged 边校验
  重排为两遍流式，或保留 slot→紧凑映射，以实测峰值为准；
- resolution（141MB）如确需多遍随机访问可整载（可接受），census 列表若可流式化更好。

## 边界（硬约束）
- **只准改** `scripts/lib/solana_exact_validate.py`；新 helper 放同文件。
  禁改任何其他脚本/协议/schema/契约/测试外的文档。
- 测试：现有套件必须全绿；如需**新增**回归测试（等价性/流式行为），放
  `tests/` 新文件，命名 `test_batch9_*`，不改动既有测试文件。
- codex 沙箱的环境性失败（loopback/EPERM 类）如实记录即可，由验收方本机复跑裁定。
- **不 commit**：纯改文件，完成即停，由验收方代 commit（两段提交协议）。
- 发现工单与代码实况矛盾时：停工，在 done 报告写明矛盾点，不得自行扩权。

## 实测验收项（执行方须自跑并在 done 报告给出数字）
1. 相关单测/夹具测试通过清单;
2. 在真实代上跑通:以只读方式对
   `/Users/uravvv/Documents/5.6筹码分析/ARC分析/data/sqd_repair/6b99816bc26d8c53bac165b4efeb03a2b0beee563bf242e05b8906ae8dff3cb8/gen-80c6929bb5fd3c1d/bundle.json`
   调用改造后的 `validate_repair_bundle_deep`(current_base 的 edge_sha256 取
   bundle 内 base.edge_sha256 同值即可,目的是让 base 绑定检查走"通过"分支),
   记录:峰值 RSS(`/usr/bin/time -l` 的 maximum resident set size)、耗时、
   返回的 ok 与 reasons(如有 reasons 原样列出,不得隐瞒);峰值 RSS 目标 < 6GB。
   注意这是**只读**调用,禁止写案根任何文件。
3. done 报告:`maintenance/repair-20260823-sqd-gap/batch9_done.md`
   (白名单:本 done 报告自身＋`scripts/lib/solana_exact_validate.py`＋新增 `tests/test_batch9_*.py`)。

## 背景补充(为何不能绕)
该校验是发布防伪闸的必经之路(resume 发布路径 `sqd_gap_repair.py:1238` 强制调用),
不可跳过、不可外部代跑。案根的 runner 循环会自动用仓库最新代码重试发布,
故本批完成并验收 commit 后无需任何手工发布操作。
