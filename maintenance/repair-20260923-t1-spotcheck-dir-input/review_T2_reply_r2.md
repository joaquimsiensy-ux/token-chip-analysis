# 工单T2复核r2：退回

v2 已吸收 r1 汇总表中的主要退回项，登记、守卫同步及消费者两层接线方案成立。此次退回限于两处工单表述：**§1.2 仍保留未经条件限定的错误断言；H16 的子目录兜底没有明确生成顺序，不能保证消除所假设的覆盖冲突。** 未发现当前 H16 正常路径存在确定的文件冲突或导入失败。

复核基线为 HEAD `a73729b9239d3c668e67ec1e661b3899e565a403`。开始及结束时工作区均干净；`d2d6641` 为 HEAD 祖先，允许检查的生产、测试及文档路径相对该提交无差异，比较时排除了禁读的 `references/attic.md`。以下“工单 L…”指 v2，“源码 :…”指当前 HEAD。

支持批准的最强证据是：两层共用的准入条件完整、既有夹具可复用、文档字节及锚点均吻合。反对直接批准的理由是：工单仍把有条件的错误路径写成必然结果，并给出不足以保证解决冲突的兜底。决定结论的是这两处说明能否准确指导施工，而非修复方向。

**1．r1 意见吸收情况**

- **`HISTORICAL_ONLY` 精确对与注释：已吸收。** 工单 L52–67 只扩充指定协议对，不改变守卫逻辑。替换文本为：

  ```python
  HISTORICAL_ONLY = {
      ("scripts/lib/anchor_plan.py", "anchor-plan/v2"),
      ("scripts/lib/time_spotcheck.py", "time-spotcheck/v3"),
  }
  ```

  源码 `test_producer_registry_current.py:21-23` 替换为：

  ```python
  # 默认验证器接受当前源码哈希；以下精确 script/protocol 对仅登记历史哈希。
  ```

  源码 `:35-50` 的脚本集合及当前哈希规则因此得到同步；`:53-68` 的 Git 复现检查仍保留。

- **私有函数及两层完整替换文：已吸收。** 工单 L74–83、L89–91、L97–100 分别规定：

  ```python
  def _time_producer_history(family, key, owner):
      if family != "evm" or key != "time" or not isinstance(owner, dict):
          return None
      producer = owner.get("producer")
      if not isinstance(producer, dict):
          return None
      path = producer.get("path")
      if not isinstance(path, str) or path not in RECON_PRODUCERS["evm"]["time"]:
          return None
      return historical_producer_hashes(path, "time-spotcheck/v3")
  ```

  ```python
      envelope_errors = validate_receipt(
          receipt, case_root=root,
          allowed_producer_hashes=_time_producer_history(family, key, receipt))
  ```

  ```python
          repo_ref_ok(
              item.get("producer"), RECON_PRODUCERS[family][key],
              f"reconciliation {key}",
              allowed_hashes=_time_producer_history(family, key, item))
  ```

  本轮将工单中的辅助函数仅编译、执行于内存：非对象 owner、list/dict 类型 path、其他 key、Solana 均返回 `None`；合法 EVM/time path 才查询固定 v3 协议。源码 `receipt_validate.py:92-93/:121-122` 保留原有非法输入处理。此结果不是完整两层回归测试通过声明。

- **H14/H15 收紧：已吸收。** 工单 L112 要求两个跨查项变体均报 envelope `producer hash mismatch`；L113 要求传入 `case_root=root`，结果恰为 `["producer hash mismatch"]`。
- **类型边界：已吸收。** 工单 L114 明确 `[]` 收据保持 `ValueError`，list path 不提前抛异常；L112 补 Solana 不取得时间历史集。辅助函数也处理 dict path。
- **H16 真实 wrapper 必测：已吸收。** L115 删除免测出口，L118–134 确为 17 行，调用真实 `validate_reconciliation_report`，包含只破坏 wrapper producer 哈希的负例及恢复后的正例。兜底措辞另见第 3 项。
- **FR-03 两行 −7 B：已吸收且字节实测吻合。** 见第 4 项。
- **CHANGELOG `:13` 整行与 200 B 索引：已吸收。** L173 是完整原文；L179 替换索引实测 200 B。
- **`:242` 锚改法：已吸收。** L38 明确它出现 29 次，只作两侧唯一锚之间的结构检查。
- **开工 HEAD 条件：已吸收。** L15 改为记录实际 HEAD、核祖先关系及源码基线不变。
- **`changelog_lint` 交调度方：已吸收。** L16、L22、L183、L187 均明确本轮不执行，未获得结果不得记 PASS。
- **§1.3/§1.5：已吸收。** L28 明确“不额外按 `input.kind` 分流”；L30 明确允许一个私有辅助函数、测试局部导入既有夹具和函数内旧哈希常量。
- **⑤来源标注：已吸收。** L9 将源码事实与 QUQ/OPN 个案材料分开，明确后者为“调度方提供、复核未独立核验”。
- **FR-02：保持另单。** L3 未将其并入本工单。

但 r1 正文指出的 **§1.2 错误路径限定仍未吸收**，见下一项。

**2．必须修订：工单 L27 的 §1.2**

当前末句：

> 固定 protocol 使 v2 schema 旧收据在 `:1404` 以"unknown schema"被拒而非含混的"hash mismatch"。

这不是必然结果。源码先检查 envelope、target、verdict、mode 和 formal-ready 条件，之后才到 `:1404`。陌生哈希仍先被拒绝；固定查询协议不会改变这一顺序。

此外，“不新增符号”与 L30 明确允许 `_time_producer_history` 的措辞有歧义，宜一起收窄。

**工单 L27 整行建议替换为：**

> - 1.2 历史集的 `script` 参数取自被校验 ref 自身的 `producer.path`（envelope 层＝receipt 的 producer.path，wrapper 层＝item 的 producer.path）；仅当 owner、producer 均为 dict、path 为 str 且属于 `RECON_PRODUCERS["evm"]["time"]` 时查询，否则传 `None`。两层共用 `_time_producer_history`，查询 `protocol` 固定为字面量 `"time-spotcheck/v3"`，不新增协议常量。该限定保证历史集与 producer.path 对应；仅当生产者哈希及此前全部校验通过时，v2 schema 才会在原 `:1404` 被报 `unknown schema`，陌生哈希仍先报 `producer hash mismatch`。

**3．H16：正常接法相容，兜底需要明确顺序**

签名相容。源码 `test_handoff_manifest.py:73` 为：

```python
def make_case(d, chain="eth", token=TOKEN, as_of_block=999):
```

工单以位置参数传 `str(root)`，以关键字传 token/block，chain 默认 `"eth"`，与 `test_recon_deep_reverify.py:23-27` 的 `TARGET` 一致。

文件写入关系如下：

| 写入来源 | 主要文件 | 与原时间夹具的关系 |
|---|---|---|
| `_plan_fixture` | `merged.csv`、`anchor_plan.input.json`、`anchor_plan.json`、`anchor_plan.receipt.json` | 原时间收据绑定对象 |
| `_produce_time` | `time_spotcheck.json`、`time_spotcheck_transcript.json` | 当前生产者输出 |
| `make_case` 的深验夹具 | `fixture_anchor_input_manifest.json`、`fixture_anchor_plan.json`、`fixture_anchor_plan_receipt.json`、`fixture_time_transcript.json` | 不覆盖上述 plan/transcript |
| `make_case` 的 wrapper | `reconciliation_report.json`、四份 `reconciliation_*_receipt.json` | 可将 time 项换成另存的 H11 收据 |
| `make_case` 其他输出 | 候选/筛选/身份文件、`data_map.json`、holders/transfers/Solana 边及 meta、EVM bundle/transcript、accounting/supply/wave/flow、`fixture_recon_*` 等文件、sealed 文件及分布扫描 JSON/图 | 未发现与原时间绑定文件同名 |
| `make_case` 的时间占位输出 | `time_spotcheck.json` | **会覆盖原同名收据**，但不覆盖另存的 H11 收据 |

因此，**按 L107 要求另存 H11 后，当前同 root 的 17 行正常接法在静态检查上成立**。wrapper 的三个供应相关检查仍共用夹具的 replay_stats；time 检查不参加源码 `:1467-1477` 的三份 replay_stats 同源比较。

导入也成立：

- 直跑测试时，`scripts/tests` 在 Python 脚本搜索路径中；测试 `:15` 只是前插 lib/report，没有移除 tests。
- `run_all.py:218-219` 用子进程按脚本路径启动测试，同样保留 tests 路径。
- `test_handoff_manifest.py` 的同目录夹具导入也可按此解析。

**兜底的问题：**仅把同样的“先 `_produce_time`、再 `make_case`”迁移到新目录，不能保证解决两者之间假设存在的同名覆盖；还必须统一 case root 和引用基准。

**将工单 L115 括号中从“若实跑发现”开始的兜底文字替换为：**

> 若实跑发现其他夹具文件冲突，使用新建子目录作为 H16 的独立 case root：先在该目录调用 `make_case`，再调用 `_produce_time`，再另存 H11 收据并生成相对于该目录的 item 引用；随后读取该目录的 wrapper、替换 time 项并执行正负例。该分支不再重复调用 `make_case`，不得混用父目录的 `h11_item` 或引用基准，并在完成报告说明冲突文件及处理顺序。

按当前已核实的文件名，这个生成顺序可行；无需修改外部夹具文件。本轮未运行会落盘的 `make_case` 或完整 H16。

**4．新增锚、FR-03 语义和字节**

实际逐行执行 `grep -n -F -x`，结果如下：

| 文件 | 核验行号 | 匹配结果 |
|---|---|---|
| `shared_release_receipt.py` | 1208、1221、1459、1460 | 每行恰 1 处，行号一致 |
| `test_producer_registry_current.py` | 21、22、23、24 | 每行恰 1 处，行号一致 |
| `test_recon_deep_reverify.py` | 593、601 | 每行恰 1 处，行号一致 |
| `references/data-pipeline-evm-recon.md` | 152、158 | 每行恰 1 处，行号一致 |
| `CHANGELOG.md` | 13、100 | 每行恰 1 处，行号一致 |
| `producer_history.py` | 241、243 | 每行恰 1 处，行号一致 |
| `producer_history.py` | 242 | 29 处；v2 已正确降为结构核对 |

工单 L61 只引用了三行注释的首尾，遗漏中间行原文。**不影响此次实际锚核验结果**，但建议将 L61 展开为：

> 并把 `:21-23` 以下三行注释分别按整行核验恰 1 处且行号一致，再整体替换为下方一行：

```python
# receipt_validate.py:115-116 默认以当前文件哈希为允许集；登记表两条只是
# 历史 anchor-plan/v2。test_anchor_plan_v3.py:376-377 的 assert not
# validate_receipt(...) 证明当前哈希无错误。豁免仅限下述精确协议对。
```

FR-03 拟议替换文本可以保留。

源码 `references/data-pipeline-evm-recon.md:152`，工单 L150：

```text
python3 scripts/lib/time_spotcheck.py --plan anchor_plan.json --input <生成plan的同一文件或v2目录> \
```

源码 `:158`，工单 L162：

```text
- 产物 `time_spotcheck.json`（`time-spotcheck/v3`）绑定 target、plan/receipt、文件或清单及 RPC transcript；exit 0/2/1＝PASS/FAIL/ERROR。EVM READY 必备，AUTO_GATES 重读。目录输入时 runner `inputs` 可省略；若登记则填清单/叶子文件，`data_map.files` 填叶子，均不填目录。
```

语义结论：

- `time_spotcheck.py:543-548` 明确对应 `ERROR/1`、`FAIL/2`、`PASS/0`。新文保留了结果映射和 ERROR 不可当 PASS 的含义，但不应解读为每次进程 exit 1 都必然成功写出 ERROR 收据；源码也存在写入失败后返回 1 的路径。
- `handoff_manifest.py:107-112` 登记时间产物为 EVM READY 必备件及 AUTO_GATE；`:368-369/:647-649` 按 EVM 家族决定必备件，未按 split-run 决定。因此删除 split-run 限定**没有引入错误陈述，反而更贴合正式 READY 路径**。
- “绑定 target”是对原 chain/token/final-block 说明的压缩，不改变绑定要求。
- runner/data_map 的文件登记说明不要求消费者重算目录，也未改动 FR-02。

UTF-8、不含换行的实测：

| 行 | 原文 | 替换文 | 净变化 |
|---|---:|---:|---:|
| `:152` | 111 B | 110 B | −1 B |
| `:158` | 326 B | 320 B | −6 B |
| 合计 | 437 B | 430 B | **−7 B** |

`929092→929085` 是以工单提供总量为起点的推算；本轮没有读取禁读文件重算 references 全量。

**5．9.0.4 详细段与 docs_lint**

9.0.4 的“修”档位适当。L182–183 已要求详细段包含出处、改法、实际字节/测试、成本指标，以及 Git 来源和 review 编号，**足够指导施工**。无需提前虚构尚未发生的测试结果。“git commit”应记录历史生产者来源及实际基线，不能理解为要求本轮创建提交。

工单 L179 的索引原文可保留，实测 **200 B**：

```text
- **9.0.4**（2026-09-23）登记旧 time-spotcheck/v3 哈希并接通 EVM 时间收据两层校验，恢复存量文件案兼容；补充同一输入目录用法。schema 不变，版本档位 修。
```

`docs_lint` 对此次 `:158` 替换未见新增风险：

- 新行 `**` 数量为 0，不触发粗体不配对。
- 使用实际 `REF_RE` 检查，路径引用匹配数为 0，不引入断链。
- `CT-RECON-03` 要求的 `time-spotcheck/v3` 仍在。
- 未改变文档入口、路径或契约 ID。

本地 `.git/hooks/pre-commit:7` 确实调用 `docs_lint.py`。**没有执行该 hook 或完整 lint**：普通模式也会读取 `references/**/*.md`，包含禁读的 attic；脚本其他扫描还涉及 archive。完整结果由获准调度方验收，不能把上述局部核验记成全量 PASS。

**汇总表**

| 项目 | r2 判定 | 意见 |
|---|---|---|
| HISTORICAL_ONLY 精确对及注释 | 通过 | 已吸收，守卫检查逻辑保留 |
| 私有函数与两层替换文 | 通过 | 已吸收，类型过滤内存核验符合预期 |
| H14/H15、类型边界 | 通过 | 已吸收 |
| H16 真实路径与负例 | 通过 | 必测要求已落入工单 |
| H16 签名、导入、正常文件布局 | 通过 | 静态核验相容，未宣称绿测 |
| H16 子目录兜底 | **退回** | 明确先 make_case、后 produce/H11，并统一 case root |
| FR-03 两行及 −7 B | 通过 | 字节准确，语义成立 |
| 新增锚行号及唯一性 | 通过 | 指定行全部符合 |
| 注释 `:22` 原文呈现 | 建议 | L61 补全中间行 |
| `:242` 锚改法 | 通过 | 两侧唯一锚＋结构核对 |
| CHANGELOG 原文及 200 B 索引 | 通过 | 已吸收 |
| 开工 HEAD 条件 | 通过 | 已吸收 |
| changelog_lint 调度方验收 | 通过 | 已吸收，不冒记 PASS |
| §1.3/§1.5 | 通过 | 边界和私有函数授权明确 |
| §1.2 错误路径说明 | **退回** | r1 已指出的问题仍保留，须限定前置条件 |
| ⑤来源标注 | 通过 | 源码事实与个案转述已分开 |
| 9.0.4 详细段要求 | 通过 | 足够，填实际结果即可 |
| docs_lint 局部影响 | 通过 | 未见粗体、断链或 needle 回归；全量待验 |
| FR-02 范围 | 通过 | 继续另单 |

本轮全程只读、离线；无新增、修改、删除或提交文件，未读取所列禁区，未运行会创建案卷的测试。报告仅交付于本最终答复。
