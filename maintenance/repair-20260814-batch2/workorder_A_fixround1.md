# 工单 A 消化轮 1：盲审 10 项全修

> 输入＝blindreview_A.md（同目录）。裁判裁决：10 项全修（2 击穿必修、3 缺陷补锚、5 观察全为低成本高价值）。
> 施工纪律同前：禁 git 写命令；完成后写 `workorder_A_fixround1_done.md`（逐项处置＋红→绿双跑＋自审）。
> 注意：工单 B（F-02）已收口 commit，本轮在其之上施工；shared_release_receipt.py 同文件有 B 的 adversarial 段，勿碰。

## 修复清单（对应盲审编号）

1. **F-A1（击穿）实义字符判定**：新增公共判定 `_meaningful_text(s)`＝字符串中至少含一个"非空白且非 Unicode Cf/Cc/Zs/Zl/Zp 类"的字符（用 unicodedata.category；覆盖 U+200B、U+FEFF、U+2060 等格式类）。替换 approval 四字段（nonce/user_approval/reported_to_user/approved_by）与 **waiver 存量同族两处**（approved_by/reason）的非空判定，生产/消费两侧等深（消费侧独立同名实现，沿用两侧独立纪律）。测试：U+200B/U+FEFF/U+2060 各字段两侧拒（盲审复现件转红）；正常中英文含前后空格照常放行；全角空格 U+3000 维持拒。
2. **F-A2（击穿）数值可 float 性＋异常归类**：
   - `_finite_number` 增加 int 分支的可转换性检查：`try: float(value) except OverflowError: return False`（两侧同步）；
   - waiver/approval 的 JSON 解析捕获 `RecursionError` 归为"JSON 损坏"（TolerancePolicyError，exit 2）——生产侧两个解析点＋消费侧两个解析点；
   - 修后验证：10**400 注入→exit 2＋旧收据作废归档件=1（盲审复现的契约失守转正）；20 万层深嵌套→exit 2；
   - 消费侧行为保持 BLOCK（原本未失守），但同样补 OverflowError/RecursionError 的显式归类，消除两侧兜底深度不一致。
3. **F-A3（缺陷）三值主闸独立锚**：新增定向测试＝注释/绕过生产侧三值 over_cap 判定时（用变异注入方式模拟或直接构造只有该闸能拦的场景：approved=150、observed=50、tolerance=50、无 approval——只有三值闸中 approved>100 这条能拦）→ 测试转红。确保原反例不再单靠第四值兜住。
4. **F-A4（缺陷）第四值复核直调锚**：保留 assert_waiver_covers_diff 的 over_cap 检查（库函数独立防线定位），补直接调用锚测试：构造 waiver dict（observed=300、无 over_cap_approval）直调 `assert_waiver_covers_diff(waiver, 200.0)` → 必须抛 TolerancePolicyError；并在该段代码加注释说明"CLI 链上三值闸先拦，此处防库函数被单独调用的路径"。
5. **F-A5（缺陷）NaN 双防线各自锚**：两条定向单元测试——①`_reject_constant` 直调抛 ValueError＋json.loads('{"x": NaN}', parse_constant=...) 抛；②`_finite_number(float("nan"))` 与 `_finite_number(float("inf"))` 返回 False。两侧各锚（四条断言起步）。
6. **F-A6（观察）文档对齐**：analyze-workflow.md 四处表述随 1/2 修复后逐句复核更新：数值有限性表述补"含超出 float 范围的巨整数"；非空表述改"须含实义字符（不可见字符不算）"；作废归档表述在 F-A2 修后即与实现一致复核即可；exit 1 语义句补"凭据内容导致的解析异常归 exit 2"。
7. **F-A7（观察）approval 有效期上限**：`expires_at_utc − user_decided_at_utc ≤ 30 天`（工程默认，防一次批准永久有效），超出拒；测试补 31 天拒/29 天过。9999 年远期用例转红。
8. **F-A8（观察）收据审计可见性**：超顶路径下生产侧 `envelope_inputs["over_cap_approval"] = approval_path`（进 receipt.inputs 三元组绑定）；消费侧验证：waiver 引用了 approval 时收据 inputs 必须含同一实物（缺失或不一致拒）。测试双向。
9. **F-A9（观察）evidence 独立性扩展**：evidence_refs 不得指向 over_cap_approval 文件（沿用"不得指向 replay_stats 自身"的同款检查，两侧）。测试：approval 兼任 evidence → 拒。
10. **F-A10（观察）两侧函数同源守卫**：test_repair_batch_a.py 增加同源断言——`_finite_number`/`_canonical_request_sha256`/`_meaningful_text` 两侧行为向量一致（对一组边界输入逐一比对两侧返回值；不比源码文本，比行为），防单侧静默漂移。

## 验收口径

裁判独立跑：盲审两条击穿的复现脚本场景（zwsp 四字段/10**400）修后全拒＋作废归档件=1；test_repair_batch_a.py rc=0；run_all 全绿。盲审员将做复核确认（消化轮闭合以盲审复核为准）。
