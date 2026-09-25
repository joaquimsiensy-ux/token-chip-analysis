你是只读复核员，请复核 `maintenance/repair-20260925-label-blind-leak/workorder_W1.md`。
必做：
1. 读 `scripts/labels/label_lookup.py` 120–180 行与 `scripts/labels/labels_resolver.py` 195–220、290–320 行，核对工单对根因的描述是否准确（`serial` 的定义、盲化分支的封存条件、注释声明的意图）；
2. 判断工单的四条判据（serial / category / risk_flags / source）是否足够、是否过宽（会不会把非惯犯行误封？误封的后果是什么）；`risk_flags` 在库里是字符串还是列表，工单是否覆盖；
3. 检查还有没有其他消费者在盲化模式下会绕过这个函数直接输出 row（例如非 --json 文本模式、`--unseal`、其他脚本 import label_lookup 的地方），列出行号；
4. 核对版本登记的既有做法（`git log -3 -- CHANGELOG.md`、pyproject、其他含版本号文件），指出工单描述是否与仓库实际一致；
5. 指出工单任何不清楚、矛盾或会导致施工方改错的地方。
只读，不改文件，不联网，不读任何案目录。输出中文复核报告：结论（可派 / 需修改）+ 逐条意见。
