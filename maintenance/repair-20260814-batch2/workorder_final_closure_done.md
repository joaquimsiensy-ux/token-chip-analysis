# 批 2 版本收口工单完工记录：6.41.0

施工分支：`repair-20260814-batch2`。开工 HEAD：
`a3447acd7a6e4536692675d86f6969cee2063bb0`。全程未执行任何 git 写命令，未提交、
未暂存；用户提供的未跟踪输入 `workorder_final_closure.md` 与
`blindreview_C_round3.md` 保持原样。

## 一、逐项处置

### 1. 版本、CHANGELOG 与 R10 台账

- `VERSION`、`SKILL.md` 版本注释、`pyproject.toml` 已从 6.40.0 同步到 6.41.0。
- `CHANGELOG.md` 已把原“工单 B 待 6.41.0 汇总”活口径并入正式 6.41.0 条目，完整
  登记 F-10/F-02/F-09 三线、三轮盲审收敛轨迹、AKE/B2/MOG/TAG v2 重发布影响、
  本单残留锚、文档边界与冻结计数。
- 现役 R10 后继事实源确认是
  `maintenance/repair-20260813-sixlens/r10_ledger.md`。R10-2/10/11/12 保留原编号并
  标为 `CLOSED 6.41.0`；新增 R10-16～27，每条均写明三线盲审/工单出处。原 15 条清
  4 条后余 11 条，新增 12 条，现役保留/接受项共 23 条。

### 2. docstring 豁免与文档三处

- 两份 `_meaningful_text` docstring 均补齐 ASCII、拉丁、通用/CJK 标点、日文假名、
  CJK 表意文字、韩文音节、全角形式覆盖清单，并明确“两侧刻意双写、须同步改且过
  行为向量守卫”。
- 以开工 HEAD 为基线对两函数做 AST 去 docstring 比较，非 docstring 函数体逐字义
  等价：producer=`True`（AST SHA256
  `c8c1e1d444bd399bc83433d3ac141548c1da33d70ca1a43b7ce6b4c9185c42ee`），consumer=
  `True`（AST SHA256
  `ee33b743bdd84cd0f5271c5420387bcca7f7698a9f6db3b24d271f06d803a822`）。
  `git diff -U0` 显示 supply 文件唯一 hunk 是 docstring；shared 的 `_meaningful_text`
  hunk也只有 docstring，另一个 hunk是本单明确授权的 R-2 消费侧行为修复。
- shared 原 B 线保护切片（文件头至 `validate_adversarial_review` 定义行前）更新为
  1～661 行、33,525 bytes，SHA256
  `80b99dbe6eec970896cfd103f256555ad8c8ab07a42718b7f84174300d472c60`。
  `validate_adversarial_review` 当前函数切片为 4,536 bytes，SHA256
  `2bc4919706a99c084ec1d615a9818d27ef7ac1cc3859773f59029e0c05f7cd1e`。
- `a4_gate.py` 注释已删除“only known zero-rendering”不实表述，改为诚实列出点名集与
  Cf/Cc/Zl/Zp/Mn/Me 全类，并声明可见组合符取舍及项目语料边界。
- 净室协议新增泰文/阿拉伯文/天城文/藏文/希伯来文不得依赖组合符承载命题语义的
  限制；A2 超顶流程新增“批复必须含白名单文字，纯 emoji 无效”。

### 3. R-2 / R-3 / O-2 与回归锚

- **R-2**：finalize 与 shared 独立消费侧的 `(role, entrypoint sha256)` 去重从仅
  claim-review 角色扩为全部角色。相同 completeness critic entrypoint 连跑三次，即使
  artifacts/execution receipts 内容各异，producer 与 consumer 均拒；不同 entrypoint 的
  合规复核仍绿。
- **R-3**：`remove_any` 的目录清理使用 `shutil.rmtree(..., onexc=...)`；权限异常时只给
  失败节点/父目录补 owner rwx 后重试。0o500 staging 场景最终 rc=2、零残留，stderr
  保留原始 `review entrypoint failed rc=7: ORIGINAL_REVIEW_REJECTION`，不再被清理
  OSError 覆盖。
- **O-2**：新增 reproduce output 未消费字段塞 `NaN` 的接线锚。开工 HEAD 的严格
  `load_json` 行为本已正确，故自然基线为绿；按工单“接线删除即红”要求，临时把该单行
  换成裸 `json.loads` 后锚精确转红（errors=`[]`），随即用 `apply_patch` 原样恢复，终态
  零破坏性 mutation 残留。

### 4. B-16 casebook 元教训

`references/casebook/entity-clustering.md` 新增 E-19 六字段判例：实义判定漏网会
fail-open，必须以白名单收严；对账键漏网会 fail-closed 误报，须以黑名单保全未知语义。
案源指向 `workorder_B_fixround2.md` 消化轮 2 的 B-16 回归。

## 二、红 → 绿证据

### 2.1 新锚基线红

仅新增测试、生产实现未修时：

```text
python3 scripts/tests/test_repair_batch2_f02.py
rc=1
FAIL workorder B F-02 regressions: 3
```

三个失败输出为：R-3 只读 staging 一项；R-2 finalize 与消费侧独立拒绝两面。O-2
在开工 HEAD 上行为已绿，临时摘严格 loader 接线后同套件为 4 个失败，新增第四项精确是
`reproduce output 严格 loader 接线拒绝未消费字段 NaN`，证明该锚会咬接线删除。

### 2.2 修后定向绿

```text
python3 scripts/tests/test_repair_batch2_f02.py
rc=0
PASS workorder B F-02 regressions

python3 scripts/tests/test_repair_batch_a.py
rc=0
PASS batch A F-01/F-02 regressions 44/44
```

## 三、6.41.0 冻结验收

### 3.1 全量 suite 与计数口径

`run_all.SUITE` 机械计数为 96 个入口；其中 88 个文件名以 `test_` 开头，定义为业务
断言入口，另 8 个是 lint/manifest/env 守卫。此口径替代上轮 95/98 混用数字。

受限环境首跑：94/96 PASS；唯二失败为：

- `test_batch3_solana_vertical_slice.py`：首次绑定 `127.0.0.1` 即 EPERM；
- `test_batch3_evm_vertical_slice.py`：同一首次 loopback bind EPERM。

两项均未进入业务断言，无第三项失败。随后在获准环境对同一最终树完整复跑：

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py
rc=0
96/96 PASS
test_batch3_solana_vertical_slice.py PASS B3-SOL-E2E
test_batch3_evm_vertical_slice.py PASS B3-EVM-E2E
```

### 3.2 census 与静态守卫

```text
invariant_scan.py:
receipt_producers=55
receipt_consumers=73
transport_calls=62
atomic_writes=48
formal_entrypoints=58
exceptions=0

docs_lint.py --all: rc=0，58 个文档
casebook_lint.py: rc=0，6 册 37 条
changelog_lint.py: rc=0，活跃 27 条＋归档 139 条
test_version_consistency.py: rc=0，6.41.0 四处一致
git diff --check: rc=0，零输出
```

## 四、三线保护面终态 SHA-256

| 线 | 文件 | SHA-256 |
|---|---|---|
| A | `scripts/lib/supply_truth_gate.py` | `1479f11dc06ba9ac0e8dcabab2eb600dbdf743586b8cb4bbbe4507add80f4280` |
| A/B | `scripts/report/shared_release_receipt.py` | `7e803839c435c6f7aa3879a80726172f2d2ff89a6413690690a809cb2b08c434` |
| A | `scripts/tests/test_repair_batch_a.py` | `1cd68c2472ea63014428f645bf6354fbbee2abc8e3e1beb8f3e66c300e760614` |
| B | `scripts/report/adversarial_review_runner.py` | `07e1eaad4df41d5cdbdb0083d87c5ee9b6b5d9960e2cfeb980d834961beace5b` |
| B | `scripts/report/a4_gate.py` | `a2982361a7daa136194356cc84ec964cd389e8ed664ebeb2840c9893edba9525` |
| B/C | `scripts/report/audit_release_gate.py` | `4034df45233ab8868f80fdd62dc62d99ba1d6cac048416484d2f5f0133e72afb` |
| B | `scripts/tests/test_repair_batch2_f02.py` | `85bdef8fd50ecaba8ccc84bff37a58a6e86aef1c3d70b5199beb33c526f9ec16` |
| C | `scripts/lib/camp_series_provenance.py` | `dcf59fa3447644b0b98f8cc550e6eac8a9a3279b7a8279e7d9155cb0038b91ba` |
| C | `scripts/solana/replay_edges.py` | `d5292625709069ba7552de868f9f6e8bc5dcc49741f6c24b77e4c4ade41e989d` |
| C | `scripts/report/state_from_facts.py` | `919604f3997f36487744f1c6f37aecfbcbb769c576e5facc1a04540dcfb0e9a9` |
| C | `scripts/tests/test_repair_batch_c.py` | `2f7f40334f8f17592036174fc3f860bd846c0161861326a4a619255d33cd283a` |
| C | `scripts/tests/test_review_resume_integrity.py` | `3f0dfbc9767e9777fa88805ea9aca2d99d30f9a00f79c8c7d6f27c2c9aaa2e98` |
| C | `maintenance/repair-20260814-batch2/import_pythia_legacy.py` | `ce13ee2afbc40d27193060f40220bcc21a040e35cce1e9f7403fa54467c7e597` |

本单 13 个 tracked 交付文件 SHA-256：

| 文件 | SHA-256 |
|---|---|
| `CHANGELOG.md` | `0f92f8192428d1b353c916dad3ec3177b172d3e734f8e569d9421d69a2ecfbb8` |
| `SKILL.md` | `91a5f7bd48654b71dd38ed17ea250da0b8f23c31417d5360f5fb0f92a1a30776` |
| `VERSION` | `08ad224f3f83dc33ed9122b17b3c3e0c549fa0a540fa9609ee5a98e3d0c0634d` |
| `maintenance/repair-20260813-sixlens/r10_ledger.md` | `cbb06ba0be6d5bff04b1fc9a1e7559f0bd2abf271caddc4fbbab513fe384fdfc` |
| `pyproject.toml` | `3fbd1845f288d8ac1ab9c9c581a9f392d2b3c11717f007d4c34af018457124e4` |
| `references/analyze-workflow.md` | `5fbb44ef1b91d880731f863506fc18e62637b7ec644ab0563d13df3904497652` |
| `references/casebook/entity-clustering.md` | `05fa05cb5fc35f3f19e46e7a7cf3fbd4ed2cfa72165444ce7cb594533b548805` |
| `references/independent-audit-protocol.md` | `a0157b186a49697ff4d7071e4307eb95fec89e1306d06bf73521a0854d671611` |
| `scripts/lib/supply_truth_gate.py` | `1479f11dc06ba9ac0e8dcabab2eb600dbdf743586b8cb4bbbe4507add80f4280` |
| `scripts/report/a4_gate.py` | `a2982361a7daa136194356cc84ec964cd389e8ed664ebeb2840c9893edba9525` |
| `scripts/report/adversarial_review_runner.py` | `07e1eaad4df41d5cdbdb0083d87c5ee9b6b5d9960e2cfeb980d834961beace5b` |
| `scripts/report/shared_release_receipt.py` | `7e803839c435c6f7aa3879a80726172f2d2ff89a6413690690a809cb2b08c434` |
| `scripts/tests/test_repair_batch2_f02.py` | `85bdef8fd50ecaba8ccc84bff37a58a6e86aef1c3d70b5199beb33c526f9ec16` |

完工记录自身在写入后单独纳入最终只读状态核对，不把自引用 SHA 写进本文。

## 五、六视角终态自审

1. **来源与信任根**：entrypoint SHA 均从案内脚本实物重算；critic 去重不信聚合自报，
   finalize/shared 各自从 execution receipt 深验结果取值。版本号唯一事实源仍为 `VERSION`。
2. **失败路径**：R-2 两侧 fail-closed；R-3 清理失败不再替换原 verdict；O-2 在 JSON
   解析层拒未消费 NaN，不依赖 summary 字段碰巧读取。
3. **语义与误伤**：critic 的不同 entrypoint 绿例保持；字符过滤按“实义白名单/对账黑名单”
   分离；组合符和纯 emoji 边界已在协议显式化，不冒充全语种支持。
4. **清理与并发**：新增测试均使用临时目录；0o500 残留由测试 finally 兜底，修后真实
   runner 已自行清零。未引入共享全局状态或跨测试文件污染。
5. **范围与禁区**：tracked diff 仅本单 13 文件；`staging-pythia/`、PYTHIA 案根、工单 C
   生产资产均无 diff。全程未执行 add/commit/checkout/reset/restore/stash 等 git 写命令。
6. **证据闭合**：定向红绿、44/44 行为向量、96/96 获准环境全量、invariant census、
   docs/casebook/changelog/version lint 与 diff check 均来自本次最终树实跑，不引用旧报告
   代替验收。

结论：批 2 版本收口工单全部完成，6.41.0 可交裁判做最终合并核对。
