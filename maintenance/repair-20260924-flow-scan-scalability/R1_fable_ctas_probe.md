# 调度方本机微实验：CTAS ORDER BY 与 preserve_insertion_order（DuckDB 1.5.4，8 线程，3,000,000 行，键有大量重复）

```
preserve=false 时 CTAS ORDER BY t,ts → (按 rowid 的下降次数, 50 次点查耗时 s): (0, 1.469)
preserve=true  时 CTAS ORDER BY t,ts → (按 rowid 的下降次数, 50 次点查耗时 s): (0, 0.008)
对照:无 ORDER BY 物化            → (按 rowid 的下降次数, 50 次点查耗时 s): (1500437, 0.03)
```

结论：本次实验里 `preserve_insertion_order=false` 下的 CTAS ORDER BY 按 rowid 未见下降，但同键点查耗时是 `true` 建表的约 180 倍、甚至比无序表慢约 50 倍——说明其物理布局/块统计不利于按候选列过滤，"rowid 无下降"不等于"过滤生效"。工单 1.5 据此规定：两张边表 CTAS 前**必须**设 `preserve_insertion_order=true`、try/finally 恢复 `false`；核验以**点查耗时**为主、rowid 下降次数为辅。
