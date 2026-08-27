# 【消化工单】F-03 批 1b:盲审第 1 轮三项发现消化(只改点名项)

- 基线:批 1 施工后的当前工作树(未提交;main 仍= 5156f6e)。禁 git 写操作。
- 范围铁律:**只修 P1-1 / P1-2 / P2-1 三项及其点名测试**,不重构、不顺手改其他;发现新问题只记录进 done 报告。
- 盲审原文:`/private/tmp/claude-502/-Users-uravvv-Desktop-----fable----/a70a76e2-4163-45ef-87cd-b97330a3d440/tasks/bek043zfa.output`(只读参考;**P1-2 的修复方向以本工单裁定为准,不按盲审原文**)。

## P1-1(必修):复用失败后 stale recheck 行仍声明 counts 覆盖

裁定修法(最小语义变更,文档零改动):
- 复用失败(任何 fallback)时,把**本轮全部 recheck 行**的 `counts_coverage` 置为 `false` 后再继续(账本行仍保留、ok 照实——诚实审计;只撤销覆盖声明)。实现落点:`_load_known_map` 的 except 兜底路径能拿到本轮 ledger 追加区间(记录进入时的 len(ledger) 即可界定),逐行降级;
- 复用成功路径不变:recheck 行保持 `counts_coverage=true`(其观测值已被逐 slot 比对证明 == 资产字节 == 交付字节,一致性成立);
- 核实 `run_probe:991-999` 的 scan_ranges 重建与 `_successful_coverage_range`/validator `_success_ranges` 都以 `counts_coverage` 为准,降级后 stale 行自然退出覆盖并集;
- **端到端测试(盲审点名的缺口)**:run_probe 级——资产 slot 值=3,recheck 返回 4(触发复用失败),后续 full 扫返回 5;断言最终发布 PASS、`validate_coverage` 通过、账本中该 recheck 行 `counts_coverage=false`、scan_ranges 无 recheck 模式残留、最终 counts 字节=5。

## P1-2(必修,**按本裁定,不按盲审建议**):稳定身份的类型强转洗白

事实前提(裁判方 live 实测,不可违背):真实 SQD `/head` 只返回 `{number, hash}`;`dataset_id/start_block/real_time` 是配置常量,**不能要求原始响应显式携带**。数据集身份的真实载体=端点指纹(URL 含 dataset 路径)+查询模板+历史锚。

裁定修法(`_validate_known_map_identity` 内,`_normalize_metadata` 保持不动以免波及 coverage envelope 存量):
- **原始响应侧**:三个稳定键**若在场**则严格校验——`dataset_id` 非空 str、`start_block` 非 bool 的非负 int、`real_time` 恰为 bool;类型不符 → `metadata-identity-changed`。**不在场不是缺陷**(真实端点形状);
- **严格类型相等**:所有稳定键比较(资产 vs 归一化当前值、以及原始在场值 vs 资产值)用 `type(a) is type(b) and a == b`,杜绝 `False==0`/`1==True`;
- **资产侧**:`metadata_normalized` 的三个稳定键必须在场且同样严格类型(资产是我们自己导出的,历来齐全),类型不符 → `metadata-identity-changed`;
- `validate_shared_map` 同深:资产 `metadata_normalized` 三稳定键在场+严格类型,违者加 reason(如 "shared map SQD stable identity invalid");**确认 20260827 实资产通过**(dataset_id="solana-mainnet" str、start_block=0 int、real_time=true bool——通过);
- 测试:负例=原始 `start_block=false`、`real_time="false"`、资产 `real_time=1`、资产缺 `dataset_id`;**正例=原始响应仅 `{number, hash}`(真实端点形状)在其余条件满足时放行**——此正例为防将来修反的守卫,必须有且加注释说明缘由。

## P2-1(必修):anchor transport 裸异常缺账本行与结构化 reason

- `_check_identity_anchor`:把 `transport.call(...)` 纳入 try;无论 Result 失败还是直接抛异常,都追加 `ok=false, counts_coverage=false` 的 identity-anchor 行(error 字段 `_safe_text` 脱敏),统一返回 `identity-anchor-request-failed`;
- 测试:构造 transport 直接 `raise TimeoutError` 的 fake(只替换 transport,§7.5 登记),断言 `fallback_reason=="identity-anchor-request-failed"` 且账本含 `ok=false` 的 anchor 行。

## 白名单(本批全集)

- `scripts/solana/sqd_coverage_probe.py`(仅 `_load_known_map`/`_check_identity_anchor`/`_validate_known_map_identity` 及其直接辅助)
- `scripts/lib/solana_exact_validate.py`(仅 `validate_shared_map` 稳定键类型段)
- `scripts/tests/test_f03_sharedmap_reuse.py`
- `maintenance/repair-20260827-f03-sharedmap/batch1b_done.md`(done 报告,显式入白名单)
- 其余一律禁改(文档/契约无需动:P1-1 修法保持既有语义,P1-2 与文档"稳定字段全等"表述相容)。

## 完工标准

1. 三项修复全部先红后绿(基线=批 1 施工态;红例输出附 done 报告,无需单独红证据文件);
2. 本机 `python3 scripts/tests/run_all.py` 全量结果原样贴报告;
3. `validate_shared_map` 对 `assets/sqd-solana-coverage-map/20260827.json` 仍 ok=true 的运行输出;
4. done 报告:逐项修复说明+diff 摘要+§7.5 登记(P2-1 的抛异常 fake)+工单外发现清单。
