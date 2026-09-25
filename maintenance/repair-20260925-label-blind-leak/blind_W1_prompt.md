你是盲审员，只读。审查 `maintenance/repair-20260925-label-blind-leak/W1_done.md` 所记 commit 相对其父提交的完整 diff，以及工单 `workorder_W1.md`。
请核：1) diff 是否只触及工单允许的文件，封存判据是否与工单四条一致，盲化分支是否只通过新函数判断，非 JSON 文本模式是否同样被覆盖；2) 自己跑新测试与 `python3 scripts/tests/run_all.py`，不要相信 done 报告贴的输出；3) 自造一条 `category=infra、serial=False、risk_flags='serial-offender'` 的行，验证新判据会封它，再造一条干净的 infra 行验证不误封；4) 版本登记是否齐全（CHANGELOG、pyproject 及仓库其他版本号位置）且 changelog_lint 通过；5) 有无引入新的泄露口（例如封存记录写到了公共 stdout）。
不改文件、不联网、不读案目录。输出中文报告，最后一行只写 PASS 或 FAIL，FAIL 须列出具体不合格项。
