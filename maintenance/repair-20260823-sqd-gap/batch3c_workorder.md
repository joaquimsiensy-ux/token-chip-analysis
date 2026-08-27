# 批 3c 工单:census SQD 查询非法字段修复(sqd_gap_repair.py;内嵌两段提交协议)

日期:2026-08-25。基线 HEAD:985690e(v6.52.3,main,批 2d 后)。归属批 3 修复生产者家族。

## 背景与实证(只读事实)

ARC live 全普查起跑 2 分钟即停:`SQD census failed at slot 326000396: http_status 400`。
- 手工复现拿到 SQD 明文拒因:`unknown field 'parentSlot', expected one of 'number','hash','parentNumber','parentHash','height','timestamp'`——census 请求体 `_census_body()`(scripts/solana/sqd_gap_repair.py:556)的 block 字段选择混入了 Solana RPC 的字段名 `parentSlot`,SQD portal 字段表里没有它。
- census 响应消费(:820-841 与 payload :856-869)只读 `header.number`、`header.hash`、交易的 `transactionIndex/signatures/err`——**parentSlot 无任何消费方**,是既写错名又无用的请求字段。
- 修正后 body(删除该字段)已真机实测:HTTP 200,header.number=326000396、hash 在、482 笔交易、每笔恰好 {err,signatures,transactionIndex},与消费预期完全吻合。
- solana_exact_validate.py 无 census body 镜像构造(grep census_body 零命中),不需要同步。
- 根因类型:离线夹具测不出的服务端契约错(本工程第二例;第一例=批 2 分页截断)。所有既有测试的 transport fixture 不校验 SQD 字段表。
- :721/:859/:981/:1015 的 parentSlot 是 **Helius getBlock 响应**字段(Solana RPC 真叫这个名),**正确,勿动**。

## 第一段任务(施工后停,等验收方 commit)

1. `scripts/solana/sqd_gap_repair.py` `_census_body()`:删除 `"parentSlot": True`(仅此;不改名为 parentNumber——无消费方,不引入死字段)。
2. 新增守卫测试 `scripts/tests/test_batch3c_census_fields.py`:
   - 断言 `_census_body(任意 slot)` 的 `fields.block` 键集 ⊆ SQD block 字段白名单 `{number,hash,parentNumber,parentHash,height,timestamp}`,`fields.transaction` 键集 ⊆ `{transactionIndex,signatures,err,version,accountKeys,addressTableLookups,signatureCount,fee,computeUnitsConsumed,loadedAddresses,feePayer,hasDroppedLogMessages}` 的保守子集(白名单常量以注释注明来源=SQD 400 错误明文与实测;若对 transaction 白名单全集不确定,只断言当前实际用到的三键在场且 block 键集精确等于 {number,hash});
   - 红证:临时把 parentSlot 加回去断言守卫红(证据落盘后还原);
   - 绿证:现行(修复后)body 通过。
3. 证据落 `batch3c_green_evidence.txt`(含红→绿);写 `batch3c_done_stage1.md`。
4. **停工等待验收方 commit(两段协议第一段)——不改 producer_history/版本/CHANGELOG/run_all。**

## 第二段任务(验收方 commit 后以新锚续做)

验收方将把第一段 commit 哈希写入本目录 `batch3c_stage2_anchor.txt`。读到锚后:
1. `scripts/lib/producer_history.py`:sqd_gap_repair.py 的 4 条登记按批 2d 先例新增同数量 ACTIVE 条目(sha256=`git show <锚>:scripts/solana/sqd_gap_repair.py` 复算,commit=锚全哈希;旧条保留);`test_anchor_plan_v3.py` 必须 PASS。
2. `scripts/tests/run_all.py` 注册新测试(SUITE 132→133)。
3. 版本五处 6.52.4+CHANGELOG 条目(根因一句话+两段提交+SUITE 变化);changelog_lint 前后各跑。
4. 全量 `run_all.py` 通过(机械计数自报,环境性失败如实记录)。
5. 正式 `batch3c_done.md`+绿证追加。

## 白名单

第一段:sqd_gap_repair.py(仅 _census_body)、test_batch3c_census_fields.py(新)、batch3c_green_evidence.txt、batch3c_done_stage1.md。
第二段:producer_history.py(仅 sqd_gap_repair 条目)、run_all.py(仅注册行)、VERSION/pyproject.toml/SKILL.md(仅版本行)、CHANGELOG.md(仅新条目)、batch3c_done.md、batch3c_green_evidence.txt(追加)。

## 禁区

禁改 Helius 响应侧 parentSlot 四处;禁改 net.py/validator/探针/既有测试;禁 commit/push;禁联网(实测证据已由验收方提供在本工单,离线守卫足够);矛盾停工写 batch3c_stopped.md。
