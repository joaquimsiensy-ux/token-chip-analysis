# 批 2 停工报告：开工门禁失败

- 状态：`BLOCKED_STAGING_B2_GATE`
- 时间：2026-08-23T14:39:25Z（2026-08-23 10:39:25 EDT）
- 分支：`fix/sqd-gap-v6520`
- 当前 HEAD：`733c4aed0eb18364f4c2a6a2dc98772ae68db422`
- 工单前置 HEAD：`0b93d34`（是当前 HEAD 的祖先；当前 HEAD 另含批 2 工单补 E20 的提交）
- 开工前工作树：干净

## 门禁原命令

```sh
cd .staging_b2 && shasum -a 256 -c STAGING_B2_SHA256.txt
```

结果：失败，清单列出的 21 个文件全部 `FAILED open or read`，最终输出：

```text
shasum: WARNING: 21 listed files could not be read
```

## 根因定位

`STAGING_B2_SHA256.txt` 登记的路径以 `./routeA_full/...`、`./sqd_query_variants/...` 开头；实际文件位于 `./arc_reference/routeA_full/...`、`./arc_reference/sqd_query_variants/...`。因此从工单指定的 `.staging_b2` 工作目录执行时，清单缺少 `arc_reference/` 路径前缀。

只读诊断把清单路径临时映射为 `./arc_reference/...` 后重新校验，21/21 均为 `OK`。这只证明现存 reference 文件内容与登记哈希一致，不能替代工单要求的原命令门禁，也没有修改清单。

## 停工边界

按工单“开工门禁全 OK；否则停工写 done”执行。未进入 PLAN／errata／契约实现阶段，未创建或修改探针、validator、网络层、guard、测试、fixture、manifest、资产 README 或 green evidence；未运行联网操作，未 commit，未切分支。

恢复施工前需由工单方二选一并重新冻结门禁：

1. 将 `STAGING_B2_SHA256.txt` 的 21 个路径统一补上 `./arc_reference/`；或
2. 将清单移动到 `.staging_b2/arc_reference/` 并明确新的权威校验命令。

修正后必须让工单规定的权威命令原样返回全 OK，才可重新开工。
