# 返修单W1F复核r1：退回

**补齐隐含值 1 的方向正确，但 §2.1 的预填映射会破坏现有 `returned_from` 校验，既产生误拒，也放过非法输入。应改为“全部事实检查通过后，再补齐返回映射”。**

复核开始时 HEAD 为 `4c3330c`、工单为 v1；收尾时外部提交将 HEAD 更新为 `bab8508`、工单更新为 v1.1。已核对差异：生产代码及背景材料未变，且指定生产路径与 `65132ab` 无差异。以下替换意见以当前 v1.1 为准；已订正的①行号和唯一锚不再列为待改。

**1．【必改】§2.1 预填映射破坏首个返回块的事实检查**

[校验器第 583 行](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_exact_validate.py:583) 使用 `next(iter(values))` 核对首个实际返回块。原映射只收录返回块；预填全区间后，首键恒为请求起点。

例如请求 `[0,1]`，响应只含 slot 1：

- 如实填写 `returned_from=1`：工单修法拒收，违反探针的完整响应解码语义。
- 伪报 `returned_from=0`：工单修法反而接受，放宽了原有事实检查。

第二种情况已经在完整 `validate_coverage()` 路径复现，属于明确的非法输入漏拒，足以阻断派工。

**直接替换 §2.1：**

> - 2.1 `solana_exact_validate.py`：保持 `values = {}`（`:568`）、逐块赋值（`:578`）及全部事实检查（`:580-585`）不变。以唯一整行 `            raise ValueError("empty recheck response facts invalid")`（`:566`）定位，将紧随其后的空响应 `return {}`（`:567`）改为 `return {slot: 1 for slot in range(start, end + 1)}`。以唯一整行 `    return values`（`:586`）定位，将其改为 `return {slot: values.get(slot, 1) for slot in range(start, end + 1)}`。非目标行早退（`:536`）不动，不改 `_validated_inherited`。补值必须发生在完整响应事实检查之后，确保 `returned_from` 继续绑定实际首个返回块。

这是两行替换，增删合计 **4 行**，满足 ≤8 行限制。相比提前填表再修改 `returned_from` 判据，改动更少，也保留全部原检查。

**2．【必改】§2.2 必须锁定 B 的漏洞构型，并防止“拒错理由也算通过”**

原定两负例、两正例**都可在现有夹具体系构造**。[`_w1_reseal`](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_sqd_coverage_probe.py:839) 已支持更新 ledger、成功区间摘要、probe_id、CURRENT 引用及代目录。

但 B 若只剩“缺继承 slot”的一条响应，HEAD 已会因缺少值 2 的证明而拒收，不能检测本次漏洞。必须保留另一条证明该 slot 为 2 的记录。此外，v1 修法会因错误的 `returned_from` 检查拒绝 B；只断言理由含 `inherited refuted`，会让错误修法通过测试。

**直接替换 §2.2：**

> - 2.2 在现有 tempfile 夹具体系内构造下列用例；新增函数登记 main。负例 A：保留继承 slot 500 的正确完整 recheck，追加请求 `[500,500]`、响应 `[]` 的完整行，空响应事实及摘要/size 全部正确。负例 B：保留上述正确行，追加请求 `[500,501]`、仅返回 slot 501 的完整非空行，正确设置 `returned_from=returned_to=501`、`slots_covered=2`、`n_blocks=1`、`empty_response=False`，重算查询摘要及响应摘要/size。A/B 均自报 `verified`；基线应接受，修复后必须拒收，且 reasons 包含完整理由 `inherited refuted recheck results conflict`，不得因响应事实错误提前拒收。
>
> 两项正例分别为单条正确完整证明、两条对同一继承 slot 均证明值 2 的完整记录。复用 `_w1_reseal` 同步更新全部外层绑定；断言不存在引用、摘要、seq 或 probe_id 错误。
>
> 补充首块事实负例：请求起点早于首个返回块，却将 `returned_from` 伪报为请求起点，必须拒收。补充 helper 解码正例：完整非空响应存在前缀空洞时，正确的 `returned_from` 应通过事实检查，缺失 slot 返回 1。该 helper 正例不冒充正常探针生成的 `verified` 发布产物。保留既有跨案边界、canary、部分继承、失败后重试和 unverified 排除回归。

内存验证结果如下；三个版本均使用完整 `validate_coverage()`，重新绑定所有引用：

| 场景 | HEAD | 工单预填修法 | 检查后补值 |
|---|---|---|---|
| A：正确值 2＋空响应 | 错误接受 | 冲突拒收 | 冲突拒收 |
| B：正确值 2＋非空响应缺目标 | 错误接受 | 因首块事实检查拒收 | 冲突拒收 |
| 单条正确证明／两条同值证明 | 接受 | 接受 | 接受 |
| 正常跨案边界、`counts_coverage=False` | 接受 | 接受 | 接受 |
| 正常 canary 行、保留完整 evidence 的部分继承 | 接受 | 接受 | 接受 |
| 首块晚于起点，却伪报 `returned_from=起点` | 拒收 | **错误接受** | 拒收 |

边界说明：共享资产[明确要求 canary 有块头](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_exact_validate.py:1062)，candidate/refuted 也属于有块头点。因此，正常生产者不会把缺这些块头的响应标成 `verified`。本次前缀空洞实验用于核对解码和独立事实检查；不能将其称为正常 canary 发布正例。

**3．【必改】事实②③仍有错误行号；语义结论成立**

v1.1 的事实①已与实现一致。②将函数起点改成 `:595` 反而不正确；实际仍为 `:589`。③的核心语义正确，但两个空响应返回和非空覆盖赋值的行号仍未准确指向实现。

**直接替换事实②③：**

> ② `_validated_inherited` 定义于 `solana_exact_validate.py:589`；`:644` 初始化 actual，`:648` 获取 measured，`:649-652` 合并并拒绝冲突，其中冲突判据和抛错位于 `:650-651`；`:656-657` 要求本案 counts 与 actual 中该 slot 的值均为 2。当前 helper 不返回缺失块头对应的隐含值 1，故另一条记录留下的值 2 可以逃过冲突检查。
>
> ③ `_scan_request` 定义于 `sqd_coverage_probe.py:332`。特定 HTTP 200 空正文解码错误分支在 `:343-357` 处理，并于 `:357` 返回全 1；空数组分支于 `:366-368` 返回全 1。非空响应以末块确定 `covered_to`（`:383`），在 `:384` 初始化全 1，再于 `:385-389` 覆盖实际返回块的值。仅当响应覆盖至请求 end 时，才能将整个请求区间的缺失块头解释为 1；短返回不能据此推定未覆盖尾部。

**4．【必改】§0.6 的 tempfile 表述与 §2.2 冲突**

当前第 15 行写成“禁 stash/checkout/reset、tempfile”，按字面禁止 tempfile；§2.2 又要求测试落 tempfile。需要明确施工规则，避免无法执行。

**直接替换第 15 行：**

> - 0.5 修改前使用唯一完整语义行执行 `grep -n -F -x`，须恰命中 1 处；不得使用重复的 `return {}` 作为唯一锚。
> - 0.6 离线、不 commit，禁 stash/checkout/reset；测试临时夹具仅使用系统 `tempfile`，不得使用禁读目录。环境不允许创建临时目录时，停止对应测试并如实报告，禁止批量删除。

此替换针对后续施工；本次复核仍全程只读。

**5．【建议】§1.4 不应把“连续区间”写成有保障的“小区间”**

[`_recheck_known_slots`](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_coverage_probe.py:582) 按连续已知点切段，没有固定宽度上限；450-slot 分页不作用于该路径。

**直接替换 §1.4：**

> - 1.4 recheck 请求按 canary/candidate/refuted 并集的连续区间生成，当前没有固定区间宽度上限；映射规模与所处理区间长度相关，不得宣称恒为小区间。本单不改探针分段，不为压缩映射而忽略缺失 slot 或案外重叠冲突。

本次实际执行了三个实现版本的 12 类内存场景，并枚举长度 1–5、值域 `{1,2,3}` 的解码组合：检查后补值方案正确处理 **247 个完整响应**、拒绝 **116 个短返回**；预填方案在其中 **80 个完整响应**上改变首块校验，且接受对应的伪造 `returned_from`。这些枚举是解码边界检查，不等同于正常发布链测试。

未运行会落盘的整套夹具或发布流程；没有新建、修改文件或 commit，没有联网，没有读取 `~/.codex/`、memories 或指定禁区。工作区前后均干净。

| 编号 | 等级 | 意见 | 派工前状态 |
|---|---|---|---|
| 1 | 必改 | 改为事实检查后补齐返回映射 | 未解决，核心阻断 |
| 2 | 必改 | B 保留正确证明；断言冲突理由；补首块事实回归 | 未解决 |
| 3 | 必改 | 订正剩余事实②③行号 | v1.1 仍未解决 |
| 4 | 必改 | 消除 tempfile 纪律冲突 | 未解决 |
| 5 | 建议 | 删除连续区间必然很小的断言 | 建议采纳 |
