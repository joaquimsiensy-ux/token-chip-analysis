# 施工 T1: 停工

A → B → C 已按工单落地，分段测试全部 GREEN；停在最终全套验收，未达到完成标准。

run_all 已结束：exit 1，145/149 PASS，4 项失败：
- test_batch3_solana_vertical_slice.py、test_batch3_evm_vertical_slice.py：localhost bind 的 PermissionError（沙箱限制）。
- test_sqd_gap_repair.py、test_batch8_repair_scale.py：缺少 .staging_b3/routeA_pilot/426649168.json.gz；该夹具不在 Git 跟踪中，也不在工单写入白名单。

后两项不是工单预告的端口失败。未擅自补造夹具、改白名单外测试或跳过失败。需有授权的一方恢复真实夹具，并在允许绑定本地端口的环境复跑。

完整交付见 t1_done.md；原始日志见 t1_run_all.log（原位置 /tmp/run_all_t1.log）；退出码见 t1_run_all.exit；RED 原文追加保存在 t1_red_evidence.txt，GREEN 见 t1_green_evidence.txt。

HEAD 保持 14f249631895cc79954486174ddce5569cc63387；未 commit、未做 Git 写操作。此次阻断与 attempt1 的 git_sha 争议无关，git_sha 原样运行且未修改。保留全部施工进度。
