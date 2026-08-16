# 工单 末刀补充：调度方裁决——采纳你的推荐项（选项 1）

白名单矛盾属调度方工单失误。裁决：

1. **追加授权** `references/data-pipeline-evm-recon.md`：在 §5 对账产物说明处补一句自然表述，使正文含 `evm-reconciliation-receipt/v3` 字面串（与既有 v3 语义一致，勿改动黄灯制等既有内容；三条既有 needle 与 F-09 落的 `gmgn-divergence-note/v1` 串保持原样）。
2. CT-RECON-02 的 authority_file 指向该文档（不用选项 2 的 .py 指向——契约挂权威文档才有防漂移价值，符合既有 CT-SEMANTIC-5x 惯例）。
3. `time-spotcheck/v3` 按 rg 实况：若只在 `references/analyze-workflow.md` 命中，CT-RECON-03 就挂它（stages 按该处语义定 A2）。
4. 其余按主工单执行，验收命令逐条落 `final_center_green.log`，写 `workorder_FINAL_done.md`。
