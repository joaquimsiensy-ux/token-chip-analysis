# 工单 C（F-09）盲审攻击报告（对 1595697）——判定 FAIL

> 入档件。盲审员（opus 子代理）基于干净快照 `git archive 1595697`，28 项破坏性注入＋身份键/窗口/JSON/staging 全面攻击。
> 判定：**FAIL**——2 击穿＋7 缺陷＋8 观察；28 项注入中 **16 项假覆盖**（其中 4 项经全库 run_all 95 测试复核仍全绿）。
> 基线：135 checks 与 run_all 全绿属实（其沙箱无 EPERM，两 vertical slice 直接过）；原反例 R1 跨案整体复制/R2 v2 旧收据均拒；PYTHIA 案根 69,458 文件零改动。
> 裁判（Fable）处置：见同目录 `workorder_C_fixround1.md`。

## 击穿级

### BC-01【击穿】`gate_pass` truthy 判定 → 对账真实失败的案可进正式编译链

`camp_series_provenance.py:495` `if not receipt.get("gate_pass")`。造 owners 与重放不符的真案（producer 实测 mismatch、rc=2、gate_pass=false），只把 receipt 里 `false` 改成 `"false"`/`"FAIL"`/`"0"`/`[false]`/`0.1` 任一 truthy 值 → 编译点 PASS 产出 analysis-state、发布点零 error。攻击成本＝2 个引号，文本 diff 里仍显示 "false"。根因：阶段 2 硬关卡全部结论压在一个 truthy 判定上；**同函数 evm-dict 分支用 `exit_code != 0`/`str(verdict).upper() != "PASS"` 精确比较——同一函数内两分支不等深**。

### BC-02【击穿·同族】producer 侧 `bool(closed)` → 未封口快照产无痕假 PASS 收据

`replay_edges.py:245` `bool(snap_meta.get("closed"))`：`"closed": "false"`（字符串）→ reconcile rc=0、gate_pass=True。比 BC-01 更坏：收据由 producer 亲写，producer sha/edge digest/三输入 sha 全真实自洽，下游任何闸看不出异常，事后审计无痕。同族第三处：`int(snap_meta.get("supply_raw", -1))` 缺失走默认 -1 静默。

## 缺陷级

- **BC-03** `endpoint_reconcile` 净供给交叉是条件式跳过（`if net_registered is not None`）：删掉 receipt 的 `net_supply_raw` 字段 → 交叉整条失效且 registry_anchor_check 不验在场 → BREACH（改错值则正常拒）。v3 schema 列必出、consumer 未列必验；违反仓库 N-C1"不留条件式跳过"教训。
- **BC-04** 旁路守卫零测试：删掉 `expected_* is None` 拒绝分支后 135 checks＋全库 95 测试全绿。"不得一处传了另一处放空"的唯一守卫无任何测试；将来第三个调用点忘传值即静默失效。
- **BC-05** `edge_digest` 实算零守卫＋消费侧"边完整性"实为 meta 自洽：producer digest 改取 meta 自报（i19）→ 全库全绿；删边文件本体（D2）→ 编译/发布全过；三处自洽改写（D1）→ 全过。consumer 从不接触边实物，对锚对象是同样可手写的 cache meta。done.md §8① 与新版 scan-schemas.md:563 措辞超出实际强度（且删掉了旧版"完整性由 replay_stats reject 记账＋供给真值链保证"的如实表述）。
- **BC-06** producer 快照闭合六项三验零守卫：`snapshot_ok` 放宽为恒 True（i28）→ 全库全绿。
- **BC-07** mint 身份键无形态校验：全链一致时纯空白/尾部 U+200B/U+FEFF/U+3164/U+2800/base58 外字符 `0OIl+/=`/900 字符超长全部通过编译＋发布。空值判定只用 `is None`；同函数 evm 分支有 strip 非空严判——不等深。
- **BC-08** 新必填身份字段 `data_cutoff_slot` 未登记：全库仅 state_from_facts.py:161 一处消费，无 schema 定义/无生产者写它/report-template token 必填清单没有/scan-schemas 存量迁移段未同步。存量 Solana 案重编译必撞 BLOCK 且用户无处查该填什么。
- **BC-09** `edge_extrema.ts` 死字段：`(fs,ft) > (ls,lt)` 元组比较只在 slot 相等时 ts 才起作用；ts 倒挂与全归零均放行；与 meta/边实物零对锚。done.md 称"辅助一致性"，实际零校验。

## 破坏性注入 28 项（16 假覆盖）

RED（有测试咬中）：i01 mint 精确比较、i03 extrema⊆window、i05 digest 对锚 meta、i06 producer 指纹、i07 三输入三验、i08 snapshot↔inputs 撕裂、i11/i12 两调用点传身份、i15 snapshot cutoff、i16 gate_pass 在场、i18 producer mint lower、i20 receipt.mint 比较。
**STILL_GREEN（假覆盖）**：i02 consumer chain 校验（run_all 亦全绿）、i04 window.to≤cutoff、i09 v2 专用分支（被 schema 分支同文案兜住，测试无区分力）、i10 expected_* None 拒绝（run_all 亦全绿）、i13 producer meta 合法性、i14 meta 摘要/行数撕裂、i17 consumer schema==v3、i19 digest 改自报（run_all 亦全绿）、i21 soltx meta schema/mint、i22 from>to、i23 count 正整数/digest 形态、i24 owners size 比对、i25 gate_pass 收紧 is not True（正向变异不红＝类型宽松零区分力实证）、i26 window 与 meta 一致性、i27 snapshot 三验、i28 snapshot_ok 六项（run_all 亦全绿）。

## 观察级

- **BC-O1** importer 逻辑摘要=原始行字节 sha，replay_edges=json.dumps 规范化 sha——双口径无守卫（PYTHIA 恰相等；紧凑分隔符边文件实测两口径不等，方向 fail-closed，属隐式假设）。
- **BC-O2** migration_receipt 与 collector 标识零消费者——"不冒充原生采集"仅文档层成立，consumer 眼中迁移案与原生案完全等价。
- **BC-O3** check_series_binding 只在 new-analysis profile 调用；independent-audit 复核路径 sol-rows 身份闸不生效。
- **BC-O4** sidecar 的 producer 字段无锚（可改成 evm 脚本照过）。
- **BC-O5** reconcile 链 JSON 解析未套 parse_constant 先例；超深嵌套 RecursionError 逃出 except 元组 exit 1（两义崩溃，工单 A 同族已修 waiver 面）。
- **BC-O6** test_repair_batch_c.main() 开头 `import duckdb` 失败即 print SKIP＋return 0——duckdb 缺席时 135 checks 静默全跳报成功（存量非本单引入，但工单 C 全部回归挂在此开关下）。
- **BC-O7** hard link 替身 consumer 不可辨（symlink 拒、hard link 过）——importer 设计依赖，记录在案。
- **BC-O8** scan-schemas 新版丢旧版两条现存约束（gate_pass 为 true、终态快照合计=net_supply_raw）——文档较代码退化。

## PYTHIA staging 独立复验（全过）

producer sha 实算相符；migration producer sha 相符；hard link 同 inode nlink=2 非 symlink；**4,857,654 行 26s 全量重放**两口径 sha 同=receipt=meta；extrema 逐项符；minted−burned=998158041739995 负余额 0；分母四方对锚（effective=net_supply_raw=owners 合计=链上 supply）；三输入 sha 逐项符。

## 未击穿项（摘要）

跨案整体复制、v2 收据、mint 单侧空白/零宽变体、chain 族、extrema 越窗、from>to、负 slot、自洽窗口漂移、digest 大写、count 巨整数、inputs 摘件/symlink/穿越/单侧替身、producer 换脚本/缺失、NaN/Infinity/巨整数/深嵌套（均 fail-closed）、发布 target 族、sidecar denominator 篡改、net_supply_raw 错值、gate_pass={}；绿反证：窗口尾部无转账与 extrema 压边界均无误伤。

## 只读自证

零 git 写命令；注入在 `cp -al`＋改前 unlink 断链的隔离目录；快照文件 sha 复核；注入指纹在仓库工作区命中 0；PYTHIA 案根与 staging 零改动。（其提到工作区 7 个 M 文件为并行施工线程所改——裁判核实：那是其快照导出时点 A 消化轮 2 的在途工作区，已随 c9afcfe 收口。）
