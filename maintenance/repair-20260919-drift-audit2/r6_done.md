# 施工 R6：完成

按 `maintenance/repair-20260919-drift-audit2/workorder_r6.md` v2 的 §0–§3 离线施工。D1、D2 仅作指定整行替换，九项守卫均退出 0；无差异、无停工点。

## 1. 开工基线与锚校验

内容基线：`8e54242`。施工 HEAD：`32fa272dfc04fc0a302afd3706a04718967397e8`。开工工作区为空，§0.1 指定范围与内容基线的差异为空；以下均为实际执行记录。

命令：

```sh
git status --short
```

原始输出（退出码 0；输出为空，0 B）：

```text
```

命令：

```sh
git rev-parse HEAD
```

原始输出（退出码 0）：

```text
32fa272dfc04fc0a302afd3706a04718967397e8
```

命令：

```sh
git diff --stat 8e54242 HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md
```

原始输出（退出码 0；输出为空，0 B）：

```text
```

工单规定的 `grep -n -F -x` 整行锚校验：D1、D2 各恰好匹配 1 处，行号分别为 201、184。

命令：

```sh
grep -n -F -x -- '- pageKey 有有效期，长任务中断后必过期：断点续拉一律读 CSV 末行区块号置 fromBlock 重开游标，容忍少量重复、下游按 tx hash 去重。（SIREN，07）' references/data-pipeline-evm-channels.md
```

原始输出（退出码 0）：

```text
201:- pageKey 有有效期，长任务中断后必过期：断点续拉一律读 CSV 末行区块号置 fromBlock 重开游标，容忍少量重复、下游按 tx hash 去重。（SIREN，07）
```

命令：

```sh
grep -n -F -x -- '**措辞锁定：** 聚类结论一律"高度疑似同一实体"，不写确权——共用出纳也可能是做市商/OTC 服务商同时服务多个独立客户；把证据链逐条列出（每条边标日期+金额）让读者自判（IO，07）。' references/playbook-entity-cluster-methods.md
```

原始输出（退出码 0）：

```text
184:**措辞锁定：** 聚类结论一律"高度疑似同一实体"，不写确权——共用出纳也可能是做市商/OTC 服务商同时服务多个独立客户；把证据链逐条列出（每条边标日期+金额）让读者自判（IO，07）。
```

## 2. 逐条改前 → 改后 diff

D1：删除“、下游按 tx hash 去重”，其余字节不变；净减 27 B。

D2：仅将“聚类结论一律”改为“共用出纳聚类一律”，其余字节不变；净增 6 B。

命令：

```sh
git diff --unified=0 -- references/data-pipeline-evm-channels.md references/playbook-entity-cluster-methods.md
```

原始输出（退出码 0）：

```text
diff --git a/references/data-pipeline-evm-channels.md b/references/data-pipeline-evm-channels.md
index e848062..cda55e4 100644
--- a/references/data-pipeline-evm-channels.md
+++ b/references/data-pipeline-evm-channels.md
@@ -201 +201 @@ size 与 SHA-256；全部通过后才原子将 v2/v3/pre-schema done 升为
-- pageKey 有有效期，长任务中断后必过期：断点续拉一律读 CSV 末行区块号置 fromBlock 重开游标，容忍少量重复、下游按 tx hash 去重。（SIREN，07）
+- pageKey 有有效期，长任务中断后必过期：断点续拉一律读 CSV 末行区块号置 fromBlock 重开游标，容忍少量重复。（SIREN，07）
diff --git a/references/playbook-entity-cluster-methods.md b/references/playbook-entity-cluster-methods.md
index bac01e0..bee8cfc 100644
--- a/references/playbook-entity-cluster-methods.md
+++ b/references/playbook-entity-cluster-methods.md
@@ -184 +184 @@ tier=exclude 设施与 locker 禁作合并边，被拦地址写入 clusters.json
-**措辞锁定：** 聚类结论一律"高度疑似同一实体"，不写确权——共用出纳也可能是做市商/OTC 服务商同时服务多个独立客户；把证据链逐条列出（每条边标日期+金额）让读者自判（IO，07）。
+**措辞锁定：** 共用出纳聚类一律"高度疑似同一实体"，不写确权——共用出纳也可能是做市商/OTC 服务商同时服务多个独立客户；把证据链逐条列出（每条边标日期+金额）让读者自判（IO，07）。
```

## 3. §1.1 字节实测

使用 `Path.stat().st_size` 汇总指定文件和 glob；统计不读取文件内容，`references/attic.md` 仅计大小。

| 范围 | 开工实测（B） | 完工实测（B） | 变化（B） |
| --- | ---: | ---: | ---: |
| `SKILL.md` | 8021 | 8021 | 0 |
| `commands-staging/*.md` 合计 | 8789 | 8789 | 0 |
| `references/*.md references/casebook/*.md references/labels/*.md` 合计 | 929549 | 929528 | -21 |

三组实测满足 §1.1；references 未超过 929549 B 基线，与工单预计的 929528 B 一致。

指定整行替换、其余字节与 `8e54242` 一致、字节数及已跟踪差异范围核验原始输出（退出码 0）：

```text
PASS: references/data-pipeline-evm-channels.md:201 仅指定整行替换，其余字节与 8e54242 一致；净变化 -27 B
PASS: references/playbook-entity-cluster-methods.md:184 仅指定整行替换，其余字节与 8e54242 一致；净变化 +6 B
{
  "SKILL.md": 8021,
  "commands-staging/*.md": 8789,
  "references/*.md references/casebook/*.md references/labels/*.md": 929528
}
PASS: 当前已跟踪文件差异仅含 D1/D2 两个白名单文件；暂存区无差异
```

## 4. §1.2 各守卫原始输出

以下九条命令均按工单原样运行，脚本未修改；原始输出完整保留。

命令：

```sh
python3 scripts/tests/docs_lint.py
```

原始输出（退出码 0）：

```text
PASS: 45 个文档，引用无断链、粗体配对完整
```

命令：

```sh
python3 scripts/tests/docs_lint.py --all
```

原始输出（退出码 0）：

```text
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

命令：

```sh
python3 scripts/tests/casebook_lint.py
```

原始输出（退出码 0）：

```text
casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
```

命令：

```sh
python3 scripts/tests/changelog_lint.py
```

原始输出（退出码 0）：

```text
PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 80 条 + 归档 139 条
```

命令：

```sh
python3 scripts/tests/test_contract_routes.py
```

原始输出（退出码 0）：

```text
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
```

命令：

```sh
python3 scripts/tests/test_sixlens_docs.py
```

原始输出（退出码 0）：

```text
PASS: 六视角批⑤大小口径与 archive 路由
```

命令：

```sh
python3 scripts/tests/test_g3_docs_guards.py
```

原始输出（退出码 0）：

```text
PASS: F-08 A0 exploration command
PASS: F-08 A2 formal rerun order
PASS: F-13 runner injection boundary
PASS: F-05 machine boundary
```

命令：

```sh
python3 scripts/tests/test_version_consistency.py
```

原始输出（退出码 0）：

```text
PASS: M-03 version metadata consistent at 9.0.1
```

命令：

```sh
python3 scripts/tests/test_commands_deploy_sync.py
```

原始输出（退出码 0）：

```text
PASS: 4 份 staging/部署命令 SHA-256 逐文件一致
```

## 5. git diff --stat 与差异范围

命令：

```sh
git diff --stat
```

原始输出（退出码 0）：

```text
 references/data-pipeline-evm-channels.md      | 2 +-
 references/playbook-entity-cluster-methods.md | 2 +-
 2 files changed, 2 insertions(+), 2 deletions(-)
```

`r6_done.md` 是新建、未跟踪的白名单文件，默认 `git diff --stat` 不列出；未执行 `git add`。两处已跟踪文件改动均属于 §0.3 白名单。

命令：

```sh
git diff --check
```

原始输出（退出码 0；输出为空，0 B）：

```text
```

## 6. 差异／停工点

无。施工 HEAD 可含 maintenance 提交，实际 §0.1 内容基线差异为空；所有锚均唯一且行号一致，未猜测或扩展修改。最终范围仅为 D1、D2 两个指定片段及本报告。

未修改 `scripts/`、`commands-staging/`、`CHANGELOG.md` 或两份 manifest；未 commit、未 push、未部署，未删除文件。

## 7. 禁读披露

本轮未读取 `~/.codex/` 下任何文件，未进行插件启动搜索或 memories 读取。

未直接读取本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/` 或 `references/attic.md` 的内容；`references/attic.md` 在字节统计中仅使用文件大小。`maintenance/` 下仅访问本工程目录 `maintenance/repair-20260919-drift-audit2/`。

按工单例外原样运行守卫脚本；其内部既有文档遍历行为属于获准的被测代码执行。施工全程未调用联网工具或外部 API。

