# R9 最终验收台账

候选分支 `fix/r9-closure-20260807`,基线 main@`63cf715`。验收要素五项:全量 suite/静态守卫/49-49 SHA 回放/两轮 codex 全库盲审/版本收口。本文件由 Fable 逐项登记,完成一项记一项。

## 1. 全量 suite(PASS,2026-08-09)

- 命令:`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py`
- 结果:89 项全部通过(Fable 环境,含 codex/opus 沙箱跑不了的两项 loopback 纵切片)。
- 执行位置:批四降级收口 commit `b7a8537` 后复跑。

## 2. 静态守卫(PASS,2026-08-09)

- `invariant_scan.py`:PASS(receipt_producers=52, receipt_consumers=55, transport_calls=62, atomic_writes=42, formal_entrypoints=58, exceptions=0)。
- `test_sixlens_docs.py`:PASS(主表 49 行/详情零空栏/18 baseline-fixed/8 supplementary 复核门禁)。
- `docs_lint.py --all`:PASS(58 文档无断链)。
- `env_check.py`:PASS(pre-commit 三检within b7a8537)。
- 边界声明:批四 G2 formal E2E provenance 守卫按用户 2026-08-09 裁决降级接受——静态挡低级伪造,模块层/外层作用域重绑定伪造已知未闭合(rereview2.md N1~N20),无独立运行时兜底;详见 b4_progress.md 用户裁决节与 invariant_scan docstring。

## 3. 49/49 SHA 回放(PASS,2026-08-09)

- 工具:scratchpad/sha_replay.py(Fable 台账对表脚本,四道检查)。
- A. diff-finding-map SHA 回填表:62 行、37 个唯一 SHA,全部存在于仓库且为 HEAD 祖先;无空 SHA 行。
- B. ledger 主表恰 49 行、零空栏。
- C. 49 个详情节均含「最终结果」与「两轮盲审与 Fable 结论」。
- D. 全区间 63cf715..HEAD 改动文件 82 个,除审查产物(map 通例明文豁免:reviews/r9-batch*-*.md 入库件与 r9-reviews/、blind-reviews/ 同性质)外全部有 map owner 提及。
- 同步动作:map 通例段补审查产物豁免明文(本次明文化,非新政策——R9 各批审查报告一直未逐行登记 owner,现把惯例写成通例)。

## 4. 两轮 codex 全库盲审(进行中)

- Round A 六视角全库(互盲,不给修复台账,自由核验):待跑,输出 `blind-reviews/r9/<tip>/round-a-sixlens.md`。
- Round B 台账重放(互盲,只给 ledger,逐项对代码验证「最终结果」属实):待跑,输出 `blind-reviews/r9/<tip>/round-b-ledger-replay.md`。
- 消化标准:确认 finding 按 R9 铁律处置(新引入/半修残留必消化;P2/P3 按性质裁决);两轮完成且消化后才升版本。

## 5. 版本收口(待盲审后)

- 升 VERSION 6.36.0→6.37.0 + CHANGELOG;请用户授权 --ff-only 合并 main+push(Fable 不自行 push)。
